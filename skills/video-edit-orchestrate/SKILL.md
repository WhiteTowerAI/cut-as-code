---
name: video-edit-orchestrate
description: >
  Run a full multi-stage video edit end to end by orchestrating the four existing
  skills — video-rough-cut (the serial root), then video-to-captions,
  video-to-remotion, and video-color-grade fanned out in parallel around a single
  manifest.json, then joined into one deliverable. The manifest.json is the edit doc:
  the dependency graph, the provenance record (what each stage decided, which files it
  hashed), and the re-render recipe all at once. This skill NEVER reimplements the four
  skills — it sequences their existing scripts and folds each branch's result into the
  manifest. Use when asked to "edit this video end to end", "run the full pipeline",
  "cut + caption + grade + graphics", "do the whole edit and keep a record so I can
  re-render", 全流程剪辑, 一条龙剪辑并留存可复现的编辑记录. NOT for a single stage
  (call that skill directly), and NOT a replacement for any of the four.
---

# Video Edit Orchestrate

Coordinate the whole edit — cut, captions, motion graphics, color — as one run with a
written, re-renderable record. `video-rough-cut` makes the first cut (serial root); then
`video-to-captions`, `video-to-remotion`, and `video-color-grade` run as **parallel
branches**; then their outputs are **joined** into `final.mp4`. Every decision and every
file hash lands in one `manifest.json` you can read, diff, and replay.

## The one idea

**The manifest is the edit.** One `manifest.json` is simultaneously the **DAG** (which
stages run, what feeds what), the **provenance doc** (each stage's decision + the hashes
of its inputs/outputs), and the **re-render recipe** (change a param, `status` tells you
what went stale, re-run only that). The orchestrator writes no video logic of its own — it
`init`s the manifest from an ffprobe of the cut, fans out the enabled stages by calling
**the four skills' own scripts unchanged**, `fold`s each branch's `stage.json` back one at
a time, and `render`s the manifest to a human-readable `EDIT.md`. If a step looks like it
belongs to one of the four skills, it does — go read that skill's SKILL.md; never edit it
here.

## Dependency graph

```
                     video-rough-cut   (serial root — not a manifest stage)
                     first_cut.mp4  +  work/selfcheck/cut_transcript.json
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
   video-to-captions        video-to-remotion         video-color-grade
   caption-overlay.mov      graphics-overlay.mov       graded.mp4
     (transparent)            (transparent)          (same geometry + audio)
          └─────────────────────────┼─────────────────────────┘
                                    ▼
                        join  (serial — two single-overlay passes)
                                 final.mp4
```

Two safety properties make the fan-out sound — **state them, and don't design around
breaking them**:

- **The overlay branches contain no source pixels.** `video-to-captions` and
  `video-to-remotion` each emit a *transparent* overlay (ProRes 4444 / VP8-alpha) — alpha
  and graphics only, never a copy of the picture. So both can be generated in parallel from
  the same cut without racing on the frame.
- **The grade branch preserves geometry.** `video-color-grade` re-colors the same frames
  in place — same duration, fps, width, height — and copies audio (`-c:a copy`). It moves
  no frame, so its output drops in as the base without shifting any overlay's timing.

Together: overlays carry no pixels and grade shifts no frame, so the three branches are
genuinely independent and the join is a pure stack.

## When to use

- A full, multi-stage edit: you want the cut **and** captions **and** motion graphics
  **and** a grade, produced together and recorded so you can re-render later.
- The ask is "edit this end to end", "run the whole pipeline", "cut + caption + grade +
  graphics", "keep an edit doc so I can tweak and re-render".

## When NOT to use

- You only want **one** stage — call that skill directly (`video-to-captions`,
  `video-to-remotion`, `video-color-grade`, `video-rough-cut`). Orchestration is overhead
  when there's nothing to coordinate.
- As a **replacement** for any of the four. This skill sequences them; it does not
  reimplement transcription, chunking, cue detection, LUT baking, or rendering.

## Dependencies

- **The four skills present and unmodified:** `video-rough-cut`, `video-to-captions`,
  `video-to-remotion`, `video-color-grade`. Their SKILL.md files stay authoritative.
- **`ffprobe`** — `manifest.py init` probes the cut (width/height/fps/duration + a source
  hash). It is the only external process `manifest.py` spawns.
- **Python 3.12, stdlib only** for `scripts/manifest.py` — no pip/conda deps.
- **Node + Remotion + ffmpeg** for the two overlay branches and the join, exactly per
  `video-to-captions` / `video-to-remotion` (pin one Remotion 4.x, React/react-dom
  `18.3.1`). `video-color-grade` needs its own deps (numpy/Pillow) per that skill.
- **Transcript reuse (do not re-transcribe).** `video-rough-cut`'s self-check writes
  `work/selfcheck/cut_transcript.json` — a word-level transcript of the *exact cut* you're
  dressing. **Both** overlay branches consume it as their `work/transcript.json`; reusing
  it saves a ~15–20 min CPU transcription per branch. Record its path in the manifest's
  `transcript` block so provenance points at the one shared transcript.

## Working layout

```
first_cut.mp4                         # the cut (video-rough-cut output, or supplied)
work/selfcheck/cut_transcript.json    # the shared word-level transcript (reused by both overlays)
manifest.json                         # *** the edit doc / DAG / re-render recipe ***
work/captions/   ...                  # video-to-captions branch (its own Remotion project)
work/remotion/   ...                  # video-to-remotion branch (its own Remotion project)
work/grade/      ...                  # video-color-grade branch
work/<branch>/stage.json              # each branch's proposal/result, folded into the manifest
work/join/base_plus_caps.mp4          # near-lossless intermediate (two-pass join)
EDIT.md                               # human-readable projection of manifest.json
final.mp4                             # THE DELIVERABLE
```

A worked manifest is in `manifest.example.json`.

## The pipeline

### 0. Rough-cut (serial root, skippable) + seed the manifest

Run `video-rough-cut` per its SKILL.md, **or** point at an existing `first_cut.mp4` +
transcript. Rough-cut is the serial root — it is *not* a manifest stage (editing its
internal `edit_coarse.json` is invisible to `status` until rough-cut is re-run). Then seed
the manifest from the cut:

```
python skills/video-edit-orchestrate/scripts/manifest.py init first_cut.mp4 \
  --enable captions,remotion,grade --out manifest.json
```

Record the transcript path into the manifest's `transcript` block (hand-edit, or a later
`fold`). **ANCHOR auto-settles:** when both `captions` and `remotion` are enabled, `init`
sets `remotion.params.anchor = "top"` so the cards clear the bottom captions — this is not
a human gate, do not ask.

### 1. Fan out (one subagent per enabled branch)

Dispatch one subagent per enabled stage. **Each works in its own `work/<branch>/` dir** —
`captions` and `remotion` each scaffold a *full, separate* Remotion project; never share a
directory. Each subagent runs its skill's **propose** phase only, then writes
`work/<branch>/stage.json` — `params` + `input_paths` + `output_paths` (so far) +
`status:"proposed"` + its proposal (the thing the human will approve) — and **exits**.

### 2. Per-branch gate

For each branch reporting `proposed`, surface just that branch's decision:

- **captions:** the chunking (read the `.srt`) + any recurring name/term fixes.
- **remotion:** which cues to keep/prune + the editorial copy.
- **grade:** pick a look number. When any overlay stage is enabled, auto-inject the hint
  *"keep it subtle — overlays sit on top"* into the grade choice.

**Opportunistic coalescing:** if several gates are ready at once, present them together;
but never wait for all — gate each branch the moment it's ready. Record each answer:

```
python skills/video-edit-orchestrate/scripts/manifest.py fold \
  --manifest manifest.json --stage <branch> --from work/<branch>/stage.json
```

`fold` merges **exactly one stage** per call and hashes that stage's listed paths from
disk. It is the manifest's only writer and it serializes — the write-queue is the mutual
exclusion, no lockfile.

**Re-propose loop (bounded).** If the human rejects a proposal, re-run **only that
branch's** propose phase and re-gate it. Max 3 rounds; then stop and ask how to proceed.
Siblings keep going — one branch's rejection never blocks the others.

### 3. Render (one subagent per approved branch, cap = 1 heavy render)

Each approved branch runs its skill's **render** phase in its own dir, under a
**foreground/monitored** process (never a detached fire-and-forget job — it can be killed
when the session goes idle). **Serialize the two Remotion renders** (see Compute cap);
grade's cheap ffmpeg pass may overlap. Then `fold` the render outputs back:

```
python skills/video-edit-orchestrate/scripts/manifest.py fold \
  --manifest manifest.json --stage <branch> --from work/<branch>/stage.json
```

### 4. Join (serial)

Stack the branch outputs into `final.mp4`. See the **Join** section.

### 5. Provenance

```
python skills/video-edit-orchestrate/scripts/manifest.py render --manifest manifest.json --out EDIT.md
python skills/video-edit-orchestrate/scripts/manifest.py status --manifest manifest.json
```

`render` writes the human-readable `EDIT.md` (source line, per-stage table, join block).
`status` reports, per stage, `clean` or `DIRTY: <reasons>` — a stage is stale iff one of
its recorded input files changed hash, an input is missing, or its `params` hash drifted.
Change a param → `status` names exactly what to re-run.

## Join

**Decision: two single-overlay ffmpeg passes** — captions first, then cards on top, each
`-c:a copy`. This is the settled approach; do not "optimize" it back into a single command.

**Why not the single-ffmpeg two-overlay chain.** The tempting one-shot form
`[0:v][1:v]overlay[a];[a][2:v]overlay[v]` (chaining both overlays in one filtergraph) was
found in this repo's prior work to **silently drop the second overlay layer** — the render
succeeds, the log looks clean, and one of the two overlays is simply missing from the
output ([[remotion-overlay-two-pass]]). It is a **known-bad form**; a mid-video still that
shows only one layer is the symptom. Composite in two explicit passes instead — each pass
does exactly one `overlay`, so neither can be dropped.

To avoid visible generation loss across two H.264 encodes, make **pass 1's intermediate
near-lossless** (`-crf 12`); pass 2 encodes the delivery at normal quality.

**Pass 1 — graded base + captions (bottom) → near-lossless intermediate:**
```
ffmpeg -y -i work/grade/out/graded.mp4 -i work/captions/out/caption-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 12 -preset veryfast -c:a copy \
  work/join/base_plus_caps.mp4
```

**Pass 2 — intermediate + cards (top) → delivery:**
```
ffmpeg -y -i work/join/base_plus_caps.mp4 -i work/remotion/out/graphics-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy \
  -movflags +faststart final.mp4
```

**Only one overlay enabled → one pass** (base is `graded.mp4`, or `first_cut.mp4` if grade
is off; overlay is whichever of captions/cards is on):
```
ffmpeg -y -i work/grade/out/graded.mp4 -i work/captions/out/caption-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy \
  -movflags +faststart final.mp4
```

`caption-overlay.mov` and `graphics-overlay.mov` are large, deletable intermediates (a full
alpha frame every frame); keep `final.mp4` and delete them after a clean join.

**Windows note.** Drive-colon paths (`D:\...`) break ffmpeg *filtergraph options that take
a path* (`lut3d=file`, `metadata=print:file=`) — run ffmpeg with `cwd` set to the file's
folder and reference by **basename** for those. The join's `overlay=` takes no path
argument (the overlays arrive as `-i` inputs, which handle drive-colons fine), so the
commands above are safe as written; the rule bites only if you add a path-taking filter.

## Compute cap

**One heavy render at a time (cap = 1).** A single Remotion render already fans out across
all cores; launching the captions and cards renders *concurrently* just thrashes the CPU
and risks OOM with no wall-clock win. So **serialize the two overlay renders** — run one to
completion, then the next. `video-color-grade`'s ffmpeg pass is cheap and may overlap a
render. Keep every render in a **monitored foreground** job (a detached job gets killed
when the controlling session goes idle). Under disk pressure, render the overlays as
**VP8-alpha webm** instead of ProRes 4444 — ~100× smaller, same quality
([[remotion-overlay-vp8-alpha-disk]]).

The real parallel win is in the **propose wave** (LLM/network-bound, genuinely
concurrent), not the render wave — fan out the proposals, serialize the renders.

## Self-check

- **Fan-out shape:** exactly one `work/<branch>/stage.json` per enabled branch; each
  branch ran in its own dir.
- **ANCHOR:** with both overlays on, `remotion.params.anchor == "top"` (auto, not asked).
- **Bounded re-propose:** a rejected proposal re-ran **only** its branch, ≤ 3 rounds;
  siblings were untouched.
- **Both layers present (the key one):** a still mid-video shows **both** the captions
  (bottom) **and** a card (top). This one check catches the silent-overlay-drop bug *and*
  an ANCHOR collision at once.
- **Geometry:** `final.mp4` is at the source's width/height/fps/duration — no 4K upscale,
  no letterbox, no drift.
- **Reproducible:** `manifest.py render` reproduces the run as `EDIT.md`, and
  `manifest.py status` reads `clean` for every stage whose files and params are unchanged.
