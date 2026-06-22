"""Render first_cut.mp4 from edit_final.json.

Robust for MANY segments: each kept segment is a SEPARATE input with its own
input-seek (-ss/-t), then the concat filter joins them with a single re-encode.
This keeps memory ~constant (each input decodes its own small range on demand),
is frame-accurate (input-seek + re-encode), and locks A/V sync per segment.
(Contrast: trimming N times off ONE input forces ffmpeg to buffer the whole
decoded stream -> tens of GB here. Avoided.)

Usage: python cut_render.py <edit_final.json> <source.mp4> <out.mp4>
"""
import sys, json, subprocess

def main():
    edit_p, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    edit = json.load(open(edit_p, encoding="utf-8"))
    keep = [k for k in edit["keep"] if float(k["out"]) - float(k["in"]) > 0.05]
    keep.sort(key=lambda k: float(k["in"]))

    total = sum(float(k["out"]) - float(k["in"]) for k in keep)
    print(f"[render] {len(keep)} segments, total ~{total:.1f}s ({total/60:.2f} min)")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats"]
    for k in keep:
        a, b = float(k["in"]), float(k["out"])
        cmd += ["-ss", f"{a:.3f}", "-t", f"{b-a:.3f}", "-i", src]
    n = len(keep)
    concat_in = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n))
    fc = f"{concat_in}concat=n={n}:v=1:a=1[v][a]"
    cmd += [
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-movflags", "+faststart",
        out,
    ]
    print(f"[render] launching ffmpeg with {n} seeked inputs + concat (single re-encode)...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("[render] FFMPEG FAILED", r.returncode); sys.exit(1)
    print(f"[render] DONE -> {out}")

if __name__ == "__main__":
    main()
