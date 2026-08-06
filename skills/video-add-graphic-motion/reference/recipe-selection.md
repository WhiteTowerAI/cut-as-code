# Local Recipe Selection

`recipes/**/recipe.motion.yaml` is the sole metadata source and each manifest-backed recipe is
selectable. `recipes/imported/**` is reference-only, and generated copies under
`hyperframes/source/**` are never indexed as separate recipes.

## Why this router

Do not concatenate 1,477 manifests into a hand-maintained catalog: it would duplicate the source
of truth and drift. Do not invoke the full motion-anything CLI: its broader project generation
and server features are unnecessary here. `scripts/recipe_library.mjs` reuses the converter's
manifest discovery and provides the smallest required interface:

```text
search --query ... --category ... --limit 8 --json
show <recipe-id> --json
materialize <recipe-id> --project <root> --cue <cue-id> --json
bind-adaptation --project <root> --cue <cue-id> --json
```

`search` tokenizes the local manifest fields, scores positive matches deterministically, reports
`avoid_when` matches separately, and breaks ties by recipe ID. It does not make the editorial
decision. `show` returns exact metadata and source hashes. `materialize` copies the already
converted HyperFrames directory and returns project-relative SHA-256 bindings.
`bind-adaptation` hashes the separate shot-designed composition after the Agent finishes editing.

`codrops/codrops-kinetic-images` is one recipe with three scene modes: `cylinders`, `paper`, and `spiral`.
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

Use `selection.shortlist` to record the router's recipe IDs, scores, and matched fields. The
chosen ID must be a matched shortlist candidate and must equal `recipe.id`. If the shortlist has
no suitable contextual match, record a skipped cue rather than inventing an effect.
