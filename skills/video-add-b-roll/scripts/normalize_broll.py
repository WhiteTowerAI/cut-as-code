"""Normalize approved B-roll selections into delivery-ready silent clips."""

import copy
import json
import math
import os
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib

import broll_plan


KEN_BURNS_DIRECTIONS = {"zoom-in", "pan-left", "pan-right"}


def _number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _timeline_spec(timeline):
    if not isinstance(timeline, dict):
        raise ValueError("timeline must be an object")
    width, height, fps = timeline.get("width"), timeline.get("height"), timeline.get("fps")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value % 2 for value in (width, height)):
        raise ValueError("timeline width and height must be positive even integers")
    if not isinstance(fps, dict):
        raise ValueError("timeline fps must be an object")
    num, den = fps.get("num"), fps.get("den")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (num, den)):
        raise ValueError("timeline fps num and den must be positive integers")
    return width, height, num, den


def _timeline_with_media_geometry(timeline, root):
    if not isinstance(timeline, dict) or all(
        field in timeline for field in ("width", "height")
    ):
        return timeline
    try:
        media = projectlib.load_json(Path(root) / "work/understand/media.json")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        media = {}
    if not isinstance(media, dict):
        media = {}
    result = copy.deepcopy(timeline)
    for field in ("width", "height"):
        if field not in result:
            result[field] = media.get(field)
    return result


def _shot_duration(shot, timeline):
    if not isinstance(shot, dict):
        raise ValueError("shot must be an object")
    value = shot.get("program_range")
    if not isinstance(value, dict):
        raise ValueError("shot program_range must be an object")
    start = _number(value.get("start_s"), "shot program start_s")
    end = _number(value.get("end_s"), "shot program end_s")
    if start < 0 or end <= start:
        raise ValueError("shot program_range must be a positive half-open range")
    timeline_duration = _number(timeline.get("program_duration_s"), "timeline program_duration_s")
    if end > timeline_duration:
        raise ValueError("shot program_range is outside timeline")
    return end - start


def _destination(value):
    target = Path(value).resolve()
    if target.suffix.lower() != ".mp4" or target.parent.parts[-4:] != ("work", "cache", "b-roll", "normalized"):
        raise ValueError("destination must be directly beneath work/cache/b-roll/normalized")
    return target, target.parent.parents[3]


def _source(candidate, root):
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    value = candidate.get("cache_path")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("candidate cache_path is required")
    source = broll_plan._candidate_path(root, value)
    if source is None:
        raise ValueError("candidate path escapes project root")
    if not source.is_file():
        raise ValueError("candidate file is missing")
    digest = broll_plan.sha256_file(source)
    if candidate.get("sha256") not in (None, digest):
        raise ValueError("candidate SHA-256 is stale")
    return source, digest


def _grade(lut, root):
    if lut is None:
        return None, {}
    path = Path(lut).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("selected LUT path escapes project root") from exc
    if not path.is_file() or path.suffix.lower() != ".cube" or not re.fullmatch(r"[A-Za-z0-9_.-]+", path.name):
        raise ValueError("selected LUT must be a safe local .cube file")
    grade_plan = root / "work/color-grade/grade-plan.json"
    if not grade_plan.is_file():
        raise ValueError("grade plan is required when applying a LUT")
    try:
        grade = projectlib.load_json(grade_plan)
        selected = Path(grade["selected_lut"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("grade plan is invalid") from exc
    selected = (selected if selected.is_absolute() else grade_plan.parent / selected).resolve()
    if selected != path:
        raise ValueError("selected LUT does not match grade plan")
    return path, {
        "grade_plan_sha256": broll_plan.sha256_file(grade_plan),
        "selected_lut_sha256": broll_plan.sha256_file(path),
    }


def _probe(path):
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,pix_fmt,sample_aspect_ratio,duration:format=duration",
            "-of", "json", str(path),
        ], check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        streams = payload["streams"]
        video = next(item for item in streams if item.get("codec_type") == "video")
        rate = Fraction(video.get("avg_frame_rate") or video["r_frame_rate"])
        duration = float(video.get("duration") or payload["format"]["duration"])
    except (OSError, KeyError, TypeError, ValueError, ZeroDivisionError, json.JSONDecodeError, StopIteration, subprocess.CalledProcessError) as exc:
        raise ValueError("normalized media probe failed") from exc
    return {
        "duration_s": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": {"num": rate.numerator, "den": rate.denominator},
        "sar": video.get("sample_aspect_ratio"),
        "codec": video.get("codec_name"),
        "pix_fmt": video.get("pix_fmt"),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
        "has_subtitles": any(item.get("codec_type") == "subtitle" for item in streams),
        "has_data": any(item.get("codec_type") == "data" for item in streams),
    }


def _check_probe(probe, width, height, num, den, duration):
    if (probe["width"], probe["height"]) != (width, height):
        raise ValueError("normalized dimensions do not match timeline")
    if Fraction(probe["fps"]["num"], probe["fps"]["den"]) != Fraction(num, den):
        raise ValueError("normalized fps does not match timeline")
    if probe["sar"] != "1:1" or probe["codec"] != "h264" or probe["pix_fmt"] != "yuv420p":
        raise ValueError("normalized video format is invalid")
    if probe["has_audio"] or probe["has_subtitles"] or probe["has_data"]:
        raise ValueError("normalized clip contains non-video streams")
    if abs(probe["duration_s"] - duration) > den / num + 1e-6:
        raise ValueError("normalized duration does not match shot")


def _selection(candidate, shot, duration, num, den):
    selected = shot.get("selected")
    if not isinstance(selected, dict) or selected.get("candidate_id") != candidate.get("id"):
        raise ValueError("shot selection does not match candidate")
    media_type = candidate.get("media_type")
    if media_type == "video":
        trim = selected.get("source_trim")
        if not isinstance(trim, dict):
            raise ValueError("video selection requires explicit source_trim")
        start = _number(trim.get("start_s"), "source_trim start_s")
        end = _number(trim.get("end_s"), "source_trim end_s")
        probe = candidate.get("probe")
        source_duration = _number(probe.get("duration_s") if isinstance(probe, dict) else None, "candidate probe.duration_s")
        if start < 0 or end <= start or end > source_duration:
            raise ValueError("video selection requires a valid source_trim")
        return media_type, (start, end)
    if media_type != "image":
        raise ValueError("candidate media_type must be video or image")
    motion = selected.get("ken_burns")
    direction = motion.get("direction") if isinstance(motion, dict) else None
    if direction not in KEN_BURNS_DIRECTIONS:
        raise ValueError("image selection requires explicit valid ken_burns")
    frames = max(1, math.ceil(duration * num / den - 1e-9))
    last = max(1, frames - 1)
    if direction == "zoom-in":
        return media_type, (f"1+0.15*on/{last}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")
    x = f"(iw-iw/zoom)*{'(1-on/' + str(last) + ')' if direction == 'pan-left' else 'on/' + str(last)}"
    return media_type, ("1.15", x, "ih/2-(ih/zoom/2)")


def normalize_shot(candidate, shot, timeline, destination, *, lut=None):
    """Render one selected candidate and publish it only after probe/decode checks."""
    target, root = _destination(destination)
    part = target.with_suffix(".part.mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    try:
        width, height, num, den = _timeline_spec(timeline)
        duration = _shot_duration(shot, timeline)
        source, source_digest = _source(candidate, root)
        lut_path, grade_hashes = _grade(lut, root)
        media_type, option = _selection(candidate, shot, duration, num, den)
        common = [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}", "setsar=1",
        ]
        if media_type == "video":
            start, end = option
            inputs = ["-ss", f"{start:.9f}", "-t", f"{end - start:.9f}", "-i", str(source)]
            filters = common + [f"fps={num}/{den}", f"trim=duration={duration:.9f}", "setpts=PTS-STARTPTS"]
        else:
            zoom, x, y = option
            inputs = ["-loop", "1", "-i", str(source)]
            filters = common + [f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={num}/{den}", "setsar=1", f"trim=duration={duration:.9f}", "setpts=PTS-STARTPTS"]
        if lut_path is not None:
            filters.append(f"lut3d={lut_path.name}")
        command = [
            "ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-vf", ",".join(filters), "-t", f"{duration:.9f}",
            "-an", "-sn", "-dn", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(part),
        ]
        subprocess.run(command, cwd=lut_path.parent if lut_path else None, check=True, capture_output=True)
        probe = _probe(part)
        _check_probe(probe, width, height, num, den, duration)
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(part), "-map", "0:v:0", "-f", "null", "-"], check=True, capture_output=True)
        digest = broll_plan.sha256_file(part)
        os.replace(part, target)
        return {
            "path": target,
            "source_path": candidate.get("cache_path"),
            "source_sha256": source_digest,
            "sha256": digest,
            "probe": probe,
            **grade_hashes,
        }
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _validate_normalized(record, candidate, shot, timeline, output, root, grade_hashes):
    if not isinstance(record, dict):
        raise ValueError("normalized record is required")
    expected_path = output.relative_to(root / "work").as_posix()
    if record.get("path") != expected_path or not output.is_file():
        raise ValueError("normalized output path is stale")
    _, source_digest = _source(candidate, root)
    if record.get("source_path") != candidate.get("cache_path") or record.get("source_sha256") != source_digest:
        raise ValueError("normalized source identity is stale")
    if record.get("sha256") != broll_plan.sha256_file(output):
        raise ValueError("normalized output SHA-256 is stale")
    for key in ("grade_plan_sha256", "selected_lut_sha256"):
        if (key in record or key in grade_hashes) and record.get(key) != grade_hashes.get(key):
            raise ValueError("normalized grade identity is stale")
    width, height, num, den = _timeline_spec(timeline)
    probe = _probe(output)
    _check_probe(probe, width, height, num, den, _shot_duration(shot, timeline))
    if record.get("probe") != probe:
        raise ValueError("normalized probe is stale")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-map", "0:v:0", "-f", "null", "-"], check=True, capture_output=True)


def normalize_plan(plan_path, timeline_path, project_root, *, lut=None):
    """Validate, resume, and durably normalize each selected shot."""
    root = Path(project_root).resolve()
    plan_path, timeline_path = Path(plan_path).resolve(), Path(timeline_path).resolve()
    if plan_path != (root / "work/b-roll/broll-plan.json").resolve():
        raise ValueError("plan_path must be canonical work/b-roll/broll-plan.json")
    if timeline_path != (root / "work/timeline.json").resolve():
        raise ValueError("timeline_path must be canonical work/timeline.json")
    try:
        plan = projectlib.load_json(plan_path)
        timeline = projectlib.load_json(timeline_path)
        transcript = projectlib.load_json(root / "work/understand/transcript.json")
        project = projectlib.load_json(root / "work/project.json")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("canonical project inputs are missing or invalid") from exc
    timeline = _timeline_with_media_geometry(timeline, root)
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list):
        raise ValueError("plan shots must be a list")
    if plan.get("review_status") != "approved":
        raise ValueError("review_status must be approved")
    errors = broll_plan.validate_plan(
        plan, timeline, transcript, project=project, project_root=root, verify_files=True
    )
    if errors:
        raise ValueError("invalid B-roll plan: " + "; ".join(errors))
    dependencies = broll_plan.active_dependencies(project)
    graded = "color-grade" in dependencies
    if graded and lut is None:
        raise ValueError("selected LUT is required for active color-grade")
    if not graded and lut is not None:
        raise ValueError("selected LUT requires active color-grade")
    lut_path, grade_hashes = _grade(lut, root) if graded else (None, {})
    input_hashes = plan.get("input_hashes", {})
    for key, digest in grade_hashes.items():
        if input_hashes.get(key) != digest:
            raise ValueError(f"{key} is stale")
    result = copy.deepcopy(plan)
    for index, shot in enumerate(result["shots"], 1):
        if not isinstance(shot, dict):
            raise ValueError("plan shots must be objects")
        if shot.get("status") == "skipped":
            continue
        selected, candidates = shot.get("selected"), shot.get("candidates")
        if not isinstance(selected, dict) or not isinstance(candidates, list):
            raise ValueError("selected shot is invalid")
        candidate = next((item for item in candidates if isinstance(item, dict) and item.get("id") == selected.get("candidate_id")), None)
        if candidate is None:
            raise ValueError("selected candidate does not belong to shot")
        output = root / f"work/cache/b-roll/normalized/broll-{index:03d}.mp4"
        if shot.get("status") == "normalized":
            _validate_normalized(shot.get("normalized"), candidate, shot, timeline, output, root, grade_hashes)
            continue
        if shot.get("status") != "selected":
            raise ValueError("normalize_plan requires selected, normalized, or skipped shots")
        record = normalize_shot(candidate, shot, timeline, output, lut=lut_path)
        record["path"] = output.relative_to(root / "work").as_posix()
        shot["normalized"], shot["status"] = record, "normalized"
        plan_part = plan_path.with_suffix(".part.json")
        try:
            errors = broll_plan.validate_plan(
                result, timeline, transcript, project=project, project_root=root, verify_files=True
            )
            if errors:
                raise ValueError("invalid normalized plan: " + "; ".join(errors))
            projectlib.write_json(plan_part, result)
            os.replace(plan_part, plan_path)
        except BaseException:
            for path in (output, output.with_suffix(".part.mp4"), plan_part):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
    return result
