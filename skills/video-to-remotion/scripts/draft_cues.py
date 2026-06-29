"""Turn content.json (opportunities) into a DRAFT cue sheet for FinalEdit.tsx.

Maps each opportunity type to its Remotion component and emits the cue's prop
SKELETON in the component's real shape (lower-third -> line1/line2, section ->
kicker/title, ...). De-stacks overlapping cues, clamps durations, assigns ids,
and prints a ready-to-paste TS `CUES` array. Also writes work/cues.json.

This is a *first pass*. The text fields are placeholders/hints: the agent must
PRUNE the noise and WRITE the copy from the transcript — line1 = the entity
(fix ASR-garbled names), line2 = a one-line gloss; chapter title = an editorial
label of what's said. Detection seeds timing + candidates, not final words.

Usage:
  python draft_cues.py [work/content.json] [work/cues.json] [--min-gap 0.6]
"""
import sys, json

TYPE_TO_COMPONENT = {
    "lower-third": "LowerThird",
    "stat":        "StatCallout",
    "keypoint":    "KeypointCallout",
    "list":        "ListReveal",
    "section":     "SectionCard",
}

MAX_DUR = 12.0   # hard cap so a bad detection can't park an overlay for minutes


def to_props(o, counts):
    """Map an opportunity to its component's prop shape (skeleton — agent fills)."""
    t = o["type"]
    p = o.get("props", {}) or {}
    if t == "lower-third":
        line1 = p.get("name") or " ".join(o.get("quote", "").split()[:4])
        return {"line1": line1, "line2": ""}          # write line2 from the transcript
    if t == "section":
        counts["section"] = counts.get("section", 0) + 1
        title = p.get("title") or o.get("quote", "")
        return {"kicker": f"PART {counts['section']}", "title": " ".join(title.split()[:6])}
    if t == "stat":
        return {"value": p.get("value", ""), "label": p.get("label", "")}
    if t == "keypoint":
        return {"text": p.get("text", "")}
    if t == "list":
        return {"title": p.get("title", ""), "items": []}   # write items from the transcript
    return p


def main():
    args = sys.argv[1:]
    inp = next((a for a in args if a.endswith(".json") and "cues" not in a), "work/content.json")
    outp = next((a for a in args if a.endswith("cues.json")), "work/cues.json")
    min_gap = 0.6
    if "--min-gap" in args:
        min_gap = float(args[args.index("--min-gap") + 1])

    with open(inp, encoding="utf-8") as f:
        content = json.load(f)
    opps = sorted(content["opportunities"], key=lambda o: o["at"])

    # Every card is bottom-anchored now, so de-stack on a single timeline: don't
    # let two cards overlap within min_gap (keep the earlier one).
    cues, last_end, seen, counts = [], -1.0, {}, {}
    for o in opps:
        comp = TYPE_TO_COMPONENT.get(o["type"])
        if not comp:
            continue
        if o["at"] < last_end + min_gap:
            continue
        dur = min(float(o.get("dur", 4.0)), MAX_DUR)
        n = seen.get(o["type"], 0) + 1
        seen[o["type"]] = n
        cues.append({"id": f"{o['type']}-{n}", "component": comp,
                     "at": o["at"], "dur": dur, "props": to_props(o, counts)})
        last_end = o["at"] + dur

    with open(outp, "w", encoding="utf-8") as f:
        json.dump(cues, f, ensure_ascii=False, indent=1)

    # ready-to-paste TS
    print("// paste into FinalEdit.tsx, then PRUNE + WRITE the copy:")
    print("//   line1 = entity (fix ASR-garbled names), line2 = one-line gloss;")
    print("//   chapter title = editorial label; nudge `at` onto the spoken word.")
    print("const CUES = [")
    for c in cues:
        props = ", ".join(f"{k}: {json.dumps(v)}" for k, v in c["props"].items())
        print(f"  {{ id: {json.dumps(c['id'])}, component: {json.dumps(c['component'])}, "
              f"at: {c['at']}, dur: {c['dur']}, props: {{ {props} }} }},")
    print("] as const;")
    print(f"\n[draft_cues] {len(cues)} cues kept (of {len(opps)} opportunities) -> {outp}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
