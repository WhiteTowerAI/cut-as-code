import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import ROOT, load_script


projectlib = load_script(
    "skills/video-understand/scripts/projectlib.py", "layout_projectlib"
)


class ProjectLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "source.mp4"
        self.project_root = self.base / "my-project"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=blue:size=160x90:rate=30:duration=1",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(self.source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def tearDown(self):
        self.temp.cleanup()

    def initialize(self):
        subprocess.run(
            [
                "python", str(ROOT / "skills/video-understand/scripts/init_project.py"),
                str(self.source), str(self.project_root), "--project-id", "my-video",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_initializer_creates_user_and_machine_facing_core(self):
        self.initialize()
        expected = [
            "START-HERE.md",
            "input/original-video.mp4",
            "review/00-video-understanding/video-summary.md",
            "final",
            "work/project.json",
            "work/timeline.json",
            "work/understand/media.json",
            "work/cache",
            "work/render",
        ]
        for relative in expected:
            self.assertTrue((self.project_root / relative).exists(), relative)
        self.assertFalse((self.project_root / "review/01-rough-cut").exists())
        self.assertFalse((self.project_root / "work/rough-cut").exists())

    def test_initialized_project_has_valid_identity_timeline_and_fingerprint(self):
        self.initialize()
        project = projectlib.load_json(self.project_root / "work/project.json")
        timeline = projectlib.load_json(self.project_root / "work/timeline.json")
        media = projectlib.load_json(self.project_root / "work/understand/media.json")
        self.assertEqual([], projectlib.validate_project(project, self.project_root, check_files=True))
        self.assertEqual([], projectlib.validate_timeline(timeline))
        self.assertEqual(1, len(timeline["clips"]))
        self.assertEqual(1.0, timeline["clips"][0]["speed"])
        self.assertEqual(media["fingerprint"], project["source"]["fingerprint"])

    def test_probe_cli_emits_parseable_media_contract(self):
        output = self.base / "media.json"
        subprocess.run(
            [
                "python", str(ROOT / "skills/video-understand/scripts/probe.py"),
                str(self.source), str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        media = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual({"num": 30, "den": 1}, media["fps"])
        self.assertEqual((160, 90), (media["width"], media["height"]))
        self.assertEqual(self.source.stat().st_size, media["fingerprint"]["size"])

    def test_start_here_exposes_status_reviews_and_final_path_without_json(self):
        self.initialize()
        start = (self.project_root / "START-HERE.md").read_text(encoding="utf-8")
        self.assertIn("Current status", start)
        self.assertIn("Pending choices", start)
        self.assertIn("review/00-video-understanding/video-summary.md", start)
        self.assertIn("final/final-video.mp4", start)
        self.assertIn("Understanding", start)

    def test_project_validator_cli_detects_source_fingerprint_change(self):
        self.initialize()
        validator = ROOT / "skills/video-understand/scripts/validate.py"
        valid = subprocess.run(
            ["python", str(validator), "project", "work/project.json", "."],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, valid.returncode, valid.stderr)
        with open(self.project_root / "input/original-video.mp4", "ab") as handle:
            handle.write(b"changed")
        changed = subprocess.run(
            ["python", str(validator), "project", "work/project.json", "."],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, changed.returncode)
        self.assertIn("fingerprint", changed.stderr)

    def test_cache_deletion_preserves_decisions_and_is_regenerable(self):
        self.initialize()
        decision = self.project_root / "work/understand/understanding.json"
        decision.write_text('{"schema_version": 1}\n', encoding="utf-8")
        shutil.rmtree(self.project_root / "work/cache")
        self.assertTrue(decision.is_file())
        (self.project_root / "work/cache").mkdir()
        self.assertTrue((self.project_root / "work/cache").is_dir())


if __name__ == "__main__":
    unittest.main()
