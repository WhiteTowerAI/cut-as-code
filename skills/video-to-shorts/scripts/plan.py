#!/usr/bin/env python3
"""Build shorts_plan.v2 from validated shorts-candidates.v2 data."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from preview import write_plan_preview_html, write_plan_preview_md
from review_gate import candidate_review_paths, sha256_file, validate_candidate_review
from transcript_utils import load_json, overlap_ratio, transcript_duration, write_json


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


def run_plan(args):
    out_dir = Path(args.out).resolve()
    review, candidates_path = validate_candidate_review(out_dir)
    selection_policy = review["decision"]["selection_mode"]
    transcript_path = Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    if not candidates_path.exists():
        fail(f"shorts_candidates.json not found: {candidates_path}")
    if not transcript_path.exists():
        fail(f"transcript.json not found: {transcript_path}")
    candidates_data = load_json(candidates_path)
    if candidates_data.get("schema_version") != "shorts-candidates.v2":
        fail("plan.py requires shorts-candidates.v2")
    raw_candidates = candidates_data.get("candidates")
    if not isinstance(raw_candidates, list):
        fail("shorts_candidates.json must contain a candidates array")
    transcript_data = load_json(transcript_path)
    candidates = [normalize_candidate(item, index, transcript_data) for index, item in enumerate(raw_candidates, 1)]
    selected, rejected = select_candidates(
        candidates,
        transcript_duration(transcript_data),
        args,
        preserve_input_order=selection_policy == "explicit_user_selection",
    )
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
    write_json(out_dir / "shorts_plan.json", plan)
    write_plan_preview_md(out_dir / "shorts_plan_preview.md", plan)
    write_plan_preview_html(out_dir / "shorts_plan_preview.html", plan)
    print(f"[video-to-shorts] plan: {out_dir / 'shorts_plan.json'}")
    print(f"[video-to-shorts] selected: {len(selected)}")
    print(f"[video-to-shorts] rejected: {len(rejected)}")


def build_parser():
    parser = argparse.ArgumentParser(description="Build shorts-plan.v2 from validated shorts-candidates.v2.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--transcript")
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
