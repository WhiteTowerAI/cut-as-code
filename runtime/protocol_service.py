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
GRAPHIC_MOTION_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "video-add-graphic-motion"
    / "scripts"
)
sys.path.insert(0, str(CARDS_SCRIPTS))
import apply_cards_review  # noqa: E402
import projectlib  # noqa: E402
sys.path.insert(0, str(GRAPHIC_MOTION_SCRIPTS))
import graphic_motion_plan  # noqa: E402


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
            return {"ok": False, "error": "plan.update accepts only a typed operation update"}
        return self._under_lease(request, lambda context: self._apply_plan_update(context, request["review"]))

    def _apply_plan_update(self, context, review):
        root, snapshot, project, operation, plan_path, plan, expected = context
        operation_id = operation.get("id")
        transform_only = False
        if operation_id == "content-cards":
            try:
                if not isinstance(review, dict):
                    raise ValueError("content-cards review must be an object")
                editor_transform = review.get("editor_transform")
                editor_content_bounds = review.get("editor_content_bounds")
                transform_only = set(review) in (
                    {"schema_version", "editor_transform"},
                    {"schema_version", "editor_transform", "editor_content_bounds"},
                )
                if transform_only and review.get("schema_version") != 1:
                    raise ValueError("content-cards transform schema_version must be 1")
                typed_review = {
                    key: copy.deepcopy(value)
                    for key, value in review.items()
                    if key not in {"editor_transform", "editor_content_bounds"}
                }
                updated_plan = copy.deepcopy(plan) if transform_only else apply_cards_review.apply_review(plan, typed_review)
                if editor_transform is not None:
                    if (not isinstance(editor_transform, dict)
                            or set(editor_transform) not in (
                                {"cue_id", "x", "y", "scale"},
                                {"cue_id", "x", "y", "scale_x", "scale_y"},
                            )):
                        raise ValueError("content-cards editor_transform is invalid")
                    cue_id = editor_transform["cue_id"]
                    transform = {key: value for key, value in editor_transform.items() if key != "cue_id"}
                    updated_plan = self._apply_editor_transform(
                        updated_plan, "content-cards", cue_id, transform
                    )
                    if editor_content_bounds is not None:
                        updated_plan = self._apply_editor_content_bounds(
                            updated_plan, "content-cards", cue_id, editor_content_bounds
                        )
            except (TypeError, ValueError) as exc:
                return {"ok": False, "error": f"invalid content-cards review: {exc}"}
        elif operation_id == "captions":
            try:
                transform_only = (
                    isinstance(review, dict)
                    and set(review) in (
                        {"schema_version", "cue_id", "editor_transform"},
                        {"schema_version", "cue_id", "editor_transform", "editor_content_bounds"},
                    )
                )
                if transform_only:
                    if review.get("schema_version") != 1:
                        raise ValueError("caption update schema_version must be 1")
                    updated_plan = self._apply_editor_transform(
                        plan, "captions", review.get("cue_id"), review.get("editor_transform")
                    )
                    if "editor_content_bounds" in review:
                        updated_plan = self._apply_editor_content_bounds(
                            updated_plan, "captions", review.get("cue_id"), review["editor_content_bounds"]
                        )
                else:
                    updated_plan = self._apply_caption_update(plan, review)
                    self._validate_caption_plan(updated_plan)
            except (TypeError, ValueError) as exc:
                return {"ok": False, "error": f"invalid captions update: {exc}"}
        elif operation_id == "graphic-motion":
            try:
                transform_only = (
                    isinstance(review, dict)
                    and set(review) in (
                        {"schema_version", "cue_id", "editor_transform"},
                        {"schema_version", "cue_id", "editor_transform", "editor_content_bounds"},
                    )
                )
                if transform_only:
                    if review.get("schema_version") != 1:
                        raise ValueError("graphic-motion update schema_version must be 1")
                    updated_plan = self._apply_editor_transform(
                        plan, "graphic-motion", review.get("cue_id"), review.get("editor_transform")
                    )
                    if "editor_content_bounds" in review:
                        updated_plan = self._apply_editor_content_bounds(
                            updated_plan, "graphic-motion", review.get("cue_id"), review["editor_content_bounds"]
                        )
                else:
                    updated_plan = self._apply_graphic_motion_update(plan, review)
                    self._validate_graphic_motion_plan(root, project, updated_plan)
            except (TypeError, ValueError) as exc:
                return {"ok": False, "error": f"invalid graphic-motion update: {exc}"}
        else:
            return {"ok": False, "error": "unsupported operation"}
        if updated_plan == plan:
            return {"ok": True, "result": "no_change", "snapshot": self._public_snapshot(snapshot)}
        updated_project = copy.deepcopy(project)
        changed = next(item for item in updated_project["operations"] if item.get("id") == operation_id)
        changed["revision"] += 1
        if transform_only:
            if "plan_sha256" in changed:
                payload = json.dumps(
                    updated_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
                changed["plan_sha256"] = hashlib.sha256(payload).hexdigest()
            try:
                dependent_plan_writes = self._advance_transform_dependencies(
                    root, updated_project, operation_id, changed["revision"]
                )
            except (TypeError, ValueError) as exc:
                return {"ok": False, "error": f"invalid downstream dependency update: {exc}"}
        else:
            dependent_plan_writes = []
            changed.update({"status": "stale", "outputs": []})
            if isinstance(changed.get("check"), dict):
                changed["check"] = {**changed["check"], "status": "pending"}
            self._invalidate_dependents(updated_project, operation_id)
        updated_project.setdefault("render", {})["status"] = "draft"
        return self._commit(
            root, plan_path, updated_plan, updated_project, expected,
            "plan.update", operation_id, dependent_plan_writes,
        )

    @staticmethod
    def _apply_caption_update(plan, update):
        if (not isinstance(update, dict)
                or not {"schema_version", "cue_id"}.issubset(update)
                or set(update) - {"schema_version", "cue_id", "text", "editor_transform", "editor_content_bounds"}):
            raise ValueError("caption update must contain only typed cue fields")
        if "text" not in update and "editor_transform" not in update:
            raise ValueError("caption update must change text or editor_transform")
        if update.get("schema_version") != 1:
            raise ValueError("caption update schema_version must be 1")
        cue_id = update.get("cue_id")
        if not isinstance(cue_id, str) or not cue_id.strip():
            raise ValueError("caption cue_id must be nonblank")
        updated = copy.deepcopy(plan)
        cue = ProtocolService._find_editor_cue(updated, "captions", cue_id)
        if cue is None:
            raise ValueError("caption cue does not exist")
        if "text" in update:
            text = update["text"]
            if not isinstance(text, str) or not text.strip():
                raise ValueError("caption text must be nonblank")
            if len(text) > 500:
                raise ValueError("caption text is too long")
            cue["text"] = text.strip()
            cue["lines"] = [text.strip()]
        if "editor_transform" in update:
            ProtocolService._validate_editor_transform(update["editor_transform"])
            updated = ProtocolService._apply_editor_transform(
                updated, "captions", cue_id, update["editor_transform"]
            )
        if "editor_content_bounds" in update:
            updated = ProtocolService._apply_editor_content_bounds(
                updated, "captions", cue_id, update["editor_content_bounds"]
            )
        if "text" in update:
            updated["review"] = {"status": "pending", "evidence": []}
        return updated

    @staticmethod
    def _apply_graphic_motion_update(plan, update):
        if (not isinstance(update, dict)
                or not {"schema_version", "cue_id"}.issubset(update)
                or set(update) - {"schema_version", "cue_id", "enabled", "editor_transform", "editor_content_bounds"}):
            raise ValueError("graphic-motion update must contain only typed cue fields")
        if "enabled" not in update and "editor_transform" not in update:
            raise ValueError("graphic-motion update must change enabled or editor_transform")
        if update.get("schema_version") != 1:
            raise ValueError("graphic-motion update schema_version must be 1")
        cue_id = update.get("cue_id")
        if not isinstance(cue_id, str) or not cue_id.strip():
            raise ValueError("graphic-motion cue_id must be nonblank")
        updated = copy.deepcopy(plan)
        cue = next((item for item in updated.get("cues", []) if isinstance(item, dict) and item.get("id") == cue_id), None)
        if cue is None:
            raise ValueError("graphic-motion cue does not exist")
        if "enabled" in update:
            enabled = update["enabled"]
            if not isinstance(enabled, bool):
                raise ValueError("graphic-motion enabled must be boolean")
            if enabled:
                cue["status"] = "verified"
                cue.pop("skip_reason", None)
            else:
                cue["status"] = "skipped"
                cue["skip_reason"] = "Disabled in the Protocol V1 editor"
        if "editor_transform" in update:
            ProtocolService._validate_editor_transform(update["editor_transform"])
            updated = ProtocolService._apply_editor_transform(
                updated, "graphic-motion", cue_id, update["editor_transform"]
            )
        if "editor_content_bounds" in update:
            updated = ProtocolService._apply_editor_content_bounds(
                updated, "graphic-motion", cue_id, update["editor_content_bounds"]
            )
        bindings = list(graphic_motion_plan._input_bindings(updated))
        for item in updated.get("cues", []):
            if isinstance(item, dict) and item.get("status") == "verified":
                bindings.extend(graphic_motion_plan._cue_bindings(item))
        updated["delivery_bindings"] = bindings
        return updated

    @staticmethod
    def _validate_editor_transform(transform):
        if not isinstance(transform, dict) or set(transform) not in (
            {"x", "y", "scale"}, {"x", "y", "scale_x", "scale_y"},
        ):
            raise ValueError("editor_transform must contain x, y, and scale or scale_x and scale_y")
        x, y = transform["x"], transform["y"]
        scale_x = transform.get("scale_x", transform.get("scale"))
        scale_y = transform.get("scale_y", transform.get("scale"))
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (x, y, scale_x, scale_y)):
            raise ValueError("editor_transform values must be numbers")
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("editor_transform position must be normalized")
        if not 0.1 <= scale_x <= 4 or not 0.1 <= scale_y <= 4:
            raise ValueError("editor_transform scale is out of range")
        if "scale" in transform:
            return {"x": float(x), "y": float(y), "scale": float(scale_x)}
        return {"x": float(x), "y": float(y), "scale_x": float(scale_x), "scale_y": float(scale_y)}

    @staticmethod
    def _apply_editor_transform(plan, operation_id, cue_id, transform):
        if not isinstance(cue_id, str) or not cue_id.strip():
            raise ValueError("editor_transform cue_id must be nonblank")
        transform = ProtocolService._validate_editor_transform(transform)
        updated = copy.deepcopy(plan)
        cue = ProtocolService._find_editor_cue(updated, operation_id, cue_id)
        if cue is None:
            raise ValueError("editor_transform cue does not exist")
        if transform in (
            {"x": 0.5, "y": 0.5, "scale": 1.0},
            {"x": 0.5, "y": 0.5, "scale_x": 1.0, "scale_y": 1.0},
        ):
            cue.pop("editor_transform", None)
        else:
            cue["editor_transform"] = transform
        return updated

    @staticmethod
    def _apply_editor_content_bounds(plan, operation_id, cue_id, bounds):
        if not isinstance(cue_id, str) or not cue_id.strip():
            raise ValueError("editor_content_bounds cue_id must be nonblank")
        if operation_id == "content-cards":
            if not isinstance(bounds, dict) or bounds.get("cue_id") != cue_id:
                raise ValueError("content-cards editor_content_bounds is invalid")
            bounds = {key: value for key, value in bounds.items() if key != "cue_id"}
        bounds = ProtocolService._validate_editor_content_bounds(bounds)
        updated = copy.deepcopy(plan)
        cue = ProtocolService._find_editor_cue(updated, operation_id, cue_id)
        if cue is None:
            raise ValueError("editor_content_bounds cue does not exist")
        cue["editor_content_bounds"] = bounds
        return updated

    @staticmethod
    def _find_editor_cue(plan, operation_id, cue_id):
        collection = "cards" if operation_id == "content-cards" else "cues"
        for position, item in enumerate(plan.get(collection, []), 1):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if operation_id == "captions" and not item_id:
                item_id = f"cue-{position:03d}"
            if item_id == cue_id:
                return item
        return None

    @staticmethod
    def _validate_editor_content_bounds(bounds):
        if not isinstance(bounds, dict) or set(bounds) != {"x", "y", "width", "height"}:
            raise ValueError("editor_content_bounds must contain x, y, width, and height")
        values = tuple(bounds[key] for key in ("x", "y", "width", "height"))
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError("editor_content_bounds values must be numbers")
        x, y, width, height = values
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("editor_content_bounds must fit the normalized canvas")
        return {"x": float(x), "y": float(y), "width": float(width), "height": float(height)}

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
        operation_id = operation.get("id")
        if review.get("based_on", {}).get(operation_id) != operation.get("revision"):
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
        return self._commit(root, None, None, updated_project, expected, "review.record", operation.get("id"))

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
        operation_id = request.get("operation")
        if operation_id not in {"content-cards", "captions", "graphic-motion"}:
            return {"ok": False, "error": "unsupported operation"}
        root = self._projects[project_id]["root"]
        snapshot = build_snapshot(root)
        if snapshot["read_only"]:
            return {"ok": False, "error": "project is read-only"}
        read_set = request.get("read_set")
        if not isinstance(read_set, dict) or set(read_set) != {"project", "operation", "plan"}:
            return {"ok": False, "error": "complete read_set is required"}
        project_resource = next(item for item in snapshot["resources"] if item["kind"] == "project")
        operation = next((item for item in snapshot["view"]["operations"] if item["id"] == operation_id), None)
        plan_resource = next((item for item in snapshot["resources"]
                              if item.get("operation_id") == operation_id), None)
        expected = {
            "project": project_resource["etag"],
            "operation": operation and operation["etag"],
            "plan": plan_resource and plan_resource["etag"],
            "dependent_plans": {
                item.get("operation_id"): item["etag"]
                for item in snapshot["resources"]
                if item.get("kind") == "plan"
            },
        }
        if read_set.get("operation") != expected["operation"] or read_set.get("plan") != expected["plan"]:
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(snapshot)}
        if not operation or not plan_resource:
            return {"ok": False, "error": f"{operation_id} operation is incomplete"}
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

    def _advance_transform_dependencies(self, root, project, changed_id, revision):
        for operation in project.get("operations", []):
            based_on = operation.get("based_on")
            if isinstance(based_on, dict) and changed_id in based_on:
                based_on[changed_id] = revision
        for review in project.get("reviews", []):
            if changed_id in review.get("depends_on", []):
                review["status"] = "stale"

        writes = []
        for operation in project.get("operations", []):
            if operation.get("id") != "graphic-motion" or operation.get("id") == changed_id:
                continue
            based_on = operation.get("based_on")
            if not isinstance(based_on, dict) or changed_id not in based_on:
                continue
            plan_value = operation.get("plan")
            if not isinstance(plan_value, str) or not plan_value.strip():
                raise ValueError("graphic-motion dependency plan is missing")
            plan_path = projectlib.resolve_project_path(root, plan_value)
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("graphic-motion dependency plan is unreadable") from exc
            plan_based_on = plan.get("based_on")
            if not isinstance(plan_based_on, dict) or changed_id not in plan_based_on:
                raise ValueError("graphic-motion dependency plan does not track the changed operation")
            plan["based_on"][changed_id] = revision
            self._validate_graphic_motion_plan(root, project, plan)
            if "plan_sha256" in operation:
                operation["plan_sha256"] = graphic_motion_plan.canonical_sha256(plan)
            writes.append((plan_path, plan, "graphic-motion"))
        return writes

    def _commit(self, root, plan_path, plan, project, expected, verb, operation_id, dependent_plan_writes=None):
        project_path = root / "work" / "project.json"
        validation_errors = projectlib.validate_project(
            project, root, check_files=True, dependency_mode="allow_stale"
        )
        if validation_errors:
            return {"ok": False, "error": "invalid committed project: " + "; ".join(validation_errors)}
        self._before_final_cas()
        current = build_snapshot(root)
        current_project_etag = next(item for item in current["resources"] if item["kind"] == "project")["etag"]
        current_operation = next(item for item in current["view"]["operations"] if item["id"] == operation_id)["etag"]
        current_plan = next(item for item in current["resources"] if item.get("operation_id") == operation_id)["etag"]
        if (current_operation, current_plan) != (expected["operation"], expected["plan"]):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        dependent_plan_writes = dependent_plan_writes or []
        current_plan_etags = {
            item.get("operation_id"): item["etag"]
            for item in current["resources"]
            if item.get("kind") == "plan"
        }
        if any(
            current_plan_etags.get(dependent_id) != expected.get("dependent_plans", {}).get(dependent_id)
            for _path, _value, dependent_id in dependent_plan_writes
        ):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        if verb == "review.record":
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            target = next((item for item in current_project.get("reviews", [])
                           if item.get("id") == expected.get("review_id")), None)
            if self._receipt_fingerprint(target) != expected.get("review"):
                return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        if current_project_etag != expected["project"]:
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            project = self._reconcile_project(current_project, project, verb, operation_id, expected.get("review_id"))
            validation_errors = projectlib.validate_project(
                project, root, check_files=True, dependency_mode="allow_stale"
            )
            if validation_errors:
                return {"ok": False, "error": "invalid reconciled project: " + "; ".join(validation_errors)}
        writes = []
        if plan_path is not None:
            writes.append((plan_path, self._json_bytes(plan)))
        writes.extend((path, self._json_bytes(value)) for path, value, _operation in dependent_plan_writes)
        writes.append((project_path, self._json_bytes(project)))
        journal_dir = projectlib.editor_state_dir(root, create=True)
        journal_path = journal_dir / "transaction.json"
        if journal_path.exists():
            raise PreparedTransactionError("pending transaction journal exists")
        intent = {
            "schema_version": 1,
            "transaction_id": str(uuid.uuid4()),
            "operation": operation_id,
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
            current_operation = next(item for item in current["view"]["operations"] if item["id"] == operation_id)["etag"]
            current_plan = next(item for item in current["resources"] if item.get("operation_id") == operation_id)["etag"]
            if (current_project, current_operation, current_plan) != (current_project_etag, expected["operation"], expected["plan"]):
                journal_path.unlink()
                return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
            current_plan_etags = {
                item.get("operation_id"): item["etag"]
                for item in current["resources"]
                if item.get("kind") == "plan"
            }
            if any(
                current_plan_etags.get(dependent_id) != expected.get("dependent_plans", {}).get(dependent_id)
                for _path, _value, dependent_id in dependent_plan_writes
            ):
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

    def _reconcile_project(self, current, proposed, verb, operation_id, target_review_id=None):
        reconciled = copy.deepcopy(current)
        if verb == "plan.update":
            changed = next(item for item in proposed["operations"] if item.get("id") == operation_id)
            index = next(index for index, item in enumerate(reconciled["operations"])
                         if item.get("id") == operation_id)
            reconciled["operations"][index] = copy.deepcopy(changed)
            self._invalidate_dependents(reconciled, operation_id)
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
            operation_id = intent.get("operation")
            if (intent.get("schema_version") != 1
                    or operation_id not in {"content-cards", "captions", "graphic-motion"}
                    or intent.get("verb") not in {"plan.update", "review.record"}
                    or intent.get("state") not in {"prepared", "committed"}
                    or not isinstance(transaction_id, str) or str(uuid.UUID(transaction_id)) != transaction_id
                    or not isinstance(files, list) or not files):
                raise ValueError
            project_path = root / "work" / "project.json"
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            operation = next((item for item in current_project.get("operations", []) if item.get("id") == operation_id), None)
            if not operation or not isinstance(operation.get("plan"), str):
                raise ValueError
            plan_path = projectlib.resolve_project_path(root, operation["plan"])
            required_targets = {project_path.resolve()}
            allowed = set(required_targets)
            if intent["verb"] == "plan.update":
                required_targets.add(plan_path.resolve())
                allowed.add(plan_path.resolve())
                graphic_operation = next(
                    (item for item in current_project.get("operations", []) if item.get("id") == "graphic-motion"),
                    None,
                )
                if (operation_id != "graphic-motion" and graphic_operation
                        and isinstance(graphic_operation.get("plan"), str)):
                    allowed.add(projectlib.resolve_project_path(root, graphic_operation["plan"]).resolve())
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
            if not required_targets.issubset(seen):
                raise ValueError
            if self._validate_recovered(root, targets, operation_id):
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

    def _validate_recovered(self, root, targets, operation_id="content-cards"):
        proposed = {path: item["new_content"] for path, item in targets}
        project_path = root / "work" / "project.json"
        try:
            project = json.loads(proposed.get(project_path, project_path.read_text(encoding="utf-8")))
            errors = projectlib.validate_project(project, root, check_files=False, dependency_mode="allow_stale")
            operation = next((item for item in project.get("operations", [])
                              if item.get("id") == operation_id), None)
            if not operation or not isinstance(operation.get("plan"), str):
                return [*errors, f"{operation_id} plan is missing"]
            plan_path = projectlib.resolve_project_path(root, operation["plan"])
            plan = json.loads(proposed.get(plan_path, plan_path.read_text(encoding="utf-8")))
            if operation_id == "content-cards":
                self._validate_cards_plan(plan)
            elif operation_id == "captions":
                self._validate_caption_plan(plan)
            else:
                self._validate_graphic_motion_plan(root, project, plan)
            graphic_operation = next(
                (item for item in project.get("operations", []) if item.get("id") == "graphic-motion"),
                None,
            )
            if graphic_operation and isinstance(graphic_operation.get("plan"), str):
                graphic_path = projectlib.resolve_project_path(root, graphic_operation["plan"]).resolve()
                if graphic_path in proposed and graphic_path != plan_path:
                    graphic_plan = json.loads(proposed[graphic_path])
                    self._validate_graphic_motion_plan(root, project, graphic_plan)
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
    def _validate_caption_plan(plan):
        if not isinstance(plan, dict) or plan.get("schema_version") != 1:
            raise ValueError("caption plan schema_version must be 1")
        cues = plan.get("cues")
        if not isinstance(cues, list) or not cues:
            raise ValueError("caption plan cues must be a non-empty list")
        ids = []
        previous_end = None
        for position, cue in enumerate(cues, 1):
            if not isinstance(cue, dict):
                raise ValueError(f"caption cue {position} must be an object")
            cue_id = cue.get("id")
            if cue_id is None:
                cue_id = f"cue-{position:03d}"
            elif not isinstance(cue_id, str) or not cue_id.strip():
                raise ValueError(f"caption cue {position} id must be nonblank")
            text = cue.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"caption cue {cue_id} text must be nonblank")
            program_range = cue.get("program_range")
            if not isinstance(program_range, dict):
                raise ValueError(f"caption cue {cue_id} program_range is required")
            start = program_range.get("start_s")
            end = program_range.get("end_s")
            if (not isinstance(start, (int, float)) or isinstance(start, bool)
                    or not isinstance(end, (int, float)) or isinstance(end, bool)
                    or start < 0 or end <= start):
                raise ValueError(f"caption cue {cue_id} program_range is invalid")
            if previous_end is not None and start < previous_end:
                raise ValueError(f"caption cue {cue_id} overlaps the previous cue")
            previous_end = end
            ids.append(cue_id)
        if len(ids) != len(set(ids)):
            raise ValueError("caption cue ids must be unique")

    @staticmethod
    def _validate_graphic_motion_plan(root, project, plan):
        active_sequence = project.get("active_sequence")
        sequences = project.get("sequences") if isinstance(project.get("sequences"), dict) else {}
        sequence = sequences.get(active_sequence) if isinstance(active_sequence, str) else None
        timeline_value = sequence.get("timeline") if isinstance(sequence, dict) else None
        if not isinstance(timeline_value, str) or not timeline_value.strip():
            raise ValueError("graphic-motion requires the active timeline")
        timeline_path = projectlib.resolve_project_path(root, timeline_value)
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        errors = graphic_motion_plan.validate_plan(
            plan,
            timeline,
            project=project,
            project_root=root,
            verify_files=False,
        )
        if errors:
            raise ValueError("; ".join(errors))

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
