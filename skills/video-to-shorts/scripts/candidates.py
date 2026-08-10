#!/usr/bin/env python3
"""Validate agent-authored short candidates and generate review previews."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from preview import write_candidates_preview_html, write_candidates_preview_md
from review_gate import sha256_file
from transcript_utils import excerpt_for_range, load_json, overlap_ratio, transcript_duration, write_json


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


SCORE_LIMITS = {
    "hook": 20,
    "completeness": 20,
    "audience_value": 20,
    "emotion_tension": 15,
    "quotability": 15,
    "pace_editability": 10,
}
EVIDENCE_MODES = {"text_visual"}
SCENE_TYPES = {"product_demo", "conversation_interview", "solo_talk", "world_cup"}
ALLOWED_TOP_LEVEL = {"schema_version", "video", "transcript", "producer", "selection", "candidates"}
ALLOWED_CANDIDATE = {
    "candidate_id", "title", "scene_type", "start_time", "end_time", "transcript_excerpt",
    "evidence_mode", "score_breakdown", "warnings", "filler_drop_spans", "visual_observations",
    "visual_risks", "visual_keyframes", "review_status", "metadata",
}


def fail(message):
    raise SystemExit(message)


def require_type(value, expected, path):
    if not isinstance(value, expected):
        fail(f"{path} must be {expected.__name__}")


def validate_score_breakdown(value, path):
    require_type(value, dict, path)
    if set(value) != set(SCORE_LIMITS):
        fail(f"{path} must contain exactly: {', '.join(SCORE_LIMITS)}")
    normalized = {}
    for dimension, maximum in SCORE_LIMITS.items():
        entry = value[dimension]
        require_type(entry, dict, f"{path}.{dimension}")
        if set(entry) != {"score", "reason"}:
            fail(f"{path}.{dimension} must contain exactly score and reason")
        score = entry["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            fail(f"{path}.{dimension}.score must be a number")
        if score < 0 or score > maximum:
            fail(f"{path}.{dimension}.score must be between 0 and {maximum}")
        reason = entry["reason"]
        require_type(reason, str, f"{path}.{dimension}.reason")
        if not reason.strip():
            fail(f"{path}.{dimension}.reason must not be empty")
        normalized[dimension] = {"score": score, "reason": reason.strip()}
    return normalized, sum(item["score"] for item in normalized.values())


def validate_string_list(value, path):
    require_type(value, list, path)
    if any(not isinstance(item, str) for item in value):
        fail(f"{path} must contain only strings")
    return [item.strip() for item in value if item.strip()]


def validate_filler_spans(value, start, end, path):
    require_type(value, list, path)
    spans = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        require_type(item, dict, item_path)
        required = {"type", "start_time", "end_time", "reason", "review_status"}
        if set(item) != required:
            fail(f"{item_path} must contain exactly type, start_time, end_time, reason, review_status")
        if item["type"] != "filler":
            fail(f"{item_path}.type must be filler")
        if item["review_status"] not in ("approved", "rejected"):
            fail(f"{item_path}.review_status must be approved or rejected")
        span_start = item["start_time"]
        span_end = item["end_time"]
        if any(isinstance(number, bool) or not isinstance(number, (int, float)) for number in (span_start, span_end)):
            fail(f"{item_path} times must be numbers")
        if span_start < start or span_end > end or span_end <= span_start:
            fail(f"{item_path} must be a valid range inside the candidate")
        require_type(item["reason"], str, f"{item_path}.reason")
        spans.append({
            "type": "filler", "start_time": span_start, "end_time": span_end,
            "reason": item["reason"].strip(), "review_status": item["review_status"],
        })
    return spans


def validate_metadata(value, path):
    require_type(value, dict, path)
    editorial_reason = value.get("editorial_reason")
    require_type(editorial_reason, str, f"{path}.editorial_reason")
    if not editorial_reason.strip():
        fail(f"{path}.editorial_reason must not be empty")
    return {**value, "editorial_reason": editorial_reason.strip()}


def normalize_candidate(item, index, transcript, transcript_duration_s):
    path = f"candidates[{index}]"
    require_type(item, dict, path)
    unknown = set(item) - ALLOWED_CANDIDATE
    if "score" in item:
        fail(f"{path}.score is not allowed; candidates.py computes score from score_breakdown")
    if unknown:
        fail(f"{path} contains unsupported fields: {', '.join(sorted(unknown))}")
    required = {"candidate_id", "title", "scene_type", "start_time", "end_time", "transcript_excerpt", "evidence_mode", "score_breakdown", "metadata"}
    missing = required - set(item)
    if missing:
        fail(f"{path} missing required fields: {', '.join(sorted(missing))}")
    for field in ("candidate_id", "title", "transcript_excerpt", "evidence_mode", "scene_type"):
        require_type(item[field], str, f"{path}.{field}")
        if not item[field].strip():
            fail(f"{path}.{field} must not be empty")
    if item["scene_type"] not in SCENE_TYPES:
        fail(f"{path}.scene_type must be one of: {', '.join(sorted(SCENE_TYPES))}")
    if item["evidence_mode"] not in EVIDENCE_MODES:
        fail(f"{path}.evidence_mode must be text_visual")
    start = item["start_time"]
    end = item["end_time"]
    if any(isinstance(number, bool) or not isinstance(number, (int, float)) for number in (start, end)):
        fail(f"{path} start_time and end_time must be numbers")
    if start < 0 or end <= start or end > transcript_duration_s:
        fail(f"{path} time range must be within 0-{transcript_duration_s:.3f}s and end after start")
    actual_excerpt = excerpt_for_range(transcript, start, end, max_chars=100000).strip()
    supplied_excerpt = item["transcript_excerpt"].strip()
    if supplied_excerpt != actual_excerpt:
        fail(f"{path}.transcript_excerpt must exactly match transcript words in the candidate time range")
    score_breakdown, score = validate_score_breakdown(item["score_breakdown"], f"{path}.score_breakdown")
    warnings = validate_string_list(item.get("warnings", []), f"{path}.warnings")
    filler_spans = validate_filler_spans(item.get("filler_drop_spans", []), start, end, f"{path}.filler_drop_spans")
    visual_observations = validate_string_list(item.get("visual_observations", []), f"{path}.visual_observations")
    visual_risks = validate_string_list(item.get("visual_risks", []), f"{path}.visual_risks")
    visual_keyframes = validate_string_list(item.get("visual_keyframes", []), f"{path}.visual_keyframes")
    metadata = validate_metadata(item["metadata"], f"{path}.metadata")
    return {
        "candidate_id": item["candidate_id"].strip(), "title": item["title"].strip(),
        "scene_type": item["scene_type"], "start_time": start, "end_time": end,
        "duration": round(end - start, 3), "transcript_excerpt": supplied_excerpt,
        "evidence_mode": item["evidence_mode"], "score_breakdown": score_breakdown, "score": score,
        "warnings": warnings, "filler_drop_spans": filler_spans,
        "visual_observations": visual_observations, "visual_risks": visual_risks,
        "visual_keyframes": visual_keyframes, "review_status": item.get("review_status", "candidate"),
        "metadata": metadata,
    }


def dedupe_candidates(candidates):
    kept = []
    for candidate in sorted(candidates, key=lambda item: item["score"], reverse=True):
        if any(overlap_ratio(candidate, existing) > 0.5 for existing in kept):
            continue
        kept.append(candidate)
    return kept


def validate_selection(value):
    require_type(value, dict, "selection")
    evidence_mode = value.get("evidence_mode")
    require_type(evidence_mode, str, "selection.evidence_mode")
    if evidence_mode not in EVIDENCE_MODES:
        fail("selection.evidence_mode must be text_visual")
    return {**value, "evidence_mode": evidence_mode}


def verify_binding(binding, expected_path, label):
    if not isinstance(binding, dict):
        fail(f"project transcript metadata is missing {label} binding")
    path = Path(binding.get("path", "")).resolve()
    expected = Path(expected_path).resolve()
    if path != expected or not path.is_file():
        fail(f"project {label} binding path is stale")
    stat = path.stat()
    if (
        binding.get("sha256") != sha256_file(path)
        or binding.get("size") != stat.st_size
        or binding.get("modified_ns") != stat.st_mtime_ns
    ):
        fail(f"project {label} changed after transcript preparation")


def validate_project_bindings(project_root, transcript_path, transcript):
    root = Path(project_root).resolve()
    project = projectlib.load_json(root / "work/project.json")
    sequence = project["sequences"][project["active_sequence"]]
    source_video = projectlib.resolve_project_path(root, project["source"]["path"])
    timeline_path = projectlib.resolve_project_path(root, sequence["timeline"])
    source_transcript = root / "work" / "understand" / "transcript.json"
    metadata_path = transcript_path.parent / "transcript_metadata.json"
    if not metadata_path.is_file():
        fail("project transcript_metadata.json is required")
    metadata = load_json(metadata_path)
    if metadata.get("timebase") != "program" or transcript.get("timebase") != "program":
        fail("project candidates require a program-time transcript")
    if metadata.get("timeline_id") != transcript.get("timeline_id"):
        fail("project transcript timeline binding is stale")
    bindings = metadata.get("bindings", {})
    verify_binding(bindings.get("video"), source_video, "video")
    verify_binding(bindings.get("timeline"), timeline_path, "timeline")
    verify_binding(bindings.get("source_transcript"), source_transcript, "source transcript")
    return metadata, timeline_path


def run_candidates(args):
    out_dir = Path(args.out).resolve()
    input_path = Path(args.candidates).resolve() if args.candidates else out_dir / "shorts_candidates.json"
    transcript_path = Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    if not input_path.exists():
        fail(f"agent-authored candidates file not found: {input_path}")
    if not transcript_path.exists():
        fail(f"transcript not found: {transcript_path}")
    raw = load_json(input_path)
    require_type(raw, dict, "root")
    unknown = set(raw) - ALLOWED_TOP_LEVEL
    if unknown:
        fail(f"root contains unsupported fields: {', '.join(sorted(unknown))}")
    require_type(raw.get("candidates"), list, "candidates")
    selection = validate_selection(raw.get("selection"))
    transcript = load_json(transcript_path)
    project_binding = (
        validate_project_bindings(args.project_root, transcript_path, transcript)
        if args.project_root else None
    )
    duration = transcript_duration(transcript)
    normalized = [normalize_candidate(item, index, transcript, duration) for index, item in enumerate(raw["candidates"])]
    present_modes = {candidate["evidence_mode"] for candidate in normalized}
    if present_modes != {selection["evidence_mode"]}:
        fail("every candidate evidence_mode must match selection.evidence_mode")
    result = dict(raw)
    result["schema_version"] = "shorts-candidates.v2"
    result["producer"] = {
        "skill": "video-to-shorts",
        "mode": "agent_first",
        "evidence_mode": selection["evidence_mode"],
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    if project_binding:
        project_metadata, timeline_path = project_binding
        video_binding = project_metadata["bindings"]["video"]
        timeline_binding = project_metadata["bindings"]["timeline"]
        result["video"] = {
            "source": video_binding["path"],
            "sha256": video_binding["sha256"],
            "duration_s": project_metadata.get("duration_s", duration),
            "timebase": "source",
            "timeline": {
                "path": str(timeline_path),
                "sha256": timeline_binding["sha256"],
            },
        }
        result["transcript"] = {
            "path": str(transcript_path),
            "timebase": "program",
            "timeline_id": transcript["timeline_id"],
        }
    else:
        result["transcript"] = {
            **raw.get("transcript", {}),
            "path": str(transcript_path),
            "timebase": transcript.get("timebase", "input_video_relative"),
        }
    result["selection"] = selection
    result["candidates"] = dedupe_candidates(normalized)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "shorts_candidates.json"
    write_json(output_path, result)
    write_candidates_preview_md(out_dir / "shorts_candidates_preview.md", result)
    write_candidates_preview_html(out_dir / "shorts_candidates_preview.html", result)
    if args.project_root:
        workflow_root = transcript_path.parent
        review_dir = Path(args.project_root).resolve() / "review" / "06-shorts"
        write_json(workflow_root / "candidates.json", result)
        review_dir.mkdir(parents=True, exist_ok=True)
        write_candidates_preview_md(review_dir / "candidates-summary.md", result)
        write_candidates_preview_html(review_dir / "candidates.html", result)
    print(f"[video-to-shorts] validated candidates: {output_path}")
    print(f"[video-to-shorts] evidence mode: {selection['evidence_mode']}")
    print(f"[video-to-shorts] kept after overlap dedupe: {len(result['candidates'])}")


def build_parser():
    parser = argparse.ArgumentParser(description="Validate agent-authored shorts_candidates.json and generate previews.")
    parser.add_argument("--out", required=True, help="Output directory containing transcript.json by default.")
    parser.add_argument("--candidates", help="Agent-authored candidate JSON. Defaults to OUT/shorts_candidates.json.")
    parser.add_argument("--transcript", help="Transcript JSON. Defaults to OUT/transcript.json.")
    parser.add_argument("--project-root")
    return parser


def main(argv=None):
    run_candidates(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
