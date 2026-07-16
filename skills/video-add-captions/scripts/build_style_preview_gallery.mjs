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

if (manifest.total !== 25) {
  throw new Error(`Expected manifest.total to be 25, received ${manifest.total}.`);
}
if (JSON.stringify(actualGroups) !== JSON.stringify(expectedGroups)) {
  throw new Error(`Unexpected manifest group order: ${actualGroups.join(", ")}.`);
}

const groupMap = Object.fromEntries(manifest.groups.map((group) => [group.id, group.items]));
const allItems = manifest.groups.flatMap((group) => group.items);
const uniqueIds = new Set(allItems.map((item) => item.id));
if (uniqueIds.size !== manifest.total) {
  throw new Error("Preview IDs must be unique.");
}

for (const item of allItems) {
  for (const relativePath of [item.image, item.props]) {
    if (!relativePath || relativePath !== relativePath.split(/[\\/]/).pop()) {
      throw new Error(`Manifest path must be a local filename: ${relativePath}.`);
    }
    if (relativePath.includes("video-add-captions-legacy")) {
      throw new Error(`Legacy path is not allowed: ${relativePath}.`);
    }
    if (!existsSync(join(assetsDirectory, relativePath))) {
      throw new Error(`Missing gallery asset: ${relativePath}.`);
    }
  }
}

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const titleCase = (value) => String(value)
  .split("-")
  .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
  .join(" ");

const renderCard = (item) => {
  const isShorts = item.orientation === "shorts";
  const isSelected = item.id === "clean";
  const themeLabel = item.theme ? titleCase(item.theme) : "Default";
  return `
    <article
      class="style-card ${isShorts ? "style-card--shorts" : "style-card--landscape"}${isSelected ? " is-selected" : ""}"
      data-preview-id="${escapeHtml(item.id)}"
      data-preview-image="${escapeHtml(item.image)}"
      data-preset="${escapeHtml(item.preset)}"
      data-theme="${escapeHtml(item.theme ?? "default")}"
      data-karaoke="${item.karaoke ? "on" : "off"}"
      role="button"
      tabindex="0"
      aria-pressed="${isSelected ? "true" : "false"}"
      aria-haspopup="dialog"
      aria-controls="preview-dialog"
      aria-label="Select and enlarge ${escapeHtml(item.label)} caption style"
    >
      <span class="selection-mark" aria-hidden="true">✓</span>
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
          <div><dt>Theme</dt><dd>${escapeHtml(themeLabel)}</dd></div>
          <div><dt>Karaoke</dt><dd class="${item.karaoke ? "status-on" : "status-off"}">${item.karaoke ? "On" : "Off"}</dd></div>
        </dl>
      </div>
    </article>`;
};

const renderGrid = (items, className = "") => `<div class="card-grid ${className}">${items.map(renderCard).join("")}\n</div>`;
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
    .selection-summary p { margin: 0; }
    .selection-summary strong { color: #1d4ed8; }
    .selection-hint { color: #5270aa; font-size: 0.88rem; }
    .selection-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .copy-selection {
      flex: 0 0 auto;
      min-width: 82px;
      padding: 8px 14px;
      border: 1px solid #93c5fd;
      border-radius: 10px;
      background: #ffffff;
      color: #1d4ed8;
      font-weight: 800;
      cursor: pointer;
      transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
    }
    .copy-selection:hover { background: #eff6ff; border-color: #60a5fa; }
    .copy-selection:focus-visible { outline: 3px solid rgba(37, 99, 235, 0.22); outline-offset: 2px; }
    .copy-selection.is-copied { border-color: #86efac; background: #f0fdf4; color: #15803d; }
    .copy-selection.is-error { border-color: #fca5a5; background: #fef2f2; color: #b91c1c; }

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
    .section-heading h2 {
      margin: 0;
      font-size: clamp(1.55rem, 3vw, 2.25rem);
      line-height: 1.15;
      letter-spacing: -0.025em;
    }
    .section-heading p {
      max-width: 620px;
      margin: 0;
      color: var(--muted);
      text-align: right;
    }

    .subgroup + .subgroup { margin-top: 38px; }
    .subgroup-heading {
      display: flex;
      align-items: center;
      gap: 11px;
      margin: 0 0 16px;
    }
    .subgroup-heading h3 { margin: 0; font-size: 1.18rem; }
    .count-badge {
      padding: 3px 9px;
      border-radius: 999px;
      background: #e8edf4;
      color: #596579;
      font-size: 0.76rem;
      font-weight: 800;
    }

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
    .selection-mark {
      position: absolute;
      z-index: 2;
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
      transform: scale(0.7);
      transition: opacity 160ms ease, transform 160ms ease;
    }
    .style-card.is-selected .selection-mark { opacity: 1; transform: scale(1); }

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
    .preview-frame img { width: 100%; height: 100%; display: block; object-fit: contain; }

    .card-copy { display: grid; gap: 12px; padding: 13px 4px 3px; }
    .card-heading { display: flex; align-items: start; justify-content: space-between; gap: 10px; }
    .card-heading h4 {
      min-width: 0;
      margin: 0;
      font-size: 1rem;
      line-height: 1.28;
      overflow-wrap: anywhere;
    }
    .aspect-badge {
      flex: 0 0 auto;
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef2f7;
      color: #526074;
      font-size: 0.72rem;
      font-weight: 800;
    }
    .metadata-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 9px 12px;
      margin: 0;
    }
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
    .metadata-grid dd.status-on { color: #15803d; }
    .metadata-grid dd.status-off { color: #667085; }

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
    .option-list {
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .option-list li {
      padding: 10px 13px;
      border-radius: 12px;
      background: var(--surface-soft);
      color: #475467;
      font-size: 0.9rem;
    }
    .option-list strong { color: var(--ink); }

    html.modal-open { scroll-behavior: auto; }
    body.modal-open { overflow: hidden; }
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

    @media (max-width: 820px) {
      .page-shell { width: min(100% - 24px, 1480px); padding-top: 12px; }
      .hero { border-radius: 22px; }
      .selection-summary, .section-heading { align-items: start; flex-direction: column; }
      .section-heading p { text-align: left; }
      .selection-actions { width: 100%; justify-content: space-between; }
      .option-panel { grid-template-columns: 1fr; }
      .style-card--landscape { flex-basis: 270px; }
      .card-grid--core { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .card-grid--shorts { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }

    @media (max-width: 540px) {
      .hero { padding: 26px 22px; }
      .gallery-section { margin-top: 44px; }
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
      .preview-dialog__media,
      .preview-dialog__image { max-height: calc(100vh - 100px); }
      .metadata-grid { grid-template-columns: 1fr; }
      .metadata-grid div:last-child { grid-column: auto; }
      .selection-hint { display: none; }
      .selection-actions { justify-content: flex-end; }
    }
  </style>
</head>
<body>
  <main class="page-shell">
    <header class="hero">
      <p class="eyebrow">25 offline preview styles</p>
      <h1>Caption Style Gallery</h1>
      <p class="hero-copy">Choose a visual direction by preview ID, then request that preset, theme, and Karaoke option when adding captions.</p>
      <div class="default-note">Default behavior: clean is used when no style is selected.</div>
    </header>

    <div class="selection-summary" aria-live="polite">
      <p>Selected preview: <strong id="selected-preview">clean</strong></p>
      <div class="selection-actions">
        <span class="selection-hint">Click a card or use Enter / Space to select and enlarge its preview.</span>
        <button class="copy-selection" id="copy-selection" type="button" aria-label="Copy selected caption style">Copy</button>
      </div>
    </div>

    <section class="gallery-section" aria-labelledby="core-title">
      <div class="section-heading">
        <h2 id="core-title">Core Presets</h2>
        <p>The primary starting points, including one explicit Karaoke combination.</p>
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
        ${renderGrid(groupMap.pill)}
      </div>
      <div class="subgroup">
        <div class="subgroup-heading"><h3>Boxed</h3><span class="count-badge">5 themes</span></div>
        ${renderGrid(groupMap.boxed)}
      </div>
    </section>

    <section class="gallery-section" aria-labelledby="stroke-title">
      <div class="section-heading">
        <h2 id="stroke-title">Stroke Styles</h2>
        <p>Background-free captions with five stroke colors.</p>
      </div>
      ${renderGrid(groupMap.stroked)}
    </section>

    <section class="gallery-section" id="shorts-styles" aria-labelledby="shorts-title">
      <div class="section-heading">
        <h2 id="shorts-title">Shorts Styles</h2>
        <p>Compact 9:16 cards preserve the vertical preview ratio without letting each image dominate the page.</p>
      </div>
      ${renderGrid(groupMap.shorts, "card-grid--shorts")}
    </section>

    <section class="gallery-section option-panel" aria-labelledby="karaoke-title">
      <div>
        <h2 id="karaoke-title">Karaoke Option</h2>
        <p>Karaoke controls word-level highlighting independently from the official preset. It can be enabled or disabled for other presets on request.</p>
      </div>
      <ul class="option-list">
        <li><strong>Karaoke is an option</strong>, not an official preset.</li>
        <li><strong>social-bold-karaoke</strong> is a combination ID.</li>
        <li>Ask for any preset with Karaoke <strong>on</strong> or <strong>off</strong>.</li>
      </ul>
    </section>

  </main>

  <dialog class="preview-dialog" id="preview-dialog" aria-labelledby="preview-dialog-title">
    <button class="preview-dialog__close" type="button" aria-label="Close enlarged preview">&#10005;</button>
    <figure class="preview-dialog__figure">
      <div class="preview-dialog__media">
        <img class="preview-dialog__image" alt="">
      </div>
      <figcaption class="preview-dialog__caption" id="preview-dialog-title">Caption preview</figcaption>
    </figure>
  </dialog>

  <script id="embedded-preview-manifest" type="application/json">${manifestJson}</script>
  <script>
    (() => {
      const cards = Array.from(document.querySelectorAll(".style-card"));
      const selectedPreview = document.getElementById("selected-preview");
      const copySelection = document.getElementById("copy-selection");
      const previewDialog = document.getElementById("preview-dialog");
      const previewDialogTitle = document.getElementById("preview-dialog-title");
      const previewDialogImage = previewDialog.querySelector(".preview-dialog__image");
      const previewDialogClose = previewDialog.querySelector(".preview-dialog__close");
      let lastTrigger = null;
      let pageScrollPosition = 0;
      let copyResetTimer = null;

      const resetCopySelection = () => {
        if (copyResetTimer) {
          window.clearTimeout(copyResetTimer);
          copyResetTimer = null;
        }
        copySelection.textContent = "Copy";
        copySelection.classList.remove("is-copied", "is-error");
      };

      const copyTextWithFallback = async (text) => {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          return;
        }

        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.setAttribute("readonly", "");
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        const copied = document.execCommand("copy");
        textArea.remove();
        if (!copied) {
          throw new Error("Unable to copy selected style");
        }
      };

      const selectCard = (card) => {
        for (const candidate of cards) {
          const selected = candidate === card;
          candidate.classList.toggle("is-selected", selected);
          candidate.setAttribute("aria-pressed", selected ? "true" : "false");
        }
        selectedPreview.textContent = card.dataset.previewId;
        resetCopySelection();
      };

      const openPreview = (card) => {
        pageScrollPosition = window.scrollY;
        selectCard(card);
        lastTrigger = card;
        previewDialogTitle.textContent = card.dataset.previewId;
        previewDialogImage.src = "./" + card.dataset.previewImage;
        previewDialogImage.alt = card.dataset.previewId + " caption preview";
        previewDialog.classList.toggle("is-shorts", card.classList.contains("style-card--shorts"));
        document.documentElement.classList.add("modal-open");
        document.body.classList.add("modal-open");
        previewDialog.showModal();
        previewDialogClose.focus({ preventScroll: true });
        window.scrollTo(0, pageScrollPosition);
      };

      const closePreview = () => {
        if (previewDialog.open) {
          previewDialog.close();
        }
      };

      for (const card of cards) {
        card.addEventListener("click", () => openPreview(card));
        card.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPreview(card);
          }
        });
      }

      copySelection.addEventListener("click", async () => {
        resetCopySelection();
        const copyText = "Use caption style: " + selectedPreview.textContent.trim();
        try {
          await copyTextWithFallback(copyText);
          copySelection.textContent = "Copied";
          copySelection.classList.add("is-copied");
        } catch {
          copySelection.textContent = "Copy failed";
          copySelection.classList.add("is-error");
        }
        copyResetTimer = window.setTimeout(resetCopySelection, 1800);
      });

      previewDialogClose.addEventListener("click", closePreview);
      previewDialog.addEventListener("click", (event) => {
        if (event.target === previewDialog) {
          closePreview();
        }
      });
      previewDialog.addEventListener("close", () => {
        document.body.classList.remove("modal-open");
        if (lastTrigger) {
          lastTrigger.focus({ preventScroll: true });
        }
        window.scrollTo(0, pageScrollPosition);
        document.documentElement.classList.remove("modal-open");
      });
    })();
  </script>
</body>
</html>
`;

writeFileSync(outputPath, html, "utf8");
console.log(`[caption-gallery] wrote ${outputPath}`);
console.log(`[caption-gallery] ${allItems.length} cards embedded from preview-manifest.json`);
