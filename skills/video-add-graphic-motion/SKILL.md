---
name: video-add-graphic-motion
description: Use when an understood Project Protocol V1 video needs selective transcript-timed motion graphics chosen from the bundled recipe library and rendered with HyperFrames.
---

# Video Add Graphic Motion

Add selective, shot-designed recipe adaptations without changing timeline,
geometry, or audio.
Face and head safety is absolute for protected people: no graphic, text, mask, particle, or
transient animation may overlap the visible face or head silhouette of a primary or foreground
person, speaker, presenter, interviewee, or semantically important person in any frame. An
incidental background-only person who is not a narrative or visual focus is exempt; protect
uncertain cases. On overlap, reposition the effect first, then scale down or redesign it; skip
the cue when no compliant placement exists.
Caption safety is also absolute. When captions are active, treat their complete occupied
region across every overlapping cue as a reserved exclusion zone. Graphic motion runs after
captions and content cards, and may not overlap either upstream overlay.
The bundled `recipes/` tree is the only effect library. Do not search the web, query a remote
catalog, or author a substitute effect. Every bundled manifest recipe is supported through its
preconverted `hyperframes/` directory.
The library contains 1,477 recipes: 218 motion-anything recipes, the MIT-licensed Codrops
`codrops/KineticImages` Three.js recipe, and 1,258 source-backed stickers across
`canvas-confetti/`, `mojs/`, `line-md/`, `meteocons/`, and `tsparticles/`. Library-level
provenance lives in `recipes/ATTRIBUTION.md`; each source directory also carries its exact
license and `SOURCE.json` receipt.

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
   When active, also read the approved caption and content-card plans and their review evidence.
   Map transcript evidence with `projectlib.map_transcript_to_timeline`. For the full cue range,
   identify every protected face and visible head silhouette, caption region, and content-card
   region and reserve them before choosing overlay placement. Classify any background-only
   person exemption explicitly; protect uncertain cases.
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

   Keep this materialized directory immutable: it is the provenance base that preserves library
   attribution and inline source credits. It is not the finished overlay.
7. Set `authoring_mode: recipe-adaptation`. Author the real composition under
   `work/cache/graphic-motion/adapted/<cue-id>/`, using the recipe's recognizable motion mechanic
   as the template. Replace demo copy and adapt layout, scale, palette, timing, and choreography
   to the actual shot. Keep every element and its complete animated path outside every protected
   face and head silhouette, including entrances, overshoot, settling, and exits. A centered web
   demo, recipe-name label, or
   unchanged 12-16px control is not an acceptable adaptation.

   **Information budget:** Every visible element must earn its place by carrying the cue's
   narrative meaning, expressing the recipe's core motion mechanic, or keeping the overlay legible
   over the footage. Use one primary message per cue. Remove demo titles, recipe names, instructions,
   status labels, redundant counters, repeated copy, decorative HUD panels, badges, chips, and
   metadata that do not meet that test. Do not express the same fact as a headline, badge, and
   caption. Fancy comes from motion, composition, typography, rhythm, and material treatment, not
   UI density. If the result resembles a dashboard, control panel, or generic AI-generated UI,
   simplify it before rendering while preserving the recipe's recognizable visual mechanic.

   Then bind the complete adapted file set:

   ```powershell
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs bind-adaptation `
     --project D:\path\to\video-project --cue gm-001 --json
   ```

8. Run HyperFrames `check`, `keyframes`, and one focused `--shot` on the adapted directory. Read
   the animation source before choosing snapshot times and build an event-time list from the
   actual timeline: every risky tween's start and end, explicit keyframes and labels, target
   crossings, overshoot peak, rebound extreme, and settled pose. For spring, elastic, bounce,
   path, scale, rotation, clip, or mask motion, capture the event/extreme plus one exact timeline frame before
   and after it, clamped inside the cue. Evenly spaced snapshots are supplemental only
   and never sufficient for approval. Render an RGBA PNG sequence at timeline dimensions and exact
   rational FPS. Bind every contiguous frame.
9. Verify both the converted base and project adaptation. Compare original source with converted
   base at one normalized time, then compare converted base with the adapted key pose. Inspect
   first/middle/last composites, every event-time full-frame composite, a focused crop of the moving
   subject, and the moving clip over the actual video with active captions and content cards
   composited first. Reject transient defects even when the
   settled pose is correct: overshooting the intended track or container, crossing the wrong target,
   clipping, collision, occlusion, separation from a label, or a one-frame flash. Reject any cue if
   any overlay pixel intersects a protected face or head silhouette at any sampled or intervening
   frame; partial, translucent, and one-frame overlaps still fail. Reposition the effect and
   repeat the complete-path review before approval. Inspect every composited frame containing a
   protected person, not only snapshots, and record protected people, any background-only
   exemptions, and the face-and-head safety result in `footage_integration`. The review must
   record non-empty `semantic_clarity`, `composition`, `readability`, `motion_quality`, and
   `footage_integration` judgments. At each sampled pose, account for every visible text or UI-like
   element: reject the cue if an element has no narrative, motion-mechanic, or legibility purpose,
   if information is repeated, or if the primary message is not clear at a glance. Collision
   avoidance alone is not approval.
10. Bind timeline, transcript, understanding, media, contact sheet, recipe files, adaptation
   files, frames, review images, HyperFrames check, and a truthful human or delegated-Agent review
   receipt. Run
   `validate_plan(..., verify_files=True)`, write `graphic-motion-plan.json`, then call
   `register_operation`. All-skipped removes or omits the operation.
11. Compile with `build_render_plan.py`, render once with `render_project.py`, and self-check
    duration, dimensions, timeline, audio, exact FPS, alpha, and every cue in context.

Canonical order:

```text
cut -> color-grade -> b-roll -> captions -> content-cards -> graphic-motion
```

This relative order is mandatory for any selected pair among the final three operations.

Schema v3 rejects v2 plans. Regenerate selection and bindings from the local recipe library.
