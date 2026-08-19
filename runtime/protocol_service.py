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

from project_snapshot import build_snapshot, canonical_project_root, load_resource, snapshot_binding


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
        if verb == "timeline.edit":
            return self._edit_timeline(request)
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

    def _edit_timeline(self, request):
        if set(request) != {"verb", "project_id", "read_set", "command"}:
            return {"ok": False, "error": "timeline.edit accepts only a typed timeline command"}
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
            context = self._timeline_mutation_context(request)
            if isinstance(context, dict) and "error" in context:
                return context
            return self._apply_timeline_edit(context, request["command"])
        except PreparedTransactionError:
            registered["quarantine"] = "pending transaction requires recovery"
            return {"ok": False, "error": "project entered recovery quarantine"}
        finally:
            self._release_lease(lease)

    def _timeline_mutation_context(self, request):
        root = self._projects[request["project_id"]]["root"]
        snapshot = build_snapshot(root)
        if snapshot["read_only"]:
            return {"ok": False, "error": "project is read-only"}
        read_set = request.get("read_set")
        if not isinstance(read_set, dict) or set(read_set) != {"project", "operation", "timeline", "plans"}:
            return {"ok": False, "error": "complete timeline read_set is required"}
        if not isinstance(read_set.get("plans"), dict):
            return {"ok": False, "error": "complete timeline read_set is required"}
        project_resource = next((item for item in snapshot["resources"] if item["kind"] == "project"), None)
        timeline_resource = next((item for item in snapshot["resources"] if item["kind"] == "timeline"), None)
        cut_operation = next((item for item in snapshot["view"]["operations"] if item["id"] == "cut"), None)
        if not project_resource or not timeline_resource or not cut_operation:
            return {"ok": False, "error": "an editable cut operation and timeline are required"}
        expected = {
            "project": project_resource["etag"],
            "operation": cut_operation["etag"],
            "timeline": timeline_resource["etag"],
        }
        if any(read_set.get(key) != value for key, value in expected.items()):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(snapshot)}
        registry = snapshot["_registry"][timeline_resource["id"]]
        timeline_path = root / "work" / registry["value"]
        project_path = root / "work" / "project.json"
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "error": "project changed during timeline mutation"}
        active_sequence = project.get("active_sequence")
        sequence = project.get("sequences", {}).get(active_sequence, {})
        if "cut" not in sequence.get("operations", []):
            return {"ok": False, "error": "cut is not active on the current sequence"}
        plan_files = []
        for operation in project.get("operations", []):
            operation_id = operation.get("id") if isinstance(operation, dict) else None
            plan_value = operation.get("plan") if isinstance(operation, dict) else None
            if (operation_id != "cut"
                    and isinstance(plan_value, str) and plan_value.strip()):
                path = projectlib.resolve_project_path(root, plan_value)
                try:
                    data = path.read_bytes()
                    plan_files.append({
                        "operation_id": operation_id,
                        "path": path,
                        "etag": self._hash(data),
                        "plan": json.loads(data.decode("utf-8")),
                    })
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
                    return {"ok": False, "error": "an active downstream plan is unavailable"}
        plan_etags = {entry["operation_id"]: entry["etag"] for entry in plan_files}
        if any(read_set["plans"].get(operation_id) != etag for operation_id, etag in plan_etags.items()):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(snapshot)}
        return root, snapshot, project, timeline_path, timeline, expected, plan_files

    def _apply_timeline_edit(self, context, command):
        root, snapshot, project, timeline_path, timeline, expected, plan_files = context
        try:
            updated_timeline = self._apply_timeline_command(timeline, command)
        except (KeyError, TypeError, ValueError) as exc:
            return {"ok": False, "error": f"invalid timeline edit: {exc}"}
        if updated_timeline == timeline:
            return {"ok": True, "result": "no_change", "snapshot": self._public_snapshot(snapshot)}
        ripple = self._timeline_ripple(timeline, updated_timeline, command)
        updated_timeline = self._sync_audio_timeline(timeline, updated_timeline, command, ripple)
        timeline_errors = projectlib.validate_timeline(updated_timeline)
        if timeline_errors:
            return {"ok": False, "error": "invalid timeline edit: " + "; ".join(timeline_errors)}

        updated_project = copy.deepcopy(project)
        active_sequence = updated_project.get("active_sequence")
        active_operation_ids = set(
            updated_project.get("sequences", {}).get(active_sequence, {}).get("operations", [])
        )
        cut = next(item for item in updated_project["operations"] if item.get("id") == "cut")
        cut["revision"] += 1
        cut["status"] = "approved"

        audio_only = command.get("type") in {
            "detach-audio", "attach-audio", "unlink-audio", "link-audio", "mute-audio",
            "mute-video-audio", "trim-audio", "move-audio", "delete-audio", "insert-audio",
            "set-audio-state", "set-audio-state-with-clip", "set-audio-clip",
        }
        affected_operation_ids = {"cut"}
        changed = True
        while changed:
            changed = False
            for operation in updated_project.get("operations", []):
                if not isinstance(operation, dict) or operation.get("id") in affected_operation_ids:
                    continue
                dependencies = set(operation.get("depends_on", [])) | set(operation.get("based_on", {}))
                if dependencies.intersection(affected_operation_ids):
                    affected_operation_ids.add(operation.get("id"))
                    changed = True

        plan_writes = []
        changed_operation_ids = set()
        plan_by_id = {entry["operation_id"]: entry for entry in plan_files}
        if not audio_only:
            for operation_id in affected_operation_ids - {"cut"}:
                entry = plan_by_id.get(operation_id)
                if not entry:
                    continue
                try:
                    remapped = self._remap_operation_plan(
                        operation_id, entry["plan"], timeline, updated_timeline
                    )
                except ValueError as exc:
                    return {"ok": False, "error": f"timeline edit cannot remap {operation_id}: {exc}"}
                if remapped != entry["plan"]:
                    entry["updated"] = remapped
                    changed_operation_ids.add(operation_id)

        operations = {
            item.get("id"): item for item in updated_project.get("operations", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for operation_id in changed_operation_ids:
            operation = operations[operation_id]
            operation["revision"] = int(operation.get("revision", 0)) + 1

        # Rebind in dependency order. Repeating is intentional because Protocol V1 graphs are small.
        for _ in range(len(operations) + 1):
            dependency_changed = False
            for operation_id in affected_operation_ids - {"cut"}:
                operation = operations.get(operation_id)
                if not operation:
                    continue
                based_on = operation.get("based_on")
                if not isinstance(based_on, dict):
                    continue
                for dependency in list(based_on):
                    revision = operations.get(dependency, {}).get("revision")
                    if dependency in affected_operation_ids and based_on.get(dependency) != revision:
                        based_on[dependency] = revision
                        dependency_changed = True
            if not dependency_changed:
                break

        timeline_bytes = self._json_bytes(updated_timeline)
        timeline_sha256 = self._hash(timeline_bytes)
        for operation_id, entry in plan_by_id.items():
            plan = copy.deepcopy(entry.get("updated", entry["plan"]))
            operation = operations.get(operation_id)
            if not operation or operation_id not in affected_operation_ids:
                continue
            self._rebind_operation_plan(plan, operation, updated_timeline, timeline_sha256)
            if operation_id == "graphic-motion":
                operation["render"] = [
                    copy.deepcopy(cue["render"])
                    for cue in plan.get("cues", [])
                    if isinstance(cue, dict) and cue.get("status") == "verified"
                    and isinstance(cue.get("render"), dict)
                ]
            elif not audio_only and ripple and operation_id in active_operation_ids and "render" in operation:
                operation["render"] = self._remap_render_timing(
                    operation["render"], timeline, updated_timeline
                )
            if "plan_sha256" in operation:
                operation["plan_sha256"] = self._canonical_hash(plan)
            data = self._json_bytes(plan)
            if data != self._json_bytes(entry["plan"]):
                plan_writes.append((entry["path"], data, entry["etag"]))

        revision_by_id = {
            operation_id: operation.get("revision") for operation_id, operation in operations.items()
        }
        for review in updated_project.get("reviews", []):
            based_on = review.get("based_on")
            if not isinstance(review, dict) or not isinstance(based_on, dict):
                continue
            for dependency in list(based_on):
                if dependency in affected_operation_ids and dependency in revision_by_id:
                    based_on[dependency] = revision_by_id[dependency]
            dependencies = set(review.get("depends_on", [])) | set(based_on)
            if dependencies.intersection(affected_operation_ids):
                review["editor_rebase"] = {
                    "kind": "deterministic-timeline-remap",
                    "cut_revision": cut["revision"],
                    "command_sha256": self._canonical_hash(command),
                }
        revision = updated_project.get("revision")
        if isinstance(revision, int) and not isinstance(revision, bool):
            updated_project["revision"] = revision + 1
        updated_project.setdefault("render", {})["status"] = "draft"

        plan_etags = {
            operation_id: self._hash(data)
            for operation_id, entry in plan_by_id.items()
            for path, data, _old_hash in plan_writes
            if path == entry["path"]
        }
        rebased_snapshot = snapshot_binding(
            updated_project,
            [
                timeline_sha256 if item.get("kind") == "timeline"
                else plan_etags.get(item.get("operation_id"), item["etag"])
                for item in snapshot["resources"] if item.get("kind") != "project"
            ],
        )
        for review in updated_project.get("reviews", []):
            dependencies = set(review.get("depends_on", [])) | set(review.get("based_on", {}))
            if dependencies.intersection(affected_operation_ids):
                review["snapshot_etag"] = rebased_snapshot
        return self._commit_timeline(root, timeline_path, updated_timeline, updated_project, expected, plan_writes)

    @classmethod
    def _apply_timeline_command(cls, timeline, command):
        if not isinstance(command, dict) or not isinstance(command.get("type"), str):
            raise ValueError("command must be an object with a type")
        updated = copy.deepcopy(timeline)
        clips = updated.get("clips")
        if not isinstance(clips, list) or (not clips and command.get("type") not in {"insert", "insert-with-audio"}):
            raise ValueError("timeline clips are unavailable")
        command_type = command["type"]
        allowed = {
            "split": {"type", "clip_id", "at_s"},
            "delete": {"type", "clip_id"},
            "trim": {"type", "clip_id", "edge", "source_s"},
            "restore-bounds": {"type", "clip_id"},
            "set-range": {"type", "clip_id", "start_s", "end_s"},
            "join": {"type", "left_clip_id", "right_clip_id"},
            "insert": {"type", "index", "clip"},
            "insert-with-audio": {"type", "index", "clip", "audio_clip"},
            "detach-audio": {"type", "clip_id"},
            "attach-audio": {"type", "clip_id"},
            "unlink-audio": {"type", "audio_clip_id"},
            "link-audio": {"type", "audio_clip_id"},
            "mute-audio": {"type", "audio_clip_id", "muted"},
            "mute-video-audio": {"type", "clip_id", "muted"},
            "trim-audio": {"type", "audio_clip_id", "edge", "source_s"},
            "move-audio": {"type", "audio_clip_id", "start_s"},
            "delete-audio": {"type", "audio_clip_id"},
            "insert-audio": {"type", "index", "clip"},
            "set-audio-state": {"type", "clip_id", "audio_mode"},
            "set-audio-state-with-clip": {"type", "clip_id", "audio_mode", "audio_clip"},
            "set-audio-clip": {"type", "clip"},
        }
        if command_type == "set-audio-state" and "audio_clip" in command:
            command_type = "set-audio-state-with-clip"
        if command_type not in allowed or set(command) != allowed[command_type]:
            raise ValueError("command fields do not match its type")
        fps = updated.get("fps", {})
        frame_duration = float(fps.get("den")) / float(fps.get("num"))
        source_duration = float(updated["source_duration_s"])

        if command_type in {
            "detach-audio", "attach-audio", "unlink-audio", "link-audio", "mute-audio",
            "mute-video-audio", "trim-audio", "move-audio", "delete-audio", "insert-audio",
            "set-audio-state", "set-audio-state-with-clip", "set-audio-clip",
        }:
            return cls._apply_audio_command(updated, command, command_type, frame_duration, source_duration)
        if command_type == "split":
            index = cls._clip_index(clips, command["clip_id"])
            clip = clips[index]
            at_s = cls._finite_number(command["at_s"], "at_s")
            at_s = cls._rounded(int(at_s / frame_duration + 0.5) * frame_duration)
            start = float(clip["program_range"]["start_s"])
            end = float(clip["program_range"]["end_s"])
            if at_s < start + frame_duration - 1e-7 or at_s > end - frame_duration + 1e-7:
                raise ValueError("split point must be inside the clip")
            speed = float(clip["speed"])
            source_split = cls._rounded(float(clip["source_range"]["start_s"]) + (at_s - start) * speed)
            right_id = cls._split_clip_id(clips, clip["id"], at_s, frame_duration)
            left = copy.deepcopy(clip)
            right = copy.deepcopy(clip)
            left["source_range"]["end_s"] = source_split
            right["id"] = right_id
            right["source_range"]["start_s"] = source_split
            clips[index:index + 1] = [left, right]
        elif command_type == "delete":
            clips.pop(cls._clip_index(clips, command["clip_id"]))
        elif command_type == "trim":
            index = cls._clip_index(clips, command["clip_id"])
            edge = command["edge"]
            if edge not in {"start", "end"}:
                raise ValueError("trim edge must be start or end")
            clip = clips[index]
            source_s = cls._finite_number(command["source_s"], "source_s")
            speed = float(clip["speed"])
            minimum_duration = frame_duration * speed
            if edge == "start":
                minimum = float(clips[index - 1]["source_range"]["end_s"]) if index else 0.0
                maximum = float(clip["source_range"]["end_s"]) - minimum_duration
            else:
                minimum = float(clip["source_range"]["start_s"]) + minimum_duration
                maximum = float(clips[index + 1]["source_range"]["start_s"]) if index + 1 < len(clips) else source_duration
            if source_s < minimum - 1e-7 or source_s > maximum + 1e-7:
                raise ValueError("trim would overlap another source range")
            clip["source_range"][f"{edge}_s"] = cls._rounded(source_s)
        elif command_type in {"restore-bounds", "set-range"}:
            index = cls._clip_index(clips, command["clip_id"])
            clip = clips[index]
            minimum = float(clips[index - 1]["source_range"]["end_s"]) if index else 0.0
            maximum = float(clips[index + 1]["source_range"]["start_s"]) if index + 1 < len(clips) else source_duration
            if command_type == "restore-bounds":
                start_s, end_s = minimum, maximum
            else:
                start_s = cls._finite_number(command["start_s"], "start_s")
                end_s = cls._finite_number(command["end_s"], "end_s")
            speed = float(clip["speed"])
            if (start_s < minimum - 1e-7 or end_s > maximum + 1e-7
                    or end_s - start_s < frame_duration * speed - 1e-7):
                raise ValueError("range would overlap another source range")
            clip["source_range"] = {"start_s": cls._rounded(start_s), "end_s": cls._rounded(end_s)}
        elif command_type == "join":
            index = cls._clip_index(clips, command["left_clip_id"])
            if index + 1 >= len(clips) or clips[index + 1].get("id") != command["right_clip_id"]:
                raise ValueError("join clips must be adjacent")
            left, right = clips[index], clips[index + 1]
            if (abs(float(left["source_range"]["end_s"]) - float(right["source_range"]["start_s"])) > 1e-7
                    or abs(float(left["speed"]) - float(right["speed"])) > 1e-7):
                raise ValueError("only matching split clips can be joined")
            left["source_range"]["end_s"] = right["source_range"]["end_s"]
            clips.pop(index + 1)
        else:
            index = command["index"]
            candidate = command["clip"]
            if (not isinstance(index, int) or isinstance(index, bool) or index < 0 or index > len(clips)
                    or not isinstance(candidate, dict)
                    or set(candidate) - {"id", "source_range", "speed", "decision_ref", "source_asset_id", "audio_mode"}
                    or set(candidate) < {"id", "source_range", "speed"}):
                raise ValueError("insert command is invalid")
            if not isinstance(candidate.get("id"), str) or not candidate["id"].strip():
                raise ValueError("insert clip id must be nonblank")
            if any(clip.get("id") == candidate["id"] for clip in clips):
                raise ValueError("insert clip id already exists")
            source_range = candidate.get("source_range")
            if not isinstance(source_range, dict) or set(source_range) != {"start_s", "end_s"}:
                raise ValueError("insert source_range is invalid")
            start = cls._finite_number(source_range["start_s"], "start_s")
            end = cls._finite_number(source_range["end_s"], "end_s")
            speed = cls._finite_number(candidate["speed"], "speed")
            if start < 0 or end <= start or end > source_duration + frame_duration or speed <= 0:
                raise ValueError("insert clip range is invalid")
            if candidate.get("audio_mode", "embedded") not in {"embedded", "detached", "muted"}:
                raise ValueError("insert clip audio_mode is invalid")
            clips.insert(index, copy.deepcopy(candidate))

        reflowed = cls._reflow_timeline(updated)
        if command_type == "insert-with-audio":
            restored_audio = cls._audio_payload(command["audio_clip"])
            source = next(clip for clip in reflowed["clips"] if clip.get("id") == candidate["id"])
            restored_audio.update({
                "source_range": copy.deepcopy(source["source_range"]),
                "program_range": copy.deepcopy(source["program_range"]),
                "speed": source.get("speed", 1.0),
                "source_video_clip_id": source["id"],
                "linked": True,
            })
            reflowed.setdefault("audio_clips", []).append(restored_audio)
        return reflowed

    @classmethod
    def _apply_audio_command(cls, timeline, command, command_type, frame_duration, source_duration):
        clips = timeline["clips"]
        audio_clips = timeline.setdefault("audio_clips", [])
        if not isinstance(audio_clips, list):
            raise ValueError("timeline audio_clips are unavailable")

        def video(clip_id):
            index = cls._clip_index(clips, clip_id)
            return clips[index]

        def audio_index(clip_id):
            return cls._clip_index(audio_clips, clip_id)

        audio_payload = cls._audio_payload

        if command_type == "detach-audio":
            source = video(command["clip_id"])
            if source.get("audio_mode", "embedded") == "detached":
                raise ValueError("audio is already detached")
            source["audio_mode"] = "detached"
            audio_clips.append({
                "id": f"{source['id']}:audio",
                "source_range": copy.deepcopy(source["source_range"]),
                "program_range": copy.deepcopy(source["program_range"]),
                "speed": source.get("speed", 1.0),
                "source_video_clip_id": source["id"],
                "linked": True,
                "muted": False,
                **({"source_asset_id": source["source_asset_id"]} if source.get("source_asset_id") else {}),
            })
        elif command_type == "attach-audio":
            source = video(command["clip_id"])
            matches = [item for item in audio_clips if item.get("source_video_clip_id") == source["id"]]
            if source.get("audio_mode") != "detached" or len(matches) != 1 or not matches[0].get("linked"):
                raise ValueError("only linked detached audio can be attached")
            audio_clips.remove(matches[0])
            source["audio_mode"] = "embedded"
        elif command_type == "mute-video-audio":
            source = video(command["clip_id"])
            if source.get("audio_mode") == "detached" or not isinstance(command["muted"], bool):
                raise ValueError("embedded video audio mute is invalid")
            source["audio_mode"] = "muted" if command["muted"] else "embedded"
        elif command_type in {"unlink-audio", "link-audio", "mute-audio"}:
            item = audio_clips[audio_index(command["audio_clip_id"])]
            if command_type == "unlink-audio":
                if not item.get("linked"):
                    raise ValueError("audio is already unlinked")
                item["linked"] = False
            elif command_type == "link-audio":
                source = video(item.get("source_video_clip_id"))
                item.update({
                    "linked": True,
                    "source_range": copy.deepcopy(source["source_range"]),
                    "program_range": copy.deepcopy(source["program_range"]),
                    "speed": source.get("speed", 1.0),
                })
            else:
                if not isinstance(command["muted"], bool):
                    raise ValueError("muted must be boolean")
                item["muted"] = command["muted"]
        elif command_type == "move-audio":
            index = audio_index(command["audio_clip_id"])
            item = audio_clips[index]
            if item.get("linked"):
                raise ValueError("unlink audio before moving it")
            start = cls._rounded(int(cls._finite_number(command["start_s"], "start_s") / frame_duration + 0.5) * frame_duration)
            duration = float(item["program_range"]["end_s"]) - float(item["program_range"]["start_s"])
            item["program_range"] = {"start_s": start, "end_s": cls._rounded(start + duration)}
        elif command_type == "trim-audio":
            item = audio_clips[audio_index(command["audio_clip_id"])]
            if item.get("linked") or command["edge"] not in {"start", "end"}:
                raise ValueError("unlink audio before trimming it")
            source_s = cls._finite_number(command["source_s"], "source_s")
            speed = float(item.get("speed", 1.0))
            source_range = item["source_range"]
            source_range[f"{command['edge']}_s"] = cls._rounded(source_s)
            if (float(source_range["start_s"]) < 0 or float(source_range["end_s"]) > source_duration
                    or float(source_range["end_s"]) - float(source_range["start_s"]) < frame_duration * speed - 1e-7):
                raise ValueError("audio trim is outside source media")
            duration = (float(source_range["end_s"]) - float(source_range["start_s"])) / speed
            if command["edge"] == "start":
                item["program_range"]["start_s"] = cls._rounded(float(item["program_range"]["end_s"]) - duration)
            else:
                item["program_range"]["end_s"] = cls._rounded(float(item["program_range"]["start_s"]) + duration)
        elif command_type == "delete-audio":
            index = audio_index(command["audio_clip_id"])
            item = audio_clips[index]
            if item.get("linked"):
                raise ValueError("unlink audio before deleting it")
            duration = float(item["program_range"]["end_s"]) - float(item["program_range"]["start_s"])
            boundary = float(item["program_range"]["end_s"])
            audio_clips.pop(index)
            for candidate in audio_clips:
                if not candidate.get("linked") and float(candidate["program_range"]["start_s"]) >= boundary - 1e-7:
                    candidate["program_range"] = {
                        "start_s": cls._rounded(float(candidate["program_range"]["start_s"]) - duration),
                        "end_s": cls._rounded(float(candidate["program_range"]["end_s"]) - duration),
                    }
        elif command_type == "insert-audio":
            index = command["index"]
            item = audio_payload(command["clip"])
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index <= len(audio_clips):
                raise ValueError("audio insert index is invalid")
            if any(candidate.get("id") == item["id"] for candidate in audio_clips):
                raise ValueError("audio clip already exists")
            duration = float(item["program_range"]["end_s"]) - float(item["program_range"]["start_s"])
            boundary = float(item["program_range"]["start_s"])
            for candidate in audio_clips:
                if not candidate.get("linked") and float(candidate["program_range"]["start_s"]) >= boundary - 1e-7:
                    candidate["program_range"] = {
                        "start_s": cls._rounded(float(candidate["program_range"]["start_s"]) + duration),
                        "end_s": cls._rounded(float(candidate["program_range"]["end_s"]) + duration),
                    }
            audio_clips.insert(index, item)
        elif command_type in {"set-audio-state", "set-audio-state-with-clip"}:
            source = video(command["clip_id"])
            mode = command["audio_mode"]
            if mode not in {"embedded", "detached", "muted"}:
                raise ValueError("audio_mode is invalid")
            audio_clips[:] = [item for item in audio_clips if item.get("source_video_clip_id") != source["id"]]
            source["audio_mode"] = mode
            if command_type == "set-audio-state-with-clip":
                audio_clips.append(audio_payload(command["audio_clip"]))
        else:
            item = audio_payload(command["clip"])
            index = audio_index(item["id"])
            audio_clips[index] = item

        return timeline

    @classmethod
    def _sync_audio_timeline(cls, before, after, command, ripple):
        if command.get("type") not in {
            "split", "delete", "trim", "restore-bounds", "set-range", "join", "insert", "insert-with-audio",
        }:
            return after
        previous_videos = before.get("clips", [])
        next_videos = after.get("clips", [])
        output = []
        for audio in before.get("audio_clips", []):
            if not isinstance(audio, dict):
                continue
            if not audio.get("linked"):
                item = copy.deepcopy(audio)
                if ripple and float(item["program_range"]["start_s"]) >= ripple[0] - 1e-7:
                    item["program_range"] = {
                        "start_s": cls._rounded(float(item["program_range"]["start_s"]) + ripple[1]),
                        "end_s": cls._rounded(float(item["program_range"]["end_s"]) + ripple[1]),
                    }
                output.append(item)
                continue
            previous = next((item for item in previous_videos if item.get("id") == audio.get("source_video_clip_id")), None)
            if not previous:
                continue
            candidates = [item for item in next_videos
                          if float(item["source_range"]["start_s"]) >= float(previous["source_range"]["start_s"]) - 1e-7
                          and float(item["source_range"]["end_s"]) <= float(previous["source_range"]["end_s"]) + 1e-7]
            for candidate in candidates:
                output.append({
                    **{key: copy.deepcopy(value) for key, value in audio.items()
                       if key not in {"id", "source_range", "program_range", "speed", "source_video_clip_id"}},
                    "id": audio["id"] if candidate.get("id") == previous.get("id") else f"{candidate['id']}:audio",
                    "source_range": copy.deepcopy(candidate["source_range"]),
                    "program_range": copy.deepcopy(candidate["program_range"]),
                    "speed": candidate.get("speed", 1.0),
                    "source_video_clip_id": candidate["id"],
                })
        if command.get("type") == "insert-with-audio":
            restored_id = command.get("audio_clip", {}).get("id")
            restored = next((item for item in after.get("audio_clips", []) if item.get("id") == restored_id), None)
            if restored and not any(item.get("id") == restored_id for item in output):
                output.append(copy.deepcopy(restored))
        after["audio_clips"] = output
        return after

    @classmethod
    def _timeline_ripple(cls, before, after, command):
        """Return (old program boundary, duration delta) for downstream ripple edits."""
        if command.get("type") in {"split", "join"}:
            return None
        before_clips = before.get("clips", [])
        after_clips = after.get("clips", [])
        if command.get("type") == "delete":
            clip = next((item for item in before_clips if item.get("id") == command.get("clip_id")), None)
            if not clip:
                return None
            boundary = float(clip["program_range"]["end_s"])
            duration = (float(clip["source_range"]["end_s"]) - float(clip["source_range"]["start_s"])) / float(clip["speed"])
            return cls._ripple_or_none(boundary, -duration)
        if command.get("type") in {"insert", "insert-with-audio"}:
            index = command.get("index")
            boundary = (float(before_clips[index]["program_range"]["start_s"])
                        if index < len(before_clips) else float(before.get("program_duration_s", 0)))
            clip = next((item for item in after_clips if item.get("id") == command.get("clip", {}).get("id")), None)
            if not clip:
                return None
            duration = float(clip["program_range"]["end_s"]) - float(clip["program_range"]["start_s"])
            return cls._ripple_or_none(boundary, duration)
        if command.get("type") in {"trim", "restore-bounds", "set-range"}:
            before_clip = next((item for item in before_clips if item.get("id") == command.get("clip_id")), None)
            after_clip = next((item for item in after_clips if item.get("id") == command.get("clip_id")), None)
            if not before_clip or not after_clip:
                return None
            old_duration = float(before_clip["program_range"]["end_s"]) - float(before_clip["program_range"]["start_s"])
            new_duration = float(after_clip["program_range"]["end_s"]) - float(after_clip["program_range"]["start_s"])
            delta = new_duration - old_duration
            start_changed = abs(
                float(before_clip["source_range"]["start_s"])
                - float(after_clip["source_range"]["start_s"])
            ) > 1e-7
            boundary = (float(before_clip["program_range"]["start_s"]) + max(0.0, -delta)
                        if start_changed
                        else float(before_clip["program_range"]["end_s"]))
            return cls._ripple_or_none(boundary, delta)
        return None

    @staticmethod
    def _ripple_or_none(boundary, delta):
        if not (float("-inf") < boundary < float("inf") and float("-inf") < delta < float("inf")):
            return None
        if abs(delta) <= 1e-7:
            return None
        return round(boundary, 9), round(delta, 9)

    @classmethod
    def _shift_operation_plan(cls, operation_id, plan, boundary, delta):
        shifted = copy.deepcopy(plan)
        if not isinstance(shifted, dict):
            return shifted
        if operation_id == "content-cards":
            for card in shifted.get("cards", []):
                cls._shift_program_start(card, boundary, delta)
        elif operation_id == "captions":
            for cue in shifted.get("cues", []):
                if not cls._shift_program_range(cue, boundary, delta):
                    cls._shift_start_end(cue, boundary, delta)
        elif operation_id == "graphic-motion":
            for cue in shifted.get("cues", []):
                cls._shift_program_range(cue, boundary, delta)
        elif operation_id == "b-roll":
            for shot in shifted.get("shots", []):
                if cls._shift_program_range(shot, boundary, delta):
                    for segment in shot.get("segments", []):
                        cls._shift_program_range(segment, boundary, delta)
        return shifted

    @classmethod
    def _remap_operation_plan(cls, operation_id, plan, before, after):
        remapped = copy.deepcopy(plan)
        if not isinstance(remapped, dict):
            raise ValueError("plan must be an object")
        if operation_id == "captions":
            remapped = cls._remap_caption_plan(remapped, before, after)
        else:
            collection = {
                "content-cards": "cards",
                "graphic-motion": "cues",
                "b-roll": "shots",
            }.get(operation_id)
            if collection and isinstance(remapped.get(collection), list):
                tombstones = remapped.get("editor_tombstones", {}).get(collection, [])
                candidates = [*remapped[collection], *(
                    tombstones if isinstance(tombstones, list) else []
                )]
                items = []
                next_tombstones = []
                seen = set()
                for item in candidates:
                    if not isinstance(item, dict):
                        items.append(item)
                        continue
                    item_id = item.get("id")
                    if isinstance(item_id, str) and item_id in seen:
                        continue
                    if isinstance(item_id, str):
                        seen.add(item_id)
                    updated = cls._remap_timed_item(item, before, after)
                    if updated is None:
                        next_tombstones.append(copy.deepcopy(item))
                        continue
                    if operation_id == "b-roll" and isinstance(updated.get("segments"), list):
                        updated["segments"] = [
                            segment
                            for value in updated["segments"]
                            if isinstance(value, dict)
                            for segment in [cls._remap_timed_item(value, before, after)]
                            if segment is not None
                        ]
                    updated = cls._remap_nested_timing(updated, before, after)
                    updated.pop("_editor_clip_id", None)
                    items.append(updated)
                remapped[collection] = items
                cls._set_plan_tombstones(remapped, collection, next_tombstones)
        if "program_duration_s" in remapped:
            remapped["program_duration_s"] = after.get("program_duration_s")
        return remapped

    @classmethod
    def _remap_caption_plan(cls, plan, before, after):
        cues = plan.get("cues")
        if not isinstance(cues, list):
            return plan
        tombstones = plan.get("editor_tombstones", {}).get("captions", [])
        candidates = [*cues, *(tombstones if isinstance(tombstones, list) else [])]
        remapped_cues = []
        next_tombstones = []
        cue_ids = {}
        seen = set()
        for cue in candidates:
            if not isinstance(cue, dict):
                continue
            original_id = cue.get("id")
            if isinstance(original_id, str) and original_id in seen:
                continue
            if isinstance(original_id, str):
                seen.add(original_id)
            words = cue.get("words")
            if not isinstance(words, list) or not words:
                updated = cls._remap_timed_item(cue, before, after, allow_partial=True)
                if updated is not None:
                    updated.pop("_editor_clip_id", None)
                    remapped_cues.append(updated)
                    if isinstance(cue.get("id"), str):
                        cue_ids[cue["id"]] = [cue["id"]]
                else:
                    next_tombstones.append(copy.deepcopy(cue))
                continue

            surviving = []
            removed_words = cue.get("editor_removed_words", [])
            word_candidates = [*words, *(removed_words if isinstance(removed_words, list) else [])]
            word_candidates.sort(key=lambda word: (
                cls._numeric_range(word.get("source_range"))[0]
                if isinstance(word, dict) and cls._numeric_range(word.get("source_range")) else float("inf")
            ))
            next_removed_words = []
            for word in word_candidates:
                if not isinstance(word, dict):
                    continue
                updated = cls._remap_timed_item(word, before, after)
                if updated is not None:
                    surviving.append(updated)
                else:
                    next_removed_words.append(copy.deepcopy(word))
            if not surviving:
                if isinstance(cue.get("id"), str):
                    cue_ids[cue["id"]] = []
                restored = copy.deepcopy(cue)
                restored["words"] = word_candidates
                restored.pop("editor_removed_words", None)
                next_tombstones.append(restored)
                continue

            groups = []
            for word in surviving:
                clip_id = word.pop("_editor_clip_id", None)
                word["clip_id"] = clip_id
                if not groups or groups[-1][0] != clip_id:
                    groups.append((clip_id, [word]))
                else:
                    groups[-1][1].append(word)
            generated_ids = []
            for group_position, (_clip_id, group) in enumerate(groups, 1):
                updated = copy.deepcopy(cue)
                updated["words"] = group
                if isinstance(original_id, str) and original_id.strip():
                    generated_id = original_id if group_position == 1 else f"{original_id}:part-{group_position}"
                    updated["id"] = generated_id
                    generated_ids.append(generated_id)
                start = float(group[0]["program_range"]["start_s"])
                end = float(group[-1]["program_range"]["end_s"])
                updated["start"] = cls._rounded(start)
                updated["end"] = cls._rounded(end)
                updated["program_range"] = {"start_s": cls._rounded(start), "end_s": cls._rounded(end)}
                updated["source_ranges"] = [{
                    "start_s": group[0]["source_range"]["start_s"],
                    "end_s": group[-1]["source_range"]["end_s"],
                }]
                if len(group) != len(words) or len(groups) > 1:
                    text = " ".join(str(word.get("word", "")).strip() for word in group).strip()
                    updated["text"] = text
                    updated["lines"] = [text]
                if next_removed_words:
                    updated["editor_removed_words"] = copy.deepcopy(next_removed_words)
                else:
                    updated.pop("editor_removed_words", None)
                remapped_cues.append(updated)
            if isinstance(cue.get("id"), str):
                cue_ids[cue["id"]] = generated_ids

        for index, cue in enumerate(remapped_cues, 1):
            if "index" in cue:
                cue["index"] = index
        plan["cues"] = remapped_cues
        cls._set_plan_tombstones(plan, "captions", next_tombstones)
        presentation = plan.get("presentation")
        if isinstance(presentation, dict) and isinstance(presentation.get("layout_beats"), list):
            beats = presentation["layout_beats"]
            evidence = plan.get("review", {}).get("evidence")
            next_beats = []
            kept_positions = []
            cue_by_id = {
                cue.get("id"): cue for cue in remapped_cues
                if isinstance(cue, dict) and isinstance(cue.get("id"), str)
            }
            for beat_position, beat in enumerate(beats):
                if not isinstance(beat, dict) or not isinstance(beat.get("cue_ids"), list):
                    continue
                ids = [mapped for cue_id in beat["cue_ids"] for mapped in cue_ids.get(cue_id, [])]
                if not ids:
                    continue
                updated = copy.deepcopy(beat)
                updated["cue_ids"] = ids
                updated["program_range"] = {
                    "start_s": cue_by_id[ids[0]]["program_range"]["start_s"],
                    "end_s": cue_by_id[ids[-1]]["program_range"]["end_s"],
                }
                next_beats.append(updated)
                kept_positions.append(beat_position)
            presentation["layout_beats"] = next_beats
            if isinstance(evidence, list) and len(evidence) == len(beats) + 1:
                plan["review"]["evidence"] = [evidence[0], *[evidence[index + 1] for index in kept_positions]]
        if "program_duration_s" in plan:
            plan["program_duration_s"] = after.get("program_duration_s")
        return plan

    @staticmethod
    def _set_plan_tombstones(plan, collection, values):
        tombstones = plan.get("editor_tombstones")
        if values:
            if not isinstance(tombstones, dict):
                tombstones = {}
                plan["editor_tombstones"] = tombstones
            tombstones[collection] = values
        elif isinstance(tombstones, dict):
            tombstones.pop(collection, None)
            if not tombstones:
                plan.pop("editor_tombstones", None)

    @classmethod
    def _remap_nested_timing(cls, value, before, after):
        if isinstance(value, list):
            return [cls._remap_nested_timing(item, before, after) for item in value]
        if not isinstance(value, dict):
            return value
        output = copy.deepcopy(value)
        for key, child in list(output.items()):
            if key in {
                "program_range", "program_start_s", "duration_s", "start", "end",
                "source_range", "source_ranges", "render",
            }:
                continue
            if isinstance(child, (dict, list)):
                if isinstance(child, dict) and cls._timing_range(child) is not None:
                    mapped = cls._remap_timed_item(child, before, after, allow_partial=True)
                    if isinstance(mapped, dict):
                        mapped.pop("_editor_clip_id", None)
                    output[key] = mapped if mapped is not None else child
                else:
                    output[key] = cls._remap_nested_timing(child, before, after)
        if isinstance(output.get("render"), dict):
            render = copy.deepcopy(output["render"])
            timing = cls._timing_range(output)
            if timing and isinstance(render.get("start_s"), (int, float)):
                render["start_s"] = timing[0]
                if isinstance(render.get("duration_s"), (int, float)):
                    render["duration_s"] = cls._rounded(timing[1] - timing[0])
            output["render"] = render
        return output

    @classmethod
    def _remap_timed_item(cls, value, before, after, allow_partial=False):
        if not isinstance(value, dict):
            return None
        source_ranges = cls._source_ranges_for_item(value, before)
        if not source_ranges:
            raise ValueError("timed item has no deterministic source mapping")
        mapped = cls._map_source_ranges(source_ranges, after)
        if not mapped:
            return None
        expected_duration = sum(end - start for start, end in source_ranges)
        retained_duration = sum(
            segment["source_range"]["end_s"] - segment["source_range"]["start_s"]
            for segment in mapped
        )
        if retained_duration < expected_duration - 1e-7 and not allow_partial:
            return None
        output = copy.deepcopy(value)
        start = mapped[0]["program_range"]["start_s"]
        end = mapped[-1]["program_range"]["end_s"]
        if isinstance(output.get("program_range"), dict):
            output["program_range"] = {"start_s": start, "end_s": end}
        if isinstance(output.get("program_start_s"), (int, float)):
            output["program_start_s"] = start
        if isinstance(output.get("start_s"), (int, float)):
            output["start_s"] = start
        if isinstance(output.get("duration_s"), (int, float)):
            output["duration_s"] = cls._rounded(end - start)
        if isinstance(output.get("start"), (int, float)):
            output["start"] = start
        if isinstance(output.get("end"), (int, float)):
            output["end"] = end
        if isinstance(output.get("source_range"), dict):
            if len(mapped) != 1 and not allow_partial:
                return None
            output["source_range"] = {
                "start_s": mapped[0]["source_range"]["start_s"],
                "end_s": mapped[-1]["source_range"]["end_s"],
            }
        if isinstance(output.get("source_ranges"), list):
            include_clip = any(
                isinstance(item, dict) and "clip_id" in item for item in output["source_ranges"]
            )
            output["source_ranges"] = [
                {
                    **({"clip_id": segment["clip_id"]} if include_clip else {}),
                    **segment["source_range"],
                }
                for segment in mapped
            ]
        output["_editor_clip_id"] = mapped[0]["clip_id"] if len(mapped) == 1 else None
        if isinstance(output.get("render"), dict):
            output["render"] = {
                **output["render"],
                "start_s": start,
                "duration_s": cls._rounded(end - start),
            }
        return output

    @classmethod
    def _source_ranges_for_item(cls, value, timeline):
        declared = value.get("source_ranges")
        if isinstance(declared, list) and declared:
            ranges = [cls._numeric_range(item) for item in declared]
            if all(item is not None for item in ranges):
                return ranges
        declared = cls._numeric_range(value.get("source_range"))
        if declared is not None:
            return [declared]
        timing = cls._timing_range(value)
        return cls._program_to_source_ranges(timeline, *timing) if timing else []

    @classmethod
    def _program_to_source_ranges(cls, timeline, start, end):
        ranges = []
        for clip in timeline.get("clips", []):
            program = cls._numeric_range(clip.get("program_range"))
            source = cls._numeric_range(clip.get("source_range"))
            if not program or not source:
                continue
            intersection_start = max(start, program[0])
            intersection_end = min(end, program[1])
            if intersection_end <= intersection_start + 1e-7:
                continue
            speed = float(clip.get("speed", 1.0))
            ranges.append((
                cls._rounded(source[0] + (intersection_start - program[0]) * speed),
                cls._rounded(source[0] + (intersection_end - program[0]) * speed),
            ))
        return ranges

    @classmethod
    def _map_source_ranges(cls, source_ranges, timeline):
        mapped = []
        for start, end in source_ranges:
            for clip in timeline.get("clips", []):
                source = cls._numeric_range(clip.get("source_range"))
                program = cls._numeric_range(clip.get("program_range"))
                if not source or not program:
                    continue
                intersection_start = max(start, source[0])
                intersection_end = min(end, source[1])
                if intersection_end <= intersection_start + 1e-7:
                    continue
                speed = float(clip.get("speed", 1.0))
                mapped.append({
                    "clip_id": clip.get("id"),
                    "source_range": {
                        "start_s": cls._rounded(intersection_start),
                        "end_s": cls._rounded(intersection_end),
                    },
                    "program_range": {
                        "start_s": cls._rounded(program[0] + (intersection_start - source[0]) / speed),
                        "end_s": cls._rounded(program[0] + (intersection_end - source[0]) / speed),
                    },
                })
        return sorted(mapped, key=lambda item: item["program_range"]["start_s"])

    @staticmethod
    def _numeric_range(value):
        if not isinstance(value, dict):
            return None
        start, end = value.get("start_s"), value.get("end_s")
        if (isinstance(start, bool) or not isinstance(start, (int, float))
                or isinstance(end, bool) or not isinstance(end, (int, float))
                or float(end) <= float(start)):
            return None
        return float(start), float(end)

    @classmethod
    def _timing_range(cls, value):
        program = cls._numeric_range(value.get("program_range"))
        if program:
            return program
        start, end = value.get("start"), value.get("end")
        if (isinstance(start, (int, float)) and not isinstance(start, bool)
                and isinstance(end, (int, float)) and not isinstance(end, bool)
                and end > start):
            return float(start), float(end)
        start, duration = value.get("program_start_s"), value.get("duration_s")
        if (isinstance(start, (int, float)) and not isinstance(start, bool)
                and isinstance(duration, (int, float)) and not isinstance(duration, bool)
                and duration > 0):
            return float(start), float(start + duration)
        start, duration = value.get("start_s"), value.get("duration_s")
        if (isinstance(start, (int, float)) and not isinstance(start, bool)
                and isinstance(duration, (int, float)) and not isinstance(duration, bool)
                and duration > 0):
            return float(start), float(start + duration)
        return None

    @classmethod
    def _remap_render_timing(cls, value, before, after):
        if isinstance(value, list):
            output = []
            for item in value:
                remapped = cls._remap_render_timing(item, before, after)
                if remapped is not None:
                    output.append(remapped)
            return output
        if not isinstance(value, dict):
            return value
        if cls._timing_range(value):
            remapped = cls._remap_timed_item(value, before, after, allow_partial=True)
            if remapped is None:
                return None
            remapped.pop("_editor_clip_id", None)
            return remapped
        return {key: cls._remap_render_timing(child, before, after) for key, child in value.items()}

    @classmethod
    def _rebind_operation_plan(cls, plan, operation, timeline, timeline_sha256):
        if not isinstance(plan, dict):
            return
        if "program_duration_s" in plan:
            plan["program_duration_s"] = timeline.get("program_duration_s")
        if isinstance(plan.get("based_on"), dict) and isinstance(operation.get("based_on"), dict):
            for dependency in list(plan["based_on"]):
                if dependency in operation["based_on"]:
                    plan["based_on"][dependency] = operation["based_on"][dependency]
        hashes = plan.get("input_hashes")
        if isinstance(hashes, dict) and "timeline_sha256" in hashes:
            hashes["timeline_sha256"] = timeline_sha256
        if operation.get("id") == "graphic-motion":
            bindings = list(graphic_motion_plan._input_bindings(plan))
            for cue in plan.get("cues", []):
                if isinstance(cue, dict) and cue.get("status") == "verified":
                    bindings.extend(graphic_motion_plan._cue_bindings(cue))
            plan["delivery_bindings"] = bindings
        bindings = plan.get("delivery_bindings")
        if isinstance(bindings, list):
            for binding in bindings:
                if isinstance(binding, dict) and binding.get("path") == "work/timeline.json":
                    binding["sha256"] = timeline_sha256
            operation["delivery_bindings"] = copy.deepcopy(bindings)

    @staticmethod
    def _canonical_hash(value):
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _shift_program_range(value, boundary, delta):
        if not isinstance(value, dict):
            return False
        program_range = value.get("program_range")
        if (not isinstance(program_range, dict)
                or not isinstance(program_range.get("start_s"), (int, float))
                or isinstance(program_range.get("start_s"), bool)
                or not isinstance(program_range.get("end_s"), (int, float))
                or isinstance(program_range.get("end_s"), bool)
                or float(program_range["start_s"]) < boundary - 1e-7):
            return False
        value["program_range"] = {
            **program_range,
            "start_s": round(float(program_range["start_s"]) + delta, 9),
            "end_s": round(float(program_range["end_s"]) + delta, 9),
        }
        return True

    @staticmethod
    def _shift_program_start(value, boundary, delta):
        if (isinstance(value, dict)
                and isinstance(value.get("program_start_s"), (int, float))
                and not isinstance(value.get("program_start_s"), bool)
                and isinstance(value.get("duration_s"), (int, float))
                and not isinstance(value.get("duration_s"), bool)
                and float(value["program_start_s"]) >= boundary - 1e-7):
            value["program_start_s"] = round(float(value["program_start_s"]) + delta, 9)
            return True
        return False

    @staticmethod
    def _shift_start_end(value, boundary, delta):
        if (isinstance(value, dict)
                and isinstance(value.get("start"), (int, float))
                and not isinstance(value.get("start"), bool)
                and isinstance(value.get("end"), (int, float))
                and not isinstance(value.get("end"), bool)
                and float(value["start"]) >= boundary - 1e-7):
            value["start"] = round(float(value["start"]) + delta, 9)
            value["end"] = round(float(value["end"]) + delta, 9)
            return True
        return False

    @classmethod
    def _shift_render_timing(cls, value, boundary, delta):
        if isinstance(value, list):
            return [cls._shift_render_timing(item, boundary, delta) for item in value]
        if not isinstance(value, dict):
            return value
        shifted = copy.deepcopy(value)
        if (isinstance(shifted.get("start_s"), (int, float))
                and not isinstance(shifted.get("start_s"), bool)
                and isinstance(shifted.get("duration_s"), (int, float))
                and not isinstance(shifted.get("duration_s"), bool)
                and float(shifted["start_s"]) >= boundary - 1e-7):
            shifted["start_s"] = round(float(shifted["start_s"]) + delta, 9)
        return {
            key: value if key in {"start_s", "duration_s"}
            else cls._shift_render_timing(value, boundary, delta)
            for key, value in shifted.items()
        }

    @staticmethod
    def _clip_index(clips, clip_id):
        if not isinstance(clip_id, str) or not clip_id.strip():
            raise ValueError("clip id must be nonblank")
        index = next((index for index, clip in enumerate(clips) if clip.get("id") == clip_id), None)
        if index is None:
            raise ValueError("clip does not exist")
        return index

    @staticmethod
    def _audio_payload(value):
        if not isinstance(value, dict):
            raise ValueError("audio clip must be an object")
        required = {"id", "source_range", "program_range", "speed", "source_video_clip_id", "linked", "muted"}
        if set(value) - (required | {"source_asset_id"}) or not required.issubset(value):
            raise ValueError("audio clip fields are invalid")
        return copy.deepcopy(value)

    @staticmethod
    def _finite_number(value, name):
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric") from exc
        if not (float("-inf") < number < float("inf")):
            raise ValueError(f"{name} must be finite")
        return number

    @staticmethod
    def _rounded(value):
        return round(float(value), 9)

    @classmethod
    def _reflow_timeline(cls, timeline):
        program_start = 0.0
        for clip in timeline["clips"]:
            speed = float(clip["speed"])
            duration = (float(clip["source_range"]["end_s"]) - float(clip["source_range"]["start_s"])) / speed
            program_end = cls._rounded(program_start + duration)
            clip["program_range"] = {"start_s": cls._rounded(program_start), "end_s": program_end}
            program_start = program_end
        timeline["program_duration_s"] = cls._rounded(program_start)
        return timeline

    @staticmethod
    def _split_clip_id(clips, clip_id, at_s, frame_duration):
        frame = round(at_s / frame_duration)
        base = f"{clip_id}:split-{frame}"
        ids = {clip.get("id") for clip in clips}
        candidate = base
        suffix = 2
        while candidate in ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

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
        if not -2 <= x <= 3 or not -2 <= y <= 3:
            raise ValueError("editor_transform position is out of range")
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

    def _commit_timeline(self, root, timeline_path, timeline, project, expected, plan_writes=()):
        project_path = root / "work" / "project.json"
        validation_errors = projectlib.validate_project(
            project, root, check_files=True, dependency_mode="require_current"
        )
        if validation_errors:
            return {"ok": False, "error": "invalid committed project: " + "; ".join(validation_errors)}
        self._before_final_cas()
        current = build_snapshot(root)
        current_project = next(item for item in current["resources"] if item["kind"] == "project")["etag"]
        current_timeline = next(item for item in current["resources"] if item["kind"] == "timeline")["etag"]
        current_operation = next(item for item in current["view"]["operations"] if item["id"] == "cut")["etag"]
        if (current_project, current_operation, current_timeline) != (
                expected["project"], expected["operation"], expected["timeline"]):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
        if any(self._hash(path.read_bytes()) != old_hash for path, _data, old_hash in plan_writes):
            return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}

        writes = [
            (timeline_path, self._json_bytes(timeline)),
            *[(path, data) for path, data, _old_hash in plan_writes],
            (project_path, self._json_bytes(project)),
        ]
        journal_dir = projectlib.editor_state_dir(root, create=True)
        journal_path = journal_dir / "transaction.json"
        if journal_path.exists():
            raise PreparedTransactionError("pending transaction journal exists")
        intent = {
            "schema_version": 1,
            "transaction_id": str(uuid.uuid4()),
            "operation": "cut",
            "verb": "timeline.edit",
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
                handle = tempfile.NamedTemporaryFile(
                    dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
                )
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
            current_timeline = next(item for item in current["resources"] if item["kind"] == "timeline")["etag"]
            current_operation = next(item for item in current["view"]["operations"] if item["id"] == "cut")["etag"]
            if (current_project, current_operation, current_timeline) != (
                    expected["project"], expected["operation"], expected["timeline"]):
                journal_path.unlink()
                return {"ok": False, "status": 409, "error": "conflict", "snapshot": self._public_snapshot(current)}
            if any(self._hash(path.read_bytes()) != old_hash for path, _data, old_hash in plan_writes):
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
            raise PreparedTransactionError("timeline transaction failed after prepare") from exc
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
                    or operation_id not in {"cut", "content-cards", "captions", "graphic-motion"}
                    or intent.get("verb") not in {"timeline.edit", "plan.update", "review.record"}
                    or intent.get("state") not in {"prepared", "committed"}
                    or not isinstance(transaction_id, str) or str(uuid.UUID(transaction_id)) != transaction_id
                    or not isinstance(files, list) or not files):
                raise ValueError
            project_path = root / "work" / "project.json"
            current_project = json.loads(project_path.read_text(encoding="utf-8"))
            operation = next((item for item in current_project.get("operations", []) if item.get("id") == operation_id), None)
            if not operation or (intent["verb"] != "timeline.edit" and not isinstance(operation.get("plan"), str)):
                raise ValueError
            required_targets = {project_path.resolve()}
            allowed = set(required_targets)
            if intent["verb"] == "timeline.edit":
                active = current_project.get("active_sequence")
                sequence = current_project.get("sequences", {}).get(active, {})
                timeline_value = sequence.get("timeline")
                if not isinstance(timeline_value, str) or not timeline_value.strip():
                    raise ValueError
                timeline_path = projectlib.resolve_project_path(root, timeline_value).resolve()
                required_targets.add(timeline_path)
                allowed.add(timeline_path)
                active_operation_ids = set(sequence.get("operations", []))
                for candidate in current_project.get("operations", []):
                    if (isinstance(candidate, dict) and candidate.get("id") in active_operation_ids
                            and candidate.get("id") != "cut" and isinstance(candidate.get("plan"), str)):
                        allowed.add(projectlib.resolve_project_path(root, candidate["plan"]).resolve())
            elif intent["verb"] == "plan.update":
                plan_path = projectlib.resolve_project_path(root, operation["plan"])
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
            if self._validate_recovered(root, targets, operation_id, intent["verb"]):
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

    def _validate_recovered(self, root, targets, operation_id="content-cards", verb="plan.update"):
        proposed = {path: item["new_content"] for path, item in targets}
        project_path = root / "work" / "project.json"
        try:
            project = json.loads(proposed.get(project_path, project_path.read_text(encoding="utf-8")))
            errors = projectlib.validate_project(project, root, check_files=False, dependency_mode="allow_stale")
            if verb == "timeline.edit":
                active = project.get("active_sequence")
                timeline_value = project.get("sequences", {}).get(active, {}).get("timeline")
                timeline_path = projectlib.resolve_project_path(root, timeline_value).resolve()
                timeline = json.loads(proposed.get(timeline_path, timeline_path.read_text(encoding="utf-8")))
                active_ids = set(project.get("sequences", {}).get(active, {}).get("operations", []))
                for candidate in project.get("operations", []):
                    if (not isinstance(candidate, dict) or candidate.get("id") not in active_ids
                            or candidate.get("id") == "cut" or not isinstance(candidate.get("plan"), str)):
                        continue
                    plan_path = projectlib.resolve_project_path(root, candidate["plan"]).resolve()
                    if plan_path not in proposed:
                        continue
                    plan = json.loads(proposed[plan_path])
                    if candidate.get("id") == "content-cards":
                        self._validate_cards_plan(plan)
                    elif candidate.get("id") == "captions":
                        self._validate_caption_plan(plan)
                    elif candidate.get("id") == "graphic-motion":
                        self._validate_graphic_motion_plan(root, project, plan)
                return [*errors, *projectlib.validate_timeline(timeline)]
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
