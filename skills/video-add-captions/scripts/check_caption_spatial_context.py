"""Regression checks for composite-aware caption placement and cue alignment."""

import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import caption_spatial_context


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return _sha256(path)


def _cue(cue_id, index, start, end, words):
    return {
        "id": cue_id,
        "index": index,
        "start": start,
        "end": end,
        "text": " ".join(word[0] for word in words),
        "lines": [" ".join(word[0] for word in words)],
        "program_range": {"start_s": start, "end_s": end},
        "source_ranges": [{"start_s": start, "end_s": end}],
        "words": [
            {
                "word": text,
                "start": word_start,
                "end": word_end,
                "source_range": {"start_s": word_start, "end_s": word_end},
                "semantic_role": "normal",
            }
            for text, word_start, word_end in words
        ],
    }


def _plan(cues, mode="standard"):
    plan = {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": "main",
        "timebase": "program",
        "program_duration_s": 12.0,
        "cues": cues,
    }
    if mode == "expressive":
        plan["presentation"] = {
            "schema_version": 1,
            "mode": "expressive",
            "planning_status": "draft",
            "planner": {"actor": "agent", "scope": "full-program", "rationale": ""},
            "layout_beats": [],
        }
    return plan


def _fixture(root):
    work = root / "work"
    normalized = work / "cache" / "b-roll" / "normalized"
    normalized.mkdir(parents=True)
    artifacts = {}
    for name in ["analysis", "agent-input", "preview", "clearance"]:
        path = work / "b-roll" / f"speaker-inset-{name}.json"
        artifacts[name] = {
            "path": f"b-roll/{path.name}",
            "sha256": _write_json(path, {"kind": name}),
        }

    shots = []
    agent_input_shots = []
    layouts = [
        ("corner-left", 2.0, 4.0, "corner-pip", "top-left", None),
        ("corner-right", 4.0, 6.0, "corner-pip", "top-right", None),
        ("focused", 6.0, 8.0, "focused-panel", "lower-center",
         {"x": 0.04, "y": 0.08, "width": 0.92, "height": 0.40}),
        ("wash", 8.0, 10.0, "full-bleed-wash", "upper-center", None),
    ]
    for shot_id, start, end, layout, anchor, allowed_rect in layouts:
        media = normalized / f"{shot_id}.mp4"
        media.write_bytes(f"normalized-{shot_id}".encode("ascii"))
        speaker_inset = {
            "enabled": True,
            "layout": layout,
            "anchor": anchor,
        }
        if allowed_rect:
            speaker_inset["broll_rect"] = allowed_rect
        shots.append({
            "id": shot_id,
            "status": "verified",
            "program_range": {"start_s": start, "end_s": end},
            "speaker_inset_style": speaker_inset,
            "normalized_composite": {
                "path": f"cache/b-roll/normalized/{media.name}",
                "sha256": _sha256(media),
                "probe": {"width": 720, "height": 1280, "fps": {"num": 60, "den": 1}},
            },
        })
        display_mode = "pure_broll" if shot_id == "wash" else "enabled"
        agent_input_shots.append({
            "shot_id": shot_id,
            "layout_recommendation": {
                "preset": layout,
                "anchor": anchor,
            },
            "subshots": [{
                "id": f"{shot_id}-subshot-001",
                "display_mode": display_mode,
                "anchor": None if display_mode == "pure_broll" else anchor,
            }],
        })

    agent_input_path = work / "b-roll" / "speaker-inset-agent-input.json"
    artifacts["agent-input"]["sha256"] = _write_json(
        agent_input_path, {"shots": agent_input_shots},
    )

    broll_plan = {
        "schema_version": 1,
        "review": {"status": "approved"},
        "speaker_inset_style": {
            "enabled": True, "width_ratio": 0.39, "aspect_ratio": 0.8,
            "margin_ratio": 0.04, "reserved_bottom_ratio": 0.2,
        },
        "speaker_inset_bindings": {
            "analysis": artifacts["analysis"],
            "agent_input": artifacts["agent-input"],
            "preview": artifacts["preview"],
            "clearance": artifacts["clearance"],
        },
        "shots": shots,
    }
    broll_path = work / "b-roll" / "broll-plan.json"
    broll_sha = _write_json(broll_path, broll_plan)
    _write_json(work / "project.json", {
        "revision": 7,
        "sequences": {"main": {"operations": ["b-roll"]}},
        "operations": {
            "b-roll": {
                "id": "b-roll",
                "status": "approved",
                "revision": 4,
                "plan": {"path": "b-roll/broll-plan.json", "sha256": broll_sha},
                "check": {"status": "pending"},
            }
        },
    })
    return broll_path


def _assert_placement(context, cue_id, visual_context, placement, anchor=None):
    beat = next(beat for beat in context["placement_beats"] if cue_id in beat["cue_ids"])
    assert beat["visual_context"] == visual_context
    assert beat["resolved_placement"] == placement
    if anchor is not None:
        assert beat["anchor"] == anchor


def check_alignment_selects_containing_word_gap():
    cue = _cue("cue-gap", 1, 0.0, 1.0, [
        ("first", 0.0, 0.2),
        ("second", 0.8, 0.9),
        ("third", 0.91, 1.0),
    ])

    split_points, markers = caption_spatial_context._alignment_for_cue(cue, [0.79])

    assert list(split_points) == [1]
    assert split_points[1]["boundary_s"] == 0.79
    assert markers == []


def check_alignment_and_placements():
    with tempfile.TemporaryDirectory(prefix="caption-spatial-") as temporary:
        root = Path(temporary)
        _fixture(root)
        cues = [
            _cue("cue-001", 1, 0.2, 1.0, [("A-roll", 0.2, 1.0)]),
            _cue("cue-002", 2, 1.5, 2.5,
                 [("cross", 1.5, 1.8), ("boundary", 2.2, 2.5)]),
            _cue("cue-003", 3, 3.0, 3.8, [("left", 3.0, 3.8)]),
            _cue("cue-004", 4, 5.0, 5.8, [("right", 5.0, 5.8)]),
            _cue("cue-005", 5, 6.2, 6.8, [("focused", 6.2, 6.8)]),
            _cue("cue-006", 6, 8.2, 8.8, [("wash", 8.2, 8.8)]),
            _cue("cue-007", 7, 10.2, 11.0, [("close", 10.2, 11.0)]),
        ]

        standard, alignment = caption_spatial_context.align_plan_to_context_boundaries(
            root, _plan(copy.deepcopy(cues)),
        )
        assert [cue["id"] for cue in standard["cues"][:3]] == ["cue-001", "cue-002a", "cue-002b"]
        assert [word["word"] for cue in standard["cues"] for word in cue["words"]] == [
            word["word"] for cue in cues for word in cue["words"]
        ]
        split = next(item for item in alignment if item["original_cue_id"] == "cue-002")
        assert split["derived_cue_ids"] == ["cue-002a", "cue-002b"]
        assert split["boundary_s"] == 2.0
        assert split["split_after_word_index"] == 1
        assert standard["cues"][1]["original_cue_id"] == "cue-002"
        assert standard["cues"][2]["program_range"] == {"start_s": 2.2, "end_s": 2.5}
        assert standard["cues"][2]["source_ranges"] == [{"start_s": 2.2, "end_s": 2.5}]

        context = caption_spatial_context.build_context(root, standard, cue_alignment=alignment)
        assert caption_spatial_context.validate_context(context, standard, root) == []
        assert [
            (interval["program_range"]["start_s"], interval["program_range"]["end_s"], interval["visual_context"])
            for interval in context["visual_intervals"]
        ] == [
            (2.0, 4.0, "corner-pip"),
            (4.0, 6.0, "corner-pip"),
            (6.0, 8.0, "focused-panel"),
            (8.0, 10.0, "full-bleed-wash"),
        ]
        _assert_placement(context, "cue-001", "a-roll", "preset-bottom")
        _assert_placement(context, "cue-002a", "a-roll", "preset-bottom")
        _assert_placement(context, "cue-002b", "corner-pip", "preset-bottom")
        _assert_placement(context, "cue-003", "corner-pip", "preset-bottom")
        _assert_placement(context, "cue-004", "corner-pip", "preset-bottom")
        _assert_placement(context, "cue-005", "focused-panel", "panel-center", {"x": 0.5, "y": 0.28})
        _assert_placement(context, "cue-006", "full-bleed-wash", "preset-bottom")
        _assert_placement(context, "cue-007", "a-roll", "preset-bottom")
        wash_beat = next(beat for beat in context["placement_beats"] if "cue-006" in beat["cue_ids"])
        assert "speaker_anchor" not in wash_beat
        assert "speaker_rect" not in wash_beat

        expressive = _plan(copy.deepcopy(standard["cues"]), mode="expressive")
        expressive["presentation"]["planning_status"] = "complete"
        expressive["presentation"]["planner"]["rationale"] = "Exercise both maintained variants."
        expressive["presentation"]["layout_beats"] = [
            {
                "id": f"beat-{cue['index']:03d}",
                "variant": "center-emphasis",
                "cue_ids": [cue["id"]],
                "program_range": {"start_s": cue["start"], "end_s": cue["end"]},
                "rationale": "Exercise deterministic placement.",
            }
            for cue in expressive["cues"]
        ]
        expressive_context = caption_spatial_context.build_context(
            root, expressive, cue_alignment=alignment,
        )
        _assert_placement(expressive_context, "cue-002b", "corner-pip", "frame-center")
        _assert_placement(expressive_context, "cue-003", "corner-pip", "frame-center")
        _assert_placement(expressive_context, "cue-004", "corner-pip", "frame-center")
        _assert_placement(expressive_context, "cue-005", "focused-panel", "panel-center")
        _assert_placement(expressive_context, "cue-006", "full-bleed-wash", "frame-center")

        missing_alignment = copy.deepcopy(context)
        missing_alignment["cue_alignment"] = []
        assert any("cue_alignment" in error for error in caption_spatial_context.validate_context(
            missing_alignment, standard, root,
        ))
        duplicate_derived = copy.deepcopy(context)
        duplicate_derived["cue_alignment"][0]["derived_cue_ids"].append("cue-002a")
        assert any("derived cue ids" in error for error in caption_spatial_context.validate_context(
            duplicate_derived, standard, root,
        ))
        stale_anchor = copy.deepcopy(context)
        panel_beat = next(beat for beat in stale_anchor["placement_beats"]
                          if beat["resolved_placement"] == "panel-center")
        panel_beat["anchor"]["y"] = 0.3
        assert any("anchor" in error or "deterministic" in error
                   for error in caption_spatial_context.validate_context(stale_anchor, standard, root))
        missing_beat = copy.deepcopy(context)
        missing_beat["placement_beats"].pop()
        assert any("cover every cue" in error or "deterministic" in error
                   for error in caption_spatial_context.validate_context(missing_beat, standard, root))
        changed_cue = copy.deepcopy(standard)
        changed_cue["cues"][0]["end"] -= 0.1
        assert any("coverage" in error or "deterministic" in error
                   for error in caption_spatial_context.validate_context(context, changed_cue, root))
        try:
            caption_spatial_context.align_plan_to_context_boundaries(root, expressive)
        except ValueError as error:
            assert "draft" in str(error)
        else:
            raise AssertionError("completed Expressive plan must not be realigned")


def check_unsplittable_and_staleness():
    with tempfile.TemporaryDirectory(prefix="caption-spatial-stale-") as temporary:
        root = Path(temporary)
        broll_path = _fixture(root)
        cue = _cue("cue-001", 1, 1.5, 2.5, [("boundary", 1.5, 2.5)])
        aligned, alignment = caption_spatial_context.align_plan_to_context_boundaries(
            root, _plan([cue]),
        )
        assert len(aligned["cues"]) == 1
        marker = aligned["cues"][0]["unsplittable_word_boundary"]
        assert marker["boundary_s"] == 2.0
        assert marker["word_index"] == 1
        assert marker["midpoint_side"] in {"before", "after"}
        assert marker["requires_review"] is True
        context = caption_spatial_context.build_context(root, aligned, cue_alignment=alignment)
        assert caption_spatial_context.validate_context(context, aligned, root) == []

        boundary_cues = [
            _cue("cue-start", 1, 5.7, 6.2, [("starts", 5.7, 6.2)]),
            _cue("cue-end", 2, 7.7, 8.3, [("ends", 7.7, 8.3)]),
        ]
        boundary_plan, boundary_alignment = caption_spatial_context.align_plan_to_context_boundaries(
            root, _plan(boundary_cues),
        )
        boundary_context = caption_spatial_context.build_context(
            root, boundary_plan, cue_alignment=boundary_alignment,
        )
        expected_bottom_rect = {"x": 0.04, "y": 0.8, "width": 0.92, "height": 0.16}
        for cue_id in ("cue-start", "cue-end"):
            beat = next(item for item in boundary_context["placement_beats"] if cue_id in item["cue_ids"])
            assert beat["resolved_placement"] == "panel-bottom"
            assert beat["allowed_rect"] == expected_bottom_rect
            assert beat["anchor"] == {"x": 0.5, "y": 0.88}
            intersected = beat["intersected_visual_contexts"]
            assert any(item["visual_context"] == "focused-panel" and item.get("speaker_rect")
                       for item in intersected)
        start_beat = next(item for item in boundary_context["placement_beats"]
                          if "cue-start" in item["cue_ids"])
        assert [item["visual_context"] for item in start_beat["intersected_visual_contexts"]] == [
            "corner-pip", "focused-panel",
        ]
        end_beat = next(item for item in boundary_context["placement_beats"]
                        if "cue-end" in item["cue_ids"])
        assert [item["visual_context"] for item in end_beat["intersected_visual_contexts"]] == [
            "focused-panel", "full-bleed-wash",
        ]

        analysis_path = root / "work" / "b-roll" / "speaker-inset-analysis.json"
        analysis_bytes = analysis_path.read_bytes()
        analysis_path.write_bytes(analysis_bytes + b"\n")
        assert any("analysis" in error for error in caption_spatial_context.validate_context(context, aligned, root))
        analysis_path.write_bytes(analysis_bytes)

        normalized_path = root / "work" / "cache" / "b-roll" / "normalized" / "corner-left.mp4"
        normalized_bytes = normalized_path.read_bytes()
        normalized_path.write_bytes(normalized_bytes + b"stale")
        assert any("normalized" in error for error in caption_spatial_context.validate_context(context, aligned, root))
        normalized_path.write_bytes(normalized_bytes)

        stale = copy.deepcopy(context)
        stale["source"]["operation_revision"] += 1
        assert any("revision" in error for error in caption_spatial_context.validate_context(stale, aligned, root))

        broll_path.write_bytes(broll_path.read_bytes() + b"\n")
        assert any("b-roll plan" in error for error in caption_spatial_context.validate_context(context, aligned, root))


def _generate_preview(root, source, plan_path, context_path, name):
    scripts = Path(__file__).resolve().parent
    run = root / "renders" / name
    state = run / "interaction.json"
    project = run / "project"
    run.mkdir(parents=True)
    subprocess.run([
        "node", str(scripts / "caption_interaction.mjs"), "start",
        "--state", str(state), "--source", str(source), "--captions", str(plan_path),
        "--spatial-context", str(context_path), "--decision-mode", "agent",
        "--delegation-note", "Synthetic spatial renderer regression.", "--no-open", "true",
    ], check=True, capture_output=True, encoding="utf-8", errors="replace")
    subprocess.run([
        "node", str(scripts / "caption_interaction.mjs"), "agent-select",
        "--state", str(state), "--choice", "clean",
        "--rationale", "Use the stable clean fixture.",
    ], check=True, capture_output=True, encoding="utf-8", errors="replace")
    subprocess.run([
        "node", str(scripts / "generate_caption_project.mjs"),
        "--video", str(source), "--captions", str(plan_path), "--out", str(project),
        "--interaction-state", str(state), "--spatial-context", str(context_path),
        "--project-root", str(root), "--mode", "preview",
    ], check=True, capture_output=True, encoding="utf-8", errors="replace")
    return state, (project / "index.html").read_text(encoding="utf-8"), json.loads(
        (project / "project-meta.json").read_text(encoding="utf-8")
    )


def check_renderer_and_interaction_binding():
    with tempfile.TemporaryDirectory(prefix="caption-spatial-renderer-") as temporary:
        root = Path(temporary)
        _fixture(root)
        source = root / "source.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0x243447:s=320x180:r=30:d=12",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
        ], check=True)
        cues = [
            _cue("cue-001", 1, 3.0, 3.8, [("corner", 3.0, 3.8)]),
            _cue("cue-002", 2, 6.2, 6.9, [("focused", 6.2, 6.9)]),
            _cue("cue-003", 3, 7.7, 8.3, [("boundary", 7.7, 8.3)]),
            _cue("cue-004", 4, 8.5, 8.9, [("wash", 8.5, 8.9)]),
        ]
        cues[2]["unsplittable_word_boundary"] = {
            "boundary_s": 8.0,
            "word_index": 1,
            "word_midpoint_s": 8.0,
            "midpoint_side": "after",
            "requires_review": True,
        }
        captions_dir = root / "work" / "captions"
        captions_dir.mkdir(parents=True)

        standard = _plan(copy.deepcopy(cues))
        standard_context = caption_spatial_context.build_context(root, standard)
        standard_context_path = captions_dir / "standard-spatial.json"
        _write_json(standard_context_path, standard_context)
        standard_path = captions_dir / "standard-plan.json"
        _write_json(standard_path, standard)
        caption_spatial_context.attach_context(standard_path, standard_context_path, root)
        standard_state, standard_html, standard_meta = _generate_preview(
            root, source, standard_path, standard_context_path, "standard",
        )
        assert "placement-panel-center" in standard_html
        assert "placement-panel-bottom" in standard_html
        assert standard_html.count("placement-preset-bottom") >= 2
        assert 'data-resolved-placement="frame-center"' not in standard_html
        assert "expressive-cue" not in standard_html
        assert standard_meta["spatialContext"]["sha256"] == _sha256(standard_context_path)
        for cue in cues:
            cue_end = (
                f'timeline.set("#caption-cue-{cue["index"]}", '
                f'{{ opacity: 0 }}, {cue["end"]:.3f});'
            )
            assert cue_end in standard_html

        expressive = _plan(copy.deepcopy(cues), mode="expressive")
        expressive["presentation"]["planning_status"] = "complete"
        expressive["presentation"]["planner"]["rationale"] = "Center emphasis except the deterministic panel."
        expressive["presentation"]["layout_beats"] = [
            {
                "id": f"beat-{cue['index']:03d}", "variant": "center-emphasis",
                "cue_ids": [cue["id"]],
                "program_range": {"start_s": cue["start"], "end_s": cue["end"]},
                "rationale": "Synthetic emphasis fixture.",
            }
            for cue in expressive["cues"]
        ]
        expressive["cues"][1]["hero_line"] = {
            "level": "hero", "word_indexes": [1],
            "rationale": "Exercise the maximum maintained hero level.",
        }
        expressive_context = caption_spatial_context.build_context(root, expressive)
        expressive_context_path = captions_dir / "expressive-spatial.json"
        _write_json(expressive_context_path, expressive_context)
        expressive_path = captions_dir / "expressive-plan.json"
        _write_json(expressive_path, expressive)
        caption_spatial_context.attach_context(expressive_path, expressive_context_path, root)
        _, expressive_html, expressive_meta = _generate_preview(
            root, source, expressive_path, expressive_context_path, "expressive",
        )
        assert expressive_html.count("placement-frame-center") >= 2
        assert "placement-panel-center" in expressive_html
        assert "placement-panel-bottom" in expressive_html
        assert 'data-resolved-placement="panel-center"' in expressive_html
        assert 'class="caption-hero-line hero-level-hero"' in expressive_html
        assert "transform: translateY(var(--caption-motion-y" in expressive_html
        assert '"--caption-motion-y":' in expressive_html
        assert " opacity: 0, y:" not in expressive_html
        assert " opacity: 1, y:" not in expressive_html
        assert expressive_meta["presentation"]["heroLines"][0]["level"] == "hero"

        context_bytes = standard_context_path.read_bytes()
        standard_context_path.write_bytes(context_bytes + b"\n")
        stale = subprocess.run([
            "node", str(Path(__file__).resolve().parent / "caption_interaction.mjs"),
            "status", "--state", str(standard_state),
        ], check=False, capture_output=True, encoding="utf-8", errors="replace")
        assert stale.returncode != 0
        assert "spatial context" in (stale.stdout + stale.stderr).lower()
        standard_context_path.write_bytes(context_bytes)

        project_path = root / "work" / "project.json"
        project_bytes = project_path.read_bytes()
        project = json.loads(project_bytes)
        project["operations"]["b-roll"]["revision"] += 1
        project_path.write_text(json.dumps(project), encoding="utf-8")
        stale = subprocess.run([
            "node", str(Path(__file__).resolve().parent / "caption_interaction.mjs"),
            "status", "--state", str(standard_state),
        ], check=False, capture_output=True, encoding="utf-8", errors="replace")
        assert stale.returncode != 0
        assert "b-roll operation" in (stale.stdout + stale.stderr).lower()
        project_path.write_bytes(project_bytes)


if __name__ == "__main__":
    check_alignment_selects_containing_word_gap()
    check_alignment_and_placements()
    check_unsplittable_and_staleness()
    check_renderer_and_interaction_binding()
    print("[caption-spatial-context] PASS composite-aware placement and stale-binding checks")
