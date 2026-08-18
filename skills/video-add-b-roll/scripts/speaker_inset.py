"""Build and validate speaker-inset evidence and contextual previews."""

import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageOps

import projectlib


LAYOUT_PRESETS = ("focused-panel", "full-bleed-wash", "corner-pip")
PRESET_ANCHORS = {
    "focused-panel": ("lower-center",),
    "full-bleed-wash": ("upper-center",),
    "corner-pip": ("top-left", "top-right"),
}
ALLOWED_ANCHORS = {
    anchor for anchors in PRESET_ANCHORS.values() for anchor in anchors
}
ARTIFACT_SHOT_STATUSES = {"composite_pending", "selected", "normalized", "verified"}
STYLE_FIELDS = {
    "enabled", "shape", "width_ratio", "aspect_ratio", "border",
    "corner_radius_ratio", "margin_ratio", "reserved_bottom_ratio",
}
DEFAULT_STYLE = {
    "enabled": True,
    "shape": "rounded-rectangle",
    "width_ratio": 0.39,
    "aspect_ratio": 0.80,
    "border": {"width_px": 3, "color": "#9E9E9E"},
    "corner_radius_ratio": 0.10,
    "margin_ratio": 0.04,
    "reserved_bottom_ratio": 0.20,
}
SPEAKER_STATUSES = {"confirmed", "ambiguous", "absent", "occluded"}
PRESET_ASSESSMENTS = {"pass", "warn", "fail"}
RECOMMENDATION_CONFIDENCE = {"high", "medium", "low"}
RANGE_EPSILON = 1e-6
SHORT_FLASH_SECONDS = 1.5


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def style_enabled(style):
    return isinstance(style, dict) and style.get("enabled") is True


def default_style():
    return copy.deepcopy(DEFAULT_STYLE)


def style_errors(style):
    """Return strict project-level speaker inset style errors."""
    if not isinstance(style, dict):
        return ["speaker_inset_style must be an object"]
    if not isinstance(style.get("enabled"), bool):
        return ["speaker_inset_style enabled must be a boolean"]
    if not style["enabled"]:
        return []

    errors = []
    unsupported = sorted(set(style) - STYLE_FIELDS)
    for field in unsupported:
        errors.append(f"speaker_inset_style {field} is unsupported; re-author the enabled style")
    shape = style.get("shape")
    if shape != "rounded-rectangle":
        errors.append("speaker_inset_style shape must be rounded-rectangle")
    width = _number(style.get("width_ratio"))
    if width is None or not 0 < width < 1:
        errors.append("speaker_inset_style width_ratio must be between 0 and 1")
    aspect = _number(style.get("aspect_ratio"))
    if aspect is None or aspect <= 0:
        errors.append("speaker_inset_style aspect_ratio must be positive")
    margin = _number(style.get("margin_ratio"))
    if margin is None or not 0 <= margin < 0.5:
        errors.append("speaker_inset_style margin_ratio must be between 0 and 0.5")
    reserved = _number(style.get("reserved_bottom_ratio"))
    if reserved is None or not 0 <= reserved < 1:
        errors.append("speaker_inset_style reserved_bottom_ratio must be between 0 and 1")

    border = style.get("border")
    if not isinstance(border, dict):
        errors.append("speaker_inset_style border must be an object")
    else:
        border_width = border.get("width_px")
        if (not isinstance(border_width, int) or isinstance(border_width, bool)
                or border_width < 0):
            errors.append("speaker_inset_style border width_px must be a nonnegative integer")
        if not isinstance(border.get("color"), str) or not re.fullmatch(
                r"#[0-9a-fA-F]{6}", border["color"]):
            errors.append("speaker_inset_style border color must be #RRGGBB")

    corner = style.get("corner_radius_ratio")
    if _number(corner) is None or not 0 <= float(corner) <= 0.5:
        errors.append(
            "speaker_inset_style corner_radius_ratio must be between 0 and 0.5 "
            "for rounded-rectangle"
        )
    if width is not None and margin is not None and width + 2 * margin > 1:
        errors.append("speaker_inset_style width and margins do not fit the frame")
    return errors


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_document_sha256(value):
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    encoded = text.replace("\n", os.linesep).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value):
    return (
        isinstance(value, str) and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def _range(value):
    if not isinstance(value, dict):
        return None
    start, end = _number(value.get("start_s")), _number(value.get("end_s"))
    if start is None or end is None or end <= start:
        return None
    return start, end


def _fps(timeline):
    value = timeline.get("fps") if isinstance(timeline, dict) else None
    num = value.get("num") if isinstance(value, dict) else None
    den = value.get("den") if isinstance(value, dict) else None
    if (not isinstance(num, int) or isinstance(num, bool) or num <= 0
            or not isinstance(den, int) or isinstance(den, bool) or den <= 0):
        raise ValueError("timeline fps num and den must be positive integers")
    return num, den


def _frame_index(value, frame_duration):
    number = _number(value)
    if number is None:
        return None
    index = round(number / frame_duration)
    return index if abs(number - index * frame_duration) <= RANGE_EPSILON else None


def _frame_time(index, frame_duration):
    return round(index * frame_duration, 9)


def _valid_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _inside(root, path, label):
    root, path = Path(root).resolve(), Path(path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside project_root") from exc
    return path


def _probe_video(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type,width,height,avg_frame_rate:format=duration",
        "-of", "json", str(path),
    ], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    payload = json.loads(result.stdout)
    streams = payload.get("streams") if isinstance(payload, dict) else None
    video = next((item for item in streams or []
                  if isinstance(item, dict) and item.get("codec_type") == "video"), None)
    if not isinstance(video, dict):
        raise ValueError("review video has no video stream")
    width, height = video.get("width"), video.get("height")
    raw_duration = payload.get("format", {}).get("duration")
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        duration = None
    if duration is not None and not math.isfinite(duration):
        duration = None
    rate = str(video.get("avg_frame_rate", "")).split("/", 1)
    if (not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0
            or duration is None or duration <= 0 or len(rate) != 2):
        raise ValueError("review video probe is invalid")
    try:
        num, den = int(rate[0]), int(rate[1])
    except ValueError as exc:
        raise ValueError("review video fps is invalid") from exc
    if num <= 0 or den <= 0:
        raise ValueError("review video fps is invalid")
    return {
        "width": width, "height": height, "duration_s": duration,
        "fps": {"num": num, "den": den},
    }


def _ffmpeg_version():
    result = subprocess.run(
        ["ffmpeg", "-version"], check=True, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout.splitlines()[0].strip()


def _detect_scene_times(video, threshold):
    if _number(threshold) is None or not 0 < float(threshold) < 1:
        raise ValueError("scene threshold must be between 0 and 1")
    expression = f"select='gt(scene,{float(threshold):.6f})',showinfo"
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(video), "-vf", expression,
        "-an", "-f", "null", os.devnull,
    ], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [
        float(value) for value in re.findall(r"pts_time:([0-9]+(?:\.[0-9]+)?)", result.stderr)
    ]


def _extract_frame(video, time_s, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(video),
        "-ss", f"{float(time_s):.9f}", "-frames:v", "1",
        "-vf", "scale=960:-2", str(output),
    ], check=True)


def _validate_jpeg(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            if image.format != "JPEG" or width <= 0 or height <= 0:
                raise ValueError
    except (OSError, SyntaxError, ValueError) as exc:
        raise ValueError(f"invalid evidence JPEG: {path}") from exc


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=path.parent, suffix=".json", encoding="utf-8") as handle:
            temporary = Path(handle.name)
        projectlib.write_json(temporary, value)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _mapped_words(transcript, timeline):
    mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    return [
        word for segment in mapped.get("segments", []) if isinstance(segment, dict)
        for word in segment.get("words", []) if isinstance(word, dict)
    ]


def _candidate_boundaries(shot_range, timeline, scene_times, frame_duration):
    start_frame = round(shot_range[0] / frame_duration)
    end_frame = round(shot_range[1] / frame_duration)
    sources = {start_frame: {"shot-start"}, end_frame: {"shot-end"}}
    for clip in timeline.get("clips", []):
        program = _range(clip.get("program_range")) if isinstance(clip, dict) else None
        if not program:
            continue
        for value in program:
            frame = round(value / frame_duration)
            if start_frame < frame < end_frame:
                sources.setdefault(frame, set()).add("timeline-cut")
    for value in scene_times:
        frame = round(float(value) / frame_duration)
        if start_frame < frame < end_frame:
            sources.setdefault(frame, set()).add("scene")
    return sorted(sources), sources


def _point_frames(start_frame, end_frame):
    last = end_frame - 1
    centers = sorted({start_frame, (start_frame + last) // 2, last})
    return [(center, sorted({
        max(start_frame, center - 1), center, min(last, center + 1),
    })) for center in centers]


def _supplemental_frames(center, start_frame, end_frame):
    last = end_frame - 1
    return list(range(max(start_frame, center - 3), min(last, center + 3) + 1))


def _normalized_supplemental_points(value, frame_duration):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("supplemental_points must be an object")
    normalized = {}
    for subshot_id, times in value.items():
        if not isinstance(subshot_id, str) or not subshot_id.strip():
            raise ValueError("supplemental_points subshot IDs must be non-empty strings")
        if not isinstance(times, list) or not times:
            raise ValueError(f"{subshot_id} supplemental_points must be a non-empty list")
        frames = []
        for time_s in times:
            number = _number(time_s)
            if number is None:
                raise ValueError(f"{subshot_id} supplemental point must be finite")
            frames.append(round(number / frame_duration))
        if len(frames) != len(set(frames)):
            raise ValueError(f"{subshot_id} supplemental points must be unique")
        normalized[subshot_id] = [_frame_time(frame, frame_duration) for frame in sorted(frames)]
    return normalized


def prepare_evidence(plan, timeline, transcript, review_video, project_root, *,
                     scene_threshold=0.32, supplemental_points=None):
    """Extract immutable temporal evidence for every composite-pending shot."""
    if not isinstance(plan, dict) or not isinstance(timeline, dict) or not isinstance(transcript, dict):
        raise ValueError("plan, timeline, and transcript must be objects")
    root = Path(project_root).resolve()
    video = _inside(root, review_video, "review video")
    if not video.is_file():
        raise FileNotFoundError(f"review video is missing: {video}")
    selection = plan.get("selection")
    if (not isinstance(selection, dict)
            or selection.get("status") != "approved"
            or selection.get("submission_intent") != "approve_selection"
            or selection.get("approval_scope") != "b-roll-selection"):
        raise ValueError("approved B-roll selection is required")
    selection_path = root / "work" / str(selection.get("path", ""))
    if (not selection_path.is_file() or not _is_sha256(selection.get("sha256"))
            or _sha256_file(selection_path) != selection["sha256"]):
        raise ValueError("approved selection file is missing or stale")
    style = plan.get("speaker_inset_style")
    validation = style_errors(style) if style is not None else ["speaker_inset_style is required"]
    if validation or not style_enabled(style):
        raise ValueError("enabled speaker_inset_style is invalid: " + "; ".join(validation))
    expected_video_hash = plan.get("input_hashes", {}).get("review_video_sha256")
    if not _is_sha256(expected_video_hash) or _sha256_file(video) != expected_video_hash:
        raise ValueError("review video SHA-256 is stale")
    num, den = _fps(timeline)
    frame_duration = den / num
    supplements = _normalized_supplemental_points(supplemental_points, frame_duration)
    probe = _probe_video(video)
    if probe.get("fps") != timeline.get("fps"):
        raise ValueError("review video fps does not match timeline")
    duration = _number(timeline.get("program_duration_s"))
    if duration is None or abs(probe["duration_s"] - duration) > frame_duration + RANGE_EPSILON:
        raise ValueError("review video duration does not match timeline")
    scene_times = sorted({
        _frame_time(round(float(value) / frame_duration), frame_duration)
        for value in _detect_scene_times(video, scene_threshold)
        if _number(value) is not None and 0 < float(value) < duration
    })
    ffmpeg_version = _ffmpeg_version()
    subject = {
        "timeline_sha256": plan.get("input_hashes", {}).get("timeline_sha256"),
        "transcript_sha256": plan.get("input_hashes", {}).get("transcript_sha256"),
        "review_video_sha256": expected_video_hash,
        "selection_sha256": selection["sha256"],
        "style_sha256": _canonical_sha256(style),
        "scene_threshold": float(scene_threshold),
        "scene_times": scene_times,
        "supplemental_points": supplements,
        "ffmpeg_version": ffmpeg_version,
    }
    analysis_id = _canonical_sha256(subject)[:20]
    cache_root = root / "work/cache/b-roll/speaker-inset/evidence"
    final_dir = cache_root / analysis_id
    stage = cache_root / f".{analysis_id}-{uuid.uuid4().hex}.part"
    stage.mkdir(parents=True, exist_ok=False)
    words = _mapped_words(transcript, timeline)
    shots = []
    try:
        for shot in plan.get("shots", []):
            if not isinstance(shot, dict) or shot.get("status") != "composite_pending":
                continue
            shot_range = _range(shot.get("program_range"))
            if not shot_range:
                raise ValueError(f"{shot.get('id')} program_range is invalid")
            boundary_frames, boundary_sources = _candidate_boundaries(
                shot_range, timeline, scene_times, frame_duration,
            )
            subshots = []
            for index, (start_frame, end_frame) in enumerate(
                    zip(boundary_frames, boundary_frames[1:]), 1):
                if end_frame <= start_frame:
                    continue
                subshot_id = f"{shot['id']}-subshot-{index:03d}"
                evidence_points = []
                for point_index, (center, burst) in enumerate(
                        _point_frames(start_frame, end_frame), 1):
                    frames = []
                    for burst_index, frame_index in enumerate(burst, 1):
                        basename = (
                            f"{shot['id']}-{index:03d}-{point_index:02d}-{burst_index:02d}.jpg"
                        )
                        staged_frame = stage / basename
                        frame_time = _frame_time(frame_index, frame_duration)
                        _extract_frame(video, frame_time, staged_frame)
                        _validate_jpeg(staged_frame)
                        frames.append({
                            "program_time_s": frame_time,
                            "path": (
                                f"cache/b-roll/speaker-inset/evidence/{analysis_id}/{basename}"
                            ),
                            "sha256": _sha256_file(staged_frame),
                        })
                    evidence_points.append({
                        "program_time_s": _frame_time(center, frame_duration),
                        "evidence_kind": "baseline",
                        "frames": frames,
                    })
                for supplemental_index, time_s in enumerate(
                        supplements.get(subshot_id, []), 1):
                    center = round(time_s / frame_duration)
                    if not start_frame <= center < end_frame:
                        raise ValueError(
                            f"{subshot_id} supplemental point must remain inside its subshot"
                        )
                    frames = []
                    for burst_index, frame_index in enumerate(
                            _supplemental_frames(center, start_frame, end_frame), 1):
                        basename = (
                            f"{shot['id']}-{index:03d}-supplemental-"
                            f"{supplemental_index:02d}-{burst_index:02d}.jpg"
                        )
                        staged_frame = stage / basename
                        frame_time = _frame_time(frame_index, frame_duration)
                        _extract_frame(video, frame_time, staged_frame)
                        _validate_jpeg(staged_frame)
                        frames.append({
                            "program_time_s": frame_time,
                            "path": (
                                f"cache/b-roll/speaker-inset/evidence/{analysis_id}/{basename}"
                            ),
                            "sha256": _sha256_file(staged_frame),
                        })
                    evidence_points.append({
                        "program_time_s": _frame_time(center, frame_duration),
                        "evidence_kind": "supplemental",
                        "frames": frames,
                    })
                source_names = sorted(boundary_sources.get(start_frame, {"scene"}))
                subshots.append({
                    "id": subshot_id,
                    "program_range": {
                        "start_s": _frame_time(start_frame, frame_duration),
                        "end_s": _frame_time(end_frame, frame_duration),
                    },
                    "boundary_source": "+".join(source_names),
                    "evidence_points": evidence_points,
                })
            shots.append({
                "shot_id": shot["id"],
                "program_range": copy.deepcopy(shot["program_range"]),
                "transcript_words": [
                    copy.deepcopy(word) for word in words
                    if (_range(word.get("program_range"))
                        and _range(word["program_range"])[0] >= shot_range[0] - RANGE_EPSILON
                        and _range(word["program_range"])[1] <= shot_range[1] + RANGE_EPSILON)
                ],
                "subshots": subshots,
            })
        known_subshots = {
            subshot["id"] for shot in shots for subshot in shot.get("subshots", [])
        }
        unknown_supplements = sorted(set(supplements) - known_subshots)
        if unknown_supplements:
            raise ValueError(
                "supplemental_points reference unknown subshots: "
                + ", ".join(unknown_supplements)
            )
        if final_dir.exists():
            shutil.rmtree(final_dir)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, final_dir)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    packet = {
        "schema_version": 1,
        "analysis_id": analysis_id,
        **subject,
        "timeline_fps": copy.deepcopy(timeline["fps"]),
        "review_video_probe": probe,
        "scene_detection": {
            "algorithm": "ffmpeg-scene-score",
            "threshold": float(scene_threshold),
            "ffmpeg_version": ffmpeg_version,
            "candidate_times_s": scene_times,
        },
        "shots": shots,
    }
    output = root / "work/b-roll/speaker-inset-analysis.json"
    _atomic_json(output, packet)
    result = copy.deepcopy(plan)
    result["speaker_inset"] = {
        "analysis": {
            "path": "b-roll/speaker-inset-analysis.json",
            "sha256": _sha256_file(output),
            "analysis_id": analysis_id,
        }
    }
    return result


def analysis_errors(analysis, plan, timeline, transcript, *, project_root=None, verify_files=False):
    errors = []
    if not isinstance(analysis, dict):
        return ["speaker analysis must be an object"]
    if analysis.get("schema_version") != 1:
        errors.append("speaker analysis schema_version must be 1")
    selection = plan.get("selection") if isinstance(plan, dict) else None
    style = plan.get("speaker_inset_style") if isinstance(plan, dict) else None
    input_hashes = plan.get("input_hashes", {}) if isinstance(plan, dict) else {}
    expected = {
        "selection_sha256": selection.get("sha256") if isinstance(selection, dict) else None,
        "style_sha256": _canonical_sha256(style) if isinstance(style, dict) else None,
        "review_video_sha256": input_hashes.get("review_video_sha256"),
        "timeline_sha256": input_hashes.get("timeline_sha256"),
        "transcript_sha256": input_hashes.get("transcript_sha256"),
    }
    for field, value in expected.items():
        if analysis.get(field) != value:
            errors.append(f"speaker analysis {field} does not match")
    if analysis.get("timeline_fps") != timeline.get("fps"):
        errors.append("speaker analysis timeline_fps does not match")
    try:
        num, den = _fps(timeline)
        frame_duration = den / num
    except ValueError as exc:
        return errors + [str(exc)]
    expected_shots = {
        shot.get("id"): shot for shot in plan.get("shots", [])
        if isinstance(shot, dict) and shot.get("status") in ARTIFACT_SHOT_STATUSES
    }
    shots = analysis.get("shots")
    if not isinstance(shots, list):
        return errors + ["speaker analysis shots must be a list"]
    if [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] != list(expected_shots):
        errors.append("speaker analysis shots do not match composite_pending shots")
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("shot_id") not in expected_shots:
            continue
        expected_range = _range(expected_shots[shot["shot_id"]].get("program_range"))
        subshots = shot.get("subshots")
        if not isinstance(subshots, list) or not subshots:
            errors.append(f"{shot['shot_id']} speaker analysis requires subshots")
            continue
        previous_end = expected_range[0] if expected_range else None
        for subshot in subshots:
            subshot_range = _range(subshot.get("program_range")) if isinstance(subshot, dict) else None
            if not subshot_range:
                errors.append(f"{shot['shot_id']} subshot range is invalid")
                continue
            if previous_end is None or abs(subshot_range[0] - previous_end) > RANGE_EPSILON:
                errors.append(f"{shot['shot_id']} subshots must be continuous")
            previous_end = subshot_range[1]
            if (_frame_index(subshot_range[0], frame_duration) is None
                    or _frame_index(subshot_range[1], frame_duration) is None):
                errors.append(f"{shot['shot_id']} subshots must align to timeline frames")
            points = subshot.get("evidence_points")
            if not isinstance(points, list) or not points:
                errors.append(f"{subshot.get('id')} requires temporal evidence points")
                continue
            for point in points:
                frames = point.get("frames") if isinstance(point, dict) else None
                if not isinstance(point, dict) or point.get("evidence_kind") not in {
                        "baseline", "supplemental"}:
                    errors.append(
                        f"{subshot.get('id')} evidence point kind must be baseline or supplemental"
                    )
                if not isinstance(frames, list) or not frames:
                    errors.append(f"{subshot.get('id')} evidence point requires frames")
                    continue
                for frame in frames:
                    if not isinstance(frame, dict) or not _is_sha256(frame.get("sha256")):
                        errors.append(f"{subshot.get('id')} evidence frame binding is invalid")
                        continue
                    if verify_files and project_root:
                        path = Path(project_root).resolve() / "work" / str(frame.get("path", ""))
                        try:
                            path.resolve().relative_to((Path(project_root).resolve() / "work").resolve())
                        except ValueError:
                            errors.append(f"{subshot.get('id')} evidence frame path escapes work")
                        else:
                            if not path.is_file():
                                errors.append(f"{subshot.get('id')} evidence frame is missing")
                            elif _sha256_file(path) != frame["sha256"]:
                                errors.append(f"{subshot.get('id')} evidence frame SHA-256 is stale")
        if expected_range and (previous_end is None or abs(previous_end - expected_range[1]) > RANGE_EPSILON):
            errors.append(f"{shot['shot_id']} subshots must cover the shot")
    return errors


def _roi_errors(roi):
    if not isinstance(roi, dict):
        return ["ROI must be an object"]
    values = {key: _number(roi.get(key)) for key in ("x", "y", "width", "height")}
    if any(value is None for value in values.values()):
        return ["ROI values must be finite numbers"]
    if values["width"] <= 0 or values["height"] <= 0:
        return ["ROI must have positive area"]
    if (values["x"] < 0 or values["y"] < 0
            or values["x"] + values["width"] > 1 + RANGE_EPSILON
            or values["y"] + values["height"] > 1 + RANGE_EPSILON):
        return ["ROI must remain inside the A-roll frame"]
    return []


def _preset_anchor_errors(preset, anchor, label):
    if preset not in LAYOUT_PRESETS:
        return [f"{label} preset is invalid"]
    if anchor not in PRESET_ANCHORS[preset]:
        return [f"{label} preset/anchor combination is invalid"]
    return []


def _recommendation_errors(recommendation, label):
    if not isinstance(recommendation, dict):
        return [f"{label} layout_recommendation must be an object"]
    errors = _preset_anchor_errors(
        recommendation.get("preset"), recommendation.get("anchor"), label,
    )
    confidence = recommendation.get("confidence")
    if confidence not in RECOMMENDATION_CONFIDENCE:
        errors.append(f"{label} recommendation confidence is invalid")
    if (not isinstance(recommendation.get("rationale"), str)
            or not recommendation["rationale"].strip()):
        errors.append(f"{label} recommendation rationale is required")
    assessments = recommendation.get("preset_assessments")
    if (not isinstance(assessments, dict)
            or set(assessments) != set(LAYOUT_PRESETS)
            or any(value not in PRESET_ASSESSMENTS for value in assessments.values())):
        errors.append(f"{label} must assess all three presets with pass, warn, or fail")
        assessments = {}
    alternate = recommendation.get("alternate")
    if alternate is None:
        if confidence == "low" and any(
                preset != recommendation.get("preset")
                and assessments.get(preset) in {"pass", "warn"}
                for preset in LAYOUT_PRESETS):
            errors.append(f"{label} low-confidence recommendation requires alternate")
    elif confidence != "low":
        errors.append(f"{label} alternate is only valid for low confidence")
    elif not isinstance(alternate, dict) or set(alternate) != {"preset", "anchor"}:
        errors.append(f"{label} alternate must contain only preset and anchor")
    else:
        errors.extend(_preset_anchor_errors(
            alternate.get("preset"), alternate.get("anchor"), f"{label} alternate",
        ))
        alternate_preset = alternate.get("preset")
        if alternate_preset == recommendation.get("preset"):
            errors.append(f"{label} alternate preset must differ from recommendation")
        if assessments.get(alternate_preset) not in {"pass", "warn"}:
            errors.append(f"{label} alternate preset assessment must not fail")
    return errors


def _strategy_errors(strategy):
    if not isinstance(strategy, dict):
        return ["speaker Agent input project_layout_strategy must be an object"]
    errors = []
    primary = strategy.get("primary_preset")
    if primary not in LAYOUT_PRESETS:
        errors.append("speaker Agent input primary_preset is invalid")
    used = strategy.get("used_presets")
    if (not isinstance(used, list) or not 1 <= len(used) <= 3
            or any(preset not in LAYOUT_PRESETS for preset in used)
            or len(used) != len(set(used))):
        errors.append("speaker Agent input used_presets must be unique supported presets")
    elif used[0] != primary:
        errors.append("speaker Agent input used_presets must start with primary_preset")
    if (not isinstance(strategy.get("rationale"), str)
            or not strategy["rationale"].strip()):
        errors.append("speaker Agent input project layout rationale is required")
    return errors


def agent_input_errors(agent_input, analysis, plan, timeline):
    errors = []
    if not isinstance(agent_input, dict):
        return ["speaker Agent input must be an object"]
    if agent_input.get("schema_version") != 1:
        errors.append("speaker Agent input schema_version must be 1")
    if agent_input.get("mode") != "agent":
        errors.append("speaker Agent input mode must be agent")
    for field in ("actor", "rationale"):
        if not isinstance(agent_input.get(field), str) or not agent_input[field].strip():
            errors.append(f"speaker Agent input {field} is required")
    if not _valid_timestamp(agent_input.get("timestamp")):
        errors.append("speaker Agent input timestamp is invalid")
    strategy = agent_input.get("project_layout_strategy")
    errors.extend(_strategy_errors(strategy))
    bindings = plan.get("speaker_inset", {}).get("analysis", {})
    expected = {
        "analysis_sha256": bindings.get("sha256"),
        "selection_sha256": plan.get("selection", {}).get("sha256"),
        "style_sha256": _canonical_sha256(plan.get("speaker_inset_style")),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
    }
    for field, value in expected.items():
        if agent_input.get(field) != value:
            errors.append(f"speaker Agent input {field} does not match")
    try:
        num, den = _fps(timeline)
        frame_duration = den / num
    except ValueError as exc:
        return errors + [str(exc)]
    analysis_shots = {
        shot.get("shot_id"): shot for shot in analysis.get("shots", [])
        if isinstance(shot, dict)
    }
    shots = agent_input.get("shots")
    if not isinstance(shots, list):
        return errors + ["speaker Agent input shots must be a list"]
    if [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] != list(analysis_shots):
        errors.append("speaker Agent input shots do not match analysis")
    recommendations = []
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("shot_id") not in analysis_shots:
            continue
        recommendation = shot.get("layout_recommendation")
        errors.extend(_recommendation_errors(
            recommendation, f"{shot['shot_id']}",
        ))
        if isinstance(recommendation, dict):
            recommendations.append(recommendation)
        expected_subshots = {
            subshot.get("id"): subshot for subshot in analysis_shots[shot["shot_id"]].get("subshots", [])
            if isinstance(subshot, dict)
        }
        subshots = shot.get("subshots")
        if not isinstance(subshots, list):
            errors.append(f"{shot['shot_id']} Agent subshots must be a list")
            continue
        if [item.get("id") for item in subshots if isinstance(item, dict)] != list(expected_subshots):
            errors.append(f"{shot['shot_id']} Agent subshots do not match analysis")
        for item in subshots:
            if not isinstance(item, dict) or item.get("id") not in expected_subshots:
                continue
            label = item["id"]
            status = item.get("speaker_status")
            mode = item.get("display_mode")
            rationale = item.get("rationale")
            keyframes = item.get("keyframes")
            if status not in SPEAKER_STATUSES:
                errors.append(f"{label} speaker_status is invalid")
                continue
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(f"{label} rationale is required")
            if status != "confirmed":
                if mode != "pure_broll" or item.get("anchor") is not None or keyframes != []:
                    errors.append(f"{label} non-confirmed speaker must use pure_broll without keyframes")
                if status == "ambiguous" and not any(
                        point.get("evidence_kind") == "supplemental"
                        for point in expected_subshots[label].get("evidence_points", [])
                        if isinstance(point, dict)):
                    errors.append(
                        f"{label} ambiguous speaker requires supplemental temporal evidence"
                    )
                continue
            if mode != "enabled":
                errors.append(f"{label} confirmed speaker must be enabled")
            recommended_anchor = (
                recommendation.get("anchor") if isinstance(recommendation, dict) else None
            )
            if item.get("anchor") != recommended_anchor:
                errors.append(f"{label} must use the shot-level recommended anchor")
            if not isinstance(keyframes, list) or not keyframes:
                errors.append(f"{label} confirmed speaker requires keyframes")
                continue
            subshot_range = _range(expected_subshots[label].get("program_range"))
            start_frame = round(subshot_range[0] / frame_duration)
            end_frame = round(subshot_range[1] / frame_duration)
            expected_last = end_frame - 1
            seen_frames = []
            for keyframe in keyframes:
                time_s = keyframe.get("program_time_s") if isinstance(keyframe, dict) else None
                frame_index = _frame_index(time_s, frame_duration)
                if frame_index is None:
                    errors.append(f"{label} keyframe must align to timeline frames")
                    continue
                if not start_frame <= frame_index < end_frame:
                    errors.append(f"{label} keyframe must remain inside its subshot")
                if frame_index in seen_frames or (seen_frames and frame_index < seen_frames[-1]):
                    errors.append(f"{label} keyframes must be strictly ordered")
                seen_frames.append(frame_index)
                errors.extend(f"{label} {error}" for error in _roi_errors(keyframe.get("roi")))
            if seen_frames and (seen_frames[0] != start_frame or seen_frames[-1] != expected_last):
                errors.append(f"{label} keyframes must cover its subshot")
    if isinstance(strategy, dict) and isinstance(strategy.get("used_presets"), list):
        assigned = []
        for recommendation in recommendations:
            preset = recommendation.get("preset")
            if preset in LAYOUT_PRESETS and preset not in assigned:
                assigned.append(preset)
        used = strategy["used_presets"]
        if set(used) != set(assigned):
            errors.append("speaker Agent input used_presets must match shot recommendations")
        primary = strategy.get("primary_preset")
        for recommendation in recommendations:
            if recommendation.get("preset") == primary:
                continue
            assessments = recommendation.get("preset_assessments", {})
            if (assessments.get(primary) not in {"warn", "fail"}
                    or assessments.get(recommendation.get("preset")) != "pass"):
                errors.append(
                    "secondary preset requires a warn/fail primary and passing recommendation"
                )
    return errors


def attach_agent_input(plan, analysis, agent_input, timeline, project_root):
    errors = agent_input_errors(agent_input, analysis, plan, timeline)
    if errors:
        raise ValueError("invalid speaker Agent input: " + "; ".join(errors))
    root = Path(project_root).resolve()
    target = root / "work/b-roll/speaker-inset-agent-input.json"
    _atomic_json(target, agent_input)
    result = copy.deepcopy(plan)
    speaker = result.setdefault("speaker_inset", {})
    speaker["agent_input"] = {
        "path": "b-roll/speaker-inset-agent-input.json",
        "sha256": _sha256_file(target),
        "actor": agent_input["actor"],
        "timestamp": agent_input["timestamp"],
    }
    return result


def interpolate_roi(keyframes, program_time_s, subshot_range):
    parsed = _range(subshot_range)
    time_s = _number(program_time_s)
    if not parsed or time_s is None or time_s < parsed[0] or time_s >= parsed[1]:
        raise ValueError("program time is outside subshot")
    if not isinstance(keyframes, list) or not keyframes:
        raise ValueError("keyframes are required")
    ordered = sorted(keyframes, key=lambda item: float(item["program_time_s"]))
    if time_s <= float(ordered[0]["program_time_s"]):
        return copy.deepcopy(ordered[0]["roi"])
    if time_s >= float(ordered[-1]["program_time_s"]):
        return copy.deepcopy(ordered[-1]["roi"])
    left, right = ordered[0], ordered[-1]
    for candidate_left, candidate_right in zip(ordered, ordered[1:]):
        if float(candidate_left["program_time_s"]) <= time_s <= float(candidate_right["program_time_s"]):
            left, right = candidate_left, candidate_right
            break
    start, end = float(left["program_time_s"]), float(right["program_time_s"])
    ratio = 0.0 if end == start else (time_s - start) / (end - start)
    return {
        key: round(float(left["roi"][key]) + (
            float(right["roi"][key]) - float(left["roi"][key])
        ) * ratio, 9)
        for key in ("x", "y", "width", "height")
    }


def _anchor_position(frame_size, inset_size, style, anchor):
    width, height = frame_size
    inset_width, inset_height = inset_size
    margin = round(width * float(style["margin_ratio"]))
    safe_bottom = round(height * (1 - float(style["reserved_bottom_ratio"])))
    if anchor in {"upper-center", "lower-center"}:
        x = (width - inset_width) // 2
    elif anchor == "top-left":
        x = margin
    elif anchor == "top-right":
        x = width - margin - inset_width
    else:
        raise ValueError("speaker inset preset/anchor combination is invalid")
    if anchor in {"top-left", "top-right"}:
        y = margin
    elif anchor == "upper-center":
        y = max(margin, (safe_bottom - inset_height) // 4)
    else:
        # lower-center is exclusive to focused-panel, so place the larger window
        # directly above the reserved subtitle area rather than overlapping its panel.
        y = safe_bottom - inset_height
    if x < 0 or y < 0 or x + inset_width > width or y + inset_height > safe_bottom:
        raise ValueError("speaker inset anchor does not fit the frame or reserved bottom")
    return x, y


def _inset_size(frame_size, style, anchor):
    """Return a proportional window size, clamped only when the safe area is too small."""
    width = max(2, round(frame_size[0] * float(style["width_ratio"])))
    height = max(2, round(width / float(style["aspect_ratio"])))
    safe_height = round(frame_size[1] * (1 - float(style["reserved_bottom_ratio"])))
    if anchor != "lower-center":
        safe_height -= round(frame_size[0] * float(style["margin_ratio"]))
    if height > safe_height:
        height = max(2, safe_height)
        width = max(2, round(height * float(style["aspect_ratio"])))
    return width, height


def _pixel_risk(max_scale_factor):
    if max_scale_factor <= 1.5:
        return "low"
    if max_scale_factor <= 3.0:
        return "medium"
    return "high"


def _find_shot(document, shot_id):
    return next((
        item for item in document.get("shots", [])
        if isinstance(item, dict) and item.get("shot_id") == shot_id
    ), None)


def _find_subshot(shot, subshot_id):
    if not isinstance(shot, dict):
        return None
    return next((
        item for item in shot.get("subshots", [])
        if isinstance(item, dict) and item.get("id") == subshot_id
    ), None)


def _checkpoint_times(program_range, frame_duration, motion_risk_time_s=None):
    start, end = _range(program_range) or (None, None)
    if start is None:
        raise ValueError("speaker pixel budget subshot range is invalid")
    start_frame = _frame_index(start, frame_duration)
    end_frame = _frame_index(end, frame_duration)
    if start_frame is None or end_frame is None or end_frame <= start_frame:
        raise ValueError("speaker pixel budget subshot range must align to timeline frames")
    times = [
        ("entry", _frame_time(start_frame, frame_duration)),
        ("middle", _frame_time(start_frame + (end_frame - start_frame) // 2, frame_duration)),
        ("exit", _frame_time(end_frame - 1, frame_duration)),
    ]
    if motion_risk_time_s is not None:
        motion_frame = _frame_index(motion_risk_time_s, frame_duration)
        if motion_frame is None:
            raise ValueError("speaker pixel budget motion-risk time must align to timeline frames")
        if not start_frame <= motion_frame < end_frame:
            raise ValueError("speaker pixel budget motion-risk time must remain inside its subshot")
        times.append(("motion_risk", _frame_time(motion_frame, frame_duration)))
    return times


def _cover_crop_box(source_size, roi, output_size):
    source_width, source_height = source_size
    output_width, output_height = output_size
    roi_left = float(roi["x"]) * source_width
    roi_top = float(roi["y"]) * source_height
    roi_right = (float(roi["x"]) + float(roi["width"])) * source_width
    roi_bottom = (float(roi["y"]) + float(roi["height"])) * source_height
    roi_left = max(0.0, min(roi_left, float(source_width)))
    roi_top = max(0.0, min(roi_top, float(source_height)))
    roi_right = max(0.0, min(roi_right, float(source_width)))
    roi_bottom = max(0.0, min(roi_bottom, float(source_height)))
    if roi_right <= roi_left:
        roi_left = min(roi_left, float(source_width) - 1.0)
        roi_right = roi_left + 1.0
    if roi_bottom <= roi_top:
        roi_top = min(roi_top, float(source_height) - 1.0)
        roi_bottom = roi_top + 1.0
    roi_width = roi_right - roi_left
    roi_height = roi_bottom - roi_top
    output_aspect = output_width / output_height
    if roi_width / roi_height >= output_aspect:
        crop_width = roi_height * output_aspect
        left = roi_left + (roi_width - crop_width) / 2
        return (left, roi_top, left + crop_width, roi_bottom)
    crop_height = roi_width / output_aspect
    return (roi_left, roi_top, roi_right, roi_top + crop_height)


def _cover_crop_facts(source_size, roi, output_size):
    output_width, output_height = output_size
    crop_box = _cover_crop_box(source_size, roi, output_size)
    crop_width = crop_box[2] - crop_box[0]
    crop_height = crop_box[3] - crop_box[1]
    scale = output_width / crop_width
    return {
        "input_crop_px": {
            "width": round(crop_width, 6),
            "height": round(crop_height, 6),
        },
        "output_content_px": {"width": output_width, "height": output_height},
        "scale_factor": round(scale, 6),
    }


def build_pixel_budget(plan, analysis, agent_input, preview, shot_id, subshot_id,
                       *, motion_risk_time_s=None):
    """Return final-size crop and scaling facts without making a display decision."""
    analysis_shot = _find_shot(analysis, shot_id)
    agent_shot = _find_shot(agent_input, shot_id)
    preview_shot = _find_shot(preview, shot_id)
    analysis_subshot = _find_subshot(analysis_shot, subshot_id)
    agent_subshot = _find_subshot(agent_shot, subshot_id)
    if not all(isinstance(value, dict) for value in (
            analysis_shot, agent_shot, preview_shot, analysis_subshot, agent_subshot)):
        raise ValueError("speaker pixel budget shot or subshot is missing")
    if agent_subshot.get("speaker_status") != "confirmed":
        raise ValueError("speaker pixel budget requires a confirmed speaker")
    keyframes = agent_subshot.get("keyframes")
    if not isinstance(keyframes, list) or not keyframes:
        raise ValueError("speaker pixel budget requires ROI keyframes")
    source_probe = analysis.get("review_video_probe")
    output_probe = preview_shot.get("preview", {}).get("probe")
    source_size = (
        source_probe.get("width"), source_probe.get("height")
    ) if isinstance(source_probe, dict) else (None, None)
    frame_size = (
        output_probe.get("width"), output_probe.get("height")
    ) if isinstance(output_probe, dict) else (None, None)
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0
           for value in (*source_size, *frame_size)):
        raise ValueError("speaker pixel budget requires positive source and preview dimensions")
    style = plan.get("speaker_inset_style")
    anchor = agent_subshot.get("anchor")
    if style_errors(style) or anchor not in ALLOWED_ANCHORS:
        raise ValueError("speaker pixel budget style or anchor is invalid")
    fps = analysis.get("timeline_fps")
    num, den = _fps({"fps": fps})
    frame_duration = den / num
    inset_size = _inset_size(frame_size, style, anchor)
    checkpoints = []
    for role, time_s in _checkpoint_times(
            analysis_subshot.get("program_range"), frame_duration,
            motion_risk_time_s):
        roi = interpolate_roi(
            keyframes, time_s, analysis_subshot["program_range"],
        )
        facts = _cover_crop_facts(source_size, roi, inset_size)
        checkpoints.append({
            "role": role,
            "program_time_s": time_s,
            **facts,
        })
    maximum = max(item["scale_factor"] for item in checkpoints)
    return {
        "analysis_sha256": plan.get("speaker_inset", {}).get("analysis", {}).get("sha256"),
        "agent_input_sha256": plan.get("speaker_inset", {}).get("agent_input", {}).get("sha256"),
        "preview_sha256": plan.get("speaker_inset", {}).get("preview", {}).get("sha256"),
        "selection_sha256": plan.get("selection", {}).get("sha256"),
        "style_sha256": _canonical_sha256(style),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
        "source_frame_px": {"width": source_size[0], "height": source_size[1]},
        "output_inset_px": {"width": inset_size[0], "height": inset_size[1]},
        "checkpoints": checkpoints,
        "max_scale_factor": maximum,
        "pixel_risk": _pixel_risk(maximum),
    }


def _apply_broll_treatment(base, preset):
    base = base.convert("RGB")
    if preset == "corner-pip":
        return base.copy()
    if preset == "full-bleed-wash":
        return Image.blend(base, Image.new("RGB", base.size, "white"), 0.30)
    if preset != "focused-panel":
        raise ValueError("speaker inset layout preset is invalid")
    result = base.filter(ImageFilter.GaussianBlur(
        radius=0.025 * min(base.width, base.height),
    ))
    x = round(base.width * 0.04)
    y = round(base.height * 0.08)
    width = round(base.width * 0.92)
    height = round(base.height * 0.40)
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    panel = ImageOps.fit(base, (width, height), method=resampling)
    result.paste(panel, (x, y))
    ImageDraw.Draw(result).rectangle(
        (x, y, x + width - 1, y + height - 1),
        outline=ImageColor.getrgb("#9E9E9E"), width=3,
    )
    return result


def _paste_speaker(base, speaker, roi, style, anchor):
    """Crop, mask, border, and paste one speaker ROI onto a treated frame."""
    if anchor not in ALLOWED_ANCHORS:
        raise ValueError("speaker inset preset/anchor combination is invalid")
    errors = style_errors(style)
    if errors or not style_enabled(style):
        raise ValueError("invalid enabled speaker_inset_style: " + "; ".join(errors))
    roi_validation = _roi_errors(roi)
    if roi_validation:
        raise ValueError("invalid speaker ROI: " + "; ".join(roi_validation))
    base = base.convert("RGB")
    speaker = speaker.convert("RGB")
    inset_width, inset_height = _inset_size(base.size, style, anchor)
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    crop_box = _cover_crop_box(speaker.size, roi, (inset_width, inset_height))
    crop = speaker.resize(
        (inset_width, inset_height), resample=resampling, box=crop_box,
    )
    mask = Image.new("L", (inset_width, inset_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    bounds = (0, 0, inset_width - 1, inset_height - 1)
    radius = round(
        min(inset_width, inset_height) * float(style["corner_radius_ratio"])
    )
    mask_draw.rounded_rectangle(bounds, radius=radius, fill=255)
    layer = crop.convert("RGBA")
    layer.putalpha(mask)
    border_width = int(style["border"]["width_px"])
    if border_width:
        color = ImageColor.getrgb(style["border"]["color"]) + (255,)
        draw = ImageDraw.Draw(layer)
        inset = max(0, border_width // 2)
        outline = (inset, inset, inset_width - 1 - inset, inset_height - 1 - inset)
        draw.rounded_rectangle(
            outline, radius=max(0, radius - inset), outline=color, width=border_width,
        )
    position = _anchor_position(base.size, layer.size, style, anchor)
    result = base.copy()
    result.paste(layer, position, layer)
    return result


def composite_frame(base, speaker, roi, style, preset, anchor):
    """Apply one preset, then optionally composite one cleared speaker ROI."""
    errors = style_errors(style)
    if errors or not style_enabled(style):
        raise ValueError("invalid enabled speaker_inset_style: " + "; ".join(errors))
    result = _apply_broll_treatment(base, preset)
    if speaker is None:
        if roi is not None or anchor is not None:
            raise ValueError("pure B-roll must not provide speaker ROI or anchor")
        return result
    anchor_errors = _preset_anchor_errors(preset, anchor, "speaker inset")
    if anchor_errors:
        raise ValueError("; ".join(anchor_errors))
    return _paste_speaker(result, speaker, roi, style, anchor)


def _candidate_source(candidate, root):
    import broll_plan

    path = broll_plan._candidate_path(root, candidate.get("cache_path", ""))
    if path is None or not path.is_file():
        raise ValueError("selected candidate path is missing or escapes project root")
    digest = _sha256_file(path)
    if candidate.get("sha256") != digest:
        raise ValueError("selected candidate SHA-256 is stale")
    return path


def _validated_lut(plan, root, lut):
    import normalize_broll

    active = "color-grade" in plan.get("dependencies", [])
    if active and lut is None:
        raise ValueError("selected LUT is required for contextual preview")
    if not active:
        if lut is not None:
            raise ValueError("selected LUT must be omitted when color grade is inactive")
        return None
    path, hashes = normalize_broll._grade(lut, root)
    expected = plan.get("input_hashes", {}).get("selected_lut_sha256")
    if hashes.get("selected_lut_sha256") != expected:
        raise ValueError("selected LUT SHA-256 is stale")
    return path


def _check_preview_probe(path, timeline, duration):
    probe = _probe_video(path)
    width, height = timeline["width"], timeline["height"]
    num, den = _fps(timeline)
    if probe["width"] != width or probe["height"] != height:
        raise ValueError("context preview dimensions do not match timeline")
    if probe["fps"] != {"num": num, "den": den}:
        raise ValueError("context preview fps does not match timeline")
    if abs(probe["duration_s"] - duration) > den / num + RANGE_EPSILON:
        raise ValueError("context preview duration does not match shot")
    subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-map", "0:v:0", "-f", "null", "-",
    ], check=True, capture_output=True)
    return probe


def _render_broll_base(plan, shot, timeline, root, destination, lut_path):
    import broll_plan

    candidates = shot.get("candidates", [])
    details = broll_plan.selection_details(shot, candidates, timeline)
    if details.get("format") != "canonical":
        raise ValueError("speaker inset preview requires canonical video segments")
    candidate_map = {candidate.get("id"): candidate for candidate in candidates}
    width, height = timeline["width"], timeline["height"]
    num, den = _fps(timeline)
    shot_range = _range(shot.get("program_range"))
    duration = shot_range[1] - shot_range[0]
    inputs = []
    filters = []
    labels = []
    for index, segment in enumerate(details["segments"]):
        candidate = candidate_map[segment["candidate_id"]]
        source = _candidate_source(candidate, root)
        source_range = _range(segment["source_range"])
        program_range = _range(segment["program_range"])
        segment_frame_count = round(
            (program_range[1] - program_range[0]) * num / den
        )
        inputs.extend([
            "-ss", f"{source_range[0]:.9f}",
            "-t", f"{source_range[1] - source_range[0]:.9f}",
            "-i", str(source),
        ])
        chain = [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}", "setsar=1",
            f"setpts=(PTS-STARTPTS)/{float(segment['playback_rate']):g}",
            f"fps={num}/{den}",
            "tpad=stop_mode=clone:stop=-1",
            f"trim=end_frame={segment_frame_count}",
            "setpts=PTS-STARTPTS",
        ]
        if lut_path is not None:
            chain.append(f"lut3d={lut_path.name}")
        filters.append(f"[{index}:v]{','.join(chain)}[v{index}]")
        labels.append(f"[v{index}]")
    if len(labels) == 1:
        output_label = labels[0]
    else:
        filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[outv]")
        output_label = "[outv]"
    target = Path(destination)
    part = target.with_suffix(".part.mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    try:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-filter_complex", ";".join(filters), "-map", output_label,
            "-t", f"{duration:.9f}", "-r", f"{num}/{den}",
            "-an", "-sn", "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(part),
        ], cwd=lut_path.parent if lut_path else None, check=True, capture_output=True)
        _check_preview_probe(part, timeline, duration)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)
    return target


def _read_exact(stream, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _agent_subshots(agent_input):
    return {
        (shot["shot_id"], subshot["id"]): subshot
        for shot in agent_input.get("shots", []) if isinstance(shot, dict)
        for subshot in shot.get("subshots", []) if isinstance(subshot, dict)
    }


def _analysis_subshot_at(analysis_shot, program_time_s):
    for subshot in analysis_shot.get("subshots", []):
        value = _range(subshot.get("program_range")) if isinstance(subshot, dict) else None
        if value and value[0] - RANGE_EPSILON <= program_time_s < value[1] - RANGE_EPSILON:
            return subshot
    return None


def _close_process(process):
    if process is None:
        return
    if process.poll() is None:
        process.kill()
    process.wait()
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def _composite_encoder_command(width, height, num, den, part, *, encoder_args=None):
    profile_args = encoder_args or [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    return [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", f"{num}/{den}", "-i", "-",
        "-vf", "setsar=1",
        "-an", "-sn", "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
        *profile_args, str(part),
    ]


def _render_composite_video(base_video, review_video, shot, analysis_shot, agent_input,
                            timeline, style, destination, *, preset,
                            anchor_override=None, display_choices=None,
                            encoder_args=None):
    width, height = timeline["width"], timeline["height"]
    num, den = _fps(timeline)
    frame_duration = den / num
    shot_range = _range(shot.get("program_range"))
    duration = shot_range[1] - shot_range[0]
    frame_count = round(duration / frame_duration)
    frame_bytes = width * height * 3
    target = Path(destination)
    part = target.with_suffix(".part.mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    base_process = speaker_process = encoder = None
    try:
        base_process = subprocess.Popen([
            "ffmpeg", "-v", "error", "-i", str(base_video),
            "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        speaker_filter = (
            f"trim=start={shot_range[0]:.9f}:end={shot_range[1]:.9f},"
            f"setpts=PTS-STARTPTS,fps={num}/{den},scale={width}:{height}"
        )
        speaker_process = subprocess.Popen([
            "ffmpeg", "-v", "error", "-i", str(review_video),
            "-vf", speaker_filter, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        encoder = subprocess.Popen(
            _composite_encoder_command(
                width, height, num, den, part, encoder_args=encoder_args,
            ),
            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        agent_choices = _agent_subshots(agent_input)
        effective_choices = display_choices or agent_choices
        for index in range(frame_count):
            base_bytes = _read_exact(base_process.stdout, frame_bytes)
            speaker_bytes = _read_exact(speaker_process.stdout, frame_bytes)
            if len(base_bytes) != frame_bytes or len(speaker_bytes) != frame_bytes:
                raise ValueError("context preview decoder ended before the shot duration")
            base_frame = Image.frombytes("RGB", (width, height), base_bytes)
            speaker_frame = Image.frombytes("RGB", (width, height), speaker_bytes)
            program_time = _frame_time(
                round(shot_range[0] / frame_duration) + index, frame_duration,
            )
            subshot = _analysis_subshot_at(analysis_shot, program_time)
            if subshot is None:
                raise ValueError("context preview frame is outside speaker subshots")
            choice = agent_choices[(shot["id"], subshot["id"])]
            effective = effective_choices[(shot["id"], subshot["id"])]
            if effective.get("display_mode") == "enabled":
                roi = interpolate_roi(
                    choice["keyframes"], program_time, subshot["program_range"],
                )
                base_frame = composite_frame(
                    base_frame, speaker_frame, roi, style, preset,
                    anchor_override or effective["anchor"],
                )
            else:
                base_frame = composite_frame(
                    base_frame, None, None, style, preset, None,
                )
            encoder.stdin.write(base_frame.tobytes())
        encoder.stdin.close()
        encoder.stdin = None
        encoder_error = encoder.stderr.read().decode("utf-8", errors="replace")
        encoder_code = encoder.wait()
        base_error = base_process.stderr.read().decode("utf-8", errors="replace")
        speaker_error = speaker_process.stderr.read().decode("utf-8", errors="replace")
        base_code, speaker_code = base_process.wait(), speaker_process.wait()
        if encoder_code or base_code or speaker_code:
            raise RuntimeError(
                "context preview ffmpeg failed: "
                + " | ".join(value for value in (base_error, speaker_error, encoder_error) if value)
            )
        probe = _check_preview_probe(part, timeline, duration)
        digest = _sha256_file(part)
        os.replace(part, target)
        return {"path": target, "sha256": digest, "probe": probe}
    finally:
        if encoder is not None and encoder.stdin is not None:
            encoder.stdin.close()
        _close_process(base_process)
        _close_process(speaker_process)
        _close_process(encoder)
        part.unlink(missing_ok=True)


def validate_review_video(plan, timeline, review_video, project_root):
    """Return the exact hash-bound review video and timeline media geometry."""
    import normalize_broll

    root = Path(project_root).resolve()
    video = _inside(root, review_video, "review video")
    if not video.is_file():
        raise ValueError("review video is missing")
    if _sha256_file(video) != plan.get("input_hashes", {}).get("review_video_sha256"):
        raise ValueError("review video SHA-256 is stale")
    media_timeline = normalize_broll._timeline_with_media_geometry(timeline, root)
    width, height, num, den = normalize_broll._timeline_spec(media_timeline)
    media_timeline = copy.deepcopy(media_timeline)
    media_timeline.update({"width": width, "height": height})
    probe = _probe_video(video)
    duration = _number(media_timeline.get("program_duration_s"))
    if (probe.get("width") != width or probe.get("height") != height
            or probe.get("fps") != {"num": num, "den": den}
            or duration is None
            or abs(probe.get("duration_s", -1) - duration) > den / num + RANGE_EPSILON):
        raise ValueError("review video geometry, fps, or duration does not match timeline")
    subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(video),
        "-map", "0:v:0", "-f", "null", "-",
    ], check=True, capture_output=True)
    return video, media_timeline


def render_delivery_composite(*, plan, shot, analysis, agent_input, preview, clearance,
                              timeline, style, base_video, review_video, destination,
                              project_root, delivery_encoder_args=None):
    """Render one clearance-effective speaker composite for normalized delivery."""
    import broll_plan
    import normalize_broll

    if delivery_encoder_args is None:
        delivery_encoder_args = normalize_broll.delivery_encoder_args()

    root = Path(project_root).resolve()
    if not isinstance(plan, dict) or not isinstance(shot, dict):
        raise ValueError("speaker inset delivery plan and shot must be objects")
    if shot not in plan.get("shots", []):
        raise ValueError("speaker inset delivery shot is not in the plan")
    if style != plan.get("speaker_inset_style"):
        raise ValueError("speaker inset delivery style does not match plan")
    errors = style_errors(style)
    errors.extend(analysis_errors(
        analysis, plan, timeline, {}, project_root=root, verify_files=True,
    ))
    errors = [error for error in errors if "transcript_sha256" not in error]
    errors.extend(agent_input_errors(agent_input, analysis, plan, timeline))
    errors.extend(preview_errors(
        preview, plan, analysis, agent_input, timeline,
        project_root=root, verify_files=True,
    ))
    errors.extend(clearance_errors(clearance, preview, agent_input, analysis, plan))
    errors.extend(broll_plan._review_errors(plan, plan.get("shots", [])))
    if errors:
        raise ValueError("invalid speaker inset delivery artifacts: " + "; ".join(errors))

    video, media_timeline = validate_review_video(
        plan, timeline, review_video, root,
    )
    width, height, num, den = normalize_broll._timeline_spec(media_timeline)

    base = _inside(root, base_video, "normalized B-roll base")
    if not base.is_file():
        raise ValueError("normalized B-roll base is missing")
    shot_id = shot.get("id")
    analysis_shot = next((
        item for item in analysis.get("shots", [])
        if isinstance(item, dict) and item.get("shot_id") == shot_id
    ), None)
    agent_shot = next((
        item for item in agent_input.get("shots", [])
        if isinstance(item, dict) and item.get("shot_id") == shot_id
    ), None)
    clearance_shot = next((
        item for item in clearance.get("shots", [])
        if isinstance(item, dict) and item.get("shot_id") == shot_id
    ), None)
    if not all(isinstance(item, dict) for item in (
            analysis_shot, agent_shot, clearance_shot)):
        raise ValueError("speaker inset delivery shot artifacts are missing")
    recommendation = agent_shot.get("layout_recommendation", {})
    choices = {
        (shot_id, item["id"]): item
        for item in clearance_shot.get("subshots", []) if isinstance(item, dict)
    }
    rendered = _render_composite_video(
        base, video, shot, analysis_shot, agent_input,
        media_timeline, style, destination,
        preset=recommendation.get("preset"), display_choices=choices,
        encoder_args=delivery_encoder_args,
    )
    output = Path(rendered["path"])
    probe = normalize_broll._probe(output)
    normalize_broll._check_probe(
        probe, width, height, num, den, _range(shot["program_range"])[1]
        - _range(shot["program_range"])[0],
    )
    return {"path": output, "sha256": _sha256_file(output), "probe": probe}


def render_context_previews(plan, analysis, agent_input, timeline, review_video,
                            project_root, *, lut=None):
    """Render exact B-roll plus approved Agent ROI/anchor contextual previews."""
    analysis_validation = analysis_errors(analysis, plan, timeline, {}, verify_files=False)
    analysis_validation = [
        error for error in analysis_validation if "transcript_sha256" not in error
    ]
    if analysis_validation:
        raise ValueError("invalid speaker analysis: " + "; ".join(analysis_validation))
    agent_validation = agent_input_errors(agent_input, analysis, plan, timeline)
    if agent_validation:
        raise ValueError("invalid speaker Agent input: " + "; ".join(agent_validation))
    root = Path(project_root).resolve()
    video = _inside(root, review_video, "review video")
    if _sha256_file(video) != plan.get("input_hashes", {}).get("review_video_sha256"):
        raise ValueError("review video SHA-256 is stale")
    import normalize_broll

    media_timeline = normalize_broll._timeline_with_media_geometry(timeline, root)
    width, height, _, _ = normalize_broll._timeline_spec(media_timeline)
    media_timeline = copy.deepcopy(media_timeline)
    media_timeline.update({"width": width, "height": height})
    lut_path = _validated_lut(plan, root, lut)
    preview_dir = (
        root / "work/cache/b-roll/speaker-inset/previews" / analysis["analysis_id"]
    )
    preview_dir.mkdir(parents=True, exist_ok=True)
    analysis_shots = {shot["shot_id"]: shot for shot in analysis["shots"]}
    agent_shots = {
        shot["shot_id"]: shot for shot in agent_input["shots"]
    }
    shot_records = []
    for shot in plan.get("shots", []):
        if not isinstance(shot, dict) or shot.get("status") != "composite_pending":
            continue
        base = _render_broll_base(
            plan, shot, media_timeline, root,
            preview_dir / f"base-{shot['id']}.mp4", lut_path,
        )
        recommendation = agent_shots[shot["id"]]["layout_recommendation"]
        preset, anchor = recommendation["preset"], recommendation["anchor"]
        context = _render_composite_video(
            base, video, shot, analysis_shots[shot["id"]], agent_input,
            media_timeline, plan["speaker_inset_style"],
            preview_dir / f"context-{shot['id']}.mp4",
            preset=preset, anchor_override=anchor,
        )
        anchor_previews = {}
        for preview_anchor in PRESET_ANCHORS[preset]:
            alternate = _render_composite_video(
                base, video, shot, analysis_shots[shot["id"]], agent_input,
                media_timeline, plan["speaker_inset_style"],
                preview_dir / f"context-{shot['id']}-{preview_anchor}.mp4",
                preset=preset, anchor_override=preview_anchor,
            )
            anchor_previews[preview_anchor] = {
                "path": alternate["path"].relative_to(root / "work").as_posix(),
                "sha256": alternate["sha256"],
                "probe": alternate["probe"],
            }
        record = {
            "shot_id": shot["id"],
            "program_range": copy.deepcopy(shot["program_range"]),
            "base_broll": {
                "path": base.relative_to(root / "work").as_posix(),
                "sha256": _sha256_file(base),
            },
            "preview": {
                "path": context["path"].relative_to(root / "work").as_posix(),
                "sha256": context["sha256"],
                "probe": context["probe"],
            },
            "anchor_previews": anchor_previews,
        }
        alternate = recommendation.get("alternate")
        if isinstance(alternate, dict):
            alternate_render = _render_composite_video(
                base, video, shot, analysis_shots[shot["id"]], agent_input,
                media_timeline, plan["speaker_inset_style"],
                preview_dir / f"context-{shot['id']}-alternate.mp4",
                preset=alternate["preset"], anchor_override=alternate["anchor"],
            )
            record["alternate_preview"] = {
                "preset": alternate["preset"],
                "anchor": alternate["anchor"],
                "path": alternate_render["path"].relative_to(root / "work").as_posix(),
                "sha256": alternate_render["sha256"],
                "probe": alternate_render["probe"],
            }
        shot_records.append(record)
    record = {
        "schema_version": 1,
        "analysis_sha256": plan["speaker_inset"]["analysis"]["sha256"],
        "agent_input_sha256": plan["speaker_inset"]["agent_input"]["sha256"],
        "selection_sha256": plan["selection"]["sha256"],
        "style_sha256": _canonical_sha256(plan["speaker_inset_style"]),
        "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
        "shots": shot_records,
    }
    output = root / "work/b-roll/speaker-inset-preview.json"
    _atomic_json(output, record)
    result = copy.deepcopy(plan)
    result["speaker_inset"]["preview"] = {
        "path": "b-roll/speaker-inset-preview.json",
        "sha256": _sha256_file(output),
    }
    return result


def _preview_binding_errors(binding, label, *, root=None, verify_files=False):
    if not isinstance(binding, dict):
        return [f"{label} binding must be an object"]
    errors = []
    path_value = binding.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        errors.append(f"{label} path is required")
    if not _is_sha256(binding.get("sha256")):
        errors.append(f"{label} SHA-256 is invalid")
    if verify_files and root is not None and not errors:
        try:
            path = _inside(root / "work", root / "work" / path_value, label)
        except ValueError:
            errors.append(f"{label} path escapes work")
        else:
            if not path.is_file():
                errors.append(f"{label} file is missing")
            elif _sha256_file(path) != binding["sha256"]:
                errors.append(f"{label} SHA-256 is stale")
    return errors


def preview_errors(preview, plan, analysis, agent_input, timeline, *,
                   project_root=None, verify_files=False):
    """Validate the exact contextual preview record and its frozen media bindings."""
    if not isinstance(preview, dict):
        return ["speaker inset preview must be an object"]
    errors = []
    if preview.get("schema_version") != 1:
        errors.append("speaker inset preview schema_version must be 1")
    if "size_review" in preview:
        errors.append("speaker inset preview size_review is unsupported")
    expected = {
        "analysis_sha256": plan.get("speaker_inset", {}).get("analysis", {}).get("sha256"),
        "agent_input_sha256": plan.get("speaker_inset", {}).get("agent_input", {}).get("sha256"),
        "selection_sha256": plan.get("selection", {}).get("sha256"),
        "style_sha256": _canonical_sha256(plan.get("speaker_inset_style")),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
    }
    for field, value in expected.items():
        if preview.get(field) != value:
            errors.append(f"speaker inset preview {field} does not match")
    if preview.get("analysis_sha256") != analysis.get("analysis_sha256", expected["analysis_sha256"]):
        errors.append("speaker inset preview analysis binding is stale")
    if preview.get("agent_input_sha256") != _json_document_sha256(agent_input):
        errors.append("speaker inset preview Agent input binding is stale")
    try:
        _fps(timeline)
    except ValueError as exc:
        errors.append(str(exc))
    expected_shots = {
        shot.get("id"): shot for shot in plan.get("shots", [])
        if isinstance(shot, dict) and shot.get("status") in ARTIFACT_SHOT_STATUSES
    }
    shots = preview.get("shots")
    if not isinstance(shots, list):
        return errors + ["speaker inset preview shots must be a list"]
    if [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] != list(expected_shots):
        errors.append("speaker inset preview shots do not match composite_pending shots")
    root = Path(project_root).resolve() if project_root is not None else None
    agent_shots = {
        shot.get("shot_id"): shot for shot in agent_input.get("shots", [])
        if isinstance(shot, dict)
    }
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("shot_id") not in expected_shots:
            continue
        shot_id = shot["shot_id"]
        if _range(shot.get("program_range")) != _range(expected_shots[shot_id].get("program_range")):
            errors.append(f"{shot_id} preview program range does not match")
        errors.extend(_preview_binding_errors(
            shot.get("base_broll"), f"{shot_id} base B-roll",
            root=root, verify_files=verify_files,
        ))
        errors.extend(_preview_binding_errors(
            shot.get("preview"), f"{shot_id} contextual preview",
            root=root, verify_files=verify_files,
        ))
        recommendation = agent_shots.get(shot_id, {}).get("layout_recommendation", {})
        preset = recommendation.get("preset")
        allowed = list(PRESET_ANCHORS.get(preset, ()))
        anchor_previews = shot.get("anchor_previews")
        if not isinstance(anchor_previews, dict) or list(anchor_previews) != allowed:
            errors.append(f"{shot_id} anchor previews must match recommended preset anchors")
            continue
        for anchor, binding in anchor_previews.items():
            errors.extend(_preview_binding_errors(
                binding, f"{shot_id} {anchor} preview",
                root=root, verify_files=verify_files,
            ))
        alternate = recommendation.get("alternate")
        alternate_preview = shot.get("alternate_preview")
        if alternate is None:
            if alternate_preview is not None:
                errors.append(f"{shot_id} alternate preview requires an alternate recommendation")
        elif not isinstance(alternate_preview, dict):
            errors.append(f"{shot_id} alternate preview is required")
        else:
            if (alternate_preview.get("preset") != alternate.get("preset")
                    or alternate_preview.get("anchor") != alternate.get("anchor")):
                errors.append(f"{shot_id} alternate preview does not match recommendation")
            errors.extend(_preview_binding_errors(
                alternate_preview, f"{shot_id} alternate preview",
                root=root, verify_files=verify_files,
            ))
    return errors


def _continuity_expectation(analysis_subshots, clearance_subshots):
    runs = []
    for analysis_item, clearance_item in zip(analysis_subshots, clearance_subshots):
        program = _range(analysis_item.get("program_range")) if isinstance(analysis_item, dict) else None
        mode = clearance_item.get("display_mode") if isinstance(clearance_item, dict) else None
        if not program or mode not in {"enabled", "pure_broll"}:
            continue
        duration = program[1] - program[0]
        if runs and runs[-1]["mode"] == mode:
            runs[-1]["duration_s"] += duration
        else:
            runs.append({"mode": mode, "duration_s": duration})
    modes = {run["mode"] for run in runs}
    if modes == {"enabled"}:
        return "none", "continuous"
    if modes == {"pure_broll"}:
        return "none", "all_pure_broll"
    short_flash = any(
        run["mode"] == "enabled"
        and run["duration_s"] < SHORT_FLASH_SECONDS - RANGE_EPSILON
        and index + 1 < len(runs)
        and runs[index + 1]["mode"] == "pure_broll"
        and runs[index + 1]["duration_s"] > run["duration_s"] + RANGE_EPSILON
        for index, run in enumerate(runs)
    )
    return ("short_flash" if short_flash else "mode_change"), "intentional_transition"


def _legibility_evidence_errors(item, analysis_subshot, plan, analysis,
                                 agent_input, preview, shot_id):
    label = item.get("id")
    errors = []
    rationale = item.get("legibility_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append(f"{label} legibility rationale is required")
    checks = item.get("legibility_checks")
    if not isinstance(checks, list):
        return errors + [f"{label} legibility_checks must be a list"]
    roles = [check.get("role") for check in checks if isinstance(check, dict)]
    if roles != ["entry", "middle", "exit", "motion_risk"]:
        errors.append(
            f"{label} legibility_checks must contain entry, middle, exit, and motion_risk in order"
        )
        return errors
    try:
        num, den = _fps({"fps": analysis.get("timeline_fps")})
        frame_duration = den / num
        expected_times = dict(_checkpoint_times(
            analysis_subshot.get("program_range"), frame_duration,
        ))
    except ValueError as exc:
        return errors + [f"{label} {exc}"]
    preview_sha256 = plan.get("speaker_inset", {}).get("preview", {}).get("sha256")
    subshot_range = _range(analysis_subshot.get("program_range"))
    motion_risk_time_s = None
    for check in checks:
        role = check["role"]
        if check.get("preview_sha256") != preview_sha256:
            errors.append(f"{label} {role} must bind the exact preview SHA-256")
        if role != "motion_risk":
            time_s = check.get("program_time_s")
            if _frame_index(time_s, frame_duration) is None:
                errors.append(f"{label} {role} program_time_s must align to timeline frames")
            elif abs(float(time_s) - expected_times[role]) > RANGE_EPSILON:
                errors.append(f"{label} {role} program_time_s must use the canonical checkpoint frame")
            if (not isinstance(check.get("observation"), str)
                    or not check["observation"].strip()):
                errors.append(f"{label} {role} observation is required")
            continue
        status = check.get("status")
        reason = check.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{label} motion-risk reason is required")
        if status == "not_applicable":
            if "program_time_s" in check or "observation" in check:
                errors.append(
                    f"{label} not_applicable motion-risk must not include a time or observation"
                )
        elif status == "checked":
            motion_risk_time_s = check.get("program_time_s")
            motion_frame = _frame_index(motion_risk_time_s, frame_duration)
            if motion_frame is None:
                errors.append(
                    f"{label} motion-risk program_time_s must align to timeline frames"
                )
            elif not subshot_range[0] <= float(motion_risk_time_s) < subshot_range[1]:
                errors.append(
                    f"{label} motion-risk program_time_s must remain inside its subshot"
                )
            if (not isinstance(check.get("observation"), str)
                    or not check["observation"].strip()):
                errors.append(f"{label} motion-risk observation is required")
        else:
            errors.append(f"{label} motion-risk status must be checked or not_applicable")
    try:
        expected_budget = build_pixel_budget(
            plan, analysis, agent_input, preview, shot_id, label,
            motion_risk_time_s=motion_risk_time_s,
        )
    except ValueError as exc:
        errors.append(f"{label} pixel budget cannot be computed: {exc}")
    else:
        if item.get("pixel_budget") != expected_budget:
            errors.append(f"{label} pixel_budget does not match final-size crop facts")
    return errors


def clearance_errors(clearance, preview, agent_input, analysis, plan):
    """Validate Agent clearance against exact composited anchor previews."""
    if not isinstance(clearance, dict):
        return ["speaker inset clearance must be an object"]
    errors = []
    if clearance.get("schema_version") != 1:
        errors.append("speaker inset clearance schema_version must be 1")
    if clearance.get("mode") != "agent":
        errors.append("speaker inset clearance mode must be agent")
    for field in ("actor", "rationale"):
        if not isinstance(clearance.get(field), str) or not clearance[field].strip():
            errors.append(f"speaker inset clearance {field} is required")
    if not _valid_timestamp(clearance.get("timestamp")):
        errors.append("speaker inset clearance timestamp is invalid")
    expected = {
        "analysis_sha256": plan.get("speaker_inset", {}).get("analysis", {}).get("sha256"),
        "agent_input_sha256": plan.get("speaker_inset", {}).get("agent_input", {}).get("sha256"),
        "preview_sha256": plan.get("speaker_inset", {}).get("preview", {}).get("sha256"),
        "selection_sha256": plan.get("selection", {}).get("sha256"),
        "style_sha256": _canonical_sha256(plan.get("speaker_inset_style")),
    }
    for field, value in expected.items():
        if clearance.get(field) != value:
            errors.append(f"speaker inset clearance {field} does not match")
    if clearance.get("analysis_sha256") != preview.get("analysis_sha256"):
        errors.append("speaker inset clearance analysis binding does not match preview")
    if clearance.get("agent_input_sha256") != preview.get("agent_input_sha256"):
        errors.append("speaker inset clearance Agent input binding does not match preview")

    if "size_assessment" in clearance:
        errors.append("speaker inset clearance size_assessment is unsupported")

    analysis_shots = {
        shot.get("shot_id"): shot for shot in analysis.get("shots", [])
        if isinstance(shot, dict)
    }
    agent_shots = {
        shot.get("shot_id"): shot for shot in agent_input.get("shots", [])
        if isinstance(shot, dict)
    }
    preview_shots = {
        shot.get("shot_id"): shot for shot in preview.get("shots", [])
        if isinstance(shot, dict)
    }
    shots = clearance.get("shots")
    if not isinstance(shots, list):
        return errors + ["speaker inset clearance shots must be a list"]
    if [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] != list(analysis_shots):
        errors.append("speaker inset clearance shots do not match analysis")
    for shot in shots:
        shot_id = shot.get("shot_id") if isinstance(shot, dict) else None
        if shot_id not in analysis_shots or shot_id not in agent_shots:
            continue
        analysis_subshots = {
            item.get("id"): item for item in analysis_shots[shot_id].get("subshots", [])
            if isinstance(item, dict)
        }
        agent_subshots = {
            item.get("id"): item for item in agent_shots[shot_id].get("subshots", [])
            if isinstance(item, dict)
        }
        items = shot.get("subshots")
        if not isinstance(items, list):
            errors.append(f"{shot_id} clearance subshots must be a list")
            continue
        if [item.get("id") for item in items if isinstance(item, dict)] != list(analysis_subshots):
            errors.append(f"{shot_id} clearance subshots do not match analysis")
        continuity = shot.get("continuity")
        expected_risk, expected_decision = _continuity_expectation(
            analysis_shots[shot_id].get("subshots", []), items,
        )
        if not isinstance(continuity, dict):
            errors.append(f"{shot_id} continuity assessment is required")
        else:
            if continuity.get("risk") != expected_risk:
                errors.append(
                    f"{shot_id} continuity risk must be {expected_risk}"
                )
            if continuity.get("decision") != expected_decision:
                errors.append(
                    f"{shot_id} continuity decision must be {expected_decision}"
                )
            if (not isinstance(continuity.get("rationale"), str)
                    or not continuity["rationale"].strip()):
                errors.append(f"{shot_id} continuity rationale is required")
        available = preview_shots.get(shot_id, {}).get("anchor_previews", {})
        recommendation = agent_shots[shot_id].get("layout_recommendation", {})
        allowed = list(PRESET_ANCHORS.get(recommendation.get("preset"), ()))
        for item in items:
            label = item.get("id") if isinstance(item, dict) else None
            if label not in analysis_subshots or label not in agent_subshots:
                continue
            agent_choice = agent_subshots[label]
            rationale = item.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(f"{label} clearance rationale is required")
            checked = item.get("checked_anchors")
            if (not isinstance(checked, list) or len(checked) != len(set(checked))
                    or any(anchor not in allowed for anchor in checked)):
                errors.append(f"{label} checked_anchors must be unique allowed anchors")
                checked = []
            if agent_choice.get("speaker_status") != "confirmed":
                if (agent_choice.get("display_mode") != "pure_broll"
                        or item.get("display_mode") != "pure_broll"
                        or item.get("anchor") is not None
                        or item.get("clearance_status") != "pass"
                        or checked != []):
                    errors.append(f"{label} non-confirmed speaker clearance must remain pure_broll")
                if item.get("subject_legibility") != "not_applicable":
                    errors.append(
                        f"{label} non-confirmed speaker subject_legibility must be not_applicable"
                    )
                for field in ("pixel_budget", "legibility_checks", "legibility_rationale"):
                    if field in item:
                        errors.append(f"{label} non-confirmed speaker must not include {field}")
                continue
            errors.extend(_legibility_evidence_errors(
                item, analysis_subshots[label], plan, analysis,
                agent_input, preview, shot_id,
            ))
            status = item.get("clearance_status")
            if status == "pass":
                anchor = item.get("anchor")
                if (item.get("display_mode") != "enabled"
                        or agent_choice.get("display_mode") != "enabled"
                        or anchor != recommendation.get("anchor")
                        or anchor not in checked
                        or anchor not in available):
                    errors.append(f"{label} passing clearance must bind the enabled checked anchor")
                if item.get("subject_legibility") != "pass":
                    errors.append(
                        f"{label} enabled speaker must pass subject legibility; "
                        "subject_legibility must be pass"
                    )
            elif status == "no_safe_position":
                if (item.get("display_mode") != "pure_broll"
                        or item.get("anchor") is not None
                        or checked != allowed
                        or any(anchor not in available for anchor in allowed)):
                    errors.append(f"{label} no_safe_position must check all allowed anchors and use pure_broll")
                if item.get("subject_legibility") != "not_applicable":
                    errors.append(
                        f"{label} no_safe_position subject_legibility must be not_applicable"
                    )
            elif status == "subject_illegible":
                recommended = recommendation.get("anchor")
                if (item.get("display_mode") != "pure_broll"
                        or item.get("anchor") is not None
                        or item.get("subject_legibility") != "fail"
                        or recommended not in checked
                        or recommended not in available):
                    errors.append(
                        f"{label} subject_illegible must use pure_broll, fail legibility, "
                        "and bind the checked recommended preview"
                    )
            else:
                errors.append(
                    f"{label} clearance_status must be pass, no_safe_position, or subject_illegible"
                )
            if (item.get("subject_legibility") == "fail"
                    and status != "subject_illegible"):
                errors.append(
                    f"{label} subject_legibility fail requires subject_illegible"
                )
    return errors


def attach_clearance(plan, analysis, agent_input, preview, clearance, project_root, timeline):
    errors = preview_errors(
        preview, plan, analysis, agent_input, timeline, verify_files=False,
    )
    errors.extend(clearance_errors(clearance, preview, agent_input, analysis, plan))
    if errors:
        raise ValueError("invalid speaker inset clearance: " + "; ".join(errors))
    root = Path(project_root).resolve()
    target = root / "work/b-roll/speaker-inset-clearance.json"
    _atomic_json(target, clearance)
    result = copy.deepcopy(plan)
    speaker = result.setdefault("speaker_inset", {})
    speaker["clearance"] = {
        "path": "b-roll/speaker-inset-clearance.json",
        "sha256": _sha256_file(target),
        "actor": clearance["actor"],
        "timestamp": clearance["timestamp"],
    }
    return result


def normalized_composition_errors(plan, shot, *, agent_input=None):
    """Validate one normalized speaker composition against its frozen plan bindings."""
    normalized = shot.get("normalized") if isinstance(shot, dict) else None
    composition = normalized.get("composition") if isinstance(normalized, dict) else None
    base = normalized.get("broll_base") if isinstance(normalized, dict) else None
    enabled = style_enabled(plan.get("speaker_inset_style")) if isinstance(plan, dict) else False
    status = shot.get("status") if isinstance(shot, dict) else None
    if not enabled:
        if composition is not None or base is not None:
            return ["speaker inset normalized composition requires enabled style"]
        return []
    if status not in {"normalized", "verified"}:
        return []
    if not isinstance(composition, dict):
        return ["speaker inset normalized composition is missing"]
    errors = []
    required = {
        "kind", "layout_preset", "project_primary_preset", "review_id",
        "selection_sha256", "analysis_sha256", "agent_input_sha256",
        "preview_sha256", "clearance_sha256", "style_sha256",
        "review_video_sha256",
    }
    if set(composition) != required:
        errors.append("speaker inset normalized composition fields are invalid")
    speaker = plan.get("speaker_inset") if isinstance(plan.get("speaker_inset"), dict) else {}
    review = plan.get("review") if isinstance(plan.get("review"), dict) else {}
    expected = {
        "kind": "speaker-inset",
        "review_id": review.get("review_id"),
        "selection_sha256": plan.get("selection", {}).get("sha256"),
        "analysis_sha256": speaker.get("analysis", {}).get("sha256"),
        "agent_input_sha256": speaker.get("agent_input", {}).get("sha256"),
        "preview_sha256": speaker.get("preview", {}).get("sha256"),
        "clearance_sha256": speaker.get("clearance", {}).get("sha256"),
        "style_sha256": _canonical_sha256(plan.get("speaker_inset_style")),
        "review_video_sha256": plan.get("input_hashes", {}).get("review_video_sha256"),
    }
    for field, value in expected.items():
        if composition.get(field) != value:
            errors.append(f"speaker inset normalized composition {field} is stale")
    for field in ("layout_preset", "project_primary_preset"):
        if composition.get(field) not in LAYOUT_PRESETS:
            errors.append(f"speaker inset normalized composition {field} is invalid")
    if agent_input is not None:
        strategy = agent_input.get("project_layout_strategy", {})
        recommendation = next((
            item.get("layout_recommendation", {})
            for item in agent_input.get("shots", [])
            if isinstance(item, dict) and item.get("shot_id") == shot.get("id")
        ), {})
        if composition.get("layout_preset") != recommendation.get("preset"):
            errors.append("speaker inset normalized composition layout_preset is stale")
        if composition.get("project_primary_preset") != strategy.get("primary_preset"):
            errors.append("speaker inset normalized composition project_primary_preset is stale")
    valid_base_fields = (
        {"path", "sha256", "probe"},
        {"path", "sha256", "probe", "intermediate_profile"},
    )
    if not isinstance(base, dict) or set(base) not in valid_base_fields:
        errors.append("speaker inset normalized composition B-roll base is invalid")
    else:
        path = base.get("path")
        if (not isinstance(path, str)
                or not re.fullmatch(r"cache/b-roll/normalized/broll-\d{3}-base\.mp4", path)):
            errors.append("speaker inset normalized composition B-roll base path is invalid")
        if not _is_sha256(base.get("sha256")):
            errors.append("speaker inset normalized composition B-roll base SHA-256 is invalid")
        if not isinstance(base.get("probe"), dict):
            errors.append("speaker inset normalized composition B-roll base probe is invalid")
        if ("intermediate_profile" in base
                and not isinstance(base.get("intermediate_profile"), dict)):
            errors.append("speaker inset normalized composition B-roll base profile is invalid")
    return errors


def artifact_errors(plan, timeline, transcript, *, project_root=None, verify_files=False):
    """Validate durable speaker artifacts and every transitive hash binding."""
    speaker = plan.get("speaker_inset") if isinstance(plan, dict) else None
    if not isinstance(speaker, dict) or not verify_files:
        return []
    if project_root is None:
        return ["speaker inset artifact verification requires project_root"]
    root = Path(project_root).resolve()
    specs = {
        "analysis": "b-roll/speaker-inset-analysis.json",
        "agent_input": "b-roll/speaker-inset-agent-input.json",
        "preview": "b-roll/speaker-inset-preview.json",
        "clearance": "b-roll/speaker-inset-clearance.json",
    }
    errors = []
    documents = {}
    for name, expected_path in specs.items():
        binding = speaker.get(name)
        if binding is None:
            continue
        if not isinstance(binding, dict) or binding.get("path") != expected_path:
            continue
        path = root / "work" / expected_path
        if not path.is_file():
            errors.append(f"speaker_inset {name} file is missing")
            continue
        if _sha256_file(path) != binding.get("sha256"):
            errors.append(f"speaker_inset {name} SHA-256 is stale")
            continue
        try:
            documents[name] = projectlib.load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append(f"speaker_inset {name} JSON is invalid")

    analysis = documents.get("analysis")
    if analysis is not None:
        errors.extend(analysis_errors(
            analysis, plan, timeline, transcript,
            project_root=root, verify_files=True,
        ))
    agent_input = documents.get("agent_input")
    if agent_input is not None and analysis is not None:
        errors.extend(agent_input_errors(agent_input, analysis, plan, timeline))
        for shot in plan.get("shots", []):
            if isinstance(shot, dict):
                errors.extend(normalized_composition_errors(
                    plan, shot, agent_input=agent_input,
                ))
    preview = documents.get("preview")
    if preview is not None and analysis is not None and agent_input is not None:
        errors.extend(preview_errors(
            preview, plan, analysis, agent_input, timeline,
            project_root=root, verify_files=True,
        ))
    clearance = documents.get("clearance")
    if (clearance is not None and preview is not None
            and analysis is not None and agent_input is not None):
        errors.extend(clearance_errors(
            clearance, preview, agent_input, analysis, plan,
        ))
    return errors
