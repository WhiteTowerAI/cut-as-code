#!/usr/bin/env node

import crypto from "node:crypto";
import {
  cp,
  mkdir,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  discoverRecipes,
  manifestList as list,
  manifestScalar as scalar,
} from "./recipe_library.mjs";

export { discoverRecipes } from "./recipe_library.mjs";

const DEFAULT_DURATION_SECONDS = 6;
const FRAME_STEP_SECONDS = 1 / 60;
const TRANSPARENT_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

function durationSeconds(manifest, recipeDir) {
  const durationMatch = manifest.match(/^\s*duration_ms:\s*(\d+(?:\.\d+)?)/m);
  const durationMs = durationMatch ? Number(durationMatch[1]) : 0;
  return Math.max(DEFAULT_DURATION_SECONDS, durationMs / 1000);
}

function escapeAttribute(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(target)));
    } else if (entry.isFile()) {
      files.push(target);
    }
  }
  return files;
}

export async function writeLibraryAttribution({
  recipesRoot,
  sourceRevision,
  upstreamAttribution,
}) {
  const target = path.join(recipesRoot, "ATTRIBUTION.md");
  const contents = `# motion-anything recipes attribution

The recipes in this directory were vendored from
[nexu-io/motion-anything](https://github.com/nexu-io/motion-anything) at revision
\`${sourceRevision}\`. Converted HyperFrames files retain credit comments found in their
original recipe implementation files.

## Upstream attribution

${upstreamAttribution.trim()}\n`;
  await writeFile(target, contents, "utf8");
  return target;
}

async function fileExists(target) {
  try {
    return (await stat(target)).isFile();
  } catch {
    return false;
  }
}

function activeLocalReferences(html) {
  const references = [];
  const pattern = /\b(?:src|href)\s*=\s*['"]([^'"]+)['"]/gi;
  for (const match of html.matchAll(pattern)) {
    const value = match[1];
    if (/^(?:[a-z]+:|\/\/|#|data:)/i.test(value)) continue;
    references.push(value.split(/[?#]/, 1)[0]);
  }
  return references;
}

function creditCommentLines(source) {
  return source
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /(?:credit|copyright|author|adapted|ported|permission|react-bits|direct port|original)/i.test(line))
    .filter((line) => /^(?:\/\/|\/\*|\*|#|<!--)/.test(line));
}

export async function auditConvertedRecipes(recipesRoot) {
  const recipes = await discoverRecipes(recipesRoot);
  const errors = [];
  let convertedCount = 0;
  let preservedCreditComments = 0;
  const forbiddenRuntime = /(?<!__hf\.)\b(?:requestAnimationFrame|setTimeout|setInterval)\s*\(|\b(?:performance\.now|Date\.now|Math\.random)\s*\(/;

  for (const recipe of recipes) {
    const outputDir = path.join(recipe.recipeDir, "hyperframes");
    const receiptPath = path.join(outputDir, "conversion.json");
    if (!(await fileExists(receiptPath))) {
      errors.push(`${recipe.id}: missing converted index or receipt`);
      continue;
    }

    let receipt;
    try {
      receipt = JSON.parse(await readFile(receiptPath, "utf8"));
    } catch (error) {
      errors.push(`${recipe.id}: conversion receipt is invalid JSON (${error.message})`);
      continue;
    }

    const receiptVariant = Array.isArray(receipt.variants)
      ? receipt.variants.find((variant) => variant.composition_id === recipe.id) || receipt.variants[0]
      : null;
    const indexPath = receiptVariant?.output
      ? path.join(outputDir, ...receiptVariant.output.split("/"))
      : path.join(outputDir, "index.html");
    const artifactDir = path.dirname(indexPath);
    if (!(await fileExists(indexPath))) {
      errors.push(`${recipe.id}: missing converted index or receipt`);
      continue;
    }
    convertedCount += 1;
    const html = await readFile(indexPath, "utf8");
    if (!html.includes(`data-composition-id="${recipe.id}"`)) {
      errors.push(`${recipe.id}: composition id does not match recipe id`);
    }
    if (!/data-width="1920"/.test(html) || !/data-height="1080"/.test(html) || !/data-duration="[0-9.]+"/.test(html)) {
      errors.push(`${recipe.id}: composition root is missing fixed geometry or duration`);
    }
    if (/\b(?:src|href)\s*=\s*['"](?:https?:)?\/\//i.test(html)) {
      errors.push(`${recipe.id}: converted entry contains a remote active reference`);
    }
    for (const reference of activeLocalReferences(html)) {
      if (!(await fileExists(path.resolve(artifactDir, reference)))) {
        errors.push(`${recipe.id}: missing local reference ${reference}`);
      }
    }

    if (receiptVariant) {
      const copiedManifestPath = path.join(
        outputDir,
        receipt.source_copy || "source",
        "recipe.motion.yaml",
      );
      const copiedManifest = (await fileExists(copiedManifestPath))
        ? await readFile(copiedManifestPath, "utf8")
        : "";
      if (receiptVariant.composition_id !== recipe.id || sha256(copiedManifest) !== sha256(recipe.manifest)) {
        errors.push(`${recipe.id}: conversion receipt does not bind the current manifest`);
      }
    } else if (receipt.recipe_id !== recipe.id || receipt.source_manifest_sha256 !== sha256(recipe.manifest)) {
      errors.push(`${recipe.id}: conversion receipt does not bind the current manifest`);
    }

    for (const name of ["hf-recipe.js", "hf-adapter.js"]) {
      const scriptPath = path.join(artifactDir, name);
      if (!(await fileExists(scriptPath))) continue;
      const script = await readFile(scriptPath, "utf8");
      if (!(name === "hf-recipe.js" && recipe.runtime.includes("three"))) {
        try {
          new Function(script);
        } catch (error) {
          errors.push(`${recipe.id}: ${name} is not valid script syntax (${error.message})`);
        }
      }
      if (name === "hf-recipe.js" && forbiddenRuntime.test(script)) {
        errors.push(`${recipe.id}: converted recipe contains an unwrapped time or random API`);
      }
    }

    const generatedRecipePath = path.join(artifactDir, "hf-recipe.js");
    const generatedRecipe = (await fileExists(generatedRecipePath))
      ? await readFile(generatedRecipePath, "utf8")
      : "";
    const originalPreview = await readFile(path.join(recipe.recipeDir, recipe.entry), "utf8");
    const loadedScriptPaths = new Set(
      scriptBlocks(originalPreview).blocks
        .filter((block) => block.source && !/^(?:[a-z]+:|\/\/)/i.test(block.source))
        .map((block) => path.resolve(recipe.recipeDir, block.source)),
    );
    const sourceFiles = (await walk(recipe.recipeDir)).filter(
      (file) => file.endsWith(".js") && !file.split(path.sep).includes("hyperframes"),
    );
    for (const sourcePath of sourceFiles) {
      const source = await readFile(sourcePath, "utf8");
      for (const line of creditCommentLines(source)) {
        const copiedPath = path.join(outputDir, "source", path.relative(recipe.recipeDir, sourcePath));
        const copied = await readFile(copiedPath, "utf8");
        if (!copied.includes(line)) {
          errors.push(`${recipe.id}: source credit comment was not preserved from ${path.basename(sourcePath)}`);
        } else {
          preservedCreditComments += 1;
        }
        if (generatedRecipe && loadedScriptPaths.has(sourcePath) && !generatedRecipe.includes(line)) {
          errors.push(`${recipe.id}: executable conversion dropped a credit comment from ${path.basename(sourcePath)}`);
        }
      }
    }
  }

  return {
    recipe_count: recipes.length,
    converted_count: convertedCount,
    preserved_credit_comments: preservedCreditComments,
    errors,
  };
}

function scriptBlocks(html) {
  const blocks = [];
  const withoutScripts = html.replace(
    /<script\b([^>]*)>([\s\S]*?)<\/script>/gi,
    (_full, attributes, inlineCode) => {
      const source = attributes.match(/\bsrc\s*=\s*["']([^"']+)["']/i)?.[1] || null;
      blocks.push({ source, inlineCode, attributes });
      return "";
    },
  );
  return { withoutScripts, blocks };
}

function documentParts(html) {
  const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] || "";
  const body = html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i)?.[1] || html;
  return { head, body };
}

function stripDemoChrome(body) {
  return body
    .replace(/<([a-z][\w:-]*)\b[^>]*>[^<]*\bmotion-anything\b[^<]*<\/\1>/gi, "")
    .replace(/<([a-z][\w:-]*)\b(?=[^>]*\bclass\s*=\s*(["'])[^"']*\bhint\b[^"']*\2)[^>]*>[\s\S]*?<\/\1>/gi, "")
    .replace(/<([a-z][\w:-]*)\b(?=[^>]*\bclass\s*=\s*(["'])[^"']*\breplay\b[^"']*\2)[^>]*>[\s\S]*?<\/\1>/gi, "");
}

export function transformRuntimeCode(source) {
  return source
    .replace(/\bnormalizeScroll\s*:\s*true\b/g, "normalizeScroll: false")
    .replace(/\brequestAnimationFrame\s*\(/g, "__hf.requestAnimationFrame(")
    .replace(/\bcancelAnimationFrame\s*\(/g, "__hf.cancelAnimationFrame(")
    .replace(/\bsetTimeout\s*\(/g, "__hf.setTimeout(")
    .replace(/\bclearTimeout\s*\(/g, "__hf.clearTimeout(")
    .replace(/\bsetInterval\s*\(/g, "__hf.setInterval(")
    .replace(/\bclearInterval\s*\(/g, "__hf.clearInterval(")
    .replace(/\bperformance\.now\s*\(\s*\)/g, "__hf.now()")
    .replace(/\bDate\.now\s*\(\s*\)/g, "__hf.dateNow()")
    .replace(/\bMath\.random\s*\(\s*\)/g, "__hf.random()");
}

function rewriteLocalAssetPaths(html) {
  return html.replace(
    /\b(src|href)=(['"])(?![a-z]+:|\/\/|#|data:)([^'"]+)\2/gi,
    (_full, attribute, quote, value) => `${attribute}=${quote}source/${value}${quote}`,
  );
}

function compositionHtml({ id, duration, head, body, runtime, lottieJson }) {
  const safeId = escapeAttribute(id);
  const safeDuration = Number(duration.toFixed(6));
  const baseStyle = `
    html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; }
    body[data-composition-id] { position: relative; box-sizing: border-box; background: transparent !important; }
  `;

  if (runtime.includes("lottie")) {
    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>${safeId} - HyperFrames</title>
${rewriteLocalAssetPaths(head)}
  <style>${baseStyle}</style>
</head>
<body data-composition-id="${safeId}" data-start="0" data-width="1920" data-height="1080" data-duration="${safeDuration}" data-no-timeline>
  <div id="lottie" class="clip" data-start="0" data-duration="${safeDuration}" data-track-index="1"></div>
  <script src="_runtime/lottie.min.js"></script>
  <script>
    const nativeGetRegisteredAnimations = lottie.getRegisteredAnimations.bind(lottie);
    const animation = lottie.loadAnimation({
      container: document.getElementById("lottie"),
      renderer: "svg",
      loop: false,
      autoplay: false,
      path: "source/${lottieJson}",
    });
    let lottieReady = false;
    let pendingTime = 0;
    function seekLottie(time) {
      pendingTime = Math.max(0, Number(time) || 0);
      if (!lottieReady) return;
      const nativeDuration = Number(animation.getDuration(false)) || ${safeDuration};
      const localTime = nativeDuration > 0 ? pendingTime % nativeDuration : pendingTime;
      animation.goToAndStop(localTime * 1000, false);
    }
    animation.addEventListener("DOMLoaded", () => {
      lottieReady = true;
      seekLottie(pendingTime);
    });
    lottie.getRegisteredAnimations = () => nativeGetRegisteredAnimations().filter((item) => item !== animation);
    if (Array.isArray(window.__hfLottie)) {
      window.__hfLottie = window.__hfLottie.filter((item) => item !== animation);
    }
    window.__hf = {
      duration: ${safeDuration},
      seek(time) { seekLottie(time); },
    };
    window.addEventListener("hf-seek", (event) => seekLottie(event.detail.time));
  </script>
</body>
</html>
`;
  }

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>${safeId} - HyperFrames</title>
${rewriteLocalAssetPaths(head)}
  <style>${baseStyle}</style>
</head>
<body data-composition-id="${safeId}" data-start="0" data-width="1920" data-height="1080" data-duration="${safeDuration}" data-no-timeline>
${rewriteLocalAssetPaths(body)}
  <script src="hf-recipe.js"></script>
  <script src="hf-adapter.js"></script>
</body>
</html>
`;
}

function threeCompositionHtml({ id, duration }) {
  const safeId = escapeAttribute(id);
  const safeDuration = Number(duration.toFixed(6));
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>${safeId} - HyperFrames</title>
  <style>
    html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: transparent; }
    [data-composition-id] { position: relative; width: 1920px; height: 1080px; overflow: hidden; }
    #three-layer { display: block; width: 1920px; height: 1080px; }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "./_runtime/three/three.module.js",
        "three/addons/": "./_runtime/three/addons/"
      }
    }
  </script>
</head>
<body>
  <div data-composition-id="${safeId}" data-start="0" data-width="1920" data-height="1080" data-duration="${safeDuration}" data-no-timeline>
    <canvas id="three-layer" class="clip" data-scene-mode="showcase" data-start="0" data-duration="${safeDuration}" data-track-index="1" width="1920" height="1080"></canvas>
  </div>
  <script src="hf-adapter.js"></script>
  <script type="module" src="hf-recipe.js"></script>
</body>
</html>
`;
}

function threeRecipeSource() {
  return `/* Generated HyperFrames entry; scene implementation remains in source/scene.js. */
import { createRecipe } from "./source/scene.js";

const canvas = document.getElementById("three-layer");
createRecipe({ canvas })
  .then(({ renderAt }) => window.__hfThreeRegister(renderAt))
  .catch((error) => {
    window.__hfThreeError = error;
    console.error(error);
  });
`;
}

function threeAdapterSource({ id, duration }) {
  return `/* Deterministic HyperFrames Three.js adapter for ${id}. */
(function () {
  "use strict";
  const duration = ${duration};
  let renderAt = null;
  let currentTime = Math.max(0, Math.min(duration, Number(window.__hfThreeTime) || 0));

  function seek(time) {
    currentTime = Math.max(0, Math.min(duration, Number(time) || 0));
    window.__hfThreeTime = currentTime;
    if (renderAt) renderAt(currentTime);
  }

  window.__hfThreeRegister = function (callback) {
    renderAt = callback;
    renderAt(currentTime);
  };
  window.__hf = { duration, seek };
  window.addEventListener("hf-seek", (event) => seek(event.detail.time));
  seek(currentTime);
})();
`;
}

function svgSmilAdapterSource({ id, duration }) {
  return `/* Deterministic HyperFrames SVG SMIL adapter for ${id}. */
(function () {
  "use strict";
  const duration = ${duration};
  const svg = document.querySelector("svg");

  function seek(time) {
    if (!svg) return;
    const target = Math.max(0, Math.min(duration, Number(time) || 0));
    const nativeDuration = Number(svg.dataset.nativeDuration) || duration;
    const localTime = nativeDuration > 0 ? target % nativeDuration : target;
    if (typeof svg.pauseAnimations === "function") svg.pauseAnimations();
    if (typeof svg.setCurrentTime === "function") svg.setCurrentTime(localTime);
  }

  window.__hf = { duration, seek };
  window.addEventListener("hf-seek", (event) => seek(event.detail.time));
  seek(0);
})();
`;
}

export function deterministicReplayAdapterSource({
  id,
  duration,
  body,
  runtime,
  interaction = { mode: "none", actions: [] },
  rewriteAssets = true,
  deferReplay = false,
  auditAllowances = {},
  resetRuntimeGlobals = [],
}) {
  return `/* Generated deterministic HyperFrames adapter for ${id}. */
(function () {
  "use strict";
  const FRAME_STEP = ${FRAME_STEP_SECONDS};
  const TRACK_CSS = ${runtime.includes("css")};
  const INTERACTION = ${JSON.stringify(interaction)};
  const AUDIT_ALLOWANCES = ${JSON.stringify(auditAllowances)};
  const RESET_RUNTIME_GLOBALS = ${JSON.stringify(resetRuntimeGlobals)};
  const SOURCE_BODY = ${JSON.stringify(rewriteAssets ? rewriteLocalAssetPaths(body) : body)};
  const SOURCE_BODY_ATTRIBUTES = Array.from(document.body.attributes || [])
    .map((attribute) => [attribute.name, attribute.value]);
  const FONT_WARMUP = document.fonts
    ? Promise.all([...document.fonts].map((fontFace) => fontFace.load().catch(() => null)))
    : null;
  const nativeDocumentGetAnimations = typeof document.getAnimations === "function"
    ? document.getAnimations.bind(document)
    : null;
  const NativeCSSAnimation = window.CSSAnimation;
  const NativeCSSTransition = window.CSSTransition;
  let state = null;
  let seekGeneration = 0;
  let renderedTime = null;

  function isCssManagedAnimation(animation) {
    return (NativeCSSAnimation && animation instanceof NativeCSSAnimation)
      || (NativeCSSTransition && animation instanceof NativeCSSTransition);
  }

  if (TRACK_CSS && nativeDocumentGetAnimations) {
    document.getAnimations = (...args) => nativeDocumentGetAnimations(...args)
      .filter((animation) => !isCssManagedAnimation(animation));
  }

  function applyAuditAllowances() {
    for (const [attribute, selectors] of Object.entries(AUDIT_ALLOWANCES)) {
      for (const selector of selectors) {
        for (const element of document.querySelectorAll(selector)) {
          if (attribute !== "data-layout-ignore-text") {
            element.setAttribute(attribute, "");
            continue;
          }
          for (const node of [...element.childNodes]) {
            if (node.nodeType !== 3 || !node.textContent?.trim()) continue;
            const wrapper = document.createElement("span");
            wrapper.style.display = "contents";
            wrapper.setAttribute("data-layout-ignore", "");
            node.replaceWith(wrapper);
            wrapper.append(node);
          }
        }
      }
    }
  }

  function createState() {
    let seed = 0x6d2b79f5;
    let nextTaskId = 1;
    const tasks = new Map();
    const listeners = [];
    const observers = new Set();
    const webglContexts = new Set();
    const animations = new Map();
    const nativeAdd = EventTarget.prototype.addEventListener;
    const nativeRemove = EventTarget.prototype.removeEventListener;
    const nativeGetContext = HTMLCanvasElement.prototype.getContext;
    const NativeImage = window.Image;
    const NativeResizeObserver = window.ResizeObserver;
    const NativeIntersectionObserver = window.IntersectionObserver;
    const NativeWheelEvent = window.WheelEvent;
    const NativePointerEvent = window.PointerEvent;
    const NativeMouseEvent = window.MouseEvent;
    const nativeScrollTo = typeof window.scrollTo === "function" ? window.scrollTo.bind(window) : null;
    const nativeRequestAnimationFrame = window.requestAnimationFrame;
    const nativeCancelAnimationFrame = window.cancelAnimationFrame;
    const nativeSetTimeout = window.setTimeout;
    const nativeClearTimeout = window.clearTimeout;
    const nativeSetInterval = window.setInterval;
    const nativeClearInterval = window.clearInterval;
    const nativeDateNow = Date.now;
    const NativeWebSocket = window.WebSocket;
    let disposed = false;
    let runtimeGlobalsInstalled = false;
    let actionCursor = 0;
    let scrollExtent = null;
    const imageReadiness = [];

    function trackedAdd(type, listener, options) {
      if (this === document && type === "DOMContentLoaded" && document.readyState !== "loading") {
        const event = new Event("DOMContentLoaded");
        if (typeof listener === "function") listener.call(this, event);
        else if (listener && typeof listener.handleEvent === "function") listener.handleEvent(event);
        return;
      }
      listeners.push({ target: this, type, listener, options });
      return nativeAdd.call(this, type, listener, options);
    }

    function trackedGetContext(type, options) {
      const webgl = /^(?:webgl2?|experimental-webgl)$/i.test(String(type));
      const resolvedOptions = webgl
        ? { ...(options && typeof options === "object" ? options : {}), preserveDrawingBuffer: true }
        : options;
      const context = nativeGetContext.call(this, type, resolvedOptions);
      if (webgl && context) webglContexts.add(context);
      return context;
    }

    function TrackedImage(...args) {
      const image = new NativeImage(...args);
      const readiness = new Promise((resolve) => {
        const settle = (event) => {
          nativeRemove.call(image, "load", settle);
          nativeRemove.call(image, "error", settle);
          if (disposed) {
            event.stopImmediatePropagation?.();
            resolve();
            return;
          }
          const restoreAfterEvent = !runtimeGlobalsInstalled;
          installRuntimeGlobals();
          nativeSetTimeout(() => {
            if (restoreAfterEvent) restoreRuntimeGlobals();
            resolve();
          }, 0);
        };
        nativeAdd.call(image, "load", settle);
        nativeAdd.call(image, "error", settle);
      });
      imageReadiness.push({ image, readiness });
      return image;
    }
    if (NativeImage) {
      TrackedImage.prototype = NativeImage.prototype;
      Object.setPrototypeOf(TrackedImage, NativeImage);
    }

    function installRuntimeGlobals() {
      if (runtimeGlobalsInstalled) return;
      runtimeGlobalsInstalled = true;
      window.requestAnimationFrame = api.requestAnimationFrame;
      window.cancelAnimationFrame = api.cancelAnimationFrame;
      window.setTimeout = api.setTimeout;
      window.clearTimeout = api.clearTimeout;
      window.setInterval = api.setInterval;
      window.clearInterval = api.clearInterval;
      if (NativeImage) window.Image = TrackedImage;
      Date.now = api.dateNow;
      window.WebSocket = undefined;
    }

    function restoreRuntimeGlobals() {
      if (!runtimeGlobalsInstalled) return;
      runtimeGlobalsInstalled = false;
      window.requestAnimationFrame = nativeRequestAnimationFrame;
      window.cancelAnimationFrame = nativeCancelAnimationFrame;
      window.setTimeout = nativeSetTimeout;
      window.clearTimeout = nativeClearTimeout;
      window.setInterval = nativeSetInterval;
      window.clearInterval = nativeClearInterval;
      if (window.Image === TrackedImage) window.Image = NativeImage;
      Date.now = nativeDateNow;
      window.WebSocket = NativeWebSocket;
    }

    class DeterministicResizeObserver {
      constructor(callback) {
        this.callback = callback;
        this.targets = new Set();
        observers.add(this);
      }
      observe(target) {
        this.targets.add(target);
        this.callback([{ target, contentRect: target.getBoundingClientRect() }], this);
      }
      unobserve(target) { this.targets.delete(target); }
      disconnect() { this.targets.clear(); observers.delete(this); }
    }

    class DeterministicIntersectionObserver {
      constructor(callback) {
        this.callback = callback;
        this.targets = new Set();
        this.root = null;
        this.rootMargin = "0px";
        this.thresholds = [0];
        observers.add(this);
      }
      observe(target) {
        this.targets.add(target);
        const rect = target.getBoundingClientRect();
        this.callback([{
          target,
          isIntersecting: true,
          intersectionRatio: 1,
          boundingClientRect: rect,
          intersectionRect: rect,
          rootBounds: null,
          time: api.now(),
        }], this);
      }
      unobserve(target) { this.targets.delete(target); }
      disconnect() { this.targets.clear(); observers.delete(this); }
      takeRecords() { return []; }
    }

    function smoothstep(value) {
      const clamped = Math.max(0, Math.min(1, value));
      return clamped * clamped * (3 - 2 * clamped);
    }

    function dispatchWheel(deltaY) {
      if (!NativeWheelEvent) return;
      window.dispatchEvent(new NativeWheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        deltaY,
        deltaMode: 0,
      }));
    }

    function dispatchPointer(time) {
      const progress = smoothstep(time / Math.max(FRAME_STEP, INTERACTION.duration || api.duration));
      const inverse = 1 - progress;
      const points = INTERACTION.pointerPath || [
        [0.12, 0.65], [0.32, 0.18], [0.72, 0.82], [0.88, 0.36],
      ];
      const x = (
        inverse * inverse * inverse * points[0][0]
        + 3 * inverse * inverse * progress * points[1][0]
        + 3 * inverse * progress * progress * points[2][0]
        + progress * progress * progress * points[3][0]
      ) * window.innerWidth;
      const y = (
        inverse * inverse * inverse * points[0][1]
        + 3 * inverse * inverse * progress * points[1][1]
        + 3 * inverse * progress * progress * points[2][1]
        + progress * progress * progress * points[3][1]
      ) * window.innerHeight;
      const target = document.elementFromPoint(x, y) || document.body;
      const init = { bubbles: true, cancelable: true, clientX: x, clientY: y };
      if (NativePointerEvent) target.dispatchEvent(new NativePointerEvent("pointermove", init));
      if (NativeMouseEvent) target.dispatchEvent(new NativeMouseEvent("mousemove", init));
    }

    function dispatchAction(action) {
      if (action.type === "wheel") {
        dispatchWheel(Number(action.deltaY) || 480);
        return;
      }
      const targets = document.querySelectorAll(action.selector || "body");
      const target = targets[Math.max(0, Number(action.index) || 0)] || targets[0];
      if (target && typeof target.click === "function") target.click();
    }

    const api = {
      time: 0,
      duration: ${duration},
      seek(time) { return queueSeek(time); },
      random() {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let value = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
        return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
      },
      now() { return api.time * 1000; },
      dateNow() { return 1700000000000 + api.now(); },
      requestAnimationFrame(callback) {
        const id = nextTaskId++;
        tasks.set(id, { id, kind: "raf", at: api.time + FRAME_STEP, callback });
        return id;
      },
      cancelAnimationFrame(id) { tasks.delete(id); },
      setTimeout(callback, delay = 0, ...args) {
        const id = nextTaskId++;
        tasks.set(id, { id, kind: "timeout", at: api.time + Math.max(0, Number(delay)) / 1000, callback, args });
        return id;
      },
      clearTimeout(id) { tasks.delete(id); },
      setInterval(callback, delay = 0, ...args) {
        const id = nextTaskId++;
        const interval = Math.max(FRAME_STEP, Number(delay) / 1000);
        tasks.set(id, { id, kind: "interval", at: api.time + interval, interval, callback, args });
        return id;
      },
      clearInterval(id) { tasks.delete(id); },
      captureAnimations() {
        if (!TRACK_CSS || !nativeDocumentGetAnimations) return;
        void document.body.offsetWidth;
        const current = new Set(nativeDocumentGetAnimations());
        for (const animation of animations.keys()) {
          if (!current.has(animation)) animations.delete(animation);
        }
        for (const animation of current) {
          if (animations.has(animation)) continue;
          try { animation.pause(); } catch {}
          animations.set(animation, api.time);
        }
      },
      seekAnimations(target) {
        api.captureAnimations();
        for (const [animation, startedAt] of animations) {
          try { animation.currentTime = Math.max(0, target - startedAt) * 1000; } catch {}
        }
      },
      applyInteraction(target) {
        if (INTERACTION.mode === "scroll") {
          const progress = smoothstep(
            (target + (Number(INTERACTION.startAt) || 0))
              / Math.max(FRAME_STEP, INTERACTION.duration || api.duration),
          );
          scrollExtent = Math.max(
            scrollExtent ?? 0,
            0,
            document.documentElement.scrollHeight - window.innerHeight,
            document.body.scrollHeight - window.innerHeight,
          );
          const maxScroll = scrollExtent;
          const scrollY = Math.max(0, maxScroll * progress);
          if (nativeScrollTo) nativeScrollTo(0, scrollY);
          document.documentElement.scrollTop = scrollY;
          document.body.scrollTop = scrollY;
          document.body.dispatchEvent(new Event("scroll"));
          window.dispatchEvent(new Event("scroll"));
          window.ScrollSmoother?.get?.()?.scrollTop?.(scrollY);
        } else if (INTERACTION.mode === "pointer") {
          dispatchPointer(target);
        }
        const actions = INTERACTION.actions || [];
        while (actionCursor < actions.length && actions[actionCursor].at <= target + 1e-9) {
          dispatchAction(actions[actionCursor++]);
        }
      },
      dispose() {
        disposed = true;
        try { window.ScrollTrigger?.disable?.(true, true); } catch {}
        restoreRuntimeGlobals();
        if (EventTarget.prototype.addEventListener === trackedAdd) {
          EventTarget.prototype.addEventListener = nativeAdd;
        }
        if (HTMLCanvasElement.prototype.getContext === trackedGetContext) {
          HTMLCanvasElement.prototype.getContext = nativeGetContext;
        }
        if (window.ResizeObserver === DeterministicResizeObserver) {
          window.ResizeObserver = NativeResizeObserver;
        }
        if (window.IntersectionObserver === DeterministicIntersectionObserver) {
          window.IntersectionObserver = NativeIntersectionObserver;
        }
        for (const item of listeners) nativeRemove.call(item.target, item.type, item.listener, item.options);
        listeners.length = 0;
        for (const observer of [...observers]) observer.disconnect();
        for (const context of webglContexts) {
          try { context.getExtension("WEBGL_lose_context")?.loseContext(); } catch {}
        }
        webglContexts.clear();
        tasks.clear();
      },
      runTasksTo(target) {
        let guard = 0;
        while (guard++ < 100000) {
          const due = [...tasks.values()]
            .filter((task) => task.at <= target + 1e-9)
            .sort((a, b) => a.at - b.at || a.id - b.id)[0];
          if (!due) break;
          tasks.delete(due.id);
          api.time = due.at;
          due.callback(...(due.kind === "raf" ? [api.now()] : due.args || []));
          api.captureAnimations();
          if (due.kind === "interval" && !tasks.has(due.id)) {
            due.at += due.interval;
            tasks.set(due.id, due);
          }
        }
        api.time = target;
      },
      async runTo(target, isCurrent, from = -FRAME_STEP) {
        const step = (time) => {
          if (!isCurrent()) return false;
          installRuntimeGlobals();
          try {
            api.time = time;
            if (INTERACTION.mode === "scroll") api.runTasksTo(time);
            api.applyInteraction(time);
            if (INTERACTION.mode !== "scroll") api.runTasksTo(time);
            api.seekAnimations(time);
          } finally {
            restoreRuntimeGlobals();
          }
          return isCurrent();
        };
        if (target < from - 1e-9) return step(target);
        const frameCount = Math.floor(target / FRAME_STEP + 1e-9);
        let frameTime = from;
        const firstFrame = Math.max(0, Math.floor(from / FRAME_STEP + 1e-9) + 1);
        for (let frame = firstFrame; frame <= frameCount; frame += 1) {
          frameTime = frame * FRAME_STEP;
          if (!step(frameTime)) return false;
          if (INTERACTION.mode !== "scroll") await Promise.resolve();
        }
        if (target > frameTime + 1e-9) {
          if (!step(target)) return false;
          if (INTERACTION.mode !== "scroll") await Promise.resolve();
        }
        return true;
      },
      runToAsync(target, isCurrent) {
        return new Promise((resolve, reject) => {
          installRuntimeGlobals();
          try {
            api.time = 0;
            api.applyInteraction(0);
            api.runTasksTo(0);
            api.seekAnimations(0);
          } finally {
            restoreRuntimeGlobals();
          }
          async function replay() {
            if (!isCurrent()) {
              restoreRuntimeGlobals();
              resolve(false);
              return;
            }
            try {
              scrollExtent = Math.max(
                0,
                document.documentElement.scrollHeight,
                document.body.scrollHeight,
              ) - window.innerHeight;
              resolve(await api.runTo(target, isCurrent));
            } catch (error) {
              reject(error);
            } finally {
              restoreRuntimeGlobals();
            }
          }
          queueMicrotask(() => queueMicrotask(() => {
            const pendingImages = imageReadiness
              .filter(({ image }) => image.currentSrc || image.getAttribute?.("src"))
              .map(({ readiness }) => readiness);
            void document.body.offsetWidth;
            const pendingFonts = document.fonts
              ? [...document.fonts].map((fontFace) => fontFace.load().catch(() => null))
              : [];
            if (document.fonts) pendingFonts.push(document.fonts.ready);
            if (window.__hfWebFontReady) pendingFonts.push(window.__hfWebFontReady);
            Promise.all([...pendingFonts, ...pendingImages]).then(async () => {
              await Promise.resolve();
              if (document.fonts && document.body && typeof getComputedStyle === "function") {
                const usedFonts = new Map();
                for (const element of document.body.querySelectorAll("*")) {
                  const text = element.childElementCount === 0 ? element.textContent?.trim() : "";
                  const font = text && getComputedStyle(element).font;
                  if (font && !usedFonts.has(font)) usedFonts.set(font, text.slice(0, 128));
                }
                await Promise.all([...usedFonts].map(([font, text]) =>
                  document.fonts.load(font, text).catch(() => null)));
                await document.fonts.ready;
              }
              void document.body.offsetWidth;
              applyAuditAllowances();
              queueMicrotask(replay);
            }, reject).catch(reject);
          }));
        });
      },
      installRuntimeGlobals,
      restoreRuntimeGlobals,
    };

    EventTarget.prototype.addEventListener = trackedAdd;
    HTMLCanvasElement.prototype.getContext = trackedGetContext;
    if (NativeResizeObserver) window.ResizeObserver = DeterministicResizeObserver;
    if (NativeIntersectionObserver) window.IntersectionObserver = DeterministicIntersectionObserver;
    return api;
  }

  function reset() {
    if (state) state.dispose();
    for (const name of RESET_RUNTIME_GLOBALS) {
      try { delete window[name]; } catch {}
      if (Object.prototype.hasOwnProperty.call(window, name)) {
        try { window[name] = undefined; } catch {}
      }
    }
    for (const attribute of Array.from(document.body.attributes || [])) {
      document.body.removeAttribute(attribute.name);
    }
    for (const [name, value] of SOURCE_BODY_ATTRIBUTES) document.body.setAttribute(name, value);
    document.body.innerHTML = SOURCE_BODY;
    window.scrollTo?.(0, 0);
    if (document.documentElement) document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    state = createState();
    window.__hf = state;
    state.installRuntimeGlobals();
    try {
      for (const factory of window.__hfRecipeFactories || []) factory(state);
    } finally {
      state.restoreRuntimeGlobals();
    }
    try { window.ScrollTrigger?.enable?.(); } catch {}
    applyAuditAllowances();
    state.captureAnimations();
  }

  async function renderAt(time) {
    const target = Math.max(0, Math.min(${duration}, Number(time) || 0));
    const generation = ++seekGeneration;
    if (state && renderedTime !== null && Math.abs(target - renderedTime) <= 1e-9) {
      applyAuditAllowances();
      return true;
    }
    if (state && renderedTime !== null && (target > renderedTime + 1e-9 || INTERACTION.bidirectionalSeek)) {
      const current = state;
      const complete = await current.runTo(
        target,
        () => state === current && generation === seekGeneration,
        renderedTime,
      );
      if (complete && state === current && generation === seekGeneration) {
        applyAuditAllowances();
        renderedTime = target;
      }
      return complete;
    }
    renderedTime = null;
    reset();
${deferReplay ? `    const current = state;
    const complete = await current.runToAsync(
      target,
      () => state === current && generation === seekGeneration,
    );` : `    const current = state;
    const complete = await current.runTo(
      target,
      () => state === current && generation === seekGeneration,
    );`}
    if (complete && state === current && generation === seekGeneration) {
      applyAuditAllowances();
      renderedTime = target;
    }
    return complete;
  }

  let requestedTime = window.__hfThreeTime || 0;
  let fontsReady = !FONT_WARMUP;
  let pendingSeek = Promise.resolve();

  function queueSeek(time) {
    requestedTime = time;
    pendingSeek = Promise.resolve(fontsReady ? renderAt(requestedTime) : readyForSeek);
    return pendingSeek;
  }

  window.addEventListener("hf-seek", (event) => {
    const completion = queueSeek(event.detail.time);
    event.detail.waitUntil?.(completion);
  });
  const readyForSeek = FONT_WARMUP
    ? FONT_WARMUP.then(() => {
        fontsReady = true;
        return renderAt(requestedTime);
      })
    : renderAt(requestedTime);
  pendingSeek = readyForSeek;
  window.__hfWaitForSeekCompletion = () => pendingSeek;
})();
`;
}

async function bundleRecipeScripts(recipeDir, blocks) {
  const factories = [];
  for (const block of blocks) {
    let source = block.inlineCode || "";
    if (block.source && !/^(?:[a-z]+:|\/\/)/i.test(block.source)) {
      const resolved = path.resolve(recipeDir, block.source);
      source = await readFile(resolved, "utf8");
    }
    if (!source.trim()) continue;
    factories.push(`function (__hf) {\n${transformRuntimeCode(source)}\n}`);
  }
  return `/* Generated from the original recipe scripts. Source credit comments are preserved below. */\nwindow.__hfRecipeFactories = [\n${factories.join(",\n")}\n];\n`;
}

async function copyRecipeSource(recipeDir, outputDir) {
  const sourceDir = path.join(outputDir, "source");
  await mkdir(sourceDir, { recursive: true });
  for (const entry of await readdir(recipeDir, { withFileTypes: true })) {
    if (entry.name === "hyperframes") continue;
    await cp(path.join(recipeDir, entry.name), path.join(sourceDir, entry.name), { recursive: true });
  }
  for (const entry of await readdir(path.dirname(recipeDir), { withFileTypes: true })) {
    if (!entry.isFile() || !/^(?:LICENSE(?:\..*)?|NOTICE(?:\..*)?|SOURCE\.json)$/i.test(entry.name)) continue;
    await cp(path.join(path.dirname(recipeDir), entry.name), path.join(sourceDir, entry.name));
  }
}

async function copyLottieRuntime(recipesRoot, outputDir) {
  const runtime = path.join(recipesRoot, "lottie", "_runtime", "lottie.min.js");
  try {
    await stat(runtime);
  } catch {
    return;
  }
  const destination = path.join(outputDir, "_runtime", "lottie.min.js");
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(runtime, destination);
}

async function copyThreeRuntime(recipeDir, outputDir) {
  const source = path.join(recipeDir, "_runtime", "three");
  const destination = path.join(outputDir, "_runtime", "three");
  await cp(source, destination, { recursive: true });
}

async function ensureLottieAssets(recipeDir, outputDir, jsonFile) {
  const animation = JSON.parse(await readFile(path.join(recipeDir, jsonFile), "utf8"));
  const layers = [
    ...(Array.isArray(animation.layers) ? animation.layers : []),
    ...(Array.isArray(animation.assets)
      ? animation.assets.flatMap((asset) => Array.isArray(asset.layers) ? asset.layers : [])
      : []),
  ];
  for (const asset of Array.isArray(animation.assets) ? animation.assets : []) {
    if (!asset || typeof asset.p !== "string" || /^(?:data:|[a-z]+:|\/\/)/i.test(asset.p)) continue;
    const relative = path.join(typeof asset.u === "string" ? asset.u : "", asset.p);
    const source = path.resolve(recipeDir, relative);
    const recipeRoot = path.resolve(recipeDir) + path.sep;
    const destination = path.resolve(outputDir, "source", relative);
    const outputRoot = path.resolve(outputDir, "source") + path.sep;
    if (!source.startsWith(recipeRoot) || !destination.startsWith(outputRoot)) {
      throw new Error(`Lottie asset escapes recipe directory: ${relative}`);
    }
    if (await fileExists(destination)) continue;
    const references = layers.filter((layer) => layer && layer.refId === asset.id);
    if (references.some((layer) => layer.hd !== true)) {
      throw new Error(`Lottie visible asset is missing: ${relative}`);
    }
    await mkdir(path.dirname(destination), { recursive: true });
    await writeFile(destination, TRANSPARENT_PNG);
  }
}

async function copyReferencedAssets({ recipesRoot, recipeDir, outputDir, html }) {
  for (const reference of activeLocalReferences(html)) {
    const source = path.resolve(recipeDir, reference);
    const sourceRoot = path.resolve(recipesRoot) + path.sep;
    if (!source.startsWith(sourceRoot)) continue;
    const destination = path.resolve(outputDir, "source", reference);
    const outputRoot = path.resolve(outputDir) + path.sep;
    if (!destination.startsWith(outputRoot)) continue;
    if (await fileExists(destination)) continue;
    if (!(await fileExists(source))) continue;
    await mkdir(path.dirname(destination), { recursive: true });
    await cp(source, destination);
  }
}

export async function convertRecipe({ recipesRoot, recipeDir }) {
  const manifest = await readFile(path.join(recipeDir, "recipe.motion.yaml"), "utf8");
  const id = scalar(manifest, "id") || path.basename(recipeDir);
  const runtime = list(manifest, "runtime");
  const entry = scalar(manifest, "entry") || "preview.html";
  const duration = durationSeconds(manifest, recipeDir);
  const outputDir = path.join(recipeDir, "hyperframes");
  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  await copyRecipeSource(recipeDir, outputDir);

  const preview = await readFile(path.join(recipeDir, entry), "utf8");
  const { withoutScripts, blocks } = scriptBlocks(preview);
  let { head, body: sourceBody } = documentParts(withoutScripts);
  let body = stripDemoChrome(sourceBody).replace(
    /class=(["'])([^"']*\bui-sheet\b[^"']*)\1/,
    (match) => `${match} data-layout-allow-overflow`,
  );
  if (id === "attention-pulse") {
    body = body.replace(
      /(<[a-z][^>]*\bdata-pulse\b[^>]*>)/gi,
      '$1<span class="hf-pulse-ring" aria-hidden="true"></span>',
    );
    head += `<style>
      [data-pulse]::after { display: none !important; }
      .hf-pulse-ring {
        display: block; position: absolute; inset: 0; border-radius: inherit;
        border: 2px solid currentColor; color: transparent; opacity: 1; transform: scale(1);
        animation: hf-ma-pulse 2s cubic-bezier(0.16, 1, 0.3, 1) infinite;
        pointer-events: none; will-change: transform, color;
      }
      @keyframes hf-ma-pulse {
        0% { color: color-mix(in srgb, var(--pulse-color, #8b7cf6) 50%, transparent); transform: scale(1); }
        70%, 100% { color: transparent; transform: scale(1.5); }
      }
    </style>`;
  }
  await copyReferencedAssets({ recipesRoot, recipeDir, outputDir, html: `${head}\n${body}` });
  let lottieJson = "animation.json";
  if (runtime.includes("lottie")) {
    const jsonFile = (await readdir(recipeDir)).find((name) => name.endsWith(".json"));
    if (jsonFile) lottieJson = jsonFile;
    await copyLottieRuntime(recipesRoot, outputDir);
    await ensureLottieAssets(recipeDir, outputDir, lottieJson);
  } else if (runtime.includes("three")) {
    await copyThreeRuntime(recipeDir, outputDir);
    await writeFile(path.join(outputDir, "hf-recipe.js"), threeRecipeSource(), "utf8");
    await writeFile(path.join(outputDir, "hf-adapter.js"), threeAdapterSource({ id, duration }), "utf8");
  } else if (runtime.includes("svg-smil")) {
    await writeFile(
      path.join(outputDir, "hf-recipe.js"),
      "/* The original inline SVG SMIL implementation is preserved in index.html and source/. */\n",
      "utf8",
    );
    await writeFile(path.join(outputDir, "hf-adapter.js"), svgSmilAdapterSource({ id, duration }), "utf8");
  } else {
    await writeFile(path.join(outputDir, "hf-recipe.js"), await bundleRecipeScripts(recipeDir, blocks), "utf8");
    await writeFile(
      path.join(outputDir, "hf-adapter.js"),
      deterministicReplayAdapterSource({ id, duration, body, runtime }),
      "utf8",
    );
  }

  const html = runtime.includes("three")
    ? threeCompositionHtml({ id, duration })
    : compositionHtml({ id, duration, head, body, runtime, lottieJson });
  await writeFile(path.join(outputDir, "index.html"), html, "utf8");
  const receipt = {
    schema_version: 1,
    recipe_id: id,
    surface: path.basename(path.dirname(recipeDir)),
    runtime,
    duration_s: duration,
    entry: "index.html",
    source_entry: entry,
    deterministic_adapter: runtime.includes("lottie")
      ? "lottie"
      : runtime.includes("three")
        ? "three"
        : runtime.includes("svg-smil")
          ? "svg-smil"
        : runtime.includes("css") && runtime.length === 1
          ? "css"
          : "replay",
    source_manifest_sha256: sha256(manifest),
  };
  await writeFile(path.join(outputDir, "conversion.json"), `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
  return receipt;
}

export async function convertAll({ recipesRoot }) {
  const recipes = await discoverRecipes(recipesRoot);
  const receipts = [];
  for (const recipe of recipes) {
    receipts.push(await convertRecipe({ recipesRoot, recipeDir: recipe.recipeDir }));
  }
  return receipts;
}

async function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const defaultRoot = path.resolve(scriptDir, "..", "recipes");
  const recipesRoot = path.resolve(process.argv[2] || defaultRoot);
  const receipts = await convertAll({ recipesRoot });
  process.stdout.write(`converted ${receipts.length} motion-anything recipes\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}
