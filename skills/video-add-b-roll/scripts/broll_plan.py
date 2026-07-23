"""Validate B-roll plans and record review decisions."""

import copy
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def candidate_manifest(plan):
    return [{"id": shot.get("id"), "candidates": sorted(copy.deepcopy(shot.get("candidates", [])), key=lambda item: str(item.get("id")))} for shot in sorted(plan.get("shots", []), key=lambda item: str(item.get("id")))]


def review_subject(plan):
    value = copy.deepcopy(plan)

    def clean(item):
        if isinstance(item, dict):
            for key in ("review", "normalized", "verification"):
                item.pop(key, None)
            for child in item.values():
                clean(child)
        elif isinstance(item, list):
            for child in item:
                clean(child)

    clean(value)
    return value


def _range(value):
    if not isinstance(value, dict):
        return None
    try:
        start, end = float(value["start_s"]), float(value["end_s"])
    except (KeyError, TypeError, ValueError):
        return None
    return (start, end) if math.isfinite(start) and math.isfinite(end) else None


def _mapped_words(transcript, timeline):
    try:
        mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    except (KeyError, TypeError, ValueError):
        return set()
    result = set()
    for segment in mapped.get("segments", []):
        for word in segment.get("words", []):
            source, program = _range(word.get("source_range")), _range(word.get("program_range"))
            if source and program:
                result.add((word.get("word"), source, program))
    return result


def _candidate_errors(shot_id, candidate):
    errors = []
    if not isinstance(candidate, dict):
        return [f"{shot_id} candidate must be an object"]
    candidate_id = candidate.get("id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        errors.append(f"{shot_id} candidate id is required")
    if candidate.get("media_type") not in {"video", "image"}:
        errors.append(f"{shot_id} candidate {candidate_id} media_type is invalid")
    if not isinstance(candidate.get("cache_path"), str) or not candidate["cache_path"].strip():
        errors.append(f"{shot_id} candidate {candidate_id} cache_path is required")
    if not isinstance(candidate.get("sha256"), str) or len(candidate["sha256"]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in candidate["sha256"]):
        errors.append(f"{shot_id} candidate {candidate_id} SHA-256 is required")
    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source_type") not in {"local", "pexels", "external-generated"}:
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
        else: ranges.append((program[0], program[1], shot_id))
        source_ranges = shot.get("source_ranges", [])
        if not isinstance(source_ranges, list): errors.append(f"{shot_id} source_ranges must be a list")
        else:
            for item in source_ranges:
                source = _range(item) if isinstance(item, dict) else None
                if not source or source[0] < 0 or source[1] <= source[0] or (source_duration is not None and source[1] > source_duration): errors.append(f"{shot_id} source range is outside timeline")
        evidence = shot.get("transcript_evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{shot_id} transcript evidence must be an object")
            evidence = {}
        words = evidence.get("words", [])
        if not isinstance(words, list): errors.append(f"{shot_id} transcript evidence words must be a list")
        else:
            for word in words:
                if not isinstance(word, dict):
                    errors.append(f"{shot_id} transcript evidence word is not mapped from transcript")
                    continue
                source, mapped_program = _range(word.get("source_range")), _range(word.get("program_range"))
                if not source or not mapped_program or (word.get("word"), source, mapped_program) not in mapped:
                    errors.append(f"{shot_id} transcript evidence word is not mapped from transcript")
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
        if status not in {"planned", "candidates_ready", "selected", "normalized", "verified", "skipped"}: errors.append(f"{shot_id} status is invalid")
        elif status in {"planned", "candidates_ready", "skipped"} and selected is not None: errors.append(f"{shot_id} {status} shot must not select a candidate")
        elif status in {"selected", "normalized", "verified"} and not isinstance(selected, dict): errors.append(f"{shot_id} {status} shot requires a selection")
        elif status in {"selected", "normalized", "verified"}:
            candidate = next((item for item in candidates if isinstance(item, dict) and item.get("id") == selected.get("candidate_id")), None)
            if candidate is None: errors.append(f"{shot_id} selected candidate does not belong to shot")
            elif candidate.get("media_type") == "video":
                trim = _range(selected.get("source_trim"))
                if not trim or trim[0] < 0 or trim[1] <= trim[0]: errors.append(f"{shot_id} {status} video requires a valid source_trim")
            elif candidate.get("media_type") == "image" and (not isinstance(selected.get("ken_burns"), dict) or not selected["ken_burns"]): errors.append(f"{shot_id} {status} image requires a non-empty ken_burns")
    for start, end, shot_id in sorted(ranges):
        for previous_start, previous_end, previous_id in ranges:
            if previous_id != shot_id and previous_start < end and start < previous_end:
                errors.append(f"{shot_id} program range overlaps {previous_id}"); break
    if project is not None:
        operations = {item.get("id"): item for item in project.get("operations", []) if isinstance(item, dict)} if isinstance(project, dict) else {}
        dependencies, based_on = plan.get("dependencies", []), plan.get("based_on", {})
        if not isinstance(dependencies, list): errors.append("dependencies must be a list"); dependencies = []
        elif any(not isinstance(item, str) or not item.strip() for item in dependencies): errors.append("dependencies must contain nonblank strings"); dependencies = [item for item in dependencies if isinstance(item, str) and item.strip()]
        if not isinstance(based_on, dict): errors.append("based_on must be an object"); based_on = {}
        active = project.get("active_sequence") if isinstance(project, dict) else None
        sequence = project.get("sequences", {}).get(active, {}) if isinstance(project, dict) and isinstance(project.get("sequences"), dict) else {}
        active_ids = sequence.get("operations", []) if isinstance(sequence, dict) else []
        required = (["understanding"] if "understanding" in operations else ["understand"] if "understand" in operations and "understand" in dependencies else [])
        required += [operation_id for operation_id in ("cut", "color-grade") if operation_id in active_ids and operation_id in operations]
        if set(dependencies) != set(required): errors.append("plan dependencies do not match current dependencies")
        if set(dependencies) != set(based_on): errors.append("based_on does not match dependencies")
        for dependency in dependencies:
            current = operations.get(dependency, {}).get("revision")
            if current != based_on.get(dependency): errors.append(f"based_on {dependency} revision is stale: expected {based_on.get(dependency)}, current {current}")
    if verify_files and not project_root: errors.append("verify_files requires project_root")
    if project_root:
        hashes = plan.get("input_hashes", {})
        for key, path in (("transcript_sha256", Path(project_root) / "work/understand/transcript.json"), ("timeline_sha256", Path(project_root) / "work/timeline.json")):
            if not path.is_file(): errors.append(f"{key.split('_')[0]} file is missing")
            elif not isinstance(hashes, dict) or hashes.get(key) != sha256_file(path): errors.append(f"{key.split('_')[0]} SHA-256 is stale")
    return errors


def apply_review(plan, review, *, mode, actor, rationale, interaction_path=None):
    if mode not in {"human", "agent"}: raise ValueError("mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip(): raise ValueError("actor is required")
    if not isinstance(rationale, str) or not rationale.strip(): raise ValueError("rationale is required")
    if mode == "human" and review.get("explicit_user_action") is not True: raise ValueError("human review requires explicit_user_action true")
    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip(): raise ValueError("review_id is required")
    result, shots = copy.deepcopy(plan), {shot.get("id"): shot for shot in plan.get("shots", [])}
    entries, seen = review.get("shots", []), set()
    if not isinstance(entries, list): raise ValueError("review shots must be a list")
    for entry in entries:
        shot_id = entry.get("id")
        if shot_id in seen: raise ValueError(f"duplicate review shot id: {shot_id}")
        seen.add(shot_id)
        if shot_id not in shots: raise ValueError(f"review has unknown shots: {shot_id}")
    missing = sorted(set(shots) - seen)
    if missing: raise ValueError("review is missing shots: " + ", ".join(missing))
    result_shots = {shot["id"]: shot for shot in result["shots"]}
    selected_hashes = []
    for entry in entries:
        shot, decision = result_shots[entry["id"]], entry.get("decision")
        if decision not in {"select", "skip"}: raise ValueError(f"{shot['id']} decision must be select or skip")
        if decision == "skip": shot["selected"], shot["status"] = None, "skipped"; continue
        candidate = next((item for item in shot.get("candidates", []) if item.get("id") == entry.get("candidate_id")), None)
        if not candidate: raise ValueError(f"{shot['id']} selected candidate does not belong to shot")
        option = "source_trim" if candidate.get("media_type") == "video" else "ken_burns"
        if not isinstance(entry.get(option), dict): raise ValueError(f"{shot['id']} select requires {option}")
        shot["selected"], shot["status"] = {"candidate_id": candidate["id"], option: copy.deepcopy(entry[option])}, "selected"; selected_hashes.append(candidate["sha256"])
    result["decision"] = {"mode": mode, "actor": actor, "rationale": rationale}
    result["review"] = {"status": "approved", "review_id": review["review_id"], "mode": mode, "actor": actor, "rationale": rationale, "plan_sha256": canonical_sha256(review_subject(result)), "candidate_manifest_sha256": canonical_sha256(candidate_manifest(result)), "selected_asset_sha256": sorted(set(selected_hashes))}
    if interaction_path:
        target = Path(interaction_path); target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=target.parent, suffix=".json", encoding="utf-8") as handle: temp = Path(handle.name)
        projectlib.write_json(temp, result["review"]); os.replace(temp, target)
    return result
