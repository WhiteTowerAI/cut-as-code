#!/usr/bin/env python3
"""Read a title for video-overlay from video-to-shorts artifacts."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SELECTORS = {"order", "id", "short_id", "filename"}


class TitleSourceError(RuntimeError):
    pass


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.in_cell:
            text = html.unescape("".join(self.current_cell)).strip()
            self.current_row.append(re.sub(r"\s+", " ", text))
            self.in_cell = False
        elif tag == "tr" and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []


def fail(message: str) -> None:
    print(f"[video-overlay] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TitleSourceError(f"plan not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TitleSourceError(f"plan is not valid JSON: {path}: {exc}") from exc


def normalize_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def filename_values(item: dict[str, Any]) -> set[str]:
    values = {
        normalize_path(item.get("id")),
        normalize_path(item.get("short_id")),
    }
    outputs = item.get("outputs")
    if isinstance(outputs, dict):
        for key in ("directory", "source_video", "vertical_video", "vertical_reframe_dir"):
            raw = normalize_path(outputs.get(key))
            if raw:
                values.add(raw)
                values.add(Path(raw).name.lower())
                parent = Path(raw).parent.name.lower()
                if parent:
                    values.add(parent)
    return {value for value in values if value}


def item_matches(item: dict[str, Any], selector_by: str, selector_value: str) -> bool:
    if selector_by == "order":
        try:
            return int(item.get("order")) == int(selector_value)
        except (TypeError, ValueError):
            return False
    if selector_by in {"id", "short_id"}:
        return str(item.get(selector_by, "")) == selector_value
    if selector_by == "filename":
        needle = normalize_path(selector_value)
        if not needle:
            return False
        return any(needle == value or needle in value for value in filename_values(item))
    raise TitleSourceError(f"unsupported selector: {selector_by}")


def candidate_label(item: dict[str, Any]) -> str:
    return (
        f"order={item.get('order')} "
        f"id={item.get('id')} "
        f"short_id={item.get('short_id')} "
        f"title={item.get('title')!r}"
    )


def select_from_plan(plan_path: Path, selector_by: str, selector_value: str) -> dict[str, Any]:
    plan = load_json(plan_path)
    shorts = plan.get("shorts")
    if not isinstance(shorts, list):
        raise TitleSourceError(f"plan has no shorts array: {plan_path}")

    matches = [
        item for item in shorts
        if isinstance(item, dict) and item_matches(item, selector_by, selector_value)
    ]
    if not matches:
        raise TitleSourceError(
            f"no short matched selector {selector_by}={selector_value!r} in {plan_path}"
        )
    if len(matches) > 1:
        candidates = "\n".join(f"- {candidate_label(item)}" for item in matches)
        raise TitleSourceError(
            f"multiple shorts matched selector {selector_by}={selector_value!r} in {plan_path}:\n{candidates}"
        )
    return matches[0]


def parse_html_rows(html_path: Path) -> list[dict[str, str]]:
    try:
        parser = TableParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TitleSourceError(f"preview HTML not found: {html_path}") from exc

    if not parser.rows:
        raise TitleSourceError(f"preview HTML has no parseable table rows: {html_path}")

    header = [cell.lower() for cell in parser.rows[0]]
    if "title" not in header:
        raise TitleSourceError(f"preview HTML title table could not be parsed: {html_path}")

    rows: list[dict[str, str]] = []
    for row in parser.rows[1:]:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        rows.append({header[index]: row[index] for index in range(len(header))})
    return rows


def select_from_html(html_path: Path, selector_by: str, selector_value: str) -> dict[str, Any]:
    rows = parse_html_rows(html_path)

    def matches(row: dict[str, str]) -> bool:
        if selector_by == "order":
            return row.get("#") == str(selector_value) or row.get("order") == str(selector_value)
        if selector_by in {"id", "short_id"}:
            return row.get("id") == selector_value
        if selector_by == "filename":
            needle = normalize_path(selector_value)
            return needle in normalize_path(row.get("id"))
        return False

    found = [row for row in rows if matches(row)]
    if not found:
        raise TitleSourceError(
            f"no short matched selector {selector_by}={selector_value!r} in {html_path}"
        )
    if len(found) > 1:
        candidates = "\n".join(
            f"- order={row.get('#') or row.get('order')} id={row.get('id')} title={row.get('title')!r}"
            for row in found
        )
        raise TitleSourceError(
            f"multiple shorts matched selector {selector_by}={selector_value!r} in {html_path}:\n{candidates}"
        )
    return {
        "order": found[0].get("#") or found[0].get("order"),
        "id": found[0].get("id"),
        "short_id": found[0].get("id"),
        "title": found[0].get("title"),
    }


def validate_title(item: dict[str, Any], selector_by: str, selector_value: str) -> str:
    title = item.get("title")
    if not isinstance(title, str) or title.strip() == "":
        raise TitleSourceError(
            f"matched short has missing title for selector {selector_by}={selector_value!r}: {candidate_label(item)}"
        )
    return title.strip()


def build_result(
    title: str,
    source_kind: str,
    source_path: Path,
    selector_by: str,
    selector_value: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "type": "video-to-shorts",
        "selector": {
            "by": selector_by,
            "value": int(selector_value) if selector_by == "order" and str(selector_value).isdigit() else selector_value,
        },
    }
    if source_kind == "plan":
        source["planPath"] = str(source_path)
    else:
        source["previewHtmlPath"] = str(source_path)

    return {
        "title": title,
        "source": source,
        "matchedShort": {
            "order": item.get("order"),
            "id": item.get("id"),
            "short_id": item.get("short_id"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read a video-overlay title from video-to-shorts artifacts.")
    parser.add_argument("--plan", type=Path, help="Path to shorts_plan.json. Preferred source.")
    parser.add_argument("--preview-html", type=Path, help="Path to shorts_plan_preview.html fallback.")
    parser.add_argument("--selector", choices=sorted(SELECTORS), required=True)
    parser.add_argument("--value", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.plan:
            item = select_from_plan(args.plan, args.selector, args.value)
            title = validate_title(item, args.selector, args.value)
            result = build_result(title, "plan", args.plan, args.selector, args.value, item)
        elif args.preview_html:
            item = select_from_html(args.preview_html, args.selector, args.value)
            title = validate_title(item, args.selector, args.value)
            result = build_result(title, "html", args.preview_html, args.selector, args.value, item)
        else:
            raise TitleSourceError("provide --plan or --preview-html")
    except TitleSourceError as exc:
        fail(str(exc))
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
