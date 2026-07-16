import base64
import copy
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
BUILDER_PATH = ROOT / "skills/video-add-content-cards/scripts/build_cards_plan.py"
REVIEW_PAGE_PATH = ROOT / "skills/video-add-content-cards/scripts/build_review_page.py"
REVIEW_TEMPLATE_PATH = ROOT / "skills/video-add-content-cards/assets/content-cards-review.html"
APPLY_REVIEW_PATH = ROOT / "skills/video-add-content-cards/scripts/apply_cards_review.py"
PAYLOAD_PATTERN = re.compile(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)";')


def plan_fixture(copy="200 customers"):
    return {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": "main",
        "brief": {"target_card_count": 1, "theme": "editorial"},
        "cards": [
            {
                "id": "card-001",
                "card_type": "stat",
                "evidence_ref": "moment-001",
                "source_range": {"start_s": 1.0, "end_s": 1.4},
                "program_start_s": 1.0,
                "duration_s": 4.0,
                "copy": {"status": "draft", "suggested_text": copy},
                "placement": {"status": "draft", "region": None},
                "visual_treatment": {"status": "draft"},
                "renderer": {},
            }
        ],
    }


def two_card_plan_fixture():
    plan = copy.deepcopy(plan_fixture())
    second = copy.deepcopy(plan["cards"][0])
    second["id"] = "card-002"
    second["evidence_ref"] = "moment-002"
    second["copy"]["suggested_text"] = "A second idea"
    plan["cards"].append(second)
    return plan


def review_fixture(plan=None, selected_ids=("card-001",)):
    plan = plan or two_card_plan_fixture()
    return {
        "schema_version": 1,
        "cards": [
            {
                "id": card["id"],
                "selected": card["id"] in selected_ids,
                "copy": f"Approved {card['id']}",
                "placement": "top" if card["id"] in selected_ids else "",
            }
            for card in plan["cards"]
        ],
    }


def review_payload(document):
    match = PAYLOAD_PATTERN.search(document)
    if match is None:
        raise AssertionError("review payload was not injected")
    return json.loads(base64.b64decode(match.group(1)).decode("utf-8"))


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

    def test_focused_theme_fits_a_narrow_screen(self):
        self.assertIn(
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            self.document,
        )
        self.assertIn(
            'body:not([data-theme="all"]) { --scale: 0.11; }', self.document
        )

    def test_focused_gallery_prevents_page_level_horizontal_scroll(self):
        focused_rule = re.search(
            r'body:not\(\[data-theme="all"\]\) \{([^}]+)\}', self.document
        )
        self.assertIsNotNone(focused_rule)
        self.assertIn("overflow-x: hidden", focused_rule.group(1))
        self.assertIn("width: 100vw; max-width: 100vw", self.document)


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

    @staticmethod
    def fake_ffmpeg(command, **kwargs):
        Path(command[-1]).write_bytes(b"\xff\xd8\xff\xd9")
        return subprocess.CompletedProcess(command, 0)

    def test_committed_template_has_live_screenshot_placement_preview(self):
        self.assertTrue(REVIEW_TEMPLATE_PATH.is_file(), REVIEW_TEMPLATE_PATH)
        template = REVIEW_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("__CONTENT_CARDS_REVIEW_DATA__", template)
        self.assertIn('class="frame-preview"', template)
        self.assertIn('class="placement-proxy"', template)
        self.assertIn("image.src = card.screenshot", template)
        for placement in ("top", "bottom", "left", "right", "center"):
            self.assertIn(f'[data-placement="{placement}"]', template)
        self.assertIn('placement.addEventListener("change", updatePreview)', template)
        self.assertIn('copy.addEventListener("input", updatePreview)', template)
        self.assertIn("font-size: clamp(10px, 1vw, 12px)", template)
        self.assertIn("-webkit-line-clamp: 2", template)
        self.assertNotIn("innerHTML", template)

    def test_template_preserves_user_summary_review_ui(self):
        self.assertTrue(REVIEW_TEMPLATE_PATH.is_file(), REVIEW_TEMPLATE_PATH)
        template = REVIEW_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn('class="summary-box"', template)
        self.assertIn("Copy the following summary back to the AI agent.", template)
        self.assertIn('id="copy-summary"', template)
        self.assertIn('id="summary-output"', template)
        self.assertIn('document.execCommand("copy")', template)
        self.assertIn('copyButton.textContent = "Copy failed"', template)
        self.assertIn("No cards selected yet.", template)
        self.assertNotIn("Download review JSON", template)

    def test_builder_extracts_retained_source_midpoint_and_safely_injects_payload(self):
        review_page = self.load_review_page()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            output = tmp / "content-cards-review.html"
            plan = plan_fixture("</script><b>unsafe</b>")
            with mock.patch.object(
                review_page.subprocess, "run", side_effect=self.fake_ffmpeg
            ) as ffmpeg:
                result = review_page.build_review_page(
                    plan, timeline_fixture(), video, output
                )

            self.assertEqual(output.resolve(), result)
            command = ffmpeg.call_args.args[0]
            self.assertEqual("1.200000", command[command.index("-ss") + 1])
            self.assertIn("-frames:v", command)
            self.assertIn("scale=960:-2", command)
            document = output.read_text(encoding="utf-8")
            self.assertNotIn("__CONTENT_CARDS_REVIEW_DATA__", document)
            self.assertNotIn("</script><b>unsafe</b>", document)
            payload = review_payload(document)
            self.assertEqual("</script><b>unsafe</b>", payload["cards"][0]["copy"])
            self.assertEqual(
                "content-cards-review-assets/frame-001.jpg",
                payload["cards"][0]["screenshot"],
            )
            self.assertTrue(
                (tmp / "content-cards-review-assets/frame-001.jpg").is_file()
            )

    def test_cli_requires_video_and_uses_committed_template(self):
        script = REVIEW_PAGE_PATH.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--video", required=True)', script)
        self.assertIn('parser.add_argument("--timeline", required=True)', script)
        self.assertIn("assets/content-cards-review.html", script)

    def test_missing_video_is_rejected_before_ffmpeg(self):
        review_page = self.load_review_page()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with mock.patch.object(review_page.subprocess, "run") as ffmpeg:
                with self.assertRaises(FileNotFoundError):
                    review_page.build_review_page(
                        plan_fixture(),
                        timeline_fixture(),
                        tmp / "missing.mp4",
                        tmp / "review.html",
                    )
            ffmpeg.assert_not_called()

    def test_missing_source_range_is_rejected_before_ffmpeg(self):
        review_page = self.load_review_page()
        plan = plan_fixture()
        del plan["cards"][0]["source_range"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            with mock.patch.object(review_page.subprocess, "run") as ffmpeg:
                with self.assertRaisesRegex(ValueError, "source_range"):
                    review_page.build_review_page(
                        plan, timeline_fixture(), video, tmp / "review.html"
                    )
            ffmpeg.assert_not_called()

    def test_mismatched_timeline_id_is_rejected_before_ffmpeg(self):
        review_page = self.load_review_page()
        plan = plan_fixture()
        plan["timeline_id"] = "another-sequence"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            with mock.patch.object(review_page.subprocess, "run") as ffmpeg:
                with self.assertRaisesRegex(ValueError, "timeline_id"):
                    review_page.build_review_page(
                        plan, timeline_fixture(), video, tmp / "review.html"
                    )
            ffmpeg.assert_not_called()

    def test_failed_frame_batch_does_not_replace_existing_review_assets(self):
        review_page = self.load_review_page()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            output = tmp / "review.html"
            output.write_text("old review", encoding="utf-8")
            assets = tmp / "review-assets"
            assets.mkdir()
            old_frame = assets / "frame-001.jpg"
            old_frame.write_bytes(b"old frame")
            calls = 0

            def fail_second_frame(command, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise subprocess.CalledProcessError(1, command)
                Path(command[-1]).write_bytes(b"new frame")
                return subprocess.CompletedProcess(command, 0)

            with mock.patch.object(
                review_page.subprocess, "run", side_effect=fail_second_frame
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    review_page.build_review_page(
                        two_card_plan_fixture(), timeline_fixture(), video, output
                    )

            self.assertEqual(b"old frame", old_frame.read_bytes())
            self.assertEqual("old review", output.read_text(encoding="utf-8"))

    def test_review_starts_unselected_at_bottom_even_for_previously_approved_cards(self):
        review_page = self.load_review_page()
        plan = plan_fixture()
        plan["cards"][0]["copy"]["status"] = "approved"
        plan["cards"][0]["placement"] = {"status": "approved", "region": "top"}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            output = tmp / "review.html"
            with mock.patch.object(
                review_page.subprocess, "run", side_effect=self.fake_ffmpeg
            ):
                review_page.build_review_page(plan, timeline_fixture(), video, output)
            card = review_payload(output.read_text(encoding="utf-8"))["cards"][0]
            self.assertFalse(card["selected"])
            self.assertEqual("bottom", card["placement"])

    def test_frame_midpoint_is_clamped_to_the_retained_clip(self):
        review_page = self.load_review_page()
        plan = plan_fixture()
        plan["cards"][0]["source_range"] = {"start_s": 1.8, "end_s": 4.2}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            with mock.patch.object(
                review_page.subprocess, "run", side_effect=self.fake_ffmpeg
            ) as ffmpeg:
                review_page.build_review_page(
                    plan, timeline_fixture(), video, tmp / "review.html"
                )
            command = ffmpeg.call_args.args[0]
            self.assertEqual("1.900000", command[command.index("-ss") + 1])

    def test_varispeed_program_time_is_not_used_to_seek_source_media(self):
        review_page = self.load_review_page()
        plan = plan_fixture()
        card = plan["cards"][0]
        card["source_range"] = {"start_s": 4.0, "end_s": 4.4}
        card["program_start_s"] = 2.0
        card["duration_s"] = 0.2
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            video = tmp / "source.mp4"
            video.write_bytes(b"video")
            with mock.patch.object(
                review_page.subprocess, "run", side_effect=self.fake_ffmpeg
            ) as ffmpeg:
                review_page.build_review_page(
                    plan, timeline_fixture(), video, tmp / "review.html"
                )
            command = ffmpeg.call_args.args[0]
            self.assertEqual("4.200000", command[command.index("-ss") + 1])

    def test_template_stacks_candidate_controls_on_narrow_screens(self):
        self.assertTrue(REVIEW_TEMPLATE_PATH.is_file(), REVIEW_TEMPLATE_PATH)
        template = REVIEW_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 780px)", template)
        self.assertIn("flex-direction: column", template)
        self.assertIn(".frame-preview { grid-column: 1 / -1; }", template)


class ApplyReviewTests(unittest.TestCase):
    def load_apply_review(self):
        self.assertTrue(APPLY_REVIEW_PATH.is_file(), APPLY_REVIEW_PATH)
        return load_script(
            "skills/video-add-content-cards/scripts/apply_cards_review.py",
            "apply_cards_review",
        )

    def test_review_keeps_selected_cards_and_approves_fields(self):
        apply_review = self.load_apply_review()
        updated = apply_review.apply_review(two_card_plan_fixture(), review_fixture())
        self.assertEqual(["card-001"], [card["id"] for card in updated["cards"]])
        card = updated["cards"][0]
        self.assertEqual("approved", card["copy"]["status"])
        self.assertEqual("Approved card-001", card["copy"]["text"])
        self.assertEqual("approved", card["placement"]["status"])
        self.assertEqual("top", card["placement"]["region"])
        self.assertEqual("approved", card["visual_treatment"]["status"])
        self.assertEqual("editorial", card["visual_treatment"]["theme"])
        self.assertEqual("approved", updated["review"]["status"])
        self.assertEqual(["card-001"], updated["review"]["selected_card_ids"])

    def test_review_rejects_unknown_duplicate_missing_and_invalid_choices(self):
        apply_review = self.load_apply_review()
        plan = two_card_plan_fixture()
        valid = review_fixture(plan)

        unknown = copy.deepcopy(valid)
        unknown["cards"].append(
            {"id": "card-999", "selected": False, "copy": "", "placement": ""}
        )
        duplicate = copy.deepcopy(valid)
        duplicate["cards"].append(copy.deepcopy(duplicate["cards"][0]))
        missing = copy.deepcopy(valid)
        missing["cards"].pop()
        invalid_placement = copy.deepcopy(valid)
        invalid_placement["cards"][0]["placement"] = "diagonal"
        blank_copy = copy.deepcopy(valid)
        blank_copy["cards"][0]["copy"] = "   "

        for review in (unknown, duplicate, missing, invalid_placement, blank_copy):
            with self.subTest(review=review), self.assertRaises(ValueError):
                apply_review.apply_review(plan, review)

    def test_cli_validates_then_writes_requested_output(self):
        self.assertTrue(APPLY_REVIEW_PATH.is_file(), APPLY_REVIEW_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            plan_path = tmp / "cards-plan.json"
            review_path = tmp / "content-cards-review.json"
            output = tmp / "approved-plan.json"
            plan_path.write_text(json.dumps(plan_fixture()), encoding="utf-8")
            review_path.write_text(
                json.dumps(review_fixture(plan_fixture())), encoding="utf-8"
            )
            subprocess.run(
                [
                    "python",
                    str(APPLY_REVIEW_PATH),
                    str(plan_path),
                    str(review_path),
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            approved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("approved", approved["review"]["status"])


if __name__ == "__main__":
    unittest.main()
