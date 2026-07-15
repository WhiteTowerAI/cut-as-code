import assert from "node:assert/strict";
import {
  captionBackgroundThemeNames,
  captionHighlightThemeNames,
  captionPresetNames,
  captionStrokeThemeNames,
  resolveCaptionStyle,
  resolveKaraoke,
} from "./caption_style_config.mjs";

assert.deepEqual(captionPresetNames, ["clean", "minimal", "social-bold", "pill", "boxed", "stroked", "shorts"]);
assert.deepEqual(captionHighlightThemeNames, ["bright-green", "orange", "yellow"]);
assert.deepEqual(captionBackgroundThemeNames, ["gray", "yellow", "blue", "pink", "green"]);
assert.deepEqual(captionStrokeThemeNames, ["black", "yellow", "blue", "pink", "green"]);

const clean = resolveCaptionStyle({ preset: "clean" });
assert.equal(clean.font.sizeRatio, 0.0416);
assert.equal(clean.layout.paddingBottomRatio, 0.07);

const shortsYellow = resolveCaptionStyle({ preset: "shorts", highlightTheme: "yellow" });
assert.equal(shortsYellow.wordHighlight.activeColor, "#F8F54F");
assert.equal(shortsYellow.font.family.startsWith("Cal_Sans"), true);
assert.equal(shortsYellow.stroke.enabled, true);
assert.equal(resolveCaptionStyle({ preset: "shorts" }).wordHighlight.activeColor, "#21D32E");

const bluePill = resolveCaptionStyle({ preset: "pill", backgroundTheme: "blue" });
assert.equal(bluePill.background.enabled, true);
assert.equal(bluePill.background.color, "#2563EB");

const greenStroke = resolveCaptionStyle({ preset: "stroked", strokeTheme: "green" });
assert.equal(greenStroke.stroke.color, "#16A34A");

assert.equal(resolveKaraoke("auto", shortsYellow), true);
assert.equal(resolveKaraoke("false", shortsYellow), false);
assert.equal(resolveKaraoke("true", clean), true);

assert.equal(resolveCaptionStyle({ preset: "unknown", strict: false }).preset, "clean");
assert.throws(() => resolveCaptionStyle({ preset: "unknown" }), /unknown caption style preset/);

console.log(`[caption-styles] ${captionPresetNames.length} presets`);
console.log(`[caption-styles] ${captionHighlightThemeNames.length} highlight themes`);
console.log(`[caption-styles] ${captionBackgroundThemeNames.length} background themes`);
console.log(`[caption-styles] ${captionStrokeThemeNames.length} stroke themes`);
console.log("[caption-styles] config check passed");
