#!/usr/bin/env python3
"""Extract horizontal short source clips from shorts_plan.json."""

import argparse
import shutil
import subprocess
from pathlib import Path

from boundary_refine import refine_short_boundary
from transcript_utils import load_json, write_json


def fail(message):
    raise SystemExit(message)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "command failed: " + " ".join(str(c) for c in cmd) + "\n" + p.stderr.strip()
        )
    return p.stdout


def resolve_tool(name, explicit=None):
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        fail(f"{name} not found: {explicit}")
    found = shutil.which(name)
    if found:
        return found
    fail(f"{name} not found. Pass --{name} PATH.")


def clamp_time(value, start, end):
    return max(start, min(end, value))


def trim_words(words, start, end):
    trimmed = []
    for word in words or []:
        try:
            word_start = float(word.get("start", 0.0))
            word_end = float(word.get("end", word_start))
        except (TypeError, ValueError):
            continue
        if word_start >= start - 0.001 and word_end <= end + 0.001:
            new_word = {
                "start": round(clamp_time(word_start, start, end) - start, 3),
                "end": round(clamp_time(word_end, start, end) - start, 3),
                "word": str(word.get("word", "")),
            }
            if new_word["end"] >= new_word["start"]:
                trimmed.append(new_word)
    return trimmed


def trim_transcript(transcript, short_item, video_path, transcript_path, refined=None, media_duration=None):
    short_id = short_item.get("id") or short_item.get("short_id")
    start = float(refined["refined_start_time"]) if refined else float(short_item["start_time"])
    end = float(refined["refined_end_time"]) if refined else float(short_item["end_time"])
    content_start = float(refined.get("content_start_time", start)) if refined else start
    content_end = float(refined.get("content_end_time", end)) if refined else end
    duration = max(0.0, end - start)
    transcript_limit = min(duration, float(media_duration)) if media_duration else duration
    segments = []

    for segment in transcript.get("segments", []):
        try:
            seg_start = float(segment.get("start", 0.0))
            seg_end = float(segment.get("end", seg_start))
        except (TypeError, ValueError):
            continue
        if seg_start >= content_end or seg_end <= content_start:
            continue

        words = trim_words(segment.get("words") or [], content_start, content_end)
        if not words:
            continue
        word_start = words[0]["start"]
        word_end = words[-1]["end"]
        new_start = round(word_start + content_start - start, 3)
        new_end = round(word_end + content_start - start, 3)
        text = " ".join(str(word.get("word", "")).strip() for word in words).strip()
        words = [
            {
                "start": round(word["start"] + content_start - start, 3),
                "end": round(word["end"] + content_start - start, 3),
                "word": word["word"],
            }
            for word in words
        ]

        new_segment = {
            "start": max(0.0, new_start),
            "end": min(round(transcript_limit, 3), max(0.0, new_end)),
            "text": text,
        }
        if words:
            new_segment["words"] = words
        if new_segment["end"] >= new_segment["start"]:
            segments.append(new_segment)

    return {
        "schema_version": "short-transcript.v1",
        "short_id": str(short_id),
        "source": {
            "input_video": str(video_path),
            "source_transcript": str(transcript_path),
            "source_start_time": round(start, 3),
            "source_end_time": round(end, 3),
        },
        "timebase": "short_relative",
        "segments": segments,
        "metadata": {
            "title": short_item.get("title", ""),
            "duration": round(duration, 3),
            "source_candidate_index": short_item.get("source_candidate_index"),
            "boundary_refinement": refined or {},
        },
    }


def probe_duration(ffprobe, path):
    data = run([
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nk=1:nw=1",
        str(path),
    ]).strip()
    return float(data)


def extract_video(ffmpeg, video_path, output_path, start, end):
    duration = end - start
    if duration <= 0:
        fail(f"invalid time range: {start} - {end}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_path),
    ])


def output_dir_for_short(out_dir, short_item):
    short_id = short_item.get("id") or short_item.get("short_id")
    if not short_id:
        fail("short item missing id/short_id")
    return out_dir / str(short_id)


def run_extract(args):
    out_dir = Path(args.out).resolve()
    video_path = Path(args.video).resolve()
    plan_path = Path(args.plan).resolve() if args.plan else out_dir / "shorts_plan.json"
    transcript_path = (
        Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    )

    if not video_path.exists():
        fail(f"video not found: {video_path}")
    if not plan_path.exists():
        fail(f"shorts_plan.json not found: {plan_path}")
    if not transcript_path.exists():
        fail(f"transcript.json not found: {transcript_path}")

    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe or (Path(ffmpeg).with_name("ffprobe.exe") if ffmpeg else None))
    plan = load_json(plan_path)
    transcript = load_json(transcript_path)
    shorts = plan.get("shorts") or []
    if not shorts:
        fail("shorts_plan.json contains no shorts")

    extracted = []
    reports = []
    for short_item in shorts:
        if args.no_refine_boundaries:
            refined = {
                "short_id": short_item.get("id") or short_item.get("short_id"),
                "original_start_time": round(float(short_item["start_time"]), 3),
                "original_end_time": round(float(short_item["end_time"]), 3),
                "original_duration": round(float(short_item["end_time"]) - float(short_item["start_time"]), 3),
                "refined_start_time": round(float(short_item["start_time"]), 3),
                "refined_end_time": round(float(short_item["end_time"]), 3),
                "refined_duration": round(float(short_item["end_time"]) - float(short_item["start_time"]), 3),
                "boundary_adjustment_s": {"start": 0.0, "end": 0.0},
                "reasons": ["BOUNDARY_REFINEMENT_DISABLED"],
                "warnings": [],
                "scene_cuts": [],
                "content_start_time": round(float(short_item["start_time"]), 3),
                "content_end_time": round(float(short_item["end_time"]), 3),
                "content_duration": round(float(short_item["end_time"]) - float(short_item["start_time"]), 3),
                "first_transcript_words": "",
                "last_transcript_words": "",
                "word_count": 0,
                "completeness": {},
            }
        else:
            refined = refine_short_boundary(
                short_item,
                transcript,
                ffmpeg=ffmpeg,
                video_path=video_path,
                pre_roll=args.pre_roll,
                post_roll=args.post_roll,
                scene_threshold=args.scene_threshold,
                max_duration=args.max_duration,
                min_tail_margin=args.min_tail_margin,
            )
        start = float(refined["refined_start_time"])
        end = float(refined["refined_end_time"])
        short_dir = output_dir_for_short(out_dir, short_item)
        source_path = short_dir / "source.mp4"
        short_transcript_path = short_dir / "transcript.json"
        report_path = short_dir / "extraction_report.json"

        extract_video(ffmpeg, video_path, source_path, start, end)
        actual_duration = probe_duration(ffprobe, source_path)
        short_transcript = trim_transcript(
            transcript,
            short_item,
            video_path,
            transcript_path,
            refined,
            media_duration=actual_duration,
        )
        write_json(short_transcript_path, short_transcript)
        transcript_words = [
            word
            for segment in short_transcript.get("segments", [])
            for word in segment.get("words", [])
        ]
        max_word_end = max([float(word["end"]) for word in transcript_words], default=0.0)
        media_validation = {
            "actual_duration": round(actual_duration, 3),
            "planned_refined_duration": round(end - start, 3),
            "transcript_last_word_end": round(max_word_end, 3),
            "tail_margin_s": round(actual_duration - max_word_end, 3),
            "duration_delta_s": round(actual_duration - (end - start), 3),
            "transcript_within_media": max_word_end <= actual_duration + 0.05,
        }
        if media_validation["tail_margin_s"] < args.min_tail_margin:
            refined.setdefault("warnings", []).append("LOW_TAIL_MARGIN")
        if not media_validation["transcript_within_media"]:
            refined.setdefault("warnings", []).append("TRANSCRIPT_EXCEEDS_MEDIA_DURATION")
        report = {
            "schema_version": "short-extraction-report.v1",
            "short_id": refined["short_id"],
            "source_video": str(video_path),
            "source_transcript": str(transcript_path),
            "outputs": {
                "source_video": str(source_path),
                "transcript": str(short_transcript_path),
            },
            "boundary_refinement": refined,
            "media_validation": media_validation,
        }
        write_json(report_path, report)
        reports.append(report)

        extracted.append((short_item.get("id") or short_item.get("short_id"), source_path, short_transcript_path))
        print(f"[video-to-shorts] extracted {extracted[-1][0]}: {source_path}")
        print(f"[video-to-shorts] transcript {extracted[-1][0]}: {short_transcript_path}")
        print(f"[video-to-shorts] report {extracted[-1][0]}: {report_path}")

    summary_path = out_dir / "shorts_extraction_report.json"
    write_json(summary_path, {
        "schema_version": "shorts-extraction-report.v1",
        "source_video": str(video_path),
        "plan": str(plan_path),
        "transcript": str(transcript_path),
        "boundary_refinement": {
            "enabled": not args.no_refine_boundaries,
            "pre_roll": args.pre_roll,
            "post_roll": args.post_roll,
            "scene_threshold": args.scene_threshold,
        },
        "shorts": reports,
    })
    print(f"[video-to-shorts] extracted_count: {len(extracted)}")
    print(f"[video-to-shorts] extraction_report: {summary_path}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extract horizontal short source clips and short-relative transcripts."
    )
    parser.add_argument("--video", required=True, help="Input video path.")
    parser.add_argument("--out", required=True, help="Output work/shorts directory.")
    parser.add_argument("--plan", help="Path to shorts_plan.json. Defaults to OUT/shorts_plan.json.")
    parser.add_argument("--transcript", help="Path to transcript.json. Defaults to OUT/transcript.json.")
    parser.add_argument("--ffmpeg", help="ffmpeg path.")
    parser.add_argument("--ffprobe", help="ffprobe path.")
    parser.add_argument("--no-refine-boundaries", action="store_true", help="Use raw plan times without Phase 2.5 boundary polish.")
    parser.add_argument("--pre-roll", type=float, default=0.25, help="Seconds to add before the refined start.")
    parser.add_argument("--post-roll", type=float, default=0.35, help="Seconds to add after the refined end.")
    parser.add_argument("--scene-threshold", type=float, default=0.35, help="ffmpeg scene detection threshold for jump-cut warnings.")
    parser.add_argument("--max-duration", type=float, default=90.0, help="Maximum refined short duration in seconds.")
    parser.add_argument("--min-tail-margin", type=float, default=0.08, help="Minimum seconds after the last transcript word before media end.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    run_extract(args)


if __name__ == "__main__":
    main()
