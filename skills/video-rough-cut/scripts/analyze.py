"""Analyze a word-timestamp transcript to surface 'bad-edit' candidates.

Usage: python analyze.py <transcript.json> [out_summary.json]
Reports: long silences (intra/inter word gaps), filler usage, fast/slow pace,
near-duplicate (repetition) consecutive segments, very long monologue runs.
"""
import sys, json, re
from collections import Counter

FILLERS = ["um", "uh", "uhh", "umm", "er", "erm", "hmm", "mm",
           "like", "you know", "i mean", "sort of", "kind of",
           "basically", "actually", "literally", "right", "okay so", "so yeah"]
FILLER_RE = {f: re.compile(r"\b" + re.escape(f) + r"\b", re.I) for f in FILLERS}

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def all_words(data):
    ws = []
    for s in data["segments"]:
        for w in s["words"]:
            ws.append(w)
    return ws

def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    data = load(path)
    segs = data["segments"]
    words = all_words(data)
    dur = data.get("duration", segs[-1]["end"] if segs else 0)

    # ---- silences from inter-word gaps ----
    silences = []
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap >= 0.8:
            silences.append({"after_word": a["word"].strip(), "start": round(a["end"], 2),
                             "end": round(b["start"], 2), "gap": round(gap, 2)})
    # leading silence before first word
    lead = words[0]["start"] if words else 0
    # trailing
    trail = dur - words[-1]["end"] if words else 0

    # ---- filler counts ----
    full_text = " ".join(s["text"] for s in segs)
    filler_counts = {}
    for f, rx in FILLER_RE.items():
        c = len(rx.findall(full_text))
        if c:
            filler_counts[f] = c

    # ---- pace ----
    n_words = len(words)
    speak_time = sum(w["end"] - w["start"] for w in words)
    wpm = n_words / (dur / 60) if dur else 0

    # ---- repetition: near-duplicate consecutive segment texts ----
    def norm(t):
        return re.sub(r"[^a-z ]", "", t.lower()).strip()
    reps = []
    for a, b in zip(segs, segs[1:]):
        na, nb = norm(a["text"]), norm(b["text"])
        if len(na) > 8 and (na == nb or (na in nb) or (nb in na)):
            reps.append({"start": a["start"], "end": b["end"], "a": a["text"].strip(), "b": b["text"].strip()})

    # ---- long monologue runs without a big pause (potential ramble) ----
    # contiguous stretch length between >=1.2s pauses
    runs = []
    run_start = words[0]["start"] if words else 0
    last_end = run_start
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] >= 1.2:
            runs.append({"start": round(run_start, 2), "end": round(a["end"], 2),
                         "len": round(a["end"] - run_start, 1)})
            run_start = b["start"]
    if words:
        runs.append({"start": round(run_start, 2), "end": round(words[-1]["end"], 2),
                     "len": round(words[-1]["end"] - run_start, 1)})
    long_runs = sorted([r for r in runs if r["len"] > 40], key=lambda r: -r["len"])[:15]

    summary = {
        "duration_s": round(dur, 1),
        "duration_min": round(dur / 60, 2),
        "n_segments": len(segs),
        "n_words": n_words,
        "wpm": round(wpm, 1),
        "speaking_ratio": round(speak_time / dur, 3) if dur else 0,
        "leading_silence_s": round(lead, 2),
        "trailing_silence_s": round(trail, 2),
        "n_silences_ge_0.8s": len(silences),
        "total_silence_in_gaps_s": round(sum(s["gap"] for s in silences), 1),
        "top_silences": sorted(silences, key=lambda s: -s["gap"])[:25],
        "filler_counts": dict(sorted(filler_counts.items(), key=lambda x: -x[1])),
        "filler_total": sum(filler_counts.values()),
        "repetitions": reps[:20],
        "long_runs_gt40s": long_runs,
    }

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("top_silences", "repetitions", "long_runs_gt40s")},
                     ensure_ascii=False, indent=1))
    print(f"\n# top silences (>=0.8s): {len(silences)} total, showing 25")
    for s in summary["top_silences"]:
        print(f"  {s['start']:7.1f} -> {s['end']:7.1f}  gap={s['gap']:.1f}s  after '{s['after_word']}'")
    print(f"\n# long runs >40s (possible rambles): {len(long_runs)}")
    for r in long_runs:
        print(f"  {r['start']:7.1f} -> {r['end']:7.1f}  len={r['len']}s")
    print(f"\n# repetitions: {len(reps)}")
    for r in reps[:20]:
        print(f"  {r['start']:7.1f}->{r['end']:7.1f}  A:{r['a'][:60]!r}  B:{r['b'][:60]!r}")

    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
        print(f"\n[analyze] wrote {out}")

if __name__ == "__main__":
    main()
