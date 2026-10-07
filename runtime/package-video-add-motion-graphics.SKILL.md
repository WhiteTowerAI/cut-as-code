---
name: video-add-motion-graphics
description: Use when an understood Project Protocol V1 video needs selective transcript-timed motion graphics from this package's compact AnimXYZ core.
---

# Video Add Motion Graphics - Packaged Core

This package ships exactly 10 selectable AnimXYZ core recipes: `xyz-fade-big`,
`xyz-fade-down`, `xyz-fade-left`, `xyz-fade-right`, `xyz-fade-small`, `xyz-fade-up`,
`xyz-flip-left`, `xyz-flip-up`, `xyz-rise-big`, and `xyz-rotate`. The archive contains
exactly 20 AnimXYZ recipe manifests because each selectable recipe also retains its bound
provenance copy under `hyperframes/source/`.
Use only those preconverted local recipes. Without the expanded HyperFrames content pack, supported
operation is limited to local search, show, materialize, and draft plan preparation. Non-skipped
validate/register/render is unavailable because it requires rendered frames, HyperFrames check
evidence, snapshots, complete file bindings, and an approved composited visual review. An
all-skipped no-op may register only when the bundled validator accepts it. The editor itself does
not invoke this skill or render video.

The full repository also supports optional Codrops and sticker libraries. They are intentionally
omitted from this compact editor package. Treat a request for Codrops, canvas-confetti, mo.js,
Line MD, Meteocons, tsParticles, or another absent family as
`missing_content_pack: motion-graphics-expanded-library`; do not silently return an empty catalog,
search the web, or substitute another effect.

HyperFrames authoring and rendering skills are external prerequisites for any non-skipped cue.
When they are unavailable, stop after materialization and draft preparation and report
`missing_content_pack: hyperframes-toolchain`.

Use `video-understand` before selecting effects. Preserve the full skill's safety contract:
captions, content cards, and every protected face/head silhouette are hard exclusion zones
throughout the complete animation path; skip any cue that cannot be placed safely.

Search and inspect the shipped core deterministically:

```powershell
node skills/video-add-motion-graphics/scripts/recipe_library.mjs search `
  --query "fade rise rotate" --limit 8 --json
node skills/video-add-motion-graphics/scripts/recipe_library.mjs show xyz-fade-up --json
```

For a selected core recipe, record manifest evidence and Agent rationale, materialize it with
`recipe_library.mjs materialize`, and prepare a draft cue. Zero cues is valid. Do not adapt, bind,
validate/register a non-skipped plan, or claim rendered output until the HyperFrames content pack is
present and its checks, frame rendering, bindings, and full composited visual review actually run.
