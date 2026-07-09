#!/usr/bin/env python3
"""Build a human-editable shorts plan from candidate highlights."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from preview import write_plan_preview_html, write_plan_preview_md
from transcript_utils import (
    excerpt_for_range,
    fmt_time,
    load_json,
    overlap_ratio,
    transcript_duration,
    write_json,
)


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


def duration_of(candidate):
    if isinstance(candidate.get("duration"), (int, float)):
        return float(candidate["duration"])
    if isinstance(candidate.get("duration_s"), (int, float)):
        return float(candidate["duration_s"])
    return float(candidate["end_time"]) - float(candidate["start_time"])


def validation_for(candidate, transcript_duration_s, args):
    errors = []
    warnings = []
    start = candidate["start_time"]
    end = candidate["end_time"]
    duration = candidate["duration"]
    if end <= start:
        errors.append("END_NOT_AFTER_START")
    if start < 0 or end > transcript_duration_s:
        errors.append("TIME_OUT_OF_RANGE")
    if duration < args.min_duration:
        errors.append("SHORT_DURATION")
    if duration > args.max_duration:
        errors.append("LONG_DURATION")
    if candidate["score"] < args.min_score:
        errors.append("LOW_SCORE")
    if not candidate.get("transcript_excerpt"):
        errors.append("EMPTY_EXCERPT")
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def normalize_candidates(candidates_data, transcript):
    raw = candidates_data.get("candidates")
    if not isinstance(raw, list):
        fail("shorts_candidates.json must contain a candidates array")
    duration = transcript_duration(transcript)
    normalized = []
    for index, item in enumerate(raw, start=1):
        try:
            start = float(item.get("start_time"))
            end = float(item.get("end_time"))
        except (TypeError, ValueError):
            continue
        cand_duration = round(end - start, 3)
        excerpt = str(item.get("transcript_excerpt") or "").strip()
        if not excerpt:
            excerpt = excerpt_for_range(transcript, start, end, max_chars=520)
        normalized.append({
            "source_candidate_index": index,
            "candidate_id": str(item.get("candidate_id") or f"cand-{index:03d}"),
            "title": str(item.get("title") or f"Candidate {index}").strip(),
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": cand_duration,
            "score": int(float(item.get("score", 0))),
            "hook_sentence": str(item.get("hook_sentence") or "").strip(),
            "virality_reason": str(item.get("virality_reason") or "").strip(),
            "transcript_excerpt": excerpt,
            "candidate_warnings": list(item.get("warnings") or []),
        })
    return normalized, duration


def select_candidates(candidates, transcript_duration_s, args):
    ordered = sorted(candidates, key=lambda c: c["score"], reverse=True)
    selected = []
    rejected = []
    for cand in ordered:
        validation = validation_for(cand, transcript_duration_s, args)
        if not validation["passed"]:
            rejected.append((cand, validation, "validation_failed"))
            continue
        if not args.allow_overlap:
            overlapping = [other for other in selected if overlap_ratio(cand, other) > 0.5]
            if overlapping:
                validation = dict(validation)
                validation["passed"] = False
                validation["errors"] = ["OVERLAPS_SELECTED"]
                rejected.append((cand, validation, "overlap"))
                continue
        selected.append(cand)
        if len(selected) >= args.max_shorts:
            break
    return selected, rejected


def build_plan(selected, candidates_data, transcript_data, transcript_path, args):
    shorts = []
    for order, cand in enumerate(selected, start=1):
        short_id = f"short_{order:02d}"
        validation = validation_for(cand, transcript_duration(transcript_data), args)
        shorts.append({
            "id": short_id,
            "short_id": short_id,
            "candidate_id": cand["candidate_id"],
            "source_candidate_index": cand["source_candidate_index"],
            "order": order,
            "title": cand["title"],
            "start_time": cand["start_time"],
            "end_time": cand["end_time"],
            "duration": cand["duration"],
            "duration_s": cand["duration"],
            "score": cand["score"],
            "hook_sentence": cand["hook_sentence"],
            "virality_reason": cand["virality_reason"],
            "reason": cand["virality_reason"],
            "transcript_excerpt": cand["transcript_excerpt"],
            "validation": validation,
            "outputs": {
                "directory": f"work/shorts/{short_id}",
                "source_video": f"work/shorts/{short_id}/source.mp4",
                "transcript": f"work/shorts/{short_id}/transcript.json",
                "vertical_reframe_dir": f"work/shorts/{short_id}/vertical-reframe",
            },
            "status": "planned",
            "metadata": {
                "candidate_warnings": cand.get("candidate_warnings", []),
            },
        })

    return {
        "schema_version": "shorts-plan.v1",
        "video": candidates_data.get("video", {
            "source": "",
            "duration_s": transcript_duration(transcript_data),
        }),
        "transcript": candidates_data.get("transcript", {
            "path": str(transcript_path),
            "timebase": "input_video_relative",
            "source": "provided",
        }),
        "producer": {
            "skill": "video-to-shorts",
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "planner": "score-duration-overlap-filter",
        },
        "source_candidates": {
            "path": "work/shorts/shorts_candidates.json",
            "schema_version": "shorts-candidates.v1",
        },
        "target": {
            "aspect_ratio": "9:16",
            "downstream_reframe_skill": "video-vertical-reframe",
        },
        "shorts": shorts,
        "metadata": {
            "selection": {
                "max_shorts": args.max_shorts,
                "min_duration": args.min_duration,
                "max_duration": args.max_duration,
                "min_score": args.min_score,
                "allow_overlap": args.allow_overlap,
            },
            "notes": "Generated from shorts_candidates.json for human confirmation/editing. No video cutting was performed.",
        },
    }


def validate_plan(plan):
    required = ["schema_version", "video", "transcript", "producer", "target", "shorts"]
    missing = [key for key in required if key not in plan]
    if missing:
        fail("shorts_plan.json missing required fields: " + ", ".join(missing))
    if plan["schema_version"] != "shorts-plan.v1":
        fail("shorts_plan.json schema_version must be shorts-plan.v1")
    if not plan["shorts"]:
        fail("shorts_plan.json contains no shorts")
    for item in plan["shorts"]:
        for key in [
            "id",
            "title",
            "start_time",
            "end_time",
            "duration",
            "hook_sentence",
            "virality_reason",
            "transcript_excerpt",
            "source_candidate_index",
        ]:
            if key not in item:
                fail(f"short item missing {key}: {item.get('id') or item.get('short_id')}")
        if item["end_time"] <= item["start_time"]:
            fail(f"short item has invalid time range: {item['id']}")
        if round(item["end_time"] - item["start_time"], 3) != round(item["duration"], 3):
            fail(f"short item duration does not match time range: {item['id']}")


def run_plan(args):
    args.allow_overlap = as_bool(args.allow_overlap)
    out_dir = Path(args.out).resolve()
    candidates_path = out_dir / "shorts_candidates.json"
    transcript_path = out_dir / "transcript.json"
    if not candidates_path.exists():
        fail(f"shorts_candidates.json not found: {candidates_path}")
    if not transcript_path.exists():
        fail(f"transcript.json not found: {transcript_path}")
    candidates_data = load_json(candidates_path)
    transcript_data = load_json(transcript_path)
    candidates, transcript_duration_s = normalize_candidates(candidates_data, transcript_data)
    selected, rejected = select_candidates(candidates, transcript_duration_s, args)
    if not selected:
        fail("No candidates passed plan filters. Lower --min-score or adjust duration limits.")
    plan = build_plan(selected, candidates_data, transcript_data, transcript_path, args)
    plan["metadata"]["rejected_count"] = len(rejected)
    validate_plan(plan)

    plan_path = out_dir / "shorts_plan.json"
    preview_md = out_dir / "shorts_plan_preview.md"
    preview_html = out_dir / "shorts_plan_preview.html"
    write_json(plan_path, plan)
    write_plan_preview_md(preview_md, plan)
    write_plan_preview_html(preview_html, plan)
    print(f"[video-to-shorts] plan: {plan_path}")
    print(f"[video-to-shorts] preview md: {preview_md}")
    print(f"[video-to-shorts] preview html: {preview_html}")
    print(f"[video-to-shorts] selected: {len(selected)}")
    print(f"[video-to-shorts] rejected: {len(rejected)}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate shorts_plan.json from reviewed shorts_candidates.json."
    )
    parser.add_argument("--out", required=True, help="Output work/shorts directory.")
    parser.add_argument("--max-shorts", type=int, default=5, help="Maximum shorts to select.")
    parser.add_argument("--min-duration", type=float, default=20.0, help="Minimum short duration in seconds.")
    parser.add_argument("--max-duration", type=float, default=90.0, help="Maximum short duration in seconds.")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum candidate score.")
    parser.add_argument(
        "--allow-overlap",
        default="false",
        help="Allow obvious overlap between selected shorts: true or false.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    run_plan(args)


if __name__ == "__main__":
    main()
