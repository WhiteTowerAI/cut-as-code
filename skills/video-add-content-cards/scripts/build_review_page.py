"""Populate the content-card review template and extract one frame per candidate."""

import argparse
import base64
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TEMPLATE_RELATIVE = Path("assets/content-cards-review.html")
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / TEMPLATE_RELATIVE
PAYLOAD_MARKER = "__CONTENT_CARDS_REVIEW_DATA__"
PLACEMENTS = {"top", "bottom", "left", "right", "center"}
UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


def _number(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a finite number") from error
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number")
    return number


def _frame_time(card, timeline):
    source_range = card.get("source_range")
    if not isinstance(source_range, dict):
        raise ValueError("card source_range is required for source-frame review")
    start = _number(source_range.get("start_s"), "source_range.start_s")
    end = _number(source_range.get("end_s"), "source_range.end_s")
    if start < 0 or end <= start:
        raise ValueError("card source_range must be a positive half-open range")
    clip = next(
        (
            clip
            for clip in timeline["clips"]
            if clip["source_range"]["start_s"]
            <= start
            < clip["source_range"]["end_s"]
        ),
        None,
    )
    if clip is None:
        raise ValueError("card source_range start is not retained by the timeline")
    retained_end = min(end, float(clip["source_range"]["end_s"]))
    return (start + retained_end) / 2


def _copy_text(card):
    copy = card.get("copy", {})
    if not isinstance(copy, dict):
        raise ValueError("card copy must be an object")
    value = copy.get("text") or copy.get("suggested_text", "")
    if not isinstance(value, str):
        raise ValueError("card copy text must be a string")
    return value


def _extract_frame(video, time_s, output):
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{time_s:.6f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        "scale=960:-2",
        "-q:v",
        "2",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg did not create review frame: {output}")


def _payload(plan, timeline, output):
    errors = projectlib.validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))
    if plan.get("timeline_id") != timeline["timeline_id"]:
        raise ValueError("plan timeline_id does not match the active timeline")
    cards = plan.get("cards")
    if not isinstance(cards, list):
        raise ValueError("plan cards must be a list")
    brief = plan.get("brief", {})
    if not isinstance(brief, dict):
        raise ValueError("plan brief must be an object")
    target = brief.get("target_card_count", len(cards))
    if not isinstance(target, int) or isinstance(target, bool) or target < 1:
        raise ValueError("brief target_card_count must be a positive integer")
    theme = brief.get("theme", "unselected")
    if not isinstance(theme, str):
        raise ValueError("brief theme must be a string")

    assets_dir = output.parent / f"{output.stem}-assets"
    payload_cards = []
    frame_specs = []
    for index, card in enumerate(cards, 1):
        if not isinstance(card, dict) or not isinstance(card.get("id"), str):
            raise ValueError("every card must be an object with a string id")
        frame = assets_dir / f"frame-{index:03d}.jpg"
        frame_specs.append((_frame_time(card, timeline), frame))
        placement = card.get("placement", {})
        if not isinstance(placement, dict):
            raise ValueError("card placement must be an object")
        region = placement.get("region") or ""
        if region and region not in PLACEMENTS:
            raise ValueError(f"invalid card placement: {region!r}")
        payload_cards.append(
            {
                "id": card["id"],
                "card_type": str(card.get("card_type", "unknown")),
                "evidence_ref": str(card.get("evidence_ref", "unknown")),
                "program_start_s": _number(
                    card.get("program_start_s"), "program_start_s"
                ),
                "duration_s": _number(card.get("duration_s"), "duration_s"),
                "copy": _copy_text(card),
                "placement": "bottom",
                "selected": False,
                "screenshot": frame.relative_to(output.parent).as_posix(),
            }
        )
    return {"theme": theme, "target": target, "cards": payload_cards}, frame_specs


def build_review_page(plan, timeline, video, output):
    video = Path(video).resolve()
    if not video.is_file():
        raise FileNotFoundError(f"review source video not found: {video}")
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"review template not found: {TEMPLATE_PATH}")

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count(PAYLOAD_MARKER) != 1:
        raise ValueError("review template must contain exactly one payload marker")
    payload, frame_specs = _payload(plan, timeline, output)
    data = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    document = template.replace(PAYLOAD_MARKER, base64.b64encode(data).decode("ascii"))

    assets_dir = output.parent / f"{output.stem}-assets"
    with tempfile.TemporaryDirectory(
        dir=output.parent, prefix=f".{output.stem}-frames-"
    ) as temporary:
        temporary = Path(temporary)
        staged_frames = []
        for time_s, final_frame in frame_specs:
            staged_frame = temporary / final_frame.name
            _extract_frame(video, time_s, staged_frame)
            staged_frames.append((staged_frame, final_frame))
        assets_dir.mkdir(parents=True, exist_ok=True)
        expected_frames = {final.name for _, final in staged_frames}
        for staged_frame, final_frame in staged_frames:
            final_frame.unlink(missing_ok=True)
            shutil.copyfile(staged_frame, final_frame)
        for stale_frame in assets_dir.glob("frame-*.jpg"):
            if stale_frame.name not in expected_frames:
                stale_frame.unlink()
        output.unlink(missing_ok=True)
        output.write_text(document, encoding="utf-8")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("output")
    parser.add_argument("--video", required=True)
    parser.add_argument("--timeline", required=True)
    args = parser.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    print(build_review_page(plan, timeline, args.video, args.output))


if __name__ == "__main__":
    main()
