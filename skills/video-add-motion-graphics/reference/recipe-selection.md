# Local Recipe Selection

`recipes/**/recipe.motion.yaml` is the sole metadata source and each manifest-backed recipe is
selectable. `recipes/imported/**` is reference-only, and generated copies under
`hyperframes/source/**` are never indexed as separate recipes.

## Why this router

Do not concatenate 1,513 manifests into a hand-maintained catalog: it would duplicate the source
of truth and drift. Do not invoke the full motion-anything CLI: its broader project generation
and server features are unnecessary here. `scripts/recipe_library.mjs` reuses the converter's
manifest discovery and provides the smallest required interface:

```text
search --query ... --category ... --structural-role ... --limit 8 --json
show <recipe-id> --json
materialize <recipe-id> --project <root> --cue <cue-id> --json
bind-adaptation --project <root> --cue <cue-id> --json
```

`search` tokenizes the local manifest fields, scores positive matches deterministically, reports
`avoid_when` matches separately, and breaks ties by recipe ID. It does not make the editorial
decision. `show` returns exact metadata and source hashes. `materialize` copies the already
converted HyperFrames directory and returns project-relative SHA-256 bindings.
`bind-adaptation` hashes the separate shot-designed composition after the Agent finishes editing.

The library includes 37 project-level Codrops recipes backed by 112 converted variants. Only each
project's default `index` composition is selectable; internal variants remain adaptation material.
Codrops recipes are full-screen or frame-dominant designed cutaways, not compact stickers.

Ordinary semantic searches omit `--structural-role` and retain the legacy seven-field scoring
contract. Use `--structural-role opener|chapter|interstitial|background|outro` only after video
understanding establishes that the cue needs that structural composition. A supplied role enables
extended-field scoring only for recipes that explicitly advertise the same role.

`codrops/KineticImages` is one recipe with three scene modes: `cylinders`, `paper`, and `spiral`.
Its immutable converted base uses `showcase` to review all three; an adaptation selects one mode.

The 1,258 sticker recipes are grouped by upstream implementation: 10 canvas-confetti celebration
effects, 10 mo.js burst/impact effects, all 1,218 Line MD icons plus its 4 aliases, 12 Meteocons
weather icons, and 4 tsParticles-derived complex particle fields. Prefer Line MD or Meteocons when a literal
symbol carries the cue. Prefer canvas-confetti or mo.js for celebration and impact. Use the four
tsParticles ports only when their complex field behavior is not covered by a smaller recipe.

## Agent Decision

For each shortlisted recipe, compare semantic fit, footage readability, cue duration, and
repetition with other cues. Before choosing, inspect these seven fields:

| Field | Decision question |
| --- | --- |
| `name` | Is this the actual treatment the cue calls for? |
| `description` | Does the described action communicate the intended idea? |
| `category` | Is this motion family appropriate for the editorial role? |
| `tags` | Do the concrete objects and mechanics match? |
| `intent_keywords` | Does the manifest name the same viewer intent? |
| `best_for` | Does the cue resemble the recommended use? |
| `avoid_when` | Does the current footage or tone trigger a warning? |

The chosen recipe supplies the motion mechanic, not final copy or layout. Reject unchanged demo
text, tiny web controls, default centering, and repeated generic pill treatments. The schema-v3
`selection.field_evidence` object must contain a non-empty assessment for every
field. `selection.avoid_when_review` must explain why the warning does or does not apply.
`avoid_when` never removes a recipe from the supported library; it only prevents a poor choice
for a particular cue.

For role-aware searches, additionally inspect these fields:

| Field | Decision question |
| --- | --- |
| `structural_roles` | Does the recipe explicitly support the requested opener, chapter, interstitial, background, or outro? |
| `motion_functions` | Does its reveal, transition, loop, build, or settle behavior fit the beat? |
| `visual_language` | Does the authored visual treatment fit the video's editorial style? |
| `rhythm_energy` | Does the motion energy fit the surrounding pacing? |
| `information_density` | Can the frame carry the intended message without overload? |
| `frame_relationship` | Is a full-screen or frame-dominant cutaway appropriate here? |
| `color_tendency` | Can its color behavior be adapted coherently to the footage? |
| `style_rationale` | Does the reviewed visible mechanism justify this structural use? |

Store the requested role as `selection.structural_role` and a non-empty assessment for all eight
fields in `selection.role_field_evidence`. Keep the existing seven-field `field_evidence` as well.
Inspect `mechanisms` and KineticImages `modes` for adaptation decisions, but do not treat them as
search-ranking evidence. A non-role selection omits both role receipt properties.

Use `selection.shortlist` to record the router's recipe IDs, scores, and matched fields. The
chosen ID must be a matched shortlist candidate and must equal `recipe.id`. If the shortlist has
no suitable contextual match, record a skipped cue rather than inventing an effect.
