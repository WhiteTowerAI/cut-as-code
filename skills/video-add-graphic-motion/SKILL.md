---
name: video-add-graphic-motion
description: Use when an understood Project Protocol V1 video needs selective transcript-timed motion graphics adapted from licensed online HTML, CSS, SVG, Canvas, or WebGL references.
---

# Video Add Graphic Motion

Add high-craft, source-backed overlays without changing timeline, geometry, or audio. Define
intent before search; generic entrances, loaders, and decorations are invalid. HyperFrames
owns seeking, alpha, exact FPS, checks, snapshots, and PNG rendering.

**REQUIRED SUB-SKILLS:** Use `video-understand` first. Use `hyperframes`,
`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, and
`hyperframes-cli` for every port and render. Use `hyperframes-creative` only before
source selection; the selected source owns the later visual design and runtime.

Read [source-catalog.md](reference/source-catalog.md),
[porting-guide.md](reference/porting-guide.md), and
[example-graphic-motion-plan.json](examples/example-graphic-motion-plan.json).

## Workflow

1. Call `validate_prerequisite(project_root)` before creative work or search. On error, finish
   `video-understand`; do not probe, transcribe, or analyze again.
2. Read project/timeline, media, transcript, analysis, understanding, summary, and contact
   sheet; map transcript evidence with `projectlib.map_transcript_to_timeline`.
3. Bind each cue to mapped words and the contact sheet. Before search, timestamp content,
   half-open range, effect, interaction, compositing, timing rationale, and literal queries.
   Reject filler and visual collisions. Zero cues is valid.
4. Search only the catalog after that timestamp with available web or GitHub tools.
   Do not ask the user to find candidates. Compare two or three exact candidates; record popularity and decisions.
   Freeze source, revision, license evidence, URL, retrieval time, files, and SHA-256 under
   `work/cache/graphic-motion/source/<cue-id>/`. Missing/disallowed license means skip; never
   infer it from a parent. Require an immutable hex revision, official
   catalog URL, hashed local `LICENSE`/`NOTICE` whose bytes match the declared SPDX license,
   and attribution. Freeze a real official or isolated-browser source preview; never synthesize
   it from metadata or port pixels. For `motion-anything`, the license URL must be beside the selected recipe.
5. Statically inspect; never execute downloaded code. Minimally port under
   `work/cache/graphic-motion/hyperframes/<cue-id>/`. Keep runtime assets local and hashed.
   Load the selected runtime's `hyperframes-animation` adapter. Preserve that runtime, DOM/SVG
   hierarchy, easing, and choreography; if determinism requires replacing them, reject the source.
   Before browser use, run `validate_port`; reject remote/undeclared code or redesigns.
6. Follow [hyperframes-port/index.html](examples/hyperframes-port/index.html). Run HyperFrames
   `check`, `keyframes`, one focused `--shot`, and representative `snapshot` checks. Render an RGBA PNG sequence at timeline
   dimensions and exact rational FPS; bind every contiguous frame. Do not add a custom
   ready gate, iframe bridge, clock, copier, or renderer. CSS-only roots declare
   `data-no-timeline`; every browser asset is local and hashed.
7. Build the source-versus-port image from the frozen `source.preview` and an actual port
   snapshot at the same normalized cue time using the exact side-by-side format in the porting
   guide. Bind it with first/middle/last composites and the normalized HyperFrames check
   receipt, and distinct `first-visible`, `key-interaction`, `final-minus-hold`, and `final`
   snapshots. Store each snapshot's strictly increasing cue-local time; all eight review images
   require unique paths and SHA-256 values. Record truthful human or delegated Agent authority,
   rationale, hashes, and receipt. Never fabricate human approval.
8. Bind timeline, transcript, understanding, media, contact sheet, every source/license, port,
   patch, runtime asset, frame, review image, check, and authority receipt. Run
   `validate_plan(..., verify_files=True)`, write `graphic-motion-plan.json`, then call
   `register_operation`; it repeats full validation. All-skipped removes/omits the operation.
9. Compile with `build_render_plan.py`, render once with `render_project.py`, and self-check.
   Inspect every cue; confirm duration, dimensions, timeline, audio, and exact FPS.

Canonical order:

```text
cut -> color-grade -> b-roll -> graphic-motion -> content-cards -> captions
```

The compiler re-hashes the plan and bindings. Mutations require re-review and a new revision.
Schema v2 deliberately rejects v1 plans because v1 lacks source-runtime and source-pixel
provenance; regenerate and re-review them rather than migrating approval receipts.
