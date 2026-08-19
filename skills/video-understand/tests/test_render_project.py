import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import render_project


def _color_video(path, color, frames, fps=60):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        f"color=c={color}:s=64x64:r={fps}:d=1",
        "-vf", f"trim=end_frame={frames},setpts=PTS-STARTPTS",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ], check=True)


def _frame_pixel(path, frame):
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-vf",
        f"select=eq(n\\,{frame})", "-vsync", "0", "-frames:v", "1",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
    ], check=True, capture_output=True)
    center = ((64 * 32) + 32) * 3
    return tuple(result.stdout[center:center + 3])


def _segmented_av(path):
    command = ["ffmpeg", "-y", "-v", "error"]
    for color, frequency in (("red", 440), ("green", 880), ("blue", 1320)):
        command += [
            "-f", "lavfi", "-i", f"color=c={color}:s=64x64:r=10:d=1",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000:duration=1",
        ]
    command += [
        "-filter_complex",
        "[0:v][2:v][4:v]concat=n=3:v=1:a=0[v];"
        "[1:a][3:a][5:a]concat=n=3:v=0:a=1[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", str(path),
    ]
    subprocess.run(command, check=True)


def _audio_samples(path, start_s, duration_s=0.25):
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", str(start_s), "-t", str(duration_s),
        "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "48000",
        "-f", "s16le", "-",
    ], check=True, capture_output=True)
    return struct.unpack(f"<{len(result.stdout) // 2}h", result.stdout)


def _frequency_hz(samples, duration_s=0.25):
    crossings = sum(
        1 for left, right in zip(samples, samples[1:])
        if (left < 0 <= right) or (left >= 0 > right)
    )
    return crossings / (2 * duration_s)


class OverlayFrameBoundaryTests(unittest.TestCase):
    def test_overlay_uses_exact_first_and_last_frame_on_rational_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            render_dir = root / "work" / "render"
            render_dir.mkdir(parents=True)
            (root / "final").mkdir()
            _color_video(root / "source.mp4", "black", 120)
            _color_video(root / "red.mp4", "red", 4)
            _color_video(root / "blue.mp4", "blue", 4)
            timeline = {
                "schema_version": 1,
                "timeline_id": "source",
                "source_asset_id": "source",
                "fps": {"num": 60, "den": 1},
                "source_duration_s": 2.0,
                "program_duration_s": 2.0,
                "clips": [{
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 0.0, "end_s": 2.0},
                    "speed": 1.0,
                    "decision_ref": "source",
                }],
            }
            (root / "work" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
            plan = {
                "schema_version": 1,
                "sequence": "main",
                "source": "../../source.mp4",
                "timeline": "../timeline.json",
                "contributions": [
                    {
                        "operation": "test",
                        "kind": "overlay",
                        "asset": "../../red.mp4",
                        "start_s": 1 / 60,
                        "duration_s": 4 / 60,
                    },
                    {
                        "operation": "test",
                        "kind": "overlay",
                        "asset": "../../blue.mp4",
                        "start_s": 17 / 60,
                        "duration_s": 4 / 60,
                    },
                ],
                "output": "../../final/output.mp4",
            }

            output = render_project.render(plan, root)

            self.assertLess(max(_frame_pixel(output, 0)), 10)
            self.assertGreater(_frame_pixel(output, 1)[0], 220)
            self.assertGreater(_frame_pixel(output, 4)[0], 220)
            self.assertLess(max(_frame_pixel(output, 5)), 10)
            self.assertGreater(_frame_pixel(output, 17)[2], 220)
            self.assertGreater(_frame_pixel(output, 20)[2], 220)
            self.assertLess(max(_frame_pixel(output, 21)), 10)


class TimelineInsertTests(unittest.TestCase):
    def test_full_frame_insert_pauses_and_resumes_source_video_and_audio(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            render_dir = root / "work" / "render"
            render_dir.mkdir(parents=True)
            (root / "final").mkdir()
            _segmented_av(root / "source.mp4")
            _color_video(root / "yellow.mp4", "yellow", 10, fps=10)
            timeline = {
                "schema_version": 1,
                "timeline_id": "source",
                "source_asset_id": "source",
                "fps": {"num": 10, "den": 1},
                "source_duration_s": 3.0,
                "program_duration_s": 3.0,
                "clips": [{
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 3.0},
                    "program_range": {"start_s": 0.0, "end_s": 3.0},
                    "speed": 1.0,
                    "decision_ref": "source",
                }],
            }
            (root / "work" / "timeline.json").write_text(
                json.dumps(timeline), encoding="utf-8",
            )
            plan = {
                "schema_version": 1,
                "sequence": "main",
                "source": "../../source.mp4",
                "timeline": "../timeline.json",
                "contributions": [{
                    "operation": "motion-graphics",
                    "kind": "timeline-insert",
                    "asset": "../../yellow.mp4",
                    "asset_type": "file",
                    "anchor_s": 1.0,
                    "duration_s": 1.0,
                    "audio": {"mode": "silence"},
                }],
                "output": "../../final/output.mp4",
            }

            output = render_project.render(plan, root)

            info = render_project._probe_delivery(output)
            self.assertAlmostEqual(4.0, float(info["format"]["duration"]), delta=0.1)
            self.assertGreater(_frame_pixel(output, 5)[0], 220)
            yellow = _frame_pixel(output, 12)
            self.assertGreater(yellow[0], 220)
            self.assertGreater(yellow[1], 220)
            resumed_green = _frame_pixel(output, 22)
            self.assertGreater(resumed_green[1], 90)
            self.assertLess(resumed_green[0], 20)
            self.assertGreater(_frame_pixel(output, 32)[2], 220)

            self.assertAlmostEqual(440, _frequency_hz(_audio_samples(output, 0.5)), delta=80)
            self.assertLess(max(abs(value) for value in _audio_samples(output, 1.5)), 300)
            self.assertAlmostEqual(880, _frequency_hz(_audio_samples(output, 2.5)), delta=100)
            self.assertAlmostEqual(1320, _frequency_hz(_audio_samples(output, 3.5)), delta=120)


if __name__ == "__main__":
    unittest.main()
