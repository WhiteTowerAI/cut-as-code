"""Probe a source video and write canonical media.json metadata."""

import argparse
import json
import subprocess
from pathlib import Path

from projectlib import quick_fingerprint, write_json


def parse_rate(value):
    try:
        num, den = (int(part) for part in value.split("/", 1))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid frame rate: {value!r}") from exc
    if num <= 0 or den <= 0:
        raise ValueError(f"invalid frame rate: {value!r}")
    return {"num": num, "den": den}


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,format_name,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,pix_fmt,sample_rate,channels,color_range,color_space,color_transfer,color_primaries",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(result.stdout)
    duration = float(raw["format"]["duration"])
    video = next((stream for stream in raw.get("streams", []) if stream.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("source has no video stream")
    rate = video.get("avg_frame_rate") or video.get("r_frame_rate")
    media = {
        "schema_version": 1,
        "source": str(Path(path)),
        "duration_s": round(duration, 6),
        "fps": parse_rate(rate),
        "width": video.get("width"),
        "height": video.get("height"),
        "format": raw.get("format", {}),
        "streams": raw.get("streams", []),
        "color": {
            key: video.get(key)
            for key in ("color_range", "color_space", "color_transfer", "color_primaries")
            if video.get(key)
        },
        "fingerprint": quick_fingerprint(path, duration),
    }
    return media


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    write_json(args.output, probe(args.source))


if __name__ == "__main__":
    main()
