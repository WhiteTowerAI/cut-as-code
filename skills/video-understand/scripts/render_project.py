"""Render a compiled Open Recut delivery plan with one video encoding pass."""

import argparse
import json
import os
import subprocess
from pathlib import Path

import projectlib


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve(project_root, plan_dir, value):
    root = Path(project_root).resolve()
    path = (Path(plan_dir) / value).resolve()
    if os.path.commonpath((str(root), str(path))) != str(root):
        raise ValueError(f"render path escapes project: {value}")
    return path


def atempo_chain(speed):
    factors = []
    value = float(speed)
    while value > 2.0:
        factors.append(2.0)
        value /= 2.0
    while value < 0.5:
        factors.append(0.5)
        value /= 0.5
    factors.append(value)
    return ",".join(f"atempo={factor:.8f}" for factor in factors)


def _verify_source_fingerprint(source, expected):
    if not expected:
        return
    stat = source.stat()
    for key, current in (("size", stat.st_size), ("modified_ns", stat.st_mtime_ns)):
        if expected.get(key) != current:
            raise ValueError(
                f"source fingerprint {key} mismatch: expected {expected.get(key)}, current {current}"
            )
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())
    if abs(float(expected["duration_s"]) - duration) > 0.05:
        raise ValueError(
            "source fingerprint duration mismatch: "
            f"expected {expected['duration_s']}, current {duration:.6f}"
        )


def _grade_filter(contribution, project_root, plan_dir):
    plan_path = _resolve(project_root, plan_dir, contribution["plan"])
    plan = _load(plan_path)
    selected = plan.get("selected_look") or contribution.get("selected_look")
    look = next((item for item in plan.get("looks", []) if item.get("name") == selected), None)
    if look is None:
        raise ValueError(f"selected grade look not found: {selected!r}")

    base = (plan.get("base") or "").strip()
    lut_value = look.get("lut") or plan.get("selected_lut")
    cwd = None
    if lut_value:
        lut_path = (plan_path.parent / lut_value).resolve()
        if not lut_path.is_file():
            raise ValueError(f"selected LUT is missing: {lut_value}")
        layer = f"lut3d={lut_path.name}"
        cwd = lut_path.parent
        return layer, cwd
    else:
        layer = (look.get("chain") or "").strip()
    if look.get("prepend_base", True) and base:
        chain = base + ("," + layer if layer else "")
    else:
        chain = layer
    return chain or "null", cwd


def _build(plan, project_root, plan_dir):
    if plan.get("schema_version") != 1:
        raise ValueError("render plan schema_version must be 1")
    plan_dir = Path(plan_dir).resolve()
    timeline = _load(_resolve(project_root, plan_dir, plan["timeline"]))
    timeline_errors = projectlib.validate_timeline(timeline)
    if timeline_errors:
        raise ValueError("invalid timeline: " + "; ".join(timeline_errors))
    contributions = plan.get("contributions", [])
    transforms = [item for item in contributions if item.get("kind") == "timeline-transform"]
    if len(transforms) > 1:
        raise ValueError("only one timeline-transform is supported")

    source_value = transforms[0].get("input") if transforms else plan.get("source")
    if not source_value:
        raise ValueError("render plan source is required")
    source = _resolve(project_root, plan_dir, source_value)
    if not source.is_file():
        raise ValueError(f"source is missing: {source_value}")
    _verify_source_fingerprint(source, plan.get("source_fingerprint"))

    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    graph = []
    fps = timeline["fps"]
    fps_text = f"{fps['num']}/{fps['den']}"
    audio_filtered = bool(transforms)

    if transforms:
        clips = timeline["clips"]
        if not clips:
            raise ValueError("timeline has no clips")
        concat_inputs = []
        for index, clip in enumerate(clips):
            start = float(clip["source_range"]["start_s"])
            duration = float(clip["source_range"]["end_s"]) - start
            speed = float(clip.get("speed", 1.0))
            command += ["-ss", f"{start:.6f}", "-t", f"{duration:.6f}", "-i", str(source)]
            graph.append(
                f"[{index}:v:0]setpts=(PTS-STARTPTS)/{speed:.8f},fps={fps_text},settb=AVTB[v{index}]"
            )
            audio_chain = "" if abs(speed - 1.0) < 1e-9 else atempo_chain(speed) + ","
            graph.append(
                f"[{index}:a:0]{audio_chain}aresample=48000,asetpts=N/SR/TB[a{index}]"
            )
            concat_inputs.append(f"[v{index}][a{index}]")
        graph.append(
            "".join(concat_inputs)
            + f"concat=n={len(clips)}:v=1:a=1[base-video][program-audio]"
        )
        video_label = "base-video"
        audio_label = "program-audio"
        next_input = len(clips)
    else:
        command += ["-i", str(source)]
        graph.append("[0:v:0]setpts=PTS-STARTPTS[base-video]")
        video_label = "base-video"
        audio_label = None
        next_input = 1

    base_filters = []
    composite_filters = []
    overlays = []
    audio_filters = []
    constraints = {}
    lut_cwd = None
    for contribution in contributions:
        kind = contribution.get("kind")
        if kind == "video-filter":
            if contribution.get("target") not in ("base-video", "composite"):
                raise ValueError("video-filter target must be base-video or composite")
            chain, cwd = _grade_filter(contribution, project_root, plan_dir)
            target = contribution.get("target")
            (base_filters if target == "base-video" else composite_filters).append(chain)
            if cwd:
                if lut_cwd and lut_cwd != cwd:
                    raise ValueError("delivery cannot use LUTs from multiple folders")
                lut_cwd = cwd
        elif kind == "overlay":
            start_s = float(contribution.get("start_s", 0))
            duration_s = contribution.get("duration_s")
            start_frame = round(start_s * fps["num"] / fps["den"])
            end_frame = None
            if duration_s is not None:
                end_frame = round(
                    (start_s + float(duration_s)) * fps["num"] / fps["den"]
                )
            overlays.append(
                {
                    "path": _resolve(project_root, plan_dir, contribution["asset"]),
                    "asset_type": contribution.get("asset_type", "file"),
                    "pattern": contribution.get("pattern"),
                    "start_number": contribution.get("start_number", 1),
                    "fps": contribution.get("fps"),
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                }
            )
        elif kind == "audio-filter":
            chain = contribution.get("filter")
            if not chain and contribution.get("plan"):
                chain = _load(_resolve(project_root, plan_dir, contribution["plan"])).get("filter")
            if not chain:
                raise ValueError("audio-filter contribution requires filter or plan")
            audio_filters.append(chain)
        elif kind == "precomputed-asset":
            if contribution.get("target") != "overlay":
                raise ValueError("precomputed-asset currently requires target=overlay")
            start_s = float(contribution.get("start_s", 0))
            duration_s = contribution.get("duration_s")
            start_frame = round(start_s * fps["num"] / fps["den"])
            end_frame = None
            if duration_s is not None:
                end_frame = round(
                    (start_s + float(duration_s)) * fps["num"] / fps["den"]
                )
            overlays.append(
                {
                    "path": _resolve(project_root, plan_dir, contribution["asset"]),
                    "asset_type": "file",
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                }
            )
        elif kind == "output-constraint":
            constraints.update({key: value for key, value in contribution.items() if key not in ("kind", "operation")})
        elif kind not in ("timeline-transform",):
            raise ValueError(f"unsupported render contribution: {kind!r}")

    for chain in base_filters:
        output_label = f"video-{len(graph)}"
        graph.append(f"[{video_label}]{chain}[{output_label}]")
        video_label = output_label

    for overlay_index, overlay_spec in enumerate(overlays):
        overlay = overlay_spec["path"]
        if overlay_spec["asset_type"] == "image-sequence":
            pattern = overlay_spec["pattern"]
            if not overlay.is_dir() or not pattern or Path(pattern).name != pattern:
                raise ValueError(f"image-sequence overlay is invalid: {overlay}")
            pattern_path = (overlay / pattern).resolve()
            if pattern_path.parent != overlay.resolve():
                raise ValueError(f"image-sequence pattern escapes overlay directory: {pattern}")
            start_number = overlay_spec["start_number"]
            try:
                first_frame = overlay / (pattern % start_number)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"image-sequence pattern is invalid: {pattern}") from exc
            if not first_frame.is_file():
                raise ValueError(f"image-sequence first frame is missing: {first_frame}")
            fps_value = overlay_spec["fps"]
            if not isinstance(fps_value, dict) or fps_value != timeline["fps"]:
                raise ValueError("image-sequence overlay fps must match timeline fps")
            command += [
                "-framerate", f"{fps_value['num']}/{fps_value['den']}",
                "-start_number", str(start_number), "-i", str(pattern_path),
            ]
        else:
            if not overlay.is_file():
                raise ValueError(f"overlay is missing: {overlay}")
            command += ["-i", str(overlay)]
        overlay_label = f"overlay-{overlay_index}"
        output_label = f"video-{len(graph)}"
        start_frame = overlay_spec["start_frame"]
        end_frame = overlay_spec["end_frame"]
        duration_filter = ""
        if end_frame is not None:
            duration_filter = f"trim=end_frame={end_frame - start_frame},"
        graph.append(
            f"[{next_input}:v:0]{duration_filter}setpts=PTS-STARTPTS+"
            f"({start_frame}*{fps['den']}/{fps['num']})/TB[{overlay_label}]"
        )
        enable = ""
        if end_frame is not None:
            enable = f":enable='between(n,{start_frame},{end_frame - 1})'"
        graph.append(
            f"[{video_label}][{overlay_label}]overlay=eof_action=pass:shortest=0:format=auto"
            f"{enable}[{output_label}]"
        )
        video_label = output_label
        next_input += 1

    for chain in composite_filters:
        output_label = f"video-{len(graph)}"
        graph.append(f"[{video_label}]{chain}[{output_label}]")
        video_label = output_label

    if constraints.get("width") or constraints.get("height") or constraints.get("fps"):
        filters = []
        if constraints.get("width") or constraints.get("height"):
            filters.append(f"scale={constraints.get('width', -2)}:{constraints.get('height', -2)}")
        if constraints.get("fps"):
            filters.append(f"fps={constraints['fps']}")
        output_label = f"video-{len(graph)}"
        graph.append(f"[{video_label}]{','.join(filters)}[{output_label}]")
        video_label = output_label

    if audio_filters:
        audio_filtered = True
        source_audio = f"[{audio_label}]" if audio_label else "[0:a:0]"
        graph.append(f"{source_audio}{','.join(audio_filters)}[filtered-audio]")
        audio_label = "filtered-audio"

    output_label = f"video-{len(graph)}"
    graph.append(
        f"[{video_label}]tpad=stop_mode=clone:stop_duration="
        f"{float(timeline['program_duration_s']):.6f}[{output_label}]"
    )
    video_label = output_label

    command += ["-filter_complex", ";".join(graph), "-map", f"[{video_label}]"]
    if audio_filtered:
        command += ["-map", f"[{audio_label}]", "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    else:
        command += ["-map", "0:a:0?", "-c:a", "copy"]

    output = _resolve(project_root, plan_dir, plan["output"])
    command += [
        "-c:v", constraints.get("video_codec", "libx264"),
        "-preset", constraints.get("preset", "veryfast"),
        "-crf", str(constraints.get("crf", 20)),
        "-pix_fmt", constraints.get("pix_fmt", "yuv420p"),
        "-movflags", "+faststart",
        "-t", f"{float(timeline['program_duration_s']):.6f}", str(output),
    ]
    return command, lut_cwd, output


def build_command(plan, project_root, plan_dir=None):
    plan_dir = plan_dir or Path(project_root) / "work" / "render"
    return _build(plan, project_root, plan_dir)[0]


def render(plan, project_root, plan_dir=None):
    plan_dir = plan_dir or Path(project_root) / "work" / "render"
    command, cwd, output = _build(plan, project_root, plan_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, cwd=cwd, check=True)
    timeline = _load(_resolve(project_root, plan_dir, plan["timeline"]))
    source = _resolve(project_root, plan_dir, plan["source"])
    _verify_delivery(output, timeline, source)
    return output


def _probe_delivery(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,width,height,duration:format=duration", "-of", "json",
            str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def _verify_delivery(output, timeline, source=None):
    info = _probe_delivery(output)
    fps = timeline["fps"]
    tolerance = fps["den"] / fps["num"]
    actual = float(info["format"]["duration"])
    expected = float(timeline["program_duration_s"])
    if abs(actual - expected) > tolerance:
        raise ValueError(
            f"delivery duration mismatch: expected {expected:.6f}, actual {actual:.6f}"
        )
    streams = {stream.get("codec_type"): stream for stream in info.get("streams", [])}
    if "video" not in streams:
        raise ValueError("delivery video stream is missing")
    if source is not None:
        source_info = _probe_delivery(source)
        source_streams = {
            stream.get("codec_type"): stream for stream in source_info.get("streams", [])
        }
        source_video = source_streams.get("video", {})
        output_video = streams["video"]
        if (
            output_video.get("width"), output_video.get("height")
        ) != (
            source_video.get("width"), source_video.get("height")
        ):
            raise ValueError("delivery dimensions do not match source")
        if "audio" in source_streams and "audio" not in streams:
            raise ValueError("delivery audio stream is missing")
    if "audio" in streams:
        video_duration = float(streams["video"].get("duration") or actual)
        audio_duration = float(streams["audio"].get("duration") or actual)
        if abs(video_duration - audio_duration) > tolerance:
            raise ValueError("delivery audio and video durations differ by more than one frame")
    return info


def _write_delivery_report(output, project_root):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,width,height,duration:format=duration", "-of", "json", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    streams = {stream["codec_type"]: stream for stream in info.get("streams", [])}
    video = streams.get("video", {})
    relative = Path(os.path.relpath(output, project_root)).as_posix()
    report = Path(project_root) / "final/delivery-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Delivery report",
                "",
                f"- Final video: `{relative}`",
                f"- Duration: {float(info['format']['duration']):.3f} seconds",
                f"- Frame size: {video.get('width', 'unknown')} x {video.get('height', 'unknown')}",
                f"- Audio stream: {'present' if 'audio' in streams else 'missing'}",
                "- Delivery render: verified",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("render_plan")
    args = parser.parse_args(argv)
    plan_path = Path(args.render_plan).resolve()
    project_root = plan_path.parent.parent.parent
    output = render(_load(plan_path), project_root, plan_path.parent)
    _write_delivery_report(output, project_root)
    project_path = project_root / "work/project.json"
    if project_path.is_file():
        project = projectlib.load_json(project_path)
        project["render"]["status"] = "verified"
        projectlib.write_json(project_path, project)
        projectlib.write_start_here(project, project_root)
    print(f"[render] DONE -> {output}")


if __name__ == "__main__":
    main()
