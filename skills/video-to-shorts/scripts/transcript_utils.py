"""Small shared helpers for video-to-shorts transcript-based planning."""

import json


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def transcript_duration(transcript):
    if isinstance(transcript.get("duration"), (int, float)):
        return float(transcript["duration"])
    segments = transcript.get("segments") or []
    if not segments:
        return 0.0
    return max(float(s.get("end", 0.0)) for s in segments)


def transcript_text(transcript):
    lines = []
    for seg in transcript.get("segments", []):
        start = float(seg.get("start", 0.0))
        text = str(seg.get("text", "")).strip()
        if text:
            lines.append(f"[{start:.1f}s] {text}")
    return "\n".join(lines)


def excerpt_for_range(transcript, start, end, max_chars=420):
    parts = []
    for seg in transcript.get("segments", []):
        s = float(seg.get("start", 0.0))
        e = float(seg.get("end", s))
        if s < end and e > start:
            text = str(seg.get("text", "")).strip()
            if text:
                parts.append(text)
    excerpt = " ".join(" ".join(parts).split())
    if len(excerpt) > max_chars:
        return excerpt[: max_chars - 3].rstrip() + "..."
    return excerpt


def fmt_time(seconds):
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def overlap_ratio(a, b):
    latest = max(a["start_time"], b["start_time"])
    earliest = min(a["end_time"], b["end_time"])
    overlap = max(0.0, earliest - latest)
    if overlap <= 0:
        return 0.0
    return overlap / max(0.001, min(a["duration"], b["duration"]))
