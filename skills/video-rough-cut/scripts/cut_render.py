"""Render first_cut.mp4 from edit_final.json.

Robust for MANY segments: each kept segment is a SEPARATE input with its own
input-seek (-ss/-t), then the concat filter joins them with a single re-encode.
This keeps memory ~constant (each input decodes its own small range on demand),
is frame-accurate (input-seek + re-encode), and locks A/V sync per segment.
(Contrast: trimming N times off ONE input forces ffmpeg to buffer the whole
decoded stream -> tens of GB here. Avoided.)

Optional per-segment SPEED (set by assign_speed.py): each kept segment may carry
a `speed` factor (>1 faster, <1 slower). Video is re-timed with setpts=PTS/speed,
audio with atempo=speed (tempo change, NO pitch shift). Both streams are normalized
per input (fps/timebase/sample-rate) so the concat joins stay clean and A/V locked.
When every speed is 1.0 the original (proven) concat graph is used unchanged.

Usage: python cut_render.py <edit_final.json> <source.mp4> <out.mp4>
"""
import sys, json, subprocess

FPS = 30
AR = 44100

def atempo_chain(spd):
    """atempo accepts 0.5..2.0 per instance; chain factors for anything outside."""
    if abs(spd - 1.0) < 1e-6:
        return None
    factors, s = [], spd
    while s > 2.0:
        factors.append(2.0); s /= 2.0
    while s < 0.5:
        factors.append(0.5); s /= 0.5
    factors.append(s)
    return ",".join(f"atempo={f:.6f}" for f in factors)


def load_segments(edit):
    """Normalize a canonical timeline or legacy edit into render segments."""
    if "clips" in edit:
        return [
            {
                "in": clip["source_range"]["start_s"],
                "out": clip["source_range"]["end_s"],
                "speed": clip.get("speed", 1.0),
            }
            for clip in edit["clips"]
        ]
    return list(edit["keep"])

def main():
    edit_p, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    edit = json.load(open(edit_p, encoding="utf-8"))
    keep = [k for k in load_segments(edit) if float(k["out"]) - float(k["in"]) > 0.05]
    keep.sort(key=lambda k: float(k["in"]))
    n = len(keep)

    speeds = [float(k.get("speed", 1.0)) for k in keep]
    has_speed = any(abs(s - 1.0) > 1e-6 for s in speeds)
    src_total = sum(float(k["out"]) - float(k["in"]) for k in keep)
    out_total = sum((float(k["out"]) - float(k["in"])) / s for k, s in zip(keep, speeds))
    print(f"[render] {n} segments, source ~{src_total:.1f}s -> output ~{out_total:.1f}s "
          f"({out_total/60:.2f} min){'  [varispeed]' if has_speed else ''}")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats"]
    for k in keep:
        a, b = float(k["in"]), float(k["out"])
        cmd += ["-ss", f"{a:.3f}", "-t", f"{b-a:.3f}", "-i", src]

    if not has_speed:
        # original proven path: raw concat, single re-encode
        concat_in = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n))
        fc = f"{concat_in}concat=n={n}:v=1:a=1[v][a]"
    else:
        # per-input re-time + normalize, then concat
        chains, labels = [], ""
        for i, spd in enumerate(speeds):
            if abs(spd - 1.0) < 1e-6:
                chains.append(f"[{i}:v:0]fps={FPS},settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
                chains.append(f"[{i}:a:0]aresample={AR},asetpts=N/SR/TB[a{i}]")
            else:
                chains.append(f"[{i}:v:0]setpts=(PTS-STARTPTS)/{spd:.6f},fps={FPS},settb=AVTB[v{i}]")
                at = atempo_chain(spd)
                chains.append(f"[{i}:a:0]{at},aresample={AR},asetpts=N/SR/TB[a{i}]")
            labels += f"[v{i}][a{i}]"
        fc = ";".join(chains) + f";{labels}concat=n={n}:v=1:a=1[v][a]"

    cmd += [
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-c:a", "aac", "-b:a", "160k", "-ar", str(AR),
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
