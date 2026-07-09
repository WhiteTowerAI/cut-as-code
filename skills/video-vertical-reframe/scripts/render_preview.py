#!/usr/bin/env python3
"""Render Phase 3 low-resolution reframe preview.

Inputs:
  source video
  tracks.json
  reframe_plan.json
  crop_path.json

Outputs:
  artifacts/reframe_preview.mp4
  artifacts/reframe_preview_contact_sheet.jpg
  artifacts/reframe_preview_summary.md

This preview is an audit tool. It renders the planned 9:16 visual result at low
resolution with subject boxes, crop windows, strategy labels, scene ids, reasons,
warnings, timestamp, crop center, and a simple center trail. It does not create a
production vertical video and does not change detection or planning.
"""

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


COLORS = {
    "TRACK": (34, 220, 170),
    "LETTERBOX": (245, 184, 65),
    "CENTER_FALLBACK": (96, 165, 250),
}


def fail(message):
    raise SystemExit(message)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(str(c) for c in cmd)}\n{p.stderr.strip()}")
    return p.stdout


def resolve_tool(name, explicit=None, near=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        fail(f"{name} not found: {explicit}")
    found = shutil.which(name)
    if found:
        return found
    if near:
        candidate = Path(near).with_name(name + ".exe")
        if candidate.exists():
            return str(candidate)
    fail(f"{name} not found. Pass --{name} PATH.")


def load_json(path, schema_version):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != schema_version:
        fail(f"{path} must use schema_version {schema_version}")
    return data


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def extract_frame(ffmpeg, source, time_s, out_path):
    run([
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(source),
        "-ss", f"{time_s:.3f}",
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ])


def encode_preview(ffmpeg, frame_pattern, preview_fps, out_path):
    run([
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-framerate", str(preview_fps),
        "-i", str(frame_pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ])


def subjects_by_time(tracks):
    return {round(frame["time_s"], 3): frame.get("subjects", []) for frame in tracks.get("frames", [])}


def short_text(text, max_len):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def draw_label(draw, xy, text, text_font, fill, bg=(0, 0, 0), pad=(7, 4)):
    x, y = xy
    px, py = pad
    bbox = draw.textbbox((0, 0), text, font=text_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.rectangle([x, y, x + tw + px * 2, y + th + py * 2], fill=bg)
    draw.text((x + px, y + py), text, font=text_font, fill=fill)
    return th + py * 2


def fit_inside(src_w, src_h, dst_w, dst_h):
    scale = min(dst_w / src_w, dst_h / src_h)
    out_w = max(1, int(round(src_w * scale)))
    out_h = max(1, int(round(src_h * scale)))
    x = (dst_w - out_w) // 2
    y = (dst_h - out_h) // 2
    return scale, x, y, out_w, out_h


def render_reframed_visual(source_im, sample, canvas_w, canvas_h):
    strategy = sample["strategy"]
    crop = sample["crop"]
    if strategy == "LETTERBOX":
        bg = source_im.resize((canvas_w, canvas_h)).filter(ImageFilter.GaussianBlur(radius=12))
        overlay = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        canvas = Image.blend(bg, overlay, 0.35)
        scale, x, y, out_w, out_h = fit_inside(source_im.width, source_im.height, canvas_w, canvas_h)
        fitted = source_im.resize((out_w, out_h))
        canvas.paste(fitted, (x, y))
        return canvas, scale, x, y, "full_frame"

    x1 = int(round(crop["x"]))
    y1 = int(round(crop["y"]))
    x2 = int(round(crop["x"] + crop["w"]))
    y2 = int(round(crop["y"] + crop["h"]))
    cropped = source_im.crop((x1, y1, x2, y2))
    canvas = cropped.resize((canvas_w, canvas_h))
    scale = canvas_w / max(1, crop["w"])
    return canvas, scale, -crop["x"] * scale, -crop["y"] * scale, "cropped"


def draw_source_panel(panel, source_im, sample, subjects):
    draw = ImageDraw.Draw(panel)
    panel_w, panel_h = panel.size
    src_area_h = int(panel_h * 0.62)
    scale, ox, oy, out_w, out_h = fit_inside(source_im.width, source_im.height, panel_w, src_area_h)
    preview = source_im.resize((out_w, out_h))
    panel.paste(preview, (ox, oy))
    color = COLORS.get(sample["strategy"], (245, 245, 245))
    green = (34, 220, 170)

    for subject in subjects:
        b = subject["bbox"]
        x1 = ox + b["x"] * scale
        y1 = oy + b["y"] * scale
        x2 = ox + (b["x"] + b["w"]) * scale
        y2 = oy + (b["y"] + b["h"]) * scale
        draw.rectangle([x1, y1, x2, y2], outline=green, width=2)

    c = sample["crop"]
    cx1 = ox + c["x"] * scale
    cy1 = oy + c["y"] * scale
    cx2 = ox + (c["x"] + c["w"]) * scale
    cy2 = oy + (c["y"] + c["h"]) * scale
    draw.rectangle([cx1, cy1, cx2, cy2], outline=color, width=3)

    title_font = font(17, True)
    small_font = font(13)
    y = src_area_h + 12
    draw_label(draw, (10, y), "source + planned crop", title_font, color, bg=(24, 24, 24))
    y += 36
    draw.text((10, y), short_text(sample.get("reason", ""), 48), fill=(245, 245, 245), font=small_font)
    y += 38
    warnings = sample.get("warnings", [])
    warn = ", ".join(warnings) if warnings else "none"
    draw.text((10, y), short_text(f"warnings: {warn}", 48), fill=(255, 190, 120), font=small_font)


def draw_output_overlay(canvas, sample, subjects, source_to_canvas, center_trail):
    draw = ImageDraw.Draw(canvas)
    color = COLORS.get(sample["strategy"], (245, 245, 245))
    green = (34, 220, 170)
    red = (235, 64, 64)
    white = (245, 245, 245)
    title_font = font(24, True)
    label_font = font(17, True)
    small_font = font(14)

    scale, ox, oy, mode = source_to_canvas
    for subject in subjects:
        b = subject["bbox"]
        x1 = ox + b["x"] * scale
        y1 = oy + b["y"] * scale
        x2 = ox + (b["x"] + b["w"]) * scale
        y2 = oy + (b["y"] + b["h"]) * scale
        if x2 < 0 or y2 < 0 or x1 > canvas.width or y1 > canvas.height:
            continue
        draw.rectangle([x1, y1, x2, y2], outline=green, width=3)
        draw_label(draw, (max(4, x1), max(76, y1 - 26)), f'{subject["track_id"]} {subject["confidence"]:.2f}', small_font, green)

    cx = ox + (sample["crop"]["x"] + sample["crop"]["w"] / 2) * scale
    cy = oy + (sample["crop"]["y"] + sample["crop"]["h"] / 2) * scale
    if mode == "cropped":
        cx = canvas.width / 2
        cy = canvas.height / 2
    center_trail.append((cx, cy))
    trail = list(center_trail)
    for a, b in zip(trail, trail[1:]):
        draw.line([a, b], fill=color, width=2)
    r = 5
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    draw.line([cx - 18, cy, cx + 18, cy], fill=color, width=2)
    draw.line([cx, cy - 18, cx, cy + 18], fill=color, width=2)

    y = 12
    draw_label(draw, (12, y), f'{sample["strategy"]}  {sample["scene_id"]}', title_font, color, bg=(0, 0, 0))
    y += 42
    draw_label(draw, (12, y), f't={sample["time_s"]:.2f}s  frame={sample["frame_index"]}', label_font, white, bg=(0, 0, 0))
    y += 34
    reason = short_text(sample.get("reason", ""), 58)
    draw_label(draw, (12, y), reason, small_font, white, bg=(0, 0, 0))
    warnings = sample.get("warnings", [])
    if warnings:
        draw_label(draw, (12, canvas.height - 36), "warning: " + ", ".join(warnings), small_font, red, bg=(0, 0, 0))


def compose_review_frame(source_path, sample, subjects, canvas_w, canvas_h, center_trail):
    source_im = Image.open(source_path).convert("RGB")
    vertical, scale, ox, oy, mode = render_reframed_visual(source_im, sample, canvas_w, canvas_h)
    draw_output_overlay(vertical, sample, subjects, (scale, ox, oy, mode), center_trail)

    panel_w = max(280, int(canvas_w * 0.72))
    combined = Image.new("RGB", (canvas_w + panel_w, canvas_h), (14, 14, 14))
    combined.paste(vertical, (0, 0))
    panel = Image.new("RGB", (panel_w, canvas_h), (24, 24, 24))
    draw_source_panel(panel, source_im, sample, subjects)
    combined.paste(panel, (canvas_w, 0))
    return combined


def select_contact_indices(samples, max_tiles):
    if len(samples) <= max_tiles:
        return list(range(len(samples)))
    step = (len(samples) - 1) / (max_tiles - 1)
    return [round(i * step) for i in range(max_tiles)]


def make_contact_sheet(rendered_paths, samples, out_path, max_tiles=24):
    indices = select_contact_indices(samples, max_tiles)
    thumb_w = 300
    label_h = 50
    gap = 8
    thumbs = []
    tile_h = None
    for idx in indices:
        im = Image.open(rendered_paths[idx]).convert("RGB")
        scale = thumb_w / im.width
        thumb_h = int(round(im.height * scale))
        tile_h = tile_h or thumb_h
        thumbs.append((idx, im.resize((thumb_w, thumb_h))))

    cols = min(3, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * gap, rows * (tile_h + label_h) + (rows + 1) * gap), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    label_font = font(13, True)
    small_font = font(11)
    for pos, (idx, im) in enumerate(thumbs):
        sample = samples[idx]
        r, c = divmod(pos, cols)
        x = gap + c * (thumb_w + gap)
        y = gap + r * (tile_h + label_h + gap)
        sheet.paste(im, (x, y + label_h))
        color = COLORS.get(sample["strategy"], (245, 245, 245))
        draw.rectangle([x, y, x + thumb_w, y + label_h], fill=(32, 32, 32))
        draw.text((x + 8, y + 6), f'{sample["time_s"]:.2f}s {sample["strategy"]}', fill=color, font=label_font)
        note = ", ".join(sample.get("warnings", [])) or sample.get("reason", "")
        draw.text((x + 8, y + 28), short_text(note, 42), fill=(245, 245, 245), font=small_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def write_summary(path, preview_path, contact_sheet_path, samples, plan_path, crop_path):
    counts = Counter(s["strategy"] for s in samples)
    warning_counts = Counter(w for s in samples for w in s.get("warnings", []))
    total = max(1, len(samples))
    lines = [
        "# video-vertical-reframe Phase3 preview summary",
        "",
        "## Inputs",
        "",
        f"- reframe plan: `{plan_path}`",
        f"- crop path: `{crop_path}`",
        "",
        "## Outputs",
        "",
        f"- reframe preview: `{preview_path}`",
        f"- contact sheet: `{contact_sheet_path}`",
        "",
        "## Strategy Ratios",
        "",
        f"- TRACK: {counts.get('TRACK', 0)} ({counts.get('TRACK', 0) / total:.1%})",
        f"- LETTERBOX: {counts.get('LETTERBOX', 0)} ({counts.get('LETTERBOX', 0) / total:.1%})",
        f"- CENTER_FALLBACK: {counts.get('CENTER_FALLBACK', 0)} ({counts.get('CENTER_FALLBACK', 0) / total:.1%})",
        "",
        "## Warning Counts",
        "",
    ]
    if warning_counts:
        lines.extend(f"- {k}: {v}" for k, v in sorted(warning_counts.items()))
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Review Checklist",
        "",
        "- Watch the full preview and check whether the subject remains in a reasonable position.",
        "- Check whether the crop center trail moves naturally.",
        "- Check whether LETTERBOX appears only when full-frame preservation is useful.",
        "- Check whether any subject face or body is visibly cut by TRACK.",
        "",
        "## Known Phase3 Limits",
        "",
        "- This is a low-resolution audit render, not production quality.",
        "- Audio is intentionally omitted; audio sync belongs to Phase4.",
        "- The center trail visualizes sampled crop centers, not dense frame-by-frame smoothing.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--tracks", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--crop-path", required=True)
    ap.add_argument("--out-dir", default=None, help="artifact output dir; default is <plan dir>/artifacts")
    ap.add_argument("--preview-fps", type=float, default=2.0)
    ap.add_argument("--height", type=int, default=540)
    ap.add_argument("--ffmpeg")
    args = ap.parse_args()

    source = Path(args.source)
    tracks = load_json(args.tracks, "subject-tracks.v1")
    load_json(args.plan, "reframe-plan.v1")
    crop_path = load_json(args.crop_path, "crop-path.v1")
    artifacts = Path(args.out_dir) if args.out_dir else Path(args.plan).parent / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)

    canvas_h = args.height
    canvas_w = int(round(canvas_h * 9 / 16))
    if canvas_w % 2:
        canvas_w += 1

    by_time = subjects_by_time(tracks)
    samples = crop_path["samples"]
    center_trail = deque(maxlen=12)
    preview_path = artifacts / "reframe_preview.mp4"
    contact_sheet_path = artifacts / "reframe_preview_contact_sheet.jpg"
    summary_path = artifacts / "reframe_preview_summary.md"

    with tempfile.TemporaryDirectory(prefix="vertical-reframe-preview-") as tmp:
        tmpdir = Path(tmp)
        rendered = tmpdir / "rendered"
        rendered.mkdir()
        rendered_paths = []
        for i, sample in enumerate(samples, start=1):
            raw = tmpdir / f"raw_{i:06d}.jpg"
            extract_frame(ffmpeg, source, sample["time_s"], raw)
            subjects = by_time.get(round(sample["time_s"], 3), [])
            frame = compose_review_frame(raw, sample, subjects, canvas_w, canvas_h, center_trail)
            out_frame = rendered / f"frame_{i:06d}.jpg"
            frame.save(out_frame, quality=92)
            rendered_paths.append(out_frame)

        make_contact_sheet(rendered_paths, samples, contact_sheet_path)
        encode_preview(ffmpeg, rendered / "frame_%06d.jpg", args.preview_fps, preview_path)

    write_summary(summary_path, preview_path, contact_sheet_path, samples, args.plan, args.crop_path)
    print(f"wrote {preview_path}")
    print(f"wrote {contact_sheet_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
