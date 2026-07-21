#!/usr/bin/env python3
"""Bake a look (corrective base + creative layer) into a portable .cube 3D LUT, by pushing
an identity grid through the EXACT ffmpeg chain (the chain is a per-pixel point operation,
so this reproduces it). Self-checks the LUT against the direct chain on a frame.

  python scripts/bake_lut.py looks.json --name clean_neutral --out work/clean_neutral.cube --verify-frame work/assess/frame.png

Why a grid render (not a guess): every filter here (colorbalance/eq/curves/vibrance) maps a
pixel from its own value alone, so feeding all 33^3 grid colors through ffmpeg and reading
them back IS the LUT -- exact, including the YUV round-trip the real video gets.
"""
import argparse, os
import numpy as np
from PIL import Image
import gradelib as gl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("looks"); ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None); ap.add_argument("--size", type=int, default=33)
    ap.add_argument("--verify-frame", default=None)
    args = ap.parse_args()
    spec = gl.load_spec(args.looks); look = gl.get_look(spec, args.name)
    chain = gl.full_chain(spec, look)
    out = os.path.abspath(args.out or f"{args.name}.cube")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    work = os.path.dirname(out) or "."
    N = args.size

    # identity grid, red fastest: index = b*N*N + g*N + r
    idx = np.arange(N**3)
    r, g, b = idx % N, (idx // N) % N, idx // (N*N)
    grid = (np.stack([r, g, b], 1).astype(np.float64) / (N-1) * 255).round().astype(np.uint8)
    Image.fromarray(grid.reshape(N, N*N, 3), "RGB").save(os.path.join(work, "_grid_id.png"))
    gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", os.path.join(work, "_grid_id.png"), "-vf", chain,
            os.path.join(work, "_grid_out.png")])
    o = (np.asarray(Image.open(os.path.join(work, "_grid_out.png")).convert("RGB"))
         .reshape(N**3, 3).astype(np.float64) / 255.0)

    with open(out, "w") as f:
        f.write(f'TITLE "{args.name}"\nLUT_3D_SIZE {N}\n')
        f.write("DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
        for i in range(N**3):
            f.write(f"{o[i,0]:.6f} {o[i,1]:.6f} {o[i,2]:.6f}\n")
    for tmp in ("_grid_id.png", "_grid_out.png"):
        try: os.remove(os.path.join(work, tmp))
        except OSError: pass
    print(f"wrote {out}  ({N}^3 = {N**3} points)")

    if args.verify_frame:
        direct = os.path.join(work, "_verify_direct.png")
        vialut = os.path.join(work, "_verify_lut.png")
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", os.path.abspath(args.verify_frame), "-vf", chain, direct])
        gl.apply_lut_relative(args.verify_frame, out, vialut)
        a = np.asarray(Image.open(vialut).convert("RGB")).astype(np.float64)
        bb = np.asarray(Image.open(direct).convert("RGB")).astype(np.float64)
        dd = np.abs(a - bb)
        print(f"verify LUT vs direct chain:  mean|d|={dd.mean():.3f}/255  max|d|={dd.max():.0f}/255  "
              + ("OK" if dd.mean() < 2 else "CHECK (raise --size or inspect)"))
        for tmp in (direct, vialut):
            try: os.remove(tmp)
            except OSError: pass


if __name__ == "__main__":
    main()
