#!/usr/bin/env python
"""Placement helper: pick card timestamps and ground card text from a word-level
transcript of the SAME video you're packaging (faster-whisper / Whisper JSON with
segments[].words[].start/end/word). All times are on the video's own timeline.

  --outline N        print a topic digest (one line per ~N seconds) -> chapter anchors
  --find "a,b,c"     first occurrence of each term (case-insensitive) + short context
                     -> lower-third / first-mention timestamps
  --window A B       print the spoken text between A and B seconds -> confirm a card's
                     content matches what's actually said

Usage:
  python place_cards.py transcript.json --outline 90
  python place_cards.py transcript.json --find "Alice,Acme,62-19"
  python place_cards.py transcript.json --window 238 246
"""
import json, argparse


def mmss(t):
    m, s = divmod(float(t), 60)
    return f"{int(m)}:{s:05.2f}"


def load_words(tr):
    words = []
    for sg in tr["segments"]:
        for w in sg.get("words", []):
            words.append((w["start"], w["end"], w["word"].strip()))
    return words


def seg_text(tr, a, b):
    return " ".join(sg["text"].strip() for sg in tr["segments"]
                    if sg["end"] >= a and sg["start"] <= b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--outline", type=float, metavar="SECONDS")
    ap.add_argument("--find", metavar="TERMS")
    ap.add_argument("--window", nargs=2, type=float, metavar=("A", "B"))
    a = ap.parse_args()
    tr = json.load(open(a.transcript, encoding="utf-8"))

    if a.outline:
        dur = tr.get("duration") or max(s["end"] for s in tr["segments"])
        t = 0.0
        while t < dur:
            txt = seg_text(tr, t, t + a.outline)
            print(f"[{mmss(t)}] {txt[:160]}")
            t += a.outline

    if a.find:
        words = load_words(tr)
        for term in [x.strip() for x in a.find.split(",") if x.strip()]:
            hit = None
            for st, en, wd in words:
                if term.lower() in wd.lower().strip(".,!?'\""):
                    hit = st
                    break
            if hit is None:
                print(f"{term:<18} -- not found (ASR may garble it; try a phonetic variant)")
            else:
                ctx = seg_text(tr, hit - 1, hit + 4)
                print(f"{term:<18} {mmss(hit):>9}  ({hit:.1f}s)  ...{ctx[:120]}")

    if a.window:
        x, y = a.window
        print(f"[{mmss(x)}-{mmss(y)}] {seg_text(tr, x, y)}")


if __name__ == "__main__":
    main()
