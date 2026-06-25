"""Self-check frames AT THE JOINS of the rendered cut (where the only glitch can occur).

Join points in the OUTPUT timeline = cumulative sum of each segment's OUTPUT
duration. With per-segment speed (assign_speed.py) the output duration is
`out_dur` = (out-in)/speed, NOT (out-in) -- so we must use the post-speed length
or every frame-check would land on the wrong frame.
For each join we grab the frames straddling it (-0.1s, +0.0s, +0.1s) into one strip,
and also run blackdetect on the whole output.

Usage: python selfcheck_frames.py <edit_final.json> <first_cut.mp4> <out_dir>
"""
import sys, json, os, subprocess

def seg_out_dur(k):
    """OUTPUT (post-speed) duration of a kept segment."""
    if "out_dur" in k:
        return float(k["out_dur"])
    return (float(k["out"]) - float(k["in"])) / float(k.get("speed", 1.0))

def main():
    edit_p, mp4, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    with open(edit_p, encoding="utf-8") as f:
        edit = json.load(f)
    keep = edit["keep"]

    # cumulative join times in the OUTPUT timeline (post-speed durations)
    joins = []
    t = 0.0
    for k in keep[:-1]:
        t += seg_out_dur(k)
        joins.append(round(t, 3))
    print(f"[selfcheck] {len(joins)} joins in output")

    # build a select expression to grab 3 frames around each join into a tiled strip
    eps = []
    for j in joins:
        for d in (-0.12, 0.0, 0.12):
            tt = max(0.0, j + d)
            eps.append(tt)
    # sample exact timestamps via a single select of nearest frames
    sel = "+".join(f"between(t,{e-0.02:.3f},{e+0.02:.3f})" for e in eps)
    ncols = 3
    nrows = max(1, len(joins))
    vf = f"select='{sel}',scale=200:-1,tile={ncols}x{nrows}"
    strip = os.path.join(out_dir, "joins_strip.png")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", vf,
           "-frames:v", "1", "-vsync", "0", strip]
    subprocess.run(cmd)
    print(f"[selfcheck] wrote {strip} (rows=joins, cols=[-0.12s, join, +0.12s])")

    # blackdetect on the output
    print("[selfcheck] blackdetect on output:")
    r = subprocess.run(["ffmpeg", "-i", mp4, "-vf", "blackdetect=d=0.1:pic_th=0.98",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    blk = [ln for ln in r.stderr.splitlines() if "blackdetect" in ln.lower()]
    if blk:
        for ln in blk:
            print("  ", ln.strip())
    else:
        print("   NONE (no black frames)")

if __name__ == "__main__":
    main()
