import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

import {
  auditConvertedRecipes,
  convertRecipe,
  discoverRecipes,
  writeLibraryAttribution,
} from "../scripts/convert_motion_anything_recipes.mjs";

async function fixtureRecipe(root, surface, id, manifest, files) {
  const recipeDir = path.join(root, surface, id);
  await mkdir(recipeDir, { recursive: true });
  await writeFile(path.join(recipeDir, "recipe.motion.yaml"), manifest, "utf8");
  for (const [relativePath, contents] of Object.entries(files)) {
    const target = path.join(recipeDir, relativePath);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, contents, "utf8");
  }
  return recipeDir;
}

test("discovers manifest recipes and excludes reference-only imported files", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-recipes-"));
  await fixtureRecipe(
    root,
    "web",
    "pulse",
    "id: pulse\nruntime: [css]\nentry: preview.html\n",
    { "preview.html": "<!doctype html><body><div>Pulse</div></body>" },
  );
  await mkdir(path.join(root, "imported", "reference-card"), { recursive: true });
  await writeFile(path.join(root, "imported", "reference-card", "Card.jsx"), "export default null;", "utf8");

  const recipes = await discoverRecipes(root);

  assert.deepEqual(recipes.map((recipe) => recipe.id), ["pulse"]);
  assert.equal(recipes[0].surface, "web");
});

test("converts JavaScript recipes to a deterministic hf-seek composition and preserves credit comments", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-js-"));
  const recipeDir = await fixtureRecipe(
    root,
    "web",
    "particles",
    [
      "id: particles",
      "runtime: [js]",
      "entry: preview.html",
      "motion:",
      "  duration_ms: 1800",
      "implementations:",
      "  - tech: js",
      "    files: [particles.js]",
      "",
    ].join("\n"),
    {
      "preview.html": '<!doctype html><html><body><canvas id="fx"></canvas><script src="particles.js"></script></body></html>',
      "particles.js": "/* Credit: Original Artist */\nrequestAnimationFrame(function tick(t) { Math.random(); requestAnimationFrame(tick); });\n",
      "SKILL.md": "# Particles\n",
    },
  );

  const receipt = await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");
  const source = await readFile(path.join(outputDir, "source", "particles.js"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");

  assert.equal(receipt.recipe_id, "particles");
  assert.match(html, /data-composition-id="particles"/);
  assert.match(html, /data-duration="6"/);
  assert.match(html, /hf-adapter\.js/);
  assert.match(source, /Credit: Original Artist/);
  assert.match(adapter, /hf-seek/);
  assert.match(adapter, /seed/i);
});

test("copies source-level license and provenance into each converted recipe", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-shared-license-"));
  const sourceRoot = path.join(root, "canvas-confetti");
  await mkdir(sourceRoot, { recursive: true });
  await writeFile(path.join(sourceRoot, "LICENSE.canvas-confetti"), "ISC License fixture\n", "utf8");
  await writeFile(
    path.join(sourceRoot, "SOURCE.json"),
    `${JSON.stringify({ name: "canvas-confetti", version: "1.9.4" }, null, 2)}\n`,
    "utf8",
  );
  const recipeDir = await fixtureRecipe(
    root,
    "canvas-confetti",
    "confetti-center-burst",
    "id: confetti-center-burst\nruntime: [js]\nentry: preview.html\n",
    { "preview.html": "<!doctype html><body><canvas></canvas></body>" },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes", "source");

  assert.equal(await readFile(path.join(outputDir, "LICENSE.canvas-confetti"), "utf8"), "ISC License fixture\n");
  assert.deepEqual(
    JSON.parse(await readFile(path.join(outputDir, "SOURCE.json"), "utf8")),
    { name: "canvas-confetti", version: "1.9.4" },
  );
});

test("removes visible demo chrome from converted output while preserving the source preview", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-demo-chrome-"));
  const recipeDir = await fixtureRecipe(
    root,
    "web",
    "clean-overlay",
    "id: clean-overlay\nruntime: [js]\nentry: preview.html\n",
    {
      "preview.html": [
        "<!doctype html><body>",
        '<div class="badge">motion-anything - entrance</div>',
        '<main id="effect">Effect content</main>',
        '<p class="hint">Demo usage guidance.</p>',
        '<div class="cap">motion-anything - ambient</div>',
        '<button class="replay" onclick="location.reload()">Replay</button>',
        "<script>window.effectReady = true;</script>",
        "</body>",
      ].join("\n"),
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");
  const sourcePreview = await readFile(path.join(outputDir, "source", "preview.html"), "utf8");

  assert.match(html, /Effect content/);
  assert.doesNotMatch(html, /motion-anything/);
  assert.doesNotMatch(html, /Demo usage guidance/);
  assert.doesNotMatch(html, />Replay</);
  assert.doesNotMatch(adapter, /motion-anything/);
  assert.doesNotMatch(adapter, /Demo usage guidance/);
  assert.doesNotMatch(adapter, />Replay</);
  assert.match(sourcePreview, /motion-anything/);
  assert.match(sourcePreview, /Demo usage guidance/);
  assert.match(sourcePreview, />Replay</);
});

test("marks bottom-sheet travel as intentional layout overflow", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-sheet-"));
  const recipeDir = await fixtureRecipe(
    root,
    "app",
    "bottom-sheet",
    "id: bottom-sheet\nruntime: [css, js]\nentry: preview.html\n",
    {
      "preview.html": [
        "<!doctype html><style>.ui-sheet{transform:translateY(100%)}</style>",
        '<div class="ui-phone"><div class="ui-sheet"></div></div>',
        "<script>setTimeout(()=>document.querySelector('.ui-phone').classList.add('open'),300)</script>",
      ].join(""),
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const html = await readFile(path.join(recipeDir, "hyperframes", "index.html"), "utf8");

  assert.match(html, /class="ui-sheet" data-layout-allow-overflow/);
});

test("materializes pseudo-element-only pulse motion as seek-visible DOM", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-pulse-"));
  const recipeDir = await fixtureRecipe(
    root,
    "web",
    "attention-pulse",
    "id: attention-pulse\nruntime: [css]\nentry: preview.html\n",
    {
      "preview.html": [
        "<!doctype html><head><style>",
        "[data-pulse]::after{content:'';animation:ma-pulse 2s ease-out infinite}",
        "@keyframes ma-pulse{from{opacity:.5;transform:scale(1)}to{opacity:0;transform:scale(1.5)}}",
        "</style></head><body>",
        '<button data-pulse>Start</button>',
        '<span data-pulse style="--pulse-color:#e0683c"></span>',
        "</body>",
      ].join(""),
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");

  assert.equal((html.match(/class="hf-pulse-ring"/g) || []).length, 2);
  assert.equal((adapter.match(/class=\\"hf-pulse-ring\\"/g) || []).length, 2);
  assert.match(html, /\[data-pulse\]::after\s*\{\s*display:\s*none\s*!important/);
  assert.match(html, /\.hf-pulse-ring[\s\S]*opacity:\s*1[\s\S]*animation:\s*hf-ma-pulse 2s cubic-bezier\(0\.16, 1, 0\.3, 1\) infinite/);
  assert.match(html, /@keyframes hf-ma-pulse[\s\S]*color:\s*color-mix[\s\S]*color:\s*transparent/);
});

test("repeated seeks clean up resources and restore deterministic visual time", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-lifecycle-"));
  const recipeDir = await fixtureRecipe(
    root,
    "web",
    "canvas-lifecycle",
    "id: canvas-lifecycle\nruntime: [css, js]\nentry: preview.html\nmotion:\n  duration_ms: 300\n",
    {
      "preview.html": [
        "<!doctype html><body><script>",
        "const canvas = document.createElement('canvas');",
        "document.body.appendChild(canvas);",
        "window.contexts.push(canvas.getContext('webgl2', { alpha: true }));",
        "new ResizeObserver(() => window.resizeCallbacks++).observe(canvas);",
        "new IntersectionObserver((entries) => { if (entries[0].isIntersecting) window.intersections++; }).observe(canvas);",
        "window.addEventListener('recipe-event', () => {});",
        "setTimeout(() => window.delayedCallbacks++, 600);",
        "</script></body>",
      ].join("\n"),
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const recipe = await readFile(path.join(outputDir, "hf-recipe.js"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");
  const contexts = [];
  class FakeCSSAnimation {
    constructor() {
      this.currentTime = null;
      this.pauseCalls = 0;
    }
    pause() { this.pauseCalls += 1; }
  }
  const animation = new FakeCSSAnimation();
  let removalsWithPatchedPrototype = 0;
  let nativeResizeObservers = 0;
  let nativeIntersectionObservers = 0;

  class FakeEventTarget {
    constructor() {
      this.listeners = new Map();
    }
    addEventListener(type, listener) {
      const listeners = this.listeners.get(type) || [];
      listeners.push(listener);
      this.listeners.set(type, listeners);
    }
    removeEventListener(type, listener) {
      if (FakeEventTarget.prototype.addEventListener !== nativeAdd) {
        removalsWithPatchedPrototype += 1;
      }
      this.listeners.set(type, (this.listeners.get(type) || []).filter((item) => item !== listener));
    }
    dispatchEvent(event) {
      for (const listener of [...(this.listeners.get(event.type) || [])]) listener.call(this, event);
    }
  }
  const nativeAdd = FakeEventTarget.prototype.addEventListener;

  class FakeCanvas extends FakeEventTarget {
    getBoundingClientRect() {
      return { x: 0, y: 0, width: 1920, height: 1080, top: 0, right: 1920, bottom: 1080, left: 0 };
    }
    getContext(kind, options) {
      const context = {
        kind,
        options,
        lost: false,
        getExtension(name) {
          if (name !== "WEBGL_lose_context") return null;
          return { loseContext: () => { context.lost = true; } };
        },
      };
      contexts.push(context);
      return context;
    }
  }

  class NativeResizeObserver {
    constructor() { nativeResizeObservers += 1; }
    observe() {}
    disconnect() {}
  }
  class NativeIntersectionObserver {
    constructor() { nativeIntersectionObservers += 1; }
    observe() {}
    disconnect() {}
  }

  const browser = new FakeEventTarget();
  const body = new FakeEventTarget();
  body.appendChild = () => {};
  Object.defineProperty(body, "innerHTML", { set() {} });
  Object.assign(browser, {
    window: browser,
    globalThis: browser,
    EventTarget: FakeEventTarget,
    HTMLCanvasElement: FakeCanvas,
    CSSAnimation: FakeCSSAnimation,
    CSSTransition: class {},
    ResizeObserver: NativeResizeObserver,
    IntersectionObserver: NativeIntersectionObserver,
    CustomEvent: class {
      constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
    },
    document: {
      body,
      createElement(tag) { return tag === "canvas" ? new FakeCanvas() : new FakeEventTarget(); },
      getAnimations() { return [animation]; },
    },
    contexts: [],
    resizeCallbacks: 0,
    intersections: 0,
    delayedCallbacks: 0,
  });

  vm.runInNewContext(recipe, browser);
  vm.runInNewContext(adapter, browser);
  assert.equal(typeof browser.__hf.seek, "function");
  assert.equal(browser.__hf.duration, 6);
  assert.equal(browser.document.getAnimations().length, 0);
  browser.__hf.seek(1);
  browser.__hf.seek(2);

  assert.equal(contexts.length, 3);
  assert.deepEqual(contexts.map((context) => context.options.preserveDrawingBuffer), [true, true, true]);
  assert.deepEqual(contexts.map((context) => context.lost), [true, true, false]);
  assert.equal(browser.resizeCallbacks, 3);
  assert.equal(browser.intersections, 3);
  assert.equal(nativeResizeObservers, 0);
  assert.equal(nativeIntersectionObservers, 0);
  assert.equal(removalsWithPatchedPrototype, 0);
  assert.equal(browser.delayedCallbacks, 2);
  assert.equal(animation.pauseCalls, 3);
  assert.equal(animation.currentTime, 2000);
});

test("keeps Lottie JSON unchanged and registers a local non-autoplay player", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-lottie-"));
  await mkdir(path.join(root, "lottie", "_runtime"), { recursive: true });
  await writeFile(path.join(root, "lottie", "_runtime", "lottie.min.js"), "window.lottie = {};", "utf8");
  const animation = JSON.stringify({
    fr: 30,
    ip: 0,
    op: 60,
    assets: [{ id: "hidden-icon", w: 380, h: 380, u: "images/", p: "icon.png" }],
    layers: [{ refId: "hidden-icon", hd: true }],
  });
  const recipeDir = await fixtureRecipe(
    root,
    "lottie",
    "favorite",
    [
      "id: favorite",
      "runtime: [lottie]",
      "entry: preview.html",
      "implementations:",
      "  - tech: lottie",
      "    files: [animation.json]",
      "",
    ].join("\n"),
    {
      "preview.html": "<!doctype html><head><style>#lottie { width:220px; height:220px; }</style></head><body><div id=\"lottie\"></div><script src=\"../_runtime/lottie.min.js\"></script></body>",
      "animation.json": animation,
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const copied = await readFile(path.join(outputDir, "source", "animation.json"), "utf8");
  const placeholder = await readFile(path.join(outputDir, "source", "images", "icon.png"));
  const previewRuntime = await readFile(path.join(outputDir, "_runtime", "lottie.min.js"), "utf8");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");

  assert.equal(copied, animation);
  assert.deepEqual([...placeholder.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(previewRuntime, "window.lottie = {};");
  assert.match(html, /src="_runtime\/lottie\.min\.js"/);
  assert.doesNotMatch(html, /src="source\/_runtime\/lottie\.min\.js"/);
  assert.match(html, /window\.__hf\s*=\s*\{/);
  assert.match(html, /seek\(time\)\s*\{\s*seekLottie\(time\)/);
  assert.match(html, /addEventListener\("hf-seek",\s*\(event\)\s*=>\s*seekLottie\(event\.detail\.time\)\)/);
  assert.match(html, /pendingTime\s*%\s*nativeDuration/);
  assert.match(html, /getRegisteredAnimations\s*=\s*\(\)\s*=>/);
  assert.doesNotMatch(html, /window\.__hfLottie\.push/);
  assert.match(html, /autoplay:\s*false/);
  assert.match(html, /loop:\s*false/);
  assert.match(html, /#lottie\s*\{\s*width:220px;\s*height:220px;/);
  assert.doesNotMatch(html, /#lottie\s*\{\s*width:\s*100%;\s*height:\s*100%;/);
  assert.doesNotMatch(html, /https?:\/\//);
});

test("converts inline SVG SMIL recipes to absolute-time HyperFrames seeks", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-svg-smil-"));
  const recipeDir = await fixtureRecipe(
    root,
    "line-md",
    "line-md-gift",
    [
      "id: line-md-gift",
      "runtime: [svg-smil]",
      "entry: preview.html",
      "motion:",
      "  duration_ms: 6000",
      "",
    ].join("\n"),
    {
      "preview.html": [
        "<!doctype html><html><body>",
        '<svg data-native-duration="2.4" viewBox="0 0 24 24">',
        '<path d="M4 9h16v11H4z"><animate attributeName="opacity" values="0;1" dur="2.4s"/></path>',
        "</svg>",
        "</body></html>",
      ].join(""),
      "LICENSE.line-md": "MIT License fixture\n",
    },
  );

  const receipt = await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");
  const events = new Map();
  const seekTimes = [];
  let pauseCalls = 0;
  const svg = {
    dataset: { nativeDuration: "2.4" },
    pauseAnimations() { pauseCalls += 1; },
    setCurrentTime(time) { seekTimes.push(time); },
  };
  const browser = {
    window: null,
    document: { querySelector: (selector) => selector === "svg" ? svg : null },
    addEventListener(type, listener) { events.set(type, listener); },
  };
  browser.window = browser;

  assert.equal(receipt.deterministic_adapter, "svg-smil");
  vm.runInNewContext(adapter, browser);
  browser.__hf.seek(3.25);
  events.get("hf-seek")({ detail: { time: 1.2 } });

  assert.match(html, /data-composition-id="line-md-gift"/);
  assert.match(html, /<svg data-native-duration="2\.4"/);
  assert.deepEqual(seekTimes.map((time) => Number(time.toFixed(3))), [0, 0.85, 1.2]);
  assert.equal(pauseCalls, 3);
});

test("converts Three.js recipes to local absolute-time hf-seek compositions", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-three-"));
  const recipeDir = await fixtureRecipe(
    root,
    "web",
    "kinetic-images",
    [
      "id: kinetic-images",
      "runtime: [three]",
      "entry: preview.html",
      "motion:",
      "  duration_ms: 6000",
      "",
    ].join("\n"),
    {
      "preview.html": '<!doctype html><canvas id="three-layer"></canvas><script type="module" src="scene.js"></script>',
      "scene.js": "export async function createRecipe() { return { renderAt() {} }; }\n",
      "assets/paper.glb": "glb fixture",
      "LICENSE.codrops": "MIT License fixture\n",
      "_runtime/three/three.module.js": "export class WebGLRenderer {}\n",
      "_runtime/three/addons/loaders/GLTFLoader.js": "export class GLTFLoader {}\n",
    },
  );

  const receipt = await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");
  const adapter = await readFile(path.join(outputDir, "hf-adapter.js"), "utf8");
  const copiedModel = await readFile(path.join(outputDir, "source", "assets", "paper.glb"), "utf8");
  const copiedRuntime = await readFile(path.join(outputDir, "_runtime", "three", "three.module.js"), "utf8");

  assert.equal(receipt.deterministic_adapter, "three");
  assert.match(html, /data-composition-id="kinetic-images"/);
  assert.match(html, /data-scene-mode="showcase"/);
  assert.match(html, /type="importmap"/);
  assert.match(html, /type="module" src="hf-recipe\.js"/);
  assert.doesNotMatch(html, /https?:\/\//);
  assert.equal(copiedModel, "glb fixture");
  assert.match(copiedRuntime, /WebGLRenderer/);

  const events = new Map();
  const rendered = [];
  const browser = {
    window: null,
    CustomEvent: class {
      constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
    },
    addEventListener(type, listener) { events.set(type, listener); },
  };
  browser.window = browser;
  vm.runInNewContext(adapter, browser);
  browser.__hfThreeRegister((time) => rendered.push(time));
  browser.__hf.seek(4.25);
  browser.__hf.seek(1.5);

  assert.deepEqual(rendered, [0, 4.25, 1.5]);
  assert.equal(browser.__hfThreeTime, 1.5);
});

test("writes one library attribution with motion-anything and original author credits", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "graphic-motion-attribution-"));
  const upstream = [
    "# ATTRIBUTION.md - third-party sources & credits",
    "",
    "- **Original Artist** - shader implementation.",
    "",
  ].join("\n");

  const target = await writeLibraryAttribution({
    recipesRoot: root,
    sourceRevision: "0123456789abcdef",
    upstreamAttribution: upstream,
  });
  const contents = await readFile(target, "utf8");

  assert.match(contents, /motion-anything/);
  assert.match(contents, /https:\/\/github\.com\/nexu-io\/motion-anything/);
  assert.match(contents, /0123456789abcdef/);
  assert.match(contents, /Original Artist/);
});

test("the vendored library exposes the curated sticker recipes plus every Line MD name", async () => {
  const recipesRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "recipes",
  );

  const recipes = await discoverRecipes(recipesRoot);
  const kineticImages = recipes.find((recipe) => recipe.id === "kinetic-images");
  const mojsEffect = await readFile(
    path.join(recipesRoot, "mojs", "mojs-shockwave", "hyperframes", "source", "effect.js"),
    "utf8",
  );
  const stickerCounts = Object.fromEntries(
    ["canvas-confetti", "mojs", "line-md", "meteocons", "tsparticles"]
      .map((surface) => [surface, recipes.filter((recipe) => recipe.surface === surface).length]),
  );

  assert.equal(recipes.length, 1477);
  assert.equal(new Set(recipes.map((recipe) => recipe.id)).size, 1477);
  assert.deepEqual(stickerCounts, {
    "canvas-confetti": 10,
    mojs: 10,
    "line-md": 1222,
    meteocons: 12,
    tsparticles: 4,
  });
  for (const id of [
    "line-md-sunny-outline",
    "line-md-sunny-outline-loop",
    "line-md-sunny-outline-twotone",
    "line-md-sunny-outline-twotone-loop",
  ]) {
    assert.ok(recipes.some((recipe) => recipe.id === id), `missing Line MD alias ${id}`);
  }
  assert.ok(!recipes.some((recipe) => recipe.id === "confetti-left-stream"));
  assert.ok(!recipes.some((recipe) => recipe.id === "mojs-double-shockwave"));
  assert.equal(kineticImages?.surface, "codrops");
  assert.match(mojsEffect, /const shiftX = x - 960;/);
  assert.match(mojsEffect, /const shiftY = y - 540;/);
});

test("all converted recipes pass the static HyperFrames artifact audit", async () => {
  const recipesRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "recipes",
  );

  const audit = await auditConvertedRecipes(recipesRoot);

  assert.equal(audit.recipe_count, 1477);
  assert.equal(audit.converted_count, 1477);
  assert.ok(audit.preserved_credit_comments > 0);
  assert.deepEqual(audit.errors, []);
});
