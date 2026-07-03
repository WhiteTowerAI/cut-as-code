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

1. **Parallelize where it actually pays — the propose wave.** The three post-cut stages'
   propose phases are LLM/network-bound (read the transcript, write card copy, fix ASR-mangled
   names, vision-judge the looks sheet), **not** CPU-bound — so running them as concurrent
   subagents is contention-free and collapses ~20–35 min of serial agent work to the longest
   single branch. The CPU-bound renders are the opposite case (§8): one Remotion render already
   saturates every core, so the two overlay renders **serialize by default** — grade's cheap
   ffmpeg pass overlaps them, but two headless-Chromium renders do not fly on one box. Net:
   a real parallel saving in the propose wave + one grade overlap; **not** a render-wave speedup.
2. **Independent per-branch gates, with the false cross-cuts removed** (§4). A co-equal
   payoff, not a side effect: ANCHOR collision and grade subtlety are auto-settled from the
   enabled-set (no human call), leaving three genuinely independent decisions; each branch
   advances on its own gate and a rejected proposal re-runs only that branch. Opportunistic
   coalescing recovers the "decide several in one sitting / step away" ergonomic without
   holding a fast branch hostage to the slowest proposer.
3. **Introduce the edit manifest** — one `manifest.json` that is simultaneously the
   provenance document, the re-render recipe, and the dependency graph the orchestrator
   walks. This is the "documentation for future reference / further editing" the repo lacks.
4. **Do not modify the four skills.** The orchestrator calls their existing scripts in
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
| **`video-edit-orchestrate/SKILL.md`** | The playbook. Holds, per stage, the propose-phase and render-phase command lists (copied from each skill's documented steps), the fan-out procedure, the per-branch gate + bounded re-propose loop, ANCHOR auto-settle rule, and the join. Agent-driven. | the 4 skills, `manifest.py` |
| **`scripts/manifest.py`** | The only real new code (small). Three verbs: `init` (probe source → seed manifest), `fold` (merge a branch's `stage.json` into `manifest.json`), `status` (hash current files vs recorded inputs → print staleness). Plus `render` → `EDIT.md`. | ffprobe |
| **`manifest.json`** | Source of truth: the edit doc + the DAG + the re-render recipe. **Orchestrator is its only writer.** | — |
| **`EDIT.md`** | Human-readable view generated from the manifest (`manifest.py render`). Never hand-edited. | manifest.json |
| **per-branch `work/<branch>/stage.json`** | A branch subagent's private output slot: its proposal, params, artifact paths+hashes, status. Avoids concurrent writes to the manifest. | — |
| **the 4 existing skills** | **Unchanged.** Their scripts are invoked; their SKILL.md stays authoritative for *how* each script works. | — |

The orchestrator sequences and merges; it never reimplements a skill. That is what keeps
this an "orchestrator skill" and not the make-style job-runner that was considered and
rejected.

## 4. Control flow — per-branch pipelines, one serial root, one serial join

Each of the four skills already splits into a **propose** phase and a **render** phase with
the human gate sitting exactly on the seam — this is not invented, it is how the skills are
written:

| Skill | propose phase (ends at the gate) | the gate (human) | render phase |
|---|---|---|---|
| color-grade | `assess.py` → `render_looks.py` → contact sheet | "present + STOP", pick a look # | `bake_lut.py` → `apply_grade.py --name CHOSEN` |
| remotion | `analyze_content.py` → `draft_cues.py` | prune cues, write copy | render overlay |
| captions | `build_captions.py` → read `.srt` | approve chunking, fix ASR names | render overlay |
| (rough-cut) | `transcribe.py`→`analyze.py`→`inspect_bounds.py` | hand-write `edit_coarse.json` | `build_edit`→`assign_speed`→`cut_render` |

Each post-cut stage is an **independent pipeline** — propose → its own gate → render —
fanned out after the serial root and rejoined at the serial composite. A branch advances the
moment *its* gate clears; it never waits on a sibling.

```
STAGE 0  rough-cut   [serial root; own gate: hand-write edit_coarse.json]
         → first_cut.mp4, transcript.json, cut_transcript.json  (folded into manifest)
                    │
   ┌────────────────┼─────────────────┐   fan out — one independent pipeline per enabled stage
   ▼                ▼                 ▼
 captions         remotion           grade
 propose:         propose:           propose:
  build_captions   analyze+draft      assess+render_looks
  → .srt           → cues draft       → looks_compare.png
   │ GATE:          │ GATE:            │ GATE:
   │ chunking ok?   │ pruning ok?      │ pick look #
   │ name fixes     │ copy ok?         │ (auto-hint: keep
   │                │                  │  subtle — overlays
   │ [reject →      │ [reject →        │  land on top)
   │  re-propose]   │  re-propose]     │ [reject → re-propose]
   ▼                ▼                 ▼
 render:          render:            render:
  caption-         graphics-          apply_grade
  overlay.mov      overlay.mov        → graded.mp4
   └────────────────┼─────────────────┘
                    ▼
              JOIN [serial; waits for every enabled branch]
              two single-overlay ffmpeg passes (§6) → final.mp4 → self-check
```

Each stage is **stateless end to end**: the propose-subagent runs its scripts, writes
`work/<branch>/stage.json`, and **exits**; the orchestrator surfaces that branch's gate,
records the answer into the manifest, then spawns a **fresh** render-subagent that reads the
manifest and renders. No subagent ever stays alive holding an open question — the handoff is
always a file. (This is why per-branch is *no harder to build* than batch: both hand off
through files, neither needs a long-lived blocked agent. An earlier draft claimed per-branch
required that live-blocked agent — it does not.)

**ANCHOR is auto-settled, never asked.** Captions are inherently bottom (the reading
safe-zone); cards must clear them. So *whenever both captions and remotion are enabled*, the
orchestrator sets `remotion.params.anchor = "top"` at manifest-init — the skills' own
"combining" sections mandate exactly this rule. It is not a line item on any gate. (The value
lives in the manifest, so an operator can still override it there; they are simply not asked.)
With cards disabled, ANCHOR stays at its `bottom` default — no collision to settle.

**Grade's "keep it subtle" is an auto-injected hint, not a cross-stage decision.** Whether
overlays will sit on top is known from the *enabled-set* at init, not from the caption/card
*proposal content* — so when any overlay stage is enabled, the orchestrator surfaces that
advisory at grade's own gate. The human still picks the look; they need not see the other
branches' proposals to pick well.

**A rejected proposal re-runs only that branch's propose phase** — a bounded loop (default 3
rounds, then the orchestrator asks how to proceed). Siblings are unaffected: an approved grade
can be rendering while remotion re-proposes. This is the redo path the two-wave model had no
slot for; per-branch treats it as the normal case.

**Opportunistic coalescing (ergonomics, not a third model).** If more than one branch's gate
is ready when the operator engages, the orchestrator presents them together — recovering
batch's "decide several in one sitting / step away" feel *without* holding a fast branch's
gate hostage to the slowest proposer. It is strictly "show all currently-ready gates," never
"wait until all are ready."

**Every stage is opt-in.** The manifest lists only enabled stages; the orchestrator fans out
whatever is present. captions + grade with no cards is a valid two-branch run.

Stage 0 is the serial root (everything downstream needs the cut + transcript) and is
**skippable**: point the manifest at an existing `first_cut.mp4` + transcript and the fan-out
starts immediately. The JOIN is the serial reduce — it waits for every enabled branch's render.

### Why per-branch (the settled decision)

Batch (propose-wave → one gate → render-wave) was designed first; two findings flipped it:

1. **The decisions do not actually interact.** Both apparent cross-cuts dissolve: ANCHOR is
   auto-settled from the enabled-set, and grade's "subtle" is an auto-injected hint from the
   enabled-set — neither needs one branch's *proposal content* to answer another's gate. What
   remains are three genuinely independent judgment calls (chunking / pruning+copy / look).
2. **Rejection is first-class.** Remotion's propose does the skill's core creative work (prune
   ~20 opportunities to ~6, write editorial copy); "redo this branch" is a normal outcome, not
   an exception. Per-branch loops that one branch while siblings proceed; batch would either
   stall approved branches waiting on the re-proposal or silently degrade into per-branch timing.

Per-branch is also **not harder to build** (equal statelessness, above) and **not slower** —
the render cap (§8) serializes the heavy renders either way, and per-branch lets a fast branch
(grade) finish while a slow one (remotion copy) is still proposing. Batch's only real edge —
"one sitting, walk away" — is recovered by opportunistic coalescing.

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

`status` (§9) hashes each stage's `inputs` **and** its `params` block, so a params-only edit
(e.g. caption chunking) is caught without any file changing. `decision` is provenance, not a
staleness input — it records *what the human chose*, and re-running a stage on a new decision
is an explicit agent action, not something `status` needs to detect.

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

Captions stay bottom-anchored; cards are auto-re-anchored to top (§4, set at manifest-init
whenever both overlay stages are enabled) so the two layers do not overlap. If only one
overlay stage is enabled, the join is a single pass and ANCHOR stays at its `bottom` default.

## 7. Isolation — subdirs, not worktrees

captions and remotion are **both full Remotion projects** — each scaffolds `package.json`,
`src/`, `public/source.mp4`. Run in one directory they clobber each other. Each branch gets
its own working dir (`work/captions/`, `work/remotion/`, `work/grade/`), which is enough for
safe parallel fan-out. Grade is pure Python + ffmpeg and needs no project scaffold. Git
worktrees would add a per-branch `npm install` and disk cost for no isolation benefit over
subdirs here. `// ponytail: subdir isolation; worktrees buy nothing extra for this`

## 8. Compute cap — why the renders serialize (cap=1 is technical, not timid)

**A single Remotion render already saturates the machine.** Its `--concurrency` default fans
frame rendering across N headless-Chrome workers = all cores. So a second simultaneous render
finds **no idle capacity**: it time-slices the same cores across 2× the work (a wash in
core-seconds at best) while **doubling peak RAM** — two Chrome worker pools + two ProRes-4444
alpha streams (a full alpha frame every frame, multiple GB each). That memory blow-up is a real
OOM failure mode, so two-in-parallel is typically *worse* than sequential, not faster. Default
policy: **grade's single cheap ffmpeg pass overlaps the renders freely, but the two Remotion
overlay renders serialize** unless `--max-render-concurrency` is raised (meaningful only on
multiple machines, or a render deliberately run at low `--concurrency` with core headroom).

**Two distinct kill modes — don't conflate them.** The improvement report shows both:
(a) **session-idle reaping** of *detached* background renders — a process-supervision problem,
fixed by keeping every render in a **monitored foreground job** that emits progress; orthogonal
to concurrency. (b) **resource exhaustion** — the one that two-in-parallel worsens. cap=1 targets
(b); the foreground-job rule targets (a).

**The lever that does exist on one box** is not "run both at once" but: tune a single render's
`--concurrency`, and use the VP8-alpha webm overlay path (§below) to cut the RAM/disk that
kills renders. Asymmetric weight is worth noting but not promising — the captions overlay is
*dense* (full-frame alpha every frame), the graphics overlay is *sparse* (mostly empty alpha,
lighter); the sparse one might fit under the dense one's headroom, but that needs measuring
before the cap is raised.
`// ponytail: one render already = all cores; cap=1 avoids an OOM, not a speedup`

**Disk fallback:** the transparent overlays are large deletable intermediates (a full alpha
frame every frame — multiple GB). Delete each `.mov` after the join. Under disk pressure,
render overlays as VP8-alpha webm instead of ProRes 4444 (~100× smaller, same quality) per
[[remotion-overlay-vp8-alpha-disk]].

## 9. Failure & re-edit handling

- **A failed branch is isolated.** It writes `status:"failed"` + the error into its
  `stage.json`; the orchestrator folds that in but does not overwrite siblings' good outputs.
  Re-running that one branch reuses its recorded inputs.
- **Direct-input staleness only — reported, not auto-rebuilt.** `manifest.py status` marks a
  stage dirty when any of *its own recorded direct inputs* changed: an input **file** whose
  hash differs, or a changed `params` value (params are hashed alongside the input files — a
  cheap per-stage check, not a graph walk). Examples that hold under this rule: regenerate the
  cut → `first_cut.mp4` / `cut_transcript.json` hashes change → captions, remotion, grade all
  flag dirty **because those files are their recorded direct inputs**; change only caption
  chunking (a `param`) → captions dirty, others clean. The **agent** decides what to re-run
  from that report.
- **Deliberate limit (no transitive walk).** `status` does **not** trace an edit back through a
  stage's *internals*. Rough-cut is the serial root, not a manifest stage (its outputs live in
  top-level `source`/`transcript`, §5), so editing its internal `edit_coarse.json` is invisible
  to `status` until you re-run rough-cut — at which point the changed `first_cut.mp4` /
  `cut_transcript.json` hashes make the downstream stages flag dirty through the normal
  direct-input check above. Modelling rough-cut as a stage and propagating dirtiness upstream→
  downstream would be a true dependency graph — i.e. the make-style engine this design lists as
  a non-goal (§1). We stay one level shy of it on purpose.
  `// ponytail: direct-input + params dirty check; re-run rough-cut yourself, no make graph`

## 10. Files created

| File | Change |
|---|---|
| `skills/video-edit-orchestrate/SKILL.md` | **New.** Playbook: dependency graph, per-stage propose/render command lists, fan-out procedure, per-branch gate + bounded re-propose loop, ANCHOR auto-settle rule, two-pass join, self-check, opt-in/skip rules, compute cap. |
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
- **Dry-run orchestration:** on a short clip, confirm the fan-out produces one `stage.json`
  per enabled branch, each branch's gate surfaces its own decision, ANCHOR auto-sets to `top`
  when both overlay stages are on, a rejected proposal re-runs only that branch (bounded loop),
  the render artifacts land in isolated dirs, and the two-pass join yields `final.mp4` at
  source geometry.
- **Join correctness:** a still mid-video shows **both** captions (bottom) and a card (top) —
  the check that catches the silent-overlay-drop regression.
- **Provenance round-trip:** `manifest.py render` yields an `EDIT.md` whose commands + decisions
  reproduce the run.

## 12. Risks

- **Low:** the manifest schema and `init/fold/status` are straightforward JSON + hashing.
- **Medium:** the parallel win is real but *located* — the LLM-bound propose wave (§1,
  contention-free) plus one grade overlap — **not** the CPU-bound render wave, which serializes
  by default (§8). The skill must sell "faster decisions + full provenance + a propose-wave
  saving," never a render-wave "3× faster" it can't deliver on one machine.
- **Low–medium:** the former cross-cutting decisions are now auto-settled (ANCHOR from the
  enabled-set; grade "subtle" as an auto-injected hint), so the operator can't forget them —
  but the auto-settle rules must be correct and documented in SKILL.md. The residual risk is a
  wrong *auto* rule (e.g. ANCHOR not flipping), caught by the join self-check (a still showing
  captions bottom + card top).
- **Low:** per-branch adds a bounded re-propose loop; if a proposal is rejected >3 rounds the
  orchestrator must stop and ask rather than loop forever (explicit cap in SKILL.md).

## 13. Open confirmation points

1. Manifest form: **`manifest.json` + generated `EDIT.md`** (recommended) vs JSON-only.
2. Default `--max-render-concurrency` = 1 heavy Remotion render (grade runs alongside). OK?
3. Spec language: written in English (this conversation); the existing repo spec is Chinese.
   Keep English, or match the repo convention?
