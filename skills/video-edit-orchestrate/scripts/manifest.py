#!/usr/bin/env python3
"""video-edit-orchestrate manifest tool. Stdlib only. See SKILL.md."""
import sys, json, hashlib, argparse, subprocess, os, tempfile, copy

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

def fold_stage(manifest: dict, stage: str, stagefile: dict, hasher=None) -> dict:
    if hasher is None:
        hasher = hash_file
    if stage not in manifest["stages"]:
        raise KeyError(f"stage '{stage}' not in manifest (have {list(manifest['stages'])})")
    m = copy.deepcopy(manifest)
    st = m["stages"][stage]
    st["params"] = stagefile.get("params", st.get("params", {}))
    st["params_hash"] = params_hash(st["params"])
    st["decision"] = stagefile.get("decision", st.get("decision", {}))
    st["status"] = stagefile.get("status", "done")
    st["inputs"] = {p: hasher(p) for p in stagefile.get("input_paths", [])}
    st["outputs"] = {p: hasher(p) for p in stagefile.get("output_paths", [])}
    return m

def stage_dirty(stage: dict, hasher=None, exists=None) -> list:
    if hasher is None:
        hasher = hash_file
    if exists is None:
        exists = os.path.exists
    reasons = []
    for path, recorded in stage.get("inputs", {}).items():
        if not exists(path):
            reasons.append(f"missing:{path}")
        elif hasher(path) != recorded:
            reasons.append(f"changed:{path}")
    if params_hash(stage.get("params", {})) != stage.get("params_hash", params_hash(stage.get("params", {}))):
        reasons.append("params")
    return reasons

def cmd_status(args) -> int:
    m = load_manifest(args.manifest)
    for name, st in m["stages"].items():
        reasons = stage_dirty(st)
        tag = "clean" if not reasons else "DIRTY: " + ", ".join(reasons)
        print(f"  {name:10s} [{st['status']}] {tag}")
    return 0

def render_edit_md(manifest: dict) -> str:
    s = manifest["source"]
    lines = [
        f"# EDIT — {s['path']}",
        "",
        f"- Source: `{s['path']}`  ({s['w']}×{s['h']}, {s['fps']} fps, {s['dur_s']}s)",
        f"- Source hash: `{s['hash']}`",
        "",
        "> Generated from `manifest.json` by `manifest.py render`. Do not hand-edit.",
        "",
        "## Stages",
        "",
        "| stage | skill | status | decision | outputs |",
        "|---|---|---|---|---|",
    ]
    for name, st in manifest["stages"].items():
        dec = json.dumps(st.get("decision", {}), ensure_ascii=False) if st.get("decision") else "—"
        outs = ", ".join(f"`{p}`" for p in st.get("outputs", {})) or "—"
        lines.append(f"| {name} | {st['skill']} | {st['status']} | {dec} | {outs} |")
    fin = manifest.get("final", {})
    order = " + ".join(fin.get("composite_order", []))
    final_outs = ", ".join(f"`{p}`" for p in fin.get("outputs", {})) or "—"
    lines += [
        "",
        "## Join (final composite)",
        "",
        f"- Composite order: {order or '—'}",
        f"- Output: {final_outs}  (status: {fin.get('status', '—')})",
        "",
        "```",
        "# see SKILL.md §join for the exact ffmpeg command(s);",
        "# captions bottom, cards top, audio -c:a copy",
        "ffmpeg -y -i graded.mp4 -i caption-overlay.mov ... -c:a copy final.mp4",
        "```",
        "",
    ]
    return "\n".join(lines)

def cmd_render(args) -> int:
    md = render_edit_md(load_manifest(args.manifest))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[render] {args.manifest} -> {args.out} ({len(md)} bytes)")
    return 0

def cmd_fold(args) -> int:
    manifest = load_manifest(args.manifest)
    with open(getattr(args, "from"), encoding="utf-8") as f:
        stagefile = json.load(f)
    manifest = fold_stage(manifest, args.stage, stagefile)
    save_manifest(manifest, args.manifest)
    print(f"[fold] {args.stage} <- {getattr(args, 'from')}: "
          f"status={manifest['stages'][args.stage]['status']}")
    return 0

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

    # --- Task 3: fold_stage merges ONE stage, leaves siblings untouched ---
    fake = {"first_cut.mp4": "sha256:aaa", "cut.json": "sha256:bbb",
            "cap.mov": "sha256:ccc"}
    m4 = build_manifest(src, ["captions", "remotion", "grade"])
    sf = {"params": {"max_chars": 12, "karaoke": False},
          "decision": {"chunking": "approved"},
          "input_paths": ["cut.json", "first_cut.mp4"],
          "output_paths": ["cap.mov"], "status": "done"}
    m5 = fold_stage(m4, "captions", sf, hasher=lambda p: fake[p])
    c = m5["stages"]["captions"]
    assert c["status"] == "done"
    assert c["inputs"] == {"cut.json": "sha256:bbb", "first_cut.mp4": "sha256:aaa"}
    assert c["outputs"] == {"cap.mov": "sha256:ccc"}
    assert c["decision"] == {"chunking": "approved"}
    assert c["params_hash"] == params_hash({"max_chars": 12, "karaoke": False})
    # siblings untouched, and the input manifest was not mutated
    assert m5["stages"]["remotion"]["status"] == "pending"
    assert m4["stages"]["captions"]["status"] == "pending"
    try:
        fold_stage(m4, "nosuch", sf)
        assert False, "expected KeyError"
    except KeyError:
        pass

    # --- Task 4: stage_dirty (pure, direct-input + params only) ---
    stg = {"inputs": {"a.mp4": "sha256:aaa", "b.json": "sha256:bbb"},
           "params": {"crf": 18}, "params_hash": params_hash({"crf": 18})}
    live = {"a.mp4": "sha256:aaa", "b.json": "sha256:bbb"}
    assert stage_dirty(stg, hasher=lambda p: live[p], exists=lambda p: True) == []
    changed = dict(live); changed["b.json"] = "sha256:ZZZ"
    assert stage_dirty(stg, hasher=lambda p: changed[p], exists=lambda p: True) == ["changed:b.json"]
    assert stage_dirty(stg, hasher=lambda p: live[p],
                       exists=lambda p: p != "a.mp4") == ["missing:a.mp4"]
    stg2 = dict(stg, params={"crf": 20})   # params drifted from stored hash
    assert stage_dirty(stg2, hasher=lambda p: live[p], exists=lambda p: True) == ["params"]
    # pending stage, nothing recorded yet -> clean
    assert stage_dirty({"inputs": {}, "params": {}, "params_hash": params_hash({})}) == []

    # --- Task 5: render_edit_md (pure) ---
    m6 = build_manifest(src, ["captions", "grade"])
    m6["stages"]["grade"]["decision"] = {"look": "clean_neutral"}
    m6["stages"]["grade"]["outputs"] = {"out/graded.mp4": "sha256:g"}
    md = render_edit_md(m6)
    assert md.startswith("# EDIT — ")
    assert "first_cut.mp4" in md
    assert "video-color-grade" in md and "clean_neutral" in md
    assert "out/graded.mp4" in md
    assert "| captions |" in md and "| grade |" in md
    assert "remotion" not in md          # disabled stage not shown
    assert "ffmpeg" in md                # join command block present

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
    pf = sub.add_parser("fold")
    pf.add_argument("--manifest", default="manifest.json")
    pf.add_argument("--stage", required=True)
    pf.add_argument("--from", dest="from", required=True)
    ps = sub.add_parser("status")
    ps.add_argument("--manifest", default="manifest.json")
    pr = sub.add_parser("render")
    pr.add_argument("--manifest", default="manifest.json")
    pr.add_argument("--out", default="EDIT.md")
    args = p.parse_args()
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "fold":
        return cmd_fold(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "render":
        return cmd_render(args)
    return 1

if __name__ == "__main__":
    sys.exit(main())
