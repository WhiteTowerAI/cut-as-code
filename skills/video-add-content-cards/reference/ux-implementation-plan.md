# Content Cards Guided UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guided interview, an automatically opened and selectable animated theme gallery, durable brief choices, and a project-specific card review board to `video-add-content-cards`.

**Architecture:** Keep the agent conversation as the interview surface. Use Python standard-library scripts for validated plan and review-file transformations, and generated static HTML for visual choices. Preserve the V1 `cards-plan.json` contract and all existing three-argument CLI callers.

**Tech Stack:** Python 3 standard library, Node.js standard library, static HTML/CSS/JavaScript, Python `unittest`, headless Chrome for visual verification.

---

## File Map

- Modify `skills/video-add-content-cards/examples/build-gallery.mjs`: generate a working, focusable theme gallery.
- Regenerate `skills/video-add-content-cards/examples/gallery-animated.html`: committed visual artifact opened for users.
- Create `skills/video-add-content-cards/scripts/open_gallery.py`: resolve and launch that artifact.
- Modify `skills/video-add-content-cards/scripts/build_cards_plan.py`: validate and persist the interview brief.
- Create `skills/video-add-content-cards/scripts/build_review_page.py`: generate a project-specific static review form.
- Create `skills/video-add-content-cards/scripts/apply_cards_review.py`: validate exported choices and update the canonical plan.
- Modify `skills/video-add-content-cards/SKILL.md`: define the interview and two human STOP gates.
- Create `tests/test_content_cards_ux.py`: one focused runnable check for the guided UX.

## Task 1: Phase 1 Selectable Animated Theme Gallery

**Files:**
- Create: `tests/test_content_cards_ux.py`
- Modify: `skills/video-add-content-cards/examples/build-gallery.mjs`
- Modify: `skills/video-add-content-cards/examples/gallery-animated.html`

- [ ] **Step 1: Write failing gallery integrity tests**

```python
class GalleryTests(unittest.TestCase):
    def test_every_animated_iframe_target_exists(self):
        subprocess.run(["node", str(EXAMPLES / "build-gallery.mjs")], check=True)
        document = (EXAMPLES / "gallery-animated.html").read_text(encoding="utf-8")
        targets = re.findall(r'<iframe[^>]+src="([^"#]+)', document)
        self.assertEqual(65, len(targets))
        for target in set(targets):
            self.assertTrue((EXAMPLES / target).is_file(), target)

    def test_gallery_offers_native_theme_selection(self):
        document = (EXAMPLES / "gallery-animated.html").read_text(encoding="utf-8")
        self.assertIn('name="theme"', document)
        self.assertIn('value="all"', document)
        for theme in ("almanac", "teal", "editorial", "dotgrid", "apex"):
            self.assertIn(f'value="{theme}"', document)
            self.assertIn(f'data-theme="{theme}"', document)
```

- [ ] **Step 2: Run the tests and verify the missing Almanac target fails**

Run: `python -m unittest tests.test_content_cards_ux.GalleryTests -v`

Expected: FAIL because `index.html` is absent and the picker markup is absent.

- [ ] **Step 3: Repair the target and generate a focused picker**

Change the Almanac entry to:

```javascript
["almanac", "", "index-almanac.html"],
```

Generate a native radio group before the table, add `data-theme` to each theme header and
cell, and add a script that reads/writes `#theme=<name>` and hides non-selected columns.
`all` remains the initial value. Focused mode increases the unitless iframe scale while a
small-screen media query keeps the table usable.

- [ ] **Step 4: Regenerate and verify**

Run: `node skills/video-add-content-cards/examples/build-gallery.mjs`

Expected: `wrote gallery.html + gallery-animated.html (13x5 grid)`.

Run: `python -m unittest tests.test_content_cards_ux.GalleryTests -v`

Expected: 2 tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_content_cards_ux.py skills/video-add-content-cards/examples/build-gallery.mjs skills/video-add-content-cards/examples/gallery-animated.html
git commit -m "fix(content-cards): [phase 1] make theme gallery selectable"
git push
```

## Task 2: Phase 1 Gallery Opener

**Files:**
- Modify: `tests/test_content_cards_ux.py`
- Create: `skills/video-add-content-cards/scripts/open_gallery.py`

- [ ] **Step 1: Write failing opener tests**

```python
class GalleryOpenerTests(unittest.TestCase):
    def test_resolves_committed_animated_gallery(self):
        uri = OPENER.open_gallery(launch=False)
        self.assertTrue(uri.startswith("file:"))
        self.assertTrue(OPENER.gallery_path().is_file())

    def test_launch_uses_default_browser(self):
        with mock.patch.object(OPENER.webbrowser, "open", return_value=True) as browser:
            uri = OPENER.open_gallery()
        browser.assert_called_once_with(uri)
```

- [ ] **Step 2: Run tests and verify the missing module fails**

Run: `python -m unittest tests.test_content_cards_ux.GalleryOpenerTests -v`

Expected: FAIL because `open_gallery.py` does not exist.

- [ ] **Step 3: Implement the standard-library opener**

```python
def gallery_path():
    path = Path(__file__).resolve().parents[1] / "examples/gallery-animated.html"
    if not path.is_file():
        raise FileNotFoundError(f"animated gallery not found: {path}")
    return path


def open_gallery(launch=True):
    uri = gallery_path().as_uri()
    if launch:
        webbrowser.open(uri)
    return uri
```

Add an argparse `--no-open` flag and always print the URI so headless agents have a useful
fallback.

- [ ] **Step 4: Verify CLI and tests**

Run: `python skills/video-add-content-cards/scripts/open_gallery.py --no-open`

Expected: prints a `file:///.../gallery-animated.html` URI and exits 0.

Run: `python -m unittest tests.test_content_cards_ux.GalleryOpenerTests -v`

Expected: 2 tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_content_cards_ux.py skills/video-add-content-cards/scripts/open_gallery.py
git commit -m "feat(content-cards): [phase 1] open gallery at theme choice"
git push
```

## Task 3: Phase 1 Durable Interview Brief

**Files:**
- Modify: `tests/test_content_cards_ux.py`
- Modify: `skills/video-add-content-cards/scripts/build_cards_plan.py`

- [ ] **Step 1: Write failing brief tests**

```python
def test_guided_brief_is_persisted(self):
    brief = {
        "purpose": "emphasize",
        "audience": "existing customers",
        "target_card_count": 3,
        "theme": "editorial",
        "must_include_types": ["stat"],
        "avoid_regions": ["bottom"],
        "notes": "Keep product names verbatim",
    }
    plan = BUILDER.build_plan(understanding_fixture(), timeline_fixture(), brief)
    self.assertEqual(brief, plan["brief"])

def test_invalid_brief_is_rejected(self):
    for brief in (
        {"target_card_count": 0},
        {"theme": "unknown"},
        {"must_include_types": ["chart"]},
        {"avoid_regions": ["diagonal"]},
    ):
        with self.subTest(brief=brief), self.assertRaises(ValueError):
            BUILDER.validate_brief(brief)
```

- [ ] **Step 2: Run tests and verify missing API fails**

Run: `python -m unittest tests.test_content_cards_ux.BriefTests -v`

Expected: FAIL because `validate_brief()` and the third `build_plan()` argument are absent.

- [ ] **Step 3: Implement minimal validation and CLI flags**

Define supported theme, card-type, and region sets. `validate_brief()` returns a shallow
copy after checking types and values. `build_plan(..., brief=None)` includes `brief` only
when supplied, preserving old output for old callers.

Add optional argparse flags:

```python
parser.add_argument("--purpose")
parser.add_argument("--audience")
parser.add_argument("--target-card-count", type=int)
parser.add_argument("--theme", choices=sorted(THEMES))
parser.add_argument("--must-include-type", action="append", choices=sorted(CARD_TYPE_NAMES))
parser.add_argument("--avoid-region", action="append", choices=sorted(REGIONS))
parser.add_argument("--notes")
```

Build a brief only when at least one flag is present, then pass it to `build_plan()`.

- [ ] **Step 4: Verify focused and compatibility tests**

Run: `python -m unittest tests.test_content_cards_ux.BriefTests tests.test_cards_plan -v`

Expected: all tests pass, including the unchanged three-positional-argument CLI test.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_content_cards_ux.py skills/video-add-content-cards/scripts/build_cards_plan.py
git commit -m "feat(content-cards): [phase 1] persist interview brief"
git push
```

## Task 4: Phase 1 Guided Skill Workflow

**Files:**
- Modify: `tests/test_content_cards_ux.py`
- Modify: `tests/test_skill_contracts.py`
- Modify: `skills/video-add-content-cards/SKILL.md`

- [ ] **Step 1: Write a failing contract test**

```python
def test_content_cards_documents_guided_human_choices(self):
    skill = text("skills/video-add-content-cards/SKILL.md")
    for required in (
        "target card count",
        "scripts/open_gallery.py",
        "gallery-animated.html",
        "Present + STOP",
        "brief",
    ):
        self.assertIn(required.lower(), skill.lower())
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_skill_contracts.SkillContractTests.test_content_cards_documents_guided_human_choices -v`

Expected: FAIL because the guided flow is undocumented.

- [ ] **Step 3: Rewrite the workflow in decision order**

Document these exact stages: inspect eligible moments; interview one question at a time;
run the opener immediately before theme selection; summarize and confirm; build the plan
with brief flags; review candidate IDs and stills; present and STOP; author and render only
after approval. Include the five theme names and supported brief values.

- [ ] **Step 4: Verify contracts**

Run: `python -m unittest tests.test_skill_contracts tests.test_content_cards_ux -v`

Expected: all tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_skill_contracts.py skills/video-add-content-cards/SKILL.md
git commit -m "docs(content-cards): [phase 1] add interview and approval gates"
git push
```

## Task 5: Phase 2 Project Review Board

**Files:**
- Modify: `tests/test_content_cards_ux.py`
- Create: `skills/video-add-content-cards/scripts/build_review_page.py`

- [ ] **Step 1: Write failing HTML-generation tests**

```python
def test_review_page_contains_safe_editable_candidates(self):
    plan = plan_fixture(copy="</script><b>unsafe</b>")
    document = REVIEW_PAGE.build_review_page(plan)
    self.assertIn('type="checkbox"', document)
    self.assertIn('name="placement"', document)
    self.assertIn('id="selection-count"', document)
    self.assertIn("editorial", document)
    self.assertNotIn("</script><b>unsafe</b>", document)
    self.assertIn("Download review JSON", document)
```

- [ ] **Step 2: Run and verify missing module failure**

Run: `python -m unittest tests.test_content_cards_ux.ReviewPageTests -v`

Expected: FAIL because `build_review_page.py` is absent.

- [ ] **Step 3: Generate a dependency-free review page**

Use `html.escape()` for attribute and text values. Render one repeated candidate article
per card with a checkbox, copy input, and native placement select. Embed only the chosen
theme, target count, and candidate fields. A short inline script updates an `aria-live`
selection count and downloads this schema:

```json
{
  "schema_version": 1,
  "cards": [
    {"id": "card-001", "selected": true, "copy": "200 customers", "placement": "top"}
  ]
}
```

The CLI accepts `PLAN OUTPUT` and `--open`; it writes UTF-8 HTML and opens the resulting
file URI only when requested.

- [ ] **Step 4: Verify generated HTML**

Run: `python -m unittest tests.test_content_cards_ux.ReviewPageTests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_content_cards_ux.py skills/video-add-content-cards/scripts/build_review_page.py
git commit -m "feat(content-cards): [phase 2] generate card review board"
git push
```

## Task 6: Phase 2 Apply Review and Integrate the Gate

**Files:**
- Modify: `tests/test_content_cards_ux.py`
- Create: `skills/video-add-content-cards/scripts/apply_cards_review.py`
- Modify: `skills/video-add-content-cards/SKILL.md`

- [ ] **Step 1: Write failing review-application tests**

```python
def test_review_keeps_selected_cards_and_approves_fields(self):
    updated = APPLY.apply_review(plan_fixture(), review_fixture(selected_ids={"card-001"}))
    self.assertEqual(["card-001"], [card["id"] for card in updated["cards"]])
    self.assertEqual("approved", updated["cards"][0]["copy"]["status"])
    self.assertEqual("editorial", updated["cards"][0]["visual_treatment"]["theme"])
    self.assertEqual("approved", updated["review"]["status"])

def test_review_rejects_unknown_duplicate_or_missing_ids(self):
    for review in invalid_review_fixtures():
        with self.subTest(review=review), self.assertRaises(ValueError):
            APPLY.apply_review(plan_fixture(), review)
```

- [ ] **Step 2: Run and verify missing module failure**

Run: `python -m unittest tests.test_content_cards_ux.ApplyReviewTests -v`

Expected: FAIL because `apply_cards_review.py` is absent.

- [ ] **Step 3: Validate then apply choices**

Require schema version 1 and exactly one review entry for every plan card. Reject unknown,
duplicate, missing IDs, blank selected copy, and placements outside the supported regions.
Use the plan brief's theme. Keep selected cards only; mark copy, placement, and visual
treatment approved; add an approved top-level review summary.

For CLI writes, validate completely first, write a sibling temporary file with
`projectlib.write_json()`, then replace the requested output with `os.replace()`.

- [ ] **Step 4: Document and verify the phase 2 STOP gate**

Add the review-page and apply commands to `SKILL.md`. Require the agent to open the board,
STOP for exported JSON, apply it, capture real-footage stills, and STOP again before render.

Run: `python -m unittest tests.test_content_cards_ux tests.test_skill_contracts -v`

Expected: all focused and contract tests pass.

- [ ] **Step 5: Commit and push**

```bash
git add tests/test_content_cards_ux.py skills/video-add-content-cards/scripts/apply_cards_review.py skills/video-add-content-cards/SKILL.md
git commit -m "feat(content-cards): [phase 2] apply approved card choices"
git push
```

## Task 7: End-to-End Verification

**Files:** none unless verification finds a defect.

- [ ] **Step 1: Verify gallery generation and all target files**

Run: `node skills/video-add-content-cards/examples/build-gallery.mjs`

Run: `python -m unittest tests.test_content_cards_ux.GalleryTests -v`

Expected: generator exits 0; all 65 iframe targets exist.

- [ ] **Step 2: Verify the full Python suite**

Run: `python -m unittest discover -s tests -p "test_*.py"`

Expected: all tests pass with zero failures or errors.

- [ ] **Step 3: Verify browser behavior**

Use headless Chrome at 1920x1080 and a narrow viewport to capture the animated gallery in
`all` and `#theme=editorial` states plus a fixture review board. Confirm nonblank frames,
working motion cells, no missing-file tiles, readable controls, and no overlap.

- [ ] **Step 4: Verify commit and isolation requirements**

Run: `git log --format="%h %s" origin/feat/video-project-protocol-v1..HEAD`

Expected: every commit subject includes `[phase 1]` or `[phase 2]`.

Run status in both `.worktree` and the original checkout. Expected: the feature worktree is
clean and the original checkout has no new changes caused by this implementation.
