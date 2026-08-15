---
name: video-add-graphic-motion
description: Use when an understood Project Protocol V1 video needs selective transcript-timed motion graphics chosen from the bundled recipe library and rendered with HyperFrames.
---

# Video Add Graphic Motion

Add selective, shot-designed recipe adaptations either over the source or as full-frame
timeline inserts. An overlay leaves source time and audio unchanged. A `timeline-insert` is a
full-frame ripple insert (also called a source-hold insert): it adds program time, pauses source
video and source audio, then resumes both from the exact paused source time. It is not a freeze
frame and not an opaque overlay.
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
The library contains 1,513 recipes: 218 motion-anything recipes, 37 MIT-licensed Codrops
project recipes backed by 112 internal variants, and 1,258 source-backed stickers across
`canvas-confetti/`, `mojs/`, `line-md/`, `meteocons/`, and `tsparticles/`. Library-level
provenance lives in `recipes/ATTRIBUTION.md`; each source directory also carries its exact
license and `SOURCE.json` receipt.

**REQUIRED SUB-SKILLS:** Use `video-understand` first. Use `hyperframes`,
`hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, and
`hyperframes-cli` for checks, snapshots, and rendering.

Read [recipe-selection.md](reference/recipe-selection.md),
[porting-guide.md](reference/porting-guide.md),
[anti-ai-aesthetic-protocol.md](reference/anti-ai-aesthetic-protocol.md), and
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
   family, interaction model, `presentation_mode`, compositing mode, timing rationale, and one or more literal
   `recipe_queries`. When video understanding identifies a genuine structural composition,
   also choose exactly one `structural_role`: `opener`, `chapter`, `interstitial`,
   `background`, or `outro`. Do not infer a role merely from a style word. Reject filler and
   visual collisions. Zero cues is valid. Before searching, apply the anti-AI aesthetic protocol
   and write cue-local working notes for `visual_thesis`, one `design_lens`, `layout_grammar`, one
   `signature_beat`, `shot_exclusion_zones`, `semantic_media_subjects`, and explicit
   `forbidden_signals`. Derive these from the footage, transcript, brand evidence, and editorial
   role; never use vague taste words as a substitute for decisions.

   Choose `presentation_mode: overlay` when the graphic must coexist with advancing footage.
   Choose `presentation_mode: timeline-insert` only for one of the five structural roles when a
   self-contained full-frame beat should interrupt and ripple the program. For an insert, use
   `compositing_mode: opaque-full-frame`; place it with `render.anchor_s` on the pre-insertion
   program clock; require `render.audio: {"mode": "silence"}` unless a later schema explicitly
   supports a bound inserted soundtrack. Never reuse source audio inside the insert.
4. Build a deterministic local shortlist:

   ```powershell
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs search `
     --query "technical text decode signal" --limit 8 --json
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs search `
     --query "cinematic image collage" --structural-role opener --limit 8 --json
   node skills/video-add-graphic-motion/scripts/recipe_library.mjs show decrypted-text --json
   ```

   Omit `--structural-role` for ordinary semantic overlays. Supplying it explicitly enables
   role-aware recall only for recipes whose `structural_roles` includes the requested role.

5. The Agent must judge the shortlist, not blindly take rank 1. For every choice, read and assess
   the seven legacy manifest fields: `name`, `description`, `category`, `tags`,
   `intent_keywords`, `best_for`, and `avoid_when`; keep their assessments in
   `selection.field_evidence`. For a role-aware search, also assess `structural_roles`,
   `motion_functions`, `visual_language`, `rhythm_energy`, `information_density`,
   `frame_relationship`, `color_tendency`, and `style_rationale`; record the requested role in
   `selection.structural_role` and all eight assessments in `selection.role_field_evidence`.
   Inspect `mechanisms` and optional KineticImages `modes` as adaptation guidance, not ranking
   evidence. Ordinary selections must omit both role receipt properties. Record an Agent
   rationale and explicit `avoid_when` review in `selection`. `avoid_when` is a contextual
   warning only; it never makes a recipe unsupported. Prefer two or more candidates when the
   query returns them. If none fits the cue or footage, skip the cue.
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
   to the actual shot. For an overlay, keep every element and its complete animated path outside
   every protected face and head silhouette, including entrances, overshoot, settling, and exits.
   A timeline insert replaces the source for its whole interval, so overlay collision rules do not
   apply inside it; instead, design its opening and closing frames to cut coherently to the exact
   paused source frame. A centered web
   demo, recipe-name label, or
   unchanged 12-16px control is not an acceptable adaptation.

   **Footage-first direction:** Use one primary message, one focal recipe mechanic, one coherent
   layout grammar, and at most one accent color unless source or brand evidence requires more.
   Motion must reveal hierarchy, connect a state or spatial change, or explain a concept; a generic
   fade, float, parallax, bounce, or decorative loop is insufficient. Preserve one readable hold
   and organize anticipation, the signature beat, settle, and exit around the cue's meaning. The
   footage supplies identity and depth; do not replace it with interface chrome.
   When `structural_role` is `opener`, reject an ordinary broadcast name strap, corner bug, or
   lower-third placed at the start. Use opener-scale hierarchy, and make the focal recipe mechanic
   establish a meaningful title/footage or evidence/title relationship rather than serving only as
   a one-time reveal of an otherwise generic lockup.

   **Semantic-media gate:** Every framed photo, image mask, texture window, thumbnail, or other
   raster insert must contain a recognizable subject that advances the cue's exact meaning. For a
   named person, place, object, document, or event, search authoritative or clearly licensed online
   sources first and prefer a directly attributable image whose subject is already clear at the
   required crop. Bind the exact source page, creator, license evidence, downloaded local file, and
   SHA-256 before authoring; a search-results thumbnail or image URL alone is not a source receipt.
   Use a source-video frame only when the online-first search finds no suitable licensed image or
   network access fails. Record the queries/sources checked and a specific `fallback_reason`; do not
   claim convenience, visual style, or an easier crop as a fallback reason. Before authoring, record
   the selected image's origin, visible subject, cue relevance, and why the crop preserves the
   meaningful evidence. A random
   crop of scenery, set lighting, clothing, architecture, or background texture fails when it is
   used only to fill a recipe image slot. The frame itself must communicate the stated subject at
   normal playback size; nearby text cannot rescue an ambiguous crop, and text, borders, or other
   graphics must not cover the subject's identifying features. When no meaningful image is
   available after this search-and-fallback sequence, redesign the recipe without the image slot or
   skip the cue. Never substitute an unverified search thumbnail.

   **Information budget:** Every visible element must earn its place by carrying the cue's
   narrative meaning, expressing the recipe's core motion mechanic, or keeping the overlay legible
   over the footage. Use one primary message per cue. Remove demo titles, recipe names, instructions,
   status labels, redundant counters, repeated copy, decorative HUD panels, badges, chips, and
   metadata that do not meet that test. Do not express the same fact as a headline, badge, and
   caption. Fancy comes from motion, composition, typography, rhythm, and material treatment, not
   UI density. If the result resembles a dashboard, control panel, or generic AI-generated UI,
   simplify it before rendering while preserving the recipe's recognizable visual mechanic.
   Reject unsupported purple-blue or multicolor gradients, glass panels, glow, HUD frames,
   arbitrary grids, fake data, pills, badges, chips, card stacks, bento layouts, sparkles, nodes,
   meaningless particles, generic technology copy, repeated facts, and raw recipe/demo UI. A
   normally forbidden primitive is allowed only when literal cue content or established brand
   evidence makes it necessary and the working notes state that evidence.

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
   rational FPS. Bind every contiguous frame. An overlay must retain usable alpha; a timeline
   insert must be fully opaque in every frame.
9. Verify both the converted base and project adaptation. Compare original source with converted
   base at one normalized time, then compare converted base with the adapted key pose. Inspect
   first/middle/last composites, every event-time full-frame composite, a focused crop of the moving
   subject, and the moving clip over the actual video with active captions and content cards
   composited first. For a timeline insert, inspect the full inserted segment plus at least one
   frame and an audio window on both sides of every splice; confirm duration grows by the inserted
   duration, the insert does not expose source pixels, source audio is silent during the insert,
   and source video/audio resume from the exact anchor. Reject transient defects even when the
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
   avoidance alone is not approval. Also judge `distinctiveness/editorial_value` in working notes:
   reject a cue that could be transplanted unchanged into an unrelated SaaS, AI, or technology
   video. Review every framed or masked image at its smallest, largest, and settled crop and confirm
   that the recorded subject remains recognizable and semantically necessary. Any protected-zone
   collision, unclear primary meaning, meaningless media crop, or central forbidden signal fails
   the cue regardless of other strengths. Name the observed failure, strengthen only the prompt
   rule that failed, and rebuild; do not merely recolor the same composition or add decoration.
10. Bind timeline, transcript, understanding, media, contact sheet, recipe files, adaptation
   files, frames, review images, HyperFrames check, and a truthful human or delegated-Agent review
   receipt. Run
   `validate_plan(..., verify_files=True)`, write `graphic-motion-plan.json`, then call
   `register_operation`. All-skipped removes or omits the operation.
11. Compile with `build_render_plan.py`, render once with `render_project.py`, and self-check
    duration, dimensions, timeline, audio, exact FPS, alpha/opacity, and every cue in context.
    Overlay-only output duration must equal the base program duration. Output with timeline inserts
    must equal base program duration plus the sum of inserted durations.

Render contribution forms:

```json
{"kind":"overlay","asset_type":"image-sequence","start_s":12.5,"duration_s":1.0}
{"kind":"timeline-insert","asset_type":"image-sequence","anchor_s":0.0,"duration_s":4.5,"audio":{"mode":"silence"}}
```

Treat all `anchor_s` values as positions on the pre-insertion program clock. The renderer applies
existing captions, cards, and overlays to that base clock first, then ripples the completed program
around each insert so downstream pixels and audio remain synchronized.

Canonical order:

```text
cut -> color-grade -> b-roll -> captions -> content-cards -> graphic-motion
```

This relative order is mandatory for any selected pair among the final three operations.

Schema v3 rejects v2 plans. Regenerate selection and bindings from the local recipe library.
