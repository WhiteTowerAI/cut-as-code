"""Regression tests for the portable local editor plugin package."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import urllib.parse
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "build_plugin_package.ps1"
PLUGIN_MANIFEST = REPOSITORY_ROOT / ".codex-plugin" / "plugin.json"
MCP_MANIFEST = REPOSITORY_ROOT / ".mcp.json"
BUNDLED_PYTHON = Path(
    r"C:\Users\Charles Kang\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)
ENTRY_SKILLS = {
    "cut-as-code",
    "video-understand",
    "video-cut",
    "video-color-grade",
    "video-add-b-roll",
    "video-add-graphic-motion",
    "video-add-captions",
    "video-add-content-cards",
    "video-edit-compare",
    "video-to-shorts",
}
FORBIDDEN_PATH_PARTS = {
    ".env",
    ".git",
    ".hyperframes",
    "cache",
    "docs",
    "fixtures",
    "node_modules",
    "screenshots",
    "test-results",
    "tests",
    "work",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".map",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".pyc",
    ".tmp",
    ".wav",
    ".webm",
    ".webp",
}
EDITOR_ASSETS = {
    "viewer-poster.png", "brand.png", "caption-boxed.png", "caption-clean.png",
    "caption-minimal.png", "caption-pill.png", "caption-shorts.png",
    "caption-social-bold.png", "caption-stroked.png", "card-cta.png",
    "card-lower-third.png", "card-product.png", "card-quote.png", "card-split.png",
    "card-stat.png", "city.png", "founder.png", "icon-filter.svg", "icon-search.svg",
    "icon-upload.svg", "product.png", "ASSET_MANIFEST.json",
}
THIRD_PARTY_COMPONENTS = {
    ("@fontsource/inter", "5.3.0", "OFL-1.1"),
    ("lucide-react", "0.468.0", "ISC"),
    ("react", "19.2.8", "MIT"),
    ("react-dom", "19.2.8", "MIT"),
    ("scheduler", "0.27.0", "MIT"),
    ("zustand", "5.0.14", "MIT"),
    ("@animxyz/core", "vendored", "MIT"),
}


class PluginPackageTests(unittest.TestCase):
    def test_manifest_declares_the_local_stdio_launcher(self) -> None:
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        mcp = json.loads(MCP_MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "cut-as-code-editor")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(
            mcp,
            {
                "mcpServers": {
                    "cut-as-code-editor": {
                        "command": "node",
                        "args": ["./runtime/mcp.cjs"],
                    }
                }
            },
        )

    def test_package_is_portable_deterministic_and_launches_after_extraction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut as code package ") as temporary:
            root = Path(temporary)
            first = root / "first.zip"
            second = root / "second.zip"
            self._build(first)
            self._build(second)
            self.assertEqual(self._sha256(first), self._sha256(second))

            package_root = self._inspect_archive(first)
            installed = root / "installed plugin path with spaces"
            with zipfile.ZipFile(first) as archive:
                archive.extractall(installed)
            extracted = installed / package_root
            self._audit_route_allowlist(extracted)
            self._audit_graphic_motion_core(extracted, root / "graphic motion core project")
            self._smoke_open_editor(extracted, root / "video project with spaces", root)

    def _build(self, output: Path) -> None:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(BUILD_SCRIPT),
                "-OutputPath",
                str(output),
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            timeout=180,
        )

    def _inspect_archive(self, output: Path) -> str:
        with zipfile.ZipFile(output) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            self.assertTrue(names)
            self.assertTrue(all("\\" not in name for name in names))
            self.assertEqual(names, sorted(names))
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(len({name.casefold() for name in names}), len(names))
            roots = {name.split("/", 1)[0] for name in names}
            self.assertEqual(roots, {"cut-as-code-editor"})
            relative_names = [name.removeprefix("cut-as-code-editor/") for name in names]

            required = {
                ".codex-plugin/plugin.json",
                ".mcp.json",
                "LICENSE",
                "PACKAGE_AUDIT.json",
                "README.md",
                "SBOM.spdx.json",
                "THIRD_PARTY_NOTICES.md",
                "runtime/mcp.cjs",
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
                "runtime/sidecar.cjs",
                "ui/dist/index.html",
            }
            self.assertTrue(required.issubset(relative_names))
            notices = archive.read("cut-as-code-editor/THIRD_PARTY_NOTICES.md").decode("utf-8")
            self.assertIn("nexu-io/motion-anything", notices)
            self.assertIn("b016900d9ee92fc2d3e4dc520359cc8999d2ed4e", notices)
            for name, version, license_id in THIRD_PARTY_COMPONENTS:
                self.assertIn(name, notices)
                self.assertIn(version, notices)
                self.assertIn(license_id, notices)

            sbom = json.loads(archive.read("cut-as-code-editor/SBOM.spdx.json"))
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            self.assertEqual(sbom["dataLicense"], "CC0-1.0")
            self.assertEqual(
                {(item["name"], item["versionInfo"], item["licenseConcluded"]) for item in sbom["packages"]},
                THIRD_PARTY_COMPONENTS,
            )
            self.assertTrue(all(item["checksums"] for item in sbom["packages"]))

            audit = json.loads(archive.read("cut-as-code-editor/PACKAGE_AUDIT.json"))
            self.assertEqual(audit["schema_version"], 1)
            self.assertEqual(audit["scope"], "all packaged files")
            self.assertEqual(audit["license_audit"]["status"], "pass")
            self.assertEqual(audit["license_audit"]["component_count"], len(THIRD_PARTY_COMPONENTS))
            self.assertEqual(audit["license_audit"]["unresolved"], [])
            self.assertEqual(audit["secret_audit"]["status"], "pass")
            self.assertEqual(audit["secret_audit"]["findings"], [])
            self.assertGreater(audit["secret_audit"]["files_scanned"], 0)
            self.assertEqual(
                audit["vendored_sources"][0]["sha256"],
                "4a133a5e4bf9ff2b3c87d7ef3a20064ccaab3c8838cafbf540c75d658f7c451d",
            )
            packaged_skills = {
                Path(name).parts[1]
                for name in relative_names
                if name.startswith("skills/") and len(Path(name).parts) > 2
            }
            self.assertTrue(ENTRY_SKILLS.issubset(packaged_skills))
            self.assertIn("skills/video-add-graphic-motion/SKILL.md", relative_names)
            self.assertNotIn("skills/video-add-graphic-motion/recipes/imported/SKILL.md", relative_names)
            animxyz_manifests = [
                name for name in relative_names
                if name.startswith("skills/video-add-graphic-motion/recipes/animxyz/")
                and name.endswith("/recipe.motion.yaml")
            ]
            self.assertEqual(len(animxyz_manifests), 20)
            graphic_motion_skill = archive.read(
                "cut-as-code-editor/skills/video-add-graphic-motion/SKILL.md"
            ).decode("utf-8")
            self.assertIn("exactly 10 selectable AnimXYZ core recipes", graphic_motion_skill)
            self.assertIn("exactly 20 AnimXYZ recipe manifests", graphic_motion_skill)
            self.assertIn("missing_content_pack", graphic_motion_skill)
            self.assertNotIn("1,477 recipes", graphic_motion_skill)
            self.assertNotIn("REQUIRED SUB-SKILLS", graphic_motion_skill)
            self.assertNotIn("reference/recipe-selection.md", graphic_motion_skill)
            normalized_graphic_motion_skill = " ".join(graphic_motion_skill.split())
            self.assertIn("Non-skipped validate/register/render is unavailable", normalized_graphic_motion_skill)
            packaged_assets = {
                Path(name).name for name in relative_names
                if name.startswith("ui/dist/assets/editor/")
            }
            self.assertEqual(packaged_assets, EDITOR_ASSETS)

            for name in relative_names:
                parts = set(Path(name).parts)
                self.assertFalse(parts & FORBIDDEN_PATH_PARTS, name)
                self.assertFalse(Path(name).name.lower().startswith(".env"), name)
                is_approved_editor_asset = name.startswith("ui/dist/assets/editor/") and Path(name).name in EDITOR_ASSETS
                if not is_approved_editor_asset:
                    self.assertNotIn(Path(name).suffix.lower(), FORBIDDEN_SUFFIXES, name)
                self.assertNotIn("..", Path(name).parts, name)

            executable_sources = {
                name: archive.read(f"cut-as-code-editor/{name}").decode("utf-8")
                for name in relative_names
                if name.startswith("runtime/") and Path(name).suffix in {".cjs", ".py"}
            }
            self.assertEqual(set(executable_sources), {
                "runtime/mcp.cjs",
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
                "runtime/sidecar.cjs",
            })
            sidecar = executable_sources["runtime/sidecar.cjs"]
            mcp = executable_sources["runtime/mcp.cjs"]
            self.assertIn("const HTTP_ROUTE_ALLOWLIST", sidecar)
            self.assertIn("routeForRequest", sidecar)
            self.assertIn("const PROTOCOL_VERB_ALLOWLIST", sidecar)
            self.assertIn("const MCP_TOOL_ALLOWLIST", mcp)
            for source in executable_sources.values():
                for forbidden in ("execFile", "spawnSync", "shell: true", "codex exec", "/v1/render", "/v1/preview", "/v1/jobs", "/v1/shell", "/v1/exec", "/v1/files"):
                    self.assertNotIn(forbidden, source)
            self.assertEqual(sidecar.count("spawn("), 1)
            self.assertEqual(mcp.count("spawn("), 1)
            self.assertIn("startProtocolService", sidecar)
            self.assertIn("sidecar.cjs", mcp)
            self.assertNotIn("ready-file", sidecar)
            self.assertNotIn("readyFile", mcp)
            self.assertNotIn("bootstrapToken", sidecar)
            self.assertNotIn("bootstrapToken", mcp)
            self.assertNotIn("cut-as-code-editor-sidecars", mcp)
        return "cut-as-code-editor"

    def _audit_route_allowlist(self, plugin_root: Path) -> None:
        script = r"""
const sidecar = require(process.argv[1]);
const cases = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify({
  declared: sidecar.HTTP_ROUTE_ALLOWLIST.map((route) => route.id),
  actual: cases.map(([method, pathname]) => sidecar.routeForRequest(method, pathname)?.id ?? null),
}));
"""
        cases = [
            ["GET", "/"],
            ["GET", "/v1/meta"],
            ["GET", "/v1/projects/project_a/snapshot"],
            ["POST", "/v1/projects/project_a/transactions"],
            ["POST", "/v1/projects/project_a/reviews/decision"],
            ["GET", "/v1/projects/project_a/resources/res_a1"],
            ["GET", "/v1/projects/project_a/media/asset_a1"],
            ["GET", "/v1/projects/project_a/artifacts/artifact_a1"],
            ["GET", "/v1/projects/project_a/events"],
            ["GET", "/assets/index.js"],
            ["HEAD", "/assets/index.js"],
            ["POST", "/v1/meta"],
            ["GET", "/v1/render"],
            ["POST", "/v1/session/bootstrap"],
            ["GET", "/v1/projects/project_a/files/anything"],
        ]
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(plugin_root / "runtime" / "sidecar.cjs"),
                json.dumps(cases),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        audit = json.loads(result.stdout)
        self.assertEqual(
            audit["declared"],
            ["launch", "meta", "snapshot", "transaction", "review", "resource", "file", "events", "static"],
        )
        self.assertEqual(
            audit["actual"],
            ["launch", "meta", "snapshot", "transaction", "review", "resource", "file", "file", "events", "static", "static", None, None, None, None],
        )

    def _audit_graphic_motion_core(self, plugin_root: Path, project_root: Path) -> None:
        library = plugin_root / "skills" / "video-add-graphic-motion" / "scripts" / "recipe_library.mjs"
        searched = subprocess.run(
            ["node", str(library), "search", "--query", "animxyz fade rotate", "--limit", "20", "--json"],
            cwd=plugin_root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        results = json.loads(searched.stdout)
        self.assertTrue(results)
        self.assertEqual({item["surface"] for item in results}, {"animxyz"})
        shown = subprocess.run(
            ["node", str(library), "show", "xyz-fade-up", "--json"],
            cwd=plugin_root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(json.loads(shown.stdout)["id"], "xyz-fade-up")
        materialized = subprocess.run(
            ["node", str(library), "materialize", "xyz-fade-up", "--project", str(project_root), "--cue", "gm-core", "--json"],
            cwd=plugin_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        receipt = json.loads(materialized.stdout)
        self.assertEqual(receipt["id"], "xyz-fade-up")
        self.assertTrue(receipt["files"])
        self.assertTrue(all((project_root / item["path"]).is_file() for item in receipt["files"]))

    def _smoke_open_editor(
        self, plugin_root: Path, project_root: Path, temporary_root: Path
    ) -> None:
        self._create_project(project_root)
        environment = {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON)}
        process = self._start_mcp(plugin_root, environment)
        first_pid = None
        try:
            tools = self._rpc(process, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual([item["name"] for item in tools["result"]["tools"]], ["open_editor"])
            opened = self._rpc(process, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root)}},
            })
            details = json.loads(opened["result"]["content"][0]["text"])
            self.assertTrue(details["url"].startswith("http://127.0.0.1:"))
            self.assertNotIn("bootstrap", details["url"])
            self.assertEqual(set(details), {"pid", "projectRoot", "url", "projectId"})
            first_pid = details["pid"]
            self._assert_real_browser_ready(details["url"], details["projectId"])
            self.assertEqual(self._navigate(details["url"]), 401)

            reopened = self._rpc(process, {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root)}},
            })
            reconnected = json.loads(reopened["result"]["content"][0]["text"])
            self.assertEqual(reconnected["url"], details["url"])
            self.assertEqual(reconnected["pid"], details["pid"])
            self._assert_adversarial_launch_rejections(reconnected["url"], reconnected["projectId"])
            self._assert_real_browser_ready(reconnected["url"], reconnected["projectId"])
            self.assertEqual(self._navigate(reconnected["url"]), 401)

            expiring = self._open_editor(process, 4, project_root)
            time.sleep(10.2)
            self.assertEqual(self._navigate(expiring["url"]), 401)

            final = self._open_editor(process, 5, project_root)
            self._assert_real_browser_ready(final["url"], final["projectId"])
            self._assert_no_secret_persistence(temporary_root, process)
            self._rpc(process, {"jsonrpc": "2.0", "id": 6, "method": "shutdown"})
        finally:
            self._stop_mcp(process)
        if first_pid is not None:
            self.assertFalse(self._pid_is_live(first_pid))

        restarted = self._start_mcp(plugin_root, environment)
        restarted_pid = None
        try:
            details = self._open_editor(restarted, 1, project_root)
            restarted_pid = details["pid"]
            self.assertNotEqual(restarted_pid, first_pid)
            self._assert_real_browser_ready(details["url"], details["projectId"])
            self._rpc(restarted, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
        finally:
            self._stop_mcp(restarted)
        if restarted_pid is not None:
            self.assertFalse(self._pid_is_live(restarted_pid))

    def _assert_adversarial_launch_rejections(self, url: str, project_id: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        self.assertEqual(self._navigate(f"{base}/?project=wrong-{project_id}"), 401)
        self.assertEqual(self._navigate(f"{url}&extra=1"), 401)
        self.assertEqual(self._navigate(url, method="POST"), 404)
        self.assertEqual(self._navigate(url, destination="script"), 401)
        self.assertEqual(self._navigate(url, site="same-origin"), 401)
        self.assertEqual(self._navigate(url, site="cross-site"), 401)

    @staticmethod
    def _navigate(
        url: str, method: str = "GET", destination: str = "document", site: str = "none"
    ) -> int:
        parsed = urllib.parse.urlsplit(url)
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        try:
            path = urllib.parse.urlunsplit(("", "", parsed.path, parsed.query, ""))
            connection.request(method, path, headers={
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": destination,
                "Sec-Fetch-Site": site,
            })
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    @staticmethod
    def _start_mcp(plugin_root: Path, environment: dict[str, str]) -> subprocess.Popen[str]:
        return subprocess.Popen(
            ["node", str(plugin_root / "runtime" / "mcp.cjs")],
            cwd=plugin_root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @staticmethod
    def _stop_mcp(process: subprocess.Popen[str]) -> None:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        if process.stdout and not process.stdout.closed:
            process.stdout.close()
        if process.stderr and not process.stderr.closed:
            process.stderr.close()

    @staticmethod
    def _pid_is_live(pid: int) -> bool:
        result = subprocess.run(
            ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and str(pid) in result.stdout

    def _open_editor(
        self, process: subprocess.Popen[str], request_id: int, project_root: Path
    ) -> dict:
        opened = self._rpc(process, {
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": "open_editor", "arguments": {"project_root": str(project_root)}},
        })
        return json.loads(opened["result"]["content"][0]["text"])

    def _assert_real_browser_ready(self, url: str, project_id: str) -> None:
        script = r"""
const { chromium } = require(process.argv[1]);
(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const page = await browser.newPage();
    await page.goto(process.argv[2]);
    await page.waitForFunction(() => document.documentElement.dataset.runtimeState === 'ready');
    const cookie = (await page.context().cookies()).find((item) => item.name === 'cut_session');
    process.stdout.write(JSON.stringify({
      url: page.url(),
      shellVisible: await page.locator('[data-editor-shell]').isVisible(),
      projectVisible: await page.getByText(process.argv[3], { exact: true }).isVisible(),
      cookie,
    }));
  } finally {
    await browser.close();
  }
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(REPOSITORY_ROOT / "ui" / "node_modules" / "playwright"),
                url,
                project_id,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["url"], url)
        self.assertTrue(evidence["shellVisible"])
        self.assertTrue(evidence["projectVisible"])
        self.assertTrue(evidence["cookie"]["httpOnly"])
        session = evidence["cookie"]["value"]
        self.assertTrue(session)
        self._session_values = getattr(self, "_session_values", []) + [session]

    def _assert_no_secret_persistence(
        self, temporary_root: Path, process: subprocess.Popen[str]
    ) -> None:
        secret_values = getattr(self, "_session_values", [])
        self.assertTrue(secret_values)
        scan_roots = [temporary_root]
        for root in scan_roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.stat().st_size > 2_000_000:
                    continue
                try:
                    content = path.read_bytes()
                except (OSError, PermissionError):
                    continue
                for secret in secret_values:
                    self.assertNotIn(secret.encode("ascii"), content, str(path))
        for known_path in (
            Path(tempfile.gettempdir()) / "cut-as-code-editor-sidecars.json",
            Path(tempfile.gettempdir()) / "cut-as-code-editor.log",
        ):
            if known_path.is_file():
                content = known_path.read_bytes()
                for secret in secret_values:
                    self.assertNotIn(secret.encode("ascii"), content, str(known_path))
        captured = str(process.args)
        mcp_source = (temporary_root / "installed plugin path with spaces" / "cut-as-code-editor" / "runtime" / "mcp.cjs").read_text(encoding="utf-8")
        sidecar_source = (temporary_root / "installed plugin path with spaces" / "cut-as-code-editor" / "runtime" / "sidecar.cjs").read_text(encoding="utf-8")
        for secret in secret_values:
            self.assertNotIn(secret, captured)
            self.assertNotIn(secret, mcp_source)
            self.assertNotIn(secret, sidecar_source)

    @staticmethod
    def _rpc(process: subprocess.Popen[str], request: dict) -> dict:
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            if line:
                return json.loads(line)
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else ""
                raise AssertionError(f"MCP exited {process.returncode}: {stderr}")
        raise AssertionError("MCP response timed out")

    @staticmethod
    def _create_project(root: Path) -> None:
        (root / "work" / "captions").mkdir(parents=True)
        (root / "input").mkdir()
        source = root / "input" / "source.mp4"
        source.write_bytes(b"fixture-video")
        stat = source.stat()
        (root / "work" / "captions" / "captions-plan.json").write_text('{"cues": []}\n', encoding="utf-8")
        (root / "work" / "timeline.json").write_text(json.dumps({
            "schema_version": 1, "source_duration_s": 1, "program_duration_s": 1,
            "fps": {"num": 30, "den": 1},
            "clips": [{"id": "clip-1", "source_range": {"start_s": 0, "end_s": 1}, "program_range": {"start_s": 0, "end_s": 1}, "speed": 1}],
        }), encoding="utf-8")
        (root / "work" / "project.json").write_text(json.dumps({
            "schema_version": 1,
            "source": {"path": "../input/source.mp4", "fingerprint": {"size": stat.st_size, "modified_ns": stat.st_mtime_ns, "duration_s": 1}},
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": ["captions"]}},
            "operations": [{"id": "captions", "revision": 1, "status": "draft", "depends_on": [], "based_on": {}, "target": {"sequence": "main", "scope": "full"}, "effects": {"changes_timeline": False, "changes_geometry": False, "changes_video_pixels": True, "changes_audio": False}, "plan": "captions/captions-plan.json", "outputs": []}],
            "reviews": [], "render": {"status": "draft"},
        }), encoding="utf-8")

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
