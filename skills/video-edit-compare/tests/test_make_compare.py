import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_compare.py"
SPEC = importlib.util.spec_from_file_location("make_compare", SCRIPT)
make_compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(make_compare)


class SourceTimePartsTest(unittest.TestCase):
    def test_part_frames_share_absolute_source_boundaries(self):
        timeline = {
            "schema_version": 1,
            "timeline_id": "main",
            "source_asset_id": "source",
            "fps": {"num": 30000, "den": 1001},
            "source_duration_s": 1.0,
            "program_duration_s": 0.92,
            "clips": [
                {
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 0.04},
                    "program_range": {"start_s": 0.0, "end_s": 0.04},
                    "speed": 1.0,
                    "decision_ref": "edit-001",
                },
                {
                    "id": "clip-002",
                    "source_range": {"start_s": 0.08, "end_s": 0.12},
                    "program_range": {"start_s": 0.04, "end_s": 0.08},
                    "speed": 1.0,
                    "decision_ref": "edit-002",
                },
                {
                    "id": "clip-003",
                    "source_range": {"start_s": 0.16, "end_s": 1.0},
                    "program_range": {"start_s": 0.08, "end_s": 0.92},
                    "speed": 1.0,
                    "decision_ref": "edit-003",
                },
            ],
        }

        parts = make_compare.source_time_parts(timeline)

        self.assertTrue(all("frame_count" in part for part in parts))
        self.assertEqual(sum(part["frame_count"] for part in parts), 30)
        self.assertEqual(
            [(part["start_frame"], part["end_frame"]) for part in parts],
            [(0, 1), (1, 2), (2, 4), (4, 5), (5, 30)],
        )


if __name__ == "__main__":
    unittest.main()
