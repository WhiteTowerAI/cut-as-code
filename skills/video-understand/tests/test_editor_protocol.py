"""Regression coverage for editor-only stale project snapshots."""

import copy
import sys
import unittest
from unittest import mock
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import projectlib  # noqa: E402


class EditorProtocolFreshnessTests(unittest.TestCase):
    def test_validate_project_rejects_stale_dependency_by_default(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(project, Path("."), check_files=False)

        self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_accepts_only_stale_node_with_old_based_on(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )

        self.assertFalse(any("based_on" in error for error in errors), errors)

        current = copy.deepcopy(project)
        current["operations"][1]["status"] = "approved"
        errors = projectlib.validate_project(
            current, Path("."), check_files=False, dependency_mode="allow_stale"
        )
        self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_rejects_non_old_or_invalid_based_on_revisions(self):
        for expected_revision in (999, "1", True, 0):
            with self.subTest(expected_revision=expected_revision):
                project = self._project_with_stale_dependency()
                project["operations"][1]["based_on"] = {"cut": expected_revision}

                errors = projectlib.validate_project(
                    project, Path("."), check_files=False, dependency_mode="allow_stale"
                )

                self.assertTrue(any("based_on" in error for error in errors), errors)

    def test_allow_stale_rejects_malformed_current_dependency_revision(self):
        for current_revision in ("2", True):
            with self.subTest(current_revision=current_revision):
                project = self._project_with_stale_dependency()
                project["operations"][0]["revision"] = current_revision

                errors = projectlib.validate_project(
                    project, Path("."), check_files=False, dependency_mode="allow_stale"
                )

                self.assertTrue(any("cut revision" in error for error in errors), errors)
                self.assertTrue(any("revision mismatch" in error for error in errors), errors)

    def test_allow_stale_accepts_review_node_with_old_based_on(self):
        project = self._project_with_stale_dependency()
        project["reviews"] = [
            {
                "id": "captions-review",
                "revision": 1,
                "status": "stale",
                "depends_on": ["cut"],
                "based_on": {"cut": 1},
            }
        ]

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )

        self.assertFalse(any("captions-review based_on" in error for error in errors), errors)

        errors = projectlib.validate_project(project, Path("."), check_files=False)
        self.assertTrue(any("captions-review based_on" in error for error in errors), errors)

        project["reviews"][0]["status"] = "approved"
        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="allow_stale"
        )
        self.assertTrue(any("captions-review based_on" in error for error in errors), errors)

    def test_require_current_and_render_plan_remain_strict(self):
        project = self._project_with_stale_dependency()

        errors = projectlib.validate_project(
            project, Path("."), check_files=False, dependency_mode="require_current"
        )
        self.assertTrue(any("based_on" in error for error in errors), errors)
        with mock.patch.object(
            projectlib,
            "validate_project",
            return_value=["revision mismatch: captions based_on cut=1, current=2"],
        ) as validate_project:
            with self.assertRaises(ValueError):
                projectlib.build_render_plan(project, Path("."))
        validate_project.assert_called_once_with(project, Path("."), check_files=True)

    def test_invalid_dependency_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dependency_mode"):
            projectlib.validate_project(
                self._project_with_stale_dependency(),
                Path("."),
                check_files=False,
                dependency_mode="ignore_dependencies",
            )

    @staticmethod
    def _project_with_stale_dependency():
        # The dependency validator only needs these operation fields before
        # later structural validation reports unrelated fixture omissions.
        return {
            "schema_version": 1,
            "active_sequence": "main",
            "sequences": {
                "main": {
                    "operations": ["cut", "captions"]
                }
            },
            "operations": [
                {
                    "id": "cut",
                    "revision": 2,
                    "status": "approved",
                    "depends_on": [],
                    "based_on": {},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": True,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                    },
                },
                {
                    "id": "captions",
                    "revision": 1,
                    "status": "stale",
                    "depends_on": ["cut"],
                    "based_on": {"cut": 1},
                    "target": {"sequence": "main", "scope": "full"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": True,
                        "changes_audio": False,
                    },
                },
            ],
        }


if __name__ == "__main__":
    unittest.main()
