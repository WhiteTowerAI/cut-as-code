"""Verify normalized B-roll and publish compact review evidence."""

import copy
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib

import broll_plan
import normalize_broll


OWNED_ARTIFACTS = (Path("stills"), Path("contact-sheet.jpg"), Path("boundary-reel.mp4"),
                   Path("b-roll-summary.md"))


def _inside(path, parent, label):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside {parent}") from exc
    return path


def _run(command, message):
    try:
        return subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(message) from exc


def _load_inputs(plan_path, timeline_path, root):
    plan_path, timeline_path = Path(plan_path).resolve(), Path(timeline_path).resolve()
    if plan_path != (root / "work/b-roll/broll-plan.json").resolve():
        raise ValueError("plan_path must be canonical work/b-roll/broll-plan.json")
    if timeline_path != (root / "work/timeline.json").resolve():
        raise ValueError("timeline_path must be canonical work/timeline.json")
    try:
        return (
            projectlib.load_json(plan_path), projectlib.load_json(timeline_path),
            projectlib.load_json(root / "work/understand/transcript.json"),
            projectlib.load_json(root / "work/project.json"),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("canonical project inputs are missing or invalid") from exc


def _grade_hashes(plan, project, root):
    if "color-grade" not in broll_plan.active_dependencies(project):
        return {}
    grade_path = root / "work/color-grade/grade-plan.json"
    try:
        grade = projectlib.load_json(grade_path)
        selected = Path(grade["selected_lut"])
    except (OSError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("grade plan is invalid") from exc
    lut = (selected if selected.is_absolute() else grade_path.parent / selected).resolve()
    _, hashes = normalize_broll._grade(lut, root)
    for key, digest in hashes.items():
        if plan.get("input_hashes", {}).get(key) != digest:
            raise ValueError(f"{key} is stale")
    return hashes


def _selected_shots(plan, timeline, root, grade_hashes):
    selected = []
    normalized_root = _inside(root / "work/cache/b-roll/normalized", root, "normalized directory")
    for index, shot in enumerate(plan["shots"], 1):
        status = shot.get("status")
        if status == "skipped":
            continue
        if status not in ("normalized", "verified"):
            raise ValueError("verify_plan requires normalized, verified, or skipped shots")
        choice = shot.get("selected", {})
        candidate_ids = broll_plan.selected_candidate_ids(choice)
        candidates = [
            next((item for item in shot.get("candidates", [])
                  if isinstance(item, dict) and item.get("id") == candidate_id), None)
            for candidate_id in candidate_ids
        ]
        if not candidate_ids or any(candidate is None for candidate in candidates):
            raise ValueError("selected candidate does not belong to shot")
        output = _inside(normalized_root / f"broll-{index:03d}.mp4", normalized_root, "normalized path")
        try:
            normalize_broll._validate_normalized(
                shot.get("normalized"), candidates, shot, timeline, output, root, grade_hashes
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("normalized media decode failed") from exc
        selected.append((index, shot, candidates, output))
    return selected


def _review_video(plan, timeline, root, video_path):
    video = _inside(video_path, root, "video_path")
    if not video.is_file():
        raise ValueError("review video is missing")
    if broll_plan.sha256_file(video) != plan.get("input_hashes", {}).get("review_video_sha256"):
        raise ValueError("review video SHA-256 is stale")
    probe = normalize_broll._probe(video)
    width, height, num, den = normalize_broll._timeline_spec(timeline)
    if (probe["width"], probe["height"]) != (width, height):
        raise ValueError("review video dimensions do not match timeline")
    if Fraction(probe["fps"]["num"], probe["fps"]["den"]) != Fraction(num, den):
        raise ValueError("review video fps does not match timeline")
    duration = normalize_broll._number(timeline.get("program_duration_s"), "timeline program_duration_s")
    if abs(probe["duration_s"] - duration) > den / num + 1e-6:
        raise ValueError("review video duration does not match timeline")
    _run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:v:0", "-f", "null", "-"],
         "review video decode failed")
    return video


def _slug(value):
    return (re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or "shot")[:40]


def _extract_stills(selected, timeline, stage):
    width, height, num, den = normalize_broll._timeline_spec(timeline)
    still_dir = stage / "stills"
    still_dir.mkdir(parents=True)
    records = []
    for index, shot, _, video in selected:
        duration = normalize_broll._shot_duration(shot, timeline)
        actual_duration = shot["normalized"]["probe"]["duration_s"]
        times = {"first": 0.0, "middle": duration / 2,
                 "last": max(0, min(duration, actual_duration) - den / num)}
        paths = {}
        for label, time_s in times.items():
            path = still_dir / f"{index:03d}-{_slug(shot.get('id'))}-{label}.png"
            _run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                "-ss", f"{time_s:.9f}", "-frames:v", "1", str(path),
            ], "normalized still decode failed")
            try:
                with Image.open(path) as image:
                    image.load()
                    if image.format != "PNG" or image.size != (width, height):
                        raise ValueError("normalized still is invalid")
            except (OSError, ValueError) as exc:
                raise ValueError("normalized still is invalid") from exc
            paths[label] = path
        records.append((index, shot, times, paths))
    return records


def _contact_sheet(records, timeline, path):
    width, height, _, _ = normalize_broll._timeline_spec(timeline)
    font_size = max(12, min(32, height // 20))
    margin, gap, header, labels = 12, 8, font_size + 10, font_size + 6
    row_height = header + labels + height + margin
    canvas = Image.new("RGB", (margin * 2 + width * 3 + gap * 2, margin + row_height * len(records)), "#171717")
    draw, font = ImageDraw.Draw(canvas), ImageFont.load_default(size=font_size)
    for row, (_, shot, times, paths) in enumerate(records):
        top = margin + row * row_height
        draw.text((margin, top), f"{shot.get('id')}  {shot['program_range']['start_s']:.3f}s-{shot['program_range']['end_s']:.3f}s", fill="white", font=font)
        for column, label in enumerate(("first", "middle", "last")):
            left = margin + column * (width + gap)
            draw.text((left, top + header), f"{label}  +{times[label]:.3f}s", fill="#d7d7d7", font=font)
            with Image.open(paths[label]) as still:
                canvas.paste(still.convert("RGB"), (left, top + header + labels))
    canvas.save(path, "JPEG", quality=90, optimize=False, progressive=False)
    with Image.open(path) as image:
        image.load()
        if image.format != "JPEG":
            raise ValueError("contact sheet is invalid")


def _boundary_reel(selected, timeline, base_video, path):
    total = normalize_broll._number(timeline.get("program_duration_s"), "timeline program_duration_s")
    width, height, num, den = normalize_broll._timeline_spec(timeline)
    frame = den / num

    def snap_to_frame(value):
        return min(total, max(0.0, round(value / frame) * frame))

    command = ["ffmpeg", "-y", "-loglevel", "error"]
    filters, outputs, expected = [], [], 0.0
    for _, shot, _, overlay in selected:
        shot_start = float(shot["program_range"]["start_s"])
        shot_end = float(shot["program_range"]["end_s"])
        for boundary in (shot_start, shot_end):
            window_start = snap_to_frame(max(0.0, boundary - 0.5))
            window_end = snap_to_frame(min(total, boundary + 0.5))
            overlap_start, overlap_end = max(window_start, shot_start), min(window_end, shot_end)
            command.extend(["-i", str(base_video), "-i", str(overlay)])
            input_index = len(outputs) * 2
            base_stream, overlay_stream = input_index, input_index + 1
            segment = len(outputs)
            offset, overlay_offset = overlap_start - window_start, overlap_start - shot_start
            filters.extend([
                f"[{base_stream}:v:0]trim=start={window_start:.9f}:end={window_end:.9f},setpts=PTS-STARTPTS[base{segment}]",
                f"[{overlay_stream}:v:0]trim=start={overlay_offset:.9f}:duration={overlap_end - overlap_start:.9f},setpts=PTS-STARTPTS+{offset:.9f}/TB[overlay{segment}]",
                f"[base{segment}][overlay{segment}]overlay=eof_action=pass:repeatlast=0:enable='between(t,{offset:.9f},{offset + overlap_end - overlap_start:.9f})'[segment{segment}]",
            ])
            outputs.append(f"[segment{segment}]")
            expected += window_end - window_start
    filters.append("".join(outputs) + f"concat=n={len(outputs)}:v=1:a=0,format=yuv420p[reel]")
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[reel]", "-an", "-sn", "-dn",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ])
    _run(command, "boundary reel render failed")
    probe = normalize_broll._probe(path)
    normalize_broll._check_probe(probe, width, height, num, den, expected)
    _run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
         "boundary reel decode failed")


def _relative(path, root):
    return Path(path).resolve().relative_to(root).as_posix()


def _hash_binding(path, published, root):
    return {"path": _relative(published, root), "sha256": broll_plan.sha256_file(path)}


def _verified_artifact(binding, root, label):
    if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
        raise ValueError(f"{label} artifact binding is invalid")
    digest = binding.get("sha256")
    if not broll_plan._is_sha256(digest):
        raise ValueError(f"{label} artifact SHA-256 is invalid")
    raw = Path(binding["path"])
    if raw.is_absolute():
        raise ValueError(f"{label} artifact path must be project-relative")
    path = _inside(root / raw, root, f"{label} artifact")
    if not path.is_file() or broll_plan.sha256_file(path) != digest:
        raise ValueError(f"{label} artifact SHA-256 is stale")
    return {"path": raw.as_posix(), "sha256": digest}


def _delivery_artifact(path, expected, root, label):
    raw = Path(path)
    resolved = _inside(raw if raw.is_absolute() else root / raw, root, label)
    if resolved != expected.resolve():
        raise ValueError(f"{label} must be {expected}")
    if not resolved.is_file():
        raise ValueError(f"{label} is missing")
    return {"path": _relative(resolved, root), "sha256": broll_plan.sha256_file(resolved)}


def _visual_review_artifacts(plan, root, final_video):
    stills, shared = [], {}
    selected = [shot for shot in plan["shots"] if shot.get("status") != "skipped"]
    if not selected:
        raise ValueError("visual review requires at least one selected B-roll shot")
    for shot in selected:
        verification = shot.get("verification")
        if shot.get("status") != "verified" or not isinstance(verification, dict) or verification.get("status") != "pass":
            raise ValueError("visual review requires verified B-roll shots")
        shot_stills = verification.get("stills")
        if not isinstance(shot_stills, dict) or set(shot_stills) != {"first", "middle", "last"}:
            raise ValueError("visual review requires first, middle, and last stills")
        for position in ("first", "middle", "last"):
            binding = _verified_artifact(shot_stills[position], root, f"{shot.get('id')} {position} still")
            stills.append({"shot_id": shot.get("id"), "position": position, **binding})
        for key in ("contact_sheet", "boundary_reel", "report"):
            binding = _verified_artifact(verification.get(key), root, key.replace("_", " "))
            if key in shared and binding != shared[key]:
                raise ValueError(f"verified shots disagree on {key.replace('_', ' ')}")
            shared[key] = binding
    return {
        "stills": stills,
        "contact_sheet": shared["contact_sheet"],
        "boundary_reel": shared["boundary_reel"],
        "machine_summary": shared["report"],
        "final_video": _delivery_artifact(
            final_video, root / "final/final-video.mp4", root, "final video"
        ),
    }


def _visual_review_report(receipt):
    labels = {
        "semantic_fit": "Semantic fit",
        "unwanted_logos_or_text": "Unwanted logos or text",
        "jump_cuts": "Jump cuts",
        "entry_exit_boundaries": "Entry and exit boundaries",
        "grade_match": "Grade match",
        "speaker_layout_fidelity": "Speaker layout fidelity",
        "speaker_legibility": "Speaker legibility",
        "broll_focal_clearance": "B-roll focal clearance",
    }
    lines = [
        "# B-roll visual review", "", "Visual review status: completed", "",
        f"- Mode: `{receipt['mode']}`", f"- Actor: `{receipt['actor']}`",
        f"- Timestamp: `{receipt['timestamp']}`",
        f"- Active review UUID: `{receipt['review_id']}`",
        f"- Reviewed plan SHA-256: `{receipt['plan_sha256']}`",
        f"- Rationale: {receipt['rationale']}", "", "## Visual checks", "",
    ]
    lines.extend(f"- [x] {labels[key]}: pass" for key in receipt["checks"])
    lines.extend(["", "## Bound artifacts", ""])
    artifacts = receipt["artifacts"]
    for still in artifacts["stills"]:
        lines.append(
            f"- {still['shot_id']} {still['position']} still: `{still['path']}` (`{still['sha256']}`)"
        )
    for key in ("contact_sheet", "boundary_reel", "machine_summary", "final_video"):
        binding = artifacts[key]
        lines.append(
            f"- {key.replace('_', ' ').title()}: `{binding['path']}` (`{binding['sha256']}`)"
        )
    return "\n".join(lines) + "\n"


def _publish_visual_review(parts, snapshots):
    try:
        for part, target in parts:
            os.replace(part, target)
    except BaseException:
        for _, target in parts:
            previous = snapshots[target]
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(previous)
        raise
    finally:
        for part, _ in parts:
            part.unlink(missing_ok=True)


def complete_visual_review(plan_path, project_root, review, final_video):
    """Bind an actual visual inspection to verified evidence and publish its receipt."""
    root, plan_path = Path(project_root).resolve(), Path(plan_path).resolve()
    if plan_path != (root / "work/b-roll/broll-plan.json").resolve():
        raise ValueError("plan_path must be canonical work/b-roll/broll-plan.json")
    if not isinstance(review, dict):
        raise ValueError("visual review must be an object")
    plan, timeline, transcript, project = _load_inputs(
        plan_path, root / "work/timeline.json", root
    )
    if "visual_review" in plan:
        raise ValueError("visual review is already completed")
    timeline = normalize_broll._timeline_with_media_geometry(timeline, root)
    errors = broll_plan.validate_plan(
        plan, timeline, transcript, project=project, project_root=root, verify_files=True
    )
    if errors:
        raise ValueError("invalid verified B-roll plan: " + "; ".join(errors))
    broll_plan._verified_overlays(plan)
    plan_sha256 = broll_plan.canonical_sha256(broll_plan.visual_review_subject(plan))
    if review.get("plan_sha256") != plan_sha256:
        raise ValueError("visual review plan SHA-256 does not match")
    active = plan.get("review")
    if not isinstance(active, dict) or review.get("review_id") != active.get("review_id"):
        raise ValueError("visual review UUID does not match active review")
    mode, actor, rationale = review.get("mode"), review.get("actor"), review.get("rationale")
    if mode not in ("human", "agent"):
        raise ValueError("visual review mode must be human or agent")
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("visual review actor is required")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("visual review rationale is required")
    if not broll_plan._valid_timestamp(review.get("timestamp")):
        raise ValueError("visual review timestamp is invalid")
    if mode == "human" and review.get("explicit_user_action") is not True:
        raise ValueError("human visual review requires explicit_user_action true")
    required_checks = broll_plan.visual_review_checks(plan)
    checks = review.get("checks")
    if (not isinstance(checks, dict) or set(checks) != set(required_checks)
            or any(checks[key] is not True for key in required_checks)):
        raise ValueError("all visual checks must be true booleans")
    artifacts = _visual_review_artifacts(plan, root, final_video)
    receipt = {
        "schema_version": 1, "status": "completed", "review_id": active["review_id"],
        "plan_sha256": plan_sha256, "mode": mode, "actor": actor.strip(),
        "rationale": rationale.strip(), "timestamp": review["timestamp"],
        "checks": {key: True for key in required_checks},
        "artifacts": artifacts,
    }
    if mode == "human":
        receipt["explicit_user_action"] = True
    receipt_path = root / "work/b-roll/b-roll-visual-review.json"
    report_path = root / "review/03-b-roll/b-roll-visual-review.md"
    receipt_part, report_part = Path(str(receipt_path) + ".part"), Path(str(report_path) + ".part")
    plan_part = Path(str(plan_path) + ".part")
    parts = ((receipt_part, receipt_path), (report_part, report_path), (plan_part, plan_path))
    snapshots = {target: target.read_bytes() if target.is_file() else None for _, target in parts}
    for part, target in parts:
        target.parent.mkdir(parents=True, exist_ok=True)
        part.unlink(missing_ok=True)
    try:
        projectlib.write_json(receipt_part, receipt)
        report_part.write_text(_visual_review_report(receipt), encoding="utf-8")
        result = copy.deepcopy(plan)
        result["visual_review"] = {
            "status": "completed", "review_id": receipt["review_id"],
            "plan_sha256": plan_sha256, "mode": mode, "actor": receipt["actor"],
            "rationale": receipt["rationale"], "timestamp": receipt["timestamp"],
            "checks": copy.deepcopy(receipt["checks"]),
            "receipt": _hash_binding(receipt_part, receipt_path, root),
            "report": _hash_binding(report_part, report_path, root),
        }
        if mode == "human":
            result["visual_review"]["explicit_user_action"] = True
        errors = broll_plan._visual_review_errors(result)
        if errors:
            raise ValueError("; ".join(errors))
        projectlib.write_json(plan_part, result)
        _publish_visual_review(parts, snapshots)
    except BaseException:
        for part, _ in parts:
            part.unlink(missing_ok=True)
        raise
    return result, {"receipt": receipt_path, "report": report_path}


def _summary(plan, selected, records, artifacts, root, stage, destination, path):
    review = plan["review"]
    recommendations = {}
    agent_binding = plan.get("speaker_inset", {}).get("agent_input", {})
    if isinstance(agent_binding, dict) and isinstance(agent_binding.get("path"), str):
        agent_path = root / "work" / agent_binding["path"]
        if (agent_path.is_file()
                and broll_plan.sha256_file(agent_path) == agent_binding.get("sha256")):
            agent_input = projectlib.load_json(agent_path)
            recommendations = {
                item.get("shot_id"): item.get("layout_recommendation", {})
                for item in agent_input.get("shots", []) if isinstance(item, dict)
            }
    lines = [
        "# B-roll verification summary", "", "Manual review status: pending.", "",
        f"- Timeline ID: `{plan.get('timeline_id')}`",
        f"- Timeline SHA-256: `{plan['input_hashes']['timeline_sha256']}`",
        f"- Review ID: `{review.get('review_id')}`",
        f"- Reviewed plan SHA-256: `{review.get('plan_sha256')}`",
        f"- Reviewed candidate manifest SHA-256: `{review.get('candidate_manifest_sha256')}`",
        f"- Review video SHA-256: `{plan['input_hashes']['review_video_sha256']}`", "",
    ]
    if not selected:
        lines.extend(["No B-roll shots were selected; all approved decisions are skips.", ""])
    for (_, shot, candidates, _), (_, _, times, stills) in zip(selected, records):
        normalized = shot["normalized"]
        source_records = normalized.get("source_segments")
        component_records = normalized.get("segments")
        chain = (
            "source-direct single-filtergraph"
            if isinstance(source_records, list) else
            "legacy component-based"
            if isinstance(component_records, list) else
            "legacy single-asset"
        )
        evidence = ", ".join(str(word.get("word", "")).strip() for word in shot["transcript_evidence"]["words"])
        lines.extend([
            f"## Shot `{str(shot.get('id')).replace('`', '')}`", "",
            f"- Program range: `{json.dumps(shot['program_range'], sort_keys=True)}`",
            f"- Source ranges: `{json.dumps(shot['source_ranges'], sort_keys=True)}`",
            f"- Transcript evidence: {evidence}",
            f"- Selection format: `{normalized.get('selection_format', 'legacy')}`",
            f"- Intermediate chain: `{chain}`",
            f"- Intermediate profile: `{json.dumps(normalized.get('intermediate_profile', 'legacy unrecorded'), sort_keys=True)}`",
            f"- Program duration: `{normalized.get('program_duration_s', 'legacy record')}s`",
            f"- Normalized SHA-256: `{normalized['sha256']}`",
            f"- Normalized probe: `{json.dumps(normalized.get('probe', {}), sort_keys=True)}`",
            f"- Grade plan SHA-256: `{normalized.get('grade_plan_sha256', 'not active')}`",
            f"- Selected LUT SHA-256: `{normalized.get('selected_lut_sha256', 'not active')}`",
        ])
        composition = normalized.get("composition")
        base = normalized.get("broll_base")
        if isinstance(composition, dict) and isinstance(base, dict):
            lines.extend([
                f"- Project primary preset: `{composition.get('project_primary_preset')}`",
                f"- Shot layout preset: `{composition.get('layout_preset')}`",
                f"- Layout recommendation rationale: {recommendations.get(shot.get('id'), {}).get('rationale', '')}",
                f"- Final composite SHA-256: `{normalized['sha256']}`",
                f"- B-roll base SHA-256: `{base.get('sha256')}`",
                f"- B-roll base profile: `{json.dumps(base.get('intermediate_profile', 'legacy unrecorded'), sort_keys=True)}`",
            ])
            lines.extend(
                f"- Composition {field}: `{value}`"
                for field, value in composition.items()
            )
        if isinstance(source_records, list):
            candidate_map = {candidate.get("id"): candidate for candidate in candidates}
            for index, source_record in enumerate(source_records, 1):
                candidate = candidate_map.get(source_record.get("candidate_id"), {})
                lines.extend([
                    f"- Source segment {index}: `{source_record.get('candidate_id')}`",
                    f"  - Selected source: `{candidate.get('cache_path')}` (`{candidate.get('sha256')}`)",
                    f"  - Source provenance: `{json.dumps(candidate.get('provenance', {}), sort_keys=True)}`",
                    f"  - Segment: `{json.dumps(source_record.get('segment', {}), sort_keys=True)}`",
                    f"  - Source duration: `{source_record.get('source_duration_s')}s`",
                    f"  - Effective duration: `{source_record.get('effective_duration_s')}s`",
                    f"  - Program duration: `{source_record.get('program_duration_s')}s`",
                    f"  - Playback rate: `{source_record.get('playback_rate')}x`",
                    f"  - Source SHA-256: `{source_record.get('source_sha256')}`",
                ])
        elif isinstance(component_records, list):
            lines.append(
                f"- Legacy concat SHA-256: `{normalized.get('concat_sha256')}`"
            )
            candidate_map = {candidate.get("id"): candidate for candidate in candidates}
            for index, component in enumerate(component_records, 1):
                candidate = candidate_map.get(component.get("candidate_id"), {})
                lines.extend([
                    f"- Segment {index}: `{component.get('candidate_id')}`",
                    f"  - Selected source: `{candidate.get('cache_path')}` (`{candidate.get('sha256')}`)",
                    f"  - Source provenance: `{json.dumps(candidate.get('provenance', {}), sort_keys=True)}`",
                    f"  - Segment: `{json.dumps(component.get('segment', {}), sort_keys=True)}`",
                    f"  - Source duration: `{component.get('source_duration_s')}s`",
                    f"  - Effective duration: `{component.get('effective_duration_s')}s`",
                    f"  - Program duration: `{component.get('program_duration_s')}s`",
                    f"  - Playback rate: `{component.get('playback_rate')}x`",
                    f"  - Normalized segment SHA-256: `{component.get('normalized_sha256')}`",
                ])
        else:
            candidate = candidates[0]
            lines.extend([
                f"- Selected source: `{candidate.get('cache_path')}` (`{candidate.get('sha256')}`)",
                f"- Source provenance: `{json.dumps(candidate.get('provenance', {}), sort_keys=True)}`",
                f"- Segment: `{json.dumps(normalized.get('segment', {}), sort_keys=True)}`",
                f"- Source duration: `{normalized.get('source_duration_s', 'legacy record')}s`",
                f"- Effective duration: `{normalized.get('effective_duration_s', 'legacy record')}s`",
            ])
        if "legacy_requested_source_range" in normalized:
            lines.append(f"- Legacy requested source range: `{json.dumps(normalized['legacy_requested_source_range'], sort_keys=True)}`")
        for label in ("first", "middle", "last"):
            published = destination / stills[label].relative_to(stage)
            lines.append(f"- {label.title()} (+{times[label]:.3f}s): `{_relative(published, root)}` (`{broll_plan.sha256_file(stills[label])}`)")
        lines.append("")
    lines.extend(["## Artifacts", ""])
    for label, artifact in artifacts.items():
        if artifact is not None:
            published = destination / artifact.relative_to(stage)
            lines.append(f"- {label.replace('_', ' ').title()}: `{_relative(published, root)}` (`{broll_plan.sha256_file(artifact)}`)")
    lines.extend([
        "", "## Manual checklist", "", "- [ ] Confirm semantic fit.",
        "- [ ] Check for unwanted logos/text.", "- [ ] Check for jump cuts.",
        "- [ ] Check entry and exit boundaries.", "- [ ] Confirm grade match.", "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _reparse_attributes(path):
    try:
        return getattr(Path(path).stat(follow_symlinks=False), "st_file_attributes", 0)
    except FileNotFoundError:
        return 0


def _is_link_or_junction(path):
    path = Path(path)
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction is not None and is_junction():
        return True
    return bool(_reparse_attributes(path) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _safe_scratch_path(path, parent, label):
    path, parent = Path(path).absolute(), Path(parent).absolute()
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside {parent}") from exc
    if _is_link_or_junction(path):
        raise ValueError(f"{label} must not be a link or reparse point")
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must resolve inside {parent.resolve()}") from exc
    return path


def _safe_scratch_tree(path, parent, label):
    path = _safe_scratch_path(path, parent, label)
    if not path.exists() or not path.is_dir():
        return path
    for child in path.iterdir():
        _safe_scratch_tree(child, parent, label)
    return path


def _remove(path):
    path = Path(path)
    if _is_link_or_junction(path):
        if path.is_symlink():
            path.unlink(missing_ok=True)
        else:
            path.rmdir()
        return
    if not path.exists():
        return
    if path.is_dir():
        if _is_link_or_junction(path):
            path.rmdir()
            return
        for child in list(path.iterdir()):
            _remove(child)
        if _is_link_or_junction(path):
            if path.is_symlink():
                path.unlink(missing_ok=True)
            else:
                path.rmdir()
        else:
            path.rmdir()
    else:
        path.unlink(missing_ok=True)


def _ignore_remove(path):
    try:
        _remove(path)
    except OSError:
        pass


def _transaction_dir(review_dir):
    return review_dir.parent / f".{review_dir.name}.check.transaction"


def _stage_dir(review_dir):
    return review_dir.parent / f".{review_dir.name}.check.part"


def _restore_backup(source, target):
    source = _safe_scratch_tree(source, source.parent, "transaction backup")
    part = target.parent / f".{target.name}.restore.part"
    _safe_scratch_tree(part, target.parent, "restore part")
    _ignore_remove(part)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        _safe_scratch_tree(source, source.parent, "transaction backup")
        shutil.copytree(source, part)
    else:
        _safe_scratch_path(source, source.parent, "transaction backup")
        shutil.copy2(source, part)
    if target.exists():
        _remove(target)
    os.replace(part, target)


def _finish_transaction(transaction):
    transaction = _safe_scratch_tree(transaction, transaction.parent, "transaction cleanup")
    marker = _safe_scratch_path(transaction / "marker.json", transaction, "transaction marker")
    errors = []
    for child in list(transaction.iterdir()):
        if child != marker:
            try:
                _safe_scratch_tree(child, transaction, "transaction cleanup")
                _remove(child)
            except Exception as exc:
                errors.append(f"{child.name}: {exc}")
    if errors:
        raise OSError("; ".join(errors))
    _safe_scratch_path(marker, transaction, "transaction marker").unlink()
    _safe_scratch_path(transaction, transaction.parent, "transaction cleanup").rmdir()


def _recover_transaction(review_dir, plan_path):
    transaction = _transaction_dir(review_dir)
    try:
        _safe_scratch_path(transaction, review_dir.parent, "transaction")
    except (OSError, ValueError) as exc:
        raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
    if not transaction.exists():
        return
    stage = _stage_dir(review_dir)
    marker_path, plan_part = transaction / "marker.json", plan_path.with_suffix(".part.json")
    try:
        _safe_scratch_tree(stage, review_dir.parent, "verification stage")
        _safe_scratch_path(marker_path, transaction, "transaction marker")
        _safe_scratch_path(plan_part, plan_path.parent, "plan part")
    except (OSError, ValueError) as exc:
        raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
    if not marker_path.is_file():
        try:
            _safe_scratch_tree(transaction, review_dir.parent, "transaction cleanup")
            _safe_scratch_tree(stage, review_dir.parent, "verification stage")
            _remove(stage)
            _remove(transaction)
        except (OSError, ValueError) as exc:
            raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
        _ignore_remove(plan_part)
        return
    try:
        marker = projectlib.load_json(marker_path)
        entries = marker["entries"]
        expected = [path.as_posix() for path in OWNED_ARTIFACTS]
        if (marker.get("schema_version") != 1
                or marker.get("phase") not in ("prepared", "artifacts-published")
                or not isinstance(marker.get("old_plan_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", marker["old_plan_sha256"])
                or not isinstance(marker.get("new_plan_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", marker["new_plan_sha256"])
                or not isinstance(marker.get("review_dir_existed"), bool)
                or not isinstance(entries, list)
                or [entry.get("path") for entry in entries if isinstance(entry, dict)] != expected
                or any(not isinstance(entry, dict) or not isinstance(entry.get("old_existed"), bool)
                       for entry in entries)):
            raise ValueError("transaction marker is invalid")
    except (OSError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
    old_dir = transaction / "old"
    try:
        _safe_scratch_tree(old_dir, transaction, "transaction backup directory")
        for entry in entries:
            _safe_scratch_tree(
                old_dir / Path(entry["path"]), old_dir, "transaction backup"
            )
    except (OSError, ValueError) as exc:
        raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
    identity_error = None
    try:
        current = broll_plan.sha256_file(plan_path)
    except OSError as exc:
        current, identity_error = None, f"canonical plan is unreadable: {exc}"
    same_plan = marker["old_plan_sha256"] == marker["new_plan_sha256"]
    committed = current == marker["new_plan_sha256"] and (
        not same_plan or marker["phase"] == "artifacts-published"
    )
    if committed:
        try:
            _safe_scratch_tree(stage, review_dir.parent, "verification stage")
            _remove(stage)
            _finish_transaction(transaction)
        except (OSError, ValueError) as exc:
            raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
        _ignore_remove(plan_part)
        return
    if current not in (marker["old_plan_sha256"], marker["new_plan_sha256"]):
        raise ValueError(
            "B-roll publication recovery failed: "
            + (identity_error or "canonical plan matches neither transaction identity")
        )

    errors = []
    for entry in entries:
        relative = Path(entry["path"])
        target, backup = review_dir / relative, old_dir / relative
        try:
            if entry["old_existed"]:
                if backup.exists():
                    _restore_backup(backup, target)
                elif not target.exists():
                    raise OSError("original and backup are both missing")
            elif target.exists():
                _remove(target)
        except Exception as exc:
            errors.append(f"{entry['path']}: {exc}")
    if errors:
        raise ValueError("B-roll publication recovery failed: " + "; ".join(errors))
    try:
        if not marker["review_dir_existed"] and review_dir.exists() and not any(review_dir.iterdir()):
            review_dir.rmdir()
        _safe_scratch_tree(stage, review_dir.parent, "verification stage")
        _remove(stage)
        _finish_transaction(transaction)
    except (OSError, ValueError) as exc:
        raise ValueError(f"B-roll publication recovery failed: {exc}") from exc
    _ignore_remove(plan_part)


def _commit(stage, review_dir, plan_path, result):
    transaction = _transaction_dir(review_dir)
    plan_part = plan_path.with_suffix(".part.json")
    review_existed = review_dir.exists()
    _recover_transaction(review_dir, plan_path)
    try:
        _safe_scratch_path(transaction, review_dir.parent, "transaction")
        _safe_scratch_tree(stage, review_dir.parent, "verification stage")
        _safe_scratch_path(plan_part, plan_path.parent, "plan part")
        old_plan_sha256 = broll_plan.sha256_file(plan_path)
        projectlib.write_json(plan_part, result)
        marker = {
            "schema_version": 1,
            "phase": "prepared",
            "old_plan_sha256": old_plan_sha256,
            "new_plan_sha256": broll_plan.sha256_file(plan_part),
            "review_dir_existed": review_existed,
            "entries": [{"path": relative.as_posix(), "old_existed": (review_dir / relative).exists()}
                        for relative in OWNED_ARTIFACTS],
        }
        transaction.mkdir(parents=True)
        marker_path, marker_part = transaction / "marker.json", transaction / "marker.part.json"
        _safe_scratch_path(marker_path, transaction, "transaction marker")
        _safe_scratch_path(marker_part, transaction, "transaction marker part")
        projectlib.write_json(marker_part, marker)
        _safe_scratch_path(marker_part, transaction, "transaction marker part")
        _safe_scratch_path(marker_path, transaction, "transaction marker")
        os.replace(marker_part, marker_path)
        review_dir.mkdir(parents=True, exist_ok=True)
        for entry in marker["entries"]:
            relative = Path(entry["path"])
            target, source, saved = review_dir / relative, stage / relative, transaction / "old" / relative
            _safe_scratch_tree(source, stage, "verification stage artifact")
            _safe_scratch_path(saved, transaction, "transaction backup")
            if target.exists():
                saved.parent.mkdir(parents=True, exist_ok=True)
                _safe_scratch_path(saved, transaction, "transaction backup")
                os.replace(target, saved)
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                _safe_scratch_tree(source, stage, "verification stage artifact")
                os.replace(source, target)
        marker["phase"] = "artifacts-published"
        projectlib.write_json(marker_part, marker)
        _safe_scratch_path(marker_part, transaction, "transaction marker part")
        _safe_scratch_path(marker_path, transaction, "transaction marker")
        os.replace(marker_part, marker_path)
        _safe_scratch_path(plan_part, plan_path.parent, "plan part")
        os.replace(plan_part, plan_path)
    except BaseException as original:
        try:
            _recover_transaction(review_dir, plan_path)
        except Exception as recovery:
            raise recovery from original
        raise
    else:
        _recover_transaction(review_dir, plan_path)
    finally:
        if not transaction.exists():
            _ignore_remove(stage)
            _ignore_remove(plan_part)


def _write_coverage_summary(root, plan_path):
    plan = projectlib.load_json(plan_path)
    ranking_binding = plan.get("candidate_ranking")
    ranking_path = None
    ranking_sha256 = None
    shortlists = []
    if isinstance(ranking_binding, dict):
        ranking_path = root / "work" / ranking_binding["path"]
        ranking_sha256 = broll_plan.sha256_file(ranking_path)
        shortlists = ranking_binding["shortlists"]
    shortlisted_ids = {
        shortlist.get("shot_id") for shortlist in shortlists
        if shortlist.get("candidate_ids")
    }
    shots = plan.get("shots", [])
    summary = {
        "schema_version": 1,
        "timeline_id": plan.get("timeline_id"),
        "program_duration_s": plan.get("program_duration_s"),
        "plan_sha256": broll_plan.sha256_file(plan_path),
        "ranking_sha256": ranking_sha256,
        **broll_plan.coverage_summary(
            plan,
            planned=shots,
            shortlisted=[shot for shot in shots if shot.get("id") in shortlisted_ids],
            selected=[shot for shot in shots if shot.get("status") != "skipped"],
        ),
    }
    target = root / "work/b-roll/coverage-summary.json"
    part = target.with_suffix(".part.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    part.unlink(missing_ok=True)
    try:
        projectlib.write_json(part, summary)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)


def verify_plan(plan_path, timeline_path, project_root, video_path, *, review_dir=None):
    """Verify canonical normalized shots, publish review artifacts, and persist pass bindings."""
    root = Path(project_root).resolve()
    plan_path = Path(plan_path).resolve()
    if plan_path != (root / "work/b-roll/broll-plan.json").resolve():
        raise ValueError("plan_path must be canonical work/b-roll/broll-plan.json")
    review_root = _inside(root / "review", root, "review root")
    destination = _inside(review_dir or review_root / "03-b-roll", review_root, "review_dir")
    _recover_transaction(destination, plan_path)
    plan, timeline, transcript, project = _load_inputs(plan_path, timeline_path, root)
    timeline = normalize_broll._timeline_with_media_geometry(timeline, root)
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list):
        raise ValueError("plan shots must be a list")
    if plan.get("review_status") != "approved":
        raise ValueError("review_status must be approved")
    errors = broll_plan.validate_plan(
        plan, timeline, transcript, project=project, project_root=root, verify_files=True
    )
    if errors:
        raise ValueError("invalid B-roll plan: " + "; ".join(errors))
    grade_hashes = _grade_hashes(plan, project, root)
    selected = _selected_shots(plan, timeline, root, grade_hashes)
    video = _review_video(plan, timeline, root, video_path)
    stage = _stage_dir(destination)
    _safe_scratch_tree(stage, review_root, "verification stage")
    _remove(stage)
    stage.mkdir(parents=True)
    try:
        records = _extract_stills(selected, timeline, stage) if selected else []
        contact = stage / "contact-sheet.jpg" if selected else None
        reel = stage / "boundary-reel.mp4" if selected else None
        if contact:
            _contact_sheet(records, timeline, contact)
            _boundary_reel(selected, timeline, video, reel)
        final_stills = [destination / path.relative_to(stage) for _, _, _, paths in records for path in paths.values()]
        final_contact = destination / contact.name if contact else None
        final_reel = destination / reel.name if reel else None
        summary = stage / "b-roll-summary.md"
        final_summary = destination / summary.name
        _summary(plan, selected, records, {
            "contact_sheet": contact, "boundary_reel": reel,
        }, root, stage, destination, summary)
        result = copy.deepcopy(plan)
        result.pop("visual_review", None)
        for (index, _, _, _), (_, _, _, stills) in zip(selected, records):
            shot = result["shots"][index - 1]
            shot["status"] = "verified"
            shot["verification"] = {
                "status": "pass", "normalized_sha256": shot["normalized"]["sha256"],
                "stills": {label: _hash_binding(path, destination / path.relative_to(stage), root)
                           for label, path in stills.items()},
                "contact_sheet": _hash_binding(contact, final_contact, root),
                "boundary_reel": _hash_binding(reel, final_reel, root),
                "report": _hash_binding(summary, final_summary, root),
            }
            composition = shot["normalized"].get("composition")
            if isinstance(composition, dict):
                shot["verification"]["composition_sha256"] = broll_plan.canonical_sha256(
                    composition
                )
        errors = broll_plan.validate_plan(
            result, timeline, transcript, project=project, project_root=root, verify_files=True
        )
        if errors:
            raise ValueError("invalid verified B-roll plan: " + "; ".join(errors))
        _commit(stage, destination, plan_path, result)
        _write_coverage_summary(root, plan_path)
        return result, {
            "stills": final_stills, "contact_sheet": final_contact,
            "boundary_reel": final_reel, "summary": final_summary,
        }
    except BaseException:
        if not _transaction_dir(destination).exists():
            _ignore_remove(stage)
        raise
