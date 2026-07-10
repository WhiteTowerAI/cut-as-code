#!/usr/bin/env python3
"""Render Phase 2 debug artifacts for video-subject-detect.

Inputs:
  tracks.json
  source video

Outputs:
  artifacts/preview.mp4
  artifacts/summary.md

This is a review artifact only. It does not write crop windows to tracks.json and
does not create a final edited video.
"""

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


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


def load_tracks(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "subject-tracks.v1":
        fail("tracks.json must use schema_version subject-tracks.v1")
    if data.get("coordinate_space") != "source_pixels":
        fail("tracks.json coordinate_space must be source_pixels")
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


def draw_frame(frame_path, frame_spec, video, max_width, show_crop_window):
    im = Image.open(frame_path).convert("RGB")
    out_w, out_h, scale = fit_size(im.width, im.height, max_width)
    im = im.resize((out_w, out_h))
    draw = ImageDraw.Draw(im)

    title_font = font(18, True)
    label_font = font(15, True)
    warn_font = font(24, True)
    green = (34, 220, 170)
    amber = (245, 184, 65)
    white = (245, 245, 245)
    red = (235, 64, 64)

    timestamp = f't={frame_spec["time_s"]:.2f}s  frame={frame_spec["frame_index"]}'
    draw_label(draw, (10, 10), timestamp, title_font, white, bg=(20, 20, 20))

    subjects = frame_spec.get("subjects", [])
    if not subjects:
        text = "NO SUBJECT"
        bbox = draw.textbbox((0, 0), text, font=warn_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (out_w - tw) // 2
        y = (out_h - th) // 2
        draw.rectangle([x - 16, y - 12, x + tw + 16, y + th + 12], fill=(0, 0, 0))
        draw.text((x, y), text, fill=red, font=warn_font)

    for subject in subjects:
        b = subject["bbox"]
        x1 = b["x"] * scale
        y1 = b["y"] * scale
        x2 = (b["x"] + b["w"]) * scale
        y2 = (b["y"] + b["h"]) * scale
        x1 = max(0, min(out_w - 1, x1))
        y1 = max(0, min(out_h - 1, y1))
        x2 = max(0, min(out_w - 1, x2))
        y2 = max(0, min(out_h - 1, y2))
        draw.rectangle([x1, y1, x2, y2], outline=green, width=3)
        label = f'{subject["track_id"]}/{subject["subject_id"]} conf={subject["confidence"]:.2f}'
        label_y = max(38, y1 - 26)
        draw_label(draw, (x1, label_y), label, label_font, green)

    if show_crop_window and subjects:
        xs = [s["bbox"]["x"] for s in subjects]
        ys = [s["bbox"]["y"] for s in subjects]
        x2s = [s["bbox"]["x"] + s["bbox"]["w"] for s in subjects]
        y2s = [s["bbox"]["y"] + s["bbox"]["h"] for s in subjects]
        pad = 0.12 * video["width"]
        cx1 = max(0, (min(xs) - pad) * scale)
        cy1 = max(0, (min(ys) - pad) * scale)
        cx2 = min(out_w - 1, (max(x2s) + pad) * scale)
        cy2 = min(out_h - 1, (max(y2s) + pad) * scale)
        draw.rectangle([cx1, cy1, cx2, cy2], outline=amber, width=2)
        draw_label(draw, (cx1, min(out_h - 28, cy2 + 4)), "debug crop overlay only", label_font, amber)

    return im


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


def write_summary(out_path, tracks_path, source, tracks, preview_path, show_crop_window):
    frames = tracks["frames"]
    subjects = [s for f in frames for s in f.get("subjects", [])]
    frames_with_subject = sum(1 for f in frames if f.get("subjects"))
    confidences = [s["confidence"] for s in subjects]
    issue_lines = summarize_review_issues(tracks)
    lines = [
        "# video-subject-detect debug summary",
        "",
        "## Inputs",
        "",
        f"- source: `{source}`",
        f"- tracks: `{tracks_path}`",
        "",
        "## Outputs",
        "",
        f"- preview: `{preview_path}`",
        "",
        "## Review Notes",
        "",
        "- This is a debug artifact only, not a final rendered video.",
        "- The preview does not write crop windows or safe areas back to `tracks.json`.",
        "- MVP `subject_id` equals `track_id`; ids do not promise cross-shot identity.",
        "",
        "## Metrics",
        "",
        f"- sampled frames: {len(frames)}",
        f"- frames with subject: {frames_with_subject}",
        f"- empty frames: {len(frames) - frames_with_subject}",
        f"- tracks: {len(tracks.get('tracks', []))}",
        f"- mean confidence: {(sum(confidences) / len(confidences)):.4f}" if confidences else "- mean confidence: 0",
        f"- future crop window overlay: {'shown as debug overlay only' if show_crop_window else 'off'}",
        "",
        "## Potential Review Issues",
        "",
        *issue_lines,
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_review_issues(tracks):
    frames = tracks["frames"]
    video_w = tracks["video"]["width"]
    empty = [f["time_s"] for f in frames if not f.get("subjects")]
    multi = [(f["time_s"], len(f.get("subjects", []))) for f in frames if len(f.get("subjects", [])) > 1]
    low_conf = [
        (f["time_s"], s["track_id"], s["confidence"])
        for f in frames
        for s in f.get("subjects", [])
        if s["confidence"] < 0.5
    ]

    centers_by_id = {}
    for f in frames:
        for s in f.get("subjects", []):
            b = s["bbox"]
            centers_by_id.setdefault(s["track_id"], []).append((
                f["time_s"],
                b["x"] + b["w"] / 2,
                b["y"] + b["h"] / 2,
            ))

    jump_threshold = max(240, video_w * 0.25)
    jumps = []
    for track_id, points in sorted(centers_by_id.items()):
        for prev, cur in zip(points, points[1:]):
            dist = math.hypot(cur[1] - prev[1], cur[2] - prev[2])
            if dist > jump_threshold:
                jumps.append((track_id, prev[0], cur[0], dist))

    lines = []
    if empty:
        lines.append("- NO SUBJECT frames: " + ", ".join(f"{t:.2f}s" for t in empty[:12]))
    else:
        lines.append("- NO SUBJECT frames: none")
    if multi:
        lines.append("- Multi-subject frames: " + ", ".join(f"{t:.2f}s ({n})" for t, n in multi[:12]))
    else:
        lines.append("- Multi-subject frames: none")
    if low_conf:
        lines.append("- Low-confidence detections (<0.50): " + ", ".join(
            f"{t:.2f}s {track_id}={conf:.2f}" for t, track_id, conf in low_conf[:12]
        ))
    else:
        lines.append("- Low-confidence detections (<0.50): none")
    if jumps:
        lines.append("- Large center jumps: " + ", ".join(
            f"{track_id} {a:.2f}s->{b:.2f}s ({dist:.0f}px)" for track_id, a, b, dist in jumps[:12]
        ))
    else:
        lines.append("- Large center jumps: none")
    lines.append("- If preview boxes still look wrong at these times, compare against contact_sheet.jpg first; this phase does not do real tracking.")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tracks")
    ap.add_argument("source")
    ap.add_argument("--out", default=None, help="artifact output dir; default is <tracks dir>/artifacts")
    ap.add_argument("--preview-fps", type=float, default=2.0)
    ap.add_argument("--max-width", type=int, default=640)
    ap.add_argument("--show-future-crop-window", action="store_true")
    ap.add_argument("--ffmpeg")
    args = ap.parse_args()

    if args.preview_fps <= 0:
        fail("--preview-fps must be > 0")
    if args.max_width < 160:
        fail("--max-width must be at least 160")

    tracks_path = Path(args.tracks)
    source = Path(args.source)
    if not tracks_path.exists():
        fail(f"tracks.json not found: {tracks_path}")
    if not source.exists():
        fail(f"source video not found: {source}")

    tracks = load_tracks(tracks_path)
    artifacts = Path(args.out) if args.out else tracks_path.parent / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)

    with tempfile.TemporaryDirectory(prefix="subject-preview-") as tmp:
        tmpdir = Path(tmp)
        rendered = tmpdir / "rendered"
        rendered.mkdir()
        for i, frame in enumerate(tracks["frames"], start=1):
            raw = tmpdir / f"raw_{i:06d}.jpg"
            extract_frame(ffmpeg, source, frame["time_s"], raw)
            drawn = draw_frame(raw, frame, tracks["video"], args.max_width, args.show_future_crop_window)
            drawn.save(rendered / f"frame_{i:06d}.jpg", quality=92)

        preview = artifacts / "preview.mp4"
        encode_preview(ffmpeg, rendered / "frame_%06d.jpg", args.preview_fps, preview)

    summary = artifacts / "summary.md"
    write_summary(summary, tracks_path, source, tracks, preview, args.show_future_crop_window)

    print(f"wrote {preview}")
    print(f"wrote {summary}")


if __name__ == "__main__":
    main()
