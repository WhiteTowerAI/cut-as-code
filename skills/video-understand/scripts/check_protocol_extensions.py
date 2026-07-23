"""Small regression checks for shared protocol extensions."""

import tempfile
from pathlib import Path

import projectlib
import render_project


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


def check_program_transcript_mapping():
    transcript = {
        "duration": 6.0,
        "language": "en",
        "segments": [
            {
                "id": 7,
                "start": 0.2,
                "end": 4.5,
                "text": "keep drop fast",
                "words": [
                    {"start": 0.2, "end": 0.6, "word": " keep"},
                    {"start": 0.7, "end": 0.7, "word": " point"},
                    {"start": 2.5, "end": 2.8, "word": " drop"},
                    {"start": 4.0, "end": 4.5, "word": " fast"},
                ],
            }
        ],
    }

    mapped = projectlib.map_transcript_to_timeline(transcript, timeline_fixture())
    assert mapped["timebase"] == "program"
    assert mapped["timeline_id"] == "main"
    assert mapped["duration"] == 3.0
    assert len(mapped["segments"]) == 2
    words = [word for segment in mapped["segments"] for word in segment["words"]]
    assert [word["word"].strip() for word in words] == ["keep", "point", "fast"]
    assert words[0]["source_range"] == {"start_s": 0.2, "end_s": 0.6}
    assert words[1]["source_range"]["end_s"] > words[1]["source_range"]["start_s"]
    assert words[1]["program_range"]["end_s"] > words[1]["program_range"]["start_s"]
    assert words[2]["program_range"] == {"start_s": 2.0, "end_s": 2.25}
    assert mapped["segments"][0]["clip_id"] == "clip-001"
    assert mapped["segments"][1]["clip_id"] == "clip-002"


def check_image_sequence_overlay():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for directory in (
            "input",
            "final",
            "review/05-captions",
            "work/captions",
            "work/cache/captions/overlay-frames",
            "work/render",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        source = root / "input/source.mp4"
        source.write_bytes(b"source")
        (root / "work/cache/captions/overlay-frames/frame_000001.png").write_bytes(
            b"\x89PNG\r\n\x1a\n"
        )
        (root / "review/05-captions/captions-summary.md").write_text(
            "# Captions\n", encoding="utf-8"
        )
        evidence = []
        for name in ("early", "middle", "late", "no-caption"):
            path = root / f"review/05-captions/preview-{name}.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n")
            evidence.append(f"../review/05-captions/preview-{name}.png")
        timeline = {
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30000, "den": 1001},
            "source_duration_s": 6.0,
            "program_duration_s": 6.0,
            "clips": [
                {
                    "id": "clip-001",
                    "source_range": {"start_s": 0.0, "end_s": 6.0},
                    "program_range": {"start_s": 0.0, "end_s": 6.0},
                    "speed": 1.0,
                    "decision_ref": "source",
                }
            ],
        }
        projectlib.write_json(root / "work/timeline.json", timeline)
        projectlib.write_json(
            root / "work/captions/captions-plan.json",
            {
                "schema_version": 1,
                "target": "overlay",
                "timeline_id": "source",
                "timebase": "program",
                "source_transcript": "understand/transcript.json",
                "program_duration_s": 6.0,
                "style": {
                    "status": "approved",
                    "selection_mode": "agent",
                    "selection_rationale": "Fixture decision.",
                    "choice_id": "clean",
                    "preset": "clean",
                    "resolved": {"preset": "clean"},
                },
                "review": {"status": "approved", "evidence": evidence},
                "cues": [
                    {
                        "start": 0.2,
                        "end": 0.6,
                        "program_range": {"start_s": 0.2, "end_s": 0.6},
                        "text": "Fixture",
                        "lines": ["Fixture"],
                        "words": [{
                            "word": "Fixture",
                            "start": 0.2,
                            "end": 0.6,
                            "clip_id": "clip-001",
                            "source_range": {"start_s": 0.2, "end_s": 0.6},
                            "program_range": {"start_s": 0.2, "end_s": 0.6},
                        }],
                    }
                ],
                "renderer_recipe": {
                    "engine": "hyperframes",
                    "asset_type": "image-sequence",
                    "fps": {"num": 30000, "den": 1001},
                    "composition": "cache/captions/index.html",
                    "asset": "cache/captions/overlay-frames",
                    "runtime_assets": [{"path": "assets/gsap.min.js", "sha256": "0" * 64}],
                },
            },
        )
        source_stat = source.stat()
        project = {
            "schema_version": 1,
            "project_id": "caption-overlay-fixture",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": source_stat.st_size,
                    "modified_ns": source_stat.st_mtime_ns,
                    "duration_s": 6.0,
                },
            },
            "active_sequence": "main",
            "sequences": {"main": {"operations": ["captions"], "timeline": "timeline.json"}},
            "operations": [
                {
                    "id": "understanding",
                    "skill": "video-understand",
                    "revision": 1,
                    "depends_on": [],
                    "based_on": {},
                    "status": "verified",
                    "plan": None,
                    "outputs": [],
                    "target": {"sequence": "main", "scope": "evidence"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                        "adds_track": None,
                    },
                },
                {
                    "id": "captions",
                    "skill": "video-add-captions",
                    "revision": 1,
                    "depends_on": ["understanding"],
                    "based_on": {"understanding": 1},
                    "status": "approved",
                    "plan": "captions/captions-plan.json",
                    "outputs": ["cache/captions/overlay-frames"],
                    "target": {"sequence": "main", "scope": "captions"},
                    "effects": {
                        "changes_timeline": False,
                        "changes_geometry": False,
                        "changes_video_pixels": False,
                        "changes_audio": False,
                        "adds_track": "captions",
                    },
                    "check": {
                        "status": "pass",
                        "report": "../review/05-captions/captions-summary.md",
                    },
                    "render": {
                        "kind": "overlay",
                        "asset": "cache/captions/overlay-frames",
                        "asset_type": "image-sequence",
                        "pattern": "frame_%06d.png",
                        "start_number": 1,
                        "fps": {"num": 30000, "den": 1001},
                    },
                },
            ],
            "render": {
                "plan": "render/render-plan.json",
                "output": "../final/final-video.mp4",
                "status": "draft",
            },
            "reviews": [],
        }
        projectlib.write_json(root / "work/project.json", project)

        plan = projectlib.build_render_plan(project, root)
        overlay = plan["contributions"][0]
        assert overlay["asset_type"] == "image-sequence"
        assert overlay["asset"] == "../cache/captions/overlay-frames"
        plan.pop("source_fingerprint")
        command = render_project.build_command(plan, root)
        assert command[command.index("-framerate") + 1] == "30000/1001"
        assert command[command.index("-start_number") + 1] == "1"
        assert command[command.index("-i", command.index("-framerate")) + 1].endswith(
            "overlay-frames\\frame_%06d.png"
        )

        caption_plan_path = root / "work/captions/captions-plan.json"
        caption_plan = projectlib.load_json(caption_plan_path)
        caption_plan["style"]["status"] = "draft"
        projectlib.write_json(caption_plan_path, caption_plan)
        try:
            projectlib.build_render_plan(project, root)
        except ValueError as error:
            assert "caption style is not approved" in str(error)
        else:
            raise AssertionError("draft caption style was accepted")
        caption_plan["style"]["status"] = "approved"
        projectlib.write_json(caption_plan_path, caption_plan)

        project["operations"][1]["render"]["pattern"] = "../frame_%06d.png"
        try:
            projectlib.build_render_plan(project, root)
        except ValueError as error:
            assert "pattern is invalid" in str(error)
        else:
            raise AssertionError("escaping image-sequence pattern was accepted")
        project["operations"][1]["render"]["pattern"] = "frame_%06d.png"
        project["operations"][1]["render"]["fps"] = {"num": 24, "den": 1}
        try:
            projectlib.build_render_plan(project, root)
        except ValueError as error:
            assert "fps does not match" in str(error)
        else:
            raise AssertionError("mismatched image-sequence fps was accepted")


def check_precomputed_overlay_compatibility():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "input").mkdir()
        (root / "final").mkdir()
        (root / "work/render").mkdir(parents=True)
        source = root / "input/source.mp4"
        overlay = root / "work/legacy-overlay.mov"
        source.write_bytes(b"source")
        overlay.write_bytes(b"overlay")
        projectlib.write_json(root / "work/timeline.json", {
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30, "den": 1},
            "source_duration_s": 1.0,
            "program_duration_s": 1.0,
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 0.0, "end_s": 1.0},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        })
        plan = {
            "schema_version": 1,
            "source": "../../input/source.mp4",
            "timeline": "../timeline.json",
            "contributions": [{
                "kind": "precomputed-asset",
                "target": "overlay",
                "asset": "../legacy-overlay.mov",
            }],
            "output": "../../final/out.mp4",
        }

        command = render_project.build_command(plan, root)
        assert str(overlay.resolve()) in command


def check_dependency_revision_coverage():
    effects = {
        "changes_timeline": False,
        "changes_geometry": False,
        "changes_video_pixels": False,
        "changes_audio": False,
        "adds_track": None,
    }
    operations = [
        {
            "id": "understanding", "skill": "video-understand", "revision": 1,
            "depends_on": [], "based_on": {}, "status": "verified",
            "target": {"sequence": "main", "scope": "evidence"}, "effects": effects,
        },
        {
            "id": "cut", "skill": "video-cut", "revision": 1,
            "depends_on": ["understanding"], "based_on": {"understanding": 1},
            "status": "verified", "target": {"sequence": "main", "scope": "timeline"},
            "effects": effects,
        },
        {
            "id": "captions", "skill": "video-add-captions", "revision": 1,
            "depends_on": ["understanding"], "based_on": {}, "status": "verified",
            "target": {"sequence": "main", "scope": "captions"}, "effects": effects,
        },
    ]
    project = {
        "schema_version": 1,
        "active_sequence": "main",
        "sequences": {"main": {"operations": [], "timeline": "timeline.json"}},
        "operations": operations,
        "reviews": [],
    }

    errors = projectlib.validate_project(project, Path("."), check_files=False)
    assert "captions based_on missing revision for dependency: understanding" in errors

    operations[2]["based_on"] = {"understanding": 1, "cut": 1}
    errors = projectlib.validate_project(project, Path("."), check_files=False)
    assert "captions based_on has unexpected dependency: cut" in errors

    operations[2]["based_on"] = {"understanding": 1}
    project["reviews"] = [{
        "id": "compare", "revision": 1, "depends_on": ["captions", "render"],
        "based_on": {"captions": 1}, "status": "verified",
    }]
    errors = projectlib.validate_project(project, Path("."), check_files=False)
    assert not [error for error in errors if error.startswith("compare based_on")]


def check_verified_durable_outputs():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for directory in (
            "input", "final/shorts", "review/06-shorts", "work/shorts", "work/cache"
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        source = root / "input/source.mp4"
        source.write_bytes(b"source")
        projectlib.write_json(root / "work/timeline.json", {
            "schema_version": 1,
            "timeline_id": "source",
            "source_asset_id": "source",
            "fps": {"num": 30, "den": 1},
            "source_duration_s": 1.0,
            "program_duration_s": 1.0,
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 1.0},
                "program_range": {"start_s": 0.0, "end_s": 1.0},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        })
        projectlib.write_json(root / "work/shorts/shorts-plan.json", {"schema_version": 1})
        (root / "review/06-shorts/shorts-summary.md").write_text("# Shorts\n", encoding="utf-8")
        project = {
            "schema_version": 1,
            "project_id": "verified-output-fixture",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": projectlib.quick_fingerprint(source, 1.0),
            },
            "active_sequence": "main",
            "sequences": {"main": {"operations": [], "timeline": "timeline.json"}},
            "operations": [{
                "id": "shorts",
                "skill": "video-to-shorts",
                "revision": 1,
                "depends_on": [],
                "based_on": {},
                "status": "verified",
                "plan": "shorts/shorts-plan.json",
                "outputs": [
                    "../final/shorts/short-001.mp4",
                    "cache/shorts/disposable-preview",
                ],
                "target": {"sequence": "main", "scope": "derivatives"},
                "effects": {
                    "changes_timeline": True,
                    "changes_geometry": True,
                    "changes_video_pixels": True,
                    "changes_audio": True,
                    "adds_track": None,
                },
                "check": {
                    "status": "pass",
                    "report": "../review/06-shorts/shorts-summary.md",
                },
            }],
            "reviews": [],
        }

        errors = projectlib.validate_project(project, root)
        assert "shorts missing output: ../final/shorts/short-001.mp4" in errors

        (root / "final/shorts/short-001.mp4").write_bytes(b"short")
        errors = projectlib.validate_project(project, root)
        assert not [error for error in errors if "output" in error]


def main():
    check_program_transcript_mapping()
    check_image_sequence_overlay()
    check_precomputed_overlay_compatibility()
    check_dependency_revision_coverage()
    check_verified_durable_outputs()
    print("[protocol-extensions] program transcript mapping passed")
    print("[protocol-extensions] image-sequence overlay passed")
    print("[protocol-extensions] precomputed overlay compatibility passed")
    print("[protocol-extensions] dependency revision coverage passed")
    print("[protocol-extensions] verified durable outputs passed")


if __name__ == "__main__":
    main()
