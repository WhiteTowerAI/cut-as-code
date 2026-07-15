import json
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import ROOT, load_script


gradelib = load_script("skills/video-color-grade/scripts/gradelib.py", "grade_plan_gradelib")


def canonical_plan(**changes):
    plan = {
        "schema_version": 1,
        "target": "base-video",
        "base": "eq=contrast=1.1",
        "looks": [{"name": "clean", "chain": "null"}],
        "selected_look": "clean",
        "evidence_refs": ["media:source"],
    }
    plan.update(changes)
    return plan


class GradePlanTests(unittest.TestCase):
    def test_canonical_grade_plan_unwraps_for_existing_scripts(self):
        spec = gradelib.normalize_spec(canonical_plan())
        self.assertEqual("clean", gradelib.get_look(spec, "clean")["name"])
        self.assertEqual("eq=contrast=1.1,null", gradelib.full_chain(spec, spec["looks"][0]))

    def test_legacy_looks_spec_remains_accepted(self):
        legacy = {
            "base": "eq=brightness=0.01",
            "looks": [{"name": "legacy", "chain": "eq=saturation=1.1"}],
        }
        self.assertEqual(legacy, gradelib.normalize_spec(legacy))

    def test_repository_legacy_looks_example_loads(self):
        spec = gradelib.load_spec(ROOT / "skills/video-color-grade/looks.example.json")
        self.assertGreaterEqual(len(spec["looks"]), 5)
        self.assertEqual("clean_neutral", gradelib.get_look(spec, "clean_neutral")["name"])

    def test_load_spec_validates_canonical_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grade-plan.json"
            path.write_text(json.dumps(canonical_plan(target="captions")), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "target"):
                gradelib.load_spec(path)

    def test_unsupported_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "target"):
            gradelib.normalize_spec(canonical_plan(target="captions"))

    def test_selected_look_must_exist(self):
        with self.assertRaisesRegex(ValueError, "selected look"):
            gradelib.normalize_spec(canonical_plan(selected_look="missing"))

    def test_delivery_requires_selected_look(self):
        plan = canonical_plan()
        del plan["selected_look"]
        with self.assertRaisesRegex(ValueError, "selected_look"):
            gradelib.normalize_spec(plan, require_selected=True)


if __name__ == "__main__":
    unittest.main()
