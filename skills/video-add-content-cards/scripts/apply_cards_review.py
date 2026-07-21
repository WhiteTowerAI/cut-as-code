"""Validate a browser review export and apply it to a content-cards plan."""

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path


CONTENT_CARD_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(CONTENT_CARD_SCRIPTS))
import build_cards_plan  # noqa: E402


def _review_entries(plan, review):
    if not isinstance(review, dict) or review.get("schema_version") != 1:
        raise ValueError("review schema_version must be 1")
    entries = review.get("cards")
    if not isinstance(entries, list):
        raise ValueError("review cards must be a list")

    plan_cards = plan.get("cards")
    if not isinstance(plan_cards, list):
        raise ValueError("plan cards must be a list")
    plan_ids = [card.get("id") for card in plan_cards if isinstance(card, dict)]
    if len(plan_ids) != len(plan_cards) or any(not isinstance(card_id, str) for card_id in plan_ids):
        raise ValueError("every plan card must have a string id")
    if len(plan_ids) != len(set(plan_ids)):
        raise ValueError("plan card ids must be unique")

    by_id = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("every review card must be an object")
        card_id = entry.get("id")
        if card_id not in plan_ids:
            raise ValueError(f"review references unknown card: {card_id!r}")
        if card_id in by_id:
            raise ValueError(f"review repeats card: {card_id}")
        if not isinstance(entry.get("selected"), bool):
            raise ValueError(f"review selected must be boolean: {card_id}")
        if not isinstance(entry.get("copy"), str):
            raise ValueError(f"review copy must be a string: {card_id}")
        placement = entry.get("placement")
        if not isinstance(placement, str) or (
            placement and placement not in build_cards_plan.REGIONS
        ):
            raise ValueError(f"invalid review placement for {card_id}: {placement!r}")
        if entry["selected"] and not entry["copy"].strip():
            raise ValueError(f"selected card copy is blank: {card_id}")
        if entry["selected"] and not placement:
            raise ValueError(f"selected card placement is missing: {card_id}")
        by_id[card_id] = entry

    missing = set(plan_ids) - set(by_id)
    if missing:
        raise ValueError(f"review is missing cards: {', '.join(sorted(missing))}")
    return by_id


def apply_review(plan, review):
    entries = _review_entries(plan, review)
    theme = plan.get("brief", {}).get("theme")
    if theme not in build_cards_plan.THEMES:
        raise ValueError("plan brief must contain a supported theme")

    updated = copy.deepcopy(plan)
    selected_cards = []
    for card in updated["cards"]:
        entry = entries[card["id"]]
        if not entry["selected"]:
            continue
        card["copy"] = {
            **card.get("copy", {}),
            "status": "approved",
            "text": entry["copy"].strip(),
        }
        card["placement"] = {"status": "approved", "region": entry["placement"]}
        card["visual_treatment"] = {
            **card.get("visual_treatment", {}),
            "status": "approved",
            "theme": theme,
        }
        selected_cards.append(card)

    selected_ids = [card["id"] for card in selected_cards]
    updated["cards"] = selected_cards
    updated["review"] = {
        "status": "approved",
        "selected_card_ids": selected_ids,
        "selected_card_count": len(selected_ids),
        "target_card_count": updated.get("brief", {}).get("target_card_count"),
    }
    return updated


def write_json_atomic(path, data):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        build_cards_plan.projectlib.write_json(temporary, data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("review")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))
    output = args.output or args.plan
    write_json_atomic(output, apply_review(plan, review))
    print(Path(output).resolve())


if __name__ == "__main__":
    main()
