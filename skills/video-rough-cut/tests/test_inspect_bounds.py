import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inspect_bounds.py"


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


if __name__ == "__main__":
    unittest.main()
