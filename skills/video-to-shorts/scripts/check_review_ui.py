#!/usr/bin/env python3
"""Check the shared offline review UI contract for shorts templates."""

import base64
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image


MARKERS = (
    "__CAPTION_STYLE_REVIEW_DATA__",
    "__CAPTION_EVIDENCE_REVIEW_DATA__",
    "__SHORTS_CANDIDATE_REVIEW_DATA__",
    "__SHORTS_VERTICAL_REVIEW_DATA__",
)
TOKENS = {
    "bg": "#151719",
    "band": "#1d2023",
    "surface": "#24282b",
    "line": "#3b4145",
    "text": "#f2eee5",
    "muted": "#aeb4b7",
    "accent": "#4fc3b4",
    "warning": "#f3bd5b",
}
IDS = ("review-status", "review-form", "copy-summary", "summary-output", "review-errors")
SKILL_ROOT = Path(__file__).resolve().parent.parent


def write_jpeg(path, width=960, height=540):
    Image.new("RGB", (width, height), "#24323a").save(path, "JPEG")


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def assert_review_template(path, marker):
    """Raise AssertionError when path does not implement the offline UI contract."""
    path = Path(path)
    _require(path.exists(), f"template missing: {path}")
    html = path.read_text(encoding="utf-8")
    for name, value in TOKENS.items():
        _require(re.search(rf"--{name}\s*:\s*{re.escape(value)}\s*(?:;|}})", html), (
            f"{path}: missing --{name}: {value}"
        ))
    _require(re.search(r"width\s*:\s*min\(1180px,\s*calc\(100%\s*-\s*32px\)\)", html), (
        f"{path}: missing review width"
    ))
    _require(re.search(r"\.toolbar\s*\{[^}}]*position\s*:\s*sticky\b", html, re.DOTALL), (
        f"{path}: toolbar must be sticky"
    ))
    for element_id in IDS:
        _require(re.search(rf"id=[\"']{element_id}[\"']", html), f"{path}: missing #{element_id}")
    _require(re.search(r"min-height\s*:\s*38px\b", html), f"{path}: missing 38px control height")
    _require(re.search(r"@media\s*\(max-width\s*:\s*1100px\)", html), (
        f"{path}: missing 1100px breakpoint"
    ))
    _require(re.search(r"@media\s*\(max-width\s*:\s*780px\)", html), (
        f"{path}: missing 780px breakpoint"
    ))
    _require(html.count(marker) == 1, f"{path}: expected exactly one {marker}")
    _require(sum(html.count(value) for value in MARKERS) == 1, (
        f"{path}: expected exactly one page-specific payload marker"
    ))


def contract_fixture(marker):
    tokens = "".join(f"--{name}: {value};" for name, value in TOKENS.items())
    elements = "".join(f'<div id="{element_id}"></div>' for element_id in IDS)
    return f"""<style>
:root {{{tokens}}}
.shell {{width: min(1180px, calc(100% - 32px));}}
.toolbar {{position: sticky; min-height: 38px;}}
@media (max-width: 1100px) {{}}
@media (max-width: 780px) {{}}
</style>{elements}<script>{marker}</script>"""


class ReviewUiContractTests(unittest.TestCase):
    def test_validator_accepts_the_common_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.html"
            path.write_text(contract_fixture(MARKERS[2]), encoding="utf-8")
            assert_review_template(path, MARKERS[2])

    def test_candidate_review_template(self):
        path = SKILL_ROOT / "assets" / "shorts-candidates-review.html"
        assert_review_template(path, MARKERS[2])
        html = path.read_text(encoding="utf-8")
        _require('type="checkbox"' in html, "candidate choices must be checkboxes")
        _require(html.count('type="radio"') == 2, "delivery must use two native radios")
        _require("horizontal_only" in html and "horizontal_and_vertical" in html, (
            "delivery modes are incomplete"
        ))
        _require(not re.search(r'type="(?:checkbox|radio)"[^>]*\bchecked\b', html), (
            "candidate and delivery controls must initially be unselected"
        ))
        _require(re.search(r'id="copy-summary"[^>]*\bdisabled\b', html), (
            "copy summary must initially be disabled"
        ))
        for text in ("max 5", "Decision: revise", "Changes:", "showModal", "focus"):
            _require(text in html, f"candidate review is missing {text!r}")
        _require("default top five" not in html.lower(), "bound page must not offer default top five")


def candidate_fixture(source, malicious=False):
    dimensions = {
        "hook": {"score": 18, "reason": "Immediate hook."},
        "completeness": {"score": 19, "reason": "Complete payoff."},
        "audience_value": {"score": 17, "reason": "Useful."},
        "emotion_tension": {"score": 8, "reason": "Clear stakes."},
        "quotability": {"score": 12, "reason": "Memorable."},
        "pace_editability": {"score": 8, "reason": "Clean pacing."},
    }
    candidates = []
    for index, (start, end) in enumerate(((10.0, 30.0), (40.0, 70.0)), 1):
        excerpt = f"Candidate {index} transcript"
        if malicious and index == 1:
            excerpt = '</script><script>throw new Error("unsafe")</script>'
        candidates.append({
            "candidate_id": f"cand-00{index}",
            "title": f"Candidate {index}",
            "scene_type": "solo_talk",
            "start_time": start,
            "end_time": end,
            "duration": end - start,
            "transcript_excerpt": excerpt,
            "evidence_mode": "text_visual",
            "score_breakdown": dimensions,
            "score": 82 - index,
            "warnings": [] if index == 1 else ["BOUNDARY_RISK"],
            "metadata": {"editorial_reason": f"Reason {index}."},
        })
    return {
        "schema_version": "shorts-candidates.v2",
        "video": {"source": str(source), "duration_s": 90.0},
        "transcript": {"path": "transcript.json", "timebase": "program"},
        "candidates": candidates,
    }


def vertical_fixture(source, strategy="SCENE_CROP"):
    if strategy == "REVIEW_REQUIRED":
        segments = [{
            "start_time": 0.0,
            "end_time": 12.0,
            "strategy": "REVIEW_REQUIRED",
            "content_type": "MULTI_SUBJECT",
            "reason": "A deterministic fixed crop cannot preserve every subject.",
        }]
    else:
        segments = [
            {
                "start_time": 0.0,
                "end_time": 6.0,
                "strategy": "SCENE_CROP",
                "content_type": "PRESENTER",
                "crop_x": 656,
                "crop_y": 0,
                "crop_width": 608,
                "crop_height": 1080,
                "reason": "The presenter remains centered.",
            },
            {
                "start_time": 6.0,
                "end_time": 12.0,
                "strategy": "LETTERBOX",
                "content_type": "WIDE_INFORMATION",
                "reason": "The complete diagram must remain visible.",
            },
        ]
    return {
        "schema_version": "video-to-shorts.vertical-plan.v1",
        "source_video": str(source.resolve()),
        "source_width": 1920,
        "source_height": 1080,
        "source_fps": {"num": 30000, "den": 1001},
        "source_duration_s": 12.0,
        "output_width": 608,
        "output_height": 1080,
        "target_aspect_ratio": "9:16",
        "strategy": strategy,
        "segments": segments,
        "strategy_summary": {},
        "warnings": ["Operator warning."],
        "validator_warnings": ["Validator warning."],
        "render_allowed": strategy != "REVIEW_REQUIRED",
    }


def vertical_probe_fixture(renderable=True):
    source_streams = [
        {"codec_type": "video", "width": 1920, "height": 1080, "avg_frame_rate": "30000/1001"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
    ]
    output = None
    if renderable:
        output = {
            "format": {"duration": "12.000"},
            "streams": [
                {"codec_type": "video", "width": 360, "height": 640, "avg_frame_rate": "30000/1001"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
        }
    return {
        "source": {"format": {"duration": "12.000"}, "streams": source_streams},
        "output": output,
        "status": "ready" if renderable else "REVIEW_REQUIRED",
    }


def vertical_summary_fixture(strategy="SCENE_CROP"):
    return {
        "schema_version": "video-to-shorts.vertical-preview-summary.v1",
        "mode": "preview",
        "strategy": strategy,
        "renderable": strategy != "REVIEW_REQUIRED",
        "warnings": ["Operator warning.", "Validator warning."],
    }


def open_vertical_fixture(
    root, strategy="SCENE_CROP", plan_mutator=None, contact_bytes=None, **patches
):
    import review_gate
    from transcript_utils import write_json

    source = root / "source.mp4"
    source.write_bytes(b"small-mp4-placeholder")
    plan = root / "vertical_plan.json"
    summary = root / "preview_summary.json"
    probe = root / "media_probe.json"
    plan_data = vertical_fixture(source, strategy)
    if plan_mutator:
        plan_mutator(plan_data)
    write_json(plan, plan_data)
    write_json(summary, vertical_summary_fixture(strategy))
    write_json(probe, vertical_probe_fixture(strategy != "REVIEW_REQUIRED"))
    review_out = root / "review" / "06-shorts"
    preview = contact = None
    if strategy != "REVIEW_REQUIRED":
        preview = review_out / "short-001-vertical-preview.mp4"
        contact = review_out / "short-001-vertical-contact-sheet.jpg"
        review_out.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"preview-mp4-placeholder")
        write_jpeg(contact, 810, 516)
        if contact_bytes is not None:
            contact.write_bytes(contact_bytes)
    candidate = {
        "review_id": "candidate-review-1",
        "decision_mode": "human",
        "delegation_note": None,
    }
    patches.setdefault("probe_review_media", mock.Mock(return_value={
        "width": 360,
        "height": 640,
        "fps": "30000/1001",
        "durationS": 12.0,
        "audio": True,
    }))
    with mock.patch.object(
        review_gate, "validate_vertical_delivery_allowed", return_value=(root, candidate)
    ), contextlib.ExitStack() as stack:
        for name, value in patches.items():
            stack.enter_context(mock.patch.object(
                review_gate, name, value, create=name == "probe_review_media"
            ))
        result = review_gate.open_vertical_review(
            root, source, plan, summary, probe, preview, contact,
            review_out=review_out, short_id="short-001",
        )
    return {
        "result": result,
        "source": source,
        "plan": plan,
        "summary": summary,
        "probe": probe,
        "preview": preview,
        "contact": contact,
        "review_out": review_out,
    }


class CandidateReviewBuilderTests(unittest.TestCase):
    def test_extracts_20_50_80_frames_and_base64_encodes_payload(self):
        import build_candidate_review

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            candidates = root / "candidates.json"
            candidates.write_text(json.dumps(candidate_fixture(source, malicious=True)), encoding="utf-8")
            commands = []

            def fake_ffmpeg(command, **kwargs):
                commands.append(command)
                write_jpeg(command[-1])
                return SimpleNamespace(returncode=0)

            result = build_candidate_review.build_candidate_review(
                source, candidates, root / "review", "review-123", run_ffmpeg=fake_ffmpeg
            )
            self.assertEqual([float(command[command.index("-ss") + 1]) for command in commands], [
                14.0, 20.0, 26.0, 46.0, 55.0, 64.0,
            ])
            self.assertTrue(result["page"].is_file())
            self.assertEqual(len(result["frames"]), 6)
            self.assertTrue(all(path.stat().st_size for path in result["frames"]))
            self.assertTrue(all("cand-" not in path.name for path in result["frames"]))
            for command in commands:
                self.assertEqual(command[command.index("-frames:v") + 1], "1")
                self.assertEqual(command[command.index("-vf") + 1], "scale=960:-2")
                self.assertEqual(command[command.index("-q:v") + 1], "2")
                self.assertLess(float(command[command.index("-ss") + 1]), 70.0)
            html = result["page"].read_text(encoding="utf-8")
            self.assertNotIn('</script><script>throw new Error("unsafe")</script>', html)
            encoded = re.search(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)"', html).group(1)
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            self.assertEqual(payload["reviewId"], "review-123")
            self.assertEqual(payload["candidates"][0]["transcriptExcerpt"], (
                '</script><script>throw new Error("unsafe")</script>'
            ))
            self.assertEqual([frame["label"] for frame in payload["candidates"][0]["frames"]], [
                "Start", "Middle", "End",
            ])

    def test_rejects_duplicate_ids_and_invalid_ranges_before_ffmpeg(self):
        import build_candidate_review

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            data = candidate_fixture(source)
            data["candidates"][1]["candidate_id"] = "cand-001"
            data["candidates"][1]["end_time"] = data["candidates"][1]["start_time"]
            candidates = root / "candidates.json"
            candidates.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "duplicate|range"):
                build_candidate_review.build_candidate_review(
                    source, candidates, root / "review", "review-123",
                    run_ffmpeg=lambda *_args, **_kwargs: self.fail("ffmpeg must not run"),
                )

    def test_rejects_non_finite_timing_before_ffmpeg(self):
        import build_candidate_review

        for field in ("start_time", "end_time", "duration"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source = root / "source.mp4"
                    source.write_bytes(b"video")
                    data = candidate_fixture(source)
                    data["candidates"][0][field] = value
                    candidates = root / "candidates.json"
                    candidates.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaisesRegex(SystemExit, "finite"):
                        build_candidate_review.build_candidate_review(
                            source, candidates, root / "review", "review-123",
                            run_ffmpeg=lambda *_args, **_kwargs: self.fail("ffmpeg must not run"),
                        )

    def test_rejects_corrupt_or_wrong_width_jpegs(self):
        import build_candidate_review

        for mode in ("corrupt", "wrong-width"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.mp4"
                source.write_bytes(b"video")
                candidates = root / "candidates.json"
                candidates.write_text(json.dumps(candidate_fixture(source)), encoding="utf-8")

                def fake_ffmpeg(command, **kwargs):
                    if mode == "corrupt":
                        Path(command[-1]).write_bytes(b"not-a-jpeg")
                    else:
                        write_jpeg(command[-1], width=640)

                with self.assertRaisesRegex(SystemExit, "JPEG|960"):
                    build_candidate_review.build_candidate_review(
                        source, candidates, root / "review", "review-123", run_ffmpeg=fake_ffmpeg
                    )

    def test_rejects_malformed_display_shapes_before_ffmpeg(self):
        import build_candidate_review

        mutations = (
            lambda data: data["candidates"].__setitem__(0, "not-an-object"),
            lambda data: data["candidates"][0].__setitem__("warnings", "warning"),
            lambda data: data["candidates"][0].__setitem__("score_breakdown", "scores"),
            lambda data: data["candidates"][0].__setitem__("title", []),
            lambda data: data["candidates"][0].__setitem__("transcript_excerpt", {}),
            lambda data: data["candidates"][0].__setitem__("candidate_id", 123),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.mp4"
                source.write_bytes(b"video")
                data = candidate_fixture(source)
                mutate(data)
                candidates = root / "candidates.json"
                candidates.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(SystemExit):
                    build_candidate_review.build_candidate_review(
                        source, candidates, root / "review", "review-123",
                        run_ffmpeg=lambda *_args, **_kwargs: self.fail("ffmpeg must not run"),
                    )

    def test_same_review_id_collision_preserves_first_publication(self):
        import build_candidate_review

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            candidates = root / "candidates.json"
            candidates.write_text(json.dumps(candidate_fixture(source)), encoding="utf-8")

            def fake_ffmpeg(command, **kwargs):
                write_jpeg(command[-1])

            first = build_candidate_review.build_candidate_review(
                source, candidates, root / "review", "same-id", run_ffmpeg=fake_ffmpeg
            )
            before = {path: path.read_bytes() for path in [first["page"], *first["frames"]]}
            with self.assertRaisesRegex(SystemExit, "already exist"):
                build_candidate_review.build_candidate_review(
                    source, candidates, root / "review", "same-id", run_ffmpeg=fake_ffmpeg
                )
            self.assertEqual(before, {path: path.read_bytes() for path in before})


class BoundCandidateResponseTests(unittest.TestCase):
    OPTIONS = [
        {"reference": f"text_visual/cand-00{index}", "candidate_id": f"cand-00{index}"}
        for index in range(1, 7)
    ]

    def test_accepts_exact_bound_approval_case_insensitively(self):
        import review_gate

        parsed = review_gate.parse_bound_candidate_response(
            "SHORTS CANDIDATE REVIEW\nreview: r-1\nCANDIDATES: text_visual/cand-001, text_visual/cand-002\nDELIVERY: horizontal_and_vertical",
            "r-1", self.OPTIONS,
        )
        self.assertEqual(parsed, {
            "decision": "approve",
            "selected_references": ["text_visual/cand-001", "text_visual/cand-002"],
            "delivery_mode": "horizontal_and_vertical",
        })

    def test_accepts_bound_revision_only_with_changes(self):
        import review_gate

        parsed = review_gate.parse_bound_candidate_response(
            "Shorts candidate review\nReview: r-1\nDecision: revise\nChanges: Tighten the first hook.",
            "r-1", self.OPTIONS,
        )
        self.assertEqual(parsed["decision"], "revise")
        self.assertEqual(parsed["changes"], "Tighten the first hook.")

    def test_rejects_malformed_bound_responses(self):
        import review_gate

        responses = (
            "Shorts candidate review\nReview: wrong\nCandidates: text_visual/cand-001\nDelivery: horizontal_only",
            "Shorts candidate review\nReview: r-1\nCandidates: text_visual/cand-001, text_visual/cand-001\nDelivery: horizontal_only",
            "Shorts candidate review\nReview: r-1\nCandidates: text_visual/cand-001\nDelivery: horizontal_only\nExtra: no",
            "Shorts candidate review\nReview: r-1\nCandidates: text_visual/cand-001, text_visual/cand-002, text_visual/cand-003, text_visual/cand-004, text_visual/cand-005, text_visual/cand-006\nDelivery: horizontal_only",
            "Shorts candidate review\nReview: r-1\nDecision: revise\nChanges:   ",
            "Shorts candidate review\nReview: r-1\nDelivery: horizontal_only",
        )
        for response in responses:
            with self.subTest(response=response), self.assertRaises(SystemExit):
                review_gate.parse_bound_candidate_response(response, "r-1", self.OPTIONS)


class CandidateReceiptTests(unittest.TestCase):
    def test_bound_review_hashes_authoritative_page_and_every_frame(self):
        import review_gate
        from transcript_utils import load_json, write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            write_json(root / "transcript.json", {"duration": 90.0, "segments": []})
            candidate_dir = root / "preview" / "text_visual"
            write_json(candidate_dir / "shorts_candidates.json", candidate_fixture(source))

            def fake_ffmpeg(command, **kwargs):
                write_jpeg(command[-1])
                return SimpleNamespace(returncode=0)

            with mock.patch("build_candidate_review.subprocess.run", fake_ffmpeg):
                review_path, _ = review_gate.open_candidate_review(
                    root, review_out=root / "review" / "06-shorts"
                )
            review = load_json(review_path)
            self.assertIn("candidate_review_page", review["artifacts"])
            self.assertEqual(len(review["artifacts"]["candidate_review_frames"]), 6)
            frame = Path(review["artifacts"]["candidate_review_frames"][0]["path"])
            frame.write_bytes(b"changed")
            with self.assertRaisesRegex(SystemExit, "changed after review"):
                review_gate.verify_candidate_artifacts(review)

    def test_mutation_during_build_preserves_prior_receipt_and_cleans_new_artifacts(self):
        import review_gate
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            write_json(root / "transcript.json", {"duration": 90.0, "segments": []})
            candidate_path = root / "preview" / "text_visual" / "shorts_candidates.json"
            write_json(candidate_path, candidate_fixture(source))
            receipt = root / "review" / "candidate_review.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"prior-receipt")
            mutated = False

            def fake_ffmpeg(command, **kwargs):
                nonlocal mutated
                if not mutated:
                    candidate_path.write_text(candidate_path.read_text() + " ", encoding="utf-8")
                    mutated = True
                write_jpeg(command[-1])

            with mock.patch("build_candidate_review.subprocess.run", fake_ffmpeg), self.assertRaisesRegex(SystemExit, "changed"):
                review_gate.open_candidate_review(root, review_out=root / "review" / "06-shorts")
            self.assertEqual(receipt.read_bytes(), b"prior-receipt")
            self.assertFalse(list((root / "review" / "06-shorts").glob("candidates-*.html")))

    def test_mutation_after_verification_is_rejected_before_bound_parse(self):
        import review_gate
        from transcript_utils import load_json, write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            write_json(root / "transcript.json", {"duration": 90.0, "segments": []})
            candidate_path = root / "preview" / "text_visual" / "shorts_candidates.json"
            write_json(candidate_path, candidate_fixture(source))

            def fake_ffmpeg(command, **kwargs):
                write_jpeg(command[-1])

            with mock.patch("build_candidate_review.subprocess.run", fake_ffmpeg):
                review_path, _ = review_gate.open_candidate_review(root, review_out=root / "review" / "06-shorts")
            review = load_json(review_path)
            response = f"Shorts candidate review\nReview: {review['review_id']}\nCandidates: text_visual/cand-001\nDelivery: horizontal_only"
            original_verify = review_gate.verify_candidate_artifacts

            def verify_then_mutate(value):
                original_verify(value)
                candidate_path.write_text(candidate_path.read_text() + " ", encoding="utf-8")

            with mock.patch.object(review_gate, "verify_candidate_artifacts", verify_then_mutate), self.assertRaisesRegex(SystemExit, "changed"):
                review_gate.answer_candidate_review(root, response)

    def test_bound_approval_uses_atomic_files_when_receipt_write_is_interrupted(self):
        import review_gate
        from transcript_utils import load_json, write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            write_json(root / "transcript.json", {"duration": 90.0, "segments": []})
            candidate_path = root / "preview" / "text_visual" / "shorts_candidates.json"
            write_json(candidate_path, candidate_fixture(source))

            def fake_ffmpeg(command, **kwargs):
                write_jpeg(command[-1])

            with mock.patch("build_candidate_review.subprocess.run", fake_ffmpeg):
                review_path, _ = review_gate.open_candidate_review(root, review_out=root / "review" / "06-shorts")
            review = load_json(review_path)
            response = f"Shorts candidate review\nReview: {review['review_id']}\nCandidates: text_visual/cand-001\nDelivery: horizontal_only"
            real_atomic = review_gate.atomic_write_json

            def interrupt_receipt(path, data):
                if Path(path) == Path(review_path) and data.get("status") == "approved":
                    raise OSError("interrupted receipt")
                return real_atomic(path, data)

            with mock.patch.object(review_gate, "atomic_write_json", interrupt_receipt), self.assertRaisesRegex(OSError, "interrupted"):
                review_gate.answer_candidate_review(root, response)
            self.assertEqual(load_json(review_path)["status"], "pending")
            self.assertEqual(load_json(root / "review" / "approved_candidates.json")["schema_version"], "shorts-candidates.v2")
            self.assertFalse(list((root / "review").glob("*.tmp")))

    def test_latest_alias_failure_warns_without_invalidating_authoritative_review(self):
        import review_gate
        from transcript_utils import load_json, write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"video")
            write_json(root / "transcript.json", {"duration": 90.0, "segments": []})
            write_json(root / "preview" / "text_visual" / "shorts_candidates.json", candidate_fixture(source))

            def fake_ffmpeg(command, **kwargs):
                write_jpeg(command[-1])

            stderr = io.StringIO()
            with mock.patch("build_candidate_review.subprocess.run", fake_ffmpeg), mock.patch.object(
                review_gate, "atomic_copy_alias", side_effect=OSError("alias denied"), create=True
            ), contextlib.redirect_stderr(stderr):
                review_path, _ = review_gate.open_candidate_review(root, review_out=root / "review" / "06-shorts")
            review = load_json(review_path)
            self.assertEqual(review["status"], "pending")
            self.assertIn(review["artifacts"]["candidate_review_page"]["path"], stderr.getvalue())
            self.assertIn("alias", stderr.getvalue().lower())


class VerticalReviewTemplateTests(unittest.TestCase):
    def test_vertical_review_template_uses_native_accessible_controls(self):
        path = SKILL_ROOT / "assets" / "shorts-vertical-review.html"
        assert_review_template(path, MARKERS[3])
        html = path.read_text(encoding="utf-8")
        self.assertEqual(html.count('type="radio"'), 3)
        for value in ("approve", "revise", "skip"):
            self.assertIn(f'value="{value}"', html)
        for text in (
            "Shorts vertical review", "<video", "controls", "<dialog", "showModal",
            "focus", "Changes:", "aria-disabled", "clipboard", "execCommand",
        ):
            self.assertIn(text, html)
        self.assertNotIn("autoplay", html.lower())
        self.assertNotRegex(html, r'https?://')

    def test_vertical_review_template_blocks_approval_on_media_load_errors(self):
        html = (SKILL_ROOT / "assets" / "shorts-vertical-review.html").read_text(encoding="utf-8")
        self.assertIn('video.addEventListener("error"', html)
        self.assertIn('sheet.addEventListener("error"', html)
        self.assertIn("mediaFailed", html)
        self.assertRegex(html, r"mediaFailed[\s\S]*approve\.disabled\s*=\s*true")
        self.assertRegex(html, r"mediaFailed[\s\S]*copy\.disabled")


class BoundVerticalResponseTests(unittest.TestCase):
    def test_accepts_exact_bound_decisions_case_insensitively(self):
        import review_gate

        approved = review_gate.parse_bound_vertical_response(
            "SHORTS VERTICAL REVIEW\nshort: short-001\nREVIEW: review-1\ndecision: APPROVE",
            "short-001", "review-1",
        )
        revised = review_gate.parse_bound_vertical_response(
            "Shorts vertical review\nShort: short-001\nReview: review-1\n"
            "Decision: revise\nChanges: Keep the diagram fully visible.",
            "short-001", "review-1",
        )
        skipped = review_gate.parse_bound_vertical_response(
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: skip",
            "short-001", "review-1",
        )
        self.assertEqual(approved, {"decision": "approve"})
        self.assertEqual(revised, {
            "decision": "revise", "changes": "Keep the diagram fully visible."
        })
        self.assertEqual(skipped, {"decision": "skip"})

    def test_rejects_unbound_or_ambiguous_vertical_responses(self):
        import review_gate

        responses = (
            "Vertical review\nShort: short-001\nReview: review-1\nDecision: approve",
            "Shorts vertical review\nShort: wrong\nReview: review-1\nDecision: approve",
            "Shorts vertical review\nShort: short-001\nReview: wrong\nDecision: approve",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: approve\nDecision: skip",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: approve\nExtra: no",
            "Shorts vertical review\nShort: short-001\nReview: review-1",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: maybe",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: revise\nChanges:   ",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: approve\nChanges: no",
            "Shorts vertical review\nShort: short-001\nReview: review-1\nDecision: skip\nChanges: no",
        )
        for response in responses:
            with self.subTest(response=response), self.assertRaises(SystemExit):
                review_gate.parse_bound_vertical_response(response, "short-001", "review-1")


class VerticalReceiptTests(unittest.TestCase):
    def test_renderable_page_binds_payload_media_segments_probe_and_warnings(self):
        from transcript_utils import load_json

        with tempfile.TemporaryDirectory() as directory:
            fixture = open_vertical_fixture(Path(directory))
            review_path, question_path, page_path = fixture["result"]
            review = load_json(review_path)
            html = page_path.read_text(encoding="utf-8")
            encoded = re.search(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)"', html).group(1)
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            self.assertEqual(payload["shortId"], "short-001")
            self.assertEqual(payload["reviewId"], review["review_id"])
            self.assertTrue(payload["renderable"])
            self.assertEqual(
                (page_path.parent / payload["previewPath"]).resolve(),
                Path(review["artifacts"]["preview_video"]["path"]),
            )
            self.assertEqual(
                (page_path.parent / payload["contactPath"]).resolve(),
                Path(review["artifacts"]["preview_contact_sheet"]["path"]),
            )
            self.assertEqual([segment["contentType"] for segment in payload["segments"]], [
                "PRESENTER", "WIDE_INFORMATION",
            ])
            self.assertEqual(payload["segments"][0]["crop"], {
                "x": 656, "y": 0, "width": 608, "height": 1080,
            })
            self.assertEqual(payload["probe"]["output"]["width"], 360)
            self.assertEqual(payload["probe"]["output"]["fps"], "30000/1001")
            self.assertTrue(payload["probe"]["output"]["audio"])
            self.assertEqual(payload["warnings"], ["Operator warning.", "Validator warning."])
            self.assertEqual(page_path.parent, fixture["review_out"])
            self.assertIn(review["review_id"], page_path.name)
            self.assertTrue(question_path.is_file())
            self.assertEqual(Path(review["artifacts"]["vertical_review_page"]["path"]), page_path)
            self.assertEqual(
                (fixture["review_out"] / "short-001-vertical-review.html").read_bytes(),
                page_path.read_bytes(),
            )

    def test_review_required_page_has_no_media_and_cannot_be_approved(self):
        import review_gate
        from transcript_utils import load_json

        with tempfile.TemporaryDirectory() as directory:
            fixture = open_vertical_fixture(Path(directory), "REVIEW_REQUIRED")
            review_path, _question_path, page_path = fixture["result"]
            review = load_json(review_path)
            html = page_path.read_text(encoding="utf-8")
            encoded = re.search(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)"', html).group(1)
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            self.assertFalse(payload["renderable"])
            self.assertIsNone(payload["previewPath"])
            self.assertIsNone(payload["contactPath"])
            response = (
                "Shorts vertical review\nShort: short-001\n"
                f"Review: {review['review_id']}\nDecision: approve"
            )
            with self.assertRaisesRegex(SystemExit, "REVIEW_REQUIRED"):
                review_gate.answer_vertical_review(fixture["source"].parent, response)
            self.assertEqual(load_json(review_path)["status"], "pending")

    def test_review_scopes_flat_evidence_and_old_receipt_survives_next_preview(self):
        import review_gate
        from transcript_utils import load_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = open_vertical_fixture(root)
            first_review = load_json(first["result"][0])
            first_page = first["result"][2]
            html = first_page.read_text(encoding="utf-8")
            encoded = re.search(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)"', html).group(1)
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
            first_preview = Path(first_review["artifacts"]["preview_video"]["path"])
            first_contact = Path(first_review["artifacts"]["preview_contact_sheet"]["path"])
            first_summary = Path(first_review["artifacts"]["preview_summary"]["path"])
            first_probe = Path(first_review["artifacts"]["media_probe"]["path"])
            evidence_dir = first_preview.parent
            self.assertEqual(evidence_dir, first_contact.parent)
            self.assertEqual(evidence_dir, first_summary.parent)
            self.assertEqual(evidence_dir, first_probe.parent)
            self.assertEqual(evidence_dir.parent.name, "short-001-vertical-review-assets")
            self.assertEqual(evidence_dir.name, first_review["review_id"])
            self.assertNotIn("..", payload["previewPath"])
            self.assertEqual((first_page.parent / payload["previewPath"]).resolve(), first_preview)
            self.assertEqual((first_page.parent / payload["contactPath"]).resolve(), first_contact)
            before = {path: path.read_bytes() for path in (
                first_preview, first_contact, first_summary, first_probe,
            )}

            second = open_vertical_fixture(root)
            second_review = load_json(second["result"][0])
            self.assertNotEqual(first_review["review_id"], second_review["review_id"])
            self.assertEqual(before, {path: path.read_bytes() for path in before})
            review_gate.verify_vertical_artifacts(first_review)

            first_preview.write_bytes(first_preview.read_bytes() + b"changed")
            with self.assertRaisesRegex(SystemExit, "changed after review"):
                review_gate.verify_vertical_artifacts(first_review)

    def test_review_required_scoped_evidence_contains_only_json_receipts(self):
        from transcript_utils import load_json

        with tempfile.TemporaryDirectory() as directory:
            fixture = open_vertical_fixture(Path(directory), "REVIEW_REQUIRED")
            review = load_json(fixture["result"][0])
            summary = Path(review["artifacts"]["preview_summary"]["path"])
            probe = Path(review["artifacts"]["media_probe"]["path"])
            self.assertEqual(summary.parent, probe.parent)
            self.assertEqual(summary.parent.name, review["review_id"])
            self.assertEqual({path.name for path in summary.parent.iterdir()}, {
                "preview-summary.json", "media-probe.json",
            })
            self.assertNotIn("preview_video", review["artifacts"])
            self.assertNotIn("preview_contact_sheet", review["artifacts"])

    def test_scoped_evidence_collision_preserves_existing_directory(self):
        import review_gate

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = (
                root / "review" / "06-shorts" /
                "short-001-vertical-review-assets" / "fixed-id"
            )
            evidence.mkdir(parents=True)
            sentinel = evidence / "sentinel.txt"
            sentinel.write_bytes(b"existing")
            with mock.patch.object(
                review_gate.secrets, "token_hex", return_value="fixed-id"
            ), self.assertRaisesRegex(SystemExit, "already exists"):
                open_vertical_fixture(root)
            self.assertEqual(sentinel.read_bytes(), b"existing")

    def test_every_bound_artifact_mutation_invalidates_final(self):
        import review_gate
        from transcript_utils import load_json

        labels = (
            "source_video", "vertical_plan", "preview_summary", "media_probe",
            "preview_video", "preview_contact_sheet", "vertical_review_page",
        )
        for label in labels:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                fixture = open_vertical_fixture(Path(directory))
                review_path, _question_path, _page_path = fixture["result"]
                review = load_json(review_path)
                response = (
                    "Shorts vertical review\nShort: short-001\n"
                    f"Review: {review['review_id']}\nDecision: approve"
                )
                review_gate.answer_vertical_review(fixture["source"].parent, response)
                artifact_path = Path(load_json(review_path)["artifacts"][label]["path"])
                artifact_path.write_bytes(artifact_path.read_bytes() + b"changed")
                candidate = {"review_id": "candidate-review-1"}
                with mock.patch.object(
                    review_gate, "validate_vertical_delivery_allowed",
                    return_value=(Path(directory), candidate),
                ), self.assertRaisesRegex(SystemExit, "changed after review"):
                    review_gate.validate_vertical_review(
                        fixture["source"].parent, fixture["source"], fixture["plan"]
                    )

    def test_revise_and_skip_preserve_non_approved_statuses(self):
        import review_gate
        from transcript_utils import load_json

        cases = (("revise", "changes_requested", "\nChanges: Move the crop left."), ("skip", "skipped", ""))
        for decision, status, suffix in cases:
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as directory:
                fixture = open_vertical_fixture(Path(directory))
                review_path = fixture["result"][0]
                review = load_json(review_path)
                response = (
                    "Shorts vertical review\nShort: short-001\n"
                    f"Review: {review['review_id']}\nDecision: {decision}{suffix}"
                )
                answered = review_gate.answer_vertical_review(fixture["source"].parent, response)
                self.assertEqual(answered["status"], status)
                with self.assertRaisesRegex(SystemExit, "not approved"):
                    review_gate.validate_vertical_review(
                        fixture["source"].parent, fixture["source"], fixture["plan"]
                    )

    def test_publish_collision_rollback_path_escape_and_alias_warning(self):
        import review_gate

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_out = root / "review" / "06-shorts"
            review_out.mkdir(parents=True)
            collision = review_out / "short-001-vertical-review-fixed-id.html"
            collision.write_bytes(b"first-publication")
            with mock.patch.object(review_gate.secrets, "token_hex", return_value="fixed-id"), self.assertRaisesRegex(SystemExit, "already exists"):
                open_vertical_fixture(root)
            self.assertEqual(collision.read_bytes(), b"first-publication")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "review" / "vertical_review.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"prior-receipt")

            real_atomic = review_gate.atomic_write_json
            def interrupted(path, data):
                if Path(path) == receipt:
                    raise OSError("receipt denied")
                return real_atomic(path, data)

            with self.assertRaisesRegex(OSError, "receipt denied"):
                open_vertical_fixture(root, atomic_write_json=interrupted)
            self.assertEqual(receipt.read_bytes(), b"prior-receipt")
            self.assertFalse(list((root / "review" / "06-shorts").glob("*-vertical-review-*.html")))
            asset_roots = list((root / "review" / "06-shorts").glob("*-vertical-review-assets"))
            self.assertTrue(all(not any(path.iterdir()) for path in asset_roots))

        with tempfile.TemporaryDirectory() as directory:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                fixture = open_vertical_fixture(
                    Path(directory), atomic_copy_alias=mock.Mock(side_effect=OSError("alias denied"))
                )
            self.assertTrue(fixture["result"][2].is_file())
            self.assertIn(str(fixture["result"][2]), stderr.getvalue())
            self.assertIn("alias", stderr.getvalue().lower())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = open_vertical_fixture(root)
            outside = root / "outside.mp4"
            outside.write_bytes(b"outside")
            with mock.patch.object(
                review_gate, "validate_vertical_delivery_allowed",
                return_value=(root, {"review_id": "candidate-review-1"}),
            ), self.assertRaisesRegex(SystemExit, "review directory"):
                review_gate.open_vertical_review(
                    root, fixture["source"], fixture["plan"], fixture["summary"],
                    fixture["probe"], outside, fixture["contact"],
                    review_out=fixture["review_out"], short_id="short-002",
                )

    def test_invalid_crop_geometry_fails_before_page_publication(self):
        cases = (
            ("crop_x", float("nan")),
            ("crop_y", "0"),
            ("crop_width", True),
            ("crop_height", 0),
            ("crop_width", -1),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)

                def mutate(plan, field=field, value=value):
                    plan["segments"][0][field] = value

                with self.assertRaisesRegex(SystemExit, "crop"):
                    open_vertical_fixture(root, plan_mutator=mutate)
                review_out = root / "review" / "06-shorts"
                self.assertFalse(list(review_out.glob("*-vertical-review-*.html")))

    def test_plan_strategy_coverage_and_source_metadata_use_deterministic_validator(self):
        mutations = (
            lambda plan: plan.__setitem__("strategy", "BOGUS"),
            lambda plan: plan["segments"][1].__setitem__("start_time", 6.5),
            lambda plan: plan["segments"][1].__setitem__("start_time", 5.5),
            lambda plan: plan.__setitem__("source_width", float("nan")),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(SystemExit):
                    open_vertical_fixture(root, plan_mutator=mutate)
                self.assertFalse(list((root / "review" / "06-shorts").glob("*-vertical-review-*.html")))

    def test_preview_probe_contact_and_bound_probe_must_be_valid_and_match(self):
        import review_gate

        with tempfile.TemporaryDirectory() as directory:
            corrupt = Path(directory) / "corrupt.mp4"
            corrupt.write_bytes(b"not-an-mp4")
            with self.assertRaisesRegex(SystemExit, "decodable|ffprobe"):
                review_gate.probe_review_media(corrupt)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mismatched = {
                "width": 362, "height": 640, "fps": "30000/1001",
                "durationS": 12.0, "audio": True,
            }
            with self.assertRaisesRegex(SystemExit, "probe|dimensions"):
                open_vertical_fixture(root, probe_review_media=mock.Mock(return_value=mismatched))
            self.assertFalse(list((root / "review" / "06-shorts").glob("*-vertical-review-*.html")))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(SystemExit, "contact sheet"):
                open_vertical_fixture(root, contact_bytes=b"not-an-image")
            self.assertFalse(list((root / "review" / "06-shorts").glob("*-vertical-review-*.html")))

    def test_exact_json_snapshot_mutation_cleans_page_and_preserves_receipt(self):
        import hashlib
        import review_gate

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "review" / "vertical_review.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"prior-receipt")
            mutated = False

            def mutating_snapshot(path, label, schema=None):
                nonlocal mutated
                path = Path(path).resolve()
                raw = path.read_bytes()
                data = json.loads(raw.decode("utf-8-sig"))
                entry = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                if label == "vertical plan" and not mutated:
                    path.write_bytes(raw + b" ")
                    mutated = True
                return path, entry, data, raw

            with mock.patch.object(
                review_gate, "snapshot_json_artifact", side_effect=mutating_snapshot, create=True
            ), self.assertRaisesRegex(SystemExit, "changed"):
                open_vertical_fixture(root)
            self.assertEqual(receipt.read_bytes(), b"prior-receipt")
            self.assertFalse(list((root / "review" / "06-shorts").glob("*-vertical-review-*.html")))

    def test_legacy_open_receipt_failure_cleans_new_question_and_preserves_receipt(self):
        import review_gate
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "short_01" / "source.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            plan = root / "vertical_plan.json"
            summary = root / "preview_summary.md"
            write_json(plan, {"strategy": "STATIC_CROP"})
            summary.write_text("summary", encoding="utf-8")
            receipt = root / "review" / "vertical_review.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_bytes(b"prior-receipt")
            real_atomic = review_gate.atomic_write_json

            def interrupted(path, data):
                if Path(path) == receipt:
                    raise OSError("receipt denied")
                return real_atomic(path, data)

            candidate = {"review_id": "candidate-review", "decision_mode": "human"}
            with mock.patch.object(
                review_gate, "validate_vertical_delivery_allowed", return_value=(root, candidate)
            ), mock.patch.object(
                review_gate, "atomic_write_json", side_effect=interrupted
            ), self.assertRaisesRegex(OSError, "receipt denied"):
                review_gate.open_vertical_review(root, source, plan, summary)
            self.assertEqual(receipt.read_bytes(), b"prior-receipt")
            self.assertFalse(list((root / "review").glob("vertical-review-*-question.md")))

    def test_validated_review_returns_the_exact_verified_plan_snapshot(self):
        import review_gate
        from transcript_utils import load_json

        with tempfile.TemporaryDirectory() as directory:
            fixture = open_vertical_fixture(Path(directory))
            review = load_json(fixture["result"][0])
            response = (
                "Shorts vertical review\nShort: short-001\n"
                f"Review: {review['review_id']}\nDecision: approve"
            )
            review_gate.answer_vertical_review(fixture["source"].parent, response)
            candidate = {"review_id": "candidate-review-1"}
            with mock.patch.object(
                review_gate, "validate_vertical_delivery_allowed",
                return_value=(fixture["source"].parent, candidate),
            ):
                _review, plan = review_gate.load_validated_vertical_review(
                    fixture["source"].parent, fixture["source"], fixture["plan"]
                )
            self.assertEqual(plan, json.loads(fixture["plan"].read_text(encoding="utf-8")))


class VerticalRenderIntegrationTests(unittest.TestCase):
    def test_preview_handoff_uses_review_directory_short_id_and_json_summary(self):
        import render_vertical
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "short-001-horizontal.mp4"
            source.write_bytes(b"source")
            plan_path = root / "vertical_plan.json"
            write_json(plan_path, vertical_fixture(source))
            review_out = root / "review" / "06-shorts"
            source_probe = vertical_probe_fixture()["source"]
            output_probe = vertical_probe_fixture()["output"]
            probes = iter((source_probe, output_probe))

            def fake_render(_ffmpeg, _probe, _video, _plan, output, *_args):
                Path(output).write_bytes(b"preview")

            def fake_contact(_ffmpeg, _video, output, _duration, _label):
                write_jpeg(output, 810, 516)

            argv = [
                "render_vertical.py", "--video", str(source), "--plan", str(plan_path),
                "--out", str(root / "vertical-agent"), "--review-out", str(review_out),
                "--mode", "preview",
            ]
            stdout = io.StringIO()
            with mock.patch("sys.argv", argv), mock.patch.object(
                render_vertical, "validate_vertical_delivery_allowed"
            ), mock.patch.object(
                render_vertical, "resolve_tool", side_effect=lambda name, _explicit: name
            ), mock.patch.object(
                render_vertical, "probe_media", side_effect=lambda *_args: next(probes)
            ), mock.patch.object(
                render_vertical, "render", side_effect=fake_render
            ), mock.patch.object(
                render_vertical, "make_contact_sheet", side_effect=fake_contact
            ), mock.patch.object(
                render_vertical, "detect_stable_black_bars", return_value={
                    "mode": "test", "detected": False,
                    "background_crop": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                    "foreground_crop_applied": False,
                }
            ), mock.patch.object(
                render_vertical, "open_vertical_review",
                return_value=(root / "receipt.json", root / "question.md", root / "page.html"),
            ) as opened, contextlib.redirect_stdout(stdout):
                render_vertical.main()

            call = opened.call_args
            self.assertEqual(call.kwargs["review_out"], review_out.resolve())
            self.assertEqual(call.kwargs["short_id"], "short-001")
            summary_path = call.args[3]
            self.assertEqual(summary_path.suffix, ".json")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["schema_version"], "video-to-shorts.vertical-preview-summary.v1")
            self.assertEqual(summary["mode"], "preview")
            self.assertIn("authoritative page", stdout.getvalue())
            self.assertIn("STOP", stdout.getvalue())

    def test_standalone_preview_publishes_pages_under_out_review(self):
        import render_vertical
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vertical_root = root / "vertical-agent"
            source = root / "short-001-horizontal.mp4"
            source.write_bytes(b"source")
            plan_path = vertical_root / "vertical_plan.json"
            write_json(plan_path, vertical_fixture(source, "STATIC_CROP") | {
                "segments": [{
                    "start_time": 0.0, "end_time": 12.0, "strategy": "STATIC_CROP",
                    "content_type": "PRESENTER", "crop_x": 656, "crop_y": 0,
                    "crop_width": 608, "crop_height": 1080, "reason": "Stable crop.",
                }],
                "strategy": "STATIC_CROP",
            })
            source_probe = vertical_probe_fixture()["source"]
            output_probe = vertical_probe_fixture()["output"]
            probes = iter((source_probe, output_probe))

            def fake_render(_ffmpeg, _probe, _video, _plan, output, *_args):
                Path(output).write_bytes(b"preview")

            def fake_contact(_ffmpeg, _video, output, _duration, _label):
                write_jpeg(output, 810, 516)

            def fake_open(*_args, **kwargs):
                page_dir = Path(kwargs["review_out"])
                page_dir.mkdir(parents=True, exist_ok=True)
                page = page_dir / "short-001-vertical-review-review-id.html"
                alias = page_dir / "short-001-vertical-review.html"
                question = page_dir / "short-001-vertical-review-review-id-question.md"
                page.write_text("authoritative", encoding="utf-8")
                alias.write_text("latest", encoding="utf-8")
                question.write_text("question", encoding="utf-8")
                return vertical_root / "review" / "vertical_review.json", question, page

            argv = [
                "render_vertical.py", "--video", str(source), "--plan", str(plan_path),
                "--out", str(vertical_root), "--mode", "preview",
            ]
            with mock.patch("sys.argv", argv), mock.patch.object(
                render_vertical, "validate_vertical_delivery_allowed"
            ), mock.patch.object(
                render_vertical, "resolve_tool", side_effect=lambda name, _explicit: name
            ), mock.patch.object(
                render_vertical, "probe_media", side_effect=lambda *_args: next(probes)
            ), mock.patch.object(
                render_vertical, "render", side_effect=fake_render
            ), mock.patch.object(
                render_vertical, "make_contact_sheet", side_effect=fake_contact
            ), mock.patch.object(
                render_vertical, "open_vertical_review", side_effect=fake_open
            ) as opened, contextlib.redirect_stdout(io.StringIO()):
                render_vertical.main()

            self.assertEqual(opened.call_args.kwargs["review_out"], (vertical_root / "review").resolve())
            self.assertTrue((vertical_root / "review" / "short-001-vertical-review-review-id.html").is_file())
            self.assertTrue((vertical_root / "review" / "short-001-vertical-review.html").is_file())
            self.assertFalse(list((vertical_root / "preview").glob("*.html")))


class ExplicitPlannerSelectionTests(unittest.TestCase):
    def test_explicit_selection_rejects_any_deterministic_drop(self):
        import plan

        rejected = [
            ({"candidate_id": "cand-002"}, {"errors": ["LOW_SCORE", "SHORT_DURATION"]}),
            ({"candidate_id": "cand-003"}, {"errors": ["OVERLAPS_HIGHER_SCORE"]}),
        ]
        with self.assertRaisesRegex(SystemExit, r"cand-002.*LOW_SCORE.*SHORT_DURATION.*cand-003.*OVERLAPS_HIGHER_SCORE"):
            plan.require_explicit_selection_survived("explicit_user_selection", rejected)
        plan.require_explicit_selection_survived("default_text_visual_top_five", rejected)


class BoundPlannerTranscriptTests(unittest.TestCase):
    def test_bound_planner_rejects_different_transcript_argument(self):
        import plan
        import review_gate
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bound = root / "bound.json"
            other = root / "other.json"
            write_json(bound, {"duration": 30.0, "segments": []})
            write_json(other, {"duration": 90.0, "segments": []})
            review = {"bound_visual_review": True, "artifacts": {"transcript": review_gate.artifact(bound)}}
            with self.assertRaisesRegex(SystemExit, "does not match"):
                plan.load_planning_transcript(review, other, root / "default.json")

    def test_bound_planner_rejects_transcript_mutated_after_receipt(self):
        import plan
        import review_gate
        from transcript_utils import write_json

        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "transcript.json"
            write_json(transcript, {"duration": 30.0, "segments": []})
            review = {"bound_visual_review": True, "artifacts": {"transcript": review_gate.artifact(transcript)}}
            transcript.write_text(transcript.read_text() + " ", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "changed"):
                plan.load_planning_transcript(review, None, Path(directory) / "default.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
