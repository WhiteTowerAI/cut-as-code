import inspect
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.protocol_testlib import load_script, timeline_fixture
from tests.test_cards_plan import understanding_fixture


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/video-add-content-cards/examples"
OPENER_PATH = ROOT / "skills/video-add-content-cards/scripts/open_gallery.py"
BUILDER_PATH = ROOT / "skills/video-add-content-cards/scripts/build_cards_plan.py"
REVIEW_PAGE_PATH = ROOT / "skills/video-add-content-cards/scripts/build_review_page.py"


def plan_fixture(copy="200 customers"):
    return {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": "source",
        "brief": {"target_card_count": 1, "theme": "editorial"},
        "cards": [
            {
                "id": "card-001",
                "card_type": "stat",
                "evidence_ref": "moment-001",
                "program_start_s": 1.0,
                "duration_s": 4.0,
                "copy": {"status": "draft", "suggested_text": copy},
                "placement": {"status": "draft", "region": None},
                "visual_treatment": {"status": "draft"},
                "renderer": {},
            }
        ],
    }


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            ["node", str(EXAMPLES / "build-gallery.mjs")],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.document = (EXAMPLES / "gallery-animated.html").read_text(encoding="utf-8")

    def test_every_animated_iframe_target_exists(self):
        targets = re.findall(r'<iframe[^>]+src="([^"#]+)', self.document)
        self.assertEqual(65, len(targets))
        for target in set(targets):
            self.assertTrue((EXAMPLES / target).is_file(), target)

    def test_gallery_offers_native_theme_selection(self):
        self.assertIn('name="theme"', self.document)
        self.assertIn('value="all"', self.document)
        for theme in ("almanac", "teal", "editorial", "dotgrid", "apex"):
            self.assertIn(f'value="{theme}"', self.document)
            self.assertIn(f'data-theme="{theme}"', self.document)

    def test_focused_theme_scales_the_cell_and_iframe_together(self):
        focused_rule = re.search(
            r'body:not\(\[data-theme="all"\]\) \{([^}]+)\}', self.document
        )
        self.assertIsNotNone(focused_rule)
        self.assertIn("--scale: 0.42", focused_rule.group(1))
        self.assertIn("--cw: calc(1920px * var(--scale))", focused_rule.group(1))


class GalleryOpenerTests(unittest.TestCase):
    def load_opener(self):
        self.assertTrue(OPENER_PATH.is_file(), OPENER_PATH)
        return load_script(
            "skills/video-add-content-cards/scripts/open_gallery.py", "open_gallery"
        )

    def test_resolves_committed_animated_gallery(self):
        opener = self.load_opener()
        uri = opener.open_gallery(launch=False)
        self.assertTrue(uri.startswith("file:"))
        self.assertTrue(opener.gallery_path().is_file())

    def test_launch_uses_default_browser(self):
        opener = self.load_opener()
        with mock.patch.object(opener.webbrowser, "open", return_value=True) as browser:
            uri = opener.open_gallery()
        browser.assert_called_once_with(uri)


class BriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_script(
            "skills/video-add-content-cards/scripts/build_cards_plan.py", "build_cards_plan_ux"
        )

    @staticmethod
    def brief():
        return {
            "purpose": "emphasize",
            "audience": "existing customers",
            "target_card_count": 3,
            "theme": "editorial",
            "must_include_types": ["stat"],
            "avoid_regions": ["bottom"],
            "notes": "Keep product names verbatim",
        }

    def test_guided_brief_is_persisted(self):
        self.assertIn("brief", inspect.signature(self.builder.build_plan).parameters)
        plan = self.builder.build_plan(
            understanding_fixture(), timeline_fixture(), self.brief()
        )
        self.assertEqual(self.brief(), plan["brief"])

    def test_invalid_brief_is_rejected(self):
        self.assertTrue(hasattr(self.builder, "validate_brief"))
        invalid_briefs = (
            {"target_card_count": 0},
            {"theme": "unknown"},
            {"must_include_types": ["chart"]},
            {"must_include_types": [{}]},
            {"avoid_regions": ["diagonal"]},
            {"unexpected": True},
        )
        for brief in invalid_briefs:
            with self.subTest(brief=brief), self.assertRaises(ValueError):
                self.builder.validate_brief(brief)

    def test_cli_flags_write_brief(self):
        self.assertIn("--purpose", BUILDER_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            understanding = tmp / "understanding.json"
            timeline = tmp / "timeline.json"
            output = tmp / "cards-plan.json"
            understanding.write_text(json.dumps(understanding_fixture()), encoding="utf-8")
            timeline.write_text(json.dumps(timeline_fixture()), encoding="utf-8")
            subprocess.run(
                [
                    "python",
                    str(BUILDER_PATH),
                    str(understanding),
                    str(timeline),
                    str(output),
                    "--purpose",
                    "emphasize",
                    "--audience",
                    "existing customers",
                    "--target-card-count",
                    "3",
                    "--theme",
                    "editorial",
                    "--must-include-type",
                    "stat",
                    "--avoid-region",
                    "bottom",
                    "--notes",
                    "Keep product names verbatim",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(self.brief(), plan["brief"])


class ReviewPageTests(unittest.TestCase):
    def load_review_page(self):
        self.assertTrue(REVIEW_PAGE_PATH.is_file(), REVIEW_PAGE_PATH)
        return load_script(
            "skills/video-add-content-cards/scripts/build_review_page.py",
            "build_review_page",
        )

    def test_review_page_contains_safe_editable_candidates(self):
        review_page = self.load_review_page()
        document = review_page.build_review_page(plan_fixture("</script><b>unsafe</b>"))
        self.assertIn('type="checkbox"', document)
        self.assertIn('name="copy"', document)
        self.assertIn('name="placement"', document)
        self.assertIn('id="selection-count"', document)
        self.assertIn("editorial", document)
        self.assertIn("Target 1", document)
        self.assertIn("Download review JSON", document)
        self.assertNotIn("</script><b>unsafe</b>", document)
        self.assertIn("&lt;/script&gt;&lt;b&gt;unsafe&lt;/b&gt;", document)

    def test_cli_writes_review_page_without_opening(self):
        self.assertTrue(REVIEW_PAGE_PATH.is_file(), REVIEW_PAGE_PATH)
        self.assertIn("--open", REVIEW_PAGE_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            plan_path = tmp / "cards-plan.json"
            output = tmp / "content-cards-review.html"
            plan_path.write_text(json.dumps(plan_fixture()), encoding="utf-8")
            subprocess.run(
                ["python", str(REVIEW_PAGE_PATH), str(plan_path), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(output.is_file())
            self.assertIn("card-001", output.read_text(encoding="utf-8"))

    def test_review_page_stacks_header_and_toolbar_on_narrow_screens(self):
        review_page = self.load_review_page()
        document = review_page.build_review_page(plan_fixture())
        self.assertIn(".header-inner, .toolbar {", document)
        self.assertIn("flex-direction: column", document)
        self.assertIn(".toolbar button { width: 100%; }", document)


if __name__ == "__main__":
    unittest.main()
