# Title Source Rules

These rules define how `video-overlay` gets the title text for v1.

## Source A: Manual User Title

Use the exact title supplied by the user.

Do not rewrite, summarize, translate, or uppercase the title unless the user
explicitly asks. Style may visually transform text in a renderer only if the
config says so, but the stored title text should remain user-authored.

## Source B: video-to-shorts Artifact

When reading a title from `video-to-shorts`, prefer `shorts_plan.json` because it
is the structured source of truth. `shorts_plan_preview.html` is a review artifact
and should be used only as a fallback when JSON is unavailable.

Supported short selectors for v1:

- `order`;
- `id`;
- `short_id`;
- `filename` or a `short_XX` path hint.

The selected short's title may be copied into the overlay config or a dedicated
intermediate title-source JSON in a later phase. Do not modify
`shorts_plan.json` or `shorts_plan_preview.html`.

## Failure Rules

Stop and report a clear issue when:

- the selected short cannot be found;
- more than one short matches the selector;
- the matched short has no title;
- the title field is empty or whitespace only;
- only HTML is available and the expected title table cannot be parsed.

Do not invent a fallback title. Ask the user for a manual title instead.

## Future Source C: captions Summary

Future versions may read `video-to-captions` output or short-relative captions
and use an LLM to summarize a title. V1 does not implement this path.

If this is added later, it should remain explicit in config and should not
overwrite a manually provided user title without confirmation.
