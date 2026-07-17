"""Markdown and HTML preview writers for video-to-shorts."""

import html
import json
from pathlib import Path

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
        f"- Producer mode: `{result['producer'].get('mode', '')}`",
        f"- Candidates: `{len(result['candidates'])}`",
        "",
    ]
    for rank, cand in enumerate(result["candidates"], start=1):
        metadata = cand.get("metadata") or {}
        lines.extend([
            f"## {rank}. {cand['candidate_id']} - {cand['title']}",
            "",
            f"- Scene type: `{cand['scene_type']}`",
            f"- Evidence mode: `{cand['evidence_mode']}`",
            f"- Time range: `{fmt_time(cand['start_time'])} to {fmt_time(cand['end_time'])}`",
            f"- Duration: `{cand['duration']:.3f}s`",
            f"- Script-generated score: `{cand['score']}`",
            f"- Warnings: `{json.dumps(cand.get('warnings', []), ensure_ascii=False)}`",
            f"- filler_drop_spans: `{json.dumps(cand.get('filler_drop_spans', []), ensure_ascii=False)}`",
            f"- Editorial reason: {metadata.get('editorial_reason', '')}",
            f"- Boundary risk: {metadata.get('boundary_risk', '')}",
            "",
            "**Transcript excerpt**",
            "",
            cand["transcript_excerpt"],
            "",
            "**Six-dimension scoring**",
            "",
            "| Dimension | Score | Reason |",
            "|---|---:|---|",
        ])
        for name, entry in cand["score_breakdown"].items():
            reason = str(entry["reason"]).replace("|", "&#124;").replace("\n", " ")
            lines.append(f"| {name} | {entry['score']} | {reason} |")
        for heading, field in (
            ("visual_observations", "visual_observations"),
            ("visual_risks", "visual_risks"),
            ("visual_keyframes", "visual_keyframes"),
        ):
            lines.extend(["", f"**{heading}**", ""])
            values = cand.get(field) or []
            if values:
                lines.extend(f"- `{value}`" if field == "visual_keyframes" else f"- {value}" for value in values)
            else:
                lines.append("- None")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_candidates_preview_html(path, result):
    def esc(value):
        return html.escape(str(value))

    def list_html(values):
        values = values or []
        if not values:
            return "<li>None</li>"
        return "".join(f"<li>{esc(value)}</li>" for value in values)

    def keyframes_html(values):
        figures = []
        for value in values or []:
            source = ""
            try:
                frame_path = Path(value)
                if frame_path.is_file():
                    source = frame_path.resolve().as_uri()
            except (OSError, ValueError):
                source = ""
            image = f'<img src="{esc(source)}" alt="{esc(Path(value).name)}">' if source else ""
            figures.append(f"<figure>{image}<figcaption>{esc(value)}</figcaption></figure>")
        return "".join(figures) or "<p>None</p>"

    cards = []
    for rank, cand in enumerate(result["candidates"], start=1):
        metadata = cand.get("metadata") or {}
        duration_text = f"{cand['duration']:.3f}s"
        score_rows = "".join(
            f"<tr><td>{esc(name)}</td><td class=\"number\">{esc(entry['score'])}</td><td>{esc(entry['reason'])}</td></tr>"
            for name, entry in cand["score_breakdown"].items()
        )
        cards.append(
            "<article class=\"candidate\">"
            f"<header><div class=\"eyebrow\">#{rank} - <code>{esc(cand['candidate_id'])}</code></div>"
            f"<h2>{esc(cand['title'])}</h2><div class=\"badges\"><span>{esc(cand['scene_type'])}</span>"
            f"<span>{esc(cand['evidence_mode'])}</span><strong>Script-generated score {esc(cand['score'])}</strong></div></header>"
            "<dl class=\"facts\">"
            f"<div><dt>Time range</dt><dd>{esc(fmt_time(cand['start_time']))} to {esc(fmt_time(cand['end_time']))}</dd></div>"
            f"<div><dt>Duration</dt><dd>{esc(duration_text)}</dd></div>"
            f"<div><dt>Warnings</dt><dd>{esc(', '.join(cand.get('warnings', [])) or 'None')}</dd></div>"
            f"<div><dt>filler_drop_spans</dt><dd><code>{esc(json.dumps(cand.get('filler_drop_spans', []), ensure_ascii=False))}</code></dd></div>"
            f"<div><dt>Editorial reason</dt><dd>{esc(metadata.get('editorial_reason', ''))}</dd></div>"
            f"<div><dt>Boundary risk</dt><dd>{esc(metadata.get('boundary_risk', ''))}</dd></div>"
            "</dl>"
            f"<section><h3>Transcript excerpt</h3><p class=\"excerpt\">{esc(cand['transcript_excerpt'])}</p></section>"
            "<section><h3>Six-dimension scoring</h3><table><thead><tr><th>Dimension</th><th>Score</th><th>Reason</th></tr></thead>"
            f"<tbody>{score_rows}</tbody></table></section>"
            "<div class=\"visual-grid\">"
            f"<section><h3>visual_observations</h3><ul>{list_html(cand.get('visual_observations'))}</ul></section>"
            f"<section><h3>visual_risks</h3><ul>{list_html(cand.get('visual_risks'))}</ul></section>"
            "</div>"
            f"<section><h3>visual_keyframes</h3><div class=\"frames\">{keyframes_html(cand.get('visual_keyframes'))}</div></section>"
            "</article>"
        )
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Shorts Candidates Preview</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; margin: 0; background: #eef1f5; color: #1f2933; line-height: 1.45; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px 20px 64px; }}
    .hero, .candidate {{ background: white; border: 1px solid #d8dee9; border-radius: 14px; padding: 22px; margin-bottom: 20px; }}
    .hero {{ background: #172554; color: white; }}
    .eyebrow, dt {{ color: #64748b; }}
    .badges {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .badges span, .badges strong {{ background: #e8eefc; color: #2946a5; border-radius: 999px; padding: 4px 10px; }}
    .badges strong {{ background: #1d4ed8; color: white; }}
    .facts {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; }}
    .facts div {{ border-left: 3px solid #c7d2fe; padding-left: 10px; }}
    dt {{ font-size: 12px; text-transform: uppercase; }}
    dd {{ margin: 3px 0 0; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
    .hero code {{ background: transparent; color: white; padding: 0; border-radius: 0; }}
    .excerpt {{ background: #f8fafc; border: 1px solid #d8dee9; border-radius: 10px; padding: 13px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #eef2f7; text-align: left; }}
    .number {{ text-align: center; font-weight: bold; }}
    .visual-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .frames {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    figure {{ margin: 0; background: #111827; border-radius: 10px; overflow: hidden; }}
    figure img {{ display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: contain; background: black; }}
    figcaption {{ color: #dbeafe; padding: 8px; font: 11px/1.35 Consolas, monospace; overflow-wrap: anywhere; }}
    @media (max-width: 760px) {{ .facts, .visual-grid, .frames {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Shorts Candidates Preview</h1>
      <p>Video: <code>{esc(result['video']['source'])}</code></p>
      <p>Duration: <code>{esc(result['video']['duration_s'])}s</code></p>
      <p>Transcript: <code>{esc(result['transcript']['path'])}</code></p>
      <p>Producer mode: <code>{esc(result['producer'].get('mode', ''))}</code></p>
      <p>Candidates: <code>{len(result['candidates'])}</code></p>
    </section>
    {''.join(cards)}
  </main>
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
        "| Order | Candidate | Scene | Evidence | Time | Source / Removed / Estimated | Six Scores | Score | Validation | Filler Drop Spans | Keep Spans | Outputs |",
        "|---:|---|---|---|---|---|---|---:|---|---|---|---|",
    ]
    for item in plan["shorts"]:
        scores = "; ".join(f"{name}: {entry['score']} ({entry['reason']})" for name, entry in item["score_breakdown"].items())
        row = [
            item["order"], item["candidate_id"], item["scene_type"], item["evidence_mode"],
            f"{fmt_time(item['start_time'])} - {fmt_time(item['end_time'])}",
            f"{item.get('source_duration', item['duration'])} / {item.get('filler_removed_duration', 0)} / {item.get('estimated_output_duration', item['duration'])}",
            scores, item["score"], validation_text(item), item["filler_drop_spans"], item.get("keep_spans", []), item["outputs"],
        ]
        row = [str(x).replace("|", "\\|").replace("\n", " ") for x in row]
        lines.append("| " + " | ".join(row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_plan_preview_html(path, plan):
    def esc(value):
        return html.escape(str(value))

    rows = []
    for item in plan["shorts"]:
        scores = "<ul>" + "".join(
            f"<li><strong>{esc(name)}</strong>: {esc(entry['score'])} - {esc(entry['reason'])}</li>"
            for name, entry in item["score_breakdown"].items()
        ) + "</ul>"
        outputs = "<br>".join(f"{esc(name)}: <code>{esc(value)}</code>" for name, value in item["outputs"].items())
        rows.append(
            "<tr>"
            f"<td>{item['order']}</td>"
            f"<td>{esc(item['candidate_id'])}</td>"
            f"<td>{esc(item['scene_type'])}</td>"
            f"<td>{esc(item['evidence_mode'])}</td>"
            f"<td>{esc(fmt_time(item['start_time']))} - {esc(fmt_time(item['end_time']))}</td>"
            f"<td>{esc(item.get('source_duration', item['duration']))} / {esc(item.get('filler_removed_duration', 0))} / {esc(item.get('estimated_output_duration', item['duration']))}</td>"
            f"<td>{scores}</td>"
            f"<td>{esc(item['score'])}</td>"
            f"<td><strong>{esc(validation_text(item))}</strong></td>"
            f"<td>{esc(item['filler_drop_spans'])}</td>"
            f"<td>{esc(item.get('keep_spans', []))}</td>"
            f"<td>{outputs}</td>"
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
        <th>Order</th><th>Candidate ID</th><th>Scene Type</th><th>Evidence Mode</th><th>Timecode</th>
        <th>Source / Removed / Estimated</th><th>Six Scores</th><th>Score</th><th>Validation</th><th>Filler Drop Spans</th><th>Keep Spans</th><th>Expected Outputs</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
