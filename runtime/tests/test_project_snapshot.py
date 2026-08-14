import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME_ROOT))

from project_snapshot import build_snapshot


class ProjectSnapshotTests(unittest.TestCase):
    def test_snapshot_exposes_only_the_opaque_authoritative_source_media_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input").mkdir()
            (root / "work").mkdir()
            (root / "input" / "source.mp4").write_bytes(b"fixture")
            (root / "work" / "timeline.json").write_text(json.dumps({
                "schema_version": 1,
                "source_duration_s": 1,
                "program_duration_s": 1,
                "fps": {"num": 30, "den": 1},
                "clips": [],
            }), encoding="utf-8")
            (root / "work" / "project.json").write_text(json.dumps({
                "schema_version": 1,
                "source": {"path": "../input/source.mp4"},
                "active_sequence": "main",
                "sequences": {"main": {"timeline": "timeline.json", "operations": []}},
                "operations": [],
                "reviews": [],
            }), encoding="utf-8")

            snapshot = build_snapshot(root)

        expected = "asset_" + hashlib.sha256(b"input/source.mp4").hexdigest()[:24]
        self.assertEqual(expected, snapshot["view"]["source_media_id"])
        self.assertNotIn("source.mp4", json.dumps(snapshot["view"]))


if __name__ == "__main__":
    unittest.main()
