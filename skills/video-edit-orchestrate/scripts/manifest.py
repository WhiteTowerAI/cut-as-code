#!/usr/bin/env python3
"""video-edit-orchestrate manifest tool. Stdlib only. See SKILL.md."""
import sys, json, hashlib, argparse, subprocess, os, tempfile

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

def parse_fps(r: str) -> float:
    if not r:
        return 0.0
    if "/" in r:
        n, d = r.split("/", 1)
        d = float(d)
        return 0.0 if d == 0 else round(float(n) / d, 3)
    return float(r)

def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def probe_source(path: str) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    st = d["streams"][0]
    return {
        "path": path,
        "w": int(st["width"]),
        "h": int(st["height"]),
        "fps": parse_fps(st.get("r_frame_rate", "0/1")),
        "dur_s": round(float(d["format"]["duration"]), 3),
        "hash": hash_file(path),
    }

def build_manifest(source: dict, enabled) -> dict:
    enabled = list(enabled)
    anchor = resolve_anchor(enabled)
    default_params = {
        "captions": {"max_chars": 14, "karaoke": True},
        "remotion": {"anchor": anchor},
        "grade": {"crf": 18, "preset": "medium"},
    }
    stages = {}
    for name in enabled:
        stages[name] = {
            "skill": SKILL_OF[name],
            "enabled": True,
            "workdir": f"work/{name}",
            "inputs": {},
            "params": default_params.get(name, {}),
            "decision": {},
            "outputs": {},
            "status": "pending",
        }
    return {"version": 1, "source": source,
            "transcript": {"path": None, "hash": None}, "stages": stages,
            "final": {"composite_order": ["graded", "captions", "cards"],
                      "outputs": {}, "status": "pending"}}

def save_manifest(manifest: dict, path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

def load_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def cmd_init(args) -> int:
    enabled = [s.strip() for s in args.enable.split(",") if s.strip()]
    bad = [s for s in enabled if s not in SKILL_OF]
    if bad:
        print(f"unknown stage(s): {bad}; valid: {list(SKILL_OF)}", file=sys.stderr)
        return 2
    m = build_manifest(probe_source(args.source), enabled)
    save_manifest(m, args.out)
    print(f"[init] {args.source} -> {args.out}: {len(enabled)} stage(s), "
          f"anchor={m['stages'].get('remotion', {}).get('params', {}).get('anchor', 'n/a')}")
    return 0

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

    # --- Task 2: parse_fps + build_manifest (pure) ---
    assert parse_fps("30/1") == 30.0
    assert abs(parse_fps("24000/1001") - 23.976) < 0.001
    assert parse_fps("25") == 25.0
    assert parse_fps("0/0") == 0.0 and parse_fps("") == 0.0
    src = {"path": "first_cut.mp4", "w": 640, "h": 298, "fps": 24.0,
           "dur_s": 1831.3, "hash": "sha256:deadbeef"}
    m = build_manifest(src, ["captions", "remotion", "grade"])
    assert m["version"] == 1 and m["source"] == src
    assert set(m["stages"]) == {"captions", "remotion", "grade"}
    assert m["stages"]["remotion"]["params"]["anchor"] == "top"
    assert m["stages"]["captions"]["skill"] == "video-to-captions"
    assert m["stages"]["grade"]["params"] == {"crf": 18, "preset": "medium"}
    assert all(m["stages"][s]["status"] == "pending" for s in m["stages"])
    m2 = build_manifest(src, ["captions", "grade"])   # no remotion
    assert "remotion" not in m2["stages"]
    assert m2["stages"]["captions"]["skill"] == "video-to-captions"
    m3 = build_manifest(src, ["remotion", "grade"])    # remotion without captions
    assert m3["stages"]["remotion"]["params"]["anchor"] == "bottom"

    print("OK")
    return 0

def main() -> int:
    p = argparse.ArgumentParser(prog="manifest.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    pi = sub.add_parser("init")
    pi.add_argument("source")
    pi.add_argument("--enable", required=True)
    pi.add_argument("--out", default="manifest.json")
    args = p.parse_args()
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "init":
        return cmd_init(args)
    return 1

if __name__ == "__main__":
    sys.exit(main())
