# Content Cards Review UX Design

## Status

Approved by the requested UX changes on 2026-07-16. `SKILL.md` remains the executable
specification; this file records the interaction and data-flow decisions behind it.

## Goal

Make theme and candidate review visual without turning the skill into an application. The
agent opens both browser artifacts itself, asks only decisions that affect card selection,
and shows placement against the real footage before the selection is returned.

## Interview

Ask one question per turn in this order:

1. Open the committed animated gallery and ask for one theme.
2. Recommend and ask for a target card count.
3. Ask whether any supported card types are required.
4. Summarize and confirm.

Do not ask for a purpose category or caption-clear regions. Those questions did not help
the user make the next visible decision. Existing optional brief fields remain accepted by
`build_cards_plan.py` for compatibility, but the normal interview does not solicit them.

## Browser Opening

Use the native command for the current OS and run it on the user's behalf:

- Windows PowerShell: `Start-Process (Resolve-Path '<file>')`
- macOS: `open <file>`
- Linux desktop: `xdg-open <file>`

Apply the same rule to `examples/gallery-animated.html` and the project review HTML. Do not
replace the action with a URI or ask the user to find and click the file.

## Review Template

Keep the reusable page at `assets/content-cards-review.html`. The Python builder reads the
template, extracts one JPEG per candidate with ffmpeg, injects a base64-encoded JSON payload,
and writes the populated review page. It does not construct page markup in Python.

Screenshots live beside the output in `content-cards-review-assets/`. Use the active timeline
to clamp each evidence midpoint to the containing retained clip. This avoids both black or
boundary frames at the range start and removed footage beyond a cut. Reject legacy cards
without a source range instead of seeking source media with a program timestamp. Use generated
frame names rather than card IDs as paths.

## Candidate Interaction

Each candidate is one row with:

- selection checkbox, ID, type, and time;
- editable copy plus native visual-treatment and placement selects;
- a collapsible chart editor for chart layouts;
- the corresponding video frame with an overlaid gray placement proxy.

Every candidate starts unselected at `bottom`. `stat` candidates suggest `metric-spotlight`,
`list` candidates suggest `side-by-side`, and the reviewer can select only treatments supported
by the canonical card type. Changing placement immediately moves the proxy
to `top`, `bottom`, `left`, `right`, or `center`. Changing copy updates the proxy label;
`Unplaced` hides it. The proxy is deliberately neutral: it previews occupied space and
collision risk, not the final theme treatment.

For `bar-chart`, `pie-chart`, and `line-chart`, the editor exposes dimension,
metric, unit, period, point labels, point values, and evidence references. It
enforces the active layout's point-count range and reports invalid labels,
values, evidence, and chart-specific totals before the summary can be copied.
The neutral proxy expands to the approximate chart footprint.

When a captions plan is available, the review payload contains only caption
cue ranges and their actual resolved top, center, or bottom region. The frame
preview draws those occupied regions over the real source frame. This is a
candidate-stage warning; final clearance still uses the rendered caption
overlay composited with the footage and content card.

The page copies a readable selected-card summary back to the agent. Chart cards
add a deterministic `data={...}` line immediately after the normal card line.
Card blocks are separated by a blank line, and summary text is written with
`textContent`. The agent materializes the existing review JSON schema and runs
the existing validator. No server, framework, CDN, or new package is introduced.

## Errors And Checks

- Reject a missing video, template, payload marker, source range, invalid time range, or failed
  ffmpeg frame before replacing the current review artifacts.
- Base64-encode injected JSON so user copy cannot terminate the template's script element.
- Validate every review entry before copying and replacing the plan; never partially apply a review.
- Unit-test template use, frame times, escaped payload data, five placement states, and skill
  workflow text.
- Run the full Python suite, then generate the real Musk review page and inspect desktop and
  narrow screenshots plus live placement changes before declaring completion.
