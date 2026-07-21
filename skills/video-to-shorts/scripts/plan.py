#!/usr/bin/env python3
"""Build shorts_plan.v2 from validated shorts-candidates.v2 data."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from preview import write_plan_preview_html, write_plan_preview_md
from review_gate import candidate_review_paths, load_json_artifact, sha256_file, validate_candidate_review
from transcript_utils import load_json, overlap_ratio, transcript_duration, write_json


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


SCORE_DIMENSIONS = {
    "hook": 20,
    "completeness": 20,
    "audience_value": 20,
    "emotion_tension": 15,
    "quotability": 15,
    "pace_editability": 10,
}
MAX_FILLER_SPAN_S = 1.5
MAX_FILLER_RATIO = 0.15
MIN_KEEP_SPAN_S = 0.15
WORD_BOUNDARY_TOLERANCE_S = 0.06


def fail(message):
    raise SystemExit(message)


def as_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on"):
        return True
    if text in ("0", "false", "no", "n", "off"):
        return False
    raise ValueError("expected true or false")


def transcript_words(transcript):
    words = []
    for segment in transcript.get("segments") or []:
        for word in segment.get("words") or []:
            try:
                start = float(word["start"])
                end = float(word["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if end >= start:
                words.append({"start": start, "end": end, "word": str(word.get("word", ""))})
    return sorted(words, key=lambda item: (item["start"], item["end"]))


def complement_spans(start, end, drops):
    keep = []
    cursor = start
    for drop in drops:
        if drop["start_time"] > cursor:
            keep.append({"start_time": round(cursor, 3), "end_time": round(drop["start_time"], 3)})
        cursor = drop["end_time"]
    if cursor < end:
        keep.append({"start_time": round(cursor, 3), "end_time": round(end, 3)})
    return keep


def rejected_span(span, reason):
    return {"requested": span, "reason": reason}


def normalize_filler_drop_spans(candidate, transcript):
    requested = candidate.get("filler_drop_spans") or []
    if not isinstance(requested, list):
        return [], [], [rejected_span(requested, "FILLER_DROP_SPANS_NOT_ARRAY")], ["INVALID_FILLER_DROP_SPANS"]
    candidate_start = candidate.get("start_time")
    candidate_end = candidate.get("end_time")
    if not isinstance(candidate_start, (int, float)) or not isinstance(candidate_end, (int, float)):
        return requested, [], [], []
    source_duration = candidate_end - candidate_start
    words = transcript_words(transcript)
    accepted = []
    rejected = []
    warnings = []
    for raw in requested:
        if not isinstance(raw, dict):
            rejected.append(rejected_span(raw, "SPAN_NOT_OBJECT"))
            continue
        if raw.get("review_status", "approved") == "rejected":
            rejected.append(rejected_span(raw, "REVIEW_STATUS_REJECTED"))
            continue
        if raw.get("type") != "filler":
            rejected.append(rejected_span(raw, "TYPE_NOT_FILLER"))
            continue
        try:
            requested_start = float(raw["start_time"])
            requested_end = float(raw["end_time"])
        except (KeyError, TypeError, ValueError):
            rejected.append(rejected_span(raw, "INVALID_TIME_RANGE"))
            continue
        if requested_end <= requested_start:
            rejected.append(rejected_span(raw, "INVALID_TIME_RANGE"))
            continue
        if requested_start < candidate_start or requested_end > candidate_end:
            rejected.append(rejected_span(raw, "OUTSIDE_CANDIDATE_RANGE"))
            continue
        if requested_end - requested_start > MAX_FILLER_SPAN_S + 0.001:
            rejected.append(rejected_span(raw, "SPAN_EXCEEDS_1_5_SECONDS"))
            continue
        overlapping_words = [word for word in words if word["start"] < requested_end and word["end"] > requested_start]
        if not overlapping_words:
            rejected.append(rejected_span(raw, "NO_WORD_IN_SPAN"))
            continue
        first_word = overlapping_words[0]
        last_word = overlapping_words[-1]
        if abs(requested_start - first_word["start"]) > WORD_BOUNDARY_TOLERANCE_S or abs(requested_end - last_word["end"]) > WORD_BOUNDARY_TOLERANCE_S:
            rejected.append(rejected_span(raw, "UNSAFE_WORD_OVERLAP"))
            continue
        normalized = {
            "type": "filler",
            "start_time": round(first_word["start"], 3),
            "end_time": round(last_word["end"], 3),
            "reason": str(raw.get("reason") or ""),
            "review_status": "approved",
            "words": [word["word"] for word in overlapping_words],
        }
        if any(normalized["start_time"] < existing["end_time"] and normalized["end_time"] > existing["start_time"] for existing in accepted):
            rejected.append(rejected_span(raw, "OVERLAPPING_FILLER_DROP_SPAN"))
            continue
        tentative = sorted(accepted + [normalized], key=lambda item: item["start_time"])
        removed = sum(item["end_time"] - item["start_time"] for item in tentative)
        if source_duration <= 0 or removed > source_duration * MAX_FILLER_RATIO + 0.001:
            rejected.append(rejected_span(raw, "TOTAL_REMOVAL_RATIO_EXCEEDED"))
            continue
        keep = complement_spans(candidate_start, candidate_end, tentative)
        if any(item["end_time"] - item["start_time"] < MIN_KEEP_SPAN_S for item in keep):
            rejected.append(rejected_span(raw, "KEEP_SPAN_TOO_SHORT"))
            continue
        accepted = tentative
    if rejected:
        warnings.append("FILLER_DROP_SPANS_REJECTED")
    return requested, accepted, rejected, warnings


def normalize_candidate(item, index, transcript):
    if not isinstance(item, dict):
        return {"source_candidate_index": index, "candidate_id": f"candidate-{index}", "normalization_errors": ["CANDIDATE_NOT_OBJECT"]}
    candidate = dict(item)
    candidate["source_candidate_index"] = index
    candidate["candidate_id"] = str(item.get("candidate_id") or f"candidate-{index}")
    candidate["normalization_errors"] = []
    for field in ("start_time", "end_time", "duration", "score"):
        value = item.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            candidate["normalization_errors"].append(f"INVALID_{field.upper()}")
        else:
            candidate[field] = value
    candidate["title"] = str(item.get("title") or "")
    candidate["scene_type"] = str(item.get("scene_type") or "")
    candidate["evidence_mode"] = str(item.get("evidence_mode") or "")
    candidate["transcript_excerpt"] = str(item.get("transcript_excerpt") or "").strip()
    candidate["hook_sentence"] = str(item.get("hook_sentence") or "")
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    candidate["editorial_reason"] = str(metadata.get("editorial_reason") or "").strip()
    if not candidate["editorial_reason"]:
        candidate["normalization_errors"].append("EMPTY_EDITORIAL_REASON")
    requested, normalized, rejected, filler_warnings = normalize_filler_drop_spans(candidate, transcript)
    candidate["requested_filler_drop_spans"] = requested
    candidate["filler_drop_spans"] = normalized
    candidate["rejected_filler_drop_spans"] = rejected
    candidate["filler_warnings"] = filler_warnings
    if isinstance(candidate.get("start_time"), (int, float)) and isinstance(candidate.get("end_time"), (int, float)):
        candidate["keep_spans"] = complement_spans(candidate["start_time"], candidate["end_time"], normalized)
        candidate["source_duration"] = round(candidate["end_time"] - candidate["start_time"], 3)
        candidate["filler_removed_duration"] = round(sum(span["end_time"] - span["start_time"] for span in normalized), 3)
        candidate["estimated_output_duration"] = round(candidate["source_duration"] - candidate["filler_removed_duration"], 3)
    candidate["score_breakdown"] = item.get("score_breakdown")
    return candidate


def validation_for(candidate, transcript_duration_s, args):
    errors = list(candidate.get("normalization_errors") or [])
    warnings = list(candidate.get("warnings") or []) + list(candidate.get("filler_warnings") or [])
    breakdown = candidate.get("score_breakdown")
    if not isinstance(breakdown, dict) or set(breakdown) != set(SCORE_DIMENSIONS):
        errors.append("INVALID_SCORE_BREAKDOWN")
    else:
        completeness = breakdown.get("completeness")
        if not isinstance(completeness, dict) or isinstance(completeness.get("score"), bool) or not isinstance(completeness.get("score"), (int, float)):
            errors.append("INVALID_COMPLETENESS")
        elif completeness["score"] < args.min_completeness:
            errors.append("LOW_COMPLETENESS")
    if not errors:
        start = candidate["start_time"]
        end = candidate["end_time"]
        duration = candidate["duration"]
        estimated_output_duration = candidate.get("estimated_output_duration", duration)
        if start < 0 or end <= start:
            errors.append("INVALID_TIME_RANGE")
        if end > transcript_duration_s:
            errors.append("TIME_OUT_OF_RANGE")
        if abs(duration - (end - start)) > 0.01:
            errors.append("DURATION_MISMATCH")
        if estimated_output_duration < args.min_duration:
            errors.append("SHORT_DURATION")
        if estimated_output_duration > args.max_duration:
            errors.append("LONG_DURATION")
        if candidate["score"] < args.min_score:
            errors.append("LOW_SCORE")
    if not candidate.get("transcript_excerpt"):
        errors.append("EMPTY_EXCERPT")
    return {"passed": not errors, "errors": errors, "warnings": warnings}


def select_candidates(candidates, transcript_duration_s, args, preserve_input_order=False):
    evaluated = []
    for candidate in candidates:
        evaluated.append((candidate, validation_for(candidate, transcript_duration_s, args)))
    eligible = [item for item in evaluated if item[1]["passed"]]
    if not preserve_input_order:
        eligible.sort(key=lambda item: item[0]["score"], reverse=True)
    selected = []
    rejected = [(candidate, validation) for candidate, validation in evaluated if not validation["passed"]]
    for candidate, validation in eligible:
        if not args.allow_overlap and any(overlap_ratio(candidate, kept) > 0.5 for kept, _ in selected):
            rejected.append((candidate, {"passed": False, "errors": ["OVERLAPS_HIGHER_SCORE"], "warnings": validation["warnings"]}))
            continue
        if len(selected) >= args.max_shorts:
            rejected.append((candidate, {"passed": False, "errors": ["MAX_SHORTS_REACHED"], "warnings": validation["warnings"]}))
            continue
        selected.append((candidate, validation))
    return selected, rejected


def require_explicit_selection_survived(selection_policy, rejected):
    if selection_policy not in ("explicit_user_selection", "explicit_agent_selection") or not rejected:
        return
    details = "; ".join(
        f"{candidate.get('candidate_id', '<unknown>')}: {', '.join(validation.get('errors') or ['REJECTED'])}"
        for candidate, validation in rejected
    )
    fail(f"explicit candidate selection was rejected by deterministic planning: {details}")


def load_planning_transcript(review, requested_path, default_path):
    if review.get("bound_visual_review"):
        path, data = load_json_artifact(review.get("artifacts", {}).get("transcript"), "transcript")
        if requested_path is not None and Path(requested_path).resolve() != path:
            fail(f"--transcript does not match the receipt-bound transcript: {requested_path} != {path}")
        return path, data
    path = Path(requested_path).resolve() if requested_path is not None else Path(default_path)
    if not path.exists():
        fail(f"transcript.json not found: {path}")
    return path, load_json(path)


def output_paths(short_id):
    directory = f"work/shorts/{short_id}"
    return {
        "directory": directory,
        "source_video": f"{directory}/source.mp4",
        "transcript": f"{directory}/transcript.json",
        "extraction_report": f"{directory}/extraction_report.json",
    }


def build_plan(selected, rejected, candidates_path, candidates_data, transcript_path):
    shorts = []
    for order, (candidate, validation) in enumerate(selected, 1):
        short_id = f"short_{order:02d}"
        shorts.append({
            "id": short_id,
            "short_id": short_id,
            "candidate_id": candidate["candidate_id"],
            "source_candidate_index": candidate["source_candidate_index"],
            "order": order,
            "title": candidate["title"],
            "scene_type": candidate["scene_type"],
            "evidence_mode": candidate["evidence_mode"],
            "start_time": candidate["start_time"],
            "end_time": candidate["end_time"],
            "duration": candidate["duration"],
            "score_breakdown": candidate["score_breakdown"],
            "score": candidate["score"],
            "hook_sentence": candidate["hook_sentence"],
            "editorial_reason": candidate["editorial_reason"],
            "transcript_excerpt": candidate["transcript_excerpt"],
            "requested_filler_drop_spans": candidate["requested_filler_drop_spans"],
            "filler_drop_spans": candidate["filler_drop_spans"],
            "rejected_filler_drop_spans": candidate["rejected_filler_drop_spans"],
            "keep_spans": candidate["keep_spans"],
            "source_duration": candidate["source_duration"],
            "filler_removed_duration": candidate["filler_removed_duration"],
            "estimated_output_duration": candidate["estimated_output_duration"],
            "validation": validation,
            "outputs": output_paths(short_id),
            "status": "planned",
        })
    rejected_items = [{
        "candidate_id": candidate["candidate_id"],
        "source_candidate_index": candidate["source_candidate_index"],
        "title": candidate.get("title", ""),
        "score": candidate.get("score"),
        "validation": validation,
    } for candidate, validation in sorted(rejected, key=lambda item: item[0]["source_candidate_index"])]
    return {
        "schema_version": "shorts-plan.v2",
        "producer": {"skill": "video-to-shorts", "planner": "deterministic", "created_at": datetime.now(timezone.utc).isoformat()},
        "source_candidates": {"path": str(candidates_path), "schema_version": candidates_data.get("schema_version")},
        "transcript": {"path": str(transcript_path), "timebase": "input_video_relative"},
        "shorts": shorts,
        "rejected_candidates": rejected_items,
        "metadata": {"notes": "Approved filler_drop_spans were normalized to transcript word boundaries and converted to keep_spans. Media extraction has not yet been performed."},
    }


def source_ranges_for_program(timeline, start, end):
    ranges = []
    for clip in timeline["clips"]:
        program = clip["program_range"]
        overlap_start = max(float(start), float(program["start_s"]))
        overlap_end = min(float(end), float(program["end_s"]))
        if overlap_end <= overlap_start:
            continue
        source = clip["source_range"]
        speed = float(clip["speed"])
        ranges.append({
            "start_s": round(float(source["start_s"]) + (overlap_start - float(program["start_s"])) * speed, 6),
            "end_s": round(float(source["start_s"]) + (overlap_end - float(program["start_s"])) * speed, 6),
        })
    return ranges


def canonical_project_plan(legacy, project_root, out_dir, transcript, review):
    root = Path(project_root).resolve()
    project = projectlib.load_json(root / "work/project.json")
    if project.get("render", {}).get("status") != "verified":
        fail("project mode requires a verified main delivery render")
    sequence = project.get("sequences", {}).get(project.get("active_sequence"), {})
    timeline = projectlib.load_json(
        projectlib.resolve_project_path(root, sequence.get("timeline", ""))
    )
    errors = projectlib.validate_timeline(timeline)
    if errors:
        fail("invalid project timeline: " + "; ".join(errors))
    if transcript.get("timebase") != "program" or transcript.get("timeline_id") != timeline["timeline_id"]:
        fail("project shorts transcript must use the active program timeline")
    source_render_value = project.get("render", {}).get("output")
    source_render = projectlib.resolve_project_path(root, source_render_value)
    if not source_render.is_file():
        fail(f"verified main render is missing: {source_render}")
    if Path(review["artifacts"]["source_video"]["path"]).resolve() != source_render:
        fail("candidate review is not bound to the verified main render")
    operations = projectlib.operation_map(project)
    depends_on = list(sequence.get("operations", []))
    based_on = {operation_id: operations[operation_id]["revision"] for operation_id in depends_on}
    delivery_mode = review["decision"]["delivery_mode"]
    canonical_shorts = []
    for index, item in enumerate(legacy["shorts"], 1):
        short_id = f"short-{index:03d}"
        program_range = {
            "start_s": round(float(item["start_time"]), 6),
            "end_s": round(float(item["end_time"]), 6),
        }
        work_directory = f"shorts/{short_id}"
        canonical_shorts.append({
            **item,
            "id": short_id,
            "short_id": short_id,
            "program_range": program_range,
            "source_ranges": source_ranges_for_program(
                timeline, program_range["start_s"], program_range["end_s"]
            ),
            "outputs": {
                "work_directory": work_directory,
                "transcript": f"{work_directory}/transcript.json",
                "extraction_report": f"{work_directory}/extraction-report.json",
                "horizontal_video": f"../final/shorts/{short_id}-horizontal.mp4",
                "vertical_video": (
                    f"../final/shorts/{short_id}-vertical.mp4"
                    if delivery_mode == "horizontal_and_vertical" else None
                ),
            },
        })
    stat = source_render.stat()
    decision = review["decision"]
    return {
        "schema_version": 1,
        "target": "derived",
        "timebase": "program",
        "timeline_id": timeline["timeline_id"],
        "source_render": {
            "path": source_render_value,
            "sha256": sha256_file(source_render),
            "size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
        },
        "source_transcript": "understand/transcript.json",
        "source_candidates": legacy["source_candidates"],
        "transcript": {"path": "shorts/transcript.json", "timebase": "program"},
        "depends_on": depends_on,
        "based_on": based_on,
        "selection": {
            "mode": review.get("decision_mode", "human"),
            "rationale": decision.get("selection_rationale", "Human selection recorded by review receipt."),
            "delivery_mode": delivery_mode,
            "review_id": review["review_id"],
        },
        "shorts": canonical_shorts,
        "rejected_candidates": legacy["rejected_candidates"],
        "metadata": {
            **legacy["metadata"],
            "candidate_review_path": str(candidate_review_paths(out_dir)["review"]),
            "candidate_review_sha256": sha256_file(candidate_review_paths(out_dir)["review"]),
            "approved_candidates_path": legacy["source_candidates"]["path"],
        },
    }


def run_plan(args):
    out_dir = Path(args.out).resolve()
    review, candidates_path = validate_candidate_review(out_dir)
    selection_policy = review["decision"]["selection_mode"]
    transcript_path, transcript_data = load_planning_transcript(
        review, args.transcript, out_dir / "transcript.json"
    )
    if not candidates_path.exists():
        fail(f"shorts_candidates.json not found: {candidates_path}")
    candidates_data = (
        load_json_artifact(review["approved_candidates"], "approved candidates", "shorts-candidates.v2")[1]
        if review.get("bound_visual_review") else load_json(candidates_path)
    )
    if candidates_data.get("schema_version") != "shorts-candidates.v2":
        fail("plan.py requires shorts-candidates.v2")
    raw_candidates = candidates_data.get("candidates")
    if not isinstance(raw_candidates, list):
        fail("shorts_candidates.json must contain a candidates array")
    candidates = [normalize_candidate(item, index, transcript_data) for index, item in enumerate(raw_candidates, 1)]
    selected, rejected = select_candidates(
        candidates,
        transcript_duration(transcript_data),
        args,
        preserve_input_order=selection_policy in ("explicit_user_selection", "explicit_agent_selection"),
    )
    require_explicit_selection_survived(selection_policy, rejected)
    plan = build_plan(selected, rejected, candidates_path, candidates_data, transcript_path)
    plan["metadata"]["candidate_selection"] = selection_policy
    plan["metadata"]["delivery_mode"] = review["decision"]["delivery_mode"]
    review_path = candidate_review_paths(out_dir)["review"]
    plan["metadata"]["human_review"] = {
        "candidate_review_id": review["review_id"],
        "candidate_review_path": str(review_path),
        "candidate_review_sha256": sha256_file(review_path),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.project_root:
        plan = canonical_project_plan(plan, args.project_root, out_dir, transcript_data, review)
        plan_path = out_dir / "shorts-plan.json"
    else:
        plan_path = out_dir / "shorts_plan.json"
    write_json(plan_path, plan)
    write_plan_preview_md(out_dir / "shorts_plan_preview.md", plan)
    write_plan_preview_html(out_dir / "shorts_plan_preview.html", plan)
    print(f"[video-to-shorts] plan: {plan_path}")
    print(f"[video-to-shorts] selected: {len(selected)}")
    print(f"[video-to-shorts] rejected: {len(rejected)}")


def build_parser():
    parser = argparse.ArgumentParser(description="Build shorts-plan.v2 from validated shorts-candidates.v2.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--transcript")
    parser.add_argument("--project-root", help="Emit canonical Project Protocol V1 shorts-plan.json.")
    parser.add_argument("--max-shorts", type=int, default=5)
    parser.add_argument("--min-duration", type=float, default=20.0)
    parser.add_argument("--max-duration", type=float, default=90.0)
    parser.add_argument("--min-score", type=float, default=70.0)
    parser.add_argument("--min-completeness", type=float, default=15.0)
    parser.add_argument("--allow-overlap", type=as_bool, default=False)
    return parser


def main(argv=None):
    run_plan(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
