#!/usr/bin/env python3
"""Phase 2 reframe planner for video-vertical-reframe.

Inputs:
  source video
  tracks.json

Outputs:
  OUT/reframe_plan.json
  OUT/crop_path.json
  OUT/plan_metrics.json

This script only plans the crop strategy. It does not detect subjects, render a
vertical preview, or create a final vertical video.
"""

import argparse
import json
import math
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


LOW_CONFIDENCE = 0.50
MULTI_SUBJECT_MAX_SPAN = 0.88
SINGLE_SUBJECT_MAX_WIDTH = 0.92
CROP_EDGE_MARGIN = 0.04
LOW_PARTIAL_BBOX_Y = 0.62
LOW_PARTIAL_BBOX_BOTTOM = 0.93
CROP_JUMP_THRESHOLD = 0.35
DENSE_SAMPLE_INTERVAL_S = 0.5
MAX_CROP_CENTER_SPEED = 0.10


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


def load_tracks(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "subject-tracks.v1":
        fail("tracks.json must use schema_version subject-tracks.v1")
    if data.get("coordinate_space") != "source_pixels":
        fail("tracks.json coordinate_space must be source_pixels")
    if not data.get("frames"):
        fail("tracks.json must include frames")
    return data


def target_from_video(video):
    height = int(video["height"])
    width = int(round(height * 9 / 16))
    if width % 2:
        width += 1
    width = min(width, int(video["width"]))
    return {
        "aspect_ratio": "9:16",
        "width": width,
        "height": height,
        "coordinate_space": "source_pixels",
        "background": "black",
    }


def clamp_crop(x, y, w, h, video):
    vw, vh = video["width"], video["height"]
    w = min(float(w), float(vw))
    h = min(float(h), float(vh))
    x = max(0.0, min(float(vw) - w, float(x)))
    y = max(0.0, min(float(vh) - h, float(y)))
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "w": round(w, 2),
        "h": round(h, 2),
    }


def full_frame_crop(video):
    return {
        "x": 0,
        "y": 0,
        "w": video["width"],
        "h": video["height"],
    }


def center_crop(video, target):
    return clamp_crop((video["width"] - target["width"]) / 2, 0, target["width"], target["height"], video)


def union_bbox(subjects):
    xs = [s["bbox"]["x"] for s in subjects]
    ys = [s["bbox"]["y"] for s in subjects]
    x2s = [s["bbox"]["x"] + s["bbox"]["w"] for s in subjects]
    y2s = [s["bbox"]["y"] + s["bbox"]["h"] for s in subjects]
    return {
        "x": min(xs),
        "y": min(ys),
        "w": max(x2s) - min(xs),
        "h": max(y2s) - min(ys),
    }


def centered_crop_for_bbox(bbox, video, target):
    cx = bbox["x"] + bbox["w"] / 2
    return clamp_crop(cx - target["width"] / 2, 0, target["width"], target["height"], video)


def bbox_inside_crop(bbox, crop, margin_px):
    left_ok = bbox["x"] >= crop["x"] + margin_px
    right_ok = bbox["x"] + bbox["w"] <= crop["x"] + crop["w"] - margin_px
    return left_ok and right_ok


def is_low_partial_bbox(bbox, video):
    bottom = bbox["y"] + bbox["h"]
    return (
        bbox["y"] > video["height"] * LOW_PARTIAL_BBOX_Y
        and bottom > video["height"] * LOW_PARTIAL_BBOX_BOTTOM
    )


def preserve_full_frame(reason, subjects, video, warnings, metadata=None):
    return {
        "strategy": "LETTERBOX",
        "crop": full_frame_crop(video),
        "subjects": subjects,
        "reason": reason,
        "warnings": ["PRESERVE_FULL_FRAME", *warnings],
        "metadata": {"preserve_full_frame": True, **(metadata or {})},
    }


def plan_frame(frame, video, target):
    subjects = frame.get("subjects", [])
    center = center_crop(video, target)
    if not subjects:
        return {
            "strategy": "CENTER_FALLBACK",
            "crop": center,
            "subjects": [],
            "reason": "No subject was detected at this timestamp, so use a safe centered crop.",
            "warnings": ["NO_SUBJECT"],
            "metadata": {"input_subject_count": 0},
        }

    reliable = [s for s in subjects if s.get("confidence", 0) >= LOW_CONFIDENCE]
    if not reliable:
        return {
            "strategy": "CENTER_FALLBACK",
            "crop": center,
            "subjects": [s["track_id"] for s in subjects],
            "reason": "All subject detections are below the confidence threshold, so avoid subject tracking.",
            "warnings": ["LOW_CONFIDENCE"],
            "metadata": {"input_subject_count": len(subjects)},
        }

    if len(reliable) == 1:
        subject = reliable[0]
        bbox = subject["bbox"]
        if is_low_partial_bbox(bbox, video):
            return preserve_full_frame(
                "The reliable subject box appears to be a low partial-body detection, so preserve the full frame instead of tracking a likely outlier.",
                [subject["track_id"]],
                video,
                ["PARTIAL_LOW_BODY_BBOX"],
                {"input_subject_count": len(subjects)},
            )
        if bbox["w"] > target["width"] * SINGLE_SUBJECT_MAX_WIDTH:
            return preserve_full_frame(
                "The reliable subject is wider than the safe 9:16 crop, so preserve the full frame.",
                [subject["track_id"]],
                video,
                ["SUBJECT_TOO_WIDE"],
                {"input_subject_count": len(subjects)},
            )
        crop = centered_crop_for_bbox(bbox, video, target)
        margin_px = target["width"] * CROP_EDGE_MARGIN
        if not bbox_inside_crop(bbox, crop, margin_px):
            return {
                "strategy": "CENTER_FALLBACK",
                "crop": center,
                "subjects": [subject["track_id"]],
                "reason": "Tracking crop would place the subject too close to the crop edge, so use center fallback.",
                "warnings": ["CROP_EDGE_RISK"],
                "metadata": {"input_subject_count": len(subjects)},
            }
        return {
            "strategy": "TRACK",
            "crop": crop,
            "subjects": [subject["track_id"]],
            "reason": "One reliable subject fits inside the 9:16 crop, so track that subject.",
            "warnings": [],
            "metadata": {"input_subject_count": len(subjects)},
        }

    group = union_bbox(reliable)
    if group["w"] > target["width"] * MULTI_SUBJECT_MAX_SPAN:
        return preserve_full_frame(
            "Multiple reliable subjects are too far apart horizontally for a safe 9:16 crop, so preserve the full frame.",
            [s["track_id"] for s in reliable],
            video,
            ["MULTI_SUBJECT_SPAN_TOO_WIDE"],
            {"input_subject_count": len(subjects)},
        )

    crop = centered_crop_for_bbox(group, video, target)
    margin_px = target["width"] * CROP_EDGE_MARGIN
    risky = [s["track_id"] for s in reliable if not bbox_inside_crop(s["bbox"], crop, margin_px)]
    if risky:
        return preserve_full_frame(
            "At least one reliable subject would be clipped by the shared crop, so preserve the full frame.",
            [s["track_id"] for s in reliable],
            video,
            ["MULTI_SUBJECT_CROP_RISK"],
            {"risky_subjects": risky, "input_subject_count": len(subjects)},
        )

    return {
        "strategy": "TRACK",
        "crop": crop,
        "subjects": [s["track_id"] for s in reliable],
        "reason": "Multiple reliable subjects fit inside one 9:16 crop, so track the group.",
        "warnings": [],
        "metadata": {"input_subject_count": len(subjects)},
    }


def sample_interval(frames, video):
    times = [f["time_s"] for f in frames]
    gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
    if gaps:
        return sorted(gaps)[len(gaps) // 2]
    return video["duration_s"]


def convert_track_to_letterbox(item, video, warning):
    item["strategy"] = "LETTERBOX"
    item["crop"] = full_frame_crop(video)
    item["reason"] = "The TRACK crop is a temporal outlier compared with neighboring samples, so preserve the full frame."
    item["warnings"] = ["PRESERVE_FULL_FRAME", warning]
    item["metadata"] = {
        **item.get("metadata", {}),
        "preserve_full_frame": True,
        "temporal_guard": warning,
    }


def apply_temporal_guards(planned, video, target):
    for idx in range(1, len(planned) - 1):
        item = planned[idx]
        if item["strategy"] != "TRACK":
            continue

        prev_item = planned[idx - 1]
        next_item = planned[idx + 1]
        prev_letterbox = prev_item["strategy"] == "LETTERBOX"
        next_letterbox = next_item["strategy"] == "LETTERBOX"
        jump_threshold_px = video["width"] * CROP_JUMP_THRESHOLD
        crop_x = item["crop"]["x"]
        prev_jump = abs(crop_x - prev_item["crop"]["x"]) > jump_threshold_px
        next_jump = abs(crop_x - next_item["crop"]["x"]) > jump_threshold_px
        if prev_letterbox and next_letterbox and prev_jump and next_jump:
            convert_track_to_letterbox(item, video, "ISOLATED_TRACK_CROP_JUMP")


def build_samples_and_segments(tracks, video, target):
    frames = sorted(tracks["frames"], key=lambda f: f["time_s"])
    interval = sample_interval(frames, video)
    planned = []
    for frame in frames:
        item = plan_frame(frame, video, target)
        item.update({
            "time_s": frame["time_s"],
            "frame_index": frame["frame_index"],
        })
        planned.append(item)
    apply_temporal_guards(planned, video, target)

    segments = []
    current = None
    seg_index = 0
    for idx, item in enumerate(planned):
        scene_id = f"scene-{seg_index + 1:03d}" if current is None else current["scene_id"]
        if current is None or item["strategy"] != current["strategy"] or item["warnings"] != current["warnings"]:
            if current is not None:
                segments.append(current)
            seg_index += 1
            scene_id = f"scene-{seg_index:03d}"
            current = {
                "segment_id": f"seg-{seg_index:03d}",
                "start_s": max(0.0, round(item["time_s"] - interval / 2, 3)),
                "end_s": min(video["duration_s"], round(item["time_s"] + interval / 2, 3)),
                "scene_id": scene_id,
                "strategy": item["strategy"],
                "reason": item["reason"],
                "subjects": item["subjects"],
                "crop": item["crop"],
                "warnings": item["warnings"],
                "metadata": {
                    **item["metadata"],
                    "sample_count": 1,
                    "representative_time_s": item["time_s"],
                },
            }
        else:
            current["end_s"] = min(video["duration_s"], round(item["time_s"] + interval / 2, 3))
            current["subjects"] = sorted(set(current["subjects"]) | set(item["subjects"]))
            current["metadata"]["sample_count"] += 1

        item["segment_id"] = current["segment_id"]
        item["scene_id"] = current["scene_id"]

    if current is not None:
        segments.append(current)

    samples = []
    for item in planned:
        samples.append({
            "time_s": item["time_s"],
            "frame_index": item["frame_index"],
            "segment_id": item["segment_id"],
            "scene_id": item["scene_id"],
            "strategy": item["strategy"],
            "crop": item["crop"],
            "reason": item["reason"],
            "warnings": item["warnings"],
            "metadata": item["metadata"],
        })
    return segments, samples


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    return t * t * (3 - 2 * t)


def interpolate_crop(a, b, t, video):
    return clamp_crop(
        lerp(a["x"], b["x"], t),
        lerp(a["y"], b["y"], t),
        lerp(a["w"], b["w"], t),
        lerp(a["h"], b["h"], t),
        video,
    )


def limit_crop_speed(prev_crop, next_crop, dt, video):
    if dt <= 0:
        return next_crop
    prev_cx = prev_crop["x"] + prev_crop["w"] / 2
    next_cx = next_crop["x"] + next_crop["w"] / 2
    max_step = video["width"] * MAX_CROP_CENTER_SPEED * dt
    delta = next_cx - prev_cx
    if abs(delta) <= max_step:
        return next_crop
    limited_cx = prev_cx + math.copysign(max_step, delta)
    return clamp_crop(limited_cx - next_crop["w"] / 2, next_crop["y"], next_crop["w"], next_crop["h"], video)


def clone_sample(sample, time_s, video):
    cloned = {
        **sample,
        "time_s": round(time_s, 3),
        "frame_index": int(round(time_s * video["fps"])),
        "crop": dict(sample["crop"]),
        "warnings": list(sample.get("warnings", [])),
        "metadata": dict(sample.get("metadata", {})),
    }
    return cloned


def build_dense_crop_path_samples(samples, video, interval_s=DENSE_SAMPLE_INTERVAL_S):
    if not samples:
        return []

    sparse = sorted(samples, key=lambda s: s["time_s"])
    dense = []
    t = 0.0
    cursor = 0
    prev_dense_crop = None
    while t <= video["duration_s"] + 1e-6:
        while cursor + 1 < len(sparse) and t > sparse[cursor + 1]["time_s"]:
            cursor += 1

        cur = sparse[cursor]
        nxt = sparse[cursor + 1] if cursor + 1 < len(sparse) else None
        if nxt and cur["strategy"] == "TRACK" and nxt["strategy"] == "TRACK" and nxt["time_s"] > cur["time_s"]:
            frac = (t - cur["time_s"]) / (nxt["time_s"] - cur["time_s"])
            frac = max(0.0, min(1.0, frac))
            item = clone_sample(cur, t, video)
            item["crop"] = interpolate_crop(cur["crop"], nxt["crop"], ease(frac), video)
            item["metadata"] = {
                **item["metadata"],
                "dense_interpolation": "track_to_track",
                "source_sample_a": cur["time_s"],
                "source_sample_b": nxt["time_s"],
            }
        else:
            nearest = cur
            if nxt and abs(nxt["time_s"] - t) < abs(cur["time_s"] - t):
                nearest = nxt
            item = clone_sample(nearest, t, video)
            item["metadata"] = {
                **item["metadata"],
                "dense_interpolation": "nearest_strategy_sample",
                "source_sample": nearest["time_s"],
            }

        if item["strategy"] == "TRACK" and prev_dense_crop is not None:
            item["crop"] = limit_crop_speed(prev_dense_crop, item["crop"], interval_s, video)
        prev_dense_crop = item["crop"]
        dense.append(item)
        t += interval_s

    return dense


def validate_plan(plan):
    if plan.get("schema_version") != "reframe-plan.v1":
        fail("reframe_plan.json must use schema_version reframe-plan.v1")
    video = plan["video"]
    for segment in plan["segments"]:
        crop = segment["crop"]
        if crop["x"] < 0 or crop["y"] < 0:
            fail("crop window may not be negative")
        if crop["x"] + crop["w"] > video["width"] + 0.01:
            fail("crop window exceeds source width")
        if crop["y"] + crop["h"] > video["height"] + 0.01:
            fail("crop window exceeds source height")
        if not segment.get("reason"):
            fail("each segment must include reason")


def write_summary(path, metrics, plan_path, crop_path):
    lines = [
        "# video-vertical-reframe Phase2 planning summary",
        "",
        "## Outputs",
        "",
        f"- reframe plan: `{plan_path}`",
        f"- crop path: `{crop_path}`",
        "",
        "## Strategy Counts",
        "",
        f"- TRACK: {metrics['strategy_counts'].get('TRACK', 0)}",
        f"- LETTERBOX: {metrics['strategy_counts'].get('LETTERBOX', 0)}",
        f"- CENTER_FALLBACK: {metrics['strategy_counts'].get('CENTER_FALLBACK', 0)}",
        "",
        "## Notes",
        "",
        "- Phase2 does not render a final vertical video.",
        "- Planning consumes existing subject tracks and does not re-run detection.",
        "- Review plan_contact_sheet.jpg and plan_preview.mp4 before Phase3.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    global SINGLE_SUBJECT_MAX_WIDTH

    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--tracks", required=True)
    ap.add_argument("--out", default="work/vertical-reframe")
    ap.add_argument("--single-subject-max-width", type=float, default=SINGLE_SUBJECT_MAX_WIDTH)
    ap.add_argument("--ffprobe")
    args = ap.parse_args()

    SINGLE_SUBJECT_MAX_WIDTH = args.single_subject_max_width

    started = time.time()
    source = Path(args.source)
    tracks_path = Path(args.tracks)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    artifacts = out / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        fail(f"source video not found: {source}")
    if not tracks_path.exists():
        fail(f"tracks.json not found: {tracks_path}")

    ffprobe = resolve_tool("ffprobe", args.ffprobe)
    probed = probe_video(source, ffprobe)
    tracks = load_tracks(tracks_path)
    video = {**probed, "source": str(source)}
    target = target_from_video(video)
    segments, samples = build_samples_and_segments(tracks, video, target)
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    plan = {
        "schema_version": "reframe-plan.v1",
        "video": video,
        "target": target,
        "source_tracks": {
            "path": str(tracks_path),
            "schema_version": "subject-tracks.v1",
            "mode": "external",
        },
        "producer": {
            "skill": "video-vertical-reframe",
            "created_at": created_at,
            "planner": "phase2-basic-planner",
        },
        "segments": segments,
        "metadata": {
            "phase": "Phase2 Reframe Planning only",
            "low_confidence_threshold": LOW_CONFIDENCE,
            "multi_subject_max_span_fraction": MULTI_SUBJECT_MAX_SPAN,
            "single_subject_max_width_fraction": SINGLE_SUBJECT_MAX_WIDTH,
            "crop_edge_margin_fraction": CROP_EDGE_MARGIN,
        },
    }
    validate_plan(plan)

    dense_samples = build_dense_crop_path_samples(samples, video)
    crop_path = {
        "schema_version": "crop-path.v1",
        "video": video,
        "target": target,
        "source_plan": {
            "path": str(out / "reframe_plan.json"),
            "schema_version": "reframe-plan.v1",
        },
        "producer": {
            "skill": "video-vertical-reframe",
            "created_at": created_at,
            "planner": "phase2-basic-planner",
        },
        "samples": dense_samples,
        "metadata": {
            "phase": "Phase2 Reframe Planning only",
            "smoothing": "dense 1-second crop path; TRACK-to-TRACK crop x/y/w/h uses eased interpolation with max center speed limiting",
            "source_samples": len(samples),
            "dense_sample_interval_s": DENSE_SAMPLE_INTERVAL_S,
            "max_crop_center_speed_fraction_per_s": MAX_CROP_CENTER_SPEED,
        },
    }

    plan_path = out / "reframe_plan.json"
    crop_path_path = out / "crop_path.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    crop_path_path.write_text(json.dumps(crop_path, indent=2) + "\n", encoding="utf-8")

    counts = Counter(sample["strategy"] for sample in dense_samples)
    total = max(1, len(dense_samples))
    metrics = {
        "schema_version": "reframe-plan-metrics.v1",
        "samples": len(dense_samples),
        "source_samples": len(samples),
        "segments": len(segments),
        "target_width": target["width"],
        "target_height": target["height"],
        "strategy_counts": dict(counts),
        "strategy_ratios": {k: round(v / total, 4) for k, v in sorted(counts.items())},
        "warning_counts": dict(Counter(w for sample in dense_samples for w in sample.get("warnings", []))),
        "wall_time_s": round(time.time() - started, 3),
        "outputs": {
            "reframe_plan": str(plan_path),
            "crop_path": str(crop_path_path),
            "plan_summary": str(artifacts / "plan_summary.md"),
        },
    }
    metrics_path = out / "plan_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    write_summary(artifacts / "plan_summary.md", metrics, plan_path, crop_path_path)

    print(f"wrote {plan_path}")
    print(f"wrote {crop_path_path}")
    print(f"wrote {metrics_path}")
    print(f"wrote {artifacts / 'plan_summary.md'}")


if __name__ == "__main__":
    main()
