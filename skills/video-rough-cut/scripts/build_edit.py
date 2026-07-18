"""Expand coarse editorial KEEP blocks into tight, dead-air-free segments.

Editorial decision (which content to keep) is made by hand in the coarse file.
This script does the mechanical precision so cuts never clip a word AND internal
dead air is reclaimed uniformly:

For each coarse block [in,out]:
  - gather words whose center falls in the block
  - split into runs wherever an inter-word gap > SPLIT_GAP (long pause -> removed)
  - each run -> segment [first.start - min(LEAD, gap_before/2),
                          last.end   + min(TRAIL, gap_after/2)]
    (boundary lands INSIDE the silence; pauses <= SPLIT_GAP are kept for rhythm,
     longer pauses collapse to ~LEAD+TRAIL of natural breath)

Usage: python build_edit.py <coarse.json> <transcript.json> <edit_final.json>
"""
import sys, json

SPLIT_GAP = 0.60   # internal pauses longer than this are cut out
LEAD = 0.10
TRAIL = 0.30
EDGE_GAP = 0.40

def main():
    coarse_p, tr_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    split_gap = float(sys.argv[4]) if len(sys.argv) > 4 else SPLIT_GAP
    coarse = json.load(open(coarse_p, encoding="utf-8"))
    tr = json.load(open(tr_p, encoding="utf-8"))

    words = [w for s in tr["segments"] for w in s["words"]]
    dur = tr.get("duration", words[-1]["end"] if words else 0)

    def gb(i):  # gap before word i
        return (words[i]["start"] - words[i-1]["end"]) if i > 0 else EDGE_GAP
    def ga(i):  # gap after word i
        return (words[i+1]["start"] - words[i]["end"]) if i < len(words)-1 else EDGE_GAP

    if "decisions" in coarse:
        blocks = [
            {
                "id": decision["id"],
                "in": decision["start_s"],
                "out": decision["end_s"],
                "reason": decision.get("reason", ""),
                "evidence_refs": decision.get("evidence_refs", []),
            }
            for decision in coarse["decisions"]
            if decision.get("action") == "keep"
        ]
        dropped = [
            {
                "id": decision["id"],
                "in": decision["start_s"],
                "out": decision["end_s"],
                "reason": decision.get("reason", ""),
                "evidence_refs": decision.get("evidence_refs", []),
            }
            for decision in coarse["decisions"]
            if decision.get("action") == "drop"
        ]
    else:
        blocks = [dict(block, id=block.get("id", f"edit-{index:03d}"))
                  for index, block in enumerate(coarse["keep"], 1)]
        dropped = coarse.get("drop", [])

    segs = []
    kept_blocks = 0
    for blk in blocks:
        a, b = float(blk["in"]), float(blk["out"])
        reason = blk.get("reason", "")
        idxs = [i for i, w in enumerate(words) if a <= (w["start"]+w["end"])/2 <= b]
        if not idxs:
            print(f"[build] WARN: block {a:.1f}-{b:.1f} '{reason[:40]}' has no words")
            continue
        kept_blocks += 1
        # split idxs into runs at large gaps
        runs = [[idxs[0]]]
        for prev, cur in zip(idxs, idxs[1:]):
            if cur != prev + 1 or (words[cur]["start"] - words[prev]["end"]) > split_gap:
                runs.append([cur])
            else:
                runs[-1].append(cur)
        for run_index, run in enumerate(runs, 1):
            fi, li = run[0], run[-1]
            in_t = max(0.0, words[fi]["start"] - min(LEAD, gb(fi)/2))
            out_t = min(dur, words[li]["end"] + min(TRAIL, ga(li)/2))
            if out_t - in_t < 0.20:
                continue
            segment_id = blk["id"] if len(runs) == 1 else f"{blk['id']}.part-{run_index:03d}"
            segs.append({
                "id": segment_id,
                "decision_ref": blk["id"],
                "in": round(in_t, 3), "out": round(out_t, 3),
                "first_word": words[fi]["word"].strip(),
                "last_word": words[li]["word"].strip(),
                "reason": reason,
                "evidence_refs": blk.get("evidence_refs", []),
            })

    segs.sort(key=lambda s: s["in"])
    # safety merge of any accidental overlaps
    merged = []
    for s in segs:
        if merged and s["in"] <= merged[-1]["out"]:
            if s["out"] > merged[-1]["out"]:
                merged[-1]["out"] = s["out"]
                merged[-1]["last_word"] = s["last_word"]
        else:
            merged.append(dict(s))

    total = sum(s["out"] - s["in"] for s in merged)
    out = {
        "source": coarse.get("source", "work/source.mp4"),
        "source_duration_s": dur,
        "source_duration_min": round(dur/60, 2),
        "final_duration_s": round(total, 1),
        "final_duration_min": round(total/60, 2),
        "compression_pct": round(total/dur*100, 1),
        "n_coarse_blocks": kept_blocks,
        "n_render_segments": len(merged),
        "params": {"split_gap_s": split_gap, "lead_s": LEAD, "trail_s": TRAIL},
        "strategy": coarse.get("strategy", ""),
        "keep": merged,
        "drop": dropped,
        "drop_note": coarse.get("drop_note", ""),
    }
    json.dump(out, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[build] {kept_blocks} blocks -> {len(merged)} segments")
    print(f"[build] final {total:.1f}s ({total/60:.2f} min) = {total/dur*100:.1f}% of {dur/60:.1f} min")
    print(f"[build] reclaimed dead-air + dropped content: {(dur-total)/60:.1f} min removed")
    print(f"[build] wrote {out_p}")

if __name__ == "__main__":
    main()
