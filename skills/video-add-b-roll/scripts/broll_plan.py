"""Validate B-roll plans and record review decisions."""

import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib
import speaker_inset


RANGE_EPSILON = 1e-6
DYNAMIC_SOCIAL_MIN_RATIO = 0.40
DYNAMIC_SOCIAL_MAX_RATIO = 0.70
KEN_BURNS_DIRECTIONS = {"zoom-in", "pan-left", "pan-right"}
HUMAN_APPROVAL_RATIONALE = "Explicit user action approved the exact configuration shown in this review."
HUMAN_SELECTION_APPROVAL_RATIONALE = "Explicit user action approved the exact B-roll selection shown in this review."
HUMAN_PREPARE_COMPOSITE_RATIONALE = "Explicit user action locked the exact B-roll selection for composite preview."
REVIEW_INTENTS = {"approve", "request_revision"}
PRESENTATION_MODES = {"ordinary", "speaker-inset"}
CHAT_PRESENTATION_RATIONALE_SOURCE = "agent_chat_explicit_action"
PLAYBACK_RATES = (0.5, 1.0, 1.5, 2.0)
VISUAL_REVIEW_CHECKS = (
    "semantic_fit", "unwanted_logos_or_text", "jump_cuts",
    "entry_exit_boundaries", "grade_match",
)
SPEAKER_VISUAL_REVIEW_CHECKS = (
    "speaker_layout_fidelity", "speaker_legibility", "broll_focal_clearance",
)
PEXELS_LICENSE_URL = "https://www.pexels.com/license/"
PEXELS_TERMS_URL = "https://www.pexels.com/terms-of-service/"
_INVALID_NUMBER = object()
REVIEW_PAGE_PAYLOAD_RE = re.compile(r"atob\('([^']+)'\)")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def visual_review_checks(plan):
    checks = VISUAL_REVIEW_CHECKS
    if isinstance(plan, dict) and speaker_inset.style_enabled(plan.get("speaker_inset_style")):
        checks += SPEAKER_VISUAL_REVIEW_CHECKS
    return checks


def visual_review_subject(plan):
    return {key: value for key, value in plan.items() if key != "visual_review"}


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


def _strict_finite_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return _INVALID_NUMBER
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return _INVALID_NUMBER
    return number if math.isfinite(number) else _INVALID_NUMBER


def _positive_duration(value):
    duration = _strict_finite_number(value)
    return duration if duration is not _INVALID_NUMBER and duration > 0 else None


def _valid_source_trim(value, candidate):
    trim = _range(value)
    if not isinstance(value, dict) or not trim or trim[0] < 0 or trim[1] <= trim[0]:
        return False
    probe = candidate.get("probe")
    duration = _positive_duration(probe.get("duration_s")) if isinstance(probe, dict) else None
    return duration is not None and trim[1] <= duration


def _valid_ken_burns(value):
    return isinstance(value, dict) and isinstance(value.get("direction"), str) and value["direction"] in KEN_BURNS_DIRECTIONS


def timeline_frame_duration(timeline):
    fps = timeline.get("fps") if isinstance(timeline, dict) else None
    num = fps.get("num") if isinstance(fps, dict) else None
    den = fps.get("den") if isinstance(fps, dict) else None
    if (not isinstance(num, int) or isinstance(num, bool) or num <= 0
            or not isinstance(den, int) or isinstance(den, bool) or den <= 0):
        raise ValueError("timeline fps num and den must be positive integers")
    return den / num


def _range_dict(value):
    parsed = _range(value)
    if not parsed:
        return None
    return {"start_s": parsed[0], "end_s": parsed[1]}


def _ranges_equal(left, right, *, tolerance=RANGE_EPSILON):
    left_range, right_range = _range(left), _range(right)
    return bool(
        left_range and right_range
        and abs(left_range[0] - right_range[0]) <= tolerance
        and abs(left_range[1] - right_range[1]) <= tolerance
    )


def _frame_index(value, frame_duration):
    number = _strict_finite_number(value)
    if number is _INVALID_NUMBER:
        return None
    frame = round(number / frame_duration)
    return frame if abs(number - frame * frame_duration) <= RANGE_EPSILON else None


def allocate_program_ranges(program_range, segment_count, timeline):
    """Split a frame-aligned program range; the final segment absorbs the remainder."""
    if (not isinstance(segment_count, int) or isinstance(segment_count, bool)
            or segment_count < 1 or segment_count > 3):
        raise ValueError("segment_count must be 1-3")
    frame_duration = timeline_frame_duration(timeline)
    program = _range(program_range)
    if not program:
        raise ValueError("program_range is invalid")
    start_frame = _frame_index(program[0], frame_duration)
    end_frame = _frame_index(program[1], frame_duration)
    if start_frame is None or end_frame is None or end_frame - start_frame < segment_count:
        raise ValueError("program_range must be frame-aligned with at least one frame per segment")
    total_frames = end_frame - start_frame
    base_frames = total_frames // segment_count
    frame_counts = [base_frames] * segment_count
    frame_counts[-1] += total_frames % segment_count
    ranges = []
    cursor = start_frame
    for index, frame_count in enumerate(frame_counts):
        following = cursor + frame_count
        ranges.append({
            "start_s": program[0] if index == 0 else round(cursor * frame_duration, 9),
            "end_s": program[1] if index == segment_count - 1 else round(following * frame_duration, 9),
        })
        cursor = following
    return ranges


def _canonical_segment_errors(segment, candidate, program_range, frame_duration):
    errors = []
    if not isinstance(segment, dict):
        return ["segment must be an object"]
    candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
    if segment.get("candidate_id") != candidate_id:
        errors.append("segment candidate_id does not match candidate")
    rate = _strict_finite_number(segment.get("playback_rate"))
    if rate is _INVALID_NUMBER or rate not in PLAYBACK_RATES:
        errors.append("segment playback_rate must be one of 0.5, 1.0, 1.5, or 2.0")
    source = _range(segment.get("source_range"))
    program = _range(segment.get("program_range"))
    expected_program = _range(program_range)
    if not source or source[0] < 0 or source[1] <= source[0]:
        errors.append("segment source_range is invalid")
    elif not _valid_source_trim(segment.get("source_range"), candidate):
        errors.append("segment source_range exceeds candidate duration")
    if not program or program[1] <= program[0]:
        errors.append("segment program_range is invalid")
    elif not expected_program or not _ranges_equal(segment.get("program_range"), program_range):
        errors.append("segment program_range must equal the shot program range")
    if source and program and rate is not _INVALID_NUMBER and rate > 0:
        source_duration = source[1] - source[0]
        program_duration = program[1] - program[0]
        if abs(source_duration / rate - program_duration) > frame_duration + RANGE_EPSILON:
            errors.append("segment source and program durations must match within one timeline frame")
    return errors


def _canonical_segments_errors(segments, candidates, program_range, frame_duration):
    if not isinstance(segments, list) or not 1 <= len(segments) <= 3:
        return ["canonical selection requires 1-3 segments"]
    if not isinstance(candidates, list):
        return ["shot candidates must be a list"]
    candidate_map = {
        candidate.get("id"): candidate for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("id"), str)
    }
    ranked_ids = {
        candidate_id for candidate_id, candidate in candidate_map.items()
        if (isinstance(candidate.get("ranking"), dict)
            and isinstance(candidate["ranking"].get("rank"), int)
            and not isinstance(candidate["ranking"].get("rank"), bool)
            and 1 <= candidate["ranking"]["rank"] <= 3)
    }
    allowed_ids = ranked_ids if ranked_ids else set(candidate_map)
    shot_program = _range(program_range)
    shot_start = _frame_index(shot_program[0], frame_duration) if shot_program else None
    shot_end = _frame_index(shot_program[1], frame_duration) if shot_program else None
    errors = []
    seen_ids = set()
    previous_end = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            errors.append(f"segment {index + 1} must be an object")
            continue
        candidate_id = segment.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            errors.append(f"segment {index + 1} candidate_id is required")
            continue
        if candidate_id in seen_ids:
            errors.append("segment candidate IDs must be unique")
        seen_ids.add(candidate_id)
        candidate = candidate_map.get(candidate_id)
        if candidate is None or candidate.get("media_type") != "video":
            errors.append("segment candidate must belong to shot video candidates")
            continue
        if candidate_id not in allowed_ids:
            errors.append("segment candidate must belong to the bound Top 3")
        segment_program = _range(segment.get("program_range"))
        errors.extend(_canonical_segment_errors(
            segment, candidate, segment.get("program_range"), frame_duration,
        ))
        if not segment_program:
            continue
        start_frame = _frame_index(segment_program[0], frame_duration)
        end_frame = _frame_index(segment_program[1], frame_duration)
        if start_frame is None or end_frame is None:
            errors.append("segment program ranges must align to timeline frames")
            continue
        if end_frame - start_frame < 1:
            errors.append("each segment must occupy at least one timeline frame")
        if previous_end is not None and start_frame != previous_end:
            errors.append("segment program ranges must be continuous without gaps or overlaps")
        previous_end = end_frame
        if index == 0 and shot_start is not None and start_frame != shot_start:
            errors.append("segment program ranges must completely cover the shot program range")
    if (shot_start is None or shot_end is None):
        errors.append("shot program_range must align to timeline frames")
    elif previous_end is not None and previous_end != shot_end:
        errors.append("segment program ranges must completely cover the shot program range")
    return errors


def selection_details(shot, candidate, timeline):
    """Return canonical segment details while preserving legacy trim intent."""
    if not isinstance(shot, dict):
        raise ValueError("shot must be an object")
    candidates = candidate if isinstance(candidate, list) else [candidate]
    if not candidates or any(not isinstance(item, dict) for item in candidates):
        raise ValueError("candidate must be an object or list of objects")
    selected = shot.get("selected")
    if not isinstance(selected, dict):
        raise ValueError("shot selection is required")
    frame = timeline_frame_duration(timeline)
    program = _range(shot.get("program_range"))
    if not program or program[1] <= program[0]:
        raise ValueError("shot program_range is invalid")
    program_range = {"start_s": program[0], "end_s": program[1]}
    program_duration = program[1] - program[0]
    segments = selected.get("segments")
    if segments is not None:
        errors = _canonical_segments_errors(segments, candidates, program_range, frame)
        if errors:
            raise ValueError("; ".join(errors))
        canonical = copy.deepcopy(segments)
        segment_details = []
        for segment in canonical:
            source = _range(segment["source_range"])
            segment_program = _range(segment["program_range"])
            rate = float(segment["playback_rate"])
            segment_details.append({
                "candidate_id": segment["candidate_id"],
                "source_duration_s": source[1] - source[0],
                "effective_duration_s": (source[1] - source[0]) / rate,
                "program_duration_s": segment_program[1] - segment_program[0],
                "playback_rate": rate,
            })
        return {
            "format": "canonical",
            "segments": canonical,
            "segment_details": segment_details,
            "source_duration_s": sum(item["source_duration_s"] for item in segment_details),
            "effective_duration_s": sum(item["effective_duration_s"] for item in segment_details),
            "program_duration_s": program_duration,
        }
    candidate = next((item for item in candidates if item.get("id") == selected.get("candidate_id")), None)
    if candidate is None:
        raise ValueError("legacy video selection does not match candidate")
    if candidate.get("media_type") != "video" or selected.get("candidate_id") != candidate.get("id"):
        raise ValueError("legacy video selection does not match candidate")
    requested = _range(selected.get("source_trim"))
    if not requested or not _valid_source_trim(selected.get("source_trim"), candidate):
        raise ValueError("legacy video selection requires a valid source_trim")
    requested_duration = requested[1] - requested[0]
    if requested_duration + frame + RANGE_EPSILON < program_duration:
        raise ValueError("legacy source_trim cannot cover the shot program duration")
    effective_end = min(requested[1], requested[0] + program_duration)
    segment = {
        "candidate_id": candidate["id"],
        "source_range": {"start_s": requested[0], "end_s": effective_end},
        "program_range": program_range,
        "playback_rate": 1.0,
    }
    return {
        "format": "legacy",
        "segments": [segment],
        "segment_details": [{
            "candidate_id": candidate["id"],
            "source_duration_s": effective_end - requested[0],
            "effective_duration_s": effective_end - requested[0],
            "program_duration_s": program_duration,
            "playback_rate": 1.0,
        }],
        "legacy_requested_source_range": {"start_s": requested[0], "end_s": requested[1]},
        "source_duration_s": effective_end - requested[0],
        "effective_duration_s": effective_end - requested[0],
        "program_duration_s": program_duration,
    }


def selected_candidate_id(selected):
    values = selected_candidate_ids(selected)
    return values[0] if values else None


def selected_candidate_ids(selected):
    if not isinstance(selected, dict):
        return []
    segments = selected.get("segments")
    if segments is not None:
        if not isinstance(segments, list) or any(not isinstance(segment, dict) for segment in segments):
            return []
        return [segment.get("candidate_id") for segment in segments]
    candidate_id = selected.get("candidate_id")
    return [candidate_id] if candidate_id is not None else []


def candidate_manifest(plan):
    return [{"id": shot.get("id"), "candidates": sorted(copy.deepcopy(shot.get("candidates", [])), key=lambda item: str(item.get("id")))} for shot in sorted(plan.get("shots", []), key=lambda item: str(item.get("id")))]


def review_subject(plan):
    value = copy.deepcopy(plan)
    receipt = value.get("review")
    receipt_ids = receipt.get("decision_skipped_shot_ids", []) if (isinstance(receipt, dict) and receipt.get("status") == "approved" and receipt.get("review_stage") != "composite") else []
    decision_skipped_ids = set(receipt_ids) if isinstance(receipt_ids, list) and all(isinstance(shot_id, str) for shot_id in receipt_ids) else set()

    def clean(item):
        if isinstance(item, dict):
            for key in ("decision", "review", "review_status", "selected", "normalized", "verification", "visual_review"):
                item.pop(key, None)
            for child in item.values():
                clean(child)
        elif isinstance(item, list):
            for child in item:
                clean(child)

    clean(value)
    for shot in value.get("shots", []):
        status = shot.get("status") if isinstance(shot, dict) else None
        if isinstance(status, str) and status in ("planned", "candidates_ready", "composite_pending", "selected", "normalized", "verified"):
            shot["status"] = "reviewable"
        elif status == "skipped" and isinstance(shot.get("id"), str) and shot["id"] in decision_skipped_ids:
            shot["status"] = "reviewable"
    return value


def presentation_subject(plan):
    value = copy.deepcopy(plan)
    for key in (
            "presentation", "speaker_inset_style", "speaker_inset", "selection",
            "decision", "review", "review_status", "visual_review"):
        value.pop(key, None)

    def clean(item):
        if isinstance(item, dict):
            for key in ("selected", "normalized", "verification"):
                item.pop(key, None)
            for child in item.values():
                clean(child)
        elif isinstance(item, list):
            for child in item:
                clean(child)

    clean(value)
    for shot in value.get("shots", []):
        if isinstance(shot, dict) and shot.get("status") in {
                "planned", "candidates_ready", "composite_pending", "selected",
                "normalized", "verified"}:
            shot["status"] = "reviewable"
    return value


def presentation_errors(plan, *, project_root=None, required=False):
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    presentation = plan.get("presentation")
    if presentation is None:
        return ["agent-chat presentation decision is required"] if required else []
    if not isinstance(presentation, dict):
        return ["presentation decision binding must be an object"]
    errors = []
    if presentation.get("status") != "chosen":
        errors.append("presentation decision status must be chosen")
    mode = presentation.get("mode")
    if mode not in PRESENTATION_MODES:
        errors.append("presentation decision mode is invalid")
    if not _is_uuid(presentation.get("decision_id")):
        errors.append("presentation decision id is invalid")
    if not isinstance(presentation.get("actor"), str) or not presentation["actor"].strip():
        errors.append("presentation decision actor is required")
    if not _valid_timestamp(presentation.get("timestamp")):
        errors.append("presentation decision timestamp is invalid")
    if presentation.get("path") != "b-roll/presentation-decision.json":
        errors.append("presentation decision path is invalid")
    if not _is_sha256(presentation.get("sha256")):
        errors.append("presentation decision SHA-256 is invalid")
    carried_from = presentation.get("carried_from_plan_sha256")
    if carried_from is not None and not _is_sha256(carried_from):
        errors.append("presentation carried plan SHA-256 is invalid")
    if mode == "speaker-inset":
        style = plan.get("speaker_inset_style")
        if not speaker_inset.style_enabled(style) or speaker_inset.style_errors(style):
            errors.append("speaker-inset presentation requires enabled speaker_inset_style")
    elif speaker_inset.style_enabled(plan.get("speaker_inset_style")):
        errors.append("ordinary presentation must not enable speaker_inset_style")
    if project_root is None or errors:
        return errors
    root = Path(project_root).resolve()
    path = root / "work" / presentation["path"]
    try:
        path.resolve().relative_to((root / "work").resolve())
    except ValueError:
        return errors + ["presentation decision path escapes work"]
    if not path.is_file() or sha256_file(path) != presentation["sha256"]:
        return errors + ["presentation decision artifact is missing or stale"]
    try:
        receipt = projectlib.load_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return errors + ["presentation decision artifact is invalid"]
    if not isinstance(receipt, dict):
        return errors + ["presentation decision artifact must be an object"]
    current_plan_sha256 = canonical_sha256(presentation_subject(plan))
    receipt_plan_sha256 = receipt.get("plan_sha256")
    if (receipt_plan_sha256 != current_plan_sha256
            and (carried_from is None or receipt_plan_sha256 != carried_from)):
        errors.append("presentation decision plan_sha256 does not match")
    expected = {
        "schema_version": 1,
        "status": "chosen",
        "mode": "human",
        "rationale_source": CHAT_PRESENTATION_RATIONALE_SOURCE,
        "explicit_user_action": True,
        "decision_id": presentation.get("decision_id"),
        "actor": presentation.get("actor"),
        "timestamp": presentation.get("timestamp"),
        "presentation_mode": mode,
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            errors.append(f"presentation decision {field} does not match")
    if not isinstance(receipt.get("user_response"), str) or not receipt["user_response"].strip():
        errors.append("presentation decision user_response is required")
    recommendation = receipt.get("agent_recommendation")
    if (not isinstance(recommendation, dict)
            or recommendation.get("presentation_mode") not in PRESENTATION_MODES
            or not isinstance(recommendation.get("rationale"), str)
            or not recommendation["rationale"].strip()):
        errors.append("presentation decision agent_recommendation is invalid")
    return errors


def record_chat_presentation_decision(plan, decision, *, project_root):
    """Persist an explicit Agent-chat route choice before any B-roll review page."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    if not isinstance(decision, dict):
        raise ValueError("presentation decision must be an object")
    if plan.get("presentation") is not None:
        raise ValueError("presentation decision is already recorded; rebuild the plan to change it")
    if any(key in plan for key in ("selection", "speaker_inset", "review_status", "visual_review")):
        raise ValueError("presentation decision must precede selection and review")
    if any(isinstance(shot, dict) and shot.get("status") not in {"candidates_ready", "skipped"}
           for shot in plan.get("shots", [])):
        raise ValueError("presentation decision requires candidates_ready or skipped shots")
    expected = {
        "mode": "human",
        "rationale_source": CHAT_PRESENTATION_RATIONALE_SOURCE,
        "explicit_user_action": True,
        "plan_sha256": canonical_sha256(presentation_subject(plan)),
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
    }
    for field, value in expected.items():
        if decision.get(field) != value:
            raise ValueError(f"presentation decision {field} does not match")
    if not _is_uuid(decision.get("decision_id")):
        raise ValueError("presentation decision id is invalid")
    if not isinstance(decision.get("actor"), str) or not decision["actor"].strip():
        raise ValueError("presentation decision actor is required")
    if not _valid_timestamp(decision.get("timestamp")):
        raise ValueError("presentation decision timestamp is invalid")
    if not isinstance(decision.get("user_response"), str) or not decision["user_response"].strip():
        raise ValueError("presentation decision user_response is required")
    mode = decision.get("presentation_mode")
    recommendation = decision.get("agent_recommendation")
    if mode not in PRESENTATION_MODES:
        raise ValueError("presentation decision mode is invalid")
    if (not isinstance(recommendation, dict)
            or recommendation.get("presentation_mode") not in PRESENTATION_MODES
            or not isinstance(recommendation.get("rationale"), str)
            or not recommendation["rationale"].strip()):
        raise ValueError("presentation decision agent_recommendation is invalid")
    result = copy.deepcopy(plan)
    if mode == "speaker-inset":
        style = result.get("speaker_inset_style")
        if style is None:
            result["speaker_inset_style"] = speaker_inset.default_style()
        elif not speaker_inset.style_enabled(style) or speaker_inset.style_errors(style):
            raise ValueError("speaker-inset presentation requires enabled speaker_inset_style")
    else:
        result.pop("speaker_inset_style", None)
    root = Path(project_root).resolve()
    target = root / "work/b-roll/presentation-decision.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = copy.deepcopy(decision)
    receipt.update({"schema_version": 1, "status": "chosen"})
    part = target.with_suffix(".part.json")
    try:
        projectlib.write_json(part, receipt)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)
    result["presentation"] = {
        "status": "chosen",
        "mode": mode,
        "path": "b-roll/presentation-decision.json",
        "sha256": sha256_file(target),
        "decision_id": decision["decision_id"],
        "actor": decision["actor"].strip(),
        "timestamp": decision["timestamp"],
    }
    errors = presentation_errors(result, project_root=root, required=True)
    if errors:
        target.unlink(missing_ok=True)
        raise ValueError("invalid presentation decision: " + "; ".join(errors))
    return result


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
        if status not in ("composite_pending", "selected", "normalized", "verified"):
            return None
        selected, candidates = shot.get("selected"), shot.get("candidates")
        if not isinstance(selected, dict) or not isinstance(candidates, list):
            return None
        segments = selected.get("segments")
        if segments is not None:
            if (not isinstance(segments, list) or not 1 <= len(segments) <= 3
                    or any(not isinstance(segment, dict) for segment in segments)):
                return None
            selected_ids = [segment.get("candidate_id") for segment in segments]
        else:
            selected_ids = [selected.get("candidate_id")]
        if (any(not isinstance(candidate_id, str) or not candidate_id.strip()
                for candidate_id in selected_ids)
                or len(selected_ids) != len(set(selected_ids))):
            return None
        selected_candidates = [
            next((item for item in candidates
                  if isinstance(item, dict) and item.get("id") == candidate_id), None)
            for candidate_id in selected_ids
        ]
        if any(candidate is None for candidate in selected_candidates):
            return None
        if segments is not None and all(candidate.get("media_type") == "video" for candidate in selected_candidates):
            decisions.append({
                "id": shot_id,
                "decision": "select",
                "program_range": copy.deepcopy(shot.get("program_range")),
                "segments": copy.deepcopy(segments),
            })
            continue
        candidate = selected_candidates[0]
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
        decisions.append({"id": shot_id, "decision": "select", "candidate_id": selected_ids[0], option: copy.deepcopy(value)})
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
    persisted_intent = review.get("submission_intent")
    if persisted_intent is not None and persisted_intent not in {"approve", "approve_selection"}:
        errors.append("approved review submission_intent is invalid")
    if persisted_intent in {"approve", "approve_selection"} and (
            not isinstance(review.get("revision_notes"), str)
            or review["revision_notes"].strip()):
        errors.append("approved review revision_notes must be empty")
    if (persisted_intent == "approve_selection"
            and review.get("approval_scope") != "b-roll-selection"):
        errors.append("approved selection review scope is invalid")
    if not isinstance(review.get("review_id"), str) or not review["review_id"].strip(): errors.append("review_id is required")
    elif not _is_uuid(review["review_id"]): errors.append("review_id must be a UUID")
    mode, actor, rationale = decision.get("mode"), decision.get("actor"), decision.get("rationale")
    if mode not in ("human", "agent"): errors.append("review mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip(): errors.append("review actor is required")
    if not isinstance(rationale, str) or not rationale.strip(): errors.append("review rationale is required")
    if any(review.get(key) != decision.get(key) for key in ("mode", "actor", "rationale")):
        errors.append("decision and review authority do not match")
    if ("rationale_source" in review or "rationale_source" in decision) and review.get("rationale_source") != decision.get("rationale_source"):
        errors.append("decision and review rationale_source do not match")
    if not _valid_timestamp(review.get("timestamp")): errors.append("review timestamp is invalid")
    if mode == "human" and (decision.get("explicit_user_action") is not True or review.get("explicit_user_action") is not True):
        errors.append("human review requires explicit_user_action true")
    if persisted_intent in {"approve", "approve_selection"} and mode == "human":
        expected_rationale = (
            HUMAN_SELECTION_APPROVAL_RATIONALE
            if persisted_intent == "approve_selection"
            else HUMAN_APPROVAL_RATIONALE
        )
        if rationale != expected_rationale:
            errors.append("new human review rationale must describe the explicit UI action")
        if (decision.get("rationale_source") != "review_ui_explicit_action"
                or review.get("rationale_source") != "review_ui_explicit_action"):
            errors.append("new human review rationale_source is invalid")
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
        selected = shot["selected"]
        for selected_id in selected_candidate_ids(selected):
            candidate = next((item for item in candidates if isinstance(item, dict) and item.get("id") == selected_id), None)
            if isinstance(candidate, dict) and isinstance(candidate.get("sha256"), str):
                selected_hashes.append(candidate["sha256"])
    if review.get("selected_asset_sha256") != sorted(set(selected_hashes)):
        errors.append("review selected asset hashes do not match")
    input_hashes = plan.get("input_hashes")
    if not isinstance(input_hashes, dict):
        errors.append("plan input_hashes must be an object")
        input_hashes = {}
    if review.get("review_video_sha256") != input_hashes.get("review_video_sha256"):
        errors.append("review video SHA-256 does not match")
    speaker_review_required = (
        speaker_inset.style_enabled(plan.get("speaker_inset_style"))
        and any(
            isinstance(shot, dict) and shot.get("status") in {
                "composite_pending", "selected", "normalized", "verified",
            }
            for shot in shots
        )
    )
    if speaker_review_required:
        if review.get("review_stage") != "composite":
            errors.append("speaker inset approval review_stage must be composite")
        speaker = plan.get("speaker_inset")
        expected_speaker = {
            "selection_sha256": plan.get("selection", {}).get("sha256"),
            "analysis_sha256": speaker.get("analysis", {}).get("sha256") if isinstance(speaker, dict) else None,
            "agent_input_sha256": speaker.get("agent_input", {}).get("sha256") if isinstance(speaker, dict) else None,
            "preview_sha256": speaker.get("preview", {}).get("sha256") if isinstance(speaker, dict) else None,
            "clearance_sha256": speaker.get("clearance", {}).get("sha256") if isinstance(speaker, dict) else None,
            "style_sha256": canonical_sha256(plan.get("speaker_inset_style")),
        }
        for field, expected in expected_speaker.items():
            if review.get(field) != expected:
                errors.append(f"review {field} does not match current speaker artifacts")
    return errors


def _ordinary_source_review_errors(plan, *, project_root=None, verify_files=False):
    review = plan.get("review") if isinstance(plan, dict) else None
    if (not isinstance(review, dict)
            or review.get("submission_intent") != "approve"
            or review.get("review_stage") == "composite"):
        return []
    source = review.get("source_review")
    if not isinstance(source, dict):
        return ["approved review source page is invalid"]
    if (not _is_uuid(source.get("review_id"))
            or source.get("review_id") != review.get("review_id")
            or source.get("consumed") is not True):
        return ["approved review source page is invalid"]
    path_value = source.get("path")
    if (not isinstance(path_value, str)
            or path_value != f"review/03-b-roll/b-roll-review-{review['review_id']}.html"
            or not _is_sha256(source.get("sha256"))):
        return ["approved review source page binding is invalid"]
    if not verify_files:
        return []
    if project_root is None:
        return ["approved review page verification requires project root"]
    root = Path(project_root).resolve()
    page = (root / path_value).resolve()
    try:
        page.relative_to((root / "review/03-b-roll").resolve())
    except ValueError:
        return ["approved review page path is invalid"]
    if not page.is_file() or sha256_file(page) != source["sha256"]:
        return ["approved review page is missing or stale"]
    return []


def _speaker_artifact_binding_errors(plan, shots):
    style = plan.get("speaker_inset_style")
    enabled = speaker_inset.style_enabled(style)
    speaker = plan.get("speaker_inset")
    if not enabled:
        return ["speaker_inset artifacts require enabled speaker_inset_style"] if speaker is not None else []
    selected = any(
        isinstance(shot, dict) and shot.get("status") in ("selected", "normalized", "verified")
        for shot in shots
    )
    if speaker is None:
        return ["selected speaker inset shots require speaker_inset artifacts"] if selected else []
    if not isinstance(speaker, dict):
        return ["speaker_inset must be an object"]
    errors = []
    expected_paths = {
        "analysis": "b-roll/speaker-inset-analysis.json",
        "agent_input": "b-roll/speaker-inset-agent-input.json",
        "preview": "b-roll/speaker-inset-preview.json",
        "clearance": "b-roll/speaker-inset-clearance.json",
    }
    if any(key not in expected_paths for key in speaker):
        errors.append("speaker_inset contains unsupported artifacts")
    seen_missing = False
    for name, expected_path in expected_paths.items():
        binding = speaker.get(name)
        if binding is None:
            seen_missing = True
            if selected:
                errors.append(f"selected speaker inset shots require {name} artifact")
            continue
        if seen_missing:
            errors.append(f"speaker_inset {name} requires all preceding artifacts")
        if not isinstance(binding, dict):
            errors.append(f"speaker_inset {name} binding must be an object")
            continue
        if binding.get("path") != expected_path:
            errors.append(f"speaker_inset {name} path is invalid")
        if not _is_sha256(binding.get("sha256")):
            errors.append(f"speaker_inset {name} SHA-256 is invalid")
    selection = plan.get("selection")
    if isinstance(selection, dict) and selection.get("style_sha256") != canonical_sha256(style):
        errors.append("approved selection speaker inset style SHA-256 is stale")
    return errors


def _visual_review_errors(plan, *, project_root=None, verify_files=False):
    review = plan.get("visual_review")
    if not isinstance(review, dict) or review.get("status") != "completed":
        return ["visual review must be completed"]
    errors = []
    decision = plan.get("review")
    if not isinstance(decision, dict) or review.get("review_id") != decision.get("review_id"):
        errors.append("visual review UUID does not match active review")
    if review.get("plan_sha256") != canonical_sha256(visual_review_subject(plan)):
        errors.append("visual review plan SHA-256 does not match")
    if review.get("mode") not in ("human", "agent"):
        errors.append("visual review mode must be human or agent")
    if not isinstance(review.get("actor"), str) or not review["actor"].strip():
        errors.append("visual review actor is required")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        errors.append("visual review rationale is required")
    if not _valid_timestamp(review.get("timestamp")):
        errors.append("visual review timestamp is invalid")
    if review.get("mode") == "human" and review.get("explicit_user_action") is not True:
        errors.append("human visual review requires explicit_user_action true")
    required_checks = visual_review_checks(plan)
    checks = review.get("checks")
    if (not isinstance(checks, dict) or set(checks) != set(required_checks)
            or any(checks[key] is not True for key in required_checks)):
        errors.append("all visual checks must be true booleans")
    for name, expected_path in (
        ("receipt", "work/b-roll/b-roll-visual-review.json"),
        ("report", "review/03-b-roll/b-roll-visual-review.md"),
    ):
        binding = review.get(name)
        if not isinstance(binding, dict) or binding.get("path") != expected_path or not _is_sha256(binding.get("sha256")):
            errors.append(f"visual review {name} binding is invalid")
            continue
        if verify_files and project_root:
            root, raw = Path(project_root).resolve(), Path(binding["path"])
            path = (root / raw).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                errors.append(f"visual review {name} path escapes project root")
                continue
            if not path.is_file():
                errors.append(f"visual review {name} file is missing")
            elif sha256_file(path) != binding["sha256"]:
                errors.append(f"visual review {name} SHA-256 is stale")
    return errors


def _range(value):
    if not isinstance(value, dict):
        return None
    start = _strict_finite_number(value.get("start_s"))
    end = _strict_finite_number(value.get("end_s"))
    if start is _INVALID_NUMBER or end is _INVALID_NUMBER:
        return None
    return start, end


def coverage_summary(plan, planned=(), shortlisted=(), selected=()):
    """Summarize internal B-roll coverage without changing plan validity."""
    duration = _positive_duration(plan.get("program_duration_s")) if isinstance(plan, dict) else None
    duration = duration if duration is not None else 0.0
    shot_ranges = {
        shot.get("id"): shot.get("program_range")
        for shot in plan.get("shots", []) if isinstance(plan, dict) and isinstance(shot, dict)
    }

    def stage_summary(members):
        if isinstance(members, dict):
            members = [members]
        elif not isinstance(members, (list, tuple, set)):
            members = []
        ranges = []
        for member in members:
            value = shot_ranges.get(member) if isinstance(member, str) else member
            interval = _range(value.get("program_range")) if isinstance(value, dict) and "program_range" in value else _range(value)
            if not interval or duration <= 0:
                continue
            start, end = max(0.0, interval[0]), min(duration, interval[1])
            if end > start:
                ranges.append((start, end))
        merged = []
        for start, end in sorted(ranges):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        covered = round(sum(end - start for start, end in merged), 9)
        ratio = round(covered / duration, 9) if duration else 0.0
        status = (
            "below_target" if ratio < DYNAMIC_SOCIAL_MIN_RATIO
            else "above_target" if ratio > DYNAMIC_SOCIAL_MAX_RATIO
            else "within_target"
        )
        return {"duration_s": covered, "ratio": ratio, "status": status}

    return {
        "profile": "dynamic-social",
        "target_min_ratio": DYNAMIC_SOCIAL_MIN_RATIO,
        "target_max_ratio": DYNAMIC_SOCIAL_MAX_RATIO,
        "planned": stage_summary(planned),
        "shortlisted": stage_summary(shortlisted),
        "selected": stage_summary(selected),
    }


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
        speed = _strict_finite_number(clip.get("speed"))
        if (not isinstance(clip_id, str) or not clip_id.strip() or not source or source[1] <= source[0]
                or not clip_program or clip_program[1] <= clip_program[0]
                or speed is _INVALID_NUMBER or speed <= 0):
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


def _valid_pexels_url(value, host, path_prefix=None):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and not parsed.username
        and not parsed.password
        and (parsed.hostname or "").lower() == host
        and port in (None, 443)
        and not parsed.fragment
        and (path_prefix is None or parsed.path.startswith(path_prefix))
    )


def _candidate_errors(shot_id, candidate):
    errors = []
    if not isinstance(candidate, dict):
        return [f"{shot_id} candidate must be an object"]
    candidate_id = candidate.get("id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        errors.append(f"{shot_id} candidate id is required")
    elif candidate_id == "skip":
        errors.append(f"{shot_id} candidate id 'skip' is reserved")
    media_type = candidate.get("media_type")
    if media_type not in ("video", "image"):
        errors.append(f"{shot_id} candidate {candidate_id} media_type is invalid")
    if not isinstance(candidate.get("cache_path"), str) or not candidate["cache_path"].strip():
        errors.append(f"{shot_id} candidate {candidate_id} cache_path is required")
    if not isinstance(candidate.get("sha256"), str) or len(candidate["sha256"]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in candidate["sha256"]):
        errors.append(f"{shot_id} candidate {candidate_id} SHA-256 is required")
    if "duration_s" in candidate and _positive_duration(candidate["duration_s"]) is None:
        errors.append(f"{shot_id} candidate {candidate_id} duration_s must be a finite positive number")
    if "probe" in candidate:
        probe = candidate["probe"]
        if not isinstance(probe, dict):
            errors.append(f"{shot_id} candidate {candidate_id} probe must be an object")
        elif "duration_s" in probe and _positive_duration(probe["duration_s"]) is None:
            errors.append(f"{shot_id} candidate {candidate_id} probe.duration_s must be a finite positive number")
    else:
        probe = None
    direct_duration = _positive_duration(candidate.get("duration_s"))
    probe_duration = _positive_duration(probe.get("duration_s")) if isinstance(probe, dict) else None
    if media_type == "video" and probe_duration is None:
        errors.append(f"{shot_id} candidate {candidate_id} video requires a finite positive probe.duration_s")
    byte_count = candidate.get("bytes")
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
        errors.append(f"{shot_id} candidate {candidate_id} bytes must be a positive integer")
    provenance = candidate.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source_type") not in ("local", "pexels", "external-generated"):
        errors.append(f"{shot_id} candidate {candidate_id} provenance is invalid")
        return errors
    if not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in ("creator", "license", "retrieval_time")):
        errors.append(f"{shot_id} candidate {candidate_id} provenance is incomplete")
    if not _valid_timestamp(provenance.get("retrieval_time")):
        errors.append(f"{shot_id} candidate {candidate_id} provenance retrieval_time is invalid")
    source_type = provenance["source_type"]
    if source_type == "local":
        if not isinstance(provenance.get("original_path"), str) or not provenance["original_path"].strip():
            errors.append(f"{shot_id} candidate {candidate_id} provenance is incomplete")
            errors.append(f"{shot_id} candidate {candidate_id} local provenance original_path is required")
    elif source_type == "external-generated":
        required = ("original_path", "generation_provider", "generation_model")
        prompt, job_id = provenance.get("prompt"), provenance.get("job_id")
        optional_values = [value for key, value in (("prompt", prompt), ("job_id", job_id)) if key in provenance]
        if (not all(isinstance(provenance.get(key), str) and provenance[key].strip() for key in required)
                or not any(isinstance(value, str) and value.strip() for value in (prompt, job_id))
                or any(not isinstance(value, str) or not value.strip() for value in optional_values)):
            errors.append(f"{shot_id} candidate {candidate_id} external-generated provenance is incomplete")
    elif source_type == "pexels":
        for field in ("provider_id", "file_id"):
            value = candidate.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"{shot_id} candidate {candidate_id} Pexels {field} must be a positive integer")
        if not _valid_pexels_url(candidate.get("download_url"), "videos.pexels.com"):
            errors.append(f"{shot_id} candidate {candidate_id} Pexels download_url is invalid")
        for field in ("width", "height"):
            value = candidate.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"{shot_id} candidate {candidate_id} Pexels {field} must be a positive integer")
        if direct_duration is None:
            errors.append(f"{shot_id} candidate {candidate_id} Pexels duration_s is required")
        if not _valid_pexels_url(provenance.get("source_url"), "www.pexels.com", "/video/"):
            errors.append(f"{shot_id} candidate {candidate_id} Pexels source_url is invalid")
        if provenance.get("license_url") != PEXELS_LICENSE_URL:
            errors.append(f"{shot_id} candidate {candidate_id} Pexels license_url is invalid")
        if provenance.get("terms_url") != PEXELS_TERMS_URL:
            errors.append(f"{shot_id} candidate {candidate_id} Pexels terms_url is invalid")
        provenance_provider_id = provenance.get("provider_id")
        if not isinstance(provenance_provider_id, int) or isinstance(provenance_provider_id, bool) or provenance_provider_id <= 0:
            errors.append(f"{shot_id} candidate {candidate_id} Pexels provenance provider_id must be a positive integer")
        if provenance_provider_id != candidate.get("provider_id"):
            errors.append(f"{shot_id} candidate {candidate_id} Pexels provenance provider_id does not match candidate")
        if provenance.get("download_url") != candidate.get("download_url"):
            errors.append(f"{shot_id} candidate {candidate_id} Pexels provenance download_url does not match candidate")
        dimensions = provenance.get("dimensions")
        valid_dimensions = isinstance(dimensions, dict) and all(
            isinstance(dimensions.get(field), int) and not isinstance(dimensions[field], bool) and dimensions[field] > 0
            for field in ("width", "height")
        )
        if not valid_dimensions or dimensions.get("width") != candidate.get("width") or dimensions.get("height") != candidate.get("height"):
            errors.append(f"{shot_id} candidate {candidate_id} Pexels provenance dimensions do not match candidate")
        provenance_duration = _positive_duration(provenance.get("duration_s"))
        if provenance_duration is None or provenance_duration != direct_duration:
            errors.append(f"{shot_id} candidate {candidate_id} Pexels provenance duration_s does not match candidate")
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


def _inside(root, target):
    try:
        Path(target).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _candidate_ranking_errors(plan, shots, *, project_root=None, verify_files=False):
    binding = plan.get("candidate_ranking")
    if binding is None:
        return []
    errors = []
    if not isinstance(binding, dict):
        return ["candidate_ranking must be an object"]
    path_value = binding.get("path")
    raw_path = Path(path_value) if isinstance(path_value, str) else None
    if (raw_path is None or raw_path.is_absolute() or ".." in raw_path.parts
            or not raw_path.parts or raw_path.parts[0] != "b-roll"):
        errors.append("candidate ranking path is invalid")
    if not _is_sha256(binding.get("sha256")):
        errors.append("candidate ranking SHA-256 is invalid")
    if not _is_sha256(binding.get("analysis_sha256")):
        errors.append("candidate ranking analysis SHA-256 is invalid")
    shortlists = binding.get("shortlists")
    if not isinstance(shortlists, list):
        errors.append("candidate ranking shortlists must be a list")
        shortlists = []
    shortlist_map, seen = {}, set()
    for shortlist in shortlists:
        if not isinstance(shortlist, dict):
            errors.append("candidate ranking shortlist must be an object")
            continue
        shot_id, candidate_ids = shortlist.get("shot_id"), shortlist.get("candidate_ids")
        if not isinstance(shot_id, str) or not shot_id.strip() or shot_id in seen:
            errors.append("candidate ranking shortlist shot ids must be unique nonblank strings")
            continue
        seen.add(shot_id)
        if (not isinstance(candidate_ids, list) or len(candidate_ids) > 3
                or any(not isinstance(item, str) or not item.strip() for item in candidate_ids)
                or len(candidate_ids) != len(set(candidate_ids))):
            errors.append(f"{shot_id} candidate ranking shortlist is invalid")
            candidate_ids = []
        shortlist_map[shot_id] = candidate_ids
    shot_map = {shot.get("id"): shot for shot in shots if isinstance(shot, dict) and isinstance(shot.get("id"), str)}
    if set(shortlist_map) != set(shot_map):
        errors.append("candidate ranking shortlists do not match plan shots")
    for shot_id, shot in shot_map.items():
        candidate_ids = [item.get("id") for item in shot.get("candidates", []) if isinstance(item, dict)]
        expected_ids = shortlist_map.get(shot_id, [])
        if candidate_ids != expected_ids:
            errors.append(f"{shot_id} candidates do not match ranked Top 3")
        for index, candidate in enumerate(shot.get("candidates", []), 1):
            if not isinstance(candidate, dict):
                continue
            candidate_id = candidate.get("id")
            ranking = candidate.get("ranking")
            if not isinstance(ranking, dict):
                errors.append(f"{shot_id} candidate {candidate_id} ranking evidence is required")
                continue
            if ranking.get("rank") != index:
                errors.append(f"{shot_id} candidate {candidate_id} rank does not match shortlist order")
            scores = ranking.get("scores")
            if not isinstance(scores, dict):
                errors.append(f"{shot_id} candidate {candidate_id} ranking scores are invalid")
            else:
                for field in ("semantic_fit", "context_fit", "composition_fit", "style_fit"):
                    value = scores.get(field)
                    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 4:
                        errors.append(f"{shot_id} candidate {candidate_id} ranking {field} is invalid")
                risk = scores.get("text_logo_risk")
                if (not isinstance(risk, int) or isinstance(risk, bool) or not 0 <= risk <= 4) and risk != "uncertain":
                    errors.append(f"{shot_id} candidate {candidate_id} ranking text_logo_risk is invalid")
            if not isinstance(ranking.get("rationale"), str) or not ranking["rationale"].strip():
                errors.append(f"{shot_id} candidate {candidate_id} ranking rationale is required")
            for field in ("warnings", "duplicate_notes"):
                value = ranking.get(field)
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    errors.append(f"{shot_id} candidate {candidate_id} ranking {field} must contain strings")
            similar = ranking.get("similar_footage")
            if similar is not None and (not isinstance(similar, list) or any(
                    not isinstance(item, dict) or not isinstance(item.get("shot_id"), str) or not item["shot_id"].strip()
                    or not isinstance(item.get("candidate_id"), str) or not item["candidate_id"].strip()
                    for item in similar)):
                errors.append(f"{shot_id} candidate {candidate_id} ranking similar_footage is invalid")
    if verify_files:
        if project_root is None:
            errors.append("candidate ranking file verification requires project root")
        elif raw_path is not None and not raw_path.is_absolute() and ".." not in raw_path.parts:
            root = Path(project_root).resolve()
            ranking_path = (root / "work" / raw_path).resolve()
            if not _inside(root / "work/b-roll", ranking_path):
                errors.append("candidate ranking path escapes work/b-roll")
            elif not ranking_path.is_file():
                errors.append("candidate ranking file is missing")
            else:
                if binding.get("sha256") != sha256_file(ranking_path):
                    errors.append("candidate ranking SHA-256 is stale")
                try:
                    ranking_document = projectlib.load_json(ranking_path)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("candidate ranking file is invalid")
                    ranking_document = None
                if isinstance(ranking_document, dict):
                    if ranking_document.get("analysis_sha256") != binding.get("analysis_sha256"):
                        errors.append("candidate ranking analysis SHA-256 does not match")
                    ranked_shots = ranking_document.get("shots")
                    if not isinstance(ranked_shots, list):
                        errors.append("candidate ranking file shots are invalid")
                    else:
                        ranked_map = {item.get("shot_id"): item for item in ranked_shots if isinstance(item, dict) and isinstance(item.get("shot_id"), str)}
                        ranked_refs = {
                            (shot_id, candidate.get("candidate_id"))
                            for shot_id, ranked_shot in ranked_map.items()
                            for candidate in ranked_shot.get("candidates", [])
                            if isinstance(candidate, dict) and isinstance(candidate.get("candidate_id"), str)
                        }
                        selected_refs = {
                            (shot_id, candidate_id)
                            for shot_id, ranked_shot in ranked_map.items()
                            for candidate_id in ranked_shot.get("top3", [])
                            if isinstance(candidate_id, str)
                        }
                        allocations = ranking_document.get("global_allocations")
                        if allocations is not None:
                            if not isinstance(allocations, list):
                                errors.append("candidate ranking global allocations must be a list")
                            else:
                                seen_allocations = set()
                                for allocation in allocations:
                                    if not isinstance(allocation, dict):
                                        errors.append("candidate ranking global allocation must be an object")
                                        continue
                                    allocation_id = allocation.get("allocation_id")
                                    if not isinstance(allocation_id, str) or not allocation_id.strip() or allocation_id in seen_allocations:
                                        errors.append("candidate ranking global allocation ids must be unique nonblank strings")
                                    seen_allocations.add(allocation_id)
                                    members = allocation.get("members")
                                    member_refs = [(member.get("shot_id"), member.get("candidate_id")) for member in members] if isinstance(members, list) and all(isinstance(member, dict) for member in members) else []
                                    kept = allocation.get("kept")
                                    kept_ref = (kept.get("shot_id"), kept.get("candidate_id")) if isinstance(kept, dict) else None
                                    suppressed = allocation.get("suppressed")
                                    suppressed_refs = [(member.get("shot_id"), member.get("candidate_id")) for member in suppressed] if isinstance(suppressed, list) and all(isinstance(member, dict) for member in suppressed) else []
                                    if (not isinstance(members, list) or len(member_refs) < 2 or len(member_refs) != len(set(member_refs))
                                            or any(ref not in ranked_refs for ref in member_refs) or kept_ref not in member_refs
                                            or set(suppressed_refs) != set(member_refs) - {kept_ref}):
                                        errors.append(f"candidate ranking global allocation {allocation_id} members are invalid")
                                        continue
                                    selected_members = set(member_refs) & selected_refs
                                    if len(selected_members) > 1 or selected_members and selected_members != {kept_ref}:
                                        errors.append(f"candidate ranking global allocation {allocation_id} is not unique across shortlists")
                        for shot_id, expected_ids in shortlist_map.items():
                            ranked_shot = ranked_map.get(shot_id)
                            if not isinstance(ranked_shot, dict) or ranked_shot.get("top3") != expected_ids:
                                errors.append(f"{shot_id} ranked Top 3 does not match binding")
                                continue
                            details = {item.get("candidate_id"): item for item in ranked_shot.get("candidates", []) if isinstance(item, dict)}
                            for index, candidate in enumerate(shot_map.get(shot_id, {}).get("candidates", []), 1):
                                if not isinstance(candidate, dict):
                                    continue
                                detail, summary = details.get(candidate.get("id")), candidate.get("ranking")
                                if (not isinstance(detail, dict) or not isinstance(summary, dict)
                                        or detail.get("rank") != index
                                        or detail.get("scores") != summary.get("scores")
                                        or detail.get("warnings") != summary.get("warnings")
                                        or detail.get("rationale") != summary.get("rationale")
                                        or detail.get("similar_footage", []) != summary.get("similar_footage", [])):
                                    errors.append(f"{shot_id} candidate {candidate.get('id')} ranking evidence does not match ranking file")
    return errors


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
    inset_enabled = speaker_inset.style_enabled(plan.get("speaker_inset_style"))
    if inset_enabled:
        for shot in plan["shots"]:
            if shot.get("status") == "skipped":
                continue
            composition_errors = speaker_inset.normalized_composition_errors(plan, shot)
            if composition_errors:
                raise ValueError("; ".join(composition_errors))
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
        candidate_ids = selected_candidate_ids(selection)
        candidates = [
            next((item for item in shot.get("candidates", [])
                  if isinstance(item, dict) and item.get("id") == candidate_id), None)
            for candidate_id in candidate_ids
        ]
        if not candidate_ids or any(candidate is None for candidate in candidates):
            raise ValueError("verified shot selected candidate is invalid")
        normalized = shot.get("normalized")
        program = _range(shot.get("program_range"))
        if not isinstance(normalized, dict) or not isinstance(normalized.get("path"), str) or not normalized["path"].strip() or _candidate_path(Path(".").resolve(), normalized["path"]) is None:
            raise ValueError("verified shot normalized path is invalid")
        digest = normalized.get("sha256")
        if not _is_sha256(digest):
            raise ValueError("verified shot normalized SHA-256 is invalid")
        if inset_enabled and verification.get("composition_sha256") != canonical_sha256(
                normalized.get("composition")):
            raise ValueError("speaker inset verification composition SHA-256 is stale")
        if "source_path" in normalized and len(candidates) == 1 and normalized["source_path"] != candidates[0].get("cache_path"):
            raise ValueError("verified shot normalized source path does not match selected candidate")
        if "source_paths" in normalized and normalized["source_paths"] != [candidate.get("cache_path") for candidate in candidates]:
            raise ValueError("verified shot normalized source paths do not match selected candidates")
        if not program or program[1] <= program[0]:
            raise ValueError("verified shot program range is invalid")
        overlays.append({"kind": "overlay", "asset": normalized["path"], "start_s": program[0], "duration_s": program[1] - program[0]})
    if overlays != sorted(overlays, key=lambda item: item["start_s"]):
        raise ValueError("verified shots must be chronological")
    return overlays


def register_operation(project, plan, *, plan_path="b-roll/broll-plan.json", report_path=None):
    """Register verified overlays, or finalize their completed visual review in place."""
    result = copy.deepcopy(project)
    if not isinstance(result, dict) or not isinstance(result.get("operations"), list) or any(not isinstance(item, dict) for item in result.get("operations", [])):
        raise ValueError("project operations must be a list of objects")
    if "render" in result and not isinstance(result["render"], dict):
        raise ValueError("project render must be an object")
    sequence, nodes = _project_parts(result)
    dependencies = active_dependencies(result)
    expected_based_on = {item: nodes[item]["revision"] for item in dependencies}
    if not isinstance(plan, dict) or plan.get("dependencies") != dependencies:
        raise ValueError("plan dependencies do not match current dependencies")
    if plan.get("based_on") != expected_based_on:
        raise ValueError("plan based_on does not match current revisions")
    overlays = _verified_overlays(plan)
    old = [item for item in result["operations"] if item.get("id") == "b-roll"]
    if not overlays:
        removed = bool(old)
        result["operations"] = [item for item in result["operations"] if item.get("id") != "b-roll"]
        if isinstance(result.get("sequences"), dict):
            for value in result["sequences"].values():
                if not isinstance(value, dict) or not isinstance(value.get("operations"), list):
                    continue
                cleaned = [item for item in value["operations"] if item != "b-roll"]
                removed = removed or len(cleaned) != len(value["operations"])
                value["operations"] = cleaned
        if removed:
            result.setdefault("render", {})["status"] = "draft"
        return result
    common = {
        "id": "b-roll", "skill": "video-add-b-roll",
        "depends_on": dependencies, "based_on": copy.deepcopy(expected_based_on),
        "plan": plan_path, "outputs": [item["asset"] for item in overlays],
        "target": {"sequence": result["active_sequence"], "scope": "b-roll"},
        "effects": {"changes_timeline": False, "changes_geometry": False, "changes_video_pixels": True, "changes_audio": False, "adds_track": "b-roll"},
        "render": overlays,
    }
    if "visual_review" in plan:
        visual_review_errors = _visual_review_errors(plan)
        if visual_review_errors:
            raise ValueError("; ".join(visual_review_errors))
        completed_report = "../" + plan["visual_review"]["report"]["path"]
        if report_path is not None and report_path != completed_report:
            raise ValueError("report_path does not match completed visual review")
        if len(old) != 1:
            raise ValueError("completed visual review requires one matching registered operation")
        existing = old[0]
        for key, value in common.items():
            if existing.get(key) != value:
                raise ValueError("completed visual review does not match registered operation")
        references = sum(
            value["operations"].count("b-roll") for value in result["sequences"].values()
            if isinstance(value, dict) and isinstance(value.get("operations"), list)
        )
        if sequence["operations"].count("b-roll") != 1 or references != 1:
            raise ValueError("completed visual review requires one B-roll sequence reference")
        pending_check = {"status": "pending", "report": "../review/03-b-roll/b-roll-summary.md"}
        completed_check = {"status": "pass", "report": completed_report}
        if existing.get("status") == "verified" and existing.get("check") == completed_check:
            return result
        if existing.get("status") != "approved" or existing.get("check") != pending_check:
            raise ValueError("registered operation must be approved with pending machine summary")
        existing["status"] = "verified"
        existing["check"] = completed_check
        return result

    machine_report = "../review/03-b-roll/b-roll-summary.md"
    if report_path is not None and report_path != machine_report:
        raise ValueError("report_path does not match pending machine verification")
    result["operations"] = [item for item in result["operations"] if item.get("id") != "b-roll"]
    if isinstance(result.get("sequences"), dict):
        for value in result["sequences"].values():
            if not isinstance(value, dict) or not isinstance(value.get("operations"), list):
                continue
            cleaned = [item for item in value["operations"] if item != "b-roll"]
            value["operations"] = cleaned
    sequence, _ = _project_parts(result)
    revision = max((item.get("revision", 0) for item in old), default=0) + 1
    operation = {
        **common, "revision": revision, "status": "approved",
        "check": {"status": "pending", "report": machine_report},
    }
    result["operations"].append(operation)
    ids = sequence["operations"]
    anchors = [index for index, item in enumerate(ids) if item in {"cut", "color-grade"}]
    if anchors:
        index = anchors[-1] + 1
    else:
        index = next((index for index, item in enumerate(ids) if item in {"graphic-motion", "content-cards", "captions"}), len(ids))
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
        frame_duration = timeline_frame_duration(timeline)
    except ValueError as exc:
        errors.append(str(exc))
        frame_duration = None
    timeline_duration = _strict_finite_number(timeline.get("program_duration_s"))
    if timeline_duration is _INVALID_NUMBER or timeline_duration < 0:
        errors.append("timeline program_duration_s is invalid")
        timeline_duration = None
    plan_duration = _strict_finite_number(plan.get("program_duration_s"))
    if plan_duration is _INVALID_NUMBER:
        errors.append("plan program_duration_s is required")
    else:
        if timeline_duration is not None and plan_duration != timeline_duration: errors.append("plan program_duration_s does not match timeline")
    brief = plan.get("brief")
    if not isinstance(brief, dict): errors.append("brief must be an object")
    elif brief.get("density") != "dynamic-social": errors.append("brief density must be dynamic-social")
    style = plan.get("speaker_inset_style")
    if style is not None:
        errors.extend(speaker_inset.style_errors(style))
    duration = timeline_duration if timeline_duration is not None else 0
    source_duration = _strict_finite_number(timeline.get("source_duration_s"))
    if source_duration is _INVALID_NUMBER or source_duration < 0:
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
            if (frame_duration is not None
                    and (not _frame_aligned(program[0], frame_duration)
                         or not _frame_aligned(program[1], frame_duration))):
                errors.append(f"{shot_id} program range must align to timeline frames")
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
        if not isinstance(status, str) or status not in ("planned", "candidates_ready", "composite_pending", "selected", "normalized", "verified", "skipped"): errors.append(f"{shot_id} status is invalid")
        elif status in {"planned", "candidates_ready", "skipped"} and selected is not None: errors.append(f"{shot_id} {status} shot must not select a candidate")
        elif status in {"composite_pending", "selected", "normalized", "verified"} and not isinstance(selected, dict): errors.append(f"{shot_id} {status} shot requires a selection")
        elif status in {"composite_pending", "selected", "normalized", "verified"}:
            selected_ids = selected_candidate_ids(selected)
            selected_candidates = [
                next((item for item in candidates
                      if isinstance(item, dict) and item.get("id") == candidate_id), None)
                for candidate_id in selected_ids
            ]
            candidate = selected_candidates[0] if len(selected_candidates) == 1 else None
            if not selected_ids or any(item is None for item in selected_candidates):
                errors.append(f"{shot_id} selected candidate does not belong to shot")
            elif "segments" in selected:
                if frame_duration is not None:
                    try:
                        selection_details(shot, candidates, timeline)
                    except ValueError as exc:
                        errors.append(f"{shot_id} {status} video {exc}")
            elif candidate is not None and candidate.get("media_type") == "video":
                if not _valid_source_trim(selected.get("source_trim"), candidate): errors.append(f"{shot_id} {status} video requires a valid source_trim")
            elif candidate is not None and candidate.get("media_type") == "image" and not _valid_ken_burns(selected.get("ken_burns")):
                errors.append(f"{shot_id} {status} image requires a non-empty ken_burns")
                errors.append(f"{shot_id} {status} image requires a valid ken_burns direction")
        review_default = shot.get("review_default")
        if review_default is not None:
            if not isinstance(review_default, dict) or review_default.get("decision") not in ("select", "skip"):
                errors.append(f"{shot_id} review_default is invalid")
            elif review_default.get("decision") == "select":
                segments = review_default.get("segments")
                review_candidate_ids = (
                    [segment.get("candidate_id") for segment in segments]
                    if isinstance(segments, list) and all(isinstance(segment, dict) for segment in segments)
                    else []
                )
                selected_candidates = [
                    next((item for item in candidates
                          if isinstance(item, dict) and item.get("id") == candidate_id), None)
                    for candidate_id in review_candidate_ids
                ]
                if (not review_candidate_ids or any(candidate is None or candidate.get("media_type") != "video"
                                                    for candidate in selected_candidates)):
                    errors.append(f"{shot_id} review_default candidate is invalid")
                elif frame_duration is not None:
                    default_shot = copy.deepcopy(shot)
                    default_shot["selected"] = {"segments": copy.deepcopy(segments)}
                    try:
                        selection_details(default_shot, candidates, timeline)
                    except ValueError as exc:
                        errors.append(f"{shot_id} review_default {exc}")
        if status in ("normalized", "verified"):
            normalized = shot.get("normalized")
            if not isinstance(normalized, dict):
                errors.append(f"{shot_id} normalized record is required")
            else:
                if not isinstance(normalized.get("path"), str) or not normalized["path"].strip():
                    errors.append(f"{shot_id} normalized path is invalid")
                if not _is_sha256(normalized.get("sha256")):
                    errors.append(f"{shot_id} normalized SHA-256 is invalid")
                errors.extend(speaker_inset.normalized_composition_errors(plan, shot))
        elif "normalized" in shot:
            errors.append(f"{shot_id} {status} shot must not carry normalized")
        if status == "verified":
            verification = shot.get("verification")
            if not isinstance(verification, dict) or verification.get("status") != "pass":
                errors.append(f"{shot_id} verified verification must pass")
            elif (speaker_inset.style_enabled(style)
                  and verification.get("composition_sha256") != canonical_sha256(
                      shot.get("normalized", {}).get("composition"))):
                errors.append(f"{shot_id} speaker inset verification composition SHA-256 is stale")
        elif "verification" in shot:
            errors.append(f"{shot_id} {status} shot must not carry verification")
    composite_pending = any(
        isinstance(shot, dict) and shot.get("status") == "composite_pending"
        for shot in shots
    )
    selection = plan.get("selection")
    if composite_pending and not speaker_inset.style_enabled(style):
        errors.append("composite_pending shots require enabled speaker_inset_style")
    if composite_pending or selection is not None:
        if not isinstance(selection, dict) or selection.get("status") != "approved":
            errors.append("composite_pending shots require an approved selection")
        elif selection.get("submission_intent") != "approve_selection":
            errors.append("approved selection submission_intent is invalid")
        elif selection.get("approval_scope") != "b-roll-selection":
            errors.append("approved selection scope is invalid")
        elif selection.get("consumed") is not True:
            errors.append("approved selection review page must be consumed")
        elif not _is_sha256(selection.get("sha256")):
            errors.append("approved selection SHA-256 is invalid")
        elif selection.get("path") != "b-roll/broll-selection.json":
            errors.append("approved selection path is invalid")
        elif verify_files and project_root:
            selection_path = Path(project_root).resolve() / "work" / selection["path"]
            if not selection_path.is_file():
                errors.append("approved selection file is missing")
            elif sha256_file(selection_path) != selection["sha256"]:
                errors.append("approved selection SHA-256 is stale")
            else:
                try:
                    selection_receipt = projectlib.load_json(selection_path)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("approved selection receipt is invalid")
                else:
                    for field in (
                            "status", "submission_intent", "approval_scope",
                            "review_id", "style_sha256"):
                        if selection_receipt.get(field) != selection.get(field):
                            errors.append(f"approved selection {field} does not match receipt")
                    source_review = selection_receipt.get("source_review")
                    if not isinstance(source_review, dict) or source_review.get("consumed") is not True:
                        errors.append("approved selection source review is invalid")
                    elif source_review.get("legacy_page_unbound") is True:
                        if selection.get("legacy_submission_intent") != "prepare_composite":
                            errors.append("unbound selection page requires legacy receipt")
                    else:
                        page_path = Path(project_root).resolve() / str(source_review.get("path", ""))
                        try:
                            page_path.resolve().relative_to(
                                (Path(project_root).resolve() / "review/03-b-roll").resolve()
                            )
                        except ValueError:
                            errors.append("approved selection review page path is invalid")
                        else:
                            page_sha256 = source_review.get("sha256")
                            if not _is_sha256(page_sha256):
                                errors.append("approved selection review page SHA-256 is invalid")
                            elif selection.get("review_page_sha256") != page_sha256:
                                errors.append("approved selection review page SHA-256 does not match")
                            elif not page_path.is_file() or sha256_file(page_path) != page_sha256:
                                errors.append("approved selection review page is missing or stale")
    errors.extend(_speaker_artifact_binding_errors(plan, shots))
    errors.extend(speaker_inset.artifact_errors(
        plan, timeline, transcript,
        project_root=project_root, verify_files=verify_files,
    ))
    for start, end, shot_id in sorted(ranges):
        for previous_start, previous_end, previous_id in ranges:
            if previous_id != shot_id and previous_start < end and start < previous_end:
                errors.append(f"{shot_id} program range overlaps {previous_id}"); break
    errors.extend(_candidate_ranking_errors(
        plan, shots, project_root=project_root, verify_files=verify_files
    ))
    errors.extend(_review_errors(plan, shots))
    errors.extend(_ordinary_source_review_errors(
        plan, project_root=project_root, verify_files=verify_files,
    ))
    if "visual_review" in plan:
        errors.extend(_visual_review_errors(
            plan, project_root=project_root, verify_files=verify_files
        ))
    project_operations = None
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
        project_operations = operations
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
        try:
            required = active_dependencies(project)
        except ValueError as exc:
            errors.append(str(exc))
            required = []
        if dependencies != required: errors.append("plan dependencies do not match current dependencies")
        if set(dependencies) != set(based_on): errors.append("based_on does not match dependencies")
        for dependency in dependencies:
            expected = based_on.get(dependency)
            if not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0:
                errors.append(f"based_on {dependency} revision must be a positive integer")
            current = operations.get(dependency, {}).get("revision")
            if current != expected: errors.append(f"based_on {dependency} revision is stale: expected {expected}, current {current}")
    if verify_files and not project_root: errors.append("verify_files requires project_root")
    if project_root:
        root = Path(project_root).resolve()
        hashes = plan.get("input_hashes", {})
        for key, path in (("transcript_sha256", Path(project_root) / "work/understand/transcript.json"), ("timeline_sha256", Path(project_root) / "work/timeline.json")):
            if not path.is_file(): errors.append(f"{key.split('_')[0]} file is missing")
            elif not isinstance(hashes, dict) or hashes.get(key) != sha256_file(path): errors.append(f"{key.split('_')[0]} SHA-256 is stale")
        dependencies = plan.get("dependencies", [])
        color_grade_active = isinstance(dependencies, list) and "color-grade" in dependencies
        if color_grade_active:
            grade_path = None
            if project_operations is None:
                grade_path = root / "work/color-grade/grade-plan.json"
            else:
                operation = project_operations.get("color-grade")
                render = operation.get("render") if isinstance(operation, dict) else None
                grade_value = render.get("plan") if isinstance(render, dict) else None
                if not isinstance(grade_value, str) or not grade_value.strip():
                    errors.append("color-grade operation render.plan is required")
                else:
                    raw_grade = Path(grade_value)
                    grade_path = (raw_grade if raw_grade.is_absolute() else root / "work" / raw_grade).resolve()
                    try:
                        grade_path.relative_to(root)
                    except ValueError:
                        errors.append("grade plan path escapes project root")
                        grade_path = None
            if not isinstance(hashes, dict) or not _is_sha256(hashes.get("grade_plan_sha256")):
                errors.append("grade plan SHA-256 is required")
            if not isinstance(hashes, dict) or not _is_sha256(hashes.get("selected_lut_sha256")):
                errors.append("selected LUT SHA-256 is required")
            grade_plan = None
            if grade_path is not None:
                if not grade_path.is_file():
                    errors.append("grade plan file is missing")
                else:
                    if isinstance(hashes, dict) and _is_sha256(hashes.get("grade_plan_sha256")) and hashes["grade_plan_sha256"] != sha256_file(grade_path):
                        errors.append("grade plan SHA-256 is stale")
                    try:
                        grade_plan = json.loads(grade_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        errors.append("grade plan is invalid JSON")
            if grade_plan is not None:
                if not isinstance(grade_plan, dict):
                    errors.append("grade plan must be an object")
                else:
                    if grade_plan.get("schema_version") != 1:
                        errors.append("grade plan schema_version must be 1")
                    selected_lut = grade_plan.get("selected_lut")
                    if not isinstance(selected_lut, str) or not selected_lut.strip():
                        errors.append("grade plan selected_lut is required")
                    else:
                        raw_lut = Path(selected_lut)
                        lut_path = (raw_lut if raw_lut.is_absolute() else grade_path.parent / raw_lut).resolve()
                        try:
                            lut_path.relative_to(root)
                        except ValueError:
                            errors.append("selected LUT path escapes project root")
                        else:
                            if not lut_path.is_file():
                                errors.append("selected LUT file is missing")
                            elif isinstance(hashes, dict) and _is_sha256(hashes.get("selected_lut_sha256")) and hashes["selected_lut_sha256"] != sha256_file(lut_path):
                                errors.append("selected LUT SHA-256 is stale")
    return errors


def _mapped_word_records(transcript, timeline):
    try:
        mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError) as exc:
        raise ValueError("transcript cannot be mapped to timeline") from exc
    records = []
    segments = mapped.get("segments") if isinstance(mapped, dict) else None
    if not isinstance(segments, list):
        raise ValueError("mapped transcript segments are invalid")
    for segment in segments:
        words = segment.get("words") if isinstance(segment, dict) else None
        if not isinstance(words, list):
            continue
        for word in words:
            if not isinstance(word, dict):
                continue
            source = _range(word.get("source_range"))
            program = _range(word.get("program_range"))
            if (isinstance(word.get("word"), str) and isinstance(word.get("clip_id"), str)
                    and source and program):
                records.append(copy.deepcopy(word))
    return records


def revision_program_bounds(plan, timeline, shot_id):
    shots = plan.get("shots") if isinstance(plan, dict) else None
    if not isinstance(shots, list):
        raise ValueError("plan shots must be a list")
    index = next((index for index, shot in enumerate(shots)
                  if isinstance(shot, dict) and shot.get("id") == shot_id), None)
    if index is None:
        raise ValueError(f"unknown shot: {shot_id}")
    frame = timeline_frame_duration(timeline)
    duration = _strict_finite_number(timeline.get("program_duration_s"))
    original = _range(shots[index].get("program_range"))
    if duration is _INVALID_NUMBER or duration <= 0 or not original:
        raise ValueError("timeline or shot program range is invalid")
    previous_end = 0.0
    if index:
        previous = _range(shots[index - 1].get("program_range"))
        if not previous:
            raise ValueError("previous shot program range is invalid")
        previous_end = previous[1]
    next_start = duration
    if index + 1 < len(shots):
        following = _range(shots[index + 1].get("program_range"))
        if not following:
            raise ValueError("next shot program range is invalid")
        next_start = following[0]
    return {
        "start_s": {
            "min": max(0.0, original[0] - 2.0, previous_end),
            "max": min(duration - frame, original[0] + 2.0, next_start - frame),
        },
        "end_s": {
            "min": max(frame, original[1] - 2.0, previous_end + frame),
            "max": min(duration, original[1] + 2.0, next_start),
        },
    }


def _frame_aligned(value, frame):
    number = _strict_finite_number(value)
    if number is _INVALID_NUMBER:
        return False
    return abs(number / frame - round(number / frame)) <= RANGE_EPSILON


def validate_revision_request(plan, request, timeline, transcript):
    """Validate a request without mutating the plan or creating approval state."""
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if not isinstance(request, dict):
        return ["revision request must be an object"]
    if request.get("submission_intent") != "request_revision":
        errors.append("submission_intent must be request_revision")
    if request.get("explicit_user_action") is not True:
        errors.append("revision request requires explicit_user_action true")
    if not _is_uuid(request.get("review_id")):
        errors.append("review_id must be a UUID")
    if not _valid_timestamp(request.get("timestamp")):
        errors.append("revision request timestamp is invalid")
    notes = request.get("revision_notes", "")
    if not isinstance(notes, str):
        errors.append("revision_notes must be a string")
    elif not notes.strip():
        errors.append("revision_notes must be non-empty")
    input_hashes = plan.get("input_hashes")
    if not isinstance(input_hashes, dict):
        errors.append("plan input_hashes must be an object")
        input_hashes = {}
    expected_bindings = {
        "plan_sha256": canonical_sha256(review_subject(plan)),
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": input_hashes.get("review_video_sha256"),
    }
    for field, expected in expected_bindings.items():
        if request.get(field) != expected:
            errors.append(f"{field} does not match current review artifacts")
    try:
        frame = timeline_frame_duration(timeline)
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    entries = request.get("shots")
    plan_shots = plan.get("shots")
    if not isinstance(entries, list):
        return errors + ["revision request shots must be a list"]
    if not isinstance(plan_shots, list):
        return errors + ["plan shots must be a list"]
    if any(not isinstance(entry, dict) for entry in entries):
        return errors + ["revision request shot must be an object"]
    ids = [entry.get("id") for entry in entries]
    plan_ids = [shot.get("id") for shot in plan_shots if isinstance(shot, dict)]
    ids_valid = all(isinstance(shot_id, str) and shot_id.strip() for shot_id in ids)
    if not ids_valid:
        errors.append("revision request shot id is required")
    if ids_valid and len(ids) != len(set(ids)):
        errors.append("revision request shot ids must be unique")
    if ids_valid and sorted(ids) != sorted(plan_ids, key=str):
        errors.append("revision request shots do not match plan shots")
    entries_by_id = {entry.get("id"): entry for entry in entries}
    requested_ranges = []
    for shot in plan_shots:
        if not isinstance(shot, dict) or shot.get("id") not in entries_by_id:
            continue
        shot_id = shot["id"]
        entry = entries_by_id[shot_id]
        decision = entry.get("decision")
        if decision not in ("select", "skip"):
            errors.append(f"{shot_id} decision must be select or skip")
            continue
        if shot.get("status") == "skipped" and decision != "skip":
            errors.append(f"{shot_id} was already skipped and requires decision skip")
        if decision == "skip":
            continue
        requested = _range(entry.get("requested_program_range"))
        if not requested or requested[1] <= requested[0]:
            errors.append(f"{shot_id} requested_program_range is invalid")
            continue
        bounds = revision_program_bounds(plan, timeline, shot_id)
        if (requested[0] < bounds["start_s"]["min"] - RANGE_EPSILON
                or requested[0] > bounds["start_s"]["max"] + RANGE_EPSILON
                or requested[1] < bounds["end_s"]["min"] - RANGE_EPSILON
                or requested[1] > bounds["end_s"]["max"] + RANGE_EPSILON):
            errors.append(f"{shot_id} requested program range is outside allowed bounds")
        if requested[1] - requested[0] + RANGE_EPSILON < frame:
            errors.append(f"{shot_id} requested program range must be at least one timeline frame")
        if not _frame_aligned(requested[0], frame) or not _frame_aligned(requested[1], frame):
            errors.append(f"{shot_id} requested program range must align to timeline frames")
        requested_ranges.append((requested[0], requested[1], shot_id))
        mapped_ranges = _timeline_source_ranges(requested, timeline)
        if not mapped_ranges:
            errors.append(f"{shot_id} requested program range cannot be mapped to source")
        segments = entry.get("segments")
        candidates = shot.get("candidates")
        errors.extend(f"{shot_id} {error}" for error in _canonical_segments_errors(
            segments, candidates,
            {"start_s": requested[0], "end_s": requested[1]}, frame,
        ))
    for index, (start, end, shot_id) in enumerate(sorted(requested_ranges)):
        for other_start, other_end, other_id in sorted(requested_ranges)[index + 1:]:
            if other_start < end - RANGE_EPSILON and start < other_end - RANGE_EPSILON:
                errors.append(f"{shot_id} requested program range overlaps {other_id}")
    return errors


def rebuild_plan_from_revision(plan, request, timeline, transcript):
    """Return an unapproved revised proposal after validating the bound request."""
    errors = validate_revision_request(plan, request, timeline, transcript)
    if errors:
        raise ValueError("invalid revision request: " + "; ".join(errors))
    result = copy.deepcopy(plan)
    entries = {entry["id"]: entry for entry in request["shots"]}
    words = _mapped_word_records(transcript, timeline)
    result["decision"] = None
    result["review"] = None
    for key in (
        "candidate_ranking", "selection", "speaker_inset", "review_status",
        "visual_review",
    ):
        result.pop(key, None)
    presentation = result.get("presentation")
    if isinstance(presentation, dict):
        presentation.setdefault(
            "carried_from_plan_sha256",
            canonical_sha256(presentation_subject(plan)),
        )
    for shot in result["shots"]:
        entry = entries[shot["id"]]
        shot.pop("normalized", None)
        shot.pop("verification", None)
        if entry["decision"] == "skip":
            shot["selected"] = None
            shot["status"] = "skipped"
            shot.pop("review_default", None)
            continue
        requested = _range(entry["requested_program_range"])
        shot["program_range"] = {"start_s": requested[0], "end_s": requested[1]}
        shot["source_ranges"] = _timeline_source_ranges(requested, timeline)
        inside = [word for word in words
                  if (_range(word.get("program_range"))[0] >= requested[0] - RANGE_EPSILON
                      and _range(word.get("program_range"))[1] <= requested[1] + RANGE_EPSILON)]
        if not inside:
            raise ValueError(f"{shot['id']} revised program range contains no complete transcript word")
        shot["transcript_evidence"] = {"words": inside}
        shot["review_default"] = {
            "decision": "select",
            "segments": copy.deepcopy(entry["segments"]),
        }
        shot["selected"] = None
        shot["status"] = "candidates_ready"
    validation = validate_plan(result, timeline, transcript)
    if validation:
        raise ValueError("rebuilt plan is invalid: " + "; ".join(validation))
    return result


def _candidate_review_page(project_root, review_id, *, presentation_mode,
                           expected_bindings, timeline):
    root = Path(project_root).resolve()
    page = root / "review/03-b-roll" / f"b-roll-review-{review_id}.html"
    if not page.is_file():
        raise ValueError("immutable candidate review page is missing")
    try:
        document = page.read_text(encoding="utf-8")
        match = REVIEW_PAGE_PAYLOAD_RE.search(document)
        if match is None:
            raise ValueError
        payload = json.loads(base64.b64decode(match.group(1), validate=True))
    except (OSError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("immutable candidate review page payload is invalid") from exc
    expected_mode = "selection" if presentation_mode == "speaker-inset" else "standard"
    expected_page_bindings = {
        "review_id": review_id,
        "review_mode": expected_mode,
        **expected_bindings,
    }
    if (not isinstance(payload, dict)
            or any(payload.get(field) != expected
                   for field, expected in expected_page_bindings.items())
            or not isinstance(payload.get("timeline"), dict)
            or payload["timeline"].get("fps") != timeline.get("fps")):
        raise ValueError("immutable candidate review page binding is invalid")
    return page


def _preflight_page_approval(plan, review_id, *, timeline, transcript,
                             project_root, presentation_mode):
    if not isinstance(timeline, dict):
        raise ValueError("explicit page approval requires the canonical timeline")
    if not isinstance(transcript, dict):
        raise ValueError("explicit page approval requires the canonical transcript")
    if project_root is None:
        raise ValueError("explicit page approval requires the project root")
    root = Path(project_root).resolve()
    for name, value, path in (
            ("timeline", timeline, root / "work/timeline.json"),
            ("transcript", transcript, root / "work/understand/transcript.json")):
        try:
            canonical = projectlib.load_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"canonical {name} file is missing or invalid") from exc
        if value != canonical:
            raise ValueError(f"canonical {name} does not match project file")
    presentation_validation = presentation_errors(
        plan, project_root=root, required=True,
    )
    if presentation_validation:
        raise ValueError(
            "invalid presentation decision: " + "; ".join(presentation_validation)
        )
    if plan["presentation"]["mode"] != presentation_mode:
        raise ValueError(
            f"explicit page approval requires {presentation_mode} presentation"
        )
    errors = validate_plan(
        plan, timeline, transcript, project_root=root, verify_files=True,
    )
    if errors:
        raise ValueError("invalid approval source plan: " + "; ".join(errors))
    expected_bindings = {
        "plan_sha256": canonical_sha256(review_subject(plan)),
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
    }
    page = _candidate_review_page(
        root, review_id, presentation_mode=presentation_mode,
        expected_bindings=expected_bindings, timeline=timeline,
    )
    return root, {
        "review_id": review_id,
        "path": page.relative_to(root).as_posix(),
        "sha256": sha256_file(page),
        "consumed": True,
    }


def _apply_exact_entries(result, entries, *, timeline, transcript=None,
                         explicit_intent, target_status, action):
    shots = {shot.get("id"): shot for shot in result["shots"]}
    seen = set()
    for entry in entries:
        shot_id = entry.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError("review shot id is required")
        if shot_id in seen:
            raise ValueError(f"duplicate review shot id: {shot_id}")
        seen.add(shot_id)
        if shot_id not in shots:
            raise ValueError(f"review has unknown shots: {shot_id}")
    missing = sorted(set(shots) - seen)
    if missing:
        raise ValueError("review is missing shots: " + ", ".join(missing))

    entries_by_id = {entry["id"]: entry for entry in entries}
    approved_ranges = {}
    approved_source_ranges = {}
    approved_words = {}
    editable_approval = explicit_intent and transcript is not None
    if editable_approval:
        if not isinstance(timeline, dict):
            raise ValueError("explicit page approval requires the canonical timeline")
        if not isinstance(transcript, dict):
            raise ValueError("explicit page approval requires the canonical transcript")
        frame = timeline_frame_duration(timeline)
        mapped_words = _mapped_word_records(transcript, timeline)
        for shot in result["shots"]:
            entry = entries_by_id[shot["id"]]
            if entry.get("decision") != "select":
                continue
            program = _range(entry.get("program_range"))
            if not program or program[1] <= program[0]:
                raise ValueError(f"{shot['id']} approve program_range is invalid")
            bounds = revision_program_bounds(result, timeline, shot["id"])
            if (program[0] < bounds["start_s"]["min"] - RANGE_EPSILON
                    or program[0] > bounds["start_s"]["max"] + RANGE_EPSILON
                    or program[1] < bounds["end_s"]["min"] - RANGE_EPSILON
                    or program[1] > bounds["end_s"]["max"] + RANGE_EPSILON):
                raise ValueError(f"{shot['id']} approved program range is outside allowed bounds")
            if program[1] - program[0] + RANGE_EPSILON < frame:
                raise ValueError(
                    f"{shot['id']} approved program range must be at least one timeline frame"
                )
            if not _frame_aligned(program[0], frame) or not _frame_aligned(program[1], frame):
                raise ValueError(
                    f"{shot['id']} approved program range must align to timeline frames"
                )
            source_ranges = _timeline_source_ranges(program, timeline)
            if not source_ranges:
                raise ValueError(
                    f"{shot['id']} approved program range cannot be mapped to source"
                )
            words = [
                copy.deepcopy(word) for word in mapped_words
                if (_range(word.get("program_range"))[0] >= program[0] - RANGE_EPSILON
                    and _range(word.get("program_range"))[1] <= program[1] + RANGE_EPSILON)
            ]
            if not words:
                raise ValueError(
                    f"{shot['id']} approved program range requires a complete transcript word"
                )
            approved_ranges[shot["id"]] = {
                "start_s": program[0], "end_s": program[1],
            }
            approved_source_ranges[shot["id"]] = source_ranges
            approved_words[shot["id"]] = words
        ordered_ranges = sorted(
            (_range(value)[0], _range(value)[1], shot_id)
            for shot_id, value in approved_ranges.items()
        )
        for index, (start, end, shot_id) in enumerate(ordered_ranges):
            for other_start, other_end, other_id in ordered_ranges[index + 1:]:
                if other_start < end - RANGE_EPSILON and start < other_end - RANGE_EPSILON:
                    raise ValueError(
                        f"{shot_id} approved program range overlaps {other_id}"
                    )

    selected_hashes = []
    decision_skipped_ids = []
    for shot in result["shots"]:
        entry = entries_by_id[shot["id"]]
        decision = entry.get("decision")
        if decision not in ("select", "skip"):
            raise ValueError(f"{shot['id']} decision must be select or skip")
        if shot.get("status") == "skipped" and decision != "skip":
            raise ValueError(f"{shot['id']} was already skipped and requires decision skip")
        shot.pop("normalized", None)
        shot.pop("verification", None)
        if editable_approval:
            shot.pop("review_default", None)
        if decision == "skip":
            if (explicit_intent and not editable_approval
                    and isinstance(shot.get("review_default"), dict)
                    and shot["review_default"].get("decision") != "skip"):
                raise ValueError(
                    f"{shot['id']} {action} does not match the exact review default"
                )
            if shot.get("status") != "skipped":
                decision_skipped_ids.append(shot["id"])
            shot["selected"], shot["status"] = None, "skipped"
            continue

        segments = entry.get("segments")
        if segments is not None and (
                not isinstance(segments, list) or not 1 <= len(segments) <= 3):
            raise ValueError(f"{shot['id']} select requires 1-3 segments")
        candidate_ids = (
            [segment.get("candidate_id") for segment in segments if isinstance(segment, dict)]
            if isinstance(segments, list) else [entry.get("candidate_id")]
        )
        candidates = shot.get("candidates", [])
        selected_candidates = [
            next((item for item in candidates
                  if isinstance(item, dict) and item.get("id") == candidate_id), None)
            for candidate_id in candidate_ids
        ]
        if (not candidate_ids or len(candidate_ids) != len(segments or candidate_ids)
                or any(candidate is None for candidate in selected_candidates)):
            raise ValueError(f"{shot['id']} selected candidate does not belong to shot")
        candidate = selected_candidates[0]
        if editable_approval:
            shot["program_range"] = copy.deepcopy(approved_ranges[shot["id"]])
            shot["source_ranges"] = copy.deepcopy(approved_source_ranges[shot["id"]])
            shot["transcript_evidence"] = {
                "words": copy.deepcopy(approved_words[shot["id"]]),
            }
        elif explicit_intent:
            if not _ranges_equal(entry.get("program_range"), shot.get("program_range")):
                raise ValueError(
                    f"{shot['id']} {action} program_range does not match current review"
                )
            default = shot.get("review_default")
            if isinstance(default, dict):
                actual = {"decision": "select", "segments": copy.deepcopy(segments)}
                if actual != default:
                    raise ValueError(
                        f"{shot['id']} {action} does not match the exact review default"
                    )
        if segments is not None:
            if any(candidate.get("media_type") != "video" for candidate in selected_candidates):
                raise ValueError(f"{shot['id']} canonical segments require a video candidate")
            if not isinstance(timeline, dict):
                raise ValueError("canonical segment approval requires the canonical timeline")
            frame_duration = timeline_frame_duration(timeline)
            segment_errors = _canonical_segments_errors(
                segments, candidates, shot["program_range"], frame_duration,
            )
            if segment_errors:
                raise ValueError(f"{shot['id']} " + "; ".join(segment_errors))
            shot["selected"] = {"segments": copy.deepcopy(segments)}
            shot["status"] = target_status
            selected_hashes.extend(item["sha256"] for item in selected_candidates)
            continue
        option = "source_trim" if candidate.get("media_type") == "video" else "ken_burns"
        if option == "source_trim" and not _valid_source_trim(entry.get(option), candidate):
            raise ValueError(f"{shot['id']} select requires a valid source_trim")
        if option == "ken_burns" and not _valid_ken_burns(entry.get(option)):
            raise ValueError(f"{shot['id']} select requires a valid ken_burns direction")
        shot["selected"] = {
            "candidate_id": candidate["id"], option: copy.deepcopy(entry[option]),
        }
        shot["status"] = target_status
        selected_hashes.append(candidate["sha256"])
    return selected_hashes, decision_skipped_ids


def _approve_selection(plan, selection, *, mode, actor, rationale,
                       project_root, timeline, transcript=None, legacy=False):
    """Apply the exact B-roll content decision before speaker compositing."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    if not isinstance(selection, dict):
        raise ValueError("selection must be an object")
    expected_intent = "prepare_composite" if legacy else "approve_selection"
    if selection.get("submission_intent") != expected_intent:
        raise ValueError(f"submission_intent must be {expected_intent}")
    if not legacy and selection.get("approval_scope") != "b-roll-selection":
        raise ValueError("approval_scope must be b-roll-selection")
    notes = selection.get("revision_notes", "")
    if not isinstance(notes, str) or notes.strip():
        raise ValueError(f"{expected_intent} requires empty revision_notes")
    if not speaker_inset.style_enabled(plan.get("speaker_inset_style")):
        raise ValueError(f"{expected_intent} requires enabled speaker_inset_style")
    style_validation = speaker_inset.style_errors(plan["speaker_inset_style"])
    if style_validation:
        raise ValueError("invalid speaker_inset_style: " + "; ".join(style_validation))
    source_review = None
    if legacy:
        presentation_validation = presentation_errors(
            plan, project_root=project_root, required=True,
        )
        if presentation_validation:
            raise ValueError(
                "invalid presentation decision: " + "; ".join(presentation_validation)
            )
        root = Path(project_root).resolve()

    plan_shots, entries = plan.get("shots"), selection.get("shots")
    if not isinstance(plan_shots, list):
        raise ValueError("plan shots must be a list")
    if not isinstance(entries, list):
        raise ValueError("selection shots must be a list")
    for shot in plan_shots:
        if not isinstance(shot, dict):
            raise ValueError("plan shot must be an object")
        candidates = shot.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError(f"{shot.get('id', '<missing>')} candidates must be a list")
        for candidate in candidates:
            candidate_validation = _candidate_errors(shot.get("id", "<missing>"), candidate)
            if candidate_validation:
                raise ValueError("; ".join(candidate_validation))
    if any(not isinstance(entry, dict) for entry in entries):
        raise ValueError("selection shot must be an object")
    if mode not in ("human", "agent"):
        raise ValueError("mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("actor is required")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("rationale is required")
    rationale = rationale.strip()
    if (not isinstance(selection.get("rationale"), str)
            or selection["rationale"].strip() != rationale):
        raise ValueError("exported rationale does not match selection rationale")
    if not _valid_timestamp(selection.get("timestamp")):
        raise ValueError("selection timestamp is invalid")
    if mode == "human" and selection.get("explicit_user_action") is not True:
        raise ValueError("human selection requires explicit_user_action true")
    rationale_source = selection.get("rationale_source")
    expected_rationale = (
        HUMAN_PREPARE_COMPOSITE_RATIONALE
        if legacy else HUMAN_SELECTION_APPROVAL_RATIONALE
    )
    if mode == "human" and (
            rationale != expected_rationale
            or rationale_source != "review_ui_explicit_action"):
        raise ValueError(
            f"human {expected_intent} requires the explicit review UI action rationale"
        )
    if not _is_uuid(selection.get("review_id")):
        raise ValueError("review_id must be a UUID")
    input_hashes = plan.get("input_hashes")
    if not isinstance(input_hashes, dict):
        raise ValueError("plan input_hashes must be an object")
    expected_bindings = {
        "plan_sha256": canonical_sha256(review_subject(plan)),
        "candidate_manifest_sha256": canonical_sha256(candidate_manifest(plan)),
        "review_video_sha256": input_hashes.get("review_video_sha256"),
    }
    if not _is_sha256(expected_bindings["review_video_sha256"]):
        raise ValueError("plan review_video_sha256 is invalid")
    for field, expected in expected_bindings.items():
        if selection.get(field) != expected:
            raise ValueError(f"{field} does not match current review artifacts")
    if not legacy:
        root, source_review = _preflight_page_approval(
            plan, selection["review_id"], timeline=timeline,
            transcript=transcript, project_root=project_root,
            presentation_mode="speaker-inset",
        )
    if selection.get("timeline_fps") != timeline.get("fps"):
        raise ValueError("timeline_fps does not match canonical timeline")

    result = copy.deepcopy(plan)
    presentation = result.get("presentation")
    if isinstance(presentation, dict):
        presentation.setdefault(
            "carried_from_plan_sha256",
            canonical_sha256(presentation_subject(plan)),
        )
    result["decision"] = None
    result["review"] = None
    result.pop("review_status", None)
    result.pop("visual_review", None)
    result.pop("selection", None)
    selected_hashes, decision_skipped_ids = _apply_exact_entries(
        result, entries, timeline=timeline, transcript=transcript,
        explicit_intent=True,
        target_status="composite_pending", action=expected_intent,
    )
    decisions = _decision_manifest(result["shots"])
    if decisions is None:
        raise ValueError("selection decision manifest cannot be reconstructed")
    if legacy:
        review_page = root / "review/03-b-roll" / f"b-roll-review-{selection['review_id']}.html"
        source_review = {
            "review_id": selection["review_id"],
            "path": review_page.relative_to(root).as_posix(),
            "consumed": True,
        }
        if review_page.is_file():
            source_review["sha256"] = sha256_file(review_page)
        else:
            source_review["legacy_page_unbound"] = True
    receipt = {
        "schema_version": 1,
        "status": "approved",
        "submission_intent": "approve_selection",
        "approval_scope": "b-roll-selection",
        "review_id": selection["review_id"],
        "mode": mode,
        "actor": actor.strip(),
        "rationale": rationale,
        "rationale_source": rationale_source,
        "timestamp": selection["timestamp"],
        "explicit_user_action": selection.get("explicit_user_action") is True,
        **expected_bindings,
        "style_sha256": canonical_sha256(plan["speaker_inset_style"]),
        "timeline_fps": copy.deepcopy(timeline["fps"]),
        "decisions": decisions,
        "decision_skipped_shot_ids": sorted(set(decision_skipped_ids)),
        "selected_asset_sha256": sorted(set(selected_hashes)),
        "source_review": source_review,
    }
    if legacy:
        receipt["legacy_submission_intent"] = "prepare_composite"
    if not legacy:
        validation_result = copy.deepcopy(result)
        validation_result["selection"] = {
            "status": "approved",
            "submission_intent": "approve_selection",
            "approval_scope": "b-roll-selection",
            "consumed": True,
            "path": "b-roll/broll-selection.json",
            "sha256": "0" * 64,
            "review_id": receipt["review_id"],
            "mode": receipt["mode"],
            "actor": receipt["actor"],
            "timestamp": receipt["timestamp"],
            "style_sha256": receipt["style_sha256"],
            "review_page_sha256": source_review["sha256"],
        }
        validation_errors = validate_plan(
            validation_result, timeline, transcript,
        )
        if validation_errors:
            raise ValueError(
                "invalid approved selection: " + "; ".join(validation_errors)
            )
    target = root / "work/b-roll/broll-selection.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=target.parent, suffix=".json", encoding="utf-8") as handle:
            temp = Path(handle.name)
        projectlib.write_json(temp, receipt)
        os.replace(temp, target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    result["selection"] = {
        "status": "approved",
        "submission_intent": "approve_selection",
        "approval_scope": "b-roll-selection",
        "consumed": True,
        "path": "b-roll/broll-selection.json",
        "sha256": sha256_file(target),
        "review_id": receipt["review_id"],
        "mode": receipt["mode"],
        "actor": receipt["actor"],
        "timestamp": receipt["timestamp"],
        "style_sha256": receipt["style_sha256"],
    }
    if "sha256" in source_review:
        result["selection"]["review_page_sha256"] = source_review["sha256"]
    if legacy:
        result["selection"]["legacy_submission_intent"] = "prepare_composite"
    if not any(shot.get("status") == "composite_pending" for shot in result["shots"]):
        result["review_status"] = "approved"
        result["decision"] = {
            "mode": mode,
            "actor": actor.strip(),
            "rationale": rationale,
            "rationale_source": rationale_source,
        }
        if mode == "human":
            result["decision"]["explicit_user_action"] = True
        result["review"] = {
            "status": "approved",
            "submission_intent": "approve_selection",
            "approval_scope": "b-roll-selection",
            "revision_notes": "",
            "review_id": selection["review_id"],
            "mode": mode,
            "actor": actor.strip(),
            "rationale": rationale,
            "rationale_source": rationale_source,
            "timestamp": selection["timestamp"],
            "explicit_user_action": selection.get("explicit_user_action") is True,
            "candidate_manifest_sha256": canonical_sha256(candidate_manifest(result)),
            "review_video_sha256": result["input_hashes"]["review_video_sha256"],
            "timeline_fps": copy.deepcopy(timeline["fps"]),
            "selection_sha256": result["selection"]["sha256"],
            "decisions": decisions,
            "decision_skipped_shot_ids": sorted(set(decision_skipped_ids)),
            "selected_asset_sha256": sorted(set(selected_hashes)),
            "source_review": copy.deepcopy(source_review),
        }
        result["review"]["plan_sha256"] = canonical_sha256(review_subject(result))
    return result


def approve_selection(plan, selection, *, mode, actor, rationale, project_root,
                      timeline, transcript=None):
    """Apply the user's exact B-roll content selection once."""
    return _approve_selection(
        plan, selection, mode=mode, actor=actor, rationale=rationale,
        project_root=project_root, timeline=timeline, transcript=transcript,
    )


def prepare_composite(plan, selection, *, mode, actor, rationale, project_root, timeline):
    """Read a legacy prepare_composite export and emit canonical selection evidence."""
    return _approve_selection(
        plan, selection, mode=mode, actor=actor, rationale=rationale,
        project_root=project_root, timeline=timeline, legacy=True,
    )


def apply_review(plan, review, *, mode, actor, rationale, interaction_path=None,
                 timeline=None, transcript=None, project_root=None):
    if not isinstance(plan, dict): raise ValueError("plan must be an object")
    if not isinstance(review, dict): raise ValueError("review must be an object")
    explicit_intent = "submission_intent" in review
    intent = review.get("submission_intent", "approve")
    if intent not in REVIEW_INTENTS:
        raise ValueError("submission_intent must be approve or request_revision")
    if intent == "request_revision":
        raise ValueError("request_revision must be validated and rebuilt before apply_review")
    if explicit_intent:
        notes = review.get("revision_notes", "")
        if not isinstance(notes, str):
            raise ValueError("revision_notes must be a string")
        if notes.strip():
            raise ValueError("approve requires empty revision_notes")
    plan_shots = plan.get("shots")
    if not isinstance(plan_shots, list): raise ValueError("plan shots must be a list")
    composite_review = (
        speaker_inset.style_enabled(plan.get("speaker_inset_style"))
        and any(
            isinstance(shot, dict) and shot.get("status") == "composite_pending"
            for shot in plan_shots
        )
    )
    if composite_review:
        if "shots" in review:
            raise ValueError("composite review must not include candidate shots")
        entries = []
    else:
        entries = review.get("shots")
        if not isinstance(entries, list):
            raise ValueError("review shots must be a list")
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
    rationale_source = review.get("rationale_source")
    if explicit_intent and mode == "human":
        if rationale != HUMAN_APPROVAL_RATIONALE or rationale_source != "review_ui_explicit_action":
            raise ValueError("new human approve requires the explicit review UI action rationale")
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
    if composite_review:
        if review.get("review_stage") != "composite":
            raise ValueError("speaker inset approval review_stage must be composite")
        if review.get("approval_scope") != "speaker-inset-composite":
            raise ValueError("speaker inset approval_scope must be speaker-inset-composite")
        speaker = plan.get("speaker_inset")
        if not isinstance(speaker, dict):
            raise ValueError("speaker inset approval requires speaker artifacts")
        expected_bindings.update({
            "selection_sha256": plan.get("selection", {}).get("sha256"),
            "analysis_sha256": speaker.get("analysis", {}).get("sha256"),
            "agent_input_sha256": speaker.get("agent_input", {}).get("sha256"),
            "preview_sha256": speaker.get("preview", {}).get("sha256"),
            "clearance_sha256": speaker.get("clearance", {}).get("sha256"),
            "style_sha256": canonical_sha256(plan.get("speaker_inset_style")),
        })
        if any(not _is_sha256(value) for field, value in expected_bindings.items()
               if field not in ("plan_sha256", "candidate_manifest_sha256", "review_video_sha256")):
            raise ValueError("speaker inset approval requires complete current artifact bindings")
    if not isinstance(expected_bindings["review_video_sha256"], str) or len(expected_bindings["review_video_sha256"]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_bindings["review_video_sha256"]):
        raise ValueError("plan review_video_sha256 is invalid")
    for field, expected in expected_bindings.items():
        if review.get(field) != expected:
            raise ValueError(f"{field} does not match current review artifacts")
    source_review = None
    editable_approval = explicit_intent and not composite_review
    if editable_approval:
        root, source_review = _preflight_page_approval(
            plan, review["review_id"], timeline=timeline,
            transcript=transcript, project_root=project_root,
            presentation_mode="ordinary",
        )
    result = copy.deepcopy(plan)
    result.pop("visual_review", None)
    if explicit_intent and review.get("timeline_fps") != timeline.get("fps"):
        raise ValueError("timeline_fps does not match canonical timeline")
    if composite_review:
        selected_hashes = []
        decision_skipped_ids = []
        for shot in result["shots"]:
            if shot.get("status") == "composite_pending":
                shot["status"] = "selected"
                candidates = shot.get("candidates", [])
                for candidate_id in selected_candidate_ids(shot["selected"]):
                    candidate = next(
                        (item for item in candidates
                         if isinstance(item, dict) and item.get("id") == candidate_id),
                        None,
                    )
                    if candidate is None:
                        raise ValueError(f"{shot['id']} locked selection candidate is missing")
                    selected_hashes.append(candidate["sha256"])
            elif shot.get("status") == "skipped":
                decision_skipped_ids.append(shot["id"])
            else:
                raise ValueError("composite approval requires composite_pending or skipped shots")
    else:
        selected_hashes, decision_skipped_ids = _apply_exact_entries(
            result, entries, timeline=timeline,
            transcript=transcript if editable_approval else None,
            explicit_intent=explicit_intent,
            target_status="selected", action="approve",
        )
    decisions = _decision_manifest(result["shots"])
    if decisions is None:
        raise ValueError("review decision manifest cannot be reconstructed")
    result["review_status"] = "approved"
    result["decision"] = {"mode": mode, "actor": actor, "rationale": rationale}
    if rationale_source is not None:
        result["decision"]["rationale_source"] = rationale_source
    if mode == "human": result["decision"]["explicit_user_action"] = True
    result["review"] = {"status": "approved", "review_id": review["review_id"], "mode": mode, "actor": actor, "rationale": rationale, "timestamp": review["timestamp"], **expected_bindings, "decisions": decisions, "decision_skipped_shot_ids": sorted(set(decision_skipped_ids)), "selected_asset_sha256": sorted(set(selected_hashes))}
    if composite_review:
        result["review"].update({
            "review_stage": "composite",
            "approval_scope": "speaker-inset-composite",
        })
    if explicit_intent:
        result["review"].update({"submission_intent": "approve", "revision_notes": ""})
    if source_review is not None:
        result["review"]["source_review"] = source_review
    if rationale_source is not None:
        result["review"]["rationale_source"] = rationale_source
    if mode == "human": result["review"]["explicit_user_action"] = True
    if editable_approval:
        result["review"]["plan_sha256"] = canonical_sha256(review_subject(result))
        validation_errors = validate_plan(result, timeline, transcript)
        if validation_errors:
            raise ValueError("invalid approved review: " + "; ".join(validation_errors))
    if interaction_path:
        target = Path(interaction_path); target.parent.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, dir=target.parent, suffix=".json", encoding="utf-8") as handle: temp = Path(handle.name)
            projectlib.write_json(temp, result["review"]); os.replace(temp, target)
        finally:
            if temp is not None: temp.unlink(missing_ok=True)
    return result
