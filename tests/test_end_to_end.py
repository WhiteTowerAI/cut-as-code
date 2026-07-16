import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageStat

from tests.protocol_testlib import ROOT, write_json


class ProjectEndToEndTests(unittest.TestCase):
    def test_complete_synthetic_project_cli_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "source.mp4"
            project_root = tmp / "project"
            self.run_command(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=6",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6",
                    "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    str(source),
                ]
            )
            self.run_command(
                [
                    "python", self.script("video-understand", "init_project.py"),
                    str(source), str(project_root), "--project-id", "end-to-end",
                ]
            )

            work = project_root / "work"
            media = self.load(work / "understand/media.json")
            duration = media["duration_s"]
            transcript = {
                "audio": "work/cache/audio16k.wav",
                "model": "fixture",
                "duration": duration,
                "language": "en",
                "language_probability": 1.0,
                "segments": [
                    {
                        "id": 0,
                        "start": 0.5,
                        "end": 1.5,
                        "text": "We serve 200 customers.",
                        "words": [
                            {"start": 0.5, "end": 0.7, "word": " We", "prob": 1.0},
                            {"start": 0.8, "end": 1.0, "word": " serve", "prob": 1.0},
                            {"start": 1.1, "end": 1.3, "word": " 200", "prob": 1.0},
                            {"start": 1.3, "end": 1.5, "word": " customers.", "prob": 1.0},
                        ],
                    }
                ],
            }
            understanding = {
                "schema_version": 1,
                "timeline_id": "source",
                "overview": {
                    "title": "Customer update",
                    "content_type": "talking-head",
                    "summary": "A short customer update.",
                    "primary_language": "en",
                },
                "chapters": [],
                "entities": [],
                "moments": [
                    {
                        "id": "moment-001",
                        "kind": "stat",
                        "start_s": 1.1,
                        "end_s": 1.5,
                        "summary": "200 customers",
                        "confidence": 0.95,
                        "evidence_refs": ["segment:0"],
                    }
                ],
                "transcript_corrections": [],
                "uncertainties": [],
            }
            write_json(work / "understand/transcript.json", transcript)
            write_json(work / "understand/understanding.json", understanding)
            self.run_command(
                [
                    "python", self.script("video-understand", "analyze.py"),
                    str(work / "understand/transcript.json"), str(work / "understand/analysis.json"),
                ]
            )
            self.run_command(
                [
                    "python", self.script("video-understand", "validate.py"),
                    "understanding", str(work / "understand/understanding.json"),
                    str(work / "understand/transcript.json"),
                ]
            )

            (work / "rough-cut").mkdir()
            edit_plan = {
                "schema_version": 1,
                "source_duration_s": duration,
                "decisions": [
                    {"id": "edit-001", "action": "keep", "start_s": 0.0, "end_s": 2.0, "reason": "opening"},
                    {"id": "drop-001", "action": "drop", "start_s": 2.0, "end_s": 4.0, "reason": "remove"},
                    {"id": "edit-002", "action": "keep", "start_s": 4.0, "end_s": duration, "reason": "ending"},
                ],
            }
            write_json(work / "rough-cut/edit-plan.json", edit_plan)
            write_json(
                work / "cache/edit-final.json",
                {
                    "source_duration_s": duration,
                    "keep": [
                        {"id": "clip-part-001", "decision_ref": "edit-001", "in": 0.0, "out": 2.0, "speed": 1.0},
                        {"id": "clip-part-002", "decision_ref": "edit-002", "in": 4.0, "out": duration, "speed": 2.0},
                    ],
                },
            )
            self.run_command(
                [
                    "python", self.script("video-understand", "build_timeline.py"),
                    str(work / "cache/edit-final.json"), str(work / "timeline.json"),
                    "--fps-num", "30", "--fps-den", "1",
                ]
            )

            (work / "color-grade").mkdir()
            write_json(
                work / "color-grade/grade-plan.json",
                {
                    "schema_version": 1,
                    "target": "base-video",
                    "base": "eq=brightness=0.04",
                    "looks": [{"name": "clean", "chain": "null"}],
                    "selected_look": "clean",
                    "selection_mode": "agent",
                    "selection_rationale": "Synthetic fixture selection.",
                    "evidence_refs": ["media:source"],
                },
            )
            (work / "content-cards").mkdir()
            self.run_command(
                [
                    "python", self.script("video-add-content-cards", "build_cards_plan.py"),
                    str(work / "understand/understanding.json"), str(work / "timeline.json"),
                    str(work / "content-cards/cards-plan.json"),
                ]
            )
            cards = self.load(work / "content-cards/cards-plan.json")
            card_stills = project_root / "review/03-content-cards/card-stills"
            card_stills.mkdir(parents=True)
            (card_stills / "card-001.jpg").write_bytes(b"fixture still")
            for card in cards["cards"]:
                card["copy"] = {
                    "status": "approved",
                    "display": {
                        "eyebrow": "",
                        "title": card["copy"]["suggested_text"],
                        "detail": "",
                    },
                }
                card["placement"] = {
                    "status": "approved",
                    "region": "top",
                    "face_clearance": "verified",
                    "review_still": "../review/03-content-cards/card-stills/card-001.jpg",
                }
                card["visual_treatment"] = {"status": "approved"}
                card["renderer"] = {
                    "composition": "cache/content-cards/index.html",
                    "asset": "cache/content-cards-overlay.mov",
                    "fps": {"num": 30, "den": 1},
                }
            write_json(work / "content-cards/cards-plan.json", cards)
            timeline = self.load(work / "timeline.json")
            self.run_command(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i",
                    f"color=c=red@0.35:size=160x90:rate=30:duration={timeline['program_duration_s']},format=rgba",
                    "-c:v", "qtrle", str(work / "cache/content-cards-overlay.mov"),
                ]
            )

            project = self.load(work / "project.json")
            project["operations"][0]["status"] = "verified"
            project["operations"] += [
                {
                    "id": "rough-cut", "skill": "video-rough-cut", "revision": 1,
                    "depends_on": ["understanding"], "based_on": {"understanding": 1},
                    "status": "verified", "plan": "rough-cut/edit-plan.json", "outputs": ["timeline.json"],
                    "target": {"sequence": "main", "scope": "timeline"},
                    "effects": {
                        "changes_timeline": True, "changes_geometry": False,
                        "changes_video_pixels": False, "changes_audio": True, "adds_track": None,
                    },
                    "render": {"kind": "timeline-transform", "input": "../input/original-video.mp4"},
                },
                {
                    "id": "color-grade", "skill": "video-color-grade", "revision": 1,
                    "depends_on": ["rough-cut"], "based_on": {"rough-cut": 1},
                    "status": "approved", "plan": "color-grade/grade-plan.json", "outputs": [],
                    "target": {"sequence": "main", "scope": "base-video"},
                    "effects": {
                        "changes_timeline": False, "changes_geometry": False,
                        "changes_video_pixels": True, "changes_audio": False, "adds_track": None,
                    },
                    "render": {"kind": "video-filter", "target": "base-video", "plan": "color-grade/grade-plan.json"},
                },
                {
                    "id": "content-cards", "skill": "video-add-content-cards", "revision": 1,
                    "depends_on": ["rough-cut", "color-grade"],
                    "based_on": {"rough-cut": 1, "color-grade": 1},
                    "status": "verified", "plan": "content-cards/cards-plan.json",
                    "outputs": ["cache/content-cards-overlay.mov"],
                    "target": {"sequence": "main", "scope": "graphics"},
                    "effects": {
                        "changes_timeline": False, "changes_geometry": False,
                        "changes_video_pixels": False, "changes_audio": False,
                        "adds_track": "graphics",
                    },
                    "render": {"kind": "overlay", "asset": "cache/content-cards-overlay.mov"},
                },
            ]
            project["sequences"]["main"]["operations"] = ["rough-cut", "color-grade", "content-cards"]
            write_json(work / "project.json", project)

            self.run_command(
                ["python", self.script("video-understand", "validate.py"), "project", "work/project.json", "."],
                cwd=project_root,
            )
            self.run_command(["python", self.script("video-understand", "build_render_plan.py"), str(project_root)])
            self.run_command(
                ["python", self.script("video-understand", "render_project.py"), str(work / "render/render-plan.json")]
            )
            compare = project_root / "review/04-edit-compare/original-vs-final-source-time.mp4"
            self.run_command(
                [
                    "python", self.script("video-edit-compare", "make_compare.py"),
                    str(work / "timeline.json"), str(project_root / "input/original-video.mp4"),
                    str(project_root / "final/final-video.mp4"), str(compare),
                ]
            )

            final_info = self.probe(project_root / "final/final-video.mp4")
            compare_info = self.probe(compare)
            self.assertAlmostEqual(timeline["program_duration_s"], float(final_info["format"]["duration"]), delta=1 / 30)
            self.assertAlmostEqual(duration, float(compare_info["format"]["duration"]), delta=1 / 30)
            video = next(stream for stream in compare_info["streams"] if stream["codec_type"] == "video")
            self.assertEqual((320, 90), (video["width"], video["height"]))
            self.assertIn("audio", {stream["codec_type"] for stream in compare_info["streams"]})
            self.assertTrue((project_root / "START-HERE.md").is_file())
            self.assertTrue((project_root / "final/delivery-report.md").is_file())
            self.assertTrue((compare.parent / "comparison-summary.md").is_file())

            frame = tmp / "drop.png"
            self.run_command(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "3",
                    "-i", str(compare), "-vf", "crop=40:30:220:45", "-frames:v", "1", str(frame),
                ]
            )
            self.assertLess(max(ImageStat.Stat(Image.open(frame).convert("RGB")).mean), 8)

    @staticmethod
    def script(skill, name):
        return str(ROOT / "skills" / skill / "scripts" / name)

    @staticmethod
    def run_command(command, cwd=None):
        subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)

    @staticmethod
    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def probe(path):
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


if __name__ == "__main__":
    unittest.main()
