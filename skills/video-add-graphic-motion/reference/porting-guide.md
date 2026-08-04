# Preconverted Recipe Verification

All manifest recipes were converted before this skill runs. During a video project, use
`recipe_library.mjs materialize`; do not port, regenerate, or patch that immutable provenance
copy. The schema-v3 validator requires its manifest, conversion receipt, complete file set, and
hashes to match the bundled preconverted recipe exactly.

The materialized directory contains the HyperFrames entry point `index.html`, its deterministic
adapter files, `conversion.json`, `recipe.motion.yaml`, and the preserved original files under
`source/`. Inline credit comments from original JavaScript and related files remain intact.

## Project Adaptation

The materialized recipe is a motion reference, not a finished video layout. New plans set
`authoring_mode: recipe-adaptation` and put editable files under
`work/cache/graphic-motion/adapted/<cue-id>/`. Start from the selected recipe's recognizable
mechanic, then adapt all six project dimensions: `content`, `layout`, `scale`, `palette`, `timing`,
and `choreography`. Record every change, the preserved recipe features, and the rationale.

After authoring, run `recipe_library.mjs bind-adaptation`. It returns the cue composition ID,
`index.html` entry binding, and complete file bindings. HyperFrames checks and rendering target
this adapted composition; source credits and the untouched base stay bound as provenance.

## HyperFrames Checks

Run `check`, `keyframes`, one focused `--shot`, and snapshots on the adaptation for first-visible,
key-interaction, final-minus-hold, and final poses. Times must be strictly increasing and inside
the cue duration. The check receipt uses the recipe's `composition_id`, not the cue ID.

Render transparent PNGs at the media-probe dimensions and exact rational timeline FPS. Frame
count is `ceil(duration * fps_num / fps_den)`. The sequence must be contiguous, RGBA, and contain
both visible and transparent pixels when compositing mode is `transparent-overlay`.

## Visual-Fidelity Acceptance

Open the original recipe entry from the materialized `source/` directory and the converted
`index.html`. Capture both at the same normalized cue time. Build `source-fidelity.png` with
original pixels unscaled on the left and converted pixels unscaled on the right, top-aligned,
RGB PNG, and black padding below the shorter image.

Approve only when sampled seeking is deterministic and the conversion keeps the recognizable
visual hierarchy, shapes, choreography, easing, and timing of the original recipe. Then compare
the converted base with the adapted key pose to confirm the selected mechanic remains visible.
Inspect first/middle/last composites and moving pixels over the actual video. Record
`semantic_clarity`, `composition`, `readability`, `motion_quality`, and `footage_integration`; a
technically valid but tiny, generic, centered, or semantically empty overlay fails. Every review
image path and hash must be distinct.
