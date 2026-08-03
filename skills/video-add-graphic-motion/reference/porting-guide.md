# Preconverted Recipe Verification

All manifest recipes were converted before this skill runs. During a video project, use
`recipe_library.mjs materialize`; do not port, regenerate, or patch a recipe. The schema-v3
validator requires the copied manifest, conversion receipt, complete materialized file set, and
hashes to match the bundled preconverted recipe exactly.

The materialized directory contains the HyperFrames entry point `index.html`, its deterministic
adapter files, `conversion.json`, `recipe.motion.yaml`, and the preserved original files under
`source/`. Inline credit comments from original JavaScript and related files remain intact.

## HyperFrames Checks

Run `check`, `keyframes`, one focused `--shot`, and snapshots for first-visible,
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
visual hierarchy, shapes, choreography, easing, and timing of the original recipe. Then inspect
first/middle/last composites over the actual video for readability and collisions. Bind the
source preview, converted key snapshot, normalized time, fidelity comparison, composites, four
pose snapshots, and HyperFrames check receipt. Every review image path and hash must be distinct.
