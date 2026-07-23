"""Validate B-roll plans and record review decisions."""

import copy
import hashlib
import json
import math
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib


RANGE_EPSILON = 1e-6
KEN_BURNS_DIRECTIONS = {"zoom-in", "pan-left", "pan-right"}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _is_uuid(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        uuid.UUID(value)
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _positive_duration(value):
    if isinstance(value, bool):
        return None
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None


def _valid_source_trim(value, candidate):
    trim = _range(value)
    if not isinstance(value, dict) or not trim or trim[0] < 0 or trim[1] <= trim[0]:
        return False
    durations = [_positive_duration(candidate.get("duration_s"))]
    probe = candidate.get("probe")
    if isinstance(probe, dict):
        durations.append(_positive_duration(probe.get("duration_s")))
    return all(duration is None or trim[1] <= duration for duration in durations)


def _valid_ken_burns(value):
    return isinstance(value, dict) and isinstance(value.get("direction"), str) and value["direction"] in KEN_BURNS_DIRECTIONS


def candidate_manifest(plan):
    return [{"id": shot.get("id"), "candidates": sorted(copy.deepcopy(shot.get("candidates", [])), key=lambda item: str(item.get("id")))} for shot in sorted(plan.get("shots", []), key=lambda item: str(item.get("id")))]


def review_subject(plan):
    value = copy.deepcopy(plan)
    receipt = value.get("review")
    receipt_ids = receipt.get("decision_skipped_shot_ids", []) if isinstance(receipt, dict) and receipt.get("status") == "approved" else []
    decision_skipped_ids = set(receipt_ids) if isinstance(receipt_ids, list) and all(isinstance(shot_id, str) for shot_id in receipt_ids) else set()

    def clean(item):
        if isinstance(item, dict):
            for key in ("decision", "review", "review_status", "selected", "normalized", "verification"):
                item.pop(key, None)
            for child in item.values():
                clean(child)
        elif isinstance(item, list):
            for child in item:
                clean(child)

    clean(value)
    for shot in value.get("shots", []):
        status = shot.get("status") if isinstance(shot, dict) else None
        if isinstance(status, str) and status in ("planned", "candidates_ready", "selected", "normalized", "verified"):
            shot["status"] = "reviewable"
        elif status == "skipped" and isinstance(shot.get("id"), str) and shot["id"] in decision_skipped_ids:
            shot["status"] = "reviewable"
    return value


def _decision_manifest(shots):
    if not isinstance(shots, list):
        return None
    decisions = []
    for shot in shots:
        if not isinstance(shot, dict):
            return None
        shot_id, status = shot.get("id"), shot.get("status")
        if not isinstance(shot_id, str) or not shot_id.strip() or not isinstance(status, str):
            return None
        if status == "skipped":
            decisions.append({"id": shot_id, "decision": "skip"})
            continue
        if status not in ("selected", "normalized", "verified"):
            return None
        selected, candidates = shot.get("selected"), shot.get("candidates")
        if not isinstance(selected, dict) or not isinstance(candidates, list):
            return None
        selected_id = selected.get("candidate_id")
        if not isinstance(selected_id, str) or not selected_id.strip():
            return None
        candidate = None
        for item in candidates:
            if not isinstance(item, dict):
                continue
            candidate_id = item.get("id")
            if isinstance(candidate_id, str) and candidate_id.strip() and candidate_id == selected_id:
                candidate = item
                break
        if candidate is None:
            return None
        media_type = candidate.get("media_type")
        if media_type == "video":
            option, value = "source_trim", selected.get("source_trim")
            if not _valid_source_trim(value, candidate):
                return None
        elif media_type == "image":
            option, value = "ken_burns", selected.get("ken_burns")
            if not _valid_ken_burns(value):
                return None
        else:
            return None
        decisions.append({"id": shot_id, "decision": "select", "candidate_id": selected_id, option: copy.deepcopy(value)})
    return decisions


def _valid_timestamp(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _review_errors(plan, shots):
    review, decision = plan.get("review"), plan.get("decision")
    trust_required = "review_status" in plan or (isinstance(review, dict) and review.get("status") == "approved") or any(
        isinstance(shot, dict) and isinstance(shot.get("status"), str) and shot.get("status") in ("selected", "normalized", "verified")
        for shot in shots
    )
    if not trust_required:
        return []
    errors = []
    if plan.get("review_status") != "approved": errors.append("review_status must be approved")
    if not isinstance(decision, dict): errors.append("review trust requires decision object")
    if not isinstance(review, dict): errors.append("review trust requires review object")
    if not isinstance(decision, dict) or not isinstance(review, dict): return errors
    if review.get("status") != "approved": errors.append("review status must be approved")
    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip(): errors.append("review_id is required")
    elif not _is_uuid(review["review_id"]): errors.append("review_id must be a UUID")
    mode, actor, rationale = decision.get("mode"), decision.get("actor"), decision.get("rationale")
    if mode not in ("human", "agent"): errors.append("review mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip(): errors.append("review actor is required")
    if not isinstance(rationale, str) or not rationale.strip(): errors.append("review rationale is required")
    if any(review.get(key) != decision.get(key) for key in ("mode", "actor", "rationale")):
        errors.append("decision and review authority do not match")
    if not _valid_timestamp(review.get("timestamp")): errors.append("review timestamp is invalid")
    if mode == "human" and (decision.get("explicit_user_action") is not True or review.get("explicit_user_action") is not True):
        errors.append("human review requires explicit_user_action true")
    decisions = _decision_manifest(shots)
    if decisions is None:
        errors.append("review decision manifest cannot be reconstructed")
    elif review.get("decisions") != decisions:
        errors.append("review decisions do not match current plan")
    decision_skipped_ids = review.get("decision_skipped_shot_ids")
    shot_statuses = {shot["id"]: shot.get("status") for shot in shots if isinstance(shot, dict) and isinstance(shot.get("id"), str)}
    if not isinstance(decision_skipped_ids, list) or any(not isinstance(shot_id, str) for shot_id in decision_skipped_ids) or decision_skipped_ids != sorted(set(decision_skipped_ids)) or any(shot_statuses.get(shot_id) != "skipped" for shot_id in decision_skipped_ids):
        errors.append("decision_skipped_shot_ids must be sorted unique current skipped shot ids")
    if review.get("plan_sha256") != canonical_sha256(review_subject(plan)):
        errors.append("review plan SHA-256 does not match")
    candidates_valid = all(
        isinstance(shot, dict)
        and isinstance(shot.get("candidates", []), list)
        and all(isinstance(candidate, dict) for candidate in shot.get("candidates", []))
        for shot in shots
    )
    if candidates_valid and review.get("candidate_manifest_sha256") != canonical_sha256(candidate_manifest(plan)):
        errors.append("review candidate manifest SHA-256 does not match")
    selected_hashes = []
    for shot in shots:
        if not isinstance(shot, dict) or not isinstance(shot.get("status"), str) or shot.get("status") not in ("selected", "normalized", "verified") or not isinstance(shot.get("selected"), dict): continue
        candidates = shot.get("candidates")
        if not isinstance(candidates, list): continue
        candidate = next((item for item in candidates if isinstance(item, dict) and item.get("id") == shot["selected"].get("candidate_id")), None)
        if isinstance(candidate, dict) and isinstance(candidate.get("sha256"), str): selected_hashes.append(candidate["sha256"])
    if review.get("selected_asset_sha256") != sorted(set(selected_hashes)):
        errors.append("review selected asset hashes do not match")
    input_hashes = plan.get("input_hashes")
    if not isinstance(input_hashes, dict):
        errors.append("plan input_hashes must be an object")
        input_hashes = {}
    if review.get("review_video_sha256") != input_hashes.get("review_video_sha256"):
        errors.append("review video SHA-256 does not match")
    return errors


def _range(value):
    if not isinstance(value, dict):
        return None
    try:
        start_value, end_value = value["start_s"], value["end_s"]
        if any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in (start_value, end_value)):
            return None
        start, end = float(start_value), float(end_value)
    except (KeyError, OverflowError, TypeError, ValueError):
        return None
    return (start, end) if math.isfinite(start) and math.isfinite(end) else None


def _timeline_source_ranges(program, timeline):
    clips = timeline.get("clips") if isinstance(timeline, dict) else None
    if not program or not isinstance(clips, list):
        return None
    result = []
    for clip in clips:
        if not isinstance(clip, dict):
            return None
        clip_id = clip.get("id")
        source = _range(clip.get("source_range"))
        clip_program = _range(clip.get("program_range"))
        try:
            speed = float(clip.get("speed"))
        except (TypeError, ValueError):
            return None
        if (not isinstance(clip_id, str) or not clip_id.strip() or not source or source[1] <= source[0]
                or not clip_program or clip_program[1] <= clip_program[0]
                or not math.isfinite(speed) or speed <= 0):
            return None
        start = max(program[0], clip_program[0])
        end = min(program[1], clip_program[1])
        if start >= end:
            continue
        result.append({
            "clip_id": clip_id,
            "start_s": source[0] + (start - clip_program[0]) * speed,
            "end_s": source[0] + (end - clip_program[0]) * speed,
        })
    return result


def _source_ranges_match(declared, expected):
    if not isinstance(declared, list) or expected is None or len(declared) != len(expected):
        return False
    for actual, required in zip(declared, expected):
        source = _range(actual) if isinstance(actual, dict) else None
        if (not source or actual.get("clip_id") != required["clip_id"]
                or abs(source[0] - required["start_s"]) > RANGE_EPSILON
                or abs(source[1] - required["end_s"]) > RANGE_EPSILON):
            return False
    return True


def _mapped_words(transcript, timeline):
    try:
        mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
        return set()
    result = set()
    segments = mapped.get("segments", []) if isinstance(mapped, dict) else []
    if not isinstance(segments, list):
        return result
    for segment in segments:
        words = segment.get("words", []) if isinstance(segment, dict) else []
        if not isinstance(words, list):
            continue
        for word in words:
            if not isinstance(word, dict):
                continue
            source, program = _range(word.get("source_range")), _range(word.get("program_range"))
            text, clip_id = word.get("word"), word.get("clip_id")
            if isinstance(text, str) and isinstance(clip_id, str) and source and program:
                result.add((text, source, program, clip_id))
    return result


def _candidate_errors(shot_id, candidate):
    errors = []
    if not isinstance(candidate, dict):
        return [f"{shot_id} candidate must be an object"]
    candidate_id = candidate.get("id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        errors.append(f"{shot_id} candidate id is required")
    elif candidate_id == "skip":
        errors.append(f"{shot_id} candidate id 'skip' is reserved")
    if candidate.get("media_type") not in ("video", "image"):
        errors.append(f"{shot_id} candidate {candidate_id} media_type is invalid")
    if not isinstance(candidate.get("cache_path"), str) or not candidate["cache_path"].strip():
        errors.append(f"{shot_id} candidate {candidate_id} cache_path is required")
    if not isinstance(candidate.get("sha256"), str) or len(candidate["sha256"]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in candidate["sha256"]):
        errors.append(f"{shot_id} candidate {candidate_id} SHA-256 is required")
    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source_type") not in ("local", "pexels", "external-generated"):
        errors.append(f"{shot_id} candidate {candidate_id} provenance is invalid")
    elif (not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("creator", "license", "retrieval_time")) or not any(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("source_url", "original_path"))):
        errors.append(f"{shot_id} candidate {candidate_id} provenance is incomplete")
    return errors


def _candidate_path(root, value):
    if not isinstance(value, str):
        return None
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    candidate = (root / raw if raw.parts and raw.parts[0] == "work" else root / "work" / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _project_parts(project):
    if not isinstance(project, dict):
        raise ValueError("project must be an object")
    active = project.get("active_sequence")
    sequences, operations = project.get("sequences"), project.get("operations")
    if not isinstance(active, str) or not active.strip() or not isinstance(sequences, dict):
        raise ValueError("project active sequence is invalid")
    sequence = sequences.get(active)
    if not isinstance(sequence, dict) or not isinstance(sequence.get("operations"), list):
        raise ValueError("project active sequence operations must be a list")
    if not isinstance(operations, list) or any(not isinstance(item, dict) for item in operations):
        raise ValueError("project operations must be a list of objects")
    nodes = {}
    for item in operations:
        operation_id, revision = item.get("id"), item.get("revision")
        if not isinstance(operation_id, str) or not operation_id.strip() or operation_id in nodes:
            raise ValueError("project operation ids must be unique nonblank strings")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0:
            raise ValueError(f"project operation {operation_id} revision must be a positive integer")
        nodes[operation_id] = item
    if any(not isinstance(item, str) or not item.strip() for item in sequence["operations"]):
        raise ValueError("project active sequence operation ids must be nonblank strings")
    return sequence, nodes


def active_dependencies(project):
    """Return the current evidence and active picture-operation dependencies."""
    sequence, nodes = _project_parts(project)
    if "understanding" not in nodes:
        raise ValueError("project understanding operation is required")
    return ["understanding", *[operation_id for operation_id in ("cut", "color-grade") if operation_id in sequence["operations"] and operation_id in nodes]]


def _verified_overlays(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list):
        raise ValueError("plan shots must be a list")
    if any(not isinstance(shot, dict) for shot in plan["shots"]):
        raise ValueError("plan shots must be objects")
    shot_ids = set()
    for shot in plan["shots"]:
        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError("registered shot id is required")
        if shot_id in shot_ids:
            raise ValueError(f"duplicate registered shot id: {shot_id}")
        shot_ids.add(shot_id)
    if plan.get("review_status") != "approved":
        raise ValueError("review_status must be approved")
    errors = _review_errors(plan, plan["shots"])
    if errors:
        raise ValueError("; ".join(errors))
    selected = [shot for shot in plan["shots"] if isinstance(shot, dict) and shot.get("status") != "skipped"]
    if not selected:
        return []
    overlays = []
    for shot in selected:
        if shot.get("status") != "verified":
            raise ValueError("selected shots must be verified")
        verification = shot.get("verification")
        if not isinstance(verification, dict) or verification.get("status") != "pass":
            raise ValueError("verified shot verification must pass")
        selection = shot.get("selected")
        candidate = next((item for item in shot.get("candidates", []) if isinstance(item, dict) and isinstance(selection, dict) and item.get("id") == selection.get("candidate_id")), None)
        if candidate is None:
            raise ValueError("verified shot selected candidate is invalid")
        normalized = shot.get("normalized")
        program = _range(shot.get("program_range"))
        if not isinstance(normalized, dict) or not isinstance(normalized.get("path"), str) or not normalized["path"].strip() or _candidate_path(Path(".").resolve(), normalized["path"]) is None:
            raise ValueError("verified shot normalized path is invalid")
        digest = normalized.get("sha256")
        if not _is_sha256(digest):
            raise ValueError("verified shot normalized SHA-256 is invalid")
        if "source_path" in normalized and normalized["source_path"] != candidate.get("cache_path"):
            raise ValueError("verified shot normalized source path does not match selected candidate")
        if not program or program[1] <= program[0]:
            raise ValueError("verified shot program range is invalid")
        overlays.append({"kind": "overlay", "asset": normalized["path"], "start_s": program[0], "duration_s": program[1] - program[0]})
    if overlays != sorted(overlays, key=lambda item: item["start_s"]):
        raise ValueError("verified shots must be chronological")
    return overlays


def register_operation(project, plan, *, plan_path="b-roll/broll-plan.json", report_path="../review/03-b-roll/b-roll-summary.md"):
    """Replace the active sequence's B-roll overlay operation from verified shots."""
    result = copy.deepcopy(project)
    if not isinstance(result, dict) or not isinstance(result.get("operations"), list):
        raise ValueError("project operations must be a list of objects")
    old = [item for item in result["operations"] if item.get("id") == "b-roll"]
    removed = bool(old)
    result["operations"] = [item for item in result["operations"] if item.get("id") != "b-roll"]
    if isinstance(result.get("sequences"), dict):
        for value in result["sequences"].values():
            if not isinstance(value, dict) or not isinstance(value.get("operations"), list):
                continue
            sequence_ids = value["operations"]
            cleaned = [item for item in sequence_ids if item != "b-roll"]
            removed = removed or len(cleaned) != len(sequence_ids)
            value["operations"] = cleaned
    sequence, nodes = _project_parts(result)
    dependencies = active_dependencies(result)
    expected_based_on = {item: nodes[item]["revision"] for item in dependencies}
    if not isinstance(plan, dict) or plan.get("dependencies") != dependencies:
        raise ValueError("plan dependencies do not match current dependencies")
    if plan.get("based_on") != expected_based_on:
        raise ValueError("plan based_on does not match current revisions")
    overlays = _verified_overlays(plan)
    if not overlays:
        if removed:
            result.setdefault("render", {})["status"] = "draft"
        return result
    revision = max((item.get("revision", 0) for item in old), default=0) + 1
    operation = {
        "id": "b-roll", "skill": "video-add-b-roll", "revision": revision,
        "depends_on": dependencies, "based_on": copy.deepcopy(expected_based_on),
        "status": "verified", "plan": plan_path, "outputs": [item["asset"] for item in overlays],
        "target": {"sequence": result["active_sequence"], "scope": "b-roll"},
        "effects": {"changes_timeline": False, "changes_geometry": False, "changes_video_pixels": True, "changes_audio": False, "adds_track": "b-roll"},
        "check": {"status": "pass", "report": report_path}, "render": overlays,
    }
    result["operations"].append(operation)
    ids = sequence["operations"]
    anchors = [index for index, item in enumerate(ids) if item in {"cut", "color-grade"}]
    if anchors:
        index = anchors[-1] + 1
    else:
        index = next((index for index, item in enumerate(ids) if item in {"content-cards", "captions"}), len(ids))
    ids.insert(index, "b-roll")
    result.setdefault("render", {})["status"] = "draft"
    return result


def validate_plan(plan, timeline, transcript, project=None, project_root=None, verify_files=False):
    """Return ordinary schema and freshness errors without throwing."""
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if not isinstance(timeline, dict):
        return ["timeline must be an object"]
    if not isinstance(transcript, dict):
        return ["transcript must be an object"]
    if plan.get("schema_version") != 1: errors.append("plan schema_version must be 1")
    if plan.get("timebase") != "program": errors.append("plan timebase must be program")
    if plan.get("timeline_id") != timeline.get("timeline_id"): errors.append("plan timeline_id does not match timeline")
    try:
        timeline_duration = float(timeline.get("program_duration_s"))
        if not math.isfinite(timeline_duration) or timeline_duration < 0: raise ValueError
    except (AttributeError, TypeError, ValueError):
        errors.append("timeline program_duration_s is invalid")
        timeline_duration = None
    try:
        plan_duration = float(plan.get("program_duration_s"))
        if not math.isfinite(plan_duration): raise ValueError
        if timeline_duration is not None and plan_duration != timeline_duration: errors.append("plan program_duration_s does not match timeline")
    except (TypeError, ValueError): errors.append("plan program_duration_s is required")
    brief = plan.get("brief")
    if not isinstance(brief, dict): errors.append("brief must be an object")
    elif brief.get("density") != "selective": errors.append("brief density must be selective")
    duration = timeline_duration if timeline_duration is not None else 0
    try:
        source_duration = float(timeline.get("source_duration_s"))
        if not math.isfinite(source_duration) or source_duration < 0: raise ValueError
    except (AttributeError, TypeError, ValueError):
        errors.append("timeline source_duration_s is invalid")
        source_duration = None
    mapped = _mapped_words(transcript, timeline)
    seen_shots, ranges, candidate_ids = set(), [], set()
    previous_program_start = None
    shots = plan.get("shots", [])
    if not isinstance(shots, list): return errors + ["shots must be a list"]
    for shot in shots:
        if not isinstance(shot, dict):
            errors.append("shot must be an object")
            continue
        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip(): errors.append("shot id is required"); shot_id = "<missing>"
        elif shot_id in seen_shots: errors.append(f"duplicate shot id: {shot_id}")
        seen_shots.add(shot_id)
        program = _range(shot.get("program_range"))
        if not program or program[0] < 0 or program[1] <= program[0] or program[1] > duration:
            errors.append(f"{shot_id} program range is outside timeline")
        else:
            if previous_program_start is not None and program[0] < previous_program_start:
                errors.append("shots must be in chronological program order")
            previous_program_start = program[0]
            ranges.append((program[0], program[1], shot_id))
        source_ranges = shot.get("source_ranges", [])
        if not isinstance(source_ranges, list): errors.append(f"{shot_id} source_ranges must be a list")
        else:
            for item in source_ranges:
                source = _range(item) if isinstance(item, dict) else None
                if not source or source[0] < 0 or source[1] <= source[0] or (source_duration is not None and source[1] > source_duration): errors.append(f"{shot_id} source range is outside timeline")
        if program and not _source_ranges_match(source_ranges, _timeline_source_ranges(program, timeline)):
            errors.append(f"{shot_id} source_ranges do not match timeline")
        evidence = shot.get("transcript_evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{shot_id} transcript evidence must be an object")
            evidence = {}
        words = evidence.get("words", [])
        if not isinstance(words, list): errors.append(f"{shot_id} transcript evidence words must be a list")
        else:
            if not words:
                errors.append(f"{shot_id} transcript evidence requires at least one word")
            for word in words:
                if not isinstance(word, dict):
                    errors.append(f"{shot_id} transcript evidence word is not mapped from transcript")
                    continue
                source, mapped_program = _range(word.get("source_range")), _range(word.get("program_range"))
                text, clip_id = word.get("word"), word.get("clip_id")
                if not isinstance(text, str) or not isinstance(clip_id, str) or not source or not mapped_program or (text, source, mapped_program, clip_id) not in mapped:
                    errors.append(f"{shot_id} transcript evidence word is not mapped from transcript")
                    continue
                if (not program or mapped_program[0] < program[0] - RANGE_EPSILON
                        or mapped_program[1] > program[1] + RANGE_EPSILON):
                    errors.append(f"{shot_id} transcript evidence word is outside shot program range")
                matching_source = next(
                    (_range(item) for item in source_ranges
                     if isinstance(item, dict) and item.get("clip_id") == clip_id),
                    None,
                ) if isinstance(source_ranges, list) else None
                if (not matching_source or source[0] < matching_source[0] - RANGE_EPSILON
                        or source[1] > matching_source[1] + RANGE_EPSILON):
                    errors.append(f"{shot_id} transcript evidence source range is outside shot source_ranges")
        queries = shot.get("queries", [])
        if not isinstance(queries, list) or not 2 <= len(queries) <= 3 or any(not isinstance(query, str) or not query.strip() for query in queries): errors.append(f"{shot_id} queries must contain 2-3 nonblank strings")
        candidates = shot.get("candidates", [])
        if not isinstance(candidates, list): errors.append(f"{shot_id} candidates must be a list"); candidates = []
        local_ids = set()
        for candidate in candidates:
            errors.extend(_candidate_errors(shot_id, candidate))
            if not isinstance(candidate, dict): continue
            candidate_id = candidate.get("id") if isinstance(candidate.get("id"), str) else "<missing>"
            if candidate_id in local_ids or candidate_id in candidate_ids: errors.append(f"duplicate candidate id: {candidate_id}")
            local_ids.add(candidate_id); candidate_ids.add(candidate_id)
            if verify_files and project_root:
                path = _candidate_path(Path(project_root).resolve(), candidate.get("cache_path", ""))
                prefix = f"{shot_id} candidate {candidate_id}"
                if path is None: errors.append(f"{prefix} path escapes project root")
                elif not path.is_file(): errors.append(f"{prefix} file is missing")
                elif candidate.get("sha256") != sha256_file(path): errors.append(f"{prefix} SHA-256 is stale")
        selected, status = shot.get("selected"), shot.get("status")
        if not isinstance(status, str) or status not in ("planned", "candidates_ready", "selected", "normalized", "verified", "skipped"): errors.append(f"{shot_id} status is invalid")
        elif status in {"planned", "candidates_ready", "skipped"} and selected is not None: errors.append(f"{shot_id} {status} shot must not select a candidate")
        elif status in {"selected", "normalized", "verified"} and not isinstance(selected, dict): errors.append(f"{shot_id} {status} shot requires a selection")
        elif status in {"selected", "normalized", "verified"}:
            candidate = next((item for item in candidates if isinstance(item, dict) and item.get("id") == selected.get("candidate_id")), None)
            if candidate is None: errors.append(f"{shot_id} selected candidate does not belong to shot")
            elif candidate.get("media_type") == "video":
                if not _valid_source_trim(selected.get("source_trim"), candidate): errors.append(f"{shot_id} {status} video requires a valid source_trim")
            elif candidate.get("media_type") == "image" and not _valid_ken_burns(selected.get("ken_burns")):
                errors.append(f"{shot_id} {status} image requires a non-empty ken_burns")
                errors.append(f"{shot_id} {status} image requires a valid ken_burns direction")
        if status in ("normalized", "verified"):
            normalized = shot.get("normalized")
            if not isinstance(normalized, dict):
                errors.append(f"{shot_id} normalized record is required")
            else:
                if not isinstance(normalized.get("path"), str) or not normalized["path"].strip():
                    errors.append(f"{shot_id} normalized path is invalid")
                if not _is_sha256(normalized.get("sha256")):
                    errors.append(f"{shot_id} normalized SHA-256 is invalid")
        if status == "verified":
            verification = shot.get("verification")
            if not isinstance(verification, dict) or verification.get("status") != "pass":
                errors.append(f"{shot_id} verified verification must pass")
    for start, end, shot_id in sorted(ranges):
        for previous_start, previous_end, previous_id in ranges:
            if previous_id != shot_id and previous_start < end and start < previous_end:
                errors.append(f"{shot_id} program range overlaps {previous_id}"); break
    errors.extend(_review_errors(plan, shots))
    if project is not None:
        if not isinstance(project, dict): return errors + ["project must be an object"]
        operation_values = project.get("operations")
        if not isinstance(operation_values, list): return errors + ["project operations must be a list"]
        if any(not isinstance(item, dict) for item in operation_values):
            return errors + ["project operations must be a list of objects"]
        sequences = project.get("sequences", {})
        if not isinstance(sequences, dict): return errors + ["project sequences must be an object"]
        active = project.get("active_sequence")
        if not isinstance(active, str) or not active.strip() or not isinstance(sequences.get(active), dict):
            return errors + ["project active sequence must be an object"]
        operation_ids = [item.get("id") for item in operation_values]
        if any(not isinstance(item, str) or not item.strip() for item in operation_ids) or len(operation_ids) != len(set(operation_ids)):
            return errors + ["project operation ids must be unique nonblank strings"]
        operations = dict(zip(operation_ids, operation_values))
        for operation_id, operation in operations.items():
            revision = operation.get("revision")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0:
                errors.append(f"project operation {operation_id} revision must be a positive integer")
        dependencies, based_on = plan.get("dependencies", []), plan.get("based_on", {})
        if not isinstance(dependencies, list): errors.append("dependencies must be a list"); dependencies = []
        elif any(not isinstance(item, str) or not item.strip() for item in dependencies): errors.append("dependencies must contain nonblank strings"); dependencies = [item for item in dependencies if isinstance(item, str) and item.strip()]
        if not isinstance(based_on, dict): errors.append("based_on must be an object"); based_on = {}
        sequence = sequences.get(active, {})
        active_ids = sequence.get("operations")
        if not isinstance(active_ids, list):
            return errors + ["project active sequence operations must be a list"]
        if any(not isinstance(item, str) or not item.strip() for item in active_ids):
            return errors + ["project active sequence operation ids must be nonblank strings"]
        required = (["understanding"] if "understanding" in operations else ["understand"] if "understand" in operations and "understand" in dependencies else [])
        required += [operation_id for operation_id in ("cut", "color-grade") if operation_id in active_ids and operation_id in operations]
        if set(dependencies) != set(required): errors.append("plan dependencies do not match current dependencies")
        if set(dependencies) != set(based_on): errors.append("based_on does not match dependencies")
        for dependency in dependencies:
            expected = based_on.get(dependency)
            if not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0:
                errors.append(f"based_on {dependency} revision must be a positive integer")
            current = operations.get(dependency, {}).get("revision")
            if current != expected: errors.append(f"based_on {dependency} revision is stale: expected {expected}, current {current}")
    if verify_files and not project_root: errors.append("verify_files requires project_root")
    if project_root:
        hashes = plan.get("input_hashes", {})
        for key, path in (("transcript_sha256", Path(project_root) / "work/understand/transcript.json"), ("timeline_sha256", Path(project_root) / "work/timeline.json")):
            if not path.is_file(): errors.append(f"{key.split('_')[0]} file is missing")
            elif not isinstance(hashes, dict) or hashes.get(key) != sha256_file(path): errors.append(f"{key.split('_')[0]} SHA-256 is stale")
    return errors


def apply_review(plan, review, *, mode, actor, rationale, interaction_path=None):
    if not isinstance(plan, dict): raise ValueError("plan must be an object")
    if not isinstance(review, dict): raise ValueError("review must be an object")
    plan_shots, entries = plan.get("shots"), review.get("shots")
    if not isinstance(plan_shots, list): raise ValueError("plan shots must be a list")
    if not isinstance(entries, list): raise ValueError("review shots must be a list")
    plan_ids = set()
    for shot in plan_shots:
        if not isinstance(shot, dict): raise ValueError("plan shot must be an object")
        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip(): raise ValueError("plan shot id is required")
        if shot_id in plan_ids: raise ValueError(f"duplicate plan shot id: {shot_id}")
        plan_ids.add(shot_id)
        candidates = shot.get("candidates", [])
        if not isinstance(candidates, list): raise ValueError(f"{shot.get('id', '<missing>')} candidates must be a list")
        for candidate in candidates:
            candidate_errors = _candidate_errors(shot.get("id", "<missing>"), candidate)
            if candidate_errors: raise ValueError("; ".join(candidate_errors))
    for entry in entries:
        if not isinstance(entry, dict): raise ValueError("review shot must be an object")
    if mode not in ("human", "agent"): raise ValueError("mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip(): raise ValueError("actor is required")
    if not isinstance(rationale, str) or not rationale.strip(): raise ValueError("rationale is required")
    rationale = rationale.strip()
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip() or review["rationale"].strip() != rationale:
        raise ValueError("exported rationale does not match review rationale")
    if not _valid_timestamp(review.get("timestamp")):
        raise ValueError("review timestamp is invalid")
    if mode == "human" and review.get("explicit_user_action") is not True: raise ValueError("human review requires explicit_user_action true")
    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip(): raise ValueError("review_id is required")
    if not _is_uuid(review["review_id"]): raise ValueError("review_id must be a UUID")
    input_hashes = plan.get("input_hashes")
    if not isinstance(input_hashes, dict):
        raise ValueError("plan input_hashes must be an object")
    expected_bindings = {
        "plan_sha256": canonical_sha256(review_subject(plan)),
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": input_hashes.get("review_video_sha256"),
    }
    if not isinstance(expected_bindings["review_video_sha256"], str) or len(expected_bindings["review_video_sha256"]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_bindings["review_video_sha256"]):
        raise ValueError("plan review_video_sha256 is invalid")
    for field, expected in expected_bindings.items():
        if review.get(field) != expected:
            raise ValueError(f"{field} does not match current review artifacts")
    result, shots = copy.deepcopy(plan), {shot.get("id"): shot for shot in plan_shots}
    seen = set()
    for entry in entries:
        shot_id = entry.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip(): raise ValueError("review shot id is required")
        if shot_id in seen: raise ValueError(f"duplicate review shot id: {shot_id}")
        seen.add(shot_id)
        if shot_id not in shots: raise ValueError(f"review has unknown shots: {shot_id}")
    missing = sorted(set(shots) - seen)
    if missing: raise ValueError("review is missing shots: " + ", ".join(missing))
    entries_by_id = {entry["id"]: entry for entry in entries}
    selected_hashes = []
    decision_skipped_ids = []
    for shot in result["shots"]:
        entry, decision = entries_by_id[shot["id"]], entries_by_id[shot["id"]].get("decision")
        if decision not in ("select", "skip"): raise ValueError(f"{shot['id']} decision must be select or skip")
        if decision == "skip":
            if shot.get("status") != "skipped": decision_skipped_ids.append(shot["id"])
            shot["selected"], shot["status"] = None, "skipped"
            continue
        candidate = next((item for item in shot.get("candidates", []) if item.get("id") == entry.get("candidate_id")), None)
        if not candidate: raise ValueError(f"{shot['id']} selected candidate does not belong to shot")
        option = "source_trim" if candidate.get("media_type") == "video" else "ken_burns"
        if option == "source_trim" and not _valid_source_trim(entry.get(option), candidate):
            raise ValueError(f"{shot['id']} select requires a valid source_trim")
        if option == "ken_burns" and not _valid_ken_burns(entry.get(option)):
            raise ValueError(f"{shot['id']} select requires a valid ken_burns direction")
        shot["selected"], shot["status"] = {"candidate_id": candidate["id"], option: copy.deepcopy(entry[option])}, "selected"; selected_hashes.append(candidate["sha256"])
    decisions = _decision_manifest(result["shots"])
    if decisions is None:
        raise ValueError("review decision manifest cannot be reconstructed")
    result["review_status"] = "approved"
    result["decision"] = {"mode": mode, "actor": actor, "rationale": rationale}
    if mode == "human": result["decision"]["explicit_user_action"] = True
    result["review"] = {"status": "approved", "review_id": review["review_id"], "mode": mode, "actor": actor, "rationale": rationale, "timestamp": review["timestamp"], **expected_bindings, "decisions": decisions, "decision_skipped_shot_ids": sorted(set(decision_skipped_ids)), "selected_asset_sha256": sorted(set(selected_hashes))}
    if mode == "human": result["review"]["explicit_user_action"] = True
    if interaction_path:
        target = Path(interaction_path); target.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, dir=target.parent, suffix=".json", encoding="utf-8") as handle: temp = Path(handle.name)
            projectlib.write_json(temp, result["review"]); os.replace(temp, target)
        finally:
            if temp is not None: temp.unlink(missing_ok=True)
    return result
