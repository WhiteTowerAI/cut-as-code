#!/usr/bin/env python3
"""video-edit-orchestrate manifest tool. Stdlib only. See SKILL.md."""
import sys, json, hashlib, argparse

SKILL_OF = {
    "captions": "video-to-captions",
    "remotion": "video-to-remotion",
    "grade": "video-color-grade",
}

def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def canon_params(params: dict) -> str:
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))

def params_hash(params: dict) -> str:
    return sha256_bytes(canon_params(params).encode("utf-8"))

def resolve_anchor(enabled) -> str:
    return "top" if {"captions", "remotion"} <= set(enabled) else "bottom"

def selftest() -> int:
    assert sha256_bytes(b"") == "sha256:" + hashlib.sha256(b"").hexdigest()
    assert canon_params({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert canon_params({}) == "{}" and canon_params(None) == "{}"
    assert params_hash({"a": 1}) == params_hash({"a": 1})
    assert params_hash({"a": 1}) != params_hash({"a": 2})
    assert resolve_anchor({"captions", "remotion"}) == "top"
    assert resolve_anchor({"captions", "remotion", "grade"}) == "top"
    assert resolve_anchor({"captions", "grade"}) == "bottom"
    assert resolve_anchor({"remotion"}) == "bottom"
    assert SKILL_OF["grade"] == "video-color-grade"
    print("OK")
    return 0

def main() -> int:
    p = argparse.ArgumentParser(prog="manifest.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    args = p.parse_args()
    if args.cmd == "selftest":
        return selftest()
    return 1

if __name__ == "__main__":
    sys.exit(main())
