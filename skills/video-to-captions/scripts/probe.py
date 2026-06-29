"""Probe the source video and write src/source-meta.json for Root.tsx to import.

Removes the two brittle things Root.tsx otherwise depends on:
  - the hand-edited static width/height/duration, and
  - the runtime getVideoMetadata/calculateMetadata call (which fails on some
    server-side render paths and silently falls back to a 4K render).

Usage:
  python probe.py [source_video] [out_json]
Defaults:
  source_video = public/source.mp4   (captions skill stages the clip in public/)
  out_json     = src/source-meta.json

Writes: { "width": int, "height": int, "durationInSeconds": float }
Root.tsx multiplies durationInSeconds by its render FPS to get durationInFrames.
"""
import sys, json, subprocess

def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    st = d["streams"][0]
    return {
        "width": int(st["width"]),
        "height": int(st["height"]),
        "durationInSeconds": round(float(d["format"]["duration"]), 3),
    }

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "public/source.mp4"
    out = sys.argv[2] if len(sys.argv) > 2 else "src/source-meta.json"
    meta = probe(src)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(f"[probe] {src} -> {out}: {meta}")

if __name__ == "__main__":
    main()
