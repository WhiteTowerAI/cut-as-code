"""Render original versus actual final pixels on the original source clock."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


def source_time_parts(timeline):
    errors = projectlib.validate_timeline(timeline)
    if errors:
        raise ValueError("unsupported source-time mapping: " + "; ".join(errors))

    parts = []
    cursor = 0.0
    for clip in timeline["clips"]:
        source_range = clip["source_range"]
        if source_range["start_s"] > cursor + 1e-6:
            parts.append(
                {
                    "kind": "black",
                    "source_range": {"start_s": cursor, "end_s": source_range["start_s"]},
                    "duration_s": round(source_range["start_s"] - cursor, 6),
                }
            )
        parts.append(
            {
                "kind": "final",
                "source_range": dict(source_range),
                "program_range": dict(clip["program_range"]),
                "speed": float(clip["speed"]),
                "duration_s": round(source_range["end_s"] - source_range["start_s"], 6),
            }
        )
        cursor = source_range["end_s"]
    duration = float(timeline["source_duration_s"])
    if duration > cursor + 1e-6:
        parts.append(
            {
                "kind": "black",
                "source_range": {"start_s": cursor, "end_s": duration},
                "duration_s": round(duration - cursor, 6),
            }
        )
    fps = timeline["fps"]
    for part in parts:
        source_range = part["source_range"]
        part["start_frame"] = round(source_range["start_s"] * fps["num"] / fps["den"])
        part["end_frame"] = round(source_range["end_s"] * fps["num"] / fps["den"])
        part["frame_count"] = part["end_frame"] - part["start_frame"]
    return parts


def _probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_s": float(data["format"]["duration"]),
    }


def _audio_hash(path):
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
            "-map", "0:a:0", "-c", "copy", "-f", "hash", "-hash", "md5", "-",
        ],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _crop_bytes(path, at_s, x, y, size):
    sample_size = min(16, size)
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{at_s:.6f}",
            "-i", str(path), "-vf",
            f"crop={size}:{size}:{x}:{y},scale={sample_size}:{sample_size}:flags=area",
            "-frames:v", "1",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
        ],
        check=True, capture_output=True,
    )
    return result.stdout


def verify_output(timeline, source, final, output):
    source_info = _probe(source)
    output_info = _probe(output)
    fps = timeline["fps"]
    tolerance = fps["den"] / fps["num"]
    expected = float(timeline["source_duration_s"])
    if abs(output_info["duration_s"] - expected) > tolerance:
        raise ValueError("comparison duration does not match source timeline")
    if output_info["width"] != source_info["width"] * 2:
        raise ValueError("comparison width is not twice the source width")
    if output_info["height"] != source_info["height"]:
        raise ValueError("comparison height does not match source height")
    source_audio = _audio_hash(source)
    if source_audio and _audio_hash(output) != source_audio:
        raise ValueError("comparison audio does not match original source audio")

    size = min(48, source_info["width"] // 4, source_info["height"] // 4)
    x = (source_info["width"] - size) // 2
    bottom_margin = max(4, source_info["height"] // 20)
    y = max(0, source_info["height"] - size - bottom_margin)
    for part in source_time_parts(timeline):
        source_range = part["source_range"]
        source_s = (source_range["start_s"] + source_range["end_s"]) / 2
        projected = _crop_bytes(
            output, source_s, source_info["width"] + x, y, size
        )
        if part["kind"] == "black":
            if max(projected, default=0) > 20:
                raise ValueError("comparison dropped range is not black")
            continue
        program = part["program_range"]
        program_s = (program["start_s"] + program["end_s"]) / 2
        expected_frames = [
            _crop_bytes(final, max(0.0, program_s + offset), x, y, size)
            for offset in (-tolerance, 0.0, tolerance)
        ]
        if not projected or any(len(projected) != len(frame) for frame in expected_frames):
            raise ValueError("comparison frame sample is missing")
        error = min(
            sum(abs(a - b) for a, b in zip(projected, frame)) / len(projected)
            for frame in expected_frames
        )
        if error > 16:
            raise ValueError(
                "comparison kept frame mismatch: "
                f"source={source_s:.6f}s program={program_s:.6f}s mean error {error:.2f}"
            )


def write_compare_plan(timeline_path, source, final, output):
    work_dir = Path(timeline_path).resolve().parent
    plan_path = work_dir / "edit-compare/compare-plan.json"
    plan_dir = plan_path.parent
    relative = lambda value: Path(os.path.relpath(Path(value).resolve(), plan_dir)).as_posix()
    projectlib.write_json(
        plan_path,
        {
            "schema_version": 1,
            "mode": "original-vs-final-source-time",
            "source": relative(source),
            "final": relative(final),
            "timeline": relative(timeline_path),
            "output": relative(output),
        },
    )
    return plan_path


def register_review(project_root, output):
    project_path = Path(project_root) / "work/project.json"
    if not project_path.is_file():
        return
    project = projectlib.load_json(project_path)
    operations = projectlib.operation_map(project)
    active_ids = project["sequences"][project["active_sequence"]].get("operations", [])
    review = {
        "id": "original-vs-final-source-time",
        "skill": "video-edit-compare",
        "revision": 1,
        "depends_on": [*active_ids, "render"],
        "based_on": {
            operation_id: operations[operation_id]["revision"] for operation_id in active_ids
        },
        "status": "verified",
        "plan": "edit-compare/compare-plan.json",
        "output": Path(os.path.relpath(Path(output).resolve(), Path(project_root) / "work")).as_posix(),
    }
    reviews = project.setdefault("reviews", [])
    for index, existing in enumerate(reviews):
        if existing.get("id") == review["id"]:
            review["revision"] = existing.get("revision", 1)
            reviews[index] = review
            break
    else:
        reviews.append(review)
    projectlib.write_json(project_path, project)
    projectlib.write_start_here(project, project_root)


def _label(path, text, panel_width):
    path.parent.mkdir(parents=True, exist_ok=True)
    width = min(140, max(80, panel_width - 20))
    image = Image.new("RGBA", (width, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, 31), fill=(0, 0, 0, 170))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw.text((9, 7), text, font=font, fill=(255, 255, 255, 255))
    image.save(path)


def build_command(timeline, source, final, output, filtergraph_path, label_dir):
    parts = source_time_parts(timeline)
    source = Path(source).resolve()
    final = Path(final).resolve()
    output = Path(output).resolve()
    fps = timeline["fps"]
    fps_text = f"{fps['num']}/{fps['den']}"
    frame_pts = f"N*{fps['den']}/({fps['num']}*TB)"
    frame_tolerance = fps["den"] / fps["num"]
    source_info = _probe(source)
    final_info = _probe(final)
    if abs(source_info["duration_s"] - float(timeline["source_duration_s"])) > frame_tolerance:
        raise ValueError("source duration does not match timeline")
    if final_info["duration_s"] + frame_tolerance < float(timeline["program_duration_s"]):
        raise ValueError("final duration is shorter than timeline program duration")
    width, height = source_info["width"], source_info["height"]

    original_label = Path(label_dir) / "original.png"
    final_label = Path(label_dir) / "final-source-time.png"
    _label(original_label, "ORIGINAL", width)
    _label(final_label, "FINAL", width)

    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)]
    input_index = 1
    final_indices = []
    for part in parts:
        if part["kind"] != "final":
            final_indices.append(None)
            continue
        program = part["program_range"]
        duration = program["end_s"] - program["start_s"]
        command += [
            "-ss", f"{program['start_s']:.6f}", "-t", f"{duration:.6f}",
            "-i", str(final),
        ]
        final_indices.append(input_index)
        input_index += 1

    original_label_index = input_index
    command += ["-loop", "1", "-framerate", fps_text, "-i", str(original_label)]
    final_label_index = input_index + 1
    command += ["-loop", "1", "-framerate", fps_text, "-i", str(final_label)]

    graph = [
        f"[0:v:0]fps={fps_text},scale={width}:{height},setsar=1,setpts=PTS-STARTPTS[left-base]"
    ]
    right_labels = []
    for index, (part, final_index) in enumerate(zip(parts, final_indices)):
        label = f"right-{index}"
        if part["kind"] == "black":
            color_duration = (part["frame_count"] + 1) * fps["den"] / fps["num"]
            graph.append(
                f"color=c=black:s={width}x{height}:r={fps_text}:d={color_duration:.9f},"
                f"format=yuv420p,trim=end_frame={part['frame_count']},"
                f"settb=AVTB,setpts={frame_pts}[{label}]"
            )
        else:
            graph.append(
                f"[{final_index}:v:0]setpts=(PTS-STARTPTS)*{part['speed']:.8f},"
                f"fps={fps_text},scale={width}:{height},setsar=1,format=yuv420p,"
                f"trim=end_frame={part['frame_count']},settb=AVTB,setpts={frame_pts}[{label}]"
            )
        right_labels.append(f"[{label}]")
    if len(right_labels) == 1:
        graph.append(f"{right_labels[0]}null[right-base]")
    else:
        graph.append("".join(right_labels) + f"concat=n={len(right_labels)}:v=1:a=0[right-base]")

    graph += [
        f"[{original_label_index}:v:0]format=rgba[original-label]",
        f"[{final_label_index}:v:0]format=rgba[final-label]",
        "[left-base][original-label]overlay=x=10:y=10:eof_action=repeat:shortest=0[left]",
        "[right-base][final-label]overlay=x=10:y=10:eof_action=repeat:shortest=0[right]",
        "[left][right]hstack=inputs=2[compare-video]",
    ]
    filtergraph = ";".join(graph)
    filtergraph_path = Path(filtergraph_path)
    filtergraph_path.parent.mkdir(parents=True, exist_ok=True)
    filtergraph_path.write_text(filtergraph + "\n", encoding="utf-8")

    command += [
        "-filter_complex", filtergraph,
        "-map", "[compare-video]", "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        "-t", f"{timeline['source_duration_s']:.6f}", str(output),
    ]
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline")
    parser.add_argument("source")
    parser.add_argument("final")
    parser.add_argument("output")
    parser.add_argument("--filter-only", action="store_true")
    args = parser.parse_args(argv)

    timeline_path = Path(args.timeline).resolve()
    timeline = projectlib.load_json(timeline_path)
    project_root = timeline_path.parent.parent
    cache = timeline_path.parent / "cache"
    write_compare_plan(timeline_path, args.source, args.final, args.output)
    command = build_command(
        timeline,
        args.source,
        args.final,
        args.output,
        cache / "filtergraphs/original-vs-final-source-time.txt",
        cache / "compare-labels",
    )
    if args.filter_only:
        return
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    output = Path(args.output).resolve()
    verify_output(timeline, args.source, args.final, output)
    parts = source_time_parts(timeline)
    (output.parent / "comparison-summary.md").write_text(
        "\n".join(
            [
                "# Edit comparison",
                "",
                "- Mode: `original-vs-final-source-time`",
                f"- Source duration: {timeline['source_duration_s']:.3f} seconds",
                f"- Kept projections: {sum(part['kind'] == 'final' for part in parts)}",
                f"- Black dropped ranges: {sum(part['kind'] == 'black' for part in parts)}",
                "- Audio: original source-time track",
                "- Verification: pass",
                f"- Video: `{output.name}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    register_review(project_root, output)
    print(f"[compare] DONE -> {output}")


if __name__ == "__main__":
    main()
