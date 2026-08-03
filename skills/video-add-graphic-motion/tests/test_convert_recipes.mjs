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
  const animation = '{"fr":30,"ip":0,"op":60,"layers":[]}';
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
      "preview.html": "<!doctype html><head><style>#lottie { width:220px; height:220px; }</style></head><body><div id=\"lottie\"></div></body>",
      "animation.json": animation,
    },
  );

  await convertRecipe({ recipesRoot: root, recipeDir });
  const outputDir = path.join(recipeDir, "hyperframes");
  const copied = await readFile(path.join(outputDir, "source", "animation.json"), "utf8");
  const html = await readFile(path.join(outputDir, "index.html"), "utf8");

  assert.equal(copied, animation);
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

test("the vendored library exposes exactly 218 selectable recipes", async () => {
  const recipesRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "recipes",
  );

  const recipes = await discoverRecipes(recipesRoot);

  assert.equal(recipes.length, 218);
  assert.equal(new Set(recipes.map((recipe) => recipe.id)).size, 218);
});

test("all converted recipes pass the static HyperFrames artifact audit", async () => {
  const recipesRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "recipes",
  );

  const audit = await auditConvertedRecipes(recipesRoot);

  assert.equal(audit.recipe_count, 218);
  assert.equal(audit.converted_count, 218);
  assert.ok(audit.preserved_credit_comments > 0);
  assert.deepEqual(audit.errors, []);
});
