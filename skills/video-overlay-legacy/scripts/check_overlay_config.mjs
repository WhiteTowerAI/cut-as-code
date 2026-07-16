import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { titleOverlayConfig } from "../examples/overlay-config.ts";
import {
  titleOverlayPresets,
  titleOverlayThemes,
} from "../examples/overlay-presets.ts";
import { resolveTitleOverlayStyle } from "../examples/overlay-style-resolver.ts";

const fail = (message) => {
  throw new Error(`[video-overlay] ${message}`);
};

const isPlainObject = (value) =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const validateConfig = (config) => {
  if (config.schemaVersion !== "title-overlay.v1") {
    fail("schemaVersion must be title-overlay.v1");
  }

  if (!config.source?.videoPath) {
    fail("source.videoPath is required");
  }
  if (!config.source?.sourceMetaPath) {
    fail("source.sourceMetaPath is required");
  }

  if (!config.title || typeof config.title.text !== "string" || config.title.text.trim() === "") {
    fail("missing title text");
  }
  if (!config.title.source || !["manual", "video-to-shorts"].includes(config.title.source.type)) {
    fail("title.source must be manual or video-to-shorts");
  }
  if (config.title.source.type === "video-to-shorts" && !config.title.source.selector) {
    fail("video-to-shorts title source requires a selector");
  }

  if (config.style?.preset !== "shorts-title") {
    fail(`unknown title overlay preset: ${config.style?.preset}`);
  }
  if (!Object.hasOwn(titleOverlayThemes, config.style?.theme)) {
    fail(`unknown title overlay theme: ${config.style?.theme}`);
  }
  if (config.style.overrides !== undefined && !isPlainObject(config.style.overrides)) {
    fail("style.overrides must be an object when provided");
  }

  if (!["top", "upper-third", "custom"].includes(config.layout?.position)) {
    fail(`unknown title position: ${config.layout?.position}`);
  }
  if (config.layout.avoidBottomCaptionArea !== true) {
    fail("layout.avoidBottomCaptionArea must be true");
  }
  if (config.layout.position === "custom" && typeof config.layout.customYRatio !== "number") {
    fail("custom position requires layout.customYRatio");
  }

  if (config.visibility?.mode === "first-n-seconds") {
    if (!(typeof config.visibility.durationSec === "number" && config.visibility.durationSec > 0)) {
      fail("first-n-seconds visibility requires positive durationSec");
    }
  } else if (config.visibility?.mode === "time-range") {
    if (!(typeof config.visibility.startTimeSec === "number" && config.visibility.startTimeSec >= 0)) {
      fail("time-range visibility requires non-negative startTimeSec");
    }
    if (!(typeof config.visibility.endTimeSec === "number" && config.visibility.endTimeSec > config.visibility.startTimeSec)) {
      fail("time-range visibility requires endTimeSec greater than startTimeSec");
    }
  } else if (config.visibility?.mode !== "entire") {
    fail(`unknown visibility mode: ${config.visibility?.mode}`);
  }

  if (config.animation?.type !== "none") {
    fail("animation.type must be none in v1");
  }
};

const clone = (value) => JSON.parse(JSON.stringify(value));

assert.deepEqual(Object.keys(titleOverlayPresets), ["shorts-title"]);
assert.equal("shorts-green" in titleOverlayPresets, false);
assert.equal("shorts-yellow" in titleOverlayPresets, false);
assert.equal("shorts-orange" in titleOverlayPresets, false);
assert.deepEqual(Object.keys(titleOverlayThemes).sort(), ["green", "orange", "yellow"].sort());

validateConfig(titleOverlayConfig);

const resolved = resolveTitleOverlayStyle({
  preset: titleOverlayConfig.style.preset,
  theme: titleOverlayConfig.style.theme,
  overrides: titleOverlayConfig.style.overrides,
});

assert.equal(resolved.preset, "shorts-title");
assert.equal(resolved.theme, "green");
assert.equal(resolved.layout.position, "upper-third");
assert.equal(resolved.layout.avoidBottomCaptionArea, true);
assert.equal(resolved.animation.type, "none");
assert.equal(resolved.font.family.includes("Cal_Sans"), true);
assert.equal(resolved.font.color, "#FFFFFF");
assert.equal(resolved.effects.stroke.color, "#000000");
assert.equal(resolved.accent.color, "#20D42C");

assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), title: { ...titleOverlayConfig.title, text: " " } }), /missing title text/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), style: { ...titleOverlayConfig.style, theme: "blue" } }), /unknown title overlay theme/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), visibility: { mode: "first-n-seconds", durationSec: 0 } }), /positive durationSec/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), visibility: { mode: "time-range", startTimeSec: 5, endTimeSec: 5 } }), /endTimeSec greater/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), style: { ...titleOverlayConfig.style, preset: "shorts-green" } }), /unknown title overlay preset/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), layout: { position: "custom", avoidBottomCaptionArea: true } }), /custom position requires/);
assert.throws(() => validateConfig({ ...clone(titleOverlayConfig), layout: { position: "upper-third", avoidBottomCaptionArea: false } }), /avoidBottomCaptionArea must be true/);
assert.throws(() => resolveTitleOverlayStyle({ preset: "shorts-green", theme: "green" }), /unknown title overlay preset/);
assert.throws(() => resolveTitleOverlayStyle({ preset: "shorts-title", theme: "blue" }), /unknown title overlay theme/);

const sourceMetaExample = JSON.parse(readFileSync(new URL("../examples/source-meta.json.example", import.meta.url), "utf8"));
assert.equal(sourceMetaExample.width, 1080);
assert.equal(sourceMetaExample.height, 1920);
assert.equal(sourceMetaExample.height > sourceMetaExample.width, true);

const summary = {
  preset: resolved.preset,
  theme: resolved.theme,
  position: resolved.layout.position,
  yRatio: resolved.layout.yRatio,
  visibility: titleOverlayConfig.visibility.mode,
  animation: resolved.animation.type,
  avoidBottomCaptionArea: resolved.layout.avoidBottomCaptionArea,
  accentColor: resolved.accent.color,
  fontFamily: resolved.font.family,
  fontSizeRatio: resolved.font.sizeRatio,
};

console.log("[video-overlay] config check passed");
console.log(JSON.stringify(summary, null, 2));
