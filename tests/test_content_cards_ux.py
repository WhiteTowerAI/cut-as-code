import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills/video-add-content-cards/examples"


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


if __name__ == "__main__":
    unittest.main()
