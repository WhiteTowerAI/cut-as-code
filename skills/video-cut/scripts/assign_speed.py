"""Auto-assign a per-segment playback SPEED so the cut reads at an even pace.

Where it sits in the pipeline:
    build_edit.py -> edit_final.json -> [assign_speed.py] -> cut_render.py

build_edit.py already reclaimed dead air. This step groups render segments by
their hand-authored `decision_ref`, measures each decision block's speaking pace,
and nudges out-of-band blocks only to the nearest deadband edge. Adjacent decision
blocks are limited to a small speed delta so the result does not feel "pumpy".

Metric (per decision block):
  rate = words / (out-in) * 60         # WPM  (CJK: chars/min, see below)
  speed = clamp(DEADBAND_EDGE / rate, MIN_SPEED, MAX_SPEED)
  - DEADBAND: if rate is already in [LOW, HIGH], speed = 1.0 (leave it alone)
  - FLOOR:    blocks shorter than MIN_SEG_DUR or with < MIN_WORDS are noisy to
              measure -> they inherit the global factor (or 1.0), never a wild ratio
  - GROUPING: render segments with the same `decision_ref` receive the same speed
  - SMOOTHING: adjacent decision blocks differ by at most MAX_ADJACENT_SPEED_DELTA
  - speed is rounded to SPEED_STEP so the table is reviewable and joins are clean

Direction check: slow speech -> small rate -> LOW/rate > 1 -> speed > 1 -> faster.

This script ONLY annotates edit_final.json in place (adds `speed` and `out_dur`
per kept segment + a `speed_params` block). cut_render.py applies setpts/atempo;
selfcheck_frames.py uses `out_dur` to find the real join times. Nothing here
touches WHICH content is kept -- that stays your hand-written editorial call.

Usage:
  python assign_speed.py <edit_final.json> <transcript.json> [out.json] [options]
Options (k=v):
  mode=segment|global|off   (default segment)
  target=165                legacy reporting metadata; correction uses deadband edges
  deadband=145,185          no-change band around the rate (lo,hi)
  min_speed=1.0 max_speed=1.3
  min_seg=3.5 min_words=6   short-block floor
  step=0.02                 round speed to this granularity
  lang=auto|en|cjk          metric unit (auto = detect from transcript)
"""
import sys, json, re

# ---- language-aware defaults (target / deadband-lo / deadband-hi) ----
# English: words/min. Comfortable narration ~150-175; >190 rushed, <140 draggy.
EN_DEFAULTS  = dict(target=165.0, lo=145.0, hi=185.0)
# CJK: chars/min. Comfortable Mandarin narration ~240-300; tune per speaker.
CJK_DEFAULTS = dict(target=260.0, lo=220.0, hi=320.0)

MIN_SPEED, MAX_SPEED = 1.00, 1.30
MIN_SEG_DUR, MIN_WORDS = 3.5, 6
SPEED_STEP = 0.02
MAX_ADJACENT_SPEED_DELTA = 0.08

CJK_RE = re.compile(r"[㐀-䶿一-鿿぀-ヿ가-힯]")

def parse_opts(argv):
    opts = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            opts[k.strip()] = v.strip()
    return opts

def is_cjk_transcript(tr, words):
    lang = (tr.get("language") or "").lower()
    if lang in ("zh", "ja", "ko", "yue", "zh-cn", "zh-tw"):
        return True
    sample = "".join(w.get("word", "") for w in words[:400])
    cjk = len(CJK_RE.findall(sample))
    return cjk >= max(20, 0.20 * max(1, len(re.sub(r"\s", "", sample))))

def unit_count(words_slice, cjk):
    if cjk:
        return sum(len(CJK_RE.findall(w.get("word", ""))) for w in words_slice)
    return len(words_slice)

def rate_of(words_slice, dur, cjk):
    """pace in units/min: words/min (en) or CJK-chars/min (cjk)."""
    if dur <= 0:
        return None
    units = unit_count(words_slice, cjk)
    if units == 0:
        return None
    return units / dur * 60.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def quantize(x, step):
    return round(round(x / step) * step, 4)

def speed_to_deadband_edge(rate, lo, hi, min_speed, max_speed, step):
    if rate is None or lo <= rate <= hi:
        return 1.0
    edge = lo if rate < lo else hi
    return quantize(clamp(edge / rate, min_speed, max_speed), step)

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    edit_p, tr_p = sys.argv[1], sys.argv[2]
    out_p = sys.argv[3] if len(sys.argv) > 3 and "=" not in sys.argv[3] else edit_p
    opts = parse_opts(sys.argv[3:])

    mode = opts.get("mode", "segment")
    if mode not in ("segment", "global", "off"):
        print(f"[speed] bad mode={mode!r}; use segment|global|off"); sys.exit(1)

    edit = json.load(open(edit_p, encoding="utf-8"))
    tr = json.load(open(tr_p, encoding="utf-8"))
    words = [w for s in tr["segments"] for w in s["words"]]

    cjk = (opts.get("lang") == "cjk") or (opts.get("lang") != "en" and is_cjk_transcript(tr, words))
    dflt = CJK_DEFAULTS if cjk else EN_DEFAULTS
    unit = "CPM" if cjk else "WPM"

    target = float(opts.get("target", dflt["target"]))
    if "deadband" in opts:
        lo, hi = (float(x) for x in opts["deadband"].split(","))
    else:
        lo, hi = dflt["lo"], dflt["hi"]
    min_speed = float(opts.get("min_speed", MIN_SPEED))
    max_speed = float(opts.get("max_speed", MAX_SPEED))
    min_seg = float(opts.get("min_seg", MIN_SEG_DUR))
    min_words = int(opts.get("min_words", MIN_WORDS))
    step = float(opts.get("step", SPEED_STEP))

    def words_in(a, b):
        return [w for w in words if a <= (w["start"] + w["end"]) / 2 <= b]

    keep = edit["keep"]

    # ---- global rate (for global mode + as the floor fallback) ----
    g_units, g_dur = 0.0, 0.0
    for k in keep:
        a, b = float(k["in"]), float(k["out"])
        ws = words_in(a, b)
        d = b - a
        if d <= 0:
            continue
        g_dur += d
        g_units += unit_count(ws, cjk)
    g_rate = (g_units / g_dur * 60.0) if g_dur else None
    g_speed = speed_to_deadband_edge(g_rate, lo, hi, min_speed, max_speed, step)

    # ---- group render segments by their hand-authored decision ----
    groups = []
    group_by_ref = {}
    for index, k in enumerate(keep, 1):
        decision_ref = k.get("decision_ref") or k.get("id") or f"segment-{index:03d}"
        group = group_by_ref.get(decision_ref)
        if group is None:
            group = {
                "decision_ref": decision_ref,
                "segments": [],
                "words": [],
                "duration": 0.0,
            }
            group_by_ref[decision_ref] = group
            groups.append(group)
        a, b = float(k["in"]), float(k["out"])
        group["segments"].append(k)
        group["words"].extend(words_in(a, b))
        group["duration"] += b - a

    # ---- per-decision assignment + adjacent speed limiting ----
    previous_speed = None
    for group in groups:
        group_rate = rate_of(group["words"], group["duration"], cjk)
        group_units = unit_count(group["words"], cjk)

        if mode == "off":
            speed, why = 1.0, "off"
        elif mode == "global":
            speed, why = g_speed, "global"
        elif group["duration"] < min_seg or group_units < min_words or group_rate is None:
            speed, why = g_speed, "short->global"
        elif lo <= group_rate <= hi:
            speed, why = 1.0, "in-band"
        else:
            speed = speed_to_deadband_edge(group_rate, lo, hi, min_speed, max_speed, step)
            why = "slow->low-edge" if group_rate < lo else "fast->high-edge"

        if mode == "segment" and previous_speed is not None:
            limited = quantize(clamp(
                speed,
                previous_speed - MAX_ADJACENT_SPEED_DELTA,
                previous_speed + MAX_ADJACENT_SPEED_DELTA,
            ), step)
            limited = clamp(limited, min_speed, max_speed)
            if abs(limited - speed) > 1e-6:
                why += "+adjacent-limit"
            speed = limited

        if abs(speed - 1.0) < 1e-6:
            speed = 1.0
        group["rate"] = group_rate
        group["speed"] = speed
        group["why"] = why
        previous_speed = speed

    # ---- write the group speed to every render segment ----
    rows = []
    for group in groups:
        for k in group["segments"]:
            a, b = float(k["in"]), float(k["out"])
            seg_dur = b - a
            out_dur = round(seg_dur / group["speed"], 3)
            k["speed"] = group["speed"]
            k["out_dur"] = out_dur
            rows.append((a, b, seg_dur, group["rate"], group["speed"], out_dur,
                         group["why"], group["decision_ref"]))

    src_keep_dur = sum(float(k["out"]) - float(k["in"]) for k in keep)
    out_total = sum(float(k["out_dur"]) for k in keep)
    n_changed = sum(1 for r in rows if abs(r[4] - 1.0) > 1e-6)
    n_groups_changed = sum(1 for group in groups if abs(group["speed"] - 1.0) > 1e-6)

    edit["speed_mode"] = mode
    edit["speed_unit"] = unit
    edit["speed_params"] = {
        "mode": mode, "unit": unit, "target": target, "deadband": [lo, hi],
        "correction": "deadband-edge", "grouping": "decision_ref",
        "min_speed": min_speed, "max_speed": max_speed,
        "min_seg_s": min_seg, "min_words": min_words, "step": step,
        "max_adjacent_speed_delta": MAX_ADJACENT_SPEED_DELTA,
        "cjk": cjk, "global_rate": round(g_rate, 1) if g_rate else None,
        "global_speed": g_speed,
    }
    edit["final_duration_s_after_speed"] = round(out_total, 1)
    edit["final_duration_min_after_speed"] = round(out_total / 60, 2)
    edit["speed_segments_changed"] = n_changed
    edit["speed_groups_changed"] = n_groups_changed

    json.dump(edit, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- human-readable table ----
    print(f"[speed] mode={mode} unit={unit} correction=deadband-edge "
          f"deadband=[{lo},{hi}] clamp=[{min_speed},{max_speed}] "
          f"adjacent_delta<={MAX_ADJACENT_SPEED_DELTA} cjk={cjk}")
    if g_rate:
        print(f"[speed] overall kept pace = {g_rate:.1f} {unit}  (global_speed={g_speed})")
    print(f"[speed] {'in':>8} {'out':>8} {'dur':>6} {unit:>6} {'speed':>6} {'->out':>6}  decision / note")
    for a, b, d, rate, spd, od, why, decision_ref in rows:
        rs = f"{rate:6.0f}" if rate is not None else "    --"
        flag = "  *" if abs(spd - 1.0) > 1e-6 else "   "
        print(f"[speed] {a:8.1f} {b:8.1f} {d:6.1f} {rs} {spd:6.2f} {od:6.1f}{flag} "
              f"{decision_ref} / {why}")
    print(f"[speed] segments re-timed: {n_changed}/{len(keep)}")
    print(f"[speed] decision groups re-timed: {n_groups_changed}/{len(groups)}")
    print(f"[speed] kept duration {src_keep_dur/60:.2f} min -> after speed "
          f"{out_total/60:.2f} min  ({out_total/src_keep_dur*100:.1f}% of kept)")
    print(f"[speed] wrote {out_p}")
    if mode != "off":
        print("[speed] review the table; tune deadband= or set mode=off to disable, "
              "then run cut_render.py")

if __name__ == "__main__":
    main()
