# Content Cards Review Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and
> execute each checkbox in order.

**Goal:** Open both decision pages automatically and review every candidate over a real video
frame with a live placement proxy.

**Architecture:** Keep the browser page as a committed skill asset. Keep Python responsible
only for plan validation, ffmpeg frame extraction, safe data injection, and output paths. Keep
the existing review JSON contract and native browser controls.

**Tech Stack:** Python standard library, ffmpeg, static HTML/CSS/JavaScript, `unittest`.

---

## File Map

- Create `skills/video-add-content-cards/assets/content-cards-review.html`: reusable UI.
- Modify `skills/video-add-content-cards/scripts/build_review_page.py`: extract frames and fill
  the template.
- Delete `skills/video-add-content-cards/scripts/open_gallery.py`: native OS commands replace it.
- Modify `skills/video-add-content-cards/SKILL.md`: new interview order and automatic open steps.
- Modify `tests/test_content_cards_ux.py`: template, extraction, payload, and UI checks.
- Modify `tests/test_skill_contracts.py`: workflow contract.

## Task 1: Lock The Workflow Contract

- [ ] Add a failing test asserting the theme choice appears before target count and required
  types, and that the old purpose and caption-region questions are absent.
- [ ] Add failing assertions for `Start-Process`, `open`, and `xdg-open`, each covering both
  `gallery-animated.html` and `content-cards-review.html`.
- [ ] Run:

```powershell
python -m unittest tests.test_skill_contracts.SkillContractTests.test_content_cards_documents_guided_human_choices -v
```

Expected: fail because the current skill references `open_gallery.py` and asks the removed
questions.

## Task 2: Lock The Template And Screenshot Contract

- [ ] Add a failing test requiring
  `skills/video-add-content-cards/assets/content-cards-review.html`.
- [ ] Add a failing builder test with a mocked ffmpeg process. Require one frame per card, the
  source-range midpoint after `-ss`, `-frames:v 1`, and a relative frame path in the injected
  payload.
- [ ] Add failing template assertions for a screenshot, placement proxy, all five placement
  selectors, live placement updates, and live copy updates.
- [ ] Keep the existing unsafe-copy fixture and assert the raw `</script>` text never appears
  in the populated HTML.
- [ ] Run:

```powershell
python -m unittest tests.test_content_cards_ux.ReviewPageTests -v
```

Expected: fail because the template is missing and the current builder emits HTML directly.

## Task 3: Implement The Reusable Review Page

- [ ] Add one dependency-free template. Render repeated candidates with DOM APIs from a
  base64 payload; do not use `innerHTML` for plan data.
- [ ] Use a fixed-aspect frame viewport. Start candidates at `bottom`, define proxy geometry
  for `top`, `bottom`, `left`, `right`, and `center`, and hide it for an empty placement.
- [ ] Update the selection count and selected-card summary; let the agent materialize the
  validated review JSON without changing schema version 1.
- [ ] Run the focused review tests and keep adjusting only until they pass.

## Task 4: Implement Frame Extraction And Injection

- [ ] Change the CLI to:

```powershell
python skills/video-add-content-cards/scripts/build_review_page.py `
  work/content-cards/cards-plan.json `
  review/03-content-cards/content-cards-review.html `
  --video input/source.mp4 `
  --timeline work/timeline.json
```

- [ ] Resolve the committed template relative to the script.
- [ ] Validate the video, active timeline, and every screenshot source range before writing
  output; clamp evidence midpoints to their containing retained clip.
- [ ] Extract 960-pixel-wide JPEGs to `content-cards-review-assets/frame-NNN.jpg` with ffmpeg.
- [ ] Replace exactly one payload marker with base64 JSON and write UTF-8 HTML.
- [ ] Run focused tests again.

## Task 5: Rewrite The Agent Workflow

- [ ] Delete `open_gallery.py` and its tests.
- [ ] Make theme the first interview question and retain only count and required types after it.
- [ ] Document the native Windows, macOS, and Linux commands and explicitly require the agent
  to run the applicable one itself.
- [ ] Document the same commands for the populated review page.
- [ ] Update the builder example with `--video` and keep both STOP gates.
- [ ] Run skill-contract and content-card UX tests.

## Task 6: Verify The Real Workflow

- [ ] Run the complete suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

- [ ] Generate the review page from the Musk fixture and its existing cards plan.
- [ ] Confirm the generated asset count equals the candidate count and every JPEG is nonblank.
- [ ] Open the generated page with `Start-Process`.
- [ ] Capture desktop and narrow browser screenshots. Change placement and copy, then verify the
  proxy moves and its label changes without console errors.
- [ ] Re-read the four user requirements against `SKILL.md`, the template, generated artifacts,
  and fresh test output before completion.
