"""Build an immutable local B-roll candidate review page."""

import argparse
import base64
import hashlib
import json
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


def _payload(plan, timeline, root, assets_dir):
    payload_shots = []
    for shot in plan["shots"]:
        if shot["status"] == "skipped":
            continue
        frame = assets_dir / f"frame-{len(payload_shots) + 1:03d}.jpg"
        candidates = []
        for candidate in shot["candidates"]:
            path = broll_plan._candidate_path(root, candidate["cache_path"])
            if path is None or not path.is_file():
                raise ValueError(f"{shot['id']} candidate path escapes project root")
            candidates.append({"id": candidate["id"], "media_type": candidate["media_type"], "path": os.path.relpath(path, assets_dir.parent).replace("\\", "/"), "sha256": candidate["sha256"], "duration_s": candidate.get("duration_s") or candidate.get("probe", {}).get("duration_s") or float(shot["program_range"]["end_s"]) - float(shot["program_range"]["start_s"]), "provenance": candidate["provenance"]})
        payload_shots.append({"id": shot["id"], "program_range": shot["program_range"], "source_ranges": shot["source_ranges"], "transcript_evidence": shot["transcript_evidence"], "editorial_reason": shot["editorial_reason"], "visual_intent": shot["visual_intent"], "queries": shot["queries"], "source_frame": {"path": f"{assets_dir.name}/{frame.name}", "sha256": None}, "candidates": candidates})
    return payload_shots


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
    if not video.is_file():
        raise FileNotFoundError(f"review source video not found: {video}")
    timeline_errors = projectlib.validate_timeline(timeline)
    if timeline_errors:
        raise ValueError("invalid timeline: " + "; ".join(timeline_errors))
    errors = broll_plan.validate_plan(plan, timeline, transcript, project_root=root, verify_files=True)
    if errors:
        raise ValueError("invalid plan: " + "; ".join(errors))
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"review template not found: {TEMPLATE_PATH}")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(PAYLOAD_MARKER) != 1:
        raise ValueError("review template must contain exactly one payload marker")
    identifier = _review_id(review_id)
    page, assets_dir = output_dir / f"b-roll-review-{identifier}.html", output_dir / f"b-roll-review-{identifier}-assets"
    if page.exists() or assets_dir.exists():
        raise FileExistsError(f"review publication already exists: {identifier}")
    shots = _payload(plan, timeline, root, assets_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=f".{output_dir.name}-") as temporary:
            stage = Path(temporary)
            staged_assets = stage / assets_dir.name
            staged_assets.mkdir()
            for index, shot in enumerate(shots, 1):
                frame = staged_assets / f"frame-{index:03d}.jpg"
                program = shot["program_range"]
                _extract_frame(video, (float(program["start_s"]) + float(program["end_s"])) / 2, frame)
                _validate_jpeg(frame)
                shot["source_frame"]["sha256"] = _hash(frame)
            subject_hash = broll_plan.canonical_sha256(broll_plan.review_subject(plan))
            payload = {"review_id": identifier, "plan_sha256": subject_hash, "plan_subject_sha256": subject_hash, "candidate_manifest_sha256": broll_plan.canonical_sha256(broll_plan.candidate_manifest(plan)), "decision_modes": ["human", "agent"], "shots": shots}
            document = template.replace(PAYLOAD_MARKER, base64.b64encode(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).decode("ascii"))
            staged_page = stage / page.name
            staged_page.write_text(document, encoding="utf-8")
            output_dir.mkdir(parents=True, exist_ok=True)
            os.replace(staged_assets, assets_dir)
            os.replace(staged_page, page)
    except Exception:
        if assets_dir.exists() and not page.exists():
            shutil.rmtree(assets_dir)
        raise
    warnings = []
    alias = output_dir / "b-roll-review.html"
    try:
        _write_alias(page, alias)
    except OSError as error:
        warnings.append(str(error))
    hashes = {"page": _hash(page), **{frame.relative_to(output_dir).as_posix(): _hash(frame) for frame in assets_dir.glob("*.jpg")}}
    return {"page": page, "alias": alias, "review_id": identifier, "assets_dir": assets_dir, "warnings": warnings, "hashes": hashes}


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
