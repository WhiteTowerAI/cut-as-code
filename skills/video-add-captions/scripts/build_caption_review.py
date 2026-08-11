"""Build source-backed Standard or Expressive caption review stills."""

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402
import caption_spatial_context  # noqa: E402


REVIEW_TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "captions-review.html"
CAPTION_STYLES = Path(__file__).resolve().with_name("caption-styles.json")
REVIEW_MARKER = "__CAPTION_EVIDENCE_REVIEW_DATA__"
REVIEW_PAYLOAD_PATTERN = re.compile(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)";')
REVIEW_LABELS = ("early", "middle", "late", "no-caption")
EXPRESSIVE_VARIANTS = ("bottom-standard", "center-emphasis")
SPATIAL_SETTLE_FRAMES = 6
CLEARANCE_ALPHA_THRESHOLD = 8
FRAME_SNAP_TOLERANCE = Fraction(1, 1_000_000)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def no_caption_sample(cues, duration, fps):
    cursor = 0.0
    gaps = []
    for cue in cues:
        start, end = float(cue["start"]), float(cue["end"])
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        gaps.append((cursor, duration))
    gap = max(gaps, key=lambda item: item[1] - item[0], default=None)
    if not gap or gap[1] - gap[0] <= 2 / fps:
        raise ValueError("caption plan has no caption-free review frame")
    return {
        "label": "no-caption",
        "file_stem": "no-caption",
        "kind": "no-caption",
        "program_s": (gap[0] + gap[1]) / 2,
        "cue_index": None,
        "cue_text": "",
        "displayed_text": "",
        "warnings": [],
    }


def standard_sample_times(plan, fps):
    cues = sorted(plan["cues"], key=lambda cue: float(cue["start"]))
    if not cues:
        raise ValueError("caption plan has no cues")
    indexes = (0, (len(cues) - 1) // 2, len(cues) - 1)
    samples = []
    for label, index in zip(("early", "middle", "late"), indexes):
        cue = cues[index]
        samples.append({
            "label": label,
            "file_stem": label,
            "kind": "standard",
            "program_s": (float(cue["start"]) + float(cue["end"])) / 2,
            "cue_index": cue.get("index", index + 1),
            "cue_text": cue.get("text", ""),
            "displayed_text": cue.get("text", ""),
            "warnings": [],
        })
    samples.append(no_caption_sample(cues, float(plan["program_duration_s"]), fps))
    return samples


def cue_text(cue):
    text = str(cue.get("text", "")).strip()
    if text:
        return text
    return " ".join(str(word.get("word", "")).strip() for word in cue.get("words", [])).strip()


def emphasized_words(cue):
    return [
        str(word.get("word", "")).strip()
        for word in cue.get("words", [])
        if word.get("semantic_role", "normal") != "normal" and str(word.get("word", "")).strip()
    ]


def expressive_sample_times(plan, fps):
    presentation = plan.get("presentation", {})
    beats = presentation.get("layout_beats")
    if presentation.get("mode") != "expressive" or not isinstance(beats, list) or not beats:
        raise ValueError("expressive caption review requires completed layout beats")
    cues = sorted(plan["cues"], key=lambda cue: float(cue["start"]))
    cue_by_id = {cue.get("id"): cue for cue in cues}
    samples = []
    for beat in beats:
        beat_id = str(beat.get("id", "")).strip()
        variant = beat.get("variant")
        cue_ids = beat.get("cue_ids")
        if not beat_id or variant not in EXPRESSIVE_VARIANTS or not isinstance(cue_ids, list) or not cue_ids:
            raise ValueError("expressive caption review found an invalid layout beat")
        beat_cues = [cue_by_id.get(cue_id) for cue_id in cue_ids]
        if any(cue is None for cue in beat_cues):
            raise ValueError(f"expressive layout beat {beat_id} references an unknown cue")
        beat_start = float(beat["program_range"]["start_s"])
        beat_end = float(beat["program_range"]["end_s"])
        target = (beat_start + beat_end) / 2
        containing = [cue for cue in beat_cues if float(cue["start"]) <= target < float(cue["end"])]
        warnings = []
        if containing:
            sample_cue = containing[0]
            program_s = target
        else:
            sample_cue = min(
                beat_cues,
                key=lambda cue: abs(((float(cue["start"]) + float(cue["end"])) / 2) - target),
            )
            program_s = (float(sample_cue["start"]) + float(sample_cue["end"])) / 2
            warnings.append("Beat midpoint falls between cues; sampled the nearest complete cue midpoint.")
        samples.append({
            "label": beat_id,
            "file_stem": re.sub(r"[^A-Za-z0-9._-]+", "-", beat_id).strip("-") or "layout-beat",
            "kind": "layout-beat",
            "beat_id": beat_id,
            "variant": variant,
            "cue_ids": cue_ids,
            "program_s": program_s,
            "cue_index": sample_cue.get("index"),
            "cue_text": cue_text(sample_cue),
            "displayed_text": cue_text(sample_cue),
            "beat_text": " ".join(cue_text(cue) for cue in beat_cues).strip(),
            "emphasized_words": emphasized_words(sample_cue),
            "hero_line": copy.deepcopy(sample_cue.get("hero_line")),
            "warnings": warnings,
        })
    samples.append(no_caption_sample(cues, float(plan["program_duration_s"]), fps))
    return samples


def sample_times(plan, fps):
    if plan.get("presentation", {}).get("mode") == "expressive":
        return expressive_sample_times(plan, fps)
    return standard_sample_times(plan, fps)


def _active_cue(plan, program_s):
    return next((cue for cue in plan["cues"]
                 if float(cue["start"]) <= program_s < float(cue["end"])), None)


def _spatial_beat(context, cue, program_s):
    if cue:
        return next((beat for beat in context["placement_beats"]
                     if cue.get("id") in beat.get("cue_ids", [])), None)
    return next((beat for beat in context["placement_beats"]
                 if float(beat["program_range"]["start_s"]) <= program_s
                 < float(beat["program_range"]["end_s"])), None)


def _fps_fraction(fps):
    if isinstance(fps, Fraction):
        value = fps
    elif isinstance(fps, dict):
        value = Fraction(int(fps["num"]), int(fps["den"]))
    else:
        value = Fraction(Decimal(str(fps)))
    if value <= 0:
        raise ValueError("caption review FPS must be positive")
    return value


def _time_fraction(value):
    return Fraction(Decimal(str(value)))


def _ceil_fraction(value):
    return -(-value.numerator // value.denominator)


def _nearest_frame(program_s, fps):
    scaled = _time_fraction(program_s) * _fps_fraction(fps)
    return (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)


def _boundary_frame(program_s, fps):
    scaled = _time_fraction(program_s) * _fps_fraction(fps)
    nearest = (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)
    if abs(scaled - nearest) <= FRAME_SNAP_TOLERANCE:
        return nearest
    return _ceil_fraction(scaled)


def _frame_time(frame, fps):
    return float(Fraction(int(frame), 1) / _fps_fraction(fps))


def _visual_interval(context, frame, fps):
    return next((interval for interval in context.get("visual_intervals", [])
                 if _boundary_frame(interval["program_range"]["start_s"], fps) <= frame
                 < _boundary_frame(interval["program_range"]["end_s"], fps)), None)


def spatial_sample_times(plan, fps, context):
    """Merge base review samples with frame-deduplicated spatial/hero evidence."""
    duration = float(plan["program_duration_s"])
    fps_fraction = _fps_fraction(fps)
    fps_value = float(fps_fraction)
    last_frame = max(0, _boundary_frame(duration, fps_fraction) - 1)
    by_frame = {}

    def add(sample, purpose):
        if "frame" in sample:
            frame = int(sample["frame"])
        else:
            program_s = min(max(float(sample["program_s"]), 0.0), duration)
            frame = _nearest_frame(program_s, fps_fraction)
        frame = min(max(frame, 0), last_frame)
        program_s = _frame_time(frame, fps_fraction)
        cue = _active_cue(plan, program_s)
        beat = _spatial_beat(context, cue, program_s)
        interval = _visual_interval(context, frame, fps_fraction)
        hero_line = cue.get("hero_line") if cue else None
        cue_entry_frame = bool(
            cue and frame == _boundary_frame(cue["start"], fps_fraction)
        )
        enriched = {
            **sample,
            "program_s": program_s,
            "frame": frame,
            "cue_index": cue.get("index") if cue else sample.get("cue_index"),
            "cue_entry_frame": cue_entry_frame,
            "cue_text": cue_text(cue) if cue else sample.get("cue_text", ""),
            "displayed_text": cue_text(cue) if cue else sample.get("displayed_text", ""),
            "purposes": [purpose],
            "hero_line": copy.deepcopy(hero_line) if hero_line else None,
        }
        if beat:
            enriched.update({
                "spatial_beat_id": beat["id"],
                "requested_variant": beat["requested_variant"],
                "resolved_placement": beat["resolved_placement"],
                "allowed_rect": copy.deepcopy(beat.get("allowed_rect")),
            })
        if interval:
            enriched.update({
                "visual_interval_id": interval["id"],
                "visual_context": interval["visual_context"],
                "background": copy.deepcopy(interval["background"]),
                "speaker_rect": copy.deepcopy(interval.get("speaker_rect")),
            })
        else:
            enriched.update({
                "visual_context": "a-roll",
                "background": None,
                "speaker_rect": None,
            })
        if frame in by_frame:
            existing = by_frame[frame]
            if purpose not in existing["purposes"]:
                existing["purposes"].append(purpose)
            for key, value in enriched.items():
                if existing.get(key) is None and value is not None:
                    existing[key] = value
            return
        by_frame[frame] = enriched

    for sample in sample_times(plan, fps_value):
        add(sample, sample["kind"])

    for cue in plan["cues"]:
        if cue.get("hero_line"):
            add({
                "label": f"hero-cue-{cue['index']:03d}",
                "file_stem": f"hero-cue-{cue['index']:03d}",
                "kind": "hero-line",
                "program_s": (float(cue["start"]) + float(cue["end"])) / 2,
                "warnings": [],
            }, "hero-line")

    for beat in context.get("placement_beats", []):
        if not beat.get("background"):
            continue
        start = float(beat["program_range"]["start_s"])
        end = float(beat["program_range"]["end_s"])
        span = end - start
        first_frame = _boundary_frame(start, fps_fraction)
        last_beat_frame = max(first_frame, _boundary_frame(end, fps_fraction) - 1)
        for ordinal, ratio in enumerate((0.0, 0.25, 0.5, 0.75, 1.0), 1):
            program_s = start + span * ratio
            frame = None
            if ratio == 0.0:
                frame = min(first_frame + SPATIAL_SETTLE_FRAMES, last_beat_frame)
            elif ratio == 1.0:
                frame = last_beat_frame
            add({
                "label": f"{beat['id']}-{ordinal}",
                "file_stem": f"{beat['id']}-{ordinal}",
                "kind": "spatial-beat",
                "program_s": program_s,
                **({"frame": frame} if frame is not None else {}),
                "warnings": [],
            }, f"spatial-{ordinal}")

    intervals = context.get("visual_intervals", [])
    boundaries = sorted({
        float(value)
        for interval in intervals
        for value in (
            interval["program_range"]["start_s"],
            interval["program_range"]["end_s"],
        )
    })
    for index, boundary in enumerate(boundaries, 1):
        first_active = _boundary_frame(boundary, fps_fraction)
        for side, frame in (("before", max(0, first_active - 1)), ("after", first_active)):
            sample = {
                "label": f"boundary-{index:03d}-{side}",
                "file_stem": f"boundary-{index:03d}-{side}",
                "kind": "spatial-boundary",
                "program_s": _frame_time(frame, fps_fraction),
                "frame": frame,
                "warnings": [],
            }
            add(sample, f"spatial-boundary-{side}")
            add(sample, f"spatial-boundary-{index:03d}-{side}")

    for cue in plan["cues"]:
        marker = cue.get("unsplittable_word_boundary")
        if not marker:
            continue
        boundary = float(marker["boundary_s"])
        boundary_frame = _boundary_frame(boundary, fps_fraction)
        for label, frame in (
            ("before", max(0, boundary_frame - 1)),
            ("boundary", boundary_frame),
            ("midpoint", _nearest_frame(marker["word_midpoint_s"], fps_fraction)),
        ):
            add({
                "label": f"unsplittable-cue-{cue['index']:03d}-{label}",
                "file_stem": f"unsplittable-cue-{cue['index']:03d}-{label}",
                "kind": "unsplittable-word-boundary",
                "program_s": _frame_time(frame, fps_fraction),
                "frame": frame,
                "warnings": ["Visual boundary falls inside a word; inspect both sides."],
            }, f"unsplittable-{label}")

    return [by_frame[frame] for frame in sorted(by_frame)]


REVIEW_CATEGORIES = (
    "bottom-standard", "center-emphasis", "preset-bottom",
    "frame-center", "panel-center", "hero-1.5x",
)


def _review_categories(sample):
    if "caption_bbox" in sample and sample["caption_bbox"] is None:
        return []
    categories = []
    requested = sample.get("requested_variant") or sample.get("variant")
    if requested in {"bottom-standard", "center-emphasis"}:
        categories.append(requested)
    placement = sample.get("resolved_placement")
    if not placement and requested:
        placement = "frame-center" if requested == "center-emphasis" else "preset-bottom"
    if placement in {"preset-bottom", "frame-center", "panel-center"}:
        categories.append(placement)
    if sample.get("hero_line"):
        categories.append("hero-1.5x")
    return [category for category in REVIEW_CATEGORIES if category in categories]


def select_review_samples(samples):
    """Return the smallest deterministic set covering maintained review categories."""
    candidates = []
    seen_pixels = set()
    for order, sample in enumerate(samples):
        if sample.get("clearance_status") != "pass":
            continue
        categories = _review_categories(sample)
        if not categories:
            continue
        pixel_key = (sample.get("preview"), sample.get("sha256"))
        if pixel_key in seen_pixels:
            continue
        seen_pixels.add(pixel_key)
        candidates.append((order, sample, categories))

    remaining = {category for _, _, categories in candidates for category in categories}
    selected = []
    while remaining:
        choices = [
            (len(remaining.intersection(categories)), -order, sample, categories)
            for order, sample, categories in candidates
            if remaining.intersection(categories)
        ]
        if not choices:
            break
        _, _, sample, categories = max(choices, key=lambda item: (item[0], item[1]))
        covered = [category for category in categories if category in remaining]
        selected.append({
            **copy.deepcopy(sample),
            "sample_label": sample["label"],
            "categories": covered,
        })
        remaining.difference_update(covered)
        candidates = [item for item in candidates if item[1] is not sample]

    if len(selected) > len(REVIEW_CATEGORIES):
        raise ValueError("caption review representative evidence exceeds maintained category count")
    return selected


def _rect_pixels(rect, width, height):
    if not rect:
        return None
    return [
        round(float(rect["x"]) * width),
        round(float(rect["y"]) * height),
        round((float(rect["x"]) + float(rect["width"])) * width),
        round((float(rect["y"]) + float(rect["height"])) * height),
    ]


def _intersects(left, right):
    return max(left[0], right[0]) < min(left[2], right[2]) and max(left[1], right[1]) < min(left[3], right[3])


def _color_rgb(value):
    value = str(value).lstrip("#")
    if len(value) != 6:
        raise ValueError("hero-line color must be #RRGGBB")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _hero_bbox(overlay, hero_color):
    target = Image.new("RGB", overlay.size, _color_rgb(hero_color))
    differences = ImageChops.difference(overlay.convert("RGB"), target).split()
    max_difference = ImageChops.lighter(ImageChops.lighter(differences[0], differences[1]), differences[2])
    color_mask = max_difference.point(lambda value: 255 if value <= 12 else 0)
    alpha_mask = overlay.getchannel("A").point(
        lambda value: 255 if value >= CLEARANCE_ALPHA_THRESHOLD else 0
    )
    return ImageChops.multiply(color_mask, alpha_mask).getbbox()


def maintained_hero_color(project_meta=None):
    current_treatments = read_json(CAPTION_STYLES)["expressiveTreatments"]
    if project_meta is None:
        return current_treatments["heroLine"]["color"]
    binding = project_meta.get("expressiveTreatments")
    if (not isinstance(binding, dict)
            or Path(binding.get("configPath", "")).resolve() != CAPTION_STYLES.resolve()
            or binding.get("configSha256") != sha256(CAPTION_STYLES)
            or binding.get("value") != current_treatments):
        raise ValueError("Expressive treatment project metadata binding is stale")
    return current_treatments["heroLine"]["color"]


def inspect_overlay_clearance(overlay, sample, beat, *, hero_color=None):
    alpha = overlay.getchannel("A")
    alpha_bbox = alpha.point(
        lambda value: 255 if value >= CLEARANCE_ALPHA_THRESHOLD else 0
    ).getbbox()
    entry_animation_blank = bool(
        alpha_bbox is None
        and sample.get("cue_entry_frame")
        and "spatial-boundary-after" in sample.get("purposes", [])
    )
    if sample.get("cue_index") is not None and alpha_bbox is None and not entry_animation_blank:
        raise ValueError(f"caption overlay is blank at cue {sample['cue_index']}")
    caption_bbox = list(alpha_bbox) if alpha_bbox else None
    width, height = overlay.size
    allowed_rect = sample.get("allowed_rect")
    if allowed_rect is None and beat:
        allowed_rect = beat.get("allowed_rect")
    allowed = _rect_pixels(allowed_rect, width, height)
    speaker = _rect_pixels(sample.get("speaker_rect"), width, height)
    placement = sample.get("resolved_placement") or (
        beat.get("resolved_placement") if beat else "preset-bottom"
    )
    if caption_bbox and placement in {"panel-center", "panel-bottom"} and (
        not allowed or caption_bbox[0] < allowed[0] or caption_bbox[1] < allowed[1]
        or caption_bbox[2] > allowed[2] or caption_bbox[3] > allowed[3]
    ):
        raise ValueError(
            f"cue {sample.get('cue_index')} {placement} bbox {caption_bbox} exceeds allowed rect {allowed}"
        )
    if caption_bbox and speaker and _intersects(caption_bbox, speaker):
        raise ValueError(
            f"cue {sample.get('cue_index')} {placement} bbox {caption_bbox} intersects speaker rect {speaker}"
        )
    hero_mask_bbox = _hero_bbox(
        overlay, hero_color or maintained_hero_color(),
    ) if sample.get("hero_line") else None
    hero_bbox = list(hero_mask_bbox) if hero_mask_bbox else None
    if sample.get("hero_line") and hero_bbox is None and not entry_animation_blank:
        raise ValueError(f"cue {sample.get('cue_index')} hero sample has no maintained hero pixels")
    if hero_bbox:
        bounds = allowed or [0, 0, width, height]
        if (hero_bbox[0] <= bounds[0] or hero_bbox[1] <= bounds[1]
                or hero_bbox[2] >= bounds[2] or hero_bbox[3] >= bounds[3]):
            raise ValueError(
                f"cue {sample.get('cue_index')} hero-line bbox {hero_bbox} clips bounds {bounds}"
            )
    return {
        "caption_bbox": caption_bbox,
        "caption_visibility": (
            "visible" if caption_bbox else
            "entry-animation-zero" if entry_animation_blank else "no-caption"
        ),
        "hero_bbox": hero_bbox,
        "allowed_rect_px": allowed,
        "speaker_rect_px": speaker,
        "clearance_status": "pass",
    }


def background_binding_for_sample(sample, context, project_root, source, source_s, source_hash):
    background = sample.get("background") if context else None
    if background:
        path = Path(background["path"])
        if not path.is_absolute():
            path = Path(project_root) / "work" / path
        path = path.resolve()
        if not path.is_file() or sha256(path) != background.get("sha256"):
            raise ValueError("spatial sample background is missing or stale")
        offset = float(sample["program_s"]) - float(background["program_start_s"])
        if offset < -1e-6:
            raise ValueError("spatial sample background offset is negative")
        return {
            "kind": background.get("kind", "normalized-broll-composite"),
            "path": str(path),
            "sha256": background["sha256"],
            "seek_s": max(0.0, offset),
            "program_start_s": background["program_start_s"],
        }
    return {
        "kind": "source-video",
        "path": str(source),
        "sha256": source_hash,
        "seek_s": source_s,
        "program_start_s": None,
    }


def comparison_sample(samples, requested_beat_id=None):
    beats = [sample for sample in samples if sample.get("kind") == "layout-beat"]
    if requested_beat_id:
        for sample in beats:
            if sample["beat_id"] == requested_beat_id:
                return sample
        raise ValueError(f"comparison beat does not exist: {requested_beat_id}")
    emphasized = [sample for sample in beats if sample.get("emphasized_words")]
    centered = [sample for sample in emphasized if sample.get("variant") == "center-emphasis"]
    return (centered or emphasized or beats)[0]


def capture_overlays(project, samples, output_dir):
    executable = shutil.which("npx.cmd") or shutil.which("npx")
    if not executable:
        raise RuntimeError("npx is required to capture HyperFrames preview snapshots")
    output_dir.mkdir(parents=True, exist_ok=True)
    times = ",".join(f"{item['program_s']:.12f}" for item in samples)
    subprocess.run([
        executable, "hyperframes", "snapshot", str(Path(project).resolve()),
        "--at", times, "--no-end", "--timeout", "60000", "--describe", "false",
        "--output", str(output_dir.resolve()),
    ], check=True)


def sorted_snapshot_files(directory):
    indexed = []
    for path in Path(directory).glob("frame-*.png"):
        match = re.match(r"frame-(\d+)", path.name)
        if not match:
            raise ValueError(f"invalid HyperFrames snapshot filename: {path.name}")
        indexed.append((int(match.group(1)), path))
    return [path for _, path in sorted(indexed)]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_interaction_state(path, source, plan, spatial_path=None, spatial_context=None):
    state = read_json(path)
    if state.get("schemaVersion") != 1 or state.get("skill") != "video-add-captions":
        raise ValueError("invalid video-add-captions interaction state")
    if state.get("decisionMode") not in ("human", "agent"):
        raise ValueError("caption interaction decisionMode must be human or agent")
    if state.get("phase") != "style_selected":
        raise ValueError("caption interaction must be in phase style_selected")
    if not str(state.get("reviewId", "")).strip():
        raise ValueError("caption interaction reviewId is required")
    if not str(state.get("selection", {}).get("choiceId", "")).strip():
        raise ValueError("caption interaction selection choiceId is required")
    for name, actual in (("sourceVideo", source), ("captions", plan)):
        binding = state.get(name, {})
        if binding.get("path") != str(actual) or binding.get("sha256") != sha256(actual):
            raise ValueError(f"caption interaction {name} binding does not match the requested input")
    binding = state.get("spatialContext")
    if spatial_context is None:
        if binding:
            raise ValueError("caption interaction unexpectedly binds a spatial context")
    else:
        if not binding or binding.get("path") != str(spatial_path) or binding.get("sha256") != sha256(spatial_path):
            raise ValueError("caption interaction spatial context binding does not match --spatial-context")
        if (binding.get("sourceOperation") != spatial_context.get("source", {}).get("operation_id")
                or binding.get("sourceRevision") != spatial_context.get("source", {}).get("operation_revision")):
            raise ValueError("caption interaction spatial context source binding is stale")
    return state


def read_project_meta(project):
    path = Path(project).resolve() / "project-meta.json"
    if not path.exists():
        raise ValueError(f"caption project metadata does not exist: {path}")
    return path, read_json(path)


def validate_expressive_comparison(primary_project, comparison_project, source, plan_path):
    primary_path, primary = read_project_meta(primary_project)
    comparison_path, comparison = read_project_meta(comparison_project)
    for label, meta in (("primary", primary), ("comparison", comparison)):
        if Path(meta.get("sourceVideo", "")).resolve() != source:
            raise ValueError(f"{label} expressive project source differs from --source")
        if Path(meta.get("captionsPath", "")).resolve() != plan_path:
            raise ValueError(f"{label} expressive project captions differ from --plan")
        if meta.get("presentation", {}).get("mode") != "expressive":
            raise ValueError(f"{label} comparison project is not Expressive")
    comparison_fields = (
        "width", "height", "fpsRational", "duration", "cueCount", "resolvedStyle",
        "spatialContext", "expressiveTreatments",
    )
    if any(primary.get(field) != comparison.get(field) for field in comparison_fields):
        raise ValueError("Expressive comparison must use the same dimensions, timing, cues, and resolved preset")
    if primary.get("presentation", {}).get("layoutBeats") != comparison.get("presentation", {}).get("layoutBeats"):
        raise ValueError("Expressive comparison must use the same layout beats")
    if primary.get("selection", {}).get("karaoke") is not False:
        raise ValueError("Primary Expressive review project must use karaoke off")
    if comparison.get("selection", {}).get("karaoke") is not True:
        raise ValueError("Expressive semantic-plus-karaoke comparison project must use karaoke on")
    return {
        "primary_project_meta": str(primary_path),
        "primary_project_meta_sha256": sha256(primary_path),
        "comparison_project_meta": str(comparison_path),
        "comparison_project_meta_sha256": sha256(comparison_path),
        "preset": primary.get("selection", {}).get("choiceId"),
    }


def write_review_page(path, evidence, review_evidence, comparison, state, timeline_path, timeline,
                      plan_path, mode, approval_evidence=None, spatial_context=None):
    template = REVIEW_TEMPLATE.read_text(encoding="utf-8")
    if template.count(REVIEW_MARKER) != 1:
        raise ValueError(f"caption review template must contain exactly one {REVIEW_MARKER} marker")
    payload = {
        "schema_version": 1,
        "review_id": state["reviewId"],
        "decision_mode": state["decisionMode"],
        "selection_id": state["selection"]["choiceId"],
        "timeline_id": timeline["timeline_id"],
        "timeline_sha256": sha256(timeline_path),
        "plan_sha256": sha256(plan_path),
        "presentation_mode": mode,
        "primary_evidence_count": len(review_evidence),
        "machine_evidence_count": len(evidence),
        "approval_evidence": approval_evidence or (
            "expressive-layout-beats" if mode == "expressive" else "standard-four"
        ),
        "samples": evidence,
        "review_samples": review_evidence,
        "experimental_comparison": comparison,
        "spatial_context": spatial_context,
    }
    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    path.write_text(template.replace(REVIEW_MARKER, encoded), encoding="utf-8")


def publish_review(stage, out):
    out.mkdir(parents=True, exist_ok=True)
    backup = out.with_name(f".{out.name}.{uuid.uuid4()}.bak")
    backup.mkdir()
    page_name = "captions-review.html"
    names = [item.name for item in stage.iterdir()]
    published = []
    try:
        # An old page must not remain usable while its bound evidence is replaced.
        ordered = [page_name, *(name for name in names if name != page_name)]
        for name in ordered:
            current = out / name
            if current.exists():
                os.replace(current, backup / name)
        for name in [*(name for name in names if name != page_name), page_name]:
            candidate = stage / name
            if candidate.exists():
                os.replace(candidate, out / name)
                published.append(name)
    except Exception:
        for name in published:
            current = out / name
            if current.exists():
                current.unlink()
        for previous in backup.iterdir():
            os.replace(previous, out / previous.name)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup.exists():
            shutil.rmtree(backup)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--interaction-state")
    parser.add_argument("--spatial-context")
    parser.add_argument("--project-root")
    parser.add_argument("--project")
    parser.add_argument("--snapshots")
    parser.add_argument("--comparison-project")
    parser.add_argument("--comparison-snapshots")
    parser.add_argument("--comparison-beat-id")
    args = parser.parse_args(argv)
    if bool(args.project) == bool(args.snapshots):
        parser.error("provide exactly one of --project or --snapshots")

    source = Path(args.source).resolve()
    timeline_path = Path(args.timeline).resolve()
    plan_path = Path(args.plan).resolve()
    timeline = read_json(timeline_path)
    plan = read_json(plan_path)
    errors = projectlib.validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))
    if plan.get("timeline_id") != timeline.get("timeline_id"):
        raise ValueError("caption plan timeline_id does not match timeline")
    spatial_binding = plan.get("spatial_context")
    spatial_context = None
    spatial_path = None
    project_root = Path(args.project_root).resolve() if args.project_root else None
    if spatial_binding:
        if not args.spatial_context or project_root is None:
            parser.error("a bound spatial context requires --spatial-context and --project-root")
        spatial_path = Path(args.spatial_context).resolve()
        if not spatial_path.is_file() or sha256(spatial_path) != spatial_binding.get("sha256"):
            raise ValueError("caption spatial context file/hash differs from the caption plan binding")
        expected_path = Path(spatial_binding["path"])
        if not expected_path.is_absolute():
            expected_path = project_root / "work" / expected_path
        if spatial_path != expected_path.resolve():
            raise ValueError("--spatial-context path differs from the caption plan binding")
        spatial_context = read_json(spatial_path)
        context_errors = caption_spatial_context.validate_context(
            spatial_context, plan, project_root, verify_files=True,
        )
        if context_errors:
            raise ValueError("invalid caption spatial context: " + "; ".join(context_errors))
    elif args.spatial_context or args.project_root:
        parser.error("spatial options are only valid when the caption plan binds spatial_context")
    fps = timeline["fps"]["num"] / timeline["fps"]["den"]
    has_hero_lines = any(cue.get("hero_line") for cue in plan.get("cues", []))
    samples = (
        spatial_sample_times(plan, timeline["fps"], spatial_context or {"placement_beats": []})
        if spatial_context or has_hero_lines else sample_times(plan, fps)
    )
    mode = plan.get("presentation", {}).get("mode", "standard")
    if mode == "expressive":
        if bool(args.comparison_project) == bool(args.comparison_snapshots):
            parser.error("Expressive review requires exactly one of --comparison-project or --comparison-snapshots")
        selected_comparison = comparison_sample(samples, args.comparison_beat_id)
    else:
        if args.comparison_project or args.comparison_snapshots or args.comparison_beat_id:
            parser.error("comparison options are only valid for Expressive review")
        selected_comparison = None
    interaction_state = (
        read_interaction_state(args.interaction_state, source, plan_path, spatial_path, spatial_context)
        if args.interaction_state else None
    )
    project_meta = None
    if args.project:
        _, project_meta = read_project_meta(args.project)
        if (project_meta.get("spatialContext", {}).get("sha256") if spatial_context else None) != (
            sha256(spatial_path) if spatial_context else None
        ):
            raise ValueError("caption project metadata spatial context binding is stale")

    cache = Path(args.cache).resolve()
    snapshots = Path(args.snapshots).resolve() if args.snapshots else cache / "overlay-snapshots"
    if args.project:
        capture_overlays(args.project, samples, snapshots)
    overlay_files = sorted_snapshot_files(snapshots)
    if len(overlay_files) != len(samples):
        raise ValueError(f"expected {len(samples)} overlay snapshots, found {len(overlay_files)}")
    comparison_overlay = None
    comparison_binding = None
    if selected_comparison:
        comparison_snapshots = (
            Path(args.comparison_snapshots).resolve()
            if args.comparison_snapshots else cache / "comparison-overlay-snapshots"
        )
        if args.comparison_project:
            capture_overlays(args.comparison_project, [selected_comparison], comparison_snapshots)
        comparison_files = sorted_snapshot_files(comparison_snapshots)
        if len(comparison_files) != 1:
            raise ValueError(f"expected 1 comparison overlay snapshot, found {len(comparison_files)}")
        comparison_overlay = comparison_files[0]
        if args.project and args.comparison_project:
            comparison_binding = validate_expressive_comparison(
                args.project, args.comparison_project, source, plan_path,
            )

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = out.with_name(f".{out.name}.{uuid.uuid4()}.tmp")
    source_frames = cache / "source-frames"
    stage.mkdir(parents=True)
    source_frames.mkdir(parents=True, exist_ok=True)
    evidence = []
    source_hash = sha256(source)
    spatial_beats = {
        beat["id"]: beat for beat in (spatial_context or {}).get("placement_beats", [])
    }
    hero_color = maintained_hero_color(project_meta)
    try:
        for sample, overlay_path in zip(samples, overlay_files):
            source_s = projectlib.program_to_source(timeline, sample["program_s"])
            if source_s is None:
                raise ValueError(f"program time does not map to source: {sample['program_s']}")
            background = background_binding_for_sample(
                sample, spatial_context, project_root, source, source_s, source_hash,
            )
            source_frame = source_frames / f"source-{sample['file_stem']}.png"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{background['seek_s']:.6f}", "-i", background["path"],
                "-frames:v", "1", str(source_frame),
            ], check=True)
            with Image.open(source_frame) as source_image, Image.open(overlay_path) as overlay_image:
                base = source_image.convert("RGBA")
                overlay = overlay_image.convert("RGBA")
                if overlay.size != base.size:
                    raise ValueError(f"overlay size {overlay.size} does not match source size {base.size}")
                clearance = inspect_overlay_clearance(
                    overlay, sample, spatial_beats.get(sample.get("spatial_beat_id")),
                    hero_color=hero_color,
                )
                preview = stage / f"preview-{sample['file_stem']}.png"
                Image.alpha_composite(base, overlay).convert("RGB").save(preview)
            evidence.append({
                **sample,
                "program_s": round(sample["program_s"], 12),
                "source_s": source_s,
                "background_kind": background["kind"],
                "background_path": background["path"],
                "background_sha256": background["sha256"],
                "background_offset_s": round(background["seek_s"], 6),
                **clearance,
                "preview": preview.name,
                "sha256": sha256(preview),
            })

        if mode == "standard" and not spatial_context:
            if tuple(item["label"] for item in evidence) != REVIEW_LABELS:
                raise ValueError("caption review requires exactly early, middle, late, and no-caption evidence")
        elif mode == "expressive" and not spatial_context:
            expected_beats = [beat["id"] for beat in plan["presentation"]["layout_beats"]]
            actual_beats = [item.get("beat_id") for item in evidence if item.get("kind") == "layout-beat"]
            hero_cues = [cue["index"] for cue in plan["cues"] if cue.get("hero_line")]
            if (actual_beats != expected_beats or not any(item["label"] == "no-caption" for item in evidence)
                    or any(not any(item.get("cue_index") == cue_index and item.get("hero_line")
                                   for item in evidence) for cue_index in hero_cues)):
                raise ValueError("Expressive review requires one ordered sample per layout beat plus no-caption")
        with Image.open(stage / evidence[0]["preview"]) as first:
            preview_size = first.size
        for item in evidence:
            with Image.open(stage / item["preview"]) as image:
                if image.size != preview_size or image.getbbox() is None:
                    raise ValueError("caption review previews must be nonblank and have equal dimensions")

        comparison = None
        if selected_comparison:
            primary = next(item for item in evidence if item.get("beat_id") == selected_comparison["beat_id"])
            semantic_preview = stage / f"comparison-semantic-only-{selected_comparison['file_stem']}.png"
            shutil.copy2(stage / primary["preview"], semantic_preview)
            source_frame = source_frames / f"source-{selected_comparison['file_stem']}.png"
            with Image.open(source_frame) as source_image, Image.open(comparison_overlay) as overlay_image:
                base = source_image.convert("RGBA")
                overlay = overlay_image.convert("RGBA")
                if overlay.size != base.size:
                    raise ValueError("comparison overlay dimensions differ from the primary source frame")
                if overlay.getchannel("A").getextrema()[1] == 0:
                    raise ValueError("Expressive semantic-plus-karaoke comparison overlay is blank")
                combined_preview = stage / f"comparison-karaoke-on-{selected_comparison['file_stem']}.png"
                Image.alpha_composite(base, overlay).convert("RGB").save(combined_preview)
            comparison = {
                "experimental": True,
                "beat_id": selected_comparison["beat_id"],
                "variant": selected_comparison["variant"],
                "cue_ids": selected_comparison["cue_ids"],
                "program_s": primary["program_s"],
                "source_s": primary["source_s"],
                "displayed_text": selected_comparison["displayed_text"],
                "emphasized_words": selected_comparison["emphasized_words"],
                "warnings": selected_comparison["warnings"],
                "project_binding": comparison_binding,
                "samples": [
                    {
                        "mode": "semantic-only",
                        "karaoke": False,
                        "preview": semantic_preview.name,
                        "sha256": sha256(semantic_preview),
                    },
                    {
                        "mode": "semantic-plus-karaoke",
                        "karaoke": True,
                        "preview": combined_preview.name,
                        "sha256": sha256(combined_preview),
                    },
                ],
            }

        review_evidence = (
            select_review_samples(evidence)
            if spatial_context or mode == "expressive" else copy.deepcopy(evidence)
        )
        if (spatial_context or mode == "expressive") and not review_evidence:
            raise ValueError("caption review has no maintained representative evidence")
        evidence_document = {
            "schema_version": 1,
            "timeline_id": timeline["timeline_id"],
            "timeline_sha256": sha256(timeline_path),
            "samples": evidence,
            "machine_evidence_count": len(evidence),
            "review_samples": review_evidence,
            "primary_evidence_count": len(review_evidence),
        }
        approval_evidence = (
            "composite-aware" if spatial_context else
            "expressive-layout-beats" if mode == "expressive" else "standard-four"
        )
        if spatial_context:
            evidence_document["spatial_context"] = {
                "path": str(spatial_path),
                "sha256": sha256(spatial_path),
                "source": spatial_context["source"],
                "placement_beat_count": len(spatial_context["placement_beats"]),
            }
        if mode == "expressive":
            evidence_document.update({
                "presentation_mode": "expressive",
                "experimental_comparison": comparison,
            })
        projectlib.write_json(stage / "captions-evidence.json", evidence_document)
        lines = ["# Caption Review", "", "Source-backed caption evidence generated from the approved timeline.", ""]
        if mode == "standard":
            lines.extend([
                "| Sample | Program | Source | Cue | Preview |", "|---|---:|---:|---|---|",
            ])
            for item in (review_evidence if spatial_context else evidence):
                cue = item["cue_text"] or "None"
                lines.append(
                    f"| {item['label']} | {item['program_s']:.3f}s | {item['source_s']:.3f}s | "
                    f"{cue.replace('|', '/')} | `{item['preview']}` |"
                )
        else:
            lines.extend([
                "| Beat | Variant | Cues | Program | Source | Displayed text | Emphasized | Warnings | Preview |",
                "|---|---|---|---:|---:|---|---|---|---|",
            ])
            for item in review_evidence:
                warnings = "; ".join(item.get("warnings", [])) or "None"
                lines.append(
                    f"| {item.get('beat_id', item['label'])} | {item.get('variant', 'none')} | "
                    f"{', '.join(item.get('cue_ids', [])) or 'None'} | {item['program_s']:.3f}s | "
                    f"{item['source_s']:.3f}s | {(item.get('displayed_text') or 'None').replace('|', '/')} | "
                    f"{', '.join(item.get('emphasized_words', [])) or 'None'} | {warnings.replace('|', '/')} | "
                    f"`{item['preview']}` |"
                )
            lines.extend([
                "", "## Expressive + Karaoke Comparison", "",
                f"- Beat: `{comparison['beat_id']}`",
                f"- Variant: `{comparison['variant']}`",
                f"- Program/source: `{comparison['program_s']:.3f}s` / `{comparison['source_s']:.3f}s`",
                f"- Semantic only: `{comparison['samples'][0]['preview']}`",
                f"- Semantic plus Karaoke: `{comparison['samples'][1]['preview']}`",
            ])
        (stage / "captions-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if interaction_state:
            write_review_page(
                stage / "captions-review.html", evidence, review_evidence, comparison, interaction_state,
                timeline_path, timeline, plan_path, mode,
                approval_evidence=approval_evidence,
                spatial_context=evidence_document.get("spatial_context"),
            )
        publish_review(stage, out)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(
        f"[caption-review] wrote {len(evidence)} machine previews and "
        f"{len(review_evidence)} human review representatives to {out}"
    )


if __name__ == "__main__":
    main()
