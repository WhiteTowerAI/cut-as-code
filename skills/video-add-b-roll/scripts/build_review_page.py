"""Build an immutable local B-roll candidate review page."""

import argparse
import base64
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


def _payload(plan, root, assets_dir):
    payload_shots = []
    pre_skipped_ids = []
    candidate_specs = []
    for shot_index, shot in enumerate(plan["shots"], 1):
        if shot["status"] == "skipped":
            pre_skipped_ids.append(shot["id"])
            continue
        frame = assets_dir / f"frame-{len(payload_shots) + 1:03d}.jpg"
        candidates = []
        for candidate_index, candidate in enumerate(shot["candidates"], 1):
            path = broll_plan._candidate_path(root, candidate["cache_path"])
            if path is None or not path.is_file():
                raise ValueError(f"{shot['id']} candidate path escapes project root")
            suffix = path.suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", path.suffix) else ""
            basename = f"candidate-{shot_index:03d}-{candidate_index:03d}{suffix}"
            candidate_specs.append((path, basename, candidate["sha256"]))
            item = {"id": candidate["id"], "media_type": candidate["media_type"], "path": f"{assets_dir.name}/{basename}", "sha256": candidate["sha256"], "provenance": candidate["provenance"]}
            if candidate["media_type"] == "video":
                probe = candidate.get("probe")
                duration = broll_plan._positive_duration(probe.get("duration_s")) if isinstance(probe, dict) else None
                if duration is None:
                    raise ValueError(f"{shot['id']} candidate {candidate['id']} has no valid review duration")
                item["duration_s"] = duration
            candidates.append(item)
        payload_shots.append({"id": shot["id"], "program_range": shot["program_range"], "source_ranges": shot["source_ranges"], "transcript_evidence": shot["transcript_evidence"], "editorial_reason": shot["editorial_reason"], "visual_intent": shot["visual_intent"], "queries": shot["queries"], "source_frame": {"path": f"{assets_dir.name}/{frame.name}", "sha256": None}, "candidates": candidates})
    return payload_shots, candidate_specs, pre_skipped_ids


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
    shots, candidate_specs, pre_skipped_ids = _payload(plan, root, assets_dir)
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
            for index, shot in enumerate(shots, 1):
                frame = staged_assets / f"frame-{index:03d}.jpg"
                program = shot["program_range"]
                _extract_frame(video, (float(program["start_s"]) + float(program["end_s"])) / 2, frame)
                _validate_jpeg(frame)
                shot["source_frame"]["sha256"] = _hash(frame)
            subject_hash = broll_plan.canonical_sha256(broll_plan.review_subject(plan))
            payload = {"review_id": identifier, "plan_sha256": subject_hash, "plan_subject_sha256": subject_hash, "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "review_video_sha256": expected_video_hash, "decision_modes": ["human", "agent"], "pre_skipped_ids": pre_skipped_ids, "shots": shots}
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
        hashes = {"page": _hash(page), **{asset.relative_to(output_dir).as_posix(): _hash(asset) for asset in assets_dir.glob("*.jpg")}}
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
