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
        words = seg.get("words")
        if isinstance(words, list):
            selected = [
                str(word.get("word", ""))
                for word in words
                if float(word.get("start", 0.0)) < end
                and float(word.get("end", word.get("start", 0.0))) > start
                and str(word.get("word", "")).strip()
            ]
            if selected:
                text = "".join(selected).strip()
                if len(selected) > 1 and not any(word[:1].isspace() for word in selected[1:]):
                    text = " ".join(word.strip() for word in selected)
                parts.append(text)
            continue
        segment_start = float(seg.get("start", 0.0))
        segment_end = float(seg.get("end", segment_start))
        if segment_start < end and segment_end > start:
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
