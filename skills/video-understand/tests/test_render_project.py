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
    def test_overlay_editor_transform_scales_and_positions_from_normalized_center(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            render_dir = root / "work" / "render"
            render_dir.mkdir(parents=True)
            (root / "final").mkdir()
            _color_video(root / "source.mp4", "black", 60)
            _color_video(root / "overlay.mp4", "red", 10)
            timeline = {
                "schema_version": 1,
                "timeline_id": "source",
                "source_asset_id": "source",
                "fps": {"num": 60, "den": 1},
                "source_duration_s": 1.0,
                "program_duration_s": 1.0,
                "clips": [{
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 1.0},
                    "program_range": {"start_s": 0.0, "end_s": 1.0},
                    "speed": 1.0,
                }],
            }
            (root / "work" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
            plan = {
                "schema_version": 1,
                "sequence": "main",
                "source": "../../source.mp4",
                "timeline": "../timeline.json",
                "contributions": [{
                    "operation": "graphic-motion",
                    "kind": "overlay",
                    "asset": "../../overlay.mp4",
                    "start_s": 0,
                    "duration_s": 0.5,
                    "editor_transform": {"x": 0.25, "y": 0.75, "scale": 0.5},
                }],
                "output": "../../final/output.mp4",
            }

            command = render_project.build_command(plan, root)
            graph = command[command.index("-filter_complex") + 1]

            self.assertIn("scale=iw*0.5:ih*0.5", graph)
            self.assertIn("overlay=x='main_w*0.25-overlay_w/2':y='main_h*0.75-overlay_h/2'", graph)

    def test_default_editor_transform_preserves_the_existing_overlay_graph(self):
        overlay = {"x": 0.5, "y": 0.5, "scale": 1.0}
        self.assertEqual((None, None), render_project._overlay_transform_filters(overlay))

    def test_graphic_motion_crops_visible_bounds_before_nonuniform_scaling(self):
        transform = {"x": 0.6, "y": 0.4, "scale_x": 1.5, "scale_y": 0.75}
        bounds = {"x": 0.1, "y": 0.2, "width": 0.25, "height": 0.3}

        filters, position = render_project._overlay_transform_filters(transform, bounds)

        self.assertEqual(
            "crop=iw*0.25:ih*0.3:iw*0.1:ih*0.2,scale=iw*1.5:ih*0.75",
            filters,
        )
        self.assertEqual(
            "x='main_w*0.6+(0.1-0.5)*main_w*1.5':"
            "y='main_h*0.4+(0.2-0.5)*main_h*0.75'",
            position,
        )

    def test_cropped_overlay_accepts_corner_position_outside_unit_center_range(self):
        filters, position = render_project._overlay_transform_filters(
            {"x": 1.15, "y": 1.0, "scale_x": 1.0, "scale_y": 1.0},
            {"x": 0.1, "y": 0.2, "width": 0.25, "height": 0.3},
        )

        self.assertEqual("crop=iw*0.25:ih*0.3:iw*0.1:ih*0.2", filters)
        self.assertIn("x='main_w*1.15+(0.1-0.5)*main_w*1'", position)

    def test_default_content_bound_transform_preserves_original_visible_position(self):
        transform = {"x": 0.5, "y": 0.5, "scale_x": 1.0, "scale_y": 1.0}
        bounds = {"x": 0.1, "y": 0.2, "width": 0.25, "height": 0.3}

        self.assertEqual(
            (
                "crop=iw*0.25:ih*0.3:iw*0.1:ih*0.2",
                "x='main_w*0.5+(0.1-0.5)*main_w*1':"
                "y='main_h*0.5+(0.2-0.5)*main_h*1'",
            ),
            render_project._overlay_transform_filters(transform, bounds),
        )

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
