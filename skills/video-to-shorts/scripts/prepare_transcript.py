#!/usr/bin/env python3
"""Prepare the standard word-level transcript consumed by video-to-shorts."""

import argparse
import hashlib
import html
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


def fail(message):
    raise SystemExit(message)


def run(command):
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(map(str, command)) + "\n" + process.stderr.strip())
    return process.stdout


def resolve_tool(name, explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if path.exists():
            return str(path)
        fail(f"{name} not found: {path}")
    found = shutil.which(name)
    if found:
        return found
    fail(f"{name} not found. Pass --{name} PATH.")


def repo_root():
    return Path(__file__).resolve().parents[3]


def validate_number(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{path} must be a number")


def load_and_validate_transcript(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid transcript JSON: {path}: {error}")
    segments = data.get("segments")
    if not isinstance(segments, list):
        fail(f"transcript must contain a segments array: {path}")
    normalized_segments = []
    for segment_index, segment in enumerate(segments):
        segment_path = f"segments[{segment_index}]"
        if not isinstance(segment, dict):
            fail(f"{segment_path} must be an object")
        for field in ("start", "end", "text"):
            if field not in segment:
                fail(f"{segment_path} missing {field}")
        validate_number(segment["start"], f"{segment_path}.start")
        validate_number(segment["end"], f"{segment_path}.end")
        if segment["start"] < 0 or segment["end"] < segment["start"]:
            fail(f"{segment_path} has an invalid time range")
        if not isinstance(segment["text"], str):
            fail(f"{segment_path}.text must be a string")
        normalized = dict(segment)
        if "words" in segment:
            if not isinstance(segment["words"], list):
                fail(f"{segment_path}.words must be an array")
            normalized_words = []
            for word_index, word in enumerate(segment["words"]):
                word_path = f"{segment_path}.words[{word_index}]"
                if not isinstance(word, dict):
                    fail(f"{word_path} must be an object")
                for field in ("start", "end", "word"):
                    if field not in word:
                        fail(f"{word_path} missing {field}")
                validate_number(word["start"], f"{word_path}.start")
                validate_number(word["end"], f"{word_path}.end")
                if word["start"] < 0 or word["end"] < word["start"]:
                    fail(f"{word_path} has an invalid time range")
                if not isinstance(word["word"], str):
                    fail(f"{word_path}.word must be a string")
                normalized_words.append(dict(word))
            normalized["words"] = normalized_words
        normalized_segments.append(normalized)
    normalized = dict(data)
    normalized["segments"] = normalized_segments
    return normalized


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_binding(path):
    path = Path(path).resolve()
    stat = path.stat()
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def generate_fallback(video_path, out_dir, ffmpeg, python_exe, model, lang):
    transcribe = repo_root() / "skills" / "video-understand" / "scripts" / "transcribe.py"
    if not transcribe.exists():
        fail(f"fallback transcriber not found: {transcribe}")
    audio_path = out_dir / "audio16k.wav"
    run([ffmpeg, "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", str(audio_path)])
    model_cache = out_dir.parent / "cache" / "shorts" / "whisper"
    model_cache.mkdir(parents=True, exist_ok=True)
    run([
        python_exe, str(transcribe), str(audio_path), str(out_dir / "generated-transcript"), model,
        "--lang", lang, "--cache-dir", str(model_cache),
    ])
    return out_dir / "generated-transcript.json"


def prepare_transcript_data(transcript, timeline=None):
    return projectlib.map_transcript_to_timeline(transcript, timeline) if timeline else transcript


def probe_video_duration(video_path, ffprobe):
    if not ffprobe:
        return None
    payload = json.loads(run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]))
    value = payload.get("format", {}).get("duration")
    return float(value) if value is not None else None


def transcript_duration(transcript, video_duration):
    if isinstance(transcript.get("duration"), (int, float)):
        return float(transcript["duration"])
    if transcript["segments"]:
        return max(float(segment["end"]) for segment in transcript["segments"])
    return float(video_duration or 0)


def segment_words(segment):
    if isinstance(segment.get("words"), list):
        return [word["word"].strip() for word in segment["words"] if word["word"].strip()]
    return segment["text"].split()


def minute_stats(transcript, duration):
    stats = []
    for minute in range(max(1, math.ceil(duration / 60))):
        start = minute * 60.0
        end = min(duration, start + 60.0)
        stats.append({"minute": minute, "start": start, "end": end, "words": 0, "segments": 0, "speech_s": 0.0})
    for segment in transcript["segments"]:
        bucket = min(len(stats) - 1, max(0, int(segment["start"] // 60)))
        stats[bucket]["words"] += len(segment_words(segment))
        stats[bucket]["segments"] += 1
        stats[bucket]["speech_s"] += max(0.0, segment["end"] - segment["start"])
    for item in stats:
        bucket_duration = max(0.001, item["end"] - item["start"])
        item["wpm"] = round(item["words"] / bucket_duration * 60, 1)
        item["speech_density"] = round(min(1.0, item["speech_s"] / bucket_duration), 3)
    return stats


def fmt_time(seconds):
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds - minutes * 60:05.2f}"


def write_preview_md(path, metadata, transcript, stats):
    total_words = sum(item["words"] for item in stats)
    speech_s = round(sum(item["speech_s"] for item in stats), 3)
    lines = ["# Transcript Preview", "", "## Metadata", "",
             f"- Video: `{metadata['video']}`", f"- Acquisition mode: `{metadata['acquisition_mode']}`",
             f"- Source transcript: `{metadata.get('source_transcript', '')}`", f"- Generator: `{metadata.get('generator', '')}`",
             f"- Duration: `{metadata['duration_s']}s`", f"- Segments: `{len(transcript['segments'])}`",
             f"- Words: `{total_words}`", f"- Speech duration: `{speech_s}s`", "", "## Minute Statistics", "",
             "| Minute | Range | Words | Segments | Speech s | WPM | Speech density |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for item in stats:
        lines.append(f"| {item['minute']} | {fmt_time(item['start'])}-{fmt_time(item['end'])} | {item['words']} | {item['segments']} | {item['speech_s']:.3f} | {item['wpm']} | {item['speech_density']} |")
    lines.extend(["", "## Transcript Segments", "", "| # | Time | Text | Words |", "|---:|---|---|---:|"])
    for index, segment in enumerate(transcript["segments"], 1):
        text = segment["text"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {index} | {fmt_time(segment['start'])}-{fmt_time(segment['end'])} | {text} | {len(segment_words(segment))} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_preview_html(path, metadata, transcript, stats):
    esc = lambda value: html.escape(str(value))
    stat_rows = "".join(f"<tr><td>{item['minute']}</td><td>{fmt_time(item['start'])}-{fmt_time(item['end'])}</td><td>{item['words']}</td><td>{item['segments']}</td><td>{item['speech_s']:.3f}</td><td>{item['wpm']}</td><td>{item['speech_density']}</td></tr>" for item in stats)
    segment_rows = "".join(f"<tr><td>{index}</td><td>{fmt_time(segment['start'])}-{fmt_time(segment['end'])}</td><td>{esc(segment['text'])}</td><td>{len(segment_words(segment))}</td></tr>" for index, segment in enumerate(transcript["segments"], 1))
    path.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>Transcript Preview</title><style>body{{font-family:Arial,sans-serif;margin:24px;color:#1f2933}}table{{border-collapse:collapse;width:100%;margin:16px 0}}th,td{{border:1px solid #d8dee9;padding:7px;vertical-align:top}}th{{background:#eef2f7;text-align:left}}code{{background:#f1f5f9;padding:2px 4px}}</style></head><body><h1>Transcript Preview</h1><h2>Metadata</h2><ul><li>Video: <code>{esc(metadata['video'])}</code></li><li>Acquisition mode: <code>{esc(metadata['acquisition_mode'])}</code></li><li>Source transcript: <code>{esc(metadata.get('source_transcript', ''))}</code></li><li>Generator: <code>{esc(metadata.get('generator', ''))}</code></li><li>Duration: <code>{metadata['duration_s']}s</code></li><li>Segments: <code>{len(transcript['segments'])}</code></li><li>Words: <code>{sum(item['words'] for item in stats)}</code></li><li>Speech duration: <code>{sum(item['speech_s'] for item in stats):.3f}s</code></li></ul><h2>Minute Statistics</h2><table><thead><tr><th>Minute</th><th>Range</th><th>Words</th><th>Segments</th><th>Speech s</th><th>WPM</th><th>Speech density</th></tr></thead><tbody>{stat_rows}</tbody></table><h2>Transcript Segments</h2><table><thead><tr><th>#</th><th>Time</th><th>Text</th><th>Words</th></tr></thead><tbody>{segment_rows}</tbody></table></body></html>""", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare the standard transcript input consumed by video-to-shorts.")
    parser.add_argument("video")
    parser.add_argument("--transcript", help="Explicit standard transcript JSON. Recommended; disables fallback transcription.")
    parser.add_argument("--timeline", help="Project timeline.json; maps a source transcript onto program time.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--ffmpeg", help="ffmpeg path used only by the temporary fallback.")
    parser.add_argument("--ffprobe", help="Optional ffprobe path for video duration metadata.")
    parser.add_argument("--python", default="python", help="Python used by the temporary video-understand transcribe.py fallback.")
    parser.add_argument("--model", default="base.en", help="Temporary fallback Whisper model.")
    parser.add_argument("--lang", default="en", help="Temporary fallback language.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.timeline and not args.transcript:
        fail("project timeline mode requires the canonical source transcript via --transcript")
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        fail(f"video not found: {video_path}")
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "transcript.json"
    if args.transcript:
        source = Path(args.transcript).resolve()
        if not source.exists():
            fail(f"explicit transcript not found: {source}")
        transcript = load_and_validate_transcript(source)
        metadata = {"acquisition_mode": "provided", "source_transcript": str(source), "generator": ""}
    else:
        generated = generate_fallback(video_path, out_dir, resolve_tool("ffmpeg", args.ffmpeg), args.python, args.model, args.lang)
        source = generated
        transcript = load_and_validate_transcript(generated)
        metadata = {"acquisition_mode": "generated_fallback", "source_transcript": "", "generator": "video-understand/transcribe.py"}
    if args.timeline:
        timeline_path = Path(args.timeline).resolve()
        if not timeline_path.exists():
            fail(f"timeline not found: {timeline_path}")
        try:
            timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            fail(f"invalid timeline JSON: {timeline_path}: {error}")
        transcript = prepare_transcript_data(transcript, timeline)
        metadata.update({
            "acquisition_mode": "project",
            "timeline": str(timeline_path),
            "timeline_id": timeline["timeline_id"],
            "timebase": "program",
            "bindings": {
                "video": file_binding(video_path),
                "source_transcript": file_binding(source),
                "timeline": file_binding(timeline_path),
            },
        })
    else:
        metadata["timebase"] = transcript.get("timebase", "input_video_relative")
    write_json(target, transcript)
    ffprobe = resolve_tool("ffprobe", args.ffprobe) if args.ffprobe else shutil.which("ffprobe")
    video_duration = probe_video_duration(video_path, ffprobe)
    duration = transcript_duration(transcript, video_duration)
    if args.timeline and video_duration is not None and abs(
        video_duration - float(timeline["source_duration_s"])
    ) > 0.1:
        fail(
            f"project source duration {video_duration:.3f}s does not match timeline source "
            f"duration {float(timeline['source_duration_s']):.3f}s"
        )
    metadata.update({"video": str(video_path), "duration_s": round(duration, 3)})
    stats = minute_stats(transcript, duration)
    write_preview_md(out_dir / "transcript_preview.md", metadata, transcript, stats)
    write_preview_html(out_dir / "transcript_preview.html", metadata, transcript, stats)
    write_json(out_dir / "transcript_metadata.json", metadata)
    print(f"[video-to-shorts] transcript: {target}")
    print(f"[video-to-shorts] acquisition_mode: {metadata['acquisition_mode']}")
    print(f"[video-to-shorts] segments: {len(transcript['segments'])}")


if __name__ == "__main__":
    main()
