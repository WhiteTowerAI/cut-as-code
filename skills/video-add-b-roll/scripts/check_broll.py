"""Verify normalized B-roll and publish compact review evidence."""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib

import broll_plan
import normalize_broll


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
        candidate = next((item for item in shot.get("candidates", [])
                          if item.get("id") == choice.get("candidate_id")), None)
        if candidate is None:
            raise ValueError("selected candidate does not belong to shot")
        output = _inside(normalized_root / f"broll-{index:03d}.mp4", normalized_root, "normalized path")
        try:
            normalize_broll._validate_normalized(
                shot.get("normalized"), candidate, shot, timeline, output, root, grade_hashes
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("normalized media decode failed") from exc
        selected.append((index, shot, candidate, output))
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
    command = ["ffmpeg", "-y", "-loglevel", "error"]
    filters, outputs, expected = [], [], 0.0
    for _, shot, _, overlay in selected:
        shot_start = float(shot["program_range"]["start_s"])
        shot_end = float(shot["program_range"]["end_s"])
        for boundary in (shot_start, shot_end):
            window_start, window_end = max(0.0, boundary - 0.5), min(total, boundary + 0.5)
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
    width, height, num, den = normalize_broll._timeline_spec(timeline)
    normalize_broll._check_probe(probe, width, height, num, den, expected)
    _run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
         "boundary reel decode failed")


def _relative(path, root):
    return Path(path).resolve().relative_to(root).as_posix()


def _hash_binding(path, published, root):
    return {"path": _relative(published, root), "sha256": broll_plan.sha256_file(path)}


def _summary(plan, selected, records, artifacts, root, stage, destination, path):
    review = plan["review"]
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
    for (_, shot, candidate, _), (_, _, times, stills) in zip(selected, records):
        normalized = shot["normalized"]
        evidence = ", ".join(str(word.get("word", "")).strip() for word in shot["transcript_evidence"]["words"])
        lines.extend([
            f"## Shot `{str(shot.get('id')).replace('`', '')}`", "",
            f"- Program range: `{json.dumps(shot['program_range'], sort_keys=True)}`",
            f"- Source ranges: `{json.dumps(shot['source_ranges'], sort_keys=True)}`",
            f"- Transcript evidence: {evidence}",
            f"- Selected source: `{candidate.get('cache_path')}` (`{candidate.get('sha256')}`)",
            f"- Source provenance: `{json.dumps(candidate.get('provenance', {}), sort_keys=True)}`",
            f"- Normalized SHA-256: `{normalized['sha256']}`",
            f"- Normalized probe: `{json.dumps(normalized.get('probe', {}), sort_keys=True)}`",
            f"- Grade plan SHA-256: `{normalized.get('grade_plan_sha256', 'not active')}`",
            f"- Selected LUT SHA-256: `{normalized.get('selected_lut_sha256', 'not active')}`",
        ])
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


def _remove(path):
    path = Path(path)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _ignore_remove(path):
    try:
        _remove(path)
    except OSError:
        pass


def _commit(stage, review_dir, plan_path, result):
    owned = [Path("stills"), Path("contact-sheet.jpg"), Path("boundary-reel.mp4"), Path("b-roll-summary.md")]
    backup = review_dir.parent / f".{review_dir.name}.check.backup"
    plan_part = plan_path.with_suffix(".part.json")
    review_existed = review_dir.exists()
    moved, published = [], []
    _remove(backup)
    backup.mkdir(parents=True)
    try:
        review_dir.mkdir(parents=True, exist_ok=True)
        for relative in owned:
            target, source, saved = review_dir / relative, stage / relative, backup / relative
            if target.exists():
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, saved)
                moved.append((saved, target))
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
                published.append(target)
        projectlib.write_json(plan_part, result)
        os.replace(plan_part, plan_path)
    except BaseException:
        plan_part.unlink(missing_ok=True)
        for target in reversed(published):
            _remove(target)
        for saved, target in reversed(moved):
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(saved, target)
        if not review_existed and review_dir.exists() and not any(review_dir.iterdir()):
            review_dir.rmdir()
        raise
    finally:
        _ignore_remove(stage)
        _ignore_remove(backup)


def verify_plan(plan_path, timeline_path, project_root, video_path, *, review_dir=None):
    """Verify canonical normalized shots, publish review artifacts, and persist pass bindings."""
    root = Path(project_root).resolve()
    plan_path = Path(plan_path).resolve()
    plan, timeline, transcript, project = _load_inputs(plan_path, timeline_path, root)
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
    review_root = _inside(root / "review", root, "review root")
    destination = _inside(review_dir or review_root / "03-b-roll", review_root, "review_dir")
    stage = destination.parent / f".{destination.name}.check.part"
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
        errors = broll_plan.validate_plan(
            result, timeline, transcript, project=project, project_root=root, verify_files=True
        )
        if errors:
            raise ValueError("invalid verified B-roll plan: " + "; ".join(errors))
        _commit(stage, destination, plan_path, result)
        return result, {
            "stills": final_stills, "contact_sheet": final_contact,
            "boundary_reel": final_reel, "summary": final_summary,
        }
    except BaseException:
        _remove(stage)
        raise
