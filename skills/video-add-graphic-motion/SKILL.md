---
name: video-add-graphic-motion
description: Use when an understood Project Protocol V1 video needs selective transcript-timed motion graphics chosen only from the bundled motion-anything recipe library and rendered with HyperFrames.
---

# Video Add Graphic Motion

Add selective motion-anything recipe overlays without changing timeline, geometry, or audio.
The bundled `recipes/` tree is the only effect library. Do not search the web, query a remote
catalog, or author a substitute effect. Every bundled manifest recipe is supported through its
preconverted `hyperframes/` directory.

**REQUIRED SUB-SKILLS:** Use `video-understand` first. Use `hyperframes`,
`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, and
`hyperframes-cli` for checks, snapshots, and rendering.

Read [recipe-selection.md](reference/recipe-selection.md),
[porting-guide.md](reference/porting-guide.md), and
[example-graphic-motion-plan.json](examples/example-graphic-motion-plan.json).

## Workflow

1. Call `validate_prerequisite(project_root)` before effect selection. On error, finish
   `video-understand`; do not repeat media analysis.
2. Read project/timeline, transcript, analysis, understanding, summary, and contact sheet.
   Map transcript evidence with `projectlib.map_transcript_to_timeline`.
3. Define each cue before recipe search: content, purpose, half-open program range, motion
   family, interaction model, compositing mode, timing rationale, and one or more literal
   `recipe_queries`. Reject filler and visual collisions. Zero cues is valid.
4. Build a deterministic local shortlist:

   ```powershell
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs search `
     --query "technical text decode signal" --limit 8 --json
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs show decrypted-text --json
   ```

5. The Agent must judge the shortlist, not blindly take rank 1. For the chosen recipe, read and
   assess all seven manifest fields: `name`, `description`, `category`, `tags`,
   `intent_keywords`, `best_for`, and `avoid_when`. Record brief evidence for every field,
   an Agent rationale, and an explicit `avoid_when` review in `selection`. `avoid_when` is a
   contextual warning only; it never makes a recipe unsupported. Prefer two or more candidates
   when the query returns them. If none fits the cue or footage, skip the cue.
6. Materialize the chosen preconverted recipe:

   ```powershell
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs materialize decrypted-text `
     --project D:\path\to\video-project --cue gm-001 --json
   ```

   Use the returned schema-v3 `recipe` object. Do not run the corpus converter during a video
   project and do not replace or edit the materialized files. The validator rechecks the local
   manifest, conversion receipt, complete file set, and every SHA-256. Library attribution stays
   in `recipes/ATTRIBUTION.md`; copied inline source credits remain in the materialized files.
7. Run HyperFrames `check`, `keyframes`, one focused `--shot`, and representative snapshots on
   the materialized directory. Render an RGBA PNG sequence at timeline dimensions and exact
   rational FPS. Bind every contiguous frame.
8. Verify the converted effect rather than trusting metadata. Capture the original recipe entry
   under the materialized `source/` directory and the converted `index.html` at the same
   normalized cue time. Build the source-versus-converted image described in the porting guide.
   Also inspect first/middle/last composites over the actual upstream video and four distinct
   HyperFrames poses. Confirm deterministic seeking and recognizable visual structure,
   choreography, easing, and timing.
9. Bind timeline, transcript, understanding, media, contact sheet, recipe files, frames, review
   images, HyperFrames check, and truthful human or delegated-Agent review receipt. Run
   `validate_plan(..., verify_files=True)`, write `graphic-motion-plan.json`, then call
   `register_operation`. All-skipped removes or omits the operation.
10. Compile with `build_render_plan.py`, render once with `render_project.py`, and self-check
    duration, dimensions, timeline, audio, exact FPS, alpha, and every cue in context.

Canonical order:

```text
cut -> color-grade -> b-roll -> graphic-motion -> content-cards -> captions
```

Schema v3 rejects v2 plans. Regenerate selection and bindings from the local recipe library.
