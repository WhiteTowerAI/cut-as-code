"""Build source-backed early/middle/late/no-caption review stills."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--project")
    parser.add_argument("--snapshots")
    args = parser.parse_args(argv)
    if bool(args.project) == bool(args.snapshots):
        parser.error("provide exactly one of --project or --snapshots")

    source = Path(args.source).resolve()
    timeline = read_json(args.timeline)
    plan = read_json(args.plan)
    errors = projectlib.validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))
    if plan.get("timeline_id") != timeline.get("timeline_id"):
        raise ValueError("caption plan timeline_id does not match timeline")
    fps = timeline["fps"]["num"] / timeline["fps"]["den"]
    samples = sample_times(plan, fps)

    cache = Path(args.cache).resolve()
    snapshots = Path(args.snapshots).resolve() if args.snapshots else cache / "overlay-snapshots"
    if args.project:
        capture_overlays(args.project, samples, snapshots)
    overlay_files = sorted(snapshots.glob("frame-*.png"))
    if len(overlay_files) != len(samples):
        raise ValueError(f"expected {len(samples)} overlay snapshots, found {len(overlay_files)}")

    out = Path(args.out).resolve()
    source_frames = cache / "source-frames"
    out.mkdir(parents=True, exist_ok=True)
    source_frames.mkdir(parents=True, exist_ok=True)
    evidence = []
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
            preview = out / f"preview-{sample['label']}.png"
            Image.alpha_composite(base, overlay).convert("RGB").save(preview)
        evidence.append({
            **sample,
            "program_s": round(sample["program_s"], 6),
            "source_s": source_s,
            "preview": preview.name,
            "sha256": sha256(preview),
        })

    projectlib.write_json(out / "captions-evidence.json", {
        "schema_version": 1,
        "timeline_id": timeline["timeline_id"],
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
    (out / "captions-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[caption-review] wrote {len(evidence)} source-backed previews to {out}")


if __name__ == "__main__":
    main()
