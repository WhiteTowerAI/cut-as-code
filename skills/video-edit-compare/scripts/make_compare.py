"""Render original versus actual final pixels on the original source clock."""

import argparse
import json
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
            graph.append(
                f"color=c=black:s={width}x{height}:r={fps_text}:d={part['duration_s']:.6f},"
                f"format=yuv420p,settb=AVTB[{label}]"
            )
        else:
            graph.append(
                f"[{final_index}:v:0]setpts=(PTS-STARTPTS)*{part['speed']:.8f},"
                f"fps={fps_text},scale={width}:{height},setsar=1,format=yuv420p,settb=AVTB[{label}]"
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
    cache = timeline_path.parent / "cache"
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
                f"- Video: `{output.name}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[compare] DONE -> {output}")


if __name__ == "__main__":
    main()
