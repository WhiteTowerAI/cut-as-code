"""Create objective speech metrics and semantic moment candidates from a transcript."""

import argparse
import json
import re
from pathlib import Path


LIST_RE = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:ways|things|reasons|steps|tips|rules|principles|lessons|parts|stages|phases|takeaways|ideas|questions)\b",
    re.IGNORECASE,
)
STAT_RE = re.compile(
    r"(?:\$\s*)?\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent|x\b|times|k\b|m\b|bn\b|billion|million|thousand|dollars?|users?|customers?|people|fps|frames?)?",
    re.IGNORECASE,
)
FILLER_RE = re.compile(r"\b(?:um+|uh+|er+m?|you know|i mean|sort of|kind of|basically)\b", re.IGNORECASE)


def _words(transcript):
    return [word for segment in transcript.get("segments", []) for word in segment.get("words", [])]


def _segment_moment(kind, segment, summary, confidence):
    return {
        "kind": kind,
        "start_s": round(float(segment["start"]), 3),
        "end_s": round(float(segment["end"]), 3),
        "summary": summary.strip(),
        "confidence": confidence,
        "evidence_refs": [f"segment:{segment['id']}"],
    }


def speech_metrics(transcript):
    words = _words(transcript)
    duration = float(
        transcript.get("duration", max((segment.get("end", 0) for segment in transcript.get("segments", [])), default=0))
    )
    gaps = [
        {
            "start_s": round(float(left["end"]), 3),
            "end_s": round(float(right["start"]), 3),
            "duration_s": round(float(right["start"]) - float(left["end"]), 3),
        }
        for left, right in zip(words, words[1:])
        if float(right["start"]) - float(left["end"]) >= 0.8
    ]
    speaking = sum(max(0.0, float(word["end"]) - float(word["start"])) for word in words)
    text = " ".join(segment.get("text", "") for segment in transcript.get("segments", []))
    return {
        "duration_s": round(duration, 3),
        "segment_count": len(transcript.get("segments", [])),
        "word_count": len(words),
        "words_per_minute": round(len(words) / (duration / 60), 1) if duration else 0,
        "speaking_ratio": round(speaking / duration, 3) if duration else 0,
        "silence_count_ge_0_8s": len(gaps),
        "silences": gaps,
        "filler_count": len(FILLER_RE.findall(text)),
    }


def detect_moment_candidates(transcript):
    moments = []
    segments = transcript.get("segments", [])
    for segment in segments:
        text = segment.get("text", "").strip()
        if LIST_RE.search(text):
            moments.append(_segment_moment("list", segment, text, 0.85))
        for match in STAT_RE.finditer(text):
            value = match.group(0).strip()
            digits = re.sub(r"\D", "", value.split()[0])
            explicit_unit = bool(re.search(r"[%$]|percent|x\b|times|billion|million|thousand|user|customer|people|fps|frame", value, re.I))
            if explicit_unit or (digits and int(digits) >= 100):
                moments.append(_segment_moment("stat", segment, value, 0.8))
        if text.endswith("?"):
            moments.append(_segment_moment("question", segment, text, 0.9))

    for left, right in zip(segments, segments[1:]):
        normalize = lambda value: re.sub(r"[^a-z0-9 ]", "", value.lower()).strip()
        left_text, right_text = normalize(left.get("text", "")), normalize(right.get("text", ""))
        if len(left_text) > 8 and (left_text == right_text or left_text in right_text or right_text in left_text):
            moment = _segment_moment("repetition", right, right.get("text", ""), 0.8)
            moment["evidence_refs"].insert(0, f"segment:{left['id']}")
            moments.append(moment)

    moments.sort(key=lambda item: (item["start_s"], item["end_s"], item["kind"]))
    for index, moment in enumerate(moments, 1):
        moment["id"] = f"moment-{index:03d}"
    return moments


def analyze_transcript(transcript):
    return {
        "schema_version": 1,
        "timeline_id": "source",
        "speech": speech_metrics(transcript),
        "moments": detect_moment_candidates(transcript),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    transcript = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(analyze_transcript(transcript), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
