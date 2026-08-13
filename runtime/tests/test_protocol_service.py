import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

from protocol_service import ProtocolService  # noqa: E402
from project_snapshot import canonical_project_root  # noqa: E402


def plan_resource_id(operation_id):
    key = f"plan:{operation_id}".encode("utf-8")
    return "res_" + hashlib.sha256(key).hexdigest()[:24]


class ProtocolServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        (self.root / "work").mkdir()
        (self.root / "input").mkdir()
        self.source = self.root / "input" / "source.mp4"
        self.source.write_bytes(b"video")
        self.timeline = self.root / "work" / "timeline.json"
        self.timeline.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_duration_s": 1.0,
                    "program_duration_s": 1.0,
                    "fps": {"num": 30, "den": 1},
                    "clips": [
                        {
                            "id": "clip-1",
                            "source_range": {"start_s": 0.0, "end_s": 1.0},
                            "program_range": {"start_s": 0.0, "end_s": 1.0},
                            "speed": 1.0,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.plan = self.root / "work" / "captions" / "captions-plan.json"
        self.plan.parent.mkdir()
        self.plan.write_text('{"cues": []}\n', encoding="utf-8")
        self.project_path = self.root / "work" / "project.json"
        self._write_project()
        self.service = ProtocolService()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_open_project_returns_registered_resources_and_byte_etags(self):
        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertFalse(response["snapshot"]["read_only"])
        self.assertEqual([], response["snapshot"]["errors"])
        by_kind = {item["kind"]: item for item in response["snapshot"]["resources"]}
        self.assertEqual({"project", "timeline", "plan"}, set(by_kind))
        self.assertEqual("captions", by_kind["plan"]["operation_id"])
        self.assertEqual(
            hashlib.sha256(self.project_path.read_bytes()).hexdigest(),
            by_kind["project"]["etag"],
        )
        view = response["snapshot"]["view"]
        self.assertEqual(1, view["schema_version"])
        self.assertEqual("main", view["active_sequence"])
        self.assertEqual(1, view["operation_count"])
        self.assertEqual(0, view["review_count"])
        self.assertEqual(
            [
                {
                    "id": "captions",
                    "revision": 1,
                    "status": "draft",
                    "target": {"sequence": "main", "scope": "full"},
                    "plan_resource_id": plan_resource_id("captions"),
                }
            ],
            view["operations"],
        )
        self.assertEqual([], view["reviews"])
        for resource in response["snapshot"]["resources"]:
            self.assertNotIn("path", resource)

    def test_get_snapshot_detects_external_file_changes(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]
        plan_before = next(
            item for item in opened["snapshot"]["resources"] if item["kind"] == "plan"
        )

        self.plan.write_text('{"cues": [{"id": "new"}]}\n', encoding="utf-8")
        refreshed = self.service.handle_request(
            {"verb": "get_snapshot", "project_id": project_id}
        )
        plan_after = next(
            item for item in refreshed["snapshot"]["resources"] if item["kind"] == "plan"
        )

        self.assertNotEqual(plan_before["etag"], plan_after["etag"])
        self.assertEqual(plan_before["id"], plan_after["id"])

    def test_get_resource_accepts_only_server_issued_resource_ids(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]
        plan_resource = next(
            item for item in opened["snapshot"]["resources"] if item["kind"] == "plan"
        )

        response = self.service.handle_request(
            {
                "verb": "get_resource",
                "project_id": project_id,
                "resource_id": plan_resource["id"],
            }
        )
        rejected = self.service.handle_request(
            {
                "verb": "get_resource",
                "project_id": project_id,
                "resource_id": "../../input/source.mp4",
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual({"cues": []}, response["resource"]["content"])
        self.assertEqual(plan_resource["etag"], response["resource"]["etag"])
        self.assertEqual(
            {"ok": False, "error": "unknown resource_id"}, rejected
        )

    def test_plan_symlink_escape_is_reported_and_not_registered(self):
        outside_dir = tempfile.TemporaryDirectory()
        self.addCleanup(outside_dir.cleanup)
        outside = Path(outside_dir.name) / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        escape = self.root / "work" / "escape.json"
        try:
            escape.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        project = self._project()
        project["operations"][0]["plan"] = "escape.json"
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertIn(
            "project path escapes root: escape.json", response["snapshot"]["errors"]
        )
        self.assertNotIn(
            "plan", {item["kind"] for item in response["snapshot"]["resources"]}
        )

    def test_invalid_json_opens_read_only_with_exact_error(self):
        self.project_path.write_text("{", encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            [
                "invalid project JSON: Expecting property name enclosed in double quotes: "
                "line 1 column 2 (char 1)"
            ],
            response["snapshot"]["errors"],
        )

    def test_non_object_json_roots_open_read_only_with_exact_error(self):
        for value in (None, [], ["project"], "project", 1, 1.5, True):
            with self.subTest(value=value):
                self.project_path.write_text(json.dumps(value), encoding="utf-8")

                response = self.service.handle_request(
                    {"verb": "open_project", "project_root": str(self.root)}
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["snapshot"]["read_only"])
                self.assertEqual(
                    ["invalid project JSON: root must be an object"],
                    response["snapshot"]["errors"],
                )

    def test_invalid_project_opens_read_only_with_projectlib_diagnostics(self):
        project = self._project()
        project["schema_version"] = 99
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            ["project schema_version must be 1"], response["snapshot"]["errors"]
        )

    def test_malformed_project_collections_do_not_crash_snapshot(self):
        project = self._project()
        project["operations"] = None
        self.project_path.write_text(json.dumps(project), encoding="utf-8")

        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["snapshot"]["read_only"])
        self.assertEqual(
            ["project validation failed: 'NoneType' object is not iterable"],
            response["snapshot"]["errors"],
        )
        self.assertEqual(0, response["snapshot"]["view"]["operation_count"])

    def test_malformed_active_sequence_and_plan_values_do_not_crash_snapshot(self):
        malformed = (
            ("active_sequence", []),
            ("plan", []),
            ("plan", {"path": "captions/captions-plan.json"}),
        )
        for field, value in malformed:
            with self.subTest(field=field, value=value):
                project = self._project()
                if field == "active_sequence":
                    project[field] = value
                else:
                    project["operations"][0][field] = value
                self.project_path.write_text(json.dumps(project), encoding="utf-8")

                response = self.service.handle_request(
                    {"verb": "open_project", "project_root": str(self.root)}
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["snapshot"]["read_only"])
                if field == "plan":
                    self.assertNotIn(
                        "plan",
                        {item["kind"] for item in response["snapshot"]["resources"]},
                    )

    def test_root_and_registered_resources_must_remain_inside_project(self):
        outside = Path(self.temp_dir.name).parent / "not-a-project"
        response = self.service.handle_request(
            {"verb": "open_project", "project_root": str(outside)}
        )
        self.assertEqual(
            {"ok": False, "error": "project root must contain work/project.json"},
            response,
        )

        project = self._project()
        project["operations"][0]["plan"] = "../../outside.json"
        self.project_path.write_text(json.dumps(project), encoding="utf-8")
        escaped = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        self.assertTrue(escaped["snapshot"]["read_only"])
        self.assertIn(
            "project path escapes root: ../../outside.json",
            escaped["snapshot"]["errors"],
        )

    def test_open_project_requires_an_explicit_root_even_from_a_project_directory(self):
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            response = self.service.handle_request({"verb": "open_project"})
        finally:
            os.chdir(previous)

        self.assertEqual(
            {"ok": False, "error": "project root must contain work/project.json"},
            response,
        )

    def test_manifest_resolved_path_must_remain_inside_project_root(self):
        root = self.root
        manifest = root / "work" / "project.json"
        escaped = root.parent / "outside-project.json"
        real_resolve = Path.resolve

        def resolve_path(path, strict=False):
            if path == manifest:
                return escaped
            return real_resolve(path, strict=strict)

        with mock.patch.object(Path, "resolve", autospec=True, side_effect=resolve_path):
            with self.assertRaisesRegex(
                ValueError, "project root must contain work/project.json"
            ):
                canonical_project_root(root)

    def test_unhashable_and_blank_resource_identifiers_are_rejected(self):
        opened = self.service.handle_request(
            {"verb": "open_project", "project_root": str(self.root)}
        )
        project_id = opened["project_id"]

        for invalid in (None, "", "   ", []):
            with self.subTest(project_id=invalid):
                self.assertEqual(
                    {
                        "ok": False,
                        "error": "project_id must be a nonblank string",
                    },
                    self.service.handle_request(
                        {"verb": "get_snapshot", "project_id": invalid}
                    ),
                )
        for invalid in (None, "", "   ", {}):
            with self.subTest(resource_id=invalid):
                self.assertEqual(
                    {
                        "ok": False,
                        "error": "resource_id must be a nonblank string",
                    },
                    self.service.handle_request(
                        {
                            "verb": "get_resource",
                            "project_id": project_id,
                            "resource_id": invalid,
                        }
                    ),
                )

    def test_request_exception_boundary_returns_fixed_error(self):
        with mock.patch.object(
            self.service, "_dispatch", side_effect=RuntimeError("private detail")
        ):
            response = self.service.handle_request({"verb": "get_snapshot"})

        self.assertEqual({"ok": False, "error": "invalid request"}, response)

    def test_json_line_entrypoint_rejects_unknown_verbs(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "protocol_service.py")],
            input='{"verb":"run_shell","command":"whoami"}\n',
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            {"ok": False, "error": "unknown verb"},
            json.loads(result.stdout),
        )
        self.assertEqual("", result.stderr)

    def test_json_line_loop_survives_a_malformed_request(self):
        result = subprocess.run(
            [sys.executable, str(RUNTIME / "protocol_service.py")],
            input=(
                '{"verb":"get_snapshot","project_id":[]}\n'
                '{"verb":"run_shell","command":"whoami"}\n'
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            [
                {
                    "ok": False,
                    "error": "project_id must be a nonblank string",
                },
                {"ok": False, "error": "unknown verb"},
            ],
            [json.loads(line) for line in result.stdout.splitlines()],
        )
        self.assertEqual("", result.stderr)

    def _write_project(self):
        self.project_path.write_text(json.dumps(self._project()), encoding="utf-8")

    def _project(self):
        stat = self.source.stat()
        return {
            "schema_version": 1,
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                    "duration_s": 1.0,
                },
            },
            "active_sequence": "main",
            "sequences": {
                "main": {
                    "timeline": "timeline.json",
                    "operations": ["captions"],
                }
            },
            "operations": [
                {
                    "id": "captions",
                    "revision": 1,
                    "status": "draft",
                    "depends_on": [],
                    "based_on": {},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": True,
                        "changes_audio": False,
                    },
                    "plan": "captions/captions-plan.json",
                    "outputs": [],
                }
            ],
            "reviews": [],
        }


if __name__ == "__main__":
    unittest.main()
