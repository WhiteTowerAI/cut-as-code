# Content Cards Guided UX Design

## Status

Approved for implementation. The user delegated product decisions and requested two
implementation phases. This document is the source of truth for those phases.

## Goal

Turn `video-add-content-cards` from an agent-only recipe into a guided, visual decision
flow without turning the repository into an application. The user should understand what
will be made, see real animated theme examples before choosing a theme, control card
density and editorial constraints, and explicitly approve the selected cards before a
full overlay render.

## Current-State Audit

The skill already has the expensive domain pieces:

- `build_cards_plan.py` maps reviewed semantic moments from source time to program time,
  drops moments removed by the rough cut, clamps cue duration, and preserves evidence.
- Five HyperFrames compositions demonstrate `almanac`, `teal`, `editorial`, `dotgrid`,
  and `apex` themes.
- `gallery-animated.html` compares 13 card treatments across all five themes with real,
  looping motion.
- The skill already requires one coherent theme, evidence-backed copy, safe placement,
  small review artifacts, and a transparent overlay render.

The current UX hides those capabilities:

- There is no discovery interview, so card count, purpose, required moments, caption
  conflicts, and theme are implicit.
- The skill says to start from the closest example but never opens the gallery or stops
  for a theme decision.
- Theme and target card count are not durable fields in `cards-plan.json`.
- The gallery is a display-only 65-cell matrix. It has no theme selection state or focused
  view, so all motion competes for attention.
- The `almanac` column is broken: the generated gallery points to missing `index.html`
  thirteen times, while the real file is `index-almanac.html`.
- Candidate review is prose-only. There is no project-specific view for selecting cards,
  editing draft copy, or choosing placement.

## Research

The design adopts concrete patterns from these repositories, inspected at the listed
commits on 2026-07-15:

### charmbracelet/huh (`e0035498085e722ddeee4c59c8e540f4c20f7661`)

Source: <https://github.com/charmbracelet/huh>

- Forms are split into small sequential groups instead of one long questionnaire.
- Select, multi-select, input, and confirm fields match the shape of the decision.
- Recommended options can be preselected, limits are stated at the choice, and validation
  happens before advancing.
- An accessible plain-prompt fallback preserves the workflow without the visual TUI.

Adoption: ask one question at a time, provide an evidence-based recommendation, constrain
answers to real supported values, and finish with an explicit summary confirmation.

### bombshell-dev/clack (`dc5bce8aae84a57b5863124adfaa839c1db1fa23`)

Source: <https://github.com/bombshell-dev/clack>

- A prompt group passes earlier results into later questions, so irrelevant choices can be
  skipped and defaults can be contextual.
- Cancellation is a normal outcome with a clear message, not an exception traceback.
- Defaults, validation, progress steps, and a concise final summary reduce uncertainty.

Adoption: derive the count recommendation before asking for a number, open the gallery
only when the theme question becomes relevant, preserve partial work on cancellation, and
state exactly which artifact was written after each step.

### remotion-dev/remotion (`b081e6011107f4a80d9b68cf9e77578238bce33c`)

Source: <https://github.com/remotion-dev/remotion>

- The Studio starts a local visual preview and opens the browser automatically.
- Composition selection uses a constrained picker rather than free-text IDs.
- Visual controls update the real preview immediately and can save the chosen value back to
  code; rendering remains a later action.

Adoption: show real animated compositions, not screenshots or prose theme descriptions;
keep preview and render as separate phases; persist the chosen theme in the editable plan.

### Existing Open-Recut pattern

`video-color-grade` already establishes the repository's strongest human-choice UX:
generate comparable artifacts, present them, STOP, record the selected value, then perform
the expensive render. Content cards should use the same two-phase gate.

## Approaches Considered

### A. Agent instructions only

Add interview questions and tell the user to open the gallery manually. This has the
smallest diff but leaves choices in chat history, keeps a fragile manual path, and cannot
validate supported themes.

### B. Standalone terminal wizard

Build an interactive CLI with prompts. It can validate and persist every answer, but it
moves an agentic workflow into a second conversational surface and still cannot show
motion well inside the terminal.

### C. Agent interview plus browser review (selected)

Keep the interview in the agent conversation, use small standard-library scripts for
precision, open the real gallery at the theme question, persist a brief in the canonical
plan, and add a static project-specific browser review in phase 2. This reuses the current
architecture and gives visual decisions the browser surface they need.

## End-to-End Experience

1. The agent reads `understanding.json` and `timeline.json`, counts eligible moments, and
   recommends a target card count. It does not author or render yet.
2. The agent interviews the user one question at a time:
   - purpose and audience outcome;
   - target number of cards, with the recommendation as default;
   - must-include or must-avoid moments/card types;
   - caption use and regions that must stay clear;
   - theme.
3. Immediately before the theme question, the agent runs the gallery opener. The exact
   repository `gallery-animated.html` opens through a file URI. The agent names the five
   supported values and waits for one choice.
4. The agent summarizes the answers and asks for confirmation. Cancellation leaves source
   analysis untouched and performs no render.
5. `build_cards_plan.py` writes the confirmed brief and all evidence-backed candidates to
   `work/content-cards/cards-plan.json`.
6. Phase 1 presents a concise candidate summary and lets the user choose card IDs in the
   conversation. The agent edits the plan, captures stills, and stops again for approval.
7. Phase 2 can generate a project-specific local review board. It shows each candidate's
   ID, program time, evidence summary, editable copy, placement, and selection checkbox.
   The user exports a small review JSON; a script validates and applies it to the plan.
8. Only approved cards are authored in HyperFrames and rendered as the transparent overlay.

## Interview Contract

The interview is an agent behavior, not a terminal TUI. Ask exactly one question per turn
and accept a free-form answer when the offered values do not fit. Use these defaults:

| Decision | Supported/default behavior |
|---|---|
| Purpose | `explain`, `emphasize`, `navigate`, or `convert`; free-form detail allowed |
| Count | Recommend `min(eligible moments, max(1, round(program minutes / 0.75)))` |
| Card types | Any subset of `intro`, `key-quote`, `stat`, `list`, `outro` |
| Clear regions | Any subset of `top`, `bottom`, `left`, `right`, `center` |
| Theme | Exactly one of `almanac`, `teal`, `editorial`, `dotgrid`, `apex` |

The count is a target, not an automatic truncation rule. Hiding candidates before a human
reviews their evidence would violate "human decides content; scripts do precision."

## Plan Contract

`cards-plan.json` remains the only durable domain plan. The confirmed interview is stored
under `brief`; no parallel database or config system is added.

```json
{
  "schema_version": 1,
  "target": "overlay",
  "timeline_id": "source",
  "brief": {
    "purpose": "emphasize",
    "audience": "existing customers",
    "target_card_count": 6,
    "theme": "editorial",
    "must_include_types": ["stat"],
    "avoid_regions": ["bottom"],
    "notes": "Keep product names verbatim"
  },
  "cards": []
}
```

Required validation:

- `target_card_count` is a positive integer.
- `theme`, card types, and regions are from the supported sets.
- Optional text fields are strings.
- A missing brief remains supported for compatibility with existing callers.

## Phase 1: Expose Existing Capability

### 1. Repair and focus the animated gallery

- Point `almanac` cells at `index-almanac.html` and regenerate the committed gallery.
- Add a sticky theme picker using native radio inputs.
- Selecting a theme highlights one column and dims the others; "compare all" restores the
  full matrix. The selected theme is reflected in the URL hash for a stable browser state.
- Keep the complete 13 by 5 matrix available because it is the only artifact that proves
  a theme works across all existing card treatments.

### 2. Open the gallery at the decision point

Add `scripts/open_gallery.py` using Python's `pathlib` and `webbrowser`. It resolves the
gallery relative to its own file, rejects a missing gallery with a useful error, prints the
file URI, and opens it by default. `--no-open` supports headless checks and agents that
cannot launch a GUI.

### 3. Persist the interview in the canonical plan

Extend `build_cards_plan.py` with optional brief arguments. The Python API accepts a brief
mapping and the CLI exposes supported choices. Existing three-positional-argument calls
continue producing a valid plan without `brief`.

### 4. Make the human gates explicit

Update `SKILL.md` so the interview happens before drafting, the opener runs immediately
before the theme question, the agent stops after both theme selection and card-still review,
and full rendering is prohibited before approval.

## Phase 2: Add Project-Specific Selection

### 1. Generate a review board

Add a standard-library Python generator that reads `cards-plan.json` and writes one static
HTML file under `review/03-content-cards/`. The page uses native checkboxes, text inputs,
and a placement select for each candidate. It displays the target count and chosen theme,
warns when selection count differs from the target, and downloads
`content-cards-review.json`.

The page contains no server, framework, CDN, or hidden application state. Candidate data is
embedded as escaped JSON, so it works from `file://` and is reproducible from the plan.

### 2. Validate and apply the review

Add a script that reads the plan and exported review JSON, rejects unknown/duplicate card
IDs and invalid placement values, keeps only selected cards, marks copy/placement/visual
treatment approved, and writes the plan atomically through `projectlib.write_json`.

### 3. Integrate the second gate

Update the skill to open the generated review board, stop for the user's export, apply it,
then capture stills. The existing final still review remains mandatory; browser form approval
does not prove visual fit against the real footage.

## Error Handling

- Missing gallery: fail before asking for a theme and print the expected absolute path.
- Browser cannot open: print the file URI and continue the interview; do not install a
  browser dependency.
- Invalid brief: reject before writing `cards-plan.json`.
- Review references unknown cards or invalid placements: reject without changing the plan.
- User cancels either gate: retain draft artifacts, keep operation status `draft`, and do not
  render the full overlay.

## Verification

- Python unit tests cover brief validation, backward-compatible plan creation, opener
  resolution without launching a browser, review HTML escaping, and review application.
- A Node check regenerates `gallery-animated.html` and confirms all 65 iframe targets exist.
- A headless Chrome screenshot verifies the gallery renders, theme selection changes the
  focused column, and the project review board has usable controls without console errors.
- The full Python `unittest` suite protects shared protocol behavior.
- Git status in the original checkout is compared before and after implementation to prove
  that only the new worktree branch changed.

## Non-Goals

- No new prompt, web, or database dependency.
- No full timeline editor or live mutation of HyperFrames source.
- No automatic ranking that silently discards semantic candidates.
- No full-length preview before the human approves small review artifacts.
- No replacement for final still-based checks against faces, captions, and graded footage.
