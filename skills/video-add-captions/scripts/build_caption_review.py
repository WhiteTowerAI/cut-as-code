"""Build source-backed early/middle/late/no-caption review stills."""

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


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sample_times(plan, fps):
    cues = sorted(plan["cues"], key=lambda cue: float(cue["start"]))
    if not cues:
        raise ValueError("caption plan has no cues")
    indexes = (0, (len(cues) - 1) // 2, len(cues) - 1)
    samples = []
    for label, index in zip(("early", "middle", "late"), indexes):
        cue = cues[index]
        samples.append({
            "label": label,
            "program_s": (float(cue["start"]) + float(cue["end"])) / 2,
            "cue_index": cue.get("index", index + 1),
            "cue_text": cue.get("text", ""),
        })

    duration = float(plan["program_duration_s"])
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
    samples.append({
        "label": "no-caption",
        "program_s": (gap[0] + gap[1]) / 2,
        "cue_index": None,
        "cue_text": "",
    })
    return samples


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


def write_review_page(path, evidence, state, timeline_path, timeline):
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
        "samples": evidence,
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
            source_frame = source_frames / f"source-{sample['label']}.png"
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
                preview = stage / f"preview-{sample['label']}.png"
                Image.alpha_composite(base, overlay).convert("RGB").save(preview)
            evidence.append({
                **sample,
                "program_s": round(sample["program_s"], 6),
                "source_s": source_s,
                "preview": preview.name,
                "sha256": sha256(preview),
            })

        if tuple(item["label"] for item in evidence) != REVIEW_LABELS:
            raise ValueError("caption review requires exactly early, middle, late, and no-caption evidence")
        with Image.open(stage / evidence[0]["preview"]) as first:
            preview_size = first.size
        for item in evidence:
            with Image.open(stage / item["preview"]) as image:
                if image.size != preview_size or image.getbbox() is None:
                    raise ValueError("caption review previews must be nonblank and have equal dimensions")

        projectlib.write_json(stage / "captions-evidence.json", {
            "schema_version": 1,
            "timeline_id": timeline["timeline_id"],
            "timeline_sha256": sha256(timeline_path),
            "samples": evidence,
        })
        lines = [
            "# Caption Review", "", "Source-backed caption evidence generated from the approved timeline.", "",
            "| Sample | Program | Source | Cue | Preview |", "|---|---:|---:|---|---|",
        ]
        for item in evidence:
            cue = item["cue_text"] or "None"
            lines.append(
                f"| {item['label']} | {item['program_s']:.3f}s | {item['source_s']:.3f}s | "
                f"{cue.replace('|', '/')} | `{item['preview']}` |"
            )
        (stage / "captions-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if interaction_state:
            write_review_page(
                stage / "captions-review.html", evidence, interaction_state, timeline_path, timeline
            )
        publish_review(stage, out)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(f"[caption-review] wrote {len(evidence)} source-backed previews to {out}")


if __name__ == "__main__":
    main()
