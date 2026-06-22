"""Print words around each coarse block's in/out so boundaries can be sentence-aligned.
Usage: python inspect_bounds.py <coarse.json> <transcript.json>
"""
import sys, json
coarse = json.load(open(sys.argv[1], encoding="utf-8"))
tr = json.load(open(sys.argv[2], encoding="utf-8"))
words = [w for s in tr["segments"] for w in s["words"]]

def window(t0, t1):
    out = []
    for w in words:
        c = (w["start"]+w["end"])/2
        if t0 <= c <= t1:
            out.append(w["word"].strip())
    return " ".join(out)

for i, b in enumerate(coarse["keep"], 1):
    a, z = float(b["in"]), float(b["out"])
    print(f"\n### block {i}: in={a} out={z}  ({a/60:.2f}-{z/60:.2f} min)")
    print(f"  ENTER [{a-2.0:.1f}|{a:.1f} -> {a+4.0:.1f}]:")
    print(f"     before: ...{window(a-3.0, a)}")
    print(f"     >>>>>>  {window(a, a+4.0)} ...")
    print(f"  EXIT  [{z-4.0:.1f} -> {z:.1f}|{z+2.0:.1f}]:")
    print(f"     ...{window(z-4.0, z)}  <<<<<<")
    print(f"     after: {window(z, z+3.0)}...")
