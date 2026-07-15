import os
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import load_script, project_fixture, timeline_fixture, write_json


projectlib = load_script(
    "skills/video-understand/scripts/projectlib.py", "open_recut_projectlib"
)


class ProjectProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "input").mkdir()
        (self.root / "work" / "rough-cut").mkdir(parents=True)
        (self.root / "work" / "content-cards").mkdir(parents=True)
        self.source = self.root / "input" / "source.mp4"
        self.source.write_bytes(b"x")
        project = project_fixture(self.root)
        stat = self.source.stat()
        project["source"]["fingerprint"].update(
            size=stat.st_size, modified_ns=stat.st_mtime_ns
        )
        self.project = project
        write_json(self.root / "work" / "timeline.json", timeline_fixture())
        write_json(self.root / "work" / "rough-cut" / "edit-plan.json", {})
        write_json(self.root / "work" / "content-cards" / "cards-plan.json", {})

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, project=None, check_files=False):
        return projectlib.validate_project(
            project or self.project, self.root, check_files=check_files
        )

    def test_valid_project_has_no_errors(self):
        self.assertEqual([], self.errors())

    def test_revision_mismatch_is_stale(self):
        self.project["operations"][1]["based_on"] = {"understanding": 0}
        self.assertTrue(
            any(
                "rough-cut based_on understanding=0, current=1" in error
                for error in self.errors()
            )
        )

    def test_dependency_cycle_is_rejected(self):
        self.project["operations"][0]["depends_on"] = ["rough-cut"]
        self.assertTrue(any("dependency cycle" in error for error in self.errors()))

    def test_missing_dependency_is_rejected(self):
        self.project["operations"][1]["depends_on"] = ["missing"]
        self.assertTrue(any("missing dependency" in error for error in self.errors()))

    def test_duplicate_operation_id_is_rejected(self):
        self.project["operations"].append(dict(self.project["operations"][0]))
        self.assertTrue(any("duplicate operation id" in error for error in self.errors()))

    def test_invalid_status_is_rejected(self):
        self.project["operations"][0]["status"] = "done"
        self.assertTrue(any("invalid status" in error for error in self.errors()))

    def test_active_sequence_operation_must_exist(self):
        self.project["sequences"]["main"]["operations"].append("missing")
        self.assertTrue(any("unknown operation" in error for error in self.errors()))

    def test_active_sequence_name_must_exist(self):
        self.project["active_sequence"] = "missing"
        self.assertTrue(any("active_sequence" in error for error in self.errors()))

    def test_reserved_render_dependency_is_allowed_for_review(self):
        self.project["reviews"] = [
            {
                "id": "compare",
                "revision": 1,
                "depends_on": ["render"],
                "based_on": {},
                "status": "draft",
                "plan": "edit-compare/compare-plan.json",
            }
        ]
        self.assertEqual([], self.errors())

    def test_missing_plan_is_rejected_when_file_checks_enabled(self):
        (self.root / "work" / "rough-cut" / "edit-plan.json").unlink()
        self.assertTrue(any("missing file" in error for error in self.errors(check_files=True)))

    def test_quick_fingerprint_changes_with_file_metadata(self):
        first = projectlib.quick_fingerprint(self.source, duration_s=1.0)
        self.source.write_bytes(b"longer")
        os.utime(self.source, ns=(self.source.stat().st_atime_ns, self.source.stat().st_mtime_ns + 1))
        second = projectlib.quick_fingerprint(self.source, duration_s=1.0)
        self.assertNotEqual(first, second)

    def test_resolve_project_path_anchors_work_paths(self):
        resolved = projectlib.resolve_project_path(self.root, "rough-cut/edit-plan.json")
        self.assertEqual(self.root / "work" / "rough-cut" / "edit-plan.json", resolved)

    def test_resolve_project_path_allows_user_facing_parent(self):
        resolved = projectlib.resolve_project_path(self.root, "../final/final.mp4")
        self.assertEqual(self.root / "final" / "final.mp4", resolved)

    def test_resolve_project_path_rejects_escape(self):
        with self.assertRaises(ValueError):
            projectlib.resolve_project_path(self.root, "../../outside.txt")


if __name__ == "__main__":
    unittest.main()
