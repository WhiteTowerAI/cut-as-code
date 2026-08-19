import crypto from "node:crypto";
import { spawn } from "node:child_process";
import {
  cp,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  deterministicReplayAdapterSource,
  transformRuntimeCode,
} from "./convert_motion_anything_recipes.mjs";

const compareNames = (left, right) => left.localeCompare(right, "en", { numeric: true });

export function stabilizeCodropsCanvasResizes(source) {
  return source
    .replace(
      /\bcanvas\.(width|height)\s*=\s*([^;\r\n]+);/g,
      (_full, property, rawValue) => {
        const value = rawValue.trim();
        return `if (canvas.${property} !== Math.floor(${value})) canvas.${property} = Math.floor(${value});`;
      },
    )
    .replace(
      /\bregl\.clear\(\{\s*color:\s*(\[[^\]]+\])\s*\}\);/g,
      "regl.clear({ color: $1, depth: 1 });",
    );
}

export function stabilizeCodropsInlineAssetVariables(source, projectId) {
  if (projectId !== "3DCarousel") return source;
  return source.replace(
    /(--img\s*:\s*url\(\s*(['"]?))assets\//gi,
    "$1../assets/",
  );
}

export function stabilizeSynchronousCodropsInitialization(source, projectId, variantName) {
  if (projectId === "3DCarousel") {
    return source.replace(
      /preloadImages\(\s*["']\.grid__item-image["']\s*\)\.then\(\s*\(\)\s*=>\s*\{\s*document\.body\.classList\.remove\(\s*["']loading["']\s*\)\s*;\s*init\(\)\s*;\s*\}\s*\)\s*;?/s,
      'document.body.classList.remove("loading");\ninit();',
    );
  }
  if (projectId === "RotatingOnScrollAnimations" && variantName === "index2") {
    return source.replace(
      /document\.addEventListener\(\s*["']DOMContentLoaded["']\s*,\s*async\s*\(\)\s*=>\s*\{\s*await\s+preloadImages\(\s*["']\.gallery__item["']\s*\)\s*;\s*document\.body\.classList\.remove\(\s*["']loading["']\s*\)\s*;\s*init\(\)\s*;\s*\}\s*\)\s*;?/s,
      'document.body.classList.remove("loading");\ninit();',
    );
  }
  return source;
}

const DETERMINISTIC_LENIS_STUB = `
window.Lenis = class Lenis {
  constructor() { this.lastScroll = window.scrollY; }
  on(type, callback) {
    if (type !== "scroll" || typeof callback !== "function") return () => {};
    const listener = () => {
      const scroll = window.scrollY;
      const velocity = scroll - this.lastScroll;
      this.lastScroll = scroll;
      callback({ scroll, animatedScroll: scroll, targetScroll: scroll, velocity, direction: Math.sign(velocity) });
    };
    window.addEventListener("scroll", listener);
    return () => window.removeEventListener("scroll", listener);
  }
  raf() { return this; }
};`;

const INTERACTION_GROUPS = {
  scroll: new Set([
    "3DCarousel",
    "3DStackMotion",
    "ColumnScroll",
    "ConnectedGrid",
    "ImageExpansionTypography",
    "OneElementScroll",
    "OnScrollColumnsRows",
    "OnScrollFilter",
    "OnScrollLayoutFormations",
    "OnScrollLetterAnimations",
    "OnScrollTypographyAnimations",
    "RotatingOnScrollAnimations",
    "Scroll3DGrid",
    "ScrollBasedLayoutAnimations",
    "ScrollBlurTypography",
    "ScrollSpiral",
    "Staggered3DGridAnimations",
  ]),
  transition: new Set([
    "CoverPageTransition",
    "DecorativeLetterAnimations",
    "FullscreenClipEffect",
    "FullscreenScroll",
    "GridToSlider",
    "ImageToGridTransition",
    "KineticTypePageTransition",
    "LayersAnimation",
    "LinesToLayout",
    "PixelTransition",
    "RepeatingImageTransition",
    "ShapesSlideshow",
    "SlideshowAnimations",
    "TextBlockTransitions",
    "TypeShuffleAnimation",
  ]),
  pointer: new Set([
    "IntroGridMotionTransition",
    "LayerMotionSlideshow",
    "PreviewContentTransition",
    "UnrevealEffects",
  ]),
};

const TRANSITION_TRIGGERS = {
  CoverPageTransition: ".item__link",
  FullscreenClipEffect: "button.cover__button",
  GridToSlider: ".intro-grid__img",
  ImageToGridTransition: ".content__enter",
  KineticTypePageTransition: ".item",
  LayersAnimation: ".layers",
  LinesToLayout: ".image",
  PixelTransition: ".intro__image",
  RepeatingImageTransition: ".grid__item",
  ShapesSlideshow: ".slides-nav__button--next",
  SlideshowAnimations: ".slides-nav__item--next",
  TextBlockTransitions: ".trigger",
};

const POINTER_TRIGGERS = {
  IntroGridMotionTransition: ".enter",
  LayerMotionSlideshow: ".nav__arrow--next",
  PreviewContentTransition: ".item__enter",
  UnrevealEffects: ".content__item-img-wrap",
};

const PROJECT_RUNTIME_GLOBAL_RESETS = {
  "3DCarousel": [
    "gsap",
    "Observer",
    "ScrollTrigger",
    "ScrollSmoother",
    "ScrollToPlugin",
    "SplitText",
    "imagesLoaded",
  ],
  LayerMotionSlideshow: [
    "_gsDefine",
    "_gsQueue",
    "TweenLite",
    "TweenMax",
    "TimelineLite",
    "TimelineMax",
  ],
  Scroll3DGrid: ["gsap", "ScrollTrigger"],
};

export function runtimeGlobalsForProject(projectId, variantName = "") {
  if (projectId === "RotatingOnScrollAnimations" && variantName === "index2") {
    return ["gsap", "Observer", "ScrollTrigger", "imagesLoaded"];
  }
  return [...(PROJECT_RUNTIME_GLOBAL_RESETS[projectId] || [])];
}

const COMMON_AUDIT_ALLOWANCES = {
  "data-layout-allow-overlap": [".char", ".word", ".oh", ".oh__inner", "[data-splitting]"],
  "data-layout-allow-occlusion": [".oh__inner"],
};

const PROJECT_AUDIT_ALLOWANCES = {
  "3DCarousel": { "data-layout-ignore-text": [".scene__title .char"] },
  "3DStackMotion": { "data-layout-allow-overlap": [".intro"] },
  ColumnScroll: { "data-layout-allow-overlap": [".heading"] },
  CoverPageTransition: {
    "data-layout-allow-overlap": [".item__link", ".item__desc"],
    "data-layout-allow-occlusion": [".item__meta", ".item__title", ".item__desc"],
    "data-layout-ignore": [
      "main > div:nth-of-type(2) > div > p, main > div:nth-of-type(2) > div > a, main > section h3 > span",
    ],
  },
  FullscreenClipEffect: {
    "data-layout-ignore": ["main > div:nth-of-type(4) > h2 > span > span"],
  },
  FullscreenScroll: { "data-layout-allow-occlusion": [".slide__content"] },
  ImageExpansionTypography: { "data-layout-allow-overlap": [".anim"] },
  LayerMotionSlideshow: {
    "data-layout-ignore": [
      'span[class^="char"]',
      "main > div:nth-of-type(2) > div:nth-of-type(1) > h2 > span:nth-of-type(3) > span",
      "main > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(5) > p:nth-of-type(2)",
    ],
  },
  LayersAnimation: { "data-layout-allow-occlusion": [".content__inner"] },
  LinesToLayout: {
    "data-layout-allow-overlap": [".row__text"],
    "data-layout-allow-occlusion": [".row__text"],
  },
  PixelTransition: { "data-layout-ignore": [".intro__text"] },
  PreviewContentTransition: {
    "data-layout-allow-overlap": [".item__excerpt", ".content__text"],
    "data-layout-ignore": [".heading--item"],
  },
  ScrollBasedLayoutAnimations: {
    "data-layout-ignore": ["main > section:nth-of-type(1) > div"],
  },
  ShapesSlideshow: {
    "data-layout-allow-overlap": [".text-row"],
    "data-layout-allow-occlusion": [".text-row"],
  },
  UnrevealEffects: {
    "data-layout-allow-overlap": [".content__item-caption"],
    "data-layout-allow-occlusion": [".content__item-caption"],
    "data-layout-ignore": [".content__item h2", ".content__item-caption", ".preview__item h3"],
  },
};

const VARIANT_AUDIT_ALLOWANCES = {
  "KineticTypePageTransition/index": {
    "data-layout-ignore": ["main > section:nth-of-type(2) > article:nth-of-type(1) > h2"],
  },
  "OnScrollLetterAnimations/index2": {
    "data-layout-ignore": ["main > section:nth-of-type(1) > h2"],
  },
  "OnScrollLetterAnimations/index4": {
    "data-layout-ignore": [
      "main > section:nth-of-type(1) > h2",
      "main > section:nth-of-type(5) > h2",
    ],
  },
  "PixelTransition/index4": {
    "data-layout-ignore": ["main > section > div:nth-of-type(1) > div:nth-of-type(2)"],
  },
  "PixelTransition/index5": {
    "data-layout-ignore": ["main > section > div:nth-of-type(1) > div:nth-of-type(2)"],
  },
  "RotatingOnScrollAnimations/index3": {
    "data-layout-ignore": ["main > div:nth-of-type(2) > div"],
  },
  "RotatingOnScrollAnimations/index4": {
    "data-layout-ignore": ["main > div:nth-of-type(2) > div"],
  },
  "RotatingOnScrollAnimations/index5": {
    "data-layout-ignore": ["main > div:nth-of-type(2) > div"],
  },
};

export function codropsAuditAllowancesForVariant(projectId, variantName) {
  const merged = {};
  for (const group of [
    COMMON_AUDIT_ALLOWANCES,
    PROJECT_AUDIT_ALLOWANCES[projectId],
    VARIANT_AUDIT_ALLOWANCES[`${projectId}/${variantName}`],
  ].filter(Boolean)) {
    for (const [attribute, selectors] of Object.entries(group)) {
      merged[attribute] = [...new Set([...(merged[attribute] || []), ...selectors])];
    }
  }
  return merged;
}

async function isDirectory(target) {
  try {
    return (await stat(target)).isDirectory();
  } catch {
    return false;
  }
}

async function fileExists(target) {
  try {
    await stat(target);
    return true;
  } catch {
    return false;
  }
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function htmlAttribute(attributes, name) {
  const match = attributes.match(new RegExp(
    `\\b${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s"'=<>\\x60]+))`,
    "i",
  ));
  return match ? match[1] ?? match[2] ?? match[3] : null;
}

function extractScripts(html) {
  const blocks = [];
  const withoutScripts = html.replace(
    /<script\b([^>]*)>([\s\S]*?)<\/script>/gi,
    (full, attributes, inlineCode) => {
      const type = htmlAttribute(attributes, "type")?.toLowerCase() || "classic";
      if (!["classic", "module", "text/javascript", "application/javascript"].includes(type)) return full;
      blocks.push({
        source: htmlAttribute(attributes, "src"),
        inlineCode,
        type,
      });
      return "";
    },
  );
  return { withoutScripts, blocks };
}

function documentParts(html) {
  const bodyMatch = /<body\b([^>]*)>/i.exec(html);
  if (!bodyMatch) return { head: "", bodyAttributes: "", body: html };

  const beforeBody = html.slice(0, bodyMatch.index);
  const explicitHead = /<head\b[^>]*>([\s\S]*?)<\/head>/i.exec(beforeBody);
  const headOpen = /<head\b[^>]*>/i.exec(beforeBody);
  const htmlOpen = /<html\b[^>]*>/i.exec(beforeBody);
  const inferredHeadStart = headOpen
    ? headOpen.index + headOpen[0].length
    : htmlOpen
      ? htmlOpen.index + htmlOpen[0].length
      : 0;
  const afterBody = html.slice(bodyMatch.index + bodyMatch[0].length);
  const closingBody = afterBody.search(/<\/body\s*>/i);
  const closingHtml = afterBody.search(/<\/html\s*>/i);
  const bodyEnd = closingBody >= 0 ? closingBody : closingHtml >= 0 ? closingHtml : afterBody.length;
  return {
    head: explicitHead?.[1]
      || beforeBody.slice(inferredHeadStart).replace(/<\/head\s*>\s*$/i, "").replace(/<!doctype[^>]*>/i, ""),
    bodyAttributes: bodyMatch[1] || "",
    body: afterBody.slice(0, bodyEnd),
  };
}

export function commandNeedsShell(command, platform = process.platform) {
  return platform === "win32" && /\.(?:cmd|bat)$/i.test(command);
}

export function prepareSpawnArgs(command, args, platform = process.platform) {
  if (!commandNeedsShell(command, platform)) return args;
  return args.map((argument) => `"${String(argument).replaceAll('"', '""')}"`);
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, prepareSpawnArgs(command, args), {
      windowsHide: true,
      shell: commandNeedsShell(command),
      ...options,
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} exited ${code}: ${stderr.trim()}`));
    });
  });
}

async function bundleModule(entryPath, { esbuildCommand = "npx.cmd" } = {}) {
  const tempDir = await mkdtemp(path.join(os.tmpdir(), "codrops-esbuild-"));
  const output = path.join(tempDir, "bundle.js");
  try {
    const args = esbuildCommand.toLowerCase().endsWith("npx.cmd")
      ? ["--yes", "esbuild@0.25.8", entryPath]
      : [entryPath];
    await run(esbuildCommand, [
      ...args,
      "--bundle",
      "--format=iife",
      "--platform=browser",
      "--target=es2020",
      "--log-level=warning",
      `--outfile=${output}`,
    ], { cwd: path.dirname(entryPath) });
    return await readFile(output, "utf8");
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

function ignoredRemoteScript(source) {
  return /(?:tympanus\.net\/codrops\/adpacks|ajax\.googleapis\.com\/ajax\/libs\/webfont)/i.test(source);
}

async function findNamedFile(directory, fileName) {
  for (const entry of (await readdir(directory, { withFileTypes: true })).sort((a, b) => compareNames(a.name, b.name))) {
    if (["hyperframes", "node_modules", ".parcel-cache", "_review"].includes(entry.name)) continue;
    const target = path.join(directory, entry.name);
    if (entry.isFile() && entry.name.toLowerCase() === fileName.toLowerCase()) return target;
    if (entry.isDirectory()) {
      const found = await findNamedFile(target, fileName);
      if (found) return found;
    }
  }
  return null;
}

async function localVendorScript(source, importsRoot) {
  const fileName = /imagesloaded/i.test(source)
    ? "imagesloaded.pkgd.min.js"
    : /splitting\.min/i.test(source)
      ? "splitting.min.js"
      : /splittext/i.test(source)
        ? "SplitText.min.js"
        : /gsap/i.test(source)
          ? "gsap.min.js"
          : null;
  if (!fileName) return null;
  const localPath = await findNamedFile(importsRoot, fileName);
  return localPath ? readFile(localPath, "utf8") : null;
}

async function replaceAsync(input, pattern, replacer) {
  let output = "";
  let lastIndex = 0;
  for (const match of input.matchAll(pattern)) {
    output += input.slice(lastIndex, match.index);
    output += await replacer(...match);
    lastIndex = match.index + match[0].length;
  }
  return output + input.slice(lastIndex);
}

function extensionForRemote(url, contentType = "") {
  const pathname = new URL(url).pathname;
  const extension = path.posix.extname(pathname).toLowerCase();
  if (/^\.(?:woff2?|ttf|otf|css)$/.test(extension)) return extension;
  if (/woff2/i.test(contentType)) return ".woff2";
  if (/woff/i.test(contentType)) return ".woff";
  if (/truetype|ttf/i.test(contentType)) return ".ttf";
  if (/opentype|otf/i.test(contentType)) return ".otf";
  return ".bin";
}

async function fetchChecked(url, fetchImpl) {
  let response;
  let failure;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      response = await fetchImpl(url, {
        headers: { "user-agent": "Mozilla/5.0 Chrome/124 Safari/537.36" },
      });
      break;
    } catch (error) {
      failure = error;
      if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, attempt * 250));
    }
  }
  if (!response) throw new Error(`failed to freeze ${url}: ${failure?.message || "fetch failed"}`);
  if (!response?.ok) throw new Error(`failed to freeze ${url}: HTTP ${response?.status || "unknown"}`);
  return response;
}

async function freezeRemoteStylesheet({ url, sourceDir, fetchImpl, cache }) {
  if (cache.has(url)) return cache.get(url);
  const remoteDir = path.join(sourceDir, "_remote");
  await mkdir(remoteDir, { recursive: true });
  const response = await fetchChecked(url, fetchImpl);
  let css = await response.text();
  css = await replaceAsync(
    css,
    /url\(\s*(["']?)((?:https?:)?\/\/[^)'"\s]+)\1\s*\)/gi,
    async (_full, quote, rawAssetUrl) => {
      const assetUrl = rawAssetUrl.startsWith("//") ? `https:${rawAssetUrl}` : rawAssetUrl;
      const assetResponse = await fetchChecked(assetUrl, fetchImpl);
      const bytes = Buffer.from(await assetResponse.arrayBuffer());
      const extension = extensionForRemote(assetUrl, assetResponse.headers?.get?.("content-type") || "");
      const fileName = `${sha256(assetUrl).slice(0, 20)}${extension}`;
      await writeFile(path.join(remoteDir, fileName), bytes);
      return `url(${quote}./${fileName}${quote})`;
    },
  );
  css = css.replace(/,\s*mono(?=\s*[;}])/gi, ", monospace");
  const cssName = `${sha256(url).slice(0, 20)}.css`;
  await writeFile(path.join(remoteDir, cssName), css, "utf8");
  const localHref = `/source/_remote/${cssName}`;
  cache.set(url, localHref);
  return localHref;
}

async function localVendorStyle(url, { sourceDir, importsRoot }) {
  const fileName = /splitting-cells/i.test(url)
    ? "splitting-cells.css"
    : /splitting\.css/i.test(url)
      ? "splitting.css"
      : null;
  if (!fileName) return null;
  const source = await findNamedFile(importsRoot, fileName);
  if (!source) return null;
  const destinationDir = path.join(sourceDir, "_vendor");
  await mkdir(destinationDir, { recursive: true });
  await cp(source, path.join(destinationDir, fileName));
  return `/source/_vendor/${fileName}`;
}

function stripRemotePromoMedia(html) {
  return html.replace(
    /url\(\s*["']?https?:\/\/(?:[^)]*codrops\/wp-content|i7x7p5b7\.stackpathcdn\.com)[^)]*\)/gi,
    "none",
  );
}

function normalizeLocalRootReferences(html) {
  return html
    .replace(
      /\b(src|href)=(['"])\/(?!\/)([^'"]+)\2/gi,
      (_full, attribute, quote, value) => `${attribute}=${quote}${value}${quote}`,
    )
    .replace(/url\(\s*(['"]?)\/(?!\/)/gi, "url($1");
}

function runtimeAssetPath(value, runtimeEntry) {
  if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(value)) return value;
  const match = /^([^?#]*)([?#].*)?$/.exec(value);
  const pathname = match?.[1] || "";
  const suffix = match?.[2] || "";
  const runtimeDirectory = path.posix.dirname(runtimeEntry);
  const resolved = path.posix.normalize(path.posix.join(
    runtimeDirectory === "." ? "" : runtimeDirectory,
    pathname.replace(/^\/+/, ""),
  ));
  const rooted = resolved === ".." ? "" : resolved.replace(/^(?:\.\.\/)+/, "");
  if (!rooted || rooted === ".") throw new Error(`asset path has no local target: ${value}`);
  return `/source/${rooted}${suffix}`;
}

function relativizeSourceRootReferences(source, runtimeEntry) {
  const runtimeDirectory = path.posix.dirname(runtimeEntry);
  const from = runtimeDirectory === "." ? "" : runtimeDirectory;
  return source.replace(
    /(^|[="'(\s:])\/source\/([^"'()\s<>]+)/g,
    (_full, prefix, target) => `${prefix}${path.posix.relative(from, target)}`,
  );
}

function anchorRuntimeAssetReferences(html, runtimeEntry) {
  return html
    .replace(
      /\b(src|poster)=(['"])([^'"]+)\2/gi,
      (_full, attribute, quote, value) => `${attribute}=${quote}${runtimeAssetPath(value, runtimeEntry)}${quote}`,
    )
    .replace(
      /url\(\s*(['"]?)([^)'"\s]+)\1\s*\)/gi,
      (_full, quote, value) => `url(${quote}${runtimeAssetPath(value, runtimeEntry)}${quote})`,
    );
}

function normalizeShaderScriptTypes(html) {
  return html.replace(
    /(<script\b[^>]*\btype\s*=\s*)(['"]?)x-shader\/x-(?:fragment|vertex)\2/gi,
    '$1"application/json"',
  );
}

export async function localizeExternalStyles({
  html,
  sourceDir,
  importsRoot,
  fetchImpl = fetch,
  cache = new Map(),
}) {
  const sanitized = stripRemotePromoMedia(html).replace(
    /<link\b[^>]*\brel\s*=\s*["'][^"']*\bicon\b[^"']*["'][^>]*>/gi,
    "",
  );
  return replaceAsync(
    sanitized,
    /<link\b[^>]*\bhref\s*=\s*(?:(["'])((?:https?:)?\/\/[^"']+)\1|((?:https?:)?\/\/[^\s>]+))[^>]*>/gi,
    async (tag, _quote, quotedUrl, unquotedUrl) => {
      const rawUrl = quotedUrl || unquotedUrl;
      const url = rawUrl.startsWith("//") ? `https:${rawUrl}` : rawUrl;
      const relMatch = tag.match(/\brel\s*=\s*(?:(["'])([^"']+)\1|([^\s>]+))/i);
      const rel = (relMatch?.[2] || relMatch?.[3] || "").toLowerCase();
      if (/preconnect|dns-prefetch|icon/.test(rel)) return "";
      if (!rel.includes("stylesheet")) return "";
      const localVendor = await localVendorStyle(url, { sourceDir, importsRoot });
      const localHref = localVendor || (/use\.typekit\.net|fonts\.googleapis\.com/i.test(url)
        ? await freezeRemoteStylesheet({ url, sourceDir, fetchImpl, cache })
        : null);
      if (!localHref) throw new Error(`render-critical remote stylesheet is not localized: ${url}`);
      return tag.replace(rawUrl, localHref);
    },
  );
}

async function localizeCopiedCss({ sourceDir, importsRoot, fetchImpl, cache }) {
  const pending = [sourceDir];
  while (pending.length) {
    const directory = pending.pop();
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (entry.name === "_remote") continue;
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        pending.push(target);
      } else if (entry.isFile() && entry.name.toLowerCase().endsWith(".css")) {
        const css = await readFile(target, "utf8");
        const localized = await replaceAsync(
          css,
          /@import\s+(?:url\(\s*)?(["'])((?:https?:)?\/\/[^"']+)\1\s*\)?\s*;/gi,
          async (_full, _quote, rawUrl) => {
            const url = rawUrl.startsWith("//") ? `https:${rawUrl}` : rawUrl;
            const href = await freezeRemoteStylesheet({ url, sourceDir, fetchImpl, cache });
            const relativeHref = href.startsWith("/source/")
              ? path.relative(directory, path.join(sourceDir, href.slice("/source/".length)))
                .split(path.sep).join("/")
              : href;
            return `@import url("${relativeHref}");`;
          },
        );
        if (localized !== css) await writeFile(target, localized, "utf8");
      }
    }
  }
}

async function recipeSource({ blocks, runtimeDir, importsRoot, esbuildCommand, projectId, variantName }) {
  const sources = [];
  let needsWebFont = false;
  for (const block of blocks) {
    let source = block.inlineCode || "";
    if (block.source) {
      if (/(?:^|\/)lenis(?:\.min)?\.js(?:[?#].*)?$/i.test(block.source)) {
        source = DETERMINISTIC_LENIS_STUB;
      } else if (/^(?:https?:)?\/\//i.test(block.source)) {
        if (ignoredRemoteScript(block.source)) {
          needsWebFont ||= /ajax\.googleapis\.com\/ajax\/libs\/webfont/i.test(block.source);
          continue;
        }
        source = await localVendorScript(block.source, importsRoot);
        if (!source) throw new Error(`render-critical remote script is not localized: ${block.source}`);
      } else {
        const cleanSource = block.source.split(/[?#]/, 1)[0].replace(/^[/\\]+/, "");
        const resolved = path.resolve(runtimeDir, cleanSource);
        source = block.type === "module"
          ? await bundleModule(resolved, { esbuildCommand })
          : await readFile(resolved, "utf8");
      }
    }
    if (!source.trim()) continue;
    needsWebFont ||= /\bWebFont\b/.test(source);
    sources.push(stabilizeCodropsCanvasResizes(
      stabilizeSynchronousCodropsInitialization(
        transformRuntimeCode(source),
        projectId,
        variantName,
      ),
    ));
  }
  if (needsWebFont) {
    sources.unshift(`
window.WebFont = window.WebFont || {
  load(options = {}) {
    const usedFonts = new Map();
    if (document.fonts && document.body && typeof getComputedStyle === "function") {
      for (const element of document.body.querySelectorAll("*")) {
        const text = element.childElementCount === 0 ? element.textContent?.trim() : "";
        if (!text) continue;
        const font = getComputedStyle(element).font;
        if (font && !usedFonts.has(font)) usedFonts.set(font, text.slice(0, 128));
      }
    }
    const fonts = document.fonts
      ? [...document.fonts].map((fontFace) => fontFace.load().catch(() => null))
      : [];
    for (const [font, text] of usedFonts) {
      fonts.push(document.fonts.load(font, text).catch(() => null));
    }
    const ready = Promise.all(fonts)
      .then(() => document.fonts?.ready)
      .then(() => {
        if (typeof options.active === "function") options.active();
      })
      .then(() => Promise.resolve());
    window.__hfWebFontReady = ready;
    return ready;
  }
};
`);
  }
  const source = sources.join(";\n");
  const parcelReset = [...new Set(source.match(/\bparcelRequire[\w$]*\b/g) || [])]
    .map((name) => `delete globalThis.${name};`)
    .join("\n");
  return `/* Generated from the original Codrops entry scripts. */\nwindow.__hfRecipeFactories = [\nfunction (__hf) {\n${parcelReset}\n${source}\n}\n];\n`;
}

async function copyProjectSource(projectDir, sourceDir) {
  await mkdir(sourceDir, { recursive: true });
  for (const entry of await readdir(projectDir, { withFileTypes: true })) {
    if (["hyperframes", "node_modules", ".parcel-cache"].includes(entry.name)) continue;
    await cp(path.join(projectDir, entry.name), path.join(sourceDir, entry.name), {
      recursive: true,
      filter(source) {
        return !["node_modules", ".parcel-cache", "hyperframes"].includes(path.basename(source));
      },
    });
  }
}

async function runtimeEntryForVariant(project, variant) {
  if (variant.sourceEntry.startsWith("src/")) {
    const builtEntry = path.posix.join("dist", path.basename(variant.sourceEntry));
    if (await fileExists(path.join(project.projectDir, ...builtEntry.split("/")))) return builtEntry;
  }
  return variant.sourceEntry;
}

export function stripCodropsNonVideoContent(html) {
  return html.replace(
    /<section\b[^>]*\bclass=["'][^"']*\bcontent--related\b[^"']*["'][^>]*>[\s\S]*?<\/section\s*>/gi,
    "",
  );
}

function stripGeneratedAdapterBody(source) {
  return source.replace(
    /(const SOURCE_BODY = )("(?:\\.|[^"\\])*")(;)/,
    (match, prefix, encodedBody, suffix) => {
      try {
        return `${prefix}${JSON.stringify(stripCodropsNonVideoContent(JSON.parse(encodedBody)))}${suffix}`;
      } catch {
        return match;
      }
    },
  );
}

function compositionHtml({ id, duration, sourceHtml, runtimeEntry, variantName, projectId }) {
  sourceHtml = stabilizeCodropsInlineAssetVariables(
    relativizeSourceRootReferences(
      normalizeShaderScriptTypes(anchorRuntimeAssetReferences(sourceHtml, runtimeEntry)),
      runtimeEntry,
    ),
    projectId,
  );
  const { withoutScripts } = extractScripts(sourceHtml);
  const { head, bodyAttributes, body: sourceBody } = documentParts(withoutScripts);
  const body = stripCodropsNonVideoContent(sourceBody);
  const runtimeDirectory = path.posix.dirname(runtimeEntry);
  const runtimeSuffix = runtimeDirectory === "." ? "" : `${runtimeDirectory}/`;
  const baseHref = `../source/${runtimeSuffix}`;
  const rootAttributes = [
    bodyAttributes.trim(),
    `data-composition-id="${id}"`,
    'data-start="0"',
    'data-width="1920"',
    'data-height="1080"',
    `data-duration="${duration}"`,
    "data-no-timeline",
  ].filter(Boolean).join(" ");
  return applyCodropsChromePolicy(`<!doctype html>
<html lang="en">
<head>
  <link rel="icon" href="data:,">
  <script defer src="./hf-recipe.js" data-hf-recipe></script>
  <script defer src="./hf-adapter.js" data-hf-adapter></script>
  <base href="${baseHref}">
${head}
  <style data-hf-codrops-frame>
    html { width: 1920px; height: 1080px; scrollbar-width: none; }
    body[data-composition-id] { margin: 0; width: 1920px; min-height: 1080px; position: relative; }
    ::-webkit-scrollbar { display: none; }
  </style>
</head>
<body ${rootAttributes}>
${body}
</body>
</html>
`);
}

export async function discoverCodropsProjects(importsRoot) {
  const entries = await readdir(importsRoot, { withFileTypes: true });
  const projects = [];

  for (const entry of entries.filter((item) => item.isDirectory() && item.name !== "_review")) {
    if (entry.name === "KineticImages") continue;
    const projectDir = path.join(importsRoot, entry.name);
    const sourceDir = (await isDirectory(path.join(projectDir, "src")))
      ? path.join(projectDir, "src")
      : projectDir;
    const sourcePrefix = sourceDir === projectDir ? "" : "src";
    const sourceEntries = (await readdir(sourceDir, { withFileTypes: true }))
      .filter((item) => item.isFile() && /^index\d*\.html$/i.test(item.name))
      .map((item) => item.name)
      .sort(compareNames);
    if (sourceEntries.length === 0) continue;

    projects.push({
      id: entry.name,
      projectDir,
      variants: sourceEntries.map((fileName) => ({
        name: path.basename(fileName, path.extname(fileName)),
        sourceEntry: path.posix.join(sourcePrefix, fileName),
      })),
    });
  }

  return projects.sort((left, right) => compareNames(left.id, right.id));
}

export function interactionForProject(projectId) {
  for (const [mode, projects] of Object.entries(INTERACTION_GROUPS)) {
    if (projects.has(projectId)) return { mode };
  }
  throw new Error(`unclassified Codrops project: ${projectId}`);
}

export function interactionSpecForVariant(projectId, variantName) {
  const { mode } = interactionForProject(projectId);
  if (projectId === "3DCarousel" || (projectId === "RotatingOnScrollAnimations" && variantName === "index2")) {
    return {
      mode,
      duration: 8,
      actions: [],
      synchronousInitialization: true,
      ...(projectId === "3DCarousel" ? { bidirectionalSeek: true } : {}),
    };
  }
  if (projectId === "DecorativeLetterAnimations") {
    return {
      mode,
      duration: 18,
      actions: Array.from({ length: 9 }, (_value, index) => ({
        at: 0.8 + index * 1.8,
        type: "click",
        selector: ".slidenav__item--next",
      })),
    };
  }
  if (projectId === "TypeShuffleAnimation") {
    return {
      mode,
      duration: 14,
      actions: Array.from({ length: 6 }, (_value, index) => ({
        at: 0.8 + index * 2.1,
        type: "click",
        selector: ".effects > button",
        index,
      })),
    };
  }
  if (projectId === "FullscreenScroll") {
    return {
      mode,
      duration: 8,
      actions: [
        { at: 0.8, type: "wheel", deltaY: 620 },
        { at: 2.2, type: "click", selector: ".slide--current .slide__img" },
        { at: 5.3, type: "click", selector: ".frame__back" },
        { at: 6.5, type: "wheel", deltaY: 620 },
      ],
    };
  }
  if (mode === "scroll") {
    return {
      mode,
      duration: 8,
      actions: [],
      ...(projectId === "OnScrollColumnsRows" && variantName === "index10"
        ? { startAt: 0.25 }
        : {}),
    };
  }
  if (mode === "pointer") {
    return {
      mode,
      duration: 8,
      actions: [{ at: 2.4, type: "click", selector: POINTER_TRIGGERS[projectId] }],
    };
  }
  const selector = TRANSITION_TRIGGERS[projectId];
  if (!selector) throw new Error(`missing transition trigger: ${projectId}/${variantName}`);
  return {
    mode,
    duration: 6,
    actions: [{ at: 0.8, type: "click", selector }],
  };
}

export function codropsReplayAdapterSource(options) {
  return deterministicReplayAdapterSource({
    ...options,
    deferReplay: !options.interaction?.synchronousInitialization,
  });
}

export function applyCodropsChromePolicy(html) {
  const style = `<style data-hf-codrops-chrome>
html, body { overflow-anchor: none !important; }
html, body, body * { cursor: none !important; }
.codrops-header,
.codrops-links,
.github,
.sponsor,
[class*="sponsor"],
.demos,
.effects,
.trigger,
.frame__links,
.frame__tags,
.frame__nav,
.frame__info,
.frame__demo,
.frame__demos,
.frame__archive,
.frame__github,
.frame__author,
.frame__hire,
.frame--footer,
.frame .modal,
.frame__title,
.frame__title-back,
.frame__back,
.frame__prev,
.slidenav,
.slides-nav,
.nav__arrow,
.cover__button,
.content__enter,
.enter,
.item__enter,
.content__nav,
.content__footer,
.intro__title-sub,
.intro__info,
.credits,
.related,
footer,
.footer,
.copyright,
.cursor { display: none !important; }
[data-composition-id^="codrops-scrollbasedlayoutanimations-"] .caption,
[data-composition-id^="codrops-scrollbasedlayoutanimations-"] .project--details:has(a[href*="twitter.com/intent/tweet"]),
[data-composition-id^="codrops-scrollspiral-"] .content__text,
[data-composition-id^="codrops-scrollspiral-"] .main-title,
[data-composition-id^="codrops-scrollspiral-"] .main-tagline,
[data-composition-id^="codrops-scrollspiral-"] .media-item { visibility: hidden !important; }
body[data-composition-id^="codrops-scrollspiral-"].loading::before,
body[data-composition-id^="codrops-scrollspiral-"].loading::after,
[data-composition-id^="codrops-scrollspiral-"] .content--main::before,
[data-composition-id^="codrops-scrollspiral-"] .content--main::after { display: none !important; }
[data-composition-id^="codrops-layermotionslideshow-"] .slide--layout-2 .slide__text-description {
  color: rgb(94, 94, 94) !important;
}
</style>`;

  return /<\/head\s*>/i.test(html)
    ? html.replace(/<\/head\s*>/i, `${style}</head>`)
    : `${style}${html}`;
}

export async function convertCodropsProject({
  project,
  esbuildCommand = "npx.cmd",
  fetchImpl = fetch,
  provenance = null,
}) {
  const projectDir = path.resolve(project.projectDir);
  const normalizedProject = { ...project, projectDir };
  const outputDir = path.join(projectDir, "hyperframes");
  if (path.dirname(outputDir) !== projectDir) {
    throw new Error(`unsafe HyperFrames output path: ${outputDir}`);
  }
  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  const sourceDir = path.join(outputDir, "source");
  const dependencyCache = new Map();
  await copyProjectSource(projectDir, sourceDir);
  await localizeCopiedCss({
    sourceDir,
    importsRoot: path.dirname(projectDir),
    fetchImpl,
    cache: dependencyCache,
  });

  const receipts = [];
  for (const variant of project.variants) {
    const runtimeEntry = await runtimeEntryForVariant(normalizedProject, variant);
    const sourcePath = path.join(projectDir, ...variant.sourceEntry.split("/"));
    const runtimePath = path.join(projectDir, ...runtimeEntry.split("/"));
    const [sourceHtml, runtimeHtmlRaw] = await Promise.all([
      readFile(sourcePath, "utf8"),
      readFile(runtimePath, "utf8"),
    ]);
    const runtimeHtml = await localizeExternalStyles({
      html: normalizeLocalRootReferences(runtimeHtmlRaw),
      sourceDir,
      importsRoot: path.dirname(projectDir),
      fetchImpl,
      cache: dependencyCache,
    });
    const { blocks, withoutScripts } = extractScripts(runtimeHtml);
    const { body: runtimeBody } = documentParts(withoutScripts);
    const body = stripCodropsNonVideoContent(stabilizeCodropsInlineAssetVariables(
      relativizeSourceRootReferences(
        anchorRuntimeAssetReferences(runtimeBody, runtimeEntry),
        runtimeEntry,
      ),
      project.id,
    ));
    const interaction = interactionSpecForVariant(project.id, variant.name);
    const id = `codrops-${project.id.toLowerCase()}-${variant.name.toLowerCase()}`;
    const variantDir = path.join(outputDir, variant.name);
    await mkdir(variantDir, { recursive: true });

    const runtimeDir = path.dirname(runtimePath);
    const recipe = relativizeSourceRootReferences(await recipeSource({
      blocks,
      runtimeDir,
      importsRoot: path.dirname(projectDir),
      esbuildCommand,
      projectId: project.id,
      variantName: variant.name,
    }), runtimeEntry);
    const adapter = `/* Original Codrops project: ${project.id}. */\n${codropsReplayAdapterSource({
      id,
      duration: interaction.duration,
      body,
      runtime: ["css", "js"],
      interaction,
      rewriteAssets: false,
      auditAllowances: codropsAuditAllowancesForVariant(project.id, variant.name),
      resetRuntimeGlobals: runtimeGlobalsForProject(project.id, variant.name),
    })}`;
    const html = compositionHtml({
      id,
      duration: interaction.duration,
      sourceHtml: runtimeHtml,
      runtimeEntry,
      variantName: variant.name,
      projectId: project.id,
    });
    await Promise.all([
      writeFile(path.join(variantDir, "index.html"), html, "utf8"),
      writeFile(path.join(variantDir, "hf-recipe.js"), recipe, "utf8"),
      writeFile(path.join(variantDir, "hf-adapter.js"), adapter, "utf8"),
    ]);
    receipts.push({
      name: variant.name,
      composition_id: id,
      source_entry: variant.sourceEntry,
      runtime_entry: runtimeEntry,
      source_sha256: sha256(sourceHtml),
      runtime_sha256: sha256(runtimeHtmlRaw),
      duration_s: interaction.duration,
      interaction,
      output: `${variant.name}/index.html`,
    });
  }

  const receipt = {
    schema_version: 1,
    project_id: project.id,
    ...(provenance ? {
      demo_url: provenance.demo_url,
      article_url: provenance.article_url,
      source_url: provenance.source_url,
      source_commit: provenance.source_commit,
      license: provenance.license,
    } : {}),
    source_copy: "source",
    variants: receipts,
  };
  await writeFile(
    path.join(outputDir, "conversion.json"),
    `${JSON.stringify(receipt, null, 2)}\n`,
    "utf8",
  );
  return receipt;
}

export async function convertAllCodrops({
  importsRoot,
  esbuildCommand = "npx.cmd",
  fetchImpl = fetch,
}) {
  const root = path.resolve(importsRoot);
  const catalogPath = path.join(root, "SOURCE_CATALOG.json");
  const catalog = await fileExists(catalogPath)
    ? JSON.parse(await readFile(catalogPath, "utf8"))
    : { projects: [] };
  const provenance = new Map((catalog.projects || []).map((project) => [project.id, project]));
  const projects = (await discoverCodropsProjects(root))
    .filter((project) => provenance.size === 0 || provenance.has(project.id));
  const receipts = [];
  for (const project of projects) {
    receipts.push(await convertCodropsProject({
      project,
      esbuildCommand,
      fetchImpl,
      provenance: provenance.get(project.id) || null,
    }));
  }
  return receipts;
}

async function rewriteFrozenSourceCss(sourceDir) {
  const pending = [sourceDir];
  let changed = 0;
  while (pending.length) {
    const directory = pending.pop();
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        pending.push(target);
      } else if (entry.isFile() && entry.name.toLowerCase().endsWith(".css")) {
        const runtimeEntry = path.relative(sourceDir, target).split(path.sep).join("/");
        const source = await readFile(target, "utf8");
        const rewritten = relativizeSourceRootReferences(source, runtimeEntry);
        if (rewritten !== source) {
          await writeFile(target, rewritten, "utf8");
          changed += 1;
        }
      }
    }
  }
  return changed;
}

export async function rewriteExistingCodropsPaths(importsRoot) {
  const root = path.resolve(importsRoot);
  let projects = 0;
  let variants = 0;
  let files = 0;
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const hyperframes = path.join(root, entry.name, "hyperframes");
    const receiptPath = path.join(hyperframes, "conversion.json");
    if (!(await fileExists(receiptPath))) continue;
    const receipt = JSON.parse(await readFile(receiptPath, "utf8"));
    if (!Array.isArray(receipt.variants)) continue;
    projects += 1;
    let receiptChanged = false;

    for (const variant of receipt.variants) {
      const interaction = receipt.project_id === "KineticImages"
        ? variant.interaction
        : interactionSpecForVariant(receipt.project_id, variant.name);
      if (JSON.stringify(variant.interaction) !== JSON.stringify(interaction)) {
        variant.interaction = interaction;
        receiptChanged = true;
      }
      const runtimeEntry = variant.runtime_entry || variant.source_entry;
      const variantDir = path.dirname(path.join(hyperframes, ...variant.output.split("/")));
      const targets = ["index.html", "hf-recipe.js", "hf-adapter.js"];
      for (const name of targets) {
        const target = path.join(variantDir, name);
        if (!(await fileExists(target))) continue;
        const source = await readFile(target, "utf8");
        let rewritten = source;
        if (name === "index.html") {
          rewritten = rewritten
            .replace(/(<script\b[^>]*\bsrc=["'])\/[^"']+\/(hf-(?:recipe|adapter)\.js)(["'])/gi, "$1./$2$3")
            .replace(/(<base\b[^>]*\bhref=["'])\/source\/([^"']*)(["'])/gi, "$1../source/$2$3");
          rewritten = stabilizeCodropsInlineAssetVariables(rewritten, receipt.project_id);
          rewritten = stripCodropsNonVideoContent(rewritten);
        } else if (name === "hf-adapter.js") {
          rewritten = rewritten
            .replace(
              /const INTERACTION = \{[^\r\n]*\};/,
              `const INTERACTION = ${JSON.stringify(interaction)};`,
            )
            .replace(
              /target > renderedTime \+ 1e-9\)/,
              "(target > renderedTime + 1e-9 || INTERACTION.bidirectionalSeek))",
            )
            .replace(
              /const RESET_RUNTIME_GLOBALS = \[[^\r\n]*\];/,
              `const RESET_RUNTIME_GLOBALS = ${JSON.stringify(runtimeGlobalsForProject(receipt.project_id, variant.name))};`,
            );
          rewritten = stripGeneratedAdapterBody(rewritten);
        }
        rewritten = relativizeSourceRootReferences(rewritten, runtimeEntry);
        if (rewritten !== source) {
          await writeFile(target, rewritten, "utf8");
          files += 1;
        }
      }
      variants += 1;
    }
    if (receiptChanged) {
      await writeFile(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
      files += 1;
    }
    files += await rewriteFrozenSourceCss(path.join(hyperframes, receipt.source_copy || "source"));
  }
  return { projects, variants, files };
}

const CODROPS_STRUCTURAL_ROLES = new Set([
  "opener", "chapter", "interstitial", "outro", "background",
]);
const CODROPS_MOTION_FUNCTIONS = new Set([
  "reveal", "transition", "loop", "build", "settle",
]);
const CODROPS_RHYTHM_ENERGIES = new Set(["calm", "medium", "medium-high", "high"]);
const CODROPS_INFORMATION_DENSITIES = new Set(["sparse", "balanced", "dense"]);
const CODROPS_FRAME_RELATIONSHIPS = new Set(["fullscreen", "frame-dominant"]);
const CODROPS_COLOR_TENDENCIES = new Set([
  "image-led", "monochrome", "dark", "light", "flexible",
]);
const CODROPS_STYLE_SCALARS = [
  "description",
  "category",
  "rhythm_energy",
  "information_density",
  "frame_relationship",
  "color_tendency",
  "style_rationale",
];
const CODROPS_STYLE_LISTS = [
  "structural_roles",
  "motion_functions",
  "visual_language",
  "mechanisms",
  "tags",
  "intent_keywords",
  "best_for",
  "avoid_when",
];
const GENERIC_RESTRAINT = "Use as one frame-dominant designed cutaway; adapt content, palette, typography, framing, and timing instead of running an unchanged source showcase.";
const KINETIC_RESTRAINT = "Use as one frame-dominant designed cutaway; adapt content and select one intentional mode instead of running a source showcase.";
const GENERIC_USAGE = "Materialize the converted HyperFrames directory, then adapt imagery, palette, typography, framing, and timing to the shot.";
const KINETIC_USAGE = "Materialize the converted HyperFrames directory, then adapt imagery, palette, typography, framing, and timing to the shot. Select one KineticImages mode for a production cue.";

function yamlString(value) {
  return JSON.stringify(String(value));
}

function appendYamlList(lines, key, values) {
  lines.push(`${key}:`);
  for (const value of values) lines.push(`  - ${yamlString(value)}`);
}

function appendYamlModes(lines, modes) {
  lines.push("modes:");
  for (const [name, mode] of Object.entries(modes)) {
    lines.push(`  ${name}:`);
    lines.push(`    roles: [${mode.roles.map(yamlString).join(", ")}]`);
    lines.push(`    energy: ${yamlString(mode.energy)}`);
  }
}

function requireNonblankString(projectId, field, value) {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${projectId}: ${field} must be a non-empty string`);
  }
}

function requireStringList(projectId, field, value) {
  if (
    !Array.isArray(value)
    || value.length === 0
    || value.some((item) => typeof item !== "string" || !item.trim())
  ) {
    throw new Error(`${projectId}: ${field} must be a non-empty string array`);
  }
  if (new Set(value).size !== value.length) {
    throw new Error(`${projectId}: ${field} must not contain duplicate values`);
  }
}

function requireEnumList(projectId, field, values, allowed) {
  requireStringList(projectId, field, values);
  for (const value of values) {
    if (!allowed.has(value)) throw new Error(`${projectId}: invalid ${field} value ${value}`);
  }
}

export function validateCodropsStyleMetadata({ catalog, styleMetadata }) {
  if (!catalog || !Array.isArray(catalog.projects)) {
    throw new Error("Codrops catalog projects are required");
  }
  if (!styleMetadata || styleMetadata.schema_version !== 1 || !styleMetadata.projects) {
    throw new Error("Codrops style metadata schema_version 1 is required");
  }
  const catalogIds = catalog.projects.map((project) => project.id);
  if (catalogIds.some((id) => typeof id !== "string" || !id)) {
    throw new Error("Codrops catalog project IDs must be non-empty strings");
  }
  if (new Set(catalogIds).size !== catalogIds.length) {
    throw new Error("Codrops catalog contains duplicate project IDs");
  }
  const styleIds = Object.keys(styleMetadata.projects);
  const missing = catalogIds.filter((id) => !Object.hasOwn(styleMetadata.projects, id));
  const extra = styleIds.filter((id) => !catalogIds.includes(id));
  if (missing.length) throw new Error(`missing style metadata: ${missing.join(", ")}`);
  if (extra.length) throw new Error(`extra style metadata: ${extra.join(", ")}`);

  for (const projectId of catalogIds) {
    const style = styleMetadata.projects[projectId];
    if (!style || typeof style !== "object" || Array.isArray(style)) {
      throw new Error(`${projectId}: style metadata must be an object`);
    }
    const allowedFields = new Set([
      ...CODROPS_STYLE_SCALARS,
      ...CODROPS_STYLE_LISTS,
      ...(projectId === "KineticImages" ? ["modes"] : []),
    ]);
    const unexpectedFields = Object.keys(style).filter((field) => !allowedFields.has(field));
    if (unexpectedFields.length) {
      throw new Error(`${projectId}: unexpected style metadata field ${unexpectedFields.join(", ")}`);
    }
    for (const field of CODROPS_STYLE_SCALARS) {
      requireNonblankString(projectId, field, style[field]);
    }
    for (const field of CODROPS_STYLE_LISTS) {
      requireStringList(projectId, field, style[field]);
    }
    requireEnumList(projectId, "structural_roles", style.structural_roles, CODROPS_STRUCTURAL_ROLES);
    requireEnumList(projectId, "motion_functions", style.motion_functions, CODROPS_MOTION_FUNCTIONS);
    if (!CODROPS_RHYTHM_ENERGIES.has(style.rhythm_energy)) {
      throw new Error(`${projectId}: invalid rhythm_energy value ${style.rhythm_energy}`);
    }
    if (!CODROPS_INFORMATION_DENSITIES.has(style.information_density)) {
      throw new Error(`${projectId}: invalid information_density value ${style.information_density}`);
    }
    if (!CODROPS_FRAME_RELATIONSHIPS.has(style.frame_relationship)) {
      throw new Error(`${projectId}: invalid frame_relationship value ${style.frame_relationship}`);
    }
    if (!CODROPS_COLOR_TENDENCIES.has(style.color_tendency)) {
      throw new Error(`${projectId}: invalid color_tendency value ${style.color_tendency}`);
    }
    if (!style.intent_keywords.some((value) => /[A-Za-z]/.test(value))) {
      throw new Error(`${projectId}: intent_keywords requires an English phrase`);
    }
    if (!style.intent_keywords.some((value) => /\p{Script=Han}/u.test(value))) {
      throw new Error(`${projectId}: intent_keywords requires a Chinese phrase`);
    }
    if (projectId === "KineticImages") {
      if (!style.modes || typeof style.modes !== "object" || Array.isArray(style.modes)) {
        throw new Error("KineticImages: modes must be an object");
      }
      for (const [modeName, mode] of Object.entries(style.modes)) {
        requireEnumList(projectId, `modes.${modeName}.roles`, mode?.roles, CODROPS_STRUCTURAL_ROLES);
        requireNonblankString(projectId, `modes.${modeName}.energy`, mode?.energy);
      }
    } else if (Object.hasOwn(style, "modes")) {
      throw new Error(`${projectId}: modes is only supported for KineticImages`);
    }
  }
  return { projects: [...catalogIds].sort(compareNames) };
}

export function buildCodropsManifest({ catalogProject, conversion, style }) {
  const projectId = catalogProject?.id || "unknown Codrops project";
  if (!conversion || conversion.project_id !== catalogProject?.id) {
    throw new Error(`${projectId}: catalog and conversion project IDs do not match`);
  }
  const defaults = Array.isArray(conversion.variants)
    ? conversion.variants.filter((variant) => variant.name === "index")
    : [];
  if (defaults.length !== 1) throw new Error(`${projectId}: expected exactly one index variant`);
  const index = defaults[0];
  requireNonblankString(projectId, "composition_id", index.composition_id);
  requireNonblankString(projectId, "entry", index.output);
  const durationMs = Number(index.duration_s) * 1000;
  if (!Number.isInteger(durationMs)) {
    throw new Error(`${projectId}: duration must resolve to integer milliseconds`);
  }
  if (catalogProject.license?.type !== "MIT") {
    throw new Error(`${projectId}: manifest requires MIT license evidence`);
  }
  if (!/^[0-9a-f]{40}$/i.test(catalogProject.source_commit || "")) {
    throw new Error(`${projectId}: source_commit must be a 40-character commit`);
  }
  requireNonblankString(projectId, "title", catalogProject.title);
  requireNonblankString(projectId, "source_url", catalogProject.source_url);
  const sourceUrl = catalogProject.source_url.replace(/\/+$/, "");
  const owner = new URL(sourceUrl).pathname.split("/").filter(Boolean)[0];
  if (!owner) throw new Error(`${projectId}: source_url must contain a GitHub owner`);
  const kinetic = projectId === "KineticImages";
  const lines = [
    "spec_version: 1",
    `id: ${yamlString(index.composition_id)}`,
    `name: ${yamlString(catalogProject.title)}`,
    `description: ${yamlString(style.description)}`,
    "surfaces: [video]",
    `category: ${yamlString(style.category)}`,
    kinetic ? "tech: [three.js, webgl, js]" : "tech: [html, css, js]",
    "canvas: [video]",
    "target: [fullscreen]",
    `intent: ${yamlString(style.category)}`,
    kinetic ? "runtime: [three.js, webgl, js]" : "runtime: [css, js]",
    "export: [skill, html]",
    "dependencies: []",
  ];
  for (const field of ["tags", "intent_keywords", "best_for", "avoid_when"]) {
    appendYamlList(lines, field, style[field]);
  }
  for (const field of ["structural_roles", "motion_functions", "visual_language", "mechanisms"]) {
    appendYamlList(lines, field, style[field]);
  }
  for (const field of [
    "rhythm_energy", "information_density", "frame_relationship", "color_tendency", "style_rationale",
  ]) {
    lines.push(`${field}: ${yamlString(style[field])}`);
  }
  if (kinetic) appendYamlModes(lines, style.modes);
  lines.push(
    "restraint:",
    "  max_per_view: 1",
    `  notes: ${yamlString(kinetic ? KINETIC_RESTRAINT : GENERIC_RESTRAINT)}`,
    "motion:",
    `  duration_ms: ${durationMs}`,
    "  easing: linear",
    "  reduced_motion: freeze",
    "  gpu_safe: true",
    `entry: ${yamlString(index.output)}`,
    "implementations:",
    `  - tech: ${kinetic ? "three.js" : "js"}`,
    "    files: [\"index/index.html\", \"index/hf-recipe.js\", \"index/hf-adapter.js\"]",
    `    usage: ${yamlString(kinetic ? KINETIC_USAGE : GENERIC_USAGE)}`,
    "license:",
    "  spdx: MIT",
    `  upstream: ${yamlString(`${sourceUrl}/tree/${catalogProject.source_commit}`)}`,
    "  attribution_required: true",
    "author:",
    `  name: ${yamlString(owner)}`,
    `  url: ${yamlString(`https://github.com/${owner}`)}`,
    "version: 0.1.0",
  );
  return `${lines.join("\n")}\n`;
}

function matchingReceiptProvenance(project, conversion) {
  for (const field of ["demo_url", "article_url", "source_url", "source_commit"]) {
    if (conversion[field] !== undefined && conversion[field] !== project[field]) {
      throw new Error(`${project.id}: catalog and receipt ${field} do not match`);
    }
  }
  if (
    conversion.license !== undefined
    && JSON.stringify(conversion.license) !== JSON.stringify(project.license)
  ) {
    throw new Error(`${project.id}: catalog and receipt license do not match`);
  }
}

async function validateCodropsLicenseEvidence(root, project) {
  const license = project.license || {};
  if (license.type !== "MIT") throw new Error(`${project.id}: MIT license evidence is required`);
  if (license.file || license.sha256) {
    if (!license.file || !/^[0-9a-f]{64}$/i.test(license.sha256 || "")) {
      throw new Error(`${project.id}: license file evidence requires file and SHA-256`);
    }
    const licensePath = path.join(root, project.local_directory, license.file);
    if (!(await fileExists(licensePath))) throw new Error(`${project.id}: missing license file ${license.file}`);
    const actual = sha256(await readFile(licensePath));
    if (actual !== license.sha256.toLowerCase()) throw new Error(`${project.id}: license SHA-256 mismatch`);
    return;
  }
  if (
    license.evidence !== "codrops-site-license"
    || license.url !== "https://tympanus.net/codrops/licensing/"
  ) {
    throw new Error(`${project.id}: unsupported MIT license evidence`);
  }
}

export async function writeCodropsManifests(importsRoot) {
  const root = path.resolve(importsRoot);
  const [catalog, styleMetadata] = await Promise.all([
    readFile(path.join(root, "SOURCE_CATALOG.json"), "utf8").then(JSON.parse),
    readFile(path.join(root, "STYLE_METADATA.json"), "utf8").then(JSON.parse),
  ]);
  validateCodropsStyleMetadata({ catalog, styleMetadata });
  const pending = [];
  const recipeIds = new Set();
  for (const project of [...catalog.projects].sort((left, right) => compareNames(left.id, right.id))) {
    if (project.local_directory !== project.id) {
      throw new Error(`${project.id}: local_directory must equal the project ID`);
    }
    const projectDir = path.join(root, project.local_directory);
    const receiptPath = path.join(projectDir, "hyperframes", "conversion.json");
    if (!(await fileExists(receiptPath))) throw new Error(`${project.id}: missing conversion receipt`);
    const conversion = JSON.parse(await readFile(receiptPath, "utf8"));
    matchingReceiptProvenance(project, conversion);
    await validateCodropsLicenseEvidence(root, project);
    const defaults = Array.isArray(conversion.variants)
      ? conversion.variants.filter((variant) => variant.name === "index")
      : [];
    if (defaults.length !== 1) throw new Error(`${project.id}: expected exactly one index variant`);
    for (const relative of [defaults[0].output, "index/hf-recipe.js", "index/hf-adapter.js"]) {
      if (!(await fileExists(path.join(projectDir, "hyperframes", ...relative.split("/"))))) {
        throw new Error(`${project.id}: missing implementation file ${relative}`);
      }
    }
    const yaml = buildCodropsManifest({
      catalogProject: project,
      conversion,
      style: styleMetadata.projects[project.id],
    });
    if (recipeIds.has(defaults[0].composition_id)) {
      throw new Error(`${project.id}: duplicate recipe ID ${defaults[0].composition_id}`);
    }
    recipeIds.add(defaults[0].composition_id);
    pending.push({
      project_id: project.id,
      recipe_id: defaults[0].composition_id,
      path: path.join(projectDir, "recipe.motion.yaml"),
      yaml,
    });
  }
  for (const manifest of pending) await writeFile(manifest.path, manifest.yaml, "utf8");
  return {
    projects: pending.length,
    manifests: pending.map(({ project_id, recipe_id, path: manifestPath }) => ({
      project_id,
      recipe_id,
      path: manifestPath,
    })),
  };
}

async function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const rootArg = process.argv.slice(2).find((arg) => !arg.startsWith("--"));
  const importsRoot = path.resolve(
    rootArg
      || path.join(scriptDir, "..", "recipes", "codrops"),
  );
  if (process.argv.includes("--rewrite-existing")) {
    const result = await rewriteExistingCodropsPaths(importsRoot);
    process.stdout.write(`rewrote ${result.projects} Codrops projects / ${result.variants} variants / ${result.files} files\n`);
    return;
  }
  if (process.argv.includes("--write-manifests")) {
    const result = await writeCodropsManifests(importsRoot);
    process.stdout.write(`wrote ${result.projects} Codrops recipe manifests\n`);
    return;
  }
  const receipts = await convertAllCodrops({ importsRoot });
  const variants = receipts.reduce((count, receipt) => count + receipt.variants.length, 0);
  await writeCodropsManifests(importsRoot);
  process.stdout.write(`converted ${receipts.length} Codrops projects / ${variants} variants\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}
