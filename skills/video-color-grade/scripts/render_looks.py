#!/usr/bin/env python3
"""Render every look onto ONE representative frame and build the choose-one deliverables:
a labeled full-res contact sheet + a zoomed face/skin-crop strip (skin is the quality bar).

  python scripts/render_looks.py work/assess/frame.png looks.json --out work/looks
  python scripts/render_looks.py --video SRC.mp4 --time 150 looks.json --out work/looks
  # face crop is auto (centered upper-middle); override for off-center subjects:
  python scripts/render_looks.py work/assess/frame.png looks.json --out work/looks --face-crop 200:175:235:48

Labels are drawn with PIL (no drawtext). Same frame for all looks = a fair comparison.
"""
import argparse, os
import gradelib as gl
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame", nargs="?", help="representative frame PNG (or use --video/--time)")
    ap.add_argument("looks")
    ap.add_argument("--out", default="work/looks")
    ap.add_argument("--video"); ap.add_argument("--time", type=float)
    ap.add_argument("--face-crop", default=None, help="ffmpeg crop W:H:X:Y for the skin strip")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    spec = gl.load_spec(args.looks)

    frame = args.frame
    if not frame:
        if not (args.video and args.time is not None):
            raise SystemExit("give a frame PNG, or --video SRC --time SEC")
        frame = os.path.join(args.out, "frame.png")
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{args.time:.2f}",
                "-i", os.path.abspath(args.video), "-frames:v", "1", os.path.abspath(frame)])

    panels = [("0_original", "ORIGINAL  ·  as shot", frame)]
    for lk in spec["looks"]:
        out = os.path.join(args.out, f"look_{lk['name']}.png")
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.abspath(frame),
                "-vf", gl.full_chain(spec, lk), os.path.abspath(out)])
        panels.append((lk["name"], f"{lk['label']}  ·  {lk.get('desc','')}", out))
    Image.open(frame).convert("RGB").save(os.path.join(args.out, "look_0_original.png"))

    imgs = [Image.open(p).convert("RGB") for _, _, p in panels]
    iw, ih = imgs[0].size

    # ---- contact sheet: 2 columns, full-res tiles, labeled ----
    cols, lblh, gap, mar, hdr = 2, 34, 14, 22, 60
    rows = (len(panels) + cols - 1) // cols
    W = mar*2 + cols*iw + (cols-1)*gap
    H = mar*2 + hdr + rows*(ih+lblh) + (rows-1)*gap
    sheet = Image.new("RGB", (W, H), (18, 18, 17)); d = ImageDraw.Draw(sheet)
    d.text((mar, mar+6), args.title or "color grade options  —  pick one", font=gl.font(30), fill=(250, 249, 245))
    d.text((mar, mar+42), "Each look = corrective base (WB+exposure+contrast) + a creative layer.",
           font=gl.font(16, False), fill=(170, 168, 160))
    for i, (im, (_, label, _)) in enumerate(zip(imgs, panels)):
        r, c = divmod(i, cols)
        x = mar + c*(iw+gap); y = mar + hdr + r*(ih+lblh+gap)
        d.rectangle([x, y, x+iw, y+lblh], fill=(90, 70, 40) if i else (44, 44, 42))
        d.text((x+10, y+8), label, font=gl.font(17), fill=(250, 249, 245))
        sheet.paste(im, (x, y+lblh))
        d.rectangle([x, y, x+iw-1, y+lblh+ih-1], outline=(70, 70, 68))
    sheet.save(os.path.join(args.out, "looks_compare.png"))

    # ---- face/skin strip (skin is the quality bar) ----
    if args.face_crop:
        cw, chh, cx, cy = (int(v) for v in args.face_crop.split(":"))
    else:  # heuristic: centered upper-middle box (works for typical talking heads)
        cw, chh = int(iw*0.42), int(ih*0.62); cx = (iw-cw)//2; cy = int(ih*0.08)
    sc = max(1.0, 300.0/cw)
    crops = [im.crop((cx, cy, cx+cw, cy+chh)).resize((int(cw*sc), int(chh*sc))) for im in imgs]
    fw, fh = crops[0].size; flbl, fgap = 24, 6
    strip = Image.new("RGB", (len(crops)*fw + (len(crops)-1)*fgap, fh+flbl), (18, 18, 17))
    sd = ImageDraw.Draw(strip)
    for i, (cr, (name, _, _)) in enumerate(zip(crops, panels)):
        x = i*(fw+fgap); sd.text((x+4, 4), name.split("_")[-1][:10], font=gl.font(15), fill=(250, 249, 245))
        strip.paste(cr, (x, flbl))
    strip.save(os.path.join(args.out, "face_skin_check.png"))

    print(f"wrote {len(spec['looks'])} looks + looks_compare.png + face_skin_check.png to {args.out}")
    print("REVIEW the contact sheet and the face strip; retune/drop any look that makes skin grey/green.")


if __name__ == "__main__":
    main()
