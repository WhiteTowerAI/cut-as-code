import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.protocol_testlib import ROOT, load_script, timeline_fixture


def understanding_fixture(start_s=1.0, end_s=1.4, kind="stat"):
    return {
        "schema_version": 1,
        "timeline_id": "source",
        "moments": [
            {
                "id": "moment-001",
                "kind": kind,
                "start_s": start_s,
                "end_s": end_s,
                "summary": "200 customers",
                "confidence": 0.9,
                "evidence_refs": ["segment:1"],
            }
        ],
    }


class CardsPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_script(
            "skills/video-add-content-cards/scripts/build_cards_plan.py",
            "build_cards_plan",
        )

    def test_kept_semantic_moment_maps_to_program_time(self):
        cards = self.builder.build_cards(understanding_fixture(), timeline_fixture())
        self.assertEqual(1.0, cards[0]["program_start_s"])
        self.assertEqual("moment-001", cards[0]["evidence_ref"])
        self.assertEqual({"start_s": 1.0, "end_s": 1.4}, cards[0]["source_range"])

    def test_dropped_semantic_moment_is_not_drafted(self):
        self.assertEqual(
            [], self.builder.build_cards(understanding_fixture(3.0, 3.4), timeline_fixture())
        )

    def test_card_duration_is_clamped_to_containing_clip(self):
        cards = self.builder.build_cards(
            understanding_fixture(1.8, 1.95, "question"), timeline_fixture()
        )
        self.assertAlmostEqual(0.2, cards[0]["duration_s"], places=6)

    def test_copy_remains_explicitly_draft(self):
        card = self.builder.build_cards(understanding_fixture(), timeline_fixture())[0]
        self.assertEqual("draft", card["copy"]["status"])
        self.assertEqual("200 customers", card["copy"]["suggested_text"])
        self.assertEqual({"eyebrow": None, "title": None, "detail": None}, card["copy"]["display"])
        self.assertEqual("pending", card["placement"]["face_clearance"])
        self.assertIn("composition", card["renderer"])

    def test_non_graphic_editorial_candidates_are_skipped(self):
        for kind in ("repetition", "tangent", "risk"):
            self.assertEqual(
                [], self.builder.build_cards(understanding_fixture(kind=kind), timeline_fixture())
            )

    def test_cli_writes_canonical_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            understanding = tmp / "understanding.json"
            timeline = tmp / "timeline.json"
            output = tmp / "cards-plan.json"
            understanding.write_text(json.dumps(understanding_fixture()), encoding="utf-8")
            timeline.write_text(json.dumps(timeline_fixture()), encoding="utf-8")
            subprocess.run(
                [
                    "python",
                    str(ROOT / "skills/video-add-content-cards/scripts/build_cards_plan.py"),
                    str(understanding),
                    str(timeline),
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(1, plan["schema_version"])
            self.assertEqual("overlay", plan["target"])
            self.assertEqual(1, len(plan["cards"]))


if __name__ == "__main__":
    unittest.main()
