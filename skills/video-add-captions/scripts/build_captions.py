"""Build readable caption cues or a canonical caption plan from word timing.

Reads a word-level transcript (the work/transcript.json produced by the
video-cut skill's transcribe.py) and groups words into caption cues —
broken on sentence punctuation, a max line budget, a max duration, and speech
gaps — while keeping per-word timings so any renderer can highlight the current
word (karaoke).

Outputs:
  captions.json   list of { index, start, end, text, lines[], words[] }
  captions.srt    standard SubRip subtitles (portable + a quick sanity read)

Usage:
  python build_captions.py <transcript.json> [captions.json] [captions.srt] \
         [--max-chars 42] [--max-lines 2] [--max-dur 6] [--gap 0.6]
"""
import argparse
import json
import sys
from pathlib import Path


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402

ENDERS = (".", "?", "!", "…", "。", "！", "？")
MIN_CUE_DUR = 0.6   # cues shorter than this (or 1 token) are merged into a neighbor

def _cjk(ch):
    return ("一" <= ch <= "鿿" or "぀" <= ch <= "ヿ"
            or "가" <= ch <= "힣" or "㐀" <= ch <= "䶿")

def needs_space(a, b):
    # a space between Latin tokens, never around CJK characters
    return (
        bool(a) and bool(b) and not b.startswith("-")
        and not _cjk(a[-1]) and not _cjk(b[0])
    )

def join_tokens(tokens):
    s = ""
    for t in tokens:
        s += (" " if s and needs_space(s, t) else "") + t
    return s

def fmt_ts(t):
    ms = int(round(float(t) * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def flat_words(data):
    out = []
    for seg in data["segments"]:
        for w in seg.get("words", []):
            tok = w["word"].strip()
            if tok:
                out.append({**w, "word": tok, "start": w["start"], "end": w["end"]})
    return out

def wrap_tokens(tokens, max_chars):
    # space-aware for Latin, character-packing for CJK (no spaces)
    lines, cur = [], []
    for t in tokens:
        if cur and len(join_tokens(cur + [t])) > max_chars:
            lines.append(join_tokens(cur)); cur = [t]
        else:
            cur.append(t)
    if cur:
        lines.append(join_tokens(cur))
    return lines

def build(words, max_chars, max_lines, max_dur, gap):
    budget = max_chars * max_lines
    cues, cur = [], []

    def text_of(ws):
        return join_tokens([w["word"] for w in ws])

    def flush():
        if cur:
            cues.append({"start": round(cur[0]["start"], 3),
                         "end": round(cur[-1]["end"], 3),
                         "text": text_of(cur),
                         "clip_id": cur[0].get("clip_id"),
                         "words": [dict(w) for w in cur]})

    for i, w in enumerate(words):
        if cur and cur[0].get("clip_id") != w.get("clip_id"):
            flush(); cur = []
        # would adding this word blow the char or duration budget? close first.
        if cur:
            cand_len = len(text_of(cur + [w]))
            cand_dur = w["end"] - cur[0]["start"]
            if cand_len > budget or cand_dur > max_dur:
                flush(); cur = []
        cur.append(w)
        # hard break right after sentence-ending punctuation
        if w["word"].endswith(ENDERS):
            flush(); cur = []
            continue
        # break on a real pause before the next word
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt and (nxt["start"] - w["end"] >= gap):
            flush(); cur = []
    flush()

    # merge orphan cues (1 token or < MIN_CUE_DUR) into a neighbor so a stray
    # "So" (0.44s) doesn't flash on its own. Prefer the previous cue; a leading
    # orphan folds into the next.
    def is_orphan(c):
        return len(c["words"]) <= 1 or (c["end"] - c["start"]) < MIN_CUE_DUR
    def fits(left, right):
        words = left["words"] + right["words"]
        return (
            words[-1]["end"] - words[0]["start"] <= max_dur
            and len(text_of(words)) <= budget
        )
    merged = []
    for c in cues:
        if (
            merged
            and is_orphan(c)
            and merged[-1].get("clip_id") == c.get("clip_id")
            and fits(merged[-1], c)
        ):
            p = merged[-1]
            p["words"] = p["words"] + c["words"]
            p["end"] = c["end"]
            p["text"] = text_of(p["words"])
        else:
            merged.append(c)
    if (
        len(merged) >= 2
        and is_orphan(merged[0])
        and merged[0].get("clip_id") == merged[1].get("clip_id")
        and fits(merged[0], merged[1])
    ):
        nxt = merged[1]
        nxt["words"] = merged[0]["words"] + nxt["words"]
        nxt["start"] = merged[0]["start"]
        nxt["text"] = text_of(nxt["words"])
        merged = merged[1:]
    cues = merged

    for current, following in zip(cues, cues[1:]):
        if current["end"] > following["start"]:
            if following["start"] <= current["start"]:
                raise ValueError("caption cue timing collapsed after millisecond rounding")
            current["end"] = following["start"]

    for idx, c in enumerate(cues, 1):
        c["index"] = idx
        c["lines"] = wrap_tokens([w["word"] for w in c["words"]], max_chars)
        c["program_range"] = {"start_s": c["start"], "end_s": c["end"]}
        source_words = [word for word in c["words"] if "source_range" in word]
        c["source_ranges"] = (
            [{
                "start_s": source_words[0]["source_range"]["start_s"],
                "end_s": source_words[-1]["source_range"]["end_s"],
            }]
            if source_words else []
        )
    return cues


def build_plan(
    transcript, timeline, *, source_transcript, max_chars=42, max_lines=2,
    max_dur=6.0, gap=0.6,
):
    mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
    words = flat_words(mapped)
    if not words:
        raise ValueError("no retained word-level timestamps in transcript")
    cues = build(words, max_chars, max_lines, max_dur, gap)
    return {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": timeline["timeline_id"],
        "timebase": "program",
        "source_transcript": source_transcript,
        "program_duration_s": timeline["program_duration_s"],
        "cue_settings": {
            "max_chars": max_chars,
            "max_lines": max_lines,
            "max_duration_s": max_dur,
            "gap_s": gap,
        },
        "style": {
            "status": "draft",
            "selection_mode": None,
            "selection_rationale": "",
        },
        "review": {"status": "pending", "evidence": []},
        "cues": cues,
        "renderer_recipe": {
            "engine": "hyperframes",
            "composition": "cache/captions/index.html",
            "asset": "cache/captions/overlay-frames",
            "asset_type": "image-sequence",
            "pattern": "frame_%06d.png",
            "start_number": 1,
            "fps": dict(timeline["fps"]),
            "runtime_assets": [],
        },
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("out_json", nargs="?", default="captions.json")
    parser.add_argument("out_srt", nargs="?", default="captions.srt")
    parser.add_argument("--timeline")
    parser.add_argument("--source-transcript")
    parser.add_argument("--max-chars", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--max-dur", type=float, default=6.0)
    parser.add_argument("--gap", type=float, default=0.6)
    args = parser.parse_args(argv)
    if args.max_chars < 1 or args.max_lines < 1 or args.max_dur <= 0 or args.gap < 0:
        parser.error("caption grouping limits must be positive (gap may be zero)")
    return args


def main(argv=None):
    args = parse_args(argv)
    with open(args.transcript, encoding="utf-8") as handle:
        transcript = json.load(handle)
    if args.timeline:
        with open(args.timeline, encoding="utf-8") as handle:
            timeline = json.load(handle)
        output = build_plan(
            transcript,
            timeline,
            source_transcript=args.source_transcript or args.transcript,
            max_chars=args.max_chars,
            max_lines=args.max_lines,
            max_dur=args.max_dur,
            gap=args.gap,
        )
        cues = output["cues"]
    else:
        words = flat_words(transcript)
        if not words:
            raise SystemExit("[captions] no word-level timestamps in transcript")
        cues = build(words, args.max_chars, args.max_lines, args.max_dur, args.gap)
        output = cues

    out_json = Path(args.out_json)
    out_srt = Path(args.out_srt)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=1)
    srt = []
    for c in cues:
        srt.append(f"{c['index']}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n"
                   + "\n".join(c["lines"]) + "\n")
    with open(out_srt, "w", encoding="utf-8") as handle:
        handle.write("\n".join(srt))

    durs = [c["end"] - c["start"] for c in cues]
    chars = [len(c["text"]) for c in cues]
    word_count = sum(len(cue["words"]) for cue in cues)
    print(f"[captions] {len(cues)} cues from {word_count} words "
          f"-> {out_json} + {out_srt}")
    print(f"[captions] dur avg={sum(durs)/len(durs):.1f}s max={max(durs):.1f}s | "
          f"chars avg={sum(chars)//len(chars)} max={max(chars)} "
          f"(budget {args.max_chars*args.max_lines})")
    for c in cues[:6]:
        print(f"  {c['start']:6.1f}-{c['end']:6.1f}  {c['text'][:60]}")

if __name__ == "__main__":
    main()
