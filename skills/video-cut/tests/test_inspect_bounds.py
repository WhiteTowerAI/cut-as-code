import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inspect_bounds.py"
ASSIGN_SPEED_SCRIPT = Path(__file__).parents[1] / "scripts" / "assign_speed.py"


def words_between(start, end, count, prefix):
    step = (end - start) / count
    return [
        {
            "word": f" {prefix}{index}",
            "start": start + index * step + step * 0.1,
            "end": start + index * step + step * 0.9,
        }
        for index in range(count)
    ]


class InspectBoundsTests(unittest.TestCase):
    def run_inspector(self, plan, transcript, encoding="utf-8"):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan_path = root / "plan.json"
            transcript_path = root / "transcript.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            transcript_path.write_text(json.dumps(transcript), encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = encoding
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(plan_path), str(transcript_path)],
                capture_output=True,
                env=env,
            )

    def test_accepts_canonical_decisions(self):
        result = self.run_inspector(
            {
                "decisions": [
                    {"id": "drop-1", "action": "drop", "start_s": 0, "end_s": 1},
                    {"id": "keep-1", "action": "keep", "start_s": 1, "end_s": 3},
                ]
            },
            {
                "segments": [
                    {"words": [{"word": " Useful", "start": 1.1, "end": 1.5}]}
                ]
            },
        )

        self.assertEqual(0, result.returncode, result.stderr.decode(errors="replace"))
        self.assertIn(b"block 1: in=1.0 out=3.0", result.stdout)

    def test_warning_is_safe_on_windows_gbk_console(self):
        result = self.run_inspector(
            {"keep": [{"in": 0, "out": 1}]},
            {
                "segments": [
                    {
                        "words": [
                            {"word": " because", "start": 0.2, "end": 0.4},
                            {"word": " next", "start": 1.2, "end": 1.4},
                        ]
                    }
                ]
            },
            encoding="gbk",
        )

        self.assertEqual(0, result.returncode, result.stderr.decode("gbk", errors="replace"))
        self.assertIn(b"WARNING: dangling exit", result.stdout)


class AssignSpeedTests(unittest.TestCase):
    def run_assigner(self, keep, words):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edit_path = root / "edit.json"
            transcript_path = root / "transcript.json"
            output_path = root / "output.json"
            edit_path.write_text(json.dumps({"keep": keep}), encoding="utf-8")
            transcript_path.write_text(
                json.dumps({"language": "en", "segments": [{"words": words}]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ASSIGN_SPEED_SCRIPT),
                    str(edit_path),
                    str(transcript_path),
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            return json.loads(output_path.read_text(encoding="utf-8"))

    def test_defaults_are_speed_up_only_and_cap_at_1_30(self):
        output = self.run_assigner(
            [{"id": "slow", "decision_ref": "slow", "in": 0, "out": 60}],
            words_between(0, 60, 60, "slow"),
        )

        self.assertEqual(1.3, output["keep"][0]["speed"])
        self.assertEqual(1.0, output["speed_params"]["min_speed"])
        self.assertEqual(1.3, output["speed_params"]["max_speed"])

    def test_out_of_band_rate_moves_only_to_deadband_edge(self):
        output = self.run_assigner(
            [{"id": "near-edge", "decision_ref": "near-edge", "in": 0, "out": 60}],
            words_between(0, 60, 140, "word"),
        )

        self.assertEqual(1.04, output["keep"][0]["speed"])
        self.assertEqual("deadband-edge", output["speed_params"]["correction"])

    def test_segments_with_same_decision_ref_share_one_speed(self):
        output = self.run_assigner(
            [
                {"id": "part-1", "decision_ref": "decision-a", "in": 0, "out": 30},
                {"id": "part-2", "decision_ref": "decision-a", "in": 30, "out": 60},
            ],
            words_between(0, 30, 30, "slow") + words_between(30, 60, 90, "fast"),
        )

        self.assertEqual(1.2, output["keep"][0]["speed"])
        self.assertEqual(output["keep"][0]["speed"], output["keep"][1]["speed"])

    def test_adjacent_decision_speeds_differ_by_at_most_0_08(self):
        output = self.run_assigner(
            [
                {"id": "slow", "decision_ref": "decision-a", "in": 0, "out": 60},
                {"id": "normal", "decision_ref": "decision-b", "in": 60, "out": 120},
            ],
            words_between(0, 60, 60, "slow") + words_between(60, 120, 165, "normal"),
        )

        first_speed = output["keep"][0]["speed"]
        second_speed = output["keep"][1]["speed"]
        self.assertEqual(1.3, first_speed)
        self.assertEqual(1.22, second_speed)
        self.assertAlmostEqual(0.08, abs(first_speed - second_speed), places=6)


if __name__ == "__main__":
    unittest.main()
