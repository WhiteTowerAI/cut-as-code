"""Collect, analyze, rank, and bind explainable B-roll candidate shortlists."""

import argparse
import copy
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "video-understand" / "scripts"))
import projectlib

import broll_plan
import pexels


SAMPLE_FRACTIONS = (0.10, 0.30, 0.50, 0.70, 0.90)
SCORE_FIELDS = ("semantic_fit", "context_fit", "composition_fit", "style_fit")
TEXT_LOGO_RISKS = {0, 1, 2, 3, 4, "uncertain"}
SEMANTIC_ROLES = {"direct", "supportive", "atmospheric"}
ANALYSIS_CACHE = Path("work/cache/b-roll/candidate-analysis")
ANALYSIS_MEDIA = ANALYSIS_CACHE / "media"
ANALYSIS_FRAMES = ANALYSIS_CACHE / "frames"


def canonical_sha256(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        staged = Path(handle.name)
    try:
        staged.write_text(serialized, encoding="utf-8")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def _finite(value, label, *, positive=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"{label} must be a finite {'positive ' if positive else ''}number")
    return number


def _valid_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _inside(root, target):
    try:
        Path(target).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _project_root_from(path):
    resolved = Path(path).resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "work":
            return parent.parent
    raise ValueError("analysis output must be inside a project work directory")


def _project_path(root, value, *, prefix=None):
    if not isinstance(value, str) or not value.strip():
        return None
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    target = (Path(root).resolve() / raw).resolve()
    if not _inside(root, target):
        return None
    if prefix is not None and not _inside(Path(root).resolve() / prefix, target):
        return None
    return target


def _safe_name(value):
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value)).strip("-.")
    return name or "candidate"


def merge_query_results(queries, results_by_query, *, limit=8):
    if not isinstance(queries, list) or not 1 <= len(queries) <= 3 or any(not isinstance(item, str) or not item.strip() for item in queries):
        raise ValueError("queries must contain one to three nonblank strings")
    if not isinstance(results_by_query, list) or len(results_by_query) != len(queries) or any(not isinstance(items, list) for items in results_by_query):
        raise ValueError("query results do not match queries")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 8:
        raise ValueError("candidate limit must be 1..8")
    merged, seen = [], set()
    max_results = max((len(items) for items in results_by_query), default=0)
    for provider_rank in range(max_results):
        for query_index, items in enumerate(results_by_query):
            if provider_rank >= len(items):
                continue
            candidate = items[provider_rank]
            if not isinstance(candidate, dict):
                continue
            provider_id = candidate.get("provider_id")
            if not isinstance(provider_id, int) or isinstance(provider_id, bool) or provider_id <= 0 or provider_id in seen:
                continue
            item = copy.deepcopy(candidate)
            item["search"] = {
                "query": queries[query_index],
                "query_index": query_index,
                "provider_rank": provider_rank,
                "merge_rank": len(merged),
            }
            merged.append(item)
            seen.add(provider_id)
            if len(merged) == limit:
                return merged
    return merged


def _validate_search_context(value):
    if not isinstance(value, dict) or set(value) != {"topic", "visual_direction", "keywords"}:
        raise ValueError("brief search_context must contain exactly topic, visual_direction, and keywords")
    for field in ("topic", "visual_direction"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"brief search_context {field} must be a nonblank string")
    keywords = value["keywords"]
    if not isinstance(keywords, list) or not 1 <= len(keywords) <= 12:
        raise ValueError("brief search_context keywords must contain one to twelve values")
    if any(not isinstance(keyword, str) or not keyword.strip() for keyword in keywords):
        raise ValueError("brief search_context keywords must be nonblank strings")
    normalized = [keyword.strip().casefold() for keyword in keywords]
    if len(normalized) != len(set(normalized)):
        raise ValueError("brief search_context keywords must be unique")
    return copy.deepcopy(value)


def search_plan(plan, *, orientation, per_page=8, include_pexels=True, searcher=pexels.search_videos):
    if orientation not in {"landscape", "portrait", "square"}:
        raise ValueError("invalid orientation")
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list):
        raise ValueError("plan shots are required")
    brief = plan.get("brief")
    search_context = _validate_search_context(brief.get("search_context") if isinstance(brief, dict) else None)
    shots = []
    for shot in plan["shots"]:
        if not isinstance(shot, dict) or not isinstance(shot.get("id"), str):
            raise ValueError("plan shot id is required")
        semantic_role = shot.get("semantic_role")
        if not isinstance(semantic_role, str) or semantic_role not in SEMANTIC_ROLES:
            raise ValueError(f"{shot['id']} semantic_role is invalid")
        queries = shot.get("queries")
        if not isinstance(queries, list) or not 2 <= len(queries) <= 3:
            raise ValueError(f"{shot['id']} queries must contain two or three values")
        query_results = [searcher(query, orientation=orientation, per_page=per_page) for query in queries] if include_pexels else [[] for _ in queries]
        merged = merge_query_results(queries, query_results, limit=8)
        for candidate in merged:
            candidate["provider_candidate_id"] = candidate.get("id")
            candidate["id"] = f"{_safe_name(shot['id'])}-{candidate['id']}"
        local_candidates = []
        for candidate in shot.get("candidates", []):
            source_type = candidate.get("provenance", {}).get("source_type") if isinstance(candidate, dict) else None
            if source_type not in {"local", "external-generated"}:
                continue
            item = copy.deepcopy(candidate)
            item["search"] = {"source": source_type, "merge_rank": len(merged) + len(local_candidates)}
            local_candidates.append(item)
        shots.append({
            "shot_id": shot["id"],
            "semantic_role": semantic_role,
            "queries": copy.deepcopy(queries),
            "query_results": copy.deepcopy(query_results),
            "merged_candidates": merged + local_candidates,
        })
    return {"schema_version": 1, "search_context": search_context, "orientation": orientation, "per_page": per_page, "candidate_limit": 8, "shots": shots}


def duration_classification(candidate_duration, shot_duration, frame_duration):
    candidate = _finite(candidate_duration, "candidate duration", positive=True)
    shot = _finite(shot_duration, "shot duration", positive=True)
    frame = _finite(frame_duration, "frame duration", positive=True)
    if candidate + frame < shot:
        return "reject"
    return "warn" if candidate - shot < 1.0 else "pass"


def reclassify_durations(analysis, plan, timeline):
    """Rebind revised shot timing while preserving frozen media and frame evidence."""
    if not isinstance(analysis, dict) or not isinstance(analysis.get("shots"), list):
        raise ValueError("candidate analysis shots are required")
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list):
        raise ValueError("plan shots are required")
    fps = timeline.get("fps") if isinstance(timeline, dict) else None
    num = fps.get("num") if isinstance(fps, dict) else None
    den = fps.get("den") if isinstance(fps, dict) else None
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (num, den)):
        raise ValueError("timeline fps is invalid")
    plan_shots = {shot.get("id"): shot for shot in plan["shots"] if isinstance(shot, dict)}
    result = copy.deepcopy(analysis)
    for shot in result["shots"]:
        if not isinstance(shot, dict) or shot.get("shot_id") not in plan_shots:
            raise ValueError("candidate analysis shot does not match revised plan")
        revised = plan_shots[shot["shot_id"]]
        program = revised.get("program_range")
        start = _finite(program.get("start_s"), "shot start") if isinstance(program, dict) else None
        end = _finite(program.get("end_s"), "shot end") if isinstance(program, dict) else None
        if start is None or end is None or end <= start:
            raise ValueError(f"{shot['shot_id']} shot duration is invalid")
        semantic_changed = shot.get("transcript_evidence") != revised.get("transcript_evidence")
        shot["program_range"] = copy.deepcopy(program)
        shot["transcript_evidence"] = copy.deepcopy(revised.get("transcript_evidence"))
        shot["editorial_reason"] = revised.get("editorial_reason")
        shot["visual_intent"] = revised.get("visual_intent")
        shot["agent_rescore_required"] = semantic_changed
        selection = revised.get("selected")
        if not isinstance(selection, dict):
            review_default = revised.get("review_default")
            selection = review_default if isinstance(review_default, dict) else {}
        selected_segments = selection.get("segments")
        segment_requirements = {}
        if isinstance(selected_segments, list):
            for segment in selected_segments:
                if not isinstance(segment, dict):
                    continue
                segment_program = segment.get("program_range")
                segment_start = _finite(segment_program.get("start_s"), "segment program start") if isinstance(segment_program, dict) else None
                segment_end = _finite(segment_program.get("end_s"), "segment program end") if isinstance(segment_program, dict) else None
                rate = _finite(segment.get("playback_rate"), "segment playback rate", positive=True)
                candidate_id = segment.get("candidate_id")
                if (isinstance(candidate_id, str) and segment_start is not None
                        and segment_end is not None and segment_end > segment_start):
                    segment_requirements[candidate_id] = {
                        "program_duration_s": segment_end - segment_start,
                        "playback_rate": rate,
                        "required_source_duration_s": (segment_end - segment_start) * rate,
                    }
        candidates = shot.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"{shot['shot_id']} candidate analysis candidates are invalid")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            media = candidate.get("analysis_media")
            probe = media.get("probe") if isinstance(media, dict) else None
            duration = probe.get("duration_s") if isinstance(probe, dict) else None
            if duration is None:
                source = candidate.get("source_candidate")
                source_probe = source.get("probe") if isinstance(source, dict) else None
                duration = source.get("duration_s", source_probe.get("duration_s") if isinstance(source_probe, dict) else None) if isinstance(source, dict) else None
            if duration is None:
                continue
            evidence = segment_requirements.get(candidate.get("candidate_id"), {
                "program_duration_s": end - start,
                "playback_rate": 1.0,
                "required_source_duration_s": end - start,
            })
            candidate["duration_evidence"] = copy.deepcopy(evidence)
            state = duration_classification(
                duration, evidence["required_source_duration_s"],
                (den / num) * evidence["playback_rate"],
            )
            checks = candidate.setdefault("hard_checks", {})
            checks["duration"] = state
            revised_duration_reason = "candidate cannot cover the revised shot duration"
            warnings = [value for value in candidate.get("warnings", [])
                        if value != "less_than_one_second_trim_pad"]
            if state == "warn":
                warnings.append("less_than_one_second_trim_pad")
            candidate["warnings"] = sorted(set(warnings))
            reasons = [value for value in candidate.get("rejection_reasons", [])
                       if value != revised_duration_reason]
            if state == "reject" and candidate.get("analysis_status") == "analyzed":
                candidate["analysis_status"] = "rejected"
                checks["status"] = "reject"
            if state == "reject":
                reasons.append(revised_duration_reason)
            elif (candidate.get("analysis_status") == "rejected"
                  and revised_duration_reason in candidate.get("rejection_reasons", [])
                  and not reasons):
                candidate["analysis_status"] = "analyzed"
                checks["status"] = "pass"
            candidate["rejection_reasons"] = reasons
        eligible = [candidate for candidate in candidates
                    if isinstance(candidate, dict) and candidate.get("analysis_status") == "analyzed"]
        shot["duplicate_evidence"] = duplicate_evidence(eligible)
    if set(plan_shots) != {shot.get("shot_id") for shot in result["shots"] if isinstance(shot, dict)}:
        raise ValueError("candidate analysis is missing revised plan shots")
    result["project_duplicate_evidence"] = project_duplicate_evidence(result["shots"])
    return result


def _extract_frame(media, timestamp, destination):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.9f}", "-i", str(media), "-frames:v", "1", str(destination)],
        check=True, capture_output=True,
    )


def _full_decode(media):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(media), "-f", "null", "-"],
        check=True, capture_output=True,
    )


def _perceptual_hash(gray):
    small = gray.resize((8, 8), Image.Resampling.LANCZOS)
    values = list(small.get_flattened_data()) if hasattr(small, "get_flattened_data") else list(small.getdata())
    average = sum(values) / len(values)
    bits = "".join("1" if value >= average else "0" for value in values)
    return f"{int(bits, 2):016x}"


def _center_crop(image, target_width, target_height):
    target_ratio = target_width / target_height
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        width, height = max(1, round(image.height * target_ratio)), image.height
    else:
        width, height = image.width, max(1, round(image.width / target_ratio))
    left, top = (image.width - width) // 2, (image.height - height) // 2
    return image.crop((left, top, left + width, top + height)), (width * height) / (image.width * image.height)


def _frame_metrics(image, previous_gray=None):
    gray = image.convert("L")
    histogram = gray.histogram()
    pixels = max(1, image.width * image.height)
    luma = sum(index * count for index, count in enumerate(histogram)) / pixels
    edge = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
    motion = None
    if previous_gray is not None:
        left = previous_gray.resize((64, 64), Image.Resampling.BILINEAR)
        right = gray.resize((64, 64), Image.Resampling.BILINEAR)
        motion = ImageStat.Stat(ImageChops.difference(left, right)).mean[0] / 255.0
    return {
        "average_luma": round(luma, 6),
        "black_clip_ratio": round(sum(histogram[:17]) / pixels, 6),
        "highlight_clip_ratio": round(sum(histogram[240:]) / pixels, 6),
        "edge_detail_energy": round(edge, 6),
        "perceptual_hash": _perceptual_hash(gray),
        "adjacent_frame_change": None if motion is None else round(motion, 6),
    }, gray


def _contact_sheet(rows, destination):
    cell_width, cell_height, label_height = 320, 220, 24
    sheet = Image.new("RGB", (cell_width * 2, (cell_height + label_height) * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, frame, crop) in enumerate(rows):
        top = index * (cell_height + label_height)
        draw.text((6, top + 5), label, fill="black")
        for column, image in enumerate((frame, crop)):
            preview = image.copy()
            preview.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
            x = column * cell_width + (cell_width - preview.width) // 2
            y = top + label_height + (cell_height - preview.height) // 2
            sheet.paste(preview, (x, y))
    sheet.save(destination, "PNG")


def sample_media(media, *, duration_s, output_dir, timeline_width, timeline_height, extract_frame=_extract_frame):
    duration = _finite(duration_s, "media duration", positive=True)
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (timeline_width, timeline_height)):
        raise ValueError("timeline dimensions must be positive integers")
    media, output_dir = Path(media).resolve(), Path(output_dir).resolve()
    if not media.is_file():
        raise FileNotFoundError(f"analysis media is missing: {media}")
    root = _project_root_from(output_dir)
    if not _inside(root / ANALYSIS_FRAMES, output_dir):
        raise ValueError("sample output must be inside the candidate-analysis frame cache")
    output_dir.mkdir(parents=True, exist_ok=True)
    samples, rows, previous = [], [], None
    for index, fraction in enumerate(SAMPLE_FRACTIONS, 1):
        timestamp = duration * fraction
        frame_path = output_dir / f"frame-{index:02d}.png"
        crop_path = output_dir / f"crop-{index:02d}.png"
        extract_frame(media, timestamp, frame_path)
        try:
            with Image.open(frame_path) as opened:
                frame = opened.convert("RGB")
        except OSError as error:
            raise ValueError("sample frame is not a decodable image") from error
        if frame.width <= 0 or frame.height <= 0:
            raise ValueError("sample frame dimensions are invalid")
        crop, retained = _center_crop(frame, timeline_width, timeline_height)
        crop.save(crop_path, "PNG")
        metrics, previous = _frame_metrics(frame, previous)
        samples.append({
            "fraction": fraction,
            "timestamp_s": round(timestamp, 6),
            "frame_path": frame_path.relative_to(root).as_posix(),
            "crop_path": crop_path.relative_to(root).as_posix(),
            "width": frame.width,
            "height": frame.height,
            "sha256": _sha256(frame_path),
            "crop_sha256": _sha256(crop_path),
            "crop_retained_ratio": round(retained, 6),
            **metrics,
        })
        rows.append((f"{round(fraction * 100)}% | original / center crop", frame, crop))
    contact_sheet = output_dir / "contact-sheet.png"
    _contact_sheet(rows, contact_sheet)
    changes = [item["adjacent_frame_change"] for item in samples if item["adjacent_frame_change"] is not None]
    metrics = {
        "average_luma": round(sum(item["average_luma"] for item in samples) / len(samples), 6),
        "black_clip_ratio": round(sum(item["black_clip_ratio"] for item in samples) / len(samples), 6),
        "highlight_clip_ratio": round(sum(item["highlight_clip_ratio"] for item in samples) / len(samples), 6),
        "edge_detail_energy": round(sum(item["edge_detail_energy"] for item in samples) / len(samples), 6),
        "sampled_frame_change": round(sum(changes) / len(changes), 6),
        "crop_retained_ratio": min(item["crop_retained_ratio"] for item in samples),
    }
    warnings = []
    if metrics["average_luma"] < 45: warnings.append("dark_luma_distribution")
    if metrics["average_luma"] > 210: warnings.append("bright_luma_distribution")
    if metrics["black_clip_ratio"] > 0.15: warnings.append("black_clipping")
    if metrics["highlight_clip_ratio"] > 0.15: warnings.append("highlight_clipping")
    if metrics["edge_detail_energy"] < 8: warnings.append("low_edge_detail")
    if metrics["sampled_frame_change"] < 0.01: warnings.append("very_low_sampled_frame_change")
    if metrics["sampled_frame_change"] > 0.30: warnings.append("very_high_sampled_frame_change")
    if metrics["crop_retained_ratio"] < 0.65: warnings.append("severe_center_crop_loss_risk")
    return {
        "samples": samples,
        "metrics": metrics,
        "warnings": warnings,
        "contact_sheet_path": contact_sheet.relative_to(root).as_posix(),
        "contact_sheet_sha256": _sha256(contact_sheet),
    }


def _hamming(left, right):
    return (int(left, 16) ^ int(right, 16)).bit_count()


def duplicate_evidence(candidates):
    exact = {}
    for candidate in candidates:
        digest = candidate.get("analysis_media", {}).get("sha256")
        if isinstance(digest, str):
            exact.setdefault(digest, []).append(candidate.get("candidate_id"))
    exact_groups = [
        {"evidence": digest, "candidate_ids": ids}
        for digest, ids in exact.items() if len(ids) > 1
    ]
    identifiers = [item.get("candidate_id") for item in candidates]
    adjacency = {identifier: set() for identifier in identifiers}
    for index, left in enumerate(candidates):
        left_hashes = [item.get("perceptual_hash") for item in left.get("samples", [])]
        for right in candidates[index + 1:]:
            right_hashes = [item.get("perceptual_hash") for item in right.get("samples", [])]
            if not left_hashes or len(left_hashes) != len(right_hashes) or any(not isinstance(value, str) for value in left_hashes + right_hashes):
                continue
            if sum(_hamming(a, b) for a, b in zip(left_hashes, right_hashes)) / len(left_hashes) <= 6:
                adjacency[left["candidate_id"]].add(right["candidate_id"])
                adjacency[right["candidate_id"]].add(left["candidate_id"])
    groups, visited = [], set()
    for identifier in identifiers:
        if identifier in visited or not adjacency.get(identifier):
            continue
        stack, members = [identifier], []
        while stack:
            current = stack.pop()
            if current in visited: continue
            visited.add(current); members.append(current); stack.extend(adjacency[current] - visited)
        if len(members) > 1:
            groups.append({"candidate_ids": [value for value in identifiers if value in members]})
    rejected = [identifier for group in exact_groups for identifier in group["candidate_ids"][1:]]
    return {"exact_groups": exact_groups, "perceptual_groups": groups, "hard_rejected_candidate_ids": rejected}


def _candidate_ref(shot_id, candidate_id):
    return {"shot_id": shot_id, "candidate_id": candidate_id}


def _ref_key(value):
    if not isinstance(value, dict):
        return None
    shot_id, candidate_id = value.get("shot_id"), value.get("candidate_id")
    if not isinstance(shot_id, str) or not shot_id.strip() or not isinstance(candidate_id, str) or not candidate_id.strip():
        return None
    return shot_id, candidate_id


def _identity_evidence(candidate):
    source = candidate.get("source_candidate") if isinstance(candidate.get("source_candidate"), dict) else {}
    provenance = source.get("provenance") if isinstance(source.get("provenance"), dict) else {}
    evidence = []
    provider_candidate_id = source.get("provider_candidate_id", candidate.get("provider_candidate_id"))
    if isinstance(provider_candidate_id, (str, int)) and not isinstance(provider_candidate_id, bool) and str(provider_candidate_id).strip():
        evidence.append(("provider_candidate_id", str(provider_candidate_id)))
    provider_id = source.get("provider_id", candidate.get("provider_id"))
    delivery = candidate.get("delivery_variant") if isinstance(candidate.get("delivery_variant"), dict) else source.get("delivery_variant")
    delivery_file_id = delivery.get("file_id") if isinstance(delivery, dict) else None
    if isinstance(provider_id, int) and not isinstance(provider_id, bool) and isinstance(delivery_file_id, int) and not isinstance(delivery_file_id, bool):
        evidence.append(("provider_delivery_file", f"{provider_id}:{delivery_file_id}"))
    analysis_media = candidate.get("analysis_media") if isinstance(candidate.get("analysis_media"), dict) else {}
    analysis_sha256 = analysis_media.get("sha256")
    if broll_plan._is_sha256(analysis_sha256):
        evidence.append(("analysis_sha256", analysis_sha256))
    delivery_sha256 = source.get("sha256")
    if broll_plan._is_sha256(delivery_sha256):
        evidence.append(("delivery_sha256", delivery_sha256))
    if provenance.get("source_type") in {"local", "external-generated"}:
        path = source.get("cache_path", analysis_media.get("path"))
        digest = source.get("sha256", analysis_sha256)
        byte_count = source.get("bytes", analysis_media.get("bytes"))
        if isinstance(path, str) and path.strip() and broll_plan._is_sha256(digest) and isinstance(byte_count, int) and not isinstance(byte_count, bool) and byte_count >= 0:
            normalized = Path(path).as_posix().casefold()
            evidence.append(("local_frozen_media", f"{normalized}|{byte_count}|{digest}"))
    return evidence


def _perceptual_distance(left, right):
    left_hashes = [item.get("perceptual_hash") for item in left.get("samples", []) if isinstance(item, dict)]
    right_hashes = [item.get("perceptual_hash") for item in right.get("samples", []) if isinstance(item, dict)]
    if not left_hashes or len(left_hashes) != len(right_hashes) or any(not isinstance(value, str) for value in left_hashes + right_hashes):
        return None
    distances = [_hamming(a, b) for a, b in zip(left_hashes, right_hashes)]
    return {"average_hamming_distance": sum(distances) / len(distances), "minimum_hamming_distance": min(distances)}


def _source_terms(candidate):
    source = candidate.get("source_candidate") if isinstance(candidate.get("source_candidate"), dict) else {}
    provenance = source.get("provenance") if isinstance(source.get("provenance"), dict) else {}
    value = provenance.get("source_url")
    if not isinstance(value, str):
        return set()
    ignored = {"https", "http", "www", "pexels", "com", "video", "videos", "with", "from", "this", "that", "footage"}
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) >= 4 and not token.isdigit() and token not in ignored}


def _series_evidence(left, right):
    left_source = left.get("source_candidate") if isinstance(left.get("source_candidate"), dict) else {}
    right_source = right.get("source_candidate") if isinstance(right.get("source_candidate"), dict) else {}
    left_provenance = left_source.get("provenance") if isinstance(left_source.get("provenance"), dict) else {}
    right_provenance = right_source.get("provenance") if isinstance(right_source.get("provenance"), dict) else {}
    evidence = []
    left_provider, right_provider = left_provenance.get("provider"), right_provenance.get("provider")
    if isinstance(left_provider, str) and left_provider.strip() and left_provider.casefold() == str(right_provider).casefold():
        evidence.append({"kind": "same_provider", "value": left_provider})
    left_creator, right_creator = left_provenance.get("creator"), right_provenance.get("creator")
    if isinstance(left_creator, str) and left_creator.strip() and left_creator.casefold() == str(right_creator).casefold():
        evidence.append({"kind": "same_creator", "value": left_creator})
    left_id = left_source.get("provider_id", left.get("provider_id"))
    right_id = right_source.get("provider_id", right.get("provider_id"))
    if all(isinstance(value, int) and not isinstance(value, bool) for value in (left_id, right_id)) and abs(left_id - right_id) <= 100:
        evidence.append({"kind": "provider_id_proximity", "value": abs(left_id - right_id)})
    shared_terms = sorted(_source_terms(left) & _source_terms(right))
    if shared_terms:
        evidence.append({"kind": "shared_source_terms", "value": shared_terms})
    distance = _perceptual_distance(left, right)
    if distance is not None and distance["average_hamming_distance"] > 6 and distance["minimum_hamming_distance"] <= 6:
        evidence.append({"kind": "partial_perceptual_overlap", "value": distance})
    kinds = {item["kind"] for item in evidence}
    if "same_creator" in kinds and kinds & {"provider_id_proximity", "shared_source_terms", "partial_perceptual_overlap"}:
        return evidence
    return []


def _connected_groups(entries, adjacency):
    order = [entry["key"] for entry in entries]
    visited, groups = set(), []
    for key in order:
        if key in visited or not adjacency.get(key):
            continue
        stack, members = [key], []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            members.append(current)
            stack.extend(adjacency[current] - visited)
        if len(members) > 1:
            groups.append([value for value in order if value in members])
    return groups


def project_duplicate_evidence(shots):
    entries = []
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id")
        for candidate in shot.get("candidates", []):
            if isinstance(candidate, dict) and candidate.get("analysis_status") == "analyzed":
                key = (shot_id, candidate.get("candidate_id"))
                entries.append({"key": key, "shot_id": shot_id, "candidate": candidate})
    by_key = {entry["key"]: entry for entry in entries}
    identity_buckets = {}
    for entry in entries:
        for evidence in _identity_evidence(entry["candidate"]):
            identity_buckets.setdefault(evidence, []).append(entry["key"])
    exact_adjacency = {entry["key"]: set() for entry in entries}
    for members in identity_buckets.values():
        for left in members:
            exact_adjacency[left].update(value for value in members if value != left)
    exact_groups = []
    exact_pairs = set()
    for index, members in enumerate(_connected_groups(entries, exact_adjacency), 1):
        member_set = set(members)
        for left_index, left in enumerate(members):
            for right in members[left_index + 1:]:
                exact_pairs.add(frozenset((left, right)))
        evidence = [
            {"kind": kind, "value": value}
            for (kind, value), bucket in sorted(identity_buckets.items())
            if len(member_set & set(bucket)) > 1
        ]
        exact_groups.append({"group_id": f"exact-{index:03d}", "members": [_candidate_ref(*key) for key in members], "evidence": evidence})

    strict_adjacency = {entry["key"]: set() for entry in entries}
    strict_pairs = {}
    possible_series = []
    for left_index, left in enumerate(entries):
        for right in entries[left_index + 1:]:
            pair = frozenset((left["key"], right["key"]))
            distance = _perceptual_distance(left["candidate"], right["candidate"])
            if distance is not None and distance["average_hamming_distance"] <= 6:
                strict_adjacency[left["key"]].add(right["key"])
                strict_adjacency[right["key"]].add(left["key"])
                strict_pairs[pair] = distance
                continue
            if pair in exact_pairs:
                continue
            evidence = _series_evidence(left["candidate"], right["candidate"])
            if evidence:
                possible_series.append({
                    "hint_id": f"possible-series-{len(possible_series) + 1:03d}",
                    "members": [_candidate_ref(*left["key"]), _candidate_ref(*right["key"])],
                    "evidence": evidence,
                })
    strict_groups = []
    for index, members in enumerate(_connected_groups(entries, strict_adjacency), 1):
        pairs = []
        for left_index, left in enumerate(members):
            for right in members[left_index + 1:]:
                distance = strict_pairs.get(frozenset((left, right)))
                if distance is not None:
                    pairs.append({"members": [_candidate_ref(*left), _candidate_ref(*right)], **distance})
        strict_groups.append({"group_id": f"strict-perceptual-{index:03d}", "members": [_candidate_ref(*key) for key in members], "pairs": pairs})
    return {"exact_groups": exact_groups, "strict_perceptual_groups": strict_groups, "possible_series": possible_series}


def validate_analysis_document(analysis, project_root=None, *, verify_files=False):
    errors = []
    if not isinstance(analysis, dict):
        return ["candidate analysis must be an object"]
    if analysis.get("schema_version") != 1: errors.append("candidate analysis schema_version must be 1")
    try:
        _validate_search_context(analysis.get("search_context"))
    except ValueError as error:
        errors.append(f"candidate analysis {error}")
    if not broll_plan._is_sha256(analysis.get("search_sha256")): errors.append("candidate analysis search SHA-256 is invalid")
    shots = analysis.get("shots")
    if not isinstance(shots, list): return errors + ["candidate analysis shots must be a list"]
    seen_shots, seen_candidates = set(), set()
    root = Path(project_root).resolve() if project_root is not None else None
    for shot in shots:
        if not isinstance(shot, dict): errors.append("candidate analysis shot must be an object"); continue
        shot_id = shot.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id.strip(): errors.append("candidate analysis shot id is required"); shot_id = "<missing>"
        elif shot_id in seen_shots: errors.append(f"duplicate candidate analysis shot id: {shot_id}")
        seen_shots.add(shot_id)
        semantic_role = shot.get("semantic_role")
        if not isinstance(semantic_role, str) or semantic_role not in SEMANTIC_ROLES:
            errors.append(f"{shot_id} candidate analysis semantic_role is invalid")
        candidates = shot.get("candidates")
        if not isinstance(candidates, list): errors.append(f"{shot_id} analysis candidates must be a list"); continue
        for candidate in candidates:
            if not isinstance(candidate, dict): errors.append(f"{shot_id} analysis candidate must be an object"); continue
            candidate_id = candidate.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id.strip(): errors.append(f"{shot_id} analysis candidate id is required"); candidate_id = "<missing>"
            elif candidate_id in seen_candidates: errors.append(f"duplicate analyzed candidate id: {candidate_id}")
            seen_candidates.add(candidate_id)
            status = candidate.get("analysis_status")
            if status not in {"analyzed", "rejected"}: errors.append(f"{shot_id} candidate {candidate_id} analysis status is invalid")
            if not isinstance(candidate.get("warnings"), list) or any(not isinstance(item, str) for item in candidate.get("warnings", [])):
                errors.append(f"{shot_id} candidate {candidate_id} warnings must be strings")
            hard_checks = candidate.get("hard_checks")
            if not isinstance(hard_checks, dict) or hard_checks.get("status") not in {"pass", "reject"}:
                errors.append(f"{shot_id} candidate {candidate_id} hard checks are invalid")
            if status != "analyzed":
                continue
            media = candidate.get("analysis_media")
            if not isinstance(media, dict) or not broll_plan._is_sha256(media.get("sha256")):
                errors.append(f"{shot_id} candidate {candidate_id} analysis media is invalid")
            samples = candidate.get("samples")
            if not isinstance(samples, list) or len(samples) != len(SAMPLE_FRACTIONS):
                errors.append(f"{shot_id} candidate {candidate_id} must have five samples")
                samples = []
            if verify_files:
                if root is None:
                    errors.append("candidate analysis file verification requires project root")
                    continue
                source_type = candidate.get("source_candidate", {}).get("provenance", {}).get("source_type")
                media_prefix = Path("work/cache/b-roll/candidates") if source_type in {"local", "external-generated"} else ANALYSIS_MEDIA
                media_path = _project_path(root, media.get("path") if isinstance(media, dict) else None, prefix=media_prefix)
                if media_path is None: errors.append(f"{shot_id} candidate {candidate_id} analysis media path is invalid")
                elif not media_path.is_file(): errors.append(f"{shot_id} candidate {candidate_id} analysis media is missing")
                elif _sha256(media_path) != media.get("sha256"): errors.append(f"{shot_id} candidate {candidate_id} analysis media SHA-256 is stale")
                for sample in samples:
                    if not isinstance(sample, dict): errors.append(f"{shot_id} candidate {candidate_id} sample is invalid"); continue
                    for field, hash_field, label in (("frame_path", "sha256", "sample frame"), ("crop_path", "crop_sha256", "sample crop")):
                        if field not in sample and field == "crop_path":
                            continue
                        path = _project_path(root, sample.get(field), prefix=ANALYSIS_FRAMES)
                        if path is None: errors.append(f"{shot_id} candidate {candidate_id} {label} path is invalid")
                        elif not path.is_file(): errors.append(f"{shot_id} candidate {candidate_id} {label} is missing")
                        elif _sha256(path) != sample.get(hash_field): errors.append(f"{shot_id} candidate {candidate_id} {label} SHA-256 is stale")
    project_evidence = analysis.get("project_duplicate_evidence")
    if project_evidence is not None:
        if not isinstance(project_evidence, dict):
            errors.append("candidate analysis project duplicate evidence must be an object")
        else:
            valid_refs = {
                (shot.get("shot_id"), candidate.get("candidate_id"))
                for shot in shots if isinstance(shot, dict)
                for candidate in shot.get("candidates", []) if isinstance(candidate, dict) and candidate.get("analysis_status") == "analyzed"
            }
            for field, identifier_field in (("exact_groups", "group_id"), ("strict_perceptual_groups", "group_id"), ("possible_series", "hint_id")):
                groups = project_evidence.get(field)
                if not isinstance(groups, list):
                    errors.append(f"candidate analysis {field} must be a list")
                    continue
                seen_ids = set()
                for group in groups:
                    if not isinstance(group, dict):
                        errors.append(f"candidate analysis {field} entry must be an object")
                        continue
                    identifier = group.get(identifier_field)
                    if not isinstance(identifier, str) or not identifier.strip() or identifier in seen_ids:
                        errors.append(f"candidate analysis {field} ids must be unique nonblank strings")
                    seen_ids.add(identifier)
                    members = group.get("members")
                    member_keys = [_ref_key(member) for member in members] if isinstance(members, list) else []
                    if not isinstance(members, list) or len(members) < 2 or None in member_keys or len(member_keys) != len(set(member_keys)) or any(key not in valid_refs for key in member_keys):
                        errors.append(f"candidate analysis {field} members are invalid")
                    evidence_field = "pairs" if field == "strict_perceptual_groups" else "evidence"
                    if not isinstance(group.get(evidence_field), list):
                        errors.append(f"candidate analysis {field} {evidence_field} must be a list")
    return errors


def _analysis_candidate(base, acquired, sampled, duration_state, timeline_width, timeline_height, hard_checks):
    path = Path(acquired["path"])
    warnings = list(sampled["warnings"])
    if duration_state == "warn": warnings.append("less_than_one_second_trim_pad")
    if acquired["probe"]["width"] < timeline_width or acquired["probe"]["height"] < timeline_height:
        warnings.append("source_resolution_below_timeline")
    checks = copy.deepcopy(hard_checks)
    checks.update({"status": "pass", "sampling": "pass", "exact_duplicate": "pass"})
    return {
        "candidate_id": base["id"],
        "provider_id": base.get("provider_id"),
        "provider_order": copy.deepcopy(base.get("search")),
        "source_candidate": copy.deepcopy(base),
        "analysis_variant": copy.deepcopy(base.get("analysis_variant")),
        "delivery_variant": copy.deepcopy(base.get("delivery_variant")),
        "analysis_status": "analyzed",
        "hard_checks": checks,
        "rejection_reasons": [],
        "warnings": sorted(set(warnings)),
        "analysis_media": {"path": path.as_posix(), "sha256": acquired["sha256"], "bytes": acquired["bytes"], "probe": copy.deepcopy(acquired["probe"])},
        **sampled,
    }


def analyze_search(plan, search, timeline, project_root, *, downloader=pexels.download_candidate, extractor=_extract_frame):
    root = Path(project_root).resolve()
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list): raise ValueError("plan shots are required")
    if not isinstance(search, dict) or search.get("schema_version") != 1 or not isinstance(search.get("shots"), list): raise ValueError("candidate search is invalid")
    brief = plan.get("brief")
    plan_context = _validate_search_context(brief.get("search_context") if isinstance(brief, dict) else None)
    search_context = _validate_search_context(search.get("search_context"))
    if search_context != plan_context:
        raise ValueError("candidate search context does not match plan")
    plan_shot_ids = []
    for shot in plan["shots"]:
        shot_id = shot.get("id") if isinstance(shot, dict) else None
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError("plan shot id is required")
        plan_shot_ids.append(shot_id)
    search_shot_ids = []
    for item in search["shots"]:
        if not isinstance(item, dict):
            raise ValueError("candidate search shot must be an object")
        shot_id = item.get("shot_id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError("candidate search shot id is required")
        if shot_id in search_shot_ids:
            raise ValueError(f"duplicate candidate search shot id: {shot_id}")
        search_shot_ids.append(shot_id)
    if search_shot_ids != plan_shot_ids:
        raise ValueError("candidate search shots do not match plan")
    search_by_shot = dict(zip(search_shot_ids, search["shots"]))
    for shot in plan["shots"]:
        shot_id = shot.get("id")
        search_shot = search_by_shot.get(shot_id)
        if not isinstance(search_shot, dict): raise ValueError(f"candidate search is missing shot {shot_id}")
        semantic_role = shot.get("semantic_role")
        if not isinstance(semantic_role, str) or semantic_role not in SEMANTIC_ROLES:
            raise ValueError(f"{shot_id} semantic_role is invalid")
        search_role = search_shot.get("semantic_role")
        if not isinstance(search_role, str) or search_role not in SEMANTIC_ROLES:
            raise ValueError(f"candidate search {shot_id} semantic_role is invalid")
        if search_role != semantic_role:
            raise ValueError(f"candidate search {shot_id} semantic_role does not match plan")
        if search_shot.get("queries") != shot.get("queries"):
            raise ValueError(f"candidate search {shot_id} queries do not match plan")
    width, height, fps = timeline.get("width"), timeline.get("height"), timeline.get("fps")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (width, height)):
        media_path = root / "work/understand/media.json"
        media = projectlib.load_json(media_path) if media_path.is_file() else {}
        width, height = media.get("width"), media.get("height")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (width, height)) or not isinstance(fps, dict):
        raise ValueError("timeline dimensions and fps are required")
    num, den = fps.get("num"), fps.get("den")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (num, den)):
        raise ValueError("timeline fps is invalid")
    analysis_shots = []
    for shot in plan["shots"]:
        shot_id = shot.get("id")
        search_shot = search_by_shot.get(shot_id)
        if not isinstance(search_shot, dict): raise ValueError(f"candidate search is missing shot {shot_id}")
        program = shot.get("program_range", {})
        shot_duration = _finite(program.get("end_s"), "shot end") - _finite(program.get("start_s"), "shot start")
        if shot_duration <= 0: raise ValueError(f"{shot_id} shot duration is invalid")
        analyzed = []
        for base in search_shot.get("merged_candidates", []):
            candidate_id = base.get("id") if isinstance(base, dict) else "<missing>"
            hard_checks = {"status": "reject", "source": "reject"}
            try:
                source_type = base.get("provenance", {}).get("source_type") if isinstance(base, dict) else None
                if source_type == "pexels":
                    source = pexels.variant_candidate(base, "analysis")
                elif source_type in {"local", "external-generated"}:
                    source = copy.deepcopy(base)
                else:
                    raise ValueError("candidate source is invalid")
                source_probe = source.get("probe") if isinstance(source.get("probe"), dict) else {}
                source_duration = source.get("duration_s", source_probe.get("duration_s"))
                duration_state = duration_classification(source_duration, shot_duration, den / num)
                hard_checks["source"] = "pass"
                hard_checks["duration"] = duration_state
                if duration_state == "reject":
                    raise ValueError("candidate cannot cover the planned shot duration")
                if source_type == "pexels":
                    file_id = source["file_id"]
                    name = f"{_safe_name(shot_id)}-{source['provider_id']}-{file_id}.mp4"
                    destination = root / ANALYSIS_MEDIA / name
                    source["cache_path"] = (ANALYSIS_MEDIA / name).as_posix()
                    acquired = downloader(source, destination, purpose="analysis")
                    hard_checks["download"] = "pass"
                else:
                    file_id = source["id"]
                    path = broll_plan._candidate_path(root, source.get("cache_path"))
                    if path is None or not path.is_file(): raise ValueError("local analysis media path is invalid")
                    if source.get("sha256") != _sha256(path): raise ValueError("local analysis media SHA-256 is stale")
                    if source.get("bytes") != path.stat().st_size: raise ValueError("local analysis media byte count is stale")
                    acquired = copy.deepcopy(source); acquired["path"] = path
                    hard_checks["download"] = "not_applicable"
                _full_decode(acquired["path"])
                hard_checks["decode"] = "pass"
                probe = acquired.get("probe")
                if not isinstance(probe, dict) or any(_finite(probe.get(field), f"probe {field}", positive=True) <= 0 for field in ("duration_s", "width", "height")):
                    raise ValueError("analysis media metadata is invalid")
                hard_checks["metadata"] = "pass"
                source_key = source.get("provider_id", source.get("id", "local"))
                sample_dir = root / ANALYSIS_FRAMES / f"{_safe_name(shot_id)}-{_safe_name(source_key)}-{_safe_name(file_id)}"
                sampled = sample_media(acquired["path"], duration_s=probe["duration_s"], output_dir=sample_dir, timeline_width=width, timeline_height=height, extract_frame=extractor)
                clean = copy.deepcopy(acquired)
                clean["path"] = Path(acquired["path"]).relative_to(root).as_posix()
                analyzed.append(_analysis_candidate(base, clean, sampled, duration_state, width, height, hard_checks))
            except Exception as error:
                analyzed.append({
                    "candidate_id": candidate_id,
                    "provider_id": base.get("provider_id") if isinstance(base, dict) else None,
                    "provider_order": copy.deepcopy(base.get("search")) if isinstance(base, dict) else None,
                    "source_candidate": copy.deepcopy(base) if isinstance(base, dict) else None,
                    "analysis_variant": copy.deepcopy(base.get("analysis_variant")) if isinstance(base, dict) else None,
                    "delivery_variant": copy.deepcopy(base.get("delivery_variant")) if isinstance(base, dict) else None,
                    "analysis_status": "rejected",
                    "hard_checks": hard_checks,
                    "rejection_reasons": [str(error)],
                    "warnings": [],
                })
        eligible = [item for item in analyzed if item["analysis_status"] == "analyzed"]
        duplicates = duplicate_evidence(eligible)
        for candidate_id in duplicates["hard_rejected_candidate_ids"]:
            item = next(candidate for candidate in analyzed if candidate["candidate_id"] == candidate_id)
            item["analysis_status"] = "rejected"
            item["hard_checks"]["status"] = "reject"
            item["hard_checks"]["exact_duplicate"] = "reject"
            item["rejection_reasons"].append("exact duplicate of an earlier candidate")
        for group in duplicates["perceptual_groups"]:
            for candidate_id in group["candidate_ids"]:
                item = next(candidate for candidate in analyzed if candidate["candidate_id"] == candidate_id)
                item["warnings"] = sorted(set(item["warnings"] + ["perceptual_similarity_requires_agent_confirmation"]))
        analysis_shots.append({
            "shot_id": shot_id,
            "semantic_role": shot["semantic_role"],
            "program_range": copy.deepcopy(shot.get("program_range")),
            "transcript_evidence": copy.deepcopy(shot.get("transcript_evidence")),
            "editorial_reason": shot.get("editorial_reason"),
            "visual_intent": shot.get("visual_intent"),
            "avoid": copy.deepcopy(plan.get("brief", {}).get("avoid", [])),
            "queries": copy.deepcopy(shot.get("queries")),
            "original_provider_order": [item.get("provider_id") for results in search_shot.get("query_results", []) for item in results if isinstance(item, dict)],
            "duplicate_evidence": duplicates,
            "candidates": analyzed,
        })
    result = {
        "schema_version": 1,
        "search_context": copy.deepcopy(plan_context),
        "search_sha256": canonical_sha256(search),
        "timeline": {"width": width, "height": height, "fps": {"num": num, "den": den}},
        "sample_fractions": list(SAMPLE_FRACTIONS),
        "shots": analysis_shots,
    }
    result["project_duplicate_evidence"] = project_duplicate_evidence(analysis_shots)
    errors = validate_analysis_document(result, root, verify_files=True)
    if errors: raise ValueError("invalid candidate analysis: " + "; ".join(errors))
    return result


def _score_errors(analysis, scores):
    errors = []
    if not isinstance(scores, dict): return ["Agent scoring must be an object"]
    if scores.get("schema_version") != 1: errors.append("Agent scoring schema_version must be 1")
    if scores.get("analysis_sha256") != canonical_sha256(analysis): errors.append("Agent scoring analysis SHA-256 does not match")
    if scores.get("mode") != "agent": errors.append("Agent scoring mode must be agent")
    actor = scores.get("actor")
    if not isinstance(actor, str) or not actor.strip() or actor.strip().casefold() in {"human", "user"}: errors.append("Agent scoring actor must name the real Agent")
    if not _valid_timestamp(scores.get("timestamp")): errors.append("Agent scoring timestamp must be timezone-aware")
    if not isinstance(scores.get("overall_rationale"), str) or not scores["overall_rationale"].strip(): errors.append("Agent scoring overall rationale is required")
    analysis_shots = {item.get("shot_id"): item for item in analysis.get("shots", []) if isinstance(item, dict)}
    score_shots = scores.get("shots")
    if not isinstance(score_shots, list): return errors + ["Agent scoring shots must be a list"]
    if len(score_shots) != len(analysis_shots): errors.append("Agent scoring shots do not match analysis")
    seen_shots = set()
    for shot in score_shots:
        if not isinstance(shot, dict): errors.append("Agent scoring shot must be an object"); continue
        shot_id = shot.get("shot_id")
        if shot_id not in analysis_shots or shot_id in seen_shots: errors.append("Agent scoring shot ids do not match analysis"); continue
        seen_shots.add(shot_id)
        expected = {item.get("candidate_id") for item in analysis_shots[shot_id].get("candidates", []) if isinstance(item, dict) and item.get("analysis_status") == "analyzed"}
        entries = shot.get("candidates")
        if not isinstance(entries, list): errors.append(f"{shot_id} Agent candidate scores must be a list"); continue
        actual, seen = set(), set()
        for entry in entries:
            if not isinstance(entry, dict): errors.append(f"{shot_id} Agent candidate score must be an object"); continue
            candidate_id = entry.get("candidate_id")
            if candidate_id in seen or candidate_id not in expected: errors.append(f"{shot_id} Agent candidate ids do not match analysis")
            seen.add(candidate_id); actual.add(candidate_id)
            for field in SCORE_FIELDS:
                value = entry.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 4:
                    errors.append(f"{shot_id} candidate {candidate_id} {field} must be an integer from 0 through 4")
            risk = entry.get("text_logo_risk")
            if risk not in TEXT_LOGO_RISKS or isinstance(risk, bool): errors.append(f"{shot_id} candidate {candidate_id} text_logo_risk is invalid")
            if not isinstance(entry.get("rationale"), str) or not entry["rationale"].strip(): errors.append(f"{shot_id} candidate {candidate_id} rationale is required")
            if not isinstance(entry.get("avoid_violation"), bool): errors.append(f"{shot_id} candidate {candidate_id} avoid_violation must be boolean")
            if not isinstance(entry.get("primary_subject_visible"), bool): errors.append(f"{shot_id} candidate {candidate_id} primary_subject_visible must be boolean")
            group = entry.get("near_duplicate_group")
            if group is not None and (not isinstance(group, str) or not group.strip()): errors.append(f"{shot_id} candidate {candidate_id} near_duplicate_group is invalid")
        if actual != expected: errors.append(f"{shot_id} Agent candidate scores do not cover every analyzable candidate")
    if seen_shots != set(analysis_shots): errors.append("Agent scoring shots do not cover analysis")
    confirmed = scores.get("near_duplicate_groups")
    if confirmed is not None:
        if not isinstance(confirmed, list):
            errors.append("Agent near-duplicate groups must be a list")
        else:
            valid_refs = {
                (shot_id, candidate.get("candidate_id"))
                for shot_id, shot in analysis_shots.items()
                for candidate in shot.get("candidates", [])
                if isinstance(candidate, dict) and candidate.get("analysis_status") == "analyzed"
            }
            seen_groups, grouped_members = set(), set()
            for group in confirmed:
                if not isinstance(group, dict):
                    errors.append("Agent near-duplicate group must be an object")
                    continue
                group_id = group.get("group_id")
                if not isinstance(group_id, str) or not group_id.strip() or group_id in seen_groups:
                    errors.append("Agent near-duplicate group ids must be unique nonblank strings")
                seen_groups.add(group_id)
                if group.get("match_type") not in {"exact_duplicate", "same_series"}:
                    errors.append(f"Agent near-duplicate group {group_id} match_type is invalid")
                group_actor = group.get("actor")
                if not isinstance(group_actor, str) or not group_actor.strip() or group_actor.strip().casefold() in {"human", "user"}:
                    errors.append(f"Agent near-duplicate group {group_id} actor must name the real Agent")
                if not _valid_timestamp(group.get("timestamp")):
                    errors.append(f"Agent near-duplicate group {group_id} timestamp must be timezone-aware")
                if not isinstance(group.get("rationale"), str) or not group["rationale"].strip():
                    errors.append(f"Agent near-duplicate group {group_id} rationale is required")
                members = group.get("members")
                member_keys = [_ref_key(member) for member in members] if isinstance(members, list) else []
                if (not isinstance(members, list) or len(members) < 2 or None in member_keys
                        or len(member_keys) != len(set(member_keys)) or any(key not in valid_refs for key in member_keys)):
                    errors.append(f"Agent near-duplicate group {group_id} members are invalid")
                    continue
                if any(key in grouped_members for key in member_keys):
                    errors.append("Agent candidate cannot belong to more than one near-duplicate group")
                grouped_members.update(member_keys)
    return errors


def _provider_key(candidate):
    provider_id = candidate.get("provider_id")
    return (provider_id if isinstance(provider_id, int) and not isinstance(provider_id, bool) else 2 ** 63, str(candidate.get("candidate_id")))


def _ranking_key(item):
    score = item.get("scores", {})
    return (
        -score.get("semantic_fit", -1),
        -score.get("context_fit", -1),
        -(score.get("composition_fit", -1) + score.get("style_fit", -1)),
        item["warning_count"],
        *_provider_key(item),
    )


def rank_candidates(analysis, scores):
    analysis_errors = validate_analysis_document(analysis)
    if analysis_errors: raise ValueError("invalid candidate analysis: " + "; ".join(analysis_errors))
    errors = _score_errors(analysis, scores)
    if errors: raise ValueError("invalid Agent scoring: " + "; ".join(errors))
    score_shots = {item["shot_id"]: item for item in scores["shots"]}
    ranked_shots, ref_items = [], {}
    for analysis_shot in analysis["shots"]:
        shot_id = analysis_shot["shot_id"]
        inputs = {item["candidate_id"]: item for item in score_shots[shot_id]["candidates"]}
        ranked = []
        for candidate in analysis_shot["candidates"]:
            candidate_id = candidate["candidate_id"]
            entry = inputs.get(candidate_id)
            if entry is None:
                item = {
                    "candidate_id": candidate_id, "provider_id": candidate.get("provider_id"),
                    "warnings": copy.deepcopy(candidate.get("warnings", [])), "warning_count": len(candidate.get("warnings", [])),
                    "eligible": False, "ineligibility_reasons": copy.deepcopy(candidate.get("rejection_reasons", ["deterministic hard check failed"])),
                    "suppressed_near_duplicate": False, "suppressed_global_duplicate": False, "similar_footage": [],
                }
            else:
                reasons = []
                if entry["semantic_fit"] == 0: reasons.append("semantic_fit is zero")
                if entry["context_fit"] == 0: reasons.append("context_fit is zero")
                if entry["avoid_violation"]: reasons.append("explicit avoid rule is violated")
                if not entry["primary_subject_visible"]: reasons.append("primary subject is not identifiable in target framing")
                warnings = copy.deepcopy(candidate.get("warnings", []))
                if entry["semantic_fit"] == 1 and "weak_semantic_match" not in warnings:
                    warnings.append("weak_semantic_match")
                item = {
                    "candidate_id": candidate_id,
                    "provider_id": candidate.get("provider_id"),
                    "scores": {field: entry[field] for field in (*SCORE_FIELDS, "text_logo_risk")},
                    "rationale": entry["rationale"].strip(),
                    "avoid_violation": entry["avoid_violation"],
                    "primary_subject_visible": entry["primary_subject_visible"],
                    "near_duplicate_group": entry.get("near_duplicate_group"),
                    "warnings": warnings,
                    "warning_count": len(warnings),
                    "eligible": not reasons,
                    "ineligibility_reasons": reasons,
                    "suppressed_near_duplicate": False,
                    "suppressed_global_duplicate": False,
                    "similar_footage": [],
                }
            ranked.append(item)
            ref_items[(shot_id, candidate_id)] = item
        eligible = sorted((item for item in ranked if item["eligible"]), key=_ranking_key)
        for index, item in enumerate(eligible, 1):
            item["base_rank"] = index
        ranked_shots.append({
            "shot_id": shot_id,
            "base_order": [item["candidate_id"] for item in eligible],
            "base_top3": [item["candidate_id"] for item in eligible[:3]],
            "duplicate_groups": [],
            "candidates": eligible + sorted((item for item in ranked if not item["eligible"]), key=lambda value: str(value["candidate_id"])),
        })

    source_groups = []
    project_evidence = analysis.get("project_duplicate_evidence")
    if not isinstance(project_evidence, dict):
        project_evidence = {"exact_groups": [], "strict_perceptual_groups": [], "possible_series": []}
    for group in project_evidence.get("exact_groups", []):
        source_groups.append({"kind": "exact_duplicate", "group_id": group["group_id"], "members": copy.deepcopy(group["members"])})
    for group in scores.get("near_duplicate_groups", []):
        source_groups.append({"kind": "agent_confirmed", "group_id": group["group_id"], "members": copy.deepcopy(group["members"])})
    for ranked_shot in ranked_shots:
        legacy = {}
        shot_id = ranked_shot["shot_id"]
        for item in ranked_shot["candidates"]:
            if item["eligible"] and item.get("near_duplicate_group"):
                legacy.setdefault(item["near_duplicate_group"], []).append(item)
        for group_id, members in legacy.items():
            if len(members) < 2:
                continue
            source_groups.append({
                "kind": "legacy_agent_group",
                "group_id": f"{shot_id}:{group_id}",
                "members": [_candidate_ref(shot_id, item["candidate_id"]) for item in members],
            })
            ranked_shot["duplicate_groups"].append({
                "group_id": group_id,
                "kept_candidate_id": members[0]["candidate_id"],
                "suppressed_candidate_ids": [item["candidate_id"] for item in members[1:]],
            })

    eligible_refs = {key for key, item in ref_items.items() if item["eligible"]}
    adjacency = {key: set() for key in eligible_refs}
    normalized_sources = []
    for group in source_groups:
        members = [key for key in (_ref_key(member) for member in group["members"]) if key in eligible_refs]
        if len(members) < 2:
            continue
        normalized_sources.append({**group, "member_keys": members})
        for left in members:
            adjacency[left].update(value for value in members if value != left)
    eligible_entries = [{"key": key} for key in ref_items if key in eligible_refs]
    global_allocations = []
    component_by_ref = {}
    for index, members in enumerate(_connected_groups(eligible_entries, adjacency), 1):
        member_set = set(members)
        sources = [
            {"kind": group["kind"], "group_id": group["group_id"]}
            for group in normalized_sources if len(member_set & set(group["member_keys"])) > 1
        ]
        kept = min(members, key=lambda key: _ranking_key(ref_items[key]))
        suppressed = [key for key in members if key != kept]
        source_labels = ", ".join(f"{item['kind']}:{item['group_id']}" for item in sources)
        kept_reason = f"Kept globally for {source_labels} because it has the strongest semantic/context ranking evidence."
        ref_items[kept]["global_allocation"] = {"status": "kept", "reason": kept_reason}
        kept_label = f"{kept[0]} / candidate {kept[1]}"
        for key in suppressed:
            ref_items[key]["suppressed_near_duplicate"] = True
            ref_items[key]["suppressed_global_duplicate"] = True
            ref_items[key]["global_allocation"] = {
                "status": "suppressed",
                "reason": f"Suppressed for {source_labels}; {kept_label} is the globally stronger placement.",
            }
        allocation_id = f"global-allocation-{index:03d}"
        for key in members:
            component_by_ref[key] = allocation_id
        global_allocations.append({
            "allocation_id": allocation_id,
            "source_groups": sources,
            "members": [_candidate_ref(*key) for key in members],
            "kept": _candidate_ref(*kept),
            "suppressed": [_candidate_ref(*key) for key in suppressed],
            "reason": kept_reason,
        })

    selected_refs = set()
    for ranked_shot in ranked_shots:
        shot_id = ranked_shot["shot_id"]
        eligible = [item for item in ranked_shot["candidates"] if item["eligible"]]
        shortlist = [item for item in eligible if not item["suppressed_global_duplicate"]][:3]
        suppressed_base = [candidate_id for candidate_id in ranked_shot["base_top3"] if ref_items[(shot_id, candidate_id)]["suppressed_global_duplicate"]]
        refills = []
        for index, item in enumerate(shortlist, 1):
            item["rank"] = index
            selected_refs.add((shot_id, item["candidate_id"]))
            if item["candidate_id"] not in ranked_shot["base_top3"]:
                refill = {
                    "candidate_id": item["candidate_id"],
                    "replaced_candidate_ids": copy.deepcopy(suppressed_base),
                    "reason": "Refilled with the next independent eligible candidate after global duplicate suppression.",
                }
                refills.append(refill)
                item["shortlist_reason"] = refill["reason"]
            else:
                item["shortlist_reason"] = "Retained from the shot base ranking after global allocation."
        ranked_shot.update({
            "outcome": "ranked" if shortlist else "no_eligible_candidates",
            "top3": [item["candidate_id"] for item in shortlist],
            "refills": refills,
        })

    for field in ("strict_perceptual_groups", "possible_series"):
        for group in project_evidence.get(field, []):
            members = [key for key in (_ref_key(member) for member in group.get("members", [])) if key in selected_refs]
            for left_index, left in enumerate(members):
                for right in members[left_index + 1:]:
                    if left[0] == right[0] or component_by_ref.get(left) == component_by_ref.get(right) and component_by_ref.get(left) is not None:
                        continue
                    ref_items[left]["similar_footage"].append(_candidate_ref(*right))
                    ref_items[right]["similar_footage"].append(_candidate_ref(*left))
    shot_order = {shot["shot_id"]: index for index, shot in enumerate(ranked_shots)}
    for item in ref_items.values():
        item["similar_footage"] = sorted(
            {(_ref_key(value)): value for value in item["similar_footage"]}.values(),
            key=lambda value: (shot_order.get(value["shot_id"], len(shot_order)), value["candidate_id"]),
        )
    return {
        "schema_version": 1,
        "analysis_sha256": canonical_sha256(analysis),
        "decision": {key: copy.deepcopy(scores[key]) for key in ("mode", "actor", "timestamp", "overall_rationale")},
        "project_duplicate_evidence": copy.deepcopy(project_evidence),
        "agent_confirmed_near_duplicates": copy.deepcopy(scores.get("near_duplicate_groups", [])),
        "global_allocations": global_allocations,
        "shots": ranked_shots,
    }


def _work_relative(path):
    path = Path(path).resolve()
    for parent in path.parents:
        if parent.name == "work":
            return path.relative_to(parent).as_posix(), parent.parent
    raise ValueError("ranking path must be inside the project work directory")


def bind_ranking(plan, ranking, ranking_path, acquired_by_shot):
    if not isinstance(plan, dict) or not isinstance(plan.get("shots"), list): raise ValueError("plan shots are required")
    if not isinstance(ranking, dict) or ranking.get("schema_version") != 1 or not broll_plan._is_sha256(ranking.get("analysis_sha256")):
        raise ValueError("candidate ranking is invalid")
    ranking_path = Path(ranking_path).resolve()
    if not ranking_path.is_file() or canonical_sha256(projectlib.load_json(ranking_path)) != canonical_sha256(ranking):
        raise ValueError("candidate ranking file does not match ranking")
    relative, _ = _work_relative(ranking_path)
    ranked = {item.get("shot_id"): item for item in ranking.get("shots", []) if isinstance(item, dict)}
    result = copy.deepcopy(plan)
    shortlists = []
    for shot in result["shots"]:
        shot_id = shot.get("id")
        ranking_shot = ranked.get(shot_id)
        if not isinstance(ranking_shot, dict): raise ValueError(f"candidate ranking is missing shot {shot_id}")
        top3 = ranking_shot.get("top3")
        acquired = acquired_by_shot.get(shot_id) if isinstance(acquired_by_shot, dict) else None
        if not isinstance(top3, list) or len(top3) > 3 or not isinstance(acquired, list) or [item.get("id") for item in acquired if isinstance(item, dict)] != top3:
            raise ValueError(f"{shot_id} acquired candidates do not match ranked Top 3")
        details = {item["candidate_id"]: item for item in ranking_shot.get("candidates", []) if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)}
        duplicate_notes = {item["kept_candidate_id"]: [f"Kept over {', '.join(item['suppressed_candidate_ids'])} in near-duplicate group {item['group_id']}." ] for item in ranking_shot.get("duplicate_groups", [])}
        bound = []
        for index, candidate in enumerate(acquired, 1):
            item = copy.deepcopy(candidate)
            detail = details.get(item["id"])
            if not isinstance(detail, dict) or not detail.get("eligible"): raise ValueError(f"{shot_id} ranked candidate details are missing")
            item["ranking"] = {
                "rank": index,
                "scores": copy.deepcopy(detail["scores"]),
                "warnings": copy.deepcopy(detail["warnings"]),
                "rationale": detail["rationale"],
                "duplicate_notes": duplicate_notes.get(item["id"], []),
                "similar_footage": copy.deepcopy(detail.get("similar_footage", [])),
            }
            bound.append(item)
        if shot.get("status") not in {"planned", "candidates_ready", "skipped"}: raise ValueError(f"{shot_id} lifecycle is past candidate analysis")
        shot["candidates"] = bound
        shot["selected"] = None
        shot["status"] = "candidates_ready" if bound else "skipped"
        shortlists.append({"shot_id": shot_id, "candidate_ids": copy.deepcopy(top3)})
    result["candidate_ranking"] = {
        "path": relative,
        "sha256": _sha256(ranking_path),
        "analysis_sha256": ranking["analysis_sha256"],
        "shortlists": shortlists,
    }
    return result


def acquire_shortlist(plan, analysis, ranking, ranking_path, project_root, *, downloader=pexels.download_candidate):
    root = Path(project_root).resolve()
    if ranking.get("analysis_sha256") != canonical_sha256(analysis): raise ValueError("candidate ranking analysis SHA-256 does not match")
    analysis_shots = {item.get("shot_id"): item for item in analysis.get("shots", []) if isinstance(item, dict)}
    acquired = {}
    for ranking_shot in ranking.get("shots", []):
        shot_id = ranking_shot["shot_id"]
        analysis_shot = analysis_shots.get(shot_id)
        if not isinstance(analysis_shot, dict): raise ValueError(f"candidate analysis is missing shot {shot_id}")
        candidates = {item.get("candidate_id"): item for item in analysis_shot.get("candidates", []) if isinstance(item, dict)}
        acquired[shot_id] = []
        for candidate_id in ranking_shot.get("top3", []):
            analyzed = candidates.get(candidate_id)
            if not isinstance(analyzed, dict) or analyzed.get("analysis_status") != "analyzed": raise ValueError(f"{shot_id} shortlist candidate is not analyzable")
            source = analyzed.get("source_candidate")
            if not isinstance(source, dict): raise ValueError(f"{shot_id} shortlist source candidate is missing")
            source_type = source.get("provenance", {}).get("source_type")
            if source_type == "pexels":
                delivery = pexels.variant_candidate(source, "delivery")
                name = f"{_safe_name(shot_id)}-{delivery['provider_id']}-{delivery['file_id']}.mp4"
                delivery["cache_path"] = f"cache/b-roll/candidates/{name}"
                record = downloader(delivery, root / "work/cache/b-roll/candidates" / name, purpose="delivery")
                record = copy.deepcopy(record); record["path"] = Path(record["path"]).relative_to(root).as_posix()
            elif source_type in {"local", "external-generated"}:
                record = copy.deepcopy(source)
                path = broll_plan._candidate_path(root, record.get("cache_path"))
                if path is None or not path.is_file() or record.get("sha256") != _sha256(path): raise ValueError(f"{shot_id} local shortlist candidate is stale")
            else:
                raise ValueError(f"{shot_id} shortlist source type is invalid")
            record["id"] = candidate_id
            acquired[shot_id].append(record)
    return bind_ranking(plan, ranking, ranking_path, acquired)


def _ranking_map(ranking):
    return {shot["shot_id"]: {item["candidate_id"]: item for item in shot.get("candidates", []) if isinstance(item, dict)} for shot in ranking.get("shots", []) if isinstance(shot, dict)}


def publish_review_packet(analysis, ranking, project_root, *, review_id=None):
    root = Path(project_root).resolve()
    errors = validate_analysis_document(analysis, root, verify_files=True)
    if errors: raise ValueError("invalid candidate analysis: " + "; ".join(errors))
    if ranking.get("analysis_sha256") != canonical_sha256(analysis): raise ValueError("candidate ranking analysis SHA-256 does not match")
    try: identifier = str(uuid.UUID(str(review_id))) if review_id is not None else str(uuid.uuid4())
    except (AttributeError, TypeError, ValueError) as error: raise ValueError("review_id must be a UUID") from error
    review_root = root / "review/03-b-roll"
    packet = review_root / f"candidate-analysis-{identifier}"
    summary = review_root / f"candidate-analysis-{identifier}.md"
    if packet.exists() or summary.exists(): raise FileExistsError(f"candidate analysis review already exists: {identifier}")
    review_root.mkdir(parents=True, exist_ok=True)
    rank_map = _ranking_map(ranking)
    published_packet = False
    try:
        with tempfile.TemporaryDirectory(dir=review_root, prefix=".candidate-analysis-") as temporary:
            stage = Path(temporary)
            stage_packet = stage / packet.name
            stage_packet.mkdir()
            write_json(stage_packet / "candidate-analysis.json", analysis)
            write_json(stage_packet / "candidate-ranking.json", ranking)
            lines = [
                "# B-roll candidate analysis", "",
                f"Analysis SHA-256: `{canonical_sha256(analysis)}`", "",
                f"Ranking SHA-256: `{canonical_sha256(ranking)}`", "",
                f"Project candidate index: [{packet.name}/candidate-index.html]({packet.name}/candidate-index.html)", "",
            ]
            evidence = ranking.get("project_duplicate_evidence", {})
            sections = (
                ("Exact duplicates", evidence.get("exact_groups", [])),
                ("Strict perceptual matches", evidence.get("strict_perceptual_groups", [])),
                ("Possible series", evidence.get("possible_series", [])),
                ("Agent-confirmed near duplicates", ranking.get("agent_confirmed_near_duplicates", [])),
                ("Global keep, suppress, and refill results", ranking.get("global_allocations", [])),
            )
            for title, entries in sections:
                lines.extend([f"## {title}", ""])
                if not entries:
                    lines.extend(["None.", ""])
                    continue
                for entry in entries:
                    lines.extend([f"- `{json.dumps(entry, ensure_ascii=False, sort_keys=True)}`", ""])
            index_entries = []
            for shot in analysis["shots"]:
                shot_id = shot["shot_id"]
                ranked_shot = next(item for item in ranking["shots"] if item["shot_id"] == shot_id)
                lines.extend([
                    f"## {shot_id}", "",
                    f"Transcript evidence: `{json.dumps(shot.get('transcript_evidence'), ensure_ascii=False)}`", "",
                    f"Editorial reason: {shot.get('editorial_reason')}", "",
                    f"Visual intent: {shot.get('visual_intent')}", "",
                    f"Queries: {' | '.join(shot.get('queries', []))}", "",
                    f"Original provider order: {', '.join(map(str, shot.get('original_provider_order', [])))}", "",
                    f"Base ranking: {', '.join(ranked_shot.get('base_order', [])) or 'no_eligible_candidates'}", "",
                    f"Shortlist: {', '.join(ranked_shot.get('top3', [])) or 'no_eligible_candidates'}", "",
                    f"Refills: `{json.dumps(ranked_shot.get('refills', []), ensure_ascii=False, sort_keys=True)}`", "",
                ])
                for candidate in shot["candidates"]:
                    candidate_id = candidate["candidate_id"]
                    detail = rank_map.get(shot_id, {}).get(candidate_id, {})
                    lines.extend([f"### {candidate_id}", "", f"Machine status: {candidate.get('analysis_status')}", "", f"Warnings: {', '.join(candidate.get('warnings', [])) or 'none'}", ""])
                    if detail.get("scores"):
                        lines.extend([f"Agent scores: `{json.dumps(detail['scores'], ensure_ascii=False)}`", "", f"Rationale: {detail.get('rationale')}", ""])
                    if detail.get("global_allocation"):
                        lines.extend([f"Global allocation: `{json.dumps(detail['global_allocation'], ensure_ascii=False, sort_keys=True)}`", ""])
                    if detail.get("shortlist_reason"):
                        lines.extend([f"Shortlist reason: {detail['shortlist_reason']}", ""])
                    candidate_assets = stage_packet / f"{_safe_name(shot_id)}-{_safe_name(candidate_id)}"
                    if candidate.get("samples"):
                        candidate_assets.mkdir()
                    for index, sample in enumerate(candidate.get("samples", []), 1):
                        for field, hash_field, label in (("frame_path", "sha256", "frame"), ("crop_path", "crop_sha256", "crop")):
                            source = _project_path(root, sample.get(field), prefix=ANALYSIS_FRAMES)
                            if source is None or not source.is_file(): raise ValueError("sample asset is missing during publication")
                            destination = candidate_assets / f"{index:02d}-{label}.png"
                            shutil.copyfile(source, destination)
                            if _sha256(destination) != sample.get(hash_field): raise ValueError("sample asset SHA-256 changed during publication")
                    for field in ("contact_sheet_path",):
                        source_value = candidate.get(field)
                        source = _project_path(root, source_value, prefix=ANALYSIS_FRAMES) if source_value else None
                        if source is not None and source.is_file():
                            candidate_assets.mkdir(exist_ok=True)
                            destination = candidate_assets / "contact-sheet.png"
                            shutil.copyfile(source, destination)
                            if _sha256(destination) != candidate.get("contact_sheet_sha256"): raise ValueError("contact sheet SHA-256 changed during publication")
                            lines.extend([f"![{candidate_id} sampled frames]({packet.name}/{candidate_assets.name}/{destination.name})", ""])
                            source_candidate = candidate.get("source_candidate") if isinstance(candidate.get("source_candidate"), dict) else {}
                            provenance = source_candidate.get("provenance") if isinstance(source_candidate.get("provenance"), dict) else {}
                            index_entries.append({
                                "shot_id": shot_id,
                                "candidate_id": candidate_id,
                                "image": f"{candidate_assets.name}/{destination.name}",
                                "provider_id": candidate.get("provider_id"),
                                "creator": provenance.get("creator"),
                                "source_url": provenance.get("source_url"),
                                "rank": detail.get("rank"),
                            })
            index_cards = []
            for entry in index_entries:
                source_url = entry.get("source_url")
                source_link = f'<a href="{html.escape(source_url, quote=True)}">source</a>' if isinstance(source_url, str) and source_url.startswith(("https://", "http://")) else "source unavailable"
                index_cards.append(
                    '<article><img loading="lazy" alt="{}" src="{}"><strong>{}</strong><span>{}</span><span>Rank: {}</span><span>Provider: {} / Creator: {}</span><span>{}</span></article>'.format(
                        html.escape(f"{entry['shot_id']} {entry['candidate_id']} sampled frames", quote=True),
                        html.escape(entry["image"], quote=True),
                        html.escape(entry["candidate_id"]),
                        html.escape(entry["shot_id"]),
                        html.escape(str(entry.get("rank") or "not shortlisted")),
                        html.escape(str(entry.get("provider_id") or "local")),
                        html.escape(str(entry.get("creator") or "unknown")),
                        source_link,
                    )
                )
            index_document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>B-roll project candidate index</title><style>*{box-sizing:border-box}body{margin:0;padding:20px;background:#f5f6f7;color:#1b1f23;font:14px/1.4 system-ui,sans-serif}h1{font-size:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}article{display:grid;gap:5px;border:1px solid #d0d7de;background:#fff;padding:10px;border-radius:4px;overflow-wrap:anywhere}img{width:100%;aspect-ratio:16/9;object-fit:contain;background:#111}span{color:#57606a;font-size:12px}</style><h1>B-roll project candidate index</h1><main class="grid">' + "".join(index_cards) + "</main></html>"
            (stage_packet / "candidate-index.html").write_text(index_document, encoding="utf-8")
            staged_summary = stage / summary.name
            staged_summary.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            os.replace(stage_packet, packet); published_packet = True
            os.replace(staged_summary, summary)
    except Exception:
        if published_packet: shutil.rmtree(packet, ignore_errors=True)
        summary.unlink(missing_ok=True)
        raise
    return {"review_id": identifier, "packet": packet, "summary": summary, "packet_sha256": canonical_sha256({path.relative_to(packet).as_posix(): _sha256(path) for path in sorted(packet.rglob("*")) if path.is_file()}), "summary_sha256": _sha256(summary)}


def _canonical_output(root, value, relative):
    target = Path(value).resolve()
    expected = (Path(root).resolve() / relative).resolve()
    if target != expected: raise ValueError(f"output must be {expected}")
    return target


def _write_coverage_summary(root, plan, ranking=None):
    shortlisted_ids = {
        shot.get("shot_id") for shot in ranking.get("shots", [])
        if isinstance(shot, dict) and shot.get("top3")
    } if isinstance(ranking, dict) else set()
    shortlisted = [
        shot for shot in plan.get("shots", [])
        if isinstance(shot, dict) and shot.get("id") in shortlisted_ids
    ] if isinstance(plan, dict) else []
    final_path = Path(root) / "work/b-roll/coverage-summary.json"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
            dir=final_path.parent, prefix=f".{final_path.name}.", suffix=".tmp", delete=False) as handle:
        staged_path = Path(handle.name)
    try:
        projectlib.write_json(
            staged_path,
            broll_plan.coverage_summary(
                plan,
                planned=plan.get("shots", []) if isinstance(plan, dict) else [],
                shortlisted=shortlisted,
                selected=[],
            ),
        )
        os.replace(staged_path, final_path)
    finally:
        staged_path.unlink(missing_ok=True)


def _json_ready(value):
    if isinstance(value, Path): return value.as_posix()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("project_root"); search.add_argument("plan"); search.add_argument("output")
    search.add_argument("--orientation", required=True, choices=("landscape", "portrait", "square")); search.add_argument("--per-page", type=int, default=8); search.add_argument("--local-only", action="store_true")
    analyze = commands.add_parser("analyze")
    analyze.add_argument("project_root"); analyze.add_argument("plan"); analyze.add_argument("search"); analyze.add_argument("timeline"); analyze.add_argument("output")
    reclassify = commands.add_parser("reclassify")
    reclassify.add_argument("project_root"); reclassify.add_argument("plan"); reclassify.add_argument("analysis"); reclassify.add_argument("timeline"); reclassify.add_argument("output")
    rank = commands.add_parser("rank")
    rank.add_argument("project_root"); rank.add_argument("analysis"); rank.add_argument("scores"); rank.add_argument("output")
    acquire = commands.add_parser("acquire")
    acquire.add_argument("project_root"); acquire.add_argument("plan"); acquire.add_argument("analysis"); acquire.add_argument("ranking")
    publish = commands.add_parser("publish")
    publish.add_argument("project_root"); publish.add_argument("analysis"); publish.add_argument("ranking"); publish.add_argument("--review-id")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.project_root).resolve()
    if args.command == "search":
        output = _canonical_output(root, args.output, "work/b-roll/candidate-search.json")
        plan = projectlib.load_json(args.plan)
        _write_coverage_summary(root, plan)
        value = search_plan(plan, orientation=args.orientation, per_page=args.per_page, include_pexels=not args.local_only)
        write_json(output, value); result = {"output": output, "sha256": _sha256(output), "search_sha256": canonical_sha256(value)}
    elif args.command == "analyze":
        output = _canonical_output(root, args.output, "work/b-roll/candidate-analysis.json")
        value = analyze_search(projectlib.load_json(args.plan), projectlib.load_json(args.search), projectlib.load_json(args.timeline), root)
        write_json(output, value); result = {"output": output, "sha256": _sha256(output), "analysis_sha256": canonical_sha256(value)}
    elif args.command == "reclassify":
        output = _canonical_output(root, args.output, "work/b-roll/candidate-analysis.json")
        value = reclassify_durations(
            projectlib.load_json(args.analysis), projectlib.load_json(args.plan),
            projectlib.load_json(args.timeline),
        )
        write_json(output, value); result = {"output": output, "sha256": _sha256(output), "analysis_sha256": canonical_sha256(value)}
    elif args.command == "rank":
        output = _canonical_output(root, args.output, "work/b-roll/candidate-ranking.json")
        value = rank_candidates(projectlib.load_json(args.analysis), projectlib.load_json(args.scores))
        write_json(output, value)
        _write_coverage_summary(root, projectlib.load_json(root / "work/b-roll/broll-plan.json"), value)
        result = {"output": output, "sha256": _sha256(output), "ranking_sha256": canonical_sha256(value)}
    elif args.command == "acquire":
        plan_path = (root / "work/b-roll/broll-plan.json").resolve()
        if Path(args.plan).resolve() != plan_path: raise ValueError(f"plan must be {plan_path}")
        value = acquire_shortlist(projectlib.load_json(plan_path), projectlib.load_json(args.analysis), projectlib.load_json(args.ranking), args.ranking, root)
        write_json(plan_path, value); result = {"output": plan_path, "sha256": _sha256(plan_path)}
    else:
        result = publish_review_packet(projectlib.load_json(args.analysis), projectlib.load_json(args.ranking), root, review_id=args.review_id)
    print(json.dumps(result, default=_json_ready, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
