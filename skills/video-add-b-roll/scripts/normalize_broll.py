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
import speaker_inset


KEN_BURNS_DIRECTIONS = {"zoom-in", "pan-left", "pan-right"}
INTERMEDIATE_PROFILE = {
    "schema_version": 1,
    "container": "mp4",
    "encoder": "libx264",
    "codec": "h264",
    "crf": 18,
    "preset": "medium",
    "pix_fmt": "yuv420p",
    "audio": "none",
    "movflags": "+faststart",
}


def delivery_encoder_args():
    return [
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]


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
    candidates = candidate if isinstance(candidate, list) else [candidate]
    if (not isinstance(selected, dict) or not candidates
            or any(not isinstance(item, dict) for item in candidates)):
        raise ValueError("shot selection does not match candidate")
    selected_ids = broll_plan.selected_candidate_ids(selected)
    candidate_ids = [item.get("id") for item in candidates]
    if not selected_ids or any(candidate_id not in candidate_ids for candidate_id in selected_ids):
        raise ValueError("shot selection does not match candidate")
    if "segments" in selected:
        if any(next(item for item in candidates if item.get("id") == candidate_id).get("media_type") != "video"
               for candidate_id in selected_ids):
            raise ValueError("canonical segments require video candidates")
        try:
            details = broll_plan.selection_details(
                shot, candidates, {"fps": {"num": num, "den": den}},
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if abs(details["program_duration_s"] - duration) > den / num + 1e-6:
            raise ValueError("selection program duration does not match shot")
        return "video", details
    if len(candidates) != 1 or selected_ids != candidate_ids:
        raise ValueError("legacy selection requires exactly one candidate")
    candidate = candidates[0]
    media_type = candidate.get("media_type")
    if media_type == "video":
        try:
            details = broll_plan.selection_details(
                shot, candidate, {"fps": {"num": num, "den": den}},
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if abs(details["program_duration_s"] - duration) > den / num + 1e-6:
            raise ValueError("selection program duration does not match shot")
        return media_type, details
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
            segment = option["segments"][0]
            start = segment["source_range"]["start_s"]
            end = segment["source_range"]["end_s"]
            requested = option.get("legacy_requested_source_range", segment["source_range"])
            input_start, input_end = requested["start_s"], requested["end_s"]
            inputs = ["-ss", f"{input_start:.9f}", "-t", f"{input_end - input_start:.9f}", "-i", str(source)]
            rate = float(segment["playback_rate"])
            filters = common + [f"setpts=(PTS-STARTPTS)/{rate:g}", f"fps={num}/{den}:round=up"]
            if option["format"] == "canonical":
                frame_count = round(duration * num / den)
                filters.extend(["tpad=stop_mode=clone:stop=-1", f"trim=end_frame={frame_count}"])
            else:
                filters.append(f"trim=duration={duration:.9f}")
        else:
            zoom, x, y = option
            inputs = ["-loop", "1", "-i", str(source)]
            filters = common + [f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={num}/{den}", "setsar=1", f"trim=duration={duration:.9f}", "setpts=PTS-STARTPTS"]
        if lut_path is not None:
            filters.append(f"lut3d={lut_path.name}")
        command = [
            "ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-map", "0:v:0",
            "-vf", ",".join(filters), "-t", f"{duration:.9f}",
            "-an", "-sn", "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
            *delivery_encoder_args(), str(part),
        ]
        subprocess.run(command, cwd=lut_path.parent if lut_path else None, check=True, capture_output=True)
        probe = _probe(part)
        _check_probe(probe, width, height, num, den, duration)
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(part), "-map", "0:v:0", "-f", "null", "-"], check=True, capture_output=True)
        digest = broll_plan.sha256_file(part)
        os.replace(part, target)
        record = {
            "path": target,
            "source_path": candidate.get("cache_path"),
            "source_sha256": source_digest,
            "sha256": digest,
            "probe": probe,
            "intermediate_profile": copy.deepcopy(INTERMEDIATE_PROFILE),
            **grade_hashes,
        }
        if media_type == "video":
            record.update({
                "selection_format": option["format"],
                "segment": copy.deepcopy(option["segments"][0]),
                "source_duration_s": option["source_duration_s"],
                "effective_duration_s": option["effective_duration_s"],
                "program_duration_s": option["program_duration_s"],
            })
            if "legacy_requested_source_range" in option:
                record["legacy_requested_source_range"] = copy.deepcopy(
                    option["legacy_requested_source_range"]
                )
        return record
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _segment_output(target, index):
    return target.with_name(f"{target.stem}-segment-{index:02d}.mp4")


def normalize_selection(candidates, shot, timeline, destination, *, lut=None):
    """Render 1-3 canonical source segments in one filtergraph and encoder pass."""
    target, root = _destination(destination)
    part = target.with_suffix(".part.mp4")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    width, height, num, den = _timeline_spec(timeline)
    duration = _shot_duration(shot, timeline)
    media_type, details = _selection(candidates, shot, duration, num, den)
    if media_type != "video" or details["format"] != "canonical":
        if len(candidates) != 1:
            raise ValueError("non-canonical selection requires exactly one candidate")
        return normalize_shot(candidates[0], shot, timeline, target, lut=lut)
    candidate_map = {candidate.get("id"): candidate for candidate in candidates}
    lut_path, grade_hashes = _grade(lut, root)
    try:
        inputs = []
        filters = []
        labels = []
        source_segments = []
        for index, (segment, timing) in enumerate(zip(
                details["segments"], details["segment_details"])):
            candidate = candidate_map[segment["candidate_id"]]
            source, source_digest = _source(candidate, root)
            inputs.extend(["-i", str(source)])
            frame_count = round(timing["program_duration_s"] * num / den)
            rate = float(timing["playback_rate"])
            source_range = segment["source_range"]
            chain = [
                f"[{index}:v]trim=start={source_range['start_s']:.9f}:end={source_range['end_s']:.9f}",
                f"setpts=(PTS-STARTPTS)/{rate:g}",
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}",
                "setsar=1",
                f"fps={num}/{den}:round=up",
                "tpad=stop_mode=clone:stop=-1",
                f"trim=end_frame={frame_count}",
            ]
            if lut_path is not None:
                chain.append(f"lut3d={lut_path.name}")
            label = f"v{index}"
            filters.append(",".join(chain) + f"[{label}]")
            labels.append(f"[{label}]")
            source_segments.append({
                "candidate_id": candidate["id"],
                "segment": copy.deepcopy(segment),
                "source_path": candidate.get("cache_path"),
                "source_sha256": source_digest,
                "source_duration_s": timing["source_duration_s"],
                "effective_duration_s": timing["effective_duration_s"],
                "program_duration_s": timing["program_duration_s"],
                "playback_rate": timing["playback_rate"],
            })
        if len(labels) == 1:
            output_label = labels[0]
        else:
            output_label = "[outv]"
            filters.append(
                f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0{output_label}"
            )
        command = [
            "ffmpeg", "-y", "-loglevel", "error", *inputs,
            "-filter_complex", ";".join(filters), "-map", output_label,
            "-t", f"{duration:.9f}", "-r", f"{num}/{den}",
            "-an", "-sn", "-dn", "-map_metadata", "-1", "-write_tmcd", "0",
            *delivery_encoder_args(), str(part),
        ]
        subprocess.run(
            command, cwd=lut_path.parent if lut_path else None,
            check=True, capture_output=True,
        )
        probe = _probe(part)
        _check_probe(probe, width, height, num, den, duration)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(part), "-map", "0:v:0", "-f", "null", "-"],
            check=True, capture_output=True,
        )
        digest = broll_plan.sha256_file(part)
        os.replace(part, target)
        return {
            "path": target,
            "selection_format": "canonical",
            "source_segments": source_segments,
            "source_paths": [record["source_path"] for record in source_segments],
            "source_sha256s": [record["source_sha256"] for record in source_segments],
            "sha256": digest,
            "probe": probe,
            "program_duration_s": details["program_duration_s"],
            "intermediate_profile": copy.deepcopy(INTERMEDIATE_PROFILE),
            **grade_hashes,
        }
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def _validate_normalized(record, candidate, shot, timeline, output, root, grade_hashes):
    if not isinstance(record, dict):
        raise ValueError("normalized record is required")
    if "composition" in record or "broll_base" in record:
        composition = record.get("composition")
        base = record.get("broll_base")
        if not isinstance(composition, dict) or composition.get("kind") != "speaker-inset":
            raise ValueError("speaker inset normalized composition is missing")
        if not isinstance(base, dict):
            raise ValueError("speaker inset normalized B-roll base is missing")
        if ("intermediate_profile" in record or "intermediate_profile" in base):
            if (record.get("intermediate_profile") != INTERMEDIATE_PROFILE
                    or base.get("intermediate_profile") != INTERMEDIATE_PROFILE):
                raise ValueError("speaker inset intermediate profile is stale")
        base_output = output.with_name(f"{output.stem}-base.mp4")
        expected_base_path = base_output.relative_to(root / "work").as_posix()
        if base.get("path") != expected_base_path:
            raise ValueError("speaker inset normalized B-roll base path is stale")
        base_record = copy.deepcopy(record)
        base_record.update({
            "path": base.get("path"), "sha256": base.get("sha256"),
            "probe": copy.deepcopy(base.get("probe")),
        })
        if "intermediate_profile" in base:
            base_record["intermediate_profile"] = copy.deepcopy(
                base["intermediate_profile"]
            )
        base_record.pop("composition", None)
        base_record.pop("broll_base", None)
        _validate_normalized(
            base_record, candidate, shot, timeline, base_output, root, grade_hashes,
        )
        expected_path = output.relative_to(root / "work").as_posix()
        if record.get("path") != expected_path or not output.is_file():
            raise ValueError("normalized output path is stale")
        if record.get("sha256") != broll_plan.sha256_file(output):
            raise ValueError("normalized output SHA-256 is stale")
        width, height, num, den = _timeline_spec(timeline)
        probe = _probe(output)
        _check_probe(probe, width, height, num, den, _shot_duration(shot, timeline))
        if record.get("probe") != probe:
            raise ValueError("normalized probe is stale")
        subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(output),
            "-map", "0:v:0", "-f", "null", "-",
        ], check=True, capture_output=True)
        return
    expected_path = output.relative_to(root / "work").as_posix()
    if record.get("path") != expected_path or not output.is_file():
        raise ValueError("normalized output path is stale")
    if record.get("sha256") != broll_plan.sha256_file(output):
        raise ValueError("normalized output SHA-256 is stale")
    for key in ("grade_plan_sha256", "selected_lut_sha256"):
        if (key in record or key in grade_hashes) and record.get(key) != grade_hashes.get(key):
            raise ValueError("normalized grade identity is stale")
    width, height, num, den = _timeline_spec(timeline)
    candidates = candidate if isinstance(candidate, list) else [candidate]
    if any(not isinstance(item, dict) for item in candidates):
        raise ValueError("normalized candidates are invalid")
    if ("intermediate_profile" in record
            and record.get("intermediate_profile") != INTERMEDIATE_PROFILE):
        raise ValueError("normalized intermediate profile is stale")
    source_records = record.get("source_segments")
    if source_records is not None:
        if record.get("intermediate_profile") != INTERMEDIATE_PROFILE:
            raise ValueError("source-direct normalized record requires the fixed intermediate profile")
        if "segments" in record or "concat_sha256" in record:
            raise ValueError("source-direct normalized record contains legacy component fields")
        _, details = _selection(
            candidates, shot, _shot_duration(shot, timeline), num, den,
        )
        if (record.get("selection_format") != "canonical"
                or details["format"] != "canonical"
                or not isinstance(source_records, list)
                or len(source_records) != len(details["segments"])):
            raise ValueError("normalized source segments are stale")
        candidate_map = {item.get("id"): item for item in candidates}
        expected_paths = []
        expected_hashes = []
        for source_record, segment, timing in zip(
                source_records, details["segments"], details["segment_details"]):
            selected_candidate = candidate_map.get(segment["candidate_id"])
            if not isinstance(source_record, dict) or selected_candidate is None:
                raise ValueError("normalized source segment candidate is stale")
            _, source_digest = _source(selected_candidate, root)
            expected_paths.append(selected_candidate.get("cache_path"))
            expected_hashes.append(source_digest)
            if (source_record.get("candidate_id") != selected_candidate.get("id")
                    or source_record.get("segment") != segment
                    or source_record.get("source_path") != selected_candidate.get("cache_path")
                    or source_record.get("source_sha256") != source_digest):
                raise ValueError("normalized source segment identity is stale")
            for key in (
                    "source_duration_s", "effective_duration_s",
                    "program_duration_s", "playback_rate"):
                actual = _number(source_record.get(key), f"normalized source segment {key}")
                if abs(actual - timing[key]) > den / num + 1e-6:
                    raise ValueError(f"normalized source segment {key} is stale")
        if (record.get("source_paths") != expected_paths
                or record.get("source_sha256s") != expected_hashes):
            raise ValueError("normalized source segment bindings are stale")
        actual_duration = _number(
            record.get("program_duration_s"), "normalized program_duration_s",
        )
        if abs(actual_duration - details["program_duration_s"]) > den / num + 1e-6:
            raise ValueError("normalized program_duration_s is stale")
        probe = _probe(output)
        _check_probe(probe, width, height, num, den, _shot_duration(shot, timeline))
        if record.get("probe") != probe:
            raise ValueError("normalized probe is stale")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(output),
             "-map", "0:v:0", "-f", "null", "-"],
            check=True, capture_output=True,
        )
        return
    component_records = record.get("segments")
    if component_records is not None:
        _, details = _selection(
            candidates, shot, _shot_duration(shot, timeline), num, den,
        )
        if (details["format"] != "canonical" or not isinstance(component_records, list)
                or len(component_records) != len(details["segments"])):
            raise ValueError("normalized segments are stale")
        candidate_map = {item.get("id"): item for item in candidates}
        expected_source_paths = []
        expected_source_hashes = []
        for index, (component, segment, timing) in enumerate(zip(
                component_records, details["segments"], details["segment_details"]), 1):
            if not isinstance(component, dict) or component.get("segment") != segment:
                raise ValueError("normalized segment is stale")
            selected_candidate = candidate_map.get(segment["candidate_id"])
            if selected_candidate is None:
                raise ValueError("normalized segment candidate is stale")
            _, source_digest = _source(selected_candidate, root)
            expected_source_paths.append(selected_candidate.get("cache_path"))
            expected_source_hashes.append(source_digest)
            if (component.get("candidate_id") != selected_candidate.get("id")
                    or component.get("source_path") != selected_candidate.get("cache_path")
                    or component.get("source_sha256") != source_digest):
                raise ValueError("normalized segment source identity is stale")
            component_output = _segment_output(output, index)
            expected_component_path = component_output.relative_to(root / "work").as_posix()
            if (component.get("normalized_path") != expected_component_path
                    or not component_output.is_file()
                    or component.get("normalized_sha256") != broll_plan.sha256_file(component_output)):
                raise ValueError("normalized segment output is stale")
            for key in ("source_duration_s", "effective_duration_s", "program_duration_s", "playback_rate"):
                actual = _number(component.get(key), f"normalized segment {key}")
                if abs(actual - timing[key]) > den / num + 1e-6:
                    raise ValueError(f"normalized segment {key} is stale")
            component_probe = _probe(component_output)
            _check_probe(component_probe, width, height, num, den, timing["program_duration_s"])
            if component.get("probe") != component_probe:
                raise ValueError("normalized segment probe is stale")
            subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(component_output), "-map", "0:v:0", "-f", "null", "-"],
                check=True, capture_output=True,
            )
        if record.get("source_paths") != expected_source_paths or record.get("source_sha256s") != expected_source_hashes:
            raise ValueError("normalized segment source bindings are stale")
        if record.get("concat_sha256") != record.get("sha256"):
            raise ValueError("normalized concat SHA-256 is stale")
        actual_program_duration = _number(record.get("program_duration_s"), "normalized program_duration_s")
        if abs(actual_program_duration - details["program_duration_s"]) > den / num + 1e-6:
            raise ValueError("normalized program_duration_s is stale")
        probe = _probe(output)
        _check_probe(probe, width, height, num, den, _shot_duration(shot, timeline))
        if record.get("probe") != probe:
            raise ValueError("normalized probe is stale")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(output), "-map", "0:v:0", "-f", "null", "-"],
            check=True, capture_output=True,
        )
        return
    if len(candidates) != 1:
        raise ValueError("legacy normalized record requires one candidate")
    candidate = candidates[0]
    _, source_digest = _source(candidate, root)
    if record.get("source_path") != candidate.get("cache_path") or record.get("source_sha256") != source_digest:
        raise ValueError("normalized source identity is stale")
    if candidate.get("media_type") == "video":
        _, details = _selection(
            candidate, shot, _shot_duration(shot, timeline), num, den,
        )
        if details["format"] == "canonical" or "selection_format" in record:
            if record.get("selection_format") != details["format"]:
                raise ValueError("normalized selection format is stale")
            if record.get("segment") != details["segments"][0]:
                raise ValueError("normalized segment is stale")
            for key in ("source_duration_s", "effective_duration_s", "program_duration_s"):
                actual = _number(record.get(key), f"normalized {key}")
                if abs(actual - details[key]) > den / num + 1e-6:
                    raise ValueError(f"normalized {key} is stale")
            if record.get("legacy_requested_source_range") != details.get("legacy_requested_source_range"):
                raise ValueError("normalized legacy requested source range is stale")
    probe = _probe(output)
    _check_probe(probe, width, height, num, den, _shot_duration(shot, timeline))
    if record.get("probe") != probe:
        raise ValueError("normalized probe is stale")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-map", "0:v:0", "-f", "null", "-"], check=True, capture_output=True)


def _speaker_documents(plan, root):
    speaker = plan.get("speaker_inset")
    if not isinstance(speaker, dict):
        raise ValueError("enabled speaker inset requires delivery composite artifacts")
    documents = {}
    for name in ("analysis", "agent_input", "preview", "clearance"):
        binding = speaker.get(name)
        if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
            raise ValueError(f"enabled speaker inset requires {name} artifact")
        path = root / "work" / binding["path"]
        try:
            path.resolve().relative_to((root / "work").resolve())
        except ValueError as exc:
            raise ValueError(f"speaker inset {name} path escapes work") from exc
        if not path.is_file() or binding.get("sha256") != broll_plan.sha256_file(path):
            raise ValueError(f"speaker inset {name} artifact is missing or stale")
        try:
            documents[name] = projectlib.load_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"speaker inset {name} artifact is invalid") from exc
    return documents


def _composition_record(plan, agent_input, shot):
    recommendation = next(
        item["layout_recommendation"]
        for item in agent_input["shots"] if item.get("shot_id") == shot.get("id")
    )
    speaker = plan["speaker_inset"]
    return {
        "kind": "speaker-inset",
        "layout_preset": recommendation["preset"],
        "project_primary_preset": agent_input["project_layout_strategy"]["primary_preset"],
        "review_id": plan["review"]["review_id"],
        "selection_sha256": plan["selection"]["sha256"],
        "analysis_sha256": speaker["analysis"]["sha256"],
        "agent_input_sha256": speaker["agent_input"]["sha256"],
        "preview_sha256": speaker["preview"]["sha256"],
        "clearance_sha256": speaker["clearance"]["sha256"],
        "style_sha256": broll_plan.canonical_sha256(plan["speaker_inset_style"]),
        "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
    }


def normalize_plan(plan_path, timeline_path, project_root, *, lut=None, review_video=None):
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
    inset_selected = (
        speaker_inset.style_enabled(plan.get("speaker_inset_style"))
        and any(
            isinstance(shot, dict) and shot.get("status") != "skipped"
            for shot in plan["shots"]
        )
    )
    if inset_selected and review_video is None:
        raise ValueError(
            "enabled speaker inset requires delivery composite and explicit review_video"
        )
    if not inset_selected and review_video is not None:
        raise ValueError("review_video is only valid for enabled speaker inset")
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
    speaker_documents = None
    review_path = None
    if inset_selected:
        review_path, timeline = speaker_inset.validate_review_video(
            plan, timeline, review_video, root,
        )
        speaker_documents = _speaker_documents(plan, root)
    result = copy.deepcopy(plan)
    for index, shot in enumerate(result["shots"], 1):
        if not isinstance(shot, dict):
            raise ValueError("plan shots must be objects")
        if shot.get("status") == "skipped":
            continue
        selected, candidates = shot.get("selected"), shot.get("candidates")
        if not isinstance(selected, dict) or not isinstance(candidates, list):
            raise ValueError("selected shot is invalid")
        selected_ids = broll_plan.selected_candidate_ids(selected)
        selected_candidates = [
            next((item for item in candidates
                  if isinstance(item, dict) and item.get("id") == candidate_id), None)
            for candidate_id in selected_ids
        ]
        if not selected_ids or any(candidate is None for candidate in selected_candidates):
            raise ValueError("selected candidate does not belong to shot")
        output = root / f"work/cache/b-roll/normalized/broll-{index:03d}.mp4"
        if shot.get("status") == "normalized":
            _validate_normalized(shot.get("normalized"), selected_candidates, shot, timeline, output, root, grade_hashes)
            continue
        if shot.get("status") != "selected":
            raise ValueError("normalize_plan requires selected, normalized, or skipped shots")
        normalized_output = output
        if inset_selected:
            normalized_output = output.with_name(f"{output.stem}-base.mp4")
        plan_part = plan_path.with_suffix(".part.json")
        generated = []
        try:
            plan_part.unlink(missing_ok=True)
            if "segments" in selected:
                record = normalize_selection(
                    selected_candidates, shot, timeline, normalized_output, lut=lut_path,
                )
            else:
                if len(selected_candidates) != 1:
                    raise ValueError("legacy selection requires exactly one candidate")
                record = normalize_shot(
                    selected_candidates[0], shot, timeline, normalized_output, lut=lut_path,
                )
            generated.append(normalized_output)
            record["path"] = normalized_output.relative_to(root / "work").as_posix()
            if inset_selected:
                base_binding = {
                    "path": record["path"],
                    "sha256": record["sha256"],
                    "probe": copy.deepcopy(record["probe"]),
                    "intermediate_profile": copy.deepcopy(
                        record["intermediate_profile"]
                    ),
                }
                composite = speaker_inset.render_delivery_composite(
                    plan=plan, shot=shot,
                    analysis=speaker_documents["analysis"],
                    agent_input=speaker_documents["agent_input"],
                    preview=speaker_documents["preview"],
                    clearance=speaker_documents["clearance"],
                    timeline=timeline, style=plan["speaker_inset_style"],
                    base_video=normalized_output, review_video=review_path,
                    destination=output, project_root=root,
                    delivery_encoder_args=delivery_encoder_args(),
                )
                generated.append(output)
                record.update({
                    "path": output.relative_to(root / "work").as_posix(),
                    "sha256": composite["sha256"],
                    "probe": copy.deepcopy(composite["probe"]),
                    "composition": _composition_record(
                        plan, speaker_documents["agent_input"], shot,
                    ),
                    "broll_base": base_binding,
                })
            shot["normalized"], shot["status"] = record, "normalized"
            errors = broll_plan.validate_plan(
                result, timeline, transcript, project=project, project_root=root, verify_files=True
            )
            if errors:
                raise ValueError("invalid normalized plan: " + "; ".join(errors))
            projectlib.write_json(plan_part, result)
            os.replace(plan_part, plan_path)
        except BaseException:
            cleanup = set(generated)
            cleanup.update({
                output.with_suffix(".part.mp4"),
                normalized_output.with_suffix(".part.mp4"),
                plan_part,
            })
            for path in cleanup:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
    return result
