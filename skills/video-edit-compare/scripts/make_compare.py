"""Build a side-by-side comparison video from an edit plan.

LEFT  = original, full length, unchanged ("ORIGINAL").
RIGHT = same original on the SAME (original) timeline, but every DROPPED span is
        filled black ("CUT"). So kept = both sides identical; cut = right goes black.
Audio = original track, continuous (you hear what was cut while the right is black).

This makes "what was kept / cut / changed" visible at a glance, perfectly time-synced.

Usage:
  python make_compare.py <edit_final.json> <source.mp4> <out.mp4> [--filter-only]
Writes work/compare_filter.txt and (unless --filter-only) renders out.mp4.
"""
import sys, json, subprocess, os

FONT = "C\\:/Windows/Fonts/arialbd.ttf"   # escaped ':' for ffmpeg filtergraph
W, H = 640, 298                            # per-side size (matches source)
FPS = 30

def drops_from_keep(keep, dur):
    spans = sorted(((float(k["in"]), float(k["out"])) for k in keep))
    drops, t = [], 0.0
    for a, b in spans:
        if a > t + 0.05:
            drops.append((t, a))
        t = max(t, b)
    if dur > t + 0.05:
        drops.append((t, dur))
    return drops

def main():
    edit_p, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    filter_only = "--filter-only" in sys.argv
    edit = json.load(open(edit_p, encoding="utf-8"))
    dur = float(edit.get("source_duration_s") or 0)
    drops = drops_from_keep(edit["keep"], dur)
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in drops)

    lab = (":fontsize=24:fontcolor=white:x=14:y=12:box=1:boxcolor=black@0.6:boxborderw=8"
           f":fontfile='{FONT}'")
    fg = (
        f"[0:v]fps={FPS},scale={W}:{H},setsar=1,split=2[L][R];"
        f"[L]drawtext=text=ORIGINAL{lab}[Lt];"
        f"[R]drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='{expr}',"
        f"drawtext=text=CUT{lab}[Rt];"
        f"[Lt][Rt]hstack=inputs=2[v]"
    )
    ftxt = os.path.join("work", "compare_filter.txt")
    open(ftxt, "w", encoding="utf-8").write(fg)
    print(f"[make_compare] {len(edit['keep'])} keep -> {len(drops)} drop spans, dur={dur}s")
    print(f"[make_compare] wrote {ftxt}")
    if filter_only:
        return
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-filter_complex_script", ftxt,
        "-map", "[v]", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-profile:v", "main", "-level", "4.0", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        out,
    ]
    print("[make_compare] running ffmpeg ...")
    subprocess.run(cmd, check=True)
    print(f"[make_compare] wrote {out}")

if __name__ == "__main__":
    main()
