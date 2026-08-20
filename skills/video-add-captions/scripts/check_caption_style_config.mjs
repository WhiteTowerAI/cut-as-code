import assert from "node:assert/strict";
import {
  captionBackgroundThemeNames,
  captionExpressiveTreatments,
  captionHighlightThemeNames,
  captionPresetNames,
  captionStrokeThemeNames,
  resolveCaptionStyle,
  resolveKaraoke,
} from "./caption_style_config.mjs";
import {
  resolveGallerySelection,
  validSelectionIds,
} from "./caption_interaction_state.mjs";

assert.deepEqual(captionPresetNames, ["clean", "minimal", "social-bold", "pill", "boxed", "stroked", "shorts"]);
assert.deepEqual(captionHighlightThemeNames, ["yellow", "green", "orange", "purple", "blue", "pink"]);
assert.deepEqual(captionBackgroundThemeNames, ["gray", "yellow", "blue", "pink", "green"]);
assert.deepEqual(captionStrokeThemeNames, ["black", "yellow", "blue", "pink", "green"]);

assert.equal(captionExpressiveTreatments.semanticScaleByRole.normal, 1.0);
assert.equal(captionExpressiveTreatments.semanticScaleByRole.keyword, 1.22);
assert.equal(captionExpressiveTreatments.semanticScaleByRole.number, 1.22);
assert.equal(captionExpressiveTreatments.semanticScaleByRole.contrast, 1.22);
assert.equal(captionExpressiveTreatments.heroLine.color, "#F4C542");
assert.equal(captionExpressiveTreatments.heroLine.levels.strong.scale, 1.5);
assert.equal(captionExpressiveTreatments.heroLine.levels.hero.scale, 1.5);
assert.equal(captionExpressiveTreatments.heroLine.canonicalLevel, "hero");

const clean = resolveCaptionStyle({ preset: "clean" });
assert.equal(clean.font.sizeRatio, 0.0416);
assert.equal(clean.layout.paddingBottomRatio, 0.07);

for (const preset of ["clean", "minimal", "social-bold", "pill", "boxed", "stroked"]) {
  assert.equal(resolveCaptionStyle({ preset }).font.family, "system-ui, sans-serif");
}
for (const preset of captionPresetNames) {
  assert.equal(resolveCaptionStyle({ preset }).effects.shadow.strength, "none");
}

const shortsYellow = resolveCaptionStyle({ preset: "shorts", highlightTheme: "yellow" });
assert.equal(shortsYellow.wordHighlight.activeColor, "#F8F54F");
assert.equal(shortsYellow.font.family.startsWith("Cal_Sans"), true);
assert.equal(shortsYellow.font.sizeRatio, 0.035);
assert.equal(shortsYellow.layout.paddingBottomRatio, 0.2);
assert.equal(shortsYellow.stroke.enabled, true);
assert.equal(resolveCaptionStyle({ preset: "shorts" }).wordHighlight.activeColor, "#21D32E");

for (const theme of captionHighlightThemeNames) {
  const resolved = resolveCaptionStyle({ preset: "shorts", highlightTheme: theme });
  assert.equal(resolved.font.sizeRatio, 0.035);
  assert.equal(resolved.wordHighlight.activeColor, resolved.wordHighlight.backgroundColor);
}

const shortsPurple = resolveCaptionStyle({ preset: "shorts", highlightTheme: "purple" });
assert.equal(shortsPurple.wordHighlight.activeColor, "#C084FC");

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

assert.equal(validSelectionIds.length, 25);
assert.equal(new Set(validSelectionIds).size, 25);
assert.deepEqual(resolveGallerySelection("shorts-purple"), {
  response: "shorts-purple",
  choiceId: "shorts-purple",
  skipped: false,
  preset: "shorts",
  highlightTheme: "purple",
  backgroundTheme: null,
  strokeTheme: null,
  karaoke: true,
});
assert.deepEqual(resolveGallerySelection("跳过"), {
  response: "跳过",
  choiceId: "clean",
  skipped: true,
  preset: "clean",
  highlightTheme: null,
  backgroundTheme: null,
  strokeTheme: null,
  karaoke: false,
});
assert.throws(() => resolveGallerySelection("随便"), /must be one exact gallery combination ID/);

console.log(`[caption-styles] ${captionPresetNames.length} presets`);
console.log(`[caption-styles] ${captionHighlightThemeNames.length} highlight themes`);
console.log(`[caption-styles] ${captionBackgroundThemeNames.length} background themes`);
console.log(`[caption-styles] ${captionStrokeThemeNames.length} stroke themes`);
console.log(`[caption-styles] ${validSelectionIds.length} interview choices`);
console.log("[caption-styles] config check passed");
