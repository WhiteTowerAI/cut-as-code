"""Draft canonical content-card plans from semantic understanding and a timeline."""

import argparse
import json
import math
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
THEMES = {"almanac", "teal", "editorial", "dotgrid", "apex", "air"}
CARD_TYPE_NAMES = set(DEFAULT_DURATION_S)
CHART_LAYOUTS = {"bar-chart", "pie-chart", "line-chart"}
CHART_POINT_LIMITS = {
    "bar-chart": (2, 6),
    "pie-chart": (2, 6),
    "line-chart": (3, 8),
}
VISUAL_TREATMENTS_BY_CARD_TYPE = {
    "intro": {"default"},
    "key-quote": {"default"},
    "stat": {"default", "metric-spotlight", *CHART_LAYOUTS},
    "list": {"default", "side-by-side", "parallel-columns"},
    "outro": {"default"},
}
DEFAULT_VISUAL_TREATMENT = {
    "stat": "metric-spotlight",
    "list": "side-by-side",
}
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


def default_visual_treatment(card_type):
    return DEFAULT_VISUAL_TREATMENT.get(card_type, "default")


def validate_visual_treatment(card_type, treatment):
    allowed = VISUAL_TREATMENTS_BY_CARD_TYPE.get(card_type)
    if allowed is None or treatment not in allowed:
        raise ValueError(
            f"invalid visual treatment for {card_type!r}: {treatment!r}"
        )
    return treatment


def _nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def validate_chart_data(card, layout, require_approved=False):
    if layout not in CHART_LAYOUTS:
        return None
    if not isinstance(card, dict) or card.get("card_type") != "stat":
        raise ValueError(f"{layout} is valid only for stat cards")
    data = card.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"{layout} requires a data object")

    status = data.get("status")
    if status is not None and status not in {"draft", "approved", "verified"}:
        raise ValueError(f"invalid chart data status: {status!r}")
    if require_approved and status not in {"approved", "verified"}:
        raise ValueError("chart data is not approved")

    for field in ("dimension_label", "metric_label", "unit", "period"):
        _nonempty_string(data.get(field), f"chart data {field}")

    points = data.get("points")
    minimum, maximum = CHART_POINT_LIMITS[layout]
    if not isinstance(points, list) or not minimum <= len(points) <= maximum:
        raise ValueError(f"{layout} points must contain {minimum} to {maximum} items")

    card_evidence = card.get("evidence_refs")
    if not isinstance(card_evidence, list) or any(
        not isinstance(ref, str) or not ref.strip() for ref in card_evidence
    ):
        raise ValueError("chart card evidence_refs must be a list of non-empty strings")
    evidence_scope = set(card_evidence)
    labels = set()
    values = []
    for index, item in enumerate(points, 1):
        if not isinstance(item, dict):
            raise ValueError(f"chart point {index} must be an object")
        label = _nonempty_string(item.get("label"), f"chart point {index} label").strip()
        label_key = label.casefold()
        if label_key in labels:
            raise ValueError(f"chart point labels must be unique: {label!r}")
        labels.add(label_key)
        values.append(_finite_number(item.get("value"), f"chart point {index} value"))
        evidence_refs = item.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in evidence_refs
        ):
            raise ValueError(f"chart point {index} evidence_refs must be non-empty")
        outside_scope = set(evidence_refs) - evidence_scope
        if outside_scope:
            raise ValueError(
                f"chart point {index} evidence_refs are outside the card evidence scope: "
                + ", ".join(sorted(outside_scope))
            )

    if layout == "bar-chart":
        if any(value < 0 for value in values):
            raise ValueError("bar-chart values must be non-negative")
        if not any(value > 0 for value in values):
            raise ValueError("bar-chart must contain at least one value greater than zero")
    elif layout == "pie-chart":
        if any(value < 0 for value in values):
            raise ValueError("pie-chart values must be non-negative")
        total = sum(values)
        if total <= 0:
            raise ValueError("pie-chart values must sum to more than zero")
        unit = data["unit"].strip().casefold()
        if ("%" in unit or unit in {"percent", "percentage", "pct"}) and not math.isclose(
            total, 100.0, rel_tol=1e-9, abs_tol=1e-6
        ):
            raise ValueError("percentage pie-chart values must sum to 100")
    return data


def validate_clearance(placement, captions_active=None, require_verified=False):
    if not isinstance(placement, dict):
        raise ValueError("placement must be an object")
    region = placement.get("region")
    if region is not None and region not in REGIONS:
        raise ValueError(f"invalid placement region: {region!r}")
    face = placement.get("face_clearance", "pending")
    caption = placement.get("caption_clearance", "pending")
    if face not in {"pending", "verified"}:
        raise ValueError(f"invalid face_clearance: {face!r}")
    if caption not in {"pending", "verified", "not-applicable"}:
        raise ValueError(f"invalid caption_clearance: {caption!r}")
    if captions_active is True and caption == "not-applicable":
        raise ValueError("caption_clearance cannot be not-applicable with active captions")
    if captions_active is False and caption == "verified":
        raise ValueError("caption_clearance must be not-applicable without active captions")
    if require_verified:
        if face != "verified":
            raise ValueError("face_clearance is not verified")
        expected_caption = "verified" if captions_active else "not-applicable"
        if captions_active is None:
            if caption not in {"verified", "not-applicable"}:
                raise ValueError("caption_clearance is not resolved")
        elif caption != expected_caption:
            raise ValueError(f"caption_clearance must be {expected_caption}")
        if not isinstance(placement.get("review_still"), str) or not placement["review_still"].strip():
            raise ValueError("clearance requires a composited review_still")
        if placement.get("clearance_decision_mode") not in {"agent", "human"}:
            raise ValueError("clearance_decision_mode must be agent or human")
        _nonempty_string(placement.get("clearance_rationale"), "clearance_rationale")
    return placement


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
                    "face_clearance": "pending",
                    "caption_clearance": "pending",
                    "review_still": None,
                    "clearance_decision_mode": None,
                    "clearance_rationale": "",
                },
                "visual_treatment": {
                    "status": "draft",
                    "layout": default_visual_treatment(card_type),
                },
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
