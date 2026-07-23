"""Print words around each coarse block's in/out so boundaries can be sentence-aligned.

Also flags "dangling" exits: a keep-block that ends on a hanging conjunction/
preposition/article (e.g. "...something that I liked. Because") or that splits a
capitalized proper-noun bigram (e.g. "...rugby too Southern" / dropped "Cross").
Nudge those `out` boundaries (build_edit.py keeps a word when its CENTER falls in
[in,out], so ±0.2s flips a whole word in/out).

Usage: python inspect_bounds.py <coarse.json> <transcript.json>
"""
import sys, json, re
coarse = json.load(open(sys.argv[1], encoding="utf-8"))
tr = json.load(open(sys.argv[2], encoding="utf-8"))
words = [w for s in tr["segments"] for w in s["words"]]

# words that should not be the LAST kept word of a block (hanging when cut after)
DANGLERS = {
    "because", "and", "but", "so", "or", "nor", "yet", "as", "than", "that",
    "the", "a", "an",
    "in", "of", "to", "for", "with", "on", "at", "by", "from", "into", "onto",
    "about", "over", "under", "between", "through",
}

def norm(tok):
    return re.sub(r"[^\w']", "", tok.strip()).lower()

def is_cap(tok):
    t = tok.strip()
    return bool(t) and t[0].isupper()

def window(t0, t1):
    return " ".join(w["word"].strip() for w in words
                    if t0 <= (w["start"] + w["end"]) / 2 <= t1)

def dangling_exit(z):
    """Return a warning string if the last kept word at out=z dangles, else ''."""
    kept = [w for w in words if (w["start"] + w["end"]) / 2 <= z]
    after = [w for w in words if (w["start"] + w["end"]) / 2 > z]
    if not kept:
        return ""
    last = kept[-1]["word"]
    nxt = after[0]["word"] if after else ""
    if norm(last) in DANGLERS:
        return f"WARNING: dangling exit: ends on '{last.strip()}' (hanging word)"
    # capitalized X Y proper-noun split: keep "Southern", drop "Cross". A trailing
    # ./!/?/… means the kept word ENDS a sentence (a clean boundary, and the next
    # capital just starts the next sentence) — don't warn on those.
    if (nxt and is_cap(last) and is_cap(nxt) and norm(last) not in ("i",)
            and not last.strip().endswith((".", "!", "?", "…"))):
        return f"WARNING: dangling exit: splits proper noun '{last.strip()} {nxt.strip()}'"
    return ""

blocks = coarse.get("keep") or [
    {"in": decision["start_s"], "out": decision["end_s"]}
    for decision in coarse.get("decisions", [])
    if decision.get("action") == "keep"
]

for i, b in enumerate(blocks, 1):
    a, z = float(b["in"]), float(b["out"])
    print(f"\n### block {i}: in={a} out={z}  ({a/60:.2f}-{z/60:.2f} min)")
    print(f"  ENTER [{a-2.0:.1f}|{a:.1f} -> {a+4.0:.1f}]:")
    print(f"     before: ...{window(a-3.0, a)}")
    print(f"     >>>>>>  {window(a, a+4.0)} ...")
    print(f"  EXIT  [{z-4.0:.1f} -> {z:.1f}|{z+2.0:.1f}]:")
    print(f"     ...{window(z-4.0, z)}  <<<<<<")
    print(f"     after: {window(z, z+3.0)}...")
    warn = dangling_exit(z)
    if warn:
        print(f"     {warn}")
