import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import ROOT, load_script, project_fixture, timeline_fixture, write_json


projectlib = load_script(
    "skills/video-understand/scripts/projectlib.py", "render_plan_projectlib"
)
render_project = load_script(
    "skills/video-understand/scripts/render_project.py", "delivery_render_project"
)


class RenderPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in (
            "input", "final", "work/rough-cut", "work/color-grade",
            "work/content-cards", "work/cache", "work/render",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        (self.root / "input/source.mp4").write_bytes(b"source")
        (self.root / "work/cache/content-cards-overlay.mov").write_bytes(b"overlay")
        write_json(self.root / "work/timeline.json", timeline_fixture())
        write_json(self.root / "work/rough-cut/edit-plan.json", {})
        write_json(
            self.root / "work/color-grade/grade-plan.json",
            {
                "schema_version": 1,
                "target": "base-video",
                "base": "eq=contrast=1.1",
                "looks": [{"name": "clean", "chain": "null"}],
                "selected_look": "clean",
            },
        )
        write_json(
            self.root / "work/content-cards/cards-plan.json",
            {
                "schema_version": 1,
                "target": "overlay",
                "cards": [
                    {
                        "id": "card-001",
                        "copy": {"status": "approved", "text": "Approved"},
                        "placement": {"status": "approved", "region": "top"},
                        "visual_treatment": {"status": "approved"},
                    }
                ],
            },
        )

        self.project = project_fixture(self.root)
        source_stat = (self.root / "input/source.mp4").stat()
        self.project["source"]["fingerprint"].update(
            size=source_stat.st_size, modified_ns=source_stat.st_mtime_ns
        )
        grade = {
            "id": "color-grade",
            "skill": "video-color-grade",
            "revision": 1,
            "depends_on": ["rough-cut"],
            "based_on": {"rough-cut": 2},
            "status": "approved",
            "plan": "color-grade/grade-plan.json",
            "outputs": [],
            "render": {
                "kind": "video-filter",
                "target": "base-video",
                "plan": "color-grade/grade-plan.json",
            },
        }
        self.project["operations"].insert(2, grade)
        cards = self.project["operations"][3]
        cards["depends_on"] = ["rough-cut", "color-grade"]
        cards["based_on"] = {"rough-cut": 2, "color-grade": 1}
        self.project["sequences"]["main"]["operations"] = [
            "rough-cut", "color-grade", "content-cards"
        ]
        write_json(self.root / "work/project.json", self.project)

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return projectlib.build_render_plan(self.project, self.root)

    def test_active_operations_compile_in_sequence_order(self):
        plan = self.build()
        self.assertEqual(
            ["timeline-transform", "video-filter", "overlay"],
            [contribution["kind"] for contribution in plan["contributions"]],
        )
        self.assertEqual(
            ["rough-cut", "color-grade", "content-cards"],
            [contribution["operation"] for contribution in plan["contributions"]],
        )

    def test_paths_are_relative_to_render_plan(self):
        plan = self.build()
        self.assertEqual("../../input/source.mp4", plan["source"])
        self.assertEqual(
            self.project["source"]["fingerprint"], plan["source_fingerprint"]
        )
        self.assertEqual("../timeline.json", plan["timeline"])
        self.assertEqual("../../input/source.mp4", plan["contributions"][0]["input"])
        self.assertEqual("../color-grade/grade-plan.json", plan["contributions"][1]["plan"])
        self.assertEqual("../cache/content-cards-overlay.mov", plan["contributions"][2]["asset"])
        self.assertEqual("../../final/final.mp4", plan["output"])

    def test_stale_operation_blocks_render_plan(self):
        self.project["operations"][3]["based_on"]["rough-cut"] = 1
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            self.build()

    def test_draft_active_operation_blocks_render_plan(self):
        self.project["operations"][2]["status"] = "draft"
        with self.assertRaisesRegex(ValueError, "not approved"):
            self.build()

    def test_unsupported_contribution_kind_is_rejected(self):
        self.project["operations"][2]["render"]["kind"] = "magic"
        with self.assertRaisesRegex(ValueError, "unsupported contribution"):
            self.build()

    def test_missing_overlay_asset_is_rejected(self):
        (self.root / "work/cache/content-cards-overlay.mov").unlink()
        with self.assertRaisesRegex(ValueError, "missing asset"):
            self.build()

    def test_delivery_grade_requires_selected_look(self):
        path = self.root / "work/color-grade/grade-plan.json"
        grade = json.loads(path.read_text(encoding="utf-8"))
        del grade["selected_look"]
        write_json(path, grade)
        with self.assertRaisesRegex(ValueError, "selected_look"):
            self.build()

    def test_delivery_cards_require_completed_human_choices(self):
        path = self.root / "work/content-cards/cards-plan.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["cards"][0]["copy"]["status"] = "draft"
        write_json(path, plan)
        with self.assertRaisesRegex(ValueError, "card-001 copy"):
            self.build()

    def test_domain_operations_record_exact_consumed_revisions(self):
        operations = {item["id"]: item for item in self.project["operations"]}
        self.assertEqual({"rough-cut": 2}, operations["color-grade"]["based_on"])
        self.assertEqual(
            {"rough-cut": 2, "color-grade": 1},
            operations["content-cards"]["based_on"],
        )

    def test_cli_writes_configured_render_plan(self):
        output = self.root / "work/render/render-plan.json"
        subprocess.run(
            [
                "python",
                str(ROOT / "skills/video-understand/scripts/build_render_plan.py"),
                str(self.root),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        plan = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(3, len(plan["contributions"]))

    def test_cards_only_plan_retains_project_source(self):
        cards = self.project["operations"][3]
        cards["depends_on"] = ["understanding"]
        cards["based_on"] = {"understanding": 1}
        self.project["sequences"]["main"]["operations"] = ["content-cards"]
        plan = self.build()
        self.assertEqual("../../input/source.mp4", plan["source"])
        self.assertEqual(["overlay"], [item["kind"] for item in plan["contributions"]])

    def test_compiled_fingerprint_blocks_source_changed_before_render(self):
        plan = self.build()
        with open(self.root / "input/source.mp4", "ab") as handle:
            handle.write(b"changed")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            render_project.build_command(plan, self.root)


class DeliveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ("input", "final", "work/render", "work/color-grade", "work/cache"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.source = self.root / "input/source.mp4"
        self.overlay = self.root / "work/cache/overlay.mov"
        self.output = self.root / "final/final.mp4"
        self._run_ffmpeg(
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30:duration=6",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=6",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(self.source),
        )
        self._run_ffmpeg(
            "-f", "lavfi", "-i", "color=c=red@0.5:size=160x90:rate=30:duration=3,format=rgba",
            "-c:v", "qtrle", str(self.overlay),
        )
        write_json(self.root / "work/timeline.json", timeline_fixture())
        write_json(
            self.root / "work/color-grade/grade-plan.json",
            {
                "schema_version": 1,
                "target": "base-video",
                "base": "eq=brightness=0.05",
                "looks": [{"name": "clean", "chain": "null"}],
                "selected_look": "clean",
            },
        )
        self.plan = {
            "schema_version": 1,
            "sequence": "main",
            "source": "../../input/source.mp4",
            "timeline": "../timeline.json",
            "contributions": [
                {
                    "operation": "rough-cut",
                    "kind": "timeline-transform",
                    "input": "../../input/source.mp4",
                },
                {
                    "operation": "color-grade",
                    "kind": "video-filter",
                    "target": "base-video",
                    "plan": "../color-grade/grade-plan.json",
                },
                {
                    "operation": "content-cards",
                    "kind": "overlay",
                    "asset": "../cache/overlay.mov",
                },
            ],
            "output": "../../final/final.mp4",
        }
        self.plan_path = self.root / "work/render/render-plan.json"
        write_json(self.plan_path, self.plan)

    def tearDown(self):
        self.temp.cleanup()

    def _run_ffmpeg(self, *args):
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def _probe(self, path):
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

    def test_delivery_filter_orders_cut_grade_then_overlay(self):
        command = render_project.build_command(self.plan, self.root)
        graph = command[command.index("-filter_complex") + 1]
        self.assertLess(graph.index("concat="), graph.index("eq=brightness"))
        self.assertLess(graph.index("eq=brightness"), graph.index("overlay="))
        self.assertNotIn("copy", command[command.index("-c:a") + 1])

    def test_renderer_rejects_invalid_video_filter_target(self):
        plan = json.loads(json.dumps(self.plan))
        plan["contributions"][1]["target"] = "captions"
        with self.assertRaisesRegex(ValueError, "target"):
            render_project.build_command(plan, self.root)

    def test_renderer_revalidates_timeline(self):
        timeline = timeline_fixture()
        timeline["clips"].reverse()
        write_json(self.root / "work/timeline.json", timeline)
        with self.assertRaisesRegex(ValueError, "chronological"):
            render_project.build_command(self.plan, self.root)

    def test_synthetic_delivery_duration_dimensions_and_audio(self):
        subprocess.run(
            ["python", str(ROOT / "skills/video-understand/scripts/render_project.py"), str(self.plan_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        info = self._probe(self.output)
        duration = float(info["format"]["duration"])
        streams = {stream["codec_type"]: stream for stream in info["streams"]}
        self.assertAlmostEqual(3.0, duration, delta=1 / 30)
        self.assertEqual((160, 90), (streams["video"]["width"], streams["video"]["height"]))
        self.assertIn("audio", streams)
        self.assertAlmostEqual(
            float(streams["video"]["duration"]),
            float(streams["audio"]["duration"]),
            delta=1 / 30,
        )

    def test_identity_timeline_copies_audio_when_only_overlay_changes_video(self):
        plan = dict(self.plan)
        plan["contributions"] = [self.plan["contributions"][2]]
        command = render_project.build_command(plan, self.root)
        self.assertEqual("copy", command[command.index("-c:a") + 1])

    def test_cards_only_identity_timeline_renders_full_source(self):
        identity = {
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30, "den": 1},
            "source_duration_s": 6.0,
            "program_duration_s": 6.0,
            "clips": [
                {
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 6.0},
                    "program_range": {"start_s": 0.0, "end_s": 6.0},
                    "speed": 1.0,
                    "decision_ref": "source",
                }
            ],
        }
        write_json(self.root / "work/identity-timeline.json", identity)
        output = self.root / "final/cards-only.mp4"
        plan = {
            "schema_version": 1,
            "sequence": "main",
            "source": "../../input/source.mp4",
            "timeline": "../identity-timeline.json",
            "contributions": [self.plan["contributions"][2]],
            "output": "../../final/cards-only.mp4",
        }
        render_project.render(plan, self.root)
        info = self._probe(output)
        self.assertAlmostEqual(6.0, float(info["format"]["duration"]), delta=1 / 30)
        self.assertIn("audio", {stream["codec_type"] for stream in info["streams"]})

    def test_delivery_cli_updates_user_facing_report_and_status(self):
        stat = self.source.stat()
        project = {
            "schema_version": 1,
            "project_id": "delivery-report-test",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                    "duration_s": 6.0,
                },
            },
            "active_sequence": "main",
            "sequences": {"main": {"operations": [], "timeline": "timeline.json"}},
            "operations": [],
            "render": {
                "plan": "render/render-plan.json",
                "output": "../final/final.mp4",
                "status": "draft",
            },
            "reviews": [],
        }
        write_json(self.root / "work/project.json", project)
        subprocess.run(
            ["python", str(ROOT / "skills/video-understand/scripts/render_project.py"), str(self.plan_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertTrue((self.root / "final/delivery-report.md").is_file())
        self.assertIn("final/final.mp4", (self.root / "START-HERE.md").read_text(encoding="utf-8"))
        updated = json.loads((self.root / "work/project.json").read_text(encoding="utf-8"))
        self.assertEqual("verified", updated["render"]["status"])


if __name__ == "__main__":
    unittest.main()
