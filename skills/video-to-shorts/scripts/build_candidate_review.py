#!/usr/bin/env python3
"""Build an immutable, offline shorts candidate review page."""

import argparse
import base64
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MARKER = "__SHORTS_CANDIDATE_REVIEW_DATA__"
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "shorts-candidates-review.html"
POSITIONS = (("Start", 0.2), ("Middle", 0.5), ("End", 0.8))


def fail(message):
    raise SystemExit(message)


def load_candidates(path, source_video):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read candidate JSON: {error}")
    if not isinstance(data, dict) or data.get("schema_version") != "shorts-candidates.v2":
        fail("candidate review requires shorts-candidates.v2")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        fail("candidate review requires a non-empty candidates array")
    seen = set()
    for index, candidate in enumerate(candidates, 1):
        if not isinstance(candidate, dict):
            fail(f"candidate {index} must be an object")
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str):
            fail(f"candidate {index} candidate_id must be a string")
        candidate_id = candidate_id.strip()
        if not candidate_id or candidate_id in seen:
            fail(f"candidate {index} has a missing or duplicate candidate_id")
        seen.add(candidate_id)
        for field in ("title", "scene_type", "transcript_excerpt", "evidence_mode"):
            if not isinstance(candidate.get(field), str) or not candidate[field].strip():
                fail(f"candidate {candidate_id} {field} must be a non-empty string")
        warnings = candidate.get("warnings", [])
        if not isinstance(warnings, list) or any(not isinstance(value, str) for value in warnings):
            fail(f"candidate {candidate_id} warnings must be a list of strings")
        breakdown = candidate.get("score_breakdown")
        if not isinstance(breakdown, dict) or not breakdown:
            fail(f"candidate {candidate_id} score_breakdown must be an object")
        for dimension, entry in breakdown.items():
            if not isinstance(entry, dict):
                fail(f"candidate {candidate_id} score_breakdown.{dimension} must be an object")
            score, reason = entry.get("score"), entry.get("reason")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
                fail(f"candidate {candidate_id} score_breakdown.{dimension}.score must be finite numeric")
            if not isinstance(reason, str) or not reason.strip():
                fail(f"candidate {candidate_id} score_breakdown.{dimension}.reason must be non-empty")
        score = candidate.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            fail(f"candidate {candidate_id} score must be finite numeric")
        metadata = candidate.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("editorial_reason"), str):
            fail(f"candidate {candidate_id} metadata.editorial_reason must be a string")
        start, end, duration = candidate.get("start_time"), candidate.get("end_time"), candidate.get("duration")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (start, end, duration)):
            fail(f"candidate {candidate_id} must contain numeric start_time, end_time, and duration")
        if not all(math.isfinite(value) for value in (start, end, duration)):
            fail(f"candidate {candidate_id} start_time, end_time, and duration must be finite")
        if start < 0 or end <= start or abs(duration - (end - start)) > 0.01:
            fail(f"candidate {candidate_id} has an invalid range or duration")
    declared_source = str(data.get("video", {}).get("source", "")).strip()
    if not declared_source or Path(declared_source).resolve() != Path(source_video).resolve():
        fail("candidate JSON source video does not match the review source")
    return data


def verify_jpeg(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError) as error:
        fail(f"ffmpeg output is not a valid JPEG: {path}: {error}")
    if width != 960 or height <= 0 or height % 2:
        fail(f"ffmpeg JPEG must be 960 pixels wide with a positive even height: {path}")


def build_candidate_review(source_video, candidates_path, review_out, review_id, template_path=TEMPLATE, run_ffmpeg=None):
    source_video = Path(source_video).resolve()
    candidates_path = Path(candidates_path).resolve()
    review_out = Path(review_out).resolve()
    if not source_video.is_file():
        fail(f"source video not found: {source_video}")
    data = load_candidates(candidates_path, source_video)
    template = Path(template_path).read_text(encoding="utf-8")
    if template.count(MARKER) != 1:
        fail(f"template must contain exactly one {MARKER}")
    review_id = str(review_id).strip()
    if not review_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in review_id):
        fail("review_id may contain only letters, digits, hyphen, and underscore")
    review_out.mkdir(parents=True, exist_ok=True)
    final_page = review_out / f"candidates-{review_id}.html"
    final_assets = review_out / "assets" / f"candidates-{review_id}"
    if final_page.exists() or final_assets.exists():
        fail(f"candidate review artifacts already exist for {review_id}")
    staging = Path(tempfile.mkdtemp(prefix=f".{review_id}-", dir=review_out))
    staged_assets = staging / "assets"
    staged_assets.mkdir()
    runner = run_ffmpeg or subprocess.run
    frames = []
    payload_candidates = []
    published_assets = False
    published_page = False
    try:
        for index, candidate in enumerate(data["candidates"], 1):
            candidate_frames = []
            start = float(candidate["start_time"])
            duration = float(candidate["duration"])
            for label, fraction in POSITIONS:
                seek = start + duration * fraction
                name = f"{index:03d}-{int(fraction * 100):02d}.jpg"
                staged_frame = staged_assets / name
                command = [
                    "ffmpeg", "-y", "-ss", f"{seek:.6f}", "-i", str(source_video),
                    "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "2", str(staged_frame),
                ]
                try:
                    runner(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                except (OSError, subprocess.CalledProcessError) as error:
                    fail(f"failed to extract candidate frame {index}/{label.lower()}: {error}")
                if not staged_frame.is_file() or staged_frame.stat().st_size == 0:
                    fail(f"ffmpeg produced an empty candidate frame: {staged_frame}")
                verify_jpeg(staged_frame)
                candidate_frames.append({
                    "label": label, "time": round(seek, 3),
                    "src": f"assets/candidates-{review_id}/{name}",
                    "alt": f"{candidate['title']} at {label.lower()} frame",
                })
                frames.append(final_assets / name)
            score_details = [
                {"name": name, "score": entry.get("score"), "reason": str(entry.get("reason", ""))}
                for name, entry in (candidate.get("score_breakdown") or {}).items()
            ]
            payload_candidates.append({
                "rank": index, "reference": f"text_visual/{candidate['candidate_id']}",
                "title": str(candidate.get("title", "")), "sceneType": str(candidate.get("scene_type", "")),
                "startTime": candidate["start_time"], "endTime": candidate["end_time"],
                "duration": candidate["duration"], "score": candidate.get("score"),
                "warnings": candidate.get("warnings") or [],
                "transcriptExcerpt": str(candidate.get("transcript_excerpt", "")),
                "editorialReason": str((candidate.get("metadata") or {}).get("editorial_reason", "")),
                "scoreDetails": score_details, "frames": candidate_frames,
            })
        payload = {"reviewId": review_id, "candidates": payload_candidates}
        encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        staged_page = staging / final_page.name
        staged_page.write_text(template.replace(MARKER, encoded), encoding="utf-8")
        if staged_page.stat().st_size == 0:
            fail("candidate review page is empty")
        final_assets.parent.mkdir(parents=True, exist_ok=True)
        staged_assets.rename(final_assets)
        published_assets = True
        os.link(staged_page, final_page)
        published_page = True
    except BaseException:
        if published_page and final_page.exists():
            final_page.unlink()
        if published_assets and final_assets.exists():
            shutil.rmtree(final_assets)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"page": final_page, "frames": frames}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--review-out", required=True)
    parser.add_argument("--review-id", required=True)
    args = parser.parse_args(argv)
    result = build_candidate_review(args.video, args.candidates, args.review_out, args.review_id)
    print(result["page"])


if __name__ == "__main__":
    main()
