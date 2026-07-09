#!/usr/bin/env python3
"""Prepare a transcript for video-to-shorts Phase 1.

This script only prepares transcript artifacts and previews. It does not choose
highlights, call an LLM, or cut video.
"""

import argparse
import html
import json
import math
import shutil
import subprocess
from pathlib import Path


def fail(message):
    raise SystemExit(message)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "command failed: " + " ".join(str(c) for c in cmd) + "\n" + p.stderr.strip()
        )
    return p.stdout


def resolve_tool(name, explicit=None, near=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        fail(f"{name} not found: {explicit}")
    found = shutil.which(name)
    if found:
        return found
    if near:
        candidate = Path(near).with_name(name + ".exe")
        if candidate.exists():
            return str(candidate)
    fail(f"{name} not found. Pass --{name} PATH.")


def repo_root_from_script():
    return Path(__file__).resolve().parents[3]


def discover_transcript(video_path, explicit_transcript):
    if explicit_transcript:
        p = Path(explicit_transcript)
        if not p.exists():
            fail(f"explicit transcript not found: {p}")
        return p, "explicit"

    video_dir = video_path.parent
    candidates = [
        (video_dir / "cut_transcript.json", "adjacent_cut_transcript"),
        (video_dir / "work" / "selfcheck" / "cut_transcript.json", "rough_cut_selfcheck"),
    ]
    for p, label in candidates:
        if p.exists():
            return p, label
    return None, "generated_by_whisper"


def probe_duration(video_path, ffprobe=None):
    if not ffprobe:
        return None
    data = json.loads(run([
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path),
    ]))
    duration = data.get("format", {}).get("duration")
    return float(duration) if duration is not None else None


def copy_transcript(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def generate_transcript(video_path, out_dir, ffmpeg, python_exe, model, lang):
    repo = repo_root_from_script()
    transcribe = repo / "skills" / "video-rough-cut" / "scripts" / "transcribe.py"
    if not transcribe.exists():
        fail(f"transcribe.py not found: {transcribe}")

    audio_path = out_dir / "audio16k.wav"
    out_prefix = out_dir / "transcript"
    run([
        ffmpeg,
        "-y",
        "-i", str(video_path),
        "-ac", "1",
        "-ar", "16000",
        str(audio_path),
    ])
    run([
        python_exe,
        str(transcribe),
        str(audio_path),
        str(out_prefix),
        model,
        "--lang",
        lang,
    ])
    return out_prefix.with_suffix(".json")


def load_transcript(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("segments"), list):
        fail(f"transcript has no segments array: {path}")
    return data


def segment_words(segment):
    words = segment.get("words") or []
    if words:
        return [str(w.get("word", "")).strip() for w in words if str(w.get("word", "")).strip()]
    return [w for w in str(segment.get("text", "")).strip().split() if w]


def transcript_duration(transcript, video_duration):
    if isinstance(transcript.get("duration"), (int, float)):
        return float(transcript["duration"])
    segments = transcript.get("segments") or []
    if segments:
        return max(float(s.get("end", 0.0)) for s in segments)
    return float(video_duration or 0.0)


def minute_stats(transcript, duration):
    minute_count = max(1, int(math.ceil(duration / 60.0)))
    stats = []
    for minute in range(minute_count):
        start = minute * 60.0
        end = min(duration, start + 60.0)
        stats.append({
            "minute": minute,
            "start": start,
            "end": end,
            "words": 0,
            "speech_s": 0.0,
            "segments": 0,
        })

    for seg in transcript.get("segments", []):
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", seg_start))
        words = segment_words(seg)
        mid = max(0, min(len(stats) - 1, int(seg_start // 60.0)))
        stats[mid]["words"] += len(words)
        stats[mid]["segments"] += 1
        stats[mid]["speech_s"] += max(0.0, seg_end - seg_start)

    for item in stats:
        dur = max(0.001, item["end"] - item["start"])
        item["wpm"] = round(item["words"] / dur * 60.0, 1)
        item["speech_density"] = round(min(1.0, item["speech_s"] / dur), 3)
    return stats


def rough_short_hints(transcript, stats, duration):
    scored = []
    hook_terms = {
        "new", "major", "growth", "driver", "faster", "times", "incredible",
        "risk", "dangerous", "revolutionary", "real-time", "real", "ai",
    }
    for item in stats:
        start = item["start"]
        end = item["end"]
        segs = [
            s for s in transcript.get("segments", [])
            if float(s.get("start", 0.0)) < end and float(s.get("end", 0.0)) > start
        ]
        text = " ".join(str(s.get("text", "")).strip() for s in segs)
        lower = text.lower()
        hook_score = sum(1 for term in hook_terms if term in lower)
        number_score = 2 if any(ch.isdigit() for ch in text) else 0
        score = item["wpm"] + item["speech_density"] * 40 + hook_score * 4 + number_score
        if item["words"] >= 18:
            scored.append((score, item, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    hints = []
    for score, item, text in scored[:5]:
        hint_start = item["start"]
        hint_end = min(duration, max(item["end"], hint_start + 30.0))
        excerpt = " ".join(text.split())
        if len(excerpt) > 220:
            excerpt = excerpt[:217].rstrip() + "..."
        hints.append({
            "start": hint_start,
            "end": hint_end,
            "score": round(score, 1),
            "reason": f"{item['words']} words, {item['wpm']} wpm, density {item['speech_density']}",
            "excerpt": excerpt,
        })
    return hints


def fmt_time(seconds):
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def write_markdown(out_path, source_label, source_path, video_path, duration, transcript, stats, hints):
    lines = [
        "# Transcript Preview",
        "",
        f"- Transcript source: `{source_label}`",
        f"- Transcript path: `{source_path}`",
        f"- Video path: `{video_path}`",
        f"- Total duration: `{duration:.3f}s`",
        f"- Segments: `{len(transcript.get('segments', []))}`",
        "",
        "## First 20 Segments",
        "",
        "| # | Time | Text |",
        "|---:|---|---|",
    ]
    for idx, seg in enumerate(transcript.get("segments", [])[:20], start=1):
        text = str(seg.get("text", "")).strip().replace("|", "\\|")
        lines.append(f"| {idx} | {fmt_time(seg.get('start', 0))} - {fmt_time(seg.get('end', 0))} | {text} |")

    lines += [
        "",
        "## Per-Minute Speech Stats",
        "",
        "| Minute | Time | Words | WPM | Speech Density | Segments |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for item in stats:
        lines.append(
            f"| {item['minute']} | {fmt_time(item['start'])} - {fmt_time(item['end'])} | "
            f"{item['words']} | {item['wpm']} | {item['speech_density']} | {item['segments']} |"
        )

    lines += [
        "",
        "## Rough Shorts Hints",
        "",
        "These are heuristic hints only. They are not LLM highlights and should be reviewed before Phase 1 candidate selection.",
        "",
        "| Rank | Time | Score | Reason | Excerpt |",
        "|---:|---|---:|---|---|",
    ]
    for idx, hint in enumerate(hints, start=1):
        excerpt = hint["excerpt"].replace("|", "\\|")
        lines.append(
            f"| {idx} | {fmt_time(hint['start'])} - {fmt_time(hint['end'])} | "
            f"{hint['score']} | {hint['reason']} | {excerpt} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(out_path, md_path, source_label, source_path, video_path, duration, transcript, stats, hints):
    def esc(value):
        return html.escape(str(value))

    segment_rows = []
    for idx, seg in enumerate(transcript.get("segments", [])[:20], start=1):
        segment_rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{esc(fmt_time(seg.get('start', 0)))} - {esc(fmt_time(seg.get('end', 0)))}</td>"
            f"<td>{esc(str(seg.get('text', '')).strip())}</td>"
            "</tr>"
        )

    stat_rows = []
    for item in stats:
        stat_rows.append(
            "<tr>"
            f"<td>{item['minute']}</td>"
            f"<td>{esc(fmt_time(item['start']))} - {esc(fmt_time(item['end']))}</td>"
            f"<td>{item['words']}</td>"
            f"<td>{item['wpm']}</td>"
            f"<td>{item['speech_density']}</td>"
            f"<td>{item['segments']}</td>"
            "</tr>"
        )

    hint_rows = []
    for idx, hint in enumerate(hints, start=1):
        hint_rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{esc(fmt_time(hint['start']))} - {esc(fmt_time(hint['end']))}</td>"
            f"<td>{hint['score']}</td>"
            f"<td>{esc(hint['reason'])}</td>"
            f"<td>{esc(hint['excerpt'])}</td>"
            "</tr>"
        )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Transcript Preview</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; line-height: 1.45; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #eef2f7; text-align: left; }}
    td:first-child, th:first-child {{ width: 64px; text-align: right; }}
    .note {{ color: #52606d; }}
  </style>
</head>
<body>
  <h1>Transcript Preview</h1>
  <ul>
    <li>Transcript source: <code>{esc(source_label)}</code></li>
    <li>Transcript path: <code>{esc(source_path)}</code></li>
    <li>Video path: <code>{esc(video_path)}</code></li>
    <li>Total duration: <code>{duration:.3f}s</code></li>
    <li>Segments: <code>{len(transcript.get('segments', []))}</code></li>
    <li>Markdown preview: <code>{esc(md_path.name)}</code></li>
  </ul>
  <h2>First 20 Segments</h2>
  <table><thead><tr><th>#</th><th>Time</th><th>Text</th></tr></thead><tbody>
    {''.join(segment_rows)}
  </tbody></table>
  <h2>Per-Minute Speech Stats</h2>
  <table><thead><tr><th>Minute</th><th>Time</th><th>Words</th><th>WPM</th><th>Speech Density</th><th>Segments</th></tr></thead><tbody>
    {''.join(stat_rows)}
  </tbody></table>
  <h2>Rough Shorts Hints</h2>
  <p class="note">These are heuristic hints only. They are not LLM highlights and should be reviewed before Phase 1 candidate selection.</p>
  <table><thead><tr><th>Rank</th><th>Time</th><th>Score</th><th>Reason</th><th>Excerpt</th></tr></thead><tbody>
    {''.join(hint_rows)}
  </tbody></table>
</body>
</html>
"""
    out_path.write_text(html_doc, encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare transcript artifacts for video-to-shorts.")
    parser.add_argument("video", help="Input video path.")
    parser.add_argument("--transcript", help="Optional explicit transcript JSON path.")
    parser.add_argument("--out", required=True, help="Output directory, normally work/shorts.")
    parser.add_argument("--ffmpeg", help="ffmpeg path, required only when transcript must be generated.")
    parser.add_argument("--ffprobe", help="ffprobe path, optional for video duration probing.")
    parser.add_argument("--python", default="python", help="Python executable used to call rough-cut transcribe.py.")
    parser.add_argument("--model", default="base.en", help="Whisper model for generated transcripts.")
    parser.add_argument("--lang", default="en", help="Whisper language code for generated transcripts.")
    return parser.parse_args()


def main():
    args = parse_args()
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        fail(f"video not found: {video_path}")
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    source_transcript, source_kind = discover_transcript(video_path, args.transcript)
    target_transcript = out_dir / "transcript.json"

    ffprobe = None
    if args.ffprobe:
        ffprobe = resolve_tool("ffprobe", args.ffprobe)
    elif shutil.which("ffprobe"):
        ffprobe = shutil.which("ffprobe")

    if source_transcript:
        copy_transcript(source_transcript, target_transcript)
        source_label = source_kind
        source_path_for_preview = str(source_transcript)
    else:
        ffmpeg = resolve_tool("ffmpeg", args.ffmpeg)
        generated = generate_transcript(video_path, out_dir, ffmpeg, args.python, args.model, args.lang)
        if generated != target_transcript:
            copy_transcript(generated, target_transcript)
        source_label = "generated_by_whisper"
        source_path_for_preview = str(target_transcript)

    transcript = load_transcript(target_transcript)
    video_duration = probe_duration(video_path, ffprobe) if ffprobe else None
    duration = transcript_duration(transcript, video_duration)
    stats = minute_stats(transcript, duration)
    hints = rough_short_hints(transcript, stats, duration)

    md_path = out_dir / "transcript_preview.md"
    html_path = out_dir / "transcript_preview.html"
    write_markdown(md_path, source_label, source_path_for_preview, video_path, duration, transcript, stats, hints)
    write_html(html_path, md_path, source_label, source_path_for_preview, video_path, duration, transcript, stats, hints)

    print(f"[video-to-shorts] transcript: {target_transcript}")
    print(f"[video-to-shorts] preview md: {md_path}")
    print(f"[video-to-shorts] preview html: {html_path}")
    print(f"[video-to-shorts] source: {source_label}")
    print(f"[video-to-shorts] duration_s: {duration:.3f}")
    print(f"[video-to-shorts] segments: {len(transcript.get('segments', []))}")


if __name__ == "__main__":
    main()
