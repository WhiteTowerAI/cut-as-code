# video-edit-orchestrate — parallel pipeline + edit manifest — design

- Date: 2026-07-03
- Status: awaiting review (pre-implementation)
- Scope: new skill `skills/video-edit-orchestrate/`; the 4 existing video skills are **not modified**
- Related memory: [[remotion-overlay-two-pass]], [[remotion-overlay-vp8-alpha-disk]]

## 1. Background & goals

Today the four video skills run **sequentially and by hand**. A full edit is:
`video-rough-cut → video-to-captions → video-to-remotion`, then `video-color-grade`
on the same material (the ordering the 2026-06-26 improvement report ran and documents).
Nothing coordinates them, and two facts about that manual flow are wasteful:

1. **The three post-cut stages are independent but run serially.** captions, remotion,
   and grade each consume the rough cut and each other's outputs never — yet an operator
   runs them one after another, and re-transcribes in each.
2. **No file records what was done.** Intermediates scatter across each skill's `work/`
   (`edit_final.json`, `captions.srt`, `cues.json`, `looks.json`). A finished `final.mp4`
   is not tied back to its source, its per-stage decisions, or the commands that made it.
   Re-editing a month later means reverse-engineering four `work/` dirs.

**Goals (priority order):**

1. **Parallelize the independent stages** behind one agent-driven orchestrator, with a
   single batched human-decision point instead of three scattered ones.
2. **Introduce the edit manifest** — one `manifest.json` that is simultaneously the
   provenance document, the re-render recipe, and the dependency graph the orchestrator
   walks. This is the "documentation for future reference / further editing" the repo lacks.
3. **Do not modify the four skills.** The orchestrator calls their existing scripts in
   their existing documented order; their SKILL.md files stay the source of truth.

**Non-goals:** no make-style auto-rebuild engine (staleness is *reported*, the agent
decides); no lock manager; no git-worktree isolation (subdirs suffice — see §7); no
propose/render "modes" added inside the four skills (the orchestrator knows the split
points); no new transcription/analysis logic.

## 2. The dependency graph (the core insight)

Reading the four SKILL.md files, the true data dependencies are:

```
video-rough-cut  [SERIAL ROOT]
  produces: first_cut.mp4  +  work/transcript.json  +  work/selfcheck/cut_transcript.json
      │
      │  (captions & remotion dress the CUT; grade grades the CUT — nothing fans out until it exists)
      ▼
  ┌───────────────┬──────────────────┬──────────────────┐
  ▼               ▼                  ▼
captions        remotion           grade
consumes:       consumes:          consumes:
 cut_transcript  cut_transcript     first_cut.mp4 (footage only)
 first_cut.mp4   first_cut.mp4
produces:       produces:          produces:
 caption-        graphics-          graded.mp4
 overlay.mov     overlay.mov        (footage, graded, no overlays)
  └───────────────┴──────────────────┴──────────────────┘
                          │  (JOIN — the only cross-stage dependency)
                          ▼
              final composite → final.mp4 → self-check
```

Two properties make the fan-out **safe**, and the design rests on both:

- **The overlays contain no source pixels.** captions → transparent ProRes with captions
  only; remotion → transparent ProRes with cards only. Neither consumes the other; neither
  consumes the grade. They are sized to the source geometry (`probe.py` → `source-meta.json`)
  purely to align to the pixel grid.
- **Grade preserves geometry.** `video-color-grade`'s contract keeps duration/fps/dimensions
  unchanged and copies audio (`-c:a copy`). So overlays built against the source geometry
  drop cleanly onto `graded.mp4` even though grade ran on a separate branch. This is also the
  improvement-report E1 rule: grade the *clean* cut, composite overlays *on top* — never grade
  after burn-in.

So the shape is a classic **3 independent producers → 1 reduce**. The reduce (final
composite) is the sole join.

**Transcript reuse is a real graph edge, not a nicety.** Rough-cut's self-check emits
`work/selfcheck/cut_transcript.json` — a word-level transcript of the exact cut. captions
and remotion both explicitly say to reuse it and skip their own ~15–20 min CPU
transcription. The manifest records it as a stage-0 output that both branches consume.

## 3. Architecture — a thin sequencer, not an engine

Six units. Only one is meaningfully new code.

| Unit | What it is / does | Depends on |
|---|---|---|
| **`video-edit-orchestrate/SKILL.md`** | The playbook. Holds, per stage, the propose-phase and render-phase command lists (copied from each skill's documented steps), the fan-out procedure, the batch-gate procedure, and the join. Agent-driven. | the 4 skills, `manifest.py` |
| **`scripts/manifest.py`** | The only real new code (small). Three verbs: `init` (probe source → seed manifest), `fold` (merge a branch's `stage.json` into `manifest.json`), `status` (hash current files vs recorded inputs → print staleness). Plus `render` → `EDIT.md`. | ffprobe |
| **`manifest.json`** | Source of truth: the edit doc + the DAG + the re-render recipe. **Orchestrator is its only writer.** | — |
| **`EDIT.md`** | Human-readable view generated from the manifest (`manifest.py render`). Never hand-edited. | manifest.json |
| **per-branch `work/<branch>/stage.json`** | A branch subagent's private output slot: its proposal, params, artifact paths+hashes, status. Avoids concurrent writes to the manifest. | — |
| **the 4 existing skills** | **Unchanged.** Their scripts are invoked; their SKILL.md stays authoritative for *how* each script works. | — |

The orchestrator sequences and merges; it never reimplements a skill. That is what keeps
this an "orchestrator skill" and not the make-style job-runner that was considered and
rejected.

## 4. Control flow — two waves around one gate

Each of the four skills already splits into a **propose** phase and a **render** phase with
the human gate sitting exactly on the seam — this is not invented, it is how the skills are
written:

| Skill | propose phase (ends at the gate) | the gate (human) | render phase |
|---|---|---|---|
| color-grade | `assess.py` → `render_looks.py` → contact sheet | "present + STOP", pick a look # | `bake_lut.py` → `apply_grade.py --name CHOSEN` |
| remotion | `analyze_content.py` → `draft_cues.py` | prune cues, write copy, set ANCHOR | render overlay |
| captions | `build_captions.py` → read `.srt` | approve chunking, fix ASR names | render overlay |
| (rough-cut) | `transcribe.py`→`analyze.py`→`inspect_bounds.py` | hand-write `edit_coarse.json` | `build_edit`→`assign_speed`→`cut_render` |

Flow:

```
STAGE 0  rough-cut   [serial root; its own gate: hand-write edit_coarse.json]
         → first_cut.mp4, transcript.json, cut_transcript.json  (folded into manifest)
                    │
   ┌────────────────┼────────────────┐   WAVE 1 — propose (parallel subagents, one per branch)
   ▼                ▼                ▼
 captions        remotion          grade
 build_captions  analyze+draft     assess+render_looks
 → .srt          → cues draft      → looks_compare.png
   └── each writes work/<branch>/stage.json (proposal + artifacts), EXITS ──┘
                    │
              ╔═════▼═════╗  BATCH GATE — orchestrator reads all 3 stage.json, presents ONE table:
              ║  human    ║   • captions: chunking OK? name fixes?
              ║  decides  ║   • remotion: which cues, copy, ANCHOR = top|bottom?
              ║  once     ║   • grade: pick look #
              ╚═════╤═════╝   • cross-cut: captions+cards both bottom-anchored → collide;
                    │            if shipping both, set cards ANCHOR="top". Keep grade look
                    │            subtle (overlays sit on top of it).
              records decisions → manifest.json (orchestrator is sole writer)
   ┌────────────────┼────────────────┐   WAVE 2 — render (parallel subagents, concurrency-capped §8)
   ▼                ▼                ▼
 caption-        graphics-        graded.mp4
 overlay.mov     overlay.mov      (apply_grade)
   └────────────────┼────────────────┘
                    ▼
              JOIN [serial] — two single-overlay ffmpeg passes (§6) → final.mp4 → self-check
```

Stage 0 is serial because everything downstream needs the cut and the transcript. It is
also **skippable**: if the operator already has `first_cut.mp4` + a transcript, the manifest
is pointed at them and Wave 1 starts immediately.

**Every stage is opt-in.** The manifest lists only enabled stages; the orchestrator fans
out whatever is present. captions + grade with no cards is a valid two-branch run.

### Why batch (the settled decision)

Raw scheduling favors per-branch gates slightly (`max_i(propose_i+render_i)` ≤
`max_i propose + max_i render`). Batch was chosen anyway for two reasons that outweigh a
wash on wall-clock:

1. **The human is a serial, often-AFK resource.** Batching = one decision sitting, step
   away between waves; per-branch = three unpredictable interrupts, and a branch blocks if
   you are away when its gate arrives.
2. **The decisions interact.** captions and cards collide (both bottom-anchored); grade must
   stay subtle *because* overlays land on top. Deciding these blind, per-branch, invites
   rework (e.g. re-render cards after seeing the grade). One table decides them coherently.

Batch is also the **simpler, more robust build**: propose-subagents and render-subagents are
stateless and short-lived, handing off through files. Per-branch would need a subagent to
stay alive and blocked mid-skill holding a round-trip question — exactly the long-lived job
the improvement report notes gets reaped when a session idles.

## 5. The manifest (the interface everything talks through)

```jsonc
{
  "version": 1,
  "source": {
    "path": "first_cut.mp4",
    "w": 640, "h": 298, "fps": 24, "dur_s": 1831.3,
    "hash": "sha256:…"
  },
  "transcript": { "path": "work/selfcheck/cut_transcript.json", "hash": "sha256:…" },
  "stages": {
    "captions": {
      "skill": "video-to-captions",
      "enabled": true,
      "workdir": "work/captions",
      "inputs":   { "cut_transcript.json": "sha256:…", "first_cut.mp4": "sha256:…" },
      "params":   { "max_chars": 14, "karaoke": true },
      "decision": { "chunking": "approved",
                    "name_fixes": { "social front": "Herschel Fruean" } },
      "outputs":  { "caption-overlay.mov": "sha256:…" },
      "status": "done"
    },
    "remotion": {
      "skill": "video-to-remotion", "enabled": true, "workdir": "work/remotion",
      "inputs":  { "cut_transcript.json": "sha256:…", "first_cut.mp4": "sha256:…" },
      "params":  { "anchor": "top" },
      "decision": { "kept_cues": ["intro", "lower-third@142", "stat@410", "outro"] },
      "outputs": { "graphics-overlay.mov": "sha256:…" },
      "status": "done"
    },
    "grade": {
      "skill": "video-color-grade", "enabled": true, "workdir": "work/grade",
      "inputs":  { "first_cut.mp4": "sha256:…" },
      "params":  { "crf": 18, "preset": "medium" },
      "decision": { "look": "clean_neutral" },
      "outputs": { "graded.mp4": "sha256:…", "clean_neutral.cube": "sha256:…" },
      "status": "done"
    }
  },
  "final": {
    "composite_order": ["graded", "captions", "cards"],
    "outputs": { "final.mp4": "sha256:…" },
    "status": "done"
  }
}
```

This single object is all three of: the missing edit-doc (decisions + params inline, per
stage), the re-render recipe (inputs + params reproduce any stage), and the DAG the
orchestrator walks. `EDIT.md` is its human projection — a table of source → each stage's
decisions/params/outputs + the composite command — regenerated, never hand-edited.

## 6. The join — two single-overlay passes, not one 3-way chain

The final composite layers `graded.mp4` (base) + `caption-overlay.mov` + `graphics-overlay.mov`.
Per [[remotion-overlay-two-pass]], a chained 3-input `overlay` filter can **silently drop the
second overlay**. The join therefore runs **two sequential single-overlay passes** (captions
onto graded, then cards onto that), copying audio each time:

```
# pass 1: captions onto graded footage
ffmpeg -y -i out/graded.mp4 -i work/captions/caption-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy work/_capped.mp4
# pass 2: cards onto that
ffmpeg -y -i work/_capped.mp4 -i work/remotion/graphics-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy -movflags +faststart out/final.mp4
```

Captions stay bottom-anchored; cards are re-anchored to top (the gate decision) so the two
layers do not overlap. If only one overlay stage is enabled, the join is a single pass.

## 7. Isolation — subdirs, not worktrees

captions and remotion are **both full Remotion projects** — each scaffolds `package.json`,
`src/`, `public/source.mp4`. Run in one directory they clobber each other. Each branch gets
its own working dir (`work/captions/`, `work/remotion/`, `work/grade/`), which is enough for
safe parallel fan-out. Grade is pure Python + ffmpeg and needs no project scaffold. Git
worktrees would add a per-branch `npm install` and disk cost for no isolation benefit over
subdirs here. `// ponytail: subdir isolation; worktrees buy nothing extra for this`

## 8. Compute cap — the honest ceiling

Two headless-Chromium Remotion overlay renders at ~40k frames are heavy; the improvement
report records such renders being reaped. So "parallel renders" is partly aspirational on one
machine. Default policy: **grade's single cheap ffmpeg pass runs alongside the renders freely,
but the two Remotion overlay renders serialize against each other** unless a
`--max-render-concurrency` knob is raised. Renders run under a foreground/monitoring process
that emits progress (never detached fire-and-forget, which gets reaped when the session idles).
`// ponytail: cap=1 heavy render by default; expose the knob, don't pretend 2 fit`

**Disk fallback:** the transparent overlays are large deletable intermediates (a full alpha
frame every frame — multiple GB). Delete each `.mov` after the join. Under disk pressure,
render overlays as VP8-alpha webm instead of ProRes 4444 (~100× smaller, same quality) per
[[remotion-overlay-vp8-alpha-disk]].

## 9. Failure & re-edit handling

- **A failed branch is isolated.** It writes `status:"failed"` + the error into its
  `stage.json`; the orchestrator folds that in but does not overwrite siblings' good outputs.
  Re-running that one branch reuses its recorded inputs.
- **Staleness is reported, not auto-rebuilt.** `manifest.py status` hashes current files
  against recorded `inputs` and prints what is dirty: change `edit_coarse.json` → transcript
  changes → captions + remotion + grade all stale; change only caption chunking → captions
  only. The **agent** decides what to re-run from that report. Recording hashes is what makes
  the manifest useful for iterative re-editing; the decision engine stays the agent.
  `// ponytail: report staleness; agent rebuilds — not a make graph`

## 10. Files created

| File | Change |
|---|---|
| `skills/video-edit-orchestrate/SKILL.md` | **New.** Playbook: dependency graph, per-stage propose/render command lists, fan-out procedure, batch-gate procedure, two-pass join, self-check, opt-in/skip rules, compute cap. |
| `skills/video-edit-orchestrate/scripts/manifest.py` | **New.** `init` / `fold` / `status` / `render` (→ `EDIT.md`). Small; ffprobe for source probe, hashlib for staleness. |
| `skills/video-edit-orchestrate/manifest.example.json` | **New.** A worked manifest (like the repo's `looks.example.json` / `overlays.example.json`). |
| the 4 existing skills | **Unchanged.** |

## 11. Testing & self-check

No test framework in-repo; follow the repo's "run it + verify artifacts" convention plus one
runnable check on the only non-trivial new logic:

- **`manifest.py` self-check** (`__main__`, assert-based): `init` a manifest from a tiny probe
  fixture; `fold` a fake `stage.json`; assert the stage lands with its hashes; mutate a file
  and assert `status` flags exactly the dependent stages dirty. This is the money path (hashing
  + dependency propagation), so it gets the one test. `// ponytail: one self-check on the DAG logic`
- **Dry-run orchestration:** on a short clip, confirm Wave 1 produces three `stage.json`, the
  gate table lists all three decisions, Wave 2 produces the three artifacts in isolated dirs,
  and the two-pass join yields `final.mp4` at source geometry.
- **Join correctness:** a still mid-video shows **both** captions (bottom) and a card (top) —
  the check that catches the silent-overlay-drop regression.
- **Provenance round-trip:** `manifest.py render` yields an `EDIT.md` whose commands + decisions
  reproduce the run.

## 12. Risks

- **Low:** the manifest schema and `init/fold/status` are straightforward JSON + hashing.
- **Medium:** real parallel speedup is capped by render contention (§8) — the win is as much
  "one coherent decision point + full provenance" as raw wall-clock. Stated honestly so the
  skill does not over-promise "3× faster".
- **Medium:** the batch gate's cross-cutting advice (anchor collision, subtle grade) must be
  spelled out in SKILL.md or an operator picks a heavy look and re-renders cards. Mitigated by
  making it an explicit line item on the gate table.

## 13. Open confirmation points

1. Manifest form: **`manifest.json` + generated `EDIT.md`** (recommended) vs JSON-only.
2. Default `--max-render-concurrency` = 1 heavy Remotion render (grade runs alongside). OK?
3. Spec language: written in English (this conversation); the existing repo spec is Chinese.
   Keep English, or match the repo convention?
