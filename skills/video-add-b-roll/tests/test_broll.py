"""Focused B-roll plan and review contract tests."""

import copy
import base64
import contextlib
import io
import json
import os
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


class _BrollFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "work/cache/b-roll").mkdir(parents=True)
        (self.root / "work/understand").mkdir()
        self.timeline = {"schema_version": 1, "timeline_id": "main", "source_duration_s": 10.0, "program_duration_s": 10.0, "fps": {"num": 30, "den": 1}, "clips": [{"id": "one", "source_range": {"start_s": 0, "end_s": 10}, "program_range": {"start_s": 0, "end_s": 10}, "speed": 1.0, "decision_ref": "keep"}]}
        self.transcript = {"segments": [{"words": [{"word": "factory", "start": 1.0, "end": 2.0}]}]}
        self.timeline_path = self.root / "work/timeline.json"
        self.transcript_path = self.root / "work/understand/transcript.json"
        projectlib.write_json(self.timeline_path, self.timeline)
        projectlib.write_json(self.transcript_path, self.transcript)
        asset = self.root / "work/cache/b-roll/factory.mp4"
        asset.write_bytes(b"asset")
        mapped = projectlib.map_transcript_to_timeline(self.transcript, self.timeline)["segments"][0]["words"][0]
        candidate = {"id": "asset", "media_type": "video", "cache_path": "cache/b-roll/factory.mp4", "sha256": broll_plan.sha256_file(asset), "provenance": {"source_type": "local", "creator": "me", "license": "owned", "retrieval_time": "2026-07-23T00:00:00Z", "original_path": "input/factory.mp4"}}
        self.plan = {"schema_version": 1, "timeline_id": "main", "timebase": "program", "program_duration_s": 10.0, "dependencies": ["understanding", "cut", "color-grade"], "based_on": {"understanding": 1, "cut": 2, "color-grade": 3}, "input_hashes": {"transcript_sha256": broll_plan.sha256_file(self.transcript_path), "timeline_sha256": broll_plan.sha256_file(self.timeline_path), "review_video_sha256": "b" * 64}, "brief": {"density": "selective"}, "decision": None, "review": None, "shots": [{"id": "shot", "program_range": {"start_s": 1.0, "end_s": 2.0}, "source_ranges": [{"clip_id": "one", "start_s": 1.0, "end_s": 2.0}], "transcript_evidence": {"words": [mapped]}, "editorial_reason": "Supports the statement.", "visual_intent": "Factory work.", "queries": ["factory assembly", "manufacturing line"], "candidates": [candidate], "selected": None, "status": "candidates_ready"}]}
        self.project = {"active_sequence": "main", "sequences": {"main": {"operations": ["cut", "color-grade"]}}, "operations": [{"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2}, {"id": "color-grade", "revision": 3}]}

    def tearDown(self): self.temp.cleanup()

    def review(self, **extra):
        return self.review_for(self.plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}], **extra)

    def review_for(self, plan, shots, rationale="Relevant footage.", timestamp="2026-07-23T12:00:00Z", **extra):
        return {"review_id": "review-1", "plan_sha256": broll_plan.canonical_sha256(broll_plan.review_subject(plan)), "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "review_video_sha256": plan["input_hashes"]["review_video_sha256"], "rationale": rationale, "timestamp": timestamp, "shots": shots, **extra}


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
        skipped = broll_plan.apply_review(self.plan, self.review_for(self.plan, [{"id": "shot", "decision": "skip"}], rationale="No useful footage.", review_id="skip"), mode="agent", actor="agent", rationale="No useful footage.")
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

    def test_review_decision_manifest_rejects_reorder_omit_duplicate_and_malformed(self):
        plan = copy.deepcopy(self.plan)
        second = copy.deepcopy(plan["shots"][0])
        second.update({"id": "second", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": []}})
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
        pre_skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": []}, "candidates": [], "selected": None, "status": "skipped"})
        plan["shots"].append(pre_skipped)
        review = self.review_for(plan, [{"id": "shot", "decision": "skip"}, {"id": "already-skipped", "decision": "skip"}], rationale="Neither shot helps.")
        approved = broll_plan.apply_review(plan, review, mode="agent", actor="agent", rationale="Neither shot helps.")
        self.assertEqual(["shot"], approved["review"]["decision_skipped_shot_ids"])
        self.assertEqual([], broll_plan.validate_plan(approved, self.timeline, self.transcript))

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

    def test_approved_plan_with_nonlist_candidates_returns_schema_and_receipt_errors(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        for candidates in (None, 3):
            malformed = copy.deepcopy(approved)
            malformed["shots"][0]["candidates"] = candidates
            with self.subTest(candidates=candidates):
                errors = broll_plan.validate_plan(malformed, self.timeline, self.transcript)
                self.assertIn("shot candidates must be a list", errors)
                self.assertIn("review decisions do not match current plan", errors)

    def test_validate_plan_catches_stale_revisions_and_real_input_hashes(self):
        self.assertEqual([], broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=self.project, project_root=self.root))
        project = copy.deepcopy(self.project); project["operations"][1]["revision"] = 3
        self.assertIn("based_on cut revision is stale: expected 2, current 3", broll_plan.validate_plan(self.plan, self.timeline, self.transcript, project=project, project_root=self.root))
        plan = copy.deepcopy(self.plan); plan["input_hashes"]["transcript_sha256"] = "0" * 64
        self.assertIn("transcript SHA-256 is stale", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root))
        plan["input_hashes"]["timeline_sha256"] = "0" * 64
        self.assertIn("timeline SHA-256 is stale", broll_plan.validate_plan(plan, self.timeline, self.transcript, project=self.project, project_root=self.root))

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

    def test_persisted_selected_media_requires_its_media_contract(self):
        plan = copy.deepcopy(self.plan); plan["shots"][0].update({"status": "selected", "selected": {"candidate_id": "asset", "source_trim": {"start_s": 1, "end_s": 1}}})
        self.assertIn("shot selected video requires a valid source_trim", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["candidates"][0]["media_type"] = "image"; plan["shots"][0].update({"status": "verified", "selected": {"candidate_id": "asset", "ken_burns": {}}})
        self.assertIn("shot verified image requires a non-empty ken_burns", broll_plan.validate_plan(plan, self.timeline, self.transcript))

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
        normalized = copy.deepcopy(selected); normalized["shots"][0].update({"status": "normalized", "normalized": {"path": "asset.mp4"}})
        verified = copy.deepcopy(normalized); verified["shots"][0].update({"status": "verified", "verification": {"status": "pass"}})
        self.assertEqual(broll_plan.review_subject(selected), broll_plan.review_subject(normalized))
        self.assertEqual(broll_plan.review_subject(selected), broll_plan.review_subject(verified))
        self.assertEqual([], broll_plan.validate_plan(verified, self.timeline, self.transcript))

    def test_shots_must_be_chronological_even_without_overlap(self):
        later = copy.deepcopy(self.plan["shots"][0]); later.update({"id": "later", "program_range": {"start_s": 3, "end_s": 4}, "source_ranges": [{"start_s": 3, "end_s": 4}], "candidates": []})
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
            shot["selected"] = None
            shot["status"] = "candidates_ready"
            plan["shots"].append(shot)
        decisions = [{"id": shot["id"], "decision": "skip"} if skip else {"id": shot["id"], "decision": "select", "candidate_id": shot["candidates"][0]["id"], "source_trim": {"start_s": 0, "end_s": 1}} for shot in plan["shots"]]
        plan = broll_plan.apply_review(plan, self.review_for(plan, decisions, review_id="registered"), mode="agent", actor="agent", rationale="Relevant footage.")
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
        self.assertEqual(("video-add-b-roll", 1, "verified"), (operation["skill"], operation["revision"], operation["status"]))
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
        project["operations"].extend([{"id": "b-roll", "revision": 7}, {"id": "b-roll", "revision": 6}])
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


class BrollReviewPageTests(_BrollFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.review_dir = self.root / "review/03-b-roll"
        self.video = self.root / "final/current.mp4"
        self.video.parent.mkdir(parents=True)
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
        skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": []}, "candidates": [], "selected": None, "status": "skipped"})
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
        self.assertIn("factory+%26+safety", requests[0].full_url); self.assertEqual("secret-key", requests[0].get_header("Authorization"))
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
        self.assertEqual(b"oldnew", target.read_bytes()); self.assertEqual("bytes=3-", requests[0].get_header("Range")); self.assertEqual(target, result["path"])

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
