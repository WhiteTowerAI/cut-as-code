"""Fixed JSON-line RPC for root-confined editor protocol access."""

import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path

from project_snapshot import build_snapshot, canonical_project_root, load_resource


CARDS_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "video-add-content-cards"
    / "scripts"
)
sys.path.insert(0, str(CARDS_SCRIPTS))
import apply_cards_review  # noqa: E402
import projectlib  # noqa: E402


class PreparedTransactionError(RuntimeError):
    pass


class ProtocolService:
    def __init__(self):
        self._projects = {}
        self._before_final_cas = lambda: None
        self._after_prepare = lambda: None
        self._after_replace = lambda _path: None
        self._before_post_commit_validation = lambda: None
        self._before_hash_verification = lambda: None

    def handle_request(self, request):
        if not isinstance(request, dict):
            return {"ok": False, "error": "request must be an object"}
        try:
            return self._dispatch(request)
        except Exception:
            return {"ok": False, "error": "invalid request"}

    def _dispatch(self, request):
        verb = request.get("verb")
        if verb == "open_project":
            return self._open_project(request)
        if verb == "get_snapshot":
            return self._get_snapshot(request)
        if verb == "get_resource":
            return self._get_resource(request)
        if verb == "plan.update":
            return self._update_plan(request)
        if verb == "review.record":
            return self._record_review(request)
        return {"ok": False, "error": "unknown verb"}

    def _open_project(self, request):
        try:
            root = canonical_project_root(request.get("project_root", ""))
        except (OSError, TypeError, ValueError):
            return {
                "ok": False,
                "error": "project root must contain work/project.json",
            }
        try:
            lease = self._acquire_lease(root)
        except ValueError:
            return {"ok": False, "error": "project editor state directory is unsafe"}
        if lease is None:
            recovery_error = "project mutation is busy during recovery"
        else:
            try:
                recovery_error = self._recover(root)
            finally:
                self._release_lease(lease)
        project_id = "project_" + uuid.uuid4().hex
        self._projects[project_id] = {"root": root, "quarantine": recovery_error}
        snapshot = build_snapshot(root)
        if recovery_error:
            snapshot["read_only"] = True
            snapshot["errors"] = [recovery_error, *snapshot["errors"]]
        return {
            "ok": True,
            "project_id": project_id,
            "snapshot": self._public_snapshot(snapshot),
        }

    def _get_snapshot(self, request):
        project_id = request.get("project_id")
        invalid = self._validate_id("project_id", project_id)
        if invalid:
            return invalid
        project = self._projects.get(project_id)
        if project is None:
            return {"ok": False, "error": "unknown project_id"}
        snapshot = build_snapshot(project["root"])
        if project["quarantine"]:
            snapshot["read_only"] = True
            snapshot["errors"] = [project["quarantine"], *snapshot["errors"]]
        return {"ok": True, "snapshot": self._public_snapshot(snapshot)}

    def _get_resource(self, request):
        project_id = request.get("project_id")
        invalid = self._validate_id("project_id", project_id)
        if invalid:
            return invalid
        resource_id = request.get("resource_id")
        invalid = self._validate_id("resource_id", resource_id)
        if invalid:
            return invalid
        project = self._projects.get(project_id)
        if project is None:
            return {"ok": False, "error": "unknown project_id"}
        root = project["root"]
        snapshot = build_snapshot(root)
        resource = snapshot["_registry"].get(resource_id)
        if resource is None:
            return {"ok": False, "error": "unknown resource_id"}
        try:
            content = load_resource(root, resource)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return {"ok": False, "error": f"invalid resource: {exc}"}
        return {"ok": True, "resource": content}

    def _update_plan(self, request):
        if set(request) != {"verb", "project_id", "operation", "read_set", "review"}:
            return {"ok": False, "error": "plan.update accepts only a typed content-cards review"}
        return self._under_lease(request, lambda context: self._apply_plan_update(context, request["review"]))

    def _apply_plan_update(self, context, review):
        root, snapshot, project, operation, plan_path, plan, expected = context
        try:
            updated_plan = apply_cards_review.apply_review(plan, review)
        except (TypeError, ValueError) as exc:
            return {"ok": False, "error": f"invalid content-cards review: {exc}"}
        if updated_plan == plan:
            return {"ok": True, "result": "no_change", "snapshot": self._public_snapshot(snapshot)}
        updated_project = copy.deepcopy(project)
        changed = next(item for item in updated_project["operations"] if item.get("id") == "content-cards")
        changed.update({"revision": changed["revision"] + 1, "status": "stale", "outputs": []})
        if isinstance(changed.get("check"), dict):
            changed["check"] = {**changed["check"], "status": "pending"}
        self._invalidate_dependents(updated_project, "content-cards")
        updated_project.setdefault("render", {})["status"] = "draft"
        return self._commit(root, plan_path, updated_plan, updated_project, expected, "plan.update")

    def _record_review(self, request):
        if set(request) != {"verb", "project_id", "operation", "read_set", "decision"}:
            return {"ok": False, "error": "review.record accepts only a typed decision"}
        return self._under_lease(request, lambda context: self._apply_review_record(context, request["decision"]))

    def _apply_review_record(self, context, decision):
        root, _snapshot, project, operation, _plan_path, _plan, expected = context
        if not isinstance(decision, dict) or set(decision) != {
            "review_id", "decision", "snapshot_etag", "evidence_hashes", "actor", "rationale"
        }:
            return {"ok": False, "error": "invalid review decision"}
        if decision.get("decision") not in {"approved", "rejected"}:
            return {"ok": False, "error": "invalid review decision"}
        if any(not isinstance(decision.get(field), str) or not decision[field].strip()
               for field in ("review_id", "snapshot_etag", "actor", "rationale")):
            return {"ok": False, "error": "review decision fields must be nonblank"}
        hashes = decision.get("evidence_hashes")
        if not isinstance(hashes, list) or not hashes or any(
            not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value)
            for value in hashes
        ):
            return {"ok": False, "error": "review evidence hashes must be SHA-256 values"}
        review = next((item for item in project.get("reviews", [])
                       if item.get("id") == decision["review_id"]), None)
        if not review or review.get("status") != "draft":
            return {"ok": False, "error": "review is missing, stale, or already decided"}
        if review.get("based_on", {}).get("content-cards") != operation.get("revision"):
            return {"ok": False, "error": "review revision is stale"}
        if review.get("snapshot_etag") != decision["snapshot_etag"] or review.get("evidence_hashes") != hashes:
            return {"ok": False, "error": "review evidence binding mismatch"}
        current_snapshot = build_snapshot(root)
        if decision["snapshot_etag"] != current_snapshot.get("snapshot_etag"):
            return {"ok": False, "error": "review snapshot binding is stale"}
        current_artifact_hashes = self._review_artifact_hashes(root)
        if any(value.removeprefix("sha256:") not in current_artifact_hashes for value in hashes):
            return {"ok": False, "error": "review evidence artifact is missing or stale"}
        current_errors = projectlib.validate_project(
            project, root, check_files=True, dependency_mode="require_current"
        )
        if current_errors:
            return {"ok": False, "error": "review requires current dependencies: " + "; ".join(current_errors)}

        updated_project = copy.deepcopy(project)
        receipt = next(item for item in updated_project["reviews"] if item.get("id") == review["id"])
        receipt.update({
            "status": decision["decision"],
            "decision_mode": "human",
            "actor": decision["actor"].strip(),
            "rationale": decision["rationale"].strip(),
            "snapshot_etag": decision["snapshot_etag"],
            "evidence_hashes": list(hashes),
        })
        return self._commit(root, None, None, updated_project, expected, "review.record")

    def _under_lease(self, request, apply):
        project_id = request.get("project_id")
        invalid = self._validate_id("project_id", project_id)
        if invalid:
            return invalid
        registered = self._projects.get(project_id)
        if registered is None:
            return {"ok": False, "error": "unknown project_id"}
        if registered["quarantine"]:
            return {"ok": False, "error": "project is in recovery quarantine"}
        root = registered["root"]
        lease = self._acquire_lease(root)
        if lease is None:
            return {"ok": False, "status": 409, "error": "project mutation is busy"}
        try:
            context = self._mutation_context(request)
            if isinstance(context, dict) and "error" in context:
                return context
            return apply(context)
        except PreparedTransactionError:
            registered["quarantine"] = "pending transaction requires recovery"
            return {"ok": False, "error": "project entered recovery quarantine"}
        finally:
            self._release_lease(lease)

    def _mutation_context(self, request):
        project_id = request["project_id"]
        if request.get("operation") != "content-cards":
            return {"ok": False, "error": "unsupported operation"}
        root = self._projects[project_id]["root"]
        snapshot = build_snapshot(root)
        if snapshot["read_only"]:
            return {"ok": False, "error": "project is read-only"}
        read_set = request.get("read_set")
        if not isinstance(read_set, dict) or set(read_set) != {"project", "operation", "plan"}:
            return {"ok": False, "error": "complete read_set is required"}
        project_resource = next(item for item in snapshot["resources"] if item["kind"] == "project")
        operation = next((item for item in snapshot["view"]["operations"] if item["id"] == "content-cards"), None)
        plan_resource = next((item for item in snapshot["resources"]
                              if item.get("operation_id") == "content-cards"), None)
        expected = {
            "project": project_resource["etag"],
            "operation": operation and operation["etag"],
            "plan": plan_resource and plan_resource["etag"],
        }
        if read_set.get("operation") != expected["operation"] or read_set.get("plan") != expected["plan"]:
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(snapshot)}
        if not operation or not plan_resource:
            return {"ok": False, "error": "content-cards operation is incomplete"}
        registry = snapshot["_registry"][plan_resource["id"]]
        plan_path = root / "work" / registry["value"]
        project_path = root / "work" / "project.json"
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "error": "project changed during mutation"}
        if request.get("verb") == "review.record":
            decision = request.get("decision")
            review_id = decision.get("review_id") if isinstance(decision, dict) else None
            target = next((item for item in project.get("reviews", []) if item.get("id") == review_id), None)
            expected["review_id"] = review_id
            expected["review"] = self._receipt_fingerprint(target)
        return root, snapshot, project, operation, plan_path, plan, expected

    @staticmethod
    def _invalidate_dependents(project, changed_id):
        stale = {changed_id}
        changed = True
        while changed:
            changed = False
            for node in [*project.get("operations", []), *project.get("reviews", [])]:
                if node.get("id") in stale:
                    continue
                if stale.intersection(node.get("depends_on", [])):
                    node["status"] = "stale"
                    stale.add(node.get("id"))
                    changed = True
        for review in project.get("reviews", []):
            if changed_id in review.get("depends_on", []):
                review["status"] = "stale"

    def _commit(self, root, plan_path, plan, project, expected, verb):
        project_path = root / "work" / "project.json"
        validation_errors = projectlib.validate_project(
            project, root, check_files=True, dependency_mode="allow_stale"
        )
        if validation_errors:
            return {"ok": False, "error": "invalid committed project: " + "; ".join(validation_errors)}
        self._before_final_cas()
        current = build_snapshot(root)
        current_project_etag = next(item for item in current["resources"] if item["kind"] == "project")["etag"]
        current_operation = next(item for item in current["view"]["operations"] if item["id"] == "content-cards")["etag"]
        current_plan = next(item for item in current["resources"] if item.get("operation_id") == "content-cards")["etag"]
        if (current_operation, current_plan) != (expected["operation"], expected["plan"]):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        if verb == "review.record":
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            target = next((item for item in current_project.get("reviews", [])
                           if item.get("id") == expected.get("review_id")), None)
            if self._receipt_fingerprint(target) != expected.get("review"):
                return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        if current_project_etag != expected["project"]:
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            project = self._reconcile_project(current_project, project, verb, expected.get("review_id"))
            validation_errors = projectlib.validate_project(
                project, root, check_files=True, dependency_mode="allow_stale"
            )
            if validation_errors:
                return {"ok": False, "error": "invalid reconciled project: " + "; ".join(validation_errors)}
        writes = []
        if plan_path is not None:
            writes.append((plan_path, self._json_bytes(plan)))
        writes.append((project_path, self._json_bytes(project)))
        journal_dir = projectlib.editor_state_dir(root, create=True)
        journal_path = journal_dir / "transaction.json"
        if journal_path.exists():
            raise PreparedTransactionError("pending transaction journal exists")
        intent = {
            "schema_version": 1,
            "transaction_id": str(uuid.uuid4()),
            "operation": "content-cards",
            "verb": verb,
            "state": "prepared",
            "files": [
                {
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "old_hash": self._hash(path.read_bytes()),
                    "new_hash": self._hash(data),
                    "new_content": data.decode("utf-8"),
                }
                for path, data in writes
            ],
        }
        self._atomic_write(journal_path, self._json_bytes(intent))
        staged = []
        try:
            self._after_prepare()
            for path, data in writes:
                handle = tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False)
                temporary = Path(handle.name)
                try:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                finally:
                    handle.close()
                staged.append((path, temporary))
            current = build_snapshot(root)
            current_project = next(item for item in current["resources"] if item["kind"] == "project")["etag"]
            current_operation = next(item for item in current["view"]["operations"] if item["id"] == "content-cards")["etag"]
            current_plan = next(item for item in current["resources"] if item.get("operation_id") == "content-cards")["etag"]
            if (current_project, current_operation, current_plan) != (current_project_etag, expected["operation"], expected["plan"]):
                journal_path.unlink()
                return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
            for path, temporary in staged:
                os.replace(temporary, path)
                self._after_replace(path)
            self._before_post_commit_validation()
            snapshot = build_snapshot(root)
            if snapshot["read_only"]:
                raise PreparedTransactionError("committed project failed validation")
            self._before_hash_verification()
            for item in intent["files"]:
                if self._hash((root / item["path"]).read_bytes()) != item["new_hash"]:
                    raise PreparedTransactionError("committed project hash verification failed")
            intent["state"] = "committed"
            self._atomic_write(journal_path, self._json_bytes(intent))
            journal_path.unlink()
            return {"ok": True, "result": "committed", "snapshot": self._public_snapshot(snapshot)}
        except PreparedTransactionError:
            raise
        except Exception as exc:
            raise PreparedTransactionError("transaction failed after prepare") from exc
        finally:
            for _path, temporary in staged:
                temporary.unlink(missing_ok=True)

    def _reconcile_project(self, current, proposed, verb, target_review_id=None):
        reconciled = copy.deepcopy(current)
        if verb == "plan.update":
            changed = next(item for item in proposed["operations"] if item.get("id") == "content-cards")
            index = next(index for index, item in enumerate(reconciled["operations"])
                         if item.get("id") == "content-cards")
            reconciled["operations"][index] = copy.deepcopy(changed)
            self._invalidate_dependents(reconciled, "content-cards")
            reconciled.setdefault("render", {})["status"] = "draft"
        else:
            changed = next(item for item in proposed.get("reviews", [])
                           if item.get("id") == target_review_id)
            index = next(index for index, item in enumerate(reconciled.get("reviews", []))
                         if item.get("id") == target_review_id)
            reconciled["reviews"][index] = copy.deepcopy(changed)
        return reconciled

    @classmethod
    def _receipt_fingerprint(cls, receipt):
        return cls._hash(cls._json_bytes(receipt)) if isinstance(receipt, dict) else None

    @staticmethod
    def _acquire_lease(root):
        return projectlib.acquire_project_lease(root, blocking=False)

    @staticmethod
    def _release_lease(lease):
        projectlib.release_project_lease(lease)

    @staticmethod
    def _unlock_descriptor(descriptor):
        os.lseek(descriptor, 0, os.SEEK_SET)

    @staticmethod
    def _json_bytes(value):
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    @staticmethod
    def _hash(value):
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def _atomic_write(path, data):
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _recover(self, root):
        journal = projectlib.editor_state_dir(root, create=True) / "transaction.json"
        if not journal.is_file():
            return None
        try:
            intent = json.loads(journal.read_text(encoding="utf-8"))
            files = intent["files"]
            transaction_id = intent.get("transaction_id")
            if (intent.get("schema_version") != 1 or intent.get("operation") != "content-cards"
                    or intent.get("verb") not in {"plan.update", "review.record"}
                    or intent.get("state") not in {"prepared", "committed"}
                    or not isinstance(transaction_id, str) or str(uuid.UUID(transaction_id)) != transaction_id
                    or not isinstance(files, list) or not files):
                raise ValueError
            project_path = root / "work" / "project.json"
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            cards = next((item for item in current_project.get("operations", []) if item.get("id") == "content-cards"), None)
            if not cards or not isinstance(cards.get("plan"), str):
                raise ValueError
            plan_path = projectlib.resolve_project_path(root, cards["plan"])
            allowed = {project_path.resolve(), plan_path.resolve()}
            expected_targets = {project_path.resolve()} if intent["verb"] == "review.record" else allowed
            states = []
            targets = []
            seen = set()
            for item in files:
                path = (root / item["path"]).resolve()
                if path not in allowed or path in seen:
                    raise ValueError
                seen.add(path)
                content = item.get("new_content")
                if (not isinstance(content, str)
                        or self._hash(content.encode("utf-8")) != item.get("new_hash")):
                    raise ValueError
                json.loads(content)
                current = self._hash(path.read_bytes())
                if current == item["new_hash"]:
                    states.append("new")
                elif current == item["old_hash"]:
                    states.append("old")
                else:
                    return "ambiguous transaction recovery"
                targets.append((path, item))
            if seen != expected_targets:
                raise ValueError
            if self._validate_recovered(root, targets):
                return "ambiguous transaction recovery"
            if intent.get("state") == "committed":
                if not all(state == "new" for state in states):
                    return "ambiguous transaction recovery"
                journal.unlink(missing_ok=True)
                return None
            if all(state == "new" for state in states):
                journal.unlink(missing_ok=True)
                return None
            if any(state == "new" for state in states):
                for (path, item), state in zip(targets, states):
                    if state == "old":
                        self._atomic_write(path, item["new_content"].encode("utf-8"))
                journal.unlink(missing_ok=True)
                return None
            journal.unlink(missing_ok=True)
            return None
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return "ambiguous transaction recovery"

    @staticmethod
    def _review_artifact_hashes(root):
        review_root = root / "review"
        if not review_root.is_dir():
            return set()
        hashes = set()
        for path in review_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                resolved = path.resolve(strict=True)
                if os.path.commonpath((str(root), str(resolved))) != str(root):
                    continue
                hashes.add(hashlib.sha256(resolved.read_bytes()).hexdigest())
            except (OSError, ValueError):
                continue
        return hashes

    def _validate_recovered(self, root, targets):
        proposed = {path: item["new_content"] for path, item in targets}
        project_path = root / "work" / "project.json"
        try:
            project = json.loads(proposed.get(project_path, project_path.read_text(encoding="utf-8")))
            errors = projectlib.validate_project(project, root, check_files=False, dependency_mode="allow_stale")
            cards = next((item for item in project.get("operations", [])
                          if item.get("id") == "content-cards"), None)
            if not cards or not isinstance(cards.get("plan"), str):
                return [*errors, "content-cards plan is missing"]
            plan_path = projectlib.resolve_project_path(root, cards["plan"])
            plan = json.loads(proposed.get(plan_path, plan_path.read_text(encoding="utf-8")))
            self._validate_cards_plan(plan)
            return errors
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return ["invalid recovered JSON"]

    @staticmethod
    def _validate_cards_plan(plan):
        if not isinstance(plan, dict) or plan.get("schema_version") != 1:
            raise ValueError("content-cards plan schema_version must be 1")
        apply_cards_review.build_cards_plan.validate_brief(plan.get("brief"))
        cards = plan.get("cards")
        if not isinstance(cards, list):
            raise ValueError("content-cards plan cards must be a list")
        ids = []
        for card in cards:
            if not isinstance(card, dict) or not isinstance(card.get("id"), str) or not card["id"].strip():
                raise ValueError("content-cards plan card id must be nonblank")
            ids.append(card["id"])
            treatment = card.get("visual_treatment")
            if not isinstance(treatment, dict):
                raise ValueError("content-cards visual treatment must be an object")
            layout = treatment.get("layout") or "default"
            apply_cards_review.build_cards_plan.validate_visual_treatment(card.get("card_type"), layout)
            apply_cards_review.build_cards_plan.validate_chart_data(card, layout)
            placement = card.get("placement")
            if placement is not None:
                apply_cards_review.build_cards_plan.validate_clearance(placement)
        if len(ids) != len(set(ids)):
            raise ValueError("content-cards plan card ids must be unique")

    @staticmethod
    def _public_snapshot(snapshot):
        return {key: value for key, value in snapshot.items() if not key.startswith("_")}

    @staticmethod
    def _validate_id(name, value):
        if not isinstance(value, str) or not value.strip():
            return {"ok": False, "error": f"{name} must be a nonblank string"}
        return None


def main():
    service = ProtocolService()
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"ok": False, "error": f"invalid request JSON: {exc}"}
        else:
            response = service.handle_request(request)
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
