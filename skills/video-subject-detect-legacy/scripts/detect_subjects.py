#!/usr/bin/env python3
"""Minimal Phase 1 person detection for video-subject-detect.

Outputs:
  OUT/tracks.json
  OUT/metrics.json
  OUT/artifacts/contact_sheet.jpg

This intentionally does not render preview video, crop, avoid subtitles, or do
complex tracking. MVP subject_id is equal to track_id.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PERSON_CLASS_ID = 0
PERSON_CLASS_NAME = "person"


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


def probe_video(source, ffprobe):
    data = json.loads(run([
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(source),
    ]))
    stream = data.get("streams", [{}])[0]
    width = int(stream["width"])
    height = int(stream["height"])
    duration = stream.get("duration") or data.get("format", {}).get("duration") or 0
    fps_raw = stream.get("r_frame_rate", "0/1")
    num, den = (float(x) for x in fps_raw.split("/", 1))
    fps = num / den if den else 0.0
    return {
        "source": str(source),
        "width": width,
        "height": height,
        "fps": fps,
        "duration_s": float(duration),
    }


def extract_sample_frames(source, ffmpeg, frame_dir, sample_fps, max_frames):
    frame_dir.mkdir(parents=True, exist_ok=True)
    vf = f"fps={sample_fps}"
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(source),
        "-vf", vf,
        "-frames:v", str(max_frames),
        "-q:v", "2",
        str(frame_dir / "frame_%06d.jpg"),
    ]
    run(cmd)
    return sorted(frame_dir.glob("frame_*.jpg"))


def load_yolo(model_name, model_cache_dir):
    try:
        from ultralytics import YOLO
    except ImportError:
        fail(
            "Missing dependency: ultralytics. Install it in the Python environment "
            "used to run this script, then rerun."
        )
    model_path = Path(model_name)
    if model_path.exists() or model_path.parent != Path("."):
        return YOLO(str(model_path))

    model_cache_dir.mkdir(parents=True, exist_ok=True)
    old_cwd = Path.cwd()
    try:
        # Ultralytics downloads bare model names into the current directory.
        # Keep those runtime weights under the run output, not the repo root.
        import os
        os.chdir(model_cache_dir)
        return YOLO(model_name)
    finally:
        os.chdir(old_cwd)


def clamp_bbox(x1, y1, x2, y2, width, height):
    x1 = max(0.0, min(float(width), float(x1)))
    y1 = max(0.0, min(float(height), float(y1)))
    x2 = max(0.0, min(float(width), float(x2)))
    y2 = max(0.0, min(float(height), float(y2)))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return {
        "x": round(x1, 2),
        "y": round(y1, 2),
        "w": round(max(0.01, x2 - x1), 2),
        "h": round(max(0.01, y2 - y1), 2),
    }


def detect_people(model, image_paths, video, conf, iou):
    if not image_paths:
        return []

    results = model.predict(
        [str(p) for p in image_paths],
        classes=[PERSON_CLASS_ID],
        conf=conf,
        iou=iou,
        verbose=False,
    )
    frames = []
    for idx, result in enumerate(results):
        time_s = idx / result.speed.get("sample_fps", 1) if False else idx
        subjects = []
        boxes = []
        if result.boxes is not None:
            for box in result.boxes:
                xyxy = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                bbox = clamp_bbox(*xyxy, video["width"], video["height"])
                boxes.append((bbox["x"] + bbox["w"] / 2, bbox, confidence))
        boxes.sort(key=lambda item: item[0])
        for rank, (_, bbox, confidence) in enumerate(boxes, start=1):
            track_id = f"t{rank}"
            subjects.append({
                "subject_id": track_id,
                "track_id": track_id,
                "class": PERSON_CLASS_NAME,
                "bbox": bbox,
                "bbox_kind": "full_body",
                "confidence": round(confidence, 4),
                "metadata": {},
            })
        frames.append(subjects)
    return frames


def build_tracks(frames):
    by_track = {}
    for frame in frames:
        t = frame["time_s"]
        for subject in frame["subjects"]:
            item = by_track.setdefault(subject["track_id"], {
                "track_id": subject["track_id"],
                "class": PERSON_CLASS_NAME,
                "start_s": t,
                "end_s": t,
                "conf": [],
                "count": 0,
                "metadata": {},
            })
            item["start_s"] = min(item["start_s"], t)
            item["end_s"] = max(item["end_s"], t)
            item["conf"].append(subject["confidence"])
            item["count"] += 1
    total = max(1, len(frames))
    tracks = []
    for item in sorted(by_track.values(), key=lambda x: x["track_id"]):
        tracks.append({
            "track_id": item["track_id"],
            "class": PERSON_CLASS_NAME,
            "start_s": round(item["start_s"], 3),
            "end_s": round(item["end_s"], 3),
            "num_observations": item["count"],
            "mean_confidence": round(sum(item["conf"]) / len(item["conf"]), 4),
            "coverage": round(item["count"] / total, 4),
            "metadata": item["metadata"],
        })
    return tracks


def font(size):
    for p in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_contact_sheet(image_paths, frames, out_path, max_tiles=36):
    if not image_paths:
        fail("No sampled frames were extracted; cannot make contact sheet.")
    selected = list(range(len(image_paths)))
    if len(selected) > max_tiles:
        step = (len(selected) - 1) / (max_tiles - 1)
        selected = [round(i * step) for i in range(max_tiles)]

    thumb_w = 320
    label_h = 38
    gap = 8
    cols = min(4, len(selected))
    rows = math.ceil(len(selected) / cols)
    tile_h = None
    thumbs = []
    for idx in selected:
        im = Image.open(image_paths[idx]).convert("RGB")
        scale = thumb_w / im.width
        thumb_h = int(round(im.height * scale))
        tile_h = tile_h or thumb_h
        im = im.resize((thumb_w, thumb_h))
        draw = ImageDraw.Draw(im)
        for subject in frames[idx]["subjects"]:
            b = subject["bbox"]
            x1, y1 = b["x"] * scale, b["y"] * scale
            x2, y2 = (b["x"] + b["w"]) * scale, (b["y"] + b["h"]) * scale
            color = (34, 220, 170)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            label = f'{subject["track_id"]}/{subject["subject_id"]} {subject["confidence"]:.2f}'
            label_font = font(14)
            tw = draw.textlength(label, font=label_font)
            th = 20
            draw.rectangle([x1, max(0, y1 - th), x1 + tw + 10, y1], fill=(0, 0, 0))
            draw.text((x1 + 5, max(0, y1 - th + 3)), label, fill=color, font=label_font)
        thumbs.append((idx, im))

    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = rows * (tile_h + label_h) + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    label_font = font(15)
    for pos, (idx, im) in enumerate(thumbs):
        r, c = divmod(pos, cols)
        x = gap + c * (thumb_w + gap)
        y = gap + r * (tile_h + label_h + gap)
        sheet.paste(im, (x, y + label_h))
        f = frames[idx]
        label = f't={f["time_s"]:.2f}s frame={f["frame_index"]} subjects={len(f["subjects"])}'
        d.rectangle([x, y, x + thumb_w, y + label_h], fill=(32, 32, 32))
        d.text((x + 8, y + 10), label, fill=(245, 245, 245), font=label_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="work/subject-detect")
    ap.add_argument("--sample-fps", type=float, default=1.0)
    ap.add_argument("--max-frames", type=int, default=36)
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--model-cache-dir", default=None)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--ffmpeg")
    ap.add_argument("--ffprobe")
    args = ap.parse_args()

    if args.sample_fps <= 0:
        fail("--sample-fps must be > 0")
    if args.max_frames <= 0:
        fail("--max-frames must be > 0")

    started = time.time()
    source = Path(args.source)
    if not source.exists():
        fail(f"source video not found: {source}")
    out = Path(args.out)
    artifacts = out / "artifacts"
    out.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe, near=ffmpeg)
    video = probe_video(source, ffprobe)
    sample_count = min(args.max_frames, max(1, math.ceil(video["duration_s"] * args.sample_fps)))

    with tempfile.TemporaryDirectory(prefix="subject-detect-") as tmp:
        frame_dir = Path(tmp) / "frames"
        image_paths = extract_sample_frames(source, ffmpeg, frame_dir, args.sample_fps, sample_count)
        model_cache_dir = Path(args.model_cache_dir) if args.model_cache_dir else out / "models"
        model = load_yolo(args.model, model_cache_dir)
        detected = detect_people(model, image_paths, video, args.conf, args.iou)

        frames = []
        sample_interval_s = 1.0 / args.sample_fps
        sample_time_offset_s = sample_interval_s / 2.0
        for idx, subjects in enumerate(detected):
            # ffmpeg's fps filter samples the center of each output interval.
            # Store that source timestamp so preview rendering uses the same
            # visual moment that detection/contact_sheet used.
            time_s = round(min(video["duration_s"], sample_time_offset_s + idx * sample_interval_s), 3)
            frames.append({
                "time_s": time_s,
                "frame_index": int(round(time_s * video["fps"])),
                "subjects": subjects,
            })

        tracks = build_tracks(frames)
        tracks_json = {
            "schema_version": "subject-tracks.v1",
            "video": video,
            "coordinate_space": "source_pixels",
            "producer": {
                "skill": "video-subject-detect",
                "detector": f"ultralytics:{args.model}",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            },
            "frames": frames,
            "tracks": tracks,
            "metadata": {
                "sample_fps": args.sample_fps,
                "sample_interval_s": round(sample_interval_s, 6),
                "sample_time_offset_s": round(sample_time_offset_s, 6),
                "sampling_note": "ffmpeg fps filter samples the center of each output interval; time_s matches that visual moment",
                "mvp_tracking": "subjects are sorted left-to-right per sampled frame; subject_id equals track_id",
            },
        }

        with (out / "tracks.json").open("w", encoding="utf-8") as f:
            json.dump(tracks_json, f, indent=2)
            f.write("\n")

        draw_contact_sheet(image_paths, frames, artifacts / "contact_sheet.jpg")

    frames_with_subject = sum(1 for f in frames if f["subjects"])
    confidences = [s["confidence"] for f in frames for s in f["subjects"]]
    metrics = {
        "schema_version": "subject-detect-metrics.v1",
        "duration_s": video["duration_s"],
        "sample_fps": args.sample_fps,
        "frames_sampled": len(frames),
        "frames_with_subject": frames_with_subject,
        "detection_rate": round(frames_with_subject / max(1, len(frames)), 4),
        "empty_frame_rate": round(1 - frames_with_subject / max(1, len(frames)), 4),
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0,
        "track_count": len(tracks),
        "processing_fps": round(len(frames) / max(0.001, time.time() - started), 3),
        "wall_time_s": round(time.time() - started, 3),
        "warnings": [
            "MVP subject_id equals track_id and does not promise cross-shot identity.",
            "MVP track assignment is left-to-right per sampled frame, not complex tracking."
        ],
    }
    with (out / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        f.write("\n")

    print(f"wrote {out / 'tracks.json'}")
    print(f"wrote {out / 'metrics.json'}")
    print(f"wrote {artifacts / 'contact_sheet.jpg'}")


if __name__ == "__main__":
    main()
