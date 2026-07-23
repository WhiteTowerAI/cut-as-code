# Video To Shorts

`video-to-shorts` turns a verified Open Recut main delivery into reviewed
horizontal and optional vertical derivatives. Project mode consumes the shared
source transcript and `timeline.json`, so every candidate uses the same program
clock as `final/final-video.mp4` and retains source traceability.

`/video-understand` is a prerequisite.

The canonical workflow is:

1. Map `work/understand/transcript.json` through `work/timeline.json`.
2. Inspect transcript and visual context; author complete candidate moments.
3. Validate word-exact excerpts and six-dimension scores.
4. Review an interactive candidate page and record a hash-bound human or explicitly delegated agent selection.
5. Write `work/shorts/shorts-plan.json` with dependency revisions and ranges.
6. Extract seeked keep ranges into `final/shorts/*-horizontal.mp4`.
7. Optionally review an interactive vertical page, approve, and render a deterministic 9:16 plan.

Extraction treats the selected final word and the media endpoint separately. Every
short targets 0.30 seconds and requires at least 0.25 seconds of release audio after
the selected content, including when semantic boundary refinement is disabled. The
short transcript excludes any following words that appear only inside this media
handle.

Shorts are recorded as a derived `project.json` operation but are not added to
the main sequence. They never modify or re-render the main delivery.

Project outputs are separated by purpose:

- durable decisions and transcripts: `work/shorts/`
- disposable frames and intermediate media: `work/cache/shorts/`
- immutable interactive pages and review-ID-scoped evidence, plus flat latest convenience outputs: `review/06-shorts/`
- delivered media: `final/shorts/`

Vertical strategies are `STATIC_CROP`, `SCENE_CROP`, `LETTERBOX`, and
`REVIEW_REQUIRED`. Plans preserve FPS as `{num, den}`. Python validates an
agent-authored crop; it does not invent coordinates or claim continuous tracking.

New vertical plans may bind the original verified delivery and the horizontal
extraction report. Preview review remains based on the approved horizontal short, but
formal rendering maps short-relative segments through `keep_spans` and reads the
original delivery directly. This removes the former horizontal-H.264-to-vertical-H.264
generation. Formal output uses `libx264 -preset slow -crf 16`; legacy plans without the
binding remain supported.

See [SKILL.md](SKILL.md) for the complete protocol, commands, candidate contract,
review modes, vertical rules, compatibility behavior, and self-check.

Run the executable protocol check from the repository root:

```powershell
python skills/video-to-shorts/scripts/check_project_protocol.py
```

Standalone `shorts-candidates.v2`, `shorts-plan.v2`, legacy human reviews, and
`short_XX/source.mp4` vertical inputs remain supported when project options are
absent.
