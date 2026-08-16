import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME_ROOT))

from project_snapshot import build_snapshot


class ProjectSnapshotTests(unittest.TestCase):
    def test_snapshot_exposes_only_the_opaque_authoritative_source_media_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input").mkdir()
            (root / "work").mkdir()
            (root / "input" / "source.mp4").write_bytes(b"fixture")
            (root / "work" / "timeline.json").write_text(json.dumps({
                "schema_version": 1,
                "source_duration_s": 1,
                "program_duration_s": 1,
                "fps": {"num": 30, "den": 1},
                "clips": [],
            }), encoding="utf-8")
            (root / "work" / "project.json").write_text(json.dumps({
                "schema_version": 1,
                "source": {"path": "../input/source.mp4"},
                "active_sequence": "main",
                "sequences": {"main": {"timeline": "timeline.json", "operations": []}},
                "operations": [],
                "reviews": [],
            }), encoding="utf-8")

            snapshot = build_snapshot(root)

        expected = "asset_" + hashlib.sha256(b"input/source.mp4").hexdigest()[:24]
        self.assertEqual(expected, snapshot["view"]["source_media_id"])
        self.assertNotIn("source.mp4", json.dumps(snapshot["view"]))

    def test_snapshot_exposes_project_identity_and_verified_sequence_geometry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input").mkdir()
            (root / "work" / "understand").mkdir(parents=True)
            (root / "input" / "landscape.mp4").write_bytes(b"fixture")
            (root / "work" / "understand" / "media.json").write_text(json.dumps({
                "schema_version": 1,
                "source": str(root / "input" / "landscape.mp4"),
                "duration_s": 167.973152,
                "fps": {"num": 30000, "den": 1001},
                "width": 1280,
                "height": 720,
                "streams": [
                    {"codec_type": "video", "width": 1280, "height": 720},
                    {"codec_type": "audio", "channels": 2},
                ],
            }), encoding="utf-8")
            (root / "work" / "timeline.json").write_text(json.dumps({
                "schema_version": 1,
                "source_duration_s": 167.973152,
                "program_duration_s": 167.973152,
                "fps": {"num": 30000, "den": 1001},
                "clips": [],
            }), encoding="utf-8")
            (root / "work" / "project.json").write_text(json.dumps({
                "schema_version": 1,
                "project_id": "landscape-project",
                "source": {"path": "../input/landscape.mp4"},
                "active_sequence": "main",
                "sequences": {"main": {"timeline": "timeline.json", "operations": []}},
                "operations": [{
                    "id": "understanding",
                    "skill": "video-understand",
                    "revision": 1,
                    "depends_on": [],
                    "based_on": {},
                    "status": "verified",
                    "outputs": ["understand/media.json"],
                    "target": {"sequence": "main", "scope": "evidence"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                        "adds_track": None,
                    },
                }],
                "reviews": [],
            }), encoding="utf-8")

            snapshot = build_snapshot(root)

        self.assertEqual("landscape-project", snapshot["view"]["project_id"])
        self.assertEqual({"width": 1280, "height": 720}, snapshot["view"]["sequence_geometry"])
        self.assertEqual({
            "name": "landscape.mp4",
            "duration_s": 167.973152,
            "width": 1280,
            "height": 720,
            "has_video": True,
            "has_audio": True,
        }, snapshot["view"]["source_media"])
        self.assertNotIn(str(root), json.dumps(snapshot["view"]))

    def test_snapshot_exposes_complete_typed_operation_cues(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input").mkdir()
            for directory in ("captions", "content-cards", "graphic-motion"):
                (root / "work" / directory).mkdir(parents=True, exist_ok=True)
            motion_frames = root / "work" / "cache" / "graphic-motion" / "rendered" / "motion-001"
            motion_frames.mkdir(parents=True)
            first_frame = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            first_frame.paste((255, 255, 255, 255), (100, 200, 300, 400))
            first_frame.save(motion_frames / "frame_000001.png")
            second_frame = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            second_frame.paste((255, 255, 255, 255), (80, 180, 350, 420))
            second_frame.save(motion_frames / "frame_000002.png")
            frame_hashes = [
                hashlib.sha256((motion_frames / name).read_bytes()).hexdigest()
                for name in ("frame_000001.png", "frame_000002.png")
            ]
            (root / "input" / "source.mp4").write_bytes(b"fixture")
            (root / "work" / "timeline.json").write_text(json.dumps({
                "schema_version": 1,
                "timeline_id": "main",
                "source_duration_s": 12,
                "program_duration_s": 12,
                "fps": {"num": 30, "den": 1},
                "clips": [{
                    "id": "clip-main",
                    "source_range": {"start_s": 0, "end_s": 12},
                    "program_range": {"start_s": 0, "end_s": 12},
                    "speed": 1.0,
                }],
            }), encoding="utf-8")
            (root / "work" / "captions" / "captions-plan.json").write_text(json.dumps({
                "schema_version": 1,
                "style": {"status": "approved", "preset": "clean"},
                "cues": [
                    {"id": "cue-001", "index": 1, "start": 1, "end": 2, "text": "First real caption", "program_range": {"start_s": 1, "end_s": 2}, "editor_transform": {"x": 0.4, "y": 0.8, "scale": 1.2}},
                    {"id": "cue-002", "index": 2, "start": 3, "end": 4, "text": "Second real caption", "program_range": {"start_s": 3, "end_s": 4}},
                ],
            }), encoding="utf-8")
            (root / "work" / "content-cards" / "cards-plan.json").write_text(json.dumps({
                "schema_version": 1,
                "brief": {"theme": "editorial", "target_card_count": 2},
                "cards": [
                    {"id": "card-001", "card_type": "title", "program_start_s": 2, "duration_s": 2, "copy": {"text": "First card"}, "placement": {"region": "top"}, "visual_treatment": {"layout": "default"}},
                    {"id": "card-002", "card_type": "quote", "program_start_s": 6, "duration_s": 2, "copy": {"text": "Second card"}, "placement": {"region": "bottom"}, "visual_treatment": {"layout": "quote"}, "editor_transform": {"x": 0.6, "y": 0.7, "scale": 0.9}},
                ],
            }), encoding="utf-8")
            (root / "work" / "graphic-motion" / "graphic-motion-plan.json").write_text(json.dumps({
                "schema_version": 3,
                "cues": [{
                    "id": "motion-001",
                    "status": "verified",
                    "program_range": {"start_s": 0, "end_s": 5},
                    "intent": {"content": "Real motion title"},
                    "selection": {"chosen_recipe_id": "recipe-real"},
                    "recipe": {
                        "id": "recipe-real",
                        "manifest": {"path": "work/cache/recipe.motion.yaml", "sha256": "a" * 64},
                        "files": [{"path": "work/cache/source/LICENSE", "sha256": "b" * 64}],
                    },
                    "render": {
                        "kind": "overlay",
                        "asset": "cache/graphic-motion/rendered/motion-001",
                        "asset_type": "image-sequence",
                        "pattern": "frame_%06d.png",
                        "start_number": 1,
                        "fps": {"num": 30, "den": 1},
                        "start_s": 0,
                        "duration_s": 5,
                        "frames": [
                            {"path": "work/cache/graphic-motion/rendered/motion-001/frame_000001.png", "sha256": frame_hashes[0]},
                            {"path": "work/cache/graphic-motion/rendered/motion-001/frame_000002.png", "sha256": frame_hashes[1]},
                        ],
                    },
                    "editor_transform": {"x": 0.55, "y": 0.5, "scale": 1.1},
                    "review": {"status": "approved", "mode": "agent"},
                }],
            }), encoding="utf-8")
            operations = []
            for operation_id, plan in (
                ("captions", "captions/captions-plan.json"),
                ("content-cards", "content-cards/cards-plan.json"),
                ("graphic-motion", "graphic-motion/graphic-motion-plan.json"),
            ):
                operations.append({
                    "id": operation_id, "revision": 1, "status": "approved", "plan": plan,
                    "depends_on": [], "based_on": {},
                })
            (root / "work" / "project.json").write_text(json.dumps({
                "schema_version": 1,
                "project_id": "typed-cues",
                "source": {"path": "../input/source.mp4"},
                "active_sequence": "main",
                "sequences": {"main": {"timeline": "timeline.json", "operations": [item["id"] for item in operations]}},
                "operations": operations,
                "reviews": [],
            }), encoding="utf-8")

            view = build_snapshot(root)["view"]

        self.assertEqual(["cue-001", "cue-002"], [cue["id"] for cue in view["captions_edit"]["cues"]])
        self.assertEqual("Second real caption", view["captions_edit"]["cues"][1]["text"])
        self.assertEqual(["card-001", "card-002"], [cue["id"] for cue in view["content_cards_edit"]["cues"]])
        self.assertEqual({"start_s": 6, "end_s": 8}, view["content_cards_edit"]["cues"][1]["program_range"])
        self.assertEqual("motion-001", view["graphic_motion_edit"]["cues"][0]["id"])
        self.assertEqual("recipe-real", view["graphic_motion_edit"]["cues"][0]["recipe_id"])
        self.assertEqual("bound", view["graphic_motion_edit"]["cues"][0]["source_status"])
        self.assertEqual("unknown", view["graphic_motion_edit"]["cues"][0]["license_status"])
        self.assertEqual(
            ["caption", "caption", "card", "card", "graphic-motion"],
            [layer["kind"] for layer in view["layers"]],
        )
        self.assertEqual(
            {"x": 0.4, "y": 0.8, "scale": 1.2},
            view["layers"][0]["transform"],
        )
        self.assertEqual(
            {"x": 0.5, "y": 0.5, "scale": 1.0},
            view["layers"][1]["transform"],
        )
        self.assertEqual(
            {"x": 0.6, "y": 0.7, "scale": 0.9},
            view["layers"][3]["transform"],
        )
        motion = view["layers"][4]
        self.assertEqual("image-sequence", motion["media_type"])
        self.assertEqual({"start_s": 0, "end_s": 5}, motion["program_range"])
        self.assertEqual(
            {
                "pattern": "frame_%06d.png",
                "start_number": 1,
                "fps": {"num": 30, "den": 1},
                "frame_count": 2,
                "content_bounds": {
                    "x": 80 / 1280,
                    "y": 180 / 720,
                    "width": 270 / 1280,
                    "height": 240 / 720,
                },
            },
            motion["image_sequence"],
        )
        self.assertNotIn("asset", json.dumps(view["layers"]))
        self.assertNotIn("work/cache", json.dumps(view["layers"]))


if __name__ == "__main__":
    unittest.main()
