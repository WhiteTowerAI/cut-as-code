"""Regression coverage for editor-only stale project snapshots."""

import copy
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from PIL import Image


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import projectlib  # noqa: E402


class EditorProtocolFreshnessTests(unittest.TestCase):
    def test_validate_timeline_accepts_only_zero_duration_when_clips_are_empty(self):
        timeline = {
            "schema_version": 1,
            "timeline_id": "main",
            "source_asset_id": "source",
            "fps": {"num": 30000, "den": 1001},
            "source_duration_s": 10.0,
            "program_duration_s": 0.0,
            "clips": [],
        }

        self.assertEqual([], projectlib.validate_timeline(timeline))
        timeline["program_duration_s"] = 0.01
        self.assertIn(
            "an empty timeline must have zero program duration",
            projectlib.validate_timeline(timeline),
        )

    def test_build_render_plan_expands_caption_cues_into_independent_layers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work/render").mkdir(parents=True)
            (root / "work/captions/overlay-frames").mkdir(parents=True)
            (root / "work/review").mkdir()
            (root / "source.mp4").write_bytes(b"source")
            for name in ("frame_000007.png", "frame_000031.png"):
                (root / "work/captions/overlay-frames" / name).write_bytes(b"frame")
            for index in range(1, 5):
                (root / "work/review" / f"caption-{index}.png").write_bytes(b"evidence")

            timeline = {
                "schema_version": 1,
                "timeline_id": "main",
                "source_asset_id": "source",
                "fps": {"num": 30, "den": 1},
                "source_duration_s": 2.0,
                "program_duration_s": 2.0,
                "clips": [{
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 0.0, "end_s": 2.0},
                    "speed": 1.0,
                    "decision_ref": "keep",
                }],
            }
            (root / "work/timeline.json").write_text(json.dumps(timeline), encoding="utf-8")

            caption_plan = {
                "schema_version": 1,
                "target": "overlay",
                "timebase": "program",
                "timeline_id": "main",
                "source_transcript": "work/transcript.json",
                "program_duration_s": 2.0,
                "style": {
                    "status": "approved",
                    "selection_mode": "agent",
                    "selection_rationale": "test",
                    "choice_id": "preset-1",
                    "preset": "clean",
                    "resolved": {"font": "sans"},
                },
                "review": {
                    "status": "approved",
                    "evidence": [f"review/caption-{index}.png" for index in range(1, 5)],
                },
                "cues": [
                    {
                        "id": "caption-1",
                        "start": 0.2,
                        "end": 0.8,
                        "program_range": {"start_s": 0.2, "end_s": 0.8},
                        "editor_transform": {"x": 0.5, "y": 0.8, "scale": 1.0},
                        "editor_content_bounds": {"x": 0.2, "y": 0.7, "width": 0.6, "height": 0.2},
                        "words": [{
                            "clip_id": "clip-001",
                            "source_range": {"start_s": 0.2, "end_s": 0.8},
                            "program_range": {"start_s": 0.2, "end_s": 0.8},
                        }],
                    },
                    {
                        "id": "caption-2",
                        "start": 1.0,
                        "end": 1.5,
                        "program_range": {"start_s": 1.0, "end_s": 1.5},
                        "editor_transform": {"x": 0.5, "y": 0.6, "scale": 1.2},
                        "editor_content_bounds": {"x": 0.1, "y": 0.6, "width": 0.8, "height": 0.25},
                        "words": [{
                            "clip_id": "clip-001",
                            "source_range": {"start_s": 1.0, "end_s": 1.5},
                            "program_range": {"start_s": 1.0, "end_s": 1.5},
                        }],
                    },
                ],
                "renderer_recipe": {
                    "engine": "hyperframes",
                    "asset_type": "image-sequence",
                "asset": "captions/overlay-frames",
                    "fps": {"num": 30, "den": 1},
                    "runtime_assets": [{"path": "runtime.js", "sha256": "0" * 64}],
                },
            }
            (root / "work/captions/captions-plan.json").write_text(
                json.dumps(caption_plan), encoding="utf-8"
            )

            project = {
                "schema_version": 1,
                "active_sequence": "main",
                "source": {"path": "../source.mp4", "fingerprint": {"sha256": "0" * 64}},
                "sequences": {"main": {"timeline": "timeline.json", "operations": ["captions"]}},
                "operations": [{
                    "id": "captions",
                    "status": "approved",
                    "skill": "video-add-captions",
                    "plan": "captions/captions-plan.json",
                    "render": {
                        "kind": "overlay",
                        "asset": "captions/overlay-frames",
                        "asset_type": "image-sequence",
                        "pattern": "frame_%06d.png",
                        "start_number": 1,
                        "fps": {"num": 30, "den": 1},
                    },
                }],
                "render": {
                    "plan": "render/render-plan.json",
                    "output": "../final/final-video.mp4",
                },
            }

            with mock.patch.object(projectlib, "validate_project", return_value=[]):
                render_plan = projectlib.build_render_plan(project, root)

            captions = [
                item for item in render_plan["contributions"] if item["operation"] == "captions"
            ]
            self.assertEqual(2, len(captions))
            self.assertEqual(
                [(0.2, 0.6, 7, 0.5, 0.8, 1.0), (1.0, 0.5, 31, 0.5, 0.6, 1.2)],
                [
                    (
                        item["start_s"], item["duration_s"], item["start_number"],
                        item["editor_transform"]["x"], item["editor_transform"]["y"],
                        item["editor_transform"]["scale"],
                    )
                    for item in captions
                ],
            )
            self.assertEqual(
                [
                    {"x": 0.2, "y": 0.7, "width": 0.6, "height": 0.2},
                    {"x": 0.1, "y": 0.6, "width": 0.8, "height": 0.25},
                ],
                [item["content_bounds"] for item in captions],
            )

    def test_editor_transforms_map_only_when_cues_and_overlay_contributions_are_unambiguous(self):
        motion_plan = {
            "cues": [
                {"id": "gm-1", "status": "verified", "editor_transform": {"x": 0.2, "y": 0.3, "scale": 0.8}},
                {"id": "gm-2", "status": "verified"},
            ]
        }

        self.assertEqual([
            {"x": 0.2, "y": 0.3, "scale": 0.8},
            {"x": 0.5, "y": 0.5, "scale": 1.0},
        ], projectlib._editor_transforms_for_contributions("motion-graphics", motion_plan, 2))

        caption_plan = {
            "cues": [
                {
                    "id": "caption-1",
                    "program_range": {"start_s": 0.2, "end_s": 0.8},
                    "editor_transform": {"x": 0.5, "y": 0.8, "scale": 1.0},
                },
                {
                    "id": "caption-2",
                    "program_range": {"start_s": 1.0, "end_s": 1.5},
                },
            ]
        }
        contribution = {
            "kind": "overlay",
            "asset": "cache/captions/overlay-frames",
            "asset_type": "image-sequence",
            "pattern": "frame_%06d.png",
            "start_number": 1,
            "fps": {"num": 30, "den": 1},
        }

        expanded = projectlib._expand_editor_overlay_contributions(
            "captions", caption_plan, [contribution], {"num": 30, "den": 1}
        )

        self.assertEqual(2, len(expanded))
        self.assertEqual({"start_s": 0.2, "duration_s": 0.6, "start_number": 7}, {
            key: expanded[0][key] for key in ("start_s", "duration_s", "start_number")
        })
        self.assertEqual({"start_s": 1.0, "duration_s": 0.5, "start_number": 31}, {
            key: expanded[1][key] for key in ("start_s", "duration_s", "start_number")
        })

        self.assertEqual([
            {"x": 0.5, "y": 0.8, "scale": 1.0},
            {"x": 0.5, "y": 0.5, "scale": 1.0},
        ], projectlib._editor_transforms_for_contributions("captions", caption_plan, len(expanded)))

        default_caption_plan = {"cues": [{"id": "caption-1"}, {"id": "caption-2"}]}
        self.assertEqual(
            [{"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}],
            projectlib._editor_content_bounds_for_contributions(
                "captions", default_caption_plan, 1, Path("."),
            ),
        )

    def test_editor_transform_accepts_saved_overlay_corner_positions(self):
        self.assertEqual(
            {"x": -0.0984375, "y": 0.40555555555555556, "scale_x": 1.0, "scale_y": 1.0},
            projectlib._editor_transform({
                "x": -0.0984375, "y": 0.40555555555555556,
                "scale_x": 1.0, "scale_y": 1.0,
            }),
        )
        self.assertEqual(
            {"x": 1.1729364070960613, "y": 0.6388415615669797,
             "scale_x": 1.4373935135257043, "scale_y": 1.4373935135257043},
            projectlib._editor_transform({
                "x": 1.1729364070960613, "y": 0.6388415615669797,
                "scale_x": 1.4373935135257043, "scale_y": 1.4373935135257043,
            }),
        )

    def test_graphic_motion_render_contribution_includes_union_alpha_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames = root / "work" / "frames"
            frames.mkdir(parents=True)
            first = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
            first.paste((255, 255, 255, 255), (20, 10, 50, 30))
            first.save(frames / "frame_000001.png")
            second = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
            second.paste((255, 255, 255, 255), (10, 20, 70, 60))
            second.save(frames / "frame_000002.png")
            cue = {
                "render": {
                    "asset_type": "image-sequence",
                    "pattern": "frame_%06d.png",
                    "start_number": 1,
                    "frames": [
                        {"path": "frames/frame_000001.png"},
                        {"path": "frames/frame_000002.png"},
                    ],
                },
            }

            self.assertEqual(
                {"x": 0.1, "y": 0.125, "width": 0.6, "height": 0.625},
                projectlib.graphic_motion_content_bounds(cue, root),
            )

    def test_validate_project_rejects_stale_dependency_by_default(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(project, Path("."), check_files=False)

        self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_accepts_only_stale_node_with_old_based_on(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )

        self.assertFalse(any("based_on" in error for error in errors), errors)

        current = copy.deepcopy(project)
        current["operations"][1]["status"] = "approved"
        errors = projectlib.validate_project(
            current, Path("."), check_files=False, dependency_mode="allow_stale"
        )
        self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_rejects_non_old_or_invalid_based_on_revisions(self):
        for expected_revision in (999, "1", True, 0):
            with self.subTest(expected_revision=expected_revision):
                project = self._project_with_stale_dependency()
                project["operations"][1]["based_on"] = {"cut": expected_revision}

                errors = projectlib.validate_project(
                    project, Path("."), check_files=False, dependency_mode="allow_stale"
                )

                self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_rejects_malformed_current_dependency_revision(self):
        for current_revision in ("2", True):
            with self.subTest(current_revision=current_revision):
                project = self._project_with_stale_dependency()
                project["operations"][0]["revision"] = current_revision

                errors = projectlib.validate_project(
                    project, Path("."), check_files=False, dependency_mode="allow_stale"
                )

                self.assertTrue(any("cut revision" in error for error in errors), errors)
                self.assertTrue(any("revision mismatch" in error for error in errors), errors)

    def test_allow_stale_accepts_review_node_with_old_based_on(self):
        project = self._project_with_stale_dependency()
        project["reviews"] = [
            {
                "id": "captions-review",
                "revision": 1,
                "status": "stale",
                "depends_on": ["cut"],
                "based_on": {"cut": 1},
            }
        ]

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )

        self.assertFalse(any("captions-review based_on" in error for error in errors), errors)

        errors = projectlib.validate_project(project, Path("."), check_files=False)
        self.assertTrue(any("captions-review based_on" in error for error in errors), errors)

        project["reviews"][0]["status"] = "approved"
        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )
        self.assertTrue(any("captions-review based_on" in error for error in errors), errors)

    def test_require_current_and_render_plan_remain_strict(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="require_current"
        )
        self.assertTrue(any("based_on" in error for error in errors), errors)
        with mock.patch.object(
            projectlib,
            "validate_project",
            return_value=["revision mismatch: captions based_on cut=1, current=2"],
        ) as validate_project:
            with self.assertRaises(ValueError):
                projectlib.build_render_plan(project, Path("."))
        validate_project.assert_called_once_with(project, Path("."), check_files=True)

    def test_invalid_dependency_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dependency_mode"):
            projectlib.validate_project(
                self._project_with_stale_dependency(),
                Path("."),
                check_files=False,
                dependency_mode="ignore_dependencies",
            )

    @staticmethod
    def _project_with_stale_dependency():
        # The dependency validator only needs these operation fields before
        # later structural validation reports unrelated fixture omissions.
        return {
            "schema_version": 1,
            "active_sequence": "main",
            "sequences": {
                "main": {
                    "operations": ["cut", "captions"]
                }
            },
            "operations": [
                {
                    "id": "cut",
                    "revision": 2,
                    "status": "approved",
                    "depends_on": [],
                    "based_on": {},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": True,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                    },
                },
                {
                    "id": "captions",
                    "revision": 1,
                    "status": "stale",
                    "depends_on": ["cut"],
                    "based_on": {"cut": 1},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": True,
                        "changes_audio": False,
                    },
                },
            ],
        }


if __name__ == "__main__":
    unittest.main()
