# Anti-AI Aesthetic Protocol

Use this protocol when defining, adapting, and reviewing every motion-graphics cue. It is an
original motion-graphics synthesis of the sources below, not copied prompt text. The source
systems primarily address web/UI design; apply only the principles that survive compositing over
real footage.

## Sources

All links are pinned to the reviewed commit.

- Open Design, SpaceX design system, Apache-2.0:
  <https://github.com/nexu-io/open-design/blob/698a17aac20226d58ced0d9843c9e75f344ecbf9/design-systems/spacex/DESIGN.md>
- Open Design, Editorial design system, Apache-2.0:
  <https://github.com/nexu-io/open-design/blob/698a17aac20226d58ced0d9843c9e75f344ecbf9/design-systems/editorial/DESIGN.md>
- ibelick/ui-skills, `baseline-ui`, MIT:
  <https://github.com/ibelick/ui-skills/blob/146fcd0b34fca2d80333b120d67f5009ccf58b28/skills/baseline-ui/SKILL.md>
- SDesign, MIT; its design-system assets declare derivation from Open Design under Apache-2.0:
  <https://github.com/simonlin1212/SDesign/blob/da61779021ee0acec330334cfefed67bd0013086/SKILL.md>
- AI Design Director, MIT:
  <https://github.com/airudotsh/ai-design-director/blob/b26bf6dac6bbdcce03f6e388c868c8cba1c2e749/skills/ai-design-director/SKILL.md>
- Anti-slop Website Prompts, MIT:
  <https://github.com/mah-claude/anti-slop-website-prompts/blob/bfce6e5b80bb87f5427d06b6ed2000db17e47c8f/SKILL.md>

## Direction Card

Before recipe search, write these cue-local decisions in working notes. They guide authoring but
do not add fields to the plan schema.

- `visual_thesis`: one sentence explaining what an uninformed viewer should understand and what
  visual relationship makes that meaning visible.
- `design_lens`: one named lens, such as editorial typography, technical diagram, or cinematic
  image mask. Define its grid, type hierarchy, surface treatment, and color relationship. Do not
  combine unrelated lenses.
- `layout_grammar`: the footage-derived alignment, scale contrast, negative space, and reading
  order. Do not default to centered web-hero composition.
- `signature_beat`: one memorable recipe-owned event tied to a spoken word, edit point, gesture,
  or visual change. Other motion supports this beat instead of competing with it.
- `shot_exclusion_zones`: protected faces, heads, hands or key gestures, captions, content cards,
  logos, and essential footage details across the complete animated path.
- `semantic_media_subjects`: for every framed photo, image mask, texture window, or thumbnail,
  record its origin, recognizable subject, cue relevance, crop rationale, and review result. Use
  `none` when the cue contains no raster insert; never leave the decision implicit.
- `forbidden_signals`: the default AI cliches below plus shot-specific forms that would contradict
  the footage or editorial tone.

Treat vague taste words such as `premium`, `modern`, `clean`, `futuristic`, or `cinematic` as
incomplete. Translate each one into concrete composition, typography, palette, material, and
motion choices before authoring.

## Default Forbidden Signals

Reject a cue when any item is central to its design without specific content or brand evidence:

- purple-blue or multicolor gradients used as an innovation shortcut;
- glass panels, frosted surfaces, decorative blur, or glow used as the primary material;
- HUD frames, arbitrary grids, scanning lines, fake charts, fake coordinates, or invented data;
- pill labels, eyebrow badges, chips, card stacks, bento tiles, or dashboard chrome;
- sparkles, nodes, network diagrams, particles, or icons that carry no literal cue meaning;
- repeated headline/badge/caption versions of the same fact;
- generic technology copy such as `visionary`, `future`, `innovation`, `unlock`, `transform`, or
  `revolutionary` unless the words are direct source evidence;
- default centered headline plus subtitle composition when the shot provides a stronger axis;
- generic fade, float, parallax, bounce, or elastic overshoot applied without an information role;
- raw recipe demo copy, recipe labels, web controls, UI states, or component-library styling.
- arbitrary crops of scenery, set lighting, clothing, architecture, or background texture used
  only because a recipe contains an image slot.

The list is contextual, not a ban on individual primitives. A literal network diagram may explain
a network; a source brand may own a gradient. Record the evidence that makes the otherwise
forbidden choice necessary. Without that evidence, remove it.

## Footage-First Construction

1. Let the footage carry identity, atmosphere, texture, and depth. Do not cover it with an opaque
   interface merely to make the overlay noticeable.
2. Establish hierarchy with scale, weight, alignment, crop, negative space, and timing before
   adding borders, shadows, effects, or secondary labels.
3. Use one primary message, one focal mechanism, and at most one accent color per cue unless the
   footage or an established brand system proves otherwise.
4. Make typography role-based. Display, support, and source labels must differ for a reason; avoid
   arbitrary microtext and universal all-caps labels.
5. Give motion at least one information role: reveal hierarchy, connect a state or spatial change,
   or explain a concept. A fade or float alone is not a motion thesis.
6. Preserve a readable hold. Choreograph anticipation, signature beat, settle, and exit around the
   cue's meaning; use at most one pronounced overshoot or rebound.
7. Keep the selected recipe recognizable through its core mechanic, not its demo layout or visual
   clutter.
8. For an `opener`, reject an ordinary broadcast name strap, corner bug, or lower-third promoted
   to the opening seconds. Use opener-scale hierarchy and make the signature mechanism establish a
   meaningful relationship between footage, evidence, and title. A mask that merely uncovers an
   otherwise generic lockup and leaves no authored spatial or semantic relationship is insufficient.
9. Treat every photo frame or image mask as editorial evidence, not decoration. The image must show
   a recognizable person, object, place, document, event, or visual state that supports the exact
   cue. A nearby label does not make an ambiguous crop meaningful. If the subject does not survive
   the smallest, largest, and settled crop at normal playback size, or if text, borders, or other
   graphics cover its identifying features, choose another frame, redesign the container, remove
   the image, or skip the cue.

## Semantic Media Receipt

Record one working-note entry for every raster insert before adapting the recipe:

- `search_priority`: for a named person, place, object, document, or event, record the authoritative
  or clearly licensed online sources searched first. Prefer a directly attributable online image
  whose subject survives the intended crop;
- `origin`: for external media, the directly verifiable source page, creator, exact license
  evidence, downloaded local file, and SHA-256; for source footage, the bound asset plus exact
  source timestamp;
- `fallback_reason`: required only for source-video frames. State that no suitable licensed online
  image was found after the recorded search, or that network access failed. Convenience, visual
  style, and an easier crop are not valid reasons;
- `recognizable_subject`: the person, object, place, document, event, or visual state a viewer can
  identify from the framed image itself;
- `cue_relevance`: how that subject supports the transcript claim, editorial purpose, or named
  identity without relying on decorative association;
- `crop_rationale`: why the selected crop retains the subject's identifying evidence across the
  complete mask, scale, pan, entrance, and exit path;
- `review_result`: `pass` only after the moving composite proves the subject remains recognizable
  at normal playback size. Otherwise replace, redesign, remove, or skip it.

Do not extract a video frame before performing the recorded online-first search. For video-derived
fallback media, inspect the exact source frame and reject blur, closed-eye accidents, partial faces,
accidental background emphasis, or crops that remove the identifying action or object. For
web-derived media, the preview image alone is not provenance: bind the downloaded file, source
page, author, license, and hash. Do not use an asset merely because it is aesthetically compatible
with the recipe.

## Review Gate

Review the moving composite over actual footage, never the overlay alone. Use the existing five
plan judgments and also state `distinctiveness/editorial_value` in the review working notes.

- `semantic_clarity`: What does an uninformed viewer believe the graphic means? Reject ambiguity,
  contradiction, invented claims, or a decorative effect with no answer.
- `composition`: Does the shot determine alignment, scale, negative space, and visual balance?
- `readability`: Is the primary message clear at normal playback size throughout its intended hold?
- `motion_quality`: Does the signature beat read cleanly, with continuous paths and no generic or
  repeated flourish?
- `footage_integration`: Does the cue belong to this exact shot without hiding protected people,
  gestures, captions, cards, or story evidence?
- `semantic_media`: Does every framed or masked image show its recorded subject clearly, remain
  necessary to the cue, and preserve that meaning through the complete animated crop path?
- `distinctiveness/editorial_value`: Is there a specific editorial viewpoint and memorable mechanic,
  or could the result be swapped into an unrelated SaaS, AI, or technology video unchanged?

Any protected-zone collision, unclear primary meaning, meaningless media crop, or central forbidden
signal fails the cue regardless of the other judgments. On failure, name the observed signal,
strengthen only the rule that failed, and rebuild. Do not respond by recoloring the same composition
or adding decoration.
