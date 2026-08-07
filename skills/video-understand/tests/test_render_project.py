import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import render_project


def _color_video(path, color, frames):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        f"color=c={color}:s=64x64:r=60:d=1",
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


if __name__ == "__main__":
    unittest.main()
