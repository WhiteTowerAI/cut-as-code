"""Focused B-roll plan and review contract tests."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT.parent / "video-understand" / "scripts")]
import broll_plan
import projectlib


class BrollPlanTests(unittest.TestCase):
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
        self.plan = {"schema_version": 1, "timeline_id": "main", "timebase": "program", "program_duration_s": 10.0, "dependencies": ["understanding", "cut", "color-grade"], "based_on": {"understanding": 1, "cut": 2, "color-grade": 3}, "input_hashes": {"transcript_sha256": broll_plan.sha256_file(self.transcript_path), "timeline_sha256": broll_plan.sha256_file(self.timeline_path)}, "brief": {"density": "selective"}, "decision": None, "review": None, "shots": [{"id": "shot", "program_range": {"start_s": 1.0, "end_s": 2.0}, "source_ranges": [{"clip_id": "one", "start_s": 1.0, "end_s": 2.0}], "transcript_evidence": {"words": [mapped]}, "editorial_reason": "Supports the statement.", "visual_intent": "Factory work.", "queries": ["factory assembly", "manufacturing line"], "candidates": [candidate], "selected": None, "status": "candidates_ready"}]}
        self.project = {"active_sequence": "main", "sequences": {"main": {"operations": ["cut", "color-grade"]}}, "operations": [{"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2}, {"id": "color-grade", "revision": 3}]}

    def tearDown(self): self.temp.cleanup()

    def review(self, **extra):
        return {"review_id": "review-1", "shots": [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}], **extra}

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
            broll_plan.apply_review(self.plan, self.review(), mode="human", actor="person", rationale="ok")
        with self.assertRaisesRegex(ValueError, "rationale"):
            broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale=" ")

    def test_apply_review_selects_or_skips_every_shot_and_binds_receipt(self):
        approved = broll_plan.apply_review(self.plan, self.review(), mode="agent", actor="agent", rationale="Relevant footage.")
        self.assertEqual("selected", approved["shots"][0]["status"])
        self.assertEqual(broll_plan.canonical_sha256(broll_plan.review_subject(approved)), approved["review"]["plan_sha256"])
        self.assertEqual(broll_plan.canonical_sha256(broll_plan.candidate_manifest(approved)), approved["review"]["candidate_manifest_sha256"])
        self.assertEqual([approved["shots"][0]["candidates"][0]["sha256"]], approved["review"]["selected_asset_sha256"])
        skipped = broll_plan.apply_review(self.plan, {"review_id": "skip", "shots": [{"id": "shot", "decision": "skip"}]}, mode="agent", actor="agent", rationale="No useful footage.")
        self.assertEqual(("skipped", None), (skipped["shots"][0]["status"], skipped["shots"][0]["selected"]))

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
                with self.assertRaisesRegex(ValueError, message): broll_plan.apply_review(plan, self.review(), mode="agent", actor="agent", rationale="reason")

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
                with self.assertRaisesRegex(ValueError, message): broll_plan.apply_review(plan, self.review(), mode="agent", actor="agent", rationale="reason")

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


if __name__ == "__main__": unittest.main()
