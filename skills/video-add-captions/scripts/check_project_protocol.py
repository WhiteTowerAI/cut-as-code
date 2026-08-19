"""Small regression checks for the caption project protocol."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import build_captions


def check_canonical_caption_plan():
    transcript = {
        "duration": 6.0,
        "language": "en",
        "segments": [
            {
                "id": 1,
                "start": 0.2,
                "end": 4.5,
                "text": "First removed second",
                "words": [
                    {"start": 0.2, "end": 0.6, "word": " First"},
                    {"start": 2.5, "end": 2.8, "word": " removed"},
                    {"start": 4.0, "end": 4.5, "word": " second"},
                ],
            }
        ],
    }
    timeline = {
        "schema_version": 1,
        "timeline_id": "main",
        "source_asset_id": "source",
        "fps": {"num": 30, "den": 1},
        "source_duration_s": 6.0,
        "program_duration_s": 3.0,
        "clips": [
            {
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 2.0},
                "program_range": {"start_s": 0.0, "end_s": 2.0},
                "speed": 1.0,
                "decision_ref": "edit-001",
            },
            {
                "id": "clip-002",
                "source_range": {"start_s": 4.0, "end_s": 6.0},
                "program_range": {"start_s": 2.0, "end_s": 3.0},
                "speed": 2.0,
                "decision_ref": "edit-002",
            },
        ],
    }

    plan = build_captions.build_plan(
        transcript,
        timeline,
        source_transcript="understand/transcript.json",
        max_chars=20,
        max_lines=2,
        max_dur=6.0,
        gap=0.6,
    )
    assert plan["schema_version"] == 1
    assert plan["target"] == "overlay"
    assert plan["timebase"] == "program"
    assert plan["timeline_id"] == "main"
    assert plan["source_transcript"] == "understand/transcript.json"
    assert len(plan["cues"]) == 2
    assert [cue["text"] for cue in plan["cues"]] == ["First", "second"]
    assert plan["cues"][1]["program_range"] == {"start_s": 2.0, "end_s": 2.25}
    assert plan["cues"][1]["source_ranges"] == [{"start_s": 4.0, "end_s": 4.5}]
    assert plan["cues"][1]["words"][0]["source_range"] == {
        "start_s": 4.0,
        "end_s": 4.5,
    }
    assert plan["renderer_recipe"]["fps"] == {"num": 30, "den": 1}

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        transcript_path = root / "transcript.json"
        timeline_path = root / "timeline.json"
        plan_path = root / "captions-plan.json"
        srt_path = root / "captions.srt"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")
        timeline_path.write_text(json.dumps(timeline), encoding="utf-8")
        build_captions.main([
            str(transcript_path),
            str(plan_path),
            str(srt_path),
            "--timeline", str(timeline_path),
            "--source-transcript", "understand/transcript.json",
        ])
        assert json.loads(plan_path.read_text(encoding="utf-8"))["cues"]
        assert "First" in srt_path.read_text(encoding="utf-8")


def check_expressive_caption_plan():
    transcript = {
        "duration": 5.0,
        "language": "en",
        "segments": [{
            "id": 1,
            "start": 0.2,
            "end": 4.6,
            "text": "Keep steady. Center three. Finish high.",
            "words": [
                {"start": 0.2, "end": 0.7, "word": " Keep"},
                {"start": 0.7, "end": 1.4, "word": " steady."},
                {"start": 1.6, "end": 2.2, "word": " Center"},
                {"start": 2.2, "end": 3.0, "word": " three."},
                {"start": 3.2, "end": 3.8, "word": " Finish"},
                {"start": 3.8, "end": 4.6, "word": " high."},
            ],
        }],
    }
    timeline = {
        "schema_version": 1,
        "timeline_id": "expressive",
        "source_asset_id": "source",
        "fps": {"num": 30, "den": 1},
        "source_duration_s": 5.0,
        "program_duration_s": 5.0,
        "clips": [{
            "id": "clip-001",
            "source_range": {"start_s": 0.0, "end_s": 5.0},
            "program_range": {"start_s": 0.0, "end_s": 5.0},
            "speed": 1.0,
            "decision_ref": "source",
        }],
    }

    standard = build_captions.build_plan(
        transcript, timeline, source_transcript="understand/transcript.json",
    )
    assert "presentation" not in standard
    assert all("id" not in cue for cue in standard["cues"])
    assert all("semantic_role" not in word for cue in standard["cues"] for word in cue["words"])

    shell = build_captions.build_plan(
        transcript, timeline, source_transcript="understand/transcript.json",
        presentation_mode="expressive",
    )
    assert shell["presentation"] == {
        "schema_version": 1,
        "mode": "expressive",
        "planning_status": "draft",
        "planner": {"actor": "agent", "scope": "full-program", "rationale": ""},
        "layout_beats": [],
    }
    assert [cue["id"] for cue in shell["cues"]] == ["cue-001", "cue-002", "cue-003"]
    assert all(
        word["semantic_role"] == "normal"
        for cue in shell["cues"] for word in cue["words"]
    )
    assert build_captions.validate_caption_plan(shell)["planning_status"] == "draft"

    complete = copy.deepcopy(shell)
    complete["presentation"]["planning_status"] = "complete"
    complete["presentation"]["planner"]["rationale"] = (
        "Keep the explanation stable at the bottom, center the numeric emphasis, "
        "then return the closing statement to the baseline."
    )
    variants = ["bottom-standard", "center-emphasis", "bottom-standard"]
    complete["presentation"]["layout_beats"] = []
    for position, (cue, variant) in enumerate(zip(complete["cues"], variants), 1):
        complete["presentation"]["layout_beats"].append({
            "id": f"layout-beat-{position:03d}",
            "variant": variant,
            "cue_ids": [cue["id"]],
            "program_range": {"start_s": cue["start"], "end_s": cue["end"]},
            "rationale": f"Use {variant} for cue {cue['index']} based on its semantic role.",
        })
    del complete["cues"][0]["words"][0]["semantic_role"]
    complete["cues"][1]["words"][1]["semantic_role"] = "number"
    complete["cues"][2]["words"][0]["semantic_role"] = "keyword"
    complete["cues"][0]["hero_line"] = {
        "level": "hero",
        "word_indexes": [1, 2],
        "rationale": "The opening phrase is the primary conclusion.",
    }
    summary = build_captions.validate_caption_plan(complete, require_complete=True)
    assert summary == {
        "mode": "expressive",
        "planning_status": "complete",
        "cue_count": 3,
        "layout_beat_count": 3,
        "hero_line_count": 1,
    }
    assert build_captions.validate_caption_plan(standard["cues"], require_complete=True)["mode"] == "standard"
    spatial_binding = {
        "policy": "composite-aware",
        "path": "captions/caption-spatial-context.json",
        "sha256": "a" * 64,
        "source_operation": "b-roll",
        "source_revision": 4,
    }
    bound_standard = copy.deepcopy(standard)
    bound_standard["spatial_context"] = copy.deepcopy(spatial_binding)
    assert build_captions.validate_caption_plan(bound_standard, require_complete=True)["mode"] == "standard"
    bound_complete = copy.deepcopy(complete)
    bound_complete["spatial_context"] = copy.deepcopy(spatial_binding)
    assert build_captions.validate_caption_plan(bound_complete, require_complete=True)["hero_line_count"] == 1

    def assert_invalid(mutator, message):
        candidate = copy.deepcopy(complete)
        mutator(candidate)
        try:
            build_captions.validate_caption_plan(candidate, require_complete=True)
        except ValueError as error:
            assert message in str(error), str(error)
        else:
            raise AssertionError(f"invalid expressive plan must fail: {message}")

    assert_invalid(lambda plan: plan["presentation"].update(mode="kinetic"), "mode")
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][0].update(variant="middle"),
        "variant",
    )
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][0].update(variant="top-statement"),
        "the plan must be replanned as bottom-standard or center-emphasis",
    )
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][0].update(cue_ids=["cue-999"]),
        "unknown cue id/index",
    )
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][1].update(cue_ids=["cue-001"]),
        "more than one layout beat",
    )

    def overlap(plan):
        cue = plan["cues"][1]
        cue["start"] = plan["cues"][0]["end"] - 0.1
        plan["presentation"]["layout_beats"][1]["program_range"]["start_s"] = cue["start"]

    assert_invalid(overlap, "overlaps")
    assert_invalid(lambda plan: plan["presentation"]["layout_beats"].pop(), "does not cover every cue")
    assert_invalid(
        lambda plan: plan["cues"][0]["words"][0].update(semantic_role="headline"),
        "semantic_role",
    )
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][0]["program_range"].update(
            start_s=plan["cues"][0]["start"] + 0.1,
        ),
        "inside a cue",
    )
    assert_invalid(lambda plan: plan["presentation"]["layout_beats"].reverse(), "sorted by time")
    assert_invalid(
        lambda plan: plan["presentation"]["layout_beats"][1].update(id="layout-beat-001"),
        "duplicate layout beat id",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(level="large"),
        "hero_line level",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(word_indexes=[]),
        "hero_line word_indexes",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(word_indexes=[1, 3]),
        "hero_line word_indexes",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(word_indexes=[2, 2]),
        "hero_line word_indexes",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(word_indexes=[0]),
        "hero_line word_indexes",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(word_indexes=[3]),
        "hero_line word_indexes",
    )
    assert_invalid(
        lambda plan: plan["cues"][0]["hero_line"].update(rationale="  "),
        "hero_line rationale",
    )
    assert_invalid(
        lambda plan: plan["cues"][0].update(hero_lines=[plan["cues"][0].pop("hero_line")]),
        "hero_lines",
    )
    assert_invalid(
        lambda plan: plan.update(spatial_context={**spatial_binding, "sha256": "ABC"}),
        "spatial_context sha256",
    )

    standard_with_hero = copy.deepcopy(standard)
    standard_with_hero["cues"][0]["hero_line"] = {
        "level": "strong",
        "word_indexes": [1],
        "rationale": "Not allowed in Standard.",
    }
    try:
        build_captions.validate_caption_plan(standard_with_hero, require_complete=True)
    except ValueError as error:
        assert "hero_line" in str(error), str(error)
    else:
        raise AssertionError("Standard plan carrying hero_line must fail")

    legacy_with_hero = copy.deepcopy(standard["cues"])
    legacy_with_hero[0]["hero_line"] = {
        "level": "strong",
        "word_indexes": [1],
        "rationale": "Not allowed in a legacy cue array.",
    }
    try:
        build_captions.validate_caption_plan(legacy_with_hero, require_complete=True)
    except ValueError as error:
        assert "hero_line" in str(error), str(error)
    else:
        raise AssertionError("legacy cue array carrying hero_line must fail")

    with tempfile.TemporaryDirectory(prefix="caption-top-layout-python-") as temporary:
        invalid_path = Path(temporary) / "top-statement.json"
        invalid = copy.deepcopy(complete)
        invalid["presentation"]["layout_beats"][0]["variant"] = "top-statement"
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(Path(build_captions.__file__)), "--validate-plan", str(invalid_path)],
            check=False, capture_output=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode != 0
        assert "the plan must be replanned as bottom-standard or center-emphasis" in (
            result.stdout + result.stderr
        )


def check_presentation_renderer_modes():
    script_dir = Path(__file__).resolve().parent
    interaction = script_dir / "caption_interaction.mjs"
    generator = script_dir / "generate_caption_project.mjs"
    with tempfile.TemporaryDirectory(prefix="caption-renderer-modes-") as temporary:
        root = Path(temporary)
        source = root / "source.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0x243447:s=320x180:r=30:d=5",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
        ], check=True)
        cues = [
            {"id": "cue-001", "index": 1, "start": 0.4, "end": 1.4, "text": "Keep steady",
             "words": [{"word": "Keep", "start": 0.4, "end": 0.8, "semantic_role": "normal"},
                       {"word": "steady", "start": 0.8, "end": 1.4, "semantic_role": "normal"}]},
            {"id": "cue-002", "index": 2, "start": 1.8, "end": 3.0, "text": "Two layouts",
             "words": [{"word": "Three", "start": 1.8, "end": 2.3, "semantic_role": "number"},
                       {"word": "layouts", "start": 2.3, "end": 3.0, "semantic_role": "keyword"}]},
            {"id": "cue-003", "index": 3, "start": 3.4, "end": 4.5, "text": "Finish steady",
             "words": [{"word": "Finish", "start": 3.4, "end": 3.9, "semantic_role": "contrast"},
                       {"word": "high", "start": 3.9, "end": 4.5, "semantic_role": "normal"}]},
        ]
        standard_plan = root / "standard.json"
        standard_plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timebase": "program",
            "timeline_id": "main",
            "program_duration_s": 5,
            "cues": cues,
        }), encoding="utf-8")
        cues[2]["hero_line"] = {
            "level": "strong",
            "word_indexes": [1, 2],
            "rationale": "The closing phrase is the fixture hero line.",
        }
        expressive_plan = root / "expressive.json"
        expressive_plan.write_text(json.dumps({
            "schema_version": 1,
            "target": "overlay",
            "timebase": "program",
            "timeline_id": "main",
            "program_duration_s": 5,
            "cues": cues,
            "presentation": {
                "schema_version": 1,
                "mode": "expressive",
                "planning_status": "complete",
                "planner": {
                    "actor": "agent", "scope": "full-program",
                    "rationale": "Keep ordinary narration low, center the number, and finish at the baseline.",
                },
                "layout_beats": [
                    {"id": "beat-001", "variant": "bottom-standard", "cue_ids": ["cue-001"],
                     "program_range": {"start_s": 0.4, "end_s": 1.4}, "rationale": "Stable opening."},
                    {"id": "beat-002", "variant": "center-emphasis", "cue_ids": ["cue-002"],
                     "program_range": {"start_s": 1.8, "end_s": 3.0}, "rationale": "Numeric thesis."},
                    {"id": "beat-003", "variant": "bottom-standard", "cue_ids": ["cue-003"],
                     "program_range": {"start_s": 3.4, "end_s": 4.5}, "rationale": "Stable close."},
                ],
            },
        }), encoding="utf-8")

        def generate(
            name, plan_path, choice, karaoke=None, overrides=None,
            mode="preview", expect_success=True, approved_karaoke=None,
        ):
            run_root = root / name
            run_root.mkdir()
            state = run_root / "interaction.json"
            review = run_root / "style-review"
            project = run_root / "project"
            start_command = [
                "node", str(interaction), "start", "--state", str(state),
                "--source", str(source), "--captions", str(plan_path),
            ]
            if mode != "overlay":
                start_command.extend(["--review-dir", str(review)])
                start_command.extend([
                    "--decision-mode", "agent",
                    "--delegation-note", "Renderer mode protocol check.",
                ])
            start_command.extend(["--no-open", "true"])
            subprocess.run(
                start_command, check=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            selection_command = ["node", str(interaction)]
            if mode == "overlay":
                selection_command.extend(["select", "--state", str(state), "--response", choice])
            else:
                selection_command.extend([
                    "agent-select", "--state", str(state), "--choice", choice,
                    "--rationale", "Use the maintained fixture style.",
                ])
            subprocess.run(
                selection_command, check=True, capture_output=True, encoding="utf-8", errors="replace",
            )
            if mode == "overlay":
                approved_preview = run_root / "approved-preview"
                subprocess.run([
                    "node", str(generator), "--video", str(source), "--captions", str(plan_path),
                    "--out", str(approved_preview), "--interaction-state", str(state), "--mode", "preview",
                ], check=True, capture_output=True, encoding="utf-8", errors="replace")
                evidence_dir = run_root / "evidence"
                evidence_dir.mkdir()
                evidence = []
                for index in range(4):
                    evidence_path = evidence_dir / f"frame-{index + 1}.png"
                    Image.new("RGBA", (320, 180), (0, 0, 0, 0)).save(evidence_path)
                    evidence.append(str(evidence_path))
                subprocess.run([
                    "node", str(interaction), "preview-ready", "--state", str(state),
                    "--project-meta", str(approved_preview / "project-meta.json"),
                    "--evidence", ",".join(evidence),
                ], check=True, capture_output=True, encoding="utf-8", errors="replace")
                subprocess.run([
                    "node", str(interaction), "confirm", "--state", str(state),
                    "--response", "确认渲染",
                ], check=True, capture_output=True, encoding="utf-8", errors="replace")
                if plan_path == expressive_plan:
                    assert isinstance(approved_karaoke, bool)
                    comparison_bindings = []
                    for comparison_mode in ("semantic-only", "semantic-plus-karaoke"):
                        comparison_path = evidence_dir / f"{comparison_mode}.png"
                        Image.new("RGBA", (320, 180), (0, 0, 0, 0)).save(comparison_path)
                        comparison_bindings.append({
                            "mode": comparison_mode,
                            "path": str(comparison_path.resolve()),
                            "sha256": hashlib.sha256(comparison_path.read_bytes()).hexdigest(),
                        })
                    comparison_signature = hashlib.sha256(json.dumps(
                        comparison_bindings, separators=(",", ":"),
                    ).encode("utf-8")).hexdigest()
                    receipt = json.loads(state.read_text(encoding="utf-8"))
                    receipt["preview"].update({
                        "presentationMode": "expressive",
                        "approvalEvidence": "expressive-layout-beats",
                        "comparisonEvidence": comparison_bindings,
                        "comparisonEvidenceSignature": comparison_signature,
                    })
                    receipt["approval"].update({
                        "karaoke": approved_karaoke,
                        "comparisonEvidenceSignature": comparison_signature,
                    })
                    state.write_text(json.dumps(receipt), encoding="utf-8")
            command = [
                "node", str(generator), "--video", str(source), "--captions", str(plan_path),
                "--out", str(project), "--interaction-state", str(state), "--mode", mode,
            ]
            if karaoke is not None:
                command.extend(["--karaoke", "true" if karaoke else "false"])
            if overrides is not None:
                overrides_path = run_root / "overrides.json"
                overrides_path.write_text(json.dumps(overrides), encoding="utf-8")
                command.extend(["--overrides", str(overrides_path)])
            result = subprocess.run(
                command, check=False, capture_output=True, encoding="utf-8", errors="replace",
            )
            if not expect_success:
                return result
            result.check_returncode()
            return (
                (project / "index.html").read_text(encoding="utf-8"),
                json.loads((project / "project-meta.json").read_text(encoding="utf-8")),
            )

        standard_off_html, standard_off_meta = generate("standard-off", standard_plan, "clean", False)
        standard_on_html, standard_on_meta = generate(
            "standard-on", standard_plan, "social-bold-karaoke", True,
        )
        expressive_overrides = {
            "font": {"color": "#F4F1E8"},
            "wordHighlight": {
                "mode": "background",
                "activeColor": "#00E5FF",
                "backgroundColor": "#FF2D95",
                "backgroundOpacity": 0.46,
                "activeScale": 1.3,
            },
        }
        expressive_off_html, expressive_off_meta = generate(
            "expressive-off", expressive_plan, "clean", False, expressive_overrides,
        )
        expressive_on_html, expressive_on_meta = generate(
            "expressive-on", expressive_plan, "clean", True, expressive_overrides,
        )
        canonical_hero_plan = root / "expressive-canonical-hero.json"
        canonical_hero_data = json.loads(expressive_plan.read_text(encoding="utf-8"))
        canonical_hero_data["cues"][2]["hero_line"]["level"] = "hero"
        canonical_hero_plan.write_text(json.dumps(canonical_hero_data), encoding="utf-8")
        canonical_hero_html, canonical_hero_meta = generate(
            "expressive-canonical-hero", canonical_hero_plan, "clean", False, expressive_overrides,
        )
        standard_overlay_off_html, standard_overlay_off_meta = generate(
            "standard-overlay-off", standard_plan, "clean", mode="overlay",
        )
        standard_overlay_on_html, standard_overlay_on_meta = generate(
            "standard-overlay-on", standard_plan, "social-bold-karaoke", mode="overlay",
        )
        expressive_approved_off_html, expressive_approved_off_meta = generate(
            "expressive-approved-off", expressive_plan, "clean",
            mode="overlay", approved_karaoke=False,
        )
        expressive_approved_on_html, expressive_approved_on_meta = generate(
            "expressive-approved-on", expressive_plan, "clean",
            mode="overlay", approved_karaoke=True,
        )
        for name, plan_path, mode in (
            ("standard-preview-karaoke-mismatch", standard_plan, "preview"),
            ("standard-overlay-karaoke-mismatch", standard_plan, "overlay"),
        ):
            rejected = generate(
                name, plan_path, "clean", True, mode=mode, expect_success=False,
            )
            assert rejected.returncode != 0
            output = rejected.stdout + rejected.stderr
            assert "Requested karaoke does not match the user's recorded selection" in output, output
        for name, approved_karaoke, requested_karaoke in (
            ("expressive-approved-off-request-on", False, True),
            ("expressive-approved-on-request-off", True, False),
        ):
            rejected = generate(
                name, expressive_plan, "clean", requested_karaoke,
                mode="overlay", expect_success=False, approved_karaoke=approved_karaoke,
            )
            assert rejected.returncode != 0
            assert "karaoke" in (rejected.stdout + rejected.stderr).lower()
        for html in (standard_off_html, standard_on_html):
            assert "expressive-cue" not in html
            assert "data-layout-beat-id" not in html
            assert "semantic-keyword" not in html
            assert "placement-" not in html
            assert "spatialContext" not in html
            assert 'class="caption-cue clip" data-start=' in html
            assert 'class="caption-word">Keep</span>' in html
        assert standard_off_meta["selection"]["karaoke"] is False
        assert standard_on_meta["selection"]["karaoke"] is True
        assert standard_overlay_off_meta["selection"]["karaoke"] is False
        assert standard_overlay_on_meta["selection"]["karaoke"] is True
        assert 'timeline.set("#caption-cue-1-word-1"' not in standard_off_html
        assert 'timeline.set("#caption-cue-1-word-1"' in standard_on_html
        assert 'timeline.set("#caption-cue-1-word-1"' not in standard_overlay_off_html
        assert 'timeline.set("#caption-cue-1-word-1"' in standard_overlay_on_html
        for variant in ("bottom-standard", "center-emphasis"):
            assert f"layout-{variant}" in expressive_off_html
            assert f"layout-{variant}" in expressive_on_html
        assert "layout-top-statement" not in expressive_off_html
        assert "layout-top-statement" not in expressive_on_html
        assert "text-decoration" not in expressive_off_html
        assert "text-decoration" not in expressive_on_html
        for role in ("semantic-keyword", "semantic-number", "semantic-contrast"):
            assert role in expressive_off_html
            assert role in expressive_on_html
        for role in ("keyword", "number", "contrast"):
            assert f'class="caption-word semantic-{role}"' in expressive_off_html
            assert "--semantic-scale:1.22" in expressive_off_html
        assert expressive_off_html.count('class="caption-hero-line hero-level-strong"') == 1
        assert expressive_on_html.count('class="caption-hero-line hero-level-strong"') == 1
        assert canonical_hero_html.count('class="caption-hero-line hero-level-hero"') == 1
        assert 'data-hero-level="strong"' in expressive_off_html
        assert 'data-hero-level="hero"' in canonical_hero_html
        assert "color: #F4C542;" in expressive_off_html
        assert "font-size: 1.5em;" in expressive_off_html
        assert ".hero-level-strong {" not in expressive_off_html
        assert ".hero-level-hero {" not in expressive_off_html
        assert "--semantic-scale:1;--semantic-color:#F4C542" in expressive_off_html
        assert expressive_off_meta["selection"]["karaoke"] is False
        assert expressive_on_meta["selection"]["karaoke"] is True
        assert expressive_approved_off_meta["selection"]["karaoke"] is False
        assert expressive_approved_on_meta["selection"]["karaoke"] is True
        assert expressive_approved_off_meta["presentation"]["coexistenceMode"] == "semantic-only"
        assert expressive_approved_on_meta["presentation"]["coexistenceMode"] == "semantic-plus-karaoke"
        assert expressive_off_meta["presentation"]["coexistenceMode"] == "semantic-only"
        assert expressive_on_meta["presentation"]["coexistenceMode"] == "semantic-plus-karaoke"
        assert expressive_off_meta["presentation"]["layoutBeats"] == expressive_on_meta["presentation"]["layoutBeats"]
        assert expressive_off_meta["presentation"]["heroLines"] == [{
            "cueIndex": 3, "level": "strong", "wordIndexes": [1, 2],
        }]
        assert canonical_hero_meta["presentation"]["heroLines"] == [{
            "cueIndex": 3, "level": "hero", "wordIndexes": [1, 2],
        }]
        assert expressive_off_meta["expressiveTreatments"]["value"]["heroLine"]["levels"]["hero"]["scale"] == 1.5
        assert expressive_off_meta["expressiveTreatments"]["value"]["heroLine"]["canonicalLevel"] == "hero"
        assert expressive_off_meta["resolvedStyle"] == expressive_on_meta["resolvedStyle"]
        assert expressive_on_meta["presentation"]["combinedScaleRule"].startswith("effective scale = max")
        generator_source = generator.read_text(encoding="utf-8")
        assert "Math.max(scale, karaokeScale)" in generator_source
        assert "effectiveScale / scale" in generator_source
        assert "scale * karaokeScale" not in generator_source

        active_semantic = next(
            line for line in expressive_on_html.splitlines()
            if 'timeline.set("#caption-cue-2-word-1"' in line and line.rstrip().endswith(", 1.800);")
        )
        active_normal = next(
            line for line in expressive_on_html.splitlines()
            if 'timeline.set("#caption-cue-1-word-1"' in line and line.rstrip().endswith(", 0.400);")
        )
        completed_normal = next(
            line for line in expressive_on_html.splitlines()
            if 'timeline.set("#caption-cue-1-word-1"' in line and line.rstrip().endswith(", 0.800);")
        )
        completed_semantic = next(
            line for line in expressive_on_html.splitlines()
            if 'timeline.set("#caption-cue-2-word-1"' in line and line.rstrip().endswith(", 2.300);")
        )
        assert '"color":"#00E5FF"' in active_semantic
        assert '"color":"#00E5FF"' in active_normal
        assert '"backgroundColor":"rgba(255, 45, 149, 0.46)"' in active_semantic
        assert '"color":"#F4F1E8"' in completed_normal
        assert '"color":"#00E5FF"' in completed_semantic

        rejected_plan = root / "top-statement.json"
        rejected = json.loads(expressive_plan.read_text(encoding="utf-8"))
        rejected["presentation"]["layout_beats"][0]["variant"] = "top-statement"
        rejected_plan.write_text(json.dumps(rejected), encoding="utf-8")
        rejected_result = subprocess.run([
            "node", str(generator), "--video", str(source), "--captions", str(rejected_plan),
            "--out", str(root / "top-statement-project"),
            "--interaction-state", str(root / "unused-interaction.json"), "--mode", "preview",
        ], check=False, capture_output=True, encoding="utf-8", errors="replace")
        assert rejected_result.returncode != 0
        assert "the plan must be replanned as bottom-standard or center-emphasis" in (
            rejected_result.stdout + rejected_result.stderr
        )


def check_orphan_merge_keeps_grouping_limits():
    cues = build_captions.build(
        [
            {"word": "one", "start": 0.0, "end": 3.0},
            {"word": "two", "start": 3.0, "end": 5.8},
            {"word": "tail", "start": 5.9, "end": 6.4},
        ],
        max_chars=8,
        max_lines=1,
        max_dur=6.0,
        gap=0.6,
    )
    assert all(cue["end"] - cue["start"] <= 6.0 for cue in cues)
    assert all(len(cue["text"]) <= 8 for cue in cues)


def check_hyphenated_tokens_do_not_gain_space():
    assert build_captions.join_tokens(["Earth", "-like", "planet."]) == "Earth-like planet."


def check_adjacent_cues_do_not_overlap():
    cues = build_captions.build(
        [
            {"word": "One", "start": 0.0, "end": 0.5, "clip_id": "clip-001"},
            {"word": "way...", "start": 1.0, "end": 1.001, "clip_id": "clip-001"},
            {"word": "Next", "start": 1.0, "end": 1.3, "clip_id": "clip-001"},
            {"word": "phrase.", "start": 1.3, "end": 2.0, "clip_id": "clip-001"},
        ],
        max_chars=42,
        max_lines=2,
        max_dur=6.0,
        gap=0.6,
    )
    assert len(cues) == 2
    assert cues[0]["end"] <= cues[1]["start"]


def check_delegated_caption_review():
    interaction = Path(__file__).resolve().parent / "caption_interaction.mjs"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.mp4"
        captions = root / "captions.json"
        state = root / "caption-review.json"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=0x203040:size=160x90:rate=30:duration=2",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                str(source),
            ],
            check=True,
            capture_output=True,
        )
        captions.write_text(
            json.dumps({
                "schema_version": 1,
                "target": "overlay",
                "timeline_id": "source",
                "timebase": "program",
                "source_transcript": "understand/transcript.json",
                "program_duration_s": 1.5,
                "cue_settings": {
                    "max_chars": 42,
                    "max_lines": 2,
                    "max_duration_s": 6.0,
                    "gap_s": 0.6,
                },
                "style": {
                    "status": "draft",
                    "selection_mode": None,
                    "selection_rationale": "",
                },
                "review": {"status": "pending", "evidence": []},
                "cues": [{
                    "index": 1,
                    "start": 0.2,
                    "end": 0.8,
                    "program_range": {"start_s": 0.2, "end_s": 0.8},
                    "source_ranges": [{"start_s": 0.2, "end_s": 0.8}],
                    "text": "Hello world",
                    "lines": ["Hello world"],
                    "words": [
                        {"word": "Hello", "start": 0.2, "end": 0.5},
                        {"word": "world", "start": 0.5, "end": 0.8},
                    ],
                }],
                "renderer_recipe": {
                    "engine": "hyperframes",
                    "composition": "cache/captions/index.html",
                    "asset": "cache/captions/overlay-frames",
                    "asset_type": "image-sequence",
                    "pattern": "frame_%06d.png",
                    "start_number": 1,
                    "fps": {"num": 30, "den": 1},
                    "runtime_assets": [],
                },
            }),
            encoding="utf-8",
        )

        def run(*arguments, check=True):
            return subprocess.run(
                ["node", str(interaction), *map(str, arguments)],
                check=check,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )

        run(
            "start", "--state", state, "--source", source, "--captions", captions,
            "--decision-mode", "agent", "--delegation-note", "User delegated caption choices.",
            "--no-open", "true",
        )
        rejected = run(
            "select", "--state", state, "--response", "clean", check=False,
        )
        assert rejected.returncode != 0
        assert "agent-select" in rejected.stderr
        run(
            "agent-select", "--state", state, "--choice", "clean",
            "--rationale", "Clean captions preserve the interview framing.",
        )

        evidence = []
        for index in range(4):
            path = root / f"preview-{index}.png"
            Image.new("RGB", (16, 9), (index * 20, 40, 60)).save(path)
            evidence.append(str(path))
        project_meta = root / "project-meta.json"
        project_meta.write_text(
            json.dumps({
                "interaction": {
                    "statePath": str(state),
                    "selectionId": "clean",
                    "overridesSha256": None,
                }
            }),
            encoding="utf-8",
        )
        preview_result = run(
            "preview-ready", "--state", state, "--project-meta", project_meta,
            "--evidence", ",".join(evidence),
            check=False,
        )
        assert preview_result.returncode == 0, preview_result.stderr
        rejected = run(
            "confirm", "--state", state, "--response", "确认渲染", check=False,
        )
        assert rejected.returncode != 0
        assert "agent-confirm" in rejected.stderr

        original_evidence = Path(evidence[0]).read_bytes()
        Path(evidence[0]).write_bytes(b"changed")
        rejected = run(
            "agent-confirm", "--state", state,
            "--rationale", "Mutated evidence must not be approved.", check=False,
        )
        assert rejected.returncode != 0
        assert "Preview evidence" in rejected.stderr
        Path(evidence[0]).write_bytes(original_evidence)

        run(
            "agent-confirm", "--state", state,
            "--rationale", "All four source-backed previews are legible and collision-free.",
        )
        receipt = json.loads(state.read_text(encoding="utf-8"))
        assert receipt["phase"] == "render_approved"
        assert receipt["decisionMode"] == "agent"
        assert receipt["selection"]["actor"] == "agent"
        assert receipt["approval"]["actor"] == "agent"
        assert "response" not in receipt["selection"]
        assert "response" not in receipt["approval"]

        generator = Path(__file__).resolve().parent / "generate_caption_project.mjs"
        project = root / "overlay-project"
        def run_generator(*arguments, check=True):
            result = subprocess.run(
                ["node", str(generator), *map(str, arguments)],
                check=False,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            if check:
                assert result.returncode == 0, result.stderr
            return result

        summary = root / "review/05-captions/captions-summary.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_bytes(
            b"# Caption Review\r\n\r\n## Approval\r\n\r\n- Style: `stale`\r\n"
        )
        original_second_evidence = Path(evidence[1]).read_bytes()
        Path(evidence[1]).write_bytes(b"changed")
        rejected = run_generator(
            "--video", source,
            "--captions", captions,
            "--out", project,
            "--interaction-state", state,
            "--project-root", root,
            "--mode", "overlay",
            check=False,
        )
        assert rejected.returncode != 0
        assert "Preview evidence" in rejected.stderr
        Path(evidence[1]).write_bytes(original_second_evidence)

        run_generator(
            "--video", source,
            "--captions", captions,
            "--out", project,
            "--interaction-state", state,
            "--project-root", root,
            "--mode", "overlay",
        )
        summary_text = summary.read_text(encoding="utf-8")
        assert summary_text.count("## Approval") == 1
        assert "`stale`" not in summary_text
        assert "- Style: `clean`" in summary_text
        assert "- Decision mode: `agent`" in summary_text
        assert "Clean captions preserve the interview framing." in summary_text
        assert "All four source-backed previews are legible and collision-free." in summary_text
        assert "- Approval binding validation: pass" in summary_text
        assert "Rendered-frame and shared-delivery checks remain required" in summary_text
        html = (project / "index.html").read_text(encoding="utf-8")
        assert "assets/gsap.min.js" in html
        assert "https://" not in html and "http://" not in html
        assert 'data-fps="30/1"' in html
        word_style = html.split(".caption-word {", 1)[1].split("}", 1)[0]
        assert "max-width:" in word_style
        assert "overflow: hidden;" in word_style
        assert (project / "assets/gsap.min.js").is_file()
        meta = json.loads((project / "project-meta.json").read_text(encoding="utf-8"))
        assert meta["fpsRational"] == {"num": 30, "den": 1}
        approved_plan = json.loads(captions.read_text(encoding="utf-8"))
        assert approved_plan["style"]["selection_mode"] == "agent"
        assert approved_plan["style"]["status"] == "approved"
        assert approved_plan["review"]["status"] == "approved"
        assert approved_plan["renderer_recipe"]["runtime_assets"][0]["sha256"]

        timeline = root / "timeline.json"
        timeline.write_text(json.dumps({
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30, "den": 1},
            "source_duration_s": 2.0,
            "program_duration_s": 1.5,
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 1.5},
                "program_range": {"start_s": 0.0, "end_s": 1.5},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        }), encoding="utf-8")
        snapshots = root / "snapshots"
        snapshots.mkdir()
        for index in range(4):
            image = Image.new("RGBA", (160, 90), (0, 0, 0, 0))
            if index < 3:
                ImageDraw.Draw(image).rectangle((30, 55, 130, 75), fill=(255, 255, 0, 220))
            image.save(snapshots / f"frame-{index + 1:02d}.png")
        review = root / "review"
        review_script = Path(__file__).resolve().parent / "build_caption_review.py"
        review_result = subprocess.run([
            "python", str(review_script), "--source", str(source),
            "--timeline", str(timeline), "--plan", str(captions),
            "--snapshots", str(snapshots), "--out", str(review),
            "--cache", str(root / "review-cache"),
        ], check=False, capture_output=True, encoding="utf-8", errors="replace")
        assert review_result.returncode == 0, review_result.stderr
        assert (review / "preview-early.png").is_file()
        evidence = json.loads((review / "captions-evidence.json").read_text(encoding="utf-8"))
        assert evidence["samples"][0]["program_s"] == evidence["samples"][0]["source_s"]

        regenerated = root / "regenerated-project"
        run_generator(
            "--video", source,
            "--captions", captions,
            "--out", regenerated,
            "--approved-plan", "true",
            "--mode", "overlay",
        )
        assert (regenerated / "index.html").is_file()


def main():
    check_canonical_caption_plan()
    check_expressive_caption_plan()
    check_presentation_renderer_modes()
    check_orphan_merge_keeps_grouping_limits()
    check_hyphenated_tokens_do_not_gain_space()
    check_adjacent_cues_do_not_overlap()
    check_delegated_caption_review()
    print("[caption-protocol] canonical caption plan passed")
    print("[caption-protocol] expressive plan shell and validation passed")
    print("[caption-protocol] Standard and Expressive renderer modes passed")
    print("[caption-protocol] grouping limits passed")
    print("[caption-protocol] hyphenated token spacing passed")
    print("[caption-protocol] non-overlapping cue timing passed")
    print("[caption-protocol] delegated review passed")


if __name__ == "__main__":
    main()
