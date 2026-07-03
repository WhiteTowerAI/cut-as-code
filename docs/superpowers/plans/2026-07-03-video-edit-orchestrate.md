# video-edit-orchestrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `skills/video-edit-orchestrate/` skill that coordinates the four existing video skills (rough-cut, captions, remotion, color-grade) as per-branch parallel pipelines around a single `manifest.json` edit-doc, without modifying any of the four skills.

**Architecture:** One small stdlib-only Python tool (`manifest.py`) owns the manifest as the shared interface — `init` seeds it from an ffprobe of the source, `fold` merges one branch's `stage.json` at a time (serialized, no lock), `status` reports direct-input + params staleness, `render` projects it to a human-readable `EDIT.md`. A prose `SKILL.md` playbook drives the agent: fan out the enabled post-cut stages, run each stage's own propose→gate→render pipeline, auto-settle ANCHOR, and join the transparent overlays onto the graded footage. The four skills stay untouched; the orchestrator only calls their existing scripts.

**Tech Stack:** Python 3.12 stdlib only (`hashlib`, `json`, `subprocess`, `argparse`, `os`, `sys`, `tempfile`); `ffprobe` (already required by the repo); Markdown for `SKILL.md` / `EDIT.md`.

## Global Constraints

- **The four existing skills are NOT modified.** `video-rough-cut`, `video-to-captions`, `video-to-remotion`, `video-color-grade` — their scripts are invoked, their SKILL.md files stay authoritative. Any task that edits them is wrong.
- **`manifest.py` uses the Python standard library only** — no new pip/conda dependencies. `ffprobe` is the only external process it spawns.
- **Orchestrator is the manifest's only writer, and serializes writes.** Every mutation is one atomic *read → merge exactly one stage → write back* (temp file + `os.replace`). `fold` takes exactly one stage per call and never batch-merges. The write-queue is the mutual exclusion — no lockfile.
- **Staleness is direct-input + params only — no transitive graph walk.** A stage is dirty iff one of its own recorded input files changed hash, an input file is missing, or its `params` hash changed. Rough-cut is the serial root, not a manifest stage; editing its internal `edit_coarse.json` is invisible to `status` until rough-cut is re-run.
- **ANCHOR auto-settle:** at `init`, if BOTH `captions` and `remotion` are in the enabled-set, set `remotion.params.anchor = "top"`; otherwise it stays `"bottom"`. Never asked as a human gate.
- **Render concurrency cap defaults to 1** heavy Remotion render (grade's cheap ffmpeg pass may overlap). Documented in SKILL.md; not enforced by `manifest.py`.
- **Windows/ffmpeg gotcha (SKILL.md join commands):** drive-colon paths break ffmpeg filtergraph options that take a path; run ffmpeg with `cwd` set to the file's folder and reference by basename. `manifest.py` itself only calls `ffprobe` (no path-taking filter), so it is unaffected — but the join commands in SKILL.md must respect this.
- **No test framework in the repo.** The one runnable check is an assert-based `selftest` subcommand inside `manifest.py` (`python manifest.py selftest`). Pure logic is separated from I/O so `selftest` can drive it with fixtures.
- **Manifest stage names** are exactly `captions`, `remotion`, `grade`. Skill mapping: `captions → video-to-captions`, `remotion → video-to-remotion`, `grade → video-color-grade`.

---
## File Structure

- `skills/video-edit-orchestrate/scripts/manifest.py` — the only real code. One module, stdlib only. Internal layers: **pure helpers** (hashing, param canonicalization, anchor rule, dirty-diff) kept free of I/O so `selftest` can drive them; **I/O helpers** (`hash_file`, `load/save_manifest`, `probe_source`); **command funcs** (`cmd_init/fold/status/render/selftest`); **argparse dispatch**.
- `skills/video-edit-orchestrate/manifest.example.json` — a worked manifest, mirrors the repo's `looks.example.json`/`overlays.example.json` convention.
- `skills/video-edit-orchestrate/SKILL.md` — the agent playbook (prose). No executable logic.

`manifest.py` is its own test harness: `python manifest.py selftest` runs assert-based checks in a tempdir. Each task that adds a verb also adds its selftest assertions — that is the TDD "failing test" for a repo with no pytest.

**Stage-name / skill map (used everywhere):** `captions → video-to-captions`, `remotion → video-to-remotion`, `grade → video-color-grade`.

**`stage.json` shape (written by a branch subagent, consumed by `fold`):**
```json
{
  "params": {"max_chars": 14, "karaoke": true},
  "decision": {"chunking": "approved", "name_fixes": {"social front": "Herschel Fruean"}},
  "input_paths": ["work/selfcheck/cut_transcript.json", "first_cut.mp4"],
  "output_paths": ["work/captions/out/caption-overlay.mov"],
  "status": "done"
}
```
`fold` hashes the listed `input_paths`/`output_paths` from disk (single source of truth), computes `params_hash`, and merges — the branch reports paths + decision + status, never hashes.

---

### Task 1: Pure helpers + selftest harness

**Files:**
- Create: `skills/video-edit-orchestrate/scripts/manifest.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `sha256_bytes(data: bytes) -> str` → returns `"sha256:" + hexdigest`.
  - `canon_params(params: dict) -> str` → deterministic JSON string (`sort_keys=True, separators=(",",":")`) used as the param-hash input.
  - `params_hash(params: dict) -> str` → `sha256_bytes(canon_params(params).encode())`.
  - `resolve_anchor(enabled: set[str]) -> str` → `"top"` if `{"captions","remotion"} <= enabled` else `"bottom"`.
  - `SKILL_OF: dict[str,str]` = `{"captions":"video-to-captions","remotion":"video-to-remotion","grade":"video-color-grade"}`.
  - `selftest()` → runs all asserts, prints `OK`, returns 0.
  - CLI: `python manifest.py selftest`.

- [ ] **Step 1: Write the failing test (the selftest body)**

Create `skills/video-edit-orchestrate/scripts/manifest.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run the selftest to confirm it passes**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: prints `OK`, exit 0. (For a repo with no pytest, the selftest IS the test; Step 1 wrote both the assertions and the code they exercise. If any assert fires, fix the helper it names before continuing.)

- [ ] **Step 3: Verify the CLI rejects unknown commands**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py bogus`
Expected: argparse error (exit 2, message listing `selftest`). Confirms dispatch is wired.

- [ ] **Step 4: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "feat(orchestrate): manifest.py pure helpers + selftest harness"
```

### Task 2: `init` — probe source, seed manifest, auto-settle ANCHOR

**Files:**
- Modify: `skills/video-edit-orchestrate/scripts/manifest.py`

**Interfaces:**
- Consumes: `sha256_bytes`, `params_hash`, `resolve_anchor`, `SKILL_OF` (Task 1).
- Produces:
  - `parse_fps(r: str) -> float` → `"24000/1001" → 23.976`, `"30/1" → 30.0`; on `0`/empty denominator returns `0.0`.
  - `probe_source(path) -> dict` → `{"path", "w", "h", "fps", "dur_s", "hash"}` via one `ffprobe` call (adds `r_frame_rate` to `probe.py`'s field set; hashes the file).
  - `build_manifest(source: dict, enabled: list[str]) -> dict` → the seeded manifest (pure; no I/O). Sets `remotion.params.anchor` via `resolve_anchor`; seeds `grade.params = {"crf":18,"preset":"medium"}`; every stage starts `status:"pending"`, empty `inputs/outputs`, `decision:{}`.
  - `save_manifest(manifest, path)` → atomic write (`tempfile` + `os.replace`), `indent=2`, trailing newline.
  - `load_manifest(path) -> dict`.
  - CLI: `python manifest.py init SOURCE --enable captions,remotion,grade [--out manifest.json]`.

- [ ] **Step 1: Extend selftest with the pure-logic assertions**

Add to `selftest()` in `manifest.py`, before `print("OK")`:

```python
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
```

- [ ] **Step 2: Run selftest to verify it FAILS**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `NameError: name 'parse_fps' is not defined` (or `build_manifest`). Confirms the new assertions exercise code that does not exist yet.

- [ ] **Step 3: Implement the functions**

Add these to `manifest.py` (after `params_hash`, before `selftest`). Add `import subprocess, os, tempfile` to the top imports:

```python
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
```

- [ ] **Step 4: Wire `init` into argparse**

In `main()`, after the `selftest` subparser line, add:

```python
    pi = sub.add_parser("init")
    pi.add_argument("source")
    pi.add_argument("--enable", required=True)
    pi.add_argument("--out", default="manifest.json")
```

And in the dispatch chain, before `return 1`:

```python
    if args.cmd == "init":
        return cmd_init(args)
```

- [ ] **Step 5: Run selftest to verify it PASSES**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `OK`, exit 0.

- [ ] **Step 6: Smoke-test `init` against a real clip**

Find any `.mp4` on disk (e.g. a repo test asset) and run:
`python skills/video-edit-orchestrate/scripts/manifest.py init <that>.mp4 --enable captions,remotion,grade --out /tmp/m.json`
Expected: prints `[init] ... anchor=top`; `/tmp/m.json` has real `w/h/fps/dur_s`, a `sha256:` source hash, three pending stages. (If no clip is handy, skip and rely on the build_manifest selftest — the ffprobe call mirrors the repo's working `probe.py`.)

- [ ] **Step 7: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "feat(orchestrate): manifest init — probe source, seed stages, auto ANCHOR"
```

### Task 3: `fold` — merge one branch's stage.json (serialized, one stage per call)

**Files:**
- Modify: `skills/video-edit-orchestrate/scripts/manifest.py`

**Interfaces:**
- Consumes: `hash_file`, `params_hash`, `load_manifest`, `save_manifest` (Task 2).
- Produces:
  - `fold_stage(manifest: dict, stage: str, stagefile: dict, hasher=hash_file) -> dict` → **pure-ish** merge of ONE stage into a copy of the manifest: sets `params`, `decision`, `status`; hashes each path in `input_paths`/`output_paths` into `inputs`/`outputs`; stores `params_hash`. `hasher` is injectable so selftest passes a fake. Raises `KeyError` if `stage` not in `manifest["stages"]`. Never touches sibling stages.
  - `cmd_fold(args)` → load manifest, read `stagefile` JSON, call `fold_stage` with real `hash_file`, save. **One stage per invocation** — the serialization guarantee (§3.1).
  - CLI: `python manifest.py fold --manifest manifest.json --stage captions --from work/captions/stage.json`.

- [ ] **Step 1: Extend selftest with fold assertions**

Add to `selftest()` before `print("OK")`:

```python
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
```

- [ ] **Step 2: Run selftest to verify it FAILS**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `NameError: name 'fold_stage' is not defined`.

- [ ] **Step 3: Implement `fold_stage` and `cmd_fold`**

Add to `manifest.py` after `load_manifest`. Add `import copy` to the top imports:

```python
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

def cmd_fold(args) -> int:
    manifest = load_manifest(args.manifest)
    with open(getattr(args, "from"), encoding="utf-8") as f:
        stagefile = json.load(f)
    manifest = fold_stage(manifest, args.stage, stagefile)
    save_manifest(manifest, args.manifest)
    print(f"[fold] {args.stage} <- {getattr(args, 'from')}: "
          f"status={manifest['stages'][args.stage]['status']}")
    return 0
```

- [ ] **Step 4: Wire `fold` into argparse**

In `main()`, add a subparser (note `--from` needs `dest` because `from` is a keyword):

```python
    pf = sub.add_parser("fold")
    pf.add_argument("--manifest", default="manifest.json")
    pf.add_argument("--stage", required=True)
    pf.add_argument("--from", dest="from", required=True)
```

And in dispatch:

```python
    if args.cmd == "fold":
        return cmd_fold(args)
```

- [ ] **Step 5: Run selftest to verify it PASSES**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `OK`.

- [ ] **Step 6: End-to-end fold smoke test**

```bash
cd skills/video-edit-orchestrate/scripts
python - <<'PY'
import json, subprocess, tempfile, os
# make a tiny real file to hash
d = tempfile.mkdtemp()
open(os.path.join(d, "cap.mov"), "wb").write(b"x")
mani = os.path.join(d, "manifest.json")
# seed a manifest by hand (init needs ffprobe; keep this test pure)
import manifest as M
m = M.build_manifest({"path":"s.mp4","w":1,"h":1,"fps":24.0,"dur_s":1.0,"hash":"sha256:0"}, ["captions"])
M.save_manifest(m, mani)
sf = os.path.join(d, "stage.json")
json.dump({"params":{"max_chars":12},"decision":{"chunking":"approved"},
           "input_paths":[], "output_paths":[os.path.join(d,"cap.mov")], "status":"done"}, open(sf,"w"))
subprocess.run(["python","manifest.py","fold","--manifest",mani,"--stage","captions","--from",sf], check=True)
out = json.load(open(mani))
assert out["stages"]["captions"]["status"] == "done"
assert list(out["stages"]["captions"]["outputs"].values())[0].startswith("sha256:")
print("fold e2e OK")
PY
```
Expected: `[fold] captions <- ...` then `fold e2e OK`.

- [ ] **Step 7: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "feat(orchestrate): manifest fold — merge one stage, hash paths, leave siblings"
```

### Task 4: `status` — direct-input + params staleness (no graph walk)

**Files:**
- Modify: `skills/video-edit-orchestrate/scripts/manifest.py`

**Interfaces:**
- Consumes: `hash_file`, `params_hash`, `load_manifest` (Tasks 2–3).
- Produces:
  - `stage_dirty(stage: dict, hasher=hash_file, exists=os.path.exists) -> list[str]` → **pure** reasons a stage is stale: `"missing:<path>"` for a recorded input file no longer on disk, `"changed:<path>"` for a hash mismatch, `"params"` if the current `params_hash(stage["params"])` differs from stored `stage["params_hash"]`. Empty list = clean. A `pending` stage with no recorded inputs returns `[]` (nothing to be stale against). Injectable `hasher`/`exists` for selftest.
  - `cmd_status(args)` → load manifest, print one line per stage (`clean` / `DIRTY: reasons`), exit 0.
  - CLI: `python manifest.py status [--manifest manifest.json]`.

- [ ] **Step 1: Extend selftest with staleness assertions**

Add to `selftest()` before `print("OK")`:

```python
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
```

- [ ] **Step 2: Run selftest to verify it FAILS**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `NameError: name 'stage_dirty' is not defined`.

- [ ] **Step 3: Implement `stage_dirty` and `cmd_status`**

Add to `manifest.py` after `fold_stage`:

```python
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
```

Note: the params clause compares against the *stored* `params_hash`; when absent it falls back to the freshly computed value, so a stage that never recorded a `params_hash` (fresh `pending`) is not spuriously flagged.

- [ ] **Step 4: Wire `status` into argparse**

```python
    ps = sub.add_parser("status")
    ps.add_argument("--manifest", default="manifest.json")
```
And dispatch:
```python
    if args.cmd == "status":
        return cmd_status(args)
```

- [ ] **Step 5: Run selftest to verify it PASSES**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "feat(orchestrate): manifest status — direct-input + params staleness"
```

### Task 5: `render` — project manifest to human-readable EDIT.md

**Files:**
- Modify: `skills/video-edit-orchestrate/scripts/manifest.py`

**Interfaces:**
- Consumes: `load_manifest` (Task 2).
- Produces:
  - `render_edit_md(manifest: dict) -> str` → **pure** Markdown string: a source line, a per-stage table (stage | skill | status | decision | outputs), and the composite/join command block. No file I/O.
  - `cmd_render(args)` → write the string to `--out` (default `EDIT.md`).
  - CLI: `python manifest.py render [--manifest manifest.json] [--out EDIT.md]`.

- [ ] **Step 1: Extend selftest with render assertions**

Add to `selftest()` before `print("OK")`:

```python
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
```

- [ ] **Step 2: Run selftest to verify it FAILS**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `NameError: name 'render_edit_md' is not defined`.

- [ ] **Step 3: Implement `render_edit_md` and `cmd_render`**

Add to `manifest.py` after `cmd_status`:

```python
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
```

- [ ] **Step 4: Wire `render` into argparse**

```python
    pr = sub.add_parser("render")
    pr.add_argument("--manifest", default="manifest.json")
    pr.add_argument("--out", default="EDIT.md")
```
And dispatch:
```python
    if args.cmd == "render":
        return cmd_render(args)
```

- [ ] **Step 5: Run selftest to verify it PASSES**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "feat(orchestrate): manifest render — EDIT.md provenance view"
```

### Task 6: `manifest.example.json` — worked example

**Files:**
- Create: `skills/video-edit-orchestrate/manifest.example.json`

**Interfaces:**
- Consumes: the schema produced by `build_manifest` + `fold_stage` (Tasks 2–3).
- Produces: a reference file that must round-trip through `load_manifest` and `render_edit_md` without error.

- [ ] **Step 1: Write the example file**

Create `skills/video-edit-orchestrate/manifest.example.json` with a fully-populated "done" manifest (real-looking hashes, all three stages, `params_hash` present so `status` treats it as clean):

```json
{
  "version": 1,
  "source": {
    "path": "first_cut.mp4",
    "w": 640, "h": 298, "fps": 24.0, "dur_s": 1831.3,
    "hash": "sha256:3b1f...source"
  },
  "transcript": {
    "path": "work/selfcheck/cut_transcript.json",
    "hash": "sha256:9c2a...transcript"
  },
  "stages": {
    "captions": {
      "skill": "video-to-captions",
      "enabled": true,
      "workdir": "work/captions",
      "inputs": {
        "work/selfcheck/cut_transcript.json": "sha256:9c2a...transcript",
        "first_cut.mp4": "sha256:3b1f...source"
      },
      "params": { "max_chars": 14, "karaoke": true },
      "params_hash": "sha256:aa01...capparams",
      "decision": { "chunking": "approved", "name_fixes": { "social front": "Herschel Fruean" } },
      "outputs": { "work/captions/out/caption-overlay.mov": "sha256:c0de...cap" },
      "status": "done"
    },
    "remotion": {
      "skill": "video-to-remotion",
      "enabled": true,
      "workdir": "work/remotion",
      "inputs": {
        "work/selfcheck/cut_transcript.json": "sha256:9c2a...transcript",
        "first_cut.mp4": "sha256:3b1f...source"
      },
      "params": { "anchor": "top" },
      "params_hash": "sha256:bb02...remparams",
      "decision": { "kept_cues": ["intro", "lower-third@142", "stat@410", "outro"] },
      "outputs": { "work/remotion/out/graphics-overlay.mov": "sha256:f00d...gfx" },
      "status": "done"
    },
    "grade": {
      "skill": "video-color-grade",
      "enabled": true,
      "workdir": "work/grade",
      "inputs": { "first_cut.mp4": "sha256:3b1f...source" },
      "params": { "crf": 18, "preset": "medium" },
      "params_hash": "sha256:cc03...grdparams",
      "decision": { "look": "clean_neutral" },
      "outputs": {
        "work/grade/out/graded.mp4": "sha256:beef...graded",
        "work/grade/out/clean_neutral.cube": "sha256:1ce0...lut"
      },
      "status": "done"
    }
  },
  "final": {
    "composite_order": ["graded", "captions", "cards"],
    "outputs": { "final.mp4": "sha256:fina...final" },
    "status": "done"
  }
}
```

- [ ] **Step 2: Verify it round-trips through the tool**

Run:
```bash
python skills/video-edit-orchestrate/scripts/manifest.py render \
  --manifest skills/video-edit-orchestrate/manifest.example.json --out /tmp/EDIT.md
```
Expected: `[render] ... -> /tmp/EDIT.md`. Open `/tmp/EDIT.md`: source line, all three stages in the table with their decisions, join block. No traceback.

- [ ] **Step 3: Verify `status` reads it (hashes are fake, so all DIRTY — expected)**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py status --manifest skills/video-edit-orchestrate/manifest.example.json`
Expected: three lines, each `DIRTY: missing:...` (the referenced files don't exist here). This confirms `status` parses the example without crashing — the DIRTY is correct, not a failure.

- [ ] **Step 4: Commit**

```bash
git add skills/video-edit-orchestrate/manifest.example.json
git commit -m "docs(orchestrate): add worked manifest.example.json"
```

### Task 7: `SKILL.md` — the orchestrator playbook

**Files:**
- Create: `skills/video-edit-orchestrate/SKILL.md`

**Interfaces:**
- Consumes: `manifest.py` verbs (Tasks 1–5), the four skills' documented commands (read from their SKILL.md — do NOT modify them).
- Produces: the agent-facing playbook. No executable logic; prose + command blocks.

This is a prose deliverable — no test cycle. The "test" is Step 2's structural check. Write it in the repo's SKILL.md voice (imperative, decisive, Windows-aware), matching the four sibling skills. Read one sibling first (`skills/video-to-captions/SKILL.md`) to match tone and the frontmatter format.

- [ ] **Step 1: Write `skills/video-edit-orchestrate/SKILL.md`**

It MUST contain these sections, with this content:

1. **YAML frontmatter** — `name: video-edit-orchestrate` and a `description:` that triggers on "edit this video end to end", "run the full pipeline", "cut + caption + grade + graphics", 全流程剪辑, and states it orchestrates the four skills without replacing them. Follow the multi-line `>` description style of the sibling skills.

2. **The one idea** — "The manifest is the edit." One `manifest.json` is the DAG, the provenance doc, and the re-render recipe; the orchestrator only sequences the four skills' existing scripts.

3. **Dependency graph** — reproduce the §2 diagram from the spec (rough-cut serial root → captions/remotion/grade parallel → serial join). State the two safety properties verbatim: overlays contain no source pixels; grade preserves geometry.

4. **When to use / NOT** — use for a full multi-stage edit; NOT when you only want one skill (then call that skill directly), NOT a replacement for any of the four.

5. **Dependencies** — the four skills present; `ffprobe`; Python 3.12 (stdlib only for `manifest.py`); Node/Remotion for the two overlay branches (per those skills). Note transcript reuse: rough-cut's `work/selfcheck/cut_transcript.json` is the shared transcript both overlay branches consume — do not re-transcribe.

6. **Pipeline** — the numbered procedure:
   - **0. Rough-cut (serial root, skippable).** Run `video-rough-cut` per its SKILL.md, OR point at an existing `first_cut.mp4` + transcript. Then seed the manifest:
     ```
     python skills/video-edit-orchestrate/scripts/manifest.py init first_cut.mp4 \
       --enable captions,remotion,grade --out manifest.json
     ```
     Record the transcript path into the manifest's `transcript` block (hand-edit or a later `fold`). ANCHOR auto-sets to `top` when both overlay stages are enabled — do not ask the human.
   - **1. Fan out (one subagent per enabled branch).** Each branch works in its own `work/<branch>/` dir (§7 isolation — captions and remotion each scaffold a full Remotion project; never share a dir). Each runs its skill's **propose** phase, then writes `work/<branch>/stage.json` (params + input_paths + output_paths[so far] + `status:"proposed"` + its proposal) and EXITS.
   - **2. Per-branch gate.** For each branch that reports `proposed`, surface its decision (captions: chunking + name fixes; remotion: prune cues + copy; grade: pick look #, with the auto-injected "keep subtle — overlays sit on top" hint when any overlay stage is enabled). **Opportunistic coalescing:** if several gates are ready at once, present them together; never wait for all. Record each answer: `manifest.py fold --stage <b> --from work/<b>/stage.json`.
   - **Re-propose loop (bounded).** If the human rejects a proposal, re-run ONLY that branch's propose phase (max 3 rounds; then stop and ask how to proceed). Siblings keep going.
   - **3. Render (one subagent per approved branch, cap=1 heavy render).** Each runs its skill's **render** phase in its own dir, under a foreground/monitored process (never detached — §8 kill-mode a). Serialize the two Remotion renders (§8); grade's ffmpeg pass may overlap. Then `fold` the render outputs back.
   - **4. Join (serial).** See the Join section.
   - **5. Provenance.** `manifest.py render --out EDIT.md`, and `manifest.py status` to show what's current.

7. **Join** — reproduce the §6 command block (two single-overlay ffmpeg passes, captions then cards, `-c:a copy`). Include the **Windows note**: run ffmpeg from the file's folder / basename if any path-taking filter is used. Include the **OPEN item** verbatim as a "Before you build the join, decide:" note — prefer the single-ffmpeg two-overlay form (`[0][1]overlay[a];[a][2]overlay[v]`) if it reliably avoids the silent-drop bug ([[remotion-overlay-two-pass]]); fallbacks: two passes (document the extra H.264 generation) or lossless intermediate. If only one overlay is enabled, one pass.

8. **Compute cap** — the §8 rule in brief: one Remotion render saturates all cores; the two overlay renders serialize by default (`--max-render-concurrency=1`); keep renders in a monitored foreground job; VP8-alpha webm overlay fallback under disk pressure ([[remotion-overlay-vp8-alpha-disk]]).

9. **Self-check** — the §11 list: fan-out produced one `stage.json` per enabled branch; ANCHOR=top when both overlays on; a rejected proposal re-ran only its branch; **a still mid-video shows both captions (bottom) AND a card (top)** (catches the silent-overlay-drop + the ANCHOR-collision regression); `final.mp4` at source geometry; `manifest.py render` reproduces the run.

- [ ] **Step 2: Structural check**

Run: `grep -nE "^#|^## |manifest.py|overlay=|--enable|cut_transcript" skills/video-edit-orchestrate/SKILL.md`
Expected: hits for each required section heading, the four `manifest.py` verbs, the join `overlay=` command, the `init --enable` line, and the transcript-reuse mention. Confirm no `TODO`/`TBD` remains: `grep -niE "todo|tbd|fixme" skills/video-edit-orchestrate/SKILL.md` returns nothing except the deliberate quoted OPEN-item.

- [ ] **Step 3: Commit**

```bash
git add skills/video-edit-orchestrate/SKILL.md
git commit -m "docs(orchestrate): SKILL.md playbook — fan-out, per-branch gates, join, compute cap"
```

### Task 8: End-to-end manifest lifecycle test

**Files:**
- Modify: `skills/video-edit-orchestrate/scripts/manifest.py` (extend `selftest` with one lifecycle assertion block)

**Interfaces:**
- Consumes: `build_manifest`, `fold_stage`, `stage_dirty`, `render_edit_md`, `save_manifest`, `load_manifest` (Tasks 2–5).
- Produces: proof the verbs compose — init → fold → status(clean) → mutate → status(dirty) → render.

This is the "money path" integration check the spec (§11) calls for: the full staleness-propagation lifecycle in one runnable block, using a tempdir and real files so the disk-hashing path is exercised (not just injected fakes).

- [ ] **Step 1: Add the lifecycle block to selftest**

Add to `selftest()` before `print("OK")`. Add `import tempfile, os` if not already imported (Task 2 added them):

```python
    # --- Task 8: end-to-end lifecycle on real temp files ---
    with tempfile.TemporaryDirectory() as d:
        cut = os.path.join(d, "first_cut.mp4")
        tr = os.path.join(d, "cut_transcript.json")
        cap = os.path.join(d, "caption-overlay.mov")
        for p, b in [(cut, b"CUT"), (tr, b"TRANS"), (cap, b"CAPMOV")]:
            open(p, "wb").write(b)
        srcx = {"path": cut, "w": 640, "h": 298, "fps": 24.0,
                "dur_s": 10.0, "hash": hash_file(cut)}
        man = build_manifest(srcx, ["captions", "remotion", "grade"])
        # fold captions with real files -> hashes come from disk
        man = fold_stage(man, "captions", {
            "params": {"max_chars": 14, "karaoke": True},
            "decision": {"chunking": "approved"},
            "input_paths": [tr, cut], "output_paths": [cap], "status": "done"})
        assert stage_dirty(man["stages"]["captions"]) == []      # clean right after fold
        # mutate an input file -> captions goes dirty, siblings still pending-clean
        open(tr, "wb").write(b"TRANS-EDITED")
        reasons = stage_dirty(man["stages"]["captions"])
        assert reasons == [f"changed:{tr}"], reasons
        assert stage_dirty(man["stages"]["grade"]) == []         # grade untouched
        # params drift -> dirty
        man["stages"]["captions"]["params"] = {"max_chars": 20, "karaoke": True}
        assert "params" in stage_dirty(man["stages"]["captions"])
        # manifest round-trips through disk and renders
        mp = os.path.join(d, "manifest.json")
        save_manifest(man, mp)
        assert load_manifest(mp)["stages"]["captions"]["decision"]["chunking"] == "approved"
        assert "video-to-captions" in render_edit_md(load_manifest(mp))
```

- [ ] **Step 2: Run selftest to verify it PASSES**

Run: `python skills/video-edit-orchestrate/scripts/manifest.py selftest`
Expected: `OK`, exit 0. (If `reasons` asserts fire, the message prints the actual list — fix `stage_dirty` path handling.)

- [ ] **Step 3: Full manual walk-through against the example**

```bash
python skills/video-edit-orchestrate/scripts/manifest.py render \
  --manifest skills/video-edit-orchestrate/manifest.example.json --out /tmp/EDIT.md
python skills/video-edit-orchestrate/scripts/manifest.py status \
  --manifest skills/video-edit-orchestrate/manifest.example.json
```
Expected: render writes `/tmp/EDIT.md`; status prints three DIRTY lines (files absent). No traceback from either.

- [ ] **Step 4: Commit**

```bash
git add skills/video-edit-orchestrate/scripts/manifest.py
git commit -m "test(orchestrate): end-to-end manifest lifecycle in selftest"
```

---

## Notes for the implementer

- **Do not touch the four skills.** Every stage command in `SKILL.md` is copied from a sibling skill's own SKILL.md; if one looks wrong, re-read that sibling — do not edit it.
- **`manifest.py` is stdlib-only.** If you reach for a third-party import, stop — the design forbids it.
- **The OPEN join question (Task 7 §Join / spec §6)** is the one thing left to decide during build. Resolve it by testing the single-ffmpeg two-overlay form on a real pair of overlays and checking a mid-video still shows BOTH layers. Record the decision in `SKILL.md` (replace the "Before you build" note with the chosen form).
- **Windows:** run every path-taking ffmpeg filter from the file's folder using basenames (repo-wide rule). `manifest.py` only calls `ffprobe`, which is unaffected.

