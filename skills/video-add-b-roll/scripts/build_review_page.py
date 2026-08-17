"""Build an immutable local B-roll candidate review page."""

import argparse
import base64
import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from PIL import Image

import broll_plan
import projectlib
import speaker_inset

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "broll-review.html"
PAYLOAD_MARKER = "__BROLL_REVIEW_DATA__"
PAYLOAD_RE = re.compile(r"atob\('([^']+)'\)")


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _inside(root, target):
    try:
        Path(target).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _extract_frame(video, time_s, output):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{time_s:.6f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "2", str(output)], check=True, capture_output=True)


def _probe_video(video):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=index:format=duration", "-of", "json", str(video)], check=True, capture_output=True, text=True)
        payload = json.loads(result.stdout)
        duration = float(payload.get("format", {}).get("duration"))
    except (subprocess.CalledProcessError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as error:
        raise ValueError("review video duration is invalid") from error
    if not isinstance(payload.get("streams"), list) or not payload["streams"]:
        raise ValueError("review video has no video stream")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("review video duration is invalid")
    return duration


def _validate_jpeg(path):
    try:
        with Image.open(path) as image:
            if image.format != "JPEG" or image.width != 960 or image.height <= 0:
                raise ValueError("review frame is not a valid JPEG")
    except (OSError, ValueError) as error:
        raise ValueError("review frame is not a valid JPEG") from error


def _review_id(value):
    try:
        return str(uuid.UUID(str(value))) if value is not None else str(uuid.uuid4())
    except (ValueError, AttributeError) as error:
        raise ValueError("review_id must be a UUID") from error


def _word_context(words, program_range):
    program = broll_plan._range(program_range)
    if not program:
        raise ValueError("shot program range is invalid")
    context_start, context_end = max(0.0, program[0] - 2.0), program[1] + 2.0
    inside, context = [], []
    for word in words:
        mapped = broll_plan._range(word.get("program_range")) if isinstance(word, dict) else None
        if not mapped:
            continue
        if mapped[0] < context_end - broll_plan.RANGE_EPSILON and mapped[1] > context_start + broll_plan.RANGE_EPSILON:
            context.append(copy.deepcopy(word))
        if (mapped[0] >= program[0] - broll_plan.RANGE_EPSILON
                and mapped[1] <= program[1] + broll_plan.RANGE_EPSILON):
            inside.append(copy.deepcopy(word))
    return {"inside": inside, "context": context}


def _candidate_default(shot, candidate):
    program = broll_plan._range(shot.get("program_range"))
    duration = program[1] - program[0]
    review_default = shot.get("review_default")
    segments = review_default.get("segments") if isinstance(review_default, dict) else None
    if isinstance(segments, list):
        match = next((segment for segment in segments
                      if isinstance(segment, dict)
                      and segment.get("candidate_id") == candidate.get("id")), None)
        if match is not None:
            return copy.deepcopy(match)
    source_end = duration
    return {
        "candidate_id": candidate["id"],
        "source_range": {"start_s": 0.0, "end_s": source_end},
        "program_range": {"start_s": program[0], "end_s": program[1]},
        "playback_rate": 1.0,
    }


def _payload(plan, timeline, transcript, root, assets_dir):
    payload_shots = []
    pre_skipped_ids = []
    candidate_specs = []
    words = broll_plan._mapped_word_records(transcript, timeline)
    for shot_index, shot in enumerate(plan["shots"], 1):
        if shot["status"] == "skipped":
            pre_skipped_ids.append(shot["id"])
            continue
        frame = assets_dir / f"frame-{len(payload_shots) + 1:03d}.jpg"
        frame_duration = broll_plan.timeline_frame_duration(timeline)
        program = broll_plan._range(shot["program_range"])
        total_frames = round((program[1] - program[0]) / frame_duration)
        default_allocations = {}
        for count in range(1, min(3, total_frames) + 1):
            ranges = broll_plan.allocate_program_ranges(shot["program_range"], count, timeline)
            default_allocations[str(count)] = [
                round((item["end_s"] - item["start_s"]) / frame_duration)
                for item in ranges
            ]
        candidates = []
        for candidate_index, candidate in enumerate(shot["candidates"], 1):
            path = broll_plan._candidate_path(root, candidate["cache_path"])
            if path is None or not path.is_file():
                raise ValueError(f"{shot['id']} candidate path escapes project root")
            suffix = path.suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", path.suffix) else ""
            basename = f"candidate-{shot_index:03d}-{candidate_index:03d}{suffix}"
            candidate_specs.append((path, basename, candidate["sha256"]))
            item = {"id": candidate["id"], "media_type": candidate["media_type"], "path": f"{assets_dir.name}/{basename}", "sha256": candidate["sha256"], "provenance": candidate["provenance"]}
            if "ranking" in candidate:
                item["ranking"] = copy.deepcopy(candidate["ranking"])
            if candidate["media_type"] == "video":
                probe = candidate.get("probe")
                duration = broll_plan._positive_duration(probe.get("duration_s")) if isinstance(probe, dict) else None
                if duration is None:
                    raise ValueError(f"{shot['id']} candidate {candidate['id']} has no valid review duration")
                item["duration_s"] = duration
                item["source_bounds"] = {"start_s": 0.0, "end_s": duration}
                item["default_segment"] = _candidate_default(shot, candidate)
                item["default_segment"]["feasible"] = (
                    item["default_segment"]["source_range"]["end_s"] <= duration + broll_plan.RANGE_EPSILON
                )
            candidates.append(item)
        payload_shots.append({
            "id": shot["id"],
            "program_range": copy.deepcopy(shot["program_range"]),
            "original_program_range": copy.deepcopy(shot["program_range"]),
            "allowed_program_range": broll_plan.revision_program_bounds(plan, timeline, shot["id"]),
            "total_program_frames": total_frames,
            "frame_duration_s": frame_duration,
            "default_allocations": default_allocations,
            "source_ranges": copy.deepcopy(shot["source_ranges"]),
            "clip_ids": sorted({item.get("clip_id") for item in shot["source_ranges"] if isinstance(item, dict) and isinstance(item.get("clip_id"), str)}),
            "transcript": _word_context(words, shot["program_range"]),
            "transcript_evidence": copy.deepcopy(shot["transcript_evidence"]),
            "editorial_reason": shot["editorial_reason"],
            "visual_intent": shot["visual_intent"],
            "queries": copy.deepcopy(shot["queries"]),
            "review_default": copy.deepcopy(shot.get("review_default")),
            "source_frame": {"path": f"{assets_dir.name}/{frame.name}", "sha256": None},
            "candidates": candidates,
        })
    return payload_shots, candidate_specs, pre_skipped_ids


def _load_speaker_document(plan, root, name):
    binding = plan.get("speaker_inset", {}).get(name)
    if not isinstance(binding, dict):
        raise ValueError(f"speaker inset {name} binding is missing")
    path = root / "work" / str(binding.get("path", ""))
    if not _inside(root / "work", path) or not path.is_file():
        raise ValueError(f"speaker inset {name} path is invalid")
    if _hash(path) != binding.get("sha256"):
        raise ValueError(f"speaker inset {name} SHA-256 is stale")
    return projectlib.load_json(path)


def _composite_payload(plan, root, assets_dir):
    analysis = _load_speaker_document(plan, root, "analysis")
    agent_input = _load_speaker_document(plan, root, "agent_input")
    preview = _load_speaker_document(plan, root, "preview")
    clearance = _load_speaker_document(plan, root, "clearance")
    analysis_shots = {item["shot_id"]: item for item in analysis["shots"]}
    agent_shots = {item["shot_id"]: item for item in agent_input["shots"]}
    preview_shots = {item["shot_id"]: item for item in preview["shots"]}
    clearance_shots = {item["shot_id"]: item for item in clearance["shots"]}
    asset_specs = []
    asset_names = {}

    def freeze(binding, label):
        source = root / "work" / str(binding.get("path", ""))
        if not _inside(root / "work", source) or not source.is_file():
            raise ValueError(f"{label} path is invalid")
        digest = binding.get("sha256")
        if _hash(source) != digest:
            raise ValueError(f"{label} SHA-256 is stale")
        key = (str(source), digest)
        if key not in asset_names:
            suffix = source.suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", source.suffix) else ""
            basename = f"speaker-{len(asset_names) + 1:03d}{suffix}"
            asset_names[key] = basename
            asset_specs.append((source, basename, digest))
        return {
            "path": f"{assets_dir.name}/{asset_names[key]}",
            "sha256": digest,
        }

    payload_shots = []
    pre_skipped_ids = []
    for shot_index, shot in enumerate(plan["shots"], 1):
        if shot["status"] == "skipped":
            pre_skipped_ids.append(shot["id"])
            continue
        if shot["status"] != "composite_pending":
            raise ValueError("composite review requires composite_pending or skipped shots")
        shot_id = shot["id"]
        if any(shot_id not in values for values in (
                analysis_shots, agent_shots, preview_shots, clearance_shots)):
            raise ValueError(f"{shot_id} speaker artifacts are incomplete")
        candidates = {item["id"]: item for item in shot["candidates"]}
        selected_candidates = []
        for candidate_index, candidate_id in enumerate(
                broll_plan.selected_candidate_ids(shot["selected"]), 1):
            candidate = candidates[candidate_id]
            source = broll_plan._candidate_path(root, candidate["cache_path"])
            if source is None or not source.is_file() or _hash(source) != candidate["sha256"]:
                raise ValueError(f"{shot_id} selected candidate is stale")
            suffix = source.suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", source.suffix) else ""
            basename = f"locked-candidate-{shot_index:03d}-{candidate_index:03d}{suffix}"
            asset_specs.append((source, basename, candidate["sha256"]))
            selected_candidates.append({
                "id": candidate_id,
                "media_type": candidate["media_type"],
                "path": f"{assets_dir.name}/{basename}",
                "sha256": candidate["sha256"],
                "provenance": copy.deepcopy(candidate["provenance"]),
            })
        analysis_subshots = {
            item["id"]: item for item in analysis_shots[shot_id]["subshots"]
        }
        agent_subshots = {
            item["id"]: item for item in agent_shots[shot_id]["subshots"]
        }
        clearance_subshots = {
            item["id"]: item for item in clearance_shots[shot_id]["subshots"]
        }
        subshots = []
        for subshot_id, analysis_subshot in analysis_subshots.items():
            agent_subshot = agent_subshots[subshot_id]
            clearance_subshot = clearance_subshots[subshot_id]
            evidence_frames = []
            seen_frames = set()
            for point in analysis_subshot.get("evidence_points", []):
                for frame in point.get("frames", []):
                    key = (frame.get("path"), frame.get("sha256"))
                    if key in seen_frames:
                        continue
                    seen_frames.add(key)
                    frozen = freeze(frame, f"{subshot_id} evidence frame")
                    frozen["program_time_s"] = frame.get("program_time_s")
                    evidence_frames.append(frozen)
            subshots.append({
                "id": subshot_id,
                "program_range": copy.deepcopy(analysis_subshot["program_range"]),
                "speaker_status": agent_subshot["speaker_status"],
                "speaker_rationale": agent_subshot["rationale"],
                "keyframes": copy.deepcopy(agent_subshot["keyframes"]),
                "display_mode": clearance_subshot["display_mode"],
                "anchor": clearance_subshot.get("anchor"),
                "clearance_status": clearance_subshot["clearance_status"],
                "checked_anchors": copy.deepcopy(clearance_subshot["checked_anchors"]),
                "subject_legibility": clearance_subshot["subject_legibility"],
                "legibility_rationale": clearance_subshot.get("legibility_rationale"),
                "pixel_budget": copy.deepcopy(clearance_subshot.get("pixel_budget")),
                "legibility_checks": copy.deepcopy(
                    clearance_subshot.get("legibility_checks", [])
                ),
                "clearance_rationale": clearance_subshot["rationale"],
                "evidence_frames": evidence_frames,
            })
        preview_shot = preview_shots[shot_id]
        payload_shot = {
            "id": shot_id,
            "program_range": copy.deepcopy(shot["program_range"]),
            "locked_selection": copy.deepcopy(shot["selected"]),
            "layout_recommendation": copy.deepcopy(
                agent_shots[shot_id]["layout_recommendation"]
            ),
            "selected_candidates": selected_candidates,
            "base_broll": freeze(preview_shot["base_broll"], f"{shot_id} base B-roll"),
            "preview": freeze(preview_shot["preview"], f"{shot_id} contextual preview"),
            "anchor_previews": {
                anchor: freeze(binding, f"{shot_id} {anchor} preview")
                for anchor, binding in preview_shot["anchor_previews"].items()
            },
            "continuity": copy.deepcopy(clearance_shots[shot_id]["continuity"]),
            "subshots": subshots,
        }
        if isinstance(preview_shot.get("alternate_preview"), dict):
            alternate = preview_shot["alternate_preview"]
            payload_shot["alternate_preview"] = {
                "preset": alternate["preset"],
                "anchor": alternate["anchor"],
                **freeze(alternate, f"{shot_id} alternate preview"),
            }
        payload_shots.append(payload_shot)
    return (
        payload_shots, asset_specs, pre_skipped_ids,
        copy.deepcopy(agent_input["project_layout_strategy"]),
    )


def _write_alias(page, alias):
    with tempfile.NamedTemporaryFile(dir=alias.parent, delete=False) as handle:
        staged = Path(handle.name)
    try:
        shutil.copyfile(page, staged)
        os.replace(staged, alias)
    finally:
        staged.unlink(missing_ok=True)


def build_review_page(plan, timeline, transcript, video, output_dir, *, project_root, review_id=None):
    root, output_dir, video = Path(project_root).resolve(), Path(output_dir).resolve(), Path(video).resolve()
    review_root = root / "review" / "03-b-roll"
    if not _inside(review_root, output_dir):
        raise ValueError("output_dir must be inside project_root/review/03-b-roll")
    if not _inside(root, video):
        raise ValueError("review video must resolve inside project_root")
    if not video.is_file():
        raise FileNotFoundError(f"review source video not found: {video}")
    canonical_values = {}
    for label, path in (
        ("timeline", root / "work/timeline.json"),
        ("transcript", root / "work/understand/transcript.json"),
        ("project", root / "work/project.json"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"canonical {label} is missing: {path}")
        try:
            canonical_values[label] = projectlib.load_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"canonical {label} is invalid: {path}") from error
    canonical_timeline = canonical_values["timeline"]
    canonical_transcript = canonical_values["transcript"]
    if timeline != canonical_timeline:
        raise ValueError("caller timeline does not match canonical timeline")
    if transcript != canonical_transcript:
        raise ValueError("caller transcript does not match canonical transcript")
    timeline_errors = projectlib.validate_timeline(canonical_timeline)
    if timeline_errors:
        raise ValueError("invalid timeline: " + "; ".join(timeline_errors))
    errors = broll_plan.validate_plan(plan, canonical_timeline, canonical_transcript, project=canonical_values["project"], project_root=root, verify_files=True)
    if errors:
        raise ValueError("invalid plan: " + "; ".join(errors))
    presentation_errors = broll_plan.presentation_errors(
        plan, project_root=root, required=True,
    )
    if presentation_errors:
        raise ValueError(
            "invalid presentation decision: " + "; ".join(presentation_errors)
        )
    expected_video_hash = plan.get("input_hashes", {}).get("review_video_sha256")
    if not isinstance(expected_video_hash, str) or len(expected_video_hash) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_video_hash):
        raise ValueError("plan review video SHA-256 is invalid")
    if _hash(video) != expected_video_hash:
        raise ValueError("review video SHA-256 does not match plan")
    duration = _probe_video(video)
    fps = canonical_timeline["fps"]
    if abs(duration - float(canonical_timeline["program_duration_s"])) > float(fps["den"]) / float(fps["num"]):
        raise ValueError("review video duration does not match timeline")
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"review template not found: {TEMPLATE_PATH}")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(PAYLOAD_MARKER) != 1:
        raise ValueError("review template must contain exactly one payload marker")
    identifier = _review_id(review_id)
    page, assets_dir = output_dir / f"b-roll-review-{identifier}.html", output_dir / f"b-roll-review-{identifier}-assets"
    if page.exists() or assets_dir.exists():
        raise FileExistsError(f"review publication already exists: {identifier}")
    speaker_enabled = speaker_inset.style_enabled(
        plan.get("speaker_inset_style")
    )
    review_mode = (
        "composite" if speaker_enabled and isinstance(
            plan.get("speaker_inset", {}).get("clearance"), dict,
        ) else "selection" if speaker_enabled else "standard"
    )
    if review_mode == "composite":
        shots, candidate_specs, pre_skipped_ids, speaker_layout_strategy = _composite_payload(
            plan, root, assets_dir,
        )
    else:
        shots, candidate_specs, pre_skipped_ids = _payload(
            plan, canonical_timeline, canonical_transcript, root, assets_dir,
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    published_assets = False
    published_page = False
    try:
        with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=f".{output_dir.name}-") as temporary:
            stage = Path(temporary)
            staged_assets = stage / assets_dir.name
            staged_assets.mkdir()
            for source, basename, digest in candidate_specs:
                frozen = staged_assets / basename
                shutil.copyfile(source, frozen)
                if _hash(frozen) != digest:
                    raise ValueError(f"candidate SHA-256 changed during review publication: {source}")
            if review_mode != "composite":
                for index, shot in enumerate(shots, 1):
                    frame = staged_assets / f"frame-{index:03d}.jpg"
                    program = shot["program_range"]
                    _extract_frame(video, (float(program["start_s"]) + float(program["end_s"])) / 2, frame)
                    _validate_jpeg(frame)
                    shot["source_frame"]["sha256"] = _hash(frame)
            subject_hash = broll_plan.canonical_sha256(broll_plan.review_subject(plan))
            payload = {"review_id": identifier, "review_mode": review_mode, "plan_sha256": subject_hash, "plan_subject_sha256": subject_hash, "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "review_video_sha256": expected_video_hash, "timeline": {"fps": copy.deepcopy(canonical_timeline["fps"]), "program_duration_s": canonical_timeline["program_duration_s"], "clips": copy.deepcopy(canonical_timeline["clips"])}, "decision_modes": ["human", "agent"], "pre_skipped_ids": pre_skipped_ids, "shots": shots}
            payload.update({
                "approval_intent": (
                    "approve_selection" if review_mode == "selection" else "approve"
                ),
                "approval_scope": (
                    "speaker-inset-composite"
                    if review_mode == "composite" else "b-roll-selection"
                ),
            })
            if review_mode == "composite":
                speaker = plan["speaker_inset"]
                payload.update({
                    "speaker_style": copy.deepcopy(plan["speaker_inset_style"]),
                    "speaker_layout_strategy": speaker_layout_strategy,
                    "speaker_bindings": {
                        "selection_sha256": plan["selection"]["sha256"],
                        "analysis_sha256": speaker["analysis"]["sha256"],
                        "agent_input_sha256": speaker["agent_input"]["sha256"],
                        "preview_sha256": speaker["preview"]["sha256"],
                        "clearance_sha256": speaker["clearance"]["sha256"],
                        "style_sha256": broll_plan.canonical_sha256(
                            plan["speaker_inset_style"]
                        ),
                    },
                })
            document = template.replace(PAYLOAD_MARKER, base64.b64encode(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).decode("ascii"))
            staged_page = stage / page.name
            staged_page.write_text(document, encoding="utf-8")
            output_dir.mkdir(parents=True, exist_ok=True)
            assets_dir.mkdir()
            published_assets = True
            for asset in staged_assets.iterdir():
                os.replace(asset, assets_dir / asset.name)
            os.link(staged_page, page)
            published_page = True
        hashes = {"page": _hash(page), **{
            asset.relative_to(output_dir).as_posix(): _hash(asset)
            for asset in assets_dir.iterdir() if asset.is_file()
        }}
        _write_alias(page, output_dir / "b-roll-review.html")
    except Exception:
        if published_page:
            page.unlink(missing_ok=True)
        if published_assets:
            shutil.rmtree(assets_dir)
        raise
    alias = output_dir / "b-roll-review.html"
    return {"page": page, "alias": alias, "review_id": identifier, "assets_dir": assets_dir, "warnings": [], "hashes": hashes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("output_dir")
    parser.add_argument("--video", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--review-id")
    args = parser.parse_args(argv)
    result = build_review_page(json.loads(Path(args.plan).read_text(encoding="utf-8")), json.loads(Path(args.timeline).read_text(encoding="utf-8")), json.loads(Path(args.transcript).read_text(encoding="utf-8")), args.video, args.output_dir, project_root=args.project_root, review_id=args.review_id)
    print(json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in result.items()}, default=str))


if __name__ == "__main__":
    main()
