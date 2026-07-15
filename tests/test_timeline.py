import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import ROOT, load_script, timeline_fixture


projectlib = load_script(
    "skills/video-understand/scripts/projectlib.py", "open_recut_timeline_projectlib"
)
cut_render = load_script(
    "skills/video-rough-cut/scripts/cut_render.py", "rough_cut_render"
)
canonical_transcribe = load_script(
    "skills/video-understand/scripts/transcribe.py", "canonical_transcribe"
)
rough_cut_transcribe = load_script(
    "skills/video-rough-cut/scripts/transcribe.py", "rough_cut_transcribe"
)


class TimelineTests(unittest.TestCase):
    def test_build_timeline_maps_linear_speed(self):
        timeline = projectlib.timeline_from_segments(
            [{"in": 10.0, "out": 14.0, "speed": 2.0, "id": "edit-1"}],
            source_duration_s=20.0,
            fps={"num": 30, "den": 1},
        )
        clip = timeline["clips"][0]
        self.assertEqual({"start_s": 10.0, "end_s": 14.0}, clip["source_range"])
        self.assertEqual({"start_s": 0.0, "end_s": 2.0}, clip["program_range"])
        self.assertEqual(2.0, timeline["program_duration_s"])

    def test_build_source_timeline_uses_one_identity_clip(self):
        timeline = projectlib.source_timeline(
            source_duration_s=6.0, fps={"num": 30000, "den": 1001}
        )
        self.assertEqual(1, len(timeline["clips"]))
        self.assertEqual(1.0, timeline["clips"][0]["speed"])
        self.assertEqual(6.0, timeline["program_duration_s"])

    def test_source_to_program_maps_kept_source_time(self):
        self.assertAlmostEqual(
            2.25, projectlib.source_to_program(timeline_fixture(), 4.5), places=6
        )

    def test_source_to_program_returns_none_for_drop(self):
        self.assertIsNone(projectlib.source_to_program(timeline_fixture(), 3.0))

    def test_source_to_program_uses_half_open_ranges(self):
        self.assertIsNone(projectlib.source_to_program(timeline_fixture(), 2.0))

    def test_program_to_source_maps_varispeed(self):
        self.assertAlmostEqual(
            5.0, projectlib.program_to_source(timeline_fixture(), 2.5), places=6
        )

    def test_program_to_source_uses_half_open_ranges(self):
        self.assertIsNone(projectlib.program_to_source(timeline_fixture(), 3.0))

    def test_valid_timeline_has_no_errors(self):
        self.assertEqual([], projectlib.validate_timeline(timeline_fixture()))

    def test_duplicate_clip_id_is_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"][1]["id"] = "clip-001"
        self.assertTrue(any("duplicate clip id" in e for e in projectlib.validate_timeline(timeline)))

    def test_overlapping_source_clips_are_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"][1]["source_range"]["start_s"] = 1.0
        self.assertTrue(any("source ranges overlap" in e for e in projectlib.validate_timeline(timeline)))

    def test_reordered_source_clips_are_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"].reverse()
        self.assertTrue(any("chronological" in e for e in projectlib.validate_timeline(timeline)))

    def test_program_gap_is_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"][1]["program_range"]["start_s"] = 2.1
        self.assertTrue(any("program ranges must be contiguous" in e for e in projectlib.validate_timeline(timeline)))

    def test_program_duration_math_is_checked(self):
        timeline = timeline_fixture()
        timeline["clips"][1]["program_range"]["end_s"] = 3.5
        timeline["program_duration_s"] = 3.5
        self.assertTrue(any("duration does not match speed" in e for e in projectlib.validate_timeline(timeline)))

    def test_program_total_is_checked(self):
        timeline = timeline_fixture()
        timeline["program_duration_s"] = 4.0
        self.assertTrue(any("program_duration_s" in e for e in projectlib.validate_timeline(timeline)))

    def test_invalid_fps_is_rejected(self):
        timeline = timeline_fixture()
        timeline["fps"] = {"num": 0, "den": 1}
        self.assertTrue(any("fps" in e for e in projectlib.validate_timeline(timeline)))

    def test_non_positive_speed_is_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"][0]["speed"] = 0
        self.assertTrue(any("speed" in e for e in projectlib.validate_timeline(timeline)))

    def test_missing_decision_reference_is_rejected_when_ids_given(self):
        errors = projectlib.validate_timeline(timeline_fixture(), decision_ids={"edit-001"})
        self.assertTrue(any("edit-002" in e for e in errors))

    def test_timeline_from_legacy_edit_preserves_ranges_speed_and_reason(self):
        legacy = {
            "source_duration_s": 10.0,
            "keep": [
                {"in": 1.0, "out": 3.0, "speed": 1.25, "reason": "keep one"},
                {"in": 7.0, "out": 9.0, "reason": "keep two"},
            ],
        }
        timeline = projectlib.timeline_from_edit(legacy, fps={"num": 25, "den": 1})
        self.assertEqual([1.25, 1.0], [clip["speed"] for clip in timeline["clips"]])
        self.assertEqual(
            [{"start_s": 1.0, "end_s": 3.0}, {"start_s": 7.0, "end_s": 9.0}],
            [clip["source_range"] for clip in timeline["clips"]],
        )
        self.assertEqual("keep one", timeline["clips"][0]["reason"])

    def test_precision_part_keeps_original_editorial_decision_reference(self):
        precision = {
            "source_duration_s": 10.0,
            "keep": [
                {
                    "id": "decision-001.part-001",
                    "decision_ref": "decision-001",
                    "in": 1.0,
                    "out": 3.0,
                }
            ],
        }
        timeline = projectlib.timeline_from_edit(precision, fps={"num": 30, "den": 1})
        self.assertEqual("decision-001", timeline["clips"][0]["decision_ref"])
        self.assertEqual(
            [], projectlib.validate_timeline(timeline, decision_ids={"decision-001"})
        )

    def test_timeline_from_canonical_decisions_uses_keep_only(self):
        plan = {
            "source_duration_s": 5.0,
            "decisions": [
                {"id": "a", "action": "drop", "start_s": 0.0, "end_s": 1.0},
                {"id": "b", "action": "keep", "start_s": 1.0, "end_s": 5.0},
            ],
        }
        timeline = projectlib.timeline_from_edit(plan, fps={"num": 24, "den": 1})
        self.assertEqual(1, len(timeline["clips"]))
        self.assertEqual("b", timeline["clips"][0]["decision_ref"])

    def test_build_timeline_cli_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "edit.json"
            output = tmp / "timeline.json"
            source.write_text(
                json.dumps(
                    {
                        "source_duration_s": 4.0,
                        "keep": [{"in": 1.0, "out": 3.0, "speed": 2.0}],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "python",
                    str(ROOT / "skills/video-understand/scripts/build_timeline.py"),
                    str(source),
                    str(output),
                    "--fps-num",
                    "24",
                    "--fps-den",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            timeline = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(1.0, timeline["program_duration_s"])
            self.assertEqual({"num": 24, "den": 1}, timeline["fps"])

    def test_repository_legacy_edit_final_example_converts(self):
        edit = json.loads(
            (ROOT / "skills/video-rough-cut/examples/edit_final.json").read_text(encoding="utf-8")
        )
        timeline = projectlib.timeline_from_edit(edit, fps={"num": 30, "den": 1})
        self.assertEqual([], projectlib.validate_timeline(timeline))
        self.assertEqual(len(edit["keep"]), len(timeline["clips"]))


class TimelineCompatibilityTests(unittest.TestCase):
    def test_rough_cut_transcriber_delegates_canonical_arguments(self):
        argv = ["audio.wav", "work/transcript", "medium", "--lang", "zh"]
        self.assertEqual(
            (ROOT / "skills/video-understand/scripts/transcribe.py").resolve(),
            rough_cut_transcribe.CANONICAL_SCRIPT,
        )
        self.assertEqual(
            canonical_transcribe.parse_args(argv), rough_cut_transcribe.parse_args(argv)
        )

    def test_cut_render_accepts_canonical_timeline(self):
        self.assertEqual(
            [
                {"in": 0.0, "out": 2.0, "speed": 1.0},
                {"in": 4.0, "out": 6.0, "speed": 2.0},
            ],
            cut_render.load_segments(timeline_fixture()),
        )

    def test_cut_render_keeps_legacy_segments(self):
        edit = {"keep": [{"in": 2.0, "out": 4.0, "speed": 1.25}]}
        self.assertEqual(edit["keep"], cut_render.load_segments(edit))

    def test_build_edit_assigns_stable_ids_from_canonical_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            coarse = tmp / "edit-plan.json"
            transcript = tmp / "transcript.json"
            output = tmp / "edit-final.json"
            coarse.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_duration_s": 4.0,
                        "decisions": [
                            {
                                "id": "decision-keep",
                                "action": "keep",
                                "start_s": 0.0,
                                "end_s": 4.0,
                                "reason": "complete thought",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            transcript.write_text(
                json.dumps(
                    {
                        "duration": 4.0,
                        "segments": [
                            {
                                "id": 0,
                                "start": 0.2,
                                "end": 3.5,
                                "text": "A complete thought",
                                "words": [
                                    {"start": 0.2, "end": 0.5, "word": " A"},
                                    {"start": 0.6, "end": 1.2, "word": " complete"},
                                    {"start": 1.3, "end": 1.8, "word": " thought"},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "python",
                    str(ROOT / "skills/video-rough-cut/scripts/build_edit.py"),
                    str(coarse),
                    str(transcript),
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("decision-keep", result["keep"][0]["id"])


if __name__ == "__main__":
    unittest.main()
