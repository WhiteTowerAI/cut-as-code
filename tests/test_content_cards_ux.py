import re
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tests.protocol_testlib import load_script


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/video-add-content-cards/examples"
OPENER_PATH = ROOT / "skills/video-add-content-cards/scripts/open_gallery.py"


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


if __name__ == "__main__":
    unittest.main()
