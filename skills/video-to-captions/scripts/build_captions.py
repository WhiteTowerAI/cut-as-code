"""Build readable caption cues from a word-level transcript.

Reads a word-level transcript (the work/transcript.json produced by the
video-rough-cut skill's transcribe.py) and groups words into caption cues —
broken on sentence punctuation, a max line budget, a max duration, and speech
gaps — while keeping per-word timings so the Remotion component can highlight
the current word (karaoke).

Outputs:
  src/captions.json   list of { index, start, end, text, lines[], words[] }
  out/captions.srt    standard SubRip subtitles (portable + a quick sanity read)

Usage:
  python build_captions.py <transcript.json> [src/captions.json] [out/captions.srt] \
         [--max-chars 42] [--max-lines 2] [--max-dur 6] [--gap 0.6]
"""
import sys, json

ENDERS = (".", "?", "!", "…", "。", "！", "？")

def _cjk(ch):
    return ("一" <= ch <= "鿿" or "぀" <= ch <= "ヿ"
            or "가" <= ch <= "힣" or "㐀" <= ch <= "䶿")

def needs_space(a, b):
    # a space between Latin tokens, never around CJK characters
    return bool(a) and bool(b) and not _cjk(a[-1]) and not _cjk(b[0])

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
                out.append({"word": tok, "start": w["start"], "end": w["end"]})
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
                         "words": [dict(w) for w in cur]})

    for i, w in enumerate(words):
        # would adding this word blow the char or duration budget? close first.
        if cur:
            cand_len = len(text_of(cur)) + 1 + len(w["word"])
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

    for idx, c in enumerate(cues, 1):
        c["index"] = idx
        c["lines"] = wrap_tokens([w["word"] for w in c["words"]], max_chars)
    return cues

def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    transcript = a[0]
    pos = [x for x in a[1:] if not x.startswith("--")]
    out_json = pos[0] if len(pos) > 0 else "src/captions.json"
    out_srt = pos[1] if len(pos) > 1 else "out/captions.srt"

    def opt(name, default, cast):
        return cast(a[a.index(name) + 1]) if name in a else default
    max_chars = opt("--max-chars", 42, int)
    max_lines = opt("--max-lines", 2, int)
    max_dur = opt("--max-dur", 6.0, float)
    gap = opt("--gap", 0.6, float)

    with open(transcript, encoding="utf-8") as f:
        data = json.load(f)
    words = flat_words(data)
    if not words:
        sys.exit("[captions] no word-level timestamps in transcript")
    cues = build(words, max_chars, max_lines, max_dur, gap)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(cues, f, ensure_ascii=False, indent=1)
    srt = []
    for c in cues:
        srt.append(f"{c['index']}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n"
                   + "\n".join(c["lines"]) + "\n")
    with open(out_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt))

    durs = [c["end"] - c["start"] for c in cues]
    chars = [len(c["text"]) for c in cues]
    print(f"[captions] {len(cues)} cues from {len(words)} words "
          f"-> {out_json} + {out_srt}")
    print(f"[captions] dur avg={sum(durs)/len(durs):.1f}s max={max(durs):.1f}s | "
          f"chars avg={sum(chars)//len(chars)} max={max(chars)} (budget {max_chars*max_lines})")
    for c in cues[:6]:
        print(f"  {c['start']:6.1f}-{c['end']:6.1f}  {c['text'][:60]}")

if __name__ == "__main__":
    main()
