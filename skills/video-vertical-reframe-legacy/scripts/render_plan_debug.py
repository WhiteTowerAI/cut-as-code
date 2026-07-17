#!/usr/bin/env python3
"""Render Phase 2 plan review artifacts.

Outputs:
  artifacts/plan_contact_sheet.jpg
  artifacts/plan_preview.mp4

This is a planning review renderer only. It overlays the planned crop window on
source frames and does not create a vertical reframed output.
"""

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


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


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def load_json(path, schema_version):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != schema_version:
        fail(f"{path} must use schema_version {schema_version}")
    return data


def subjects_by_time(tracks):
    return {round(frame["time_s"], 3): frame.get("subjects", []) for frame in tracks.get("frames", [])}


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


def fit_size(width, height, max_width):
    if width <= max_width:
        return width, height, 1.0
    scale = max_width / width
    return max_width, int(round(height * scale)), scale


def draw_label(draw, xy, text, text_font, fill, bg=(0, 0, 0)):
    x, y = xy
    pad_x, pad_y = 6, 4
    bbox = draw.textbbox((0, 0), text, font=text_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.rectangle([x, y, x + tw + pad_x * 2, y + th + pad_y * 2], fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=text_font, fill=fill)
    return th + pad_y * 2


def short_text(text, max_len=84):
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def draw_plan_frame(frame_path, sample, subjects, max_width):
    im = Image.open(frame_path).convert("RGB")
    out_w, out_h, scale = fit_size(im.width, im.height, max_width)
    im = im.resize((out_w, out_h))
    draw = ImageDraw.Draw(im)

    title_font = font(17, True)
    label_font = font(14, True)
    small_font = font(12)
    color = COLORS.get(sample["strategy"], (245, 245, 245))
    white = (245, 245, 245)
    green = (34, 220, 170)
    red = (235, 64, 64)

    header = f't={sample["time_s"]:.2f}s  {sample["scene_id"]}  {sample["strategy"]}'
    y = 10
    draw_label(draw, (10, y), header, title_font, color, bg=(20, 20, 20))
    y += 34
    draw_label(draw, (10, y), short_text(sample.get("reason", "")), small_font, white, bg=(20, 20, 20))
    y += 28
    warnings = sample.get("warnings", [])
    if warnings:
        draw_label(draw, (10, y), "warning: " + ", ".join(warnings), small_font, red, bg=(20, 20, 20))

    for subject in subjects:
        b = subject["bbox"]
        x1 = b["x"] * scale
        y1 = b["y"] * scale
        x2 = (b["x"] + b["w"]) * scale
        y2 = (b["y"] + b["h"]) * scale
        draw.rectangle([x1, y1, x2, y2], outline=green, width=3)
        label = f'{subject["track_id"]} conf={subject["confidence"]:.2f}'
        draw_label(draw, (x1, max(94, y1 - 26)), label, label_font, green)

    c = sample["crop"]
    cx1 = c["x"] * scale
    cy1 = c["y"] * scale
    cx2 = (c["x"] + c["w"]) * scale
    cy2 = (c["y"] + c["h"]) * scale
    draw.rectangle([cx1, cy1, cx2, cy2], outline=color, width=4)
    draw_label(draw, (cx1 + 4, min(out_h - 30, cy2 - 30)), "planned crop window", label_font, color)
    return im


def select_contact_indices(samples, max_tiles):
    if len(samples) <= max_tiles:
        return list(range(len(samples)))
    step = (len(samples) - 1) / (max_tiles - 1)
    return [round(i * step) for i in range(max_tiles)]


def draw_contact_sheet(rendered_frames, samples, out_path, max_tiles=36):
    indices = select_contact_indices(samples, max_tiles)
    thumbs = []
    thumb_w = 360
    label_h = 56
    gap = 8
    tile_h = None
    for idx in indices:
        im = Image.open(rendered_frames[idx]).convert("RGB")
        scale = thumb_w / im.width
        thumb_h = int(round(im.height * scale))
        tile_h = tile_h or thumb_h
        im = im.resize((thumb_w, thumb_h))
        thumbs.append((idx, im))

    cols = min(3, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = rows * (tile_h + label_h) + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    label_font = font(14, True)
    small_font = font(11)

    for pos, (idx, im) in enumerate(thumbs):
        sample = samples[idx]
        r, c = divmod(pos, cols)
        x = gap + c * (thumb_w + gap)
        y = gap + r * (tile_h + label_h + gap)
        sheet.paste(im, (x, y + label_h))
        color = COLORS.get(sample["strategy"], (245, 245, 245))
        draw.rectangle([x, y, x + thumb_w, y + label_h], fill=(32, 32, 32))
        draw.text((x + 8, y + 7), f'{sample["time_s"]:.2f}s  {sample["strategy"]}', fill=color, font=label_font)
        note = ", ".join(sample.get("warnings", [])) or short_text(sample.get("reason", ""), 44)
        draw.text((x + 8, y + 31), short_text(note, 48), fill=(245, 245, 245), font=small_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--tracks", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--crop-path", required=True)
    ap.add_argument("--out", default=None, help="artifact output dir; default is <plan dir>/artifacts")
    ap.add_argument("--preview-fps", type=float, default=2.0)
    ap.add_argument("--max-width", type=int, default=760)
    ap.add_argument("--ffmpeg")
    args = ap.parse_args()

    source = Path(args.source)
    tracks = load_json(args.tracks, "subject-tracks.v1")
    load_json(args.plan, "reframe-plan.v1")
    crop_path = load_json(args.crop_path, "crop-path.v1")
    artifacts = Path(args.out) if args.out else Path(args.plan).parent / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    by_time = subjects_by_time(tracks)
    samples = crop_path["samples"]

    with tempfile.TemporaryDirectory(prefix="vertical-plan-debug-") as tmp:
        tmpdir = Path(tmp)
        rendered = tmpdir / "rendered"
        rendered.mkdir()
        for i, sample in enumerate(samples, start=1):
            raw = tmpdir / f"raw_{i:06d}.jpg"
            extract_frame(ffmpeg, source, sample["time_s"], raw)
            subjects = by_time.get(round(sample["time_s"], 3), [])
            drawn = draw_plan_frame(raw, sample, subjects, args.max_width)
            drawn_path = rendered / f"frame_{i:06d}.jpg"
            drawn.save(drawn_path, quality=92)

        draw_contact_sheet(sorted(rendered.glob("frame_*.jpg")), samples, artifacts / "plan_contact_sheet.jpg")
        encode_preview(ffmpeg, rendered / "frame_%06d.jpg", args.preview_fps, artifacts / "plan_preview.mp4")

    print(f"wrote {artifacts / 'plan_contact_sheet.jpg'}")
    print(f"wrote {artifacts / 'plan_preview.mp4'}")


if __name__ == "__main__":
    main()
