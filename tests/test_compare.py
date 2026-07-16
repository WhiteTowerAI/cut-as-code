import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageStat

from tests.protocol_testlib import ROOT, load_script, project_fixture, timeline_fixture, write_json


make_compare = load_script(
    "skills/video-edit-compare/scripts/make_compare.py", "source_time_compare"
)


class CompareMappingTests(unittest.TestCase):
    def test_compare_parts_include_black_source_gaps(self):
        parts = make_compare.source_time_parts(timeline_fixture())
        self.assertEqual(
            [("final", 2.0), ("black", 2.0), ("final", 2.0)],
            [(part["kind"], part["duration_s"]) for part in parts],
        )
        self.assertEqual(
            {"start_s": 2.0, "end_s": 3.0}, parts[2]["program_range"]
        )

    def test_reordered_clips_are_rejected(self):
        timeline = timeline_fixture()
        timeline["clips"].reverse()
        with self.assertRaisesRegex(ValueError, "chronological"):
            make_compare.source_time_parts(timeline)


class CompareIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "input").mkdir()
        (cls.root / "final").mkdir()
        (cls.root / "review").mkdir()
        (cls.root / "work").mkdir()
        cls.source = cls.root / "input/source.mp4"
        cls.final = cls.root / "final/final.mp4"
        cls.output = cls.root / "review/compare.mp4"
        cls.timeline = cls.root / "work/timeline.json"
        write_json(cls.timeline, timeline_fixture())
        cls._run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=6",
                "-f", "lavfi", "-i", "sine=frequency=523:sample_rate=44100:duration=6",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(cls.source),
            ]
        )
        project = project_fixture(cls.root)
        stat = cls.source.stat()
        project["source"]["fingerprint"].update(
            size=stat.st_size, modified_ns=stat.st_mtime_ns
        )
        write_json(cls.root / "work/project.json", project)
        cls._run(
            [
                "python", str(ROOT / "skills/video-rough-cut/scripts/cut_render.py"),
                str(cls.timeline), str(cls.source), str(cls.final),
            ]
        )
        cls._run(
            [
                "python", str(ROOT / "skills/video-edit-compare/scripts/make_compare.py"),
                str(cls.timeline), str(cls.source), str(cls.final), str(cls.output),
            ]
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def _run(command):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(
                f"command failed ({result.returncode}): {command!r}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )

    @classmethod
    def _probe(cls, path):
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,width,height,duration:format=duration", "-of", "json", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    @classmethod
    def _crop(cls, path, at_s, crop, name):
        output = cls.root / f"{name}.png"
        cls._run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(at_s), "-i", str(path), "-vf", crop, "-frames:v", "1", str(output),
            ]
        )
        return Image.open(output).convert("RGB")

    @classmethod
    def _audio_md5(cls, path):
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                "-map", "0:a:0", "-f", "s16le", "-acodec", "pcm_s16le", "-",
            ],
            check=True,
            capture_output=True,
        )
        return hashlib.md5(result.stdout).hexdigest()

    def test_output_uses_source_duration_double_width_and_original_audio(self):
        info = self._probe(self.output)
        streams = {stream["codec_type"]: stream for stream in info["streams"]}
        self.assertAlmostEqual(6.0, float(info["format"]["duration"]), delta=1 / 30)
        self.assertEqual((320, 90), (streams["video"]["width"], streams["video"]["height"]))
        self.assertEqual(self._audio_md5(self.source), self._audio_md5(self.output))
        summary = self.output.parent / "comparison-summary.md"
        self.assertTrue(summary.is_file())
        self.assertIn("original-vs-final-source-time", summary.read_text(encoding="utf-8"))
        plan = self.root / "work/edit-compare/compare-plan.json"
        self.assertTrue(plan.is_file())
        self.assertEqual(
            "original-vs-final-source-time",
            json.loads(plan.read_text(encoding="utf-8"))["mode"],
        )
        project = json.loads((self.root / "work/project.json").read_text(encoding="utf-8"))
        review = next(item for item in project["reviews"] if item["id"] == "original-vs-final-source-time")
        self.assertEqual({"rough-cut": 2, "content-cards": 1}, review["based_on"])
        self.assertIn(
            "original-vs-final-source-time",
            (self.root / "START-HERE.md").read_text(encoding="utf-8"),
        )

    def test_dropped_source_time_is_black_on_right(self):
        image = self._crop(self.output, 3.0, "crop=40:30:220:45", "dropped")
        self.assertLess(max(ImageStat.Stat(image).mean), 8)

    def test_kept_source_time_matches_expected_final_program_frame(self):
        projected = self._crop(self.output, 5.0, "crop=40:30:220:45", "projected")
        left = list(projected.getdata())
        errors = []
        for offset in (-1 / 30, 0, 1 / 30):
            expected = self._crop(
                self.final, 2.5 + offset, "crop=40:30:60:45", f"expected-{offset}"
            )
            right = list(expected.getdata())
            errors.append(
                sum(
                    abs(a - b)
                    for lp, rp in zip(left, right)
                    for a, b in zip(lp, rp)
                )
                / (len(left) * 3)
            )
        self.assertLess(min(errors), 12)

    def test_filter_only_writes_durable_filtergraph_without_output(self):
        output = self.root / "review/filter-only.mp4"
        self._run(
            [
                "python", str(ROOT / "skills/video-edit-compare/scripts/make_compare.py"),
                str(self.timeline), str(self.source), str(self.final), str(output), "--filter-only",
            ]
        )
        self.assertFalse(output.exists())
        self.assertTrue(
            (self.root / "work/cache/filtergraphs/original-vs-final-source-time.txt").is_file()
        )

    def test_compare_rejects_final_shorter_than_program_timeline(self):
        short_final = self.root / "final/short.mp4"
        self._run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=red:size=160x90:rate=30:duration=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(short_final),
            ]
        )
        with self.assertRaisesRegex(ValueError, "final duration"):
            make_compare.build_command(
                timeline_fixture(), self.source, short_final,
                self.root / "review/short-compare.mp4",
                self.root / "work/cache/filtergraphs/short.txt",
                self.root / "work/cache/compare-labels-short",
            )


if __name__ == "__main__":
    unittest.main()
