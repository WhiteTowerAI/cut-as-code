---
name: video-overlay
description: >
  Add a single title overlay to an existing vertical short video. Use after
  video-vertical-reframe or another workflow has already produced a vertical
  MP4, when the user wants a preview-first title treatment for short-form
  output. This skill does not cut video, generate captions, reframe footage,
  modify shorts plans, or add logos, watermarks, CTAs, progress bars,
  animations, or multiple overlay items.
---

# Video Overlay

`video-overlay` adds one video-level title overlay to an existing vertical short
video. Version 1 is intentionally narrow: one title, one vertical input video,
preview first, then final render only after confirmation.

The usual input is `vertical.mp4` from `video-vertical-reframe`. The output is an
MP4 with the title overlay composited onto the same video.

## Boundary

This skill owns:

- title overlay planning for one vertical short video;
- title source selection from either user input or existing `video-to-shorts`
  artifacts;
- preview generation before final render;
- final title-overlay compositing after the user confirms a preview.

This skill does not own:

- cutting, trimming, or reordering footage;
- horizontal-to-vertical reframing;
- caption generation or caption rendering;
- modifying `shorts_plan.json` or `shorts_plan_preview.html`;
- logo, watermark, CTA, progress bar, animation, or multiple overlay items.

If the input video is not vertical, stop with a clear message and suggest running
`video-vertical-reframe` first. The v1 workflow supports vertical input only, but
implementation should still compute layout from source width, height, and safe
areas rather than hard-coding one 9:16 resolution.

## Preview-First Workflow

Always preview before final render unless the user explicitly asks to skip
preview.

1. Resolve the title text from user input or `video-to-shorts` artifacts.
2. Write or update the title/style config.
3. Generate preview PNGs or an HTML preview for review.
4. Wait for the user to confirm or request a config-only adjustment.
5. After confirmation, render the final MP4.

For visual feedback, change config values first. Do not edit renderer internals
for ordinary style tuning.

## Title Sources

Supported in v1:

- Manual title from the user. Do not rewrite or summarize it unless explicitly
  asked.
- Existing `video-to-shorts` title. Prefer reading structured `shorts_plan.json`;
  use `shorts_plan_preview.html` only as a fallback when JSON is unavailable.

Future work may derive a title from captions or transcript text, but v1 does not
call an LLM to generate titles.

See `reference/title-source-rules.md` for selection and failure rules.

## Style and Layout

The v1 visual target is a short-form title that feels close to the
`video-add-captions` shorts caption style: bold, readable, high-contrast, and
suited to vertical short video.

Use one preset concept:

- `shorts-title`

Use theme options for color variations:

- `green`
- `yellow`
- `orange`

Do not treat `shorts-green`, `shorts-yellow`, or `shorts-orange` as official
presets. They are only preview candidate labels if needed.

Place the title in the top or upper-third region by default. The title must not
cover the bottom captions area.

See `reference/overlay-rules.md` for visual and layout rules.

## Safe Edit Points

Agents may safely edit:

- title text;
- title source selector;
- style/config files;
- preview candidate config;
- intermediate title-source JSON, if a later phase adds one.

Agents should not modify these for ordinary use:

- title renderer components;
- Root composition;
- animation helpers;
- preset resolver internals.

Modify renderer internals only when expanding the skill capability or fixing a
confirmed renderer bug.

## Expected Working Shape

Later phases should add Remotion examples and scripts under this structure:

```text
skills/video-overlay/
  SKILL.md
  examples/
  scripts/
  reference/
```

Keep this skill independent from `video-add-captions`, `video-to-shorts`, and
`video-vertical-reframe`. It may read their durable outputs, but it must not
change their implementations or owned artifacts.
