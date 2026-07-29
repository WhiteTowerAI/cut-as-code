"""Build source-backed Standard or Expressive caption review stills."""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from PIL import Image


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


REVIEW_TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "captions-review.html"
REVIEW_MARKER = "__CAPTION_EVIDENCE_REVIEW_DATA__"
REVIEW_PAYLOAD_PATTERN = re.compile(r'const REVIEW_DATA_B64 = "([A-Za-z0-9+/=]+)";')
REVIEW_LABELS = ("early", "middle", "late", "no-caption")
EXPRESSIVE_VARIANTS = ("bottom-standard", "center-emphasis")


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
            "warnings": warnings,
        })
    samples.append(no_caption_sample(cues, float(plan["program_duration_s"]), fps))
    return samples


def sample_times(plan, fps):
    if plan.get("presentation", {}).get("mode") == "expressive":
        return expressive_sample_times(plan, fps)
    return standard_sample_times(plan, fps)


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
    times = ",".join(f"{item['program_s']:.6f}" for item in samples)
    subprocess.run([
        executable, "hyperframes", "snapshot", str(Path(project).resolve()),
        "--at", times, "--no-end", "--timeout", "60000", "--describe", "false",
        "--output", str(output_dir.resolve()),
    ], check=True)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_interaction_state(path, source, plan):
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


def write_review_page(path, evidence, comparison, state, timeline_path, timeline, plan_path, mode):
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
        "primary_evidence_count": len(evidence),
        "approval_evidence": "expressive-layout-beats" if mode == "expressive" else "standard-four",
        "samples": evidence,
        "experimental_comparison": comparison,
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
    fps = timeline["fps"]["num"] / timeline["fps"]["den"]
    samples = sample_times(plan, fps)
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
        read_interaction_state(args.interaction_state, source, plan_path)
        if args.interaction_state else None
    )

    cache = Path(args.cache).resolve()
    snapshots = Path(args.snapshots).resolve() if args.snapshots else cache / "overlay-snapshots"
    if args.project:
        capture_overlays(args.project, samples, snapshots)
    overlay_files = sorted(snapshots.glob("frame-*.png"))
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
        comparison_files = sorted(comparison_snapshots.glob("frame-*.png"))
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
    try:
        for sample, overlay_path in zip(samples, overlay_files):
            source_s = projectlib.program_to_source(timeline, sample["program_s"])
            if source_s is None:
                raise ValueError(f"program time does not map to source: {sample['program_s']}")
            source_frame = source_frames / f"source-{sample['file_stem']}.png"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{source_s:.6f}", "-i", str(source), "-frames:v", "1", str(source_frame),
            ], check=True)
            with Image.open(source_frame) as source_image, Image.open(overlay_path) as overlay_image:
                base = source_image.convert("RGBA")
                overlay = overlay_image.convert("RGBA")
                if overlay.size != base.size:
                    raise ValueError(f"overlay size {overlay.size} does not match source size {base.size}")
                if sample["cue_index"] is not None and overlay.getchannel("A").getextrema()[1] == 0:
                    raise ValueError(f"caption overlay is blank at {sample['label']} sample")
                preview = stage / f"preview-{sample['file_stem']}.png"
                Image.alpha_composite(base, overlay).convert("RGB").save(preview)
            evidence.append({
                **sample,
                "program_s": round(sample["program_s"], 6),
                "source_s": source_s,
                "preview": preview.name,
                "sha256": sha256(preview),
            })

        if mode == "standard":
            if tuple(item["label"] for item in evidence) != REVIEW_LABELS:
                raise ValueError("caption review requires exactly early, middle, late, and no-caption evidence")
        else:
            expected_beats = [beat["id"] for beat in plan["presentation"]["layout_beats"]]
            actual_beats = [item.get("beat_id") for item in evidence if item.get("kind") == "layout-beat"]
            if actual_beats != expected_beats or evidence[-1]["label"] != "no-caption":
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

        evidence_document = {
            "schema_version": 1,
            "timeline_id": timeline["timeline_id"],
            "timeline_sha256": sha256(timeline_path),
            "samples": evidence,
        }
        if mode == "expressive":
            evidence_document.update({
                "presentation_mode": "expressive",
                "primary_evidence_count": len(evidence),
                "experimental_comparison": comparison,
            })
        projectlib.write_json(stage / "captions-evidence.json", evidence_document)
        lines = ["# Caption Review", "", "Source-backed caption evidence generated from the approved timeline.", ""]
        if mode == "standard":
            lines.extend([
                "| Sample | Program | Source | Cue | Preview |", "|---|---:|---:|---|---|",
            ])
            for item in evidence:
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
            for item in evidence:
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
                stage / "captions-review.html", evidence, comparison, interaction_state,
                timeline_path, timeline, plan_path, mode,
            )
        publish_review(stage, out)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(f"[caption-review] wrote {len(evidence)} source-backed previews to {out}")


if __name__ == "__main__":
    main()
