// build-gallery.mjs — assemble the 5-theme × 13-card contact sheets.
//
// Writes TWO galleries, same 13-row × 5-column layout (one row per card type,
// one column per theme):
//   gallery.html          — static: the shoot.mjs stills (snapshots/*.png).
//   gallery-animated.html  — live: each cell is an <iframe> of the composition
//                            loaded with #loop=<start>,<dur>, so its card plays
//                            on a loop. Identical content, just moving.
// A file:// parent can't script a file:// iframe (opaque origins), so each
// composition drives ITSELF via the dormant #loop hash handler baked into the 5
// index*.html files. Stages are windowed by data-start/duration exactly as the
// HF runtime and shoot.mjs do.
// almanac stills have no prefix (t3s.png); other themes are <theme>-t3s.png.
import { writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const snap = (name) => join(here, "snapshots", name);

// card mid-window time → card name (matches the 13 cues in index.html).
// Each cue is data-start = t-3, duration 6s; the still is the mid-window.
const DUR = 6;
const CARDS = [
  [3, "Intro"], [9, "SectionCard"], [15, "LowerThird"], [21, "StatCallout"],
  [27, "Outro"], [33, "TitleBumper"], [39, "KeypointCallout"], [45, "ReframeCard"],
  [51, "PromptCard"], [57, "BeforeAfter"], [63, "Checklist"], [69, "CommandChips"],
  [75, "ListReveal"],
];
// theme → [snapshot-prefix, composition-file]. "" prefix = almanac (shipped).
const THEMES = [
  ["almanac", "", "index-almanac.html"],
  ["teal", "teal-", "index-teal.html"],
  ["editorial", "editorial-", "index-editorial.html"],
  ["dotgrid", "dotgrid-", "index-dotgrid.html"],
  ["apex", "apex-", "index-apex.html"],
];

const HEAD = (title) => `<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  /* --scale is UNITLESS (CSS scale() rejects lengths); cell width derives from it. */
  :root { --scale: 0.1771; --cw: calc(1920px * var(--scale)); }
  body { margin: 0; background: #1a1a1e; color: #e8e8ea;
         font: 14px/1.4 system-ui, sans-serif; }
  h1 { font-size: 18px; font-weight: 600; padding: 20px 24px 4px; margin: 0;
       overflow-wrap: anywhere; }
  p.sub { padding: 0 24px 16px; margin: 0; color: #9a9aa2; overflow-wrap: anywhere; }
  h1, p.sub { width: 100vw; max-width: 100vw; box-sizing: border-box; }
  .theme-picker { position: sticky; top: 0; z-index: 6; display: flex; gap: 16px;
                  align-items: center; min-height: 52px; box-sizing: border-box;
                  min-width: 0; width: 100vw; max-width: 100vw;
                  margin: 0; padding: 8px 24px; border: 0; border-bottom: 1px solid #3a3a42;
                  background: #202027; }
  .theme-picker legend { padding: 0 12px 0 0; font-weight: 600; }
  .theme-picker label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
  .theme-picker input { accent-color: #65d1c8; }
  table { border-collapse: collapse; width: max-content; }
  thead th { position: sticky; top: 52px; background: #26262c; color: #e8e8ea;
             font-weight: 600; padding: 10px 8px; text-align: center; z-index: 3;
             border-bottom: 2px solid #3a3a42; }
  thead th:first-child { text-align: left; padding-left: 24px; }
  th.card { text-align: left; padding: 8px 8px 8px 24px; white-space: nowrap;
            vertical-align: middle; color: #e8e8ea; font-weight: 600;
            background: #202027; position: sticky; left: 0; z-index: 2; }
  th.card .t { display: block; color: #7a7a82; font-weight: 400; font-size: 12px; }
  td { padding: 6px; vertical-align: top; }
  .missing { display: grid; place-items: center; width: var(--cw); aspect-ratio: 16/9;
             color: #d06060; font-size: 12px; text-align: center;
             border: 1px dashed #5a3a3a; border-radius: 4px; }
  img { display: block; width: var(--cw); height: auto; border-radius: 4px;
        background: repeating-conic-gradient(#3a3a3e 0 25%, #2a2a2e 0 50%) 0 0/24px 24px; }
  .frame { position: relative; width: var(--cw); aspect-ratio: 16/9; overflow: hidden;
           border-radius: 4px;
           background: repeating-conic-gradient(#3a3a3e 0 25%, #2a2a2e 0 50%) 0 0/24px 24px; }
  .frame iframe { position: absolute; top: 0; left: 0; width: 1920px; height: 1080px;
                  transform-origin: top left; transform: scale(var(--scale));
                  border: 0; }
  body:not([data-theme="all"]) { --scale: 0.42; --cw: calc(1920px * var(--scale)); overflow-x: hidden; }
  body:not([data-theme="all"]) [data-theme] { display: none; }
  ${THEMES.map(([name]) => `body[data-theme="${name}"] [data-theme="${name}"] { display: table-cell; }`).join("\n  ")}
  @media (max-width: 900px) {
    :root { --scale: 0.12; }
    body:not([data-theme="all"]) { --scale: 0.11; }
    .theme-picker { position: static; flex-wrap: wrap; gap: 10px 14px; }
    thead th { top: 0; }
  }
</style></head>
<body data-theme="all">
  <h1>${title}</h1>`;

const PICKER = `
  <fieldset class="theme-picker">
    <legend>Theme view</legend>
    <label><input type="radio" name="theme" value="all" checked> Compare all</label>
    ${THEMES.map(([name]) => `<label><input type="radio" name="theme" value="${name}"> ${name}</label>`).join("\n    ")}
  </fieldset>`;

const table = (subline, cellFn, tail = "") => `
  <p class="sub">${subline}</p>
${PICKER}
  <table>
    <thead><tr>
      <th>Card ↓ / Theme →</th>
      ${THEMES.map(([name]) => `<th data-theme="${name}">${name}</th>`).join("")}
    </tr></thead>
    <tbody>${CARDS.map(([t, name]) => `
      <tr>
        <th class="card">${name}<span class="t">t${t}s</span></th>
        ${THEMES.map((th) => `<td data-theme="${th[0]}">${cellFn(th, t)}</td>`).join("")}
      </tr>`).join("")}
    </tbody>
  </table>${tail}
</body></html>`;

// --- static: the stills -----------------------------------------------------
const staticCell = ([, prefix], t) => {
  const rel = `snapshots/${prefix}t${t}s.png`;
  return existsSync(snap(`${prefix}t${t}s.png`))
    ? `<img loading="lazy" src="${rel}" alt="${rel}">`
    : `<div class="missing">missing<br>${rel}</div>`;
};

// --- animated: a self-looping iframe of the composition ---------------------
const animCell = ([, , file], t) =>
  `<div class="frame"><iframe loading="lazy" title="${file} t${t}s"
      src="${file}#loop=${t - 3},${DUR}"></iframe></div>`;

const PICKER_SCRIPT = `
  <script>
    const themeInputs = [...document.querySelectorAll('input[name="theme"]')];
    const requestedTheme = new URLSearchParams(location.hash.slice(1)).get("theme");
    const initialTheme = themeInputs.some((input) => input.value === requestedTheme)
      ? requestedTheme : "all";
    function selectTheme(theme) {
      document.body.dataset.theme = theme;
      themeInputs.find((input) => input.value === theme).checked = true;
      history.replaceState(null, "", "#theme=" + theme);
    }
    for (const input of themeInputs) input.addEventListener("change", () => selectTheme(input.value));
    selectTheme(initialTheme);
  <\/script>`;

writeFileSync(
  join(here, "gallery.html"),
  HEAD("video-add-content-cards — 5 themes × 13 cards (static)") +
    table(
      "Each still is the mid-window of a 6s cue (composition resolution 1920×1080). Checkerboard = transparent (footage would show through); opaque = fullBleed / card.",
      staticCell,
      PICKER_SCRIPT,
    ),
);
// Master clock: Chrome throttles requestAnimationFrame inside cross-origin
// (file://) iframes, so each embedded composition can't self-drive. The parent
// page's top-level rAF is never throttled — broadcast its elapsed seconds to
// every iframe via postMessage; each composition's driver seeks on that clock.
// (A file:// parent can't READ an iframe's document, but it CAN postMessage TO
// it, which is all we need.)
const CLOCK = `
  <script>
    const frames = () => [...document.querySelectorAll("iframe")];
    const t0 = performance.now();
    function beat() {
      const t = (performance.now() - t0) / 1000;
      for (const f of frames()) { try { f.contentWindow.postMessage({ hfClock: t }, "*"); } catch (e) {} }
      requestAnimationFrame(beat);
    }
    requestAnimationFrame(beat);
  <\/script>`;

writeFileSync(
  join(here, "gallery-animated.html"),
  HEAD("video-add-content-cards — 5 themes × 13 cards (animated)") +
    table(
      "Each cell is the live composition looping its 6s cue (entrance → hold → exit). 65 iframes driven by a shared master clock. Same content as the static gallery, just moving.",
      animCell,
      PICKER_SCRIPT + CLOCK,
    ),
);

const missing = CARDS.flatMap(([t]) =>
  THEMES.filter(([, p]) => !existsSync(snap(`${p}t${t}s.png`))).map(([n]) => `${n}/t${t}`));
console.log(`wrote gallery.html + gallery-animated.html (${CARDS.length}×${THEMES.length} grid)`);
if (missing.length) console.log(`${missing.length} missing stills:`, missing.join(", "));
else console.log("all 65 stills present");
