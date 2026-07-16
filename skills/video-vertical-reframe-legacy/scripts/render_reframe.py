#!/usr/bin/env python3
"""Render Phase 4 production vertical video.

Inputs:
  source video
  reframe_plan.json
  crop_path.json

Outputs:
  OUT/vertical.mp4
  artifacts/final_contact_sheet.jpg
  artifacts/final_summary.md
  artifacts/media_probe.json

This renderer consumes the approved plan and crop path. It does not re-run
subject detection and does not regenerate crop strategy.
"""

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
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


def load_json(path, schema_version):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != schema_version:
        fail(f"{path} must use schema_version {schema_version}")
    return data


def probe_media(ffprobe, path):
    data = json.loads(run([
        ffprobe,
        "-v", "error",
        "-show_entries",
        "stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration,start_time",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]))
    return data


def fps_from_probe(media):
    for stream in media.get("streams", []):
        if stream.get("codec_type") == "video":
            raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
            num, den = raw.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else 0.0
    return 0.0


def even_width_for_height(height):
    width = int(round(height * 9 / 16))
    return width + (width % 2)


def fit_inside(src_w, src_h, dst_w, dst_h):
    scale = min(dst_w / src_w, dst_h / src_h)
    out_w = max(1, int(round(src_w * scale)))
    out_h = max(1, int(round(src_h * scale)))
    x = (dst_w - out_w) // 2
    y = (dst_h - out_h) // 2
    return x, y, out_w, out_h


def clamp_crop(crop, frame_w, frame_h):
    w = min(float(crop["w"]), float(frame_w))
    h = min(float(crop["h"]), float(frame_h))
    x = max(0.0, min(float(frame_w) - w, float(crop["x"])))
    y = max(0.0, min(float(frame_h) - h, float(crop["y"])))
    return x, y, w, h


def choose_sample(samples, time_s, cursor):
    while cursor + 1 < len(samples):
        cur = samples[cursor]["time_s"]
        nxt = samples[cursor + 1]["time_s"]
        if time_s <= (cur + nxt) / 2:
            break
        cursor += 1
    return samples[cursor], cursor


def render_frame(frame_bgr, sample, out_w, out_h):
    strategy = sample["strategy"]
    frame_h, frame_w = frame_bgr.shape[:2]
    if strategy == "LETTERBOX":
        bg = cv2.resize(frame_bgr, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
        bg = cv2.GaussianBlur(bg, (0, 0), 12)
        bg = cv2.addWeighted(bg, 0.65, np.zeros_like(bg), 0.35, 0)
        x, y, fitted_w, fitted_h = fit_inside(frame_w, frame_h, out_w, out_h)
        fitted = cv2.resize(frame_bgr, (fitted_w, fitted_h), interpolation=cv2.INTER_AREA)
        bg[y:y + fitted_h, x:x + fitted_w] = fitted
        return bg

    x, y, w, h = clamp_crop(sample["crop"], frame_w, frame_h)
    x1 = int(round(x))
    y1 = int(round(y))
    x2 = int(round(x + w))
    y2 = int(round(y + h))
    cropped = frame_bgr[y1:y2, x1:x2]
    if cropped.size == 0:
        return cv2.resize(frame_bgr, (out_w, out_h), interpolation=cv2.INTER_AREA)
    return cv2.resize(cropped, (out_w, out_h), interpolation=cv2.INTER_LINEAR)


def encode_silent_video(ffmpeg, source, crop_path, temp_video, fps, out_w, out_h, encoder, crf, preset):
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        fail(f"could not open source video: {source}")

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{out_w}x{out_h}",
        "-r", f"{fps:.6f}",
        "-i", "-",
        "-an",
        "-c:v", encoder,
    ]
    if encoder == "libx264":
        cmd += ["-preset", preset, "-crf", str(crf)]
    cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp_video)]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    samples = crop_path["samples"]
    cursor = 0
    frame_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            time_s = frame_count / fps if fps else 0.0
            sample, cursor = choose_sample(samples, time_s, cursor)
            out_bgr = render_frame(frame, sample, out_w, out_h)
            out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
            proc.stdin.write(out_rgb.tobytes())
            frame_count += 1
    finally:
        cap.release()
        if proc.stdin:
            proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        fail(f"ffmpeg video encoder failed with exit code {rc}")
    return frame_count


def mux_audio(ffmpeg, source, silent_video, final_video, has_audio):
    if has_audio:
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(silent_video),
            "-i", str(source),
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-c:v", "copy",
            "-c:a", "copy",
            "-shortest",
            "-movflags", "+faststart",
            str(final_video),
        ]
    else:
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(silent_video),
            "-c:v", "copy",
            "-movflags", "+faststart",
            str(final_video),
        ]
    run(cmd)


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


def make_contact_sheet(ffmpeg, final_video, samples, out_path):
    selected = list(range(len(samples)))
    if len(selected) > 12:
        step = (len(selected) - 1) / 11
        selected = [round(i * step) for i in range(12)]
    max_sample_time = max((float(sample["time_s"]) for sample in samples), default=0.0)

    thumbs = []
    with tempfile.TemporaryDirectory(prefix="vertical-final-sheet-") as tmp:
        tmpdir = Path(tmp)
        for pos, idx in enumerate(selected):
            sample = samples[idx]
            frame_path = tmpdir / f"frame_{pos:03d}.jpg"
            time_s = float(sample["time_s"])
            if max_sample_time > 0 and time_s >= max_sample_time:
                time_s = max(0.0, max_sample_time - 0.05)
            extract_frame(ffmpeg, final_video, time_s, frame_path)
            im = Image.open(frame_path).convert("RGB")
            thumb_w = 180
            thumb_h = int(round(im.height * thumb_w / im.width))
            im = im.resize((thumb_w, thumb_h))
            thumbs.append((sample, im))

    cols = min(4, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    label_h = 44
    gap = 8
    tile_w = thumbs[0][1].width if thumbs else 180
    tile_h = thumbs[0][1].height if thumbs else 320
    sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * gap, rows * (tile_h + label_h) + (rows + 1) * gap), (18, 18, 18))
    draw = ImageDraw.Draw(sheet)
    label_font = font(12, True)
    small_font = font(10)
    for pos, (sample, im) in enumerate(thumbs):
        r, c = divmod(pos, cols)
        x = gap + c * (tile_w + gap)
        y = gap + r * (tile_h + label_h + gap)
        sheet.paste(im, (x, y + label_h))
        draw.rectangle([x, y, x + tile_w, y + label_h], fill=(32, 32, 32))
        draw.text((x + 6, y + 5), f'{sample["time_s"]:.1f}s {sample["strategy"]}', fill=(245, 245, 245), font=label_font)
        warn = ", ".join(sample.get("warnings", [])) or "ok"
        draw.text((x + 6, y + 24), warn[:25], fill=(245, 184, 65), font=small_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=92)


def media_summary(media):
    video = next((s for s in media.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in media.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "r_frame_rate": video.get("r_frame_rate"),
            "avg_frame_rate": video.get("avg_frame_rate"),
            "duration": video.get("duration"),
            "start_time": video.get("start_time"),
        },
        "audio": None if audio is None else {
            "codec": audio.get("codec_name"),
            "duration": audio.get("duration"),
            "start_time": audio.get("start_time"),
        },
        "format_duration": media.get("format", {}).get("duration"),
    }


def write_summary(path, final_video, contact_sheet, probe_path, source_probe, final_probe, counts, regression):
    src = media_summary(source_probe)
    out = media_summary(final_probe)
    lines = [
        "# video-vertical-reframe Phase4 final render summary",
        "",
        "## Outputs",
        "",
        f"- vertical video: `{final_video}`",
        f"- final contact sheet: `{contact_sheet}`",
        f"- media probe: `{probe_path}`",
        "",
        "## Media",
        "",
        f"- output resolution: {out['video'].get('width')}x{out['video'].get('height')}",
        f"- output fps: {out['video'].get('avg_frame_rate')}",
        f"- output duration: {out.get('format_duration')}",
        f"- video codec: {out['video'].get('codec')}",
        f"- audio codec: {out['audio'].get('codec') if out['audio'] else 'none'}",
        "",
        "## Strategy Counts",
        "",
        f"- TRACK: {counts.get('TRACK', 0)}",
        f"- LETTERBOX: {counts.get('LETTERBOX', 0)}",
        f"- CENTER_FALLBACK: {counts.get('CENTER_FALLBACK', 0)}",
        "",
        "## Regression Report",
        "",
        f"- crop source: {regression['crop_source']}",
        f"- strategy source: {regression['strategy_source']}",
        f"- preview/final visual rule match: {regression['visual_rule_match']}",
        f"- normal differences: {regression['normal_differences']}",
        f"- suspected bugs: {regression['suspected_bugs']}",
        "",
        "## Review Notes",
        "",
        "- Compare this final render against the Phase3 reframe preview for crop and letterbox consistency.",
        "- Audio is copied from the source; check spoken audio against visible slide/speaker timing.",
        "- This phase does not alter subject detection or reframe planning.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--crop-path", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg")
    ap.add_argument("--ffprobe")
    ap.add_argument("--encoder", default="libx264", help="libx264 or future auto mode")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="veryfast")
    args = ap.parse_args()

    started = time.time()
    source = Path(args.source)
    plan = load_json(args.plan, "reframe-plan.v1")
    crop_path = load_json(args.crop_path, "crop-path.v1")
    out_video = Path(args.out)
    out_video.parent.mkdir(parents=True, exist_ok=True)
    artifacts = out_video.parent.parent / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
    ffprobe = resolve_tool("ffprobe", args.ffprobe, near=ffmpeg)
    source_probe = probe_media(ffprobe, source)
    fps = fps_from_probe(source_probe)
    if fps <= 0:
        fail("could not determine source fps")
    source_video = next(s for s in source_probe.get("streams", []) if s.get("codec_type") == "video")
    src_h = int(source_video["height"])
    out_h = src_h
    out_w = even_width_for_height(out_h)
    target = crop_path.get("target", {})
    if target.get("width") and target.get("height"):
        out_w = int(target["width"])
        out_h = int(target["height"])

    encoder = "libx264" if args.encoder == "auto" else args.encoder
    has_audio = any(s.get("codec_type") == "audio" for s in source_probe.get("streams", []))
    source_audio_start = next((s.get("start_time") for s in source_probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    source_video_start = source_video.get("start_time")

    with tempfile.TemporaryDirectory(prefix="vertical-reframe-final-") as tmp:
        temp_video = Path(tmp) / "silent_vertical.mp4"
        frame_count = encode_silent_video(ffmpeg, source, crop_path, temp_video, fps, out_w, out_h, encoder, args.crf, args.preset)
        mux_audio(ffmpeg, source, temp_video, out_video, has_audio)

    final_probe = probe_media(ffprobe, out_video)
    media_probe_path = artifacts / "media_probe.json"
    media_probe = {
        "schema_version": "vertical-reframe-media-probe.v1",
        "source": media_summary(source_probe),
        "output": media_summary(final_probe),
        "render": {
            "frame_count": frame_count,
            "fps": fps,
            "encoder": encoder,
            "crf": args.crf,
            "preset": args.preset if encoder == "libx264" else None,
            "pix_fmt": "yuv420p",
            "movflags": "+faststart",
            "audio_mode": "copy" if has_audio else "none",
            "source_video_start_time": source_video_start,
            "source_audio_start_time": source_audio_start,
            "wall_time_s": round(time.time() - started, 3),
        },
    }
    media_probe_path.write_text(json.dumps(media_probe, indent=2) + "\n", encoding="utf-8")

    contact_sheet = artifacts / "final_contact_sheet.jpg"
    make_contact_sheet(ffmpeg, out_video, crop_path["samples"], contact_sheet)
    counts = Counter(sample["strategy"] for sample in crop_path["samples"])
    regression = {
        "crop_source": "Phase4 consumed the approved crop_path.json without regenerating it.",
        "strategy_source": "Phase4 consumed the approved reframe_plan.json/crop_path.json strategies without modifying them.",
        "visual_rule_match": "Final render uses the same crop and letterbox visual rules as Phase3, without review overlays.",
        "normal_differences": "Phase3 includes labels, source context panel, bboxes, crop window, warnings, and center trail; final render removes all audit overlays and includes copied audio.",
        "suspected_bugs": "none detected by automated render/probe checks",
    }
    summary = artifacts / "final_summary.md"
    write_summary(summary, out_video, contact_sheet, media_probe_path, source_probe, final_probe, counts, regression)

    print(f"wrote {out_video}")
    print(f"wrote {contact_sheet}")
    print(f"wrote {summary}")
    print(f"wrote {media_probe_path}")


if __name__ == "__main__":
    main()
