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
if (manifest.total !== 25 || allItems.length !== 25 || new Set(allItems.map((item) => item.id)).size !== 25) {
  throw new Error(`Expected 25 unique preview items, found manifest.total=${manifest.total}, items=${allItems.length}`);
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
      <article class="style-card ${isShorts ? "style-card--shorts" : "style-card--landscape"}"
        data-preview-id="${escapeHtml(item.id)}" data-preview-image="${escapeHtml(item.image)}"
        data-preview-props="${escapeHtml(item.props)}" data-preview-label="${escapeHtml(item.label)}">
        <label class="style-choice">
          <input type="radio" name="caption-style" value="${escapeHtml(item.id)}">
          <span class="selection-mark" aria-hidden="true">Selected</span>
          <span class="preview-frame ${isShorts ? "preview-frame--shorts" : "preview-frame--landscape"}">
            <img src="./${escapeHtml(item.image)}" alt="${escapeHtml(item.label)} caption preview" loading="lazy" draggable="false">
          </span>
          <span class="card-copy">
            <span class="card-heading"><strong>${escapeHtml(item.id)}</strong><span>${escapeHtml(item.aspectRatio)}</span></span>
            <span class="metadata-grid">
              <span><small>Preset</small>${escapeHtml(item.preset)}</span>
              <span><small>Theme</small>${escapeHtml(titleCase(theme))}</span>
              <span><small>Karaoke</small>${item.karaoke ? "On" : "Off"}</span>
            </span>
          </span>
        </label>
        <button class="enlarge-preview" type="button" aria-haspopup="dialog" aria-controls="preview-dialog">Enlarge preview</button>
      </article>`;
};

const renderSection = (id, title, copy, items, gridClass = "") => `
    <section class="gallery-section" aria-labelledby="${id}-title">
      <div class="section-heading">
        <h2 id="${id}-title">${title}</h2>
        <p>${copy}</p>
      </div>
      <div class="card-grid ${gridClass}">${items.map(renderCard).join("")}</div>
    </section>`;

const manifestJson = JSON.stringify(manifest).replaceAll("<", "\\u003c");
const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <base href="./">
  <title>Caption style review</title>
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
      min-width: 320px;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 system-ui, sans-serif;
      letter-spacing: 0;
    }
    button, input { font: inherit; }
    header { border-bottom: 1px solid var(--line); background: var(--band); }
    .header-inner, main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; }
    .header-inner { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; padding: 20px 0; }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    .header-copy { margin: 0; color: var(--muted); }
    main { padding: 0 0 40px; }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 58px;
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
      background: var(--bg);
    }
    #review-status { color: var(--muted); }
    .toolbar-actions { display: flex; gap: 8px; }
    button {
      min-height: 38px;
      padding: 8px 12px;
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: transparent;
      color: var(--text);
      cursor: pointer;
    }
    button:hover, button:focus-visible { background: #253b38; outline: none; }
    button:disabled { border-color: var(--line); color: #737a7e; cursor: not-allowed; }
    #copy-summary.copied { border-color: var(--accent); background: #253b38; }
    #review-form { display: grid; gap: 28px; padding-top: 20px; }
    .section-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; margin-bottom: 10px; }
    .section-heading h2 { margin: 0; font-size: 17px; letter-spacing: 0; }
    .section-heading p { margin: 0; color: var(--muted); text-align: right; }
    .card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .card-grid--core { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .card-grid--shorts { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .style-card {
      position: relative;
      display: flex;
      min-width: 0;
      flex-direction: column;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
    }
    .style-card:has(input:checked) { border-color: var(--accent); box-shadow: 0 0 0 2px #265950; }
    .style-card:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
    .style-choice { display: flex; min-width: 0; flex: 1; flex-direction: column; padding: 10px; cursor: pointer; }
    .style-choice > input { position: absolute; width: 1px; height: 1px; opacity: 0; }
    .style-choice > input:focus-visible + .selection-mark { outline: 2px solid var(--accent); outline-offset: 3px; }
    .selection-mark {
      position: absolute;
      z-index: 1;
      top: 16px;
      right: 16px;
      display: none;
      padding: 3px 6px;
      border-radius: 4px;
      background: var(--accent);
      color: #10211f;
      font-size: 11px;
      font-weight: 700;
    }
    .style-card:has(input:checked) .selection-mark { display: block; }
    .preview-frame { display: grid; place-items: center; overflow: hidden; border: 1px solid #50575c; border-radius: 4px; background: #090a0b; }
    .preview-frame--landscape { aspect-ratio: 16 / 9; }
    .preview-frame--shorts { width: min(100%, 146px); aspect-ratio: 9 / 16; margin: 0 auto; }
    .preview-frame img { display: block; width: 100%; height: 100%; object-fit: contain; }
    .card-copy { display: grid; gap: 9px; padding-top: 10px; }
    .card-heading { display: flex; justify-content: space-between; gap: 8px; color: var(--text); }
    .card-heading strong { min-width: 0; overflow-wrap: anywhere; }
    .card-heading > span { color: var(--muted); font-size: 12px; }
    .metadata-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; color: var(--text); font-size: 12px; }
    .metadata-grid > span { min-width: 0; overflow-wrap: anywhere; }
    .metadata-grid small { display: block; color: var(--muted); font-size: 10px; }
    .enlarge-preview { min-height: 38px; margin: 0 10px 10px; border-color: #50575c; }
    .summary-box { margin-top: 20px; padding: 14px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); }
    .summary-box-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
    .summary-box-header h2 { margin: 0; font-size: 16px; }
    #summary-output {
      width: 100%;
      min-height: 92px;
      margin: 0;
      padding: 10px;
      border: 1px solid #50575c;
      border-radius: 4px;
      background: #171a1c;
      color: var(--text);
      font: 13px/1.5 ui-monospace, "Cascadia Code", Consolas, monospace;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    #review-errors { min-height: 20px; margin: 8px 0 0; color: var(--warning); }
    .preview-dialog {
      width: min(980px, calc(100vw - 48px));
      max-width: none;
      max-height: calc(100vh - 40px);
      padding: 44px 12px 12px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      color: var(--text);
    }
    .preview-dialog.is-shorts { width: min(390px, calc(100vw - 24px)); }
    .preview-dialog::backdrop { background: rgba(0, 0, 0, 0.78); }
    .preview-dialog__close { position: absolute; top: 6px; right: 8px; min-width: 38px; padding: 0; }
    .preview-dialog figure { margin: 0; }
    .preview-dialog__media { display: grid; max-height: calc(100vh - 120px); place-items: center; overflow: hidden; background: #090a0b; }
    .preview-dialog__image { display: block; max-width: 100%; max-height: calc(100vh - 150px); object-fit: contain; }
    .preview-dialog__caption { padding-top: 10px; text-align: center; overflow-wrap: anywhere; }
    body.modal-open { overflow: hidden; }
    @media (max-width: 1100px) {
      .card-grid, .card-grid--core { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .card-grid--shorts { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }
    @media (max-width: 780px) {
      .header-inner, .toolbar, .section-heading, .summary-box-header { align-items: stretch; flex-direction: column; gap: 10px; }
      .toolbar { position: static; }
      .toolbar-actions { display: grid; grid-template-columns: 1fr 1fr; }
      .toolbar-actions button { width: 100%; }
      .section-heading p { text-align: left; }
      .card-grid, .card-grid--core { grid-template-columns: 1fr; }
      .card-grid--shorts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metadata-grid { grid-template-columns: 1fr; }
      .preview-dialog { width: calc(100vw - 20px); max-height: calc(100vh - 20px); }
    }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <h1>Caption style review</h1>
      <p class="header-copy">25 maintained local previews</p>
    </div>
  </header>
  <main>
    <div class="toolbar">
      <strong id="review-status" aria-live="polite">No style selected</strong>
      <div class="toolbar-actions">
        <button id="select-default" type="button">Use clean default</button>
        <button id="copy-summary" type="button" disabled>Copy ID</button>
      </div>
    </div>
    <form id="review-form">
      ${renderSection("core", "Core presets", "Primary treatments, including one karaoke combination.", groupMap.core, "card-grid--core")}
      ${renderSection("pill", "Pill", "Background themes with a compact rounded silhouette.", groupMap.pill)}
      ${renderSection("boxed", "Boxed", "Background themes with a rectangular caption block.", groupMap.boxed)}
      ${renderSection("stroked", "Stroked", "Background-free treatments with themed outlines.", groupMap.stroked)}
      ${renderSection("shorts", "Shorts", "Vertical treatments for 9:16 delivery.", groupMap.shorts, "card-grid--shorts")}
    </form>
    <section class="summary-box" aria-labelledby="summary-title">
      <div class="summary-box-header"><h2 id="summary-title">Return the selected style</h2></div>
      <pre id="summary-output">No style selected yet.</pre>
      <p id="review-errors" role="alert" aria-live="assertive"></p>
    </section>
  </main>

  <dialog class="preview-dialog" id="preview-dialog" aria-labelledby="preview-dialog-title">
    <button class="preview-dialog__close" type="button" aria-label="Close enlarged preview">Close</button>
    <figure>
      <div class="preview-dialog__media"><img class="preview-dialog__image" alt=""></div>
      <figcaption class="preview-dialog__caption" id="preview-dialog-title">Caption preview</figcaption>
    </figure>
  </dialog>

  <script id="embedded-preview-manifest" type="application/json">${manifestJson}</script>
  <script>
    (() => {
      const REVIEW_DATA_B64 = "__CAPTION_STYLE_REVIEW_DATA__";
      const genericReviewData = {
        schema_version: 1,
        review_id: null,
        source_name: null,
        decision_mode: "human",
        default_choice: "clean"
      };
      const reviewData = REVIEW_DATA_B64.startsWith("__CAPTION_STYLE_")
        ? genericReviewData
        : JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(REVIEW_DATA_B64), (character) => character.charCodeAt(0))));
      const form = document.getElementById("review-form");
      const cards = [...form.querySelectorAll(".style-card")];
      const status = document.getElementById("review-status");
      const defaultButton = document.getElementById("select-default");
      const copyButton = document.getElementById("copy-summary");
      const summaryOutput = document.getElementById("summary-output");
      const errors = document.getElementById("review-errors");
      const previewDialog = document.getElementById("preview-dialog");
      const previewDialogImage = previewDialog.querySelector(".preview-dialog__image");
      const previewDialogTitle = document.getElementById("preview-dialog-title");
      const previewDialogClose = previewDialog.querySelector(".preview-dialog__close");
      let lastTrigger = null;

      copyButton.textContent = reviewData.review_id ? "Copy summary" : "Copy ID";

      function buildSummary() {
        const selected = form.querySelector('input[name="caption-style"]:checked');
        if (!selected) return "No style selected yet.";
        if (!reviewData.review_id) return selected.value;
        return \`Caption style review\\nReview: \${reviewData.review_id}\\nDecision: select\\nChoice: \${selected.value}\`;
      }

      function updateSelection() {
        const selected = form.querySelector('input[name="caption-style"]:checked');
        cards.forEach((card) => card.classList.toggle("is-selected", card.querySelector("input").checked));
        status.textContent = selected ? "Selected: " + selected.value : "No style selected";
        summaryOutput.textContent = buildSummary();
        copyButton.disabled = !selected;
        copyButton.textContent = reviewData.review_id ? "Copy summary" : "Copy ID";
        copyButton.classList.remove("copied");
        errors.textContent = "";
      }

      for (const input of form.querySelectorAll('input[name="caption-style"]')) {
        input.addEventListener("change", updateSelection);
      }
      defaultButton.addEventListener("click", () => {
        const input = [...form.elements].find((element) => element.value === reviewData.default_choice);
        if (!input) return;
        input.checked = true;
        updateSelection();
        input.focus();
      });

      function fallbackCopy(text) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.append(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        textarea.remove();
        return copied;
      }
      async function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          try {
            await navigator.clipboard.writeText(text);
            return true;
          } catch {
            return fallbackCopy(text);
          }
        }
        return fallbackCopy(text);
      }
      copyButton.addEventListener("click", async () => {
        if (copyButton.disabled) return;
        if (!(await copyText(summaryOutput.textContent))) {
          errors.textContent = "Copy failed. Select the summary text manually.";
          return;
        }
        copyButton.textContent = "Copied";
        copyButton.classList.add("copied");
      });

      for (const button of form.querySelectorAll(".enlarge-preview")) {
        button.addEventListener("click", () => {
          const card = button.closest(".style-card");
          lastTrigger = button;
          previewDialogImage.src = "./" + card.dataset.previewImage;
          previewDialogImage.alt = card.dataset.previewLabel + " caption preview";
          previewDialogTitle.textContent = card.dataset.previewId;
          previewDialog.classList.toggle("is-shorts", card.classList.contains("style-card--shorts"));
          document.body.classList.add("modal-open");
          previewDialog.showModal();
          previewDialogClose.focus({ preventScroll: true });
        });
      }
      previewDialogClose.addEventListener("click", () => previewDialog.close());
      previewDialog.addEventListener("click", (event) => {
        if (event.target === previewDialog) previewDialog.close();
      });
      previewDialog.addEventListener("close", () => {
        document.body.classList.remove("modal-open");
        if (lastTrigger) lastTrigger.focus({ preventScroll: true });
      });
      updateSelection();
    })();
  </script>
</body>
</html>
`;

writeFileSync(outputPath, html.replaceAll(/[ \t]+$/gm, ""), "utf8");
console.log(`[caption-gallery] generated ${allItems.length} previews`);
console.log(`[caption-gallery] ${outputPath}`);
