"""Small regression checks for shared protocol extensions."""

import copy
import hashlib
import json
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


def check_broll_compiler_consistency():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for directory in (
            "input", "final", "review/03-b-roll", "work/b-roll",
            "work/cache/b-roll/normalized", "work/render",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        source = root / "input/source.mp4"
        source.write_bytes(b"source")
        (root / "review/03-b-roll/b-roll-summary.md").write_text(
            "# B-roll\n", encoding="utf-8"
        )
        for index in (1, 2):
            (root / f"work/cache/b-roll/normalized/broll-{index:03d}.mp4").write_bytes(
                f"overlay-{index}".encode()
            )

        timeline = {
            "schema_version": 1,
            "timeline_id": "main",
            "source_asset_id": "source",
            "fps": {"num": 30, "den": 1},
            "source_duration_s": 6.0,
            "program_duration_s": 6.0,
            "clips": [{
                "id": "clip-001",
                "source_range": {"start_s": 0.0, "end_s": 6.0},
                "program_range": {"start_s": 0.0, "end_s": 6.0},
                "speed": 1.0,
                "decision_ref": "source",
            }],
        }
        shots = []
        for index, (start, end) in enumerate(((1.0, 2.0), (3.0, 4.5)), 1):
            digest = str(index) * 64
            shots.append({
                "id": f"shot-{index:03d}",
                "status": "verified",
                "program_range": {"start_s": start, "end_s": end},
                "selected": {"candidate_id": f"asset-{index:03d}", "source_trim": {"start_s": 0.0, "end_s": end - start}},
                "candidates": [{"id": f"asset-{index:03d}", "media_type": "video", "sha256": digest}],
                "normalized": {
                    "path": f"cache/b-roll/normalized/broll-{index:03d}.mp4",
                    "sha256": digest,
                },
                "verification": {"status": "pass", "normalized_sha256": digest},
            })
        plan = {
            "schema_version": 1,
            "timeline_id": "main",
            "timebase": "program",
            "program_duration_s": 6.0,
            "dependencies": ["understanding"],
            "based_on": {"understanding": 1},
            "input_hashes": {"review_video_sha256": "f" * 64},
            "review_status": "approved",
            "decision": {"mode": "agent", "actor": "compiler-fixture", "rationale": "Both shots support the narration."},
            "review": {
                "status": "approved",
                "review_id": "123e4567-e89b-12d3-a456-426614174000",
                "mode": "agent",
                "actor": "compiler-fixture",
                "rationale": "Both shots support the narration.",
                "timestamp": "2026-07-24T00:00:00Z",
                "plan_sha256": "a" * 64,
                "candidate_manifest_sha256": "b" * 64,
                "review_video_sha256": "f" * 64,
                "decision_skipped_shot_ids": [],
                "selected_asset_sha256": ["1" * 64, "2" * 64],
                "decisions": [
                    {"id": "shot-001", "decision": "select", "candidate_id": "asset-001", "source_trim": {"start_s": 0.0, "end_s": 1.0}},
                    {"id": "shot-002", "decision": "select", "candidate_id": "asset-002", "source_trim": {"start_s": 0.0, "end_s": 1.5}},
                ],
            },
            "shots": shots,
        }
        effects = {
            "changes_timeline": False,
            "changes_geometry": False,
            "changes_video_pixels": False,
            "changes_audio": False,
            "adds_track": None,
        }
        source_stat = source.stat()
        project = {
            "schema_version": 1,
            "project_id": "broll-compiler-fixture",
            "source": {
                "path": "../input/source.mp4",
                "fingerprint": {
                    "size": source_stat.st_size,
                    "modified_ns": source_stat.st_mtime_ns,
                    "duration_s": 6.0,
                },
            },
            "active_sequence": "main",
            "sequences": {
                "main": {"operations": ["b-roll"], "timeline": "timeline.json"},
                "alternate": {"operations": []},
            },
            "operations": [
                {
                    "id": "understanding", "skill": "video-understand", "revision": 1,
                    "depends_on": [], "based_on": {}, "status": "verified", "outputs": [],
                    "target": {"sequence": "main", "scope": "evidence"}, "effects": effects,
                },
                {
                    "id": "cut", "skill": "video-cut", "revision": 2,
                    "depends_on": ["understanding"], "based_on": {"understanding": 1},
                    "status": "verified", "outputs": [],
                    "target": {"sequence": "main", "scope": "timeline"}, "effects": effects,
                    "render": {"kind": "output-constraint"},
                },
                {
                    "id": "b-roll", "skill": "video-add-b-roll", "revision": 1,
                    "depends_on": ["understanding"],
                    "based_on": {"understanding": 1},
                    "status": "approved", "plan": "b-roll/broll-plan.json",
                    "outputs": [shot["normalized"]["path"] for shot in shots],
                    "target": {"sequence": "main", "scope": "b-roll"},
                    "effects": {**effects, "changes_video_pixels": True, "adds_track": "b-roll"},
                    "check": {"status": "pending", "report": "../review/03-b-roll/b-roll-summary.md"},
                    "render": [
                        {"kind": "overlay", "asset": shot["normalized"]["path"],
                         "start_s": shot["program_range"]["start_s"],
                         "duration_s": shot["program_range"]["end_s"] - shot["program_range"]["start_s"]}
                        for shot in shots
                    ],
                },
                {
                    "id": "color-grade", "skill": "fixture-color-grade", "revision": 3,
                    "depends_on": ["understanding"], "based_on": {"understanding": 1},
                    "status": "verified", "outputs": [],
                    "target": {"sequence": "main", "scope": "color"}, "effects": effects,
                    "render": {"kind": "output-constraint"},
                },
            ],
            "render": {
                "plan": "render/render-plan.json",
                "output": "../final/final-video.mp4",
                "status": "draft",
            },
            "reviews": [],
        }

        def compile_values(current_plan, current_project, current_timeline):
            projectlib.write_json(root / "work/timeline.json", current_timeline)
            projectlib.write_json(root / "work/b-roll/broll-plan.json", current_plan)
            return projectlib.build_render_plan(current_project, root)

        compiled = compile_values(plan, project, timeline)["contributions"]
        assert [item["operation"] for item in compiled] == ["b-roll", "b-roll"]
        assert [item["start_s"] for item in compiled] == [1.0, 3.0]
        assert [item["duration_s"] for item in compiled] == [1.0, 1.5]
        assert [item["asset"] for item in compiled] == [
            "../cache/b-roll/normalized/broll-001.mp4",
            "../cache/b-roll/normalized/broll-002.mp4",
        ]

        def binding(relative, content):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return {"path": relative, "sha256": hashlib.sha256(content).hexdigest()}

        contact = binding("review/03-b-roll/contact-sheet.jpg", b"contact")
        boundary = binding("review/03-b-roll/boundary-reel.mp4", b"boundary")
        summary = binding("review/03-b-roll/b-roll-summary.md", b"summary")
        final_video = binding("final/final-video.mp4", b"final")
        stills = []
        for shot in shots:
            shot_stills = {}
            for position in ("first", "middle", "last"):
                item = binding(
                    f"review/03-b-roll/stills/{shot['id']}-{position}.png",
                    f"{shot['id']}-{position}".encode(),
                )
                shot_stills[position] = item
                stills.append({"shot_id": shot["id"], "position": position, **item})
            shot["verification"].update({
                "stills": shot_stills, "contact_sheet": contact,
                "boundary_reel": boundary, "report": summary,
            })

        receipt_path = root / "work/b-roll/b-roll-visual-review.json"
        report_path = root / "review/03-b-roll/b-roll-visual-review.md"
        report_path.write_bytes(b"completed report")
        completed_plan = copy.deepcopy(plan)
        plan_payload = json.dumps(
            completed_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        receipt = {
            "schema_version": 1,
            "status": "completed",
            "review_id": plan["review"]["review_id"],
            "plan_sha256": hashlib.sha256(plan_payload.encode("utf-8")).hexdigest(),
            "mode": "agent", "actor": "compiler-fixture",
            "rationale": "All final visual evidence passed inspection.",
            "timestamp": "2026-07-24T01:00:00Z",
            "checks": {
                "semantic_fit": True, "unwanted_logos_or_text": True,
                "jump_cuts": True, "entry_exit_boundaries": True,
                "grade_match": True,
            },
            "artifacts": {
                "stills": stills, "contact_sheet": contact, "boundary_reel": boundary,
                "machine_summary": summary, "final_video": final_video,
            },
        }
        projectlib.write_json(receipt_path, receipt)
        completed_plan["visual_review"] = {
            **{key: receipt[key] for key in (
                "status", "review_id", "plan_sha256", "mode", "actor",
                "rationale", "timestamp", "checks",
            )},
            "receipt": {
                "path": "work/b-roll/b-roll-visual-review.json",
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            },
            "report": {
                "path": "review/03-b-roll/b-roll-visual-review.md",
                "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            },
        }
        completed_project = copy.deepcopy(project)
        completed_operation = completed_project["operations"][2]
        completed_operation["status"] = "verified"
        completed_operation["check"] = {
            "status": "pass",
            "report": "../review/03-b-roll/b-roll-visual-review.md",
        }
        completed_compiled = compile_values(completed_plan, completed_project, timeline)["contributions"]
        assert completed_operation["revision"] == project["operations"][2]["revision"]
        assert completed_operation["render"] == project["operations"][2]["render"]
        assert completed_compiled == compiled

        def completed_failure(label, current_plan, current_receipt, expected):
            projectlib.write_json(receipt_path, current_receipt)
            current_plan["visual_review"]["receipt"]["sha256"] = hashlib.sha256(
                receipt_path.read_bytes()
            ).hexdigest()
            try:
                compile_values(current_plan, completed_project, timeline)
            except ValueError as error:
                assert expected in str(error), f"{label}: {error}"
            else:
                raise AssertionError(f"{label}: mismatch was accepted")

        human_plan, human_receipt = copy.deepcopy(completed_plan), copy.deepcopy(receipt)
        human_plan["visual_review"]["mode"] = human_receipt["mode"] = "human"
        completed_failure("forged human", human_plan, human_receipt, "explicit_user_action")
        blank_plan, blank_receipt = copy.deepcopy(completed_plan), copy.deepcopy(receipt)
        blank_plan["visual_review"]["actor"] = blank_receipt["actor"] = " "
        completed_failure("blank actor", blank_plan, blank_receipt, "actor is required")
        time_plan, time_receipt = copy.deepcopy(completed_plan), copy.deepcopy(receipt)
        time_plan["visual_review"]["timestamp"] = time_receipt["timestamp"] = "2026-07-24T01:00:00"
        completed_failure("invalid timestamp", time_plan, time_receipt, "timestamp is invalid")
        mismatch_receipt = copy.deepcopy(receipt)
        mismatch_receipt["rationale"] = "Different rationale."
        completed_failure(
            "receipt mismatch", copy.deepcopy(completed_plan), mismatch_receipt,
            "receipt authority does not match",
        )
        schema_receipt = copy.deepcopy(receipt)
        schema_receipt["schema_version"] = 2
        completed_failure(
            "receipt schema", copy.deepcopy(completed_plan), schema_receipt,
            "receipt schema_version must be 1",
        )
        status_receipt = copy.deepcopy(receipt)
        status_receipt["status"] = "draft"
        completed_failure(
            "receipt status", copy.deepcopy(completed_plan), status_receipt,
            "receipt authority does not match",
        )
        completed_failure(
            "non-object receipt", copy.deepcopy(completed_plan), [],
            "receipt must be an object",
        )

        def malformed_still_path(value, expected):
            current_plan, current_receipt = copy.deepcopy(completed_plan), copy.deepcopy(receipt)
            current_plan["shots"][0]["verification"]["stills"]["first"]["path"] = value
            current_receipt["artifacts"]["stills"][0]["path"] = value
            subject = {key: item for key, item in current_plan.items() if key != "visual_review"}
            payload = json.dumps(subject, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            current_plan["visual_review"]["plan_sha256"] = current_receipt["plan_sha256"] = digest
            completed_failure(f"still path {value!r}", current_plan, current_receipt, expected)

        malformed_still_path(None, "binding is invalid")
        malformed_still_path("review/03-b-roll/stills/bad\0.png", "path is invalid")
        projectlib.write_json(receipt_path, receipt)
        completed_plan["visual_review"]["receipt"]["sha256"] = hashlib.sha256(
            receipt_path.read_bytes()
        ).hexdigest()
        (root / final_video["path"]).write_bytes(b"stale final")
        try:
            compile_values(completed_plan, completed_project, timeline)
        except ValueError as error:
            assert "final video SHA-256 is stale" in str(error)
        else:
            raise AssertionError("stale final artifact was accepted")
        (root / final_video["path"]).write_bytes(b"final")
        report_path.write_bytes(b"tampered report")
        try:
            compile_values(completed_plan, completed_project, timeline)
        except ValueError as error:
            assert "visual review report SHA-256 is stale" in str(error)
        else:
            raise AssertionError("compiler accepted a stale completed visual review report")
        report_path.write_bytes(b"completed report")

        extra_render = copy.deepcopy(project["operations"][2]["render"])
        extra_render.append(copy.deepcopy(extra_render[0]))
        mutations = [
            ("non-object plan", "plan", (), [], "plan must be an object"),
            ("plan schema", "plan", ("schema_version",), 2, "plan schema_version must be 1"),
            ("boolean plan schema", "plan", ("schema_version",), True, "plan schema_version must be integer 1"),
            ("float plan schema", "plan", ("schema_version",), 1.0, "plan schema_version must be integer 1"),
            ("contribution asset", "project", ("operations", 2, "render", 0, "asset"), "cache/b-roll/normalized/broll-002.mp4", "contribution 1 asset"),
            ("contribution start", "project", ("operations", 2, "render", 0, "start_s"), 0.5, "contribution 1 start_s"),
            ("contribution duration", "project", ("operations", 2, "render", 0, "duration_s"), 2.0, "contribution 1 duration_s"),
            ("contribution kind", "project", ("operations", 2, "render", 0, "kind"), "precomputed-asset", "contribution 1 kind"),
            ("contribution extra field", "project", ("operations", 2, "render", 0, "blend"), "normal", "contribution 1 fields must be exactly"),
            ("contribution operation override", "project", ("operations", 2, "render", 0, "operation"), "forged", "contribution 1 fields must be exactly"),
            ("extra contribution", "project", ("operations", 2, "render"), extra_render, "overlay contribution count"),
            ("review status marker", "plan", ("review_status",), "draft", "review_status must be approved"),
            ("review receipt status", "plan", ("review", "status"), "draft", "review receipt must be approved"),
            ("missing review receipt", "plan", ("review",), None, "review receipt must be approved"),
            ("shot lifecycle", "plan", ("shots", 0, "status"), "normalized", "shot shot-001 must be verified or skipped"),
            ("shot verification", "plan", ("shots", 0, "verification", "status"), "fail", "shot shot-001 verification must pass"),
            ("missing verification hash", "plan", ("shots", 0, "verification"), {"status": "pass"}, "shot shot-001 verification normalized_sha256 is required"),
            ("invalid verification hash", "plan", ("shots", 0, "verification", "normalized_sha256"), "bad", "shot shot-001 verification normalized_sha256 is invalid"),
            ("mismatched verification hash", "plan", ("shots", 0, "verification", "normalized_sha256"), "0" * 64, "shot shot-001 verification normalized_sha256 does not match normalized SHA-256"),
            ("timeline id", "plan", ("timeline_id",), "other", "timeline_id does not match timeline"),
            ("missing plan timeline id", "plan", ("timeline_id",), "", "plan timeline_id must be nonblank"),
            ("program duration", "plan", ("program_duration_s",), 5.0, "program_duration_s does not match timeline"),
            ("finite program duration", "plan", ("program_duration_s",), float("inf"), "program_duration_s must be finite"),
            ("operation dependency order", "operation-dependencies", (), ["cut", "understanding"], "operation dependencies do not match plan"),
            ("plan dependency order", "plan", ("dependencies",), ["cut", "understanding"], "plan dependencies do not match operation"),
            ("operation based_on integer", "project", ("operations", 2, "based_on", "understanding"), 1.0, "operation based_on revisions must be positive integers"),
            ("plan based_on integer", "plan", ("based_on", "understanding"), 1.0, "plan based_on revisions must be positive integers"),
            ("operation based_on boolean revision", "project", ("operations", 2, "based_on", "understanding"), True, "operation based_on revisions must be positive integers"),
            ("plan based_on boolean revision", "plan", ("based_on", "understanding"), True, "plan based_on revisions must be positive integers"),
            ("plan based_on parity", "plan", ("based_on",), {}, "operation based_on does not match plan"),
            ("operation target sequence", "project", ("operations", 2, "target", "sequence"), "alternate", "operation target sequence does not match active_sequence"),
            ("operation target scope", "project", ("operations", 2, "target", "scope"), "overlay", "operation target scope must be b-roll"),
            ("unsafe normalized path", "plan", ("shots", 0, "normalized", "path"), "../escape.mp4", "shot shot-001 normalized path"),
            ("normalized SHA", "plan", ("shots", 0, "normalized", "sha256"), "bad", "shot shot-001 normalized SHA-256"),
            ("selected overlap", "plan", ("shots", 1, "program_range"), {"start_s": 1.5, "end_s": 3.5}, "selected shot ranges overlap"),
            ("selected order", "plan", ("shots",), list(reversed(copy.deepcopy(shots))), "selected shots must be chronological"),
            ("duplicate shot id", "plan", ("shots", 1, "id"), "shot-001", "duplicate shot id: shot-001"),
            ("skipped contribution", "plan", ("shots", 0, "status"), "skipped", "overlay contribution count"),
            ("malformed shots", "plan", ("shots",), {}, "shots must be a list"),
            ("malformed contribution", "project", ("operations", 2, "render", 0), [], "contribution 1 must be an object"),
            ("duplicate dependencies", "both-dependencies", (), ["understanding", "cut", "cut"], "dependencies must be unique and canonically ordered"),
            ("reordered dependencies", "both-dependencies", (), ["cut", "understanding"], "dependencies must be unique and canonically ordered"),
        ]

        failures = []
        for label, target_name, path, replacement, expected in mutations:
            current_plan = copy.deepcopy(plan)
            current_project = copy.deepcopy(project)
            current_timeline = copy.deepcopy(timeline)
            if target_name == "both-dependencies":
                current_plan["dependencies"] = replacement
                current_project["operations"][2]["depends_on"] = replacement
                based_on = {item: {"understanding": 1, "cut": 2}[item] for item in replacement if isinstance(item, str)}
                current_plan["based_on"] = based_on
                current_project["operations"][2]["based_on"] = based_on
            elif target_name == "operation-dependencies":
                current_project["operations"][2]["depends_on"] = replacement
                current_project["operations"][2]["based_on"] = {"understanding": 1, "cut": 2}
            elif not path:
                current_plan = replacement
            else:
                target = {"plan": current_plan, "project": current_project, "timeline": current_timeline}[target_name]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
            try:
                compile_values(current_plan, current_project, current_timeline)
            except ValueError as error:
                message = str(error)
                if "b-roll B-roll plan mismatch:" not in message or expected not in message:
                    failures.append(f"{label}: {message}")
            else:
                failures.append(f"{label}: mismatch was accepted")

        dependency_probes = [
            ("missing understanding", ["b-roll"], ["cut"], {"cut": 2}),
            ("missing active cut", ["cut", "b-roll"], ["understanding"], {"understanding": 1}),
            ("missing active color-grade", ["color-grade", "b-roll"], ["understanding"], {"understanding": 1}),
        ]
        for label, active_operations, dependencies, based_on in dependency_probes:
            current_plan = copy.deepcopy(plan)
            current_project = copy.deepcopy(project)
            current_project["sequences"]["main"]["operations"] = active_operations
            current_plan["dependencies"] = dependencies
            current_plan["based_on"] = based_on
            current_project["operations"][2]["depends_on"] = dependencies
            current_project["operations"][2]["based_on"] = based_on
            try:
                compile_values(current_plan, current_project, timeline)
            except ValueError as error:
                if "operation dependencies do not match active upstream operations" not in str(error):
                    failures.append(f"{label}: {error}")
            else:
                failures.append(f"{label}: mismatch was accepted")

        direct_probes = []
        missing_timeline_id = copy.deepcopy(timeline)
        missing_timeline_id["timeline_id"] = ""
        direct_probes.append(("missing timeline timeline_id", plan, project["operations"][2], missing_timeline_id, "timeline timeline_id must be nonblank"))
        boolean_revision = copy.deepcopy(project["operations"][2])
        boolean_revision["revision"] = True
        direct_probes.append(("boolean operation revision", plan, boolean_revision, timeline, "operation revision must be a positive integer"))
        missing_based_on_plan = copy.deepcopy(plan)
        missing_based_on_operation = copy.deepcopy(project["operations"][2])
        missing_based_on_plan["based_on"] = {}
        missing_based_on_operation["based_on"] = {}
        direct_probes.append(("incomplete based_on mappings", missing_based_on_plan, missing_based_on_operation, timeline, "based_on keys must exactly match dependencies"))
        malformed_dependencies_plan = copy.deepcopy(plan)
        malformed_dependencies_project = copy.deepcopy(project)
        malformed_dependencies_plan["dependencies"] = [["understanding"]]
        malformed_dependencies_project["operations"][2]["depends_on"] = [["understanding"]]
        try:
            compile_values(malformed_dependencies_plan, malformed_dependencies_project, timeline)
        except ValueError as error:
            if "b-roll dependency id must be a nonblank string" not in str(error):
                failures.append(f"malformed build dependencies: {error}")
        except Exception as error:
            failures.append(f"malformed build dependencies: {type(error).__name__}: {error}")
        else:
            failures.append("malformed build dependencies: mismatch was accepted")

        for label, current_plan, operation, current_timeline, expected in direct_probes:
            direct_errors = []
            try:
                projectlib._validate_broll_plan(
                    current_plan, operation, operation["render"], current_timeline,
                    direct_errors,
                )
            except TypeError as error:
                failures.append(f"{label}: {error}")
            else:
                if not any(expected in error for error in direct_errors):
                    failures.append(f"{label}: {direct_errors}")

        alternate = copy.deepcopy(project)
        alternate["active_sequence"] = "alternate"
        alternate["sequences"]["main"]["operations"] = []
        alternate["sequences"]["alternate"] = {
            "operations": ["b-roll"], "timeline": "timeline.json",
        }
        alternate["operations"][2]["target"]["sequence"] = "alternate"
        try:
            alternate_compiled = compile_values(plan, alternate, timeline)["contributions"]
        except ValueError as error:
            failures.append(f"alternate active sequence: {error}")
        else:
            if [item["operation"] for item in alternate_compiled] != ["b-roll", "b-roll"]:
                failures.append(f"alternate active sequence: {alternate_compiled}")

        if failures:
            raise AssertionError("B-roll compiler review regressions:\n- " + "\n- ".join(failures))


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
    check_broll_compiler_consistency()
    check_dependency_revision_coverage()
    check_verified_durable_outputs()
    print("[protocol-extensions] program transcript mapping passed")
    print("[protocol-extensions] image-sequence overlay passed")
    print("[protocol-extensions] precomputed overlay compatibility passed")
    print("[protocol-extensions] B-roll compiler consistency passed")
    print("[protocol-extensions] dependency revision coverage passed")
    print("[protocol-extensions] verified durable outputs passed")


if __name__ == "__main__":
    main()
