"""Self-check for the source-backed caption evidence review builder."""

import base64
import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import caption_spatial_context
import check_caption_spatial_context as spatial_check


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


def make_expressive_fixture(root):
    source, timeline, plan, state, _ = make_fixture(root)
    cues = [
        {"id": "cue-001", "index": 1, "start": 0.5, "end": 1.5, "text": "Opening setup",
         "words": [{"word": "Opening", "semantic_role": "normal"},
                   {"word": "setup", "semantic_role": "normal"}]},
        {"id": "cue-002", "index": 2, "start": 3.5, "end": 4.5, "text": "Three layouts",
         "words": [{"word": "Three", "semantic_role": "number"},
                   {"word": "layouts", "semantic_role": "keyword"}],
         "hero_line": {"level": "strong", "word_indexes": [1, 2], "rationale": "Fixture hero."}},
        {"id": "cue-003", "index": 3, "start": 6.5, "end": 7.5, "text": "Context first",
         "words": [{"word": "Context", "semantic_role": "keyword"},
                   {"word": "first", "semantic_role": "normal"}]},
        {"id": "cue-004", "index": 4, "start": 8.5, "end": 9.5, "text": "Return to baseline",
         "words": [{"word": "Return", "semantic_role": "normal"},
                   {"word": "baseline", "semantic_role": "contrast"}]},
    ]
    write_json(plan, {
        "timeline_id": "mapped",
        "program_duration_s": 12,
        "cues": cues,
        "presentation": {
            "mode": "expressive",
            "layout_beats": [
                {"id": "beat-001", "variant": "bottom-standard", "cue_ids": ["cue-001"],
                 "program_range": {"start_s": 0.5, "end_s": 1.5}},
                {"id": "beat-002", "variant": "center-emphasis", "cue_ids": ["cue-002"],
                 "program_range": {"start_s": 3.5, "end_s": 4.5}},
                {"id": "beat-003", "variant": "bottom-standard", "cue_ids": ["cue-003"],
                 "program_range": {"start_s": 6.5, "end_s": 7.5}},
                {"id": "beat-004", "variant": "center-emphasis", "cue_ids": ["cue-004"],
                 "program_range": {"start_s": 8.5, "end_s": 9.5}},
            ],
        },
    })
    state_value = json.loads(state.read_text(encoding="utf-8"))
    state_value["captions"]["sha256"] = file_sha256(plan)
    write_json(state, state_value)
    snapshots = root / "expressive-snapshots"
    snapshots.mkdir()
    for index in range(5):
        image = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
        if index < 4:
            color = (244, 197, 66, 230) if index == 1 else (255, 225, 60, 230)
            ImageDraw.Draw(image).rectangle((80, 60 + index * 15, 240, 90 + index * 15), fill=color)
        image.save(snapshots / f"frame-{index + 1:02d}.png")
    comparison = root / "comparison-snapshots"
    comparison.mkdir()
    image = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((75, 62, 245, 96), fill=(255, 190, 40, 230))
    image.save(comparison / "frame-01.png")
    return source, timeline, plan, state, snapshots, comparison


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
    assert 'data-filter="center-emphasis"' in html
    for placement in ("preset-bottom", "frame-center", "panel-center", "hero-1.5x"):
        assert f'data-filter="{placement}"' in html
    assert 'data-filter="hero-strong"' not in html
    assert 'data-filter="hero-hero"' not in html
    assert "Hero 2x" not in html
    assert 'data-filter="top-statement"' not in html
    assert "Top statement" not in html
    assert '<section id="comparison" class="comparison" hidden>' in html
    assert 'id="comparison-grid"' in html
    assert 'id="karaoke-choice"' in html
    karaoke_radios = html.split('<input type="radio" name="karaoke"')
    assert len(karaoke_radios) - 1 == 2
    assert 'value="off"' in html and 'value="on"' in html
    assert not any("checked" in fragment.split(">", 1)[0] for fragment in karaoke_radios[1:])
    assert 'Karaoke: ${karaokeChoice.value}' in html
    assert "!isExpressive || Boolean(karaokeChoice)" in html
    assert '<button id="copy-summary" type="button" disabled>' in html
    assert "if (isExpressive && reviewData.experimental_comparison)" in html
    assert "reviewData.review_samples" in html
    assert "expressive-layout-beats" in html
    assert html.count(MARKER) == 1


def check_representative_evidence_selection():
    module = load_builder()
    samples = [
        {
            "label": "entry-blank", "preview": "entry-blank.png", "sha256": "0" * 64,
            "requested_variant": "bottom-standard", "resolved_placement": "preset-bottom",
            "clearance_status": "pass", "caption_bbox": None, "hero_line": None,
        },
        {
            "label": "bottom-a", "preview": "bottom-a.png", "sha256": "a" * 64,
            "requested_variant": "bottom-standard", "resolved_placement": "preset-bottom",
            "clearance_status": "pass", "hero_line": None,
        },
        {
            "label": "bottom-b", "preview": "bottom-b.png", "sha256": "b" * 64,
            "requested_variant": "bottom-standard", "resolved_placement": "preset-bottom",
            "clearance_status": "pass", "hero_line": None,
        },
        {
            "label": "center", "preview": "center.png", "sha256": "c" * 64,
            "requested_variant": "center-emphasis", "resolved_placement": "frame-center",
            "clearance_status": "pass", "hero_line": None,
        },
        {
            "label": "panel", "preview": "panel.png", "sha256": "d" * 64,
            "requested_variant": "bottom-standard", "resolved_placement": "panel-center",
            "clearance_status": "pass", "hero_line": None,
        },
        {
            "label": "hero", "preview": "hero.png", "sha256": "e" * 64,
            "requested_variant": "center-emphasis", "resolved_placement": "frame-center",
            "clearance_status": "pass",
            "hero_line": {"level": "hero", "word_indexes": [1]},
        },
        {
            "label": "technical", "preview": "technical.png", "sha256": "f" * 64,
            "requested_variant": "bottom-standard", "resolved_placement": "panel-bottom",
            "clearance_status": "pass", "hero_line": None,
        },
    ]
    selected = module.select_review_samples(samples)
    assert len(selected) == 3
    assert len({item["preview"] for item in selected}) == len(selected)
    categories = [category for item in selected for category in item["categories"]]
    assert set(categories) == {
        "bottom-standard", "center-emphasis", "preset-bottom", "frame-center",
        "panel-center", "hero-1.5x",
    }
    assert len(categories) == len(set(categories))
    shared = next(item for item in selected if item["preview"] == "bottom-a.png")
    assert shared["categories"] == ["bottom-standard", "preset-bottom"]
    assert all(item["sample_label"] in {sample["label"] for sample in samples} for item in selected)


def check_entry_animation_boundary_clearance():
    module = load_builder()
    plan = {
        "program_duration_s": 3,
        "cues": [{
            "id": "cue-001", "index": 1, "start": 1, "end": 2, "text": "Entry cue",
            "words": [{"word": "Entry", "semantic_role": "normal"},
                      {"word": "cue", "semantic_role": "normal"}],
            "hero_line": {"level": "hero", "word_indexes": [1], "rationale": "Entry fixture."},
        }],
    }
    context = {
        "placement_beats": [{
            "id": "spatial-001", "cue_ids": ["cue-001"], "cue_indexes": [1],
            "program_range": {"start_s": 1, "end_s": 2},
            "visual_context": "full-bleed-wash", "requested_variant": "bottom-standard",
            "resolved_placement": "preset-bottom",
        }],
        "visual_intervals": [{
            "id": "visual-001", "program_range": {"start_s": 1, "end_s": 2},
            "visual_context": "full-bleed-wash",
            "background": {"path": "composite.mp4", "sha256": "a" * 64, "program_start_s": 1},
        }],
    }
    samples = module.spatial_sample_times(plan, {"num": 60, "den": 1}, context)
    entry = next(
        sample for sample in samples
        if sample["frame"] == 60 and "spatial-boundary-after" in sample["purposes"]
    )
    assert entry["cue_index"] == 1
    assert entry["cue_entry_frame"] is True
    blank = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    result = module.inspect_overlay_clearance(blank, entry, context["placement_beats"][0])
    assert result["caption_bbox"] is None
    assert result["caption_visibility"] == "entry-animation-zero"

    ordinary = {**entry, "cue_entry_frame": False}
    try:
        module.inspect_overlay_clearance(blank, ordinary, context["placement_beats"][0])
    except ValueError as error:
        assert "blank at cue 1" in str(error)
    else:
        raise AssertionError("blank cue evidence outside an entry boundary must fail")


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


def check_expressive_builder():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-expressive-") as temporary:
        root = Path(temporary)
        source, timeline, plan, state, snapshots, comparison = make_expressive_fixture(root)
        out = root / "review"
        with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
            module.main([
                "--source", str(source), "--timeline", str(timeline), "--plan", str(plan),
                "--interaction-state", str(state), "--snapshots", str(snapshots),
                "--comparison-snapshots", str(comparison), "--comparison-beat-id", "beat-002",
                "--out", str(out), "--cache", str(root / "cache"),
            ])
        evidence = json.loads((out / "captions-evidence.json").read_text(encoding="utf-8"))
        assert evidence["presentation_mode"] == "expressive"
        assert evidence["machine_evidence_count"] == 5
        assert evidence["primary_evidence_count"] == 2
        assert len(evidence["review_samples"]) == 2
        assert {category for sample in evidence["review_samples"] for category in sample["categories"]} == {
            "bottom-standard", "center-emphasis", "preset-bottom", "frame-center", "hero-1.5x",
        }
        assert [sample.get("beat_id") for sample in evidence["samples"][:-1]] == [
            "beat-001", "beat-002", "beat-003", "beat-004",
        ]
        assert evidence["samples"][-1]["label"] == "no-caption"
        assert {sample["variant"] for sample in evidence["samples"][:-1]} == {
            "bottom-standard", "center-emphasis",
        }
        comparison_payload = evidence["experimental_comparison"]
        assert comparison_payload["beat_id"] == "beat-002"
        assert [sample["mode"] for sample in comparison_payload["samples"]] == [
            "semantic-only", "semantic-plus-karaoke",
        ]
        assert all((out / sample["preview"]).is_file() for sample in comparison_payload["samples"])
        page = (out / "captions-review.html").read_text(encoding="utf-8")
        payload = json.loads(base64.b64decode(module.REVIEW_PAYLOAD_PATTERN.search(page).group(1)))
        assert payload["presentation_mode"] == "expressive"
        assert payload["approval_evidence"] == "expressive-layout-beats"
        assert payload["machine_evidence_count"] == 5
        assert payload["primary_evidence_count"] == 2
        assert len(payload["review_samples"]) == 2
        hero_sample = next(sample for sample in payload["samples"] if sample.get("cue_index") == 2)
        assert hero_sample["hero_line"]["level"] == "strong"
        assert hero_sample["hero_bbox"]

        invalid = json.loads(plan.read_text(encoding="utf-8"))
        invalid["presentation"]["layout_beats"][0]["variant"] = "top-statement"
        try:
            module.expressive_sample_times(invalid, 30)
        except ValueError as error:
            assert "invalid layout beat" in str(error)
        else:
            raise AssertionError("Expressive review must reject top-statement fixtures")


def check_spatial_planner_and_clearance():
    module = load_builder()
    assert module.maintained_hero_color() == "#F4C542"
    style_config = json.loads(module.CAPTION_STYLES.read_text(encoding="utf-8"))
    treatment_binding = {
        "configPath": str(module.CAPTION_STYLES.resolve()),
        "configSha256": file_sha256(module.CAPTION_STYLES),
        "value": style_config["expressiveTreatments"],
    }
    assert module.maintained_hero_color({"expressiveTreatments": treatment_binding}) == "#F4C542"
    try:
        module.maintained_hero_color({})
    except ValueError as error:
        assert "Expressive treatment" in str(error)
    else:
        raise AssertionError("missing Expressive treatment binding must fail")
    for field, value in (
        ("configPath", str(module.CAPTION_STYLES.with_name("other-styles.json"))),
        ("configSha256", "0" * 64),
        ("value", {**style_config["expressiveTreatments"], "heroLine": {"color": "#123456"}}),
    ):
        invalid_binding = copy.deepcopy(treatment_binding)
        invalid_binding[field] = value
        try:
            module.maintained_hero_color({"expressiveTreatments": invalid_binding})
        except ValueError as error:
            assert "Expressive treatment" in str(error)
        else:
            raise AssertionError(f"changed Expressive treatment {field} must fail")
    plan = {
        "timeline_id": "main", "program_duration_s": 6,
        "cues": [
            {"id": "cue-001", "index": 1, "start": 1.0, "end": 2.0, "text": "Panel text",
             "words": [{"word": "Panel"}, {"word": "text"}],
             "hero_line": {"level": "strong", "word_indexes": [1, 2], "rationale": "Fixture."}},
            {"id": "cue-002", "index": 2, "start": 3.0, "end": 4.0, "text": "Closing",
             "words": [{"word": "Closing"}]},
        ],
    }
    context = {
        "visual_intervals": [
            {"id": "visual-001", "program_range": {"start_s": 1.0, "end_s": 2.4},
             "visual_context": "focused-panel",
             "background": {"kind": "normalized-broll-composite", "path": "cache/panel.mp4",
                            "sha256": "a" * 64, "program_start_s": 1.0}},
            {"id": "visual-002", "program_range": {"start_s": 2.4, "end_s": 2.8},
             "visual_context": "corner-pip",
             "background": {"kind": "normalized-broll-composite", "path": "cache/corner.mp4",
                            "sha256": "b" * 64, "program_start_s": 2.4}},
        ],
        "placement_beats": [
            {"id": "spatial-001", "cue_ids": ["cue-001"], "cue_indexes": [1],
             "program_range": {"start_s": 1.0, "end_s": 2.0},
             "visual_context": "focused-panel", "requested_variant": "standard",
             "resolved_placement": "panel-center",
             "anchor": {"x": 0.5, "y": 0.28},
             "allowed_rect": {"x": 0.04, "y": 0.08, "width": 0.92, "height": 0.4},
             "background": {"kind": "normalized-broll-composite", "path": "cache/broll.mp4",
                            "sha256": "a" * 64, "program_start_s": 1.0}},
            {"id": "spatial-002", "cue_ids": ["cue-002"], "cue_indexes": [2],
             "program_range": {"start_s": 3.0, "end_s": 4.0},
             "visual_context": "a-roll", "requested_variant": "standard",
             "resolved_placement": "preset-bottom"},
        ],
    }
    samples = module.spatial_sample_times(plan, 30, context)
    assert len(samples) > 4
    assert any("hero-line" in sample["purposes"] for sample in samples)
    assert any(sample.get("spatial_beat_id") == "spatial-001" for sample in samples)
    assert len({sample["frame"] for sample in samples}) == len(samples)
    gap_boundary = next(
        sample for sample in samples
        if sample.get("visual_interval_id") == "visual-002"
        and "spatial-boundary-after" in sample["purposes"]
    )
    assert gap_boundary["cue_index"] is None
    assert gap_boundary["background"]["kind"] == "normalized-broll-composite"
    first_beat_start = next(sample for sample in samples if sample["label"] == "spatial-001-1")
    assert first_beat_start["program_s"] == 1.0 + 6 / 30
    assert gap_boundary["program_s"] == 2.4
    assert any(sample["label"].startswith("spatial-001-") for sample in samples)
    assert not any(sample["label"].startswith("spatial-002-") for sample in samples)

    rounded_boundary_context = {
        "visual_intervals": [{
            "id": "rounded-end",
            "program_range": {"start_s": 56.883333333, "end_s": 66.566666667},
            "visual_context": "focused-panel",
            "speaker_rect": {"x": 0.3, "y": 0.5, "width": 0.4, "height": 0.3},
        }],
    }
    fps_60 = {"num": 60, "den": 1}
    assert module._visual_interval(rounded_boundary_context, 3412, fps_60) is None
    first_active = module._visual_interval(rounded_boundary_context, 3413, fps_60)
    assert first_active["id"] == "rounded-end"
    assert first_active["visual_context"] == "focused-panel"
    assert first_active["speaker_rect"] is not None
    assert module._visual_interval(rounded_boundary_context, 3993, fps_60)["id"] == "rounded-end"
    assert module._visual_interval(rounded_boundary_context, 3994, fps_60) is None

    crossing_plan = {
        "timeline_id": "main", "program_duration_s": 5,
        "cues": [
            {"id": "cue-panel", "index": 1, "start": 0.8, "end": 1.4,
             "text": "Panel midpoint", "words": [{"word": "Panel"}],
             "unsplittable_word_boundary": {
                 "boundary_s": 1.0, "word_midpoint_s": 1.2, "requires_review": True,
             }},
            {"id": "cue-aroll", "index": 2, "start": 3.3, "end": 4.1,
             "text": "A-roll midpoint", "words": [{"word": "A-roll"}],
             "unsplittable_word_boundary": {
                 "boundary_s": 3.5, "word_midpoint_s": 3.8, "requires_review": True,
             }},
        ],
    }
    panel_background = {"kind": "normalized-broll-composite", "path": "panel.mp4",
                        "sha256": "c" * 64, "program_start_s": 1.0}
    corner_background = {"kind": "normalized-broll-composite", "path": "corner.mp4",
                         "sha256": "d" * 64, "program_start_s": 3.0}
    panel_rect = {"x": 0.04, "y": 0.08, "width": 0.92, "height": 0.4}
    panel_speaker = {"x": 0.3, "y": 0.58, "width": 0.4, "height": 0.3}
    corner_speaker = {"x": 0.0, "y": 0.0, "width": 0.3, "height": 0.3}
    crossing_context = {
        "visual_intervals": [
            {"id": "visual-panel", "program_range": {"start_s": 1.0, "end_s": 1.5},
             "visual_context": "focused-panel", "background": panel_background,
             "speaker_rect": panel_speaker, "allowed_rect": panel_rect},
            {"id": "visual-corner", "program_range": {"start_s": 3.0, "end_s": 3.5},
             "visual_context": "corner-pip", "background": corner_background,
             "speaker_rect": corner_speaker},
        ],
        "placement_beats": [
            {"id": "spatial-panel", "cue_ids": ["cue-panel"], "cue_indexes": [1],
             "program_range": {"start_s": 0.8, "end_s": 1.4},
             "visual_context": "focused-panel", "requested_variant": "standard",
             "resolved_placement": "panel-center", "background": panel_background,
             "speaker_rect": panel_speaker, "allowed_rect": panel_rect},
            {"id": "spatial-aroll", "cue_ids": ["cue-aroll"], "cue_indexes": [2],
             "program_range": {"start_s": 3.3, "end_s": 4.1},
             "visual_context": "a-roll", "requested_variant": "standard",
             "resolved_placement": "preset-bottom"},
        ],
    }
    crossing_samples = module.spatial_sample_times(crossing_plan, 30, crossing_context)
    panel_before = next(sample for sample in crossing_samples
                        if sample.get("cue_index") == 1
                        and "unsplittable-before" in sample["purposes"])
    arroll_before = next(sample for sample in crossing_samples
                         if sample.get("cue_index") == 2
                         and "unsplittable-before" in sample["purposes"])
    midpoint_failures = []
    if panel_before.get("resolved_placement") != "panel-center" or panel_before.get("allowed_rect") != panel_rect:
        midpoint_failures.append("panel placement metadata did not remain cue-stable")
    if panel_before.get("visual_context") != "a-roll" or panel_before.get("background") is not None:
        midpoint_failures.append("panel beat background leaked into boundary-before A-roll sample")
    if panel_before.get("speaker_rect") is not None:
        midpoint_failures.append("panel beat speaker_rect leaked outside its visual interval")
    if (arroll_before.get("resolved_placement") != "preset-bottom"
            or arroll_before.get("visual_context") != "corner-pip"
            or arroll_before.get("background") != corner_background):
        midpoint_failures.append("A-roll placement did not retain interval visual/background evidence")
    if arroll_before.get("speaker_rect") != corner_speaker:
        midpoint_failures.append("inside-B-roll sample did not receive interval speaker_rect")
    collision = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    ImageDraw.Draw(collision).rectangle((10, 10, 80, 50), fill=(255, 255, 255, 255))
    try:
        module.inspect_overlay_clearance(
            collision, arroll_before, crossing_context["placement_beats"][1],
        )
    except ValueError as error:
        if "intersects speaker rect" not in str(error):
            midpoint_failures.append(f"unexpected collision failure: {error}")
    else:
        midpoint_failures.append("inside-B-roll interval speaker collision did not fail clearance")
    assert not midpoint_failures, "; ".join(midpoint_failures)

    inside = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    inside_draw = ImageDraw.Draw(inside)
    inside_draw.rectangle((30, 25, 290, 65), fill=(255, 255, 255, 255))
    inside_draw.rectangle((80, 40, 240, 60), fill=(244, 197, 66, 255))
    result = module.inspect_overlay_clearance(
        inside, {"cue_index": 1, "hero_line": {"level": "strong"}}, context["placement_beats"][0],
        hero_color="#F4C542",
    )
    assert result["clearance_status"] == "pass"
    assert result["caption_bbox"] == [30, 25, 291, 66]
    assert result["hero_bbox"] == [80, 40, 241, 61]

    for y1, y2 in ((14, 30), (70, 85)):
        clipped = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
        clipped_draw = ImageDraw.Draw(clipped)
        clipped_draw.rectangle((30, 20, 290, 80), fill=(255, 255, 255, 255))
        clipped_draw.rectangle((80, y1, 240, y2), fill=(244, 197, 66, 255))
        try:
            module.inspect_overlay_clearance(
                clipped, {"cue_index": 1, "hero_line": {"level": "hero"}},
                context["placement_beats"][0], hero_color="#F4C542",
            )
        except ValueError as error:
            assert "hero-line" in str(error) and "bounds" in str(error)
        else:
            raise AssertionError("hero-line top/bottom clipping must fail before approval")

    no_hero_pixels = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    ImageDraw.Draw(no_hero_pixels).rectangle((30, 25, 290, 65), fill=(255, 255, 255, 255))
    try:
        module.inspect_overlay_clearance(
            no_hero_pixels, {"cue_index": 1, "hero_line": {"level": "strong"}},
            context["placement_beats"][0], hero_color="#F4C542",
        )
    except ValueError as error:
        assert "hero pixels" in str(error)
    else:
        raise AssertionError("hero samples without maintained gold pixels must fail")

    faint_glow = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(faint_glow)
    glow_draw.rectangle((0, 20, 319, 70), fill=(33, 211, 70, 4))
    glow_draw.rectangle((30, 25, 290, 65), fill=(255, 255, 255, 255))
    glow_result = module.inspect_overlay_clearance(
        faint_glow, {"cue_index": 1}, context["placement_beats"][0]
    )
    assert glow_result["caption_bbox"] == [30, 25, 291, 66]

    outside = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    ImageDraw.Draw(outside).rectangle((0, 5, 319, 90), fill=(255, 255, 255, 255))
    try:
        module.inspect_overlay_clearance(
            outside, {"cue_index": 1, "hero_line": {"level": "hero"}}, context["placement_beats"][0]
        )
    except ValueError as error:
        assert "panel-center" in str(error) or "hero-line" in str(error)
    else:
        raise AssertionError("panel/hero overflow must fail before approval")

    bottom_beat = {
        "resolved_placement": "panel-bottom",
        "allowed_rect": {"x": 0.04, "y": 0.8, "width": 0.92, "height": 0.16},
    }
    bottom_outside = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
    ImageDraw.Draw(bottom_outside).rectangle((30, 130, 290, 170), fill=(255, 255, 255, 255))
    try:
        module.inspect_overlay_clearance(bottom_outside, {"cue_index": 2}, bottom_beat)
    except ValueError as error:
        assert "panel-bottom" in str(error) and "allowed rect" in str(error)
    else:
        raise AssertionError("panel-bottom overflow must fail before approval")


def check_snapshot_numeric_sorting():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-snapshot-order-") as temporary:
        root = Path(temporary)
        for name in ("frame-100-at-4s.png", "frame-10-at-2s.png", "frame-11-at-3s.png", "frame-00-at-1s.png"):
            (root / name).touch()
        assert [path.name for path in module.sorted_snapshot_files(root)] == [
            "frame-00-at-1s.png", "frame-10-at-2s.png", "frame-11-at-3s.png", "frame-100-at-4s.png",
        ]


def check_spatial_builder_uses_composite_pixels():
    module = load_builder()
    with tempfile.TemporaryDirectory(prefix="caption-review-spatial-") as temporary:
        root = Path(temporary)
        spatial_check._fixture(root)
        source = root / "source.png"
        Image.new("RGB", (320, 180), (12, 18, 24)).save(source)
        timeline = root / "timeline.json"
        write_json(timeline, {
            "schema_version": 1, "timeline_id": "main", "source_asset_id": "source",
            "fps": {"num": 30, "den": 1}, "source_duration_s": 12,
            "program_duration_s": 12,
            "clips": [{"id": "source", "source_range": {"start_s": 0, "end_s": 12},
                       "program_range": {"start_s": 0, "end_s": 12}, "speed": 1,
                       "decision_ref": "source"}],
        })
        plan_value = spatial_check._plan([
            spatial_check._cue("cue-001", 1, 3.0, 3.8, [("corner", 3.0, 3.8)]),
            spatial_check._cue("cue-002", 2, 6.2, 6.9, [("focused", 6.2, 6.9)]),
            spatial_check._cue("cue-003", 3, 8.2, 8.9, [("wash", 8.2, 8.9)]),
        ])
        context = caption_spatial_context.build_context(root, plan_value)
        captions_dir = root / "work" / "captions"
        captions_dir.mkdir(parents=True)
        context_path = captions_dir / "caption-spatial-context.json"
        plan = captions_dir / "captions-plan.json"
        write_json(context_path, context)
        write_json(plan, plan_value)
        caption_spatial_context.attach_context(plan, context_path, root)
        plan_value = json.loads(plan.read_text(encoding="utf-8"))
        samples = module.spatial_sample_times(plan_value, 30, context)
        snapshots = root / "snapshots"
        snapshots.mkdir()
        for index, sample in enumerate(samples, 1):
            overlay = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
            if sample["cue_index"] is not None:
                y1, y2 = (30, 60) if sample.get("resolved_placement") == "panel-center" else (130, 160)
                ImageDraw.Draw(overlay).rectangle((40, y1, 280, y2), fill=(255, 220, 50, 240))
            overlay.save(snapshots / f"frame-{index:03d}.png")
        state = root / "interaction.json"
        interaction = SCRIPT_DIR / "caption_interaction.mjs"
        subprocess.run([
            "node", str(interaction), "start", "--state", str(state.resolve()), "--source", str(source.resolve()),
            "--captions", str(plan.resolve()), "--spatial-context", str(context_path.resolve()),
            "--review-dir", str(root / "style-review"), "--decision-mode", "agent",
            "--delegation-note", "Synthetic review binding regression.", "--no-open", "true",
        ], check=True, capture_output=True, encoding="utf-8", errors="replace")
        subprocess.run([
            "node", str(interaction), "agent-select", "--state", str(state.resolve()), "--choice", "clean",
            "--rationale", "Use the stable clean fixture.",
        ], check=True, capture_output=True, encoding="utf-8", errors="replace")
        out = root / "review"
        with patch.object(module.subprocess, "run", side_effect=fake_ffmpeg):
            module.main([
                "--source", str(source), "--timeline", str(timeline), "--plan", str(plan),
                "--interaction-state", str(state), "--spatial-context", str(context_path),
                "--project-root", str(root), "--snapshots", str(snapshots),
                "--out", str(out), "--cache", str(root / "cache"),
            ])
        evidence = json.loads((out / "captions-evidence.json").read_text(encoding="utf-8"))
        assert evidence["spatial_context"]["sha256"] == file_sha256(context_path)
        assert len(evidence["samples"]) > 4
        focused = [sample for sample in evidence["samples"] if sample.get("visual_context") == "focused-panel"]
        assert focused and all(sample["background_kind"] == "normalized-broll-composite" for sample in focused)
        gap_transition = next(
            sample for sample in evidence["samples"]
            if sample.get("cue_index") is None
            and sample.get("visual_interval_id") == "visual-002"
            and "spatial-boundary-after" in sample.get("purposes", [])
        )
        assert gap_transition["background_kind"] == "normalized-broll-composite"
        assert gap_transition["background_offset_s"] == 0.0
        assert all(sample["clearance_status"] == "pass" for sample in evidence["samples"])
        page = (out / "captions-review.html").read_text(encoding="utf-8")
        payload = json.loads(base64.b64decode(module.REVIEW_PAYLOAD_PATTERN.search(page).group(1)))
        assert payload["approval_evidence"] == "composite-aware"
        assert payload["spatial_context"]["source"]["operation_status"] == "approved"
        state_value = json.loads(state.read_text(encoding="utf-8"))
        project_meta = root / "project-meta.json"
        write_json(project_meta, {
            "interaction": {"statePath": str(state.resolve()),
                            "selectionId": state_value["selection"]["choiceId"]},
            "spatialContext": {"sha256": file_sha256(context_path)},
        })
        evidence_paths = [str((out / sample["preview"]).resolve()) for sample in evidence["review_samples"]]
        result = subprocess.run([
            "node", str(interaction), "preview-ready", "--state", str(state.resolve()),
            "--project-meta", str(project_meta), "--evidence", ",".join(evidence_paths),
            "--evidence-document", str((out / "captions-evidence.json").resolve()),
            "--review-page", str((out / "captions-review.html").resolve()), "--timeline", str(timeline),
        ], check=False, capture_output=True, encoding="utf-8", errors="replace")
        assert result.returncode == 0, result.stdout + result.stderr
        state_value = json.loads(state.read_text(encoding="utf-8"))
        assert state_value["preview"]["approvalEvidence"] == "composite-aware"
        assert len(state_value["preview"]["evidence"]) == evidence["primary_evidence_count"] <= 6
        assert state_value["preview"]["machineEvidence"]["sampleCount"] == len(evidence["samples"])


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
check_representative_evidence_selection()
print("[caption-review] PASS representative evidence selection")
check_entry_animation_boundary_clearance()
print("[caption-review] PASS entry-animation boundary clearance")
check_builder()
print("[caption-review] PASS mapped evidence and safe payload")
check_failure_is_atomic()
print("[caption-review] PASS atomic failure")
check_expressive_builder()
print("[caption-review] PASS dynamic Expressive evidence and comparison")
check_spatial_planner_and_clearance()
print("[caption-review] PASS composite-aware evidence planner and clearance")
check_snapshot_numeric_sorting()
print("[caption-review] PASS numeric snapshot ordering")
check_spatial_builder_uses_composite_pixels()
print("[caption-review] PASS normalized composite backgrounds and bindings")
check_standalone_rebuild_removes_stale_page()
print("[caption-review] PASS stale page removal")
check_bound_inputs_cannot_be_substituted()
print("[caption-review] PASS bound input integrity")
print("[caption-review] 11 checks passed")
