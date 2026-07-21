"""Small executable checks for the video-to-shorts project protocol."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import extract_shorts
import boundary_refine
import candidates
import plan as shorts_plan
import prepare_transcript
import render_vertical
import review_gate
import vertical_plan
from transcript_utils import excerpt_for_range
from transcript_utils import load_json, write_json


def timeline_fixture():
    return {
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


def check_boundary_release_guard():
    transcript = {
        "duration": 3.0,
        "segments": [{
            "start": 0.2,
            "end": 1.4,
            "text": "complete. next",
            "words": [
                {"start": 0.2, "end": 1.0, "word": " complete."},
                {"start": 1.1, "end": 1.4, "word": " next"},
            ],
        }],
    }
    refined = boundary_refine.refine_short_boundary(
        {"short_id": "short-release", "start_time": 0.2, "end_time": 1.0},
        transcript,
        media_duration=3.0,
        snap_to_phrases=False,
    )
    assert refined["content_end_time"] == 1.0
    assert refined["refined_end_time"] == 1.3
    assert refined["media_tail_after_content_end_s"] == 0.3
    assert "RAW_END_PROTECTED_BY_RELEASE_HANDLE" in refined["reasons"]
    assert "TAIL_OVERLAP_ALLOWED_FOR_FINAL_WORD_RELEASE" in refined["warnings"]

    keep_spans = [{"start_time": 0.2, "end_time": 1.3}]
    remapped = extract_shorts.remap_transcript(
        transcript,
        {"short_id": "short-release"},
        Path("source.mp4"),
        Path("transcript.json"),
        keep_spans,
        1.1,
        refined["content_start_time"],
        refined["content_end_time"],
    )
    words = [
        word["word"].strip()
        for segment in remapped["segments"]
        for word in segment["words"]
    ]
    assert words == ["complete."]
    assert extract_shorts.map_source_time_to_output(keep_spans, 1.0) == 0.8


def transcript_fixture():
    return {
        "duration": 6.0,
        "segments": [{
            "id": 1,
            "start": 0.0,
            "end": 5.0,
            "text": "first middle removed final",
            "words": [
                {"start": 0.0, "end": 0.4, "word": " first"},
                {"start": 0.8, "end": 1.2, "word": " middle"},
                {"start": 2.5, "end": 2.9, "word": " removed"},
                {"start": 4.0, "end": 4.5, "word": " final"},
            ],
        }],
    }


def check_exact_excerpt():
    assert excerpt_for_range(transcript_fixture(), 0.7, 1.3) == "middle"


def check_program_transcript():
    transcript = prepare_transcript.prepare_transcript_data(
        transcript_fixture(), timeline_fixture()
    )
    assert transcript["timebase"] == "program"
    assert transcript["timeline_id"] == "main"
    assert transcript["duration"] == 3.0
    words = [word for segment in transcript["segments"] for word in segment["words"]]
    assert [word["word"].strip() for word in words] == ["first", "middle", "final"]
    assert words[-1]["program_range"] == {"start_s": 2.0, "end_s": 2.25}


def check_delegated_reviews():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "short_01" / "source.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"source")
        write_json(root / "transcript.json", transcript_fixture())
        candidate_dir = root / "preview" / "text_visual"
        write_json(candidate_dir / "shorts_candidates.json", {
            "schema_version": "shorts-candidates.v2",
            "video": {"source": str(source)},
            "selection": {"evidence_mode": "text_visual"},
            "candidates": [{
                "candidate_id": "cand-001",
                "title": "Candidate",
                "evidence_mode": "text_visual",
                "score": 90,
                "duration": 25.0,
            }],
        })
        (candidate_dir / "shorts_candidates_preview.html").write_text(
            "<html>candidate</html>", encoding="utf-8"
        )
        review_gate.open_candidate_review(
            root, decision_mode="agent", delegation_note="User delegated shorts review."
        )
        candidate_review = review_gate.answer_candidate_review_agent(
            root,
            ["text_visual/cand-001"],
            "horizontal_and_vertical",
            "The complete candidate has a clear hook and payoff.",
        )
        assert candidate_review["status"] == "approved"
        assert candidate_review["decision_mode"] == "agent"
        assert candidate_review["decision"]["actor"] == "agent"
        assert "user_response" not in candidate_review

        vertical_root = source.parent / "vertical-agent"
        plan = vertical_root / "vertical_plan.json"
        summary = vertical_root / "preview_summary.md"
        probe = vertical_root / "media_probe.json"
        preview = vertical_root / "vertical_preview.mp4"
        contact = vertical_root / "vertical_contact.jpg"
        write_json(plan, {"strategy": "STATIC_CROP"})
        summary.write_text("preview", encoding="utf-8")
        write_json(probe, {"ok": True})
        preview.write_bytes(b"preview")
        contact.write_bytes(b"contact")
        review_gate.open_vertical_review(
            vertical_root, source, plan, summary, probe, preview, contact
        )
        vertical_review = review_gate.answer_vertical_review_agent(
            vertical_root, "The crop keeps the subject safe in every reviewed frame."
        )
        assert vertical_review["status"] == "approved"
        assert vertical_review["decision_mode"] == "agent"
        assert vertical_review["decision_actor"] == "agent"
        assert "user_response" not in vertical_review
        summary.write_text("changed", encoding="utf-8")
        try:
            review_gate.validate_vertical_review(vertical_root, source, plan)
        except SystemExit as error:
            assert "changed after review" in str(error)
        else:
            raise AssertionError("changed vertical preview evidence was accepted")


def score_breakdown():
    return {
        "hook": {"score": 16, "reason": "Immediate claim."},
        "completeness": {"score": 19, "reason": "Complete thought."},
        "audience_value": {"score": 18, "reason": "Useful insight."},
        "emotion_tension": {"score": 8, "reason": "Clear stakes."},
        "quotability": {"score": 12, "reason": "Memorable line."},
        "pace_editability": {"score": 8, "reason": "Compact delivery."},
    }


def check_canonical_plan_and_extraction_command():
    with tempfile.TemporaryDirectory() as temporary:
        project_root = Path(temporary)
        work = project_root / "work"
        shorts = work / "shorts"
        final_video = project_root / "final" / "final-video.mp4"
        source_video = project_root / "input" / "source.mp4"
        final_video.parent.mkdir(parents=True)
        source_video.parent.mkdir(parents=True)
        final_video.write_bytes(b"final")
        source_video.write_bytes(b"source")
        timeline = {
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30000, "den": 1001},
            "source_duration_s": 60.0,
            "program_duration_s": 60.0,
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 60.0},
                "program_range": {"start_s": 0.0, "end_s": 60.0},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        }
        write_json(work / "timeline.json", timeline)
        transcript = {
            "duration": 60.0,
            "timebase": "program",
            "timeline_id": "source",
            "segments": [{
                "start": 10.0,
                "end": 35.0,
                "text": "A clear complete payoff",
                "words": [
                    {"start": 10.0, "end": 10.5, "word": " A", "clip_id": "clip-001", "source_range": {"start_s": 10.0, "end_s": 10.5}, "program_range": {"start_s": 10.0, "end_s": 10.5}},
                    {"start": 15.0, "end": 15.5, "word": " clear", "clip_id": "clip-001", "source_range": {"start_s": 15.0, "end_s": 15.5}, "program_range": {"start_s": 15.0, "end_s": 15.5}},
                    {"start": 34.0, "end": 34.5, "word": " payoff", "clip_id": "clip-001", "source_range": {"start_s": 34.0, "end_s": 34.5}, "program_range": {"start_s": 34.0, "end_s": 34.5}},
                ],
            }],
        }
        write_json(shorts / "transcript.json", transcript)
        project = {
            "schema_version": 1,
            "project_id": "shorts-fixture",
            "source": {"path": "../input/source.mp4", "fingerprint": {}},
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": ["understanding", "captions"]}},
            "operations": [
                {"id": "understanding", "revision": 2},
                {"id": "captions", "revision": 3},
            ],
            "render": {"output": "../final/final-video.mp4", "status": "verified"},
        }
        write_json(work / "project.json", project)
        candidate_dir = shorts / "preview" / "text_visual"
        write_json(candidate_dir / "shorts_candidates.json", {
            "schema_version": "shorts-candidates.v2",
            "video": {"source": str(final_video)},
            "transcript": {"path": str(shorts / "transcript.json"), "timebase": "program"},
            "selection": {"evidence_mode": "text_visual"},
            "candidates": [{
                "candidate_id": "cand-001", "title": "Complete payoff",
                "scene_type": "solo_talk", "evidence_mode": "text_visual",
                "start_time": 10.0, "end_time": 35.0, "duration": 25.0,
                "transcript_excerpt": "A clear payoff", "score_breakdown": score_breakdown(),
                "score": 81, "metadata": {"editorial_reason": "The claim and payoff form a complete short."},
                "warnings": [], "filler_drop_spans": [],
            }],
        })
        (candidate_dir / "shorts_candidates_preview.html").write_text("preview", encoding="utf-8")
        review_gate.open_candidate_review(shorts, "agent", "User delegated shorts decisions.")
        review_gate.answer_candidate_review_agent(
            shorts, ["text_visual/cand-001"], "horizontal_and_vertical",
            "The candidate is complete and useful.",
        )
        shorts_plan.run_plan(SimpleNamespace(
            out=str(shorts), transcript=None, project_root=str(project_root),
            max_shorts=5, min_duration=20.0, max_duration=90.0,
            min_score=70.0, min_completeness=15.0, allow_overlap=False,
        ))
        canonical = load_json(shorts / "shorts-plan.json")
        assert canonical["schema_version"] == 1
        assert canonical["based_on"] == {"understanding": 2, "captions": 3}
        assert canonical["selection"]["mode"] == "agent"
        short = canonical["shorts"][0]
        assert short["program_range"] == {"start_s": 10.0, "end_s": 35.0}
        assert short["source_ranges"] == [{"start_s": 10.0, "end_s": 35.0}]
        assert short["outputs"]["horizontal_video"] == "../final/shorts/short-001-horizontal.mp4"
        assert short["outputs"]["vertical_video"] == "../final/shorts/short-001-vertical.mp4"

        command = extract_shorts.build_extract_command(
            "ffmpeg", final_video, project_root / "out.mp4",
            [{"start_time": 10.0, "end_time": 15.0}, {"start_time": 16.0, "end_time": 20.0}],
            has_audio=True,
        )
        assert command.count("-ss") == 2
        assert command.count("-t") == 2
        assert command.count("-i") == 2
        assert vertical_plan.parse_rate("30000/1001") == {"num": 30000, "den": 1001}


def check_media_integration():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30000/1001:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(source),
        ], check=True)
        horizontal = root / "horizontal.mp4"
        command = extract_shorts.build_extract_command(
            "ffmpeg", source, horizontal,
            [{"start_time": 0.5, "end_time": 1.5}, {"start_time": 2.0, "end_time": 3.0}],
            has_audio=True,
        )
        subprocess.run(command, check=True, capture_output=True)
        horizontal_probe = render_vertical.probe_media("ffprobe", horizontal)
        assert any(stream.get("codec_type") == "audio" for stream in horizontal_probe["streams"])
        assert abs(float(horizontal_probe["format"]["duration"]) - 2.0) < 0.1
        extract_shorts.validate_extracted_media(
            extract_shorts.probe_media("ffprobe", source),
            extract_shorts.probe_media("ffprobe", horizontal),
            2.0,
        )

        source_metadata = vertical_plan.probe_video("ffprobe", source)
        raw_plan = {
            "target_aspect_ratio": "9:16",
            "strategy": "STATIC_CROP",
            "segments": [{
                "start_time": 0.0,
                "end_time": source_metadata["duration_s"],
                "strategy": "STATIC_CROP",
                "content_type": "PRESENTER",
                "crop_x": 110,
                "crop_y": 0,
                "crop_width": 100,
                "crop_height": 178,
                "reason": "Synthetic subject remains inside a stable crop.",
            }],
            "visual_evidence": [],
            "warnings": [],
        }
        vertical = vertical_plan.validate_plan(raw_plan, source, source_metadata)
        output = root / "vertical.mp4"
        source_probe = render_vertical.probe_media("ffprobe", source)
        render_vertical.render(
            "ffmpeg", source_probe, source, vertical, output,
            vertical["output_width"], vertical["output_height"], vertical["source_fps"],
            {"background_crop": {"x": 0, "y": 0, "width": 320, "height": 180}},
        )
        output_probe = render_vertical.probe_media("ffprobe", output)
        render_vertical.validate_rendered_media(
            output_probe, vertical["output_width"], vertical["output_height"],
            vertical["source_duration_s"], vertical["source_fps"], True,
        )


def check_direct_vertical_rendering():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30000/1001:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(source),
        ], check=True)
        keep_spans = [
            {"start_time": 0.5, "end_time": 1.5},
            {"start_time": 2.0, "end_time": 3.0},
        ]
        horizontal = root / "horizontal.mp4"
        subprocess.run(
            extract_shorts.build_extract_command(
                "ffmpeg", source, horizontal, keep_spans, has_audio=True,
            ),
            check=True,
            capture_output=True,
        )
        report_path = root / "extraction-report.json"
        write_json(report_path, {
            "schema_version": "short-extraction-report.v2",
            "source_video": str(source.resolve()),
            "keep_spans": keep_spans,
            "outputs": {"horizontal_video": str(horizontal.resolve())},
        })
        horizontal_metadata = vertical_plan.probe_video("ffprobe", horizontal)
        raw_plan = {
            "target_aspect_ratio": "9:16",
            "strategy": "STATIC_CROP",
            "segments": [{
                "start_time": 0.0,
                "end_time": horizontal_metadata["duration_s"],
                "strategy": "STATIC_CROP",
                "content_type": "PRESENTER",
                "crop_x": 110,
                "crop_y": 0,
                "crop_width": 100,
                "crop_height": 178,
                "reason": "Synthetic subject remains inside a stable crop.",
            }],
            "visual_evidence": [],
            "warnings": [],
        }
        plan = vertical_plan.validate_plan(raw_plan, horizontal, horizontal_metadata)
        vertical_plan.bind_direct_render(
            plan, horizontal, horizontal_metadata, source, report_path, "ffprobe",
        )
        context = render_vertical.direct_render_context(plan, horizontal, "ffprobe")
        render_source, source_probe, render_plan, mapped_duration, bound_report = context
        assert render_source == source.resolve()
        assert bound_report == report_path.resolve()
        assert mapped_duration == 2.0
        assert [
            (segment["start_time"], segment["end_time"])
            for segment in render_plan["segments"]
        ] == [(0.5, 1.5), (2.0, 3.0)]
        output = root / "vertical-direct.mp4"
        render_vertical.render(
            "ffmpeg", source_probe, render_source, render_plan, output,
            plan["output_width"], plan["output_height"], plan["source_fps"],
            {"background_crop": {"x": 0, "y": 0, "width": 320, "height": 180}},
        )
        output_probe = render_vertical.probe_media("ffprobe", output)
        render_vertical.validate_rendered_media(
            output_probe, plan["output_width"], plan["output_height"],
            mapped_duration, plan["source_fps"], True,
        )


def check_project_candidate_binding():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        work = root / "work"
        final_video = root / "final" / "final-video.mp4"
        source_transcript = work / "understand" / "transcript.json"
        timeline_path = work / "timeline.json"
        shorts = work / "shorts"
        candidate_dir = shorts / "preview" / "text_visual"
        final_video.parent.mkdir(parents=True)
        final_video.write_bytes(b"final")
        transcript = {
            "duration": 20.0,
            "timebase": "program",
            "timeline_id": "source",
            "segments": [{
                "start": 0.0, "end": 20.0, "text": "hello payoff",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": " hello"},
                    {"start": 19.0, "end": 19.5, "word": " payoff"},
                ],
            }],
        }
        write_json(source_transcript, transcript)
        write_json(shorts / "transcript.json", transcript)
        timeline = {
            "schema_version": 1, "timeline_id": "source", "source_asset_id": "source",
            "fps": {"num": 30, "den": 1}, "source_duration_s": 20.0,
            "program_duration_s": 20.0,
            "clips": [{
                "id": "clip-001", "source_range": {"start_s": 0.0, "end_s": 20.0},
                "program_range": {"start_s": 0.0, "end_s": 20.0}, "speed": 1.0,
                "decision_ref": "source",
            }],
        }
        write_json(timeline_path, timeline)
        write_json(work / "project.json", {
            "render": {"status": "verified", "output": "../final/final-video.mp4"},
            "active_sequence": "main",
            "sequences": {"main": {"timeline": "timeline.json", "operations": []}},
        })
        write_json(shorts / "transcript_metadata.json", {
            "timebase": "program", "timeline_id": "source",
            "bindings": {
                "video": prepare_transcript.file_binding(final_video),
                "source_transcript": prepare_transcript.file_binding(source_transcript),
                "timeline": prepare_transcript.file_binding(timeline_path),
            },
        })
        write_json(candidate_dir / "input.json", {
            "schema_version": "shorts-candidates.v2",
            "selection": {"evidence_mode": "text_visual"},
            "candidates": [{
                "candidate_id": "cand-001", "title": "Hello payoff",
                "scene_type": "solo_talk", "start_time": 0.0, "end_time": 20.0,
                "transcript_excerpt": "hello payoff", "evidence_mode": "text_visual",
                "score_breakdown": score_breakdown(),
                "metadata": {"editorial_reason": "The complete claim ends with a payoff."},
            }],
        })
        args = SimpleNamespace(
            out=str(candidate_dir), candidates=str(candidate_dir / "input.json"),
            transcript=str(shorts / "transcript.json"), project_root=str(root),
        )
        candidates.run_candidates(args)
        normalized = load_json(candidate_dir / "shorts_candidates.json")
        assert normalized["video"]["source"] == str(final_video.resolve())
        assert normalized["transcript"]["timebase"] == "program"
        timeline["note"] = "changed"
        write_json(timeline_path, timeline)
        try:
            candidates.run_candidates(args)
        except SystemExit as error:
            assert "timeline changed" in str(error)
        else:
            raise AssertionError("changed project timeline was accepted")


def normalize_whitespace(value):
    return re.sub(r"\s+", " ", value).strip()


def markdown_section(document, heading):
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", document
    )
    assert match, f"missing ## {heading} section"
    return match.group(1)


def fenced_blocks(section):
    return re.findall(r"(?ms)^```[^\n]*\n(.*?)^```\s*$", section)


def require_block(section, *parts):
    expected = [normalize_whitespace(part) for part in parts]
    assert any(
        all(part in normalize_whitespace(block) for part in expected)
        for block in fenced_blocks(section)
    ), f"no command/summary block contains: {', '.join(parts)}"


def require_exact_block(section, pattern, label):
    assert any(
        re.fullmatch(pattern, normalize_whitespace(block))
        for block in fenced_blocks(section)
    ), f"missing exact {label} block"


def check_workflow_ui():
    script = Path(__file__).with_name("check_review_ui.py")
    subprocess.run([sys.executable, str(script)], check=True)
    print("[shorts-protocol] bound workflow UI passed")


def check_documented_review_workflow():
    skill_root = Path(__file__).resolve().parent.parent
    skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    readme = (skill_root / "README.md").read_text(encoding="utf-8")
    output = markdown_section(skill, "Output Layout")
    candidates_review = markdown_section(skill, "Review Modes")
    vertical_review = markdown_section(skill, "Vertical Planning")
    compatibility = markdown_section(skill, "Compatibility")

    assert not re.search(r"\bUUIDs?\b", f"{skill}\n{readme}", re.IGNORECASE), (
        "token_hex review IDs must not be described as UUIDs"
    )

    for marker in (
        "candidates-<review-id>.html", "assets/candidates-<review-id>/",
        "candidates.html", "<short-id>-vertical-review-<review-id>.html",
        "<short-id>-vertical-review.html", "vertical-preview.mp4",
        "vertical-contact-sheet.jpg", "vertical-preview-summary.json",
        "vertical-preview-probe.json",
    ):
        assert marker in output, f"output layout omits {marker}"
    require_block(
        output, "<short-id>-vertical-review-assets/", "<review-id>/",
        "preview.mp4", "contact-sheet.jpg", "preview-summary.json", "media-probe.json",
    )

    require_exact_block(
        candidates_review,
        r'python "\$SkillRoot\\scripts\\interaction\.py" candidate-open '
        r'--out \$ShortsWork --review-out \$ShortsReview',
        "candidate-open command",
    )
    require_block(
        candidates_review, "Start-Process", "Resolve-Path", "open", "xdg-open",
        "Present the authoritative page and STOP.",
    )
    require_block(
        candidates_review, "Shorts candidate review", "Review:", "Candidates:", "Delivery:"
    )
    require_block(
        candidates_review, "Shorts candidate review", "Review:", "Decision: revise", "Changes:"
    )
    candidate_text = normalize_whitespace(candidates_review)
    for marker in (
        "authoritative", "non-authoritative", "initially unselected", "1-5",
        "copy", "unchanged", "retry", "Present", "STOP", "explicit candidate",
        "explicit delivery", "rationale", "fake human",
    ):
        assert marker in candidate_text, f"candidate review workflow omits {marker}"
    assert "default top five" not in candidate_text.lower(), (
        "bound candidate workflow must not mention default top five"
    )

    require_exact_block(
        vertical_review,
        r'python "\$SkillRoot\\scripts\\render_vertical\.py" ` '
        r'--video \$Horizontal --plan "\$VerticalWork\\vertical_plan\.json" ` '
        r'--out \$VerticalWork --review-out \$ShortsReview --mode preview',
        "vertical preview command",
    )
    require_block(
        vertical_review, "Start-Process", "Resolve-Path", "open", "xdg-open",
        "Present the authoritative page and STOP.",
    )
    require_block(
        vertical_review, "Shorts vertical review", "Short:", "Review:", "Decision: approve"
    )
    require_block(
        vertical_review, "Shorts vertical review", "Short:", "Review:",
        "Decision: revise", "Changes:"
    )
    require_block(
        vertical_review, "Shorts vertical review", "Short:", "Review:", "Decision: skip"
    )
    vertical_text = normalize_whitespace(vertical_review)
    for marker in (
        "authoritative", "non-authoritative", "preview", "contact sheet", "segments",
        "media probe", "warnings", "copy", "unchanged", "retry", "Present", "STOP",
        "REVIEW_REQUIRED", "revise", "skip", "Agent", "rationale",
    ):
        assert marker in vertical_text, f"vertical review workflow omits {marker}"

    assert normalize_whitespace(skill).count("Present the authoritative page and STOP.") == 2, (
        "candidate and vertical workflows each need their own Present + STOP gate"
    )
    for marker in ("human and Agent modes are mutually exclusive", "page and media hashes"):
        assert marker.casefold() in normalize_whitespace(skill).casefold(), f"workflow omits {marker}"
    assert "candidate review invalidates" in vertical_text.casefold()
    assert "only approved" in vertical_text.casefold()
    assert "review-ID-scoped" in vertical_review
    assert "authoritative page and receipt bind" in vertical_text
    assert re.search(r"`?REVIEW_REQUIRED`? stores only", vertical_review)
    assert skill.casefold().count("default top five") == compatibility.casefold().count(
        "default top five"
    ) >= 1

    readme_text = normalize_whitespace(readme)
    assert all(re.search(rf"(?m)^{number}\. ", readme) for number in range(1, 8))
    assert not re.search(r"(?m)^8\. ", readme)
    for marker in (
        "interactive candidate", "interactive vertical", "work/shorts/",
        "work/cache/shorts/", "review/06-shorts/", "final/shorts/", "[SKILL.md](SKILL.md)",
        "review-ID-scoped",
    ):
        assert marker in readme_text, f"README omits {marker}"


def main():
    check_boundary_release_guard()
    check_exact_excerpt()
    check_program_transcript()
    check_delegated_reviews()
    check_canonical_plan_and_extraction_command()
    check_media_integration()
    check_direct_vertical_rendering()
    check_project_candidate_binding()
    check_workflow_ui()
    check_documented_review_workflow()
    print("[shorts-protocol] boundary release guard passed")
    print("[shorts-protocol] exact word excerpt passed")
    print("[shorts-protocol] program transcript passed")
    print("[shorts-protocol] delegated reviews passed")
    print("[shorts-protocol] canonical plan and seeked extraction passed")
    print("[shorts-protocol] horizontal and vertical media integration passed")
    print("[shorts-protocol] direct-source vertical rendering passed")
    print("[shorts-protocol] project candidate bindings passed")
    print("[shorts-protocol] documented review workflow passed")


if __name__ == "__main__":
    main()
