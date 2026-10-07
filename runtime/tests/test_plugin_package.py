"""Regression tests for the portable local editor plugin package."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.parse
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "build_plugin_package.ps1"
COMPLIANCE_SCRIPT = REPOSITORY_ROOT / "scripts" / "generate_package_compliance.cjs"
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
    "video-add-motion-graphics",
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
    ("Cal Sans", "1.000", "OFL-1.1"),
    ("GSAP", "3.12.5", "LicenseRef-GSAP-Standard"),
    ("Lexend", "1.007", "OFL-1.1"),
}
THIRD_PARTY_ASSETS = {
    "skills/video-add-captions/examples/fonts/CalSans-Regular.ttf": {
        "component": "Cal Sans",
        "sha256": "c7e50dba671a7b2e606d5bcb9390cbd5e4e1de269afc0bc98eb1eacc517fdb05",
        "license_url": "https://openfontlicense.org",
        "source_revision": "46b43bfb793e324d84a8c93f127d4addcadcbfd9",
    },
    "skills/video-add-captions/public/fonts/CalSans-Regular.ttf": {
        "component": "Cal Sans",
        "sha256": "c7e50dba671a7b2e606d5bcb9390cbd5e4e1de269afc0bc98eb1eacc517fdb05",
        "license_url": "https://openfontlicense.org",
        "source_revision": "46b43bfb793e324d84a8c93f127d4addcadcbfd9",
    },
    "skills/video-add-captions/public/gsap.min.js": {
        "component": "GSAP",
        "sha256": "c71e401021a12cfa35fe7afcf45240c0dea1ca87016d3921b9ecd35424e49026",
        "license_url": "https://gsap.com/standard-license",
        "source_revision": "a7646f5b8acf6369f30df1b04aa9a9c85dfae38c",
    },
    "skills/video-add-content-cards/assets/fonts/Lexend-VariableFont_wght.ttf": {
        "component": "Lexend",
        "sha256": "91342a7f7da58a6bc398057da404b563d8890cc755ab312718a7cea515c09232",
        "license_url": "https://scripts.sil.org/OFL",
        "source_revision": "388ae39e02759a6c5ff40419e1c2c43c2736e533",
    },
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

    def test_browser_opener_defaults_and_keeps_url_as_single_argv(self) -> None:
        script = r"""
const { TOOL, browserLaunchSpec, openBrowser, shouldOpenBrowser } = require(process.argv[1]);
const url = 'http://127.0.0.1:43123/?project=project_a&launch=token-value';
const calls = [];
(async () => {
  await openBrowser(url, (command, args, options) => {
    const handlers = {};
    const child = {
      unref() { calls.push({ event: 'unref' }); },
      once(event, handler) { handlers[event] = handler; return child; },
    };
    calls.push({ command, args, options });
    queueMicrotask(() => handlers.spawn?.());
    return child;
  }, 'win32');
  const failure = await openBrowser(url, () => {
    const handlers = {};
    const child = {
      unref() {},
      once(event, handler) { handlers[event] = handler; queueMicrotask(() => event === 'error' && handler(Object.assign(new Error('missing'), { code: 'ENOENT' }))); return child; },
    };
    return child;
  }, 'linux').then(() => null, (error) => error.message);
  process.stdout.write(JSON.stringify({
    defaultValue: shouldOpenBrowser(undefined),
    falseValue: shouldOpenBrowser(false),
    trueValue: shouldOpenBrowser(true),
    invalidValue: (() => { try { shouldOpenBrowser('false'); return null; } catch (error) { return error.message; } })(),
    description: TOOL.description,
    inputSchema: TOOL.inputSchema,
    calls,
    darwin: browserLaunchSpec('darwin'),
    linux: browserLaunchSpec('linux'),
    failure,
  }));
})().catch((error) => { process.stderr.write(error.stack); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "mcp.cjs")],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        audit = json.loads(result.stdout)
        self.assertTrue(audit["defaultValue"])
        self.assertFalse(audit["falseValue"])
        self.assertTrue(audit["trueValue"])
        self.assertEqual(audit["invalidValue"], "open_browser must be a boolean")
        self.assertEqual(
            audit["description"],
            "Open one explicit local Cut as Code project in the system default browser.",
        )
        self.assertEqual(audit["inputSchema"]["properties"]["open_browser"], {
            "type": "boolean",
            "default": True,
            "description": "Open the editor in the system default browser. Set false only for automation.",
        })
        self.assertEqual(audit["calls"], [{
            "command": "powershell.exe",
            "args": [
                "-NoProfile", "-NonInteractive", "-Command",
                "Start-Process -FilePath $args[0]",
                "http://127.0.0.1:43123/?project=project_a&launch=token-value",
            ],
            "options": {"detached": True, "stdio": "ignore", "windowsHide": True},
        }, {"event": "unref"}])
        self.assertEqual(audit["darwin"], {
            "command": "open", "args": [], "options": {"detached": True, "stdio": "ignore"},
        })
        self.assertEqual(audit["linux"], {
            "command": "xdg-open", "args": [], "options": {"detached": True, "stdio": "ignore"},
        })
        self.assertEqual(
            audit["failure"],
            "Could not open the system browser automatically. Open this URL manually: "
            "http://127.0.0.1:43123/?project=project_a&launch=token-value",
        )

    def test_windows_export_actions_wait_for_system_process_start(self) -> None:
        script = r"""
const { openExportPath } = require(process.argv[1]);
const calls = [];
const spawnProcess = (command, args, options) => {
  calls.push({ command, args, options });
  const handlers = {};
  const child = {
    once(event, handler) { handlers[event] = handler; return child; },
    unref() { calls.push({ event: 'unref' }); },
  };
  queueMicrotask(() => handlers.spawn());
  return child;
};
Promise.all([
  openExportPath('D:\\Projects\\46-sol\\final\\final-video.mp4', 'open', spawnProcess, 'win32'),
  openExportPath('D:\\Projects\\46-sol\\final\\final-video.mp4', 'reveal', spawnProcess, 'win32'),
]).then(() => process.stdout.write(JSON.stringify(calls)));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(json.loads(result.stdout), [
            {
                "command": "powershell.exe",
                "args": [
                    "-NoProfile", "-NonInteractive", "-Command",
                    "Start-Process -FilePath $args[0]",
                    r"D:\Projects\46-sol\final\final-video.mp4",
                ],
                "options": {"detached": True, "stdio": "ignore", "windowsHide": True},
            },
            {
                "command": "explorer.exe",
                "args": ["/select,", r"D:\Projects\46-sol\final\final-video.mp4"],
                "options": {"detached": True, "stdio": "ignore", "windowsHide": True},
            },
            {"event": "unref"},
            {"event": "unref"},
        ])

    def test_export_action_rejects_when_system_process_cannot_start(self) -> None:
        script = r"""
const { openExportPath } = require(process.argv[1]);
const spawnProcess = () => {
  const handlers = {};
  const child = {
    once(event, handler) { handlers[event] = handler; return child; },
    unref() {},
  };
  queueMicrotask(() => handlers.error(new Error('explorer unavailable')));
  return child;
};
openExportPath('D:\\Projects\\46-sol\\final\\final-video.mp4', 'open', spawnProcess, 'win32')
  .then(() => { process.exitCode = 1; })
  .catch((error) => process.stdout.write(error.message));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(result.stdout, "explorer unavailable")

    def test_export_failure_summary_removes_absolute_paths(self) -> None:
        script = r"""
const { summarizeExportFailure } = require(process.argv[1]);
process.stdout.write(summarizeExportFailure(
  "Traceback\nPermissionError: [WinError 5]: 'D:\\\\Projects\\\\46-sol\\\\final\\\\staging.mp4' -> 'D:\\\\Projects\\\\46-sol\\\\final\\\\final.mp4'",
  'D:\\Projects\\46-sol'
));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertIn("PermissionError: [WinError 5]", result.stdout)
        self.assertNotIn("Projects", result.stdout)
        self.assertNotIn("46-sol", result.stdout)

    def test_import_writes_unique_files_inside_the_project_input_directory(self) -> None:
        script = r"""
const { Readable } = require('node:stream');
const { writeImportedFile } = require(process.argv[1]);
const root = process.argv[2];
(async () => {
  const first = await writeImportedFile(root, 'clip.mp4', Readable.from(Buffer.from('first')));
  const second = await writeImportedFile(root, 'clip.mp4', Readable.from(Buffer.from('second')));
  process.stdout.write(JSON.stringify({ first, second }));
})().catch((error) => { process.stderr.write(error.stack); process.exitCode = 1; });
"""
        with tempfile.TemporaryDirectory(prefix="cut editor import ") as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            result = subprocess.run(
                ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs"), str(root)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            imported = json.loads(result.stdout)
            self.assertEqual("clip.mp4", imported["first"]["name"])
            self.assertEqual("clip-2.mp4", imported["second"]["name"])
            self.assertEqual(b"first", (root / "input" / "clip.mp4").read_bytes())
            self.assertEqual(b"second", (root / "input" / "clip-2.mp4").read_bytes())

    def test_delete_imported_asset_removes_only_an_unreferenced_input_file(self) -> None:
        script = r"""
const fs = require('node:fs/promises');
const path = require('node:path');
const { deleteImportedAsset } = require(process.argv[1]);
const root = process.argv[2];
(async () => {
  const input = path.join(root, 'input');
  await fs.mkdir(input, { recursive: true });
  const file = path.join(input, 'clip.mp4');
  await fs.writeFile(file, 'clip');
  const assets = new Map([['asset_clip', { path: file }]]);
  let timelineError = '';
  try { await deleteImportedAsset(root, assets, 'asset_clip', { view: { timeline: { clips: [{ source_asset_id: 'asset_clip' }], audio_clips: [] } } }); } catch (error) { timelineError = error.message; }
  let sourceError = '';
  try { await deleteImportedAsset(root, assets, 'asset_clip', { view: { source_media_id: 'asset_clip' } }); } catch (error) { sourceError = error.message; }
  await deleteImportedAsset(root, assets, 'asset_clip', { view: { timeline: { clips: [], audio_clips: [] } } });
  process.stdout.write(JSON.stringify({ exists: await fs.stat(file).then(() => true, () => false), sourceError, timelineError }));
})().catch((error) => { process.stderr.write(error.stack); process.exitCode = 1; });
"""
        with tempfile.TemporaryDirectory(prefix="cut editor delete ") as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            result = subprocess.run(
                ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs"), str(root)],
                check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
            )
        deleted = json.loads(result.stdout)
        self.assertFalse(deleted["exists"])
        self.assertEqual("The project source asset cannot be deleted", deleted["sourceError"])
        self.assertEqual("Remove this asset from the timeline before deleting it", deleted["timelineError"])

    def test_invalid_open_browser_is_a_correlated_invalid_params_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut invalid browser flag ") as temporary:
            project_root = Path(temporary) / "project"
            self._create_project(project_root)
            process = self._start_mcp(REPOSITORY_ROOT, {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON)})
            try:
                response = self._rpc(process, {
                    "jsonrpc": "2.0", "id": 71, "method": "tools/call",
                    "params": {"name": "open_editor", "arguments": {
                        "project_root": str(project_root), "open_browser": "false",
                    }},
                })
                self.assertEqual(response["id"], 71)
                self.assertEqual(response["error"], {
                    "code": -32602, "message": "open_browser must be a boolean",
                })
            finally:
                self._stop_mcp(process)

    def test_editor_drafts_survive_runtime_restart_without_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut editor drafts ") as temporary:
            temporary_root = Path(temporary)
            project_root = temporary_root / "video project"
            plugin_data = temporary_root / "plugin data"
            self._create_project(project_root)
            environment = {
                **os.environ,
                "CAC_PYTHON": str(BUNDLED_PYTHON),
                "PLUGIN_DATA": str(plugin_data),
            }
            process = self._start_mcp(REPOSITORY_ROOT, environment)
            try:
                opened = self._open_editor(process, 1, project_root)
                self._assert_real_browser_ready(opened["url"], opened["projectId"], project_root.name)
                session = self._session_values[-1]
                snapshot = self._draft_request(opened["url"], opened["projectId"], session, "GET", "snapshot")[2]["snapshot"]
                revision = next(item["revision"] for item in snapshot["view"]["operations"] if item["id"] == "captions")
                authority_before = (project_root / "work" / "project.json").read_bytes()
                saved = self._draft_request(opened["url"], opened["projectId"], session, "PUT", "drafts/captions", {
                    "baseRevision": revision,
                    "changes": [{"cueId": "cue-001", "text": "Recovered copy"}],
                })
                self.assertEqual(saved[0], 200)
                self.assertEqual((project_root / "work" / "project.json").read_bytes(), authority_before)
                update_script = r"""
const { ensureHub } = require(process.argv[1]);
(async () => {
  const before = await ensureHub({ pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA });
  const pending = await ensureHub({ pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA, protocolVersion: 2, runtimeVersion: 'next-incompatible' });
  process.stdout.write(JSON.stringify({ beforePid: before.pid, pendingPid: pending.pid, updatePending: pending.updatePending }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
                update_result = subprocess.run(
                    ["node", "-e", update_script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), str(REPOSITORY_ROOT)],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
                )
                update_evidence = json.loads(update_result.stdout)
                self.assertEqual(update_evidence["beforePid"], update_evidence["pendingPid"])
                self.assertTrue(update_evidence["updatePending"])
            finally:
                self._stop_mcp(process)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, timeout=20,
                )

            restarted = self._start_mcp(REPOSITORY_ROOT, environment)
            try:
                reopened = self._open_editor(restarted, 2, project_root)
                self._assert_real_browser_ready(reopened["url"], reopened["projectId"], project_root.name)
                session = self._session_values[-1]
                recovered = self._draft_request(reopened["url"], reopened["projectId"], session, "GET", "drafts/captions")
                self.assertEqual(recovered[0], 200)
                self.assertEqual(recovered[2]["draft"]["changes"][0]["text"], "Recovered copy")
                self.assertFalse(recovered[2]["draft"]["conflict"])
                stale = self._draft_request(reopened["url"], reopened["projectId"], session, "PUT", "drafts/captions", {
                    "baseRevision": revision - 1,
                    "changes": [{"cueId": "cue-001", "text": "Stale copy"}],
                })
                self.assertTrue(stale[2]["draft"]["conflict"])
                removed = self._draft_request(reopened["url"], reopened["projectId"], session, "DELETE", "drafts/captions")
                self.assertEqual(removed[0], 200)
                self.assertEqual(self._draft_request(reopened["url"], reopened["projectId"], session, "GET", "drafts/captions")[0], 404)
            finally:
                self._stop_mcp(restarted)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_editor_hub_hands_off_compatible_and_incompatible_versions_when_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut editor update ") as temporary:
            environment = {**os.environ, "PLUGIN_DATA": str(Path(temporary) / "plugin data")}
            script = r"""
const { HUB_CAPABILITIES, ensureHub, hubRequest } = require(process.argv[1]);
(async () => {
  const options = { pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA };
  const first = await ensureHub({ ...options, protocolVersion: 1, runtimeVersion: '1.0.0' });
  const compatible = await ensureHub({ ...options, protocolVersion: 1, runtimeVersion: '1.1.0' });
  const capabilityHandoff = await ensureHub({
    ...options, protocolVersion: 1, runtimeVersion: '1.2.0',
    capabilities: [...HUB_CAPABILITIES, 'future-capability'],
  });
  const handedOff = await ensureHub({ ...options, protocolVersion: 2, runtimeVersion: '2.0.0' });
  const meta = await hubRequest(handedOff, 'GET', '/v1/health');
  process.stdout.write(JSON.stringify({
    firstPid: first.pid,
    compatiblePid: compatible.pid,
    compatibleUpdateAvailable: compatible.updateAvailable,
    capabilityHandoffPid: capabilityHandoff.pid,
    capabilityHandoffCapabilities: capabilityHandoff.capabilities,
    handedOffPid: handedOff.pid,
    meta,
  }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
            try:
                result = subprocess.run(
                    ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), str(REPOSITORY_ROOT)],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=30,
                )
                evidence = json.loads(result.stdout)
                self.assertNotEqual(evidence["firstPid"], evidence["compatiblePid"])
                self.assertIsNone(evidence.get("compatibleUpdateAvailable"))
                self.assertNotEqual(evidence["compatiblePid"], evidence["capabilityHandoffPid"])
                self.assertIn("future-capability", evidence["capabilityHandoffCapabilities"])
                self.assertNotEqual(evidence["capabilityHandoffPid"], evidence["handedOffPid"])
                self.assertEqual(evidence["meta"]["protocolVersion"], 2)
                self.assertEqual(evidence["meta"]["runtimeVersion"], "2.0.0")
                self.assertIn("recoverable-drafts", evidence["meta"]["capabilities"])
            finally:
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_active_editor_drains_before_compatible_update_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut draining update ") as temporary:
            root = Path(temporary)
            project_root = root / "video project"
            plugin_data = root / "plugin data"
            self._create_project(project_root)
            environment = {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON), "PLUGIN_DATA": str(plugin_data)}
            process = self._start_mcp(REPOSITORY_ROOT, environment)
            events = None
            connection = None
            try:
                opened = self._open_editor(process, 1, project_root)
                self._assert_real_browser_ready(opened["url"], opened["projectId"], project_root.name)
                session = self._session_values[-1]
                parsed = urllib.parse.urlsplit(opened["url"])
                connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
                connection.request(
                    "GET",
                    f"/v1/projects/{urllib.parse.quote(opened['projectId'], safe='')}/events",
                    headers={"Cookie": f"cut_session={session}"},
                )
                events = connection.getresponse()
                self.assertEqual(events.status, 200)
                self.assertEqual(events.readline(), b"event: ready\n")

                script = r"""
const { ensureHub } = require(process.argv[1]);
(async () => {
  const current = await ensureHub({ pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA });
  const pending = await ensureHub({
    pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA,
    protocolVersion: current.protocolVersion, runtimeVersion: '9.0.0',
  });
  process.stdout.write(JSON.stringify({ oldPid: current.pid, pendingPid: pending.pid, updateAvailable: pending.updateAvailable }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
                requested = subprocess.run(
                    ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), str(REPOSITORY_ROOT)],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
                )
                evidence = json.loads(requested.stdout)
                self.assertEqual(evidence["oldPid"], evidence["pendingPid"])
                self.assertTrue(evidence["updateAvailable"])
                time.sleep(1.5)
                while True:
                    locator = json.loads((plugin_data / "hub.json").read_text(encoding="utf-8"))
                    if locator["pid"] == evidence["oldPid"]:
                        break
                    self.fail("compatible update interrupted an active editor")

                events.close()
                connection.close()
                events = None
                connection = None
                deadline = time.monotonic() + 15
                promoted = None
                while time.monotonic() < deadline:
                    try:
                        candidate = json.loads((plugin_data / "hub.json").read_text(encoding="utf-8"))
                    except (FileNotFoundError, json.JSONDecodeError):
                        candidate = None
                    if candidate and candidate.get("runtimeVersion") == "9.0.0" and candidate.get("pid") != evidence["oldPid"]:
                        promoted = candidate
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(promoted)
            finally:
                if events:
                    events.close()
                if connection:
                    connection.close()
                self._stop_mcp(process)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_close_project_protects_a_mutation_waiting_for_its_request_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut close barrier ") as temporary:
            root = Path(temporary)
            project_root = root / "video project"
            plugin_data = root / "plugin data"
            self._create_project(project_root)
            environment = {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON), "PLUGIN_DATA": str(plugin_data)}
            process = self._start_mcp(REPOSITORY_ROOT, environment)
            stalled = None
            try:
                opened = self._open_editor(process, 1, project_root)
                self._assert_real_browser_ready(opened["url"], opened["projectId"], project_root.name)
                project_session = self._session_values[-1]
                editor = urllib.parse.urlsplit(opened["url"])

                locator = json.loads((plugin_data / "hub.json").read_text(encoding="utf-8"))
                control = http.client.HTTPConnection(locator["host"], locator["port"], timeout=5)
                try:
                    control.request(
                        "POST", "/v1/hub/launch", body=b"{}",
                        headers={"Authorization": f"Bearer {locator['controlToken']}", "Content-Type": "application/json"},
                    )
                    launch_response = control.getresponse()
                    launch = json.loads(launch_response.read())
                    self.assertEqual(launch_response.status, 200)
                finally:
                    control.close()
                status, headers, _ = self._request(launch["url"])
                self.assertEqual(status, 303)
                hub_cookie = headers["set-cookie"].split(";", 1)[0]

                stalled = socket.create_connection((editor.hostname, editor.port), timeout=5)
                request_head = (
                    f"POST /v1/projects/{urllib.parse.quote(opened['projectId'], safe='')}/transactions HTTP/1.1\r\n"
                    f"Host: {editor.netloc}\r\n"
                    f"Cookie: cut_session={project_session}\r\n"
                    f"Origin: {editor.scheme}://{editor.netloc}\r\n"
                    "Content-Type: application/json\r\n"
                    "Content-Length: 1024\r\n"
                    "Connection: keep-alive\r\n\r\n"
                    "{"
                )
                stalled.sendall(request_head.encode("utf-8"))
                time.sleep(0.2)

                hub = http.client.HTTPConnection(locator["host"], locator["port"], timeout=5)
                try:
                    payload = json.dumps({"force": False}).encode("utf-8")
                    hub.request(
                        "POST", f"/v1/hub/projects/{urllib.parse.quote(opened['projectId'], safe='')}/close",
                        body=payload,
                        headers={
                            "Cookie": hub_cookie,
                            "Origin": f"http://{locator['host']}:{locator['port']}",
                            "Content-Type": "application/json",
                        },
                    )
                    close_response = hub.getresponse()
                    close_result = json.loads(close_response.read())
                    self.assertEqual(close_response.status, 409)
                    self.assertTrue(close_result["requiresConfirmation"])
                    self.assertIn("active operation", close_result["reasons"])
                finally:
                    hub.close()
            finally:
                if stalled:
                    stalled.close()
                self._stop_mcp(process)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_pending_editor_update_advances_automatically_after_draft_is_cleared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut pending update ") as temporary:
            root = Path(temporary)
            project_root = root / "video project"
            plugin_data = root / "plugin data"
            self._create_project(project_root)
            environment = {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON), "PLUGIN_DATA": str(plugin_data)}
            process = self._start_mcp(REPOSITORY_ROOT, environment)
            try:
                opened = self._open_editor(process, 1, project_root)
                self._assert_real_browser_ready(opened["url"], opened["projectId"], project_root.name)
                session = self._session_values[-1]
                saved = self._draft_request(opened["url"], opened["projectId"], session, "PUT", "drafts/captions", {
                    "baseRevision": 1,
                    "changes": [{"cueId": "cue-001", "text": "Blocks update"}],
                })
                self.assertEqual(saved[0], 200)
                script = r"""
const { ensureHub } = require(process.argv[1]);
(async () => {
  const current = await ensureHub({ pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA });
  const pending = await ensureHub({
    pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA,
    protocolVersion: 2, runtimeVersion: '2.0.0',
  });
  process.stdout.write(JSON.stringify({ oldPid: current.pid, pending: pending.updatePending }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
                requested = subprocess.run(
                    ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), str(REPOSITORY_ROOT)],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
                )
                evidence = json.loads(requested.stdout)
                self.assertTrue(evidence["pending"])
                removed = self._draft_request(opened["url"], opened["projectId"], session, "DELETE", "drafts/captions")
                self.assertEqual(removed[0], 200)
                locator_path = plugin_data / "hub.json"
                deadline = time.monotonic() + 15
                promoted = None
                while time.monotonic() < deadline:
                    try:
                        candidate = json.loads(locator_path.read_text(encoding="utf-8"))
                    except (FileNotFoundError, json.JSONDecodeError):
                        candidate = None
                    if candidate and candidate.get("protocolVersion") == 2 and candidate.get("pid") != evidence["oldPid"]:
                        promoted = candidate
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(promoted)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and self._pid_is_live(opened["pid"]):
                    time.sleep(0.1)
                self.assertFalse(self._pid_is_live(opened["pid"]))
                reopened = self._open_editor(process, 2, project_root)
                self.assertNotEqual(reopened["pid"], opened["pid"])
                self._assert_real_browser_ready(reopened["url"], reopened["projectId"], project_root.name)
            finally:
                self._stop_mcp(process)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_handoff_prepare_rechecks_a_real_mutation_lease(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut handoff lease ") as temporary:
            root = Path(temporary)
            project_root = root / "video project"
            plugin_data = root / "plugin data"
            self._create_project(project_root)
            environment = {**os.environ, "CAC_PYTHON": str(BUNDLED_PYTHON), "PLUGIN_DATA": str(plugin_data)}
            process = self._start_mcp(REPOSITORY_ROOT, environment)
            lease_process = None
            try:
                self._open_editor(process, 1, project_root)
                lease_script = (
                    "import sys; sys.path.insert(0, sys.argv[2]); import projectlib; "
                    "lease=projectlib.acquire_project_lease(sys.argv[1], blocking=True); "
                    "print('ready', flush=True); input(); projectlib.release_project_lease(lease)"
                )
                lease_process = subprocess.Popen(
                    [str(BUNDLED_PYTHON), "-c", lease_script, str(project_root),
                     str(REPOSITORY_ROOT / "skills" / "video-understand" / "scripts")],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                self.assertEqual(lease_process.stdout.readline().strip(), "ready")
                script = r"""
const { hubPaths, hubRequest, readTrustedLocator } = require(process.argv[1]);
(async () => {
  const locator = await readTrustedLocator(hubPaths(process.env.PLUGIN_DATA).locator);
  let failure;
  try { await hubRequest(locator, 'POST', '/v1/hub/handoff/prepare', {}); }
  catch (error) { failure = error.message; }
  const resumed = await hubRequest(locator, 'POST', '/v1/hub/handoff/resume', {});
  process.stdout.write(JSON.stringify({ failure, resumed }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
                result = subprocess.run(
                    ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs")],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
                )
                evidence = json.loads(result.stdout)
                self.assertEqual(evidence["failure"], "Projects have protected work")
                self.assertEqual(evidence["resumed"]["status"], "resumed")
            finally:
                if lease_process:
                    if lease_process.stdin and not lease_process.stdin.closed:
                        lease_process.stdin.write("release\n")
                        lease_process.stdin.flush()
                    lease_process.wait(timeout=10)
                    for stream in (lease_process.stdin, lease_process.stdout, lease_process.stderr):
                        if stream and not stream.closed:
                            stream.close()
                self._stop_mcp(process)
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
                )

    def test_editor_hub_rejects_a_locator_with_a_forged_challenge_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut forged hub ") as temporary:
            script = r"""
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { readTrustedLocator } = require(process.argv[1]);
const { locatorProof } = require(process.argv[2]);
const root = process.argv[3];
const lockToken = crypto.randomBytes(32).toString('base64url');
const controlToken = crypto.randomBytes(32).toString('base64url');
const server = http.createServer((request, response) => {
  response.writeHead(200, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify({ ok: true, instanceId: 'forged', pid: process.pid, proof: 'forged' }));
});
server.listen(0, '127.0.0.1', async () => {
  const locator = {
    schemaVersion: 2, host: '127.0.0.1', port: server.address().port, pid: process.pid,
    instanceId: 'forged', protocolVersion: 1, runtimeVersion: '1.0.0', capabilities: [], controlToken,
  };
  locator.startupProof = locatorProof(lockToken, locator);
  fs.writeFileSync(path.join(root, 'hub.lock'), JSON.stringify({ token: lockToken }));
  fs.writeFileSync(path.join(root, 'hub.json'), JSON.stringify(locator));
  const trusted = await readTrustedLocator(path.join(root, 'hub.json'));
  process.stdout.write(JSON.stringify({ trusted }));
  server.close();
});
"""
            result = subprocess.run(
                [
                    "node", "-e", script,
                    str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"),
                    str(REPOSITORY_ROOT / "runtime" / "hub-trust.cjs"),
                    temporary,
                ],
                cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
            )
            self.assertIsNone(json.loads(result.stdout)["trusted"])

    def test_failed_editor_hub_handoff_preserves_the_trusted_old_hub(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut failed hub handoff ") as temporary:
            environment = {**os.environ, "PLUGIN_DATA": str(Path(temporary) / "plugin data")}
            script = r"""
const fs = require('node:fs');
const path = require('node:path');
const { ensureHub, hubPaths, readTrustedLocator } = require(process.argv[1]);
(async () => {
  const options = { pluginRoot: process.argv[2], dataRoot: process.env.PLUGIN_DATA };
  const old = await ensureHub({ ...options, protocolVersion: 1, runtimeVersion: '1.0.0' });
  const paths = hubPaths(options.dataRoot);
  const beforeLocator = fs.readFileSync(paths.locator, 'utf8');
  const beforeLock = fs.readFileSync(paths.lock, 'utf8');
  let failure;
  try {
    await ensureHub({
      ...options, protocolVersion: 2, runtimeVersion: '2.0.0', startupTimeoutMs: 100,
      spawnProcess: () => ({ unref() {} }),
    });
  } catch (error) { failure = error.message; }
  const trusted = await readTrustedLocator(paths.locator);
  process.stdout.write(JSON.stringify({
    failure, oldPid: old.pid, trustedPid: trusted?.pid,
    locatorUnchanged: beforeLocator === fs.readFileSync(paths.locator, 'utf8'),
    lockUnchanged: beforeLock === fs.readFileSync(paths.lock, 'utf8'),
    candidates: fs.readdirSync(options.dataRoot).filter((name) => name.startsWith('hub.next.')),
  }));
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
            try:
                result = subprocess.run(
                    ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), str(REPOSITORY_ROOT)],
                    cwd=REPOSITORY_ROOT, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
                )
                evidence = json.loads(result.stdout)
                self.assertEqual(evidence["failure"], "replacement editor Hub startup timed out")
                self.assertEqual(evidence["oldPid"], evidence["trustedPid"])
                self.assertTrue(evidence["locatorUnchanged"])
                self.assertTrue(evidence["lockUnchanged"])
                self.assertEqual(evidence["candidates"], [])
            finally:
                subprocess.run(
                    ["node", str(REPOSITORY_ROOT / "runtime" / "hub-client.cjs"), "shutdown"],
                    cwd=REPOSITORY_ROOT, env=environment, check=False, capture_output=True, text=True, timeout=20,
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
            self._assert_unknown_third_party_asset_is_rejected(extracted)
            self._audit_route_allowlist(extracted)
            self._audit_motion_graphics_core(extracted, root / "motion graphics core project")
            self._smoke_open_editor(extracted, root / "video project with spaces", root)

    def test_compliance_inventory_covers_packaged_third_party_assets_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut compliance package ") as temporary:
            package_root = Path(temporary) / "package with spaces"
            shutil.copytree(
                REPOSITORY_ROOT / "skills" / "video-add-motion-graphics" / "recipes" / "animxyz",
                package_root / "skills" / "video-add-motion-graphics" / "recipes" / "animxyz",
            )
            shutil.copytree(REPOSITORY_ROOT / "ui" / "dist", package_root / "ui" / "dist")
            (package_root / "runtime").mkdir(parents=True)
            for runtime_file in ("mcp.cjs", "sidecar.cjs"):
                shutil.copy2(
                    REPOSITORY_ROOT / "runtime" / runtime_file,
                    package_root / "runtime" / runtime_file,
                )
            for asset_path in THIRD_PARTY_ASSETS:
                destination = package_root / asset_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPOSITORY_ROOT / asset_path, destination)

            subprocess.run(
                ["node", str(COMPLIANCE_SCRIPT), str(REPOSITORY_ROOT), str(package_root)],
                cwd=REPOSITORY_ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            notices = (package_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
            audit = json.loads((package_root / "PACKAGE_AUDIT.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {
                    (item["name"], item["version"], item["license"])
                    for item in audit["license_audit"]["components"]
                },
                THIRD_PARTY_COMPONENTS,
            )
            inter_assets = [
                item
                for item in audit["third_party_asset_audit"]["third_party"]
                if item["component"] == "@fontsource/inter"
            ]
            self.assertEqual(len(inter_assets), 6)
            self.assertTrue(all(item["path"].startswith("ui/dist/assets/inter-") for item in inter_assets))
            generated_bundles = audit["third_party_asset_audit"]["generated_bundles"]
            self.assertEqual(len(generated_bundles), 1)
            self.assertRegex(generated_bundles[0]["path"], r"^ui/dist/assets/index-.+\.js$")
            self.assertEqual(
                set(generated_bundles[0]["components"]),
                {name for name, _, _ in THIRD_PARTY_COMPONENTS if name not in {"@animxyz/core", "Cal Sans", "GSAP", "Lexend"}},
            )
            animxyz_styles = [
                item for item in audit["third_party_asset_audit"]["third_party"]
                if item["component"] == "@animxyz/core" and item["path"].endswith("animxyz.css")
            ]
            self.assertEqual(len(animxyz_styles), 11)
            self.assertEqual(
                {item["sha256"] for item in animxyz_styles},
                {"4a133a5e4bf9ff2b3c87d7ef3a20064ccaab3c8838cafbf540c75d658f7c451d"},
            )
            generated_stylesheets = audit["third_party_asset_audit"]["generated_stylesheets"]
            self.assertEqual(len(generated_stylesheets), 1)
            self.assertRegex(generated_stylesheets[0]["path"], r"^ui/dist/assets/index-.+\.css$")
            self._assert_asset_component_evidence(notices, audit)
            self._assert_sbom_asset_evidence(
                json.loads((package_root / "SBOM.spdx.json").read_text(encoding="utf-8"))
            )
            self._assert_unknown_third_party_asset_is_rejected(package_root, "unknown-vendor.js")
            self._assert_unknown_third_party_asset_is_rejected(package_root, "unknown-font.ttf")
            self._assert_unknown_third_party_asset_is_rejected(
                package_root, "ui/dist/assets/inter-evil.woff2"
            )
            self._assert_unknown_third_party_asset_is_rejected(
                package_root, "ui/dist/assets/index-evil.js"
            )
            self._assert_unknown_third_party_asset_is_rejected(package_root, "unknown-style.css")
            self._assert_unknown_third_party_asset_is_rejected(package_root, "unknown-runtime.wasm")
            self._assert_unknown_third_party_asset_is_rejected(package_root, "unknown-addon.node")
            self.assertEqual(
                audit["scope"],
                "all packaged files for secrets; executable, stylesheet, font, and runtime binary assets for third-party licensing",
            )
            self.assertEqual(audit["third_party_asset_audit"]["scope"], "executable, stylesheet, font, and runtime binary assets")

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
            for asset_path, expected in THIRD_PARTY_ASSETS.items():
                self.assertIn(asset_path, relative_names)
                self.assertEqual(
                    hashlib.sha256(archive.read(f"cut-as-code-editor/{asset_path}")).hexdigest(),
                    expected["sha256"],
                )

            required = {
                ".codex-plugin/plugin.json",
                ".mcp.json",
                "LICENSE",
                "PACKAGE_AUDIT.json",
                "README.md",
                "SBOM.spdx.json",
                "THIRD_PARTY_NOTICES.md",
                "runtime/mcp.cjs",
                "runtime/hub-client.cjs",
                "runtime/hub-trust.cjs",
                "runtime/hub.cjs",
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
                "runtime/reconcile_manual_timeline.py",
                "runtime/sequence_bounds.py",
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
            self._assert_sbom_asset_evidence(sbom)

            audit = json.loads(archive.read("cut-as-code-editor/PACKAGE_AUDIT.json"))
            self.assertEqual(audit["schema_version"], 1)
            self.assertEqual(
                audit["scope"],
                "all packaged files for secrets; executable, stylesheet, font, and runtime binary assets for third-party licensing",
            )
            self.assertEqual(audit["license_audit"]["status"], "pass")
            self.assertEqual(audit["license_audit"]["component_count"], len(THIRD_PARTY_COMPONENTS))
            self.assertEqual(audit["license_audit"]["unresolved"], [])
            asset_audit = audit["third_party_asset_audit"]
            self.assertEqual(asset_audit["status"], "pass")
            self.assertEqual(asset_audit["unknown"], [])
            self._assert_asset_component_evidence(notices, audit)
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
            self.assertIn("skills/video-add-motion-graphics/SKILL.md", relative_names)
            self.assertNotIn("skills/video-add-motion-graphics/recipes/imported/SKILL.md", relative_names)
            animxyz_manifests = [
                name for name in relative_names
                if name.startswith("skills/video-add-motion-graphics/recipes/animxyz/")
                and name.endswith("/recipe.motion.yaml")
            ]
            self.assertEqual(len(animxyz_manifests), 20)
            motion_graphics_skill = archive.read(
                "cut-as-code-editor/skills/video-add-motion-graphics/SKILL.md"
            ).decode("utf-8")
            self.assertIn("exactly 10 selectable AnimXYZ core recipes", motion_graphics_skill)
            self.assertIn("exactly 20 AnimXYZ recipe manifests", motion_graphics_skill)
            self.assertIn("missing_content_pack", motion_graphics_skill)
            self.assertNotIn("1,477 recipes", motion_graphics_skill)
            self.assertNotIn("REQUIRED SUB-SKILLS", motion_graphics_skill)
            self.assertNotIn("reference/recipe-selection.md", motion_graphics_skill)
            normalized_motion_graphics_skill = " ".join(motion_graphics_skill.split())
            self.assertIn("Non-skipped validate/register/render is unavailable", normalized_motion_graphics_skill)
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
                "runtime/export_project.py",
                "runtime/hub-client.cjs",
                "runtime/hub-trust.cjs",
                "runtime/hub.cjs",
                "runtime/mcp.cjs",
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
                "runtime/reconcile_manual_timeline.py",
                "runtime/sequence_bounds.py",
                "runtime/sidecar.cjs",
            })
            sidecar = executable_sources["runtime/sidecar.cjs"]
            hub = executable_sources["runtime/hub.cjs"]
            hub_client = executable_sources["runtime/hub-client.cjs"]
            mcp = executable_sources["runtime/mcp.cjs"]
            self.assertIn("const HTTP_ROUTE_ALLOWLIST", sidecar)
            self.assertIn("routeForRequest", sidecar)
            self.assertIn("const PROTOCOL_VERB_ALLOWLIST", sidecar)
            self.assertIn("const MCP_TOOL_ALLOWLIST", mcp)
            for source in executable_sources.values():
                for forbidden in ("execFile", "spawnSync", "shell: true", "codex exec", "/v1/render", "/v1/preview", "/v1/jobs", "/v1/shell", "/v1/exec", "/v1/files"):
                    self.assertNotIn(forbidden, source)
            self.assertEqual(sidecar.count("spawn("), 3)
            self.assertIn("runProcess('ffmpeg',", sidecar)
            self.assertIn("path.join(__dirname, 'sequence_bounds.py')", sidecar)
            self.assertEqual(mcp.count("spawn("), 0)
            self.assertEqual(hub.count("spawn("), 2)
            self.assertEqual(hub_client.count("spawnProcess(process.execPath,"), 1)
            self.assertIn("startProtocolService", sidecar)
            self.assertIn("sidecar.cjs", hub)
            self.assertIn("ensureHub", mcp)
            self.assertIn("PLUGIN_DATA", hub_client)
            self.assertIn("function browserLaunchSpec", mcp)
            self.assertIn("function openBrowser", mcp)
            self.assertIn("spawnProcess(command, [...args, url], options)", mcp)
            self.assertIn("child.once('spawn', resolve)", mcp)
            self.assertIn("Could not open the system browser automatically. Open this URL manually:", mcp)
            self.assertNotIn("ready-file", sidecar)
            self.assertNotIn("readyFile", hub_client)
            self.assertNotIn("bootstrapToken", sidecar)
            self.assertNotIn("bootstrapToken", hub_client)
            self.assertNotIn("cut-as-code-editor-sidecars", hub_client)
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
            ["POST", "/v1/projects/project_a/timeline/edits"],
            ["POST", "/v1/projects/project_a/reviews/decision"],
            ["POST", "/v1/projects/project_a/exports"],
            ["GET", "/v1/projects/project_a/exports/status"],
            ["POST", "/v1/projects/project_a/exports/open"],
            ["GET", "/v1/projects/project_a/resources/res_a1"],
            ["POST", "/v1/projects/project_a/imports"],
            ["DELETE", "/v1/projects/project_a/assets/asset_a1"],
            ["GET", "/v1/projects/project_a/media/asset_a1"],
            ["GET", "/v1/projects/project_a/artifacts/artifact_a1"],
            ["GET", "/v1/projects/project_a/layers/layer_a1/frames/1"],
            ["GET", "/v1/projects/project_a/events"],
            ["GET", "/v1/projects/project_a/drafts/captions"],
            ["PUT", "/v1/projects/project_a/drafts/content-cards"],
            ["DELETE", "/v1/projects/project_a/drafts/motion-graphics"],
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
            ["launch", "meta", "snapshot", "transaction", "timeline-edit", "review", "export-start", "export-status", "export-action", "resource", "import", "asset-delete", "file", "layer-frame", "events", "draft", "static"],
        )
        self.assertEqual(
            audit["actual"],
            ["launch", "meta", "snapshot", "transaction", "timeline-edit", "review", "export-start", "export-status", "export-action", "resource", "import", "asset-delete", "file", "file", "layer-frame", "events", "draft", "draft", "draft", "static", "static", None, None, None, None],
        )

    def _assert_unknown_third_party_asset_is_rejected(
        self, plugin_root: Path, filename: str = "unknown-vendor.js"
    ) -> None:
        relative_path = (
            filename
            if "/" in filename
            else f"skills/video-add-captions/public/{filename}"
        )
        unknown = plugin_root / relative_path
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_text("/* unclassified third-party fixture */\n", encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "node",
                    str(COMPLIANCE_SCRIPT),
                    str(REPOSITORY_ROOT),
                    str(plugin_root),
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown third-party runtime assets:", result.stderr)
            self.assertIn(relative_path, result.stderr)
        finally:
            unknown.unlink(missing_ok=True)

    def _assert_sbom_asset_evidence(self, sbom: dict) -> None:
        sbom_components = {item["name"]: item for item in sbom["packages"]}
        for asset_path, expected in THIRD_PARTY_ASSETS.items():
            component = sbom_components[expected["component"]]
            self.assertIn(asset_path, component["packageFileName"])
            self.assertIn(expected["license_url"], component["sourceInfo"])
            self.assertIn(expected["source_revision"], component["sourceInfo"])
        self.assertEqual(
            sbom["hasExtractedLicensingInfos"][0]["licenseId"],
            "LicenseRef-GSAP-Standard",
        )
        self.assertIn(
            "https://gsap.com/standard-license",
            sbom["hasExtractedLicensingInfos"][0]["extractedText"],
        )

    def _assert_asset_component_evidence(self, notices: str, audit: dict) -> None:
        audited_components = {
            item["name"]: item for item in audit["license_audit"]["components"]
        }
        audited_assets = {
            item["path"]: item
            for item in audit["third_party_asset_audit"]["third_party"]
        }
        for asset_path, expected in THIRD_PARTY_ASSETS.items():
            self.assertIn(asset_path, notices)
            self.assertIn(expected["sha256"], notices)
            self.assertIn(expected["license_url"], notices)
            self.assertIn(expected["source_revision"], notices)
            component = audited_components[expected["component"]]
            self.assertIn(asset_path, component["packaged_paths"])
            self.assertEqual(component["checksum"]["value"], expected["sha256"])
            self.assertEqual(component["evidence"]["license_url"], expected["license_url"])
            self.assertEqual(component["evidence"]["source_revision"], expected["source_revision"])
            self.assertEqual(audited_assets[asset_path]["component"], expected["component"])
            self.assertEqual(audited_assets[asset_path]["sha256"], expected["sha256"])

    def _audit_motion_graphics_core(self, plugin_root: Path, project_root: Path) -> None:
        library = plugin_root / "skills" / "video-add-motion-graphics" / "scripts" / "recipe_library.mjs"
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
        plugin_data = temporary_root / "plugin data"
        environment = {
            **os.environ,
            "CAC_PYTHON": str(BUNDLED_PYTHON),
            "PLUGIN_DATA": str(plugin_data),
        }
        process = self._start_mcp(plugin_root, environment)
        first_pid = None
        first_session = None
        second_pid = None
        try:
            tools = self._rpc(process, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual([item["name"] for item in tools["result"]["tools"]], ["open_editor"])
            opened = self._rpc(process, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root), "open_browser": False}},
            })
            details = json.loads(opened["result"]["content"][0]["text"])
            self.assertTrue(details["url"].startswith("http://127.0.0.1:"))
            self.assertIn("launch=", details["url"])
            self.assertEqual(set(details), {"pid", "projectRoot", "url", "projectId"})
            first_pid = details["pid"]
            self._assert_real_browser_ready(details["url"], details["projectId"], project_root.name)
            first_session = self._session_values[-1]
            self._assert_launch_error(details["url"])

            second_root = temporary_root / "second video project"
            self._create_project(second_root)
            second = self._open_editor(process, 20, second_root)
            second_pid = second["pid"]
            self.assertNotEqual(second["projectId"], details["projectId"])
            self.assertNotEqual(second_pid, first_pid)
            same_first = self._open_editor(process, 21, project_root)
            self.assertEqual(same_first["pid"], first_pid)
            self.assertEqual(same_first["projectId"], details["projectId"])
            lease_script = (
                "import sys; sys.path.insert(0, sys.argv[2]); import projectlib; "
                "lease = projectlib.acquire_project_lease(sys.argv[1], blocking=True); "
                "print('ready', flush=True); input(); projectlib.release_project_lease(lease)"
            )
            lease_process = subprocess.Popen(
                [str(BUNDLED_PYTHON), "-c", lease_script, str(second_root),
                 str(plugin_root / "skills" / "video-understand" / "scripts")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            old_hub_pid = json.loads((plugin_data / "hub.json").read_text(encoding="utf-8"))["pid"]
            try:
                self.assertEqual(lease_process.stdout.readline().strip(), "ready")
                self._assert_hub_picker(plugin_root, environment, [project_root.name, second_root.name])
            finally:
                if lease_process.stdin:
                    lease_process.stdin.write("release\n")
                    lease_process.stdin.flush()
                lease_process.wait(timeout=10)
                for stream in (lease_process.stdin, lease_process.stdout, lease_process.stderr):
                    if stream and not stream.closed:
                        stream.close()

            deadline = time.monotonic() + 15
            promoted = None
            while time.monotonic() < deadline:
                try:
                    candidate = json.loads((plugin_data / "hub.json").read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError):
                    candidate = None
                if candidate and candidate.get("runtimeVersion") == "99.0.0" and candidate.get("pid") != old_hub_pid:
                    promoted = candidate
                    break
                time.sleep(0.1)
            self.assertIsNotNone(promoted)

            reopened = self._rpc(process, {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root), "open_browser": False}},
            })
            reconnected = json.loads(reopened["result"]["content"][0]["text"])
            self.assertNotEqual(reconnected["url"], details["url"])
            self.assertNotEqual(reconnected["pid"], details["pid"])
            self._assert_adversarial_launch_rejections(reconnected["url"], reconnected["projectId"])
            self._assert_real_browser_ready(reconnected["url"], reconnected["projectId"], project_root.name)
            first_pid = reconnected["pid"]
            first_session = self._session_values[-1]
            self._assert_launch_error(reconnected["url"])

            final = self._open_editor(process, 4, project_root)
            self._assert_real_browser_ready(final["url"], final["projectId"], project_root.name)
            self._assert_no_secret_persistence(temporary_root, process)
            self._rpc(process, {"jsonrpc": "2.0", "id": 5, "method": "shutdown"})
        finally:
            self._stop_mcp(process)
        if first_pid is not None:
            self.assertTrue(self._pid_is_live(first_pid))
        if first_session is not None:
            self._assert_authenticated_snapshot(final["url"], final["projectId"], first_session)

        restarted = self._start_mcp(plugin_root, environment)
        restarted_pid = None
        try:
            details = self._open_editor(restarted, 1, project_root)
            restarted_pid = details["pid"]
            self.assertEqual(restarted_pid, first_pid)
            self._assert_real_browser_ready(details["url"], details["projectId"], project_root.name)
            self._rpc(restarted, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
        finally:
            self._stop_mcp(restarted)
        if restarted_pid is not None:
            self.assertTrue(self._pid_is_live(restarted_pid))
        subprocess.run(
            ["node", str(plugin_root / "runtime" / "hub-client.cjs"), "shutdown"],
            cwd=plugin_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        if restarted_pid is not None:
            self.assertFalse(self._pid_is_live(restarted_pid))
        if second_pid is not None:
            self.assertFalse(self._pid_is_live(second_pid))

    def _assert_hub_picker(
        self, plugin_root: Path, environment: dict[str, str], project_names: list[str]
    ) -> None:
        update = subprocess.run(
            [
                "node", "-e",
                "const {ensureHub}=require(process.argv[1]); ensureHub({pluginRoot:process.argv[2],dataRoot:process.env.PLUGIN_DATA,runtimeVersion:'99.0.0'}).catch(e=>{console.error(e);process.exit(1)})",
                str(plugin_root / "runtime" / "hub-client.cjs"), str(plugin_root),
            ],
            cwd=plugin_root, env=environment, check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(update.returncode, 0)
        launched = subprocess.run(
            ["node", str(plugin_root / "runtime" / "hub-client.cjs"), "launch"],
            cwd=plugin_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        url = json.loads(launched.stdout)["url"]
        script = r"""
const { chromium } = require(process.argv[1]);
(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(process.argv[2]);
    await page.waitForFunction(() => document.documentElement.dataset.runtimeState === 'hub-ready');
    const names = await page.locator('[data-hub-project-name]').allTextContents();
    const updateText = await page.locator('[data-update-pending]').textContent();
    await page.screenshot({ path: process.argv[3], fullPage: true });
    const closeTarget = process.argv[5];
    const firstTarget = process.argv[6];
    const openProject = async (name) => {
      const [editor] = await Promise.all([
        context.waitForEvent('page'),
        page.getByRole('link', { name: `Open ${name}` }).click(),
      ]);
      await editor.waitForFunction(() => document.documentElement.dataset.runtimeState === 'ready');
      return editor;
    };
    const firstEditor = await openProject(firstTarget);
    const closeEditor = await openProject(closeTarget);
    const concurrentEditors = (await context.pages()).filter((candidate) => candidate !== page && candidate.url().includes('?project=')).length;
    const staleWrite = await firstEditor.evaluate(async () => {
      const projectId = new URL(location.href).searchParams.get('project');
      const snapshotResponse = await fetch(`/v1/projects/${encodeURIComponent(projectId)}/snapshot`, { credentials: 'same-origin' });
      const snapshotBody = await snapshotResponse.json();
      const snapshot = snapshotBody.snapshot;
      const project = snapshot.resources.find((item) => item.kind === 'project');
      const plan = snapshot.resources.find((item) => item.operation_id === 'captions');
      const operation = snapshot.view.operations.find((item) => item.id === 'captions');
      const body = JSON.stringify({
        operation: 'captions',
        readSet: { project: project.etag, operation: operation.etag, plan: plan.etag },
        review: { schema_version: 1, cue_id: 'cue-001', text: 'Saved from packaged Chrome' },
      });
      const save = () => fetch(`/v1/projects/${encodeURIComponent(projectId)}/transactions`, {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body,
      });
      const first = await save();
      const firstBody = await first.json();
      const stale = await save();
      const staleBody = await stale.json();
      return { firstStatus: first.status, firstOk: firstBody.ok, staleStatus: stale.status, staleError: staleBody.error };
    });
    const draftWrite = await closeEditor.evaluate(async () => {
      const projectId = new URL(location.href).searchParams.get('project');
      const response = await fetch(`/v1/projects/${encodeURIComponent(projectId)}/drafts/captions`, {
        method: 'PUT', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseRevision: 1, changes: [{ cueId: 'cue-001', text: 'Recovered in Chrome' }] }),
      });
      return { status: response.status, body: await response.json() };
    });
    const quitDialogReady = page.waitForEvent('dialog');
    const quitClick = page.getByRole('button', { name: 'Quit Editor Service' }).click();
    const quitDialog = await quitDialogReady;
    const quitConfirmation = quitDialog.message();
    await quitDialog.dismiss();
    await quitClick;
    await page.waitForFunction(() => document.documentElement.dataset.runtimeState === 'hub-ready');
    const closeDialogReady = page.waitForEvent('dialog');
    const closeClick = page.getByRole('button', { name: `Close ${closeTarget}` }).click();
    const closeDialog = await closeDialogReady;
    const confirmation = closeDialog.message();
    await closeDialog.accept();
    await closeClick;
    await page.locator('[data-hub-project]', { hasText: closeTarget }).getByText('Ready', { exact: true }).waitFor();
    const recoveredEditor = await openProject(closeTarget);
    const recoveredDraft = await recoveredEditor.evaluate(async () => {
      const projectId = new URL(location.href).searchParams.get('project');
      const response = await fetch(`/v1/projects/${encodeURIComponent(projectId)}/drafts/captions`, { credentials: 'same-origin' });
      return { status: response.status, body: await response.json() };
    });
    await page.getByRole('button', { name: 'Refresh projects' }).click();
    await page.locator('[data-hub-project]', { hasText: closeTarget }).getByText('Open', { exact: true }).waitFor();
    const cleanupDialogReady = page.waitForEvent('dialog');
    const cleanupClick = page.getByRole('button', { name: `Close ${closeTarget}` }).click();
    const cleanupDialog = await cleanupDialogReady;
    await cleanupDialog.accept();
    await cleanupClick;
    await page.locator('[data-hub-project]', { hasText: closeTarget }).getByText('Ready', { exact: true }).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: process.argv[4], fullPage: true });
    process.stdout.write(JSON.stringify({
      url: page.url(),
      names,
      updateText,
      concurrentEditors,
      staleWrite,
      draftWrite,
      quitConfirmation,
      confirmation,
      recoveredDraft,
      firstStatus: await page.locator('[data-hub-project]', { hasText: firstTarget }).locator('.hub-status').textContent(),
      closedStatus: await page.locator('[data-hub-project]', { hasText: closeTarget }).locator('.hub-status').textContent(),
    }));
  } finally { await browser.close(); }
})().catch((error) => { process.stderr.write(String(error)); process.exit(1); });
"""
        result = subprocess.run(
            [
                "node", "-e", script,
                str(REPOSITORY_ROOT / "ui" / "node_modules" / "playwright"), url,
                str(REPOSITORY_ROOT / "ui" / "test-results" / "hub-picker-desktop.png"),
                str(REPOSITORY_ROOT / "ui" / "test-results" / "hub-picker-mobile.png"),
                project_names[1], project_names[0],
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if result.returncode != 0:
            subprocess.run(
                ["node", str(plugin_root / "runtime" / "hub-client.cjs"), "shutdown"],
                cwd=plugin_root, env=environment, check=False, capture_output=True, text=True, timeout=20,
            )
            self.fail(f"installed Chrome Hub smoke failed: {result.stderr}")
        evidence = json.loads(result.stdout)
        parsed = urllib.parse.urlsplit(url)
        self.assertEqual(evidence["url"], f"{parsed.scheme}://{parsed.netloc}/")
        self.assertEqual(set(evidence["names"]), set(project_names))
        self.assertIn("99.0.0 is available", evidence["updateText"])
        self.assertEqual(evidence["concurrentEditors"], 2)
        self.assertEqual(evidence["staleWrite"], {
            "firstStatus": 200, "firstOk": True, "staleStatus": 409, "staleError": "conflict",
        })
        self.assertEqual(evidence["draftWrite"]["status"], 200)
        self.assertIn("mutation lease", evidence["quitConfirmation"])
        self.assertIn("recoverable draft", evidence["quitConfirmation"])
        self.assertIn("recoverable draft", evidence["confirmation"])
        self.assertIn("mutation lease", evidence["confirmation"])
        self.assertEqual(evidence["recoveredDraft"]["status"], 200)
        self.assertEqual(
            evidence["recoveredDraft"]["body"]["draft"]["changes"][0]["text"],
            "Recovered in Chrome",
        )
        self.assertEqual(evidence["firstStatus"], "Open")
        self.assertEqual(evidence["closedStatus"], "Ready")

    def _assert_authenticated_snapshot(self, url: str, project_id: str, session: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        try:
            connection.request(
                "GET",
                f"/v1/projects/{urllib.parse.quote(project_id, safe='')}/snapshot",
                headers={"Cookie": f"cut_session={session}"},
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertTrue(body["ok"])
            self.assertIsInstance(body["snapshot"], dict)
        finally:
            connection.close()

    @staticmethod
    def _draft_request(
        url: str, project_id: str, session: str, method: str, suffix: str,
        body: dict | None = None,
    ) -> tuple[int, dict[str, str], dict]:
        parsed = urllib.parse.urlsplit(url)
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        path = f"/v1/projects/{urllib.parse.quote(project_id, safe='')}/{suffix}"
        try:
            connection.request(method, path, body=payload, headers={
                "Cookie": f"cut_session={session}",
                "Origin": f"{parsed.scheme}://{parsed.netloc}",
                **({"Content-Type": "application/json"} if payload else {}),
            })
            response = connection.getresponse()
            response_body = json.loads(response.read())
            return response.status, {key.lower(): value for key, value in response.getheaders()}, response_body
        finally:
            connection.close()

    def _assert_adversarial_launch_rejections(self, url: str, project_id: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        self._assert_launch_error(f"{base}/?project=wrong-{project_id}&launch={urllib.parse.parse_qs(parsed.query)['launch'][0]}")
        self._assert_launch_error(f"{url}&extra=1")
        self.assertEqual(self._navigate(url, method="POST"), 404)
        self._assert_launch_error(url, destination="script")
        self._assert_launch_error(url, site="same-origin")
        self._assert_launch_error(url, site="cross-site")

    def _assert_launch_error(
        self, url: str, destination: str = "document", site: str = "none"
    ) -> None:
        status, headers, body = self._request(url, destination=destination, site=site)
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("content-type"), "text/html; charset=utf-8")
        self.assertNotIn("set-cookie", headers)
        self.assertIn("Editor launch unavailable", body.decode("utf-8"))

    def test_launch_token_ttl_is_sixty_seconds(self) -> None:
        script = r"""
const { LAUNCH_TTL_MS, launchIsExpired } = require(process.argv[1]);
process.stdout.write(JSON.stringify({
  ttl: LAUNCH_TTL_MS,
  atDeadline: launchIsExpired({ expiresAt: 60000 }, 60000),
  beforeDeadline: launchIsExpired({ expiresAt: 60000 }, 59999),
}));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(json.loads(result.stdout), {
            "ttl": 60_000, "atDeadline": True, "beforeDeadline": False,
        })

    def test_sidecar_uses_snapshot_compatible_generated_caption_cue_ids(self) -> None:
        script = r"""
const { cueIdFor } = require(process.argv[1]);
process.stdout.write(JSON.stringify([
  cueIdFor('captions', {}, 0),
  cueIdFor('captions', { id: 'named' }, 1),
  cueIdFor('content-cards', {}, 0),
]));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(["cue-001", "named", None], json.loads(result.stdout))

    def test_sidecar_reports_ready_before_indexing_heavy_layer_sequences(self) -> None:
        source = (REPOSITORY_ROOT / "runtime" / "sidecar.cjs").read_text(encoding="utf-8")
        initial_files = source.index("await refreshFiles(state, false)")
        listen = source.index("server.listen(0, LOOPBACK, resolve)")
        ready = source.index("process.stdout.write(JSON.stringify(ready) + '\\n')")
        layers = source.index("state.layerRefresh = refreshLayerSequences(state)")

        self.assertLess(initial_files, listen)
        self.assertLess(listen, ready)
        self.assertLess(ready, layers)

    def test_sidecar_keeps_layer_sequences_when_bounds_analysis_is_unavailable(self) -> None:
        source = (REPOSITORY_ROOT / "runtime" / "sidecar.cjs").read_text(encoding="utf-8")
        bounds = source[source.index("async function addSequenceBounds"):source.index("function runProcess")]
        self.assertIn("try {", bounds)
        self.assertIn("} catch {\n    return\n  }", bounds)

    def test_protocol_call_timeout_allows_full_project_validation(self) -> None:
        script = r"""
const { PROTOCOL_CALL_TIMEOUT_MS } = require(process.argv[1]);
process.stdout.write(JSON.stringify(PROTOCOL_CALL_TIMEOUT_MS));
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "sidecar.cjs")],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(json.loads(result.stdout), 30_000)

    @staticmethod
    def _navigate(
        url: str, method: str = "GET", destination: str = "document", site: str = "none"
    ) -> int:
        return PluginPackageTests._request(url, method, destination, site)[0]

    @staticmethod
    def _request(
        url: str, method: str = "GET", destination: str = "document", site: str = "none"
    ) -> tuple[int, dict[str, str], bytes]:
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
            return response.status, {key.lower(): value for key, value in response.getheaders()}, response.read()
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
            "params": {"name": "open_editor", "arguments": {"project_root": str(project_root), "open_browser": False}},
        })
        return json.loads(opened["result"]["content"][0]["text"])

    def _assert_real_browser_ready(self, url: str, project_id: str, project_name: str) -> None:
        script = r"""
const { chromium } = require(process.argv[1]);
(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
    try {
      const page = await browser.newPage();
      await page.goto(process.argv[2]);
      await page.waitForFunction(() => document.documentElement.dataset.runtimeState === 'ready');
      const shell = page.locator('[data-editor-shell]');
      const project = page.getByText(process.argv[3], { exact: true });
      await Promise.all([
        shell.waitFor({ state: 'visible' }),
        project.waitFor({ state: 'visible' }),
      ]);
      const cookie = (await page.context().cookies()).find((item) => item.name === 'cut_session');
      process.stdout.write(JSON.stringify({
        url: page.url(),
        shellVisible: await shell.isVisible(),
        projectVisible: await project.isVisible(),
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
                project_name,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        evidence = json.loads(result.stdout)
        parsed = urllib.parse.urlsplit(url)
        expected_url = f"{parsed.scheme}://{parsed.netloc}/?project={urllib.parse.quote(project_id, safe='')}"
        self.assertEqual(evidence["url"], expected_url)
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
        runtime_root = temporary_root / "installed plugin path with spaces" / "cut-as-code-editor" / "runtime"
        runtime_sources = [
            (runtime_root / name).read_text(encoding="utf-8")
            for name in ("hub-client.cjs", "hub.cjs", "mcp.cjs", "sidecar.cjs")
        ]
        for secret in secret_values:
            self.assertNotIn(secret, captured)
            for source in runtime_sources:
                self.assertNotIn(secret, source)

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
        (root / "work" / "captions" / "captions-plan.json").write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 1,
            "style": {"status": "approved", "preset": "clean"},
            "review": {"status": "pending", "evidence": []},
            "cues": [{
                "id": "cue-001", "index": 1, "start": 0, "end": 1,
                "text": "Fixture caption", "lines": ["Fixture caption"],
                "program_range": {"start_s": 0, "end_s": 1},
            }],
        }) + "\n", encoding="utf-8")
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
