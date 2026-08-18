import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

import protocol_service  # noqa: E402
from protocol_service import ProtocolService  # noqa: E402
from project_snapshot import build_snapshot, canonical_project_root  # noqa: E402


def plan_resource_id(operation_id):
    key = f"plan:{operation_id}".encode("utf-8")
    return "res_" + hashlib.sha256(key).hexdigest()[:24]


class ProtocolServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        (self.root / "work").mkdir()
        (self.root / "input").mkdir()
        self.source = self.root / "input" / "source.mp4"
        self.source.write_bytes(b"video")
        self.timeline = self.root / "work" / "timeline.json"
        self.timeline.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_duration_s": 1.0,
                    "program_duration_s": 1.0,
                    "fps": {"num": 30, "den": 1},
                    "clips": [
                        {
                            "id": "clip-1",
                            "source_range": {"start_s": 0.0, "end_s": 1.0},
                            "program_range": {"start_s": 0.0, "end_s": 1.0},
                            "speed": 1.0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.plan = self.root / "work" / "captions" / "captions-plan.json"
        self.plan.parent.mkdir()
        self.plan.write_text('{"cues": []}\n', encoding="utf-8")
        self.project_path = self.root / "work" / "project.json"
        self._write_project()
        self.service = ProtocolService()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_open_project_returns_registered_resources_and_byte_etags(self):
        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertFalse(response["snapshot"]["read_only"])
        self.assertEqual([], response["snapshot"]["errors"])
        by_kind = {item["kind"]: item for item in response["snapshot"]["resources"]}
        self.assertEqual({"project", "timeline", "plan"}, set(by_kind))
        self.assertEqual("captions", by_kind["plan"]["operation_id"])
        self.assertEqual(
            hashlib.sha256(self.project_path.read_bytes()).hexdigest(),
            by_kind["project"]["etag"],
        )
        view = response["snapshot"]["view"]
        self.assertEqual(1, view["schema_version"])
        self.assertEqual("main", view["active_sequence"])
        self.assertEqual(1, view["operation_count"])
        self.assertEqual(0, view["review_count"])
        operation = view["operations"][0]
        self.assertEqual(64, len(operation.pop("etag")))
        self.assertEqual(
            {
                "id": "captions",
                "revision": 1,
                "status": "draft",
                "target": {"sequence": "main", "scope": "full"},
                "plan_resource_id": plan_resource_id("captions"),
                "based_on": {},
            },
            operation,
        )
        self.assertEqual([], view["reviews"])
        for resource in response["snapshot"]["resources"]:
            self.assertNotIn("path", resource)

    def test_get_snapshot_detects_external_file_changes(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]
        plan_before = next(
            item for item in opened["snapshot"]["resources"] if item["kind"] == "plan"
        )

        self.plan.write_text('{"cues": [{"id": "new"}]}\n', encoding="utf-8")
        refreshed = self.service.handle_request(
            {"verb": "get_snapshot", "project_id": project_id}
        )
        plan_after = next(
            item for item in refreshed["snapshot"]["resources"] if item["kind"] == "plan"
        )

        self.assertNotEqual(plan_before["etag"], plan_after["etag"])
        self.assertEqual(plan_before["id"], plan_after["id"])

    def test_timeline_edits_split_trim_delete_and_invalidate_active_dependents(self):
        self._configure_cut_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]

        split = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": project_id,
            "read_set": self._timeline_read_set(opened["snapshot"]),
            "command": {"type": "split", "clip_id": "clip-1", "at_s": 0.5},
        })

        self.assertTrue(split["ok"], split)
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual(2, len(timeline["clips"]))
        self.assertEqual(1.0, timeline["program_duration_s"])
        self.assertEqual(0.5, timeline["clips"][0]["source_range"]["end_s"])
        right_id = timeline["clips"][1]["id"]
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        cut, captions = project["operations"]
        self.assertEqual((2, "stale"), (cut["revision"], cut["status"]))
        self.assertEqual("stale", captions["status"])
        self.assertEqual("draft", project["render"]["status"])

        trim = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": project_id,
            "read_set": self._timeline_read_set(split["snapshot"]),
            "command": {"type": "trim", "clip_id": right_id, "edge": "start", "source_s": 0.6},
        })
        self.assertTrue(trim["ok"])
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertAlmostEqual(0.9, timeline["program_duration_s"])
        self.assertAlmostEqual(0.5, timeline["clips"][1]["program_range"]["start_s"])

        delete = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": project_id,
            "read_set": self._timeline_read_set(trim["snapshot"]),
            "command": {"type": "delete", "clip_id": "clip-1"},
        })
        self.assertTrue(delete["ok"])
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual([right_id], [clip["id"] for clip in timeline["clips"]])
        self.assertEqual(0.0, timeline["clips"][0]["program_range"]["start_s"])
        self.assertAlmostEqual(0.4, timeline["program_duration_s"])

    def test_timeline_restore_bounds_is_atomic_undoable_and_ripples_downstream_cues(self):
        self._configure_cut_project()
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "cues": [{
                "id": "cue-later",
                "text": "Later cue",
                "program_range": {"start_s": 0.75, "end_s": 0.9},
            }],
        }), encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        split = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(opened["snapshot"]),
            "command": {"type": "split", "clip_id": "clip-1", "at_s": 0.5},
        })
        right_id = json.loads(self.timeline.read_text(encoding="utf-8"))["clips"][1]["id"]
        trimmed = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(split["snapshot"]),
            "command": {"type": "trim", "clip_id": right_id, "edge": "start", "source_s": 0.6},
        })
        self.assertTrue(trimmed["ok"], trimmed)
        self.assertEqual(
            {"start_s": 0.65, "end_s": 0.8},
            json.loads(self.plan.read_text(encoding="utf-8"))["cues"][0]["program_range"],
        )

        restored = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(trimmed["snapshot"]),
            "command": {"type": "restore-bounds", "clip_id": right_id},
        })
        self.assertTrue(restored["ok"], restored)
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual({"start_s": 0.5, "end_s": 1.0}, timeline["clips"][1]["source_range"])
        self.assertEqual(1.0, timeline["program_duration_s"])
        self.assertEqual(
            {"start_s": 0.75, "end_s": 0.9},
            json.loads(self.plan.read_text(encoding="utf-8"))["cues"][0]["program_range"],
        )

        undone = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(restored["snapshot"]),
            "command": {"type": "set-range", "clip_id": right_id, "start_s": 0.6, "end_s": 1.0},
        })
        self.assertTrue(undone["ok"], undone)
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual({"start_s": 0.6, "end_s": 1.0}, timeline["clips"][1]["source_range"])
        self.assertEqual(0.9, timeline["program_duration_s"])
        self.assertEqual(
            {"start_s": 0.65, "end_s": 0.8},
            json.loads(self.plan.read_text(encoding="utf-8"))["cues"][0]["program_range"],
        )

    def test_timeline_trim_ripples_downstream_plan_cues_and_render_contributions(self):
        self._configure_cut_project()
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "cues": [{
                "id": "cue-later",
                "text": "Later cue",
                "program_range": {"start_s": 0.75, "end_s": 0.9},
            }],
        }), encoding="utf-8")
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        project["operations"][1]["render"] = [{
            "kind": "overlay", "asset": "cache/caption.mov", "start_s": 0.75, "duration_s": 0.15,
        }]
        project["operations"].append({
            "id": "shorts",
            "revision": 1,
            "status": "approved",
            "depends_on": ["cut"],
            "based_on": {"cut": 1},
            "target": {"sequence": "main", "scope": "derivative"},
            "effects": {
                "changes_timeline": False,
                "changes_geometry": True,
                "changes_video_pixels": True,
                "changes_audio": True,
            },
            "render": [{
                "kind": "overlay", "asset": "cache/short.mp4", "start_s": 0.75, "duration_s": 0.15,
            }],
            "outputs": [],
        })
        self.project_path.write_text(json.dumps(project), encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        split = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(opened["snapshot"]),
            "command": {"type": "split", "clip_id": "clip-1", "at_s": 0.5},
        })
        self.assertTrue(split["ok"], split)
        trimmed = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(split["snapshot"]),
            "command": {"type": "trim", "clip_id": "clip-1", "edge": "end", "source_s": 0.4},
        })
        self.assertTrue(trimmed["ok"])

        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual({"start_s": 0.65, "end_s": 0.8}, plan["cues"][0]["program_range"])
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        captions = next(item for item in project["operations"] if item["id"] == "captions")
        self.assertEqual((2, "stale"), (captions["revision"], captions["status"]))
        self.assertEqual(0.65, captions["render"][0]["start_s"])
        shorts = next(item for item in project["operations"] if item["id"] == "shorts")
        self.assertEqual((1, "stale", 0.75), (
            shorts["revision"], shorts["status"], shorts["render"][0]["start_s"],
        ))
        layer = trimmed["snapshot"]["view"]["layers"][0]
        self.assertEqual({"start_s": 0.65, "end_s": 0.8}, layer["program_range"])

    def test_timeline_edit_rejects_stale_etag_and_noncanonical_trim(self):
        self._configure_cut_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._timeline_read_set(opened["snapshot"])
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        timeline["timeline_id"] = "externally-changed"
        self.timeline.write_text(json.dumps(timeline), encoding="utf-8")

        conflict = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": read_set,
            "command": {"type": "trim", "clip_id": "clip-1", "edge": "end", "source_s": 0.8},
        })
        self.assertEqual((False, 409, "conflict"), (conflict["ok"], conflict["status"], conflict["error"]))
        current = self.service.handle_request({"verb": "get_snapshot", "project_id": opened["project_id"]})
        invalid = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(current["snapshot"]),
            "command": {"type": "trim", "clip_id": "clip-1", "edge": "end", "source_s": 0.0},
        })
        self.assertFalse(invalid["ok"])
        self.assertIn("trim would overlap", invalid["error"])

    def test_timeline_edit_rejects_an_externally_changed_active_downstream_plan(self):
        self._configure_cut_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._timeline_read_set(opened["snapshot"])
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        plan["external_change"] = True
        self.plan.write_text(json.dumps(plan), encoding="utf-8")

        conflict = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": read_set,
            "command": {"type": "trim", "clip_id": "clip-1", "edge": "end", "source_s": 0.8},
        })

        self.assertEqual((False, 409, "conflict"), (conflict["ok"], conflict["status"], conflict["error"]))
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual({"start_s": 0.0, "end_s": 1.0}, timeline["clips"][0]["program_range"])

    def test_timeline_edit_deletes_and_restores_the_final_clip(self):
        self._configure_cut_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        deleted = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(opened["snapshot"]),
            "command": {"type": "delete", "clip_id": "clip-1"},
        })
        self.assertTrue(deleted["ok"])
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual(([], 0.0), (timeline["clips"], timeline["program_duration_s"]))

        restored = self.service.handle_request({
            "verb": "timeline.edit",
            "project_id": opened["project_id"],
            "read_set": self._timeline_read_set(deleted["snapshot"]),
            "command": {
                "type": "insert",
                "index": 0,
                "clip": {
                    "id": "clip-1",
                    "source_range": {"start_s": 0.0, "end_s": 1.0},
                    "speed": 1.0,
                },
            },
        })
        self.assertTrue(restored["ok"])
        timeline = json.loads(self.timeline.read_text(encoding="utf-8"))
        self.assertEqual(["clip-1"], [clip["id"] for clip in timeline["clips"]])
        self.assertEqual({"start_s": 0.0, "end_s": 1.0}, timeline["clips"][0]["program_range"])

    def test_content_cards_update_targets_the_second_card_by_id(self):
        self._configure_content_cards_project()
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        plan["brief"]["target_card_count"] = 2
        second = copy.deepcopy(plan["cards"][0])
        second["id"] = "card-002"
        second["copy"]["suggested_text"] = "Second original"
        plan["cards"].append(second)
        self.plan.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        review = {
            "schema_version": 1,
            "cards": [
                {"id": "card-001", "selected": True, "copy": "Original copy", "placement": "bottom", "visual_treatment": "default"},
                {"id": "card-002", "selected": True, "copy": "Second updated", "placement": "top", "visual_treatment": "default"},
            ],
        }

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"), "review": review,
        })

        self.assertTrue(response["ok"])
        updated = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual(["Original copy", "Second updated"], [card["copy"]["text"] for card in updated["cards"]])
        self.assertEqual(["bottom", "top"], [card["placement"]["region"] for card in updated["cards"]])

    def test_caption_update_targets_a_non_first_cue_and_invalidates_preview_state(self):
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1.0,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "approved", "evidence": ["old"]},
            "cues": [
                {"id": "cue-001", "index": 1, "start": 0.0, "end": 0.4, "text": "First", "lines": ["First"], "program_range": {"start_s": 0.0, "end_s": 0.4}},
                {"id": "cue-002", "index": 2, "start": 0.5, "end": 0.9, "text": "Second", "lines": ["Second"], "program_range": {"start_s": 0.5, "end_s": 0.9}},
            ],
        }, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "captions",
            "read_set": self._read_set(opened["snapshot"], "captions"),
            "review": {"schema_version": 1, "cue_id": "cue-002", "text": "Second updated"},
        })

        self.assertTrue(response["ok"])
        updated = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual(["First", "Second updated"], [cue["text"] for cue in updated["cues"]])
        self.assertEqual(["First"], updated["cues"][0]["lines"])
        self.assertEqual(["Second updated"], updated["cues"][1]["lines"])
        self.assertEqual({"status": "pending", "evidence": []}, updated["review"])
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        self.assertEqual((2, "stale"), (project["operations"][0]["revision"], project["operations"][0]["status"]))

    def test_caption_update_persists_a_typed_editor_transform_without_rendering(self):
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1.0,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "approved", "evidence": ["old"]},
            "cues": [{
                "id": "cue-001", "index": 1, "start": 0.0, "end": 0.4,
                "text": "First", "lines": ["First"],
                "program_range": {"start_s": 0.0, "end_s": 0.4},
            }],
        }, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "captions",
            "read_set": self._read_set(opened["snapshot"], "captions"),
            "review": {
                "schema_version": 1, "cue_id": "cue-001", "text": "First",
                "editor_transform": {"x": 0.25, "y": 0.75, "scale": 1.5},
                "editor_content_bounds": {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2},
            },
        })

        self.assertTrue(response["ok"])
        updated = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual(
            {"x": 0.25, "y": 0.75, "scale": 1.5},
            updated["cues"][0]["editor_transform"],
        )
        self.assertEqual(
            {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2},
            updated["cues"][0]["editor_content_bounds"],
        )
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        self.assertEqual("draft", project["render"]["status"])
        self.assertFalse((self.root / "final" / "final-video.mp4").exists())

    def test_caption_transform_resolves_the_snapshot_id_for_an_idless_cue(self):
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1.0,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "approved", "evidence": ["old"]},
            "cues": [
                {
                    "index": 1, "start": 0.0, "end": 0.4,
                    "text": "First", "lines": ["First"],
                    "program_range": {"start_s": 0.0, "end_s": 0.4},
                },
                {
                    "index": 2, "start": 0.5, "end": 0.9,
                    "text": "Second", "lines": ["Second"],
                    "program_range": {"start_s": 0.5, "end_s": 0.9},
                },
            ],
        }, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "captions",
            "read_set": self._read_set(opened["snapshot"], "captions"),
            "review": {
                "schema_version": 1,
                "cue_id": "cue-002",
                "editor_transform": {"x": 0.25, "y": 0.75, "scale": 1.5},
                "editor_content_bounds": {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2},
            },
        })

        self.assertTrue(response["ok"], response.get("error"))
        updated = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertNotIn("id", updated["cues"][1])
        self.assertNotIn("editor_transform", updated["cues"][0])
        self.assertEqual(
            {"x": 0.25, "y": 0.75, "scale": 1.5},
            updated["cues"][1]["editor_transform"],
        )
        self.assertEqual(
            {"x": 0.1, "y": 0.7, "width": 0.8, "height": 0.2},
            updated["cues"][1]["editor_content_bounds"],
        )

    def test_caption_transform_advances_the_downstream_graphic_motion_plan_atomically(self):
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1.0,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "approved", "evidence": ["old"]},
            "cues": [{
                "index": 1, "start": 0.0, "end": 0.4,
                "text": "First", "lines": ["First"],
                "program_range": {"start_s": 0.0, "end_s": 0.4},
            }],
        }, indent=2) + "\n", encoding="utf-8")
        graphic_plan_path = self.root / "work" / "graphic-motion" / "graphic-motion-plan.json"
        graphic_plan_path.parent.mkdir()
        graphic_plan = {
            "schema_version": 3,
            "dependencies": ["captions"],
            "based_on": {"captions": 1},
            "cues": [],
        }
        graphic_plan_path.write_text(json.dumps(graphic_plan, indent=2) + "\n", encoding="utf-8")
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        graphic_operation = copy.deepcopy(project["operations"][0])
        graphic_operation.update({
            "id": "graphic-motion",
            "revision": 3,
            "status": "verified",
            "depends_on": ["captions"],
            "based_on": {"captions": 1},
            "plan": "graphic-motion/graphic-motion-plan.json",
            "plan_sha256": protocol_service.graphic_motion_plan.canonical_sha256(graphic_plan),
        })
        project["operations"].append(graphic_operation)
        project["sequences"]["main"]["operations"].append("graphic-motion")
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        with mock.patch.object(self.service, "_validate_graphic_motion_plan"):
            response = self.service.handle_request({
                "verb": "plan.update", "project_id": opened["project_id"], "operation": "captions",
                "read_set": self._read_set(opened["snapshot"], "captions"),
                "review": {
                    "schema_version": 1,
                    "cue_id": "cue-001",
                    "editor_transform": {"x": 0.25, "y": 0.75, "scale": 1.5},
                },
            })

        self.assertTrue(response["ok"], response.get("error"))
        saved_project = json.loads(self.project_path.read_text(encoding="utf-8"))
        saved_operation = next(
            item for item in saved_project["operations"] if item["id"] == "graphic-motion"
        )
        saved_plan = json.loads(graphic_plan_path.read_text(encoding="utf-8"))
        self.assertEqual(2, saved_operation["based_on"]["captions"])
        self.assertEqual(2, saved_plan["based_on"]["captions"])
        self.assertEqual(
            protocol_service.graphic_motion_plan.canonical_sha256(saved_plan),
            saved_operation["plan_sha256"],
        )

    def test_caption_plan_validation_accepts_snapshot_compatible_idless_cues(self):
        self.service._validate_caption_plan({
            "schema_version": 1,
            "cues": [
                {"text": "First", "program_range": {"start_s": 0.0, "end_s": 0.4}},
                {"text": "Second", "program_range": {"start_s": 0.5, "end_s": 0.9}},
            ],
        })

    def test_transform_only_update_preserves_operation_renderability(self):
        plan = {
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1.0,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "approved", "evidence": ["old"]},
            "cues": [{
                "id": "cue-001", "index": 1, "start": 0.0, "end": 0.4,
                "text": "First", "lines": ["First"],
                "program_range": {"start_s": 0.0, "end_s": 0.4},
            }],
        }
        operation = {
            "id": "captions", "revision": 4, "status": "approved",
            "render": {"kind": "overlay", "asset": "cache/captions/overlay-frames"},
            "outputs": ["cache/captions/overlay-frames"],
        }
        project = {
            "operations": [copy.deepcopy(operation)],
            "reviews": [],
            "render": {"status": "verified"},
        }
        context = (
            self.root, {"resources": []}, project, operation,
            self.plan, plan, {"project": "p", "operation": "o", "plan": "a"},
        )
        captured = {}

        def capture(_root, _plan_path, updated_plan, updated_project, *_args):
            captured["plan"] = updated_plan
            captured["project"] = updated_project
            return {"ok": True}

        with (
            mock.patch.object(self.service, "_validate_caption_plan", side_effect=AssertionError("full validation must not run")),
            mock.patch.object(self.service, "_commit", side_effect=capture),
        ):
            response = self.service._apply_plan_update(context, {
                "schema_version": 1,
                "cue_id": "cue-001",
                "editor_transform": {"x": 0.3, "y": 0.7, "scale": 1.2},
            })

        self.assertTrue(response["ok"])
        self.assertEqual("First", captured["plan"]["cues"][0]["text"])
        changed = captured["project"]["operations"][0]
        self.assertEqual((5, "approved"), (changed["revision"], changed["status"]))
        self.assertEqual(operation["render"], changed["render"])
        self.assertEqual(operation["outputs"], changed["outputs"])
        self.assertEqual("draft", captured["project"]["render"]["status"])

    def test_graphic_motion_transform_only_update_does_not_revalidate_unchanged_recipe_metadata(self):
        plan = {
            "schema_version": 3,
            "cues": [{"id": "gm-001", "status": "verified"}],
            "delivery_bindings": [],
        }
        operation = {
            "id": "graphic-motion", "revision": 2, "status": "verified",
            "render": {"kind": "overlay", "asset": "cache/graphic-motion/gm-001"},
            "outputs": ["cache/graphic-motion/gm-001"],
        }
        project = {
            "operations": [copy.deepcopy(operation)],
            "reviews": [],
            "render": {"status": "verified"},
        }
        context = (
            self.root, {"resources": []}, project, operation,
            self.plan, plan, {"project": "p", "operation": "o", "plan": "a"},
        )
        captured = {}

        def capture(_root, _plan_path, updated_plan, updated_project, *_args):
            captured["plan"] = updated_plan
            captured["project"] = updated_project
            return {"ok": True}

        with (
            mock.patch.object(protocol_service.graphic_motion_plan, "_input_bindings", return_value=[]),
            mock.patch.object(protocol_service.graphic_motion_plan, "_cue_bindings", return_value=[]),
            mock.patch.object(self.service, "_validate_graphic_motion_plan", side_effect=AssertionError("full validation must not run")),
            mock.patch.object(self.service, "_commit", side_effect=capture),
        ):
            response = self.service._apply_plan_update(context, {
                "schema_version": 1,
                "cue_id": "gm-001",
                "editor_transform": {"x": 0.3, "y": 0.7, "scale": 1.2},
            })

        self.assertTrue(response["ok"])
        self.assertEqual(
            {"x": 0.3, "y": 0.7, "scale": 1.2},
            captured["plan"]["cues"][0]["editor_transform"],
        )
        changed = captured["project"]["operations"][0]
        self.assertEqual((3, "verified"), (changed["revision"], changed["status"]))
        self.assertEqual("draft", captured["project"]["render"]["status"])

    def test_graphic_motion_transform_supports_independent_axis_scaling(self):
        transform = {"x": 0.3, "y": 0.7, "scale_x": 1.25, "scale_y": 0.75}

        self.assertEqual(transform, self.service._validate_editor_transform(transform))

    def test_frozen_graphic_motion_recipe_uses_materialized_hashes_without_current_catalog_entry(self):
        target = self.root / "work/cache/graphic-motion/hyperframes/gm-001"
        target.mkdir(parents=True)
        manifest_path = target / "recipe.motion.yaml"
        conversion_path = target / "conversion.json"
        manifest_path.write_text("id: legacy-recipe\n", encoding="utf-8")
        conversion_path.write_text(json.dumps({
            "schema_version": 1,
            "project_id": "LegacyRecipe",
            "variants": [{"composition_id": "legacy-recipe"}],
        }), encoding="utf-8")

        def binding(path):
            return {
                "path": path.relative_to(self.root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }

        manifest = binding(manifest_path)
        conversion = binding(conversion_path)
        cue = {
            "recipe": {
                "id": "legacy-recipe",
                "composition_id": "legacy-recipe",
                "manifest": manifest,
                "conversion_receipt": conversion,
                "files": [manifest, conversion],
            },
        }

        errors = protocol_service.graphic_motion_plan._recipe_errors(
            "gm-001", cue, self.root, verify_files=True, library={},
            require_library_match=False,
        )

        self.assertEqual([], errors)

    def test_frozen_graphic_motion_selection_allows_historical_matched_field_names(self):
        cue = {
            "intent": {"recipe_queries": ["legacy query"]},
            "selection": {
                "query": "legacy query",
                "shortlist": [{
                    "recipe_id": "legacy-recipe",
                    "score": 10,
                    "matched_fields": ["name", "structural_roles"],
                }],
                "chosen_recipe_id": "legacy-recipe",
                "agent_rationale": "The frozen candidate matches the cue.",
                "avoid_when_review": "No frozen warning applies.",
                "field_evidence": {
                    field: f"Evidence for {field}"
                    for field in protocol_service.graphic_motion_plan.SELECTION_FIELDS
                },
            },
        }

        errors = protocol_service.graphic_motion_plan._selection_errors(
            "gm-001", cue, {"legacy-recipe"}, require_known_fields=False,
        )

        self.assertEqual([], errors)

    def test_editor_transform_rejects_out_of_range_values_and_unknown_fields(self):
        for transform in (
            {"x": -2.01, "y": 0.5, "scale": 1.0},
            {"x": 0.5, "y": 3.01, "scale": 1.0},
            {"x": 0.5, "y": 0.5, "scale": 0.09},
            {"x": 0.5, "y": 0.5, "scale": 4.01},
            {"x": 0.5, "y": 0.5, "scale": 1.0, "rotation": 10},
        ):
            with self.subTest(transform=transform):
                with self.assertRaises(ValueError):
                    self.service._validate_editor_transform(transform)

    def test_editor_transform_accepts_cropped_overlay_corner_positions(self):
        self.assertEqual(
            {"x": 1.15, "y": -0.7, "scale_x": 1.0, "scale_y": 4.0},
            self.service._validate_editor_transform(
                {"x": 1.15, "y": -0.7, "scale_x": 1.0, "scale_y": 4.0},
            ),
        )

    def test_content_cards_update_persists_transform_on_the_target_card(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        review = self._cards_review(copy="Original copy", placement="bottom")
        review["editor_transform"] = {
            "cue_id": "card-001", "x": 0.7, "y": 0.35, "scale": 0.8,
        }

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"), "review": review,
        })

        self.assertTrue(response["ok"])
        updated = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual(
            {"x": 0.7, "y": 0.35, "scale": 0.8},
            updated["cards"][0]["editor_transform"],
        )

    def test_get_resource_accepts_only_server_issued_resource_ids(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]
        plan_resource = next(
            item for item in opened["snapshot"]["resources"] if item["kind"] == "plan"
        )

        response = self.service.handle_request(
            {
                "verb": "get_resource",
                "project_id": project_id,
                "resource_id": plan_resource["id"],
            }
        )
        rejected = self.service.handle_request(
            {
                "verb": "get_resource",
                "project_id": project_id,
                "resource_id": "../../input/source.mp4",
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual({"cues": []}, response["resource"]["content"])
        self.assertEqual(plan_resource["etag"], response["resource"]["etag"])
        self.assertEqual(
            {"ok": False, "error": "unknown resource_id"}, rejected
        )

    def test_plan_symlink_escape_is_reported_and_not_registered(self):
        outside_dir = tempfile.TemporaryDirectory()
        self.addCleanup(outside_dir.cleanup)
        outside = Path(outside_dir.name) / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        escape = self.root / "work" / "escape.json"
        try:
            escape.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        project = self._project()
        project["operations"][0]["plan"] = "escape.json"
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertIn(
            "project path escapes root: escape.json", response["snapshot"]["errors"]
        )
        self.assertNotIn(
            "plan", {item["kind"] for item in response["snapshot"]["resources"]}
        )

    def test_invalid_json_opens_read_only_with_exact_error(self):
        self.project_path.write_text("{", encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            [
                "invalid project JSON: Expecting property name enclosed in double quotes: "
                "line 1 column 2 (char 1)"
            ],
            response["snapshot"]["errors"],
        )

    def test_non_object_json_roots_open_read_only_with_exact_error(self):
        for value in (None, [], ["project"], "project", 1, 1.5, True):
            with self.subTest(value=value):
                self.project_path.write_text(json.dumps(value), encoding="utf-8")

                response = self.service.handle_request(
                    {"verb": "open_project", "project_root": str(self.root)}
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["snapshot"]["read_only"])
                self.assertEqual(
                    ["invalid project JSON: root must be an object"],
                    response["snapshot"]["errors"],
                )

    def test_invalid_project_opens_read_only_with_projectlib_diagnostics(self):
        project = self._project()
        project["schema_version"] = 99
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            ["project schema_version must be 1"], response["snapshot"]["errors"]
        )

    def test_malformed_project_collections_do_not_crash_snapshot(self):
        project = self._project()
        project["operations"] = None
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            ["project validation failed: 'NoneType' object is not iterable"],
            response["snapshot"]["errors"],
        )
        self.assertEqual(0, response["snapshot"]["view"]["operation_count"])

    def test_malformed_active_sequence_and_plan_values_do_not_crash_snapshot(self):
        malformed = (
            ("active_sequence", []),
            ("plan", []),
            ("plan", {"path": "captions/captions-plan.json"}),
        )
        for field, value in malformed:
            with self.subTest(field=field, value=value):
                project = self._project()
                if field == "active_sequence":
                    project[field] = value
                else:
                    project["operations"][0][field] = value
                self.project_path.write_text(json.dumps(project), encoding="utf-8")

                response = self.service.handle_request(
                    {"verb": "open_project", "project_root": str(self.root)}
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["snapshot"]["read_only"])
                if field == "plan":
                    self.assertNotIn(
                        "plan",
                        {item["kind"] for item in response["snapshot"]["resources"]},
                    )

    def test_root_and_registered_resources_must_remain_inside_project(self):
        outside = Path(self.temp_dir.name).parent / "not-a-project"
        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(outside)}
        )
        self.assertEqual(
            {"ok": False, "error": "project root must contain work/project.json"},
            response,
        )

        project = self._project()
        project["operations"][0]["plan"] = "../../outside.json"
        self.project_path.write_text(json.dumps(project), encoding="utf-8")
        escaped = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        self.assertTrue(escaped["snapshot"]["read_only"])
        self.assertIn(
            "project path escapes root: ../../outside.json",
            escaped["snapshot"]["errors"],
        )

    def test_open_project_requires_an_explicit_root_even_from_a_project_directory(self):
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            response = self.service.handle_request({"verb": "open_project"})
        finally:
            os.chdir(previous)

        self.assertEqual(
            {"ok": False, "error": "project root must contain work/project.json"},
            response,
        )

    def test_manifest_resolved_path_must_remain_inside_project_root(self):
        root = self.root
        manifest = root / "work" / "project.json"
        escaped = root.parent / "outside-project.json"
        real_resolve = Path.resolve

        def resolve_path(path, strict=False):
            if path == manifest:
                return escaped
            return real_resolve(path, strict=strict)

        with mock.patch.object(Path, "resolve", autospec=True, side_effect=resolve_path):
            with self.assertRaisesRegex(
                ValueError, "project root must contain work/project.json"
            ):
                canonical_project_root(root)

    def test_unhashable_and_blank_resource_identifiers_are_rejected(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]

        for invalid in (None, "", "   ", []):
            with self.subTest(project_id=invalid):
                self.assertEqual(
                    {
                        "ok": False,
                        "error": "project_id must be a nonblank string",
                    },
                    self.service.handle_request(
                        {"verb": "get_snapshot", "project_id": invalid}
                    ),
                )
        for invalid in (None, "", "   ", {}):
            with self.subTest(resource_id=invalid):
                self.assertEqual(
                    {
                        "ok": False,
                        "error": "resource_id must be a nonblank string",
                    },
                    self.service.handle_request(
                        {
                            "verb": "get_resource",
                            "project_id": project_id,
                            "resource_id": invalid,
                        }
                    ),
                )

    def test_request_exception_boundary_returns_fixed_error(self):
        with mock.patch.object(
            self.service, "_dispatch", side_effect=RuntimeError("private detail")
        ):
            response = self.service.handle_request({"verb": "get_snapshot"})

        self.assertEqual({"ok": False, "error": "invalid request"}, response)

    def test_json_line_entrypoint_rejects_unknown_verbs(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "protocol_service.py")],
            input='{"verb":"run_shell","command":"whoami"}\n',
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            {"ok": False, "error": "unknown verb"},
            json.loads(result.stdout),
        )
        self.assertEqual("", result.stderr)

    def test_json_line_loop_survives_a_malformed_request(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "protocol_service.py")],
            input=(
                '{"verb":"get_snapshot","project_id":[]}\n'
                '{"verb":"run_shell","command":"whoami"}\n'
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            [
                {
                    "ok": False,
                    "error": "project_id must be a nonblank string",
                },
                {"ok": False, "error": "unknown verb"},
            ],
            [json.loads(line) for line in result.stdout.splitlines()],
        )
        self.assertEqual("", result.stderr)

    def test_content_cards_plan_update_uses_complete_etag_read_set_and_leaf_review_semantics(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._read_set(opened["snapshot"], "content-cards")

        response = self.service.handle_request(
            {
                "verb": "plan.update",
                "project_id": opened["project_id"],
                "operation": "content-cards",
                "read_set": read_set,
                "review": self._cards_review(copy="A stronger opening", placement="top"),
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual("committed", response["result"])
        saved = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual("A stronger opening", saved["cards"][0]["copy"]["text"])
        self.assertEqual("approved", saved["cards"][0]["copy"]["status"])
        self.assertEqual("top", saved["cards"][0]["placement"]["region"])
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        operation = next(item for item in project["operations"] if item["id"] == "content-cards")
        dependent = next(item for item in project["operations"] if item["id"] == "graphic-motion")
        review = project["reviews"][0]
        self.assertEqual((2, "stale"), (operation["revision"], operation["status"]))
        self.assertEqual(("stale", {"content-cards": 1}), (dependent["status"], dependent["based_on"]))
        self.assertEqual(("stale", {"content-cards": 1}), (review["status"], review["based_on"]))
        self.assertEqual("draft", project["render"]["status"])

    def test_content_cards_semantic_no_op_does_not_rewrite_or_increment_revision(self):
        self._configure_content_cards_project(approved_plan=True)
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        before_project = self.project_path.read_bytes()
        before_plan = self.plan.read_bytes()

        response = self.service.handle_request(
            {
                "verb": "plan.update",
                "project_id": opened["project_id"],
                "operation": "content-cards",
                "read_set": self._read_set(opened["snapshot"], "content-cards"),
                "review": self._cards_review(copy="Original copy", placement="bottom"),
            }
        )

        self.assertEqual({"ok": True, "result": "no_change", "snapshot": opened["snapshot"]}, response)
        self.assertEqual(before_project, self.project_path.read_bytes())
        self.assertEqual(before_plan, self.plan.read_bytes())

    def test_same_operation_external_change_returns_conflict_without_overwrite(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._read_set(opened["snapshot"], "content-cards")
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        plan["cards"][0]["copy"]["suggested_text"] = "Agent update"
        self.plan.write_text(json.dumps(plan), encoding="utf-8")

        response = self.service.handle_request(
            {
                "verb": "plan.update",
                "project_id": opened["project_id"],
                "operation": "content-cards",
                "read_set": read_set,
                "review": self._cards_review(copy="Local update", placement="top"),
            }
        )

        self.assertFalse(response["ok"])
        self.assertEqual(409, response["status"])
        self.assertEqual("conflict", response["error"])
        self.assertEqual("Agent update", json.loads(self.plan.read_text(encoding="utf-8"))["cards"][0]["copy"]["suggested_text"])

    def test_different_operation_external_change_refreshes_without_conflicting(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._read_set(opened["snapshot"], "content-cards")
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        project["operations"][1]["revision"] = 3
        project["operations"][1]["status"] = "stale"
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"],
            "operation": "content-cards", "read_set": read_set,
            "review": self._cards_review(copy="Local update", placement="top"),
        })

        self.assertTrue(response["ok"])
        saved = json.loads(self.project_path.read_text(encoding="utf-8"))
        graphic_motion = next(item for item in saved["operations"] if item["id"] == "graphic-motion")
        self.assertEqual(3, graphic_motion["revision"])

    def test_plan_update_rejects_generic_patch_and_managed_fields(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        base = {
            "verb": "plan.update",
            "project_id": opened["project_id"],
            "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"),
        }
        for extra in ({"patch": {"revision": 99}}, {"review": self._cards_review(), "revision": 99}):
            with self.subTest(extra=extra):
                response = self.service.handle_request({**base, **extra})
                self.assertFalse(response["ok"])

    def test_review_record_requires_current_same_revision_full_evidence_binding(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        read_set = self._read_set(opened["snapshot"], "content-cards")
        decision = {
            "review_id": "content-cards-preview-r1",
            "decision": "approved",
            "snapshot_etag": opened["snapshot"]["snapshot_etag"],
            "evidence_hashes": [self.preview_hash],
            "actor": "local-user",
            "rationale": "Reviewed the bound composited evidence",
        }

        response = self.service.handle_request(
            {
                "verb": "review.record",
                "project_id": opened["project_id"],
                "operation": "content-cards",
                "read_set": read_set,
                "decision": decision,
            }
        )

        self.assertTrue(response["ok"])
        receipt = json.loads(self.project_path.read_text(encoding="utf-8"))["reviews"][0]
        self.assertEqual("approved", receipt["status"])
        self.assertEqual("human", receipt["decision_mode"])
        self.assertEqual(decision["evidence_hashes"], receipt["evidence_hashes"])

        for field, value in (("evidence_hashes", []), ("snapshot_etag", "wrong"), ("review_id", "wrong")):
            self._configure_content_cards_project()
            reopened = self.service.handle_request(
                {"verb": "open_project", "project_root": str(self.root)}
            )
            invalid = {**decision, field: value}
            rejected = self.service.handle_request(
                {
                    "verb": "review.record",
                    "project_id": reopened["project_id"],
                    "operation": "content-cards",
                    "read_set": self._read_set(reopened["snapshot"], "content-cards"),
                    "decision": invalid,
                }
            )
            self.assertFalse(rejected["ok"], field)

    def test_review_record_rejects_forged_stale_missing_and_replaced_artifacts(self):
        for forged in ("sha256:preview-r1", "a" * 64, "sha256:" + "A" * 64):
            with self.subTest(forged=forged):
                self._configure_content_cards_project()
                project = json.loads(self.project_path.read_text(encoding="utf-8"))
                project["reviews"][0]["evidence_hashes"] = [forged]
                self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
                opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
                response = self.service.handle_request({
                    "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
                    "read_set": self._read_set(opened["snapshot"], "content-cards"),
                    "decision": {
                        "review_id": "content-cards-preview-r1", "decision": "approved",
                        "snapshot_etag": opened["snapshot"]["snapshot_etag"], "evidence_hashes": [forged],
                        "actor": "local-user", "rationale": "Forged evidence",
                    },
                })
                self.assertFalse(response["ok"])

        for mutation in ("delete", "replace"):
            with self.subTest(mutation=mutation):
                self._configure_content_cards_project()
                opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
                if mutation == "delete":
                    self.preview_path.unlink()
                else:
                    self.preview_path.write_bytes(b"replacement bytes")
                response = self.service.handle_request({
                    "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
                    "read_set": self._read_set(opened["snapshot"], "content-cards"),
                    "decision": {
                        "review_id": "content-cards-preview-r1", "decision": "approved",
                        "snapshot_etag": opened["snapshot"]["snapshot_etag"], "evidence_hashes": [self.preview_hash],
                        "actor": "local-user", "rationale": "Stale artifact",
                    },
                })
                self.assertFalse(response["ok"])

        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        project["render"]["status"] = "draft"
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        refreshed = self.service.handle_request({"verb": "get_snapshot", "project_id": opened["project_id"]})
        response = self.service.handle_request({
            "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(refreshed["snapshot"], "content-cards"),
            "decision": {
                "review_id": "content-cards-preview-r1", "decision": "approved",
                "snapshot_etag": opened["snapshot"]["snapshot_etag"], "evidence_hashes": [self.preview_hash],
                "actor": "local-user", "rationale": "Stale snapshot",
            },
        })
        self.assertFalse(response["ok"])

    def test_editor_state_link_is_rejected_before_lock_or_journal_writes(self):
        outside = self.root / "outside-editor"
        outside.mkdir()
        editor = self.root / "work" / ".editor"
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd.exe", "/c", "mklink", "/J", str(editor), str(outside)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.skipTest("Windows junction creation is unavailable")
            else:
                editor.symlink_to(outside, target_is_directory=True)
            response = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
            self.assertFalse(response["ok"])
            self.assertFalse((outside / "mutation.lock").exists())
            self.assertFalse((outside / "transaction.json").exists())
        finally:
            if editor.exists() or editor.is_symlink():
                if os.name == "nt":
                    os.rmdir(editor)
                else:
                    editor.unlink()

    def test_projectlib_writer_waits_for_the_editor_project_lease(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        writer = None

        def start_writer():
            nonlocal writer
            scripts = RUNTIME.parent / "skills" / "video-understand" / "scripts"
            script = (
                "import sys; from pathlib import Path; "
                f"sys.path.insert(0, {str(scripts)!r}); "
                "import projectlib; projectlib.write_json(Path(sys.argv[1]), {'writer': 'complete'})"
            )
            writer = subprocess.Popen([sys.executable, "-c", script, str(self.root / "work" / "external.json")])
            with self.assertRaises(subprocess.TimeoutExpired):
                writer.wait(timeout=0.2)

        self.service._after_prepare = start_writer
        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"),
            "review": self._cards_review(copy="Lease protected"),
        })

        self.assertTrue(response["ok"])
        self.assertIsNotNone(writer)
        writer.wait(timeout=5)
        self.assertEqual({"writer": "complete"}, json.loads((self.root / "work" / "external.json").read_text(encoding="utf-8")))

    def test_open_project_recovers_prepared_transaction_after_plan_replacement(self):
        self._configure_content_cards_project()
        original_project = self.project_path.read_bytes()
        original_plan = self.plan.read_bytes()
        updated_project = json.loads(original_project)
        updated_project["operations"][0]["revision"] = 2
        updated_project["operations"][0]["status"] = "stale"
        updated_project["operations"][1]["status"] = "stale"
        updated_project["reviews"][0]["status"] = "stale"
        updated_project["render"]["status"] = "draft"
        updated_project_bytes = (json.dumps(updated_project, indent=2) + "\n").encode()
        updated_plan = json.loads(original_plan)
        updated_plan["cards"][0]["copy"]["suggested_text"] = "Recovered edit"
        updated_plan_bytes = (json.dumps(updated_plan, indent=2) + "\n").encode()
        self.plan.write_bytes(updated_plan_bytes)
        journal = self.root / "work" / ".editor" / "transaction.json"
        journal.parent.mkdir()
        journal.write_text(json.dumps({
            "schema_version": 1,
            "transaction_id": str(uuid.uuid4()),
            "operation": "content-cards",
            "verb": "plan.update",
            "state": "prepared",
            "files": [
                {"path": "work/content-cards/cards-plan.json", "old_hash": hashlib.sha256(original_plan).hexdigest(),
                 "new_hash": hashlib.sha256(updated_plan_bytes).hexdigest(), "new_content": updated_plan_bytes.decode()},
                {"path": "work/project.json", "old_hash": hashlib.sha256(original_project).hexdigest(),
                 "new_hash": hashlib.sha256(updated_project_bytes).hexdigest(), "new_content": updated_project_bytes.decode()},
            ],
        }), encoding="utf-8")

        response = ProtocolService().handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertEqual(2, json.loads(self.project_path.read_text(encoding="utf-8"))["operations"][0]["revision"])
        self.assertFalse(journal.exists())

    def test_open_project_enters_read_only_when_transaction_recovery_is_ambiguous(self):
        self._configure_content_cards_project()
        journal = self.root / "work" / ".editor" / "transaction.json"
        journal.parent.mkdir()
        journal.write_text(json.dumps({
            "schema_version": 1, "transaction_id": str(uuid.uuid4()), "operation": "content-cards",
            "verb": "review.record", "state": "prepared", "files": [{
                "path": "work/project.json", "old_hash": "0" * 64,
                "new_hash": "1" * 64, "new_content": "{}\n",
            }],
        }), encoding="utf-8")

        response = ProtocolService().handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["snapshot"]["read_only"])
        self.assertIn("ambiguous transaction recovery", response["snapshot"]["errors"])

        project_id = response["project_id"]
        service = ProtocolService()
        response = service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        project_id = response["project_id"]
        refreshed = service.handle_request({"verb": "get_snapshot", "project_id": project_id})
        self.assertTrue(refreshed["snapshot"]["read_only"])
        for verb, payload in (
            ("plan.update", {"review": self._cards_review()}),
            ("review.record", {"decision": {}}),
        ):
            rejected = service.handle_request({
                "verb": verb, "project_id": project_id, "operation": "content-cards",
                "read_set": self._read_set(response["snapshot"], "content-cards"), **payload,
            })
            self.assertFalse(rejected["ok"])
            self.assertEqual("project is in recovery quarantine", rejected["error"])

    def test_project_mutation_lease_blocks_a_second_writer(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        lease = self.service._acquire_lease(self.root)
        try:
            response = ProtocolService()._acquire_lease(self.root)
            self.assertIsNone(response)
            response = self.service.handle_request({
                "verb": "plan.update", "project_id": opened["project_id"],
                "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
                "review": self._cards_review(copy="Blocked"),
            })
        finally:
            self.service._release_lease(lease)

        self.assertEqual((False, 409, "project mutation is busy"),
                         (response["ok"], response["status"], response["error"]))

    def test_project_mutation_lease_recovers_a_dead_owner_without_stealing_a_live_lock(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        lock = self.root / "work" / ".editor" / "mutation.lock"
        lock.parent.mkdir(exist_ok=True)
        lock.write_text("999999999\n", encoding="utf-8")

        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"],
            "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
            "review": self._cards_review(copy="Recovered owner"),
        })

        self.assertTrue(response["ok"])
        lease = self.service._acquire_lease(self.root)
        try:
            blocked = self.service.handle_request({
                "verb": "plan.update", "project_id": opened["project_id"],
                "operation": "content-cards", "read_set": self._read_set(response["snapshot"], "content-cards"),
                "review": self._cards_review(copy="Must not steal"),
            })
        finally:
            self.service._release_lease(lease)
        self.assertEqual((False, 409), (blocked["ok"], blocked["status"]))

    def test_final_cas_rejects_same_operation_change_during_transaction(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        changed = False

        def external_write():
            nonlocal changed
            if changed:
                return
            changed = True
            plan = json.loads(self.plan.read_text(encoding="utf-8"))
            plan["cards"][0]["copy"]["suggested_text"] = "External boundary update"
            self.plan.write_text(json.dumps(plan), encoding="utf-8")

        self.service._before_final_cas = external_write
        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"],
            "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
            "review": self._cards_review(copy="Local overwrite"),
        })

        self.assertEqual((False, 409, "conflict"), (response["ok"], response["status"], response["error"]))
        self.assertEqual("External boundary update", json.loads(self.plan.read_text(encoding="utf-8"))["cards"][0]["copy"]["suggested_text"])

    def test_final_cas_reconciles_a_different_operation_change(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        def external_write():
            project = json.loads(self.project_path.read_text(encoding="utf-8"))
            project["operations"][1]["revision"] = 9
            self.project_path.write_text(json.dumps(project), encoding="utf-8")

        self.service._before_final_cas = external_write
        response = self.service.handle_request({
            "verb": "plan.update", "project_id": opened["project_id"],
            "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
            "review": self._cards_review(copy="Local update"),
        })

        self.assertTrue(response["ok"])
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        self.assertEqual(9, next(item for item in project["operations"] if item["id"] == "graphic-motion")["revision"])
        self.assertEqual(2, next(item for item in project["operations"] if item["id"] == "content-cards")["revision"])

    def test_review_final_cas_reconciles_other_operation_and_updates_exact_receipt(self):
        self._configure_content_cards_project()
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        project["reviews"].insert(0, {
            "id": "older-preview", "revision": 1, "status": "approved", "depends_on": ["content-cards"],
            "based_on": {"content-cards": 1}, "snapshot_etag": "older-snapshot",
            "evidence_hashes": ["sha256:older"], "decision_mode": "human", "actor": "local-user",
            "rationale": "Older evidence",
        })
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        def external_write():
            current = json.loads(self.project_path.read_text(encoding="utf-8"))
            next(item for item in current["operations"] if item["id"] == "graphic-motion")["revision"] = 9
            self.project_path.write_text(json.dumps(current), encoding="utf-8")

        self.service._before_final_cas = external_write
        response = self.service.handle_request({
            "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"), "decision": {
                "review_id": "content-cards-preview-r1", "decision": "approved", "snapshot_etag": opened["snapshot"]["snapshot_etag"],
                "evidence_hashes": [self.preview_hash], "actor": "local-user", "rationale": "Current evidence",
            },
        })

        self.assertTrue(response["ok"])
        committed = json.loads(self.project_path.read_text(encoding="utf-8"))
        self.assertEqual(9, next(item for item in committed["operations"] if item["id"] == "graphic-motion")["revision"])
        receipt = next(item for item in committed["reviews"] if item["id"] == "content-cards-preview-r1")
        self.assertEqual(("approved", "Current evidence"), (receipt["status"], receipt["rationale"]))

    def test_review_final_cas_rejects_changed_target_receipt_without_overwriting_terminal_decision(self):
        self._configure_content_cards_project()
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        def external_decision():
            current = json.loads(self.project_path.read_text(encoding="utf-8"))
            receipt = next(item for item in current["reviews"] if item["id"] == "content-cards-preview-r1")
            receipt.update({
                "status": "approved", "decision_mode": "human", "actor": "external-user",
                "rationale": "External evidence approved",
            })
            self.project_path.write_text(json.dumps(current), encoding="utf-8")

        self.service._before_final_cas = external_decision
        response = self.service.handle_request({
            "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"), "decision": {
                "review_id": "content-cards-preview-r1", "decision": "approved", "snapshot_etag": opened["snapshot"]["snapshot_etag"],
                "evidence_hashes": [self.preview_hash], "actor": "local-user", "rationale": "Local approval",
            },
        })

        self.assertEqual((False, 409, "conflict"), (response["ok"], response["status"], response["error"]))
        authoritative = next(item for item in response["snapshot"]["view"]["reviews"]
                             if item["id"] == "content-cards-preview-r1")
        self.assertEqual(("approved", "External evidence approved"),
                         (authoritative["status"], authoritative["rationale"]))
        persisted = next(item for item in json.loads(self.project_path.read_text(encoding="utf-8"))["reviews"]
                         if item["id"] == "content-cards-preview-r1")
        self.assertEqual(("approved", "external-user"), (persisted["status"], persisted["actor"]))

    def test_review_final_cas_preserves_unrelated_receipt_change(self):
        self._configure_content_cards_project()
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        project["reviews"].append({
            "id": "graphic-motion-preview", "revision": 1, "status": "approved",
            "depends_on": ["graphic-motion"], "based_on": {"graphic-motion": 2},
            "snapshot_etag": "graphic-snapshot", "evidence_hashes": ["sha256:graphic"],
            "decision_mode": "human", "actor": "first-reviewer", "rationale": "Initial decision",
        })
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})

        def external_receipt_change():
            current = json.loads(self.project_path.read_text(encoding="utf-8"))
            receipt = next(item for item in current["reviews"] if item["id"] == "graphic-motion-preview")
            receipt.update({"actor": "external-reviewer", "rationale": "Updated external decision"})
            self.project_path.write_text(json.dumps(current), encoding="utf-8")

        self.service._before_final_cas = external_receipt_change
        response = self.service.handle_request({
            "verb": "review.record", "project_id": opened["project_id"], "operation": "content-cards",
            "read_set": self._read_set(opened["snapshot"], "content-cards"), "decision": {
                "review_id": "content-cards-preview-r1", "decision": "approved", "snapshot_etag": opened["snapshot"]["snapshot_etag"],
                "evidence_hashes": [self.preview_hash], "actor": "local-user", "rationale": "Current evidence",
            },
        })

        self.assertTrue(response["ok"])
        committed = json.loads(self.project_path.read_text(encoding="utf-8"))
        unrelated = next(item for item in committed["reviews"] if item["id"] == "graphic-motion-preview")
        target = next(item for item in committed["reviews"] if item["id"] == "content-cards-preview-r1")
        self.assertEqual(("external-reviewer", "Updated external decision"),
                         (unrelated["actor"], unrelated["rationale"]))
        self.assertEqual(("approved", "Current evidence"), (target["status"], target["rationale"]))

    def test_any_failure_after_prepare_quarantines_live_registration_and_preserves_journal(self):
        for boundary in ("stage", "replace-plan", "replace-project", "validate", "hash", "mark-committed", "unlink"):
            with self.subTest(boundary=boundary):
                self._configure_content_cards_project()
                service = ProtocolService()
                opened = service.handle_request({"verb": "open_project", "project_root": str(self.root)})
                journal = self.root / "work" / ".editor" / "transaction.json"
                original_atomic = service._atomic_write
                original_unlink = Path.unlink

                service._after_prepare = lambda: (_ for _ in ()).throw(OSError("injected stage failure")) if boundary == "stage" else None
                def after_replace(path):
                    if boundary == "replace-plan" and path == self.plan:
                        raise OSError("injected plan replacement failure")
                    if boundary == "replace-project" and path == self.project_path:
                        raise OSError("injected project replacement failure")
                service._after_replace = after_replace
                service._before_post_commit_validation = lambda: (_ for _ in ()).throw(OSError("injected validation failure")) if boundary == "validate" else None
                service._before_hash_verification = lambda: (_ for _ in ()).throw(OSError("injected hash failure")) if boundary == "hash" else None

                atomic_calls = 0
                def fail_atomic(path, data):
                    nonlocal atomic_calls
                    atomic_calls += 1
                    if boundary == "mark-committed" and atomic_calls == 2:
                        raise OSError("injected marker failure")
                    return original_atomic(path, data)

                def fail_unlink(path, *args, **kwargs):
                    if boundary == "unlink" and Path(path) == journal:
                        raise OSError("injected unlink failure")
                    return original_unlink(path, *args, **kwargs)

                with mock.patch.object(service, "_atomic_write", side_effect=fail_atomic), \
                        mock.patch.object(Path, "unlink", fail_unlink):
                    response = service.handle_request({
                        "verb": "plan.update", "project_id": opened["project_id"],
                        "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
                        "review": self._cards_review(copy=f"Failure {boundary}"),
                    })

                self.assertFalse(response["ok"])
                self.assertTrue(journal.exists(), boundary)
                retry = service.handle_request({
                    "verb": "plan.update", "project_id": opened["project_id"],
                    "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"),
                    "review": self._cards_review(copy="Retry"),
                })
                self.assertEqual("project is in recovery quarantine", retry["error"])
                journal.unlink(missing_ok=True)

    def test_open_project_does_not_recover_while_a_live_mutation_lease_is_held(self):
        self._configure_content_cards_project()
        journal = self.root / "work" / ".editor" / "transaction.json"
        journal.parent.mkdir(exist_ok=True)
        project_bytes = self.project_path.read_bytes()
        journal.write_text(json.dumps({"schema_version": 1, "transaction_id": str(uuid.uuid4()),
            "operation": "content-cards", "verb": "review.record", "state": "prepared", "files": [{
                "path": "work/project.json", "old_hash": hashlib.sha256(project_bytes).hexdigest(),
                "new_hash": hashlib.sha256(project_bytes).hexdigest(), "new_content": project_bytes.decode(),
            }]}), encoding="utf-8")
        lease = self.service._acquire_lease(self.root)
        try:
            response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})
        finally:
            self.service._release_lease(lease)

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertIn("busy during recovery", response["snapshot"]["errors"][0])
        self.assertTrue(journal.exists())

    def test_review_record_rejects_stale_upstream_dependencies(self):
        self._configure_content_cards_project()
        project = json.loads(self.project_path.read_text(encoding="utf-8"))
        captions = copy.deepcopy(project["operations"][0])
        captions.update({"id": "captions", "revision": 2, "status": "approved", "depends_on": [], "based_on": {}, "plan": None})
        cards = project["operations"][0]
        cards["depends_on"] = ["captions"]
        cards["based_on"] = {"captions": 1}
        cards["status"] = "stale"
        project["operations"].insert(0, captions)
        project["sequences"]["main"]["operations"] = ["captions", "content-cards", "graphic-motion"]
        self.project_path.write_text(json.dumps(project), encoding="utf-8")
        project["reviews"][0]["snapshot_etag"] = build_snapshot(self.root)["snapshot_etag"]
        self.project_path.write_text(json.dumps(project), encoding="utf-8")
        opened = self.service.handle_request({"verb": "open_project", "project_root": str(self.root)})
        decision = {"review_id": "content-cards-preview-r1", "decision": "approved", "snapshot_etag": opened["snapshot"]["snapshot_etag"],
                    "evidence_hashes": [self.preview_hash], "actor": "local-user", "rationale": "Looks correct"}

        response = self.service.handle_request({"verb": "review.record", "project_id": opened["project_id"],
            "operation": "content-cards", "read_set": self._read_set(opened["snapshot"], "content-cards"), "decision": decision})

        self.assertFalse(response["ok"])
        self.assertIn("current dependencies", response["error"])

    def test_crafted_recovery_journals_are_quarantined(self):
        self._configure_content_cards_project()
        project_bytes = self.project_path.read_bytes()
        cases = (
            [{"path": "input/source.mp4", "old_hash": hashlib.sha256(self.source.read_bytes()).hexdigest(), "new_hash": hashlib.sha256(b"owned").hexdigest(), "new_content": "owned"}],
            [{"path": "work/project.json", "old_hash": hashlib.sha256(project_bytes).hexdigest(), "new_hash": hashlib.sha256(project_bytes).hexdigest(), "new_content": project_bytes.decode()}] * 2,
        )
        for files in cases:
            with self.subTest(files=files):
                journal = self.root / "work" / ".editor" / "transaction.json"
                journal.parent.mkdir(exist_ok=True)
                journal.write_text(json.dumps({"schema_version": 1, "transaction_id": str(uuid.uuid4()),
                    "operation": "content-cards", "verb": "plan.update", "state": "prepared", "files": files}), encoding="utf-8")
                response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})
                self.assertTrue(response["snapshot"]["read_only"])
                journal.unlink(missing_ok=True)

    def test_committed_recovery_requires_every_target_at_new_hash(self):
        self._configure_content_cards_project()
        project_bytes = self.project_path.read_bytes()
        plan_bytes = self.plan.read_bytes()
        journal = self.root / "work" / ".editor" / "transaction.json"
        journal.parent.mkdir(exist_ok=True)
        journal.write_text(json.dumps({"schema_version": 1, "transaction_id": str(uuid.uuid4()),
            "operation": "content-cards", "verb": "plan.update", "state": "committed", "files": [
                {"path": "work/content-cards/cards-plan.json", "old_hash": hashlib.sha256(plan_bytes).hexdigest(), "new_hash": "1" * 64, "new_content": "{}"},
                {"path": "work/project.json", "old_hash": hashlib.sha256(project_bytes).hexdigest(), "new_hash": "2" * 64, "new_content": "{}"},
            ]}), encoding="utf-8")

        response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})

        self.assertTrue(response["snapshot"]["read_only"])

    def test_recovery_rejects_invalid_proposed_content_cards_plan_before_replay_or_removal(self):
        self._configure_content_cards_project()
        old_project = self.project_path.read_bytes()
        old_plan = self.plan.read_bytes()
        new_project = json.loads(old_project)
        next(item for item in new_project["operations"] if item["id"] == "content-cards")["revision"] = 2
        new_project = (json.dumps(new_project, indent=2) + "\n").encode()
        invalid_plan = b'{"schema_version": 1, "cards": "invalid"}\n'
        self.plan.write_bytes(invalid_plan)
        journal = self._write_journal("prepared", old_project, old_plan, new_project, invalid_plan)

        response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertTrue(journal.exists())
        self.assertEqual(old_project, self.project_path.read_bytes())

    def test_recovery_rejects_an_all_old_invalid_proposal_before_removing_journal(self):
        self._configure_content_cards_project()
        old_project = self.project_path.read_bytes()
        old_plan = self.plan.read_bytes()
        new_project = json.loads(old_project)
        next(item for item in new_project["operations"] if item["id"] == "content-cards")["revision"] = 2
        new_project = (json.dumps(new_project, indent=2) + "\n").encode()
        invalid_plan = b'{"schema_version": 1, "cards": "invalid"}\n'
        journal = self._write_journal("prepared", old_project, old_plan, new_project, invalid_plan)

        response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertTrue(journal.exists())
        self.assertEqual(old_plan, self.plan.read_bytes())

    def test_committed_all_new_recovery_validates_plan_before_removing_journal(self):
        self._configure_content_cards_project()
        old_project = self.project_path.read_bytes()
        old_plan = self.plan.read_bytes()
        new_project = json.loads(old_project)
        next(item for item in new_project["operations"] if item["id"] == "content-cards")["revision"] = 2
        new_project = (json.dumps(new_project, indent=2) + "\n").encode()
        invalid_plan = b'{"schema_version": 1, "cards": "invalid"}\n'
        self.project_path.write_bytes(new_project)
        self.plan.write_bytes(invalid_plan)
        journal = self._write_journal("committed", old_project, old_plan, new_project, invalid_plan)

        response = ProtocolService().handle_request({"verb": "open_project", "project_root": str(self.root)})

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertTrue(journal.exists())

    def _write_journal(self, state, old_project, old_plan, new_project, new_plan):
        journal = self.root / "work" / ".editor" / "transaction.json"
        journal.parent.mkdir(exist_ok=True)
        journal.write_text(json.dumps({"schema_version": 1, "transaction_id": str(uuid.uuid4()),
            "operation": "content-cards", "verb": "plan.update", "state": state, "files": [
                {"path": "work/content-cards/cards-plan.json", "old_hash": hashlib.sha256(old_plan).hexdigest(),
                 "new_hash": hashlib.sha256(new_plan).hexdigest(), "new_content": new_plan.decode()},
                {"path": "work/project.json", "old_hash": hashlib.sha256(old_project).hexdigest(),
                 "new_hash": hashlib.sha256(new_project).hexdigest(), "new_content": new_project.decode()},
            ]}), encoding="utf-8")
        return journal

    def _configure_content_cards_project(self, approved_plan=False):
        self.plan = self.root / "work" / "content-cards" / "cards-plan.json"
        self.plan.parent.mkdir(exist_ok=True)
        plan = {
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "brief": {"theme": "almanac", "target_card_count": 1},
            "cards": [
                {
                    "id": "card-001",
                    "card_type": "intro",
                    "evidence_refs": ["moment-1"],
                    "copy": {"status": "draft", "suggested_text": "Original copy", "display": {"title": None}},
                    "placement": {"status": "draft", "region": None},
                    "visual_treatment": {"status": "draft", "layout": "default"},
                }
            ],
        }
        if approved_plan:
            scripts = self.root.parents[0]
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "video-add-content-cards" / "scripts"))
            import apply_cards_review
            plan = apply_cards_review.apply_review(plan, self._cards_review(copy="Original copy", placement="bottom"))
        self.plan.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        project = self._project()
        project["sequences"]["main"]["operations"] = ["content-cards", "graphic-motion"]
        project["operations"] = [
            {**project["operations"][0], "id": "content-cards", "status": "approved", "plan": "content-cards/cards-plan.json"},
            {**project["operations"][0], "id": "graphic-motion", "status": "approved", "revision": 2,
             "depends_on": ["content-cards"], "based_on": {"content-cards": 1}, "plan": None},
        ]
        self.preview_path = self.root / "review" / "03-content-cards" / "preview.png"
        self.preview_path.parent.mkdir(parents=True, exist_ok=True)
        self.preview_path.write_bytes(b"current preview bytes")
        self.preview_hash = "sha256:" + hashlib.sha256(self.preview_path.read_bytes()).hexdigest()
        project["reviews"] = [{
            "id": "content-cards-preview-r1", "revision": 1, "status": "draft",
            "depends_on": ["content-cards"], "based_on": {"content-cards": 1},
            "snapshot_etag": "pending", "evidence_hashes": [self.preview_hash],
        }]
        project["render"] = {"status": "verified", "output": "../final/final.mp4"}
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
        project["reviews"][0]["snapshot_etag"] = build_snapshot(self.root)["snapshot_etag"]
        self.project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")

    def _cards_review(self, copy="Original copy", placement="bottom"):
        return {"schema_version": 1, "cards": [{
            "id": "card-001", "selected": True, "copy": copy,
            "placement": placement, "visual_treatment": "default",
        }]}

    @staticmethod
    def _read_set(snapshot, operation_id):
        resources = snapshot["resources"]
        project = next(item for item in resources if item["kind"] == "project")
        plan = next(item for item in resources if item.get("operation_id") == operation_id)
        operation = next(item for item in snapshot["view"]["operations"] if item["id"] == operation_id)
        return {"project": project["etag"], "operation": operation["etag"], "plan": plan["etag"]}

    @staticmethod
    def _timeline_read_set(snapshot):
        resources = snapshot["resources"]
        project = next(item for item in resources if item["kind"] == "project")
        timeline = next(item for item in resources if item["kind"] == "timeline")
        operation = next(item for item in snapshot["view"]["operations"] if item["id"] == "cut")
        plans = {
            item["operation_id"]: item["etag"]
            for item in resources
            if item["kind"] == "plan" and item.get("operation_id")
        }
        return {"project": project["etag"], "operation": operation["etag"], "timeline": timeline["etag"], "plans": plans}

    def _configure_cut_project(self):
        project = self._project()
        cut = {
            "id": "cut",
            "revision": 1,
            "status": "verified",
            "depends_on": [],
            "based_on": {},
            "target": {"sequence": "main", "scope": "full"},
            "effects": {
                "changes_timeline": True,
                "changes_geometry": False,
                "changes_video_pixels": True,
                "changes_audio": True,
            },
            "outputs": [],
        }
        captions = project["operations"][0]
        captions.update({
            "status": "approved",
            "depends_on": ["cut"],
            "based_on": {"cut": 1},
        })
        project["operations"] = [cut, captions]
        project["sequences"]["main"]["operations"] = ["cut", "captions"]
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

    def _write_project(self):
        self.project_path.write_text(json.dumps(self._project()), encoding="utf-8")

    def _project(self):
        stat = self.source.stat()
        return {
            "schema_version": 1,
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                    "duration_s": 1.0,
                },
            },
            "active_sequence": "main",
            "sequences": {
                "main": {
                    "timeline": "timeline.json",
                    "operations": ["captions"],
                }
            },
            "operations": [
                {
                    "id": "captions",
                    "revision": 1,
                    "status": "draft",
                    "depends_on": [],
                    "based_on": {},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": True,
                        "changes_audio": False,
                    },
                    "plan": "captions/captions-plan.json",
                    "outputs": [],
                }
            ],
            "reviews": [],
        }


if __name__ == "__main__":
    unittest.main()
