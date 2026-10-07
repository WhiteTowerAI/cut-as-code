"""Build the stable cross-platform desktop launcher bundle."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


FILES = (
    ("Cut as Code Editor.cmd", "Cut as Code Editor.cmd", 0o100644),
    ("Cut as Code Editor.command", "unix-launcher", 0o100755),
    ("cut-as-code-editor", "unix-launcher", 0o100755),
    ("launcher.cjs", "launcher.cjs", 0o100644),
)
TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def build(output: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "launcher"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, source_name, mode in FILES:
                info = zipfile.ZipInfo(name, TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, (source / source_name).read_bytes())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_desktop_launcher.py OUTPUT.zip")
    build(Path(sys.argv[1]))
