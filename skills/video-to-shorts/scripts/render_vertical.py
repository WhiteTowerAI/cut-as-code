#!/usr/bin/env python3
"""Render a validated video-to-shorts vertical plan with ffmpeg."""

import argparse
import json
import math
import statistics
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat

from review_gate import (
      load_validated_vertical_review,
      open_vertical_review,
      sha256_file,
      validate_vertical_delivery_allowed,
)

RENDERABLE_STRATEGIES = {"STATIC_CROP", "SCENE_CROP", "LETTERBOX"}


def fail(message):
    raise SystemExit(message)


def run(command):
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(map(str, command)) + "\n" + process.stderr.strip())
    return process.stdout


def resolve_tool(name, explicit):
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path.resolve())
        fail(f"{name} not found: {path}")
    found = shutil.which(name)
    if found:
        return found
    fail(f"{name} not found; pass --{name} PATH")


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid JSON: {path}: {error}")


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_file_binding(binding, label):
    if not isinstance(binding, dict):
        fail(f"{label} binding is invalid")
    path = Path(binding.get("path", "")).resolve()
    if not path.is_file():
        fail(f"{label} no longer exists: {path}")
    stat = path.stat()
    if (
        binding.get("size") != stat.st_size
        or binding.get("modified_ns") != stat.st_mtime_ns
        or binding.get("sha256") != sha256_file(path)
    ):
        fail(f"{label} changed after vertical planning: {path}")
    return path


def probe_media(ffprobe, video):
    payload = json.loads(run([
        ffprobe, "-v", "error", "-show_entries",
        "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
        "-of", "json", str(video),
    ]))
    payload["path"] = str(video.resolve())
    return payload


def rational_fps(value):
    if isinstance(value, dict):
        numerator, denominator = value.get("num"), value.get("den")
        if (
            not isinstance(numerator, int) or isinstance(numerator, bool)
            or not isinstance(denominator, int) or isinstance(denominator, bool)
            or numerator <= 0 or denominator <= 0
        ):
            fail("source_fps must use positive integer num and den")
        rate = Fraction(numerator, denominator)
    else:
        rate = Fraction(str(value)).limit_denominator(100000)
    return {"num": rate.numerator, "den": rate.denominator}


def map_segments_to_render_source(segments, keep_spans):
    timeline_spans = []
    cursor = 0.0
    for index, span in enumerate(keep_spans):
        start = float(span["start_time"])
        end = float(span["end_time"])
        if end <= start:
            fail(f"direct_render.keep_spans[{index}] has invalid duration")
        duration = end - start
        timeline_spans.append({
            "short_start": cursor,
            "short_end": cursor + duration,
            "source_start": start,
        })
        cursor += duration
    mapped = []
    for segment in segments:
        segment_start = float(segment["start_time"])
        segment_end = float(segment["end_time"])
        for span in timeline_spans:
            overlap_start = max(segment_start, span["short_start"])
            overlap_end = min(segment_end, span["short_end"])
            if overlap_end - overlap_start <= 0.000001:
                continue
            mapped_segment = dict(segment)
            mapped_segment["short_start_time"] = round(overlap_start, 6)
            mapped_segment["short_end_time"] = round(overlap_end, 6)
            mapped_segment["start_time"] = round(
                span["source_start"] + overlap_start - span["short_start"], 6
            )
            mapped_segment["end_time"] = round(
                span["source_start"] + overlap_end - span["short_start"], 6
            )
            mapped.append(mapped_segment)
    if not mapped:
        fail("vertical plan does not overlap the bound source keep_spans")
    expected_duration = min(
        float(segments[-1]["end_time"]),
        sum(float(span["end_time"]) - float(span["start_time"]) for span in keep_spans),
    )
    mapped_duration = sum(segment["end_time"] - segment["start_time"] for segment in mapped)
    if abs(mapped_duration - expected_duration) > 0.05:
        fail("direct render mapping does not fully cover the vertical timeline")
    return mapped, mapped_duration


def normalized_keep_spans(value):
    if not isinstance(value, list) or not value:
        fail("bound extraction report keep_spans are invalid")
    normalized = []
    for index, span in enumerate(value):
        if not isinstance(span, dict):
            fail(f"bound extraction report keep_spans[{index}] is invalid")
        start = float(span.get("start_time"))
        end = float(span.get("end_time"))
        if end <= start:
            fail(f"bound extraction report keep_spans[{index}] has invalid duration")
        normalized.append({"start_time": round(start, 6), "end_time": round(end, 6)})
    return normalized


def direct_render_context(plan, horizontal_video, ffprobe):
    binding = plan.get("direct_render")
    if not binding:
        return None
    source_video = verify_file_binding(binding.get("source_video"), "direct render source")
    extraction_report = verify_file_binding(binding.get("extraction_report"), "extraction report")
    report = load_json(extraction_report)
    if Path(report.get("source_video", "")).resolve() != source_video:
        fail("bound extraction report points to a different render source")
    report_horizontal = Path((report.get("outputs") or {}).get("horizontal_video", "")).resolve()
    if report_horizontal != Path(horizontal_video).resolve():
        fail("bound extraction report points to a different horizontal short")
    if normalized_keep_spans(report.get("keep_spans")) != binding.get("keep_spans"):
        fail("bound extraction report keep_spans differ from the vertical plan")
    source_probe = probe_media(ffprobe, source_video)
    source_stream = next(
        (stream for stream in source_probe.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not source_stream:
        fail("direct render source has no video stream")
    if (
        int(source_stream.get("width", 0)) != int(plan["source_width"])
        or int(source_stream.get("height", 0)) != int(plan["source_height"])
        or Fraction(source_stream.get("avg_frame_rate") or "0/1")
        != Fraction(plan["source_fps"]["num"], plan["source_fps"]["den"])
    ):
        fail("direct render source geometry or FPS differs from the validated horizontal short")
    mapped_segments, mapped_duration = map_segments_to_render_source(
        plan["segments"], binding["keep_spans"]
    )
    render_plan = dict(plan)
    render_plan["segments"] = mapped_segments
    return source_video, source_probe, render_plan, mapped_duration, extraction_report


def dimensions_for_mode(plan, mode, preview_height):
    if mode == "final":
        return int(plan["output_width"]), int(plan["output_height"])
    height = min(int(preview_height), int(plan["output_height"]))
    height -= height % 2
    width = int(round(height * 9 / 16))
    width += width % 2
    return width, height


def black_edge_size(image, side, mean_limit=3.0, deviation_limit=3.0):
    width, height = image.size
    limit = height if side in {"top", "bottom"} else width
    size = 0
    for offset in range(limit):
        if side == "top":
            strip = image.crop((0, offset, width, offset + 1))
        elif side == "bottom":
            strip = image.crop((0, height - offset - 1, width, height - offset))
        elif side == "left":
            strip = image.crop((offset, 0, offset + 1, height))
        else:
            strip = image.crop((width - offset - 1, 0, width - offset, height))
        stats = ImageStat.Stat(strip)
        if stats.mean[0] > mean_limit or stats.stddev[0] > deviation_limit:
            break
        size += 1
    return size


def stable_edge(values, sample_count, minimum_size):
    required = math.ceil(sample_count * 0.75)
    candidates = [value for value in values if value >= minimum_size]
    if len(candidates) < required or max(candidates) - min(candidates) > 2:
        return 0
    return int(round(statistics.median(candidates)))


def detect_stable_black_bars(ffmpeg, video, work_dir, duration, source_width, source_height):
    sample_dir = work_dir / ".black_bar_samples"
    if sample_dir.exists():
        shutil.rmtree(sample_dir)
    sample_dir.mkdir(parents=True)
    sample_count = 9
    timestamps = [duration * (index + 0.5) / sample_count for index in range(sample_count)]
    edges = {"top": [], "bottom": [], "left": [], "right": []}
    sample_width = sample_height = 0
    try:
        for index, timestamp in enumerate(timestamps):
            frame_path = sample_dir / f"sample_{index:02d}.png"
            run([
                ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", str(video),
                "-frames:v", "1", "-vf", "scale=480:-2", "-update", "1", str(frame_path),
            ])
            with Image.open(frame_path) as frame:
                gray = frame.convert("L")
                sample_width, sample_height = gray.size
                for side in edges:
                    edges[side].append(black_edge_size(gray, side))
    finally:
        shutil.rmtree(sample_dir, ignore_errors=True)
    minimum_vertical = max(4, round(sample_height * 0.02))
    minimum_horizontal = max(4, round(sample_width * 0.02))
    stable = {
        "top": stable_edge(edges["top"], sample_count, minimum_vertical),
        "bottom": stable_edge(edges["bottom"], sample_count, minimum_vertical),
        "left": stable_edge(edges["left"], sample_count, minimum_horizontal),
        "right": stable_edge(edges["right"], sample_count, minimum_horizontal),
    }
    detected = any(stable.values())
    if detected:
        x = round(stable["left"] * source_width / sample_width)
        y = round(stable["top"] * source_height / sample_height)
        right = round(stable["right"] * source_width / sample_width)
        bottom = round(stable["bottom"] * source_height / sample_height)
        x -= x % 2
        y -= y % 2
        crop_width = source_width - x - right
        crop_height = source_height - y - bottom
        crop_width -= crop_width % 2
        crop_height -= crop_height % 2
        if crop_width < source_width * 0.35 or crop_height < source_height * 0.35:
            detected = False
    if not detected:
        x, y, crop_width, crop_height = 0, 0, source_width, source_height
    return {
        "mode": "stable_active_picture" if detected else "full_frame_fallback",
        "detected": detected,
        "sample_count": sample_count,
        "sample_edges": edges,
        "stable_sample_edges": stable,
        "background_crop": {"x": x, "y": y, "width": crop_width, "height": crop_height},
        "foreground_crop_applied": False,
    }


def segment_video_filters(segment, index, output_width, output_height):
    strategy = segment["strategy"]
    if strategy in {"STATIC_CROP", "SCENE_CROP"}:
        return [
            (
                f"[0:v]trim=start={segment['start_time']:.6f}:end={segment['end_time']:.6f},setpts=PTS-STARTPTS,"
                f"crop={segment['crop_width']}:{segment['crop_height']}:{segment['crop_x']}:{segment['crop_y']},"
                f"scale={output_width}:{output_height}:flags=lanczos,setsar=1[v{index}]"
            )
        ]
    fail(f"segment strategy is not renderable: {strategy}")


def render(
    ffmpeg, source_probe, video, plan, output, output_width, output_height, fps,
    background_analysis, video_preset="medium", video_crf=20,
):
    has_audio = any(stream.get("codec_type") == "audio" for stream in source_probe.get("streams", []))
    filters = []
    concat_inputs = []
    for index, segment in enumerate(plan["segments"]):
        start = segment["start_time"]
        end = segment["end_time"]
        if segment["strategy"] == "LETTERBOX":
            background_crop = background_analysis["background_crop"]
            filters.extend([
                f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[base{index}]",
                f"[base{index}]split=2[bg{index}][fg{index}]",
                (
                    f"[bg{index}]crop={background_crop['width']}:{background_crop['height']}:"
                    f"{background_crop['x']}:{background_crop['y']},"
                    f"scale={output_width}:{output_height}:force_original_aspect_ratio=increase:flags=lanczos,"
                    f"crop={output_width}:{output_height},gblur=sigma=28,eq=brightness=-0.12:saturation=0.75,setsar=1[blur{index}]"
                ),
                (
                    f"[fg{index}]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
                    f"setsar=1[fit{index}]"
                ),
                (
                    f"[blur{index}][fit{index}]overlay=(W-w)/2:(H-h)/2:shortest=1,"
                    f"format=yuv420p[v{index}]"
                ),
            ])
        else:
            filters.extend(segment_video_filters(segment, index, output_width, output_height))
        concat_inputs.append(f"[v{index}]")
        if has_audio:
            filters.append(f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{index}]")
            concat_inputs.append(f"[a{index}]")
    if has_audio:
        filters.append("".join(concat_inputs) + f"concat=n={len(plan['segments'])}:v=1:a=1[vout][aout]")
    else:
        filters.append("".join(concat_inputs) + f"concat=n={len(plan['segments'])}:v=1:a=0[vout]")
    command = [
        ffmpeg, "-y", "-i", str(video), "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-c:v", "libx264", "-preset", str(video_preset),
        "-crf", str(video_crf),
        "-r", f"{fps['num']}/{fps['den']}", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    if has_audio:
        command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    command.append(str(output))
    run(command)


def validate_rendered_media(probe, width, height, duration, fps, require_audio):
    video = next(
        (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not video or int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        fail("vertical render dimensions do not match the plan")
    actual_rate = Fraction(video.get("avg_frame_rate") or "0/1")
    expected_rate = Fraction(fps["num"], fps["den"])
    if actual_rate != expected_rate:
        fail("vertical render frame rate does not match the rational source FPS")
    actual_duration = float(probe.get("format", {}).get("duration") or 0.0)
    if abs(actual_duration - float(duration)) > max(0.1, 2 / float(expected_rate)):
        fail("vertical render duration does not match the source short")
    if require_audio and not any(
        stream.get("codec_type") == "audio" for stream in probe.get("streams", [])
    ):
        fail("vertical render lost the source audio stream")


def make_contact_sheet(ffmpeg, video, output, duration, label):
    temp_dir = output.parent / ".contact_sheet_frames"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    count = 9
    timestamps = [duration * (index + 0.5) / count for index in range(count)]
    frames = []
    for index, timestamp in enumerate(timestamps):
        frame_path = temp_dir / f"frame_{index:02d}.png"
        run([ffmpeg, "-y", "-ss", f"{max(0.0, timestamp):.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=270:-2", str(frame_path)])
        frames.append((timestamp, frame_path))
    with Image.open(frames[0][1]) as sample:
        cell_width, image_height = sample.size
    label_height = 34
    sheet = Image.new("RGB", (cell_width * 3, (image_height + label_height) * 3), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (timestamp, frame_path) in enumerate(frames):
        with Image.open(frame_path) as image:
            image = image.convert("RGB")
            x = index % 3 * cell_width
            y = index // 3 * (image_height + label_height)
            sheet.paste(image, (x, y))
            draw.rectangle((x, y + image_height, x + cell_width, y + image_height + label_height), fill="#111827")
            draw.text((x + 8, y + image_height + 10), f"{label}  {timestamp:.2f}s", fill="white", font=font)
    sheet.save(output, quality=92)
    shutil.rmtree(temp_dir)


def write_summary(path, mode, plan, source, output=None, output_probe=None, contact_sheet=None, note=None):
    write_json(path, {
        "schema_version": f"video-to-shorts.vertical-{mode}-summary.v1",
        "mode": mode,
        "source": str(source),
        "strategy": plan["strategy"],
        "target_aspect_ratio": plan["target_aspect_ratio"],
        "renderable": plan.get("render_allowed", plan["strategy"] != "REVIEW_REQUIRED") is True,
        "output": str(output) if output else None,
        "contact_sheet": str(contact_sheet) if contact_sheet else None,
        "output_probe": output_probe,
        "segments": plan["segments"],
        "warnings": [*plan.get("warnings", []), *plan.get("validator_warnings", [])],
        "note": note,
    })


def main():
    parser = argparse.ArgumentParser(description="Render a validated vertical plan.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", required=True, choices=("preview", "final"))
    parser.add_argument("--preview-height", type=int, default=640)
    parser.add_argument("--review-out", help="User-facing preview/contact-sheet directory.")
    parser.add_argument("--final-output", help="Override the validated formal output path.")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()
    video = Path(args.video).resolve()
    plan_path = Path(args.plan).resolve()
    root = Path(args.out).resolve()
    if not video.exists():
        fail(f"video not found: {video}")
    if not plan_path.exists():
        fail(f"plan not found: {plan_path}")
    validate_vertical_delivery_allowed(video)
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe)
    if args.mode == "final":
        _review, plan = load_validated_vertical_review(root, video, plan_path)
    else:
        plan = load_json(plan_path)
    if plan.get("schema_version") != "video-to-shorts.vertical-plan.v1":
        fail("plan must be a validated video-to-shorts.vertical-plan.v1 file")
    if str(Path(plan.get("source_video", "")).resolve()) != str(video):
        fail("plan source_video does not match --video")
    source_probe = probe_media(ffprobe, video)
    source_video_stream = next((stream for stream in source_probe.get("streams", []) if stream.get("codec_type") == "video"), None)
    if not source_video_stream:
        fail("source has no video stream")
    if int(source_video_stream.get("width", 0)) != int(plan.get("source_width", -1)) or int(source_video_stream.get("height", 0)) != int(plan.get("source_height", -1)):
        fail("source dimensions no longer match validated plan")
    fps = rational_fps(plan.get("source_fps") or 30.0)
    if Fraction(source_video_stream.get("avg_frame_rate") or "0/1") != Fraction(fps["num"], fps["den"]):
        fail("source FPS no longer matches the validated vertical plan")
    source_duration = float(source_probe.get("format", {}).get("duration") or 0.0)
    if abs(source_duration - float(plan.get("source_duration_s", 0.0))) > max(
        0.1, 2 / float(Fraction(fps["num"], fps["den"]))
    ):
        fail("source duration no longer matches the validated vertical plan")
    slug = video.stem[:-len("-horizontal")] if video.stem.endswith("-horizontal") else video.stem
    review_destination = Path(args.review_out).resolve() if args.review_out else None
    review_page_directory = review_destination or root / "review"
    if args.mode == "preview":
        destination = review_destination or root / "preview"
        output_path = destination / (
            f"{slug}-vertical-preview.mp4" if review_destination else "vertical_preview.mp4"
        )
        contact_path = destination / (
            f"{slug}-vertical-contact-sheet.jpg" if review_destination else "preview_contact_sheet.jpg"
        )
        summary_path = destination / (
            f"{slug}-vertical-preview-summary.json" if review_destination else "preview_summary.json"
        )
        probe_path = destination / (
            f"{slug}-vertical-preview-probe.json" if review_destination else "media_probe.json"
        )
    else:
        output_value = args.final_output or plan.get("output_video")
        if not output_value:
            fail("formal vertical output is missing from the plan")
        output_path = Path(output_value).resolve()
        if output_path == video:
            fail("formal vertical output must exist in the plan and not overwrite its input")
        destination = review_destination or output_path.parent
        contact_path = destination / (
            f"{slug}-vertical-final-contact-sheet.jpg" if review_destination else "final_contact_sheet.jpg"
        )
        summary_path = destination / (
            f"{slug}-vertical-final-summary.json" if review_destination else "final_summary.json"
        )
        probe_path = destination / (
            f"{slug}-vertical-final-probe.json" if review_destination else "media_probe.json"
        )
    destination.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if plan.get("strategy") == "REVIEW_REQUIRED":
        write_json(probe_path, {"source": source_probe, "output": None, "status": "REVIEW_REQUIRED"})
        note = "`REVIEW_REQUIRED` is a valid review outcome. No media was rendered because the evidence does not support a safe deterministic crop."
        write_summary(summary_path, args.mode, plan, video, note=note)
        if args.mode == "final":
            fail(f"REVIEW_REQUIRED plans cannot be rendered; summary: {summary_path}")
        review_path, question_path, review_page = open_vertical_review(
            root, video, plan_path, summary_path, probe_path,
            review_out=review_page_directory, short_id=slug,
        )
        print(f"[video-to-shorts] review summary: {summary_path}")
        print(f"[video-to-shorts] vertical review: {review_path}")
        print(f"[video-to-shorts] fixed question: {question_path}")
        print(f"[video-to-shorts] authoritative page: {review_page}")
        print("[video-to-shorts] STOP: show the question to the user and end the current turn")
        return
    if plan.get("strategy") not in RENDERABLE_STRATEGIES:
        fail(f"unsupported plan strategy: {plan.get('strategy')}")
    if args.mode == "final" and plan.get("render_allowed") is not True:
        fail("formal render is not allowed by the validated plan")
    output_width, output_height = dimensions_for_mode(plan, args.mode, args.preview_height)
    render_video = video
    render_probe = source_probe
    render_plan = plan
    expected_duration = float(plan["source_duration_s"])
    direct_context = direct_render_context(plan, video, ffprobe) if args.mode == "final" else None
    extraction_report = None
    if direct_context:
        render_video, render_probe, render_plan, expected_duration, extraction_report = direct_context
    if any(segment["strategy"] == "LETTERBOX" for segment in plan["segments"]):
        background_analysis = detect_stable_black_bars(
            ffmpeg, video, destination, float(plan["source_duration_s"]),
            int(plan["source_width"]), int(plan["source_height"]),
        )
    else:
        background_analysis = {
            "mode": "not_used",
            "detected": False,
            "background_crop": {"x": 0, "y": 0, "width": int(plan["source_width"]), "height": int(plan["source_height"])},
            "foreground_crop_applied": False,
        }
    render(
        ffmpeg, render_probe, render_video, render_plan, output_path,
        output_width, output_height, fps, background_analysis,
        video_preset="slow" if args.mode == "final" else "medium",
        video_crf=16 if args.mode == "final" else 20,
    )
    output_probe = probe_media(ffprobe, output_path)
    validate_rendered_media(
        output_probe, output_width, output_height, expected_duration, fps,
        any(stream.get("codec_type") == "audio" for stream in render_probe.get("streams", [])),
    )
    duration = float(output_probe.get("format", {}).get("duration") or 0.0)
    make_contact_sheet(ffmpeg, output_path, contact_path, duration, args.mode)
    write_json(probe_path, {
        "planning_source": source_probe,
        "render_source": render_probe,
        "direct_render": bool(direct_context),
        "encoding": {
            "video_codec": "libx264",
            "preset": "slow" if args.mode == "final" else "medium",
            "crf": 16 if args.mode == "final" else 20,
            "pixel_format": "yuv420p",
        },
        "extraction_report": str(extraction_report) if extraction_report else None,
        "output": output_probe,
        "plan": str(plan_path),
        "letterbox_background": background_analysis,
    })
    write_summary(summary_path, args.mode, plan, video, output_path, output_probe, contact_path)
    if args.mode == "preview":
        review_path, question_path, review_page = open_vertical_review(
            root, video, plan_path, summary_path, probe_path, output_path, contact_path,
            review_out=review_page_directory, short_id=slug,
        )
    print(f"[video-to-shorts] vertical {args.mode}: {output_path}")
    print(f"[video-to-shorts] contact sheet: {contact_path}")
    print(f"[video-to-shorts] media probe: {probe_path}")
    print(f"[video-to-shorts] summary: {summary_path}")
    if args.mode == "preview":
        print(f"[video-to-shorts] vertical review: {review_path}")
        print(f"[video-to-shorts] fixed question: {question_path}")
        print(f"[video-to-shorts] authoritative page: {review_page}")
        print("[video-to-shorts] STOP: show the question to the user and end the current turn")


if __name__ == "__main__":
    main()
