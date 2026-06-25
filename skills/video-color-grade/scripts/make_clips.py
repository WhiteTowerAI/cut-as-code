#!/usr/bin/env python3
"""Short labeled preview clips of selected looks, so they're judged in motion (audio kept).
Label is a PIL PNG overlaid by ffmpeg (drawtext font paths are unreliable on Windows).

  python scripts/make_clips.py SRC.mp4 looks.json --out work/clips --pick clean_neutral,warm_filmic,teal_orange --with-original
  python scripts/make_clips.py SRC.mp4 looks.json --out work/clips --ss 148 --t 8
"""
import argparse, os
import gradelib as gl
from PIL import Image, ImageDraw


def label_png(text, path):
    f = gl.font(17)
    tmp = Image.new("RGBA", (10, 10)); bb = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=f)
    tw, th, pad = bb[2]-bb[0], bb[3]-bb[1], 8
    im = Image.new("RGBA", (tw+pad*2, th+pad*2), (15, 15, 14, 150))
    ImageDraw.Draw(im).text((pad, pad-bb[1]), text, font=f, fill=(255, 255, 255, 255))
    im.save(path)


def render_clip(video, ss, t, chain, label, out, workdir):
    lp = os.path.join(workdir, "_lbl.png"); label_png(label, lp)
    gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(ss), "-t", str(t),
            "-i", os.path.abspath(video), "-i", os.path.abspath(lp),
            "-filter_complex", f"[0:v]{chain}[g];[g][1:v]overlay=10:10[v]",
            "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            os.path.abspath(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("looks")
    ap.add_argument("--out", default="work/clips")
    ap.add_argument("--pick", default=None, help="comma names; default = first 3 looks")
    ap.add_argument("--ss", default="0"); ap.add_argument("--t", default="8")
    ap.add_argument("--with-original", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    spec = gl.load_spec(args.looks)

    names = [s.strip() for s in args.pick.split(",")] if args.pick else \
        [l["name"] for l in spec["looks"][:3]]

    if args.with_original:
        render_clip(args.video, args.ss, args.t, "null", "ORIGINAL  ·  as shot",
                    os.path.join(args.out, "clip_0_original.mp4"), args.out)
        print("ok clip_0_original.mp4")
    for nm in names:
        lk = gl.get_look(spec, nm)
        render_clip(args.video, args.ss, args.t, gl.full_chain(spec, lk), lk["label"],
                    os.path.join(args.out, f"clip_{nm}.mp4"), args.out)
        print(f"ok clip_{nm}.mp4")
    try:
        os.remove(os.path.join(args.out, "_lbl.png"))
    except OSError:
        pass


if __name__ == "__main__":
    main()
