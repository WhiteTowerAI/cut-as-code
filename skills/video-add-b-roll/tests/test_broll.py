"""Focused B-roll plan and review contract tests."""

import copy
import base64
import contextlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT.parent / "video-understand" / "scripts")]
import broll_plan
import projectlib
import pexels
import build_review_page
import normalize_broll
import check_broll


class _BrollFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "work/cache/b-roll").mkdir(parents=True)
        (self.root / "work/understand").mkdir()
        self.timeline = {"schema_version": 1, "timeline_id": "main", "source_duration_s": 10.0, "program_duration_s": 10.0, "fps": {"num": 30, "den": 1}, "clips": [{"id": "one", "source_range": {"start_s": 0, "end_s": 10}, "program_range": {"start_s": 0, "end_s": 10}, "speed": 1.0, "decision_ref": "keep"}]}
        self.transcript = {"segments": [{"words": [{"word": "factory", "start": 1.0, "end": 2.0}, {"word": "process", "start": 2.0, "end": 3.0}, {"word": "output", "start": 3.0, "end": 4.0}, {"word": "quality", "start": 4.0, "end": 5.0}]}]}
        self.timeline_path = self.root / "work/timeline.json"
        self.transcript_path = self.root / "work/understand/transcript.json"
        projectlib.write_json(self.timeline_path, self.timeline)
        projectlib.write_json(self.transcript_path, self.transcript)
        self.grade_plan_path = self.root / "work/color-grade/grade-plan.json"
        self.selected_lut_path = self.root / "final/selected-color-look.cube"
        self.selected_lut_path.parent.mkdir(parents=True)
        self.selected_lut_path.write_text("TITLE local\nLUT_3D_SIZE 2\n", encoding="utf-8")
        self.grade_plan = {"schema_version": 1, "selected_lut": "../../final/selected-color-look.cube"}
        projectlib.write_json(self.grade_plan_path, self.grade_plan)
        asset = self.root / "work/cache/b-roll/factory.mp4"
        asset.write_bytes(b"asset")
        self.mapped_words = projectlib.map_transcript_to_timeline(self.transcript, self.timeline)["segments"][0]["words"]
        candidate = {"id": "asset", "media_type": "video", "cache_path": "cache/b-roll/factory.mp4", "sha256": broll_plan.sha256_file(asset), "bytes": asset.stat().st_size, "duration_s": 2.0, "probe": {"duration_s": 2.0, "width": 1920, "height": 1080}, "provenance": {"source_type": "local", "creator": "me", "license": "owned", "retrieval_time": "2026-07-23T00:00:00Z", "original_path": "input/factory.mp4"}}
        self.plan = {"schema_version": 1, "timeline_id": "main", "timebase": "program", "program_duration_s": 10.0, "dependencies": ["understanding", "cut", "color-grade"], "based_on": {"understanding": 1, "cut": 2, "color-grade": 3}, "input_hashes": {"transcript_sha256": broll_plan.sha256_file(self.transcript_path), "timeline_sha256": broll_plan.sha256_file(self.timeline_path), "grade_plan_sha256": broll_plan.sha256_file(self.grade_plan_path), "selected_lut_sha256": broll_plan.sha256_file(self.selected_lut_path), "review_video_sha256": "b" * 64}, "brief": {"density": "selective"}, "decision": None, "review": None, "shots": [{"id": "shot", "program_range": {"start_s": 1.0, "end_s": 2.0}, "source_ranges": [{"clip_id": "one", "start_s": 1.0, "end_s": 2.0}], "transcript_evidence": {"words": [self.mapped_words[0]]}, "editorial_reason": "Supports the statement.", "visual_intent": "Factory work.", "queries": ["factory assembly", "manufacturing line"], "candidates": [candidate], "selected": None, "status": "candidates_ready"}]}
        self.project = {"active_sequence": "main", "sequences": {"main": {"operations": ["cut", "color-grade"]}}, "operations": [{"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2}, {"id": "color-grade", "revision": 3, "render": {"plan": "color-grade/grade-plan.json"}}]}
        self.project_path = self.root / "work/project.json"
        projectlib.write_json(self.project_path, self.project)

    def tearDown(self): self.temp.cleanup()

    def review(self, **extra):
        return self.review_for(self.plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}], **extra)

    def review_for(self, plan, shots, rationale="Relevant footage.", timestamp="2026-07-23T12:00:00Z", **extra):
        return {"review_id": "123e4567-e89b-12d3-a456-426614174000", "plan_sha256": broll_plan.canonical_sha256(broll_plan.review_subject(plan)), "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "review_video_sha256": plan["input_hashes"]["review_video_sha256"], "rationale": rationale, "timestamp": timestamp, "shots": shots, **extra}

    def pexels_candidate(self):
        candidate = copy.deepcopy(self.plan["shots"][0]["candidates"][0])
        candidate.update({
            "provider_id": 101,
            "file_id": 202,
            "download_url": "https://videos.pexels.com/factory.mp4",
            "width": 1920,
            "height": 1080,
            "duration_s": 2.0,
        })
        candidate["provenance"] = {
            "source_type": "pexels",
            "provider_id": 101,
            "source_url": "https://www.pexels.com/video/factory-101/",
            "creator": "Pexels Creator",
            "license": "Pexels License",
            "license_url": "https://www.pexels.com/license/",
            "terms_url": "https://www.pexels.com/terms-of-service/",
            "retrieval_time": "2026-07-23T00:00:00Z",
            "download_url": "https://videos.pexels.com/factory.mp4",
            "dimensions": {"width": 1920, "height": 1080},
            "duration_s": 2.0,
        }
        return candidate


class BrollPlanTests(_BrollFixture, unittest.TestCase):

    def test_rejects_invalid_overlapping_or_out_of_bounds_ranges(self):
        plan = copy.deepcopy(self.plan); duplicate = copy.deepcopy(plan["shots"][0]); duplicate["id"] = "second"; duplicate["program_range"] = {"start_s": 1.5, "end_s": 3}; plan["shots"].append(duplicate)
        self.assertIn("second program range overlaps shot", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["program_range"] = {"start_s": -1, "end_s": 1}
        self.assertIn("shot program range is outside timeline", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_evidence_word_must_exactly_match_mapped_transcript_word(self):
        plan = copy.deepcopy(self.plan); plan["shots"][0]["transcript_evidence"]["words"][0]["source_range"]["start_s"] = 1.1
        self.assertIn("shot transcript evidence word is not mapped from transcript", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["transcript_evidence"]["words"][0]["program_range"]["end_s"] = 2.1
        self.assertIn("shot transcript evidence word is not mapped from transcript", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_apply_review_rejects_human_without_action_and_agent_blank_rationale(self):
        with self.assertRaisesRegex(ValueError, "explicit_user_action"):
            broll_plan.apply_review(self.plan, self.review(rationale="ok"), mode="human", actor="person", rationale="ok")
        with self.assertRaisesRegex(ValueError, "rationale"):
            broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale=" ")

    def test_apply_review_selects_or_skips_every_shot_and_binds_receipt(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual("selected", approved["shots"][0]["status"])
        self.assertEqual(broll_plan.canonical_sha256(broll_plan.review_subject(approved)), approved["review"]["plan_sha256"])
        self.assertEqual(broll_plan.canonical_sha256(broll_plan.candidate_manifest(approved)), approved["review"]["candidate_manifest_sha256"])
        self.assertEqual([approved["shots"][0]["candidates"][0]["sha256"]], approved["review"]["selected_asset_sha256"])
        self.assertEqual(self.plan["input_hashes"]["review_video_sha256"], approved["review"]["review_video_sha256"])
        skipped = broll_plan.apply_review(self.plan, self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage.", review_id="123e4567-e89b-12d3-a456-426614174010"), mode="agent", actor="agent", rationale="No useful footage.")
        self.assertEqual(("skipped", None), (skipped["shots"][0]["status"], skipped["shots"][0]["selected"]))
        self.assertEqual(["shot"], skipped["review"]["decision_skipped_shot_ids"])
        self.assertEqual([], broll_plan.validate_plan(skipped, self.timeline, self.transcript))

    def test_review_decisions_bind_video_trim_and_image_motion(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual([{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}], approved["review"]["decisions"])
        changed = copy.deepcopy(approved)
        changed["shots"][0]["selected"]["source_trim"]["end_s"] = 0.5
        self.assertIn("review decisions do not match current plan", broll_plan.validate_plan(changed, self.timeline, self.transcript))

        image_plan = copy.deepcopy(self.plan)
        image_plan["shots"][0]["candidates"][0]["media_type"] = "image"
        image_review = self.review_for(image_plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "ken_burns": {"direction": "zoom-in"}}])
        image = broll_plan.apply_review(image_plan, image_review, mode="agent", actor="agent", rationale="Relevant footage.")
        image["shots"][0]["selected"]["ken_burns"]["direction"] = "pan-left"
        self.assertIn("review decisions do not match current plan", broll_plan.validate_plan(image, self.timeline, self.transcript))

    def test_review_id_must_be_a_uuid_when_applied_or_persisted(self):
        review = self.review(review_id="review-1")
        with self.assertRaisesRegex(ValueError, "review_id must be a UUID"):
            broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        approved["review"]["review_id"] = "review-1"
        self.assertIn("review_id must be a UUID", broll_plan.validate_plan(approved, self.timeline, self.transcript))

    def test_apply_review_rejects_invalid_video_trim_without_null_decisions(self):
        missing = object()
        cases = [
            missing,
            None,
            [],
            {},
            {"start_s": -0.1, "end_s": 1},
            {"start_s": 1, "end_s": 1},
            {"start_s": 2, "end_s": 1},
            {"start_s": "bad", "end_s": 1},
            {"start_s": 0, "end_s": float("nan")},
            {"start_s": 0, "end_s": float("inf")},
        ]
        for value in cases:
            plan = copy.deepcopy(self.plan)
            plan["shots"][0]["candidates"][0]["duration_s"] = 2.0
            entry = {"id": "shot", "decision": "select", "candidate_id": "asset"}
            if value is not missing:
                entry["source_trim"] = copy.deepcopy(value)
            review = self.review_for(plan, [entry])
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "shot select requires a valid source_trim"):
                    broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0]["probe"] = {"duration_s": 1.0}
        review = self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1.1}}])
        with self.assertRaisesRegex(ValueError, "shot select requires a valid source_trim"):
            broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_apply_review_rejects_boolean_and_string_trim_endpoints(self):
        trims = [
            {"start_s": False, "end_s": 1},
            {"start_s": True, "end_s": 2},
            {"start_s": 0, "end_s": True},
            {"start_s": False, "end_s": True},
            {"start_s": True, "end_s": True},
            {"start_s": 0, "end_s": False},
            {"start_s": "0", "end_s": 1},
            {"start_s": 0, "end_s": "1"},
            {"start_s": "0", "end_s": "1"},
            {"start_s": False, "end_s": "1"},
            {"start_s": "0", "end_s": True},
        ]
        for trim in trims:
            review = self.review_for(self.plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": trim}])
            with self.subTest(trim=trim):
                with self.assertRaisesRegex(ValueError, "shot select requires a valid source_trim"):
                    broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_apply_review_contains_oversized_integer_trim_endpoints(self):
        huge = 10 ** 10000
        trims = [
            ("positive start", {"start_s": huge, "end_s": 1}),
            ("negative start", {"start_s": -huge, "end_s": 1}),
            ("positive end", {"start_s": 0, "end_s": huge}),
            ("negative end", {"start_s": 0, "end_s": -huge}),
        ]
        for name, trim in trims:
            review = self.review_for(self.plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": trim}])
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "shot select requires a valid source_trim"):
                    broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_candidate_durations_reject_non_json_finite_numbers(self):
        huge = 10 ** 10000
        invalid = [
            ("true", True),
            ("false", False),
            ("numeric string", "2"),
            ("nan", float("nan")),
            ("infinity", float("inf")),
            ("negative infinity", float("-inf")),
            ("huge positive", huge),
            ("huge negative", -huge),
        ]
        for location in ("duration_s", "probe"):
            for name, value in invalid:
                plan = copy.deepcopy(self.plan)
                candidate = plan["shots"][0]["candidates"][0]
                if location == "duration_s":
                    candidate[location] = value
                else:
                    candidate[location] = {"duration_s": value}
                if name.startswith("huge"):
                    review = self.review()
                else:
                    review = self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}])
                with self.subTest(action="apply", location=location, name=name):
                    with self.assertRaises(ValueError):
                        broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

                persisted = copy.deepcopy(plan)
                persisted["shots"][0].update({"status": "selected", "selected": {"candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}})
                with self.subTest(action="validate", location=location, name=name):
                    field = "duration_s" if location == "duration_s" else "probe.duration_s"
                    self.assertIn(f"shot candidate asset {field} must be a finite positive number", broll_plan.validate_plan(persisted, self.timeline, self.transcript))

    def test_candidate_durations_are_validated_before_review(self):
        huge = 10 ** 10000
        invalid = [
            ("true", True),
            ("false", False),
            ("numeric string", "2"),
            ("zero", 0),
            ("negative", -1),
            ("nan", float("nan")),
            ("infinity", float("inf")),
            ("negative infinity", float("-inf")),
            ("huge positive", huge),
            ("huge negative", -huge),
        ]
        for location in ("duration_s", "probe.duration_s"):
            for name, value in invalid:
                plan = copy.deepcopy(self.plan)
                candidate = plan["shots"][0]["candidates"][0]
                if location == "duration_s":
                    candidate["duration_s"] = value
                else:
                    candidate["probe"] = {"duration_s": value}
                with self.subTest(location=location, value=name):
                    self.assertIn(
                        f"shot candidate asset {location} must be a finite positive number",
                        broll_plan.validate_plan(plan, self.timeline, self.transcript),
                    )

        plan = copy.deepcopy(self.plan)
        candidate = plan["shots"][0]["candidates"][0]
        candidate.pop("duration_s")
        candidate.pop("probe")
        self.assertIn(
            "shot candidate asset video requires a finite positive probe.duration_s",
            broll_plan.validate_plan(plan, self.timeline, self.transcript),
        )

        for value in (None, [], "probe", 1, 1.0, True):
            plan = copy.deepcopy(self.plan)
            plan["shots"][0]["candidates"][0]["probe"] = value
            with self.subTest(probe=repr(value)):
                self.assertIn(
                    "shot candidate asset probe must be an object",
                    broll_plan.validate_plan(plan, self.timeline, self.transcript),
                )

    def test_video_candidates_require_probe_duration_and_images_remain_exempt(self):
        direct_only = copy.deepcopy(self.plan)
        candidate = direct_only["shots"][0]["candidates"][0]
        candidate["duration_s"] = 999
        candidate.pop("probe")
        self.assertTrue(any("probe.duration_s" in error for error in broll_plan.validate_plan(direct_only, self.timeline, self.transcript)))
        with self.assertRaisesRegex(ValueError, "probe.duration_s"):
            broll_plan.apply_review(direct_only, self.review_for(direct_only, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}]), mode="agent", actor="agent", rationale="Relevant footage.")

        for probe_duration in (1, 1.5):
            plan = copy.deepcopy(self.plan)
            plan["shots"][0]["candidates"][0].pop("duration_s")
            plan["shots"][0]["candidates"][0]["probe"] = {"duration_s": probe_duration}
            with self.subTest(probe_duration=probe_duration):
                self.assertEqual([], broll_plan.validate_plan(plan, self.timeline, self.transcript))

        image = copy.deepcopy(self.plan)
        candidate = image["shots"][0]["candidates"][0]
        candidate["media_type"] = "image"
        candidate.pop("duration_s")
        candidate.pop("probe")
        self.assertEqual([], broll_plan.validate_plan(image, self.timeline, self.transcript))

    def test_probe_duration_is_authoritative_for_video_trims(self):
        shorter_direct = copy.deepcopy(self.plan)
        shorter_direct["shots"][0]["candidates"][0].update({"duration_s": 0.5, "probe": {"duration_s": 2}})
        try:
            accepted = broll_plan.apply_review(
                shorter_direct,
                self.review_for(shorter_direct, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}]),
                mode="agent", actor="agent", rationale="Relevant footage.",
            )
        except ValueError as exc:
            self.fail(f"probe-bounded trim was rejected: {exc}")
        self.assertEqual({"start_s": 0, "end_s": 1}, accepted["shots"][0]["selected"]["source_trim"])
        self.assertEqual([], broll_plan.validate_plan(accepted, self.timeline, self.transcript))

        longer_direct = copy.deepcopy(self.plan)
        longer_direct["shots"][0]["candidates"][0].update({"duration_s": 999, "probe": {"duration_s": 1}})
        review = self.review_for(longer_direct, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 2}}])
        with self.assertRaisesRegex(ValueError, "valid source_trim"):
            broll_plan.apply_review(longer_direct, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_apply_review_requires_authoritative_duration_and_bounded_trim(self):
        cases = [
            ({"remove": ("duration_s", "probe")}, {"start_s": 0, "end_s": 1}, "duration"),
            ({"duration_s": 0.5, "remove": ("probe",)}, {"start_s": 0, "end_s": 1}, "probe.duration_s"),
            ({"duration_s": 2.0, "remove": ("probe",)}, {"start_s": 0, "end_s": 999}, "probe.duration_s"),
            ({"duration_s": 2.0, "probe": {"duration_s": 0}}, {"start_s": 0, "end_s": 1}, "probe.duration_s"),
            ({"duration_s": 0, "probe": {"duration_s": 2.0}}, {"start_s": 0, "end_s": 1}, "duration_s"),
        ]
        for change, trim, message in cases:
            plan = copy.deepcopy(self.plan)
            candidate = plan["shots"][0]["candidates"][0]
            for key in change.pop("remove", ()):
                candidate.pop(key, None)
            candidate.update(change)
            review = self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": trim}])
            with self.subTest(change=change, trim=trim):
                with self.assertRaisesRegex(ValueError, message):
                    broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual({"start_s": 0, "end_s": 1}, approved["shots"][0]["selected"]["source_trim"])

    def test_apply_review_rejects_invalid_image_motion_without_null_decisions(self):
        missing = object()
        for value in (missing, None, [], {}, {"direction": None}, {"direction": []}, {"direction": "spin"}):
            plan = copy.deepcopy(self.plan)
            plan["shots"][0]["candidates"][0]["media_type"] = "image"
            entry = {"id": "shot", "decision": "select", "candidate_id": "asset"}
            if value is not missing:
                entry["ken_burns"] = copy.deepcopy(value)
            review = self.review_for(plan, [entry])
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "shot select requires a valid ken_burns direction"):
                    broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_every_valid_selected_media_control_immediately_validates(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0].update({"duration_s": 2.0, "probe": {"duration_s": 2.0}})
        video = broll_plan.apply_review(plan, self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 2}}]), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual([], broll_plan.validate_plan(video, self.timeline, self.transcript))

        for direction in ("zoom-in", "pan-left", "pan-right"):
            plan = copy.deepcopy(self.plan)
            plan["shots"][0]["candidates"][0]["media_type"] = "image"
            review = self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "ken_burns": {"direction": direction}}])
            approved = broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")
            with self.subTest(direction=direction):
                self.assertEqual([], broll_plan.validate_plan(approved, self.timeline, self.transcript))

    def test_review_decision_manifest_rejects_reorder_omit_duplicate_and_malformed(self):
        plan = copy.deepcopy(self.plan)
        second = copy.deepcopy(plan["shots"][0])
        second.update({"id": "second", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": [self.mapped_words[2]]}})
        second["candidates"][0]["id"] = "asset-2"
        plan["shots"].append(second)
        entries = [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}, {"id": "second", "decision": "select", "candidate_id": "asset-2", "source_trim": {"start_s": 0, "end_s": 1}}]
        approved = broll_plan.apply_review(plan, self.review_for(plan, entries), mode="agent", actor="agent", rationale="Relevant footage.")
        decisions = approved["review"]["decisions"]
        for value in (list(reversed(decisions)), decisions[:1], [decisions[0], decisions[0]], None, [{"bad": []}]):
            tampered = copy.deepcopy(approved)
            tampered["review"]["decisions"] = value
            with self.subTest(value=value):
                self.assertIn("review decisions do not match current plan", broll_plan.validate_plan(tampered, self.timeline, self.transcript))

    def test_exported_rationale_and_timestamp_are_required_and_bound(self):
        valid = self.review(rationale="  Exact reason.  ", timestamp="2026-07-23T12:00:00Z")
        approved = broll_plan.apply_review(self.plan, valid, mode="agent", actor="agent", rationale="Exact reason.")
        self.assertEqual("Exact reason.", approved["review"]["rationale"])
        self.assertEqual("2026-07-23T12:00:00Z", approved["review"]["timestamp"])
        cases = []
        for value in (None, " "):
            review = self.review(); review["rationale"] = value; cases.append((review, "Relevant footage.", "exported rationale"))
        cases.append((self.review(rationale="Other reason."), "Relevant footage.", "exported rationale"))
        for value in (None, "not-a-time", "2026-07-23T12:00:00"):
            review = self.review(); review["timestamp"] = value; cases.append((review, "Relevant footage.", "timestamp"))
        for review, rationale, message in cases:
            with self.subTest(message=message, value=review.get("rationale") or review.get("timestamp")):
                with self.assertRaisesRegex(ValueError, message):
                    broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale=rationale)

    def test_apply_review_rejects_old_or_tampered_artifact_bindings(self):
        for field in ("plan_sha256", "candidate_manifest_sha256", "review_video_sha256"):
            for value in (None, "0" * 64):
                review = self.review()
                if value is None:
                    review.pop(field)
                else:
                    review[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, field):
                        broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.")
        malformed = copy.deepcopy(self.plan)
        malformed["input_hashes"] = None
        with self.assertRaisesRegex(ValueError, "input_hashes"):
            broll_plan.apply_review(malformed, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")

    def test_review_subject_rejects_stale_candidates_ready_to_skipped_export(self):
        export = self.review()
        for receipt in (None, {"status": "draft", "decision_skipped_shot_ids": ["shot"]}):
            current = copy.deepcopy(self.plan)
            current["shots"][0]["status"] = "skipped"
            current["review"] = receipt
            with self.subTest(receipt=receipt), self.assertRaisesRegex(ValueError, "plan_sha256"):
                broll_plan.apply_review(current, export, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_mixed_pre_skipped_and_decision_skipped_receipt_validates(self):
        plan = copy.deepcopy(self.plan)
        pre_skipped = copy.deepcopy(plan["shots"][0])
        pre_skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": [self.mapped_words[2]]}, "candidates": [], "selected": None, "status": "skipped"})
        plan["shots"].append(pre_skipped)
        review = self.review_for(plan, [{"id": "shot", "decision": "skip"}, {"id": "already-skipped", "decision": "skip"}], rationale="Neither shot helps.")
        approved = broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Neither shot helps.")
        self.assertEqual(["shot"], approved["review"]["decision_skipped_shot_ids"])
        self.assertEqual([], broll_plan.validate_plan(approved, self.timeline, self.transcript))

    def test_apply_review_requires_pre_skipped_shots_to_remain_skipped(self):
        plan = copy.deepcopy(self.plan)
        skipped = copy.deepcopy(plan["shots"][0])
        skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": [self.mapped_words[2]]}, "status": "skipped"})
        skipped["candidates"][0]["id"] = "skipped-asset"
        plan["shots"].append(skipped)
        malicious = self.review_for(plan, [
            {"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}},
            {"id": "already-skipped", "decision": "select", "candidate_id": "skipped-asset", "source_trim": {"start_s": 0, "end_s": 1}},
        ])
        with self.assertRaisesRegex(ValueError, "already-skipped was already skipped and requires decision skip"):
            broll_plan.apply_review(plan, malicious, mode="agent", actor="agent", rationale="Relevant footage.")

        exact = self.review_for(plan, [
            {"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}},
            {"id": "already-skipped", "decision": "skip"},
        ])
        approved = broll_plan.apply_review(plan, exact, mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual("skipped", approved["shots"][1]["status"])
        self.assertEqual([], approved["review"]["decision_skipped_shot_ids"])

    def test_all_skipped_lifecycle_marker_controls_validation_and_registration(self):
        approved = broll_plan.apply_review(self.plan, self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage."), mode="agent", actor="agent", rationale="No useful footage.")
        self.assertEqual("approved", approved["review_status"])
        registered = broll_plan.register_operation(self._registration_project(), approved)
        self.assertFalse(any(item.get("id") == "b-roll" for item in registered["operations"]))

        missing_receipt = copy.deepcopy(approved)
        missing_receipt["decision"] = missing_receipt["review"] = None
        self.assertIn("review trust requires decision object", broll_plan.validate_plan(missing_receipt, self.timeline, self.transcript))
        with self.assertRaises(ValueError): broll_plan.register_operation(self._registration_project(), missing_receipt)

        missing_marker = copy.deepcopy(approved)
        missing_marker.pop("review_status")
        self.assertIn("review_status must be approved", broll_plan.validate_plan(missing_marker, self.timeline, self.transcript))
        with self.assertRaises(ValueError): broll_plan.register_operation(self._registration_project(), missing_marker)

        invalid_marker = copy.deepcopy(approved)
        invalid_marker["review_status"] = "draft"
        self.assertIn("review_status must be approved", broll_plan.validate_plan(invalid_marker, self.timeline, self.transcript))

        pre_review = copy.deepcopy(self.plan)
        pre_review["shots"][0]["status"] = "skipped"
        self.assertEqual([], broll_plan.validate_plan(pre_review, self.timeline, self.transcript))
        with self.assertRaises(ValueError): broll_plan.register_operation(self._registration_project(), pre_review)

    def test_decision_skipped_receipt_rejects_malformed_or_tampered_ids(self):
        approved = broll_plan.apply_review(self.plan, self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage."), mode="agent", actor="agent", rationale="No useful footage.")
        cases = [(None, "decision_skipped_shot_ids"), (["shot", "shot"], "decision_skipped_shot_ids"), (["unknown"], "decision_skipped_shot_ids"), ([["shot"]], "decision_skipped_shot_ids"), ([], "review plan SHA-256 does not match")]
        for value, message in cases:
            tampered = copy.deepcopy(approved)
            tampered["review"]["decision_skipped_shot_ids"] = value
            with self.subTest(value=value):
                self.assertTrue(any(message in error for error in broll_plan.validate_plan(tampered, self.timeline, self.transcript)))

    def test_approved_plan_with_nonstring_shot_id_returns_errors(self):
        approved = broll_plan.apply_review(self.plan, self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage."), mode="agent", actor="agent", rationale="No useful footage.")
        for shot_id in ([], 3):
            malformed = copy.deepcopy(approved)
            malformed["shots"][0]["id"] = shot_id
            with self.subTest(shot_id=shot_id):
                self.assertIn("shot id is required", broll_plan.validate_plan(malformed, self.timeline, self.transcript))

    def test_approved_plan_with_malformed_decision_inputs_returns_schema_and_receipt_errors(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        delete = object()
        cases = [
            ("shot non-object", [(("shots", 0), None)], "shot must be an object"),
            ("shot id missing", [(("shots", 0, "id"), delete)], "shot id is required"),
            ("shot id none", [(("shots", 0, "id"), None)], "shot id is required"),
            ("shot id list", [(("shots", 0, "id"), [])], "shot id is required"),
            ("candidates none", [(("shots", 0, "candidates"), None)], "shot candidates must be a list"),
            ("candidates scalar", [(("shots", 0, "candidates"), 3)], "shot candidates must be a list"),
            ("candidate non-object", [(("shots", 0, "candidates"), [[]])], "shot candidate must be an object"),
            ("candidate id missing", [(("shots", 0, "candidates", 0, "id"), delete)], "shot candidate id is required"),
            ("candidate id none", [(("shots", 0, "candidates", 0, "id"), None), (("shots", 0, "selected", "candidate_id"), None)], "shot candidate id is required"),
            ("candidate id list", [(("shots", 0, "candidates", 0, "id"), []), (("shots", 0, "selected", "candidate_id"), [])], "shot candidate id is required"),
            ("reviewer candidate", [(("shots", 0, "candidates"), [{"media_type": "video"}]), (("shots", 0, "selected", "candidate_id"), None)], "shot candidate id is required"),
            ("selected missing", [(("shots", 0, "selected"), delete)], "shot selected shot requires a selection"),
            ("selected none", [(("shots", 0, "selected"), None)], "shot selected shot requires a selection"),
            ("selected scalar", [(("shots", 0, "selected"), 3)], "shot selected shot requires a selection"),
            ("selected candidate id missing", [(("shots", 0, "selected", "candidate_id"), delete)], "shot selected candidate does not belong to shot"),
            ("selected candidate id none", [(("shots", 0, "selected", "candidate_id"), None)], "shot selected candidate does not belong to shot"),
            ("selected candidate id list", [(("shots", 0, "selected", "candidate_id"), [])], "shot selected candidate does not belong to shot"),
            ("selected candidate not found", [(("shots", 0, "selected", "candidate_id"), "missing")], "shot selected candidate does not belong to shot"),
            ("video trim missing", [(("shots", 0, "selected", "source_trim"), delete)], "shot selected video requires a valid source_trim"),
            ("video trim none", [(("shots", 0, "selected", "source_trim"), None)], "shot selected video requires a valid source_trim"),
            ("video trim list", [(("shots", 0, "selected", "source_trim"), [])], "shot selected video requires a valid source_trim"),
            ("video trim malformed", [(("shots", 0, "selected", "source_trim"), {"start_s": "bad"})], "shot selected video requires a valid source_trim"),
            ("image motion missing", [(("shots", 0, "candidates", 0, "media_type"), "image")], "shot selected image requires a non-empty ken_burns"),
            ("image motion none", [(("shots", 0, "candidates", 0, "media_type"), "image"), (("shots", 0, "selected", "ken_burns"), None)], "shot selected image requires a non-empty ken_burns"),
            ("image motion list", [(("shots", 0, "candidates", 0, "media_type"), "image"), (("shots", 0, "selected", "ken_burns"), [])], "shot selected image requires a non-empty ken_burns"),
            ("image motion empty", [(("shots", 0, "candidates", 0, "media_type"), "image"), (("shots", 0, "selected", "ken_burns"), {})], "shot selected image requires a non-empty ken_burns"),
            ("unknown media type", [(("shots", 0, "candidates", 0, "media_type"), "audio")], "shot candidate asset media_type is invalid"),
            ("media type list", [(("shots", 0, "candidates", 0, "media_type"), [])], "shot candidate asset media_type is invalid"),
            ("status missing", [(("shots", 0, "status"), delete)], "shot status is invalid"),
            ("status none", [(("shots", 0, "status"), None)], "shot status is invalid"),
            ("status list", [(("shots", 0, "status"), [])], "shot status is invalid"),
            ("normalized selection", [(("shots", 0, "status"), "normalized"), (("shots", 0, "selected"), None)], "shot normalized shot requires a selection"),
            ("verified trim", [(("shots", 0, "status"), "verified"), (("shots", 0, "selected", "source_trim"), None)], "shot verified video requires a valid source_trim"),
        ]
        for name, changes, expected_error in cases:
            malformed = copy.deepcopy(approved)
            for path, value in changes:
                target = malformed
                for key in path[:-1]:
                    target = target[key]
                if value is delete:
                    target.pop(path[-1], None)
                else:
                    target[path[-1]] = copy.deepcopy(value)
            with self.subTest(name=name):
                errors = broll_plan.validate_plan(malformed, self.timeline, self.transcript)
                self.assertTrue(errors)
                self.assertIn(expected_error, errors)
                self.assertIn("review decision manifest cannot be reconstructed", errors)

    def test_approved_plan_with_unhashable_values_returns_errors(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        cases = [
            ("input hashes none", "plan", ("input_hashes",), None, "plan input_hashes must be an object"),
            ("input hashes list", "plan", ("input_hashes",), [], "plan input_hashes must be an object"),
            ("input hashes scalar", "plan", ("input_hashes",), 3, "plan input_hashes must be an object"),
            ("decision mode list", "plan", ("decision", "mode"), [], "review mode must be human or agent"),
            ("decision mode object", "plan", ("decision", "mode"), {}, "review mode must be human or agent"),
            ("media type list", "plan", ("shots", 0, "candidates", 0, "media_type"), [], "shot candidate asset media_type is invalid"),
            ("media type object", "plan", ("shots", 0, "candidates", 0, "media_type"), {}, "shot candidate asset media_type is invalid"),
            ("source type list", "plan", ("shots", 0, "candidates", 0, "provenance", "source_type"), [], "shot candidate asset provenance is invalid"),
            ("source type object", "plan", ("shots", 0, "candidates", 0, "provenance", "source_type"), {}, "shot candidate asset provenance is invalid"),
            ("status list", "plan", ("shots", 0, "status"), [], "shot status is invalid"),
            ("status object", "plan", ("shots", 0, "status"), {}, "shot status is invalid"),
            ("evidence word list", "plan", ("shots", 0, "transcript_evidence", "words", 0, "word"), [], "shot transcript evidence word is not mapped from transcript"),
            ("evidence word object", "plan", ("shots", 0, "transcript_evidence", "words", 0, "word"), {}, "shot transcript evidence word is not mapped from transcript"),
            ("transcript word list", "transcript", ("segments", 0, "words", 0, "word"), [], "shot transcript evidence word is not mapped from transcript"),
            ("transcript word object", "transcript", ("segments", 0, "words", 0, "word"), {}, "shot transcript evidence word is not mapped from transcript"),
        ]
        for name, target_name, path, value, expected_error in cases:
            malformed, transcript = copy.deepcopy(approved), copy.deepcopy(self.transcript)
            target = malformed if target_name == "plan" else transcript
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = copy.deepcopy(value)
            with self.subTest(name=name):
                errors = broll_plan.validate_plan(malformed, self.timeline, transcript)
                self.assertTrue(errors)
                self.assertIn(expected_error, errors)

    def test_apply_review_rejects_unhashable_mode_and_entry_decision_with_value_error(self):
        for mode in ([], {}):
            with self.subTest(field="mode", value=mode):
                with self.assertRaisesRegex(ValueError, "mode must be human or agent"):
                    broll_plan.apply_review(self.plan, self.review(), mode=mode, actor="agent", rationale="Relevant footage.")
        for decision in ([], {}):
            review = self.review()
            review["shots"][0]["decision"] = decision
            with self.subTest(field="decision", value=decision):
                with self.assertRaisesRegex(ValueError, "decision must be select or skip"):
                    broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.")

    def test_validate_plan_catches_stale_revisions_and_real_input_hashes(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project, project_root=self.root))
        project = copy.deepcopy(self.project); project["operations"][1]["revision"] = 3
        self.assertIn("based_on cut revision is stale: expected 2, current 3", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project, project_root=self.root))
        plan = copy.deepcopy(self.plan); plan["input_hashes"]["transcript_sha256"] = "0" * 64
        self.assertIn("transcript SHA-256 is stale", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root))
        plan["input_hashes"]["timeline_sha256"] = "0" * 64
        self.assertIn("timeline SHA-256 is stale", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root))

    def test_active_color_grade_files_and_hashes_must_be_current(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project, project_root=self.root, verify_files=True))
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project_root=self.root, verify_files=True))

        original_grade = self.grade_plan_path.read_bytes()
        original_lut = self.selected_lut_path.read_bytes()
        file_cases = [
            ("changed grade plan", self.grade_plan_path, json.dumps({**self.grade_plan, "selected_look": "changed"}).encode(), "grade plan SHA-256 is stale"),
            ("changed selected LUT", self.selected_lut_path, b"changed LUT", "selected LUT SHA-256 is stale"),
            ("missing grade plan", self.grade_plan_path, None, "grade plan file is missing"),
            ("missing selected LUT", self.selected_lut_path, None, "selected LUT file is missing"),
        ]
        for name, path, replacement, message in file_cases:
            original = path.read_bytes()
            if replacement is None:
                path.unlink()
            else:
                path.write_bytes(replacement)
            try:
                with self.subTest(name=name):
                    self.assertIn(message, broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project, project_root=self.root, verify_files=True))
            finally:
                path.write_bytes(original)
        self.assertEqual(original_grade, self.grade_plan_path.read_bytes())
        self.assertEqual(original_lut, self.selected_lut_path.read_bytes())

        for key, message in (("grade_plan_sha256", "grade plan SHA-256 is required"), ("selected_lut_sha256", "selected LUT SHA-256 is required")):
            plan = copy.deepcopy(self.plan)
            plan["input_hashes"].pop(key)
            with self.subTest(missing_hash=key):
                self.assertIn(message, broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root, verify_files=True))

    def test_active_color_grade_paths_and_plan_shape_are_validated(self):
        grade_cases = [
            ({"schema_version": 1}, "grade plan selected_lut is required"),
            ({"schema_version": 1, "selected_lut": " "}, "grade plan selected_lut is required"),
            ({"schema_version": 1, "selected_lut": "../../../outside.cube"}, "selected LUT path escapes project root"),
            ([], "grade plan must be an object"),
        ]
        original = self.grade_plan_path.read_bytes()
        for grade_plan, message in grade_cases:
            projectlib.write_json(self.grade_plan_path, grade_plan)
            plan = copy.deepcopy(self.plan)
            plan["input_hashes"]["grade_plan_sha256"] = broll_plan.sha256_file(self.grade_plan_path)
            try:
                with self.subTest(grade_plan=grade_plan):
                    self.assertIn(message, broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root, verify_files=True))
            finally:
                self.grade_plan_path.write_bytes(original)

        project = copy.deepcopy(self.project)
        project["operations"][2]["render"]["plan"] = "color-grade/other-grade-plan.json"
        self.assertIn("grade plan file is missing", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project, project_root=self.root, verify_files=True))

    def test_color_grade_hashes_are_not_required_without_active_dependency(self):
        plan = copy.deepcopy(self.plan)
        plan["dependencies"] = ["understanding", "cut"]
        plan["based_on"] = {"understanding": 1, "cut": 2}
        plan["input_hashes"].pop("grade_plan_sha256")
        plan["input_hashes"].pop("selected_lut_sha256")
        project = copy.deepcopy(self.project)
        errors = broll_plan.validate_plan(plan, self.timeline, self.transcript, project=project, project_root=self.root, verify_files=True)
        self.assertFalse(any("grade plan SHA-256 is required" in error or "selected LUT SHA-256 is required" in error for error in errors), errors)
        project["sequences"]["main"]["operations"] = ["cut"]
        self.assertEqual([], broll_plan.validate_plan(plan, self.timeline, self.transcript, project=project, project_root=self.root, verify_files=True))

    def test_dependencies_must_match_canonical_order_without_duplicates(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project))
        for dependencies in (
            ["cut", "understanding", "color-grade"],
            ["understanding", "cut", "color-grade", "cut"],
        ):
            plan = copy.deepcopy(self.plan)
            plan["dependencies"] = dependencies
            with self.subTest(dependencies=dependencies):
                self.assertIn(
                    "plan dependencies do not match current dependencies",
                    broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project),
                )

    def test_validate_plan_requires_canonical_understanding_operation(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project))
        plan, project = copy.deepcopy(self.plan), copy.deepcopy(self.project)
        plan["dependencies"][0] = "understand"
        plan["based_on"]["understand"] = plan["based_on"].pop("understanding")
        project["operations"][0]["id"] = "understand"
        self.assertIn(
            "project understanding operation is required",
            broll_plan.validate_plan(plan, self.timeline, self.transcript, project=project),
        )

    def test_verify_files_rejects_escape_missing_and_hash_mismatch(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project_root=self.root, verify_files=True))
        for path, digest, message in (("../escape.mp4", None, "path escapes project root"), ("cache/b-roll/missing.mp4", None, "file is missing"), ("cache/b-roll/factory.mp4", "0" * 64, "SHA-256 is stale")):
            plan = copy.deepcopy(self.plan); plan["shots"][0]["candidates"][0]["cache_path"] = path
            if digest: plan["shots"][0]["candidates"][0]["sha256"] = digest
            self.assertTrue(any(message in error for error in broll_plan.validate_plan(plan, self.timeline, self.transcript, project_root=self.root, verify_files=True)))

    def test_malformed_nested_values_return_precise_errors_without_raising(self):
        for key, value, message in (("brief", [], "brief must be an object"), ("shots", [None], "shot must be an object"), ("evidence", None, "shot transcript evidence must be an object"), ("candidate", None, "shot candidate must be an object"), ("provenance", None, "shot candidate asset provenance is invalid")):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                if key == "brief": plan["brief"] = value
                elif key == "shots": plan["shots"] = value
                elif key == "evidence": plan["shots"][0]["transcript_evidence"] = value
                elif key == "candidate": plan["shots"][0]["candidates"] = [value]
                else: plan["shots"][0]["candidates"][0]["provenance"] = value
                self.assertIn(message, broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_validation_rejects_nonfinite_timings_exact_words_and_bad_provenance(self):
        for value in (float("nan"), float("inf")):
            plan = copy.deepcopy(self.plan); plan["shots"][0]["program_range"]["start_s"] = value
            self.assertIn("shot program range is outside timeline", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["transcript_evidence"]["words"][0]["word"] = " factory"
        self.assertIn("shot transcript evidence word is not mapped from transcript", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); candidate = plan["shots"][0]["candidates"][0]; candidate["sha256"] = "g" * 64; candidate["provenance"]["original_path"] = 3
        errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
        self.assertIn("shot candidate asset SHA-256 is required", errors); self.assertIn("shot candidate asset provenance is incomplete", errors)

    def test_source_specific_provenance_accepts_valid_acquisition_records(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript))

        external = copy.deepcopy(self.plan)
        external["shots"][0]["candidates"][0]["provenance"] = {
            "source_type": "external-generated",
            "creator": "Generator Operator",
            "license": "commercial",
            "retrieval_time": "2026-07-23T00:00:00+08:00",
            "original_path": "input/generated.mp4",
            "generation_provider": "provider",
            "generation_model": "model-v1",
            "prompt": "Factory assembly line",
        }
        self.assertEqual([], broll_plan.validate_plan(external, self.timeline, self.transcript))
        external["shots"][0]["candidates"][0]["provenance"].pop("prompt")
        external["shots"][0]["candidates"][0]["provenance"]["job_id"] = "job-123"
        self.assertEqual([], broll_plan.validate_plan(external, self.timeline, self.transcript))

        pexels_plan = copy.deepcopy(self.plan)
        pexels_plan["shots"][0]["candidates"][0] = self.pexels_candidate()
        self.assertEqual([], broll_plan.validate_plan(pexels_plan, self.timeline, self.transcript))

    def test_common_and_local_provenance_fields_are_strict(self):
        delete = object()
        cases = [
            (("bytes",), delete, "bytes must be a positive integer"),
            (("bytes",), True, "bytes must be a positive integer"),
            (("bytes",), 0, "bytes must be a positive integer"),
            (("bytes",), -1, "bytes must be a positive integer"),
            (("bytes",), 1.5, "bytes must be a positive integer"),
            (("bytes",), "5", "bytes must be a positive integer"),
            (("provenance", "creator"), " ", "provenance is incomplete"),
            (("provenance", "license"), None, "provenance is incomplete"),
            (("provenance", "retrieval_time"), "2026-07-23T00:00:00", "retrieval_time is invalid"),
            (("provenance", "retrieval_time"), "not-a-time", "retrieval_time is invalid"),
            (("provenance", "original_path"), delete, "local provenance original_path is required"),
            (("provenance", "original_path"), " ", "local provenance original_path is required"),
            (("provenance", "original_path"), 3, "local provenance original_path is required"),
        ]
        for path, value, message in cases:
            plan = copy.deepcopy(self.plan)
            target = plan["shots"][0]["candidates"][0]
            for key in path[:-1]:
                target = target[key]
            if value is delete:
                target.pop(path[-1])
            else:
                target[path[-1]] = value
            with self.subTest(path=path, value=value):
                errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_external_generated_provenance_fields_are_strict(self):
        base = copy.deepcopy(self.plan["shots"][0]["candidates"][0])
        base["provenance"] = {
            "source_type": "external-generated",
            "creator": "Generator Operator",
            "license": "commercial",
            "retrieval_time": "2026-07-23T00:00:00Z",
            "original_path": "input/generated.mp4",
            "generation_provider": "provider",
            "generation_model": "model-v1",
            "prompt": "Factory assembly line",
        }
        delete = object()
        cases = [
            ("original_path", delete),
            ("generation_provider", delete),
            ("generation_provider", " "),
            ("generation_model", None),
            ("prompt", delete),
            ("prompt", " "),
            ("prompt", 3),
        ]
        for field, value in cases:
            plan = copy.deepcopy(self.plan)
            candidate = copy.deepcopy(base)
            if value is delete:
                candidate["provenance"].pop(field)
            else:
                candidate["provenance"][field] = value
            plan["shots"][0]["candidates"][0] = candidate
            with self.subTest(field=field, value=value):
                errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
                self.assertTrue(any("external-generated provenance is incomplete" in error for error in errors), errors)

    def test_pexels_provenance_and_selected_variant_must_be_exact_and_consistent(self):
        delete = object()
        cases = [
            (("provider_id",), delete, "Pexels provider_id must be a positive integer"),
            (("provider_id",), True, "Pexels provider_id must be a positive integer"),
            (("file_id",), 0, "Pexels file_id must be a positive integer"),
            (("download_url",), "https://evil.test/factory.mp4", "Pexels download_url is invalid"),
            (("width",), 0, "Pexels width must be a positive integer"),
            (("height",), 1.5, "Pexels height must be a positive integer"),
            (("duration_s",), delete, "Pexels duration_s is required"),
            (("provenance", "source_url"), "http://www.pexels.com/video/factory-101/", "Pexels source_url is invalid"),
            (("provenance", "source_url"), "https://www.pexels.com/not-video/", "Pexels source_url is invalid"),
            (("provenance", "license_url"), "https://www.pexels.com/other/", "Pexels license_url is invalid"),
            (("provenance", "terms_url"), delete, "Pexels terms_url is invalid"),
            (("provenance", "provider_id"), 999, "Pexels provenance provider_id does not match candidate"),
            (("provenance", "download_url"), "https://videos.pexels.com/other.mp4", "Pexels provenance download_url does not match candidate"),
            (("provenance", "dimensions", "width"), 1280, "Pexels provenance dimensions do not match candidate"),
            (("provenance", "duration_s"), 3.0, "Pexels provenance duration_s does not match candidate"),
        ]
        for path, value, message in cases:
            plan = copy.deepcopy(self.plan)
            candidate = self.pexels_candidate()
            target = candidate
            for key in path[:-1]:
                target = target[key]
            if value is delete:
                target.pop(path[-1])
            else:
                target[path[-1]] = value
            plan["shots"][0]["candidates"][0] = candidate
            with self.subTest(path=path, value=value):
                errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
                self.assertTrue(any(message in error for error in errors), errors)

        plan = copy.deepcopy(self.plan)
        candidate = self.pexels_candidate()
        candidate["provider_id"] = 1
        candidate["provenance"]["provider_id"] = True
        plan["shots"][0]["candidates"][0] = candidate
        errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
        self.assertTrue(any("Pexels provenance provider_id must be a positive integer" in error for error in errors), errors)

        candidate = self.pexels_candidate()
        candidate["width"] = 1
        candidate["provenance"]["dimensions"]["width"] = True
        plan["shots"][0]["candidates"][0] = candidate
        errors = broll_plan.validate_plan(plan, self.timeline, self.transcript)
        self.assertTrue(any("Pexels provenance dimensions do not match candidate" in error for error in errors), errors)

    def test_lifecycles_and_current_dependency_set_are_enforced(self):
        plan = copy.deepcopy(self.plan); plan["shots"][0].update({"status": "selected", "selected": None})
        self.assertIn("shot selected shot requires a selection", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0].update({"status": "planned", "selected": {"candidate_id": "asset"}})
        self.assertIn("shot planned shot must not select a candidate", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["dependencies"] = ["understanding", "cut"]
        self.assertIn("plan dependencies do not match current dependencies", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root))

    def test_root_inputs_must_exist_and_verify_files_requires_root(self):
        self.assertIn("verify_files requires project_root", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, verify_files=True))
        self.transcript_path.unlink()
        self.assertIn("transcript file is missing", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project_root=self.root))
        self.timeline_path.unlink()
        self.assertIn("timeline file is missing", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project_root=self.root))

    def test_malformed_timeline_duration_returns_error_without_raising(self):
        timeline = copy.deepcopy(self.timeline); timeline["program_duration_s"] = "not-a-number"
        self.assertIn("timeline program_duration_s is invalid", broll_plan.validate_plan(self.plan, timeline, self.transcript))

    def test_non_object_timeline_returns_error_without_raising(self):
        for timeline in (None, []):
            with self.subTest(timeline=timeline):
                self.assertEqual(["timeline must be an object"], broll_plan.validate_plan(self.plan, timeline, self.transcript))

    def test_malformed_project_contracts_return_errors_without_raising(self):
        cases = [([], "project must be an object"), ({"operations": {}}, "project operations must be a list"), ({"operations": [], "sequences": []}, "project sequences must be an object"), ({"operations": [], "active_sequence": "main", "sequences": {"main": []}}, "project active sequence must be an object")]
        for project, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project))

    def test_project_operation_and_active_sequence_shapes_are_total(self):
        cases = []
        for operation in (None, []):
            project = copy.deepcopy(self.project); project["operations"] = [operation]
            cases.append((project, "project operations must be a list of objects"))
        for operation_id in (None, "", " ", [], {}):
            project = copy.deepcopy(self.project); project["operations"][0]["id"] = copy.deepcopy(operation_id)
            cases.append((project, "project operation ids must be unique nonblank strings"))
        duplicate = copy.deepcopy(self.project); duplicate["operations"].append(copy.deepcopy(duplicate["operations"][0]))
        cases.append((duplicate, "project operation ids must be unique nonblank strings"))
        for active_operations in (None, 3, "cut"):
            project = copy.deepcopy(self.project); project["sequences"]["main"]["operations"] = active_operations
            cases.append((project, "project active sequence operations must be a list"))
        for operation_id in (None, "", " ", [], {}):
            project = copy.deepcopy(self.project); project["sequences"]["main"]["operations"] = [copy.deepcopy(operation_id)]
            cases.append((project, "project active sequence operation ids must be nonblank strings"))
        for active in ([], {}):
            project = copy.deepcopy(self.project); project["active_sequence"] = copy.deepcopy(active)
            cases.append((project, "project active sequence must be an object"))
        for project, message in cases:
            with self.subTest(message=message, project=project):
                self.assertIn(message, broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project))

    def test_dependency_ids_and_revisions_are_strict_positive_integers(self):
        for dependency in (None, "", " ", [], {}):
            plan = copy.deepcopy(self.plan)
            plan["dependencies"] = [copy.deepcopy(dependency)]
            with self.subTest(kind="dependency", value=dependency):
                self.assertIn("dependencies must contain nonblank strings", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project))

        for revision in (True, 0, -1, 1.0, "1"):
            project = copy.deepcopy(self.project)
            project["operations"][0]["revision"] = revision
            with self.subTest(kind="project", revision=revision):
                self.assertIn("project operation understanding revision must be a positive integer", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project))

            plan = copy.deepcopy(self.plan)
            plan["based_on"]["understanding"] = revision
            with self.subTest(kind="based_on", revision=revision):
                self.assertIn("based_on understanding revision must be a positive integer", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project))

    def test_apply_review_rejects_malformed_objects_and_collections(self):
        cases = [(None, self.review(), "plan must be an object"), (self.plan, None, "review must be an object"), ({**self.plan, "shots": None}, self.review(), "plan shots must be a list"), ({**self.plan, "shots": [None]}, self.review(), "plan shot must be an object"), (self.plan, {"review_id": "r", "shots": None}, "review shots must be a list"), (self.plan, {"review_id": "r", "shots": [None]}, "review shot must be an object")]
        for plan, review, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message): broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="reason")

    def test_apply_review_rejects_malformed_candidates_before_receipt_hashing(self):
        for candidate, message in ((None, "shot candidate must be an object"), ({"id": "asset", "media_type": "video"}, "shot candidate asset SHA-256 is required")):
            with self.subTest(message=message):
                plan = copy.deepcopy(self.plan); plan["shots"][0]["candidates"] = [candidate]
                with self.assertRaisesRegex(ValueError, message): broll_plan.apply_review(plan, self.review(rationale="reason"), mode="agent", actor="agent", rationale="reason")

    def test_apply_review_rejects_missing_or_duplicate_plan_identifiers(self):
        cases = []
        for shot_id in (None, "", 3):
            plan = copy.deepcopy(self.plan); plan["shots"][0]["id"] = shot_id
            cases.append((plan, "plan shot id is required"))
        plan = copy.deepcopy(self.plan); plan["shots"].append(copy.deepcopy(plan["shots"][0]))
        cases.append((plan, "duplicate plan shot id: shot"))
        for candidate_id, sha256, message in ((None, "a" * 64, "shot candidate id is required"), ("", "a" * 64, "shot candidate id is required"), ("asset", "not-a-hash", "shot candidate asset SHA-256 is required")):
            plan = copy.deepcopy(self.plan); plan["shots"][0]["candidates"][0].update({"id": candidate_id, "sha256": sha256})
            cases.append((plan, message))
        for plan, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message): broll_plan.apply_review(plan, self.review(rationale="reason"), mode="agent", actor="agent", rationale="reason")

    def test_candidate_id_skip_is_reserved_for_the_ui_decision(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0]["id"] = "skip"
        self.assertIn("shot candidate id 'skip' is reserved", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_source_ranges_must_be_ordered_nonnegative_and_within_source(self):
        for source_range in ({"start_s": -1, "end_s": 1}, {"start_s": 2, "end_s": 2}, {"start_s": 9, "end_s": 11}):
            with self.subTest(source_range=source_range):
                plan = copy.deepcopy(self.plan); plan["shots"][0]["source_ranges"] = [source_range]
                self.assertIn("shot source range is outside timeline", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def _retimed_plan(self):
        timeline = {
            "schema_version": 1,
            "timeline_id": "main",
            "source_duration_s": 7.0,
            "program_duration_s": 4.0,
            "fps": {"num": 30, "den": 1},
            "clips": [
                {"id": "fast", "source_range": {"start_s": 0, "end_s": 4}, "program_range": {"start_s": 0, "end_s": 2}, "speed": 2.0},
                {"id": "normal", "source_range": {"start_s": 5, "end_s": 7}, "program_range": {"start_s": 2, "end_s": 4}, "speed": 1.0},
            ],
        }
        transcript = {"segments": [{"words": [{"word": "fast", "start": 2.0, "end": 4.0}, {"word": "normal", "start": 5.0, "end": 6.0}]}]}
        mapped = projectlib.map_transcript_to_timeline(transcript, timeline)["segments"][0]["words"]
        plan = copy.deepcopy(self.plan)
        plan.update({"program_duration_s": 4.0, "shots": [copy.deepcopy(plan["shots"][0])]})
        plan["shots"][0].update({
            "program_range": {"start_s": 1.0, "end_s": 3.0},
            "source_ranges": [
                {"clip_id": "fast", "start_s": 2.0, "end_s": 4.0},
                {"clip_id": "normal", "start_s": 5.0, "end_s": 6.0},
            ],
            "transcript_evidence": {"words": mapped},
        })
        return plan, timeline, transcript

    def test_source_ranges_exactly_reconstruct_identity_and_retimed_timeline(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript))
        plan, timeline, transcript = self._retimed_plan()
        self.assertEqual([], broll_plan.validate_plan(plan, timeline, transcript))

        within_tolerance = copy.deepcopy(plan)
        within_tolerance["shots"][0]["source_ranges"][0]["start_s"] += 0.0000005
        self.assertEqual([], broll_plan.validate_plan(within_tolerance, timeline, transcript))

        outside_tolerance = copy.deepcopy(plan)
        outside_tolerance["shots"][0]["source_ranges"][0]["start_s"] += 0.000002
        self.assertIn("shot source_ranges do not match timeline", broll_plan.validate_plan(outside_tolerance, timeline, transcript))

    def test_source_ranges_reject_missing_extra_unrelated_wrong_and_reordered_clips(self):
        plan, timeline, transcript = self._retimed_plan()
        valid = plan["shots"][0]["source_ranges"]
        cases = {
            "missing": valid[:1],
            "extra": valid + [{"clip_id": "normal", "start_s": 6.0, "end_s": 7.0}],
            "unrelated": [{"clip_id": "other", "start_s": 2.0, "end_s": 4.0}, valid[1]],
            "wrong clip": [{**valid[0], "clip_id": "normal"}, valid[1]],
            "reordered": list(reversed(valid)),
        }
        for name, source_ranges in cases.items():
            malformed = copy.deepcopy(plan)
            malformed["shots"][0]["source_ranges"] = copy.deepcopy(source_ranges)
            with self.subTest(name=name):
                self.assertIn("shot source_ranges do not match timeline", broll_plan.validate_plan(malformed, timeline, transcript))

    def test_transcript_evidence_must_be_nonempty_inside_shot_and_declared_source(self):
        empty = copy.deepcopy(self.plan)
        empty["shots"][0]["transcript_evidence"]["words"] = []
        self.assertIn("shot transcript evidence requires at least one word", broll_plan.validate_plan(empty, self.timeline, self.transcript))

        other_moment = copy.deepcopy(self.plan)
        other_moment["shots"][0]["transcript_evidence"]["words"] = [copy.deepcopy(self.mapped_words[1])]
        self.assertIn("shot transcript evidence word is outside shot program range", broll_plan.validate_plan(other_moment, self.timeline, self.transcript))

        not_contained = copy.deepcopy(self.plan)
        not_contained["shots"][0]["source_ranges"] = [{"clip_id": "one", "start_s": 1.1, "end_s": 2.0}]
        self.assertIn("shot transcript evidence source range is outside shot source_ranges", broll_plan.validate_plan(not_contained, self.timeline, self.transcript))

    def test_malformed_transcript_and_timeline_mapping_returns_errors_without_raising(self):
        transcript_cases = [
            {"segments": None},
            {"segments": [None]},
            {"segments": [[]]},
            {"segments": [{"words": None}]},
            {"segments": [{"words": [None]}]},
            {"segments": [{"words": [[]]}]},
            {"segments": [{"words": [{}]}]},
        ]
        for transcript in transcript_cases:
            with self.subTest(kind="transcript", value=transcript):
                self.assertTrue(broll_plan.validate_plan(self.plan, self.timeline, transcript))

        timeline_cases = []
        for clips in (None, 3, [None]):
            timeline_cases.append({**self.timeline, "clips": clips})
        for clip in (
            {"id": "one", "source_range": None, "program_range": {"start_s": 0, "end_s": 10}, "speed": 1},
            {"id": "one", "source_range": {"start_s": 0, "end_s": 10}, "program_range": [], "speed": 1},
            {"id": "one", "source_range": {"start_s": 0, "end_s": 10}, "program_range": {"start_s": 0, "end_s": 10}, "speed": []},
        ):
            timeline_cases.append({**self.timeline, "clips": [clip]})
        for timeline in timeline_cases:
            with self.subTest(kind="timeline", value=timeline["clips"]):
                self.assertTrue(broll_plan.validate_plan(self.plan, timeline, self.transcript))

    def test_persisted_selected_media_requires_its_media_contract(self):
        plan = copy.deepcopy(self.plan); plan["shots"][0].update({"status": "selected", "selected": {"candidate_id": "asset", "source_trim": {"start_s": 1, "end_s": 1}}})
        self.assertIn("shot selected video requires a valid source_trim", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["candidates"][0]["media_type"] = "image"; plan["shots"][0].update({"status": "verified", "selected": {"candidate_id": "asset", "ken_burns": {}}})
        self.assertIn("shot verified image requires a non-empty ken_burns", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_persisted_ranges_reject_boolean_and_string_endpoints(self):
        cases = [
            (("shots", 0, "program_range", "start_s"), True, "shot program range is outside timeline"),
            (("shots", 0, "program_range", "start_s"), "1", "shot program range is outside timeline"),
            (("shots", 0, "program_range", "end_s"), True, "shot program range is outside timeline"),
            (("shots", 0, "program_range", "end_s"), "2", "shot program range is outside timeline"),
            (("shots", 0, "source_ranges", 0, "start_s"), True, "shot source range is outside timeline"),
            (("shots", 0, "source_ranges", 0, "start_s"), "1", "shot source range is outside timeline"),
            (("shots", 0, "source_ranges", 0, "end_s"), True, "shot source range is outside timeline"),
            (("shots", 0, "source_ranges", 0, "end_s"), "2", "shot source range is outside timeline"),
            (("shots", 0, "transcript_evidence", "words", 0, "source_range", "start_s"), True, "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "source_range", "start_s"), "1", "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "source_range", "end_s"), True, "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "source_range", "end_s"), "2", "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "program_range", "start_s"), True, "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "program_range", "start_s"), "1", "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "program_range", "end_s"), True, "shot transcript evidence word is not mapped from transcript"),
            (("shots", 0, "transcript_evidence", "words", 0, "program_range", "end_s"), "2", "shot transcript evidence word is not mapped from transcript"),
        ]
        for path, value, message in cases:
            plan = copy.deepcopy(self.plan)
            target = plan
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path, value=value):
                self.assertIn(message, broll_plan.validate_plan(plan, self.timeline, self.transcript))

        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        for trim in (
            {"start_s": False, "end_s": 1},
            {"start_s": "0", "end_s": 1},
            {"start_s": 0, "end_s": True},
            {"start_s": 0, "end_s": "1"},
            {"start_s": False, "end_s": True},
            {"start_s": "0", "end_s": "1"},
        ):
            plan = copy.deepcopy(approved)
            plan["shots"][0]["selected"]["source_trim"] = trim
            with self.subTest(persisted_trim=trim):
                self.assertIn("shot selected video requires a valid source_trim", broll_plan.validate_plan(plan, self.timeline, self.transcript))

        valid = copy.deepcopy(self.plan)
        valid["shots"][0]["program_range"] = {"start_s": 1, "end_s": 2.0}
        valid["shots"][0]["source_ranges"][0].update({"start_s": 1.0, "end_s": 2})
        self.assertEqual([], broll_plan.validate_plan(valid, self.timeline, self.transcript))

    def test_persisted_plan_timeline_and_evidence_contain_oversized_integer_ranges(self):
        huge = 10 ** 10000
        plan_paths = [
            ("program start", ("shots", 0, "program_range", "start_s")),
            ("program end", ("shots", 0, "program_range", "end_s")),
            ("source start", ("shots", 0, "source_ranges", 0, "start_s")),
            ("source end", ("shots", 0, "source_ranges", 0, "end_s")),
            ("evidence source start", ("shots", 0, "transcript_evidence", "words", 0, "source_range", "start_s")),
            ("evidence source end", ("shots", 0, "transcript_evidence", "words", 0, "source_range", "end_s")),
            ("evidence program start", ("shots", 0, "transcript_evidence", "words", 0, "program_range", "start_s")),
            ("evidence program end", ("shots", 0, "transcript_evidence", "words", 0, "program_range", "end_s")),
        ]
        for name, path in plan_paths:
            for sign, value in (("positive", huge), ("negative", -huge)):
                plan = copy.deepcopy(self.plan)
                target = plan
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.subTest(scope="plan", name=name, sign=sign):
                    self.assertTrue(broll_plan.validate_plan(plan, self.timeline, self.transcript))

        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        for endpoint in ("start_s", "end_s"):
            for sign, value in (("positive", huge), ("negative", -huge)):
                plan = copy.deepcopy(approved)
                plan["shots"][0]["selected"]["source_trim"][endpoint] = value
                with self.subTest(scope="selected", endpoint=endpoint, sign=sign):
                    self.assertIn("shot selected video requires a valid source_trim", broll_plan.validate_plan(plan, self.timeline, self.transcript))

        timeline_paths = [
            ("source start", ("clips", 0, "source_range", "start_s")),
            ("source end", ("clips", 0, "source_range", "end_s")),
            ("program start", ("clips", 0, "program_range", "start_s")),
            ("program end", ("clips", 0, "program_range", "end_s")),
        ]
        for name, path in timeline_paths:
            for sign, value in (("positive", huge), ("negative", -huge)):
                timeline = copy.deepcopy(self.timeline)
                target = timeline
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.subTest(scope="timeline", name=name, sign=sign):
                    self.assertTrue(broll_plan.validate_plan(self.plan, timeline, self.transcript))

    def test_top_level_durations_and_clip_speed_reject_non_json_finite_numbers(self):
        huge = 10 ** 10000
        invalid = [
            ("true", True),
            ("false", False),
            ("nan", float("nan")),
            ("infinity", float("inf")),
            ("negative infinity", float("-inf")),
            ("huge positive", huge),
            ("huge negative", -huge),
        ]
        fields = [
            ("plan program duration", "plan", ("program_duration_s",), "10", "plan program_duration_s is required"),
            ("timeline program duration", "timeline", ("program_duration_s",), "10", "timeline program_duration_s is invalid"),
            ("timeline source duration", "timeline", ("source_duration_s",), "10", "timeline source_duration_s is invalid"),
            ("clip speed", "timeline", ("clips", 0, "speed"), "1", None),
        ]
        for field, target_name, path, numeric_string, expected in fields:
            for name, value in [("numeric string", numeric_string), *invalid]:
                plan, timeline = copy.deepcopy(self.plan), copy.deepcopy(self.timeline)
                target = plan if target_name == "plan" else timeline
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.subTest(field=field, name=name):
                    errors = broll_plan.validate_plan(plan, timeline, self.transcript)
                    if expected:
                        self.assertIn(expected, errors)
                    else:
                        self.assertTrue(errors)

    def test_all_numeric_sites_preserve_json_ints_and_floats(self):
        plan, timeline = copy.deepcopy(self.plan), copy.deepcopy(self.timeline)
        plan["program_duration_s"] = 10
        timeline.update({"program_duration_s": 10.0, "source_duration_s": 10})
        timeline["clips"][0]["speed"] = 1
        candidate = plan["shots"][0]["candidates"][0]
        candidate.update({"duration_s": 2, "probe": {"duration_s": 2.0}})
        review = self.review_for(plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1.0}}])
        approved = broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual([], broll_plan.validate_plan(approved, timeline, self.transcript))

    def test_review_receipt_integrity_and_human_authority_are_validated(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual([], broll_plan.validate_plan(approved, self.timeline, self.transcript))
        cases = []
        missing = copy.deepcopy(approved); missing["decision"] = None; cases.append((missing, "review trust requires decision object"))
        missing = copy.deepcopy(approved); missing["review"] = None; cases.append((missing, "review trust requires review object"))
        draft = copy.deepcopy(approved); draft["review"]["status"] = "draft"; cases.append((draft, "review status must be approved"))
        mismatch = copy.deepcopy(approved); mismatch["decision"]["actor"] = "other"; cases.append((mismatch, "decision and review authority do not match"))
        invalid_mode = copy.deepcopy(approved); invalid_mode["decision"]["mode"] = invalid_mode["review"]["mode"] = "robot"; cases.append((invalid_mode, "review mode must be human or agent"))
        blank_actor = copy.deepcopy(approved); blank_actor["decision"]["actor"] = blank_actor["review"]["actor"] = " "; cases.append((blank_actor, "review actor is required"))
        missing_id = copy.deepcopy(approved); missing_id["review"].pop("review_id"); cases.append((missing_id, "review_id is required"))
        for field, message in (("plan_sha256", "review plan SHA-256 does not match"), ("candidate_manifest_sha256", "review candidate manifest SHA-256 does not match"), ("review_video_sha256", "review video SHA-256 does not match"), ("selected_asset_sha256", "review selected asset hashes do not match")):
            tampered = copy.deepcopy(approved); tampered["review"][field] = [] if field == "selected_asset_sha256" else "0" * 64; cases.append((tampered, message))
        bad_timestamp = copy.deepcopy(approved); bad_timestamp["review"]["timestamp"] = "2026-07-23T12:00:00"; cases.append((bad_timestamp, "review timestamp is invalid"))
        for plan, message in cases:
            with self.subTest(message=message): self.assertIn(message, broll_plan.validate_plan(plan, self.timeline, self.transcript))
        human = broll_plan.apply_review(self.plan, self.review(rationale="I chose it.", explicit_user_action=True), mode="human", actor="person", rationale="I chose it.")
        self.assertTrue(human["decision"]["explicit_user_action"]); self.assertTrue(human["review"]["explicit_user_action"])
        human["review"].pop("explicit_user_action")
        self.assertIn("human review requires explicit_user_action true", broll_plan.validate_plan(human, self.timeline, self.transcript))

    def test_review_subject_is_stable_across_post_review_lifecycle(self):
        selected = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        normalized = copy.deepcopy(selected); normalized["shots"][0].update({"status": "normalized", "normalized": {"path": "asset.mp4", "sha256": "a" * 64}})
        verified = copy.deepcopy(normalized); verified["shots"][0].update({"status": "verified", "verification": {"status": "pass"}})
        self.assertEqual(broll_plan.review_subject(selected), broll_plan.review_subject(normalized))
        self.assertEqual(broll_plan.review_subject(selected), broll_plan.review_subject(verified))
        self.assertEqual([], broll_plan.validate_plan(verified, self.timeline, self.transcript))

    def test_normalized_and_verified_lifecycle_records_are_required_and_validated(self):
        selected = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        normalized = copy.deepcopy(selected)
        normalized["shots"][0].update({"status": "normalized", "normalized": {"path": "cache/b-roll/normalized/shot.mp4", "sha256": "a" * 64}})
        self.assertEqual([], broll_plan.validate_plan(normalized, self.timeline, self.transcript))
        verified = copy.deepcopy(normalized)
        verified["shots"][0].update({"status": "verified", "verification": {"status": "pass", "report": "review/report.md"}})
        self.assertEqual([], broll_plan.validate_plan(verified, self.timeline, self.transcript))

        delete = object()
        normalized_cases = [
            (delete, "shot normalized record is required"),
            (None, "shot normalized record is required"),
            ([], "shot normalized record is required"),
            ({"path": "", "sha256": "a" * 64}, "shot normalized path is invalid"),
            ({"path": [], "sha256": "a" * 64}, "shot normalized path is invalid"),
            ({"path": "asset.mp4", "sha256": "bad"}, "shot normalized SHA-256 is invalid"),
        ]
        for status in ("normalized", "verified"):
            for value, message in normalized_cases:
                malformed = copy.deepcopy(verified if status == "verified" else normalized)
                malformed["shots"][0]["status"] = status
                if value is delete:
                    malformed["shots"][0].pop("normalized", None)
                else:
                    malformed["shots"][0]["normalized"] = copy.deepcopy(value)
                with self.subTest(status=status, value=value):
                    self.assertIn(message, broll_plan.validate_plan(malformed, self.timeline, self.transcript))

        for verification in (None, [], {}, {"status": "fail"}, {"status": None}):
            malformed = copy.deepcopy(verified)
            malformed["shots"][0]["verification"] = copy.deepcopy(verification)
            with self.subTest(verification=verification):
                self.assertIn("shot verified verification must pass", broll_plan.validate_plan(malformed, self.timeline, self.transcript))

        for status in ("normalized", "verified"):
            malformed = copy.deepcopy(selected)
            malformed["shots"][0].update({"status": status, "selected": None})
            with self.subTest(status=status, missing="selection and lifecycle"):
                errors = broll_plan.validate_plan(malformed, self.timeline, self.transcript)
                self.assertIn(f"shot {status} shot requires a selection", errors)
                self.assertIn("shot normalized record is required", errors)
                if status == "verified":
                    self.assertIn("shot verified verification must pass", errors)

    def test_lifecycle_rejects_stale_normalized_and_verification_fields(self):
        selected = broll_plan.apply_review(
            self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage."
        )
        normalized = copy.deepcopy(selected)
        normalized["shots"][0].update({
            "status": "normalized",
            "normalized": {"path": "cache/b-roll/normalized/shot.mp4", "sha256": "a" * 64},
        })
        cases = [
            (selected, "normalized", {"path": "asset.mp4", "sha256": "a" * 64},
             "shot selected shot must not carry normalized"),
            (selected, "verification", {"status": "pass"},
             "shot selected shot must not carry verification"),
            (normalized, "verification", {"status": "pass"},
             "shot normalized shot must not carry verification"),
        ]
        skipped = broll_plan.apply_review(
            self.plan,
            self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage."),
            mode="agent", actor="agent", rationale="No useful footage.",
        )
        cases.extend([
            (skipped, "normalized", {"path": "asset.mp4", "sha256": "a" * 64},
             "shot skipped shot must not carry normalized"),
            (skipped, "verification", {"status": "pass"},
             "shot skipped shot must not carry verification"),
        ])
        planned = copy.deepcopy(self.plan)
        planned["shots"][0]["status"] = "planned"
        for source in (planned, self.plan):
            status = source["shots"][0]["status"]
            cases.extend([
                (source, "normalized", {"path": "asset.mp4", "sha256": "a" * 64},
                 f"shot {status} shot must not carry normalized"),
                (source, "verification", {"status": "pass"},
                 f"shot {status} shot must not carry verification"),
            ])
        for source, field, value, message in cases:
            malformed = copy.deepcopy(source)
            malformed["shots"][0][field] = value
            with self.subTest(status=malformed["shots"][0]["status"], field=field):
                self.assertIn(message, broll_plan.validate_plan(malformed, self.timeline, self.transcript))

    def test_registration_requires_approved_receipt_and_passing_verification(self):
        for verification in (None, {}, {"status": "fail"}):
            plan = self._registered_plan((2, 3))
            plan["shots"][0]["verification"] = copy.deepcopy(verification)
            with self.subTest(verification=verification):
                with self.assertRaisesRegex(ValueError, "verification must pass"):
                    broll_plan.register_operation(self._registration_project(), plan)

        hand_built = copy.deepcopy(self.plan)
        hand_built["shots"][0].update({
            "status": "verified",
            "selected": {"candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}},
            "normalized": {"path": "asset.mp4", "sha256": "a" * 64},
            "verification": {"status": "pass"},
        })
        with self.assertRaisesRegex(ValueError, "review_status must be approved"):
            broll_plan.register_operation(self._registration_project(), hand_built)

    def test_shots_must_be_chronological_even_without_overlap(self):
        later = copy.deepcopy(self.plan["shots"][0]); later.update({"id": "later", "program_range": {"start_s": 3, "end_s": 4}, "source_ranges": [{"clip_id": "one", "start_s": 3, "end_s": 4}], "transcript_evidence": {"words": [self.mapped_words[2]]}, "candidates": []})
        plan = copy.deepcopy(self.plan); plan["shots"] = [later, plan["shots"][0]]
        self.assertIn("shots must be in chronological program order", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_review_entry_id_must_be_a_nonblank_string(self):
        for shot_id in (None, "", []):
            review = self.review(rationale="reason"); review["shots"][0]["id"] = shot_id
            with self.subTest(shot_id=shot_id):
                with self.assertRaisesRegex(ValueError, "review shot id is required"): broll_plan.apply_review(self.plan, review, mode="agent", actor="agent", rationale="reason")

    def test_failed_atomic_receipt_replace_removes_temporary_file(self):
        before = set(self.root.iterdir())
        with mock.patch.object(broll_plan.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                broll_plan.apply_review(self.plan, self.review(rationale="reason"), mode="agent", actor="agent", rationale="reason", interaction_path=self.root / "receipt.json")
        self.assertEqual(before, set(self.root.iterdir()))

    def _registered_plan(self, *ranges, dependencies=None, skip=False):
        plan = copy.deepcopy(self.plan)
        if dependencies is not None:
            plan["dependencies"] = dependencies
            revisions = {"understanding": 1, "cut": 2, "color-grade": 3}
            plan["based_on"] = {item: revisions[item] for item in dependencies}
        original = plan["shots"][0]
        plan["shots"] = []
        for index, (start, end) in enumerate(ranges, 1):
            shot = copy.deepcopy(original)
            shot["id"] = f"shot-{index}"
            shot["candidates"][0]["id"] = f"asset-{index}"
            shot["program_range"] = {"start_s": start, "end_s": end}
            shot["source_ranges"] = [{"clip_id": "one", "start_s": start, "end_s": end}]
            shot["transcript_evidence"] = {"words": [copy.deepcopy(next(word for word in self.mapped_words if word["program_range"]["start_s"] >= start and word["program_range"]["end_s"] <= end))]}
            shot["selected"] = None
            shot["status"] = "candidates_ready"
            plan["shots"].append(shot)
        decisions = [{"id": shot["id"], "decision": "skip"} if skip else {"id": shot["id"], "decision": "select", "candidate_id": shot["candidates"][0]["id"], "source_trim": {"start_s": 0, "end_s": 1}} for shot in plan["shots"]]
        plan = broll_plan.apply_review(plan, self.review_for(plan, decisions, review_id="123e4567-e89b-12d3-a456-426614174011"), mode="agent", actor="agent", rationale="Relevant footage.")
        for index, shot in enumerate(plan["shots"], 1):
            if shot["status"] == "skipped": continue
            shot["normalized"] = {"path": f"cache/b-roll/normalized/broll-{index:03d}.mp4", "sha256": "a" * 64}
            shot["verification"] = {"status": "pass"}
            shot["status"] = "verified"
        return plan

    def _registration_project(self, sequence=None):
        return {
            "active_sequence": "main",
            "sequences": {"main": {"operations": sequence or ["cut", "color-grade", "content-cards", "captions"]}},
            "operations": [
                {"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2},
                {"id": "color-grade", "revision": 3}, {"id": "content-cards", "revision": 4},
                {"id": "captions", "revision": 5},
            ],
            "render": {"status": "verified"},
        }

    def test_active_dependencies_validates_project_and_uses_active_sequence(self):
        project = self._registration_project()
        self.assertEqual(["understanding", "cut", "color-grade"], broll_plan.active_dependencies(project))
        self.assertEqual(["understanding"], broll_plan.active_dependencies(self._registration_project(["content-cards"])))
        for invalid in (None, {"active_sequence": "main", "sequences": {}, "operations": []}, {"active_sequence": "main", "sequences": {"main": {"operations": []}}, "operations": []}, {"active_sequence": "main", "sequences": {"main": {"operations": "cut"}}, "operations": [{"id": "understanding", "revision": 1}]}):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError): broll_plan.active_dependencies(invalid)

    def test_register_operation_creates_verified_overlay_without_mutating_input(self):
        project = self._registration_project(); before = copy.deepcopy(project)
        result = broll_plan.register_operation(project, self._registered_plan((2.0, 4.5)))
        operation = next(item for item in result["operations"] if item["id"] == "b-roll")
        self.assertEqual(before, project)
        self.assertEqual(["cut", "color-grade", "b-roll", "content-cards", "captions"], result["sequences"]["main"]["operations"])
        self.assertEqual(["understanding", "cut", "color-grade"], operation["depends_on"])
        self.assertEqual({"understanding": 1, "cut": 2, "color-grade": 3}, operation["based_on"])
        self.assertEqual(("video-add-b-roll", 1, "approved"), (operation["skill"], operation["revision"], operation["status"]))
        self.assertEqual(
            {"status": "pending", "report": "../review/03-b-roll/b-roll-summary.md"},
            operation["check"],
        )
        self.assertEqual(["cache/b-roll/normalized/broll-001.mp4"], operation["outputs"])
        self.assertEqual({"kind": "overlay", "asset": "cache/b-roll/normalized/broll-001.mp4", "start_s": 2.0, "duration_s": 2.5}, operation["render"][0])
        self.assertEqual("draft", result["render"]["status"])

    def test_register_operation_requires_verified_approved_normalized_shots_and_orders_overlays(self):
        project = self._registration_project(["cut", "unknown", "content-cards", "captions"])
        result = broll_plan.register_operation(project, self._registered_plan((2, 3), (4, 5), dependencies=["understanding", "cut"]))
        self.assertEqual(["cut", "b-roll", "unknown", "content-cards", "captions"], result["sequences"]["main"]["operations"])
        self.assertEqual(["cache/b-roll/normalized/broll-001.mp4", "cache/b-roll/normalized/broll-002.mp4"], [item["asset"] for item in next(item for item in result["operations"] if item["id"] == "b-roll")["render"]])
        for change in (("status", "selected"), ("normalized", {"path": "../bad.mp4", "sha256": "a" * 64}), ("review.status", "draft")):
            plan = self._registered_plan((2, 3))
            if change[0] == "review.status": plan["review"]["status"] = change[1]
            else: plan["shots"][0][change[0]] = change[1]
            with self.subTest(change=change):
                with self.assertRaises(ValueError): broll_plan.register_operation(project, plan)

    def test_register_operation_removes_old_registration_for_no_selected_shots(self):
        project = self._registration_project(["cut", "b-roll", "b-roll", "captions"])
        project["operations"].append({"id": "b-roll", "revision": 7})
        plan = self._registered_plan((2, 3), dependencies=["understanding", "cut"], skip=True)
        result = broll_plan.register_operation(project, plan)
        self.assertNotIn("b-roll", result["sequences"]["main"]["operations"])
        self.assertFalse(any(item.get("id") == "b-roll" for item in result["operations"]))
        self.assertEqual("draft", result["render"]["status"])

    def test_zero_selection_cleans_stale_broll_ids_from_every_sequence(self):
        project = self._registration_project(["cut", "captions"])
        project["sequences"]["alternate"] = {"operations": ["captions", "b-roll", "b-roll", "unknown"]}
        plan = self._registered_plan((2, 3), dependencies=["understanding", "cut"], skip=True)
        result = broll_plan.register_operation(project, plan)
        self.assertEqual(["captions", "unknown"], result["sequences"]["alternate"]["operations"])
        self.assertEqual("draft", result["render"]["status"])

    def test_zero_selection_without_stale_broll_leaves_render_status(self):
        project = self._registration_project(["cut", "captions"])
        plan = self._registered_plan((2, 3), dependencies=["understanding", "cut"], skip=True)
        result = broll_plan.register_operation(project, plan)
        self.assertEqual("verified", result["render"]["status"])

    def test_register_operation_rejects_missing_nonstrings_and_duplicate_shot_ids(self):
        for shot_id in (None, "", 3):
            plan = self._registered_plan((2, 3)); plan["shots"][0]["id"] = shot_id
            with self.subTest(shot_id=shot_id):
                with self.assertRaisesRegex(ValueError, "registered shot id"): broll_plan.register_operation(self._registration_project(), plan)
        plan = self._registered_plan((2, 3), (4, 5)); plan["shots"][1]["id"] = plan["shots"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate registered shot id"): broll_plan.register_operation(self._registration_project(), plan)

    def test_register_operation_rejects_stale_or_mismatched_plan_dependencies(self):
        cases = [
            ({"dependencies": ["understanding", "cut"]}, "plan dependencies"),
            ({"dependencies": ["understanding", "cut", "color-grade", "captions"]}, "plan dependencies"),
            ({"dependencies": ["cut", "understanding", "color-grade"]}, "plan dependencies"),
            ({"dependencies": ["understanding", "cut", "color-grade", "cut"]}, "plan dependencies"),
            ({"based_on": {"understanding": 1, "cut": 2, "color-grade": 2}}, "plan based_on"),
            ({"based_on": {"understanding": 1, "cut": 2}}, "plan based_on"),
        ]
        for change, message in cases:
            plan = self._registered_plan((2, 3)); plan.update(change)
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, message): broll_plan.register_operation(self._registration_project(), plan)

    def test_active_dependencies_requires_positive_integer_revisions(self):
        for revision in (True, 0, -1, 1.5, "1"):
            project = self._registration_project(); project["operations"][0]["revision"] = revision
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(ValueError, "positive integer"): broll_plan.active_dependencies(project)

    def test_register_operation_rejects_non_object_operations_with_value_error(self):
        for value in (None, [], 3, "operation"):
            project = self._registration_project()
            project["operations"].append(value)
            with self.subTest(value=value):
                try:
                    broll_plan.register_operation(project, self._registered_plan((2, 3)))
                except Exception as error:
                    self.assertIsInstance(error, ValueError)
                    self.assertRegex(str(error), "project operations must be a list of objects")
                else:
                    self.fail("register_operation accepted a non-object operation")

    def test_register_operation_rejects_invalid_existing_broll_revisions(self):
        for revision in (None, "7", [], {}, 1.5, True, 0, -1):
            project = self._registration_project()
            project["operations"].append({"id": "b-roll", "revision": revision})
            project["sequences"]["main"]["operations"].append("b-roll")
            with self.subTest(revision=revision):
                try:
                    broll_plan.register_operation(project, self._registered_plan((2, 3)))
                except Exception as error:
                    self.assertIsInstance(error, ValueError)
                    self.assertRegex(str(error), "project operation b-roll revision must be a positive integer")
                else:
                    self.fail("register_operation accepted an invalid existing B-roll revision")

    def test_register_operation_rejects_non_object_render_for_selected_and_noop_plans(self):
        selected = self._registered_plan((2, 3))
        skipped = self._registered_plan((2, 3), skip=True)
        for value in (None, [], 3, "render", True):
            for kind, plan in (("selected", selected), ("skipped", skipped)):
                project = self._registration_project()
                project["render"] = value
                with self.subTest(value=value, kind=kind):
                    try:
                        broll_plan.register_operation(project, plan)
                    except Exception as error:
                        self.assertIsInstance(error, ValueError)
                        self.assertRegex(str(error), "project render must be an object")
                    else:
                        self.fail("register_operation accepted a non-object project render")

    def test_register_operation_allows_missing_or_object_render_and_increments_valid_revision(self):
        selected = self._registered_plan((2, 3))
        skipped = self._registered_plan((2, 3), skip=True)
        missing_selected = self._registration_project()
        missing_selected.pop("render")
        self.assertEqual("draft", broll_plan.register_operation(missing_selected, selected)["render"]["status"])
        missing_skipped = self._registration_project()
        missing_skipped.pop("render")
        self.assertNotIn("render", broll_plan.register_operation(missing_skipped, skipped))
        self.assertEqual("verified", broll_plan.register_operation(self._registration_project(), skipped)["render"]["status"])

        project = self._registration_project()
        project["operations"].append({"id": "b-roll", "revision": 7})
        project["sequences"]["main"]["operations"].append("b-roll")
        result = broll_plan.register_operation(project, selected)
        operation = next(item for item in result["operations"] if item["id"] == "b-roll")
        self.assertEqual(8, operation["revision"])


class BrollReviewPageTests(_BrollFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.review_dir = self.root / "review/03-b-roll"
        self.video = self.root / "final/current.mp4"
        self.video.parent.mkdir(parents=True, exist_ok=True)
        self.video.write_bytes(b"program")
        self.plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(self.video)
        self.real_probe_video = build_review_page._probe_video
        self.probe = mock.patch.object(build_review_page, "_probe_video", return_value=10.0)
        self.probe.start()
        self.addCleanup(self.probe.stop)

    @staticmethod
    def _frame(video, time_s, output):
        Image.new("RGB", (960, 540), "white").save(output, "JPEG")

    def test_build_review_page_publishes_local_payload_and_immutable_assets(self):
        review_id = "123e4567-e89b-12d3-a456-426614174000"
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(
                self.plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root, review_id=review_id,
            )
        page = result["page"]
        self.assertEqual(page, self.review_dir / f"b-roll-review-{review_id}.html")
        self.assertTrue(result["alias"].is_file())
        self.assertTrue(result["assets_dir"].is_dir())
        self.assertEqual([], result["warnings"])
        html = page.read_text(encoding="utf-8")
        self.assertNotIn("__BROLL_REVIEW_DATA__", html)
        self.assertNotRegex(html, r"(?:src|href)=['\"]https?://")
        payload = json.loads(base64.b64decode(build_review_page.PAYLOAD_RE.search(html).group(1)))
        self.assertEqual(review_id, payload["review_id"])
        self.assertEqual(f"b-roll-review-{review_id}-assets/frame-001.jpg", payload["shots"][0]["source_frame"]["path"])
        self.assertTrue((page.parent / payload["shots"][0]["source_frame"]["path"]).is_file())
        candidate_path = page.parent / payload["shots"][0]["candidates"][0]["path"]
        self.assertEqual(result["assets_dir"], candidate_path.parent)
        self.assertEqual(b"asset", candidate_path.read_bytes())
        self.assertEqual(self.plan["input_hashes"]["review_video_sha256"], payload["review_video_sha256"])
        for field in ("plan_sha256", "candidate_manifest_sha256", "review_video_sha256"):
            self.assertIn(f"{field}:data.{field}", html)
        self.assertIn("type=\"radio\"", html)
        self.assertIn("textarea", html)
        self.assertIn("ken_burns", html)
        self.assertIn("explicit_user_action", html)
        with self.assertRaises(FileExistsError):
            build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=review_id)

    def test_build_review_page_keeps_prior_publication_when_a_second_uuid_is_published(self):
        first = "123e4567-e89b-12d3-a456-426614174001"
        second = "123e4567-e89b-12d3-a456-426614174002"
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            original = build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=first)
            previous_bytes = original["page"].read_bytes()
            next_review = build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=second)
        self.assertEqual(previous_bytes, original["page"].read_bytes())
        self.assertNotEqual(original["assets_dir"], next_review["assets_dir"])

    def test_target_created_during_staging_is_never_overwritten(self):
        review_id = "123e4567-e89b-12d3-a456-426614174004"
        page = self.review_dir / f"b-roll-review-{review_id}.html"
        alias = self.review_dir / "b-roll-review.html"
        self.review_dir.mkdir(parents=True)
        alias.write_bytes(b"prior alias")

        def racing_frame(video, time_s, output):
            self._frame(video, time_s, output)
            page.write_bytes(b"racing publisher")

        with mock.patch.object(build_review_page, "_extract_frame", side_effect=racing_frame):
            with self.assertRaises(FileExistsError):
                build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=review_id)
        self.assertEqual(b"racing publisher", page.read_bytes())
        self.assertEqual(b"prior alias", alias.read_bytes())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_alias_failure_rolls_back_uuid_publication_and_preserves_prior_alias(self):
        review_id = "123e4567-e89b-12d3-a456-426614174005"
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        alias.write_bytes(b"prior alias")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame), mock.patch.object(build_review_page, "_write_alias", side_effect=OSError("alias unavailable")):
            with self.assertRaisesRegex(OSError, "alias unavailable"):
                build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=review_id)
        self.assertEqual(b"prior alias", alias.read_bytes())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_published_candidate_survives_live_cache_replacement(self):
        review_id = "123e4567-e89b-12d3-a456-426614174003"
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root, review_id=review_id)
        payload = json.loads(base64.b64decode(build_review_page.PAYLOAD_RE.search(result["page"].read_text(encoding="utf-8")).group(1)))
        frozen = result["page"].parent / payload["shots"][0]["candidates"][0]["path"]
        live = self.root / "work/cache/b-roll/factory.mp4"
        replacement = live.with_suffix(".replacement")
        replacement.write_bytes(b"changed")
        os.replace(replacement, live)
        self.assertEqual(b"asset", frozen.read_bytes())

    def test_published_candidate_survives_in_place_cache_mutation(self):
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        payload = json.loads(base64.b64decode(build_review_page.PAYLOAD_RE.search(result["page"].read_text(encoding="utf-8")).group(1)))
        frozen = result["page"].parent / payload["shots"][0]["candidates"][0]["path"]
        live = self.root / "work/cache/b-roll/factory.mp4"
        live.write_bytes(b"changed in place")
        self.assertEqual(b"asset", frozen.read_bytes())

    def test_payload_is_ascii_safe_and_unicode_round_trips(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["id"] = "shot-cafe\u0301"
        plan["shots"][0]["queries"] = ["usine animee", "工場の映像"]
        plan["shots"][0]["candidates"][0]["id"] = "候補"
        plan["shots"][0]["candidates"][0]["provenance"]["creator"] = "Jose Alvarez - 東京"
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        encoded = build_review_page.PAYLOAD_RE.search(result["page"].read_text(encoding="utf-8")).group(1)
        payload_bytes = base64.b64decode(encoded)
        payload_bytes.decode("ascii")
        payload = json.loads(payload_bytes)
        self.assertEqual("shot-cafe\u0301", payload["shots"][0]["id"])
        self.assertEqual("工場の映像", payload["shots"][0]["queries"][1])
        self.assertEqual("候補", payload["shots"][0]["candidates"][0]["id"])
        self.assertEqual("Jose Alvarez - 東京", payload["shots"][0]["candidates"][0]["provenance"]["creator"])

    def test_build_review_page_rejects_video_path_hash_and_duration_before_frames(self):
        outside = self.root.parent / f"{self.root.name}-outside.mp4"
        outside.write_bytes(b"program")
        self.addCleanup(outside.unlink, missing_ok=True)
        cases = [(outside, self.plan, 10.0, "inside project_root"), (self.video, {**self.plan, "input_hashes": {**self.plan["input_hashes"], "review_video_sha256": "0" * 64}}, 10.0, "review video SHA-256"), (self.video, self.plan, 9.9, "duration")]
        for video, plan, duration, message in cases:
            with self.subTest(message=message), mock.patch.object(build_review_page, "_probe_video", return_value=duration), mock.patch.object(build_review_page, "_extract_frame") as extract:
                with self.assertRaisesRegex((ValueError, FileNotFoundError), message):
                    build_review_page.build_review_page(plan, self.timeline, self.transcript, video, self.review_dir, project_root=self.root)
                extract.assert_not_called()

    def test_build_review_page_requires_canonical_timeline_and_transcript(self):
        review_id = "123e4567-e89b-12d3-a456-426614174020"
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        alias.write_bytes(b"prior alias")
        substituted_timeline = copy.deepcopy(self.timeline)
        substituted_timeline["fps"] = {"num": 24, "den": 1}
        substituted_transcript = copy.deepcopy(self.transcript)
        substituted_transcript["segments"][0]["words"][0]["word"] = "substituted"
        for label, timeline, transcript in (
            ("timeline", substituted_timeline, self.transcript),
            ("transcript", self.timeline, substituted_transcript),
        ):
            with self.subTest(label=label), mock.patch.object(build_review_page, "_extract_frame") as extract:
                with self.assertRaisesRegex(ValueError, f"caller {label} does not match canonical"):
                    build_review_page.build_review_page(
                        self.plan, timeline, transcript, self.video, self.review_dir,
                        project_root=self.root, review_id=review_id,
                    )
                extract.assert_not_called()
                self.assertEqual(b"prior alias", alias.read_bytes())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_build_review_page_requires_present_valid_canonical_files(self):
        paths = [self.timeline_path, self.transcript_path, self.project_path]
        review_ids = [
            "123e4567-e89b-12d3-a456-426614174021",
            "123e4567-e89b-12d3-a456-426614174022",
            "123e4567-e89b-12d3-a456-426614174023",
            "123e4567-e89b-12d3-a456-426614174024",
            "123e4567-e89b-12d3-a456-426614174025",
            "123e4567-e89b-12d3-a456-426614174026",
        ]
        cases = [(path, None, "missing") for path in paths] + [(path, b"{", "invalid") for path in paths]
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        for (path, replacement, message), review_id in zip(cases, review_ids):
            original = path.read_bytes()
            if replacement is None:
                path.unlink()
            else:
                path.write_bytes(replacement)
            alias.write_bytes(b"prior alias")
            try:
                with self.subTest(path=path.name, message=message), mock.patch.object(build_review_page, "_extract_frame") as extract:
                    with self.assertRaisesRegex((ValueError, FileNotFoundError), f"canonical .* {message}"):
                        build_review_page.build_review_page(
                            self.plan, self.timeline, self.transcript, self.video, self.review_dir,
                            project_root=self.root, review_id=review_id,
                        )
                    extract.assert_not_called()
                    self.assertEqual(b"prior alias", alias.read_bytes())
                    self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
                    self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())
            finally:
                path.write_bytes(original)

    def test_build_review_page_rejects_stale_canonical_project(self):
        original = self.project_path.read_bytes()
        cases = []
        revision = copy.deepcopy(self.project)
        revision["operations"][2]["revision"] = 4
        cases.append((revision, "based_on color-grade revision is stale"))
        inactive = copy.deepcopy(self.project)
        inactive["sequences"]["main"]["operations"] = ["cut"]
        cases.append((inactive, "dependencies do not match"))
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        for index, (project, message) in enumerate(cases, 27):
            review_id = f"123e4567-e89b-12d3-a456-4266141740{index}"
            projectlib.write_json(self.project_path, project)
            alias.write_bytes(b"prior alias")
            try:
                with self.subTest(message=message), mock.patch.object(build_review_page, "_extract_frame") as extract:
                    with self.assertRaisesRegex(ValueError, message):
                        build_review_page.build_review_page(
                            self.plan, self.timeline, self.transcript, self.video, self.review_dir,
                            project_root=self.root, review_id=review_id,
                        )
                    extract.assert_not_called()
                    self.assertEqual(b"prior alias", alias.read_bytes())
                    self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
                    self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())
            finally:
                self.project_path.write_bytes(original)

    def test_build_review_page_rejects_noncanonical_dependencies_before_publication(self):
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        for index, dependencies in enumerate((
            ["cut", "understanding", "color-grade"],
            ["understanding", "cut", "color-grade", "cut"],
        ), 30):
            plan = copy.deepcopy(self.plan)
            plan["dependencies"] = dependencies
            review_id = f"123e4567-e89b-12d3-a456-4266141740{index}"
            alias.write_bytes(b"prior alias")
            with self.subTest(dependencies=dependencies), mock.patch.object(build_review_page, "_extract_frame") as extract:
                with self.assertRaisesRegex(ValueError, "dependencies do not match"):
                    build_review_page.build_review_page(
                        plan, self.timeline, self.transcript, self.video, self.review_dir,
                        project_root=self.root, review_id=review_id,
                    )
                extract.assert_not_called()
                self.assertEqual(b"prior alias", alias.read_bytes())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_build_review_page_rejects_invalid_candidate_duration_before_publication(self):
        review_id = "123e4567-e89b-12d3-a456-426614174006"
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0]["duration_s"] = 0
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        alias.write_bytes(b"prior alias")
        with mock.patch.object(build_review_page, "_extract_frame") as extract:
            with self.assertRaisesRegex(ValueError, "duration_s"):
                build_review_page.build_review_page(
                    plan, self.timeline, self.transcript, self.video, self.review_dir,
                    project_root=self.root, review_id=review_id,
                )
        extract.assert_not_called()
        self.assertEqual(b"prior alias", alias.read_bytes())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_payload_candidate_duration_is_always_a_positive_finite_number(self):
        variants = [
            ({"probe": {"duration_s": 3}}, ("duration_s",), 3.0),
            ({"probe": {"duration_s": 3.5}}, ("duration_s",), 3.5),
            ({"duration_s": 999, "probe": {"duration_s": 1}}, (), 1.0),
            ({"duration_s": 0.5, "probe": {"duration_s": 2}}, (), 2.0),
        ]
        for index, (variant, removed, expected) in enumerate(variants, 10):
            plan = copy.deepcopy(self.plan)
            for key in removed:
                plan["shots"][0]["candidates"][0].pop(key)
            plan["shots"][0]["candidates"][0].update(variant)
            review_id = f"123e4567-e89b-12d3-a456-4266141740{index}"
            with self.subTest(variant=variant), mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
                result = build_review_page.build_review_page(
                    plan, self.timeline, self.transcript, self.video, self.review_dir,
                    project_root=self.root, review_id=review_id,
                )
            encoded = build_review_page.PAYLOAD_RE.search(result["page"].read_text(encoding="utf-8")).group(1)
            payload = json.loads(base64.b64decode(encoded))
            duration = payload["shots"][0]["candidates"][0]["duration_s"]
            self.assertIsInstance(duration, (int, float))
            self.assertNotIsInstance(duration, bool)
            self.assertTrue(math.isfinite(duration))
            self.assertGreater(duration, 0)
            self.assertEqual(expected, duration)

    def test_build_review_page_does_not_invent_video_duration(self):
        for index, keep_direct in enumerate((False, True), 8):
            review_id = f"123e4567-e89b-12d3-a456-4266141740{index:02d}"
            plan = copy.deepcopy(self.plan)
            candidate = plan["shots"][0]["candidates"][0]
            candidate.pop("probe")
            if keep_direct:
                candidate["duration_s"] = 999
            else:
                candidate.pop("duration_s")
            self.review_dir.mkdir(parents=True, exist_ok=True)
            alias = self.review_dir / "b-roll-review.html"
            alias.write_bytes(b"prior alias")
            with self.subTest(keep_direct=keep_direct), mock.patch.object(build_review_page, "_extract_frame") as extract:
                with self.assertRaisesRegex(ValueError, "duration"):
                    build_review_page.build_review_page(
                        plan, self.timeline, self.transcript, self.video, self.review_dir,
                        project_root=self.root, review_id=review_id,
                    )
                extract.assert_not_called()
                self.assertEqual(b"prior alias", alias.read_bytes())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
                self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_payload_nan_rolls_back_publication_and_preserves_alias(self):
        review_id = "123e4567-e89b-12d3-a456-426614174007"
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0]["provenance"]["metadata"] = {"score": float("nan")}
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        alias.write_bytes(b"prior alias")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            with self.assertRaisesRegex(ValueError, "JSON compliant"):
                build_review_page.build_review_page(
                    plan, self.timeline, self.transcript, self.video, self.review_dir,
                    project_root=self.root, review_id=review_id,
                )
        self.assertEqual(b"prior alias", alias.read_bytes())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}.html").exists())
        self.assertFalse((self.review_dir / f"b-roll-review-{review_id}-assets").exists())

    def test_probe_video_requires_video_stream_and_positive_finite_duration(self):
        for payload in ([], {"streams": "invalid", "format": {"duration": "10"}}, {"streams": [], "format": {"duration": "10"}}, {"streams": [{"index": 0}], "format": {"duration": "nan"}}, {"streams": [{"index": 0}], "format": {"duration": "0"}}):
            with self.subTest(payload=payload), mock.patch.object(build_review_page.subprocess, "run", return_value=mock.Mock(stdout=json.dumps(payload))):
                with self.assertRaisesRegex(ValueError, "video|duration"):
                    self.real_probe_video(self.video)

    def test_review_jpeg_requires_exact_review_width(self):
        wrong = self.root / "wrong.jpg"
        Image.new("RGB", (959, 540), "white").save(wrong, "JPEG")
        with self.assertRaisesRegex(ValueError, "valid JPEG"):
            build_review_page._validate_jpeg(wrong)

    def test_template_blocks_invalid_selected_media_controls(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("路", template)
        for text in ("Number.isFinite(start)", "end>start", "end>duration", "ken_burns", "Select a Ken Burns direction", "Invalid video trim"):
            self.assertIn(text, template)
        for text in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;", "@media(max-width:600px)", "overflow-wrap:anywhere"):
            self.assertIn(text, template)
        self.assertIn("Queries:", template)
        self.assertIn("shot.queries", template)
        self.assertIn("data.pre_skipped_ids.map", template)
        self.assertIn("timestamp:new Date().toISOString()", template)

    def test_mixed_plan_exports_pre_skipped_shot_exactly_once(self):
        plan = copy.deepcopy(self.plan)
        skipped = copy.deepcopy(plan["shots"][0])
        skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": [self.mapped_words[2]]}, "candidates": [], "selected": None, "status": "skipped"})
        plan["shots"].append(skipped)
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        payload = json.loads(base64.b64decode(build_review_page.PAYLOAD_RE.search(result["page"].read_text(encoding="utf-8")).group(1)))
        self.assertEqual(["already-skipped"], payload["pre_skipped_ids"])
        self.assertEqual(["shot"], [shot["id"] for shot in payload["shots"]])
        review = {key: payload[key] for key in ("review_id", "plan_sha256", "candidate_manifest_sha256", "review_video_sha256")}
        review.update({"rationale": "Relevant footage.", "timestamp": "2026-07-23T12:00:00Z"})
        review["shots"] = [{"id": shot_id, "decision": "skip"} for shot_id in payload["pre_skipped_ids"]] + [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}]
        approved = broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual(["selected", "skipped"], [shot["status"] for shot in approved["shots"]])

    def test_quoted_ids_remain_only_encoded_data(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["id"] = 'shot" onmouseover="evil'
        plan["shots"][0]["candidates"][0]["id"] = "asset' onerror='evil"
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        html = result["page"].read_text(encoding="utf-8")
        self.assertNotIn('onmouseover="evil', html)
        self.assertNotIn("onerror='evil", html)

    def test_build_review_page_rejects_invalid_or_escaping_input_without_publication(self):
        invalid = copy.deepcopy(self.plan)
        invalid["shots"][0]["candidates"][0]["cache_path"] = "../outside.mp4"
        with self.assertRaises(ValueError):
            build_review_page.build_review_page(invalid, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        self.assertFalse(self.review_dir.exists())

    def test_build_review_page_rolls_back_bad_frame(self):
        def broken(video, time_s, output):
            output.write_bytes(b"not jpeg")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=broken):
            with self.assertRaises(ValueError):
                build_review_page.build_review_page(self.plan, self.timeline, self.transcript, self.video, self.review_dir, project_root=self.root)
        self.assertFalse(self.review_dir.exists())


class NormalizeAndCheckTests(_BrollFixture, unittest.TestCase):
    def setUp(self):
        _BrollFixture.setUp(self)
        self.candidates = self.root / "work/cache/b-roll/candidates"
        self.candidates.mkdir(parents=True)
        self.output = self.root / "work/cache/b-roll/normalized/broll-001.mp4"
        self.timeline.update({"width": 96, "height": 54, "fps": {"num": 30000, "den": 1001}})
        projectlib.write_json(self.timeline_path, self.timeline)
        self.selected_lut_path.write_text(
            'TITLE "Identity"\nLUT_3D_SIZE 2\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n'
            "0 0 0\n0 0 1\n0 1 0\n0 1 1\n1 0 0\n1 0 1\n1 1 0\n1 1 1\n",
            encoding="ascii",
        )
        source = self._video()
        candidate = self.plan["shots"][0]["candidates"][0]
        candidate.update({
            "cache_path": source.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(source), "bytes": source.stat().st_size,
            "duration_s": 2.0, "probe": {"duration_s": 2.0, "width": 128, "height": 96},
        })
        self.plan["input_hashes"].update({
            "timeline_sha256": broll_plan.sha256_file(self.timeline_path),
            "grade_plan_sha256": broll_plan.sha256_file(self.grade_plan_path),
            "selected_lut_sha256": broll_plan.sha256_file(self.selected_lut_path),
        })
        self.base_plan = copy.deepcopy(self.plan)
        self.plan = self._approve(self.base_plan)
        self.plan_path = self.root / "work/b-roll/broll-plan.json"
        projectlib.write_json(self.plan_path, self.plan)

    def _approve(self, plan):
        decisions = [
            {"id": shot["id"], "decision": "select", "candidate_id": shot["candidates"][0]["id"], "source_trim": {"start_s": 0.25, "end_s": 1.25}}
            for shot in plan["shots"]
        ]
        return broll_plan.apply_review(
            plan, self.review_for(plan, decisions), mode="agent", actor="agent", rationale="Relevant footage."
        )

    def _two_shot_plan(self):
        plan = copy.deepcopy(self.base_plan)
        second = copy.deepcopy(plan["shots"][0])
        second.update({
            "id": "second", "program_range": {"start_s": 2, "end_s": 3},
            "source_ranges": [{"clip_id": "one", "start_s": 2, "end_s": 3}],
            "transcript_evidence": {"words": [self.mapped_words[1]]},
        })
        second["candidates"][0]["id"] = "asset-2"
        plan["shots"].append(second)
        return self._approve(plan)

    def _video(self, name="source.mp4"):
        path = self.candidates / name
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=128x96:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ], check=True, capture_output=True)
        return path

    def _video_shot(self, source):
        candidate = {
            "id": "asset", "media_type": "video",
            "cache_path": source.relative_to(self.root / "work").as_posix(),
            "probe": {"duration_s": 2.0},
        }
        shot = {
            "id": "shot", "status": "selected",
            "program_range": {"start_s": 0, "end_s": 1},
            "candidates": [candidate],
            "selected": {"candidate_id": "asset", "source_trim": {"start_s": 0.25, "end_s": 1.25}},
        }
        return candidate, shot

    def _review_video(self):
        path = self.root / "final/review.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=blue:size=96x54:rate=30000/1001",
            "-t", "10", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
        ], check=True, capture_output=True)
        return path

    def _normalized_for_check(self):
        video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        projectlib.write_json(self.plan_path, self._approve(plan))
        return video, normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        )

    def _seed_review_outputs(self):
        review_dir = self.root / "review/03-b-roll"
        (review_dir / "stills").mkdir(parents=True, exist_ok=True)
        (review_dir / "assets").mkdir(exist_ok=True)
        expected = {
            "stills/old.txt": b"old stills",
            "contact-sheet.jpg": b"old contact",
            "boundary-reel.mp4": b"old reel",
            "b-roll-summary.md": b"old summary",
        }
        for relative, content in expected.items():
            (review_dir / relative).write_bytes(content)
        (review_dir / "index.html").write_text("review page", encoding="utf-8")
        (review_dir / "assets/review.js").write_text("immutable asset", encoding="utf-8")
        return review_dir, expected

    def _assert_old_review_outputs(self, review_dir, expected):
        for relative, content in expected.items():
            self.assertEqual(content, (review_dir / relative).read_bytes())
        self.assertEqual("review page", (review_dir / "index.html").read_text(encoding="utf-8"))
        self.assertEqual("immutable asset", (review_dir / "assets/review.js").read_text(encoding="utf-8"))

    def _verification_artifact_bytes(self, plan):
        verification = plan["shots"][0]["verification"]
        bindings = [verification["contact_sheet"], verification["boundary_reel"], verification["report"],
                    *verification["stills"].values()]
        return {binding["path"]: (self.root / binding["path"]).read_bytes() for binding in bindings}

    def _tree_snapshot(self, root):
        root = Path(root)
        if not root.exists():
            return None
        snapshot = {".": ("directory", None)}

        def visit(directory):
            for entry in os.scandir(directory):
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                linked = entry.is_symlink() or (
                    hasattr(path, "is_junction") and path.is_junction()
                )
                if linked:
                    snapshot[relative] = ("link", os.readlink(path))
                elif entry.is_dir(follow_symlinks=False):
                    snapshot[relative] = ("directory", None)
                    visit(path)
                else:
                    snapshot[relative] = ("file", path.read_bytes())

        visit(root)
        return snapshot

    def _directory_link_or_skip(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
            return
        except PermissionError as exc:
            symlink_error = exc
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                symlink_error = exc
            else:
                raise
        if os.name == "nt":
            junction = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True, text=True,
            )
            if junction.returncode == 0:
                return
            raise OSError(
                f"directory symlink failed ({symlink_error}); "
                f"junction failed ({junction.returncode}): {junction.stderr.strip()}"
            )
        self.skipTest(f"directory symlinks are unavailable: {symlink_error}")

    def _crash_verification(self, video, mode):
        code = """
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import check_broll
real_replace = os.replace
plan, review_dir, mode = Path(sys.argv[3]).resolve(), Path(sys.argv[7]).resolve(), sys.argv[8]
def crash_after_move(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    phase = None
    if target.name == "marker.json" and source.is_file():
        phase = json.loads(source.read_text(encoding="utf-8")).get("phase")
    result = real_replace(source, target)
    if mode == "first-old" and source == review_dir / "stills" and target != review_dir / "stills":
        os._exit(91)
    if mode == "all-new" and target == review_dir / "b-roll-summary.md":
        os._exit(92)
    if mode == "plan" and target == plan:
        os._exit(93)
    if mode == "artifacts-published" and phase == "artifacts-published":
        os._exit(94)
    return result
os.replace = crash_after_move
check_broll.verify_plan(sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
"""
        return subprocess.run([
            sys.executable, "-c", code, str(ROOT / "scripts"),
            str(ROOT.parent / "video-understand" / "scripts"),
            str(self.plan_path), str(self.timeline_path), str(self.root), str(video),
            str(self.root / "review/03-b-roll"), mode,
        ], capture_output=True, text=True)

    def _reel_pixel(self, reel, time_s):
        frame = self.root / f"reel-{time_s}.png"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", str(time_s), "-i", str(reel),
            "-frames:v", "1", str(frame),
        ], check=True, capture_output=True)
        with Image.open(frame) as image:
            return image.convert("RGB").getpixel((image.width // 2, image.height // 2))

    def test_normalizes_video_to_dimensions_fps_duration_and_no_audio(self):
        candidate, shot = self._video_shot(self._video())
        record = normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output)
        self.assertEqual(self.output, record["path"])
        self.assertEqual((96, 54), (record["probe"]["width"], record["probe"]["height"]))
        self.assertEqual({"num": 30000, "den": 1001}, record["probe"]["fps"])
        self.assertEqual("1:1", record["probe"]["sar"])
        self.assertFalse(record["probe"]["has_audio"])
        self.assertAlmostEqual(1.0, record["probe"]["duration_s"], delta=1001 / 30000)

        updated = normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        self.assertEqual("normalized", updated["shots"][0]["status"])
        self.assertEqual("cache/b-roll/normalized/broll-001.mp4", updated["shots"][0]["normalized"]["path"])
        self.assertEqual(
            {key: self.plan["input_hashes"][key] for key in ("grade_plan_sha256", "selected_lut_sha256")},
            {key: updated["shots"][0]["normalized"][key] for key in ("grade_plan_sha256", "selected_lut_sha256")},
        )
        self.assertEqual(updated, projectlib.load_json(self.plan_path))

    def test_normalize_and_verify_plans_derive_missing_geometry_from_canonical_media(self):
        self.timeline.pop("width")
        self.timeline.pop("height")
        projectlib.write_json(self.timeline_path, self.timeline)
        projectlib.write_json(
            self.root / "work/understand/media.json", {"width": 96, "height": 54}
        )
        video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["timeline_sha256"] = broll_plan.sha256_file(self.timeline_path)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        projectlib.write_json(self.plan_path, self._approve(plan))

        normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        )
        verified, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )

        self.assertEqual((96, 54), (
            verified["shots"][0]["normalized"]["probe"]["width"],
            verified["shots"][0]["normalized"]["probe"]["height"],
        ))
        self.assertEqual("verified", verified["shots"][0]["status"])
        self.assertTrue(artifacts["contact_sheet"].is_file())
        self.assertTrue(
            {"width", "height"}.isdisjoint(projectlib.load_json(self.timeline_path))
        )

    def test_normalize_shot_preserves_existing_target_until_atomic_success(self):
        candidate, shot = self._video_shot(self.candidates / "source.mp4")
        sentinel = b"last-good-normalized-output"
        part = self.output.with_suffix(".part.mp4")
        invalid = copy.deepcopy(shot)
        invalid["selected"].pop("source_trim")
        real_run = subprocess.run

        def fail_render(command, *args, **kwargs):
            if command[0] == "ffmpeg" and "-vf" in command:
                raise subprocess.CalledProcessError(1, command)
            return real_run(command, *args, **kwargs)

        def render_failure():
            with mock.patch.object(normalize_broll.subprocess, "run", side_effect=fail_render):
                normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output)

        failures = (
            ("validation", ValueError, lambda: normalize_broll.normalize_shot(candidate, invalid, self.timeline, self.output)),
            ("render", subprocess.CalledProcessError, render_failure),
        )
        for name, error, action in failures:
            with self.subTest(name=name):
                self.output.parent.mkdir(parents=True, exist_ok=True)
                self.output.write_bytes(sentinel)
                part.write_bytes(b"stale-part")
                with self.assertRaises(error):
                    action()
                self.assertTrue(self.output.exists())
                self.assertEqual(sentinel, self.output.read_bytes())
                self.assertFalse(part.exists())

        self.output.write_bytes(sentinel)
        record = normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output)
        self.assertNotEqual(sentinel, self.output.read_bytes())
        self.assertEqual(broll_plan.sha256_file(self.output), record["sha256"])

    def test_explicit_still_uses_ken_burns_but_no_implicit_fallback(self):
        source = self.candidates / "still.png"
        image = Image.new("RGB", (128, 96))
        image.putdata([(x * 2, y * 2, (x + y) % 256) for y in range(96) for x in range(128)])
        image.save(source)
        candidate = {
            "id": "still", "media_type": "image",
            "cache_path": source.relative_to(self.root / "work").as_posix(),
        }
        shot = {
            "id": "shot", "status": "selected",
            "program_range": {"start_s": 0, "end_s": 1},
            "candidates": [candidate],
            "selected": {"candidate_id": "still", "ken_burns": {"direction": "zoom-in"}},
        }
        record = normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output)
        self.assertEqual(self.output, record["path"])
        first, last = self.root / "first.png", self.root / "last.png"
        for time_s, frame in ((0, first), (0.8, last)):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(time_s), "-i", str(self.output), "-frames:v", "1", str(frame)], check=True, capture_output=True)
        with Image.open(first) as first_image, Image.open(last) as last_image:
            self.assertNotEqual(first_image.tobytes(), last_image.tobytes())

        implicit = copy.deepcopy(shot)
        implicit["selected"].pop("ken_burns")
        fallback = self.output.with_name("implicit.mp4")
        with self.assertRaisesRegex(ValueError, "ken_burns"):
            normalize_broll.normalize_shot(candidate, implicit, self.timeline, fallback)
        self.assertFalse(fallback.exists())
        self.assertFalse(fallback.with_suffix(".part.mp4").exists())

    def test_active_lut_is_applied_by_basename_from_lut_cwd(self):
        candidate, shot = self._video_shot(self._video("graded-source.mp4"))
        lut = self.root / "final/look.cube"
        lut.parent.mkdir(parents=True, exist_ok=True)
        lut.write_text(
            'TITLE "Identity"\nLUT_3D_SIZE 2\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n'
            "0 0 0\n0 0 1\n0 1 0\n0 1 1\n1 0 0\n1 0 1\n1 1 0\n1 1 1\n",
            encoding="ascii",
        )
        grade_plan = self.root / "work/color-grade/grade-plan.json"
        projectlib.write_json(grade_plan, {"schema_version": 1, "selected_lut": "../../final/look.cube"})
        calls, real_run = [], subprocess.run

        def capture(command, *args, **kwargs):
            calls.append((command, kwargs.get("cwd")))
            return real_run(command, *args, **kwargs)

        with mock.patch.object(normalize_broll.subprocess, "run", side_effect=capture):
            record = normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output, lut=lut)
        command, cwd = next((command, cwd) for command, cwd in calls if command[0] == "ffmpeg" and "-vf" in command)
        video_filter = command[command.index("-vf") + 1]
        self.assertIn("lut3d=look.cube", video_filter)
        self.assertNotIn(str(lut), video_filter)
        self.assertEqual(lut.parent.resolve(), Path(cwd).resolve())
        self.assertEqual(broll_plan.sha256_file(grade_plan), record["grade_plan_sha256"])
        self.assertEqual(broll_plan.sha256_file(lut), record["selected_lut_sha256"])

    def test_resume_persists_each_shot_and_reuses_only_valid_normalized_output(self):
        projectlib.write_json(self.plan_path, self._two_shot_plan())
        real_normalize = normalize_broll.normalize_shot
        calls = []

        def fail_second(candidate, *args, **kwargs):
            calls.append(candidate["id"])
            if candidate["id"] == "asset-2":
                raise RuntimeError("later shot failed")
            return real_normalize(candidate, *args, **kwargs)

        with mock.patch.object(normalize_broll, "normalize_shot", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "later shot failed"):
                normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        persisted = projectlib.load_json(self.plan_path)
        self.assertEqual(["normalized", "selected"], [shot["status"] for shot in persisted["shots"]])
        self.assertEqual([], broll_plan.validate_plan(
            persisted, self.timeline, self.transcript, project=self.project, project_root=self.root, verify_files=True
        ))
        first_output = self.output.read_bytes()

        stale = copy.deepcopy(persisted)
        stale["shots"][0]["normalized"]["sha256"] = "0" * 64
        projectlib.write_json(self.plan_path, stale)
        with mock.patch.object(normalize_broll, "normalize_shot", wraps=real_normalize) as render:
            with self.assertRaisesRegex(ValueError, "normalized.*SHA-256"):
                normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
            render.assert_not_called()
        self.assertEqual(first_output, self.output.read_bytes())

        projectlib.write_json(self.plan_path, persisted)
        with mock.patch.object(normalize_broll, "normalize_shot", wraps=real_normalize) as render:
            updated = normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        self.assertEqual(1, render.call_count)
        self.assertEqual("asset-2", render.call_args.args[0]["id"])
        self.assertEqual(first_output, self.output.read_bytes())
        self.assertEqual(["normalized", "normalized"], [shot["status"] for shot in updated["shots"]])

    def test_plan_rejects_unapproved_tampered_and_stale_canonical_inputs(self):
        original = {
            "plan": copy.deepcopy(self.plan), "timeline": copy.deepcopy(self.timeline),
            "transcript": copy.deepcopy(self.transcript), "project": copy.deepcopy(self.project),
            "source": (self.candidates / "source.mp4").read_bytes(),
        }
        cases = []
        cases.append(("unapproved", copy.deepcopy(self.base_plan), None, "review_status must be approved"))
        tampered = copy.deepcopy(self.plan)
        tampered["shots"][0]["selected"]["source_trim"]["start_s"] = 0.5
        cases.append(("review", tampered, None, "review decisions do not match"))
        transcript = copy.deepcopy(self.transcript); transcript["extra"] = True
        cases.append(("transcript", copy.deepcopy(self.plan), (self.transcript_path, transcript), "transcript SHA-256 is stale"))
        timeline = copy.deepcopy(self.timeline); timeline["fps"] = {"num": 24, "den": 1}
        cases.append(("timeline", copy.deepcopy(self.plan), (self.timeline_path, timeline), "timeline SHA-256 is stale"))
        project = copy.deepcopy(self.project); next(item for item in project["operations"] if item["id"] == "cut")["revision"] = 99
        cases.append(("dependency", copy.deepcopy(self.plan), (self.project_path, project), "based_on cut revision is stale"))
        cases.append(("candidate", copy.deepcopy(self.plan), (self.candidates / "source.mp4", original["source"] + b"changed"), "candidate asset SHA-256 is stale"))

        for name, plan, mutation, message in cases:
            with self.subTest(name=name):
                projectlib.write_json(self.plan_path, plan)
                projectlib.write_json(self.timeline_path, original["timeline"])
                projectlib.write_json(self.transcript_path, original["transcript"])
                projectlib.write_json(self.project_path, original["project"])
                (self.candidates / "source.mp4").write_bytes(original["source"])
                self.output.unlink(missing_ok=True)
                if mutation:
                    path, value = mutation
                    projectlib.write_json(path, value) if isinstance(value, dict) else path.write_bytes(value)
                with self.assertRaisesRegex(ValueError, message):
                    normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
                self.assertFalse(self.output.exists())

    def test_plan_requires_exact_canonical_plan_and_timeline_paths(self):
        alternate_plan = self.root / "work/b-roll/alternate-plan.json"
        alternate_timeline = self.root / "work/alternate-timeline.json"
        projectlib.write_json(alternate_plan, self.plan)
        projectlib.write_json(alternate_timeline, self.timeline)
        canonical_plan = self.plan_path.read_bytes()
        cases = (
            (alternate_plan, self.timeline_path, "plan_path must be canonical"),
            (self.plan_path, alternate_timeline, "timeline_path must be canonical"),
        )
        for plan_path, timeline_path, message in cases:
            with self.subTest(message=message):
                self.output.unlink(missing_ok=True)
                with mock.patch.object(normalize_broll, "normalize_shot", wraps=normalize_broll.normalize_shot) as render, mock.patch.object(normalize_broll.projectlib, "write_json", wraps=projectlib.write_json) as write:
                    with self.assertRaisesRegex(ValueError, message):
                        normalize_broll.normalize_plan(plan_path, timeline_path, self.root, lut=self.selected_lut_path)
                    render.assert_not_called()
                    write.assert_not_called()
                self.assertFalse(self.output.exists())
                self.assertFalse(self.output.with_suffix(".part.mp4").exists())
                self.assertEqual(canonical_plan, self.plan_path.read_bytes())

    def test_plan_write_failure_removes_only_new_unrecorded_output(self):
        projectlib.write_json(self.plan_path, self._two_shot_plan())
        real_normalize = normalize_broll.normalize_shot

        def fail_second(candidate, *args, **kwargs):
            if candidate["id"] == "asset-2":
                raise RuntimeError("pause after first")
            return real_normalize(candidate, *args, **kwargs)

        with mock.patch.object(normalize_broll, "normalize_shot", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "pause after first"):
                normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        persisted = projectlib.load_json(self.plan_path)
        first_bytes = self.output.read_bytes()
        second_output = self.output.with_name("broll-002.mp4")
        real_write = projectlib.write_json

        def fail_after_write(path, value):
            real_write(path, value)
            raise OSError("disk full")

        with mock.patch.object(normalize_broll.projectlib, "write_json", side_effect=fail_after_write):
            with self.assertRaisesRegex(OSError, "disk full"):
                normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        self.assertEqual(persisted, projectlib.load_json(self.plan_path))
        self.assertEqual(first_bytes, self.output.read_bytes())
        self.assertFalse(second_output.exists())
        self.assertFalse(second_output.with_suffix(".part.mp4").exists())
        self.assertFalse(self.plan_path.with_suffix(".part.json").exists())

    def test_plan_uses_reviewed_cache_path_not_candidate_path(self):
        reviewed = self.candidates / "reviewed.mp4"
        alternate = self.candidates / "alternate.mp4"
        for path, color in ((reviewed, "blue"), (alternate, "red")):
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                f"color={color}:size=128x96:rate=24", "-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
            ], check=True, capture_output=True)
        plan = copy.deepcopy(self.base_plan)
        candidate = plan["shots"][0]["candidates"][0]
        candidate.update({
            "cache_path": reviewed.relative_to(self.root / "work").as_posix(),
            "path": alternate.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(reviewed), "bytes": reviewed.stat().st_size,
        })
        projectlib.write_json(self.plan_path, self._approve(plan))
        calls, real_run = [], subprocess.run

        def capture(command, *args, **kwargs):
            calls.append(command)
            return real_run(command, *args, **kwargs)

        with mock.patch.object(normalize_broll.subprocess, "run", side_effect=capture):
            updated = normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path)
        record = updated["shots"][0]["normalized"]
        command = next(command for command in calls if command[0] == "ffmpeg" and "-vf" in command)
        self.assertEqual(reviewed.resolve(), Path(command[command.index("-i") + 1]).resolve())
        self.assertEqual(candidate["cache_path"], record["source_path"])
        self.assertEqual(candidate["sha256"], record.get("source_sha256"))

    def test_plan_requires_active_grade_and_omits_hashes_without_grade(self):
        with mock.patch.object(normalize_broll, "normalize_shot", wraps=normalize_broll.normalize_shot) as render:
            with self.assertRaisesRegex(ValueError, "selected LUT is required"):
                normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root)
            render.assert_not_called()
        self.assertFalse(self.output.exists())

        plan = copy.deepcopy(self.base_plan)
        plan["dependencies"] = ["understanding", "cut"]
        plan["based_on"].pop("color-grade")
        plan["input_hashes"].pop("grade_plan_sha256")
        plan["input_hashes"].pop("selected_lut_sha256")
        project = copy.deepcopy(self.project)
        project["sequences"]["main"]["operations"] = ["cut"]
        projectlib.write_json(self.project_path, project)
        projectlib.write_json(self.plan_path, self._approve(plan))
        updated = normalize_broll.normalize_plan(self.plan_path, self.timeline_path, self.root)
        record = updated["shots"][0]["normalized"]
        self.assertNotIn("grade_plan_sha256", record)
        self.assertNotIn("selected_lut_sha256", record)

    def test_equivalent_unreduced_timeline_fps_is_accepted(self):
        timeline = copy.deepcopy(self.timeline)
        timeline["fps"] = {"num": 60000, "den": 2002}
        candidate, shot = self._video_shot(self.candidates / "source.mp4")
        record = normalize_broll.normalize_shot(candidate, shot, timeline, self.output)
        self.assertEqual({"num": 30000, "den": 1001}, record["probe"]["fps"])

    def test_checker_rejects_bad_hash_audio_short_duration_and_stale_receipt(self):
        video, normalized = self._normalized_for_check()
        original_output = self.output.read_bytes()
        review_dir = self.root / "review/03-b-roll"
        cases = []

        bad_hash = copy.deepcopy(normalized)
        bad_hash["shots"][0]["normalized"]["sha256"] = "0" * 64
        cases.append(("hash", bad_hash, None, "SHA-256"))

        audio = copy.deepcopy(normalized)
        cases.append(("audio", audio, [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=96x54:rate=30000/1001",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
            "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", str(self.output),
        ], "non-video streams"))

        short = copy.deepcopy(normalized)
        cases.append(("short", short, [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=96x54:rate=30000/1001",
            "-t", "0.8", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.output),
        ], "duration"))

        stale = copy.deepcopy(normalized)
        stale["review"]["plan_sha256"] = "0" * 64
        cases.append(("receipt", stale, None, "review plan SHA-256"))

        for name, plan, render, message in cases:
            with self.subTest(name=name):
                self.output.write_bytes(original_output)
                if render:
                    subprocess.run(render, check=True, capture_output=True)
                    plan["shots"][0]["normalized"]["sha256"] = broll_plan.sha256_file(self.output)
                    plan["shots"][0]["normalized"]["probe"] = normalize_broll._probe(self.output)
                projectlib.write_json(self.plan_path, plan)
                canonical = self.plan_path.read_bytes()
                with self.assertRaisesRegex(ValueError, message):
                    check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
                self.assertEqual(canonical, self.plan_path.read_bytes())
                self.assertEqual("normalized", projectlib.load_json(self.plan_path)["shots"][0]["status"])
                self.assertFalse(review_dir.exists())

    def test_checker_writes_three_stills_contact_sheet_boundary_reel_and_summary(self):
        video, normalized = self._normalized_for_check()
        immutable = self.root / "review/03-b-roll/index.html"
        immutable.parent.mkdir(parents=True)
        immutable.write_text("review page", encoding="utf-8")
        updated, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )

        self.assertEqual("verified", updated["shots"][0]["status"])
        self.assertEqual(updated, projectlib.load_json(self.plan_path))
        verification = updated["shots"][0]["verification"]
        self.assertEqual("pass", verification["status"])
        self.assertEqual(normalized["shots"][0]["normalized"]["sha256"], verification["normalized_sha256"])

        stills = [Path(path) for path in artifacts["stills"]]
        self.assertEqual(3, len(stills))
        for label, path in zip(("first", "middle", "last"), stills):
            with Image.open(path) as image:
                image.load()
                self.assertEqual((96, 54), image.size)
            binding = verification["stills"][label]
            self.assertEqual(path.relative_to(self.root).as_posix(), binding["path"])
            self.assertEqual(broll_plan.sha256_file(path), binding["sha256"])

        contact_sheet = Path(artifacts["contact_sheet"])
        with Image.open(contact_sheet) as image:
            image.load()
            self.assertEqual("JPEG", image.format)
            self.assertGreater(image.width, 96 * 3)
            self.assertGreater(image.height, 54)

        boundary_reel = Path(artifacts["boundary_reel"])
        reel_probe = normalize_broll._probe(boundary_reel)
        self.assertEqual(("h264", "yuv420p", False), (
            reel_probe["codec"], reel_probe["pix_fmt"], reel_probe["has_audio"]
        ))
        reel_frames = self.root / "reel-frames"
        reel_frames.mkdir()
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(boundary_reel),
            str(reel_frames / "%03d.png"),
        ], check=True, capture_output=True)
        varied = False
        for path in reel_frames.iterdir():
            with Image.open(path) as image:
                varied |= max(channel[1] - channel[0] for channel in image.convert("RGB").getextrema()) > 40
        self.assertTrue(varied, "boundary reel must include composited B-roll, not only the solid base video")

        summary = Path(artifacts["summary"])
        text = summary.read_text(encoding="utf-8")
        for value in (
            normalized["timeline_id"], normalized["review"]["review_id"],
            normalized["shots"][0]["normalized"]["sha256"], "semantic fit",
            "unwanted logos/text", "jump cuts", "boundaries", "grade match",
        ):
            self.assertIn(value, text)
        for name, path in (("contact_sheet", contact_sheet), ("boundary_reel", boundary_reel), ("report", summary)):
            binding = verification[name]
            self.assertEqual(path.relative_to(self.root).as_posix(), binding["path"])
            self.assertEqual(broll_plan.sha256_file(path), binding["sha256"])

        hashes = {name: broll_plan.sha256_file(path) for name, path in artifacts.items() if name != "stills"}
        hashes["stills"] = [broll_plan.sha256_file(path) for path in stills]
        rerun, rerun_artifacts = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        self.assertEqual(updated, rerun)
        self.assertEqual(hashes, {
            **{name: broll_plan.sha256_file(path) for name, path in rerun_artifacts.items() if name != "stills"},
            "stills": [broll_plan.sha256_file(path) for path in rerun_artifacts["stills"]],
        })
        self.assertEqual("review page", immutable.read_text(encoding="utf-8"))

        projectlib.write_json(self.plan_path, normalized)
        canonical = self.plan_path.read_bytes()
        with mock.patch.object(check_broll.projectlib, "write_json", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        self.assertEqual(canonical, self.plan_path.read_bytes())
        self.assertEqual(hashes, {
            **{name: broll_plan.sha256_file(path) for name, path in artifacts.items() if name != "stills"},
            "stills": [broll_plan.sha256_file(path) for path in stills],
        })
        self.assertEqual("review page", immutable.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "review/.03-b-roll.check.part").exists())
        self.assertFalse((self.root / "review/.03-b-roll.check.backup").exists())

    def _visual_review(self, plan_sha256, **changes):
        review = {
            "review_id": "123e4567-e89b-12d3-a456-426614174000",
            "plan_sha256": plan_sha256,
            "mode": "agent",
            "actor": "Codex",
            "rationale": "The footage fits the spoken claim and all transitions are clean.",
            "timestamp": "2026-07-24T12:00:00Z",
            "checks": {
                "semantic_fit": True,
                "unwanted_logos_or_text": True,
                "jump_cuts": True,
                "entry_exit_boundaries": True,
                "grade_match": True,
            },
        }
        review.update(changes)
        return review

    def test_complete_visual_review_binds_exact_evidence_and_registration_report(self):
        video, _ = self._normalized_for_check()
        verified, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )
        summary_bytes = artifacts["summary"].read_bytes()
        final_video = self.root / "final/final-video.mp4"
        plan_sha256 = broll_plan.canonical_sha256(broll_plan.visual_review_subject(verified))

        source = self.root / "input/source.mp4"
        source.parent.mkdir()
        source.write_bytes(b"source")
        source_stat = source.stat()
        effects = {
            "changes_timeline": False, "changes_geometry": False,
            "changes_video_pixels": False, "changes_audio": False,
            "adds_track": None,
        }
        compiler_project = {
            "schema_version": 1, "project_id": "visual-review-order",
            "source": {"path": "../input/source.mp4", "fingerprint": {
                "size": source_stat.st_size, "modified_ns": source_stat.st_mtime_ns,
                "duration_s": 10.0,
            }},
            "active_sequence": "main",
            "sequences": {"main": {
                "operations": ["cut", "color-grade"], "timeline": "timeline.json",
            }},
            "operations": [
                {"id": "understanding", "skill": "video-understand", "revision": 1,
                 "depends_on": [], "based_on": {}, "status": "verified", "outputs": [],
                 "target": {"sequence": "main", "scope": "evidence"}, "effects": effects},
                {"id": "cut", "skill": "video-cut", "revision": 2,
                 "depends_on": ["understanding"], "based_on": {"understanding": 1},
                 "status": "verified", "outputs": [],
                 "target": {"sequence": "main", "scope": "timeline"}, "effects": effects,
                 "render": {"kind": "output-constraint"}},
                {"id": "color-grade", "skill": "video-color-grade", "revision": 3,
                 "depends_on": ["understanding"], "based_on": {"understanding": 1},
                 "status": "verified", "outputs": [],
                 "target": {"sequence": "main", "scope": "color"}, "effects": effects,
                 "render": {"kind": "output-constraint", "plan": "color-grade/grade-plan.json"}},
            ],
            "render": {"plan": "render/render-plan.json",
                       "output": "../final/final-video.mp4", "status": "verified"},
            "reviews": [],
        }
        registered = broll_plan.register_operation(compiler_project, verified)
        pending = next(item for item in registered["operations"] if item["id"] == "b-roll")
        self.assertEqual(("approved", "pending", "../review/03-b-roll/b-roll-summary.md"), (
            pending["status"], pending["check"]["status"], pending["check"]["report"],
        ))
        before_contributions = [
            item for item in projectlib.build_render_plan(registered, self.root)["contributions"]
            if item.get("operation") == "b-roll"
        ]
        final_video.write_bytes(video.read_bytes())
        registered["render"]["status"] = "verified"
        projectlib.write_json(self.project_path, registered)
        resolved_root = self.root.resolve()
        completed, published = check_broll.complete_visual_review(
            self.plan_path, self.root, self._visual_review(plan_sha256),
            resolved_root / "final/final-video.mp4",
        )

        self.assertEqual(summary_bytes, artifacts["summary"].read_bytes())
        self.assertIn("Manual review status: pending.", summary_bytes.decode("utf-8"))
        self.assertEqual(completed, projectlib.load_json(self.plan_path))
        receipt = projectlib.load_json(published["receipt"])
        self.assertEqual(("completed", "agent", "Codex"), (
            receipt["status"], receipt["mode"], receipt["actor"],
        ))
        self.assertEqual(plan_sha256, receipt["plan_sha256"])
        self.assertEqual(verified["review"]["review_id"], receipt["review_id"])
        self.assertTrue(all(receipt["checks"].values()))
        expected_hashes = {
            artifacts["contact_sheet"].relative_to(self.root).as_posix(): broll_plan.sha256_file(artifacts["contact_sheet"]),
            artifacts["boundary_reel"].relative_to(self.root).as_posix(): broll_plan.sha256_file(artifacts["boundary_reel"]),
            artifacts["summary"].relative_to(self.root).as_posix(): broll_plan.sha256_file(artifacts["summary"]),
            final_video.relative_to(self.root).as_posix(): broll_plan.sha256_file(final_video),
            **{path.relative_to(self.root).as_posix(): broll_plan.sha256_file(path) for path in artifacts["stills"]},
        }
        bound_hashes = {
            item["path"]: item["sha256"]
            for key, value in receipt["artifacts"].items()
            for item in (value if key == "stills" else [value])
        }
        for path, digest in expected_hashes.items():
            self.assertEqual(digest, bound_hashes[path])
        report_text = published["report"].read_text(encoding="utf-8")
        for value in ("Visual review status: completed", "Codex", plan_sha256,
                      expected_hashes[final_video.relative_to(self.root).as_posix()]):
            self.assertIn(value, report_text)
        duplicate = copy.deepcopy(registered)
        duplicate["sequences"]["alternate"] = {"operations": ["b-roll"]}
        with self.assertRaisesRegex(ValueError, "one B-roll sequence reference"):
            broll_plan.register_operation(duplicate, completed)
        failed = copy.deepcopy(registered)
        failed_operation = next(item for item in failed["operations"] if item["id"] == "b-roll")
        failed_operation["status"] = "failed"
        failed_operation["check"] = {"status": "fail", "report": "../review/03-b-roll/b-roll-summary.md"}
        with self.assertRaisesRegex(ValueError, "approved with pending machine summary"):
            broll_plan.register_operation(failed, completed)
        wrong_check = copy.deepcopy(registered)
        next(item for item in wrong_check["operations"] if item["id"] == "b-roll")["check"]["status"] = "pass"
        with self.assertRaisesRegex(ValueError, "approved with pending machine summary"):
            broll_plan.register_operation(wrong_check, completed)
        registration = broll_plan.register_operation(registered, completed)
        operation = next(item for item in registration["operations"] if item["id"] == "b-roll")
        self.assertEqual("../review/03-b-roll/b-roll-visual-review.md", operation["check"]["report"])
        self.assertEqual((pending["revision"], pending["render"]), (operation["revision"], operation["render"]))
        self.assertEqual("verified", registration["render"]["status"])
        after_contributions = [
            item for item in projectlib.build_render_plan(registration, self.root)["contributions"]
            if item.get("operation") == "b-roll"
        ]
        self.assertEqual(before_contributions, after_contributions)
        self.assertEqual(registration, broll_plan.register_operation(registration, completed))

    def test_complete_visual_review_rejects_unchecked_or_stale_evidence(self):
        video, _ = self._normalized_for_check()
        _, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )
        final_video = self.root / "final/final-video.mp4"
        final_video.write_bytes(video.read_bytes())
        original_plan = self.plan_path.read_bytes()
        current_plan = projectlib.load_json(self.plan_path)
        plan_sha256 = broll_plan.canonical_sha256(broll_plan.visual_review_subject(current_plan))
        cases = []
        for value in (False, None, "pass"):
            checks = self._visual_review(plan_sha256)["checks"]
            checks["semantic_fit"] = value
            cases.append((f"check-{value}", self._visual_review(plan_sha256, checks=checks), None, "visual checks"))
        cases.append(("stale-plan", self._visual_review("0" * 64), None, "plan SHA-256"))
        cases.append(("stale-still", self._visual_review(plan_sha256), artifacts["stills"][0], "artifact SHA-256"))
        cases.append(("stale-summary", self._visual_review(plan_sha256), artifacts["summary"], "artifact SHA-256"))

        for name, review, mutation, message in cases:
            with self.subTest(name=name):
                if mutation:
                    original_artifact = mutation.read_bytes()
                    mutation.write_bytes(original_artifact + b"changed")
                with self.assertRaisesRegex(ValueError, message):
                    check_broll.complete_visual_review(
                        self.plan_path, self.root, review, final_video,
                    )
                if mutation:
                    mutation.write_bytes(original_artifact)
                self.assertEqual(original_plan, self.plan_path.read_bytes())
                self.assertFalse((self.root / "work/b-roll/b-roll-visual-review.json").exists())
                self.assertFalse((self.root / "review/03-b-roll/b-roll-visual-review.md").exists())

    def test_complete_visual_review_rolls_back_partial_publication(self):
        video, _ = self._normalized_for_check()
        check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        final_video = self.root / "final/final-video.mp4"
        final_video.write_bytes(video.read_bytes())
        original_plan = self.plan_path.read_bytes()
        current_plan = projectlib.load_json(self.plan_path)
        review = self._visual_review(
            broll_plan.canonical_sha256(broll_plan.visual_review_subject(current_plan))
        )
        real_replace, calls = os.replace, 0

        def fail_plan_replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("plan replace failed")
            return real_replace(source, target)

        with mock.patch.object(check_broll.os, "replace", side_effect=fail_plan_replace):
            with self.assertRaisesRegex(OSError, "plan replace failed"):
                check_broll.complete_visual_review(
                    self.plan_path, self.root, review, final_video,
                )
        self.assertEqual(original_plan, self.plan_path.read_bytes())
        self.assertFalse((self.root / "work/b-roll/b-roll-visual-review.json").exists())
        self.assertFalse((self.root / "review/03-b-roll/b-roll-visual-review.md").exists())
        self.assertFalse(any(path.name.endswith(".part") for path in self.root.rglob("*")))

    def test_checker_accepts_duration_short_by_one_frame_and_extracts_last_still(self):
        video, normalized = self._normalized_for_check()
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=96x54:rate=30000/1001",
            "-frames:v", "29", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.output),
        ], check=True, capture_output=True)
        probe = normalize_broll._probe(self.output)
        difference = 1.0 - probe["duration_s"]
        self.assertGreater(difference, 0)
        self.assertLessEqual(difference, 1001 / 30000 + 1e-6)
        record = normalized["shots"][0]["normalized"]
        record["sha256"], record["probe"] = broll_plan.sha256_file(self.output), probe
        projectlib.write_json(self.plan_path, normalized)

        updated, artifacts = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)

        self.assertEqual("verified", updated["shots"][0]["status"])
        self.assertEqual(3, len(artifacts["stills"]))
        for path in artifacts["stills"]:
            with Image.open(path) as image:
                image.load()
                self.assertEqual((96, 54), image.size)

    def test_checker_zero_selected_is_durable_noop(self):
        video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        review = self.review_for(plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage.")
        plan = broll_plan.apply_review(
            plan, review, mode="agent", actor="agent", rationale="No useful footage."
        )
        projectlib.write_json(self.plan_path, plan)
        review_dir = self.root / "review/03-b-roll"
        (review_dir / "stills").mkdir(parents=True)
        (review_dir / "assets").mkdir()
        (review_dir / "stills/stale.png").write_bytes(b"stale")
        (review_dir / "contact-sheet.jpg").write_bytes(b"stale")
        (review_dir / "boundary-reel.mp4").write_bytes(b"stale")
        (review_dir / "b-roll-summary.md").write_text("stale", encoding="utf-8")
        (review_dir / "index.html").write_text("review page", encoding="utf-8")
        (review_dir / "assets/review.js").write_text("asset", encoding="utf-8")

        updated, artifacts = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)

        self.assertEqual("skipped", updated["shots"][0]["status"])
        self.assertNotIn("verification", updated["shots"][0])
        self.assertEqual([], artifacts["stills"])
        self.assertIsNone(artifacts["contact_sheet"])
        self.assertIsNone(artifacts["boundary_reel"])
        self.assertFalse((review_dir / "stills").exists())
        self.assertFalse((review_dir / "contact-sheet.jpg").exists())
        self.assertFalse((review_dir / "boundary-reel.mp4").exists())
        self.assertEqual("review page", (review_dir / "index.html").read_text(encoding="utf-8"))
        self.assertEqual("asset", (review_dir / "assets/review.js").read_text(encoding="utf-8"))
        summary = artifacts["summary"]
        self.assertIn("No B-roll shots were selected", summary.read_text(encoding="utf-8"))
        self.assertEqual(updated, projectlib.load_json(self.plan_path))
        self.assertEqual([], broll_plan.validate_plan(
            updated, self.timeline, self.transcript,
            project=self.project, project_root=self.root, verify_files=True,
        ))

        canonical, report = self.plan_path.read_bytes(), summary.read_bytes()
        rerun, rerun_artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )
        self.assertEqual(updated, rerun)
        self.assertEqual(canonical, self.plan_path.read_bytes())
        self.assertEqual(report, rerun_artifacts["summary"].read_bytes())
        self.assertEqual([], rerun_artifacts["stills"])
        self.assertIsNone(rerun_artifacts["contact_sheet"])
        self.assertIsNone(rerun_artifacts["boundary_reel"])
        self.assertEqual("review page", (review_dir / "index.html").read_text(encoding="utf-8"))
        self.assertEqual("asset", (review_dir / "assets/review.js").read_text(encoding="utf-8"))

    def test_checker_recovers_crash_after_old_artifact_move_before_validation(self):
        video, _ = self._normalized_for_check()
        review_dir, expected = self._seed_review_outputs()

        crashed = self._crash_verification(video, "first-old")

        self.assertEqual(91, crashed.returncode, crashed.stderr)
        self.assertFalse((review_dir / "stills").exists())
        transaction = self.root / "review/.03-b-roll.check.transaction"
        marker = projectlib.load_json(transaction / "marker.json")
        self.assertEqual(1, marker["schema_version"])
        self.assertEqual(broll_plan.sha256_file(self.plan_path), marker["old_plan_sha256"])
        self.assertNotEqual(marker["old_plan_sha256"], marker["new_plan_sha256"])
        self.assertEqual(
            {"stills": True, "contact-sheet.jpg": True, "boundary-reel.mp4": True,
             "b-roll-summary.md": True},
            {entry["path"]: entry["old_existed"] for entry in marker["entries"]},
        )

        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self._assert_old_review_outputs(review_dir, expected)
        self.assertFalse(transaction.exists())
        self.assertFalse((self.root / "review/.03-b-roll.check.part").exists())

    def test_checker_attempts_all_restores_and_preserves_failed_transaction(self):
        video, _ = self._normalized_for_check()
        review_dir, expected = self._seed_review_outputs()
        crashed = self._crash_verification(video, "all-new")
        self.assertEqual(92, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        old_dir, attempted = transaction / "old", []
        real_restore = check_broll._restore_backup

        def fail_stills_restore(source, target):
            source = Path(source)
            attempted.append(source.relative_to(old_dir).as_posix())
            if source == old_dir / "stills":
                raise RuntimeError("restore blocked")
            return real_restore(source, target)

        with mock.patch.object(check_broll, "_restore_backup", side_effect=fail_stills_restore):
            with self.assertRaisesRegex(ValueError, "publication recovery failed.*restore blocked"):
                check_broll.verify_plan(
                    self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
                )
        self.assertEqual(
            {"stills", "contact-sheet.jpg", "boundary-reel.mp4", "b-roll-summary.md"}, set(attempted)
        )
        self.assertTrue((transaction / "marker.json").is_file())
        self.assertTrue(all((old_dir / relative).exists() for relative in expected))

        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self._assert_old_review_outputs(review_dir, expected)
        self.assertFalse(transaction.exists())
        self.assertFalse((self.root / "review/.03-b-roll.check.part").exists())

    def test_checker_preserves_recovery_when_plan_matches_neither_identity(self):
        video, _ = self._normalized_for_check()
        old_plan = self.plan_path.read_bytes()
        review_dir, expected = self._seed_review_outputs()
        crashed = self._crash_verification(video, "all-new")
        self.assertEqual(92, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        stage = self.root / "review/.03-b-roll.check.part"
        artifact_snapshot = self._tree_snapshot(review_dir)
        transaction_snapshot = self._tree_snapshot(transaction)
        stage_snapshot = self._tree_snapshot(stage)
        self.plan_path.write_bytes(old_plan + b"\n")
        third_identity = self.plan_path.read_bytes()

        with self.assertRaisesRegex(ValueError, "matches neither transaction identity"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(third_identity, self.plan_path.read_bytes())
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertEqual(transaction_snapshot, self._tree_snapshot(transaction))
        self.assertEqual(stage_snapshot, self._tree_snapshot(stage))

        self.plan_path.write_bytes(old_plan)
        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self._assert_old_review_outputs(review_dir, expected)
        self.assertFalse(transaction.exists())
        self.assertFalse((self.root / "review/.03-b-roll.check.part").exists())

    def test_checker_keeps_committed_artifacts_and_cleans_transaction_after_crash(self):
        video, _ = self._normalized_for_check()
        review_dir, _ = self._seed_review_outputs()

        crashed = self._crash_verification(video, "plan")

        self.assertEqual(93, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        self.assertTrue((transaction / "marker.json").is_file())
        committed = projectlib.load_json(self.plan_path)
        self.assertEqual("verified", committed["shots"][0]["status"])
        bindings = committed["shots"][0]["verification"]
        artifact_hashes = {
            binding["path"]: binding["sha256"]
            for binding in (bindings["contact_sheet"], bindings["boundary_reel"], bindings["report"])
        }
        artifact_hashes.update(
            {binding["path"]: binding["sha256"] for binding in bindings["stills"].values()}
        )

        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertFalse(transaction.exists())
        self.assertFalse((self.root / "review/.03-b-roll.check.part").exists())
        for relative, digest in artifact_hashes.items():
            self.assertEqual(digest, broll_plan.sha256_file(self.root / relative))
        self.assertEqual("review page", (review_dir / "index.html").read_text(encoding="utf-8"))
        self.assertEqual("immutable asset", (review_dir / "assets/review.js").read_text(encoding="utf-8"))

    def test_checker_rejects_unreadable_committed_plan_before_mutating_recovery_state(self):
        video, _ = self._normalized_for_check()
        review_dir, _ = self._seed_review_outputs()
        crashed = self._crash_verification(video, "plan")
        self.assertEqual(93, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        stage = self.root / "review/.03-b-roll.check.part"
        committed = self.plan_path.read_bytes()
        artifact_snapshot = self._tree_snapshot(review_dir)
        transaction_snapshot = self._tree_snapshot(transaction)
        stage_snapshot = self._tree_snapshot(stage)
        saved_plan = self.plan_path.with_name("broll-plan.saved.json")
        os.replace(self.plan_path, saved_plan)

        with self.assertRaisesRegex(ValueError, "canonical plan is unreadable"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertEqual(transaction_snapshot, self._tree_snapshot(transaction))
        self.assertEqual(stage_snapshot, self._tree_snapshot(stage))

        os.replace(saved_plan, self.plan_path)
        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(committed, self.plan_path.read_bytes())
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertFalse(transaction.exists())
        self.assertFalse(stage.exists())

    def test_checker_rejects_third_plan_identity_before_mutating_committed_state(self):
        video, _ = self._normalized_for_check()
        review_dir, _ = self._seed_review_outputs()
        crashed = self._crash_verification(video, "plan")
        self.assertEqual(93, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        stage = self.root / "review/.03-b-roll.check.part"
        committed = self.plan_path.read_bytes()
        artifact_snapshot = self._tree_snapshot(review_dir)
        transaction_snapshot = self._tree_snapshot(transaction)
        stage_snapshot = self._tree_snapshot(stage)
        third_plan = projectlib.load_json(self.plan_path)
        third_plan["unexpected_identity"] = True
        projectlib.write_json(self.plan_path, third_plan)
        third_identity = self.plan_path.read_bytes()

        with self.assertRaisesRegex(ValueError, "matches neither transaction identity"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(third_identity, self.plan_path.read_bytes())
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertEqual(transaction_snapshot, self._tree_snapshot(transaction))
        self.assertEqual(stage_snapshot, self._tree_snapshot(stage))

        self.plan_path.write_bytes(committed)
        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertFalse(transaction.exists())
        self.assertFalse(stage.exists())

    def test_checker_rejects_linked_transaction_without_touching_external_target(self):
        video, _ = self._normalized_for_check()
        review_dir, _ = self._seed_review_outputs()
        transaction = self.root / "review/.03-b-roll.check.transaction"
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name)
        (outside / "sentinel.bin").write_bytes(b"external transaction sentinel")
        outside_snapshot = self._tree_snapshot(outside)
        self._directory_link_or_skip(transaction, outside)

        with self.assertRaisesRegex(ValueError, "transaction.*link|transaction.*reparse"):
            check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        self.assertTrue(transaction.is_symlink() or (
            hasattr(transaction, "is_junction") and transaction.is_junction()
        ))
        self.assertEqual(outside_snapshot, self._tree_snapshot(outside))
        self._assert_old_review_outputs(review_dir, {
            "stills/old.txt": b"old stills",
            "contact-sheet.jpg": b"old contact",
            "boundary-reel.mp4": b"old reel",
            "b-roll-summary.md": b"old summary",
        })

    def test_checker_rejects_linked_backup_before_copy_or_cleanup(self):
        video, _ = self._normalized_for_check()
        review_dir, _ = self._seed_review_outputs()
        crashed = self._crash_verification(video, "all-new")
        self.assertEqual(92, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        stage = self.root / "review/.03-b-roll.check.part"
        old_dir = transaction / "old"
        shutil.rmtree(old_dir)
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name)
        (outside / "stills").mkdir(parents=True)
        (outside / "stills/sentinel.bin").write_bytes(b"external stills")
        for name in ("contact-sheet.jpg", "boundary-reel.mp4", "b-roll-summary.md"):
            (outside / name).write_bytes(f"external {name}".encode("ascii"))
        self._directory_link_or_skip(old_dir, outside)
        artifact_snapshot = self._tree_snapshot(review_dir)
        marker = (transaction / "marker.json").read_bytes()
        stage_snapshot = self._tree_snapshot(stage)
        outside_snapshot = self._tree_snapshot(outside)

        with self.assertRaisesRegex(ValueError, "backup.*link|backup.*reparse"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(artifact_snapshot, self._tree_snapshot(review_dir))
        self.assertEqual(marker, (transaction / "marker.json").read_bytes())
        self.assertTrue(old_dir.is_symlink() or (
            hasattr(old_dir, "is_junction") and old_dir.is_junction()
        ))
        self.assertEqual(stage_snapshot, self._tree_snapshot(stage))
        self.assertEqual(outside_snapshot, self._tree_snapshot(outside))

    def test_checker_rolls_back_prepared_equal_hash_rerun_after_first_move(self):
        video, _ = self._normalized_for_check()
        verified, _ = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        canonical, old_artifacts = self.plan_path.read_bytes(), self._verification_artifact_bytes(verified)

        crashed = self._crash_verification(video, "first-old")

        self.assertEqual(91, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        marker = projectlib.load_json(transaction / "marker.json")
        self.assertEqual(marker["old_plan_sha256"], marker["new_plan_sha256"])
        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(canonical, self.plan_path.read_bytes())
        for relative, content in old_artifacts.items():
            self.assertEqual(content, (self.root / relative).read_bytes())
        self.assertEqual("prepared", marker["phase"])
        self.assertFalse(transaction.exists())

    def test_checker_keeps_equal_hash_rerun_after_artifacts_published_phase(self):
        video, _ = self._normalized_for_check()
        verified, _ = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        canonical, expected_artifacts = self.plan_path.read_bytes(), self._verification_artifact_bytes(verified)

        crashed = self._crash_verification(video, "artifacts-published")

        self.assertEqual(94, crashed.returncode, crashed.stderr)
        transaction = self.root / "review/.03-b-roll.check.transaction"
        marker = projectlib.load_json(transaction / "marker.json")
        self.assertEqual(marker["old_plan_sha256"], marker["new_plan_sha256"])
        self.assertEqual("artifacts-published", marker["phase"])
        with self.assertRaisesRegex(ValueError, "review video is missing"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, self.root / "missing.mp4"
            )
        self.assertEqual(canonical, self.plan_path.read_bytes())
        for relative, content in expected_artifacts.items():
            self.assertEqual(content, (self.root / relative).read_bytes())
        self.assertFalse(transaction.exists())

    def test_fresh_review_clears_verified_lifecycle_before_zero_selected_check(self):
        video, _ = self._normalized_for_check()
        verified, _ = check_broll.verify_plan(self.plan_path, self.timeline_path, self.root, video)
        review_dir = self.root / "review/03-b-roll"
        (review_dir / "assets").mkdir(exist_ok=True)
        (review_dir / "index.html").write_text("review page", encoding="utf-8")
        (review_dir / "assets/review.js").write_text("immutable asset", encoding="utf-8")
        review = self.review_for(
            verified, [{"id": "shot", "decision": "skip"}], rationale="No longer useful.",
            review_id="123e4567-e89b-12d3-a456-426614174099",
        )

        skipped = broll_plan.apply_review(
            verified, review, mode="agent", actor="agent", rationale="No longer useful."
        )

        self.assertEqual("skipped", skipped["shots"][0]["status"])
        self.assertIsNone(skipped["shots"][0]["selected"])
        self.assertNotIn("normalized", skipped["shots"][0])
        self.assertNotIn("verification", skipped["shots"][0])
        projectlib.write_json(self.plan_path, skipped)
        checked, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )
        self.assertEqual("skipped", checked["shots"][0]["status"])
        self.assertEqual([], artifacts["stills"])
        self.assertIsNone(artifacts["contact_sheet"])
        self.assertIsNone(artifacts["boundary_reel"])
        self.assertIn("No B-roll shots were selected", artifacts["summary"].read_text(encoding="utf-8"))
        self.assertFalse((review_dir / "stills").exists())
        self.assertFalse((review_dir / "contact-sheet.jpg").exists())
        self.assertFalse((review_dir / "boundary-reel.mp4").exists())
        self.assertEqual("review page", (review_dir / "index.html").read_text(encoding="utf-8"))
        self.assertEqual("immutable asset", (review_dir / "assets/review.js").read_text(encoding="utf-8"))
        self.assertEqual([], broll_plan.validate_plan(
            checked, self.timeline, self.transcript,
            project=self.project, project_root=self.root, verify_files=True,
        ))

    def test_boundary_reel_samples_base_overlay_base_for_each_shot(self):
        video = self._review_video()
        self.base_plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        projectlib.write_json(self.plan_path, self._two_shot_plan())
        normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        )
        _, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )

        pixels = [self._reel_pixel(artifacts["boundary_reel"], time_s)
                  for time_s in (0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)]
        for index in (0, 3, 4, 7):
            self.assertGreater(pixels[index][2], 200)
            self.assertLess(pixels[index][0], 30)
            self.assertLess(pixels[index][1], 30)
        for overlay, base in ((1, 0), (2, 3), (5, 4), (6, 7)):
            self.assertGreater(max(abs(a - b) for a, b in zip(pixels[overlay], pixels[base])), 40)

    def test_boundary_reel_clips_short_shots_at_program_edges(self):
        video = self._review_video()
        self.transcript = {"segments": [{"words": [
            {"word": "opening", "start": 0.05, "end": 0.35},
            {"word": "closing", "start": 9.65, "end": 9.95},
        ]}]}
        projectlib.write_json(self.transcript_path, self.transcript)
        mapped = projectlib.map_transcript_to_timeline(self.transcript, self.timeline)["segments"][0]["words"]
        plan = copy.deepcopy(self.base_plan)
        first = plan["shots"][0]
        first.update({
            "id": "opening", "program_range": {"start_s": 0, "end_s": 0.4},
            "source_ranges": [{"clip_id": "one", "start_s": 0, "end_s": 0.4}],
            "transcript_evidence": {"words": [mapped[0]]},
        })
        second = copy.deepcopy(first)
        second.update({
            "id": "closing", "program_range": {"start_s": 9.6, "end_s": 10},
            "source_ranges": [{"clip_id": "one", "start_s": 9.6, "end_s": 10}],
            "transcript_evidence": {"words": [mapped[1]]},
        })
        second["candidates"][0]["id"] = "asset-2"
        plan["shots"] = [first, second]
        plan["input_hashes"].update({
            "review_video_sha256": broll_plan.sha256_file(video),
            "transcript_sha256": broll_plan.sha256_file(self.transcript_path),
        })
        decisions = [
            {"id": shot["id"], "decision": "select", "candidate_id": shot["candidates"][0]["id"],
             "source_trim": {"start_s": 0.25, "end_s": 0.65}}
            for shot in plan["shots"]
        ]
        projectlib.write_json(
            self.plan_path,
            broll_plan.apply_review(
                plan, self.review_for(plan, decisions), mode="agent", actor="agent",
                rationale="Relevant footage.",
            ),
        )
        normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        )
        _, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video
        )

        samples = {
            name: self._reel_pixel(artifacts["boundary_reel"], time_s)
            for name, time_s in (
                ("start-entry-overlay", 0.2), ("start-entry-base", 0.45),
                ("start-exit-overlay", 0.7), ("start-exit-base", 1.2),
                ("end-entry-base", 1.6), ("end-entry-overlay", 2.1),
                ("end-exit-base", 2.35), ("end-exit-overlay", 2.6),
            )
        }
        for name in ("start-entry-base", "start-exit-base", "end-entry-base", "end-exit-base"):
            self.assertGreater(samples[name][2], 200)
            self.assertLess(samples[name][0], 30)
            self.assertLess(samples[name][1], 30)
        for overlay, base in (
            ("start-entry-overlay", "start-entry-base"),
            ("start-exit-overlay", "start-exit-base"),
            ("end-entry-overlay", "end-entry-base"),
            ("end-exit-overlay", "end-exit-base"),
        ):
            self.assertGreater(
                max(abs(a - b) for a, b in zip(samples[overlay], samples[base])), 40
            )


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cache = Path(self.temp.name) / "work/cache/b-roll/candidates"
        self.cache.mkdir(parents=True)

    def tearDown(self): self.temp.cleanup()

    def test_validate_url_accepts_only_exact_https_hosts(self):
        self.assertEqual("https://videos.pexels.com/a.mp4", pexels.validate_url("https://videos.pexels.com/a.mp4", {"videos.pexels.com"}))
        for value in ("http://videos.pexels.com/a", "https://user@videos.pexels.com/a", "https://videos.pexels.com:444/a", "https://evil.videos.pexels.com/a"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): pexels.validate_url(value, {"videos.pexels.com"})

    def test_search_keeps_best_valid_file_and_never_exposes_key(self):
        payload = {"videos": [{"id": 7, "url": "https://www.pexels.com/video/7/", "user": {"name": "Maker"}, "duration": 4, "width": 1920, "height": 1080, "video_files": [{"id": 1, "link": "https://videos.pexels.com/one.mp4", "width": 640, "height": 360}, {"id": 2, "link": "https://videos.pexels.com/two.mp4", "width": 1920, "height": 1080}]}]}
        class Response:
            def geturl(self): return pexels.PEXELS_API
            def read(self): return json.dumps(payload).encode()
            def __enter__(self): return self
            def __exit__(self, *args): pass
        requests = []
        def opener(request, timeout=None): requests.append(request); return Response()
        records = pexels.search_videos("factory & safety", api_key="secret-key", opener=opener)
        self.assertEqual(1, len(records)); self.assertEqual(2, records[0]["file_id"])
        self.assertIn("factory+%26+safety", requests[0].full_url); self.assertEqual("secret-key", requests[0].get_header("Authorization")); self.assertEqual(pexels.USER_AGENT, requests[0].get_header("User-agent"))
        self.assertNotIn("secret-key", json.dumps(records))

    def test_download_resumes_and_publishes_only_after_probe(self):
        target = self.cache / "clip.mp4"; target.with_suffix(".mp4.part").write_bytes(b"old")
        class Response:
            status = 206
            headers = {"Content-Length": "3", "Content-Range": "bytes 3-5/6"}
            def geturl(self): return "https://videos.pexels.com/clip.mp4"
            def read(self, size):
                value, self.read = b"new", lambda size: b""
                return value
            def __enter__(self): return self
            def __exit__(self, *args): pass
        requests = []
        def opener(request, timeout=None): requests.append(request); return Response()
        candidate = {"id": "7-2", "download_url": "https://videos.pexels.com/clip.mp4", "provider_id": 7, "file_id": 2, "provenance": {"source_type": "pexels", "creator": "Maker", "license": "Pexels License", "retrieval_time": "2026-07-23T00:00:00Z", "source_url": "https://www.pexels.com/video/7/"}}
        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1.0, "width": 2, "height": 2}):
            result = pexels.download_candidate(candidate, target, opener=opener)
        self.assertEqual(b"oldnew", target.read_bytes()); self.assertEqual("bytes=3-", requests[0].get_header("Range")); self.assertEqual(pexels.USER_AGENT, requests[0].get_header("User-agent")); self.assertEqual(target, result["path"])

    def test_download_same_host_redirect_updates_pexels_provenance_immutably(self):
        fixture = _BrollFixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        initial_url = "https://videos.pexels.com/factory.mp4"
        final_url = "https://videos.pexels.com/redirected/factory.mp4"
        candidate = fixture.pexels_candidate()
        candidate["cache_path"] = "cache/b-roll/candidates/redirected.mp4"
        candidate["download_url"] = initial_url
        candidate["provenance"]["download_url"] = initial_url
        candidate["provenance"]["other"] = {"nested": [{"value": "original"}]}
        original = copy.deepcopy(candidate)
        target = fixture.root / "work/cache/b-roll/candidates/redirected.mp4"
        target.parent.mkdir(parents=True)

        class Response:
            status = 200
            headers = {"Content-Length": "3"}
            def geturl(self): return final_url
            def read(self, size): value, self.read = b"new", lambda size: b""; return value
            def __enter__(self): return self
            def __exit__(self, *args): pass

        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 2.0, "width": 1920, "height": 1080}):
            result = pexels.download_candidate(candidate, target, opener=lambda request, timeout=None: Response())
        with self.subTest(field="redirect URLs"):
            self.assertEqual(final_url, result["download_url"])
            self.assertEqual(final_url, result["provenance"]["download_url"])
        with self.subTest(field="caller immutability"):
            self.assertEqual(original, candidate)
            self.assertIsNot(result["provenance"], candidate["provenance"])
            self.assertIsNot(result["provenance"]["dimensions"], candidate["provenance"]["dimensions"])
            self.assertIsNot(result["provenance"]["other"], candidate["provenance"]["other"])
            self.assertIsNot(result["provenance"]["other"]["nested"], candidate["provenance"]["other"]["nested"])
            self.assertIsNot(result["provenance"]["other"]["nested"][0], candidate["provenance"]["other"]["nested"][0])
        plan = copy.deepcopy(fixture.plan)
        plan["shots"][0]["candidates"] = [result]
        with self.subTest(field="plan validation"):
            self.assertEqual([], broll_plan.validate_plan(plan, fixture.timeline, fixture.transcript))
        result["provenance"]["dimensions"]["width"] = 1
        result["provenance"]["other"]["nested"][0]["value"] = "changed"
        self.assertEqual(original, candidate)

        with self.assertRaises(ValueError):
            pexels.download_candidate(
                original,
                fixture.root / "work/cache/b-roll/candidates/cross-host.mp4",
                opener=lambda request, timeout=None: type("CrossHostResponse", (), {
                    "status": 200,
                    "headers": {"Content-Length": "3"},
                    "geturl": lambda self: "https://evil.test/factory.mp4",
                    "read": lambda self, size: b"new",
                    "__enter__": lambda self: self,
                    "__exit__": lambda self, *args: None,
                })(),
            )

    def test_import_local_requires_cache_containment_and_leaves_source_unchanged(self):
        source = Path(self.temp.name) / "source.mp4"; source.write_bytes(b"source")
        provenance = {"source_type": "local", "creator": "me", "license": "owned", "retrieval_time": "2026-07-23T00:00:00Z", "original_path": str(source)}
        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1.0, "width": 2, "height": 2}):
            result = pexels.import_local(source, self.cache / "copy.mp4", provenance)
        self.assertEqual(b"source", source.read_bytes()); self.assertEqual(b"source", result["path"].read_bytes())
        with self.assertRaises(ValueError): pexels.import_local(source, Path(self.temp.name) / "escape.mp4", provenance)

    def test_permanent_http_errors_clean_part_without_retry(self):
        for status in (401, 501):
            with self.subTest(status=status):
                target = self.cache / f"clip-{status}.mp4"; part = target.with_name(f"clip-{status}.mp4.part"); part.write_bytes(b"resume")
                calls = []
                def opener(request, timeout=None):
                    calls.append(request); raise HTTPError(request.full_url, status, "no", {}, None)
                with self.assertRaises(HTTPError): pexels.download_candidate({"download_url": "https://videos.pexels.com/clip.mp4"}, target, opener=opener, retries=3)
                self.assertEqual(1, len(calls)); self.assertFalse(part.exists())

    def test_exhausted_transient_error_preserves_part(self):
        target = self.cache / "clip.mp4"; part = target.with_name("clip.mp4.part"); part.write_bytes(b"resume")
        calls = []
        def opener(request, timeout=None):
            calls.append(request); raise HTTPError(request.full_url, 503, "later", {}, None)
        with self.assertRaises(HTTPError): pexels.download_candidate({"download_url": "https://videos.pexels.com/clip.mp4"}, target, opener=opener, retries=2)
        self.assertEqual(2, len(calls)); self.assertTrue(part.exists())

    def test_download_hashes_part_before_atomic_publish(self):
        target = self.cache / "hash.mp4"; events = []
        class Response:
            status = 200; headers = {"Content-Length": "3"}
            def geturl(self): return "https://videos.pexels.com/hash.mp4"
            def read(self, size): value, self.read = b"ok!", lambda size: b""; return value
            def __enter__(self): return self
            def __exit__(self, *args): pass
        real_hash = pexels._sha256
        real_replace = os.replace
        def digest(path): events.append(("hash", Path(path).name)); return real_hash(path)
        def publish(source, destination): events.append(("replace", Path(source).name)); real_replace(source, destination)
        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1, "width": 1, "height": 1}), mock.patch.object(pexels, "_sha256", side_effect=digest), mock.patch.object(pexels.os, "replace", side_effect=publish):
            pexels.download_candidate({"download_url": "https://videos.pexels.com/hash.mp4"}, target, opener=lambda request, timeout=None: Response())
        self.assertLess(events.index(("hash", "hash.mp4.part")), events.index(("replace", "hash.mp4.part")))

    def test_hash_failure_cleans_part_without_final(self):
        target = self.cache / "broken.mp4"
        class Response:
            status = 200; headers = {"Content-Length": "3"}
            def geturl(self): return "https://videos.pexels.com/broken.mp4"
            def read(self, size): value, self.read = b"bad", lambda size: b""; return value
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1, "width": 1, "height": 1}), mock.patch.object(pexels, "_sha256", side_effect=OSError("hash failed")):
            with self.assertRaises(OSError): pexels.download_candidate({"download_url": "https://videos.pexels.com/broken.mp4"}, target, opener=lambda request, timeout=None: Response())
        self.assertFalse(target.exists()); self.assertFalse(target.with_name("broken.mp4.part").exists())

    def test_search_rejects_redirected_api_and_invalid_page_and_honors_orientation(self):
        payload = {"videos": [{"id": 1, "url": "https://www.pexels.com/video/1/", "duration": 2, "width": 720, "height": 1280, "video_files": [{"id": 2, "link": "https://videos.pexels.com/one.mp4", "width": 720, "height": 1280}]}]}
        class Response:
            def __init__(self, final): self.final = final
            def geturl(self): return self.final
            def read(self): return json.dumps(payload).encode()
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with self.assertRaises(ValueError): pexels.search_videos("portrait", orientation="portrait", api_key="k", opener=lambda request, timeout=None: Response("https://evil.test/"))
        self.assertEqual(1, len(pexels.search_videos("portrait", orientation="portrait", api_key="k", opener=lambda request, timeout=None: Response(pexels.PEXELS_API))))
        payload["videos"][0]["url"] = "https://evil.pexels.com/video/1/"
        self.assertEqual([], pexels.search_videos("portrait", orientation="portrait", api_key="k", opener=lambda request, timeout=None: Response(pexels.PEXELS_API)))

    def test_cli_search_does_not_accept_api_key(self):
        for argv in (("search", "factory", "--api-key", "secret"), ("search", "factory", "--api-key=secret")):
            with self.subTest(argv=argv):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit): pexels.main(list(argv))
                self.assertEqual("Pexels API key must be set in PEXELS_API_KEY\n", stderr.getvalue())
                self.assertNotIn("secret", stderr.getvalue())

    def test_redirect_handler_rejects_cross_host_before_parent_and_allows_exact_host(self):
        request = Request("https://api.pexels.com/videos/search", headers={"Authorization": "secret"})
        handler = pexels._RedirectLimit({"api.pexels.com"})
        with mock.patch.object(pexels.HTTPRedirectHandler, "redirect_request", side_effect=AssertionError("parent followed")):
            for url in ("https://evil.test/", "https://videos.pexels.com/file.mp4"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    handler.redirect_request(request, None, 302, "found", {}, url)
        redirected = handler.redirect_request(request, None, 302, "found", {}, "https://api.pexels.com/next")
        self.assertEqual("https://api.pexels.com/next", redirected.full_url)

    def test_download_redirect_handler_permits_only_video_host(self):
        request = Request("https://videos.pexels.com/file.mp4")
        handler = pexels._RedirectLimit(pexels.VIDEO_HOSTS)
        with self.assertRaises(ValueError): handler.redirect_request(request, None, 302, "found", {}, "https://api.pexels.com/videos/search")
        self.assertEqual("https://videos.pexels.com/next", handler.redirect_request(request, None, 302, "found", {}, "https://videos.pexels.com/next").full_url)

    def test_download_rejects_truncated_200_and_incomplete_or_mismatched_206(self):
        cases = [
            ("truncated.mp4", b"", 200, {"Content-Length": "4"}, b"bad"),
            ("span.mp4", b"old", 206, {"Content-Length": "4", "Content-Range": "bytes 3-5/6"}, b"new"),
            ("range.mp4", b"old", 206, {"Content-Length": "2", "Content-Range": "bytes 3-4/6"}, b"ne"),
        ]
        for name, initial, status, headers, body in cases:
            with self.subTest(name=name):
                target = self.cache / name; part = target.with_name(name + ".part")
                if initial: part.write_bytes(initial)
                class Response:
                    def __init__(self): self.status, self.headers, self.body = status, headers, body
                    def geturl(self): return "https://videos.pexels.com/file.mp4"
                    def read(self, size): value, self.body = self.body, b""; return value
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1, "width": 1, "height": 1}):
                    with self.assertRaises(ValueError): pexels.download_candidate({"download_url": "https://videos.pexels.com/file.mp4"}, target, opener=lambda request, timeout=None: Response())
                self.assertFalse(part.exists()); self.assertFalse(target.exists())

    def test_import_local_enforces_limit_and_binds_original_path(self):
        source = Path(self.temp.name) / "source.mp4"; source.write_bytes(b"source")
        provenance = {"source_type": "local", "creator": "me", "license": "owned", "retrieval_time": "2026-07-23T00:00:00Z", "original_path": "misleading.mp4"}
        small = self.cache / "small.mp4"
        with self.assertRaises(ValueError): pexels.import_local(source, small, provenance, max_bytes=3)
        self.assertFalse(small.exists()); self.assertFalse(small.with_name("small.mp4.part").exists())
        with mock.patch.object(pexels, "probe_media", return_value={"duration_s": 1, "width": 1, "height": 1}):
            record = pexels.import_local(source, self.cache / "copy.mp4", provenance)
        self.assertEqual(source.resolve().as_posix(), record["provenance"]["original_path"])
        self.assertEqual("misleading.mp4", provenance["original_path"])

    def test_search_skips_malformed_provider_and_file_ids(self):
        videos = [
            {"id": [], "url": "https://www.pexels.com/video/bad/", "duration": 1, "width": 2, "height": 1, "video_files": []},
            {"id": True, "url": "https://www.pexels.com/video/bad/", "duration": 1, "width": 2, "height": 1, "video_files": []},
            {"id": 4, "url": "https://www.pexels.com/video/4/", "duration": 1, "width": 2, "height": 1, "video_files": [{"id": {}, "link": "https://videos.pexels.com/bad.mp4", "width": 2, "height": 1}, {"id": 5, "link": "https://videos.pexels.com/good.mp4", "width": 2, "height": 1}]},
        ]
        class Response:
            def geturl(self): return pexels.PEXELS_API
            def read(self): return json.dumps({"videos": videos}).encode()
            def __enter__(self): return self
            def __exit__(self, *args): pass
        records = pexels.search_videos("valid", api_key="k", opener=lambda request, timeout=None: Response())
        self.assertEqual([(4, 5)], [(item["provider_id"], item["file_id"]) for item in records])


if __name__ == "__main__": unittest.main()
