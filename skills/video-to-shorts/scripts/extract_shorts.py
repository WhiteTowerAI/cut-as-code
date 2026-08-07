#!/usr/bin/env python3
"""Extract planned shorts with optional multi keep-span filler removal."""

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from boundary_refine import refine_short_boundary
from review_gate import sha256_file, validate_plan_review
from transcript_utils import load_json, write_json


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


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


def probe_media(ffprobe, path):
    return json.loads(run([
        ffprobe, "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,pix_fmt",
        "-of", "json", str(path),
    ]))


def validate_extracted_media(source_probe, output_probe, expected_duration):
    source_video = next(
        stream for stream in source_probe["streams"] if stream.get("codec_type") == "video"
    )
    output_video = next(
        (stream for stream in output_probe["streams"] if stream.get("codec_type") == "video"),
        None,
    )
    if not output_video or output_video.get("codec_name") != "h264":
        fail("horizontal short must contain H.264 video")
    if output_video.get("pix_fmt") != "yuv420p":
        fail("horizontal short must use yuv420p")
    if (
        output_video.get("width") != source_video.get("width")
        or output_video.get("height") != source_video.get("height")
        or Fraction(output_video.get("avg_frame_rate") or "0/1")
        != Fraction(source_video.get("avg_frame_rate") or "0/1")
    ):
        fail("horizontal short geometry or FPS differs from the main render")
    source_has_audio = any(
        stream.get("codec_type") == "audio" for stream in source_probe["streams"]
    )
    output_has_audio = any(
        stream.get("codec_type") == "audio" for stream in output_probe["streams"]
    )
    if source_has_audio and not output_has_audio:
        fail("horizontal short lost the main render audio")
    duration = float(output_probe.get("format", {}).get("duration") or 0.0)
    fps = float(Fraction(source_video.get("avg_frame_rate") or "30/1"))
    if abs(duration - expected_duration) > max(0.1, 2 / fps):
        fail("horizontal short duration differs from its keep spans")


def output_dir_for_short(out_dir, short_item):
    short_id = short_item.get("id") or short_item.get("short_id")
    if not short_id:
        fail("short item missing id/short_id")
    return out_dir / str(short_id)


def canonical_output_paths(project_root, short_item):
    outputs = short_item.get("outputs") or {}
    required = ("work_directory", "horizontal_video", "transcript", "extraction_report")
    if any(not outputs.get(field) for field in required):
        fail(f"{short_item.get('id')} canonical outputs are incomplete")
    return {
        field: projectlib.resolve_project_path(project_root, outputs[field])
        for field in required
    }


def validate_project_input(project_root, plan, video_path):
    root = Path(project_root).resolve()
    project = projectlib.load_json(root / "work/project.json")
    if plan.get("delivery_status") != "ready" or not plan.get("source_render"):
        fail("shorts plan is awaiting the verified main render; run plan.py again after delivery rendering")
    if project.get("render", {}).get("status") != "verified":
        fail("project main render is not verified")
    expected = projectlib.resolve_project_path(root, project["render"]["output"])
    if video_path != expected:
        fail("extraction video is not the current project main render")
    fingerprint = plan.get("source_render", {})
    stat = video_path.stat()
    if (
        fingerprint.get("path") != project["render"]["output"]
        or fingerprint.get("size") != stat.st_size
        or fingerprint.get("modified_ns") != stat.st_mtime_ns
        or fingerprint.get("sha256") != sha256_file(video_path)
    ):
        fail("verified main render changed after shorts plan finalization")
    operations = projectlib.operation_map(project)
    sequence = project["sequences"][project["active_sequence"]]
    if plan.get("depends_on") != list(sequence.get("operations", [])):
        fail("shorts plan does not include the current main-sequence operations")
    for dependency, revision in plan.get("based_on", {}).items():
        if operations.get(dependency, {}).get("revision") != revision:
            fail(f"shorts plan dependency revision is stale: {dependency}")


def refined_boundary(short_item, transcript, ffmpeg, video_path, media_duration, args):
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
        media_duration=media_duration,
        snap_to_phrases=not args.no_refine_boundaries,
    )


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


def build_extract_command(ffmpeg, video_path, output_path, keep_spans, has_audio):
    command = [ffmpeg, "-y"]
    filters = []
    concat_inputs = []
    for index, span in enumerate(keep_spans):
        start = span["start_time"]
        duration = span["end_time"] - start
        command.extend([
            "-ss", f"{start:.6f}", "-t", f"{duration:.6f}", "-i", str(video_path)
        ])
        filters.append(f"[{index}:v:0]setpts=PTS-STARTPTS[v{index}]")
        concat_inputs.append(f"[v{index}]")
        if has_audio:
            filters.append(f"[{index}:a:0]asetpts=PTS-STARTPTS[a{index}]")
            concat_inputs.append(f"[a{index}]")
    if has_audio:
        filters.append("".join(concat_inputs) + f"concat=n={len(keep_spans)}:v=1:a=1[vout][aout]")
    else:
        filters.append("".join(concat_inputs) + f"concat=n={len(keep_spans)}:v=1:a=0[vout]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    if has_audio:
        command.extend(["-map", "[aout]"])
    command.extend([
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"
    ])
    if has_audio:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    command.extend(["-movflags", "+faststart", str(output_path)])
    return command


def extract_keep_spans(ffmpeg, ffprobe, video_path, output_path, keep_spans):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run(build_extract_command(
        ffmpeg, video_path, output_path, keep_spans, has_audio(ffprobe, video_path)
    ))


def remap_transcript(
    transcript,
    short_item,
    video_path,
    transcript_path,
    keep_spans,
    media_duration,
    content_start,
    content_end,
):
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
                if (
                    word_start >= keep_start - 0.001
                    and word_end <= keep_end + 0.001
                    and word_start >= content_start - 0.001
                    and word_end <= content_end + 0.001
                ):
                    mapped_words.append({
                        **word,
                        "start": round(elapsed + word_start - keep_start, 3),
                        "end": round(elapsed + word_end - keep_start, 3),
                        "word": str(word.get("word", "")),
                        "input_program_range": word.get("program_range", {
                            "start_s": word_start, "end_s": word_end,
                        }),
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
        "input_timebase": transcript.get("timebase", "input_video_relative"),
        "segments": segments,
        "metadata": {
            "title": short_item.get("title", ""),
            "duration": round(media_duration, 3),
            "source_candidate_index": short_item.get("source_candidate_index"),
            "keep_spans": keep_spans,
        },
    }


def map_source_time_to_output(keep_spans, source_time):
    elapsed = 0.0
    for keep in keep_spans:
        keep_start = float(keep["start_time"])
        keep_end = float(keep["end_time"])
        if keep_start - 0.001 <= source_time <= keep_end + 0.001:
            return elapsed + max(0.0, min(source_time, keep_end) - keep_start)
        elapsed += keep_end - keep_start
    return elapsed


def executed_drop_spans(short_item):
    return list(short_item.get("filler_drop_spans") or [])


def write_shorts_summary(path, reports):
    lines = ["# Shorts Delivery", "", f"Verified horizontal shorts: {len(reports)}", ""]
    for report in reports:
        lines.extend([
            f"## {report['short_id']}", "",
            f"- Output: `{report['outputs']['horizontal_video']}`",
            f"- Duration: {report['actual_duration']:.3f}s",
            f"- Transcript within media: `{str(report['transcript_within_media']).lower()}`",
            f"- Warnings: {', '.join(report['warnings']) if report['warnings'] else 'None'}", "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def make_review_still(ffmpeg, video, output, duration):
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        ffmpeg, "-y", "-ss", f"{duration / 2:.6f}", "-i", str(video),
        "-frames:v", "1", "-vf", "scale=640:-2", str(output),
    ])


def run_extract(args):
    out_dir = Path(args.out).resolve()
    video_path = Path(args.video).resolve()
    project_root = Path(args.project_root).resolve() if args.project_root else None
    default_plan = "shorts-plan.json" if project_root else "shorts_plan.json"
    plan_path = Path(args.plan).resolve() if args.plan else out_dir / default_plan
    transcript_path = Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    for path, label in ((video_path, "video"), (plan_path, "plan"), (transcript_path, "transcript")):
        if not path.exists():
            fail(f"{label} not found: {path}")
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe or Path(ffmpeg).with_name("ffprobe.exe"))
    plan = load_json(plan_path)
    canonical = plan.get("schema_version") == 1
    if canonical and not project_root:
        fail("canonical shorts plan extraction requires --project-root")
    if project_root:
        validate_project_input(project_root, plan, video_path)
    validate_plan_review(out_dir, plan, video_path)
    transcript = load_json(transcript_path)
    source_probe = probe_media(ffprobe, video_path)
    media_duration = float(source_probe.get("format", {}).get("duration") or 0.0)
    shorts = plan.get("shorts") or []
    if not shorts:
        fail("shorts_plan.json contains no shorts")
    reports = []
    for short_item in shorts:
        refined = refined_boundary(
            short_item, transcript, ffmpeg, video_path, media_duration, args
        )
        keep_spans = extraction_keep_spans(short_item, refined)
        if canonical:
            paths = canonical_output_paths(project_root, short_item)
            short_dir = paths["work_directory"]
            source_path = paths["horizontal_video"]
            short_transcript_path = paths["transcript"]
            report_path = paths["extraction_report"]
        else:
            short_dir = output_dir_for_short(out_dir, short_item)
            source_path = short_dir / "source.mp4"
            short_transcript_path = short_dir / "transcript.json"
            report_path = short_dir / "extraction_report.json"
        short_dir.mkdir(parents=True, exist_ok=True)
        extract_keep_spans(ffmpeg, ffprobe, video_path, source_path, keep_spans)
        actual_duration = probe_duration(ffprobe, source_path)
        output_probe = probe_media(ffprobe, source_path)
        expected_duration = sum(span["end_time"] - span["start_time"] for span in keep_spans)
        validate_extracted_media(source_probe, output_probe, expected_duration)
        short_transcript = remap_transcript(
            transcript,
            short_item,
            video_path,
            transcript_path,
            keep_spans,
            actual_duration,
            float(refined["content_start_time"]),
            float(refined["content_end_time"]),
        )
        write_json(short_transcript_path, short_transcript)
        words = [word for segment in short_transcript["segments"] for word in segment.get("words") or []]
        last_word_end = max((float(word["end"]) for word in words), default=0.0)
        estimated_output_duration = expected_duration
        warnings = list(refined.get("warnings") or [])
        transcript_within_media = last_word_end <= actual_duration + 0.05
        content_end_in_output = map_source_time_to_output(
            keep_spans, float(refined["content_end_time"])
        )
        tail_margin = actual_duration - content_end_in_output
        transcript_tail_margin = actual_duration - last_word_end
        tail_release_verified = tail_margin + 0.001 >= args.min_tail_margin
        if tail_margin < args.min_tail_margin:
            warnings.append("LOW_TAIL_MARGIN")
        if not transcript_within_media:
            warnings.append("TRANSCRIPT_EXCEEDS_MEDIA_DURATION")
        refined_source_duration = refined["refined_end_time"] - refined["refined_start_time"]
        filler_removed_duration = refined_source_duration - estimated_output_duration
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
            "source_duration": round(refined_source_duration, 3),
            "filler_removed_duration": round(filler_removed_duration, 3),
            "estimated_output_duration": round(estimated_output_duration, 3),
            "actual_duration": round(actual_duration, 3),
            "transcript_last_word_end": round(last_word_end, 3),
            "content_end_in_output_s": round(content_end_in_output, 3),
            "tail_margin_s": round(tail_margin, 3),
            "transcript_tail_margin_s": round(transcript_tail_margin, 3),
            "tail_release_verified": tail_release_verified,
            "transcript_within_media": transcript_within_media,
            "boundary_refinement": refined,
            "warnings": list(dict.fromkeys(warnings)),
            "outputs": {
                "horizontal_video": str(source_path),
                "transcript": str(short_transcript_path),
                "extraction_report": str(report_path),
            },
        }
        write_json(report_path, report)
        if not tail_release_verified:
            fail(
                f"{report['short_id']} has only {tail_margin:.3f}s after its selected final word; "
                f"minimum is {args.min_tail_margin:.3f}s"
            )
        if canonical:
            short_item["status"] = "verified"
            short_item["actual_duration_s"] = round(actual_duration, 3)
            review_still = (
                project_root / "review" / "06-shorts"
                / f"{short_item['id']}-horizontal.jpg"
            )
            make_review_still(ffmpeg, source_path, review_still, actual_duration)
            report["outputs"]["review_still"] = str(review_still)
            write_json(report_path, report)
        reports.append(report)
        print(f"[video-to-shorts] extracted {report['short_id']}: {source_path}")
    summary_path = out_dir / "shorts_extraction_report.json"
    write_json(summary_path, {
        "schema_version": "shorts-extraction-report.v2", "source_video": str(video_path),
        "plan": str(plan_path), "transcript": str(transcript_path), "shorts": reports,
    })
    if canonical:
        write_json(plan_path, plan)
        review_summary = project_root / "review" / "06-shorts" / "shorts-summary.md"
        write_shorts_summary(review_summary, reports)
    print(f"[video-to-shorts] extracted_count: {len(reports)}")
    print(f"[video-to-shorts] extraction_report: {summary_path}")


def build_parser():
    parser = argparse.ArgumentParser(description="Extract horizontal shorts using planned keep_spans.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--transcript")
    parser.add_argument("--project-root")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    parser.add_argument(
        "--no-refine-boundaries",
        action="store_true",
        help="Disable semantic phrase snapping while retaining mandatory audio release handles.",
    )
    parser.add_argument("--pre-roll", type=float, default=0.25)
    parser.add_argument("--post-roll", type=float, default=0.30)
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    parser.add_argument("--max-duration", type=float, default=90.0)
    parser.add_argument("--min-tail-margin", type=float, default=0.25)
    return parser


def main(argv=None):
    run_extract(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
