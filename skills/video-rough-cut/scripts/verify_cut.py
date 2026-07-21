"""Self-check the rendered cut against the edit plan.

- expected_text  = words from the ORIGINAL transcript that fall inside the kept spans
- actual_text    = re-transcript of first_cut.mp4
Compares them (difflib) to catch a dropped/duplicated segment or a clipped boundary,
and reports filler counts + per-minute density before vs after.

Usage: python verify_cut.py <edit_final.json> <orig_transcript.json> <cut_transcript.json>
"""
import sys, json, re, difflib
from collections import Counter

FILLERS = ["um", "uh", "like", "you know", "i mean", "sort of", "kind of",
           "basically", "actually", "literally", "right"]

def norm_tokens(text):
    return re.sub(r"[^a-z' ]", " ", text.lower()).split()

def filler_stats(text, minutes):
    counts = {}
    for f in FILLERS:
        c = len(re.findall(r"\b" + re.escape(f) + r"\b", text, re.I))
        if c:
            counts[f] = c
    tot = sum(counts.values())
    return counts, tot, round(tot / minutes, 1) if minutes else 0

def main():
    edit = json.load(open(sys.argv[1], encoding="utf-8"))
    orig = json.load(open(sys.argv[2], encoding="utf-8"))
    cut = json.load(open(sys.argv[3], encoding="utf-8"))

    owords = [w for s in orig["segments"] for w in s["words"]]
    def in_span(w, a, b):
        c = (w["start"] + w["end"]) / 2
        return a <= c <= b

    expected_words = []
    for k in edit["keep"]:
        a, b = float(k["in"]), float(k["out"])
        expected_words += [w["word"].strip() for w in owords if in_span(w, a, b)]
    expected_text = " ".join(expected_words)

    cut_text = " ".join(s["text"] for s in cut["segments"])
    exp_t = norm_tokens(expected_text)
    act_t = norm_tokens(cut_text)

    sm = difflib.SequenceMatcher(a=exp_t, b=act_t, autojunk=False)
    ratio = sm.ratio()

    # find the biggest contiguous mismatched runs (dropped/dup/garbled regions)
    big_gaps = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal" and max(i2 - i1, j2 - j1) >= 6:
            big_gaps.append((tag, " ".join(exp_t[i1:i2])[:80], " ".join(act_t[j1:j2])[:80]))

    cut_min = cut.get("duration", cut["segments"][-1]["end"]) / 60
    orig_min = orig.get("duration", 0) / 60
    orig_text = " ".join(s["text"] for s in orig["segments"])

    oc, ot, od = filler_stats(orig_text, orig_min)
    cc, ct, cd = filler_stats(cut_text, cut_min)

    print("=== CONTENT MATCH (expected kept words vs re-transcript) ===")
    print(f"  expected tokens: {len(exp_t)}   actual tokens: {len(act_t)}")
    print(f"  difflib similarity ratio: {ratio:.4f}  (>0.90 = no dropped/duplicated segment)")
    print(f"  large mismatch runs (>=6 tok): {len(big_gaps)}")
    for tag, e, a in big_gaps[:12]:
        print(f"    [{tag}] expected:'{e}'  |  actual:'{a}'")

    print("\n=== FILLER DENSITY  (count | per-minute) ===")
    print(f"  ORIGINAL ({orig_min:.1f} min): total={ot} | {od}/min   {oc}")
    print(f"  CUT      ({cut_min:.1f} min): total={ct} | {cd}/min   {cc}")
    print("  NOTE: Whisper omits most vocalized 'um/uh', so those are NOT transcript-measurable.")

    print("\n=== BOUNDARY WORDS present in re-transcript? (first/last of each kept render-seg) ===")
    miss = 0
    for k in edit["keep"]:
        for key in ("first_word", "last_word"):
            w = re.sub(r"[^a-z']", "", k.get(key, "").lower())
            if w and w not in act_t:
                miss += 1
    print(f"  boundary words not found in re-transcript: {miss} / {2*len(edit['keep'])}")
    print("  (a few misses are normal: Whisper spelling drift / merged tokens, not clips)")

if __name__ == "__main__":
    main()
