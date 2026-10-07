"""Behavioral contract for the stable desktop launcher."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = REPOSITORY_ROOT / "launcher" / "launcher.cjs"
BUILD_LAUNCHER = REPOSITORY_ROOT / "scripts" / "build_desktop_launcher.py"


class DesktopLauncherTests(unittest.TestCase):
    def test_launcher_opens_the_exact_plugin_version_reported_by_codex(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher & ") as temporary:
            root = Path(temporary)
            codex_home = root / "Codex Home"
            cache = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor"
            self._write_plugin(cache / "0.1.9", "0.1.9", valid=True)
            self._write_plugin(cache / "0.1.10", "0.1.10", valid=True)
            self._write_plugin(cache / "99.0.0", "different-version", valid=True)

            codex_cli = root / "fake codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "pluginId:'cut-as-code-editor@personal',name:'cut-as-code-editor',"
                "marketplaceName:'personal',version:'0.1.10',installed:true,enabled:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "fake browser.cjs"
            browser_log = root / "browser log.json"
            browser_cli.write_text(
                "require('node:fs').writeFileSync(process.env.BROWSER_LOG,"
                "JSON.stringify(process.argv.slice(2)))\n",
                encoding="utf-8",
            )

            environment = os.environ.copy()
            environment.update({
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
                "CAC_BROWSER_CLI": str(browser_cli),
                "BROWSER_LOG": str(browser_log),
                "HUB_LOG": str(root / "hub log.json"),
            })
            result = subprocess.run(
                ["node", str(LAUNCHER)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "Cut as Code Editor opened.\n")
            self.assertEqual(
                json.loads((root / "hub log.json").read_text(encoding="utf-8")),
                {"version": "0.1.10", "args": ["launch"]},
            )
            self.assertEqual(
                json.loads(browser_log.read_text(encoding="utf-8")),
                ["http://127.0.0.1:43123/"],
            )

    def test_all_os_entries_run_the_same_launcher_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher entries ") as temporary:
            root = Path(temporary)
            bundle = root / "launcher.zip"
            subprocess.run([sys.executable, str(BUILD_LAUNCHER), str(bundle)], check=True, timeout=20)
            installed = root / "installed launcher"
            with zipfile.ZipFile(bundle) as archive:
                archive.extractall(installed)
            codex_home = root / "codex"
            plugin_root = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor" / "1.0.0"
            self._write_plugin(plugin_root, "1.0.0", valid=True)
            codex_cli = root / "codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.0.0',"
                "installed:true,enabled:true}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "browser.cjs"
            browser_cli.write_text("process.exit(0)\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
                "CAC_BROWSER_CLI": str(browser_cli),
                "HUB_LOG": str(root / "hub.json"),
            })
            entries = [
                ["cmd.exe", "/d", "/c", "call", str(installed / "Cut as Code Editor.cmd")],
                ["node", str(installed / "Cut as Code Editor.command")],
                ["node", str(installed / "cut-as-code-editor")],
            ]

            for command in entries:
                with self.subTest(entry=command[-1]):
                    result = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        env=environment,
                        timeout=20,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "Cut as Code Editor opened.\n")

    @unittest.skipUnless(os.name == "nt", "Windows npm shim contract")
    def test_windows_npm_codex_shim_runs_without_a_shell(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher npm shim ") as temporary:
            root = Path(temporary)
            codex_home = root / "codex-home"
            plugin_root = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor" / "1.2.3"
            self._write_plugin(plugin_root, "1.2.3", valid=True)
            bin_root = root / "npm"
            codex_js = bin_root / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
            codex_js.parent.mkdir(parents=True)
            (bin_root / "codex.cmd").write_text("@echo off\r\n", encoding="utf-8")
            codex_js.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.2.3',installed:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "browser.cjs"
            browser_cli.write_text("process.exit(0)\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "CODEX_HOME": str(codex_home),
                "CAC_BROWSER_CLI": str(browser_cli),
                "HUB_LOG": str(root / "hub.json"),
                "PATH": str(bin_root),
            })
            environment.pop("CAC_CODEX_CLI", None)

            result = subprocess.run(
                ["node", str(LAUNCHER)], check=False, capture_output=True, text=True,
                encoding="utf-8", env=environment, timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "Cut as Code Editor opened.\n")

    def test_invalid_plugin_and_browser_failure_are_actionable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher failures ") as temporary:
            root = Path(temporary)
            codex_home = root / "codex"
            cache = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor"
            self._write_plugin(cache / "1.0.0", "1.0.0", valid=False)
            codex_cli = root / "codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.0.0',installed:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "browser.cjs"
            browser_cli.write_text("process.exit(1)\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
                "CAC_BROWSER_CLI": str(browser_cli),
            })

            result = subprocess.run(
                ["node", str(LAUNCHER)], check=False, capture_output=True, text=True,
                encoding="utf-8", env=environment, timeout=20,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No valid installed Cut as Code Editor Plugin", result.stderr)

    def test_browser_failure_preserves_the_local_url(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher browser ") as temporary:
            root = Path(temporary)
            codex_home = root / "codex"
            self._write_plugin(
                codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor" / "1.0.0",
                "1.0.0",
                valid=True,
            )
            codex_cli = root / "codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.0.0',installed:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "browser.cjs"
            browser_cli.write_text("process.exit(1)\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
                "CAC_BROWSER_CLI": str(browser_cli),
                "HUB_LOG": str(root / "hub.json"),
            })

            result = subprocess.run(
                ["node", str(LAUNCHER)], check=False, capture_output=True, text=True,
                encoding="utf-8", env=environment, timeout=20,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("http://127.0.0.1:43123/", result.stderr)

    def test_missing_prerequisites_and_hub_failure_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher errors ") as temporary:
            root = Path(temporary)
            missing_cli = os.environ.copy()
            missing_cli["CAC_CODEX_CLI"] = str(root / "missing-codex.cjs")
            result = self._run_launcher(missing_cli)
            self.assertIn("Codex Plugin metadata is unavailable", result.stderr)

            codex_cli = root / "codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[]})+'\\n')\n",
                encoding="utf-8",
            )
            no_plugin = {**os.environ, "CAC_CODEX_CLI": str(codex_cli)}
            result = self._run_launcher(no_plugin)
            self.assertIn("Plugin is not installed", result.stderr)

            codex_home = root / "codex"
            plugin_root = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor" / "1.0.0"
            self._write_plugin(plugin_root, "1.0.0", valid=True)
            (plugin_root / "runtime" / "hub-client.cjs").write_text("process.exit(1)\n", encoding="utf-8")
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.0.0',installed:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            hub_failure = {
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
            }
            result = self._run_launcher(hub_failure)
            self.assertIn("Editor Hub could not be started", result.stderr)

    def test_concurrent_double_clicks_delegate_to_the_hub_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher concurrent ") as temporary:
            root = Path(temporary)
            codex_home = root / "codex"
            plugin_root = codex_home / "plugins" / "cache" / "personal" / "cut-as-code-editor" / "1.0.0"
            self._write_plugin(plugin_root, "1.0.0", valid=True)
            codex_cli = root / "codex.cjs"
            codex_cli.write_text(
                "process.stdout.write(JSON.stringify({installed:[{"
                "name:'cut-as-code-editor',marketplaceName:'personal',version:'1.0.0',installed:true"
                "}]})+'\\n')\n",
                encoding="utf-8",
            )
            browser_cli = root / "browser.cjs"
            browser_cli.write_text("process.exit(0)\n", encoding="utf-8")
            environment = {
                **os.environ,
                "CODEX_HOME": str(codex_home),
                "CAC_CODEX_CLI": str(codex_cli),
                "CAC_BROWSER_CLI": str(browser_cli),
                "HUB_LOG": str(root / "hub.json"),
            }
            processes = [
                subprocess.Popen(
                    ["node", str(LAUNCHER)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", env=environment,
                )
                for _ in range(2)
            ]

            results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]

            self.assertEqual(results, [
                ("Cut as Code Editor opened.\n", "", 0),
                ("Cut as Code Editor opened.\n", "", 0),
            ])

    def test_launcher_build_creates_one_stable_cross_platform_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cut launcher bundle ") as temporary:
            output = Path(temporary) / "cut-as-code-editor-launcher.zip"
            second = Path(temporary) / "cut-as-code-editor-launcher-second.zip"
            results = [subprocess.run(
                [sys.executable, str(BUILD_LAUNCHER), str(target)],
                check=False, capture_output=True, text=True, encoding="utf-8", timeout=20,
            ) for target in (output, second)]

            self.assertTrue(all(result.returncode == 0 for result in results), results)
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), [
                    "Cut as Code Editor.cmd",
                    "Cut as Code Editor.command",
                    "cut-as-code-editor",
                    "launcher.cjs",
                ])
                self.assertEqual(archive.getinfo("Cut as Code Editor.command").external_attr >> 16, 0o100755)
                self.assertEqual(archive.getinfo("cut-as-code-editor").external_attr >> 16, 0o100755)

    @staticmethod
    def _run_launcher(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["node", str(LAUNCHER)], check=False, capture_output=True, text=True,
            encoding="utf-8", env=environment, timeout=20,
        )

    @staticmethod
    def _write_plugin(plugin_root: Path, version: str, *, valid: bool) -> None:
        (plugin_root / ".codex-plugin").mkdir(parents=True)
        (plugin_root / "runtime").mkdir()
        (plugin_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "cut-as-code-editor", "version": version}),
            encoding="utf-8",
        )
        if valid:
            (plugin_root / "runtime" / "hub-client.cjs").write_text(
                "const fs=require('node:fs');const path=require('node:path');"
                "const manifest=require(path.join(__dirname,'..','.codex-plugin','plugin.json'));"
                "fs.writeFileSync(process.env.HUB_LOG,JSON.stringify({version:manifest.version,args:process.argv.slice(2)}));"
                "process.stdout.write(JSON.stringify({ok:true,url:'http://127.0.0.1:43123/'})+'\\n')\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    unittest.main()
