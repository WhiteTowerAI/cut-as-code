"""Build a local, editable review page from a content-cards plan."""

import argparse
import html
import json
import webbrowser
from pathlib import Path


PLACEMENTS = ("top", "bottom", "left", "right", "center")


def _copy_text(card):
    copy = card.get("copy", {})
    return copy.get("text") or copy.get("suggested_text", "")


def _placement_options(selected):
    options = ['<option value="">Unplaced</option>']
    for value in PLACEMENTS:
        mark = " selected" if value == selected else ""
        options.append(f'<option value="{value}"{mark}>{value.title()}</option>')
    return "".join(options)


def _candidate(card):
    card_id = html.escape(str(card["id"]), quote=True)
    card_type = html.escape(str(card.get("card_type", "unknown")))
    evidence = html.escape(str(card.get("evidence_ref", "unknown")))
    copy = html.escape(str(_copy_text(card)), quote=True)
    start = float(card.get("program_start_s", 0))
    duration = float(card.get("duration_s", 0))
    region = card.get("placement", {}).get("region")
    checked = " checked" if card.get("copy", {}).get("status") == "approved" else ""
    return f"""
      <article class="candidate" data-card-id="{card_id}">
        <label class="pick">
          <input type="checkbox" name="selected" aria-label="Select {card_id}"{checked}>
        </label>
        <div class="identity">
          <strong>{card_id}</strong>
          <span>{card_type}</span>
          <span>{start:.3f}s / {duration:.3f}s</span>
          <span>{evidence}</span>
        </div>
        <label class="field copy-field">
          <span>Copy</span>
          <input type="text" name="copy" value="{copy}">
        </label>
        <label class="field placement-field">
          <span>Placement</span>
          <select name="placement">{_placement_options(region)}</select>
        </label>
      </article>"""


def build_review_page(plan):
    brief = plan.get("brief", {})
    cards = plan.get("cards", [])
    theme = html.escape(str(brief.get("theme", "unselected")))
    target = brief.get("target_card_count", len(cards))
    rows = "".join(_candidate(card) for card in cards)
    prefix = """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Content cards review</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #151719;
      --band: #1d2023;
      --surface: #24282b;
      --line: #3b4145;
      --text: #f2eee5;
      --muted: #aeb4b7;
      --accent: #4fc3b4;
      --warning: #f3bd5b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 system-ui, sans-serif;
      letter-spacing: 0;
    }
    header { border-bottom: 1px solid var(--line); background: var(--band); }
    .header-inner, main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
    .header-inner { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; padding: 20px 0; }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    .summary { display: flex; gap: 18px; color: var(--muted); white-space: nowrap; }
    .summary strong { color: var(--text); }
    main { padding: 20px 0 40px; }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 58px;
      padding: 8px 0;
      background: var(--bg);
      border-bottom: 1px solid var(--line);
    }
    #selection-count { color: var(--warning); }
    #selection-count.on-target { color: var(--accent); }
    button {
      min-height: 38px;
      padding: 8px 12px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: transparent;
      color: var(--text);
      font: inherit;
      cursor: pointer;
    }
    button:hover, button:focus-visible { background: #253b38; outline: none; }
    form { display: grid; gap: 10px; padding-top: 14px; }
    .candidate {
      display: grid;
      grid-template-columns: 40px 180px minmax(260px, 1fr) 170px;
      gap: 14px;
      align-items: center;
      min-height: 104px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
    }
    .pick { display: grid; place-items: center; align-self: stretch; cursor: pointer; }
    .pick input { width: 20px; height: 20px; accent-color: var(--accent); }
    .identity { display: grid; gap: 2px; min-width: 0; color: var(--muted); }
    .identity strong { color: var(--text); font-size: 15px; }
    .identity span { overflow-wrap: anywhere; }
    .field { display: grid; gap: 6px; min-width: 0; color: var(--muted); }
    input[type="text"], select {
      width: 100%;
      min-height: 40px;
      border: 1px solid #50575c;
      border-radius: 4px;
      background: #171a1c;
      color: var(--text);
      font: inherit;
      padding: 8px 10px;
    }
    input[type="text"]:focus, select:focus { border-color: var(--accent); outline: 2px solid #265950; }
    @media (max-width: 780px) {
      .header-inner, .toolbar { align-items: stretch; flex-direction: column; gap: 10px; }
      .toolbar { position: static; }
      .toolbar button { width: 100%; }
      .summary { display: grid; gap: 2px; white-space: normal; }
      .candidate { grid-template-columns: 36px 1fr; align-items: start; }
      .copy-field, .placement-field { grid-column: 2; }
    }
  </style>
</head>"""
    heading = f"""
<body data-target="{target}">
  <header>
    <div class="header-inner">
      <h1>Content cards review</h1>
      <div class="summary"><span>Theme {theme}</span><span>Target {target}</span></div>
    </div>
  </header>
  <main>
    <div class="toolbar">
      <strong id="selection-count" aria-live="polite"></strong>
      <button id="download" type="button">Download review JSON</button>
    </div>
    <form id="review-form">{rows}
    </form>
  </main>"""
    suffix = """
  <script>
    const candidates = [...document.querySelectorAll(".candidate")];
    const target = Number(document.body.dataset.target);
    const count = document.querySelector("#selection-count");
    function selectedCount() {
      return candidates.filter((row) => row.querySelector('[name="selected"]').checked).length;
    }
    function updateCount() {
      const selected = selectedCount();
      count.textContent = `${selected} selected / target ${target}`;
      count.classList.toggle("on-target", selected === target);
    }
    for (const checkbox of document.querySelectorAll('[name="selected"]')) {
      checkbox.addEventListener("change", updateCount);
    }
    document.querySelector("#download").addEventListener("click", () => {
      const review = {
        schema_version: 1,
        cards: candidates.map((row) => ({
          id: row.dataset.cardId,
          selected: row.querySelector('[name="selected"]').checked,
          copy: row.querySelector('[name="copy"]').value,
          placement: row.querySelector('[name="placement"]').value,
        })),
      };
      const url = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2) + "\\n"], {type: "application/json"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = "content-cards-review.json";
      link.click();
      URL.revokeObjectURL(url);
    });
    updateCount();
  </script>
</body>
</html>
"""
    return prefix + heading + suffix


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("output")
    parser.add_argument("--open", action="store_true", help="open the generated review page")
    args = parser.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_review_page(plan), encoding="utf-8")
    print(output)
    if args.open:
        webbrowser.open(output.as_uri())


if __name__ == "__main__":
    main()
