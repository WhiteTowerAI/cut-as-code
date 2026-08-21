import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "video-understand" / "scripts"))
import projectlib


class HubProjectsTests(unittest.TestCase):
    def test_browser_folder_name_resolves_to_unregistered_project(self):
        script = r"""
const path = require('node:path');
const { resolveSelectedProject } = require(process.argv[1]);
(async () => {
  const parent = process.argv[2];
  const selected = await resolveSelectedProject({ registry: { projects: [{ root: path.join(parent, 'registered') }] } }, 'candidate');
  process.stdout.write(JSON.stringify({ selected }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
        with tempfile.TemporaryDirectory(prefix="cut hub picker ") as temporary:
            parent = Path(temporary)
            self._project(parent / "registered")
            self._project(parent / "nested" / "candidate")
            result = subprocess.run(
                ["node", "-e", script, str(ROOT / "runtime" / "hub.cjs"), str(parent)],
                cwd=ROOT, check=True, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(parent / "nested" / "candidate", Path(json.loads(result.stdout)["selected"]))

    def test_creates_scaffold_without_overwriting_and_discovers_unregistered_sibling(self):
        with tempfile.TemporaryDirectory(prefix="cut hub projects ") as temporary:
            parent = Path(temporary)
            registered = parent / "registered"
            candidate = parent / "candidate"
            source = parent / "source.mp4"
            source.write_bytes(b"video")
            self._project(registered)
            self._project(candidate)
            script = r"""
const path = require('node:path');
const { createProjectScaffold, discoverProjects, publicCandidates } = require(process.argv[1]);
(async () => {
  const parent = process.argv[2];
  const registered = path.join(parent, 'registered');
  const state = { registry: { projects: [{ root: registered }] } };
  const before = await discoverProjects(state);
  const probeMedia = async () => ({ duration: 2.5, fps: { num: 30000, den: 1001 } });
  const source = path.join(parent, 'source.mp4');
  const created = await createProjectScaffold(parent, 'new project', source, { probeMedia });
  let duplicate;
  try { await createProjectScaffold(parent, 'new project', source, { probeMedia }); } catch (error) { duplicate = error.message; }
  process.stdout.write(JSON.stringify({ before: publicCandidates(before), created, duplicate }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
            result = subprocess.run(
                ["node", "-e", script, str(ROOT / "runtime" / "hub.cjs"), str(parent)],
                cwd=ROOT, check=True, capture_output=True, text=True, timeout=20,
            )
            evidence = json.loads(result.stdout)
            self.assertEqual(["candidate"], [item["displayName"] for item in evidence["before"]])
            self.assertNotIn("root", evidence["before"][0])
            self.assertEqual(parent / "new project", Path(evidence["created"]))
            self.assertEqual("project already exists", evidence["duplicate"])
            manifest = json.loads((parent / "new project" / "work" / "project.json").read_text())
            self.assertEqual("main", manifest["active_sequence"])
            self.assertEqual("../input/source.mp4", manifest["source"]["path"])
            timeline = json.loads((parent / "new project" / "work" / "timeline.json").read_text())
            self.assertEqual(2.5, timeline["program_duration_s"])
            self.assertEqual({"num": 30000, "den": 1001}, timeline["fps"])
            self.assertEqual([], projectlib.validate_project(manifest, parent / "new project", check_files=True))
            self.assertTrue(all((parent / "new project" / name).is_dir() for name in ("input", "review", "final", "work")))

    @staticmethod
    def _project(root):
        (root / "work").mkdir(parents=True)
        (root / "work" / "project.json").write_text("{}", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
