#!/usr/bin/env python
"""Composite overlay cards onto a source video in one ffmpeg pass.

Each card PNG (full-frame RGBA, from render_cards.py) is looped for its window,
alpha-faded in/out, time-shifted with setpts, and overlaid with enable=between(t,a,b).
Audio is copied (-c:a copy) so A/V sync is identical to the source; duration/fps/dims
are preserved. No color grade, no re-cut.

Usage: python build_render.py overlays.json source.mp4 out.mp4 [--cards cards/]
                                [--crf 19] [--preset medium]
"""
import json, os, argparse, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("source")
    ap.add_argument("out")
    ap.add_argument("--cards", default="cards")
    ap.add_argument("--crf", default="19")
    ap.add_argument("--preset", default="medium")
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding="utf-8"))
    elems = spec["elements"]
    fade = spec.get("fade_s", 0.3)

    inputs = ["-i", a.source]
    for e in elems:
        dur = round(e["t_out"] - e["t_in"], 3)
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", os.path.join(a.cards, e["id"] + ".png")]

    parts = []
    for i, e in enumerate(elems, start=1):
        dur = round(e["t_out"] - e["t_in"], 3)
        fo = round(dur - fade, 3)
        parts.append(
            f"[{i}:v]format=rgba,fade=t=in:st=0:d={fade}:alpha=1,"
            f"fade=t=out:st={fo}:d={fade}:alpha=1,setpts=PTS-STARTPTS+{e['t_in']}/TB[ov{i}]"
        )
        src = "0:v" if i == 1 else f"b{i-1}"
        dst = "vout" if i == len(elems) else f"b{i}"
        parts.append(f"[{src}][ov{i}]overlay=0:0:enable='between(t,{e['t_in']},{e['t_out']})'[{dst}]")
    fc = ";".join(parts)

    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", fc,
           "-map", "[vout]", "-map", "0:a",
           "-c:a", "copy",
           "-c:v", "libx264", "-preset", a.preset, "-crf", a.crf,
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]

    print(f"compositing {len(elems)} cards -> {a.out}")
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
