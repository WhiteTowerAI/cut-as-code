#!/usr/bin/env python3
"""Check project-protocol precision retained by the cut compiler."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def check_source_duration_precision():
    source_duration = 10.033367
    transcript = {
        "duration": source_duration,
        "segments": [
            {
                "id": 1,
                "start": 1.0,
                "end": 2.0,
                "text": " Exact duration.",
                "words": [
                    {"word": " Exact", "start": 1.0, "end": 1.4},
                    {"word": " duration.", "start": 1.5, "end": 2.0},
                ],
            }
        ],
    }
    coarse = {
        "schema_version": 1,
        "source": "../input/original-video.mp4",
        "decisions": [
            {
                "id": "edit-001",
                "action": "keep",
                "start_s": 0.0,
                "end_s": source_duration,
                "reason": "Fixture",
                "evidence_refs": ["segment:1"],
            }
        ],
    }

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        coarse_path = temp_dir / "edit-plan.json"
        transcript_path = temp_dir / "transcript.json"
        output_path = temp_dir / "edit-final.json"
        write_json(coarse_path, coarse)
        write_json(transcript_path, transcript)

        subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "build_edit.py"),
                str(coarse_path),
                str(transcript_path),
                str(output_path),
                "1.5",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["source_duration_s"] == source_duration, (
        "cut compiler rounded source duration: "
        f"expected {source_duration}, got {result['source_duration_s']}"
    )


def main():
    check_source_duration_precision()
    print("cut project protocol checks passed")


if __name__ == "__main__":
    main()
