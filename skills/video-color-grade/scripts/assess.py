#!/usr/bin/env python3
"""Assess footage BEFORE grading: probe + white-balance/exposure stats + pick a
representative frame. Never grade blind.

  python scripts/assess.py SOURCE.mp4 --out work/
  python scripts/assess.py SOURCE.mp4 --out work/ --frame-time 150

Writes work/assess/frame.png (the comparison frame), assessment.txt and assessment.json.
"""
import argparse, json, os, shutil
import gradelib as gl
from PIL import Image


def pick_frame(video, dur, out_png, n=9):
    """Extract n evenly-spaced frames, keep the one whose luma is the MEDIAN (a typical,
    non-black / non-transition frame)."""
    tmp = os.path.join(os.path.dirname(out_png), "_cand")
    os.makedirs(tmp, exist_ok=True)
    rows = []
    for i in range(n):
        t = dur * (i + 1) / (n + 1)
        p = os.path.join(tmp, f"c{i}.png")
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}",
                "-i", os.path.abspath(video), "-frames:v", "1", os.path.abspath(p)])
        lum = Image.open(p).convert("L")
        rows.append((sum(lum.getdata()) / (lum.width * lum.height), t, p))
    rows.sort()
    _, t_med, p_med = rows[len(rows) // 2]
    shutil.copy(p_med, out_png)
    shutil.rmtree(tmp, ignore_errors=True)
    return t_med


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="work")
    ap.add_argument("--frame-time", type=float, default=None, help="seconds; auto if omitted")
    ap.add_argument("--win-start", default=None, help="signalstats window start sec (auto if omitted)")
    ap.add_argument("--win-dur", default="10", help="signalstats window length sec")
    args = ap.parse_args()

    adir = os.path.join(args.out, "assess")
    os.makedirs(adir, exist_ok=True)

    info = gl.ffprobe_info(args.video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0) or 0)
    num, den = (v.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
    fps = round(float(num) / float(den), 3) if float(den) else 0
    transfer = (v.get("color_transfer") or "").lower()
    prim = (v.get("color_primaries") or "").lower()
    is_log = any(s in (transfer + prim) for s in ("log", "hlg", "smpte2084", "arib-std-b67"))

    ws = args.win_start if args.win_start else f"{max(0.0, dur*0.1):.2f}"
    ss = gl.signalstats(args.video, ws, args.win_dur, adir)

    ft = args.frame_time if args.frame_time is not None else \
        pick_frame(args.video, dur, os.path.join(adir, "frame.png"))
    if args.frame_time is not None:
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{ft:.2f}",
                "-i", os.path.abspath(args.video), "-frames:v", "1",
                os.path.abspath(os.path.join(adir, "frame.png"))])

    def cast(stat, lo, hi):
        d = ss.get(stat, 128) - 128
        if abs(d) < 2: return "neutral"
        return f"{hi} (+{d:.1f})" if d > 0 else f"{lo} ({d:.1f})"

    lines = [
        f"video       : {args.video}",
        f"dimensions  : {v.get('width')}x{v.get('height')}  @ {fps} fps   pix_fmt={v.get('pix_fmt')}",
        f"duration    : {dur:.1f}s    audio: {a['codec_name'] if a else 'NONE'}",
        f"color       : transfer={transfer or '?'} primaries={prim or '?'}  ->  "
        + ("LOG/flat profile - convert log->Rec.709 in the corrective BASE first"
           if is_log else "already Rec.709/standard - correct WB/exposure in the BASE"),
        f"exposure    : YAVG={ss['YAVG']:.1f}/255  ->  " +
        ("a bit dark, lift gamma slightly" if ss["YAVG"] < 110 else
         "bright, watch highlights" if ss["YAVG"] > 150 else "ok"),
        f"white bal   : UAVG={ss['UAVG']:.1f} -> {cast('UAVG','warm/yellow','cool/blue')} ; "
        f"VAVG={ss['VAVG']:.1f} -> {cast('VAVG','green','red/magenta')}",
        f"frame       : assess/frame.png  @ {ft:.1f}s (representative)",
        "",
        "Suggested BASE direction (retune in looks.json, keep it subtle - do NOT push U/V",
        "all the way to 128 or you desaturate skin):",
    ]
    tips = []
    if not is_log:
        if ss["UAVG"] < 126: tips.append("warm cast -> add a little blue (colorbalance bm/bh +, rm/rh -)")
        if ss["UAVG"] > 130: tips.append("cool cast -> add a little warmth (colorbalance rm/rh +, bm/bh -)")
        if ss["VAVG"] > 130: tips.append("magenta lean -> ease red slightly, but skin lives here - go gentle")
        if ss["VAVG"] < 126: tips.append("green lean -> add a touch of magenta (colorbalance gm/gs -)")
        if ss["YAVG"] < 110: tips.append("underexposed -> eq=gamma~1.05, small brightness lift")
        tips.append("then mild eq=contrast~1.06:saturation~1.05 to undo flatness")
    else:
        tips.append("apply your camera's log->Rec.709 conversion (LUT or curve) as the BASE, THEN style")
    lines += ["  - " + t for t in tips] if tips else ["  - looks clean; a light contrast/sat lift is enough"]

    txt = "\n".join(lines)
    print(txt)
    with open(os.path.join(adir, "assessment.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    with open(os.path.join(adir, "assessment.json"), "w", encoding="utf-8") as f:
        json.dump({"width": v.get("width"), "height": v.get("height"), "fps": fps,
                   "duration_s": dur, "pix_fmt": v.get("pix_fmt"), "is_log": is_log,
                   "audio": (a["codec_name"] if a else None), "signalstats": ss,
                   "frame_time": ft, "frame": "assess/frame.png"}, f, indent=2)


if __name__ == "__main__":
    main()
