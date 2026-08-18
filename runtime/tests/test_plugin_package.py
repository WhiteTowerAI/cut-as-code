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
const { TOOL, openBrowser, shouldOpenBrowser } = require(process.argv[1]);
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
  process.stdout.write(JSON.stringify({
    defaultValue: shouldOpenBrowser(undefined),
    falseValue: shouldOpenBrowser(false),
    trueValue: shouldOpenBrowser(true),
    invalidValue: (() => { try { shouldOpenBrowser('false'); return null; } catch (error) { return error.message; } })(),
    description: TOOL.description,
    inputSchema: TOOL.inputSchema,
    calls,
  }));
})().catch((error) => { process.stderr.write(error.stack); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(REPOSITORY_ROOT / "runtime" / "mcp.cjs")],
            check=True,
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
            self._audit_graphic_motion_core(extracted, root / "graphic motion core project")
            self._smoke_open_editor(extracted, root / "video project with spaces", root)

    def test_compliance_inventory_covers_packaged_third_party_assets_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut compliance package ") as temporary:
            package_root = Path(temporary) / "package with spaces"
            shutil.copytree(
                REPOSITORY_ROOT / "skills" / "video-add-graphic-motion" / "recipes" / "animxyz",
                package_root / "skills" / "video-add-graphic-motion" / "recipes" / "animxyz",
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
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
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
                "runtime/export_project.py",
                "runtime/mcp.cjs",
                "runtime/project_snapshot.py",
                "runtime/protocol_service.py",
                "runtime/sequence_bounds.py",
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
            self.assertEqual(sidecar.count("spawn("), 3)
            self.assertIn("runProcess('ffmpeg',", sidecar)
            self.assertIn("path.join(__dirname, 'sequence_bounds.py')", sidecar)
            self.assertEqual(mcp.count("spawn("), 1)
            self.assertIn("startProtocolService", sidecar)
            self.assertIn("sidecar.cjs", mcp)
            self.assertIn("function browserLaunchSpec", mcp)
            self.assertIn("function openBrowser", mcp)
            self.assertIn("spawnProcess(command, [...args, url], options)", mcp)
            self.assertIn("child.once('spawn', resolve)", mcp)
            self.assertIn("child.once('error', reject)", mcp)
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
            ["POST", "/v1/projects/project_a/exports"],
            ["GET", "/v1/projects/project_a/exports/status"],
            ["POST", "/v1/projects/project_a/exports/open"],
            ["GET", "/v1/projects/project_a/resources/res_a1"],
            ["GET", "/v1/projects/project_a/media/asset_a1"],
            ["GET", "/v1/projects/project_a/artifacts/artifact_a1"],
            ["GET", "/v1/projects/project_a/layers/layer_a1/frames/1"],
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
            ["launch", "meta", "snapshot", "transaction", "review", "export-start", "export-status", "export-action", "resource", "file", "layer-frame", "events", "static"],
        )
        self.assertEqual(
            audit["actual"],
            ["launch", "meta", "snapshot", "transaction", "review", "export-start", "export-status", "export-action", "resource", "file", "file", "layer-frame", "events", "static", "static", None, None, None, None],
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
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root), "open_browser": False}},
            })
            details = json.loads(opened["result"]["content"][0]["text"])
            self.assertTrue(details["url"].startswith("http://127.0.0.1:"))
            self.assertIn("launch=", details["url"])
            self.assertEqual(set(details), {"pid", "projectRoot", "url", "projectId"})
            first_pid = details["pid"]
            self._assert_real_browser_ready(details["url"], details["projectId"])
            self._assert_launch_error(details["url"])

            reopened = self._rpc(process, {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "open_editor", "arguments": {"project_root": str(project_root), "open_browser": False}},
            })
            reconnected = json.loads(reopened["result"]["content"][0]["text"])
            self.assertNotEqual(reconnected["url"], details["url"])
            self.assertEqual(reconnected["pid"], details["pid"])
            self._assert_adversarial_launch_rejections(reconnected["url"], reconnected["projectId"])
            self._assert_real_browser_ready(reconnected["url"], reconnected["projectId"])
            self._assert_launch_error(reconnected["url"])

            final = self._open_editor(process, 4, project_root)
            self._assert_real_browser_ready(final["url"], final["projectId"])
            self._assert_no_secret_persistence(temporary_root, process)
            self._rpc(process, {"jsonrpc": "2.0", "id": 5, "method": "shutdown"})
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
        layers = source.index("void refreshLayerSequences(state)")

        self.assertLess(initial_files, listen)
        self.assertLess(listen, ready)
        self.assertLess(ready, layers)

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
