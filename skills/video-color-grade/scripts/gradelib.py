"""Shared helpers for the video-color-grade scripts.

Two Windows gotchas are handled here once, so every script inherits the fix:
  * ffmpeg filtergraph options that take a PATH (lut3d, metadata=print:file) choke on
    the drive-letter colon (C:/...). We never pass such a path inline -- we run ffmpeg
    with cwd set to the file's folder and reference it by BASENAME (no colon).
  * Labels are drawn with PIL (drawtext fontfile path escaping is unreliable on Windows).
"""
import json, os, subprocess, sys, collections
from PIL import ImageFont

# Fonts: Windows TTFs by default. Swap for other platforms / a different identity.
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REG  = "C:/Windows/Fonts/arial.ttf"


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def run(cmd, cwd=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"\ncommand failed ({r.returncode}): {' '.join(map(str, cmd))}")
    return r


def normalize_spec(spec, require_selected=False):
    """Validate canonical grade plans while leaving legacy looks specs intact."""
    if "schema_version" not in spec:
        return spec
    if spec.get("schema_version") != 1:
        raise ValueError("grade plan schema_version must be 1")
    if spec.get("target") not in ("base-video", "composite"):
        raise ValueError("grade plan target must be base-video or composite")

    looks = spec.get("looks")
    if not isinstance(looks, list) or not looks:
        raise ValueError("grade plan looks must be a non-empty list")
    names = [look.get("name") for look in looks]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("grade plan look names must be unique and non-empty")

    selected = spec.get("selected_look")
    if require_selected and not selected:
        raise ValueError("grade plan selected_look is required for delivery")
    if selected and selected not in names:
        raise ValueError(f"selected look not found: {selected}")
    if require_selected:
        if spec.get("selection_mode") not in ("human", "agent"):
            raise ValueError("grade plan selection_mode must be human or agent")
        if not str(spec.get("selection_rationale", "")).strip():
            raise ValueError("grade plan selection_rationale is required for delivery")
    return spec


def load_spec(path, require_selected=False):
    with open(path, encoding="utf-8") as f:
        return normalize_spec(json.load(f), require_selected=require_selected)


def get_look(spec, name):
    for lk in spec["looks"]:
        if lk["name"] == name:
            return lk
    avail = [l["name"] for l in spec["looks"]]
    raise SystemExit(f"look '{name}' not found. Available: {avail}")


def full_chain(spec, look):
    """A look's full ffmpeg filter = corrective base + ',' + creative layer."""
    base = (spec.get("base") or "").strip()
    layer = (look.get("chain") or "").strip()
    if look.get("prepend_base", True) and base:
        return base + ("," + layer if layer else "")
    return layer or "null"


def ffprobe_info(video):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,"
             "color_space,color_transfer,color_primaries:format=duration,size",
             "-of", "json", os.path.abspath(video)])
    return json.loads(r.stdout)


def signalstats(video, ws, wd, workdir):
    """Mean YAVG/UAVG/VAVG over a window (128 = chroma-neutral). Writes the metadata
    file by basename with cwd=workdir to dodge the colon-in-filtergraph problem."""
    os.makedirs(workdir, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-ss", ws, "-t", wd,
         "-i", os.path.abspath(video),
         "-vf", "signalstats,metadata=print:file=_ss.txt", "-f", "null", "-"], cwd=workdir)
    acc = collections.defaultdict(list)
    ss_file = os.path.join(workdir, "_ss.txt")
    with open(ss_file, encoding="utf-8", errors="ignore") as f:
        for line in f:
            for k in ("YAVG", "UAVG", "VAVG"):
                if f"signalstats.{k}=" in line:
                    try:
                        acc[k].append(float(line.strip().split("=")[-1]))
                    except ValueError:
                        pass
    try:
        os.remove(ss_file)
    except OSError:
        pass
    return {k: (sum(v) / len(v) if v else float("nan")) for k, v in
            (("YAVG", acc["YAVG"]), ("UAVG", acc["UAVG"]), ("VAVG", acc["VAVG"]))}


def apply_lut_relative(in_path, lut_path, out_path, extra_vf=None):
    """Apply a .cube via lut3d with cwd=lut folder + basename (no colon escaping)."""
    lut_dir = os.path.dirname(os.path.abspath(lut_path)) or "."
    vf = f"lut3d={os.path.basename(lut_path)}"
    if extra_vf:
        vf = f"{extra_vf},{vf}"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", os.path.abspath(in_path), "-vf", vf, os.path.abspath(out_path)], cwd=lut_dir)
