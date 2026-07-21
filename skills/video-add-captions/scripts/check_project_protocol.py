"""Small regression checks for the caption project protocol."""

import json
import subprocess
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
                    "statePath": str(state.resolve()),
                    "selectionId": "clean",
                    "overridesSha256": None,
                }
            }),
            encoding="utf-8",
        )
        run(
            "preview-ready", "--state", state, "--project-meta", project_meta,
            "--evidence", ",".join(evidence),
        )
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
    check_orphan_merge_keeps_grouping_limits()
    check_hyphenated_tokens_do_not_gain_space()
    check_adjacent_cues_do_not_overlap()
    check_delegated_caption_review()
    print("[caption-protocol] canonical caption plan passed")
    print("[caption-protocol] grouping limits passed")
    print("[caption-protocol] hyphenated token spacing passed")
    print("[caption-protocol] non-overlapping cue timing passed")
    print("[caption-protocol] delegated review passed")


if __name__ == "__main__":
    main()
