#!/usr/bin/env python3
"""Extract planned shorts with optional multi keep-span filler removal."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from boundary_refine import refine_short_boundary
from transcript_utils import load_json, write_json


MIN_KEEP_SPAN_S = 0.15


def fail(message):
    raise SystemExit(message)


def run(command):
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(map(str, command)) + "\n" + process.stderr.strip())
    return process.stdout


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


def probe_duration(ffprobe, path):
    return float(run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)]).strip())


def has_audio(ffprobe, path):
    output = run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)])
    return bool(output.strip())


def output_dir_for_short(out_dir, short_item):
    short_id = short_item.get("id") or short_item.get("short_id")
    if not short_id:
        fail("short item missing id/short_id")
    return out_dir / str(short_id)


def refined_boundary(short_item, transcript, ffmpeg, video_path, args):
    if not args.no_refine_boundaries:
        return refine_short_boundary(
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
    start = float(short_item["start_time"])
    end = float(short_item["end_time"])
    return {
        "short_id": short_item.get("id") or short_item.get("short_id"),
        "original_start_time": round(start, 3), "original_end_time": round(end, 3),
        "original_duration": round(end - start, 3), "refined_start_time": round(start, 3),
        "refined_end_time": round(end, 3), "refined_duration": round(end - start, 3),
        "content_start_time": round(start, 3), "content_end_time": round(end, 3),
        "content_duration": round(end - start, 3), "boundary_adjustment_s": {"start": 0.0, "end": 0.0},
        "reasons": ["BOUNDARY_REFINEMENT_DISABLED"], "warnings": [], "scene_cuts": [],
    }


def extraction_keep_spans(short_item, refined):
    refined_start = float(refined["refined_start_time"])
    refined_end = float(refined["refined_end_time"])
    planned = short_item.get("keep_spans") or []
    if not planned:
        return [{"start_time": round(refined_start, 3), "end_time": round(refined_end, 3)}]
    keep = []
    for item in planned:
        start = max(refined_start, float(item["start_time"]))
        end = min(refined_end, float(item["end_time"]))
        if end > start:
            keep.append({"start_time": start, "end_time": end})
    if not keep:
        fail(f"{short_item.get('short_id')} has no playable keep_spans after boundary refinement")
    if refined_start < keep[0]["start_time"]:
        keep[0]["start_time"] = refined_start
    if refined_end > keep[-1]["end_time"]:
        keep[-1]["end_time"] = refined_end
    normalized = [{"start_time": round(item["start_time"], 3), "end_time": round(item["end_time"], 3)} for item in keep]
    if any(item["end_time"] - item["start_time"] < MIN_KEEP_SPAN_S for item in normalized):
        fail(f"{short_item.get('short_id')} contains an unplayable keep_span")
    return normalized


def extract_keep_spans(ffmpeg, ffprobe, video_path, output_path, keep_spans):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio = has_audio(ffprobe, video_path)
    filters = []
    concat_inputs = []
    for index, span in enumerate(keep_spans):
        start = span["start_time"]
        end = span["end_time"]
        filters.append(f"[0:v:0]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{index}]")
        concat_inputs.append(f"[v{index}]")
        if audio:
            filters.append(f"[0:a:0]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{index}]")
            concat_inputs.append(f"[a{index}]")
    if audio:
        filters.append("".join(concat_inputs) + f"concat=n={len(keep_spans)}:v=1:a=1[vout][aout]")
    else:
        filters.append("".join(concat_inputs) + f"concat=n={len(keep_spans)}:v=1:a=0[vout]")
    command = [ffmpeg, "-y", "-i", str(video_path), "-filter_complex", ";".join(filters), "-map", "[vout]"]
    if audio:
        command.extend(["-map", "[aout]"])
    command.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"])
    if audio:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    command.extend(["-movflags", "+faststart", str(output_path)])
    run(command)


def remap_transcript(transcript, short_item, video_path, transcript_path, keep_spans, media_duration):
    segments = []
    elapsed = 0.0
    for keep in keep_spans:
        keep_start = keep["start_time"]
        keep_end = keep["end_time"]
        for source_segment in transcript.get("segments") or []:
            mapped_words = []
            for word in source_segment.get("words") or []:
                try:
                    word_start = float(word["start"])
                    word_end = float(word["end"])
                except (KeyError, TypeError, ValueError):
                    continue
                if word_start >= keep_start - 0.001 and word_end <= keep_end + 0.001:
                    mapped_words.append({
                        "start": round(elapsed + word_start - keep_start, 3),
                        "end": round(elapsed + word_end - keep_start, 3),
                        "word": str(word.get("word", "")),
                    })
            if mapped_words:
                segments.append({
                    "start": mapped_words[0]["start"],
                    "end": mapped_words[-1]["end"],
                    "text": " ".join(word["word"].strip() for word in mapped_words).strip(),
                    "words": mapped_words,
                })
        elapsed += keep_end - keep_start
    return {
        "schema_version": "short-transcript.v2",
        "short_id": str(short_item.get("id") or short_item.get("short_id")),
        "source": {"input_video": str(video_path), "source_transcript": str(transcript_path)},
        "timebase": "short_relative",
        "segments": segments,
        "metadata": {
            "title": short_item.get("title", ""),
            "duration": round(media_duration, 3),
            "source_candidate_index": short_item.get("source_candidate_index"),
            "keep_spans": keep_spans,
        },
    }


def executed_drop_spans(short_item):
    return list(short_item.get("filler_drop_spans") or [])


def run_extract(args):
    out_dir = Path(args.out).resolve()
    video_path = Path(args.video).resolve()
    plan_path = Path(args.plan).resolve() if args.plan else out_dir / "shorts_plan.json"
    transcript_path = Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    for path, label in ((video_path, "video"), (plan_path, "plan"), (transcript_path, "transcript")):
        if not path.exists():
            fail(f"{label} not found: {path}")
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe or Path(ffmpeg).with_name("ffprobe.exe"))
    plan = load_json(plan_path)
    transcript = load_json(transcript_path)
    shorts = plan.get("shorts") or []
    if not shorts:
        fail("shorts_plan.json contains no shorts")
    reports = []
    for short_item in shorts:
        refined = refined_boundary(short_item, transcript, ffmpeg, video_path, args)
        keep_spans = extraction_keep_spans(short_item, refined)
        short_dir = output_dir_for_short(out_dir, short_item)
        source_path = short_dir / "source.mp4"
        short_transcript_path = short_dir / "transcript.json"
        report_path = short_dir / "extraction_report.json"
        extract_keep_spans(ffmpeg, ffprobe, video_path, source_path, keep_spans)
        actual_duration = probe_duration(ffprobe, source_path)
        short_transcript = remap_transcript(transcript, short_item, video_path, transcript_path, keep_spans, actual_duration)
        write_json(short_transcript_path, short_transcript)
        words = [word for segment in short_transcript["segments"] for word in segment.get("words") or []]
        last_word_end = max((float(word["end"]) for word in words), default=0.0)
        estimated_output_duration = sum(span["end_time"] - span["start_time"] for span in keep_spans)
        warnings = list(refined.get("warnings") or [])
        transcript_within_media = last_word_end <= actual_duration + 0.05
        tail_margin = actual_duration - last_word_end
        if tail_margin < args.min_tail_margin:
            warnings.append("LOW_TAIL_MARGIN")
        if not transcript_within_media:
            warnings.append("TRANSCRIPT_EXCEEDS_MEDIA_DURATION")
        source_duration = refined["refined_end_time"] - refined["refined_start_time"]
        filler_removed_duration = source_duration - estimated_output_duration
        report = {
            "schema_version": "short-extraction-report.v2",
            "short_id": short_item.get("id") or short_item.get("short_id"),
            "source_video": str(video_path), "source_transcript": str(transcript_path),
            "original_candidate_start": short_item["start_time"], "original_candidate_end": short_item["end_time"],
            "refined_start": refined["refined_start_time"], "refined_end": refined["refined_end_time"],
            "requested_filler_drop_spans": short_item.get("requested_filler_drop_spans") or [],
            "executed_filler_drop_spans": executed_drop_spans(short_item),
            "rejected_filler_drop_spans": short_item.get("rejected_filler_drop_spans") or [],
            "keep_spans": keep_spans,
            "source_duration": round(source_duration, 3),
            "filler_removed_duration": round(filler_removed_duration, 3),
            "estimated_output_duration": round(estimated_output_duration, 3),
            "actual_duration": round(actual_duration, 3),
            "transcript_last_word_end": round(last_word_end, 3),
            "tail_margin_s": round(tail_margin, 3),
            "transcript_within_media": transcript_within_media,
            "boundary_refinement": refined,
            "warnings": list(dict.fromkeys(warnings)),
            "outputs": {"source_video": str(source_path), "transcript": str(short_transcript_path)},
        }
        write_json(report_path, report)
        reports.append(report)
        print(f"[video-to-shorts] extracted {report['short_id']}: {source_path}")
    summary_path = out_dir / "shorts_extraction_report.json"
    write_json(summary_path, {
        "schema_version": "shorts-extraction-report.v2", "source_video": str(video_path),
        "plan": str(plan_path), "transcript": str(transcript_path), "shorts": reports,
    })
    print(f"[video-to-shorts] extracted_count: {len(reports)}")
    print(f"[video-to-shorts] extraction_report: {summary_path}")


def build_parser():
    parser = argparse.ArgumentParser(description="Extract horizontal shorts using planned keep_spans.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--transcript")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    parser.add_argument("--no-refine-boundaries", action="store_true", help="Use raw outer plan times without boundary refinement.")
    parser.add_argument("--pre-roll", type=float, default=0.25)
    parser.add_argument("--post-roll", type=float, default=0.35)
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    parser.add_argument("--max-duration", type=float, default=90.0)
    parser.add_argument("--min-tail-margin", type=float, default=0.08)
    return parser


def main(argv=None):
    run_extract(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
