import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


from runtime import export_project


class ExportProjectTests(unittest.TestCase):
    def test_export_compiles_renders_and_marks_the_delivery_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work" / "render").mkdir(parents=True)
            (root / "final").mkdir()
            project_path = root / "work" / "project.json"
            project_path.write_text(json.dumps({
                "render": {
                    "status": "draft",
                    "plan": "render/render-plan.json",
                    "output": "../final/final.mp4",
                },
            }), encoding="utf-8")
            output = root / "final" / "final.mp4"
            output.write_bytes(b"previous")
            projectlib = mock.Mock()
            projectlib.load_json.side_effect = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
            projectlib.build_render_plan.return_value = {
                "schema_version": 1,
                "output": "../../final/final.mp4",
                "contributions": [],
            }
            projectlib.resolve_project_path.side_effect = lambda project_root, value: (
                Path(project_root) / "work" / value
            ).resolve()
            projectlib.write_json.side_effect = lambda path, value: Path(path).write_text(
                json.dumps(value), encoding="utf-8"
            )
            renderer = mock.Mock()

            def render(render_plan, _root, plan_dir):
                target = (Path(plan_dir) / render_plan["output"]).resolve()
                target.write_bytes(b"rendered")
                return target

            renderer.render.side_effect = render

            result = export_project.run_export(root, projectlib=projectlib, renderer=renderer)

            self.assertEqual({
                "ok": True,
                "output": "final/final.mp4",
                "size": len(b"rendered"),
            }, result)
            renderer.render.assert_called_once()
            self.assertEqual(b"rendered", output.read_bytes())
            saved = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual("verified", saved["render"]["status"])

    def test_failed_export_keeps_the_existing_delivery_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work" / "render").mkdir(parents=True)
            (root / "final").mkdir()
            project_path = root / "work" / "project.json"
            project_path.write_text(json.dumps({
                "render": {
                    "status": "verified",
                    "plan": "render/render-plan.json",
                    "output": "../final/final.mp4",
                },
            }), encoding="utf-8")
            output = root / "final" / "final.mp4"
            output.write_bytes(b"existing-delivery")
            projectlib = mock.Mock()
            projectlib.load_json.side_effect = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
            projectlib.build_render_plan.return_value = {
                "schema_version": 1,
                "output": "../../final/final.mp4",
                "contributions": [],
            }
            projectlib.resolve_project_path.side_effect = lambda project_root, value: (
                Path(project_root) / "work" / value
            ).resolve()
            projectlib.write_json.side_effect = lambda path, value: Path(path).write_text(
                json.dumps(value), encoding="utf-8"
            )
            renderer = mock.Mock()

            def fail_after_writing(render_plan, _root, plan_dir):
                target = (Path(plan_dir) / render_plan["output"]).resolve()
                target.write_bytes(b"partial-export")
                raise RuntimeError("render failed")

            renderer.render.side_effect = fail_after_writing

            with self.assertRaisesRegex(RuntimeError, "render failed"):
                export_project.run_export(root, projectlib=projectlib, renderer=renderer)

            self.assertEqual(b"existing-delivery", output.read_bytes())
            self.assertEqual([], list(output.parent.glob("*.export-*.mp4")))

    def test_locked_delivery_publishes_a_versioned_output_and_updates_the_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work" / "render").mkdir(parents=True)
            (root / "final").mkdir()
            project_path = root / "work" / "project.json"
            project_path.write_text(json.dumps({
                "render": {
                    "status": "draft",
                    "plan": "render/render-plan.json",
                    "output": "../final/final.mp4",
                },
            }), encoding="utf-8")
            output = root / "final" / "final.mp4"
            output.write_bytes(b"locked-delivery")
            projectlib = mock.Mock()
            projectlib.load_json.side_effect = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
            projectlib.build_render_plan.return_value = {
                "schema_version": 1,
                "output": "../../final/final.mp4",
                "contributions": [],
            }
            projectlib.resolve_project_path.side_effect = lambda project_root, value: (
                Path(project_root) / "work" / value
            ).resolve()
            projectlib.write_json.side_effect = lambda path, value: Path(path).write_text(
                json.dumps(value), encoding="utf-8"
            )
            renderer = mock.Mock()

            def render(render_plan, _root, plan_dir):
                target = (Path(plan_dir) / render_plan["output"]).resolve()
                target.write_bytes(b"rendered")
                return target

            renderer.render.side_effect = render
            def replace_with_locked_destination(source, target):
                if Path(target) == output:
                    raise PermissionError(13, "delivery is open")
                os.replace(source, target)
                return Path(target)

            with mock.patch.object(Path, "replace", autospec=True, side_effect=replace_with_locked_destination):
                result = export_project.run_export(root, projectlib=projectlib, renderer=renderer)

            published = root / result["output"]
            self.assertNotEqual(output, published)
            self.assertEqual(b"locked-delivery", output.read_bytes())
            self.assertEqual(b"rendered", published.read_bytes())
            saved = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(published, (project_path.parent / saved["render"]["output"]).resolve())
            self.assertEqual("verified", saved["render"]["status"])


if __name__ == "__main__":
    unittest.main()
