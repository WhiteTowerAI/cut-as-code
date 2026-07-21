"""Self-check for the source-backed caption evidence review builder."""

import base64
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
BUILDER_PATH = SCRIPT_DIR / "build_caption_review.py"
TEMPLATE_PATH = SCRIPT_DIR.parent / "assets" / "captions-review.html"
MARKER = "__CAPTION_EVIDENCE_REVIEW_DATA__"
LABELS = ["early", "middle", "late", "no-caption"]
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


def load_builder():
    spec = importlib.util.spec_from_file_location("caption_review_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(root):
    source = root / "source.png"
    Image.new("RGB", (320, 180), (42, 55, 63)).save(source)
    timeline = root / "timeline.json"
    write_json(timeline, {
        "schema_version": 1,
        "timeline_id": "mapped",
        "source_asset_id": "source",
        "fps": {"num": 30, "den": 1},
        "source_duration_s": 30,
        "program_duration_s": 12,
        "clips": [
            {"id": "a", "source_range": {"start_s": 10, "end_s": 16},
             "program_range": {"start_s": 0, "end_s": 3}, "speed": 2, "decision_ref": "a"},
            {"id": "b", "source_range": {"start_s": 20, "end_s": 29},
             "program_range": {"start_s": 3, "end_s": 12}, "speed": 1, "decision_ref": "b"},
        ],
    })
    plan = root / "captions.json"
    write_json(plan, {
        "timeline_id": "mapped",
        "program_duration_s": 12,
        "cues": [
            {"index": 1, "start": 0.5, "end": 1.5, "text": "Opening cue"},
            {"index": 2, "start": 4, "end": 5, "text": "</script><script>unsafe()</script>"},
            {"index": 3, "start": 8, "end": 9, "text": "Closing cue"},
        ],
    })
    state = root / "interaction.json"
    write_json(state, {
        "schemaVersion": 1,
        "skill": "video-add-captions",
        "reviewId": "review-123",
        "decisionMode": "human",
        "phase": "style_selected",
        "selection": {"choiceId": "clean"},
        "sourceVideo": {"path": str(source.resolve()), "sha256": file_sha256(source)},
        "captions": {"path": str(plan.resolve()), "sha256": file_sha256(plan)},
    })
    snapshots = root / "snapshots"
    snapshots.mkdir()
    for index in range(4):
        image = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
        if index < 3:
            ImageDraw.Draw(image).rectangle((80, 125, 240, 155), fill=(255, 225, 60, 230))
        image.save(snapshots / f"frame-{index + 1:02d}.png")
    return source, timeline, plan, state, snapshots


def fake_ffmpeg(command, check):
    assert command[0] == "ffmpeg"
    Image.new("RGB", (320, 180), (42, 55, 63)).save(command[-1])


def run_builder(module, root, *, snapshots=None):
    source, timeline, plan, state, default_snapshots = make_fixture(root)
    out = root / "review"
    out.mkdir()
    (out / "captions.srt").write_text("durable\n", encoding="utf-8")
    with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
        module.main([
            "--source", str(source), "--timeline", str(timeline), "--plan", str(plan),
            "--interaction-state", str(state), "--snapshots", str(snapshots or default_snapshots),
            "--out", str(out), "--cache", str(root / "cache"),
        ])
    return out


def check_template():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    for name, value in TOKENS.items():
        assert f"--{name}: {value}" in html
    assert "width: min(1180px, calc(100% - 32px))" in html
    assert ".toolbar" in html and "position: sticky" in html
    for element_id in ("review-status", "review-form", "copy-summary", "summary-output", "review-errors"):
        assert f'id="{element_id}"' in html
    assert "min-height: 38px" in html
    assert "@media (max-width: 1100px)" in html
    assert "@media (max-width: 780px)" in html
    assert html.count(MARKER) == 1


def check_builder():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-check-") as temporary:
        out = run_builder(module, Path(temporary))
        evidence = json.loads((out / "captions-evidence.json").read_text(encoding="utf-8"))
        assert (out / "captions.srt").read_text(encoding="utf-8") == "durable\n"
        samples = evidence["samples"]
        assert [item["label"] for item in samples] == LABELS
        assert len(set(item["label"] for item in samples)) == 4
        assert [item["program_s"] for item in samples] == [1.0, 4.5, 8.5, 6.5]
        assert [item["source_s"] for item in samples] == [12.0, 21.5, 25.5, 23.5]
        assert [item["cue_text"] for item in samples[:3]] == [
            "Opening cue", "</script><script>unsafe()</script>", "Closing cue",
        ]
        assert all(Path(item["preview"]).name == item["preview"] for item in samples)
        images = [Image.open(out / item["preview"]) for item in samples]
        try:
            assert {image.size for image in images} == {(320, 180)}
            assert all(image.getbbox() for image in images)
        finally:
            for image in images:
                image.close()

        page = (out / "captions-review.html").read_text(encoding="utf-8")
        assert page.count(MARKER) == 0
        assert "</script><script>unsafe()" not in page
        match = module.REVIEW_PAYLOAD_PATTERN.search(page)
        assert match
        payload = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
        assert payload["review_id"] == "review-123"
        assert payload["selection_id"] == "clean"
        assert [item["label"] for item in payload["samples"]] == LABELS
        assert [item["preview"] for item in payload["samples"]] == [f"preview-{label}.png" for label in LABELS]


def check_failure_is_atomic():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-failure-") as temporary:
        root = Path(temporary)
        source, timeline, plan, state, snapshots = make_fixture(root)
        Image.new("RGBA", (160, 90), (255, 255, 255, 255)).save(snapshots / "frame-03.png")
        out = root / "review"
        try:
            with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
                module.main([
                    "--source", str(source), "--timeline", str(timeline), "--plan", str(plan),
                    "--interaction-state", str(state), "--snapshots", str(snapshots),
                    "--out", str(out), "--cache", str(root / "cache"),
                ])
        except ValueError:
            pass
        else:
            raise AssertionError("mismatched preview dimensions must fail")
        assert not (out / "captions-review.html").exists()
        assert not (out / "captions-evidence.json").exists()
        assert not list(out.glob("preview-*.png"))


def check_bound_inputs_cannot_be_substituted():
    module = load_builder()
    for substituted in ("source", "plan"):
        with tempfile.TemporaryDirectory(prefix=f"caption-review-{substituted}-") as temporary:
            root = Path(temporary)
            source, timeline, plan, state, snapshots = make_fixture(root)
            out = root / "review"
            out.mkdir()
            owned = out / "captions-summary.md"
            owned.write_text("authoritative\n", encoding="utf-8")
            wrong_source = root / "wrong-source.png"
            Image.new("RGB", (320, 180), (90, 20, 30)).save(wrong_source)
            wrong_plan = root / "wrong-plan.json"
            wrong = json.loads(plan.read_text(encoding="utf-8"))
            wrong["cues"][0]["text"] = "Substituted"
            write_json(wrong_plan, wrong)
            argv = [
                "--source", str(wrong_source if substituted == "source" else source),
                "--timeline", str(timeline),
                "--plan", str(wrong_plan if substituted == "plan" else plan),
                "--interaction-state", str(state), "--snapshots", str(snapshots),
                "--out", str(out), "--cache", str(root / "cache"),
            ]
            try:
                with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
                    module.main(argv)
            except ValueError:
                pass
            else:
                raise AssertionError(f"bound {substituted} substitution must fail")
            assert owned.read_text(encoding="utf-8") == "authoritative\n"
            assert not (out / "captions-review.html").exists()


def check_standalone_rebuild_removes_stale_page():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-standalone-") as temporary:
        root = Path(temporary)
        out = run_builder(module, root)
        assert (out / "captions-review.html").is_file()
        source = root / "source.png"
        timeline = root / "timeline.json"
        plan = root / "captions.json"
        snapshots = root / "snapshots"
        with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
            module.main([
                "--source", str(source), "--timeline", str(timeline), "--plan", str(plan),
                "--snapshots", str(snapshots), "--out", str(out), "--cache", str(root / "cache"),
            ])
        assert not (out / "captions-review.html").exists()
        assert (out / "captions-evidence.json").is_file()
        assert (out / "captions.srt").read_text(encoding="utf-8") == "durable\n"


check_template()
print("[caption-review] PASS shared evidence shell")
check_builder()
print("[caption-review] PASS mapped evidence and safe payload")
check_failure_is_atomic()
print("[caption-review] PASS atomic failure")
check_standalone_rebuild_removes_stale_page()
print("[caption-review] PASS stale page removal")
check_bound_inputs_cannot_be_substituted()
print("[caption-review] PASS bound input integrity")
print("[caption-review] 5 checks passed")
