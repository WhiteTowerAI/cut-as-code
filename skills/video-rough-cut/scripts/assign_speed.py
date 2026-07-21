"""Auto-assign a per-segment playback SPEED so the cut reads at an even pace.

Where it sits in the pipeline:
    build_edit.py -> edit_final.json -> [assign_speed.py] -> cut_render.py

build_edit.py already reclaimed dead air. This step nudges each kept segment's
*speaking* pace toward a comfortable target: slow stretches get sped up, fast
stretches get slowed down ("反之亦然"). It is a varispeed, not a global stretch.

Metric (per kept segment):
  rate = words / (out-in) * 60         # WPM  (CJK: chars/min, see below)
  speed = clamp(TARGET / rate, MIN_SPEED, MAX_SPEED)
  - DEADBAND: if rate is already in [LOW, HIGH], speed = 1.0 (leave it alone)
  - FLOOR:    segments shorter than MIN_SEG_DUR or with < MIN_WORDS are noisy to
              measure -> they inherit the global factor (or 1.0), never a wild ratio
  - speed is rounded to SPEED_STEP so the table is reviewable and joins are clean

Direction check: slow speech -> small rate -> TARGET/rate > 1 -> speed > 1 -> faster.

This script ONLY annotates edit_final.json in place (adds `speed` and `out_dur`
per kept segment + a `speed_summary` block). cut_render.py applies setpts/atempo;
selfcheck_frames.py uses `out_dur` to find the real join times. Nothing here
touches WHICH content is kept -- that stays your hand-written editorial call.

Usage:
  python assign_speed.py <edit_final.json> <transcript.json> [out.json] [options]
Options (k=v):
  mode=segment|global|off   (default segment)
  target=165                target WPM (or CPM for CJK); overrides language default
  deadband=145,185          no-change band around the rate (lo,hi)
  min_speed=0.9 max_speed=1.5
  min_seg=3.5 min_words=6   short-segment floor
  step=0.02                 round speed to this granularity
  lang=auto|en|cjk          metric unit (auto = detect from transcript)
"""
import sys, json, re

# ---- language-aware defaults (target / deadband-lo / deadband-hi) ----
# English: words/min. Comfortable narration ~150-175; >190 rushed, <140 draggy.
EN_DEFAULTS  = dict(target=165.0, lo=145.0, hi=185.0)
# CJK: chars/min. Comfortable Mandarin narration ~240-300; tune per speaker.
CJK_DEFAULTS = dict(target=260.0, lo=220.0, hi=320.0)

MIN_SPEED, MAX_SPEED = 0.90, 1.50
MIN_SEG_DUR, MIN_WORDS = 3.5, 6
SPEED_STEP = 0.02

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

def rate_of(words_slice, dur, cjk):
    """pace in units/min: words/min (en) or CJK-chars/min (cjk)."""
    if dur <= 0:
        return None
    if cjk:
        units = sum(len(CJK_RE.findall(w.get("word", ""))) for w in words_slice)
    else:
        units = len(words_slice)
    if units == 0:
        return None
    return units / dur * 60.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def quantize(x, step):
    return round(round(x / step) * step, 4)

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
    g_words, g_dur = 0.0, 0.0
    for k in keep:
        a, b = float(k["in"]), float(k["out"])
        ws = words_in(a, b)
        d = b - a
        if d <= 0:
            continue
        g_dur += d
        g_words += (sum(len(CJK_RE.findall(w.get("word", ""))) for w in ws) if cjk else len(ws))
    g_rate = (g_words / g_dur * 60.0) if g_dur else None
    if g_rate and not (lo <= g_rate <= hi):
        g_speed = quantize(clamp(target / g_rate, min_speed, max_speed), step)
    else:
        g_speed = 1.0

    # ---- per-segment assignment ----
    rows = []
    for k in keep:
        a, b = float(k["in"]), float(k["out"])
        seg_dur = b - a
        ws = words_in(a, b)
        rate = rate_of(ws, seg_dur, cjk)

        if mode == "off":
            spd, why = 1.0, "off"
        elif mode == "global":
            spd, why = g_speed, "global"
        elif seg_dur < min_seg or len(ws) < min_words or rate is None:
            spd, why = g_speed, "short->global"          # too short to measure
        elif lo <= rate <= hi:
            spd, why = 1.0, "in-band"
        else:
            spd = quantize(clamp(target / rate, min_speed, max_speed), step)
            why = "slow->faster" if rate < lo else "fast->slower"

        if abs(spd - 1.0) < 1e-6:
            spd = 1.0
        out_dur = round(seg_dur / spd, 3)
        k["speed"] = spd
        k["out_dur"] = out_dur
        rows.append((a, b, seg_dur, rate, spd, out_dur, why,
                     k.get("first_word", ""), k.get("last_word", "")))

    src_keep_dur = sum(float(k["out"]) - float(k["in"]) for k in keep)
    out_total = sum(float(k["out_dur"]) for k in keep)
    n_changed = sum(1 for r in rows if abs(r[4] - 1.0) > 1e-6)

    edit["speed_mode"] = mode
    edit["speed_unit"] = unit
    edit["speed_params"] = {
        "mode": mode, "unit": unit, "target": target, "deadband": [lo, hi],
        "min_speed": min_speed, "max_speed": max_speed,
        "min_seg_s": min_seg, "min_words": min_words, "step": step,
        "cjk": cjk, "global_rate": round(g_rate, 1) if g_rate else None,
        "global_speed": g_speed,
    }
    edit["final_duration_s_after_speed"] = round(out_total, 1)
    edit["final_duration_min_after_speed"] = round(out_total / 60, 2)
    edit["speed_segments_changed"] = n_changed

    json.dump(edit, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- human-readable table ----
    print(f"[speed] mode={mode} unit={unit} target={target} deadband=[{lo},{hi}] "
          f"clamp=[{min_speed},{max_speed}] cjk={cjk}")
    if g_rate:
        print(f"[speed] overall kept pace = {g_rate:.1f} {unit}  (global_speed={g_speed})")
    print(f"[speed] {'in':>8} {'out':>8} {'dur':>6} {unit:>6} {'speed':>6} {'->out':>6}  note")
    for a, b, d, rate, spd, od, why, fw, lw in rows:
        rs = f"{rate:6.0f}" if rate is not None else "    --"
        flag = "  *" if abs(spd - 1.0) > 1e-6 else "   "
        print(f"[speed] {a:8.1f} {b:8.1f} {d:6.1f} {rs} {spd:6.2f} {od:6.1f}{flag} {why}")
    print(f"[speed] segments re-timed: {n_changed}/{len(keep)}")
    print(f"[speed] kept duration {src_keep_dur/60:.2f} min -> after speed "
          f"{out_total/60:.2f} min  ({out_total/src_keep_dur*100:.1f}% of kept)")
    print(f"[speed] wrote {out_p}")
    if mode != "off":
        print("[speed] review the table; tune target=/deadband= or set mode=off to disable, "
              "then run cut_render.py")

if __name__ == "__main__":
    main()
