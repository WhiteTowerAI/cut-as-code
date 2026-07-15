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


if __name__ == "__main__":
    unittest.main()
