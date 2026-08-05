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

from PIL import Image, ImageColor, ImageDraw

import projectlib


ALLOWED_ANCHORS = {
    "top-left", "top-right", "middle-left", "middle-right",
}
ALLOWED_SHAPES = {"circle", "rounded-rectangle"}
SPEAKER_STATUSES = {"confirmed", "ambiguous", "absent", "occluded"}
RANGE_EPSILON = 1e-6
SHORT_FLASH_SECONDS = 1.5


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def style_enabled(style):
    return isinstance(style, dict) and style.get("enabled") is True


def style_errors(style):
    """Return strict project-level speaker inset style errors."""
    if not isinstance(style, dict):
        return ["speaker_inset_style must be an object"]
    if not isinstance(style.get("enabled"), bool):
        return ["speaker_inset_style enabled must be a boolean"]
    if not style["enabled"]:
        return []

    errors = []
    shape = style.get("shape")
    if shape not in ALLOWED_SHAPES:
        errors.append("speaker_inset_style shape must be circle or rounded-rectangle")
    width = _number(style.get("width_ratio"))
    if width is None or not 0 < width < 1:
        errors.append("speaker_inset_style width_ratio must be between 0 and 1")
    size_candidates = style.get("size_candidates")
    parsed_sizes = []
    if (not isinstance(size_candidates, list) or not 2 <= len(size_candidates) <= 3
            or any(_number(value) is None or not 0 < float(value) < 1
                   for value in size_candidates)):
        errors.append(
            "speaker_inset_style size_candidates must contain two or three valid width ratios"
        )
    else:
        parsed_sizes = [float(value) for value in size_candidates]
        if parsed_sizes != sorted(set(parsed_sizes)):
            errors.append(
                "speaker_inset_style size_candidates must be unique and strictly increasing"
            )
        if width is not None and not any(
                abs(width - value) <= RANGE_EPSILON for value in parsed_sizes):
            errors.append("speaker_inset_style size_candidates must include width_ratio")
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

    anchors = style.get("allowed_anchors")
    if (not isinstance(anchors, list) or not anchors
            or any(anchor not in ALLOWED_ANCHORS for anchor in anchors)
            or len(anchors) != len(set(anchors))):
        errors.append("speaker_inset_style allowed_anchors must be unique supported anchors")

    corner = style.get("corner_radius_ratio")
    if shape == "rounded-rectangle" and (
            _number(corner) is None or not 0 <= float(corner) <= 0.5):
        errors.append(
            "speaker_inset_style corner_radius_ratio must be between 0 and 0.5 "
            "for rounded-rectangle"
        )
    if width is not None and margin is not None and width + 2 * margin > 1:
        errors.append("speaker_inset_style width and margins do not fit the frame")
    if (width is not None and aspect is not None and margin is not None
            and reserved is not None and width / aspect + 2 * margin + reserved > 1):
        errors.append("speaker_inset_style height, margins, and reserved bottom do not fit the frame")
    if margin is not None and aspect is not None and reserved is not None:
        for candidate in parsed_sizes:
            if candidate + 2 * margin > 1:
                errors.append("speaker_inset_style size_candidates and margins do not fit the frame")
                break
            if candidate / aspect + 2 * margin + reserved > 1:
                errors.append(
                    "speaker_inset_style size_candidates height and reserved bottom do not fit the frame"
                )
                break
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
    if not isinstance(selection, dict) or selection.get("status") != "prepared":
        raise ValueError("prepared selection is required")
    selection_path = root / "work" / str(selection.get("path", ""))
    if (not selection_path.is_file() or not _is_sha256(selection.get("sha256"))
            or _sha256_file(selection_path) != selection["sha256"]):
        raise ValueError("prepared selection file is missing or stale")
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
        if isinstance(shot, dict) and shot.get("status") == "composite_pending"
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
    allowed_anchors = set(plan.get("speaker_inset_style", {}).get("allowed_anchors", []))
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("shot_id") not in analysis_shots:
            continue
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
            if item.get("anchor") not in allowed_anchors:
                errors.append(f"{label} anchor is not allowed by speaker_inset_style")
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
    x = margin if anchor.endswith("left") else width - margin - inset_width
    if anchor.startswith("top"):
        y = margin
    else:
        centered = (safe_bottom - inset_height) // 2
        y = max(margin, centered)
    if x < 0 or y < 0 or x + inset_width > width or y + inset_height > safe_bottom:
        raise ValueError("speaker inset anchor does not fit the frame or reserved bottom")
    return x, y


def composite_frame(base, speaker, roi, style, anchor):
    """Composite one masked speaker ROI over one exact B-roll frame."""
    errors = style_errors(style)
    if errors or not style_enabled(style):
        raise ValueError("invalid enabled speaker_inset_style: " + "; ".join(errors))
    if anchor not in style["allowed_anchors"]:
        raise ValueError("speaker inset anchor is not allowed")
    roi_validation = _roi_errors(roi)
    if roi_validation:
        raise ValueError("invalid speaker ROI: " + "; ".join(roi_validation))
    base = base.convert("RGB")
    speaker = speaker.convert("RGB")
    source_width, source_height = speaker.size
    left = max(0, min(source_width - 1, math.floor(float(roi["x"]) * source_width)))
    top = max(0, min(source_height - 1, math.floor(float(roi["y"]) * source_height)))
    right = max(left + 1, min(
        source_width, math.ceil((float(roi["x"]) + float(roi["width"])) * source_width),
    ))
    bottom = max(top + 1, min(
        source_height, math.ceil((float(roi["y"]) + float(roi["height"])) * source_height),
    ))
    inset_width = max(2, round(base.width * float(style["width_ratio"])))
    inset_height = max(2, round(inset_width / float(style["aspect_ratio"])))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    crop = speaker.crop((left, top, right, bottom)).resize(
        (inset_width, inset_height), resampling,
    )
    mask = Image.new("L", (inset_width, inset_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    bounds = (0, 0, inset_width - 1, inset_height - 1)
    if style["shape"] == "circle":
        mask_draw.ellipse(bounds, fill=255)
    else:
        radius = round(
            min(inset_width, inset_height) * float(style.get("corner_radius_ratio", 0.08))
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
        if style["shape"] == "circle":
            draw.ellipse(outline, outline=color, width=border_width)
        else:
            radius = round(
                min(inset_width, inset_height) * float(style.get("corner_radius_ratio", 0.08))
            )
            draw.rounded_rectangle(
                outline, radius=max(0, radius - inset), outline=color, width=border_width,
            )
    position = _anchor_position(base.size, layer.size, style, anchor)
    result = base.copy()
    result.paste(layer, position, layer)
    return result


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


def _render_composite_video(base_video, review_video, shot, analysis_shot, agent_input,
                            timeline, style, destination, *, anchor_override=None):
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
        encoder = subprocess.Popen([
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", f"{num}/{den}", "-i", "-",
            "-an", "-sn", "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(part),
        ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        choices = _agent_subshots(agent_input)
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
            choice = choices[(shot["id"], subshot["id"])]
            if choice.get("display_mode") == "enabled":
                roi = interpolate_roi(
                    choice["keyframes"], program_time, subshot["program_range"],
                )
                base_frame = composite_frame(
                    base_frame, speaker_frame, roi, style,
                    anchor_override or choice["anchor"],
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
    agent_subshots = _agent_subshots(agent_input)
    shot_records = []
    size_review = None
    for shot in plan.get("shots", []):
        if not isinstance(shot, dict) or shot.get("status") != "composite_pending":
            continue
        base = _render_broll_base(
            plan, shot, media_timeline, root,
            preview_dir / f"base-{shot['id']}.mp4", lut_path,
        )
        context = _render_composite_video(
            base, video, shot, analysis_shots[shot["id"]], agent_input,
            media_timeline, plan["speaker_inset_style"],
            preview_dir / f"context-{shot['id']}.mp4",
        )
        anchor_previews = {}
        for anchor in plan["speaker_inset_style"]["allowed_anchors"]:
            alternate = _render_composite_video(
                base, video, shot, analysis_shots[shot["id"]], agent_input,
                media_timeline, plan["speaker_inset_style"],
                preview_dir / f"context-{shot['id']}-{anchor}.mp4",
                anchor_override=anchor,
            )
            anchor_previews[anchor] = {
                "path": alternate["path"].relative_to(root / "work").as_posix(),
                "sha256": alternate["sha256"],
                "probe": alternate["probe"],
            }
        if size_review is None and any(
                choice.get("display_mode") == "enabled"
                for (shot_id, _), choice in agent_subshots.items()
                if shot_id == shot["id"]):
            size_candidates = []
            selected_width = float(plan["speaker_inset_style"]["width_ratio"])
            for width_ratio in plan["speaker_inset_style"]["size_candidates"]:
                width_ratio = float(width_ratio)
                if abs(width_ratio - selected_width) <= RANGE_EPSILON:
                    candidate = context
                else:
                    candidate_style = copy.deepcopy(plan["speaker_inset_style"])
                    candidate_style["width_ratio"] = width_ratio
                    token = str(width_ratio).replace(".", "p")
                    candidate = _render_composite_video(
                        base, video, shot, analysis_shots[shot["id"]], agent_input,
                        media_timeline, candidate_style,
                        preview_dir / f"size-{shot['id']}-{token}.mp4",
                    )
                size_candidates.append({
                    "width_ratio": width_ratio,
                    "path": candidate["path"].relative_to(root / "work").as_posix(),
                    "sha256": candidate["sha256"],
                    "probe": candidate["probe"],
                })
            size_review = {
                "shot_id": shot["id"],
                "selected_width_ratio": selected_width,
                "candidates": size_candidates,
            }
        shot_records.append({
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
        })
    record = {
        "schema_version": 1,
        "analysis_sha256": plan["speaker_inset"]["analysis"]["sha256"],
        "agent_input_sha256": plan["speaker_inset"]["agent_input"]["sha256"],
        "selection_sha256": plan["selection"]["sha256"],
        "style_sha256": _canonical_sha256(plan["speaker_inset_style"]),
        "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
        "shots": shot_records,
    }
    if size_review is not None:
        record["size_review"] = size_review
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
    if preview.get("agent_input_sha256") != _canonical_sha256(agent_input):
        binding = plan.get("speaker_inset", {}).get("agent_input", {}).get("sha256")
        if preview.get("agent_input_sha256") != binding:
            errors.append("speaker inset preview Agent input binding is stale")
    try:
        _fps(timeline)
    except ValueError as exc:
        errors.append(str(exc))
    expected_shots = {
        shot.get("id"): shot for shot in plan.get("shots", [])
        if isinstance(shot, dict) and shot.get("status") == "composite_pending"
    }
    shots = preview.get("shots")
    if not isinstance(shots, list):
        return errors + ["speaker inset preview shots must be a list"]
    if [shot.get("shot_id") for shot in shots if isinstance(shot, dict)] != list(expected_shots):
        errors.append("speaker inset preview shots do not match composite_pending shots")
    root = Path(project_root).resolve() if project_root is not None else None
    allowed = plan.get("speaker_inset_style", {}).get("allowed_anchors", [])
    enabled_shot_ids = []
    for agent_shot in agent_input.get("shots", []):
        if (isinstance(agent_shot, dict) and any(
                isinstance(item, dict) and item.get("display_mode") == "enabled"
                for item in agent_shot.get("subshots", []))):
            enabled_shot_ids.append(agent_shot.get("shot_id"))
    size_review = preview.get("size_review")
    if enabled_shot_ids:
        if not isinstance(size_review, dict):
            errors.append("speaker inset project size review is required")
        else:
            expected_ratios = [
                float(value) for value in plan.get("speaker_inset_style", {}).get(
                    "size_candidates", []
                ) if _number(value) is not None
            ]
            candidates = size_review.get("candidates")
            if size_review.get("shot_id") != enabled_shot_ids[0]:
                errors.append("speaker inset size review must use the first enabled shot")
            if _number(size_review.get("selected_width_ratio")) is None or abs(
                    float(size_review.get("selected_width_ratio", 0))
                    - float(plan.get("speaker_inset_style", {}).get("width_ratio", 0))
            ) > RANGE_EPSILON:
                errors.append("speaker inset size review selected width does not match style")
            if (not isinstance(candidates, list)
                    or [float(item.get("width_ratio")) for item in candidates
                        if isinstance(item, dict) and _number(item.get("width_ratio")) is not None]
                    != expected_ratios
                    or len(candidates or []) != len(expected_ratios)):
                errors.append("speaker inset size review candidates do not match style")
            else:
                for candidate in candidates:
                    errors.extend(_preview_binding_errors(
                        candidate,
                        f"speaker inset size review {candidate['width_ratio']}",
                        root=root, verify_files=verify_files,
                    ))
    elif size_review is not None:
        errors.append("speaker inset size review requires an enabled speaker subshot")
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
        anchor_previews = shot.get("anchor_previews")
        if not isinstance(anchor_previews, dict) or list(anchor_previews) != allowed:
            errors.append(f"{shot_id} anchor previews must match allowed anchors")
            continue
        for anchor, binding in anchor_previews.items():
            errors.extend(_preview_binding_errors(
                binding, f"{shot_id} {anchor} preview",
                root=root, verify_files=verify_files,
            ))
    if enabled_shot_ids and isinstance(size_review, dict):
        selected = next((
            candidate for candidate in size_review.get("candidates", [])
            if isinstance(candidate, dict)
            and _number(candidate.get("width_ratio")) is not None
            and abs(float(candidate["width_ratio"]) - float(
                plan["speaker_inset_style"]["width_ratio"])) <= RANGE_EPSILON
        ), None)
        selected_shot = next((
            item for item in shots if isinstance(item, dict)
            and item.get("shot_id") == size_review.get("shot_id")
        ), None)
        if (not isinstance(selected, dict) or not isinstance(selected_shot, dict)
                or selected.get("path") != selected_shot.get("preview", {}).get("path")
                or selected.get("sha256") != selected_shot.get("preview", {}).get("sha256")):
            errors.append("speaker inset selected size review must bind the contextual preview")
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

    size_assessment = clearance.get("size_assessment")
    size_review = preview.get("size_review")
    if not isinstance(size_assessment, dict):
        errors.append("speaker inset project size assessment is required")
    else:
        rationale = size_assessment.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append("speaker inset size assessment rationale is required")
        if isinstance(size_review, dict):
            expected_widths = [
                candidate.get("width_ratio")
                for candidate in size_review.get("candidates", [])
                if isinstance(candidate, dict)
            ]
            if (size_assessment.get("status") != "pass"
                    or size_assessment.get("calibration_shot_id") != size_review.get("shot_id")
                    or _number(size_assessment.get("selected_width_ratio")) is None
                    or abs(float(size_assessment.get("selected_width_ratio", 0)) - float(
                        size_review.get("selected_width_ratio", 0))) > RANGE_EPSILON
                    or size_assessment.get("checked_width_ratios") != expected_widths):
                errors.append(
                    "speaker inset size assessment must pass and bind every project size preview"
                )
        elif size_assessment.get("status") != "not_applicable":
            errors.append("speaker inset size assessment must be not_applicable without an enabled inset")

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
    allowed = plan.get("speaker_inset_style", {}).get("allowed_anchors", [])
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
        for item in items:
            label = item.get("id") if isinstance(item, dict) else None
            if label not in analysis_subshots or label not in agent_subshots:
                continue
            agent_choice = agent_subshots[label]
            rationale = item.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(f"{label} clearance rationale is required")
            expected_legibility = (
                "pass" if item.get("display_mode") == "enabled" else "not_applicable"
            )
            if item.get("subject_legibility") != expected_legibility:
                errors.append(
                    f"{label} subject_legibility must be {expected_legibility}"
                )
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
                continue
            status = item.get("clearance_status")
            if status == "pass":
                anchor = item.get("anchor")
                if (item.get("display_mode") != "enabled"
                        or agent_choice.get("display_mode") != "enabled"
                        or anchor != agent_choice.get("anchor")
                        or anchor not in checked
                        or anchor not in available):
                    errors.append(f"{label} passing clearance must bind the enabled checked anchor")
            elif status == "no_safe_position":
                if (item.get("display_mode") != "pure_broll"
                        or item.get("anchor") is not None
                        or checked != allowed
                        or any(anchor not in available for anchor in allowed)):
                    errors.append(f"{label} no_safe_position must check all allowed anchors and use pure_broll")
            else:
                errors.append(f"{label} clearance_status must be pass or no_safe_position")
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
