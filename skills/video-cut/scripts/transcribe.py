"""Compatibility entry point for the canonical video-understand transcriber."""

import importlib.util
from pathlib import Path


CANONICAL_SCRIPT = (
    Path(__file__).resolve().parents[2] / "video-understand" / "scripts" / "transcribe.py"
)
_spec = importlib.util.spec_from_file_location("open_recut_transcribe", CANONICAL_SCRIPT)
_canonical = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canonical)

fmt_ts = _canonical.fmt_ts
parse_args = _canonical.parse_args
transcribe = _canonical.transcribe
main = _canonical.main


if __name__ == "__main__":
    main()
