"""Markdown and HTML preview writers for video-to-shorts."""

import html

from transcript_utils import fmt_time


def recommended_marker(candidate):
    if candidate["score"] >= 80 and not candidate.get("warnings"):
        return "YES"
    if candidate["score"] >= 70:
        return "MAYBE"
    return "NO"


def write_candidates_preview_md(path, result):
    lines = [
        "# Shorts Candidates Preview",
        "",
        f"- Video: `{result['video']['source']}`",
        f"- Duration: `{result['video']['duration_s']}s`",
        f"- Transcript: `{result['transcript']['path']}`",
        f"- LLM model: `{result['producer'].get('llm_model', '')}`",
        f"- Candidates: `{len(result['candidates'])}`",
        "",
        "| Rank | Recommend | Time | Duration | Score | Title | Hook | Reason | Excerpt |",
        "|---:|---|---|---:|---:|---|---|---|---|",
    ]
    for rank, cand in enumerate(result["candidates"], start=1):
        row = [
            str(rank),
            recommended_marker(cand),
            f"{fmt_time(cand['start_time'])} - {fmt_time(cand['end_time'])}",
            str(cand["duration"]),
            str(cand["score"]),
            cand["title"],
            cand["hook_sentence"],
            cand["virality_reason"],
            cand["transcript_excerpt"],
        ]
        row = [str(x).replace("|", "\\|").replace("\n", " ") for x in row]
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_candidates_preview_html(path, result):
    def esc(value):
        return html.escape(str(value))

    rows = []
    for rank, cand in enumerate(result["candidates"], start=1):
        rec = recommended_marker(cand)
        rows.append(
            "<tr>"
            f"<td>{rank}</td>"
            f"<td><strong>{esc(rec)}</strong></td>"
            f"<td>{esc(fmt_time(cand['start_time']))} - {esc(fmt_time(cand['end_time']))}</td>"
            f"<td>{esc(cand['duration'])}</td>"
            f"<td>{esc(cand['score'])}</td>"
            f"<td>{esc(cand['title'])}</td>"
            f"<td>{esc(cand['hook_sentence'])}</td>"
            f"<td>{esc(cand['virality_reason'])}</td>"
            f"<td>{esc(cand['transcript_excerpt'])}</td>"
            "</tr>"
        )
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Shorts Candidates Preview</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; line-height: 1.45; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #eef2f7; text-align: left; }}
    td:nth-child(1), td:nth-child(4), td:nth-child(5) {{ text-align: right; white-space: nowrap; }}
    td:nth-child(2), td:nth-child(3) {{ white-space: nowrap; }}
  </style>
</head>
<body>
  <h1>Shorts Candidates Preview</h1>
  <ul>
    <li>Video: <code>{esc(result['video']['source'])}</code></li>
    <li>Duration: <code>{esc(result['video']['duration_s'])}s</code></li>
    <li>Transcript: <code>{esc(result['transcript']['path'])}</code></li>
    <li>LLM model: <code>{esc(result['producer'].get('llm_model', ''))}</code></li>
    <li>Candidates: <code>{len(result['candidates'])}</code></li>
  </ul>
  <table>
    <thead>
      <tr>
        <th>Rank</th><th>Recommend</th><th>Timecode</th><th>Duration</th><th>Score</th>
        <th>Title</th><th>Hook</th><th>Reason</th><th>Transcript Excerpt</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


def validation_text(item):
    validation = item.get("validation") or {}
    if validation.get("passed"):
        return "PASS"
    errors = validation.get("errors") or []
    return "FAIL: " + ", ".join(errors)


def write_plan_preview_md(path, plan):
    lines = [
        "# Shorts Plan Preview",
        "",
        f"- Candidates: `{plan['source_candidates']['path']}`",
        f"- Output shorts: `{len(plan['shorts'])}`",
        "- This is a human-editable plan. No video cutting has been performed.",
        "",
        "| # | ID | Validation | Title | Time | Duration | Score | Hook | Reason | Transcript Excerpt |",
        "|---:|---|---|---|---|---:|---:|---|---|---|",
    ]
    for item in plan["shorts"]:
        row = [
            item["order"],
            item["id"],
            validation_text(item),
            item["title"],
            f"{fmt_time(item['start_time'])} - {fmt_time(item['end_time'])}",
            item["duration"],
            item["score"],
            item["hook_sentence"],
            item["virality_reason"],
            item["transcript_excerpt"],
        ]
        row = [str(x).replace("|", "\\|").replace("\n", " ") for x in row]
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_plan_preview_html(path, plan):
    def esc(value):
        return html.escape(str(value))

    rows = []
    for item in plan["shorts"]:
        rows.append(
            "<tr>"
            f"<td>{item['order']}</td>"
            f"<td>{esc(item['id'])}</td>"
            f"<td><strong>{esc(validation_text(item))}</strong></td>"
            f"<td>{esc(item['title'])}</td>"
            f"<td>{esc(fmt_time(item['start_time']))} - {esc(fmt_time(item['end_time']))}</td>"
            f"<td>{esc(item['duration'])}</td>"
            f"<td>{esc(item['score'])}</td>"
            f"<td>{esc(item['hook_sentence'])}</td>"
            f"<td>{esc(item['virality_reason'])}</td>"
            f"<td>{esc(item['transcript_excerpt'])}</td>"
            "</tr>"
        )
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Shorts Plan Preview</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2933; line-height: 1.45; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #eef2f7; text-align: left; }}
    td:nth-child(1), td:nth-child(6), td:nth-child(7) {{ text-align: right; white-space: nowrap; }}
    td:nth-child(2), td:nth-child(3), td:nth-child(5) {{ white-space: nowrap; }}
  </style>
</head>
<body>
  <h1>Shorts Plan Preview</h1>
  <ul>
    <li>Candidates: <code>{esc(plan['source_candidates']['path'])}</code></li>
    <li>Output shorts: <code>{len(plan['shorts'])}</code></li>
    <li>No video cutting has been performed.</li>
  </ul>
  <table>
    <thead>
      <tr>
        <th>#</th><th>ID</th><th>Validation</th><th>Title</th><th>Timecode</th>
        <th>Duration</th><th>Score</th><th>Hook</th><th>Reason</th><th>Transcript Excerpt</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
