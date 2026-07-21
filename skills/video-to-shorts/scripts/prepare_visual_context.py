#!/usr/bin/env python3
"""Generate deterministic, timestamped contact sheets for optional visual review."""

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def fail(message):
    raise SystemExit(message)


def run(command):
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(map(str, command)) + "\n" + process.stderr.strip())
    return process.stdout


def resolve_tool(name, explicit):
    if explicit and Path(explicit).exists():
        return str(Path(explicit).resolve())
    found = shutil.which(name)
    if found:
        return found
    fail(f"{name} not found; pass --{name} PATH")


def probe(ffprobe, video):
    payload = json.loads(run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=width,height", "-select_streams", "v:0", "-of", "json", str(video)]))
    stream = payload["streams"][0]
    return float(payload["format"]["duration"]), int(stream["width"]), int(stream["height"])


def label_time(seconds):
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(description="Prepare paged contact sheets for text_visual candidate review.")
    parser.add_argument("video")
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=float, default=60.0)
    parser.add_argument("--frames-per-sheet", type=int, default=12)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    args = parser.parse_args()
    video = Path(args.video).resolve()
    if not video.exists():
        fail(f"video not found: {video}")
    out = Path(args.out).resolve()
    frames_dir = out / "visual_frames"
    sheets_dir = out / "contact_sheets"
    frames_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe)
    duration, width, height = probe(ffprobe, video)
    timestamps = [min(index * args.interval, max(0, duration - 0.05)) for index in range(math.ceil(duration / args.interval))]
    manifest_frames = []
    for index, timestamp in enumerate(timestamps, 1):
        frame_path = frames_dir / f"frame_{index:04d}_{int(timestamp):06d}s.jpg"
        run([ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "2", str(frame_path)])
        manifest_frames.append({"index": index, "timestamp_s": round(timestamp, 3), "timecode": label_time(timestamp), "path": str(frame_path)})
    rows = math.ceil(args.frames_per_sheet / args.columns)
    cell_width, image_height, label_height = 480, round(480 * height / width), 34
    sheet_paths = []
    font = ImageFont.load_default()
    for page, offset in enumerate(range(0, len(manifest_frames), args.frames_per_sheet), 1):
        page_frames = manifest_frames[offset:offset + args.frames_per_sheet]
        sheet = Image.new("RGB", (args.columns * cell_width, rows * (image_height + label_height)), "white")
        draw = ImageDraw.Draw(sheet)
        for cell, frame in enumerate(page_frames):
            image = Image.open(frame["path"]).convert("RGB").resize((cell_width, image_height))
            x = cell % args.columns * cell_width
            y = cell // args.columns * (image_height + label_height)
            sheet.paste(image, (x, y))
            draw.rectangle((x, y + image_height, x + cell_width, y + image_height + label_height), fill="#111827")
            draw.text((x + 10, y + image_height + 10), f"#{frame['index']:04d}  {frame['timecode']}  {frame['timestamp_s']:.3f}s", fill="white", font=font)
        sheet_path = sheets_dir / f"contact_sheet_{page:02d}.jpg"
        sheet.save(sheet_path, quality=92)
        sheet_paths.append(str(sheet_path))
    manifest = {"video": str(video), "duration_s": round(duration, 3), "source_width": width, "source_height": height, "interval_s": args.interval, "frames_per_sheet": args.frames_per_sheet, "contact_sheets": sheet_paths, "frames": manifest_frames, "purpose": "Optional review context only; visual evidence does not affect candidate scoring."}
    (out / "visual_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[video-to-shorts] visual manifest: {out / 'visual_manifest.json'}")
    print(f"[video-to-shorts] contact sheets: {len(sheet_paths)}")


if __name__ == "__main__":
    main()
