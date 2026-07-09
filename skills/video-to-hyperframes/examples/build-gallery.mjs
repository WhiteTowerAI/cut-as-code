// build-gallery.mjs — assemble the 5-theme × 13-card contact sheet.
//
// Reads snapshots/ (produced by shoot.mjs, one run per theme) and writes
// gallery.html: a 13-row × 5-column grid, one row per card type, one column
// per theme, so you can eyeball how each card looks across all 5 looks at once.
// almanac shots have no prefix (t3s.png); other themes are <theme>-t3s.png.
import { writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const snap = (name) => join(here, "snapshots", name);

// card mid-window times → card names (matches the 13 cues in index.html)
const CARDS = [
  [3, "Intro"], [9, "SectionCard"], [15, "LowerThird"], [21, "StatCallout"],
  [27, "Outro"], [33, "TitleBumper"], [39, "KeypointCallout"], [45, "ReframeCard"],
  [51, "PromptCard"], [57, "BeforeAfter"], [63, "Checklist"], [69, "CommandChips"],
  [75, "ListReveal"],
];
// theme → snapshot filename prefix ("" = almanac, the shipped look)
const THEMES = [
  ["almanac", ""], ["teal", "teal-"], ["editorial", "editorial-"],
  ["dotgrid", "dotgrid-"], ["apex", "apex-"],
];

const cell = (prefix, t) => {
  const file = `snapshots/${prefix}t${t}s.png`;
  return existsSync(snap(`${prefix}t${t}s.png`))
    ? `<img loading="lazy" src="${file}" alt="${file}">`
    : `<div class="missing">missing<br>${file}</div>`;
};

const rows = CARDS.map(([t, name]) => `
    <tr>
      <th class="card">${name}<span class="t">t${t}s</span></th>
      ${THEMES.map(([, prefix]) => `<td>${cell(prefix, t)}</td>`).join("")}
    </tr>`).join("");

const html = `<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<title>video-to-hyperframes — 5 themes × 13 cards</title>
<style>
  body { margin: 0; background: #1a1a1e; color: #e8e8ea;
         font: 14px/1.4 system-ui, sans-serif; }
  h1 { font-size: 18px; font-weight: 600; padding: 20px 24px 4px; margin: 0; }
  p.sub { padding: 0 24px 16px; margin: 0; color: #9a9aa2; }
  table { border-collapse: collapse; width: 100%; }
  thead th { position: sticky; top: 0; background: #26262c; color: #e8e8ea;
             font-weight: 600; padding: 10px 8px; text-align: center; z-index: 2;
             border-bottom: 2px solid #3a3a42; }
  thead th:first-child { text-align: left; padding-left: 24px; }
  th.card { text-align: left; padding: 8px 8px 8px 24px; white-space: nowrap;
            vertical-align: middle; color: #e8e8ea; font-weight: 600;
            background: #202027; position: sticky; left: 0; z-index: 1; }
  th.card .t { display: block; color: #7a7a82; font-weight: 400; font-size: 12px; }
  td { padding: 6px; vertical-align: top; }
  img { display: block; width: 100%; height: auto; border-radius: 4px;
        background: repeating-conic-gradient(#3a3a3e 0 25%, #2a2a2e 0 50%) 0 0/24px 24px; }
  .missing { display: grid; place-items: center; aspect-ratio: 16/9;
             color: #d06060; font-size: 12px; text-align: center;
             border: 1px dashed #5a3a3a; border-radius: 4px; }
</style></head>
<body>
  <h1>video-to-hyperframes — 5 themes × 13 cards</h1>
  <p class="sub">Each still is the mid-window of a 6s cue (composition resolution 1920×1080). Checkerboard = transparent (footage would show through); opaque = fullBleed / card.</p>
  <table>
    <thead><tr>
      <th>Card ↓ / Theme →</th>
      ${THEMES.map(([name]) => `<th>${name}</th>`).join("")}
    </tr></thead>
    <tbody>${rows}
    </tbody>
  </table>
</body></html>`;

writeFileSync(join(here, "gallery.html"), html);
const missing = CARDS.flatMap(([t]) => THEMES.filter(([, p]) => !existsSync(snap(`${p}t${t}s.png`))).map(([n]) => `${n}/t${t}`));
console.log(`wrote gallery.html (${CARDS.length}×${THEMES.length} grid)`);
if (missing.length) console.log(`${missing.length} missing stills:`, missing.join(", "));
else console.log("all 65 stills present");
