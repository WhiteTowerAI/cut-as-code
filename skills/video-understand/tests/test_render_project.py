import json
import re
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


def _tone_video(path):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=1",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=1",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
    ], check=True)


def _mean_volume(path):
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-",
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", result.stderr)
    if not match:
        raise AssertionError(f"mean volume was not reported: {result.stderr}")
    return float(match.group(1))


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
    def test_detached_audio_renders_once_without_embedded_audio_doubling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            render_dir = root / "work" / "render"
            render_dir.mkdir(parents=True)
            (root / "final").mkdir()
            source = root / "source.mp4"
            output = root / "final" / "output.mp4"
            _tone_video(source)
            timeline = {
                "schema_version": 1,
                "timeline_id": "source",
                "source_asset_id": "source",
                "fps": {"num": 30, "den": 1},
                "source_duration_s": 1.0,
                "program_duration_s": 1.0,
                "clips": [{
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 1.0},
                    "program_range": {"start_s": 0.0, "end_s": 1.0},
                    "speed": 1.0,
                    "audio_mode": "detached",
                }],
                "audio_clips": [{
                    "id": "clip-001:audio",
                    "source_range": {"start_s": 0.0, "end_s": 1.0},
                    "program_range": {"start_s": 0.0, "end_s": 1.0},
                    "speed": 1.0,
                    "source_video_clip_id": "clip-001",
                    "linked": True,
                    "muted": False,
                }],
            }
            (root / "work" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
            plan = {
                "schema_version": 1,
                "sequence": "main",
                "source": "../../source.mp4",
                "timeline": "../timeline.json",
                "contributions": [],
                "output": "../../final/output.mp4",
            }

            command = render_project.build_command(plan, root)
            graph = command[command.index("-filter_complex") + 1]
            self.assertEqual(2, graph.count("[timeline-audio-0]"))
            self.assertNotIn("timeline-audio-1", graph)
            self.assertNotIn("amix=", graph)
            render_project.render(plan, root)
            self.assertTrue(output.is_file())
            self.assertLess(abs(_mean_volume(output) - _mean_volume(source)), 1.5)

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
                    "operation": "motion-graphics",
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
