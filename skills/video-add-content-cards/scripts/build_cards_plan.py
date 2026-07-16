"""Draft canonical content-card plans from semantic understanding and a timeline."""

import argparse
import json
import sys
from pathlib import Path


UNDERSTAND_SCRIPTS = Path(__file__).resolve().parents[2] / "video-understand" / "scripts"
sys.path.insert(0, str(UNDERSTAND_SCRIPTS))
import projectlib  # noqa: E402


CARD_TYPES = {
    "hook": "intro",
    "key-point": "key-quote",
    "quote": "key-quote",
    "stat": "stat",
    "list": "list",
    "question": "key-quote",
    "cta": "outro",
}
DEFAULT_DURATION_S = {
    "intro": 4.0,
    "key-quote": 6.0,
    "stat": 4.0,
    "list": 8.0,
    "outro": 5.0,
}
THEMES = {"almanac", "teal", "editorial", "dotgrid", "apex"}
CARD_TYPE_NAMES = set(DEFAULT_DURATION_S)
REGIONS = {"top", "bottom", "left", "right", "center"}
BRIEF_FIELDS = {
    "purpose",
    "audience",
    "target_card_count",
    "theme",
    "must_include_types",
    "avoid_regions",
    "notes",
}


def validate_brief(brief):
    if not isinstance(brief, dict):
        raise ValueError("brief must be an object")
    unknown = set(brief) - BRIEF_FIELDS
    if unknown:
        raise ValueError(f"unknown brief fields: {', '.join(sorted(unknown))}")
    for field in ("purpose", "audience", "notes"):
        if field in brief and not isinstance(brief[field], str):
            raise ValueError(f"brief {field} must be a string")
    if "target_card_count" in brief:
        count = brief["target_card_count"]
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("brief target_card_count must be a positive integer")
    if "theme" in brief and brief["theme"] not in THEMES:
        raise ValueError(f"invalid brief theme: {brief['theme']!r}")
    for field, allowed in (
        ("must_include_types", CARD_TYPE_NAMES),
        ("avoid_regions", REGIONS),
    ):
        if field not in brief:
            continue
        values = brief[field]
        if not isinstance(values, list) or any(
            not isinstance(value, str) or value not in allowed for value in values
        ):
            raise ValueError(f"invalid brief {field}: {values!r}")
    return dict(brief)


def _containing_clip(timeline, source_s):
    return next(
        (
            clip
            for clip in timeline["clips"]
            if clip["source_range"]["start_s"] <= source_s < clip["source_range"]["end_s"]
        ),
        None,
    )


def build_cards(understanding, timeline):
    errors = projectlib.validate_timeline(timeline)
    if errors:
        raise ValueError("invalid timeline: " + "; ".join(errors))

    cards = []
    for moment in understanding.get("moments", []):
        card_type = CARD_TYPES.get(moment.get("kind"))
        if not card_type:
            continue
        source_start = float(moment["start_s"])
        clip = _containing_clip(timeline, source_start)
        if clip is None:
            continue
        program_start = projectlib.source_to_program(timeline, source_start)
        remaining = clip["program_range"]["end_s"] - program_start
        duration = min(DEFAULT_DURATION_S[card_type], remaining)
        if duration <= 0:
            continue
        cards.append(
            {
                "id": f"card-{len(cards) + 1:03d}",
                "card_type": card_type,
                "evidence_ref": moment["id"],
                "evidence_refs": moment.get("evidence_refs", []),
                "source_range": {
                    "start_s": source_start,
                    "end_s": float(moment["end_s"]),
                },
                "program_start_s": program_start,
                "duration_s": round(duration, 6),
                "copy": {
                    "status": "draft",
                    "suggested_text": moment.get("summary", ""),
                    "display": {"eyebrow": None, "title": None, "detail": None},
                },
                "placement": {
                    "status": "draft", "region": None,
                    "face_clearance": "pending", "review_still": None,
                },
                "visual_treatment": {"status": "draft"},
                "renderer": {
                    "composition": "cache/content-cards/index.html",
                    "asset": None,
                    "fps": dict(timeline["fps"]),
                },
            }
        )
    return cards


def build_plan(understanding, timeline, brief=None):
    plan = {
        "schema_version": 1,
        "target": "overlay",
        "timeline_id": timeline["timeline_id"],
        "cards": build_cards(understanding, timeline),
    }
    if brief is not None:
        plan["brief"] = validate_brief(brief)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("understanding")
    parser.add_argument("timeline")
    parser.add_argument("output")
    parser.add_argument("--purpose")
    parser.add_argument("--audience")
    parser.add_argument("--target-card-count", type=int)
    parser.add_argument("--theme", choices=sorted(THEMES))
    parser.add_argument("--must-include-type", action="append", choices=sorted(CARD_TYPE_NAMES))
    parser.add_argument("--avoid-region", action="append", choices=sorted(REGIONS))
    parser.add_argument("--notes")
    args = parser.parse_args(argv)
    understanding = json.loads(Path(args.understanding).read_text(encoding="utf-8"))
    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    brief = {
        key: value
        for key, value in {
            "purpose": args.purpose,
            "audience": args.audience,
            "target_card_count": args.target_card_count,
            "theme": args.theme,
            "must_include_types": args.must_include_type,
            "avoid_regions": args.avoid_region,
            "notes": args.notes,
        }.items()
        if value is not None
    }
    projectlib.write_json(
        args.output, build_plan(understanding, timeline, brief=brief or None)
    )


if __name__ == "__main__":
    main()
