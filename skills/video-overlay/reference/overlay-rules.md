# Title Overlay Rules

These rules define the v1 visual and layout contract for `video-overlay`.

## Scope

Version 1 supports one title overlay on an existing vertical short video. It does
not support logos, watermarks, CTAs, progress bars, animation, or multiple
overlay items.

The input is already vertical. It commonly comes from `video-vertical-reframe` as
`vertical.mp4`. If the input is not vertical, the workflow should stop or warn
clearly instead of reframing inside this skill.

## Visual Direction

The default title style should be close to the `video-to-captions` shorts visual
language:

- bold short-video typography;
- large title text sized for vertical viewing;
- high contrast over real footage;
- white primary text with black stroke or strong shadow;
- green, yellow, or orange theme accents that feel related to shorts caption
  highlight colors.

Use `shorts-title` as the preset. Use `green`, `yellow`, and `orange` as themes.
Do not create official presets named `shorts-green`, `shorts-yellow`, or
`shorts-orange`.

## Layout

Default position is `upper-third`.

Supported v1 positions:

- `top`;
- `upper-third`;
- custom y ratio.

The title must avoid the bottom captions area. Do not place the v1 title in the
lower-third region by default, because `video-to-captions` shorts captions are
expected to occupy the lower part of the frame.

## Vertical Input and Future Extensibility

V1 only accepts vertical input video. Future versions may support horizontal
video, so layout math should be based on source width, source height, and ratios.
Do not hard-code a single pixel resolution such as 1080x1920 into the design
contract.

The v1 implementation can assume a vertical frame for validation and defaults,
but safe areas, title width, title y position, stroke width, and font size should
be expressed as ratios where practical.

## Text Handling

Do not rewrite the user's title unless the user explicitly asks.

Keep titles short enough to read quickly. Long titles may wrap, but the preview
workflow should make overflow or crowding visible before final render. If a title
is too long to fit cleanly, ask the user to shorten it or confirm a smaller
config value.

## Animation

V1 does not implement animation. If a config field for animation exists in a
future phase, its v1 value should remain `none`.
