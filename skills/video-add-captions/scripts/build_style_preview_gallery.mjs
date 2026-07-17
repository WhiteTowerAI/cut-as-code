import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(scriptDirectory, "..");
const assetsDirectory = join(skillRoot, "assets", "style-previews");
const manifestPath = join(assetsDirectory, "preview-manifest.json");
const outputPath = join(assetsDirectory, "index.html");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8").replace(/^\uFEFF/, ""));
const expectedGroups = ["core", "pill", "boxed", "stroked", "shorts"];
const actualGroups = manifest.groups.map((group) => group.id);

if (JSON.stringify(actualGroups) !== JSON.stringify(expectedGroups)) {
  throw new Error(`Unexpected preview groups: ${actualGroups.join(", ")}`);
}

const groupMap = Object.fromEntries(manifest.groups.map((group) => [group.id, group.items]));
const allItems = manifest.groups.flatMap((group) => group.items);
if (manifest.total !== 25 || allItems.length !== 25) {
  throw new Error(`Expected 25 preview items, found manifest.total=${manifest.total}, items=${allItems.length}`);
}

for (const item of allItems) {
  for (const fileName of [item.image, item.props]) {
    if (!existsSync(join(assetsDirectory, fileName))) {
      throw new Error(`Missing preview asset: ${fileName}`);
    }
  }
}

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const titleCase = (value) => String(value)
  .split("-")
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(" ");

const renderCard = (item) => {
  const theme = item.theme ?? "Default";
  const isShorts = item.orientation === "shorts";
  return `
    <article
      class="style-card ${isShorts ? "style-card--shorts" : "style-card--landscape"}"
      data-preview-id="${escapeHtml(item.id)}"
      data-preview-image="${escapeHtml(item.image)}"
      data-preview-label="${escapeHtml(item.label)}"
      role="button"
      tabindex="0"
      aria-pressed="false"
      aria-haspopup="dialog"
      aria-controls="preview-dialog"
      aria-label="Select and enlarge ${escapeHtml(item.label)} caption style"
    >
      <span class="selection-mark" aria-hidden="true">&#10003;</span>
      <div class="preview-frame ${isShorts ? "preview-frame--shorts" : "preview-frame--landscape"}">
        <img src="./${escapeHtml(item.image)}" alt="${escapeHtml(item.label)} caption preview" loading="lazy" draggable="false">
      </div>
      <div class="card-copy">
        <div class="card-heading">
          <h4>${escapeHtml(item.id)}</h4>
          <span class="aspect-badge">${escapeHtml(item.aspectRatio)}</span>
        </div>
        <dl class="metadata-grid">
          <div><dt>Official preset</dt><dd>${escapeHtml(item.preset)}</dd></div>
          <div><dt>Theme</dt><dd>${escapeHtml(titleCase(theme))}</dd></div>
          <div><dt>Karaoke</dt><dd class="${item.karaoke ? "status-on" : "status-off"}">${item.karaoke ? "On" : "Off"}</dd></div>
        </dl>
      </div>
    </article>`;
};

const renderGrid = (items, className) => `<div class="card-grid ${className}">${items.map(renderCard).join("")}</div>`;
const manifestJson = JSON.stringify(manifest).replaceAll("<", "\\u003c");

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Caption Style Gallery</title>
  <style>
    :root {
      --page: #f3f5f8;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --ink: #172033;
      --muted: #667085;
      --line: #dfe4ec;
      --line-strong: #c8d0dc;
      --accent: #2563eb;
      --accent-soft: #eaf1ff;
      --success: #15803d;
      --navy: #111827;
      --radius-lg: 24px;
      --radius-md: 17px;
      --shadow: 0 10px 30px rgba(15, 23, 42, 0.07);
      --shadow-selected: 0 14px 34px rgba(37, 99, 235, 0.18);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-width: 320px;
      background: var(--page);
      color: var(--ink);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    button, input, select, textarea { font: inherit; }
    code { font-family: inherit; }
    img { max-width: 100%; }

    .page-shell {
      width: min(1480px, calc(100% - 40px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      padding: clamp(28px, 5vw, 56px);
      border-radius: 30px;
      background: var(--navy);
      color: #ffffff;
      box-shadow: 0 18px 48px rgba(15, 23, 42, 0.18);
    }
    .hero::after {
      content: "";
      position: absolute;
      width: 300px;
      height: 300px;
      right: -120px;
      top: -150px;
      border-radius: 50%;
      background: rgba(96, 165, 250, 0.16);
    }
    .eyebrow {
      margin: 0 0 10px;
      color: #93c5fd;
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    .hero h1 {
      position: relative;
      margin: 0;
      max-width: 850px;
      font-size: clamp(2.15rem, 5vw, 4.4rem);
      line-height: 1.03;
      letter-spacing: -0.045em;
    }
    .hero-copy {
      position: relative;
      max-width: 760px;
      margin: 20px 0 0;
      color: #cbd5e1;
      font-size: clamp(1rem, 1.7vw, 1.16rem);
    }
    .default-note {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 22px;
      padding: 9px 13px;
      border: 1px solid rgba(147, 197, 253, 0.34);
      border-radius: 999px;
      background: rgba(37, 99, 235, 0.16);
      color: #dbeafe;
      font-size: 0.88rem;
      font-weight: 700;
    }

    .selection-summary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin: 22px 0 0;
      padding: 15px 18px;
      border: 1px solid #bfdbfe;
      border-radius: 16px;
      background: var(--accent-soft);
      color: #1e3a8a;
    }
    .selection-copy { min-width: 0; }
    .selection-copy p { margin: 0; }
    .selection-label {
      color: #5270aa;
      font-size: 0.7rem;
      font-weight: 800;
      letter-spacing: 0.09em;
      text-transform: uppercase;
    }
    .selected-value {
      margin-top: 2px !important;
      color: #5270aa;
      font-size: 1rem;
      font-weight: 800;
    }
    .selected-value.has-selection { color: #1d4ed8; }
    .selection-help {
      margin-top: 3px !important;
      color: var(--muted);
      font-size: 0.79rem;
    }
    .selection-help code { color: #344054; }
    .copy-selection {
      flex: 0 0 auto;
      padding: 9px 14px;
      border: 1px solid #93c5fd;
      border-radius: 10px;
      background: #ffffff;
      color: #1d4ed8;
      font-weight: 800;
      cursor: pointer;
    }
    .copy-selection:disabled { color: #98a2b3; border-color: var(--line); background: #f2f4f7; cursor: not-allowed; }
    .copy-selection.is-copied { color: var(--success); border-color: #a9d8b8; background: #f2fbf5; }

    .gallery-section { margin-top: clamp(48px, 7vw, 78px); }
    .section-heading {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 22px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }
    .section-heading h2 { margin: 0; font-size: clamp(1.55rem, 3vw, 2.25rem); line-height: 1.15; letter-spacing: -0.025em; }
    .section-heading p { max-width: 620px; margin: 0; color: var(--muted); text-align: right; }
    .subgroup + .subgroup { margin-top: 38px; }
    .subgroup-heading { display: flex; align-items: center; gap: 11px; margin: 0 0 16px; }
    .subgroup-heading h3 { margin: 0; font-size: 1.18rem; }
    .count-badge { padding: 3px 9px; border-radius: 999px; background: #e8edf4; color: #596579; font-size: 0.76rem; font-weight: 800; }

    .card-grid {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      align-items: stretch;
      gap: 18px;
    }
    .card-grid--core {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .card-grid--shorts {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }
    .style-card {
      position: relative;
      display: flex;
      flex-direction: column;
      min-width: 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface);
      box-shadow: var(--shadow);
      cursor: pointer;
      outline: none;
      transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
    }
    .style-card--landscape { flex: 1 1 245px; max-width: 310px; }
    .style-card--shorts { flex: 0 1 210px; width: min(100%, 210px); }
    .card-grid--core .style-card--landscape,
    .card-grid--shorts .style-card--shorts {
      width: 100%;
      max-width: none;
    }
    .style-card:hover { transform: translateY(-3px); border-color: var(--line-strong); }
    .style-card:focus-visible { box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2), var(--shadow); }
    .style-card.is-selected {
      transform: translateY(-3px);
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16), var(--shadow-selected);
    }

    .preview-frame {
      display: grid;
      place-items: center;
      overflow: hidden;
      border: 1px solid #e4e8ee;
      border-radius: 12px;
      background: #3b404f;
    }
    .preview-frame--landscape { width: 100%; aspect-ratio: 16 / 9; }
    .preview-frame--shorts { width: min(100%, 168px); aspect-ratio: 9 / 16; margin: 0 auto; }
    .card-grid--shorts .preview-frame--shorts { width: min(100%, 184px); }
    .preview-frame img { width: 100%; height: 100%; object-fit: contain; }

    .card-copy { display: grid; gap: 12px; padding: 13px 4px 3px; }
    .card-heading { display: flex; align-items: start; justify-content: space-between; gap: 10px; margin: 0; }
    .card-heading h4 { min-width: 0; margin: 0; color: var(--ink); font-size: 1rem; line-height: 1.28; overflow-wrap: anywhere; }
    .aspect-badge { flex: 0 0 auto; padding: 3px 8px; border-radius: 999px; background: #eef2f7; color: #526074; font-size: 0.72rem; font-weight: 800; }
    .metadata-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 12px; margin: 0; }
    .metadata-grid div:last-child { grid-column: 1 / -1; }
    .metadata-grid dt {
      color: #8a94a5;
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .metadata-grid dd {
      margin: 2px 0 0;
      color: #344054;
      font-size: 0.82rem;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    .metadata-grid dd.status-on { color: var(--success); }
    .metadata-grid dd.status-off { color: #667085; }
    .selection-mark {
      position: absolute;
      top: 20px;
      right: 20px;
      display: grid;
      width: 28px;
      height: 28px;
      place-items: center;
      border-radius: 50%;
      background: var(--accent);
      color: #ffffff;
      font-size: 0.85rem;
      font-weight: 900;
      opacity: 0;
      transform: scale(0.75);
      transition: opacity 150ms ease, transform 150ms ease;
    }
    .style-card.is-selected .selection-mark { opacity: 1; transform: scale(1); }

    .option-panel {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
      gap: 24px;
      align-items: center;
      padding: clamp(24px, 4vw, 42px);
      border: 1px solid #cbd5e1;
      border-radius: var(--radius-lg);
      background: var(--surface);
      box-shadow: var(--shadow);
    }
    .option-panel h2 { margin: 0 0 10px; font-size: clamp(1.5rem, 3vw, 2.1rem); }
    .option-panel p { margin: 0; color: var(--muted); }
    .option-code { padding: 14px 16px; border-radius: 12px; background: var(--surface-soft); color: #475467; font-size: 0.9rem; font-weight: 700; text-align: center; }

    .preview-dialog {
      position: fixed;
      inset: 0;
      width: min(980px, calc(100vw - 48px));
      max-width: none;
      max-height: calc(100vh - 40px);
      margin: auto;
      padding: 44px 12px 0;
      overflow: hidden;
      border: 0;
      border-radius: 18px;
      background: #ffffff;
      color: var(--ink);
      box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
    }
    .preview-dialog.is-shorts { width: min(360px, calc(100vw - 24px)); }
    .preview-dialog::backdrop {
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(3px);
    }
    .preview-dialog__close {
      display: grid;
      position: absolute;
      z-index: 2;
      top: 8px;
      right: 10px;
      width: 34px;
      height: 34px;
      padding: 0;
      place-items: center;
      border: 0;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.9);
      color: var(--ink);
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.16);
    }
    .preview-dialog__close:hover { background: #ffffff; }
    .preview-dialog__close:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }
    .preview-dialog__figure { margin: 0; }
    .preview-dialog__media {
      display: grid;
      max-height: calc(100vh - 132px);
      place-items: center;
      overflow: hidden;
      background: #ffffff;
    }
    .preview-dialog__image {
      display: block;
      width: auto;
      max-width: 100%;
      height: auto;
      max-height: calc(100vh - 132px);
      object-fit: contain;
      border: 1px solid #e4e7ec;
      border-radius: 12px;
    }
    .preview-dialog__caption {
      padding: 11px 4px 13px;
      color: var(--ink);
      font-size: 1.404rem;
      font-weight: 750;
      line-height: 1.3;
      text-align: center;
      overflow-wrap: anywhere;
    }

    html.modal-open { scroll-behavior: auto; }
    body.modal-open { overflow: hidden; }

    @media (max-width: 820px) {
      .page-shell { width: min(100% - 24px, 1480px); padding-top: 12px; }
      .hero { border-radius: 22px; }
      .selection-summary, .section-heading { align-items: flex-start; flex-direction: column; gap: 12px; }
      .section-heading p { text-align: left; }
      .option-panel { grid-template-columns: 1fr; }
      .style-card--landscape { flex-basis: 270px; }
      .card-grid--core { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .card-grid--shorts { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }
    @media (max-width: 540px) {
      .hero { padding: 26px 22px; }
      .gallery-section { margin-top: 44px; }
      .selection-summary, .option-panel { align-items: stretch; flex-direction: column; }
      .copy-selection { width: 100%; }
      .card-grid { gap: 14px; }
      .style-card--landscape { flex-basis: 100%; max-width: 420px; }
      .style-card--shorts { flex-basis: 168px; width: 168px; }
      .card-grid--core { grid-template-columns: 1fr; }
      .card-grid--shorts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .card-grid--core .style-card--landscape,
      .card-grid--shorts .style-card--shorts { width: 100%; max-width: none; }
      .preview-frame--shorts { width: 138px; }
      .preview-dialog { width: calc(100vw - 20px); max-height: calc(100vh - 20px); padding: 40px 8px 0; border-radius: 14px; }
      .preview-dialog__close { top: 6px; right: 8px; }
      .preview-dialog__media, .preview-dialog__image { max-height: calc(100vh - 100px); }
      .metadata-grid { grid-template-columns: 1fr; }
      .metadata-grid div:last-child { grid-column: auto; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
    }
  </style>
</head>
<body>
  <main class="page-shell">
    <header class="hero">
      <p class="eyebrow">25 offline preview styles</p>
      <h1>Caption Style Gallery</h1>
      <p class="hero-copy">Compare the maintained caption combinations, select one card, copy its exact combination ID, and return that ID to the Agent.</p>
      <div class="default-note">Reply <strong>skip</strong> to the Agent only when you explicitly want the default <strong>clean</strong> style.</div>
    </header>

    <div class="selection-summary" aria-live="polite">
      <div class="selection-copy">
        <p class="selection-label">Selected combination ID</p>
        <p class="selected-value" id="selected-preview">No style selected</p>
        <p class="selection-help">To use the default <code>clean</code> style without browsing, return to the Agent and explicitly reply <code>skip</code>.</p>
      </div>
      <button class="copy-selection" id="copy-selection" type="button" disabled>Copy ID</button>
    </div>

    <section class="gallery-section" aria-labelledby="core-title">
      <div class="section-heading">
        <h2 id="core-title">Core Presets</h2>
        <p>The four primary starting points, including one explicit Karaoke combination.</p>
      </div>
      ${renderGrid(groupMap.core, "card-grid--core")}
    </section>

    <section class="gallery-section" aria-labelledby="background-title">
      <div class="section-heading">
        <h2 id="background-title">Background Styles</h2>
        <p>Pill and boxed treatments are separated so their silhouette and padding differences remain easy to compare.</p>
      </div>
      <div class="subgroup">
        <div class="subgroup-heading"><h3>Pill</h3><span class="count-badge">5 themes</span></div>
        ${renderGrid(groupMap.pill, "")}
      </div>
      <div class="subgroup">
        <div class="subgroup-heading"><h3>Boxed</h3><span class="count-badge">5 themes</span></div>
        ${renderGrid(groupMap.boxed, "")}
      </div>
    </section>

    <section class="gallery-section" aria-labelledby="stroked-title">
      <div class="section-heading">
        <h2 id="stroked-title">Stroked Styles</h2>
        <p>Five background-free options arranged on the same five-column alignment as the background styles.</p>
      </div>
      ${renderGrid(groupMap.stroked, "")}
    </section>

    <section class="gallery-section" aria-labelledby="shorts-title">
      <div class="section-heading">
        <h2 id="shorts-title">Shorts Styles</h2>
        <p>Six vertical-video treatments in one evenly aligned row on wide screens.</p>
      </div>
      ${renderGrid(groupMap.shorts, "card-grid--shorts")}
    </section>

    <section class="gallery-section option-panel" aria-labelledby="karaoke-title">
      <div>
        <h2 id="karaoke-title">Karaoke is an option, not a preset</h2>
        <p>The gallery includes explicit combinations where Karaoke changes the visual result. Later preview adjustments can still turn it on or off.</p>
      </div>
      <span class="option-code">auto · true · false</span>
    </section>
  </main>

  <dialog class="preview-dialog" id="preview-dialog" aria-labelledby="preview-dialog-title">
    <button class="preview-dialog__close" type="button" aria-label="Close enlarged preview">✕</button>
    <figure class="preview-dialog__figure">
      <div class="preview-dialog__media"><img class="preview-dialog__image" alt=""></div>
      <figcaption class="preview-dialog__caption" id="preview-dialog-title">Caption preview</figcaption>
    </figure>
  </dialog>

  <script id="embedded-preview-manifest" type="application/json">${manifestJson}</script>
  <script>
    (() => {
      const cards = [...document.querySelectorAll(".style-card")];
      const selectedPreview = document.getElementById("selected-preview");
      const copySelection = document.getElementById("copy-selection");
      const previewDialog = document.getElementById("preview-dialog");
      const previewDialogImage = previewDialog.querySelector(".preview-dialog__image");
      const previewDialogTitle = document.getElementById("preview-dialog-title");
      const previewDialogClose = previewDialog.querySelector(".preview-dialog__close");
      let selectedId = null;
      let lastTrigger = null;
      let pageScrollPosition = 0;

      const copyText = async (text) => {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          return;
        }
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        textarea.remove();
        if (!copied) throw new Error("Unable to copy selected style");
      };

      const selectCard = (card) => {
        cards.forEach((candidate) => {
          const selected = candidate === card;
          candidate.classList.toggle("is-selected", selected);
          candidate.setAttribute("aria-pressed", selected ? "true" : "false");
        });
        selectedId = card.dataset.previewId;
        selectedPreview.textContent = selectedId;
        selectedPreview.classList.add("has-selection");
        copySelection.disabled = false;
        copySelection.textContent = "Copy ID";
        copySelection.classList.remove("is-copied");
      };

      const openPreview = (card) => {
        pageScrollPosition = window.scrollY;
        lastTrigger = card;
        previewDialogImage.src = "./" + card.dataset.previewImage;
        previewDialogImage.alt = card.dataset.previewLabel + " caption preview";
        previewDialogTitle.textContent = card.dataset.previewId;
        previewDialog.classList.toggle("is-shorts", card.classList.contains("style-card--shorts"));
        document.documentElement.classList.add("modal-open");
        document.body.classList.add("modal-open");
        previewDialog.showModal();
        previewDialogClose.focus({ preventScroll: true });
        window.scrollTo(0, pageScrollPosition);
      };

      cards.forEach((card) => {
        card.addEventListener("click", () => {
          selectCard(card);
          openPreview(card);
        });
        card.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectCard(card);
            openPreview(card);
          }
        });
      });

      copySelection.addEventListener("click", async () => {
        if (!selectedId) return;
        try {
          await copyText(selectedId);
          copySelection.textContent = "Copied";
          copySelection.classList.add("is-copied");
        } catch {
          copySelection.textContent = "Copy failed";
        }
      });

      previewDialogClose.addEventListener("click", () => previewDialog.close());
      previewDialog.addEventListener("click", (event) => {
        if (event.target === previewDialog) previewDialog.close();
      });
      previewDialog.addEventListener("close", () => {
        document.body.classList.remove("modal-open");
        if (lastTrigger) lastTrigger.focus({ preventScroll: true });
        window.scrollTo(0, pageScrollPosition);
        document.documentElement.classList.remove("modal-open");
      });
    })();
  </script>
</body>
</html>
`;

writeFileSync(outputPath, html.replaceAll(/[ \t]+$/gm, ""), "utf8");
console.log(`[caption-gallery] generated ${allItems.length} previews`);
console.log(`[caption-gallery] ${outputPath}`);
