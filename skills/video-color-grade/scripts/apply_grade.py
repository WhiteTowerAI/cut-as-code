#!/usr/bin/env python3
"""Apply the CHOSEN look to the full clip at source res/fps, audio copied (sync preserved),
then verify. Use either the look's filter chain or a baked .cube LUT.

  python scripts/apply_grade.py SRC.mp4 --looks looks.json --name clean_neutral --out out/graded.mp4
  python scripts/apply_grade.py SRC.mp4 --lut out/clean_neutral.cube --out out/graded.mp4

Verify = ffprobe (duration/streams kept) + signalstats before/after + a spot frame.
"""
import argparse, os, shutil
import gradelib as gl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--out", required=True)
    ap.add_argument("--looks"); ap.add_argument("--name"); ap.add_argument("--lut")
    ap.add_argument("--crf", default="18"); ap.add_argument("--preset", default="slow")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    if args.lut:
        # apply .cube via lut3d with cwd=lut folder + basename (dodges the colon-in-path issue)
        lut_dir = os.path.dirname(os.path.abspath(args.lut)) or "."
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.abspath(args.video),
                "-vf", f"lut3d={os.path.basename(args.lut)}",
                "-c:v", "libx264", "-crf", args.crf, "-preset", args.preset, "-pix_fmt", "yuv420p",
                "-c:a", "copy", "-movflags", "+faststart", os.path.abspath(args.out)], cwd=lut_dir)
    else:
        if not (args.looks and args.name):
            raise SystemExit("give --lut FILE.cube, or --looks JSON --name LOOK")
        spec = gl.load_spec(args.looks); chain = gl.full_chain(spec, gl.get_look(spec, args.name))
        gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.abspath(args.video),
                "-vf", chain, "-c:v", "libx264", "-crf", args.crf, "-preset", args.preset,
                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                os.path.abspath(args.out)])
    print(f"wrote {args.out}")

    if args.no_verify:
        return
    src = gl.ffprobe_info(args.video); dst = gl.ffprobe_info(args.out)
    def dur(i): return float(i["format"].get("duration", 0) or 0)
    def has_audio(i): return any(s["codec_type"] == "audio" for s in i["streams"])
    print(f"duration  src={dur(src):.1f}s  out={dur(dst):.1f}s  ({'OK' if abs(dur(src)-dur(dst))<0.5 else 'MISMATCH'})")
    print(f"audio     src={has_audio(src)}  out={has_audio(dst)}")
    wd = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_verify")
    a = gl.signalstats(args.video, f"{dur(src)*0.1:.2f}", "10", wd)
    b = gl.signalstats(args.out, f"{dur(src)*0.1:.2f}", "10", wd)
    print(f"WB/exp    Y {a['YAVG']:.1f}->{b['YAVG']:.1f}   U {a['UAVG']:.1f}->{b['UAVG']:.1f}   "
          f"V {a['VAVG']:.1f}->{b['VAVG']:.1f}   (U/V toward 128 = cast reduced)")
    shutil.rmtree(wd, ignore_errors=True)  # throwaway stats dir
    spot = os.path.join(os.path.dirname(os.path.abspath(args.out)), "verify_frame.png")
    gl.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{dur(src)*0.2:.2f}",
            "-i", os.path.abspath(args.out), "-frames:v", "1", spot])
    print(f"spot frame -> {spot}  (eyeball skin + whites)")


if __name__ == "__main__":
    main()
