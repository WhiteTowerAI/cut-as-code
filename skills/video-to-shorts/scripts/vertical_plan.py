#!/usr/bin/env python3
"""Validate and normalize an Agent-authored vertical delivery plan."""

import argparse
import html
import json
import math
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from review_gate import sha256_file, validate_vertical_delivery_allowed


ALLOWED_STRATEGIES = {"STATIC_CROP", "SCENE_CROP", "LETTERBOX", "REVIEW_REQUIRED"}
ALLOWED_CONTENT_TYPES = {"PRESENTER", "WIDE_INFORMATION", "PRODUCT", "MULTI_SUBJECT", "OTHER", "UNSPECIFIED"}
STRATEGY_ORDER = ("STATIC_CROP", "SCENE_CROP", "LETTERBOX", "REVIEW_REQUIRED")
TIME_TOLERANCE = 0.05
RATIO_TOLERANCE = 0.002


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


def file_binding(path):
    path = Path(path).resolve()
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def parse_rate(value):
    rate = Fraction(value)
    if rate <= 0:
        fail(f"invalid frame rate: {value}")
    return {"num": rate.numerator, "den": rate.denominator}


def probe_video(ffprobe, video):
    payload = json.loads(run([
        ffprobe, "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,width,height,avg_frame_rate,r_frame_rate",
        "-of", "json", str(video),
    ]))
    video_stream = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), None)
    if not video_stream:
        fail(f"source has no video stream: {video}")
    duration = float(payload.get("format", {}).get("duration") or 0.0)
    if duration <= 0:
        fail(f"source duration is invalid: {duration}")
    rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1"
    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": parse_rate(rate),
        "duration_s": round(duration, 6),
    }


def even_round(value):
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else rounded + 1


def number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        fail(f"{field} must be a finite number")
    return float(value)


def integer(value, field):
    numeric = number(value, field)
    if not numeric.is_integer():
        fail(f"{field} must be an integer")
    return int(numeric)


def validate_segment(segment, index, source, duration):
    if not isinstance(segment, dict):
        fail(f"segments[{index}] must be an object")
    prefix = f"segments[{index}]"
    start = number(segment.get("start_time"), f"{prefix}.start_time")
    end = number(segment.get("end_time"), f"{prefix}.end_time")
    if start < -TIME_TOLERANCE or end > duration + TIME_TOLERANCE or end <= start:
        fail(f"{prefix} time range must satisfy 0 <= start_time < end_time <= {duration:.3f}")
    strategy = segment.get("strategy")
    if strategy not in ALLOWED_STRATEGIES:
        fail(f"{prefix}.strategy must be one of {sorted(ALLOWED_STRATEGIES)}")
    content_type = segment.get("content_type", "UNSPECIFIED")
    if content_type not in ALLOWED_CONTENT_TYPES:
        fail(f"{prefix}.content_type must be one of {sorted(ALLOWED_CONTENT_TYPES - {'UNSPECIFIED'})}")
    reason = segment.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        fail(f"{prefix}.reason is required")
    normalized = {
        "start_time": round(max(0.0, start), 6),
        "end_time": round(min(duration, end), 6),
        "strategy": strategy,
        "content_type": content_type,
    }
    if strategy in {"STATIC_CROP", "SCENE_CROP"}:
        crop_x = integer(segment.get("crop_x"), f"{prefix}.crop_x")
        crop_y = integer(segment.get("crop_y"), f"{prefix}.crop_y")
        crop_width = integer(segment.get("crop_width"), f"{prefix}.crop_width")
        crop_height = integer(segment.get("crop_height"), f"{prefix}.crop_height")
        if crop_x < 0 or crop_y < 0 or crop_width <= 0 or crop_height <= 0:
            fail(f"{prefix} crop values must be non-negative with positive width and height")
        if crop_x + crop_width > source["width"] or crop_y + crop_height > source["height"]:
            fail(f"{prefix} crop exceeds source bounds {source['width']}x{source['height']}")
        if abs((crop_width / crop_height) - (9 / 16)) > RATIO_TOLERANCE:
            fail(f"{prefix} crop must match target aspect ratio 9:16")
        normalized.update({
            "crop_x": crop_x,
            "crop_y": crop_y,
            "crop_width": crop_width,
            "crop_height": crop_height,
        })
    normalized["reason"] = reason.strip()
    return normalized


def summarize_strategies(segments, duration):
    totals = {strategy: 0.0 for strategy in STRATEGY_ORDER}
    for segment in segments:
        totals[segment["strategy"]] += segment["end_time"] - segment["start_time"]
    return {
        strategy: {
            "duration_s": round(totals[strategy], 6),
            "percentage": round((totals[strategy] / duration) * 100, 2) if duration else 0.0,
        }
        for strategy in STRATEGY_ORDER
    }


def build_validator_warnings(strategy, segments, strategy_summary):
    warnings = []
    letterbox = strategy_summary["LETTERBOX"]
    if strategy == "LETTERBOX" and letterbox["percentage"] >= 99.99:
        warnings.append(
            "LETTERBOX covers the complete short. Confirm that each stable presenter or product scene was considered for a safe fixed crop and document why segment-level SCENE_CROP is not appropriate."
        )
    presenter_letterbox = [
        segment for segment in segments
        if segment["content_type"] == "PRESENTER" and segment["strategy"] == "LETTERBOX"
    ]
    for segment in presenter_letterbox:
        warnings.append(
            f"PRESENTER segment {segment['start_time']:.3f}-{segment['end_time']:.3f}s uses LETTERBOX. Confirm that no fixed 9:16 crop can keep the speaker's head and torso visible at an adequate vertical viewing size."
        )
    if any(segment["content_type"] == "PRESENTER" for segment in segments) and letterbox["percentage"] > 50:
        warnings.append(
            f"LETTERBOX covers {letterbox['percentage']:.2f}% of a plan containing presenter content. Confirm that LETTERBOX is limited to scenes with essential horizontal information."
        )
    if any(segment["content_type"] == "UNSPECIFIED" for segment in segments):
        warnings.append(
            "One or more segments omit content_type. New Agent-authored plans should classify every segment so presenter-led LETTERBOX decisions receive deterministic review prompts."
        )
    return warnings


def validate_plan(raw, video, source):
    if not isinstance(raw, dict):
        fail("plan root must be an object")
    if raw.get("target_aspect_ratio") != "9:16":
        fail('target_aspect_ratio must be "9:16"')
    strategy = raw.get("strategy")
    if strategy not in ALLOWED_STRATEGIES:
        fail(f"strategy must be one of {sorted(ALLOWED_STRATEGIES)}")
    segments = raw.get("segments")
    if not isinstance(segments, list) or not segments:
        fail("segments must be a non-empty array")
    normalized_segments = [validate_segment(segment, index, source, source["duration_s"]) for index, segment in enumerate(segments)]
    previous_end = 0.0
    for index, segment in enumerate(normalized_segments):
        if segment["start_time"] + TIME_TOLERANCE < previous_end:
            fail(f"segments[{index}] overlaps or is not sorted")
        if abs(segment["start_time"] - previous_end) > TIME_TOLERANCE:
            fail(f"segments do not fully cover the render timeline near {previous_end:.3f}s")
        previous_end = segment["end_time"]
    if abs(previous_end - source["duration_s"]) > TIME_TOLERANCE:
        fail(f"segments do not cover source end {source['duration_s']:.3f}s")
    if strategy == "STATIC_CROP":
        if len(normalized_segments) != 1 or normalized_segments[0]["strategy"] != "STATIC_CROP":
            fail("STATIC_CROP requires exactly one STATIC_CROP segment")
    elif strategy == "SCENE_CROP":
        if any(segment["strategy"] not in {"SCENE_CROP", "STATIC_CROP", "LETTERBOX"} for segment in normalized_segments):
            fail("SCENE_CROP segments may use SCENE_CROP, STATIC_CROP, or LETTERBOX")
    elif strategy == "LETTERBOX":
        if any(segment["strategy"] != "LETTERBOX" for segment in normalized_segments):
            fail("LETTERBOX requires LETTERBOX segments")
    elif strategy == "REVIEW_REQUIRED":
        if any(segment["strategy"] != "REVIEW_REQUIRED" for segment in normalized_segments):
            fail("REVIEW_REQUIRED requires REVIEW_REQUIRED segments")
    evidence = raw.get("visual_evidence", [])
    if not isinstance(evidence, list):
        fail("visual_evidence must be an array")
    normalized_evidence = []
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            fail(f"visual_evidence[{index}] must be an object")
        timestamp = number(item.get("timestamp_s"), f"visual_evidence[{index}].timestamp_s")
        if timestamp < -TIME_TOLERANCE or timestamp > source["duration_s"] + TIME_TOLERANCE:
            fail(f"visual_evidence[{index}].timestamp_s is outside the short timeline")
        frame_path = item.get("frame_path")
        observation = item.get("observation")
        if not isinstance(frame_path, str) or not frame_path.strip():
            fail(f"visual_evidence[{index}].frame_path is required")
        if not isinstance(observation, str) or not observation.strip():
            fail(f"visual_evidence[{index}].observation is required")
        normalized_evidence.append({
            "timestamp_s": round(max(0.0, min(source["duration_s"], timestamp)), 6),
            "frame_path": frame_path.strip(),
            "observation": observation.strip(),
        })
    warnings = raw.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        fail("warnings must be an array of strings")
    strategy_summary = summarize_strategies(normalized_segments, source["duration_s"])
    validator_warnings = build_validator_warnings(strategy, normalized_segments, strategy_summary)
    output_height = source["height"]
    output_width = even_round(output_height * 9 / 16)
    return {
        "schema_version": "video-to-shorts.vertical-plan.v1",
        "source_video": str(video),
        "target_aspect_ratio": "9:16",
        "source_width": source["width"],
        "source_height": source["height"],
        "source_fps": source["fps"],
        "source_duration_s": source["duration_s"],
        "output_width": output_width,
        "output_height": output_height,
        "strategy": strategy,
        "segments": normalized_segments,
        "strategy_summary": strategy_summary,
        "visual_evidence": normalized_evidence,
        "warnings": warnings,
        "validator_warnings": validator_warnings,
        "render_allowed": strategy != "REVIEW_REQUIRED",
    }


def validate_vertical_plan_data(plan, video, source):
    """Validate an already-normalized plan against its bound source probe."""
    if not isinstance(plan, dict) or plan.get("schema_version") != "video-to-shorts.vertical-plan.v1":
        fail("plan must use video-to-shorts.vertical-plan.v1")
    video = Path(video).resolve()
    if Path(plan.get("source_video", "")).resolve() != video:
        fail("plan source_video does not match the reviewed source")
    width = integer(source.get("width"), "source.width")
    height = integer(source.get("height"), "source.height")
    duration = number(source.get("duration_s"), "source.duration_s")
    if width <= 0 or height <= 0 or duration <= 0:
        fail("source dimensions and duration must be positive")
    fps = source.get("fps")
    if not isinstance(fps, dict):
        fail("source.fps must use num and den")
    num = integer(fps.get("num"), "source.fps.num")
    den = integer(fps.get("den"), "source.fps.den")
    if num <= 0 or den <= 0:
        fail("source FPS must be positive")
    normalized_source = {
        "width": width, "height": height, "duration_s": duration,
        "fps": {"num": num, "den": den},
    }
    if integer(plan.get("source_width"), "source_width") != width:
        fail("plan source_width does not match the reviewed source")
    if integer(plan.get("source_height"), "source_height") != height:
        fail("plan source_height does not match the reviewed source")
    if plan.get("source_fps") != normalized_source["fps"]:
        fail("plan source_fps does not match the reviewed source")
    if abs(number(plan.get("source_duration_s"), "source_duration_s") - duration) > TIME_TOLERANCE:
        fail("plan source_duration_s does not match the reviewed source")
    validated = validate_plan(plan, video, normalized_source)
    if integer(plan.get("output_width"), "output_width") != validated["output_width"]:
        fail("plan output_width does not match deterministic validation")
    if integer(plan.get("output_height"), "output_height") != validated["output_height"]:
        fail("plan output_height does not match deterministic validation")
    if plan.get("render_allowed") is not validated["render_allowed"]:
        fail("plan render_allowed does not match its strategy")
    if "output_video" in plan:
        validated["output_video"] = plan["output_video"]
    return validated
def validate_keep_spans(value, source_duration_s):
    if not isinstance(value, list) or not value:
        fail("extraction report keep_spans must be a non-empty array")
    normalized = []
    previous_end = -1.0
    for index, span in enumerate(value):
        if not isinstance(span, dict):
            fail(f"extraction report keep_spans[{index}] must be an object")
        start = number(span.get("start_time"), f"keep_spans[{index}].start_time")
        end = number(span.get("end_time"), f"keep_spans[{index}].end_time")
        if start < 0 or end <= start or end > source_duration_s + TIME_TOLERANCE:
            fail(f"keep_spans[{index}] must satisfy 0 <= start_time < end_time <= {source_duration_s:.3f}")
        if start < previous_end - TIME_TOLERANCE:
            fail(f"keep_spans[{index}] overlaps or is not sorted")
        normalized.append({"start_time": round(start, 6), "end_time": round(end, 6)})
        previous_end = end
    return normalized


def bind_direct_render(plan, horizontal_video, horizontal_source, source_video, extraction_report, ffprobe):
    source_video = Path(source_video).resolve()
    extraction_report = Path(extraction_report).resolve()
    if not source_video.is_file():
        fail(f"direct render source not found: {source_video}")
    if not extraction_report.is_file():
        fail(f"extraction report not found: {extraction_report}")
    report = load_json(extraction_report)
    if report.get("schema_version") != "short-extraction-report.v2":
        fail("direct rendering requires short-extraction-report.v2")
    if Path(report.get("source_video", "")).resolve() != source_video:
        fail("extraction report source_video does not match --source-video")
    report_horizontal = Path((report.get("outputs") or {}).get("horizontal_video", "")).resolve()
    if report_horizontal != Path(horizontal_video).resolve():
        fail("extraction report horizontal_video does not match --video")
    render_source = probe_video(ffprobe, source_video)
    if (
        render_source["width"] != horizontal_source["width"]
        or render_source["height"] != horizontal_source["height"]
        or render_source["fps"] != horizontal_source["fps"]
    ):
        fail("direct render source geometry or FPS differs from the horizontal short")
    keep_spans = validate_keep_spans(report.get("keep_spans"), render_source["duration_s"])
    mapped_duration = sum(span["end_time"] - span["start_time"] for span in keep_spans)
    fps_value = horizontal_source["fps"]["num"] / horizontal_source["fps"]["den"]
    if abs(mapped_duration - horizontal_source["duration_s"]) > max(0.1, 2 / fps_value):
        fail("extraction report keep_spans duration does not match the horizontal short")
    plan["direct_render"] = {
        "source_video": file_binding(source_video),
        "extraction_report": file_binding(extraction_report),
        "keep_spans": keep_spans,
        "mapped_duration_s": round(mapped_duration, 6),
    }
    return plan


def write_markdown(path, plan):
    fps = plan["source_fps"]
    fps_value = fps["num"] / fps["den"]
    lines = [
        "# Vertical Plan Preview",
        "",
        f"- Source: `{plan['source_video']}`",
        f"- Source media: {plan['source_width']}x{plan['source_height']} at {fps_value:.3f} fps (`{fps['num']}/{fps['den']}`)",
        f"- Duration: {plan['source_duration_s']:.3f}s",
        f"- Output: {plan['output_width']}x{plan['output_height']} (`{plan['target_aspect_ratio']}`)",
        f"- Strategy: `{plan['strategy']}`",
        f"- Formal render allowed: `{str(plan['render_allowed']).lower()}`",
        "",
        "## Strategy Duration",
        "",
    ]
    if plan.get("direct_render"):
        lines[8:8] = [
            f"- Formal render source: `{plan['direct_render']['source_video']['path']}`",
            "- Formal render generations after the bound source: `1`",
        ]
    for strategy in STRATEGY_ORDER:
        item = plan["strategy_summary"][strategy]
        lines.append(f"- `{strategy}`: {item['duration_s']:.3f}s ({item['percentage']:.2f}%)")
    lines.extend([
        "",
        "## Segments",
        "",
    ])
    for index, segment in enumerate(plan["segments"], 1):
        crop = ""
        if "crop_x" in segment:
            crop = f"; crop=({segment['crop_x']},{segment['crop_y']}) {segment['crop_width']}x{segment['crop_height']}"
        lines.append(f"{index}. `{segment['start_time']:.3f}` - `{segment['end_time']:.3f}` `{segment['strategy']}` `{segment['content_type']}`{crop}  ")
        lines.append(f"   Reason: {segment['reason']}")
    lines.extend(["", "## Visual Evidence", ""])
    if plan["visual_evidence"]:
        for item in plan["visual_evidence"]:
            lines.append(f"- `{item['timestamp_s']:.3f}s` `{item['frame_path']}` - {item['observation']}")
    else:
        lines.append("- No visual evidence entries were provided.")
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in plan["warnings"]] or ["- None."])
    lines.extend(["", "## Validator Warnings", ""])
    lines.extend([f"- {warning}" for warning in plan["validator_warnings"]] or ["- None."])
    if plan["strategy"] == "REVIEW_REQUIRED":
        lines.extend(["", "`REVIEW_REQUIRED` is a valid review outcome. Formal rendering is intentionally blocked."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(path, plan):
    def esc(value):
        return html.escape(str(value))

    rows = []
    for segment in plan["segments"]:
        crop = "-"
        if "crop_x" in segment:
            crop = f"({segment['crop_x']}, {segment['crop_y']}) {segment['crop_width']}x{segment['crop_height']}"
        rows.append(
            "<tr>"
            f"<td>{segment['start_time']:.3f} - {segment['end_time']:.3f}</td>"
            f"<td><code>{esc(segment['strategy'])}</code></td>"
            f"<td><code>{esc(segment['content_type'])}</code></td>"
            f"<td>{esc(crop)}</td><td>{esc(segment['reason'])}</td>"
            "</tr>"
        )
    evidence = "".join(
        f"<li><code>{item['timestamp_s']:.3f}s</code> <code>{esc(item['frame_path'])}</code> - {esc(item['observation'])}</li>"
        for item in plan["visual_evidence"]
    ) or "<li>No visual evidence entries were provided.</li>"
    warnings = "".join(f"<li>{esc(item)}</li>" for item in plan["warnings"]) or "<li>None.</li>"
    validator_warnings = "".join(f"<li>{esc(item)}</li>" for item in plan["validator_warnings"]) or "<li>None.</li>"
    strategy_summary = "".join(
        f"<li><code>{strategy}</code>: {plan['strategy_summary'][strategy]['duration_s']:.3f}s ({plan['strategy_summary'][strategy]['percentage']:.2f}%)</li>"
        for strategy in STRATEGY_ORDER
    )
    review_note = "<p class='notice'>REVIEW_REQUIRED is a valid review outcome. Formal rendering is intentionally blocked.</p>" if plan["strategy"] == "REVIEW_REQUIRED" else ""
    fps = plan["source_fps"]
    fps_value = fps["num"] / fps["den"]
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vertical Plan Preview</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f3f4f6;color:#111827}}main{{max-width:1100px;margin:32px auto;background:white;padding:28px;border-radius:14px;box-shadow:0 8px 30px #0001}}
h1,h2{{margin-top:0}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:20px 0}}.card{{background:#f8fafc;padding:12px;border-radius:8px}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #e5e7eb;padding:10px}}code{{background:#eef2ff;padding:2px 5px;border-radius:4px}}.notice{{background:#fff7ed;border-left:4px solid #f97316;padding:12px}}
</style></head><body><main><h1>Vertical Plan Preview</h1>
<div class="meta"><div class="card"><strong>Source</strong><br>{esc(plan['source_video'])}</div><div class="card"><strong>Media</strong><br>{plan['source_width']}x{plan['source_height']} / {fps_value:.3f} fps ({fps['num']}/{fps['den']}) / {plan['source_duration_s']:.3f}s</div><div class="card"><strong>Output</strong><br>{plan['output_width']}x{plan['output_height']} / 9:16</div><div class="card"><strong>Strategy</strong><br><code>{esc(plan['strategy'])}</code></div></div>
{review_note}<h2>Strategy Duration</h2><ul>{strategy_summary}</ul><h2>Segments</h2><table><thead><tr><th>Time</th><th>Strategy</th><th>Content</th><th>Crop</th><th>Reason</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Visual Evidence</h2><ul>{evidence}</ul><h2>Warnings</h2><ul>{warnings}</ul><h2>Validator Warnings</h2><ul>{validator_warnings}</ul></main></body></html>"""
    path.write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Validate an Agent-authored vertical plan.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-video", help="Original verified render used for one-generation final vertical rendering.")
    parser.add_argument("--extraction-report", help="Horizontal short extraction report containing source keep_spans.")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()
    video = Path(args.video).resolve()
    input_path = Path(args.input).resolve()
    out = Path(args.out).resolve()
    if not video.exists():
        fail(f"video not found: {video}")
    if not input_path.exists():
        fail(f"plan input not found: {input_path}")
    validate_vertical_delivery_allowed(video)
    out.mkdir(parents=True, exist_ok=True)
    ffprobe = resolve_tool("ffprobe", args.ffprobe)
    source = probe_video(ffprobe, video)
    plan = validate_plan(load_json(input_path), video, source)
    if bool(args.source_video) != bool(args.extraction_report):
        fail("--source-video and --extraction-report must be provided together")
    if args.source_video:
        plan = bind_direct_render(
            plan, video, source, args.source_video, args.extraction_report, ffprobe
        )
    if video.name.lower().endswith("-horizontal.mp4") and video.parent.name == "shorts":
        plan["output_video"] = str(
            video.with_name(video.name[:-len("-horizontal.mp4")] + "-vertical.mp4")
        )
    else:
        plan["output_video"] = str(out / "out" / "vertical.mp4")
    plan_path = out / "vertical_plan.json"
    markdown_path = out / "vertical_plan_preview.md"
    html_path = out / "vertical_plan_preview.html"
    write_json(plan_path, plan)
    write_markdown(markdown_path, plan)
    write_html(html_path, plan)
    print(f"[video-to-shorts] vertical plan: {plan_path}")
    print(f"[video-to-shorts] plan preview markdown: {markdown_path}")
    print(f"[video-to-shorts] plan preview html: {html_path}")


if __name__ == "__main__":
    main()
