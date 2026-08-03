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

const DEFAULT_DURATION_SECONDS = 6;
const FRAME_STEP_SECONDS = 1 / 60;

function scalar(manifest, key) {
  const match = manifest.match(new RegExp(`^\\s*${key}:\\s*([^#\\r\\n]+)`, "m"));
  if (!match) return null;
  return match[1].trim().replace(/^['"]|['"]$/g, "");
}

function list(manifest, key) {
  const value = scalar(manifest, key);
  if (!value) return [];
  const bracketed = value.match(/^\[(.*)\]$/);
  if (!bracketed) return [value];
  return bracketed[1]
    .split(",")
    .map((item) => item.trim().replace(/^['"]|['"]$/g, ""))
    .filter(Boolean);
}

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

export async function discoverRecipes(recipesRoot) {
  const manifestPaths = (await walk(recipesRoot))
    .filter((file) => path.basename(file) === "recipe.motion.yaml")
    .filter((file) => !file.split(path.sep).includes("hyperframes"))
    .sort((a, b) => a.localeCompare(b));

  return Promise.all(
    manifestPaths.map(async (manifestPath) => {
      const manifest = await readFile(manifestPath, "utf8");
      const recipeDir = path.dirname(manifestPath);
      return {
        id: scalar(manifest, "id") || path.basename(recipeDir),
        surface: path.basename(path.dirname(recipeDir)),
        recipeDir,
        manifestPath,
        manifest,
        runtime: list(manifest, "runtime"),
        entry: scalar(manifest, "entry") || "preview.html",
      };
    }),
  );
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
    const indexPath = path.join(outputDir, "index.html");
    const receiptPath = path.join(outputDir, "conversion.json");
    if (!(await fileExists(indexPath)) || !(await fileExists(receiptPath))) {
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
      if (!(await fileExists(path.resolve(outputDir, reference)))) {
        errors.push(`${recipe.id}: missing local reference ${reference}`);
      }
    }

    let receipt;
    try {
      receipt = JSON.parse(await readFile(receiptPath, "utf8"));
    } catch (error) {
      errors.push(`${recipe.id}: conversion receipt is invalid JSON (${error.message})`);
      continue;
    }
    if (receipt.recipe_id !== recipe.id || receipt.source_manifest_sha256 !== sha256(recipe.manifest)) {
      errors.push(`${recipe.id}: conversion receipt does not bind the current manifest`);
    }

    for (const name of ["hf-recipe.js", "hf-adapter.js"]) {
      const scriptPath = path.join(outputDir, name);
      if (!(await fileExists(scriptPath))) continue;
      const script = await readFile(scriptPath, "utf8");
      try {
        new Function(script);
      } catch (error) {
        errors.push(`${recipe.id}: ${name} is not valid script syntax (${error.message})`);
      }
      if (name === "hf-recipe.js" && forbiddenRuntime.test(script)) {
        errors.push(`${recipe.id}: converted recipe contains an unwrapped time or random API`);
      }
    }

    const generatedRecipePath = path.join(outputDir, "hf-recipe.js");
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

function transformRuntimeCode(source) {
  return source
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
  <script src="source/_runtime/lottie.min.js"></script>
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

function adapterSource({ id, duration, body, runtime }) {
  return `/* Generated deterministic HyperFrames adapter for ${id}. */
(function () {
  "use strict";
  const FRAME_STEP = ${FRAME_STEP_SECONDS};
  const TRACK_CSS = ${runtime.includes("css")};
  const SOURCE_BODY = ${JSON.stringify(rewriteLocalAssetPaths(body))};
  const nativeDocumentGetAnimations = typeof document.getAnimations === "function"
    ? document.getAnimations.bind(document)
    : null;
  const NativeCSSAnimation = window.CSSAnimation;
  const NativeCSSTransition = window.CSSTransition;
  let state = null;

  function isCssManagedAnimation(animation) {
    return (NativeCSSAnimation && animation instanceof NativeCSSAnimation)
      || (NativeCSSTransition && animation instanceof NativeCSSTransition);
  }

  if (TRACK_CSS && nativeDocumentGetAnimations) {
    document.getAnimations = (...args) => nativeDocumentGetAnimations(...args)
      .filter((animation) => !isCssManagedAnimation(animation));
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
    const NativeResizeObserver = window.ResizeObserver;
    const NativeIntersectionObserver = window.IntersectionObserver;

    function trackedAdd(type, listener, options) {
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

    const api = {
      time: 0,
      duration: ${duration},
      seek(time) { renderAt(time); },
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
      dispose() {
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
      runTo(target) {
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
    };

    EventTarget.prototype.addEventListener = trackedAdd;
    HTMLCanvasElement.prototype.getContext = trackedGetContext;
    if (NativeResizeObserver) window.ResizeObserver = DeterministicResizeObserver;
    if (NativeIntersectionObserver) window.IntersectionObserver = DeterministicIntersectionObserver;
    return api;
  }

  function reset() {
    if (state) state.dispose();
    document.body.innerHTML = SOURCE_BODY;
    state = createState();
    window.__hf = state;
    for (const factory of window.__hfRecipeFactories || []) factory(state);
    state.captureAnimations();
  }

  function renderAt(time) {
    const target = Math.max(0, Math.min(${duration}, Number(time) || 0));
    reset();
    state.runTo(target);
    state.seekAnimations(target);
  }

  window.addEventListener("hf-seek", (event) => renderAt(event.detail.time));
  renderAt(window.__hfThreeTime || 0);
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
}

async function copyLottieRuntime(recipesRoot, outputDir) {
  const runtime = path.join(recipesRoot, "lottie", "_runtime", "lottie.min.js");
  try {
    await stat(runtime);
  } catch {
    return;
  }
  const destination = path.join(outputDir, "source", "_runtime", "lottie.min.js");
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(runtime, destination);
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
  const { head, body: sourceBody } = documentParts(withoutScripts);
  const body = stripDemoChrome(sourceBody);
  await copyReferencedAssets({ recipesRoot, recipeDir, outputDir, html: `${head}\n${body}` });
  let lottieJson = "animation.json";
  if (runtime.includes("lottie")) {
    const jsonFile = (await readdir(recipeDir)).find((name) => name.endsWith(".json"));
    if (jsonFile) lottieJson = jsonFile;
    await copyLottieRuntime(recipesRoot, outputDir);
  } else {
    await writeFile(path.join(outputDir, "hf-recipe.js"), await bundleRecipeScripts(recipeDir, blocks), "utf8");
    await writeFile(path.join(outputDir, "hf-adapter.js"), adapterSource({ id, duration, body, runtime }), "utf8");
  }

  const html = compositionHtml({ id, duration, head, body, runtime, lottieJson });
  await writeFile(path.join(outputDir, "index.html"), html, "utf8");
  const receipt = {
    schema_version: 1,
    recipe_id: id,
    surface: path.basename(path.dirname(recipeDir)),
    runtime,
    duration_s: duration,
    entry: "index.html",
    source_entry: entry,
    deterministic_adapter: runtime.includes("lottie") ? "lottie" : runtime.includes("css") && runtime.length === 1 ? "css" : "replay",
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
