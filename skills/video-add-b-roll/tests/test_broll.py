"""Focused B-roll plan and review contract tests."""

import copy
import base64
import contextlib
import io
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT.parent / "video-understand" / "scripts")]
import broll_plan
import candidate_analysis
import projectlib
import pexels
import build_review_page
import normalize_broll
import check_broll
import speaker_inset


def _final_size_clearance_fields(plan, analysis, agent_input, preview,
                                 shot_id, subshot_id):
    budget = speaker_inset.build_pixel_budget(
        plan, analysis, agent_input, preview, shot_id, subshot_id,
    )
    checks = [
        {
            "role": item["role"],
            "program_time_s": item["program_time_s"],
            "preview_sha256": plan["speaker_inset"]["preview"]["sha256"],
            "observation": "The complete speaker silhouette remains readable at final size.",
        }
        for item in budget["checkpoints"]
    ]
    checks.append({
        "role": "motion_risk",
        "status": "not_applicable",
        "preview_sha256": plan["speaker_inset"]["preview"]["sha256"],
        "reason": "No additional motion-risk frame exists in this stable subshot.",
    })
    return {
        "legibility_rationale": "The speaker remains immediately recognizable at final size.",
        "pixel_budget": budget,
        "legibility_checks": checks,
    }


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
        self.plan = {"schema_version": 1, "timeline_id": "main", "timebase": "program", "program_duration_s": 10.0, "dependencies": ["understanding", "cut", "color-grade"], "based_on": {"understanding": 1, "cut": 2, "color-grade": 3}, "input_hashes": {"transcript_sha256": broll_plan.sha256_file(self.transcript_path), "timeline_sha256": broll_plan.sha256_file(self.timeline_path), "grade_plan_sha256": broll_plan.sha256_file(self.grade_plan_path), "selected_lut_sha256": broll_plan.sha256_file(self.selected_lut_path), "review_video_sha256": "b" * 64}, "brief": {"density": "dynamic-social"}, "decision": None, "review": None, "shots": [{"id": "shot", "program_range": {"start_s": 1.0, "end_s": 2.0}, "source_ranges": [{"clip_id": "one", "start_s": 1.0, "end_s": 2.0}], "transcript_evidence": {"words": [self.mapped_words[0]]}, "editorial_reason": "Supports the statement.", "visual_intent": "Factory work.", "queries": ["factory assembly", "manufacturing line"], "candidates": [candidate], "selected": None, "status": "candidates_ready"}]}
        self.project = {"active_sequence": "main", "sequences": {"main": {"operations": ["cut", "color-grade"]}}, "operations": [{"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2}, {"id": "color-grade", "revision": 3, "render": {"plan": "color-grade/grade-plan.json"}}]}
        self.project_path = self.root / "work/project.json"
        projectlib.write_json(self.project_path, self.project)

    def tearDown(self): self.temp.cleanup()

    def review(self, **extra):
        return self.review_for(self.plan, [{"id": "shot", "decision": "select", "candidate_id": "asset", "source_trim": {"start_s": 0, "end_s": 1}}], **extra)

    def review_for(self, plan, shots, rationale="Relevant footage.", timestamp="2026-07-23T12:00:00Z", **extra):
        return {"review_id": "123e4567-e89b-12d3-a456-426614174000", "plan_sha256": broll_plan.canonical_sha256(broll_plan.review_subject(plan)), "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "review_video_sha256": plan["input_hashes"]["review_video_sha256"], "rationale": rationale, "timestamp": timestamp, "shots": shots, **extra}

    def record_presentation(self, plan, mode):
        decision = {
            "decision_id": (
                "123e4567-e89b-12d3-a456-426614174002"
                if mode == "speaker-inset"
                else "123e4567-e89b-12d3-a456-426614174001"
            ),
            "mode": "human",
            "actor": "Actual user",
            "timestamp": "2026-08-06T12:00:00Z",
            "explicit_user_action": True,
            "rationale_source": "agent_chat_explicit_action",
            "user_response": f"Use the {mode} presentation route.",
            "presentation_mode": mode,
            "agent_recommendation": {
                "presentation_mode": mode,
                "rationale": f"The selected media supports the {mode} presentation route.",
            },
            "plan_sha256": broll_plan.canonical_sha256(
                broll_plan.presentation_subject(plan)
            ),
            "candidate_manifest_sha256": broll_plan.canonical_sha256(
                broll_plan.candidate_manifest(plan)
            ),
            "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
        }
        return broll_plan.record_chat_presentation_decision(
            plan, decision, project_root=self.root,
        )

    def publish_review_page(self, review_id="123e4567-e89b-12d3-a456-426614174000", *, plan=None):
        plan = self.plan if plan is None else plan
        page = self.root / "review/03-b-roll" / f"b-roll-review-{review_id}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "review_id": review_id,
            "review_mode": (
                "selection"
                if plan.get("presentation", {}).get("mode") == "speaker-inset"
                else "standard"
            ),
            "plan_sha256": broll_plan.canonical_sha256(
                broll_plan.review_subject(plan)
            ),
            "candidate_manifest_sha256": broll_plan.canonical_sha256(
                broll_plan.candidate_manifest(plan)
            ),
            "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
            "timeline": {
                "fps": copy.deepcopy(self.timeline["fps"]),
                "program_duration_s": self.timeline["program_duration_s"],
                "clips": copy.deepcopy(self.timeline["clips"]),
            },
        }
        encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        page.write_text(f"<script>const data=JSON.parse(atob('{encoded}'));</script>", encoding="utf-8")
        return page

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

    def test_dynamic_social_density_is_required_without_coverage_validation(self):
        self.assertEqual([], broll_plan.validate_plan(
            self.plan, self.timeline, self.transcript,
        ))
        selective = copy.deepcopy(self.plan)
        selective["brief"]["density"] = "selective"
        self.assertIn("brief density must be dynamic-social", broll_plan.validate_plan(
            selective, self.timeline, self.transcript,
        ))
        for start_s, end_s, status in (
            (1.0, 2.0, "below_target"),
            (0.0, 8.0, "above_target"),
        ):
            with self.subTest(coverage_status=status):
                plan = copy.deepcopy(self.plan)
                plan["shots"][0].update({
                    "program_range": {"start_s": start_s, "end_s": end_s},
                    "source_ranges": [{"clip_id": "one", "start_s": start_s, "end_s": end_s}],
                    "candidates": [],
                    "selected": None,
                    "status": "planned",
                })
                summary = broll_plan.coverage_summary(plan, planned=plan["shots"])
                self.assertEqual(status, summary["planned"]["status"])
                self.assertEqual([], broll_plan.validate_plan(
                    plan, self.timeline, self.transcript,
                ))

    def test_coverage_summary_merges_ranges_and_reports_stage_status(self):
        summary = broll_plan.coverage_summary(
            self.plan,
            [
                {"program_range": {"start_s": 0.0, "end_s": 4.0}},
                {"program_range": {"start_s": 3.0, "end_s": 5.0}},
            ],
            [
                {"start_s": 0.0, "end_s": 2.0},
                {"start_s": 3.0, "end_s": 4.0},
            ],
            [{"program_range": {"start_s": 0.0, "end_s": 8.0}}],
        )

        self.assertEqual("dynamic-social", summary["profile"])
        self.assertEqual(0.40, summary["target_min_ratio"])
        self.assertEqual(0.70, summary["target_max_ratio"])
        self.assertEqual({"duration_s": 5.0, "ratio": 0.5, "status": "within_target"}, summary["planned"])
        self.assertEqual({"duration_s": 3.0, "ratio": 0.3, "status": "below_target"}, summary["shortlisted"])
        self.assertEqual({"duration_s": 8.0, "ratio": 0.8, "status": "above_target"}, summary["selected"])

    def test_coverage_summary_empty_stage_and_zero_duration_are_below(self):
        empty = broll_plan.coverage_summary(self.plan, planned=[], shortlisted=[], selected=[])
        self.assertEqual(0.0, empty["planned"]["duration_s"])
        self.assertEqual(0.0, empty["planned"]["ratio"])
        self.assertEqual("below_target", empty["planned"]["status"])

        zero_duration = copy.deepcopy(self.plan)
        zero_duration["program_duration_s"] = 0.0
        zero = broll_plan.coverage_summary(
            zero_duration,
            planned=[{"start_s": 0.0, "end_s": 1.0}],
            shortlisted=[{"start_s": 0.0, "end_s": 1.0}],
            selected=[{"start_s": 0.0, "end_s": 1.0}],
        )
        for stage in ("planned", "shortlisted", "selected"):
            with self.subTest(stage=stage):
                self.assertEqual(0.0, zero[stage]["duration_s"])
                self.assertEqual(0.0, zero[stage]["ratio"])
                self.assertEqual("below_target", zero[stage]["status"])

    @staticmethod
    def _speaker_style():
        return {
            "enabled": True,
            "shape": "rounded-rectangle",
            "width_ratio": 0.39,
            "aspect_ratio": 0.80,
            "border": {"width_px": 3, "color": "#9E9E9E"},
            "corner_radius_ratio": 0.10,
            "margin_ratio": 0.04,
            "reserved_bottom_ratio": 0.20,
        }

    def test_speaker_inset_style_is_optional_and_enabled_style_is_strict(self):
        self.assertEqual([], broll_plan.validate_plan(
            self.plan, self.timeline, self.transcript,
        ))
        valid = copy.deepcopy(self.plan)
        valid["speaker_inset_style"] = self._speaker_style()
        self.assertEqual([], broll_plan.validate_plan(
            valid, self.timeline, self.transcript,
        ))

        invalid_values = (
            ({**self._speaker_style(), "shape": "circle"}, "rounded-rectangle"),
            ({**self._speaker_style(), "width_ratio": 0}, "width_ratio"),
            ({**self._speaker_style(), "aspect_ratio": True}, "aspect_ratio"),
            ({**self._speaker_style(), "border": {"width_px": -1, "color": "white"}}, "border"),
            ({**self._speaker_style(), "size_candidates": [0.24, 0.30]}, "size_candidates"),
            ({**self._speaker_style(), "layout_preset": "corner-pip"}, "layout_preset"),
            ({**self._speaker_style(), "allowed_anchors": ["top-left"]}, "allowed_anchors"),
        )
        for style, message in invalid_values:
            plan = copy.deepcopy(self.plan)
            plan["speaker_inset_style"] = style
            with self.subTest(message=message):
                self.assertTrue(any(
                    message in error for error in broll_plan.validate_plan(
                        plan, self.timeline, self.transcript,
                    )
                ))

    def test_chat_presentation_decision_binds_user_response_and_recommendation(self):
        decision = {
            "decision_id": "123e4567-e89b-12d3-a456-426614174001",
            "mode": "human",
            "actor": "Actual user",
            "timestamp": "2026-08-06T12:00:00Z",
            "explicit_user_action": True,
            "rationale_source": "agent_chat_explicit_action",
            "user_response": "Use ordinary full-screen B-roll for this video.",
            "presentation_mode": "ordinary",
            "agent_recommendation": {
                "presentation_mode": "speaker-inset",
                "rationale": "The speaker should remain visible for continuity.",
            },
            "plan_sha256": broll_plan.canonical_sha256(
                broll_plan.presentation_subject(self.plan)
            ),
            "candidate_manifest_sha256": broll_plan.canonical_sha256(
                broll_plan.candidate_manifest(self.plan)
            ),
            "review_video_sha256": self.plan["input_hashes"]["review_video_sha256"],
        }

        updated = broll_plan.record_chat_presentation_decision(
            self.plan, decision, project_root=self.root,
        )

        receipt_path = self.root / "work/b-roll/presentation-decision.json"
        self.assertTrue(receipt_path.is_file())
        self.assertEqual("ordinary", updated["presentation"]["mode"])
        self.assertEqual(broll_plan.sha256_file(receipt_path), updated["presentation"]["sha256"])
        receipt = projectlib.load_json(receipt_path)
        self.assertEqual(decision["user_response"], receipt["user_response"])
        self.assertEqual(decision["agent_recommendation"], receipt["agent_recommendation"])
        self.assertEqual([], broll_plan.presentation_errors(
            updated, project_root=self.root, required=True,
        ))

    def test_chat_speaker_presentation_decision_enables_default_inset_style(self):
        decision = {
            "decision_id": "123e4567-e89b-12d3-a456-426614174002",
            "mode": "human",
            "actor": "Actual user",
            "timestamp": "2026-08-06T12:00:00Z",
            "explicit_user_action": True,
            "rationale_source": "agent_chat_explicit_action",
            "user_response": "Keep the speaker and show me the composite preview.",
            "presentation_mode": "speaker-inset",
            "agent_recommendation": {
                "presentation_mode": "speaker-inset",
                "rationale": "The speaker's explanation remains editorially important.",
            },
            "plan_sha256": broll_plan.canonical_sha256(
                broll_plan.presentation_subject(self.plan)
            ),
            "candidate_manifest_sha256": broll_plan.canonical_sha256(
                broll_plan.candidate_manifest(self.plan)
            ),
            "review_video_sha256": self.plan["input_hashes"]["review_video_sha256"],
        }

        updated = broll_plan.record_chat_presentation_decision(
            self.plan, decision, project_root=self.root,
        )

        self.assertEqual("speaker-inset", updated["presentation"]["mode"])
        self.assertEqual(BrollPlanTests._speaker_style(), updated["speaker_inset_style"])

    def test_approve_selection_requires_chat_speaker_presentation_decision(self):
        self.assertTrue(hasattr(broll_plan, "approve_selection"))
        selection_rationale = (
            "Explicit user action approved the exact B-roll selection shown in this review."
        )
        candidates = self._canonical_candidates(1)
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        self.plan["speaker_inset_style"] = self._speaker_style()
        selection = self._canonical_review([segment], intent="approve_selection")
        selection.update({
            "rationale": selection_rationale,
            "rationale_source": "review_ui_explicit_action",
        })

        with self.assertRaisesRegex(ValueError, "agent-chat presentation decision is required"):
            broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=selection_rationale,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )

    def test_speaker_inset_skill_docs_and_example_match_delivery_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        rules = (ROOT / "reference/broll-rules.md").read_text(encoding="utf-8")
        example = json.loads((
            ROOT / "examples/example-broll-plan.json"
        ).read_text(encoding="utf-8"))
        style = example["speaker_inset_style"]
        self.assertEqual(self._speaker_style(), style)
        for text in (skill, rules):
            normalized = " ".join(text.split())
            for value in (
                    "focused-panel", "full-bleed-wash", "corner-pip",
                    "project_layout_strategy", "layout_recommendation",
                    "top-left", "top-right", "width_ratio", "0.39",
                    "agent_chat_explicit_action", "presentation-decision.json",
                    "ordinary", "speaker-inset", "approve_selection",
                    "b-roll-selection", "Copy", "Download JSON",
                    "read-only", "collapsed", "final visual"):
                self.assertIn(value, text)
            self.assertIn("consumed as immutable evidence", normalized)
            self.assertIn("must not present it again", normalized)
            self.assertIn("ROI", text)
            self.assertIn("layout", text)
            self.assertIn("composite", text)
            self.assertNotIn("prepare_composite", text)
            self.assertNotIn("only to freeze exact B-roll selections", normalized)
            self.assertNotIn("size_candidates", text)
            self.assertNotIn("bottom-left", text)
            self.assertNotIn("bottom-right", text)
            self.assertNotIn('shape: "circle"', text)
        self.assertIn("review_video=Path(sys.argv[3]).resolve()", skill)
        self.assertNotIn("currently stops at the second-page review gate", rules)
        self.assertNotIn("do not normalize\nor deliver", skill)
        self.assertNotIn("layout_preset", style)
        self.assertNotIn("allowed_anchors", style)
        self.assertEqual("chosen", example["presentation"]["status"])
        self.assertEqual("speaker-inset", example["presentation"]["mode"])
        self.assertEqual("b-roll/presentation-decision.json", example["presentation"]["path"])
        self.assertEqual("approved", example["selection"]["status"])
        self.assertEqual("approve_selection", example["selection"]["submission_intent"])
        self.assertEqual("b-roll-selection", example["selection"]["approval_scope"])
        self.assertTrue(example["selection"]["consumed"])

    def test_candidate_review_docs_allow_direct_approval_of_page_edits(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        rules = (ROOT / "reference/broll-rules.md").read_text(encoding="utf-8")

        for text in (skill, rules):
            normalized = " ".join(text.split()).lower()
            self.assertIn("current exact configuration", normalized)
            self.assertIn("non-empty natural-language", normalized)
            self.assertIn("empty request changes", normalized)
            self.assertIn("page controls cannot express", normalized)
            self.assertIn("candidate selection and speaker composite approval remain separate", normalized)
            self.assertIn(
                "do not ask the user to choose ordinary or speaker-inset again",
                normalized,
            )
            self.assertIn(
                "`presentation-decision.json` receipt remains unchanged",
                normalized,
            )
            self.assertNotIn(
                "changed program timing, a changed prefilled segment, non-empty notes",
                normalized,
            )

        self.assertIn(
            "timeline=timeline,transcript=transcript,project_root=root",
            skill,
        )
        self.assertIn(
            "project_root=root,timeline=timeline,transcript=transcript",
            skill,
        )
        self.assertNotIn(
            "A changed candidate, plan, or review video requires a new chat choice",
            skill,
        )

    def test_dynamic_social_docs_and_example_define_search_context_and_semantic_ranking_contract(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        rules = (ROOT / "reference/broll-rules.md").read_text(encoding="utf-8")
        example = json.loads((
            ROOT / "examples/example-broll-plan.json"
        ).read_text(encoding="utf-8"))

        for text in (skill, rules):
            normalized = " ".join(text.split())
            for value in (
                    "dynamic-social", "0.40", "0.70",
                    "brief.search_context", "topic", "visual_direction", "1-12 unique keywords",
                    "semantic_role", "direct", "supportive", "atmospheric",
                    "direct subject/action", "defensible context/process", "theme-enhancing variant",
                    "visible frozen-frame evidence", "weak_semantic_match",
                    "semantic-first lexicographic", "tech", "entertainment",
                    "Both `semantic_fit == 0` and `context_fit == 0` are retained hard ineligibility protections",
                    "then the combined `composition_fit + style_fit` score"):
                self.assertIn(value, normalized)
            self.assertIn("complete A-roll scan", normalized)
            self.assertNotIn("selective", text.lower())
            self.assertNotIn("no minimum coverage", text.lower())

        self.assertEqual("dynamic-social", example["brief"]["density"])
        self.assertEqual(
            {"topic", "visual_direction", "keywords"},
            set(example["brief"]["search_context"]),
        )
        self.assertTrue(example["brief"]["search_context"]["topic"].strip())
        self.assertTrue(example["brief"]["search_context"]["visual_direction"].strip())
        keywords = example["brief"]["search_context"]["keywords"]
        self.assertGreaterEqual(len(keywords), 1)
        self.assertLessEqual(len(keywords), 12)
        self.assertEqual(len(keywords), len({item.casefold().strip() for item in keywords}))
        self.assertTrue(all(item.strip() for item in keywords))
        self.assertTrue(all(
            shot["semantic_role"] in {"direct", "supportive", "atmospheric"}
            for shot in example["shots"]
        ))

    def test_approve_selection_writes_consumed_authoritative_selection(self):
        self.assertTrue(hasattr(broll_plan, "approve_selection"))
        selection_rationale = (
            "Explicit user action approved the exact B-roll selection shown in this review."
        )
        candidates = self._canonical_candidates(1)
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        self.plan["speaker_inset_style"] = self._speaker_style()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self._canonical_review([segment], intent="approve_selection")
        selection.update({
            "rationale": selection_rationale,
            "rationale_source": "review_ui_explicit_action",
        })
        review_page = self.publish_review_page(selection["review_id"])

        prepared = broll_plan.approve_selection(
            self.plan, selection,
            mode="human", actor="Actual user",
            rationale=selection_rationale,
            project_root=self.root, timeline=self.timeline,
            transcript=self.transcript,
        )

        self.assertEqual("composite_pending", prepared["shots"][0]["status"])
        self.assertEqual({"segments": [segment]}, prepared["shots"][0]["selected"])
        self.assertNotIn("review_status", prepared)
        self.assertIsNone(prepared["decision"])
        self.assertIsNone(prepared["review"])
        binding = prepared["selection"]
        self.assertEqual("approved", binding["status"])
        self.assertEqual("approve_selection", binding["submission_intent"])
        self.assertEqual("b-roll-selection", binding["approval_scope"])
        self.assertTrue(binding["consumed"])
        self.assertEqual(broll_plan.sha256_file(review_page), binding["review_page_sha256"])
        self.assertEqual("b-roll/broll-selection.json", binding["path"])
        selection_path = self.root / "work" / binding["path"]
        self.assertTrue(selection_path.is_file())
        self.assertEqual(binding["sha256"], broll_plan.sha256_file(selection_path))
        receipt = projectlib.load_json(selection_path)
        self.assertEqual("approved", receipt["status"])
        self.assertEqual("b-roll-selection", receipt["approval_scope"])
        self.assertEqual([segment], prepared["shots"][0]["selected"]["segments"])
        self.assertEqual(
            [prepared["shots"][0]["candidates"][0]["sha256"]],
            receipt["selected_asset_sha256"],
        )
        self.assertEqual(selection["review_id"], receipt["source_review"]["review_id"])
        self.assertEqual(
            review_page.relative_to(self.root).as_posix(),
            receipt["source_review"]["path"],
        )
        self.assertEqual(broll_plan.sha256_file(review_page), receipt["source_review"]["sha256"])
        self.assertTrue(receipt["source_review"]["consumed"])
        self.assertEqual([], broll_plan.validate_plan(
            prepared, self.timeline, self.transcript,
            project_root=self.root, verify_files=True,
        ))

    def test_prepare_composite_legacy_export_is_canonicalized(self):
        candidates = self._canonical_candidates(1)
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        self.plan["speaker_inset_style"] = self._speaker_style()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self._canonical_review([segment], intent="prepare_composite")
        selection.update({
            "rationale": broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
        })

        prepared = broll_plan.prepare_composite(
            self.plan, selection,
            mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            project_root=self.root, timeline=self.timeline,
        )

        self.assertEqual("approved", prepared["selection"]["status"])
        self.assertEqual("approve_selection", prepared["selection"]["submission_intent"])
        self.assertEqual("b-roll-selection", prepared["selection"]["approval_scope"])
        receipt = projectlib.load_json(
            self.root / "work" / prepared["selection"]["path"]
        )
        self.assertEqual("approve_selection", receipt["submission_intent"])
        self.assertEqual("approved", receipt["status"])

    def test_approve_selection_all_skipped_is_an_approved_no_op(self):
        selection_rationale = (
            "Explicit user action approved the exact B-roll selection shown in this review."
        )
        self.plan["speaker_inset_style"] = self._speaker_style()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self.review_for(
            self.plan, [{"id": "shot", "decision": "skip"}],
            rationale=selection_rationale,
            submission_intent="approve_selection",
            approval_scope="b-roll-selection",
            explicit_user_action=True,
            revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        self.publish_review_page(selection["review_id"])

        approved = broll_plan.approve_selection(
            self.plan, selection,
            mode="human", actor="Actual user", rationale=selection_rationale,
            project_root=self.root, timeline=self.timeline,
            transcript=self.transcript,
        )

        self.assertEqual("skipped", approved["shots"][0]["status"])
        self.assertIn("review_status", approved)
        self.assertEqual("approved", approved["review_status"])
        self.assertEqual("b-roll-selection", approved["review"]["approval_scope"])
        self.assertEqual("approve_selection", approved["review"]["submission_intent"])
        self.assertEqual([], broll_plan.validate_plan(
            approved, self.timeline, self.transcript,
            project_root=self.root, verify_files=True,
        ))
        registered = broll_plan.register_operation(self.project, approved)
        self.assertNotIn("b-roll", registered["sequences"]["main"]["operations"])
        self.assertFalse(any(
            item.get("id") == "b-roll" for item in registered["operations"]
        ))
        self.publish_review_page(selection["review_id"]).write_bytes(b"tampered")
        self.assertTrue(any(
            "review page is missing or stale" in error
            for error in broll_plan.validate_plan(
                approved, self.timeline, self.transcript,
                project_root=self.root, verify_files=True,
            )
        ))

    def test_composite_review_binds_all_speaker_artifacts_and_cannot_change_selection(self):
        self.assertTrue(hasattr(broll_plan, "approve_selection"))
        selection_rationale = (
            "Explicit user action approved the exact B-roll selection shown in this review."
        )
        candidates = self._canonical_candidates(1)
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        skipped = copy.deepcopy(self.plan["shots"][0])
        skipped.update({
            "id": "pre-skipped",
            "program_range": {"start_s": 2.0, "end_s": 3.0},
            "source_ranges": [{"clip_id": "one", "start_s": 2.0, "end_s": 3.0}],
            "transcript_evidence": {"words": [self.mapped_words[1]]},
            "candidates": [],
            "selected": None,
            "status": "skipped",
        })
        self.plan["shots"].append(skipped)
        self.plan["speaker_inset_style"] = self._speaker_style()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self._canonical_review([segment], intent="approve_selection")
        selection["shots"].append({"id": "pre-skipped", "decision": "skip"})
        selection.update({
            "rationale": selection_rationale,
            "rationale_source": "review_ui_explicit_action",
        })
        self.publish_review_page(selection["review_id"])
        prepared = broll_plan.approve_selection(
            self.plan, selection,
            mode="human", actor="Actual user",
            rationale=selection_rationale,
            project_root=self.root, timeline=self.timeline,
            transcript=self.transcript,
        )
        prepared["speaker_inset"] = {
            "analysis": {
                "path": "b-roll/speaker-inset-analysis.json", "sha256": "a" * 64,
            },
            "agent_input": {
                "path": "b-roll/speaker-inset-agent-input.json", "sha256": "b" * 64,
            },
            "preview": {
                "path": "b-roll/speaker-inset-preview.json", "sha256": "c" * 64,
            },
            "clearance": {
                "path": "b-roll/speaker-inset-clearance.json", "sha256": "d" * 64,
            },
        }
        review = self.review_for(
            prepared, [],
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent="approve",
            approval_scope="speaker-inset-composite",
            review_stage="composite",
            explicit_user_action=True,
            revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
            selection_sha256=prepared["selection"]["sha256"],
            analysis_sha256=prepared["speaker_inset"]["analysis"]["sha256"],
            agent_input_sha256=prepared["speaker_inset"]["agent_input"]["sha256"],
            preview_sha256=prepared["speaker_inset"]["preview"]["sha256"],
            clearance_sha256=prepared["speaker_inset"]["clearance"]["sha256"],
            style_sha256=broll_plan.canonical_sha256(prepared["speaker_inset_style"]),
        )
        review.pop("shots")
        approved = broll_plan.apply_review(
            prepared, review,
            mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline,
        )
        self.assertEqual("selected", approved["shots"][0]["status"])
        self.assertEqual("skipped", approved["shots"][1]["status"])
        self.assertEqual("composite", approved["review"]["review_stage"])
        self.assertEqual(
            prepared["speaker_inset"]["clearance"]["sha256"],
            approved["review"]["clearance_sha256"],
        )
        self.assertEqual([], broll_plan.validate_plan(
            approved, self.timeline, self.transcript,
        ))

        stale = copy.deepcopy(review)
        stale["preview_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "preview_sha256"):
            broll_plan.apply_review(
                prepared, stale,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                timeline=self.timeline,
            )
        changed = copy.deepcopy(review)
        changed["shots"] = broll_plan._decision_manifest(prepared["shots"])
        changed["shots"][0]["segments"][0]["source_range"]["start_s"] = 0.25
        interaction_path = self.root / "work/b-roll/broll-interaction.json"
        with self.assertRaisesRegex(ValueError, "must not include candidate shots"):
            broll_plan.apply_review(
                prepared, changed,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                interaction_path=interaction_path,
                timeline=self.timeline,
            )
        self.assertFalse(interaction_path.exists())

    def _canonical_candidates(self, count=3):
        shot = self.plan["shots"][0]
        base = shot["candidates"][0]
        candidates = []
        for index in range(count):
            candidate = copy.deepcopy(base)
            candidate_id = f"asset-{index + 1}"
            path = self.root / f"work/cache/b-roll/{candidate_id}.mp4"
            path.write_bytes(f"asset-{index + 1}".encode("ascii"))
            candidate.update({
                "id": candidate_id,
                "cache_path": path.relative_to(self.root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(path),
                "bytes": path.stat().st_size,
                "duration_s": 4.0,
                "probe": {"duration_s": 4.0, "width": 1920, "height": 1080},
                "ranking": {
                    "rank": index + 1,
                    "scores": {
                        "semantic_fit": 4, "context_fit": 4,
                        "composition_fit": 3, "style_fit": 3,
                        "text_logo_risk": 0,
                    },
                    "warnings": [], "rationale": "Relevant footage.",
                    "duplicate_notes": [], "similar_footage": [],
                },
            })
            candidates.append(candidate)
        shot["candidates"] = candidates
        return candidates

    def _canonical_review(self, segments, *, intent="approve"):
        review = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
                "segments": copy.deepcopy(segments),
            }],
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent=intent,
            explicit_user_action=True,
            revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        if intent == "approve_selection":
            review["approval_scope"] = "b-roll-selection"
        return review

    def _edited_review_configuration(self):
        candidates = self._canonical_candidates(2)
        program_range = {"start_s": 1.5, "end_s": 3.5}
        segments = [
            {
                "candidate_id": candidates[1]["id"],
                "source_range": {"start_s": 0.5, "end_s": 2.0},
                "program_range": {"start_s": 1.5, "end_s": 2.5},
                "playback_rate": 1.5,
            },
            {
                "candidate_id": candidates[0]["id"],
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 2.5, "end_s": 3.5},
                "playback_rate": 1.0,
            },
        ]
        return candidates, program_range, segments

    def test_apply_review_accepts_edited_page_configuration_without_rebuild(self):
        self.assertIn("transcript", inspect.signature(broll_plan.apply_review).parameters)
        self.assertIn("project_root", inspect.signature(broll_plan.apply_review).parameters)
        candidates, program_range, segments = self._edited_review_configuration()
        self.plan["shots"][0]["review_default"] = {
            "decision": "select",
            "segments": [{
                "candidate_id": candidates[0]["id"],
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": 1.0,
            }],
        }
        self.plan = self.record_presentation(self.plan, "ordinary")
        presentation = copy.deepcopy(self.plan["presentation"])
        presentation_path = self.root / "work/b-roll/presentation-decision.json"
        presentation_sha256 = broll_plan.sha256_file(presentation_path)
        review = self._canonical_review(segments)
        review["shots"][0]["program_range"] = copy.deepcopy(program_range)
        review_page = self.publish_review_page(review["review_id"])
        review_page_sha256 = broll_plan.sha256_file(review_page)
        interaction_path = self.root / "work/b-roll/broll-interaction.json"

        with mock.patch.object(
                broll_plan, "rebuild_plan_from_revision",
                side_effect=AssertionError("edited approval must not rebuild")):
            approved = broll_plan.apply_review(
                self.plan, review,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                interaction_path=interaction_path,
                timeline=self.timeline, transcript=self.transcript,
                project_root=self.root,
            )

        shot = approved["shots"][0]
        self.assertEqual("selected", shot["status"])
        self.assertEqual(program_range, shot["program_range"])
        self.assertEqual([{"clip_id": "one", **program_range}], shot["source_ranges"])
        self.assertEqual([self.mapped_words[1]], shot["transcript_evidence"]["words"])
        self.assertEqual(segments, shot["selected"]["segments"])
        self.assertNotIn("review_default", shot)
        self.assertEqual(presentation, approved["presentation"])
        self.assertEqual(presentation_sha256, broll_plan.sha256_file(presentation_path))
        self.assertEqual(review_page_sha256, broll_plan.sha256_file(review_page))
        self.assertTrue(interaction_path.is_file())
        self.assertEqual({
            "review_id": review["review_id"],
            "path": review_page.relative_to(self.root).as_posix(),
            "sha256": review_page_sha256,
            "consumed": True,
        }, approved["review"]["source_review"])
        self.assertEqual([], broll_plan.validate_plan(
            approved, self.timeline, self.transcript,
            project_root=self.root, verify_files=True,
        ))
        self.assertEqual(
            sorted(candidate["sha256"] for candidate in candidates),
            approved["review"]["selected_asset_sha256"],
        )
        review_page.write_bytes(b"tampered review page")
        self.assertIn(
            "approved review page is missing or stale",
            broll_plan.validate_plan(
                approved, self.timeline, self.transcript,
                project_root=self.root, verify_files=True,
            ),
        )

    def test_approve_selection_accepts_edited_page_configuration_and_preserves_route(self):
        self.assertIn("transcript", inspect.signature(broll_plan.approve_selection).parameters)
        candidates, program_range, segments = self._edited_review_configuration()
        self.plan["shots"][0]["review_default"] = {
            "decision": "select",
            "segments": [{
                "candidate_id": candidates[0]["id"],
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": 1.0,
            }],
        }
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        presentation = copy.deepcopy(self.plan["presentation"])
        speaker_style = copy.deepcopy(self.plan["speaker_inset_style"])
        presentation_path = self.root / "work/b-roll/presentation-decision.json"
        presentation_sha256 = broll_plan.sha256_file(presentation_path)
        selection = self._canonical_review(segments, intent="approve_selection")
        selection["shots"][0]["program_range"] = copy.deepcopy(program_range)
        selection.update({
            "rationale": broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
        })
        review_page = self.publish_review_page(selection["review_id"])
        review_page_sha256 = broll_plan.sha256_file(review_page)
        candidate_pages = sorted((self.root / "review/03-b-roll").glob("b-roll-review-*.html"))

        with mock.patch.object(
                broll_plan, "rebuild_plan_from_revision",
                side_effect=AssertionError("edited approval must not rebuild")):
            approved = broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )

        shot = approved["shots"][0]
        self.assertEqual("composite_pending", shot["status"])
        self.assertEqual(program_range, shot["program_range"])
        self.assertEqual([{"clip_id": "one", **program_range}], shot["source_ranges"])
        self.assertEqual([self.mapped_words[1]], shot["transcript_evidence"]["words"])
        self.assertEqual(segments, shot["selected"]["segments"])
        self.assertNotIn("review_default", shot)
        carried_presentation = copy.deepcopy(approved["presentation"])
        carried_from = carried_presentation.pop("carried_from_plan_sha256")
        self.assertEqual(presentation, carried_presentation)
        self.assertEqual(
            projectlib.load_json(presentation_path)["plan_sha256"], carried_from,
        )
        self.assertEqual(speaker_style, approved["speaker_inset_style"])
        self.assertEqual(presentation_sha256, broll_plan.sha256_file(presentation_path))
        self.assertEqual(review_page_sha256, broll_plan.sha256_file(review_page))
        self.assertEqual(
            candidate_pages,
            sorted((self.root / "review/03-b-roll").glob("b-roll-review-*.html")),
        )
        self.assertEqual("approved", approved["selection"]["status"])
        self.assertFalse((self.root / "work/b-roll/broll-interaction.json").exists())
        self.assertNotIn("review_status", approved)
        self.assertEqual(
            sorted(candidate["sha256"] for candidate in candidates),
            projectlib.load_json(
                self.root / "work/b-roll/broll-selection.json"
            )["selected_asset_sha256"],
        )

    def test_edited_approval_rejects_invalid_page_configuration_without_writes(self):
        self._canonical_candidates(2)
        self.plan = self.record_presentation(self.plan, "ordinary")
        original = copy.deepcopy(self.plan)
        review_page = self.publish_review_page()
        presentation_path = self.root / "work/b-roll/presentation-decision.json"
        interaction_path = self.root / "work/b-roll/broll-interaction.json"
        interaction_path.write_bytes(b"existing interaction")
        immutable_hashes = {
            "page": broll_plan.sha256_file(review_page),
            "presentation": broll_plan.sha256_file(presentation_path),
            "interaction": broll_plan.sha256_file(interaction_path),
        }

        def review_with(program_range, segments):
            review = self._canonical_review(segments)
            review["shots"][0]["program_range"] = copy.deepcopy(program_range)
            return review

        valid_segments = self._edited_review_configuration()[2]
        cases = []
        outside = review_with(
            {"start_s": 1.5, "end_s": 4.033333333}, valid_segments,
        )
        cases.append(("outside bounds", outside, "allowed bounds"))
        unaligned = review_with(
            {"start_s": 1.51, "end_s": 3.5}, valid_segments,
        )
        cases.append(("frame alignment", unaligned, "timeline frames"))
        no_words = review_with(
            {"start_s": 0.0, "end_s": 0.5},
            [{
                "candidate_id": self.plan["shots"][0]["candidates"][0]["id"],
                "source_range": {"start_s": 0.0, "end_s": 0.5},
                "program_range": {"start_s": 0.0, "end_s": 0.5},
                "playback_rate": 1.0,
            }],
        )
        cases.append(("complete transcript word", no_words, "complete transcript word"))
        unknown = review_with(
            {"start_s": 1.5, "end_s": 3.5}, valid_segments,
        )
        unknown["shots"][0]["segments"][0]["candidate_id"] = "unknown"
        cases.append(("unknown candidate", unknown, "does not belong"))
        duplicate = review_with(
            {"start_s": 1.5, "end_s": 3.5}, valid_segments,
        )
        duplicate["shots"][0]["segments"][1]["candidate_id"] = (
            duplicate["shots"][0]["segments"][0]["candidate_id"]
        )
        cases.append(("duplicate candidate", duplicate, "unique"))

        for label, review, message in cases:
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, message):
                broll_plan.apply_review(
                    self.plan, review,
                    mode="human", actor="Actual user",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    interaction_path=interaction_path,
                    timeline=self.timeline, transcript=self.transcript,
                    project_root=self.root,
                )
            self.assertEqual(original, self.plan)
            self.assertEqual(immutable_hashes["page"], broll_plan.sha256_file(review_page))
            self.assertEqual(
                immutable_hashes["presentation"],
                broll_plan.sha256_file(presentation_path),
            )
            self.assertEqual(
                immutable_hashes["interaction"],
                broll_plan.sha256_file(interaction_path),
            )

    def test_explicit_approval_rejects_stale_evidence_before_writing_receipts(self):
        candidates, program_range, segments = self._edited_review_configuration()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self._canonical_review(segments, intent="approve_selection")
        selection["shots"][0]["program_range"] = copy.deepcopy(program_range)
        selection.update({
            "rationale": broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
        })
        review_page = self.publish_review_page(selection["review_id"])
        presentation_path = self.root / "work/b-roll/presentation-decision.json"
        selection_path = self.root / "work/b-roll/broll-selection.json"
        selection_path.write_bytes(b"existing selection")
        original = copy.deepcopy(self.plan)
        original_page = review_page.read_bytes()
        original_presentation = presentation_path.read_bytes()
        original_selection = selection_path.read_bytes()

        candidate_path = self.root / "work" / candidates[0]["cache_path"]
        candidate_bytes = candidate_path.read_bytes()
        candidate_path.write_bytes(b"tampered candidate")
        with self.assertRaisesRegex(ValueError, "candidate .*SHA-256 is stale"):
            broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )
        candidate_path.write_bytes(candidate_bytes)

        review_page.unlink()
        with self.assertRaisesRegex(ValueError, "immutable candidate review page is missing"):
            broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )
        review_page.write_bytes(original_page)

        presentation_path.write_bytes(b"tampered presentation")
        with self.assertRaisesRegex(ValueError, "presentation decision"):
            broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )
        presentation_path.write_bytes(original_presentation)

        self.assertEqual(original, self.plan)
        self.assertEqual(original_page, review_page.read_bytes())
        self.assertEqual(original_presentation, presentation_path.read_bytes())
        self.assertEqual(original_selection, selection_path.read_bytes())

    def test_explicit_approval_rejects_misbound_review_page_before_writing_receipts(self):
        candidates, program_range, segments = self._edited_review_configuration()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        selection = self._canonical_review(segments, intent="approve_selection")
        selection["shots"][0]["program_range"] = copy.deepcopy(program_range)
        selection.update({
            "rationale": broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
        })
        review_page = self.publish_review_page(selection["review_id"])
        page_text = review_page.read_text(encoding="utf-8")
        encoded = build_review_page.PAYLOAD_RE.search(page_text).group(1)
        payload = json.loads(base64.b64decode(encoded))
        payload["candidate_manifest_sha256"] = "0" * 64
        stale_encoded = base64.b64encode(
            json.dumps(payload).encode("utf-8")
        ).decode("ascii")
        review_page.write_text(
            page_text.replace(encoded, stale_encoded), encoding="utf-8",
        )
        selection_path = self.root / "work/b-roll/broll-selection.json"

        with self.assertRaisesRegex(ValueError, "review page .*binding"):
            broll_plan.approve_selection(
                self.plan, selection,
                mode="human", actor="Actual user",
                rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                project_root=self.root, timeline=self.timeline,
                transcript=self.transcript,
            )

        self.assertFalse(selection_path.exists())

    def test_explicit_approval_requires_canonical_project_inputs_without_writes(self):
        candidates = self._canonical_candidates(1)
        self.plan = self.record_presentation(self.plan, "ordinary")
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": {"start_s": 1.0, "end_s": 2.0},
            "playback_rate": 1.0,
        }
        review = self._canonical_review([segment])
        self.publish_review_page(review["review_id"])
        interaction_path = self.root / "work/b-roll/broll-interaction.json"
        original = copy.deepcopy(self.plan)
        altered_transcript = copy.deepcopy(self.transcript)
        altered_transcript["segments"][0]["words"].append({
            "word": "injected", "start": 1.25, "end": 1.5,
        })
        cases = (
            ({"timeline": None, "transcript": self.transcript, "project_root": self.root}, "canonical timeline"),
            ({"timeline": self.timeline, "transcript": None, "project_root": self.root}, "canonical transcript"),
            ({"timeline": self.timeline, "transcript": self.transcript, "project_root": None}, "project root"),
            ({"timeline": self.timeline, "transcript": altered_transcript, "project_root": self.root}, "transcript does not match project file"),
        )
        for arguments, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                broll_plan.apply_review(
                    self.plan, review,
                    mode="human", actor="Actual user",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    interaction_path=interaction_path,
                    **arguments,
                )
            self.assertEqual(original, self.plan)
            self.assertFalse(interaction_path.exists())

    def test_approve_selection_requires_canonical_timeline_and_transcript(self):
        candidates = self._canonical_candidates(1)
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        segment = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": {"start_s": 1.0, "end_s": 2.0},
            "playback_rate": 1.0,
        }
        selection = self._canonical_review([segment], intent="approve_selection")
        selection.update({
            "rationale": broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
        })
        self.publish_review_page(selection["review_id"])
        for arguments, message in (
                ({"timeline": None, "transcript": self.transcript}, "canonical timeline"),
                ({"timeline": self.timeline, "transcript": None}, "canonical transcript")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                broll_plan.approve_selection(
                    self.plan, selection,
                    mode="human", actor="Actual user",
                    rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
                    project_root=self.root, **arguments,
                )
        self.assertFalse((self.root / "work/b-roll/broll-selection.json").exists())

    def test_explicit_page_approval_accepts_skip_and_image_ken_burns(self):
        base_plan = copy.deepcopy(self.plan)
        self.plan["shots"][0]["review_default"] = {
            "decision": "select",
            "segments": [{
                "candidate_id": "asset",
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": 1.0,
            }],
        }
        self.plan = self.record_presentation(self.plan, "ordinary")
        skip = self.review_for(
            self.plan, [{"id": "shot", "decision": "skip"}],
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent="approve", explicit_user_action=True,
            revision_notes="", rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        self.publish_review_page(skip["review_id"])
        skipped = broll_plan.apply_review(
            self.plan, skip, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline, transcript=self.transcript,
            project_root=self.root,
        )
        self.assertEqual("skipped", skipped["shots"][0]["status"])
        self.assertNotIn("review_default", skipped["shots"][0])

        image_plan = base_plan
        image_plan["shots"][0]["candidates"][0]["media_type"] = "image"
        image_plan["shots"][0]["candidates"][0].pop("duration_s")
        image_plan["shots"][0]["candidates"][0].pop("probe")
        image_plan = self.record_presentation(image_plan, "ordinary")
        image_review = self.review_for(
            image_plan,
            [{
                "id": "shot", "decision": "select",
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "candidate_id": "asset",
                "ken_burns": {"direction": "pan-right"},
            }],
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent="approve", explicit_user_action=True,
            revision_notes="", rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        self.publish_review_page(image_review["review_id"], plan=image_plan)
        image = broll_plan.apply_review(
            image_plan, image_review, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline, transcript=self.transcript,
            project_root=self.root,
        )
        self.assertEqual("selected", image["shots"][0]["status"])
        self.assertEqual(
            {"candidate_id": "asset", "ken_burns": {"direction": "pan-right"}},
            image["shots"][0]["selected"],
        )

    def test_canonical_segments_allow_fixed_rates_and_one_to_three_unique_candidates(self):
        candidates = self._canonical_candidates()
        self.plan = self.record_presentation(self.plan, "ordinary")
        self.publish_review_page()
        segments = [
            {
                "candidate_id": candidates[0]["id"],
                "source_range": {"start_s": 0.0, "end_s": 0.25},
                "program_range": {"start_s": 1.0, "end_s": 1.5},
                "playback_rate": 0.5,
            },
            {
                "candidate_id": candidates[1]["id"],
                "source_range": {"start_s": 0.0, "end_s": 0.75},
                "program_range": {"start_s": 1.5, "end_s": 2.0},
                "playback_rate": 1.5,
            },
        ]
        approved = broll_plan.apply_review(
            self.plan, self._canonical_review(segments), mode="human", actor="User",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline, transcript=self.transcript,
            project_root=self.root,
        )
        self.assertEqual(segments, approved["shots"][0]["selected"]["segments"])
        self.assertEqual(
            sorted(candidate["sha256"] for candidate in candidates[:2]),
            approved["review"]["selected_asset_sha256"],
        )
        details = broll_plan.selection_details(
            approved["shots"][0], candidates, self.timeline,
        )
        self.assertEqual([0.5, 1.5], [item["playback_rate"] for item in details["segments"]])
        self.assertEqual(2, len(details["segment_details"]))

        for rate in (0.5, 1.0, 1.5, 2.0):
            single = [{
                "candidate_id": candidates[0]["id"],
                "source_range": {"start_s": 0.0, "end_s": rate},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": rate,
            }]
            with self.subTest(rate=rate):
                result = broll_plan.apply_review(
                    self.plan, self._canonical_review(single), mode="human", actor="User",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    timeline=self.timeline, transcript=self.transcript,
                    project_root=self.root,
                )
                self.assertEqual(rate, result["shots"][0]["selected"]["segments"][0]["playback_rate"])

    def test_canonical_segments_reject_bad_rates_cardinality_identity_and_program_coverage(self):
        candidates = self._canonical_candidates()
        self.plan = self.record_presentation(self.plan, "ordinary")
        self.publish_review_page()
        base = {
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": {"start_s": 1.0, "end_s": 2.0},
            "playback_rate": 1.0,
        }
        for rate in (True, float("nan"), float("inf"), 0, -1, 0.75, 2.5):
            segment = copy.deepcopy(base)
            segment["playback_rate"] = rate
            with self.subTest(rate=rate), self.assertRaisesRegex(ValueError, "playback_rate"):
                broll_plan.apply_review(
                    self.plan, self._canonical_review([segment]), mode="human", actor="User",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    timeline=self.timeline, transcript=self.transcript,
                    project_root=self.root,
                )

        cases = []
        cases.append(([], "1-3 segments"))
        cases.append(([copy.deepcopy(base)] * 4, "1-3 segments"))
        duplicate = [copy.deepcopy(base), copy.deepcopy(base)]
        duplicate[0]["program_range"]["end_s"] = 1.5
        duplicate[0]["source_range"]["end_s"] = 0.5
        duplicate[1]["program_range"]["start_s"] = 1.5
        duplicate[1]["source_range"]["end_s"] = 0.5
        cases.append((duplicate, "unique"))
        unknown = [copy.deepcopy(base)]
        unknown[0]["candidate_id"] = "unknown"
        cases.append((unknown, "belong"))
        gap = [copy.deepcopy(base), copy.deepcopy(base)]
        gap[0].update({
            "candidate_id": candidates[0]["id"],
            "source_range": {"start_s": 0.0, "end_s": 0.4},
            "program_range": {"start_s": 1.0, "end_s": 1.4},
        })
        gap[1].update({
            "candidate_id": candidates[1]["id"],
            "source_range": {"start_s": 0.0, "end_s": 0.5},
            "program_range": {"start_s": 1.5, "end_s": 2.0},
        })
        cases.append((gap, "continuous"))
        for segments, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                broll_plan.apply_review(
                    self.plan, self._canonical_review(segments), mode="human", actor="User",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    timeline=self.timeline, transcript=self.transcript,
                    project_root=self.root,
                )

    def test_equal_program_frame_allocation_covers_range_and_last_absorbs_remainder(self):
        timeline = {"fps": {"num": 30, "den": 1}}
        program = {"start_s": 1.0, "end_s": 2.0}
        self.assertEqual(
            [{"start_s": 1.0, "end_s": 2.0}],
            broll_plan.allocate_program_ranges(program, 1, timeline),
        )
        two = broll_plan.allocate_program_ranges(program, 2, timeline)
        self.assertEqual([15, 15], [round((item["end_s"] - item["start_s"]) * 30) for item in two])
        odd = broll_plan.allocate_program_ranges(
            {"start_s": 0.0, "end_s": 31 / 30}, 3, timeline,
        )
        self.assertEqual([10, 10, 11], [round((item["end_s"] - item["start_s"]) * 30) for item in odd])
        self.assertEqual(odd[0]["end_s"], odd[1]["start_s"])
        self.assertEqual(odd[1]["end_s"], odd[2]["start_s"])
        self.assertAlmostEqual(31 / 30, odd[-1]["end_s"])

    def test_multiple_review_defaults_preserve_candidate_id_validation_state(self):
        plan = copy.deepcopy(self.plan)
        first = plan["shots"][0]
        first["review_default"] = {
            "decision": "select",
            "segments": [{
                "candidate_id": "asset",
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": 1.0,
            }],
        }
        second = copy.deepcopy(first)
        second["id"] = "second"
        second["program_range"] = {"start_s": 2.0, "end_s": 3.0}
        second["source_ranges"] = [{"clip_id": "one", "start_s": 2.0, "end_s": 3.0}]
        second["transcript_evidence"] = {"words": [self.mapped_words[1]]}
        second["candidates"][0]["id"] = "asset-2"
        second["review_default"]["segments"][0].update({
            "candidate_id": "asset-2",
            "program_range": {"start_s": 2.0, "end_s": 3.0},
        })
        plan["shots"].append(second)

        self.assertEqual([], broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_rejects_invalid_overlapping_or_out_of_bounds_ranges(self):
        plan = copy.deepcopy(self.plan); duplicate = copy.deepcopy(plan["shots"][0]); duplicate["id"] = "second"; duplicate["program_range"] = {"start_s": 1.5, "end_s": 3}; plan["shots"].append(duplicate)
        self.assertIn("second program range overlaps shot", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["program_range"] = {"start_s": -1, "end_s": 1}
        self.assertIn("shot program range is outside timeline", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_rejects_non_frame_aligned_program_range_before_review_publication(self):
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["program_range"]["end_s"] = 2.01
        plan["shots"][0]["source_ranges"][0]["end_s"] = 2.01

        self.assertIn(
            "shot program range must align to timeline frames",
            broll_plan.validate_plan(plan, self.timeline, self.transcript),
        )

    def test_evidence_word_must_exactly_match_mapped_transcript_word(self):
        plan = copy.deepcopy(self.plan); plan["shots"][0]["transcript_evidence"]["words"][0]["source_range"]["start_s"] = 1.1
        self.assertIn("shot transcript evidence word is not mapped from transcript", broll_plan.validate_plan(plan, self.timeline, self.transcript))
        plan = copy.deepcopy(self.plan); plan["shots"][0]["transcript_evidence"]["words"][0]["program_range"]["end_s"] = 2.1
        self.assertIn("shot transcript evidence word is not mapped from transcript", broll_plan.validate_plan(plan, self.timeline, self.transcript))

    def test_apply_review_rejects_revision_request_before_writing_or_mutating(self):
        request = self.review(
            submission_intent="request_revision",
            explicit_user_action=True,
            revision_notes="Start on the next phrase.",
        )
        request.pop("rationale")
        interaction = self.root / "work/b-roll/broll-interaction.json"
        original = copy.deepcopy(self.plan)

        with self.assertRaisesRegex(ValueError, "request_revision"):
            broll_plan.apply_review(
                self.plan, request, mode="human", actor="User",
                rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                interaction_path=interaction,
            )

        self.assertEqual(original, self.plan)
        self.assertFalse(interaction.exists())

    def test_canonical_single_segment_approve_requires_fixed_rate_and_frame_match(self):
        self.plan = self.record_presentation(self.plan, "ordinary")
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.25, "end_s": 1.25},
            "program_range": {"start_s": 1.0, "end_s": 2.0},
            "playback_rate": 1.0,
        }
        review = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
                "segments": [copy.deepcopy(segment)],
            }],
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent="approve",
            explicit_user_action=True,
            revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        self.publish_review_page(review["review_id"])
        approved = broll_plan.apply_review(
            self.plan, review, mode="human", actor="User",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline, transcript=self.transcript,
            project_root=self.root,
        )
        self.assertEqual({"segments": [segment]}, approved["shots"][0]["selected"])
        self.assertEqual("review_ui_explicit_action", approved["review"]["rationale_source"])
        self.assertEqual("canonical", broll_plan.selection_details(
            approved["shots"][0], approved["shots"][0]["candidates"][0], self.timeline,
        )["format"])
        tampered = copy.deepcopy(approved)
        tampered["review"].pop("rationale_source")
        tampered["decision"].pop("rationale_source")
        self.assertIn(
            "new human review rationale_source is invalid",
            broll_plan.validate_plan(tampered, self.timeline, self.transcript),
        )

        for label, mutate, message in (
            ("speed", lambda value: value.update(playback_rate=0.75), "playback_rate"),
            ("duration", lambda value: value["source_range"].update(end_s=1.5), "one timeline frame"),
        ):
            invalid = copy.deepcopy(review)
            mutate(invalid["shots"][0]["segments"][0])
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, message):
                broll_plan.apply_review(
                    self.plan, invalid, mode="human", actor="User",
                    rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                    timeline=self.timeline, transcript=self.transcript,
                    project_root=self.root,
                )

        multiple = copy.deepcopy(review)
        multiple["shots"][0]["segments"].append(copy.deepcopy(segment))
        with self.assertRaisesRegex(ValueError, "unique"):
            broll_plan.apply_review(
                self.plan, multiple, mode="human", actor="User",
                rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
                timeline=self.timeline, transcript=self.transcript,
                project_root=self.root,
            )

    def test_revision_request_validates_bounds_and_rebuilds_unapproved_plan(self):
        request = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                "segments": [{
                    "candidate_id": "asset",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 1.0, "end_s": 3.0},
                    "playback_rate": 1.0,
                }],
            }],
            submission_intent="request_revision",
            explicit_user_action=True,
            revision_notes="End after process.",
        )
        request.pop("rationale")

        self.assertEqual([], broll_plan.validate_revision_request(
            self.plan, request, self.timeline, self.transcript,
        ))
        rebuilt = broll_plan.rebuild_plan_from_revision(
            self.plan, request, self.timeline, self.transcript,
        )
        shot = rebuilt["shots"][0]
        self.assertEqual({"start_s": 1.0, "end_s": 3.0}, shot["program_range"])
        self.assertEqual(["factory", "process"], [
            word["word"] for word in shot["transcript_evidence"]["words"]
        ])
        self.assertEqual("candidates_ready", shot["status"])
        self.assertIsNone(shot["selected"])
        self.assertEqual(request["shots"][0]["segments"], shot["review_default"]["segments"])
        self.assertIsNone(rebuilt["review"])
        self.assertIsNone(rebuilt["decision"])
        self.assertNotEqual(
            broll_plan.canonical_sha256(broll_plan.review_subject(self.plan)),
            broll_plan.canonical_sha256(broll_plan.review_subject(rebuilt)),
        )

        stale = copy.deepcopy(request)
        stale["plan_sha256"] = "0" * 64
        self.assertTrue(any("plan_sha256 does not match" in error for error in
                            broll_plan.validate_revision_request(
                                self.plan, stale, self.timeline, self.transcript,
                            )))
        out_of_bounds = copy.deepcopy(request)
        out_of_bounds["shots"][0]["requested_program_range"] = {"start_s": 1.0, "end_s": 4.033333333}
        out_of_bounds["shots"][0]["segments"][0]["program_range"] = copy.deepcopy(
            out_of_bounds["shots"][0]["requested_program_range"]
        )
        out_of_bounds["shots"][0]["segments"][0]["source_range"]["end_s"] = 3.033333333
        self.assertTrue(any("allowed" in error or "candidate" in error for error in
                            broll_plan.validate_revision_request(
                                self.plan, out_of_bounds, self.timeline, self.transcript,
                            )))

    def test_revision_request_rejects_empty_notes(self):
        request = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                "segments": [{
                    "candidate_id": "asset",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 1.0, "end_s": 3.0},
                    "playback_rate": 1.0,
                }],
            }],
            submission_intent="request_revision",
            explicit_user_action=True,
            revision_notes="Required natural-language change.",
        )
        request.pop("rationale")

        for notes in ("", "   "):
            with self.subTest(notes=repr(notes)):
                invalid = copy.deepcopy(request)
                invalid["revision_notes"] = notes
                self.assertIn(
                    "revision_notes must be non-empty",
                    broll_plan.validate_revision_request(
                        self.plan, invalid, self.timeline, self.transcript,
                    ),
                )

    def test_revision_rebuild_preserves_the_original_presentation_route(self):
        for mode in ("ordinary", "speaker-inset"):
            with self.subTest(mode=mode):
                presented = self.record_presentation(copy.deepcopy(self.plan), mode)
                original_subject_sha256 = broll_plan.canonical_sha256(
                    broll_plan.presentation_subject(presented)
                )
                receipt_path = self.root / "work/b-roll/presentation-decision.json"
                original_receipt = receipt_path.read_bytes()
                original_receipt_sha256 = broll_plan.sha256_file(receipt_path)
                request = self.review_for(
                    presented,
                    [{
                        "id": "shot", "decision": "select",
                        "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                        "segments": [{
                            "candidate_id": "asset",
                            "source_range": {"start_s": 0.0, "end_s": 2.0},
                            "program_range": {"start_s": 1.0, "end_s": 3.0},
                            "playback_rate": 1.0,
                        }],
                    }],
                    submission_intent="request_revision",
                    explicit_user_action=True,
                    revision_notes="Use the revised range.",
                )
                request.pop("rationale")

                rebuilt = broll_plan.rebuild_plan_from_revision(
                    presented, request, self.timeline, self.transcript,
                )

                self.assertEqual(mode, rebuilt["presentation"]["mode"])
                self.assertEqual(
                    original_subject_sha256,
                    rebuilt["presentation"]["carried_from_plan_sha256"],
                )
                self.assertEqual(
                    mode == "speaker-inset",
                    "speaker_inset_style" in rebuilt,
                )
                self.assertEqual([], broll_plan.presentation_errors(
                    rebuilt, project_root=self.root, required=True,
                ))
                self.assertEqual(original_receipt, receipt_path.read_bytes())
                self.assertEqual(
                    original_receipt_sha256, broll_plan.sha256_file(receipt_path),
                )
                other_mode = "ordinary" if mode == "speaker-inset" else "speaker-inset"
                with self.assertRaisesRegex(ValueError, "already recorded"):
                    self.record_presentation(rebuilt, other_mode)

    def test_presentation_route_survives_multiple_revisions(self):
        presented = self.record_presentation(self.plan, "speaker-inset")

        def revise(plan, notes):
            request = self.review_for(
                plan,
                [{
                    "id": "shot", "decision": "select",
                    "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                    "segments": [{
                        "candidate_id": "asset",
                        "source_range": {"start_s": 0.0, "end_s": 2.0},
                        "program_range": {"start_s": 1.0, "end_s": 3.0},
                        "playback_rate": 1.0,
                    }],
                }],
                submission_intent="request_revision",
                explicit_user_action=True,
                revision_notes=notes,
            )
            request.pop("rationale")
            return broll_plan.rebuild_plan_from_revision(
                plan, request, self.timeline, self.transcript,
            )

        first = revise(presented, "Use the revised range.")
        second = revise(first, "Keep this route and candidate timing.")

        self.assertEqual("speaker-inset", second["presentation"]["mode"])
        self.assertEqual(
            first["presentation"]["carried_from_plan_sha256"],
            second["presentation"]["carried_from_plan_sha256"],
        )
        self.assertEqual([], broll_plan.presentation_errors(
            second, project_root=self.root, required=True,
        ))

    def test_carried_presentation_still_rejects_stale_artifact_bindings(self):
        presented = self.record_presentation(self.plan, "ordinary")
        request = self.review_for(
            presented,
            [{
                "id": "shot", "decision": "select",
                "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                "segments": [{
                    "candidate_id": "asset",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 1.0, "end_s": 3.0},
                    "playback_rate": 1.0,
                }],
            }],
            submission_intent="request_revision",
            explicit_user_action=True,
            revision_notes="Use the revised range.",
        )
        request.pop("rationale")
        rebuilt = broll_plan.rebuild_plan_from_revision(
            presented, request, self.timeline, self.transcript,
        )

        stale_candidate = copy.deepcopy(rebuilt)
        stale_candidate["shots"][0]["candidates"][0]["provenance"]["creator"] = "changed"
        self.assertTrue(any(
            "candidate_manifest_sha256" in error
            for error in broll_plan.presentation_errors(
                stale_candidate, project_root=self.root, required=True,
            )
        ))

        stale_video = copy.deepcopy(rebuilt)
        stale_video["input_hashes"]["review_video_sha256"] = "c" * 64
        self.assertTrue(any(
            "review_video_sha256" in error
            for error in broll_plan.presentation_errors(
                stale_video, project_root=self.root, required=True,
            )
        ))

        stale_style = copy.deepcopy(rebuilt)
        stale_style["speaker_inset_style"] = self._speaker_style()
        self.assertIn(
            "ordinary presentation must not enable speaker_inset_style",
            broll_plan.presentation_errors(
                stale_style, project_root=self.root, required=True,
            ),
        )

        invalid_carry = copy.deepcopy(rebuilt)
        invalid_carry["presentation"]["carried_from_plan_sha256"] = "invalid"
        self.assertIn(
            "presentation carried plan SHA-256 is invalid",
            broll_plan.presentation_errors(
                invalid_carry, project_root=self.root, required=True,
            ),
        )

        receipt_path = self.root / "work/b-roll/presentation-decision.json"
        original_receipt = receipt_path.read_bytes()
        receipt_path.write_bytes(b"tampered")
        self.assertIn(
            "presentation decision artifact is missing or stale",
            broll_plan.presentation_errors(
                rebuilt, project_root=self.root, required=True,
            ),
        )
        receipt_path.write_bytes(original_receipt)

    def test_presentation_receipt_requires_a_plan_hash_without_revision_carry(self):
        presented = self.record_presentation(self.plan, "ordinary")
        receipt_path = self.root / "work/b-roll/presentation-decision.json"
        receipt = projectlib.load_json(receipt_path)
        receipt.pop("plan_sha256")
        projectlib.write_json(receipt_path, receipt)
        presented["presentation"]["sha256"] = broll_plan.sha256_file(receipt_path)

        self.assertIn(
            "presentation decision plan_sha256 does not match",
            broll_plan.presentation_errors(
                presented, project_root=self.root, required=True,
            ),
        )

    def test_legacy_long_trim_exposes_requested_and_effective_ranges(self):
        review = self.review_for(self.plan, [{
            "id": "shot", "decision": "select", "candidate_id": "asset",
            "source_trim": {"start_s": 0, "end_s": 2},
        }])
        approved = broll_plan.apply_review(
            self.plan, review, mode="agent", actor="agent", rationale="Relevant footage.",
        )
        details = broll_plan.selection_details(
            approved["shots"][0], approved["shots"][0]["candidates"][0], self.timeline,
        )
        self.assertEqual("legacy", details["format"])
        self.assertEqual({"start_s": 0.0, "end_s": 2.0}, details["legacy_requested_source_range"])
        self.assertEqual({"start_s": 0.0, "end_s": 1.0}, details["segments"][0]["source_range"])

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
            "sequences": {"main": {"operations": sequence or ["cut", "color-grade", "captions", "content-cards"]}},
            "operations": [
                {"id": "understanding", "revision": 1}, {"id": "cut", "revision": 2},
                {"id": "color-grade", "revision": 3}, {"id": "captions", "revision": 4},
                {"id": "content-cards", "revision": 5},
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
        self.assertEqual(["cut", "color-grade", "b-roll", "captions", "content-cards"], result["sequences"]["main"]["operations"])
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
        project = self._registration_project(["cut", "unknown", "captions", "content-cards"])
        result = broll_plan.register_operation(project, self._registered_plan((2, 3), (4, 5), dependencies=["understanding", "cut"]))
        self.assertEqual(["cut", "b-roll", "unknown", "captions", "content-cards"], result["sequences"]["main"]["operations"])
        self.assertEqual(["cache/b-roll/normalized/broll-001.mp4", "cache/b-roll/normalized/broll-002.mp4"], [item["asset"] for item in next(item for item in result["operations"] if item["id"] == "b-roll")["render"]])
        for change in (("status", "selected"), ("normalized", {"path": "../bad.mp4", "sha256": "a" * 64}), ("review.status", "draft")):
            plan = self._registered_plan((2, 3))
            if change[0] == "review.status": plan["review"]["status"] = change[1]
            else: plan["shots"][0][change[0]] = change[1]
            with self.subTest(change=change):
                with self.assertRaises(ValueError): broll_plan.register_operation(project, plan)

    def test_register_operation_stays_before_downstream_overlays_without_upstream_anchors(self):
        project = self._registration_project(["captions", "content-cards", "graphic-motion"])
        result = broll_plan.register_operation(
            project,
            self._registered_plan((2, 3), dependencies=["understanding"]),
        )
        self.assertEqual(
            ["b-roll", "captions", "content-cards", "graphic-motion"],
            result["sequences"]["main"]["operations"],
        )

    def test_registered_speaker_inset_requires_composited_normalized_overlay(self):
        plan = self._registered_plan((2, 3))
        plan["speaker_inset_style"] = self._speaker_style()

        with self.assertRaisesRegex(
                ValueError, "speaker inset normalized composition is missing"):
            broll_plan._verified_overlays(plan)

    def test_enabled_speaker_style_all_skipped_remains_a_noop(self):
        plan = copy.deepcopy(self.plan)
        plan["speaker_inset_style"] = self._speaker_style()
        review = self.review_for(
            plan, [{"id": "shot", "decision": "skip"}],
            rationale="No useful footage.",
        )

        approved = broll_plan.apply_review(
            plan, review, mode="agent", actor="agent",
            rationale="No useful footage.", timeline=self.timeline,
        )

        self.assertEqual("skipped", approved["shots"][0]["status"])
        self.assertEqual([], broll_plan._verified_overlays(approved))

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
        self.plan = self.record_presentation(self.plan, "ordinary")
        self.real_probe_video = build_review_page._probe_video
        self.probe = mock.patch.object(build_review_page, "_probe_video", return_value=10.0)
        self.probe.start()
        self.addCleanup(self.probe.stop)

    @staticmethod
    def _frame(video, time_s, output):
        Image.new("RGB", (960, 540), "white").save(output, "JPEG")

    def _bind_composite_artifacts(self, plan):
        cache = self.root / "work/cache/b-roll/speaker-inset"
        cache.mkdir(parents=True)
        evidence = cache / "evidence.jpg"
        Image.new("RGB", (160, 90), "navy").save(evidence, "JPEG")
        base = cache / "base.mp4"
        context = cache / "context.mp4"
        base.write_bytes(b"base-preview")
        context.write_bytes(b"context-preview")
        alternates = {}
        for anchor in speaker_inset.PRESET_ANCHORS["corner-pip"]:
            path = cache / f"context-{anchor}.mp4"
            path.write_bytes(f"context-{anchor}".encode("ascii"))
            alternates[anchor] = {
                "path": path.relative_to(self.root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(path),
            }
        start_s = plan["shots"][0]["program_range"]["start_s"]
        analysis = {
            "schema_version": 1,
            "shots": [{
                "shot_id": "shot",
                "subshots": [{
                    "id": "shot-subshot-001",
                    "program_range": copy.deepcopy(plan["shots"][0]["program_range"]),
                    "evidence_points": [{
                        "frames": [{
                            "program_time_s": start_s,
                            "path": evidence.relative_to(self.root / "work").as_posix(),
                            "sha256": broll_plan.sha256_file(evidence),
                        }],
                    }],
                }],
            }],
        }
        analysis_path = self.root / "work/b-roll/speaker-inset-analysis.json"
        projectlib.write_json(analysis_path, analysis)
        agent_input = {
            "schema_version": 1, "actor": "Codex",
            "project_layout_strategy": SpeakerInsetTests._layout_strategy(),
            "shots": [{
                "shot_id": "shot",
                "layout_recommendation": SpeakerInsetTests._layout_recommendation(),
                "subshots": [{
                    "id": "shot-subshot-001", "speaker_status": "confirmed",
                    "display_mode": "enabled", "anchor": "top-left",
                    "rationale": "One current speaker is visible.",
                    "keyframes": [{
                        "program_time_s": start_s,
                        "roi": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.6},
                    }],
                }],
            }],
        }
        agent_path = self.root / "work/b-roll/speaker-inset-agent-input.json"
        projectlib.write_json(agent_path, agent_input)
        preview = {
            "schema_version": 1,
            "shots": [{
                "shot_id": "shot",
                "base_broll": {
                    "path": base.relative_to(self.root / "work").as_posix(),
                    "sha256": broll_plan.sha256_file(base),
                },
                "preview": {
                    "path": context.relative_to(self.root / "work").as_posix(),
                    "sha256": broll_plan.sha256_file(context),
                },
                "anchor_previews": alternates,
            }],
        }
        preview_path = self.root / "work/b-roll/speaker-inset-preview.json"
        projectlib.write_json(preview_path, preview)
        clearance = {
            "schema_version": 1, "actor": "Codex",
            "shots": [{
                "shot_id": "shot",
                "continuity": {
                    "risk": "none",
                    "decision": "continuous",
                    "rationale": "The inset remains enabled for the complete shot.",
                },
                "subshots": [{
                    "id": "shot-subshot-001", "display_mode": "enabled",
                    "anchor": "top-left", "clearance_status": "pass",
                    "checked_anchors": ["top-left"],
                    "subject_legibility": "pass",
                    "legibility_rationale": "The speaker remains readable at final size.",
                    "pixel_budget": {
                        "pixel_risk": "medium", "max_scale_factor": 1.75,
                        "checkpoints": [{
                            "role": "entry", "program_time_s": start_s,
                            "input_crop_px": {"width": 200, "height": 300},
                            "output_content_px": {"width": 350, "height": 525},
                            "scale_factor": 1.75,
                        }],
                    },
                    "legibility_checks": [{
                        "role": "entry", "program_time_s": start_s,
                        "preview_sha256": "c" * 64,
                        "observation": "The complete speaker silhouette is readable.",
                    }],
                    "rationale": "The inset does not cover the B-roll focal action.",
                }],
            }],
        }
        clearance_path = self.root / "work/b-roll/speaker-inset-clearance.json"
        projectlib.write_json(clearance_path, clearance)
        plan["speaker_inset"] = {
            "analysis": {
                "path": "b-roll/speaker-inset-analysis.json",
                "sha256": broll_plan.sha256_file(analysis_path),
            },
            "agent_input": {
                "path": "b-roll/speaker-inset-agent-input.json",
                "sha256": broll_plan.sha256_file(agent_path),
            },
            "preview": {
                "path": "b-roll/speaker-inset-preview.json",
                "sha256": broll_plan.sha256_file(preview_path),
            },
            "clearance": {
                "path": "b-roll/speaker-inset-clearance.json",
                "sha256": broll_plan.sha256_file(clearance_path),
            },
        }

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

    def test_build_review_page_requires_chat_presentation_decision(self):
        plan = copy.deepcopy(self.plan)
        plan.pop("presentation")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            with self.assertRaisesRegex(ValueError, "agent-chat presentation decision is required"):
                build_review_page.build_review_page(
                    plan, self.timeline, self.transcript, self.video,
                    self.review_dir, project_root=self.root,
                    review_id="123e4567-e89b-12d3-a456-426614174010",
                )

    def test_build_review_page_reuses_the_original_route_after_revision(self):
        for index, mode in enumerate(("ordinary", "speaker-inset"), 11):
            with self.subTest(mode=mode):
                plan = copy.deepcopy(self.plan)
                if mode == "speaker-inset":
                    plan.pop("presentation")
                    plan = self.record_presentation(plan, mode)
                request = self.review_for(
                    plan,
                    [{
                        "id": "shot", "decision": "select",
                        "requested_program_range": {"start_s": 1.0, "end_s": 3.0},
                        "segments": [{
                            "candidate_id": "asset",
                            "source_range": {"start_s": 0.0, "end_s": 2.0},
                            "program_range": {"start_s": 1.0, "end_s": 3.0},
                            "playback_rate": 1.0,
                        }],
                    }],
                    submission_intent="request_revision",
                    explicit_user_action=True,
                    revision_notes="Use the revised range.",
                )
                request.pop("rationale")
                rebuilt = broll_plan.rebuild_plan_from_revision(
                    plan, request, self.timeline, self.transcript,
                )

                review_id = f"123e4567-e89b-12d3-a456-4266141740{index}"
                with mock.patch.object(
                        build_review_page, "_extract_frame", side_effect=self._frame):
                    result = build_review_page.build_review_page(
                        rebuilt, self.timeline, self.transcript, self.video,
                        self.review_dir, project_root=self.root, review_id=review_id,
                    )
                payload = json.loads(base64.b64decode(
                    build_review_page.PAYLOAD_RE.search(
                        result["page"].read_text(encoding="utf-8")
                    ).group(1)
                ))
                self.assertEqual(
                    "selection" if mode == "speaker-inset" else "standard",
                    payload["review_mode"],
                )

    def test_approve_selection_carries_presentation_route_into_composite_review(self):
        plan = copy.deepcopy(self.plan)
        plan.pop("presentation")
        plan["shots"][0]["review_default"] = {
            "decision": "select",
            "segments": [{
                "candidate_id": "asset",
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 1.0, "end_s": 2.0},
                "playback_rate": 1.0,
            }],
        }
        plan = self.record_presentation(plan, "speaker-inset")
        presentation_path = self.root / "work/b-roll/presentation-decision.json"
        original_presentation = presentation_path.read_bytes()
        original_presentation_sha256 = broll_plan.sha256_file(presentation_path)
        original_presentation_plan_sha256 = projectlib.load_json(
            presentation_path
        )["plan_sha256"]

        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            selection_result = build_review_page.build_review_page(
                plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
                review_id="123e4567-e89b-12d3-a456-426614174030",
            )
        selection_payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(
                selection_result["page"].read_text(encoding="utf-8")
            ).group(1)
        ))
        edited_range = {"start_s": 1.0, "end_s": 3.0}
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": 2.0},
            "program_range": copy.deepcopy(edited_range),
            "playback_rate": 1.0,
        }
        selection = {
            "review_id": selection_payload["review_id"],
            "submission_intent": "approve_selection",
            "approval_scope": "b-roll-selection",
            "explicit_user_action": True,
            "revision_notes": "",
            "plan_sha256": selection_payload["plan_sha256"],
            "candidate_manifest_sha256": selection_payload["candidate_manifest_sha256"],
            "review_video_sha256": selection_payload["review_video_sha256"],
            "timeline_fps": copy.deepcopy(selection_payload["timeline"]["fps"]),
            "timestamp": "2026-08-17T12:00:00Z",
            "rationale": broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            "rationale_source": "review_ui_explicit_action",
            "shots": [{
                "id": "shot", "decision": "select",
                "program_range": copy.deepcopy(edited_range),
                "segments": [segment],
            }],
        }
        prepared = broll_plan.approve_selection(
            plan, selection, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_SELECTION_APPROVAL_RATIONALE,
            project_root=self.root, timeline=self.timeline,
            transcript=self.transcript,
        )
        self.assertEqual(original_presentation, presentation_path.read_bytes())
        self.assertEqual(
            original_presentation_sha256, broll_plan.sha256_file(presentation_path),
        )
        self._bind_composite_artifacts(prepared)

        with mock.patch.object(broll_plan, "validate_plan", return_value=[]), mock.patch.object(
                build_review_page, "_extract_frame") as extract:
            result = build_review_page.build_review_page(
                prepared, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
                review_id="123e4567-e89b-12d3-a456-426614174031",
            )
        extract.assert_not_called()
        html = result["page"].read_text(encoding="utf-8")
        payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(html).group(1)
        ))
        self.assertEqual("composite_pending", prepared["shots"][0]["status"])
        self.assertNotIn("review_default", prepared["shots"][0])
        self.assertEqual(
            original_presentation_plan_sha256,
            prepared["presentation"]["carried_from_plan_sha256"],
        )
        self.assertEqual([], broll_plan.presentation_errors(
            prepared, project_root=self.root, required=True,
        ))
        self.assertEqual("composite", payload["review_mode"])
        self.assertEqual("approve", payload["approval_intent"])
        self.assertEqual("speaker-inset-composite", payload["approval_scope"])
        composite_receipt_source = re.search(
            r"function buildCompositeReceipt\(commit,action\)\{(.+?)\ncopyButton",
            html,
        ).group(1)
        self.assertNotIn("shots:", composite_receipt_source)

    def test_review_page_switches_selection_intent_and_publishes_composite_assets(self):
        selection_plan = copy.deepcopy(self.plan)
        selection_plan.pop("presentation")
        selection_plan["speaker_inset_style"] = BrollPlanTests._speaker_style()
        selection_plan = self.record_presentation(selection_plan, "speaker-inset")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            selection_result = build_review_page.build_review_page(
                selection_plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
                review_id="123e4567-e89b-12d3-a456-426614174020",
            )
        selection_payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(
                selection_result["page"].read_text(encoding="utf-8")
            ).group(1)
        ))
        self.assertEqual("selection", selection_payload["review_mode"])
        self.assertIn("approval_intent", selection_payload)
        self.assertEqual("approve_selection", selection_payload["approval_intent"])
        self.assertEqual("b-roll-selection", selection_payload["approval_scope"])

        plan = copy.deepcopy(selection_plan)
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        plan["shots"][0].update({
            "selected": {"segments": [segment]},
            "status": "composite_pending",
        })
        plan["selection"] = {
            "status": "approved", "submission_intent": "approve_selection",
            "approval_scope": "b-roll-selection", "consumed": True,
            "path": "b-roll/broll-selection.json", "sha256": "9" * 64,
            "style_sha256": broll_plan.canonical_sha256(plan["speaker_inset_style"]),
        }
        self._bind_composite_artifacts(plan)
        with mock.patch.object(broll_plan, "validate_plan", return_value=[]), mock.patch.object(
                build_review_page, "_extract_frame") as extract:
            result = build_review_page.build_review_page(
                plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
                review_id="123e4567-e89b-12d3-a456-426614174021",
            )
        extract.assert_not_called()
        html = result["page"].read_text(encoding="utf-8")
        payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(html).group(1)
        ))
        self.assertEqual("composite", payload["review_mode"])
        self.assertIn("approval_scope", payload)
        self.assertEqual("speaker-inset-composite", payload["approval_scope"])
        self.assertEqual({"segments": [segment]}, payload["shots"][0]["locked_selection"])
        self.assertEqual("pass", payload["shots"][0]["subshots"][0]["clearance_status"])
        self.assertEqual("pass", payload["shots"][0]["subshots"][0]["subject_legibility"])
        self.assertEqual(
            "medium", payload["shots"][0]["subshots"][0]["pixel_budget"]["pixel_risk"],
        )
        self.assertEqual(
            "entry", payload["shots"][0]["subshots"][0]["legibility_checks"][0]["role"],
        )
        self.assertEqual(
            "The speaker remains readable at final size.",
            payload["shots"][0]["subshots"][0]["legibility_rationale"],
        )
        self.assertEqual("continuous", payload["shots"][0]["continuity"]["decision"])
        self.assertEqual(
            SpeakerInsetTests._layout_strategy(),
            payload["speaker_layout_strategy"],
        )
        self.assertEqual(
            SpeakerInsetTests._layout_recommendation(),
            payload["shots"][0]["layout_recommendation"],
        )
        self.assertEqual(0.39, payload["speaker_style"]["width_ratio"])
        self.assertNotIn("speaker_size_review", payload)
        self.assertEqual(
            plan["speaker_inset"]["clearance"]["sha256"],
            payload["speaker_bindings"]["clearance_sha256"],
        )
        for key in ("base_broll", "preview"):
            self.assertTrue((result["page"].parent / payload["shots"][0][key]["path"]).is_file())
        self.assertTrue((
            result["page"].parent
            / payload["shots"][0]["subshots"][0]["evidence_frames"][0]["path"]
        ).is_file())
        for text in (
                "approve_selection", "Approve B-roll selection",
                "value.review_stage='composite'", "speaker_bindings",
                "Project layout strategy", "Preset assessments", "subject_legibility",
                "Pixel risk", "Legibility checks", "function legibilityMarkup",
                "replace('_','-')", "continuity",
                "Copy", "Download JSON",
                "<details class=\"technical\"><summary>Locked B-roll</summary>"):
            self.assertIn(text, html)
        self.assertNotIn("function lockedEntry", html)
        self.assertNotIn("shots:shotEntries", html)
        self.assertNotIn("<h3>Pure B-roll source</h3>", html)
        self.assertNotIn(
            "<details open class=\"technical\"><summary>Locked B-roll</summary>", html,
        )
        self.assertNotIn("Project speaker size", html)
        self.assertNotIn("size-candidates", html)

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
        plan.pop("presentation")
        plan["shots"][0]["id"] = "shot-cafe\u0301"
        plan["shots"][0]["queries"] = ["usine animee", "工場の映像"]
        plan["shots"][0]["candidates"][0]["id"] = "候補"
        plan["shots"][0]["candidates"][0]["provenance"]["creator"] = "Jose Alvarez - 東京"
        plan = self.record_presentation(plan, "ordinary")
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
        cases = [
            (outside, self.plan, 10.0, "inside project_root"),
            (self.video, self.plan, 9.9, "duration"),
            (self.video, None, 10.0, "review video SHA-256"),
        ]
        for video, plan, duration, message in cases:
            if message == "review video SHA-256":
                plan = copy.deepcopy(self.plan)
                plan.pop("presentation")
                plan["input_hashes"]["review_video_sha256"] = "0" * 64
                plan = self.record_presentation(plan, "ordinary")
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
            plan.pop("presentation")
            for key in removed:
                plan["shots"][0]["candidates"][0].pop(key)
            plan["shots"][0]["candidates"][0].update(variant)
            plan = self.record_presentation(plan, "ordinary")
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

    def test_payload_exposes_transcript_mapping_bounds_fps_and_single_segment_defaults(self):
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(
                self.plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
            )
        payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(
                result["page"].read_text(encoding="utf-8")
            ).group(1)
        ))
        shot = payload["shots"][0]

        self.assertEqual({"num": 30, "den": 1}, payload["timeline"]["fps"])
        self.assertEqual(10.0, payload["timeline"]["program_duration_s"])
        self.assertEqual({"start_s": 1.0, "end_s": 2.0}, shot["original_program_range"])
        self.assertEqual(0.0, shot["allowed_program_range"]["start_s"]["min"])
        self.assertEqual(3.0, shot["allowed_program_range"]["start_s"]["max"])
        self.assertEqual(4.0, shot["allowed_program_range"]["end_s"]["max"])
        self.assertEqual(["one"], shot["clip_ids"])
        self.assertEqual(["factory"], [word["word"] for word in shot["transcript"]["inside"]])
        self.assertEqual(["factory", "process", "output"], [
            word["word"] for word in shot["transcript"]["context"]
        ])
        for word in shot["transcript"]["context"]:
            self.assertIn("program_range", word)
            self.assertIn("source_range", word)
            self.assertEqual("one", word["clip_id"])
        default = shot["candidates"][0]["default_segment"]
        self.assertEqual("asset", default["candidate_id"])
        self.assertEqual({"start_s": 0.0, "end_s": 1.0}, default["source_range"])
        self.assertEqual({"start_s": 1.0, "end_s": 2.0}, default["program_range"])
        self.assertEqual(1.0, default["playback_rate"])

    def test_payload_exposes_frame_first_defaults_and_prefills_multiple_segments(self):
        candidates = []
        base = self.plan["shots"][0]["candidates"][0]
        for index in range(3):
            candidate = copy.deepcopy(base)
            candidate["id"] = f"asset-{index + 1}"
            candidates.append(candidate)
        self.plan["shots"][0]["candidates"] = candidates
        self.plan["shots"][0]["review_default"] = {
            "decision": "select",
            "segments": [
                {
                    "candidate_id": "asset-1",
                    "source_range": {"start_s": 0.0, "end_s": 0.5},
                    "program_range": {"start_s": 1.0, "end_s": 1.5},
                    "playback_rate": 1.0,
                },
                {
                    "candidate_id": "asset-2",
                    "source_range": {"start_s": 0.0, "end_s": 1.0},
                    "program_range": {"start_s": 1.5, "end_s": 2.0},
                    "playback_rate": 2.0,
                },
            ],
        }
        shots, _, _ = build_review_page._payload(
            self.plan, self.timeline, self.transcript, self.root,
            self.review_dir / "assets",
        )
        shot = shots[0]
        self.assertEqual(30, shot["total_program_frames"])
        self.assertAlmostEqual(1 / 30, shot["frame_duration_s"])
        self.assertEqual([15, 15], shot["default_allocations"]["2"])
        self.assertEqual([10, 10, 10], shot["default_allocations"]["3"])
        self.assertEqual(
            self.plan["shots"][0]["review_default"], shot["review_default"],
        )

    def test_template_supports_multiselect_order_speed_timeline_and_explicit_fit(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        for text in (
            'type="checkbox"',
            'class="segments-list"',
            'move-up',
            'move-down',
            'class="playback-rate"',
            '<option value="0.5"',
            '<option value="1.5"',
            '<option value="2"',
            'class="timeline-bar"',
            'Fit to A-roll',
            'function equalAllocation(',
            'function moveBoundary(',
            'function reorderSegment(',
            'function fitToAroll(',
            'entry.segments=',
            'Fit applied: segment allocation now matches the A-roll duration.',
            'Unable to fit:',
        ):
            self.assertIn(text, template)
        self.assertNotIn(
            'type="radio" name="${esc(shot.id)}" value="${esc(candidate.id)}"',
            template,
        )

    def test_template_uses_coarse_frame_aligned_segment_timing(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("const SEGMENT_COARSE_STEP_S=0.1;", template)
        self.assertIn(
            "const coarseStepFrames=Math.max(1,Math.round(SEGMENT_COARSE_STEP_S/frameDuration));",
            template,
        )
        self.assertIn(
            "moveBoundary(shot,state,Number(button.dataset.index),Number(button.dataset.delta)*(event.altKey?1:coarseStepFrames))",
            template,
        )
        self.assertIn('step="0.1"', template)
        self.assertIn('class="trim-end" type="number"', template)
        self.assertIn('class="trim-end" type="number" min="0" readonly', template)
        self.assertNotIn("else if(target.matches('.trim-end'))segment.source_end=Number(target.value)", template)
        self.assertIn(
            "segment.source_start+segment.frames*frameDuration*segment.playback_rate",
            template,
        )
        self.assertIn("selected.forEach(autoSourceEnd)", template)
        self.assertIn("state.fitValid=true;state.fitMessage='';renderShotState(shot)", template)

    def test_template_reports_structured_actionable_segment_errors(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        for text in (
            "reason:'source_too_short'",
            "requiredSourceS",
            "availableSourceS",
            "shortageS",
            "latestLegalStartS",
            "candidateDurationS",
            "feasibleRates",
            "Source footage is too short",
            "candidate ends at",
            "Move the clip start earlier",
            "choose a feasible playback rate",
            "shorten the segment",
            "select another candidate",
            'aria-invalid="true"',
            'aria-describedby="${id}"',
        ):
            self.assertIn(text, template)
        self.assertIn("function segmentStatus(", template)
        self.assertIn("function segmentStatusText(", template)
        self.assertIn(
            "startInvalid=!status.valid&&(status.reason==='invalid_trim'||status.reason==='source_too_short')",
            template,
        )
        self.assertIn("rateInvalid=status.reason==='source_too_short'", template)
        self.assertIn(
            "boundaryInvalid=index&&(!status.valid||!previousStatus.valid)",
            template,
        )
        self.assertIn(
            "previousStatus=index?segmentStatus(shot,segments[index-1]):null",
            template,
        )
        self.assertIn(
            "boundaryStatusId=status.valid&&previousStatus&&!previousStatus.valid?`segment-status-${esc(shot.id)}-${index-1}`:statusId",
            template,
        )
        self.assertIn(
            "class=\"boundary-adjust${boundaryInvalid?' timing-invalid':''}\"${assist(boundaryInvalid,boundaryStatusId)}",
            template,
        )
        self.assertIn("Number.isFinite(status.latestLegalStartS)", template)
        self.assertIn("segment.source_start=target.valueAsNumber", template)
        self.assertIn(
            "const invalidTrim=state.selected.map(segment=>segmentStatus(shot,segment)).find(status=>status.reason==='invalid_trim')",
            template,
        )
        self.assertNotIn("reason_code", template.split("function buildReviewReceipt", 1)[1])

    def test_template_uses_stable_candidate_tones_for_reordered_segments(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        for text in (
            "body{margin:0;background:#1a1a1e;color:#e8e8ea",
            "const SEGMENT_TONES=['orange','sand','stone'];",
            "function candidateTone(shot,candidateId)",
            'class="timeline-segment segment-tone-${candidateTone(shot,segment.candidate_id)}"',
            "${index+1}. ${esc(segment.candidate_id)}",
            ".segment-tone-orange{background:#c15f3c",
            ".segment-tone-sand{background:#d4a779",
            ".segment-tone-stone{background:#7e786d",
        ):
            self.assertIn(text, template)
        self.assertNotIn(".timeline-segment:nth-child", template)

    def test_rebuilt_review_payload_prefills_exact_review_default(self):
        plan = copy.deepcopy(self.plan)
        plan.pop("presentation")
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.5, "end_s": 1.5},
            "program_range": {"start_s": 1.0, "end_s": 2.0},
            "playback_rate": 1.0,
        }
        plan["shots"][0]["review_default"] = {
            "decision": "select", "segments": [copy.deepcopy(segment)],
        }
        plan = self.record_presentation(plan, "ordinary")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            result = build_review_page.build_review_page(
                plan, self.timeline, self.transcript, self.video, self.review_dir,
                project_root=self.root,
            )
        payload = json.loads(base64.b64decode(
            build_review_page.PAYLOAD_RE.search(
                result["page"].read_text(encoding="utf-8")
            ).group(1)
        ))
        self.assertEqual(segment, payload["shots"][0]["review_default"]["segments"][0])

    def test_template_allows_structured_edits_and_requires_revision_notes(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn('id="modification-notes"', template)
        self.assertNotIn('id="rationale"', template)
        self.assertIn(
            "Approve: leave blank. Request changes: required.",
            template,
        )
        for text in (
            "submission_intent", "request_revision", "revision_notes",
            "requested_program_range", "playback_rate:1.0", "Fit to A-roll",
            "Insert start", "Insert end", "Transcript", "A-roll source mapping",
            "Explicit user action approved the exact configuration shown in this review.",
            "function syncIntent(){if(revisionNotes.value.trim())",
            "Modification notes are required for Request changes.",
        ):
            self.assertIn(text, template)
        self.assertNotIn("programRangeChanged", template)
        self.assertNotIn("segmentChangedFromDefault", template)
        self.assertNotIn("forcedRevision", template)
        self.assertIn("revisionNotes.value.trim()", template)
        self.assertIn("source_range", template)
        self.assertIn("remaining", template)
        self.assertIn("overflow", template)

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

    def test_stale_presentation_decision_rolls_back_publication_and_preserves_alias(self):
        review_id = "123e4567-e89b-12d3-a456-426614174007"
        plan = copy.deepcopy(self.plan)
        plan["shots"][0]["candidates"][0]["provenance"]["metadata"] = {"score": float("nan")}
        self.review_dir.mkdir(parents=True)
        alias = self.review_dir / "b-roll-review.html"
        alias.write_bytes(b"prior alias")
        with mock.patch.object(build_review_page, "_extract_frame", side_effect=self._frame):
            with self.assertRaisesRegex(ValueError, "presentation decision"):
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
        self.assertIn("Stock search queries", template)
        self.assertIn("shot.queries", template)
        self.assertIn("data.pre_skipped_ids.map", template)
        self.assertIn("timestamp:new Date().toISOString()", template)

    def test_template_prioritizes_readable_review_content(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        for text in (
            "function transcriptMarkup(",
            "Number(value).toFixed(2)",
            "const PROGRAM_STEP=0.5",
            'class="timing-adjust"',
            'data-value="${shot.program_range.start_s}"',
            "B-roll appears on A-roll:",
            "Why B-roll here",
            "Desired B-roll",
            "Stock search queries",
            "Technical provenance",
            "View source",
            "View terms",
            "B-roll clip start",
            "B-roll clip end",
        ):
            self.assertIn(text, template)
        self.assertNotIn("function wordMarkup(", template)
        self.assertNotIn('class="word-time"', template)
        self.assertNotIn("Context:", template)
        self.assertNotIn("<p class=\"meta\">${esc(JSON.stringify(candidate.provenance))}</p>", template)

    def test_template_summarizes_decisions_and_uses_one_receipt_for_copy_and_download(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn('id="copy"', template)
        self.assertIn('id="download"', template)
        self.assertIn('>Copy</button>', template)
        self.assertIn('>Download JSON</button>', template)
        self.assertNotIn("Export review", template)
        self.assertIn('id="decision-summary"', template)
        self.assertIn('id="receipt"', template)
        self.assertIn("readonly", template)
        self.assertEqual(1, template.count("function buildReviewReceipt("))
        self.assertGreaterEqual(template.count("buildReviewReceipt(true,"), 2)
        self.assertIn("navigator.clipboard.writeText", template)
        self.assertIn("receipt.select()", template)
        self.assertNotIn("value.duplicate_notes", template)

    def test_template_preserves_unchanged_program_timing_and_snaps_structured_edits(self):
        template = build_review_page.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("rangesEqual(raw,shot.original_program_range)?raw", template)
        self.assertIn("{start_s:snap(raw.start_s),end_s:snap(raw.end_s)}", template)
        self.assertNotIn("programRangeChanged", template)

    def test_mixed_plan_exports_pre_skipped_shot_exactly_once(self):
        plan = copy.deepcopy(self.plan)
        plan.pop("presentation")
        skipped = copy.deepcopy(plan["shots"][0])
        skipped.update({"id": "already-skipped", "program_range": {"start_s": 3.0, "end_s": 4.0}, "source_ranges": [{"clip_id": "one", "start_s": 3.0, "end_s": 4.0}], "transcript_evidence": {"words": [self.mapped_words[2]]}, "candidates": [], "selected": None, "status": "skipped"})
        plan["shots"].append(skipped)
        plan = self.record_presentation(plan, "ordinary")
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
        plan.pop("presentation")
        plan["shots"][0]["id"] = 'shot" onmouseover="evil'
        plan["shots"][0]["candidates"][0]["id"] = "asset' onerror='evil"
        plan = self.record_presentation(plan, "ordinary")
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


class SpeakerInsetTests(_BrollFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.review_video = self.root / "final/current.mp4"
        self.review_video.parent.mkdir(parents=True, exist_ok=True)
        self.review_video.write_bytes(b"review-video")
        self.plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(
            self.review_video
        )
        self.plan["speaker_inset_style"] = BrollPlanTests._speaker_style()
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        selection = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
                "segments": [segment],
            }],
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            submission_intent="prepare_composite",
            explicit_user_action=True,
            revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        self.prepared = broll_plan.prepare_composite(
            self.plan, selection,
            mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            project_root=self.root, timeline=self.timeline,
        )

    @staticmethod
    def _frame(video, time_s, output):
        Image.new("RGB", (480, 270), (40, 60, 80)).save(output, "JPEG")

    @staticmethod
    def _layout_recommendation(preset="corner-pip", anchor="top-left", **changes):
        recommendation = {
            "preset": preset,
            "anchor": anchor,
            "confidence": "high",
            "alternate": None,
            "rationale": "The selected B-roll remains readable with this placement.",
            "preset_assessments": {
                "focused-panel": "warn",
                "full-bleed-wash": "fail",
                "corner-pip": "pass",
            },
        }
        recommendation.update(changes)
        return recommendation

    @staticmethod
    def _layout_strategy(primary="corner-pip", used=None):
        return {
            "primary_preset": primary,
            "used_presets": used or [primary],
            "rationale": "The selected shots favor one consistent project layout.",
        }

    def _clearance_contract_fixture(self):
        style = {
            **BrollPlanTests._speaker_style(),
            "width_ratio": 0.30,
            "aspect_ratio": 1.0,
            "border": {"width_px": 0, "color": "#9E9E9E"},
        }
        hashes = {
            "analysis_sha256": "a" * 64,
            "agent_input_sha256": "b" * 64,
            "preview_sha256": "c" * 64,
            "selection_sha256": "d" * 64,
            "style_sha256": broll_plan.canonical_sha256(style),
            "review_video_sha256": "e" * 64,
        }
        plan = {
            "speaker_inset_style": style,
            "speaker_inset": {
                "analysis": {"sha256": hashes["analysis_sha256"]},
                "agent_input": {"sha256": hashes["agent_input_sha256"]},
                "preview": {"sha256": hashes["preview_sha256"]},
            },
            "selection": {"sha256": hashes["selection_sha256"]},
            "input_hashes": {
                "review_video_sha256": hashes["review_video_sha256"],
            },
        }
        analysis = {
            "timeline_fps": {"num": 10, "den": 1},
            "review_video_probe": {"width": 1000, "height": 1000},
            "shots": [{
                "shot_id": "shot",
                "subshots": [{
                    "id": "subshot",
                    "program_range": {"start_s": 1.0, "end_s": 2.0},
                }],
            }],
        }
        roi = {"x": 0.0, "y": 0.0, "width": 0.20, "height": 0.20}
        agent_input = {
            "shots": [{
                "shot_id": "shot",
                "layout_recommendation": {
                    "preset": "corner-pip", "anchor": "top-left",
                },
                "subshots": [{
                    "id": "subshot",
                    "speaker_status": "confirmed",
                    "display_mode": "enabled",
                    "anchor": "top-left",
                    "keyframes": [
                        {"program_time_s": 1.0, "roi": copy.deepcopy(roi)},
                        {"program_time_s": 1.9, "roi": copy.deepcopy(roi)},
                    ],
                }],
            }],
        }
        preview = {
            "analysis_sha256": hashes["analysis_sha256"],
            "agent_input_sha256": hashes["agent_input_sha256"],
            "shots": [{
                "shot_id": "shot",
                "preview": {
                    "path": "cache/b-roll/context.mp4",
                    "sha256": "f" * 64,
                    "probe": {"width": 1000, "height": 1000},
                },
                "anchor_previews": {
                    anchor: {"path": f"cache/b-roll/{anchor}.mp4", "sha256": "f" * 64}
                    for anchor in speaker_inset.PRESET_ANCHORS["corner-pip"]
                },
            }],
        }
        checkpoint_facts = [
            {
                "role": role,
                "program_time_s": time_s,
                "input_crop_px": {"width": 200, "height": 200},
                "output_content_px": {"width": 300, "height": 300},
                "scale_factor": 1.5,
            }
            for role, time_s in (("entry", 1.0), ("middle", 1.5), ("exit", 1.9))
        ]
        pixel_budget = {
            **hashes,
            "source_frame_px": {"width": 1000, "height": 1000},
            "output_inset_px": {"width": 300, "height": 300},
            "checkpoints": checkpoint_facts,
            "max_scale_factor": 1.5,
            "pixel_risk": "low",
        }
        legibility_checks = [
            {
                "role": role,
                "program_time_s": time_s,
                "preview_sha256": hashes["preview_sha256"],
                "observation": "The complete speaker silhouette remains readable at final size.",
            }
            for role, time_s in (("entry", 1.0), ("middle", 1.5), ("exit", 1.9))
        ]
        legibility_checks.append({
            "role": "motion_risk",
            "status": "not_applicable",
            "preview_sha256": hashes["preview_sha256"],
            "reason": "No additional motion-risk frame exists in this stable subshot.",
        })
        clearance = {
            "schema_version": 1,
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-14T12:00:00+08:00",
            "rationale": "Checked the exact final-size speaker inset.",
            **{key: hashes[key] for key in (
                "analysis_sha256", "agent_input_sha256", "preview_sha256",
                "selection_sha256", "style_sha256",
            )},
            "shots": [{
                "shot_id": "shot",
                "continuity": {
                    "risk": "none",
                    "decision": "continuous",
                    "rationale": "The speaker inset remains continuous.",
                },
                "subshots": [{
                    "id": "subshot",
                    "display_mode": "enabled",
                    "anchor": "top-left",
                    "clearance_status": "pass",
                    "checked_anchors": ["top-left"],
                    "subject_legibility": "pass",
                    "legibility_rationale": "The speaker is immediately recognizable at final size.",
                    "pixel_budget": pixel_budget,
                    "legibility_checks": legibility_checks,
                    "rationale": "The inset preserves the B-roll focal action.",
                }],
            }],
        }
        return plan, analysis, agent_input, preview, clearance

    def test_confirmed_agent_input_cannot_skip_exact_preview_with_pure_broll(self):
        plan, analysis, agent_input, _, _ = self._clearance_contract_fixture()
        agent_input["schema_version"] = 1
        agent_input.update({
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-14T12:00:00+08:00",
            "rationale": "Reviewed the temporal evidence.",
            "project_layout_strategy": self._layout_strategy(),
            "analysis_sha256": plan["speaker_inset"]["analysis"]["sha256"],
            "selection_sha256": plan["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(plan["speaker_inset_style"]),
            "review_video_sha256": plan["input_hashes"]["review_video_sha256"],
        })
        recommendation = agent_input["shots"][0]["layout_recommendation"]
        recommendation.update(self._layout_recommendation())
        analysis["shots"][0]["subshots"][0]["evidence_points"] = []

        premature = copy.deepcopy(agent_input)
        premature_subshot = premature["shots"][0]["subshots"][0]
        premature_subshot.update({
            "display_mode": "pure_broll", "anchor": None, "keyframes": [],
        })
        errors = speaker_inset.agent_input_errors(
            premature, analysis, plan, {"fps": analysis["timeline_fps"]},
        )
        self.assertTrue(any("confirmed speaker must be enabled" in error for error in errors))

    def test_clearance_legibility_state_matrix_is_fail_closed(self):
        cases = (
            ("confirmed", "enabled", "pass", "pass", True, None),
            ("confirmed", "pure_broll", "fail", "subject_illegible", True, None),
            ("confirmed", "pure_broll", "not_applicable", "no_safe_position", True, None),
            ("ambiguous", "pure_broll", "not_applicable", "pass", True, None),
            ("confirmed", "enabled", "fail", "pass", False, "enabled speaker must pass subject legibility"),
            ("confirmed", "pure_broll", "fail", "pass", False, "subject_legibility fail requires subject_illegible"),
            ("confirmed", "pure_broll", "fail", "no_safe_position", False, "subject_legibility fail requires subject_illegible"),
            ("ambiguous", "enabled", "pass", "pass", False, "non-confirmed speaker clearance must remain pure_broll"),
        )
        for speaker_status, display_mode, legibility, status, valid, expected in cases:
            with self.subTest(
                    speaker_status=speaker_status, display_mode=display_mode,
                    legibility=legibility, status=status):
                plan, analysis, agent_input, preview, clearance = (
                    self._clearance_contract_fixture()
                )
                agent_subshot = agent_input["shots"][0]["subshots"][0]
                item = clearance["shots"][0]["subshots"][0]
                agent_subshot["speaker_status"] = speaker_status
                item.update({
                    "display_mode": display_mode,
                    "anchor": "top-left" if display_mode == "enabled" else None,
                    "clearance_status": status,
                    "subject_legibility": legibility,
                    "checked_anchors": (
                        ["top-left"] if display_mode == "enabled"
                        or status == "subject_illegible"
                        else list(speaker_inset.PRESET_ANCHORS["corner-pip"])
                        if status == "no_safe_position" else []
                    ),
                })
                if speaker_status != "confirmed":
                    agent_subshot.update({
                        "display_mode": "pure_broll", "anchor": None, "keyframes": [],
                    })
                    item.pop("pixel_budget")
                    item.pop("legibility_checks")
                    item.pop("legibility_rationale")
                if display_mode == "pure_broll":
                    clearance["shots"][0]["continuity"].update({
                        "risk": "none", "decision": "all_pure_broll",
                    })
                errors = speaker_inset.clearance_errors(
                    clearance, preview, agent_input, analysis, plan,
                )
                if valid:
                    self.assertEqual([], errors)
                else:
                    self.assertTrue(
                        any(expected in error for error in errors), errors,
                    )

    def test_pixel_risk_boundaries_are_advisory(self):
        plan, analysis, agent_input, preview, _ = self._clearance_contract_fixture()
        helper_parameters = inspect.signature(
            speaker_inset.build_pixel_budget
        ).parameters
        self.assertNotIn("display_mode", helper_parameters)
        cases = ((200, "low"), (199, "medium"), (100, "medium"), (99, "high"))
        for source_crop_px, expected_risk in cases:
            with self.subTest(source_crop_px=source_crop_px):
                ratio = source_crop_px / analysis["review_video_probe"]["width"]
                for keyframe in agent_input["shots"][0]["subshots"][0]["keyframes"]:
                    keyframe["roi"].update({"width": ratio, "height": ratio})
                budget = speaker_inset.build_pixel_budget(
                    plan, analysis, agent_input, preview, "shot", "subshot",
                )
                self.assertEqual(expected_risk, budget["pixel_risk"])
                self.assertAlmostEqual(
                    300 / source_crop_px, budget["max_scale_factor"], places=6,
                )
                self.assertNotIn("display_mode", budget)

    def test_legibility_checks_bind_preview_and_validate_motion_risk(self):
        plan, analysis, agent_input, preview, clearance = (
            self._clearance_contract_fixture()
        )
        self.assertEqual([], speaker_inset.clearance_errors(
            clearance, preview, agent_input, analysis, plan,
        ))

        for role in ("entry", "middle", "exit", "motion_risk"):
            stale = copy.deepcopy(clearance)
            check = next(
                item for item in stale["shots"][0]["subshots"][0]["legibility_checks"]
                if item["role"] == role
            )
            check["preview_sha256"] = "0" * 64
            errors = speaker_inset.clearance_errors(
                stale, preview, agent_input, analysis, plan,
            )
            self.assertTrue(any("exact preview SHA-256" in error for error in errors), errors)

        unaligned = copy.deepcopy(clearance)
        unaligned["shots"][0]["subshots"][0]["legibility_checks"][1][
            "program_time_s"
        ] = 1.55
        errors = speaker_inset.clearance_errors(
            unaligned, preview, agent_input, analysis, plan,
        )
        self.assertTrue(any("timeline frames" in error for error in errors), errors)

        motion = copy.deepcopy(clearance)
        motion_check = motion["shots"][0]["subshots"][0]["legibility_checks"][3]
        motion_check.update({
            "status": "checked",
            "program_time_s": 1.6,
            "reason": "The speaker turns while the camera moves.",
            "observation": "The full silhouette remains distinct during the turn.",
        })
        motion["shots"][0]["subshots"][0]["pixel_budget"] = (
            speaker_inset.build_pixel_budget(
                plan, analysis, agent_input, preview, "shot", "subshot",
                motion_risk_time_s=1.6,
            )
        )
        self.assertEqual([], speaker_inset.clearance_errors(
            motion, preview, agent_input, analysis, plan,
        ))
        outside = copy.deepcopy(motion)
        outside["shots"][0]["subshots"][0]["legibility_checks"][3][
            "program_time_s"
        ] = 2.0
        errors = speaker_inset.clearance_errors(
            outside, preview, agent_input, analysis, plan,
        )
        self.assertTrue(any("inside its subshot" in error for error in errors), errors)
        missing_reason = copy.deepcopy(motion)
        missing_reason["shots"][0]["subshots"][0]["legibility_checks"][3][
            "reason"
        ] = ""
        errors = speaker_inset.clearance_errors(
            missing_reason, preview, agent_input, analysis, plan,
        )
        self.assertTrue(any("motion-risk reason is required" in error for error in errors), errors)

    def _prepare_evidence(self, supplemental_points=None):
        probe = {
            "width": 1920, "height": 1080, "duration_s": 10.0,
            "fps": {"num": 30, "den": 1},
        }
        with (
            mock.patch.object(speaker_inset, "_probe_video", return_value=probe),
            mock.patch.object(speaker_inset, "_detect_scene_times", return_value=[1.5]),
            mock.patch.object(speaker_inset, "_extract_frame", side_effect=self._frame),
            mock.patch.object(speaker_inset, "_ffmpeg_version", return_value="ffmpeg test"),
        ):
            args = {}
            if supplemental_points is not None:
                args["supplemental_points"] = supplemental_points
            return speaker_inset.prepare_evidence(
                self.prepared, self.timeline, self.transcript,
                self.review_video, self.root, **args,
            )

    def test_prepare_evidence_splits_scenes_and_hash_binds_temporal_frames(self):
        updated = self._prepare_evidence()
        binding = updated["speaker_inset"]["analysis"]
        analysis_path = self.root / "work" / binding["path"]
        self.assertTrue(analysis_path.is_file())
        self.assertEqual(binding["sha256"], broll_plan.sha256_file(analysis_path))
        analysis = projectlib.load_json(analysis_path)
        self.assertEqual(self.prepared["selection"]["sha256"], analysis["selection_sha256"])
        self.assertEqual([1.5], analysis["scene_detection"]["candidate_times_s"])
        subshots = analysis["shots"][0]["subshots"]
        self.assertEqual(2, len(subshots))
        self.assertEqual(1.5, subshots[0]["program_range"]["end_s"])
        self.assertEqual(1.5, subshots[1]["program_range"]["start_s"])
        self.assertEqual("scene", subshots[1]["boundary_source"])
        for subshot in subshots:
            self.assertGreaterEqual(len(subshot["evidence_points"]), 2)
            for point in subshot["evidence_points"]:
                self.assertGreaterEqual(len(point["frames"]), 2)
                for frame in point["frames"]:
                    path = self.root / "work" / frame["path"]
                    self.assertTrue(path.is_file())
                    self.assertEqual(frame["sha256"], broll_plan.sha256_file(path))
        self.assertEqual([], speaker_inset.analysis_errors(
            analysis, updated, self.timeline, self.transcript,
            project_root=self.root, verify_files=True,
        ))

    def test_prepare_evidence_adds_requested_dense_supplemental_points(self):
        self.assertIn(
            "supplemental_points",
            inspect.signature(speaker_inset.prepare_evidence).parameters,
        )
        baseline = self._prepare_evidence()
        analysis_path = self.root / "work" / baseline["speaker_inset"]["analysis"]["path"]
        analysis = projectlib.load_json(analysis_path)
        second = analysis["shots"][0]["subshots"][1]
        start = second["program_range"]["start_s"]
        supplemented = self._prepare_evidence({second["id"]: [start + 0.1]})
        supplemented_path = self.root / "work" / supplemented["speaker_inset"]["analysis"]["path"]
        supplemented_analysis = projectlib.load_json(supplemented_path)
        supplemented_second = supplemented_analysis["shots"][0]["subshots"][1]
        extra = [
            point for point in supplemented_second["evidence_points"]
            if point.get("evidence_kind") == "supplemental"
        ]
        self.assertEqual(1, len(extra))
        self.assertGreaterEqual(len(extra[0]["frames"]), 5)

    def test_agent_input_requires_per_subshot_frame_aligned_tracks_and_honest_fallbacks(self):
        updated = self._prepare_evidence()
        analysis_path = self.root / "work" / updated["speaker_inset"]["analysis"]["path"]
        analysis = projectlib.load_json(analysis_path)
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        subshot_inputs = []
        for index, subshot in enumerate(analysis["shots"][0]["subshots"]):
            start = subshot["program_range"]["start_s"]
            end = subshot["program_range"]["end_s"]
            if index == 0:
                subshot_inputs.append({
                    "id": subshot["id"],
                    "speaker_status": "confirmed",
                    "display_mode": "enabled",
                    "anchor": "top-left",
                    "rationale": "The visible speaker moves continuously in the frame burst.",
                    "keyframes": [
                        {"program_time_s": start, "roi": {"x": 0.10, "y": 0.10, "width": 0.30, "height": 0.60}},
                        {"program_time_s": round(end - frame, 9), "roi": {"x": 0.20, "y": 0.10, "width": 0.30, "height": 0.60}},
                    ],
                })
            else:
                subshot_inputs.append({
                    "id": subshot["id"],
                    "speaker_status": "ambiguous",
                    "display_mode": "pure_broll",
                    "anchor": None,
                    "rationale": "The frame burst does not identify one current speaker.",
                    "keyframes": [],
                })
        agent_input = {
            "schema_version": 1,
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-04T16:00:00+08:00",
            "rationale": "Reviewed every frozen temporal evidence packet.",
            "project_layout_strategy": self._layout_strategy(),
            "analysis_sha256": updated["speaker_inset"]["analysis"]["sha256"],
            "selection_sha256": updated["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(updated["speaker_inset_style"]),
            "review_video_sha256": updated["input_hashes"]["review_video_sha256"],
            "shots": [{
                "shot_id": "shot",
                "layout_recommendation": self._layout_recommendation(),
                "subshots": subshot_inputs,
            }],
        }
        self.assertTrue(any(
            "supplemental" in error for error in speaker_inset.agent_input_errors(
                agent_input, analysis, updated, self.timeline,
            )
        ))
        analysis["shots"][0]["subshots"][1]["evidence_points"][1][
            "evidence_kind"
        ] = "supplemental"
        self.assertEqual([], speaker_inset.agent_input_errors(
            agent_input, analysis, updated, self.timeline,
        ))
        attached = speaker_inset.attach_agent_input(
            updated, analysis, agent_input, self.timeline, self.root,
        )
        binding = attached["speaker_inset"]["agent_input"]
        path = self.root / "work" / binding["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(binding["sha256"], broll_plan.sha256_file(path))

        crossing = copy.deepcopy(agent_input)
        crossing["shots"][0]["subshots"][0]["keyframes"][-1]["program_time_s"] = 1.5
        self.assertTrue(any(
            "cover its subshot" in error or "inside its subshot" in error
            for error in speaker_inset.agent_input_errors(
                crossing, analysis, updated, self.timeline,
            )
        ))
        dishonest = copy.deepcopy(agent_input)
        dishonest["shots"][0]["subshots"][1]["keyframes"] = [
            {"program_time_s": 1.5, "roi": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.6}},
        ]
        self.assertTrue(any(
            "pure_broll" in error for error in speaker_inset.agent_input_errors(
                dishonest, analysis, updated, self.timeline,
            )
        ))

        missing_strategy = copy.deepcopy(agent_input)
        missing_strategy.pop("project_layout_strategy")
        self.assertTrue(any(
            "project_layout_strategy" in error
            for error in speaker_inset.agent_input_errors(
                missing_strategy, analysis, updated, self.timeline,
            )
        ))
        bad_anchor = copy.deepcopy(agent_input)
        bad_anchor["shots"][0]["layout_recommendation"]["anchor"] = "bottom-left"
        self.assertTrue(any(
            "preset/anchor" in error
            for error in speaker_inset.agent_input_errors(
                bad_anchor, analysis, updated, self.timeline,
            )
        ))
        moved_subshot = copy.deepcopy(agent_input)
        moved_subshot["shots"][0]["subshots"][0]["anchor"] = "top-right"
        self.assertTrue(any(
            "shot-level recommended anchor" in error
            for error in speaker_inset.agent_input_errors(
                moved_subshot, analysis, updated, self.timeline,
            )
        ))
        missing_assessment = copy.deepcopy(agent_input)
        del missing_assessment["shots"][0]["layout_recommendation"][
            "preset_assessments"
        ]["focused-panel"]
        self.assertTrue(any(
            "assess all three presets" in error
            for error in speaker_inset.agent_input_errors(
                missing_assessment, analysis, updated, self.timeline,
            )
        ))
        low_without_alternate = copy.deepcopy(agent_input)
        low_without_alternate["shots"][0]["layout_recommendation"][
            "confidence"
        ] = "low"
        self.assertTrue(any(
            "low-confidence recommendation requires alternate" in error
            for error in speaker_inset.agent_input_errors(
                low_without_alternate, analysis, updated, self.timeline,
            )
        ))

    def test_roi_interpolation_is_linear_and_never_crosses_subshot_boundaries(self):
        keyframes = [
            {"program_time_s": 1.0, "roi": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}},
            {"program_time_s": 1.4, "roi": {"x": 0.3, "y": 0.4, "width": 0.5, "height": 0.6}},
        ]
        self.assertEqual(
            {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.5},
            speaker_inset.interpolate_roi(keyframes, 1.2, {"start_s": 1.0, "end_s": 1.5}),
        )
        with self.assertRaisesRegex(ValueError, "outside subshot"):
            speaker_inset.interpolate_roi(
                keyframes, 1.5, {"start_s": 1.0, "end_s": 1.5},
            )

    def test_composite_frame_uses_fractional_roi_motion_without_integer_plateaus(self):
        frame_size = (200, 320)
        base = Image.new("RGB", frame_size, (0, 180, 0))
        speaker = Image.new("RGB", frame_size)
        speaker.putdata([
            (x, x, x)
            for y in range(frame_size[1]) for x in range(frame_size[0])
        ])
        style = BrollPlanTests._speaker_style()
        style["border"]["width_px"] = 0
        roi = {"y": 0.1, "width": 0.4, "height": 0.5}

        first = speaker_inset.composite_frame(
            base, speaker, {"x": 0.101, **roi}, style, "corner-pip", "top-left",
        )
        second = speaker_inset.composite_frame(
            base, speaker, {"x": 0.103, **roi}, style, "corner-pip", "top-left",
        )

        self.assertFalse(first.tobytes() == second.tobytes())

    def test_fractional_roi_cover_crop_box_preserves_aspect_centering_and_top_alignment(self):
        self.assertTrue(hasattr(speaker_inset, "_cover_crop_box"))
        cases = (
            ((200, 100), {"x": 0.101, "y": 0.203, "width": 0.603, "height": 0.407},
             (64.22, 20.3, 96.78, 61.0)),
            ((200, 200), {"x": 0.101, "y": 0.203, "width": 0.203, "height": 0.607},
             (20.2, 40.6, 60.8, 91.35)),
        )
        for source_size, roi, expected in cases:
            with self.subTest(source_size=source_size):
                crop_box = speaker_inset._cover_crop_box(source_size, roi, (80, 100))
                self.assertEqual(expected, tuple(round(value, 6) for value in crop_box))

    def test_fractional_roi_tolerance_stays_inside_source_frame(self):
        frame_size = (100, 100)
        base = Image.new("RGB", frame_size)
        speaker = Image.new("RGB", frame_size)
        style = BrollPlanTests._speaker_style()
        roi = {"x": 0.9, "y": 0.0, "width": 0.1000005, "height": 0.5}

        self.assertEqual([], speaker_inset._roi_errors(roi))
        result = speaker_inset.composite_frame(
            base, speaker, roi, style, "corner-pip", "top-left",
        )
        crop_box = speaker_inset._cover_crop_box(
            frame_size, roi, speaker_inset._inset_size(frame_size, style, "top-left"),
        )
        left, top, right, bottom = crop_box
        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(right, frame_size[0])
        self.assertLessEqual(bottom, frame_size[1])
        self.assertGreater(right, left)
        self.assertGreater(bottom, top)
        self.assertEqual(frame_size, result.size)

    def test_probe_video_accepts_ffprobe_string_duration_and_rational_fps(self):
        payload = {
            "streams": [{
                "codec_type": "video", "width": 96, "height": 54,
                "avg_frame_rate": "30000/1001",
            }],
            "format": {"duration": "10.000000"},
        }
        with mock.patch.object(
                speaker_inset.subprocess, "run",
                return_value=mock.Mock(stdout=json.dumps(payload))):
            self.assertEqual({
                "width": 96, "height": 54, "duration_s": 10.0,
                "fps": {"num": 30000, "den": 1001},
            }, speaker_inset._probe_video(self.review_video))

    def test_composite_frame_applies_presets_rounded_speaker_and_strict_anchors(self):
        size = (200, 320)
        base = Image.new("RGB", size)
        base.putdata([
            ((x // 4 + y // 4) % 2 * 255,) * 3
            for y in range(size[1]) for x in range(size[0])
        ])
        speaker = Image.new("RGB", size, (220, 20, 20))
        style = BrollPlanTests._speaker_style()
        roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

        focused = speaker_inset.composite_frame(
            base, speaker, roi, style, "focused-panel", "lower-center",
        )
        self.assertEqual(size, focused.size)
        self.assertNotIn(focused.getpixel((100, 300))[0], {0, 255})
        self.assertGreater(
            abs(focused.getpixel((98, 100))[0] - focused.getpixel((102, 100))[0]),
            150,
        )

        washed = speaker_inset.composite_frame(
            Image.new("RGB", size, (20, 40, 60)), speaker, roi, style,
            "full-bleed-wash", "upper-center",
        )
        self.assertEqual((90, 104, 118), washed.getpixel((10, 300)))

        for anchor, center_x in (("top-left", 38), ("top-right", 162)):
            corner = speaker_inset.composite_frame(
                Image.new("RGB", size, (0, 180, 0)), speaker, roi, style,
                "corner-pip", anchor,
            )
            self.assertEqual((0, 180, 0), corner.getpixel((100, 300)))
            self.assertGreater(corner.getpixel((center_x, 45))[0], 150)
            self.assertEqual((0, 180, 0), corner.getpixel((8 if anchor == "top-left" else 191, 8)))

        pure = speaker_inset.composite_frame(
            base, None, None, style, "focused-panel", None,
        )
        self.assertEqual(size, pure.size)
        self.assertNotIn(pure.getpixel((100, 300))[0], {0, 255})

        for anchor in ("bottom-left", "bottom-right"):
            with self.subTest(anchor=anchor), self.assertRaisesRegex(
                    ValueError, "preset/anchor"):
                speaker_inset.composite_frame(
                    base, speaker, roi, style, "corner-pip", anchor,
                )

    def test_focused_panel_has_gray_border_and_places_larger_speaker_below_panel(self):
        frame_size = (200, 320)
        style = BrollPlanTests._speaker_style()
        base = Image.new("RGB", frame_size, (20, 40, 60))

        treated = speaker_inset._apply_broll_treatment(base, "focused-panel")
        panel_x = round(frame_size[0] * 0.04)
        panel_y = round(frame_size[1] * 0.08)
        self.assertEqual((158, 158, 158), treated.getpixel((100, panel_y)))

        inset_width, inset_height = speaker_inset._inset_size(
            frame_size, style, "lower-center",
        )
        _, inset_y = speaker_inset._anchor_position(
            frame_size, (inset_width, inset_height), style, "lower-center",
        )
        panel_bottom = panel_y + round(frame_size[1] * 0.40)
        safe_bottom = round(frame_size[1] * (1 - style["reserved_bottom_ratio"]))
        self.assertGreaterEqual(inset_y, panel_bottom)
        self.assertEqual(safe_bottom, inset_y + inset_height)

    def test_composite_frame_preserves_speaker_pixel_aspect_ratio(self):
        frame_size = (200, 320)
        base = Image.new("RGB", frame_size, (0, 180, 0))
        style = BrollPlanTests._speaker_style()
        style["border"]["width_px"] = 0
        roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

        for speaker_size in ((200, 320), (320, 200), (160, 200)):
            with self.subTest(speaker_size=speaker_size):
                speaker = Image.new("RGB", speaker_size, "black")
                draw = ImageDraw.Draw(speaker)
                center = (speaker_size[0] // 2, speaker_size[1] // 2)
                draw.ellipse(
                    (center[0] - 30, center[1] - 30,
                     center[0] + 30, center[1] + 30),
                    fill="white",
                )
                composite = speaker_inset.composite_frame(
                    base, speaker, roi, style, "corner-pip", "top-left",
                )
                inset_width, inset_height = speaker_inset._inset_size(
                    frame_size, style, "top-left",
                )
                inset_x, inset_y = speaker_inset._anchor_position(
                    frame_size, (inset_width, inset_height), style, "top-left",
                )
                inset = composite.crop((
                    inset_x, inset_y, inset_x + inset_width, inset_y + inset_height,
                ))
                white_pixels = [
                    (x, y)
                    for y in range(inset.height)
                    for x in range(inset.width)
                    if min(inset.getpixel((x, y))) >= 200
                ]
                self.assertTrue(white_pixels)
                circle_width = max(x for x, _ in white_pixels) - min(
                    x for x, _ in white_pixels
                ) + 1
                circle_height = max(y for _, y in white_pixels) - min(
                    y for _, y in white_pixels
                ) + 1
                self.assertLessEqual(
                    abs(circle_width - circle_height), 1,
                    f"speaker geometry was stretched to {circle_width}x{circle_height}",
                )

    def test_composite_frame_preserves_complete_face_before_lower_body(self):
        frame_size = (200, 320)
        base = Image.new("RGB", frame_size, (0, 180, 0))
        speaker = Image.new("RGB", frame_size, "black")
        draw = ImageDraw.Draw(speaker)
        draw.ellipse((70, 25, 130, 85), fill="white")
        style = BrollPlanTests._speaker_style()
        style["border"]["width_px"] = 0
        roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

        composite = speaker_inset.composite_frame(
            base, speaker, roi, style, "corner-pip", "top-left",
        )
        inset_width, inset_height = speaker_inset._inset_size(
            frame_size, style, "top-left",
        )
        inset_x, inset_y = speaker_inset._anchor_position(
            frame_size, (inset_width, inset_height), style, "top-left",
        )
        inset = composite.crop((
            inset_x, inset_y, inset_x + inset_width, inset_y + inset_height,
        ))
        face_pixels = [
            (x, y)
            for y in range(inset.height)
            for x in range(inset.width)
            if min(inset.getpixel((x, y))) >= 200
        ]
        self.assertTrue(face_pixels)
        face_width = max(x for x, _ in face_pixels) - min(
            x for x, _ in face_pixels
        ) + 1
        face_height = max(y for _, y in face_pixels) - min(
            y for _, y in face_pixels
        ) + 1
        self.assertGreaterEqual(
            min(y for _, y in face_pixels), 5,
            "speaker face lost its top edge or headroom",
        )
        self.assertLessEqual(
            abs(face_width - face_height), 1,
            f"speaker face was cropped to {face_width}x{face_height}",
        )

    def test_composite_frame_keeps_head_top_and_headroom_inside_rounded_mask(self):
        frame_size = (200, 320)
        base = Image.new("RGB", frame_size, (0, 180, 0))
        speaker = Image.new("RGB", frame_size, "black")
        draw = ImageDraw.Draw(speaker)
        draw.ellipse((70, 4, 130, 64), fill="white")
        style = BrollPlanTests._speaker_style()
        style["border"]["width_px"] = 0
        roi = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

        composite = speaker_inset.composite_frame(
            base, speaker, roi, style, "corner-pip", "top-left",
        )
        inset_width, inset_height = speaker_inset._inset_size(
            frame_size, style, "top-left",
        )
        inset_x, inset_y = speaker_inset._anchor_position(
            frame_size, (inset_width, inset_height), style, "top-left",
        )
        inset = composite.crop((
            inset_x, inset_y, inset_x + inset_width, inset_y + inset_height,
        ))
        head_pixels = [
            (x, y)
            for y in range(inset.height)
            for x in range(inset.width)
            if min(inset.getpixel((x, y))) >= 200
        ]
        self.assertTrue(head_pixels)
        self.assertGreaterEqual(
            min(y for _, y in head_pixels), 1,
            "speaker head top was cropped by the cover fit",
        )

    def test_render_context_preview_uses_exact_selection_and_real_speaker_frames(self):
        self.plan.pop("presentation")
        self.timeline.update({"width": 96, "height": 54, "fps": {"num": 10, "den": 1}})
        projectlib.write_json(self.timeline_path, self.timeline)
        self.selected_lut_path.write_text(
            'TITLE "Identity"\nLUT_3D_SIZE 2\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n'
            "0 0 0\n0 0 1\n0 1 0\n0 1 1\n1 0 0\n1 0 1\n1 1 0\n1 1 1\n",
            encoding="ascii",
        )
        candidate_path = self.root / "work/cache/b-roll/factory.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=green:size=128x96:rate=10",
            "-t", "2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(candidate_path),
        ], check=True, capture_output=True)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=blue:size=96x54:rate=10",
            "-t", "10", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(self.review_video),
        ], check=True, capture_output=True)
        candidate = self.plan["shots"][0]["candidates"][0]
        candidate.update({
            "cache_path": candidate_path.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(candidate_path),
            "bytes": candidate_path.stat().st_size,
            "duration_s": 2.0,
            "probe": {"duration_s": 2.0, "width": 128, "height": 96},
        })
        self.plan["input_hashes"].update({
            "timeline_sha256": broll_plan.sha256_file(self.timeline_path),
            "review_video_sha256": broll_plan.sha256_file(self.review_video),
            "selected_lut_sha256": broll_plan.sha256_file(self.selected_lut_path),
        })
        self.plan = self.record_presentation(self.plan, "speaker-inset")
        segment = {
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": 1.0},
            "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
            "playback_rate": 1.0,
        }
        selection = self.review_for(
            self.plan,
            [{
                "id": "shot", "decision": "select",
                "program_range": copy.deepcopy(self.plan["shots"][0]["program_range"]),
                "segments": [segment],
            }],
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            submission_intent="prepare_composite", explicit_user_action=True,
            revision_notes="", rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        prepared = broll_plan.prepare_composite(
            self.plan, selection, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            project_root=self.root, timeline=self.timeline,
        )
        with (
            mock.patch.object(speaker_inset, "_detect_scene_times", return_value=[]),
            mock.patch.object(speaker_inset, "_extract_frame", side_effect=self._frame),
        ):
            analyzed = speaker_inset.prepare_evidence(
                prepared, self.timeline, self.transcript,
                self.review_video, self.root,
            )
        analysis_path = self.root / "work" / analyzed["speaker_inset"]["analysis"]["path"]
        analysis = projectlib.load_json(analysis_path)
        subshot = analysis["shots"][0]["subshots"][0]
        agent_input = {
            "schema_version": 1, "mode": "agent", "actor": "Codex",
            "timestamp": "2026-08-04T16:00:00+08:00",
            "rationale": "The exact A-roll evidence shows one continuous speaker.",
            "project_layout_strategy": self._layout_strategy(),
            "analysis_sha256": analyzed["speaker_inset"]["analysis"]["sha256"],
            "selection_sha256": analyzed["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(analyzed["speaker_inset_style"]),
            "review_video_sha256": analyzed["input_hashes"]["review_video_sha256"],
            "shots": [{
                "shot_id": "shot",
                "layout_recommendation": self._layout_recommendation(),
                "subshots": [{
                    "id": subshot["id"], "speaker_status": "confirmed",
                    "display_mode": "enabled", "anchor": "top-left",
                    "rationale": "One visible speaker remains continuous.",
                    "keyframes": [
                        {"program_time_s": 1.0, "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}},
                        {"program_time_s": 1.9, "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}},
                    ],
                }],
            }],
        }
        attached = speaker_inset.attach_agent_input(
            analyzed, analysis, agent_input, self.timeline, self.root,
        )
        previewed = speaker_inset.render_context_previews(
            attached, analysis, agent_input, self.timeline,
            self.review_video, self.root, lut=self.selected_lut_path,
        )
        preview_binding = previewed["speaker_inset"]["preview"]
        record_path = self.root / "work" / preview_binding["path"]
        self.assertTrue(record_path.is_file())
        self.assertEqual(preview_binding["sha256"], broll_plan.sha256_file(record_path))
        record = projectlib.load_json(record_path)
        video = self.root / "work" / record["shots"][0]["preview"]["path"]
        self.assertTrue(video.is_file())
        self.assertEqual(record["shots"][0]["preview"]["sha256"], broll_plan.sha256_file(video))
        anchor_previews = record["shots"][0]["anchor_previews"]
        self.assertEqual(
            set(speaker_inset.PRESET_ANCHORS["corner-pip"]),
            set(anchor_previews),
        )
        self.assertNotIn("size_review", record)
        for binding in anchor_previews.values():
            alternate = self.root / "work" / binding["path"]
            self.assertTrue(alternate.is_file())
            self.assertEqual(binding["sha256"], broll_plan.sha256_file(alternate))
        probe = speaker_inset._probe_video(video)
        self.assertEqual({"num": 10, "den": 1}, probe["fps"])
        self.assertAlmostEqual(1.0, probe["duration_s"], places=2)
        still = self.root / "preview-still.png"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5",
            "-i", str(video), "-frames:v", "1", str(still),
        ], check=True, capture_output=True)
        with Image.open(still).convert("RGB") as image:
            inset_pixel = image.getpixel((14, 14))
            broll_pixel = image.getpixel((80, 40))
        self.assertGreater(inset_pixel[2], inset_pixel[1])
        self.assertGreater(broll_pixel[1], broll_pixel[2])

    def test_broll_preview_base_covers_every_timeline_frame_when_upsampling(self):
        self.timeline.update({"width": 96, "height": 54, "fps": {"num": 60, "den": 1}})
        frame_count = 209
        duration = frame_count / 60
        candidate_path = self.root / "work/cache/b-roll/factory.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=green:size=128x96:rate=30",
            "-t", "4", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-video_track_timescale", "30",
            str(candidate_path),
        ], check=True, capture_output=True)
        plan = copy.deepcopy(self.prepared)
        shot = plan["shots"][0]
        candidate = shot["candidates"][0]
        candidate.update({
            "cache_path": candidate_path.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(candidate_path),
            "bytes": candidate_path.stat().st_size,
            "duration_s": 4.0,
            "probe": {"duration_s": 4.0, "width": 128, "height": 96},
        })
        shot["program_range"] = {"start_s": 1.0, "end_s": 1.0 + duration}
        shot["selected"] = {"segments": [{
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": duration},
            "program_range": copy.deepcopy(shot["program_range"]),
            "playback_rate": 1.0,
        }]}
        output = self.root / "work/cache/b-roll/speaker-inset/base.mp4"

        speaker_inset._render_broll_base(
            plan, shot, self.timeline, self.root, output, None,
        )

        probe = subprocess.run([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "json", str(output),
        ], check=True, capture_output=True, text=True)
        self.assertEqual(
            frame_count,
            int(json.loads(probe.stdout)["streams"][0]["nb_read_frames"]),
        )

    def test_clearance_binds_exact_preview_and_requires_honest_safe_position_fallback(self):
        analyzed = self._prepare_evidence()
        analysis_path = self.root / "work" / analyzed["speaker_inset"]["analysis"]["path"]
        analysis = projectlib.load_json(analysis_path)
        analysis["shots"][0]["subshots"][1]["evidence_points"][1][
            "evidence_kind"
        ] = "supplemental"
        projectlib.write_json(analysis_path, analysis)
        analyzed["speaker_inset"]["analysis"]["sha256"] = broll_plan.sha256_file(
            analysis_path
        )
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        subshots = analysis["shots"][0]["subshots"]
        first_range = subshots[0]["program_range"]
        agent_input = {
            "schema_version": 1,
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-04T16:00:00+08:00",
            "rationale": "Reviewed the frozen A-roll evidence for every subshot.",
            "project_layout_strategy": self._layout_strategy(),
            "analysis_sha256": analyzed["speaker_inset"]["analysis"]["sha256"],
            "selection_sha256": analyzed["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(analyzed["speaker_inset_style"]),
            "review_video_sha256": analyzed["input_hashes"]["review_video_sha256"],
            "shots": [{
                "shot_id": "shot",
                "layout_recommendation": self._layout_recommendation(),
                "subshots": [{
                    "id": subshots[0]["id"],
                    "speaker_status": "confirmed",
                    "display_mode": "enabled",
                    "anchor": "top-left",
                    "rationale": "One current speaker remains continuous.",
                    "keyframes": [
                        {
                            "program_time_s": first_range["start_s"],
                            "roi": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.6},
                        },
                        {
                            "program_time_s": round(first_range["end_s"] - frame, 9),
                            "roi": {"x": 0.2, "y": 0.1, "width": 0.3, "height": 0.6},
                        },
                    ],
                }, {
                    "id": subshots[1]["id"],
                    "speaker_status": "ambiguous",
                    "display_mode": "pure_broll",
                    "anchor": None,
                    "rationale": "The temporal evidence cannot isolate one current speaker.",
                    "keyframes": [],
                }],
            }],
        }
        attached = speaker_inset.attach_agent_input(
            analyzed, analysis, agent_input, self.timeline, self.root,
        )
        preview_media = self.root / "work/cache/b-roll"
        base_path = preview_media / "base.mp4"
        context_path = preview_media / "context.mp4"
        base_path.write_bytes(b"base-broll-preview")
        context_path.write_bytes(b"contextual-preview")
        alternate_bindings = {}
        for index, anchor in enumerate(speaker_inset.PRESET_ANCHORS["corner-pip"]):
            path = preview_media / f"context-{anchor}.mp4"
            path.write_bytes(f"context-{anchor}-{index}".encode("ascii"))
            alternate_bindings[anchor] = {
                "path": path.relative_to(self.root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(path),
            }
        preview_record = {
            "schema_version": 1,
            "analysis_sha256": attached["speaker_inset"]["analysis"]["sha256"],
            "agent_input_sha256": attached["speaker_inset"]["agent_input"]["sha256"],
            "selection_sha256": attached["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(attached["speaker_inset_style"]),
            "review_video_sha256": attached["input_hashes"]["review_video_sha256"],
            "shots": [{
                "shot_id": "shot",
                "program_range": copy.deepcopy(attached["shots"][0]["program_range"]),
                "base_broll": {
                    "path": base_path.relative_to(self.root / "work").as_posix(),
                    "sha256": broll_plan.sha256_file(base_path),
                },
                "preview": {
                    "path": context_path.relative_to(self.root / "work").as_posix(),
                    "sha256": broll_plan.sha256_file(context_path),
                    "probe": {"width": 1920, "height": 1080},
                },
                "anchor_previews": alternate_bindings,
            }],
        }
        obsolete_size_review = copy.deepcopy(preview_record)
        obsolete_size_review["size_review"] = {}
        self.assertTrue(any(
            "size_review" in error for error in speaker_inset.preview_errors(
                obsolete_size_review, attached, analysis, agent_input, self.timeline,
            )
        ))
        changed_recommendation = copy.deepcopy(agent_input)
        changed_recommendation["shots"][0]["layout_recommendation"][
            "rationale"
        ] = "A changed recommendation must invalidate the frozen preview."
        self.assertTrue(any(
            "Agent input binding is stale" in error
            for error in speaker_inset.preview_errors(
                preview_record, attached, analysis, changed_recommendation,
                self.timeline,
            )
        ))
        preview_path = self.root / "work/b-roll/speaker-inset-preview.json"
        projectlib.write_json(preview_path, preview_record)
        previewed = copy.deepcopy(attached)
        previewed["speaker_inset"]["preview"] = {
            "path": "b-roll/speaker-inset-preview.json",
            "sha256": broll_plan.sha256_file(preview_path),
        }
        clearance = {
            "schema_version": 1,
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-04T16:10:00+08:00",
            "rationale": "Checked the exact composited previews against B-roll focal content.",
            "analysis_sha256": previewed["speaker_inset"]["analysis"]["sha256"],
            "agent_input_sha256": previewed["speaker_inset"]["agent_input"]["sha256"],
            "preview_sha256": previewed["speaker_inset"]["preview"]["sha256"],
            "selection_sha256": previewed["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(previewed["speaker_inset_style"]),
            "shots": [{
                "shot_id": "shot",
                "continuity": {
                    "risk": "mode_change",
                    "decision": "intentional_transition",
                    "rationale": "The speaker window stops only after the independently reviewed cut.",
                },
                "subshots": [{
                    "id": subshots[0]["id"],
                    "display_mode": "enabled",
                    "anchor": "top-left",
                    "clearance_status": "pass",
                    "checked_anchors": ["top-left"],
                    "subject_legibility": "pass",
                    "rationale": "The inset leaves the primary B-roll action visible.",
                }, {
                    "id": subshots[1]["id"],
                    "display_mode": "pure_broll",
                    "anchor": None,
                    "clearance_status": "pass",
                    "checked_anchors": [],
                    "subject_legibility": "not_applicable",
                    "rationale": "Speaker identity is ambiguous, so the inset stays disabled.",
                }],
            }],
        }
        clearance["shots"][0]["subshots"][0].update(
            _final_size_clearance_fields(
                previewed, analysis, agent_input, preview_record,
                "shot", subshots[0]["id"],
            )
        )
        obsolete_size_assessment = copy.deepcopy(clearance)
        obsolete_size_assessment["size_assessment"] = {}
        self.assertTrue(any(
            "size_assessment" in error for error in speaker_inset.clearance_errors(
                obsolete_size_assessment, preview_record, agent_input, analysis, previewed,
            )
        ))
        missing_continuity = copy.deepcopy(clearance)
        missing_continuity["shots"][0].pop("continuity")
        self.assertTrue(any(
            "continuity" in error for error in speaker_inset.clearance_errors(
                missing_continuity, preview_record, agent_input, analysis, previewed,
            )
        ))
        missing_legibility = copy.deepcopy(clearance)
        missing_legibility["shots"][0]["subshots"][0].pop("subject_legibility")
        self.assertTrue(any(
            "subject_legibility" in error for error in speaker_inset.clearance_errors(
                missing_legibility, preview_record, agent_input, analysis, previewed,
            )
        ))
        flash_analysis = copy.deepcopy(analysis)
        flash_subshots = flash_analysis["shots"][0]["subshots"]
        flash_subshots[0]["program_range"] = {"start_s": 0.0, "end_s": 0.933333333}
        flash_subshots[1]["program_range"] = {"start_s": 0.933333333, "end_s": 3.483333333}
        wrong_flash = copy.deepcopy(clearance)
        self.assertTrue(any(
            "short_flash" in error for error in speaker_inset.clearance_errors(
                wrong_flash, preview_record, agent_input, flash_analysis, previewed,
            )
        ))
        wrong_flash["shots"][0]["continuity"]["risk"] = "short_flash"
        self.assertFalse(any(
            "continuity risk" in error for error in speaker_inset.clearance_errors(
                wrong_flash, preview_record, agent_input, flash_analysis, previewed,
            )
        ))
        self.assertEqual([], speaker_inset.clearance_errors(
            clearance, preview_record, agent_input, analysis, previewed,
        ))
        cleared = speaker_inset.attach_clearance(
            previewed, analysis, agent_input, preview_record, clearance,
            self.root, self.timeline,
        )
        binding = cleared["speaker_inset"]["clearance"]
        path = self.root / "work" / binding["path"]
        self.assertTrue(path.is_file())
        self.assertEqual(binding["sha256"], broll_plan.sha256_file(path))
        self.assertEqual([], broll_plan.validate_plan(
            cleared, self.timeline, self.transcript,
            project_root=self.root, verify_files=True,
        ))

        no_safe = copy.deepcopy(clearance)
        fallback = no_safe["shots"][0]["subshots"][0]
        fallback.update({
            "display_mode": "pure_broll",
            "anchor": None,
            "clearance_status": "no_safe_position",
            "checked_anchors": list(speaker_inset.PRESET_ANCHORS["corner-pip"]),
            "subject_legibility": "not_applicable",
            "rationale": "Every allowed anchor covers the primary B-roll action.",
        })
        no_safe["shots"][0]["continuity"].update({
            "risk": "none",
            "decision": "all_pure_broll",
            "rationale": "Every subshot is pure B-roll after the safe-position fallback.",
        })
        self.assertEqual([], speaker_inset.clearance_errors(
            no_safe, preview_record, agent_input, analysis, previewed,
        ))
        dishonest = copy.deepcopy(no_safe)
        dishonest["shots"][0]["subshots"][0]["checked_anchors"] = ["top-left"]
        self.assertTrue(any(
            "all allowed anchors" in error
            for error in speaker_inset.clearance_errors(
                dishonest, preview_record, agent_input, analysis, previewed,
            )
        ))
        stale = copy.deepcopy(clearance)
        stale["preview_sha256"] = "f" * 64
        self.assertTrue(any(
            "preview_sha256" in error
            for error in speaker_inset.clearance_errors(
                stale, preview_record, agent_input, analysis, previewed,
            )
        ))
        path.write_text("{}\n", encoding="utf-8")
        self.assertTrue(any(
            "clearance SHA-256 is stale" in error
            for error in broll_plan.validate_plan(
                cleared, self.timeline, self.transcript,
                project_root=self.root, verify_files=True,
            )
        ))


class NormalizeAndCheckTests(_BrollFixture, unittest.TestCase):
    def setUp(self):
        _BrollFixture.setUp(self)
        self.candidates = self.root / "work/cache/b-roll/candidates"
        self.candidates.mkdir(parents=True)
        self.output = self.root / "work/cache/b-roll/normalized/broll-001.mp4"
        self.timeline.update({"width": 96, "height": 54, "fps": {"num": 30000, "den": 1001}})
        projectlib.write_json(self.timeline_path, self.timeline)
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        self.transcript["segments"][0]["words"] = [
            {
                "word": word,
                "start": round(index * 30 * frame, 9),
                "end": round((index + 1) * 30 * frame, 9),
            }
            for index, word in enumerate(("factory", "process", "output", "quality"), 1)
        ]
        projectlib.write_json(self.transcript_path, self.transcript)
        self.mapped_words = projectlib.map_transcript_to_timeline(
            self.transcript, self.timeline,
        )["segments"][0]["words"]
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
            "transcript_sha256": broll_plan.sha256_file(self.transcript_path),
            "timeline_sha256": broll_plan.sha256_file(self.timeline_path),
            "grade_plan_sha256": broll_plan.sha256_file(self.grade_plan_path),
            "selected_lut_sha256": broll_plan.sha256_file(self.selected_lut_path),
        })
        start = round(30 * frame, 9)
        end = round(60 * frame, 9)
        self.plan["shots"][0].update({
            "program_range": {"start_s": start, "end_s": end},
            "source_ranges": [{"clip_id": "one", "start_s": start, "end_s": end}],
            "transcript_evidence": {"words": [self.mapped_words[0]]},
        })
        self.base_plan = copy.deepcopy(self.plan)
        self.plan = self._approve(self.base_plan)
        self.plan_path = self.root / "work/b-roll/broll-plan.json"
        projectlib.write_json(self.plan_path, self.plan)

    def test_base_plan_matches_final_timeline_frame_grid(self):
        self.assertEqual([], broll_plan.validate_plan(
            self.base_plan, self.timeline, self.transcript,
        ))

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
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        start, end = round(60 * frame, 9), round(90 * frame, 9)
        second.update({
            "id": "second", "program_range": {"start_s": start, "end_s": end},
            "source_ranges": [{"clip_id": "one", "start_s": start, "end_s": end}],
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
        rate = f"{self.timeline['fps']['num']}/{self.timeline['fps']['den']}"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=blue:size=96x54:rate={rate}",
            "-t", "10", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
        ], check=True, capture_output=True)
        return path

    def _approved_speaker_plan(self, *, preset="corner-pip", anchor="top-left",
                               clearance_mode="enabled", secondary=None):
        self.timeline["fps"] = {"num": 30, "den": 1}
        projectlib.write_json(self.timeline_path, self.timeline)
        self.transcript["segments"][0]["words"] = [
            {"word": word, "start": float(index), "end": float(index + 1)}
            for index, word in enumerate(("factory", "process", "output", "quality"), 1)
        ]
        projectlib.write_json(self.transcript_path, self.transcript)
        self.mapped_words = projectlib.map_transcript_to_timeline(
            self.transcript, self.timeline,
        )["segments"][0]["words"]
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        start = round(30 * frame, 9)
        end = round(60 * frame, 9)
        review_video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["speaker_inset_style"] = BrollPlanTests._speaker_style()
        plan["input_hashes"]["timeline_sha256"] = broll_plan.sha256_file(self.timeline_path)
        plan["input_hashes"]["transcript_sha256"] = broll_plan.sha256_file(self.transcript_path)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(review_video)
        shot = plan["shots"][0]
        shot["program_range"] = {"start_s": start, "end_s": end}
        shot["source_ranges"] = [{"clip_id": "one", "start_s": start, "end_s": end}]
        shot["transcript_evidence"] = {"words": [self.mapped_words[0]]}
        layouts = [{"shot_id": "shot", "preset": preset, "anchor": anchor}]
        if secondary is not None:
            second = copy.deepcopy(shot)
            second.update({
                "id": "second",
                "program_range": {"start_s": end, "end_s": round(end + 30 * frame, 9)},
                "source_ranges": [{
                    "clip_id": "one", "start_s": end, "end_s": round(end + 30 * frame, 9),
                }],
                "transcript_evidence": {"words": [self.mapped_words[1]]},
            })
            second["candidates"][0]["id"] = "asset-2"
            plan["shots"].append(second)
            layouts.append({
                "shot_id": "second",
                "preset": secondary["preset"],
                "anchor": secondary["anchor"],
            })
        plan = self.record_presentation(plan, "speaker-inset")
        selections = []
        for current in plan["shots"]:
            candidate_id = current["candidates"][0]["id"]
            selections.append({
                "id": current["id"], "decision": "select",
                "program_range": copy.deepcopy(current["program_range"]),
                "segments": [{
                    "candidate_id": candidate_id,
                    "source_range": {
                        "start_s": 0.25,
                        "end_s": round(
                            0.25 + current["program_range"]["end_s"]
                            - current["program_range"]["start_s"],
                            9,
                        ),
                    },
                    "program_range": copy.deepcopy(current["program_range"]),
                    "playback_rate": 1.0,
                }],
            })
        selection = self.review_for(
            plan, selections,
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            submission_intent="prepare_composite", explicit_user_action=True,
            revision_notes="", rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
        )
        prepared = broll_plan.prepare_composite(
            plan, selection, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_PREPARE_COMPOSITE_RATIONALE,
            project_root=self.root, timeline=self.timeline,
        )
        with mock.patch.object(speaker_inset, "_detect_scene_times", return_value=[]):
            analyzed = speaker_inset.prepare_evidence(
                prepared, self.timeline, self.transcript,
                review_video, self.root,
            )
        analysis_path = self.root / "work" / analyzed["speaker_inset"]["analysis"]["path"]
        analysis = projectlib.load_json(analysis_path)
        analysis_by_id = {item["shot_id"]: item for item in analysis["shots"]}
        used_presets = []
        for layout in layouts:
            if layout["preset"] not in used_presets:
                used_presets.append(layout["preset"])
        agent_shots = []
        for layout in layouts:
            subshot = analysis_by_id[layout["shot_id"]]["subshots"][0]
            assessments = {name: "warn" for name in speaker_inset.LAYOUT_PRESETS}
            assessments[layout["preset"]] = "pass"
            agent_shots.append({
                "shot_id": layout["shot_id"],
                "layout_recommendation": {
                    "preset": layout["preset"], "anchor": layout["anchor"],
                    "confidence": "high", "alternate": None,
                    "rationale": "The recommended placement preserves the B-roll focal content.",
                    "preset_assessments": assessments,
                },
                "subshots": [{
                    "id": subshot["id"], "speaker_status": "confirmed",
                    "display_mode": "enabled", "anchor": layout["anchor"],
                    "rationale": "One current speaker remains visible throughout the shot.",
                    "keyframes": [{
                        "program_time_s": subshot["program_range"]["start_s"],
                        "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                    }, {
                        "program_time_s": round(
                            subshot["program_range"]["end_s"] - frame, 9,
                        ),
                        "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                    }],
                }],
            })
        agent_input = {
            "schema_version": 1, "mode": "agent", "actor": "Codex",
            "timestamp": "2026-08-05T12:00:00+08:00",
            "rationale": "Reviewed the exact selected B-roll and frozen speaker evidence.",
            "project_layout_strategy": {
                "primary_preset": preset, "used_presets": used_presets,
                "rationale": (
                    "The second shot needs a separated panel while the primary layout preserves "
                    "full-contrast detail."
                    if secondary is not None else
                    "The selected shot supports one consistent project layout."
                ),
            },
            "analysis_sha256": analyzed["speaker_inset"]["analysis"]["sha256"],
            "selection_sha256": analyzed["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(analyzed["speaker_inset_style"]),
            "review_video_sha256": analyzed["input_hashes"]["review_video_sha256"],
            "shots": agent_shots,
        }
        attached = speaker_inset.attach_agent_input(
            analyzed, analysis, agent_input, self.timeline, self.root,
        )
        preview_root = self.root / "work/cache/b-roll/speaker-inset/test-preview"
        preview_root.mkdir(parents=True, exist_ok=True)

        def binding(name):
            path = preview_root / name
            path.write_bytes(name.encode("ascii"))
            return {
                "path": path.relative_to(self.root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(path),
            }

        attached_shots = {item["id"]: item for item in attached["shots"]}
        preview_shots = []
        for layout in layouts:
            shot_id = layout["shot_id"]
            preview_shots.append({
                "shot_id": shot_id,
                "program_range": copy.deepcopy(attached_shots[shot_id]["program_range"]),
                "base_broll": binding(f"{shot_id}-base.mp4"),
                "preview": {
                    **binding(f"{shot_id}-recommended.mp4"),
                    "probe": {
                        "width": self.timeline["width"],
                        "height": self.timeline["height"],
                    },
                },
                "anchor_previews": {
                    value: binding(f"{shot_id}-anchor-{value}.mp4")
                    for value in speaker_inset.PRESET_ANCHORS[layout["preset"]]
                },
            })
        preview = {
            "schema_version": 1,
            "analysis_sha256": attached["speaker_inset"]["analysis"]["sha256"],
            "agent_input_sha256": attached["speaker_inset"]["agent_input"]["sha256"],
            "selection_sha256": attached["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(attached["speaker_inset_style"]),
            "review_video_sha256": attached["input_hashes"]["review_video_sha256"],
            "shots": preview_shots,
        }
        preview_path = self.root / "work/b-roll/speaker-inset-preview.json"
        projectlib.write_json(preview_path, preview)
        previewed = copy.deepcopy(attached)
        previewed["speaker_inset"]["preview"] = {
            "path": "b-roll/speaker-inset-preview.json",
            "sha256": broll_plan.sha256_file(preview_path),
        }
        enabled = clearance_mode == "enabled"
        clearance_shots = []
        for layout in layouts:
            subshot = analysis_by_id[layout["shot_id"]]["subshots"][0]
            clearance_subshot = {
                "id": subshot["id"],
                "display_mode": "enabled" if enabled else "pure_broll",
                "anchor": layout["anchor"] if enabled else None,
                "clearance_status": "pass" if enabled else "no_safe_position",
                "checked_anchors": [layout["anchor"]] if enabled else list(
                    speaker_inset.PRESET_ANCHORS[layout["preset"]]
                ),
                "subject_legibility": "pass" if enabled else "not_applicable",
                "rationale": (
                    "The recommended placement is clear." if enabled else
                    "No supported anchor leaves the B-roll focal content clear."
                ),
            }
            clearance_subshot.update(_final_size_clearance_fields(
                previewed, analysis, agent_input, preview,
                layout["shot_id"], subshot["id"],
            ))
            clearance_shots.append({
                "shot_id": layout["shot_id"],
                "continuity": {
                    "risk": "none",
                    "decision": "continuous" if enabled else "all_pure_broll",
                    "rationale": "The effective display mode remains constant for the shot.",
                },
                "subshots": [clearance_subshot],
            })
        clearance = {
            "schema_version": 1, "mode": "agent", "actor": "Codex",
            "timestamp": "2026-08-05T12:05:00+08:00",
            "rationale": "Checked the exact preview against the B-roll focal content.",
            "analysis_sha256": previewed["speaker_inset"]["analysis"]["sha256"],
            "agent_input_sha256": previewed["speaker_inset"]["agent_input"]["sha256"],
            "preview_sha256": previewed["speaker_inset"]["preview"]["sha256"],
            "selection_sha256": previewed["selection"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(previewed["speaker_inset_style"]),
            "shots": clearance_shots,
        }
        cleared = speaker_inset.attach_clearance(
            previewed, analysis, agent_input, preview, clearance,
            self.root, self.timeline,
        )
        review = self.review_for(
            cleared, [], rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            submission_intent="approve",
            approval_scope="speaker-inset-composite", review_stage="composite",
            explicit_user_action=True, revision_notes="",
            rationale_source="review_ui_explicit_action",
            timeline_fps=copy.deepcopy(self.timeline["fps"]),
            selection_sha256=cleared["selection"]["sha256"],
            analysis_sha256=cleared["speaker_inset"]["analysis"]["sha256"],
            agent_input_sha256=cleared["speaker_inset"]["agent_input"]["sha256"],
            preview_sha256=cleared["speaker_inset"]["preview"]["sha256"],
            clearance_sha256=cleared["speaker_inset"]["clearance"]["sha256"],
            style_sha256=broll_plan.canonical_sha256(cleared["speaker_inset_style"]),
        )
        review.pop("shots")
        approved = broll_plan.apply_review(
            cleared, review, mode="human", actor="Actual user",
            rationale=broll_plan.HUMAN_APPROVAL_RATIONALE,
            timeline=self.timeline,
        )
        return approved, analysis, agent_input, preview, clearance, review_video

    def test_render_delivery_composite_uses_clearance_effective_choices(self):
        approved, analysis, agent_input, preview, clearance, review_video = (
            self._approved_speaker_plan()
        )
        shot = approved["shots"][0]
        base = self.output.with_name("broll-001-base.mp4")
        base_record = normalize_broll.normalize_selection(
            shot["candidates"], shot, self.timeline, base,
            lut=self.selected_lut_path,
        )
        result = speaker_inset.render_delivery_composite(
            plan=approved, shot=shot, analysis=analysis, agent_input=agent_input,
            preview=preview, clearance=clearance, timeline=self.timeline,
            style=approved["speaker_inset_style"], base_video=base,
            review_video=review_video, destination=self.output,
            project_root=self.root,
        )

        self.assertEqual(self.output, result["path"])
        self.assertEqual(broll_plan.sha256_file(self.output), result["sha256"])
        self.assertFalse(result["probe"]["has_audio"])
        self.assertEqual(base_record["probe"]["fps"], result["probe"]["fps"])
        still = self.root / "delivery-speaker.png"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5",
            "-i", str(self.output), "-frames:v", "1", str(still),
        ], check=True, capture_output=True)
        with Image.open(still).convert("RGB") as image:
            self.assertGreater(image.getpixel((8, 8))[2], image.getpixel((8, 8))[0])

    def test_normalize_plan_precomposes_speaker_and_persists_delivery_bindings(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)

        with mock.patch.object(
                speaker_inset, "render_delivery_composite",
                wraps=speaker_inset.render_delivery_composite) as render:
            result = normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        shot = result["shots"][0]
        normalized = shot["normalized"]
        self.assertEqual(
            normalize_broll.delivery_encoder_args(),
            render.call_args.kwargs["delivery_encoder_args"],
        )
        self.assertEqual("normalized", shot["status"])
        self.assertEqual("cache/b-roll/normalized/broll-001.mp4", normalized["path"])
        self.assertEqual(
            "cache/b-roll/normalized/broll-001-base.mp4",
            normalized["broll_base"]["path"],
        )
        base = self.root / "work" / normalized["broll_base"]["path"]
        self.assertEqual(normalized["broll_base"]["sha256"], broll_plan.sha256_file(base))
        self.assertEqual(
            normalize_broll.INTERMEDIATE_PROFILE,
            normalized["intermediate_profile"],
        )
        self.assertEqual(
            normalize_broll.INTERMEDIATE_PROFILE,
            normalized["broll_base"]["intermediate_profile"],
        )
        self.assertEqual({
            "kind": "speaker-inset",
            "layout_preset": "corner-pip",
            "project_primary_preset": "corner-pip",
            "review_id": approved["review"]["review_id"],
            "selection_sha256": approved["selection"]["sha256"],
            "analysis_sha256": approved["speaker_inset"]["analysis"]["sha256"],
            "agent_input_sha256": approved["speaker_inset"]["agent_input"]["sha256"],
            "preview_sha256": approved["speaker_inset"]["preview"]["sha256"],
            "clearance_sha256": approved["speaker_inset"]["clearance"]["sha256"],
            "style_sha256": broll_plan.canonical_sha256(approved["speaker_inset_style"]),
            "review_video_sha256": approved["input_hashes"]["review_video_sha256"],
        }, normalized["composition"])
        self.assertEqual(normalized["sha256"], broll_plan.sha256_file(self.output))
        self.assertEqual(normalized, projectlib.load_json(self.plan_path)["shots"][0]["normalized"])

    def test_normalize_plan_delivers_primary_and_justified_secondary_presets(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan(
            secondary={"preset": "focused-panel", "anchor": "lower-center"},
        )
        projectlib.write_json(self.plan_path, approved)

        result = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )

        self.assertEqual(2, len(result["shots"]))
        self.assertEqual(
            ["corner-pip", "focused-panel"],
            [shot["normalized"]["composition"]["layout_preset"] for shot in result["shots"]],
        )
        self.assertEqual(
            ["corner-pip", "corner-pip"],
            [
                shot["normalized"]["composition"]["project_primary_preset"]
                for shot in result["shots"]
            ],
        )
        for index, shot in enumerate(result["shots"], 1):
            self.assertEqual("normalized", shot["status"])
            self.assertTrue(
                (self.root / "work" / shot["normalized"]["path"]).is_file(),
                f"shot {index} composite was not published",
            )

    def test_normalize_plan_reuses_current_speaker_base_and_composite(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        first = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )

        with (
            mock.patch.object(normalize_broll, "normalize_selection", wraps=normalize_broll.normalize_selection) as normalize,
            mock.patch.object(speaker_inset, "render_delivery_composite", wraps=speaker_inset.render_delivery_composite) as render,
        ):
            second = normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        self.assertEqual(first, second)
        normalize.assert_not_called()
        render.assert_not_called()

    def test_changed_clearance_rerenders_composite_and_reuses_base_components(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        first = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        first_normalized = first["shots"][0]["normalized"]
        first_base_sha256 = first_normalized["broll_base"]["sha256"]
        first_composite_sha256 = first_normalized["sha256"]

        revised, _, _, _, _, review_video = self._approved_speaker_plan(
            clearance_mode="pure_broll",
        )
        self.assertNotEqual(
            approved["speaker_inset"]["clearance"]["sha256"],
            revised["speaker_inset"]["clearance"]["sha256"],
        )
        projectlib.write_json(self.plan_path, revised)

        with (
            mock.patch.object(
                normalize_broll, "normalize_shot", wraps=normalize_broll.normalize_shot,
            ) as normalize_component,
            mock.patch.object(
                speaker_inset, "render_delivery_composite",
                wraps=speaker_inset.render_delivery_composite,
            ) as render,
        ):
            second = normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        second_normalized = second["shots"][0]["normalized"]
        normalize_component.assert_not_called()
        render.assert_called_once()
        self.assertEqual(first_base_sha256, second_normalized["broll_base"]["sha256"])
        self.assertNotEqual(first_composite_sha256, second_normalized["sha256"])

    def test_clearance_authorized_all_pure_broll_normalizes_and_verifies(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan(
            preset="full-bleed-wash", anchor="upper-center",
            clearance_mode="pure_broll",
        )
        projectlib.write_json(self.plan_path, approved)

        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        verified, _ = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, review_video,
        )

        self.assertEqual(
            "full-bleed-wash",
            normalized["shots"][0]["normalized"]["composition"]["layout_preset"],
        )
        self.assertEqual("verified", verified["shots"][0]["status"])

    def test_base_render_failure_preserves_existing_speaker_composite(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        published_bytes = self.output.read_bytes()
        base_path = self.root / "work" / normalized["shots"][0]["normalized"]["broll_base"]["path"]
        base_bytes = base_path.read_bytes()
        projectlib.write_json(self.plan_path, approved)

        with (
            mock.patch.object(
                normalize_broll, "normalize_selection",
                side_effect=RuntimeError("base render failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "base render failed"),
        ):
            normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        self.assertEqual(published_bytes, self.output.read_bytes())
        self.assertEqual(base_bytes, base_path.read_bytes())
        self.assertEqual("selected", projectlib.load_json(self.plan_path)["shots"][0]["status"])
        self.assertFalse(self.output.with_suffix(".part.mp4").exists())
        self.assertFalse(base_path.with_suffix(".part.mp4").exists())
        self.assertFalse(self.plan_path.with_suffix(".part.json").exists())
        self.assertFalse(any(self.output.parent.glob("broll-001-segment-*")))

    def test_composite_render_failure_preserves_existing_speaker_composite(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        published_bytes = self.output.read_bytes()
        base_path = self.root / "work" / normalized["shots"][0]["normalized"]["broll_base"]["path"]
        projectlib.write_json(self.plan_path, approved)

        with (
            mock.patch.object(
                speaker_inset, "render_delivery_composite",
                side_effect=RuntimeError("composite render failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "composite render failed"),
        ):
            normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        self.assertEqual(published_bytes, self.output.read_bytes())
        self.assertFalse(base_path.exists())
        self.assertEqual("selected", projectlib.load_json(self.plan_path)["shots"][0]["status"])
        self.assertFalse(self.output.with_suffix(".part.mp4").exists())
        self.assertFalse(base_path.with_suffix(".part.mp4").exists())
        self.assertFalse(self.plan_path.with_suffix(".part.json").exists())
        self.assertFalse(any(self.output.parent.glob("broll-001-segment-*")))

    def test_stale_review_video_preserves_existing_speaker_outputs(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        final_bytes = self.output.read_bytes()
        base_path = self.root / "work" / normalized["shots"][0]["normalized"]["broll_base"]["path"]
        base_bytes = base_path.read_bytes()
        review_video.write_bytes(b"changed-review-video")

        with self.assertRaisesRegex(ValueError, "review video SHA-256 is stale"):
            normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

        self.assertEqual(final_bytes, self.output.read_bytes())
        self.assertEqual(base_bytes, base_path.read_bytes())

    def test_standard_broll_rejects_explicit_review_video(self):
        review_video = self._review_video()
        with self.assertRaisesRegex(
                ValueError, "review_video is only valid for enabled speaker inset"):
            normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path, review_video=review_video,
            )

    def test_speaker_composition_rejects_stale_bindings_and_layout_identity(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        mutations = {
            "review_id": "223e4567-e89b-12d3-a456-426614174000",
            "selection_sha256": "0" * 64,
            "analysis_sha256": "1" * 64,
            "agent_input_sha256": "2" * 64,
            "preview_sha256": "3" * 64,
            "clearance_sha256": "4" * 64,
            "style_sha256": "5" * 64,
            "review_video_sha256": "6" * 64,
            "layout_preset": "focused-panel",
            "project_primary_preset": "full-bleed-wash",
        }
        composition_sha256 = broll_plan.canonical_sha256(
            normalized["shots"][0]["normalized"]["composition"]
        )
        for field, value in mutations.items():
            stale = copy.deepcopy(normalized)
            stale["shots"][0]["normalized"]["composition"][field] = value
            with self.subTest(field=field):
                errors = broll_plan.validate_plan(
                    stale, self.timeline, self.transcript,
                    project=self.project, project_root=self.root, verify_files=True,
                )
                self.assertTrue(any("composition" in error for error in errors), errors)
                verified = copy.deepcopy(stale)
                verified["shots"][0].update({
                    "status": "verified", "verification": {
                        "status": "pass", "composition_sha256": composition_sha256,
                    },
                })
                with self.assertRaisesRegex(ValueError, "composition"):
                    broll_plan._verified_overlays(verified)

    def test_verify_speaker_composite_binds_final_composition_and_summary(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )

        verified, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, review_video,
        )

        shot = verified["shots"][0]
        self.assertEqual("verified", shot["status"])
        self.assertEqual(
            broll_plan.canonical_sha256(shot["normalized"]["composition"]),
            shot["verification"]["composition_sha256"],
        )
        for binding in shot["verification"]["stills"].values():
            self.assertTrue((self.root / binding["path"]).is_file())
        summary = artifacts["summary"].read_text(encoding="utf-8")
        self.assertIn("Project primary preset: `corner-pip`", summary)
        self.assertIn("Shot layout preset: `corner-pip`", summary)
        self.assertIn(
            f"Final composite SHA-256: `{shot['normalized']['sha256']}`", summary,
        )
        self.assertIn(
            f"B-roll base SHA-256: `{shot['normalized']['broll_base']['sha256']}`", summary,
        )
        for field, value in normalized["shots"][0]["normalized"]["composition"].items():
            self.assertIn(f"{field}: `{value}`", summary)

    def test_verify_speaker_composite_rejects_altered_base_bytes(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalized = normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        base_path = (
            self.root / "work" /
            normalized["shots"][0]["normalized"]["broll_base"]["path"]
        )
        base_path.write_bytes(b"altered base")

        with self.assertRaisesRegex(ValueError, "B-roll plan|normalized|SHA-256"):
            check_broll.verify_plan(
                self.plan_path, self.timeline_path, self.root, review_video,
            )

    def _normalized_for_check(self):
        video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        projectlib.write_json(self.plan_path, self._approve(plan))
        return video, normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        )

    def _selected_and_skipped_for_check(self):
        video = self._review_video()
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        skipped = copy.deepcopy(plan["shots"][0])
        skipped.update({
            "id": "skipped",
            "program_range": {"start_s": round(90 * frame, 9), "end_s": round(120 * frame, 9)},
            "source_ranges": [{"clip_id": "one", "start_s": round(90 * frame, 9), "end_s": round(120 * frame, 9)}],
            "transcript_evidence": {"words": [self.mapped_words[2]]},
        })
        skipped["candidates"][0]["id"] = "skipped-asset"
        plan["shots"].append(skipped)
        decisions = [
            {"id": "shot", "decision": "select", "candidate_id": "asset",
             "source_trim": {"start_s": 0.25, "end_s": 1.25}},
            {"id": "skipped", "decision": "skip"},
        ]
        approved = broll_plan.apply_review(
            plan, self.review_for(plan, decisions), mode="agent", actor="agent",
            rationale="Relevant footage.",
        )
        projectlib.write_json(self.plan_path, approved)
        ranking_path = self.root / "work/b-roll/candidate-ranking.json"
        projectlib.write_json(ranking_path, {
            "schema_version": 1,
            "shots": [
                {"shot_id": "shot", "top3": ["asset"]},
                {"shot_id": "skipped", "top3": []},
            ],
        })
        return video, normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path
        ), ranking_path

    def test_verify_writes_internal_coverage_summary_for_selected_and_skipped_shots(self):
        video, _, _ = self._selected_and_skipped_for_check()

        verified, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video,
        )

        coverage_path = self.root / "work/b-roll/coverage-summary.json"
        self.assertTrue(coverage_path.is_file(), "verify_plan must publish coverage-summary.json")
        coverage = projectlib.load_json(coverage_path)
        self.assertEqual(1, coverage["schema_version"])
        self.assertEqual("main", coverage["timeline_id"])
        self.assertEqual(10.0, coverage["program_duration_s"])
        self.assertEqual("dynamic-social", coverage["profile"])
        self.assertEqual(0.40, coverage["target_min_ratio"])
        self.assertEqual(0.70, coverage["target_max_ratio"])
        frame = 1001 / 30000
        selected_duration = round(30 * frame, 9)
        planned_duration = round(60 * frame, 9)
        self.assertEqual(
            {"duration_s": selected_duration, "ratio": round(selected_duration / 10.0, 9), "status": "below_target"},
            coverage["selected"],
        )
        self.assertEqual(
            {"duration_s": planned_duration, "ratio": round(planned_duration / 10.0, 9), "status": "below_target"},
            coverage["planned"],
        )
        self.assertEqual(
            {"duration_s": 0.0, "ratio": 0.0, "status": "below_target"},
            coverage["shortlisted"],
        )
        self.assertEqual(broll_plan.sha256_file(self.plan_path), coverage["plan_sha256"])
        self.assertIsNone(coverage["ranking_sha256"])
        self.assertEqual("verified", verified["shots"][0]["status"])
        self.assertEqual("skipped", verified["shots"][1]["status"])

        final_video = self.root / "final/final-video.mp4"
        final_video.write_bytes(video.read_bytes())
        visual_subject = broll_plan.canonical_sha256(broll_plan.visual_review_subject(verified))
        _, published = check_broll.complete_visual_review(
            self.plan_path, self.root, self._visual_review(visual_subject), final_video,
        )
        user_facing = (
            artifacts["summary"].read_text(encoding="utf-8"),
            projectlib.load_json(published["receipt"]),
            verified["review"]["rationale"],
            verified["decision"]["rationale"],
        )
        forbidden = (
            "coverage_summary", "target_min_ratio", "target_max_ratio",
            "planned_ratio", "shortlist_ratio", "selected_ratio",
            "below_target", "within_target", "above_target",
        )
        for value in forbidden:
            for output in user_facing:
                with self.subTest(value=value, output_type=type(output).__name__):
                    self.assertNotIn(value, json.dumps(output, sort_keys=True))

    def test_verify_writes_below_target_selected_coverage_for_all_skipped_plan(self):
        video = self._review_video()
        plan = copy.deepcopy(self.base_plan)
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        approved = broll_plan.apply_review(
            plan, self.review_for(plan, [{"id": "shot", "decision": "skip"}]),
            mode="agent", actor="agent", rationale="Relevant footage.",
        )
        projectlib.write_json(self.plan_path, approved)

        verified, _ = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video,
        )

        coverage_path = self.root / "work/b-roll/coverage-summary.json"
        self.assertTrue(coverage_path.is_file(), "verify_plan must publish coverage-summary.json")
        coverage = projectlib.load_json(coverage_path)
        self.assertEqual(
            {"duration_s": 0.0, "ratio": 0.0, "status": "below_target"},
            coverage["selected"],
        )
        self.assertEqual("skipped", verified["shots"][0]["status"])

    def test_verify_ignores_unbound_malformed_ranking_for_coverage(self):
        video, _, ranking_path = self._selected_and_skipped_for_check()
        ranking_path.write_text(
            json.dumps({"shots": [{"shot_id": "shot", "top3": ["asset"]}]}),
            encoding="utf-8",
        )

        verified, _ = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, video,
        )

        coverage = projectlib.load_json(self.root / "work/b-roll/coverage-summary.json")
        self.assertEqual(
            {"duration_s": 0.0, "ratio": 0.0, "status": "below_target"},
            coverage["shortlisted"],
        )
        self.assertIsNone(coverage["ranking_sha256"])
        self.assertEqual("verified", verified["shots"][0]["status"])

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
        self.assertEqual(self.output.resolve(), record["path"])
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

    def test_enabled_speaker_inset_fails_closed_until_delivery_composite_exists(self):
        plan = copy.deepcopy(self.plan)
        plan["speaker_inset_style"] = BrollPlanTests._speaker_style()
        projectlib.write_json(self.plan_path, plan)

        with self.assertRaisesRegex(
                ValueError, "enabled speaker inset requires delivery composite"):
            normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root,
                lut=self.selected_lut_path,
            )

        self.assertFalse(self.output.exists())

    def test_canonical_segment_normalization_uses_exact_source_range_without_silent_trim(self):
        source = self._video("canonical.mp4")
        candidate, shot = self._video_shot(source)
        frame_aligned_end = 30 * 1001 / 30000
        shot["program_range"]["end_s"] = frame_aligned_end
        shot["selected"] = {"segments": [{
            "candidate_id": "asset",
            "source_range": {"start_s": 0.25, "end_s": 0.25 + frame_aligned_end},
            "program_range": {"start_s": 0.0, "end_s": frame_aligned_end},
            "playback_rate": 1.0,
        }]}
        commands = []
        real_run = subprocess.run

        def record(command, *args, **kwargs):
            commands.append(command)
            return real_run(command, *args, **kwargs)

        with mock.patch.object(normalize_broll.subprocess, "run", side_effect=record):
            result = normalize_broll.normalize_shot(
                candidate, shot, self.timeline, self.output,
            )

        render = next(command for command in commands if command[0] == "ffmpeg" and "-vf" in command)
        filters = render[render.index("-vf") + 1]
        self.assertNotIn("trim=duration", filters)
        self.assertEqual("canonical", result["selection_format"])
        self.assertAlmostEqual(frame_aligned_end, result["source_duration_s"])
        self.assertAlmostEqual(frame_aligned_end, result["effective_duration_s"])
        self.assertAlmostEqual(frame_aligned_end, result["program_duration_s"])

        invalid = copy.deepcopy(shot)
        invalid["selected"]["segments"][0]["source_range"]["end_s"] = 1.75
        with mock.patch.object(normalize_broll.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "one timeline frame"):
                normalize_broll.normalize_shot(
                    candidate, invalid, self.timeline,
                    self.output.with_name("invalid.mp4"),
                )
            run.assert_not_called()

    def test_canonical_segment_normalization_keeps_exact_timeline_frame_count(self):
        self.timeline.update({"fps": {"num": 60, "den": 1}})
        source = self.candidates / "25fps-frame-boundary.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=128x96:rate=25",
            "-t", "7", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-video_track_timescale", "25",
            str(source),
        ], check=True, capture_output=True)
        candidate, shot = self._video_shot(source)
        candidate.update({
            "sha256": broll_plan.sha256_file(source),
            "probe": {"duration_s": 7.0},
        })
        expected_frames = 243
        duration = expected_frames / 60
        shot["program_range"] = {"start_s": 0.0, "end_s": duration}
        shot["selected"] = {"segments": [{
            "candidate_id": "asset",
            "source_range": {"start_s": 0.0, "end_s": duration * 1.5},
            "program_range": {"start_s": 0.0, "end_s": duration},
            "playback_rate": 1.5,
        }]}

        output = self.output.with_name("25fps-frame-boundary.mp4")
        normalize_broll.normalize_shot(candidate, shot, self.timeline, output)

        probe = subprocess.run([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "json", str(output),
        ], check=True, capture_output=True, text=True)
        self.assertEqual(
            expected_frames,
            int(json.loads(probe.stdout)["streams"][0]["nb_read_frames"]),
        )

    def test_fixed_speed_segments_use_source_direct_hard_concat(self):
        frame = 1001 / 30000
        boundary = 15 * frame
        shot_end = 30 * frame
        first_source = self._video("speed-half.mp4")
        second_source = self._video("speed-double.mp4")
        first = {
            "id": "first", "media_type": "video",
            "cache_path": first_source.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(first_source),
            "probe": {"duration_s": 2.0},
        }
        second = {
            "id": "second", "media_type": "video",
            "cache_path": second_source.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(second_source),
            "probe": {"duration_s": 2.0},
        }
        shot = {
            "id": "shot", "status": "selected",
            "program_range": {"start_s": 0.0, "end_s": shot_end},
            "candidates": [first, second],
            "selected": {"segments": [
                {
                    "candidate_id": "first",
                    "source_range": {"start_s": 0.0, "end_s": boundary * 0.5},
                    "program_range": {"start_s": 0.0, "end_s": boundary},
                    "playback_rate": 0.5,
                },
                {
                    "candidate_id": "second",
                    "source_range": {"start_s": 0.0, "end_s": boundary * 2.0},
                    "program_range": {"start_s": boundary, "end_s": shot_end},
                    "playback_rate": 2.0,
                },
            ]},
        }
        commands = []
        real_run = subprocess.run

        def record(command, *args, **kwargs):
            commands.append(command)
            return real_run(command, *args, **kwargs)

        with mock.patch.object(normalize_broll.subprocess, "run", side_effect=record):
            result = normalize_broll.normalize_selection(
                [first, second], shot, self.timeline, self.output,
            )

        self.assertEqual("canonical", result["selection_format"])
        self.assertEqual(normalize_broll.INTERMEDIATE_PROFILE, result["intermediate_profile"])
        self.assertEqual(2, len(result["source_segments"]))
        self.assertNotIn("segments", result)
        self.assertNotIn("concat_sha256", result)
        self.assertAlmostEqual(shot_end, result["probe"]["duration_s"], delta=frame)
        self.assertFalse(result["probe"]["has_audio"])
        for index, segment in enumerate(result["source_segments"], 1):
            self.assertFalse((self.output.parent / f"broll-001-segment-{index:02d}.mp4").exists())
            self.assertEqual(shot["selected"]["segments"][index - 1], segment["segment"])
        render = next(
            command for command in commands
            if command[0] == "ffmpeg" and "-filter_complex" in command
        )
        filters = render[render.index("-filter_complex") + 1]
        self.assertIn("/0.5", filters)
        self.assertIn("/2", filters)
        self.assertIn("concat=n=2:v=1:a=0", filters)
        self.assertEqual(1, sum(
            command[0] == "ffmpeg" and "-filter_complex" in command
            for command in commands
        ))

    def test_multisegment_retry_rebuilds_whole_shot_without_component_state(self):
        frame = 1001 / 30000
        boundary, shot_end = 30 * frame, 60 * frame
        plan = copy.deepcopy(self.base_plan)
        review_video = self._review_video()
        plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(review_video)
        first = plan["shots"][0]["candidates"][0]
        second_source = self._video("resume-second.mp4")
        second = copy.deepcopy(first)
        second.update({
            "id": "asset-2",
            "cache_path": second_source.relative_to(self.root / "work").as_posix(),
            "sha256": broll_plan.sha256_file(second_source),
            "bytes": second_source.stat().st_size,
        })
        shot = plan["shots"][0]
        shot["program_range"] = {"start_s": 0.0, "end_s": shot_end}
        shot["source_ranges"] = [{"clip_id": "one", "start_s": 0.0, "end_s": shot_end}]
        shot["candidates"] = [first, second]
        segments = [
            {
                "candidate_id": first["id"],
                "source_range": {"start_s": 0.0, "end_s": boundary},
                "program_range": {"start_s": 0.0, "end_s": boundary},
                "playback_rate": 1.0,
            },
            {
                "candidate_id": second["id"],
                "source_range": {"start_s": 0.0, "end_s": boundary},
                "program_range": {"start_s": boundary, "end_s": shot_end},
                "playback_rate": 1.0,
            },
        ]
        review = self.review_for(plan, [{
            "id": "shot", "decision": "select", "segments": segments,
        }], timeline_fps=copy.deepcopy(self.timeline["fps"]))
        approved = broll_plan.apply_review(
            plan, review, mode="agent", actor="agent", rationale="Relevant footage.",
            timeline=self.timeline,
        )
        projectlib.write_json(self.plan_path, approved)
        real_normalize = normalize_broll.normalize_selection

        with mock.patch.object(
                normalize_broll, "normalize_selection",
                side_effect=RuntimeError("shot filtergraph failed")):
            with self.assertRaisesRegex(RuntimeError, "shot filtergraph failed"):
                normalize_broll.normalize_plan(
                    self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path,
                )
        self.assertEqual("selected", projectlib.load_json(self.plan_path)["shots"][0]["status"])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".part.mp4").exists())
        self.assertFalse(self.plan_path.with_suffix(".part.json").exists())
        self.assertFalse(any(self.output.parent.glob("broll-001-segment-*")))

        with mock.patch.object(
                normalize_broll, "normalize_selection", wraps=real_normalize) as render:
            updated = normalize_broll.normalize_plan(
                self.plan_path, self.timeline_path, self.root, lut=self.selected_lut_path,
            )
        self.assertEqual(1, render.call_count)
        self.assertEqual(["asset", "asset-2"], [
            candidate["id"] for candidate in render.call_args.args[0]
        ])
        self.assertEqual("normalized", updated["shots"][0]["status"])
        self.assertEqual(2, len(updated["shots"][0]["normalized"]["source_segments"]))
        self.assertNotIn("segments", updated["shots"][0]["normalized"])
        verified, artifacts = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, review_video,
        )
        summary = artifacts["summary"].read_text(encoding="utf-8")
        self.assertEqual("verified", verified["shots"][0]["status"])
        for text in (
                "source-direct single-filtergraph", "Intermediate profile",
                "Source segment 1", "Source segment 2", "asset-2", "Playback rate"):
            self.assertIn(text, summary)
        self.assertNotIn("Legacy concat SHA-256", summary)

    def test_legacy_component_record_remains_readable_without_new_profile_claim(self):
        frame = 1001 / 30000
        boundary, shot_end = 30 * frame, 60 * frame
        first_source = self._video("legacy-component-1.mp4")
        second_source = self._video("legacy-component-2.mp4")
        candidates = []
        for candidate_id, source in (("first", first_source), ("second", second_source)):
            candidates.append({
                "id": candidate_id, "media_type": "video",
                "cache_path": source.relative_to(self.root / "work").as_posix(),
                "sha256": broll_plan.sha256_file(source),
                "probe": {"duration_s": 2.0},
                "provenance": {"source_type": "local", "license": "owned"},
            })
        segments = [{
            "candidate_id": candidate["id"],
            "source_range": {"start_s": 0.0, "end_s": boundary},
            "program_range": {
                "start_s": index * boundary, "end_s": (index + 1) * boundary,
            },
            "playback_rate": 1.0,
        } for index, candidate in enumerate(candidates)]
        shot = {
            "id": "shot", "status": "selected",
            "program_range": {"start_s": 0.0, "end_s": shot_end},
            "source_ranges": [{"clip_id": "one", "start_s": 0.0, "end_s": shot_end}],
            "transcript_evidence": {"words": [{"word": "factory"}]},
            "candidates": candidates,
            "selected": {"segments": copy.deepcopy(segments)},
        }
        component_records = []
        for index, (candidate, segment) in enumerate(zip(candidates, segments), 1):
            component_output = normalize_broll._segment_output(self.output, index)
            component_shot = {
                "id": "shot", "status": "selected",
                "program_range": copy.deepcopy(segment["program_range"]),
                "candidates": [candidate],
                "selected": {"segments": [copy.deepcopy(segment)]},
            }
            component = normalize_broll.normalize_shot(
                candidate, component_shot, self.timeline, component_output,
            )
            component_records.append({
                "candidate_id": candidate["id"],
                "segment": copy.deepcopy(segment),
                "source_path": component["source_path"],
                "source_sha256": component["source_sha256"],
                "normalized_path": component_output.relative_to(
                    self.root / "work"
                ).as_posix(),
                "normalized_sha256": component["sha256"],
                "probe": copy.deepcopy(component["probe"]),
                "source_duration_s": boundary,
                "effective_duration_s": boundary,
                "program_duration_s": boundary,
                "playback_rate": 1.0,
            })
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(normalize_broll._segment_output(self.output, 1)),
            "-i", str(normalize_broll._segment_output(self.output, 2)),
            "-filter_complex",
            "[0:v]setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[outv]",
            "-map", "[outv]", "-an", *normalize_broll.delivery_encoder_args(),
            str(self.output),
        ], check=True, capture_output=True)
        probe = normalize_broll._probe(self.output)
        legacy = {
            "path": self.output.relative_to(self.root / "work").as_posix(),
            "selection_format": "canonical",
            "segments": component_records,
            "source_paths": [candidate["cache_path"] for candidate in candidates],
            "source_sha256s": [candidate["sha256"] for candidate in candidates],
            "sha256": broll_plan.sha256_file(self.output),
            "concat_sha256": broll_plan.sha256_file(self.output),
            "probe": probe,
            "program_duration_s": shot_end,
        }
        normalize_broll._validate_normalized(
            legacy, candidates, shot, self.timeline, self.output.resolve(),
            self.root.resolve(), {},
        )
        self.assertNotIn("intermediate_profile", legacy)

        shot["normalized"] = legacy
        stage = self.root / "work/cache/b-roll/legacy-summary"
        destination = self.root / "review/03-b-roll/legacy-summary"
        stage.mkdir(parents=True)
        stills = {}
        for label in ("first", "middle", "last"):
            still = stage / f"{label}.jpg"
            still.write_bytes(label.encode("ascii"))
            stills[label] = still
        summary_path = self.root / "legacy-summary.md"
        check_broll._summary(
            {
                "timeline_id": "main",
                "input_hashes": {
                    "timeline_sha256": "1" * 64,
                    "review_video_sha256": "2" * 64,
                },
                "review": {
                    "review_id": "legacy-review",
                    "plan_sha256": "3" * 64,
                    "candidate_manifest_sha256": "4" * 64,
                },
            },
            [(1, shot, candidates, None)],
            [(None, None, {"first": 0.0, "middle": boundary, "last": shot_end - frame}, stills)],
            {}, self.root.resolve(), stage, destination, summary_path,
        )
        summary = summary_path.read_text(encoding="utf-8")
        self.assertIn("legacy component-based", summary)
        self.assertIn("legacy unrecorded", summary)
        self.assertIn("Legacy concat SHA-256", summary)
        self.assertNotIn("source-direct single-filtergraph", summary)

    def test_legacy_long_trim_remains_recoverable_and_is_reported(self):
        source = self._video("legacy-long.mp4")
        candidate, shot = self._video_shot(source)
        shot["selected"]["source_trim"] = {"start_s": 0.25, "end_s": 1.75}

        result = normalize_broll.normalize_shot(
            candidate, shot, self.timeline, self.output,
        )

        self.assertEqual("legacy", result["selection_format"])
        self.assertEqual(
            {"start_s": 0.25, "end_s": 1.75},
            result["legacy_requested_source_range"],
        )
        self.assertAlmostEqual(1.0, result["effective_duration_s"])

    def test_normalize_discards_source_timecode_data_track(self):
        source = self.candidates / "timecoded.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=128x96:rate=24",
            "-t", "2", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-timecode", "01:00:49:12", str(source),
        ], check=True, capture_output=True)
        candidate, shot = self._video_shot(source)

        record = normalize_broll.normalize_shot(candidate, shot, self.timeline, self.output)

        self.assertFalse(record["probe"]["has_data"])
        self.assertFalse(record["probe"]["has_audio"])

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
        persisted_plan_bytes = self.plan_path.read_bytes()
        first_record_sha256 = persisted["shots"][0]["normalized"]["sha256"]
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
        self.assertEqual(persisted_plan_bytes, self.plan_path.read_bytes())
        self.assertEqual(
            first_record_sha256,
            projectlib.load_json(self.plan_path)["shots"][0]["normalized"]["sha256"],
        )
        self.assertEqual("selected", projectlib.load_json(self.plan_path)["shots"][1]["status"])
        self.assertEqual(first_bytes, self.output.read_bytes())
        self.assertFalse(second_output.exists())
        self.assertFalse(second_output.with_suffix(".part.mp4").exists())
        self.assertFalse(self.plan_path.with_suffix(".part.json").exists())
        self.assertFalse(any(self.output.parent.glob("broll-002-segment-*")))

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
            "Selection format", "Source duration", "Effective duration", "Program duration",
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

    def test_speaker_visual_review_requires_three_composite_checks(self):
        approved, _, _, _, _, review_video = self._approved_speaker_plan()
        projectlib.write_json(self.plan_path, approved)
        normalize_broll.normalize_plan(
            self.plan_path, self.timeline_path, self.root,
            lut=self.selected_lut_path, review_video=review_video,
        )
        verified, _ = check_broll.verify_plan(
            self.plan_path, self.timeline_path, self.root, review_video,
        )
        final_video = self.root / "final/final-video.mp4"
        final_video.write_bytes(review_video.read_bytes())
        plan_sha256 = broll_plan.canonical_sha256(
            broll_plan.visual_review_subject(verified)
        )
        with self.assertRaisesRegex(ValueError, "visual checks"):
            check_broll.complete_visual_review(
                self.plan_path, self.root, self._visual_review(plan_sha256),
                final_video,
            )

        checks = copy.deepcopy(self._visual_review(plan_sha256)["checks"])
        checks.update({
            "speaker_layout_fidelity": True,
            "speaker_legibility": True,
            "broll_focal_clearance": True,
        })
        completed, published = check_broll.complete_visual_review(
            self.plan_path, self.root,
            self._visual_review(plan_sha256, checks=checks), final_video,
        )

        self.assertEqual(checks, completed["visual_review"]["checks"])
        report = published["report"].read_text(encoding="utf-8")
        for label in (
                "Speaker layout fidelity", "Speaker legibility", "B-roll focal clearance"):
            self.assertIn(label, report)

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
        frame = self.timeline["fps"]["den"] / self.timeline["fps"]["num"]
        self.transcript = {"segments": [{"words": [
            {"word": "opening", "start": 0.05, "end": 0.35},
            {"word": "closing", "start": 9.65, "end": 9.95},
        ]}]}
        projectlib.write_json(self.transcript_path, self.transcript)
        mapped = projectlib.map_transcript_to_timeline(self.transcript, self.timeline)["segments"][0]["words"]
        plan = copy.deepcopy(self.base_plan)
        first = plan["shots"][0]
        first.update({
            "id": "opening", "program_range": {"start_s": 0, "end_s": round(12 * frame, 9)},
            "source_ranges": [{"clip_id": "one", "start_s": 0, "end_s": round(12 * frame, 9)}],
            "transcript_evidence": {"words": [mapped[0]]},
        })
        second = copy.deepcopy(first)
        second.update({
            "id": "closing", "program_range": {"start_s": round(288 * frame, 9), "end_s": round(299 * frame, 9)},
            "source_ranges": [{"clip_id": "one", "start_s": round(288 * frame, 9), "end_s": round(299 * frame, 9)}],
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


class CandidateAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "work/cache/b-roll/candidate-analysis/media").mkdir(parents=True)
        (self.root / "work/cache/b-roll/candidate-analysis/frames").mkdir(parents=True)

    def tearDown(self): self.temp.cleanup()

    @staticmethod
    def _candidate(candidate_id, provider_id, warning_count=0, status="analyzed"):
        return {
            "candidate_id": candidate_id,
            "provider_id": provider_id,
            "analysis_status": status,
            "hard_checks": {"status": "pass" if status == "analyzed" else "reject"},
            "warnings": [f"warning-{index}" for index in range(warning_count)],
            "analysis_variant": {"file_id": provider_id * 10 + 1},
            "delivery_variant": {"file_id": provider_id * 10 + 2},
            "analysis_media": {"path": f"work/cache/b-roll/candidate-analysis/media/{candidate_id}.mp4", "sha256": f"{provider_id % 10}" * 64, "bytes": 10},
            "samples": [{"frame_path": f"work/cache/b-roll/candidate-analysis/frames/{candidate_id}-{index}.png", "sha256": f"{index}" * 64, "perceptual_hash": f"{index:016x}"} for index in range(1, 6)],
        }

    @staticmethod
    def _score(candidate_id, semantic, context, composition, style, **extra):
        return {
            "candidate_id": candidate_id,
            "semantic_fit": semantic,
            "context_fit": context,
            "composition_fit": composition,
            "style_fit": style,
            "text_logo_risk": 0,
            "rationale": f"Concrete assessment for {candidate_id}.",
            "avoid_violation": False,
            "primary_subject_visible": True,
            "near_duplicate_group": None,
            **extra,
        }

    @staticmethod
    def _search_plan():
        return {
            "brief": {
                "density": "dynamic-social",
                "search_context": {
                    "topic": "Factory automation",
                    "visual_direction": "Precise hands-on industrial work",
                    "keywords": ["robotics", " precision "],
                },
            },
            "shots": [{
                "id": "shot",
                "semantic_role": "direct",
                "queries": ["factory process", "assembly line"],
                "candidates": [],
            }],
        }

    @staticmethod
    def _pexels_search_candidate():
        return {
            "id": "shot-101-202",
            "provider_id": 101,
            "duration_s": 2.0,
            "analysis_variant": {"file_id": 202, "download_url": "https://videos.pexels.com/analysis.mp4", "width": 720, "height": 1280},
            "delivery_variant": {"file_id": 303, "download_url": "https://videos.pexels.com/delivery.mp4", "width": 720, "height": 1280},
            "provenance": {"source_type": "pexels", "provider_id": 101, "source_url": "https://www.pexels.com/video/test-101/", "license_url": pexels.LICENSE_URL, "terms_url": pexels.TERMS_URL},
        }

    def _analysis_and_scores(self):
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [{
                "shot_id": "shot",
                "semantic_role": "direct",
                "candidates": [
                    self._candidate("a", 30, warning_count=4),
                    self._candidate("b", 20),
                    self._candidate("c", 10),
                    self._candidate("weak", 40),
                ],
            }],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-07-30T12:00:00+08:00",
            "overall_rationale": "Ranked visible evidence against the transcript claim.",
            "shots": [{
                "shot_id": "shot",
                "candidates": [
                    self._score("a", 4, 4, 1, 1),
                    self._score("b", 4, 3, 4, 4, near_duplicate_group="process-angle"),
                    self._score("c", 4, 3, 3, 4, near_duplicate_group="process-angle"),
                    self._score("weak", 0, 4, 4, 4),
                ],
            }],
        }
        return analysis, scores

    def test_round_robin_merge_preserves_query_and_provider_order(self):
        merged = candidate_analysis.merge_query_results(
            ["factory worker", "assembly line", "precision process"],
            [
                [{"provider_id": 1}, {"provider_id": 4}],
                [{"provider_id": 2}, {"provider_id": 1}, {"provider_id": 5}],
                [{"provider_id": 3}, {"provider_id": 6}],
            ],
            limit=5,
        )
        self.assertEqual([1, 2, 3, 4, 6], [item["provider_id"] for item in merged])
        self.assertEqual(
            [(0, 0, 0), (1, 0, 1), (2, 0, 2), (0, 1, 3), (2, 1, 4)],
            [(item["search"]["query_index"], item["search"]["provider_rank"], item["search"]["merge_rank"]) for item in merged],
        )
        self.assertEqual("precision process", merged[-1]["search"]["query"])

    def test_search_plan_persists_exact_context_and_semantic_role(self):
        plan = self._search_plan()

        result = candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)

        self.assertEqual(plan["brief"]["search_context"], result["search_context"])
        self.assertIsNot(plan["brief"]["search_context"], result["search_context"])
        self.assertEqual("direct", result["shots"][0]["semantic_role"])
        self.assertEqual(plan["shots"][0]["queries"], result["shots"][0]["queries"])

    def test_search_and_ranking_write_internal_coverage_summary_without_ui_fields(self):
        plan = self._search_plan()
        plan["program_duration_s"] = 10.0
        plan["shots"][0]["program_range"] = {"start_s": 1.0, "end_s": 2.0}
        plan_path = self.root / "work/b-roll/broll-plan.json"
        search_path = self.root / "work/b-roll/candidate-search.json"
        ranking_path = self.root / "work/b-roll/candidate-ranking.json"
        projectlib.write_json(plan_path, plan)

        with contextlib.redirect_stdout(io.StringIO()):
            candidate_analysis.main([
                "search", str(self.root), str(plan_path), str(search_path),
                "--orientation", "portrait", "--local-only",
            ])

        coverage_path = self.root / "work/b-roll/coverage-summary.json"
        planned = projectlib.load_json(coverage_path)
        self.assertEqual({"duration_s": 1.0, "ratio": 0.1, "status": "below_target"}, planned["planned"])
        self.assertEqual({"duration_s": 0.0, "ratio": 0.0, "status": "below_target"}, planned["shortlisted"])
        self.assertEqual({"duration_s": 0.0, "ratio": 0.0, "status": "below_target"}, planned["selected"])

        analysis, scores = self._analysis_and_scores()
        analysis_path = self.root / "work/b-roll/candidate-analysis.json"
        scores_path = self.root / "work/cache/b-roll/candidate-ranking-input.json"
        projectlib.write_json(analysis_path, analysis)
        projectlib.write_json(scores_path, scores)
        with contextlib.redirect_stdout(io.StringIO()):
            candidate_analysis.main([
                "rank", str(self.root), str(analysis_path), str(scores_path), str(ranking_path),
            ])

        shortlisted = projectlib.load_json(coverage_path)
        self.assertEqual({"duration_s": 1.0, "ratio": 0.1, "status": "below_target"}, shortlisted["planned"])
        self.assertEqual({"duration_s": 1.0, "ratio": 0.1, "status": "below_target"}, shortlisted["shortlisted"])
        self.assertEqual({"duration_s": 0.0, "ratio": 0.0, "status": "below_target"}, shortlisted["selected"])

    def test_coverage_summary_publication_stages_then_atomically_replaces(self):
        plan = self._search_plan()
        plan["program_duration_s"] = 10.0
        plan["shots"][0]["program_range"] = {"start_s": 1.0, "end_s": 2.0}
        final_path = self.root / "work/b-roll/coverage-summary.json"
        original_write_json = projectlib.write_json
        original_replace = os.replace
        original_payload = {"profile": "previous"}
        original_write_json(final_path, original_payload)
        write_paths = []
        replacements = []

        def staged_write(path, value):
            path = Path(path)
            if path == final_path:
                raise AssertionError("coverage summary must not write directly to final path")
            write_paths.append(path)
            return original_write_json(path, value)

        def atomic_replace(source, destination):
            replacements.append((Path(source), Path(destination)))
            return original_replace(source, destination)

        with mock.patch.object(candidate_analysis.projectlib, "write_json", side_effect=staged_write), \
             mock.patch.object(candidate_analysis.os, "replace", side_effect=atomic_replace):
            candidate_analysis._write_coverage_summary(self.root, plan)

        self.assertEqual(1, len(write_paths))
        self.assertEqual(1, len(replacements))
        self.assertEqual(final_path, replacements[0][1])
        self.assertEqual(final_path.parent, write_paths[0].parent)
        self.assertNotEqual(final_path, write_paths[0])
        self.assertFalse(write_paths[0].exists())
        self.assertEqual("dynamic-social", projectlib.load_json(final_path)["profile"])

    def test_search_plan_requires_strict_search_context(self):
        valid = self._search_plan()["brief"]["search_context"]
        missing = self._search_plan()
        missing["brief"].pop("search_context")
        with self.assertRaises(ValueError):
            candidate_analysis.search_plan(missing, orientation="portrait", include_pexels=False)

        invalid_contexts = [
            None,
            [],
            {**valid, "extra": "not allowed"},
            {"visual_direction": valid["visual_direction"], "keywords": valid["keywords"]},
            {**valid, "topic": " "},
            {**valid, "visual_direction": " "},
            {**valid, "keywords": []},
            {**valid, "keywords": [f"keyword-{index}" for index in range(13)]},
            {**valid, "keywords": ["factory", " "]},
            {**valid, "keywords": ["Factory", " factory "]},
            {**valid, "keywords": [1]},
        ]
        for context in invalid_contexts:
            with self.subTest(context=context):
                plan = self._search_plan()
                plan["brief"]["search_context"] = context
                with self.assertRaises(ValueError):
                    candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)

        for keyword_count in (1, 12):
            with self.subTest(keyword_count=keyword_count):
                plan = self._search_plan()
                plan["brief"]["search_context"]["keywords"] = [f"keyword-{index}" for index in range(keyword_count)]
                candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)

    def test_search_plan_requires_known_semantic_role(self):
        for role in (None, "primary"):
            with self.subTest(role=role):
                plan = self._search_plan()
                if role is None:
                    plan["shots"][0].pop("semantic_role")
                else:
                    plan["shots"][0]["semantic_role"] = role
                with self.assertRaises(ValueError):
                    candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)

    def test_analyze_search_binds_exact_context_role_and_queries(self):
        plan = self._search_plan()
        plan["shots"][0]["program_range"] = {"start_s": 0.0, "end_s": 1.0}
        search = candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)

        analysis = candidate_analysis.analyze_search(
            plan, search, {"width": 720, "height": 1280, "fps": {"num": 30, "den": 1}}, self.root,
        )

        self.assertEqual(plan["brief"]["search_context"], analysis.get("search_context"))
        self.assertEqual(plan["shots"][0]["semantic_role"], analysis["shots"][0].get("semantic_role"))
        self.assertEqual(plan["shots"][0]["queries"], analysis["shots"][0]["queries"])

    def test_analyze_search_rejects_stale_context_role_and_queries(self):
        plan = self._search_plan()
        plan["shots"][0]["program_range"] = {"start_s": 0.0, "end_s": 1.0}
        search = candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)
        search["shots"][0]["merged_candidates"] = [self._pexels_search_candidate()]
        timeline = {"width": 720, "height": 1280, "fps": {"num": 30, "den": 1}}

        for mismatch in ("topic", "semantic_role", "queries"):
            with self.subTest(mismatch=mismatch):
                stale = copy.deepcopy(search)
                if mismatch == "topic":
                    stale["search_context"]["topic"] = "Stale topic"
                elif mismatch == "semantic_role":
                    stale["shots"][0]["semantic_role"] = "supportive"
                else:
                    stale["shots"][0]["queries"].reverse()
                downloader = mock.Mock(side_effect=AssertionError("stale input must fail before download"))
                with self.assertRaises(ValueError):
                    candidate_analysis.analyze_search(
                        plan, stale, timeline, self.root, downloader=downloader,
                    )
                downloader.assert_not_called()

    def test_analyze_search_rejects_unbound_search_shots_before_download(self):
        plan = self._search_plan()
        plan["shots"][0]["program_range"] = {"start_s": 0.0, "end_s": 1.0}
        search = candidate_analysis.search_plan(plan, orientation="portrait", include_pexels=False)
        search["shots"][0]["merged_candidates"] = [self._pexels_search_candidate()]
        timeline = {"width": 720, "height": 1280, "fps": {"num": 30, "den": 1}}

        invalid_shots = {
            "duplicate": search["shots"] + [copy.deepcopy(search["shots"][0])],
            "extra": search["shots"] + [{**copy.deepcopy(search["shots"][0]), "shot_id": "extra"}],
            "non_object": search["shots"] + [None],
            "missing_id": search["shots"] + [{}],
            "invalid_id": search["shots"] + [{"shot_id": 1}],
        }
        for case, shots in invalid_shots.items():
            with self.subTest(case=case):
                invalid = copy.deepcopy(search)
                invalid["shots"] = shots
                downloader = mock.Mock(side_effect=AssertionError("unbound search must fail before download"))
                with self.assertRaises(ValueError):
                    candidate_analysis.analyze_search(
                        plan, invalid, timeline, self.root, downloader=downloader,
                    )
                downloader.assert_not_called()

        ordered_plan = self._search_plan()
        ordered_plan["shots"].append({
            "id": "second-shot",
            "semantic_role": "supportive",
            "queries": ["factory detail", "industrial closeup"],
            "candidates": [],
        })
        ordered_search = candidate_analysis.search_plan(
            ordered_plan, orientation="portrait", include_pexels=False,
        )
        ordered_search["shots"].reverse()
        downloader = mock.Mock(side_effect=AssertionError("reordered search must fail before download"))
        with self.assertRaises(ValueError):
            candidate_analysis.analyze_search(
                ordered_plan, ordered_search, timeline, self.root, downloader=downloader,
            )
        downloader.assert_not_called()

    def test_analysis_validation_requires_strict_context_and_semantic_role(self):
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [{"shot_id": "shot", "semantic_role": "direct", "candidates": []}],
        }
        self.assertEqual([], candidate_analysis.validate_analysis_document(analysis))

        invalid_documents = []
        for field in ("search_context", "semantic_role"):
            missing = copy.deepcopy(analysis)
            if field == "search_context":
                missing.pop(field)
            else:
                missing["shots"][0].pop(field)
            invalid_documents.append(missing)
        invalid_context = copy.deepcopy(analysis)
        invalid_context["search_context"]["topic"] = " "
        invalid_documents.append(invalid_context)
        invalid_role = copy.deepcopy(analysis)
        invalid_role["shots"][0]["semantic_role"] = "primary"
        invalid_documents.append(invalid_role)

        for document in invalid_documents:
            with self.subTest(document=document):
                self.assertTrue(candidate_analysis.validate_analysis_document(document))

    def test_duration_classification_has_frame_tolerance_and_trim_pad_warning(self):
        frame = 1 / 30
        self.assertEqual("reject", candidate_analysis.duration_classification(0.96, 1.0, frame))
        self.assertEqual("warn", candidate_analysis.duration_classification(0.98, 1.0, frame))
        self.assertEqual("pass", candidate_analysis.duration_classification(2.0, 1.0, frame))
        for invalid in (True, "2", float("nan"), float("inf"), 0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                candidate_analysis.duration_classification(invalid, 1.0, frame)

    def test_reclassify_durations_reuses_frozen_evidence_and_requires_semantic_rescore(self):
        candidate = self._candidate("a", 10)
        candidate["hard_checks"]["duration"] = "pass"
        candidate["analysis_media"]["probe"] = {"duration_s": 1.5}
        candidate["samples"][0]["marker"] = "preserve"
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "timeline": {"width": 100, "height": 100, "fps": {"num": 30, "den": 1}},
            "sample_fractions": [0.1, 0.3, 0.5, 0.7, 0.9],
            "shots": [{
                "shot_id": "shot",
                "semantic_role": "direct",
                "program_range": {"start_s": 0.0, "end_s": 1.0},
                "transcript_evidence": {"words": [{"word": "old"}]},
                "candidates": [candidate],
            }],
        }
        plan = {"shots": [{
            "id": "shot",
            "program_range": {"start_s": 0.0, "end_s": 2.0},
            "transcript_evidence": {"words": [{"word": "revised"}]},
            "editorial_reason": "Revised timing.",
            "visual_intent": "Same frozen candidate.",
        }]}

        revised = candidate_analysis.reclassify_durations(
            analysis, plan, {"fps": {"num": 30, "den": 1}},
        )

        result = revised["shots"][0]
        self.assertTrue(result["agent_rescore_required"])
        self.assertEqual({"start_s": 0.0, "end_s": 2.0}, result["program_range"])
        self.assertEqual("revised", result["transcript_evidence"]["words"][0]["word"])
        self.assertEqual("rejected", result["candidates"][0]["analysis_status"])
        self.assertEqual("reject", result["candidates"][0]["hard_checks"]["duration"])
        self.assertEqual("preserve", result["candidates"][0]["samples"][0]["marker"])
        self.assertEqual("analyzed", analysis["shots"][0]["candidates"][0]["analysis_status"])

        restored_plan = copy.deepcopy(plan)
        restored_plan["shots"][0]["program_range"] = {"start_s": 0.0, "end_s": 0.4}
        restored = candidate_analysis.reclassify_durations(
            revised, restored_plan, {"fps": {"num": 30, "den": 1}},
        )["shots"][0]["candidates"][0]
        self.assertEqual("analyzed", restored["analysis_status"])
        self.assertEqual("pass", restored["hard_checks"]["duration"])
        self.assertEqual("pass", restored["hard_checks"]["status"])
        self.assertEqual([], restored["rejection_reasons"])
        self.assertEqual("preserve", restored["samples"][0]["marker"])

    def test_reclassify_duration_uses_selected_program_allocation_and_speed(self):
        candidate = self._candidate("a", 10)
        candidate["hard_checks"]["duration"] = "pass"
        candidate["analysis_media"]["probe"] = {"duration_s": 1.5}
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "timeline": {"width": 100, "height": 100, "fps": {"num": 30, "den": 1}},
            "sample_fractions": [0.1, 0.3, 0.5, 0.7, 0.9],
            "shots": [{
                "shot_id": "shot",
                "semantic_role": "direct",
                "program_range": {"start_s": 0.0, "end_s": 2.0},
                "transcript_evidence": {"words": [{"word": "same"}]},
                "candidates": [candidate],
            }],
        }
        plan = {"shots": [{
            "id": "shot",
            "program_range": {"start_s": 0.0, "end_s": 2.0},
            "transcript_evidence": {"words": [{"word": "same"}]},
            "editorial_reason": "Same timing evidence.",
            "visual_intent": "Same frozen candidate.",
            "review_default": {
                "decision": "select",
                "segments": [{
                    "candidate_id": "a",
                    "source_range": {"start_s": 0.0, "end_s": 2.0},
                    "program_range": {"start_s": 0.0, "end_s": 1.0},
                    "playback_rate": 2.0,
                }],
            },
        }]}

        revised = candidate_analysis.reclassify_durations(
            analysis, plan, {"fps": {"num": 30, "den": 1}},
        )["shots"][0]

        self.assertFalse(revised["agent_rescore_required"])
        result = revised["candidates"][0]
        self.assertEqual("rejected", result["analysis_status"])
        self.assertEqual({
            "program_duration_s": 1.0,
            "playback_rate": 2.0,
            "required_source_duration_s": 2.0,
        }, result["duration_evidence"])

    def test_durable_analysis_write_never_publishes_partial_json(self):
        output = self.root / "work/b-roll/candidate-analysis.json"
        with mock.patch.object(candidate_analysis.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError): candidate_analysis.write_json(output, {"schema_version": 1})
        self.assertFalse(output.exists())
        self.assertEqual([], list(output.parent.glob(f".{output.name}.*")))

    def test_frame_metrics_and_fixed_sampling_are_deterministic_and_json_safe(self):
        media = self.root / "work/cache/b-roll/candidate-analysis/media/candidate.mp4"
        media.write_bytes(b"frozen")
        output = self.root / "work/cache/b-roll/candidate-analysis/frames/candidate"
        calls = []

        def extract(source, timestamp, destination):
            calls.append((Path(source), timestamp))
            value = max(0, min(255, round(timestamp * 20)))
            Image.new("RGB", (80, 120), (value, 40, 200 - value)).save(destination, "PNG")

        first = candidate_analysis.sample_media(
            media, duration_s=5.0, output_dir=output,
            timeline_width=720, timeline_height=1280, extract_frame=extract,
        )
        second = candidate_analysis.sample_media(
            media, duration_s=5.0, output_dir=output,
            timeline_width=720, timeline_height=1280, extract_frame=extract,
        )
        self.assertEqual([0.5, 1.5, 2.5, 3.5, 4.5], [item[1] for item in calls[:5]])
        self.assertEqual(5, len(first["samples"]))
        self.assertEqual(first, second)
        json.dumps(first, allow_nan=False)
        for sample in first["samples"]:
            self.assertTrue((self.root / sample["frame_path"]).is_file())
            self.assertTrue((self.root / sample["crop_path"]).is_file())

    def test_duplicate_evidence_distinguishes_exact_and_perceptual_matches(self):
        candidates = [
            {"candidate_id": "a", "analysis_media": {"sha256": "1" * 64}, "samples": [{"sha256": "2" * 64, "perceptual_hash": "0000000000000000"}]},
            {"candidate_id": "b", "analysis_media": {"sha256": "1" * 64}, "samples": [{"sha256": "3" * 64, "perceptual_hash": "0000000000000000"}]},
            {"candidate_id": "c", "analysis_media": {"sha256": "4" * 64}, "samples": [{"sha256": "5" * 64, "perceptual_hash": "0000000000000001"}]},
        ]
        evidence = candidate_analysis.duplicate_evidence(candidates)
        self.assertEqual(["a", "b"], evidence["exact_groups"][0]["candidate_ids"])
        self.assertEqual(["a", "b", "c"], evidence["perceptual_groups"][0]["candidate_ids"])
        self.assertNotIn("c", evidence["hard_rejected_candidate_ids"])

    def test_project_duplicate_evidence_finds_cross_shot_identity_and_only_hints_series(self):
        exact_a = self._candidate("exact-a", 101)
        exact_b = self._candidate("exact-b", 202)
        exact_a["source_candidate"] = {"provider_candidate_id": "shared-provider-file", "provenance": {"source_type": "pexels", "provider": "Pexels", "creator": "Creator A"}}
        exact_b["source_candidate"] = {"provider_candidate_id": "shared-provider-file", "provenance": {"source_type": "pexels", "provider": "Pexels", "creator": "Creator B"}}
        exact_b["analysis_media"]["sha256"] = "f" * 64
        series_a = self._candidate("series-a", 3000)
        series_b = self._candidate("series-b", 3002)
        for candidate, source_url in (
            (series_a, "https://www.pexels.com/video/coding-session-modern-office-3000/"),
            (series_b, "https://www.pexels.com/video/modern-office-coding-closeup-3002/"),
        ):
            candidate["source_candidate"] = {
                "provider_candidate_id": str(candidate["provider_id"]),
                "provenance": {"source_type": "pexels", "provider": "Pexels", "creator": "Same Creator", "source_url": source_url},
            }
        series_b["analysis_media"]["sha256"] = "e" * 64
        series_b["samples"] = [{**sample, "perceptual_hash": "ffffffffffffffff"} for sample in series_b["samples"]]
        shots = [
            {"shot_id": "first", "queries": ["coding office"], "candidates": [exact_a, series_a, series_b]},
            {"shot_id": "second", "queries": ["software office"], "candidates": [exact_b]},
        ]

        evidence = candidate_analysis.project_duplicate_evidence(shots)

        exact_members = evidence["exact_groups"][0]["members"]
        self.assertEqual([("first", "exact-a"), ("second", "exact-b")], [(item["shot_id"], item["candidate_id"]) for item in exact_members])
        hint = next(item for item in evidence["possible_series"] if {member["candidate_id"] for member in item["members"]} == {"series-a", "series-b"})
        self.assertIn("same_creator", [item["kind"] for item in hint["evidence"]])
        self.assertIn("provider_id_proximity", [item["kind"] for item in hint["evidence"]])
        self.assertEqual("analyzed", exact_b["analysis_status"])

    def test_analysis_validation_rejects_stale_media_and_sample_hashes(self):
        media = self.root / "work/cache/b-roll/candidate-analysis/media/a.mp4"
        frame = self.root / "work/cache/b-roll/candidate-analysis/frames/a.png"
        media.write_bytes(b"media")
        frame.write_bytes(b"frame")
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [{"shot_id": "shot", "semantic_role": "direct", "candidates": [{
                "candidate_id": "a", "analysis_status": "analyzed",
                "analysis_media": {"path": media.relative_to(self.root).as_posix(), "sha256": broll_plan.sha256_file(media), "bytes": media.stat().st_size},
                "samples": [{"frame_path": frame.relative_to(self.root).as_posix(), "sha256": broll_plan.sha256_file(frame)} for _ in range(5)],
                "warnings": [], "hard_checks": {"status": "pass"},
            }]}],
        }
        self.assertEqual([], candidate_analysis.validate_analysis_document(analysis, self.root, verify_files=True))
        frame.write_bytes(b"changed")
        self.assertIn("shot candidate a sample frame SHA-256 is stale", candidate_analysis.validate_analysis_document(analysis, self.root, verify_files=True))
        frame.write_bytes(b"frame"); media.write_bytes(b"changed")
        self.assertIn("shot candidate a analysis media SHA-256 is stale", candidate_analysis.validate_analysis_document(analysis, self.root, verify_files=True))

    def test_agent_scoring_requires_truthful_identity_bounded_integers_and_rationales(self):
        analysis, scores = self._analysis_and_scores()
        invalid_cases = [
            ("mode", "human"), ("actor", ""), ("timestamp", "2026-07-30"),
            ("overall_rationale", ""),
        ]
        for field, value in invalid_cases:
            with self.subTest(field=field):
                invalid = copy.deepcopy(scores); invalid[field] = value
                with self.assertRaises(ValueError): candidate_analysis.rank_candidates(analysis, invalid)
        for field, value in (("semantic_fit", True), ("context_fit", 5), ("composition_fit", -1), ("style_fit", 2.5), ("text_logo_risk", "unknown"), ("rationale", "")):
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(scores); invalid["shots"][0]["candidates"][0][field] = value
                with self.assertRaises(ValueError): candidate_analysis.rank_candidates(analysis, invalid)
        stale = copy.deepcopy(scores); stale["analysis_sha256"] = "0" * 64
        with self.assertRaises(ValueError): candidate_analysis.rank_candidates(analysis, stale)

    def test_agent_global_duplicate_groups_require_truthful_complete_evidence(self):
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [
                {"shot_id": "first", "semantic_role": "direct", "candidates": [self._candidate("a", 1)]},
                {"shot_id": "second", "semantic_role": "supportive", "candidates": [self._candidate("b", 2)]},
            ],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-07-30T12:00:00+08:00",
            "overall_rationale": "Compared the frozen frames across both transcript moments.",
            "near_duplicate_groups": [{
                "group_id": "same-series",
                "match_type": "same_series",
                "actor": "Codex",
                "timestamp": "2026-07-30T12:01:00+08:00",
                "members": [{"shot_id": "first", "candidate_id": "a"}, {"shot_id": "second", "candidate_id": "b"}],
                "rationale": "The same actor, workstation, lighting, and camera setup would repeat visibly across the two moments.",
            }],
            "shots": [
                {"shot_id": "first", "candidates": [self._score("a", 4, 4, 3, 3)]},
                {"shot_id": "second", "candidates": [self._score("b", 4, 3, 3, 3)]},
            ],
        }
        candidate_analysis.rank_candidates(analysis, scores)
        invalid_groups = [
            {"actor": "human"},
            {"timestamp": "2026-07-30"},
            {"rationale": ""},
            {"members": [{"shot_id": "first", "candidate_id": "a"}]},
            {"members": [{"shot_id": "first", "candidate_id": "a"}, {"shot_id": "first", "candidate_id": "a"}]},
            {"members": [{"shot_id": "first", "candidate_id": "a"}, {"shot_id": "second", "candidate_id": "missing"}]},
        ]
        for update in invalid_groups:
            with self.subTest(update=update):
                invalid = copy.deepcopy(scores)
                invalid["near_duplicate_groups"][0].update(update)
                with self.assertRaisesRegex(ValueError, "Agent scoring"):
                    candidate_analysis.rank_candidates(analysis, invalid)

    def test_fixed_ranking_prioritizes_meaning_suppresses_duplicates_and_allows_empty(self):
        analysis, scores = self._analysis_and_scores()
        ranking = candidate_analysis.rank_candidates(analysis, scores)
        shot = ranking["shots"][0]
        self.assertEqual(["a", "b"], shot["top3"])
        self.assertEqual("c", shot["duplicate_groups"][0]["suppressed_candidate_ids"][0])
        weak = next(item for item in shot["candidates"] if item["candidate_id"] == "weak")
        self.assertFalse(weak["eligible"])
        self.assertIn("semantic_fit is zero", weak["ineligibility_reasons"])
        for item in shot["candidates"]:
            if "scores" in item:
                self.assertIn("semantic_fit", item["scores"])
                self.assertIn("rationale", item)

        zero_scores = copy.deepcopy(scores)
        for item in zero_scores["shots"][0]["candidates"]:
            item["semantic_fit"] = 0
        empty = candidate_analysis.rank_candidates(analysis, zero_scores)["shots"][0]
        self.assertEqual([], empty["top3"])
        self.assertEqual("no_eligible_candidates", empty["outcome"])

    def test_semantic_gate_ranks_lexicographically_and_warns_on_weak_match(self):
        candidate_ids = ["direct-three", "fact-two", "weak-one", "unrelated-zero"]
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [{
                "shot_id": "concrete-fact",
                "semantic_role": "direct",
                "candidates": [
                    self._candidate(candidate_id, provider_id)
                    for candidate_id, provider_id in zip(candidate_ids, range(1, 5))
                ],
            }],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-06T12:00:00+08:00",
            "overall_rationale": "Compared each candidate against the concrete fact.",
            "shots": [{
                "shot_id": "concrete-fact",
                "candidates": [
                    self._score("direct-three", 3, 1, 1, 1),
                    self._score("fact-two", 2, 4, 4, 4),
                    self._score("weak-one", 1, 4, 4, 4),
                    self._score("unrelated-zero", 0, 4, 4, 4),
                ],
            }],
        }

        shot = candidate_analysis.rank_candidates(analysis, scores)["shots"][0]

        self.assertEqual(["direct-three", "fact-two", "weak-one"], shot["top3"])
        weak = next(item for item in shot["candidates"] if item["candidate_id"] == "weak-one")
        self.assertTrue(weak["eligible"])
        self.assertIn("weak_semantic_match", weak["warnings"])
        self.assertGreater(weak["base_rank"], next(
            item["base_rank"] for item in shot["candidates"] if item["candidate_id"] == "fact-two"
        ))
        unrelated = next(item for item in shot["candidates"] if item["candidate_id"] == "unrelated-zero")
        self.assertFalse(unrelated["eligible"])
        self.assertEqual(scores["shots"][0]["candidates"][0]["rationale"], shot["candidates"][0]["rationale"])
        self.assertEqual(3, shot["candidates"][0]["scores"]["semantic_fit"])

    def test_semantic_gate_all_zero_returns_no_eligible_candidates(self):
        analysis, scores = self._analysis_and_scores()
        for item in scores["shots"][0]["candidates"]:
            item["semantic_fit"] = 0

        shot = candidate_analysis.rank_candidates(analysis, scores)["shots"][0]

        self.assertEqual([], shot["top3"])
        self.assertEqual("no_eligible_candidates", shot["outcome"])

    def test_semantic_gate_counts_weak_match_before_provider_tiebreak(self):
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "shots": [{
                "shot_id": "weak-fact",
                "semantic_role": "direct",
                "candidates": [
                    self._candidate("fewer-warnings", 20),
                    self._candidate("more-warnings", 10, warning_count=1),
                ],
            }],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-08-06T12:00:00+08:00",
            "overall_rationale": "Both candidates are weak but usable matches for the fact.",
            "shots": [{
                "shot_id": "weak-fact",
                "candidates": [
                    self._score("fewer-warnings", 1, 3, 3, 3),
                    self._score("more-warnings", 1, 3, 3, 3),
                ],
            }],
        }

        shot = candidate_analysis.rank_candidates(analysis, scores)["shots"][0]
        candidates = {item["candidate_id"]: item for item in shot["candidates"]}

        self.assertEqual(["fewer-warnings", "more-warnings"], shot["top3"])
        self.assertEqual(1, candidates["fewer-warnings"]["warnings"].count("weak_semantic_match"))
        self.assertEqual(1, candidates["more-warnings"]["warnings"].count("weak_semantic_match"))
        self.assertEqual(1, candidates["fewer-warnings"]["warning_count"])
        self.assertEqual(2, candidates["more-warnings"]["warning_count"])

    def test_global_allocation_keeps_best_duplicate_refills_and_leaves_hints_eligible(self):
        first_candidates = [self._candidate(name, provider) for name, provider in (("a-exact", 11), ("a-series", 12), ("a-hint", 13), ("a-refill", 14))]
        second_candidates = [self._candidate(name, provider) for name, provider in (("b-exact", 21), ("b-series", 22), ("b-hint", 23), ("b-refill", 24))]
        exact_members = [{"shot_id": "first", "candidate_id": "a-exact"}, {"shot_id": "second", "candidate_id": "b-exact"}]
        hint_members = [{"shot_id": "first", "candidate_id": "a-hint"}, {"shot_id": "second", "candidate_id": "b-hint"}]
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]),
            "search_sha256": "a" * 64,
            "project_duplicate_evidence": {
                "exact_groups": [{"group_id": "exact-001", "members": exact_members, "evidence": [{"kind": "provider_candidate_id", "value": "shared"}]}],
                "strict_perceptual_groups": [],
                "possible_series": [{"hint_id": "possible-series-001", "members": hint_members, "evidence": [{"kind": "same_creator", "value": "creator"}]}],
            },
            "shots": [
                {"shot_id": "first", "semantic_role": "direct", "candidates": first_candidates},
                {"shot_id": "second", "semantic_role": "supportive", "candidates": second_candidates},
            ],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-07-30T12:00:00+08:00",
            "overall_rationale": "Allocated repeated footage to the strongest semantic moment and retained independent refills.",
            "near_duplicate_groups": [{
                "group_id": "same-series",
                "match_type": "same_series",
                "actor": "Codex",
                "timestamp": "2026-07-30T12:01:00+08:00",
                "members": [{"shot_id": "first", "candidate_id": "a-series"}, {"shot_id": "second", "candidate_id": "b-series"}],
                "rationale": "The same workstation, actor, wardrobe, and camera setup would repeat as one visual sequence.",
            }],
            "shots": [
                {"shot_id": "first", "candidates": [
                    self._score("a-exact", 4, 4, 3, 3), self._score("a-series", 4, 3, 4, 4),
                    self._score("a-hint", 3, 3, 3, 3), self._score("a-refill", 2, 2, 3, 3),
                ]},
                {"shot_id": "second", "candidates": [
                    self._score("b-exact", 3, 3, 4, 4), self._score("b-series", 4, 4, 4, 4),
                    self._score("b-hint", 3, 3, 3, 3), self._score("b-refill", 2, 2, 3, 3),
                ]},
            ],
        }

        first = candidate_analysis.rank_candidates(analysis, scores)
        second = candidate_analysis.rank_candidates(analysis, scores)

        self.assertEqual(first, second)
        shot_map = {shot["shot_id"]: shot for shot in first["shots"]}
        self.assertEqual(["a-exact", "a-hint", "a-refill"], shot_map["first"]["top3"])
        self.assertEqual(["b-series", "b-hint", "b-refill"], shot_map["second"]["top3"])
        self.assertEqual(["a-refill"], [item["candidate_id"] for item in shot_map["first"]["refills"]])
        self.assertEqual(["b-refill"], [item["candidate_id"] for item in shot_map["second"]["refills"]])
        self.assertEqual(2, len(first["global_allocations"]))
        self.assertEqual(
            [{"shot_id": "second", "candidate_id": "b-hint"}],
            next(item for item in shot_map["first"]["candidates"] if item["candidate_id"] == "a-hint")["similar_footage"],
        )

    def test_optional_ranking_binding_is_hash_bound_and_old_plans_remain_valid(self):
        fixture = _BrollFixture(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        analysis = {"schema_version": 1, "search_context": copy.deepcopy(self._search_plan()["brief"]["search_context"]), "search_sha256": "a" * 64, "shots": [{"shot_id": "shot", "semantic_role": "direct", "candidates": [self._candidate("asset", 1)]}]}
        scores = {
            "schema_version": 1, "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent", "actor": "Codex", "timestamp": "2026-07-30T12:00:00+08:00",
            "overall_rationale": "The local candidate directly shows the stated process.",
            "shots": [{"shot_id": "shot", "candidates": [self._score("asset", 4, 4, 3, 3)]}],
        }
        ranking = candidate_analysis.rank_candidates(analysis, scores)
        ranking_path = fixture.root / "work/b-roll/candidate-ranking.json"
        projectlib.write_json(ranking_path, ranking)
        bound = candidate_analysis.bind_ranking(fixture.plan, ranking, ranking_path, {"shot": [fixture.plan["shots"][0]["candidates"][0]]})
        self.assertEqual([], broll_plan.validate_plan(bound, fixture.timeline, fixture.transcript, project_root=fixture.root, verify_files=True))
        self.assertNotIn("candidate_ranking", fixture.plan)
        self.assertEqual([], broll_plan.validate_plan(fixture.plan, fixture.timeline, fixture.transcript))
        ranking_path.write_text("{}", encoding="utf-8")
        self.assertIn("candidate ranking SHA-256 is stale", broll_plan.validate_plan(bound, fixture.timeline, fixture.transcript, project_root=fixture.root, verify_files=True))

    def test_review_payload_exposes_bound_rank_scores_warnings_and_rationale(self):
        fixture = _BrollFixture(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        candidate = fixture.plan["shots"][0]["candidates"][0]
        candidate["ranking"] = {
            "rank": 1,
            "scores": {"semantic_fit": 4, "context_fit": 4, "composition_fit": 3, "style_fit": 3, "text_logo_risk": 0},
            "warnings": ["low_source_resolution"],
            "rationale": "The visible process matches the transcript claim.",
            "duplicate_notes": [],
        }
        assets = fixture.root / "review/03-b-roll/assets"
        shots, _, _ = build_review_page._payload(
            fixture.plan, fixture.timeline, fixture.transcript, fixture.root, assets,
        )
        ranking = shots[0]["candidates"][0]["ranking"]
        self.assertEqual(1, ranking["rank"])
        self.assertEqual(4, ranking["scores"]["semantic_fit"])
        self.assertEqual(["low_source_resolution"], ranking["warnings"])
        self.assertIn("matches", ranking["rationale"])

    def test_candidate_review_payload_omits_internal_search_context_and_semantic_role(self):
        fixture = _BrollFixture(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        search_context = {
            "topic": "PRIVATE_TOPIC_SENTINEL_7F31",
            "visual_direction": "PRIVATE_VISUAL_DIRECTION_SENTINEL_8A42",
            "keywords": ["PRIVATE_KEYWORD_SENTINEL_9B53"],
        }
        fixture.plan["brief"]["search_context"] = search_context
        fixture.plan["shots"][0]["semantic_role"] = "direct"
        fixture.plan["coverage_summary"] = {
            "profile": "PRIVATE_COVERAGE_PROFILE_SENTINEL_6C64",
            "planned": {"status": "PRIVATE_COVERAGE_STATUS_SENTINEL_5D75"},
        }
        analysis = {
            "schema_version": 1,
            "search_context": copy.deepcopy(search_context),
            "search_sha256": "a" * 64,
            "shots": [{"shot_id": "shot", "semantic_role": "direct", "candidates": [self._candidate("asset", 1)]}],
        }
        scores = {
            "schema_version": 1,
            "analysis_sha256": candidate_analysis.canonical_sha256(analysis),
            "mode": "agent",
            "actor": "Codex",
            "timestamp": "2026-07-30T12:00:00+08:00",
            "overall_rationale": "The candidate directly shows the described factory process.",
            "shots": [{"shot_id": "shot", "candidates": [self._score("asset", 4, 4, 3, 3)]}],
        }
        ranking = candidate_analysis.rank_candidates(analysis, scores)
        ranking_path = fixture.root / "work/b-roll/candidate-ranking.json"
        projectlib.write_json(ranking_path, ranking)
        bound = candidate_analysis.bind_ranking(
            fixture.plan, ranking, ranking_path,
            {"shot": [fixture.plan["shots"][0]["candidates"][0]]},
        )

        shots, _, _ = build_review_page._payload(
            bound, fixture.timeline, fixture.transcript, fixture.root,
            fixture.root / "review/03-b-roll/assets",
        )
        serialized = json.dumps(shots, sort_keys=True)

        self.assertNotIn('"search_context"', serialized)
        for value in (search_context["topic"], search_context["visual_direction"], *search_context["keywords"]):
            self.assertNotIn(value, serialized)
        self.assertNotIn('"semantic_role"', serialized)
        self.assertNotIn('"direct"', serialized)
        self.assertNotIn('"coverage_summary"', serialized)
        self.assertNotIn("PRIVATE_COVERAGE_PROFILE_SENTINEL_6C64", serialized)
        self.assertNotIn("PRIVATE_COVERAGE_STATUS_SENTINEL_5D75", serialized)

    def test_generated_review_page_payload_and_html_omit_private_context_role_and_coverage(self):
        fixture = _BrollFixture(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        video = fixture.root / "input/review.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"review-video")
        search_context = {
            "topic": "PRIVATE_TOPIC_SENTINEL_C8A1",
            "visual_direction": "PRIVATE_DIRECTION_SENTINEL_D9B2",
            "keywords": ["PRIVATE_KEYWORD_SENTINEL_EAC3"],
        }
        fixture.plan["input_hashes"]["review_video_sha256"] = broll_plan.sha256_file(video)
        fixture.plan["brief"]["search_context"] = search_context
        fixture.plan["shots"][0]["semantic_role"] = "atmospheric"
        fixture.plan["coverage_summary"] = {
            "profile": "PRIVATE_COVERAGE_PROFILE_SENTINEL_FBD4",
            "planned": {"status": "PRIVATE_COVERAGE_STATUS_SENTINEL_ACE5"},
        }
        fixture.plan = fixture.record_presentation(fixture.plan, "ordinary")

        def extract_frame(_video, _timestamp, destination):
            Image.new("RGB", (960, 540), "gray").save(destination, "JPEG")

        with mock.patch.object(build_review_page, "_probe_video", return_value=10.0), \
             mock.patch.object(build_review_page, "_extract_frame", side_effect=extract_frame):
            publication = build_review_page.build_review_page(
                fixture.plan, fixture.timeline, fixture.transcript, video,
                fixture.root / "review/03-b-roll", project_root=fixture.root,
                review_id="123e4567-e89b-12d3-a456-426614174003",
            )

        html = publication["page"].read_text(encoding="utf-8")
        encoded = build_review_page.PAYLOAD_RE.search(html)
        self.assertIsNotNone(encoded)
        payload = json.loads(base64.b64decode(encoded.group(1)).decode("utf-8"))
        serialized = json.dumps(payload, sort_keys=True)
        forbidden = (
            "coverage", "planned_ratio", "shortlist_ratio", "selected_ratio",
            "below_target", "within_target", "above_target", "search_context",
            "semantic_role", "atmospheric", search_context["topic"],
            search_context["visual_direction"], *search_context["keywords"],
            "PRIVATE_COVERAGE_PROFILE_SENTINEL_FBD4",
            "PRIVATE_COVERAGE_STATUS_SENTINEL_ACE5",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, serialized)
                self.assertNotIn(value, html)

    def test_synthetic_video_flows_from_analysis_through_shortlist_acquisition(self):
        source = self.root / "source.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=320x480:rate=10:duration=3", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", str(source),
        ], check=True, capture_output=True)
        probe = pexels.probe_media(source)
        candidate = {
            "id": "101-303", "provider_id": 101, "file_id": 303, "media_type": "video",
            "download_url": "https://videos.pexels.com/delivery.mp4", "width": 320, "height": 480,
            "duration_s": probe["duration_s"],
            "analysis_variant": {"file_id": 202, "download_url": "https://videos.pexels.com/analysis.mp4", "width": 320, "height": 480},
            "delivery_variant": {"file_id": 303, "download_url": "https://videos.pexels.com/delivery.mp4", "width": 320, "height": 480},
            "provenance": {"source_type": "pexels", "provider_id": 101, "source_url": "https://www.pexels.com/video/test-101/", "creator": "Maker", "license": "Pexels License", "license_url": pexels.LICENSE_URL, "terms_url": pexels.TERMS_URL, "retrieval_time": "2026-07-30T12:00:00+08:00", "download_url": "https://videos.pexels.com/delivery.mp4", "dimensions": {"width": 320, "height": 480}, "duration_s": probe["duration_s"]},
            "search": {"query": "factory process", "query_index": 0, "provider_rank": 0, "merge_rank": 0},
        }
        plan = self._search_plan()
        plan["shots"][0].update({"program_range": {"start_s": 0.5, "end_s": 1.5}, "transcript_evidence": {"words": [{"word": "process"}]}, "editorial_reason": "Shows the process.", "visual_intent": "Visible factory process.", "candidates": [], "selected": None, "status": "planned"})
        search = {"schema_version": 1, "search_context": copy.deepcopy(plan["brief"]["search_context"]), "shots": [{"shot_id": "shot", "semantic_role": "direct", "queries": plan["shots"][0]["queries"], "query_results": [[candidate], []], "merged_candidates": [candidate]}]}
        timeline = {"width": 720, "height": 1280, "fps": {"num": 30, "den": 1}}

        def downloader(value, destination, *, purpose):
            destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            return {**copy.deepcopy(value), "path": destination, "cache_path": value["cache_path"], "sha256": broll_plan.sha256_file(destination), "bytes": destination.stat().st_size, "probe": pexels.probe_media(destination)}

        analysis = candidate_analysis.analyze_search(plan, search, timeline, self.root, downloader=downloader)
        self.assertEqual(5, len(analysis["shots"][0]["candidates"][0]["samples"]))
        scores = {"schema_version": 1, "analysis_sha256": candidate_analysis.canonical_sha256(analysis), "mode": "agent", "actor": "Codex", "timestamp": "2026-07-30T12:00:00+08:00", "overall_rationale": "The visible process is directly relevant.", "shots": [{"shot_id": "shot", "candidates": [self._score("101-303", 4, 4, 3, 3)]}]}
        ranking = candidate_analysis.rank_candidates(analysis, scores)
        publication = candidate_analysis.publish_review_packet(analysis, ranking, self.root, review_id="123e4567-e89b-12d3-a456-426614174099")
        self.assertTrue(publication["summary"].is_file())
        self.assertEqual(11, len(list(publication["packet"].rglob("*.png"))))
        ranking_path = self.root / "work/b-roll/candidate-ranking.json"
        projectlib.write_json(ranking_path, ranking)
        bound = candidate_analysis.acquire_shortlist(plan, analysis, ranking, ranking_path, self.root, downloader=downloader)
        self.assertEqual(["101-303"], bound["candidate_ranking"]["shortlists"][0]["candidate_ids"])
        self.assertEqual("candidates_ready", bound["shots"][0]["status"])
        acquired = bound["shots"][0]["candidates"][0]
        self.assertEqual("delivery", acquired["variant_role"])
        self.assertEqual(1, acquired["ranking"]["rank"])

    def test_local_candidates_are_analyzed_from_frozen_cache_without_downloader(self):
        media = self.root / "work/cache/b-roll/candidates/local.mp4"
        media.parent.mkdir(parents=True, exist_ok=True); media.write_bytes(b"local")
        candidate = {"id": "local", "media_type": "video", "cache_path": "cache/b-roll/candidates/local.mp4", "sha256": broll_plan.sha256_file(media), "bytes": media.stat().st_size, "probe": {"duration_s": 3.0, "width": 720, "height": 1280}, "provenance": {"source_type": "local", "creator": "Owner", "license": "Owned", "retrieval_time": "2026-07-30T12:00:00+08:00", "original_path": "input/local.mp4"}}
        plan = self._search_plan()
        plan["shots"][0].update({"program_range": {"start_s": 0.0, "end_s": 1.0}, "transcript_evidence": {"words": [{"word": "process"}]}, "editorial_reason": "Shows the process.", "visual_intent": "Visible process.", "candidates": [candidate], "selected": None, "status": "candidates_ready"})
        search = candidate_analysis.search_plan(plan, orientation="portrait", searcher=lambda *args, **kwargs: [])
        self.assertEqual(["local"], [item["id"] for item in search["shots"][0]["merged_candidates"]])
        projectlib.write_json(self.root / "work/understand/media.json", {"width": 720, "height": 1280})

        def extract(source, timestamp, destination): Image.new("RGB", (72, 128), "gray").save(destination, "PNG")
        with mock.patch.object(candidate_analysis, "_full_decode"):
            analysis = candidate_analysis.analyze_search(
                plan, search, {"fps": {"num": 30, "den": 1}}, self.root,
                downloader=mock.Mock(side_effect=AssertionError("local analysis must not download")), extractor=extract,
            )
        analyzed = analysis["shots"][0]["candidates"][0]
        self.assertEqual("analyzed", analyzed["analysis_status"])
        self.assertEqual("work/cache/b-roll/candidates/local.mp4", analyzed["analysis_media"]["path"])
        self.assertEqual("not_applicable", analyzed["hard_checks"]["download"])


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

    def test_analysis_download_cache_is_separate_from_delivery_cache(self):
        analysis = Path(self.temp.name) / "work/cache/b-roll/candidate-analysis/media/proxy.mp4"
        analysis.parent.mkdir(parents=True)
        self.assertEqual(analysis.resolve(), pexels._cache_destination(analysis, purpose="analysis"))
        with self.assertRaises(ValueError): pexels._cache_destination(analysis)
        with self.assertRaises(ValueError): pexels._cache_destination(self.cache / "clip.mp4", purpose="analysis")

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

    def test_search_exposes_analysis_and_delivery_variants_without_changing_legacy_fields(self):
        payload = {"videos": [{
            "id": 7, "url": "https://www.pexels.com/video/7/", "user": {"name": "Maker"},
            "duration": 4, "width": 720, "height": 1280,
            "video_files": [
                {"id": 1, "link": "https://videos.pexels.com/360.mp4", "width": 360, "height": 640},
                {"id": 2, "link": "https://videos.pexels.com/540.mp4", "width": 540, "height": 960},
                {"id": 3, "link": "https://videos.pexels.com/720.mp4", "width": 720, "height": 1280},
            ],
        }]}

        class Response:
            def geturl(self): return pexels.PEXELS_API
            def read(self): return json.dumps(payload).encode()
            def __enter__(self): return self
            def __exit__(self, *args): pass

        record = pexels.search_videos("vertical factory", orientation="portrait", api_key="secret", opener=lambda request, timeout=None: Response())[0]
        self.assertEqual((3, 720, 1280), (record["file_id"], record["width"], record["height"]))
        self.assertEqual((3, 720, 1280), (record["delivery_variant"]["file_id"], record["delivery_variant"]["width"], record["delivery_variant"]["height"]))
        self.assertEqual((2, 540, 960), (record["analysis_variant"]["file_id"], record["analysis_variant"]["width"], record["analysis_variant"]["height"]))
        analysis = pexels.variant_candidate(record, "analysis")
        self.assertEqual((2, 540, 960), (analysis["file_id"], analysis["width"], analysis["height"]))
        self.assertEqual(analysis["download_url"], analysis["provenance"]["download_url"])
        self.assertEqual({"width": 540, "height": 960}, analysis["provenance"]["dimensions"])
        self.assertEqual(3, record["file_id"])
        self.assertNotIn("secret", json.dumps(record))
        with self.assertRaises(ValueError): pexels.variant_candidate(record, "proxy")

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
