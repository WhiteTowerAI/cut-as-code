import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { captionBackgroundThemes, captionHighlightThemes, captionStrokeThemes } from "../examples/caption-color-themes.ts";
import { captionPresets } from "../examples/caption-presets.ts";
import { selectedCaptionStyle } from "../examples/caption-style.ts";
import { resolveCaptionStyle } from "../examples/caption-style-resolver.ts";
import { previewConfig } from "../examples/preview-config.ts";

const clean = resolveCaptionStyle({ preset: "clean" });
const backgroundThemes = ["gray", "yellow", "blue", "pink", "green"];
const strokeThemes = ["black", "yellow", "blue", "pink", "green"];

assert.deepEqual(Object.keys(captionBackgroundThemes).sort(), backgroundThemes.sort());
assert.deepEqual(Object.keys(captionStrokeThemes).sort(), strokeThemes.sort());
assert.deepEqual(Object.keys(captionHighlightThemes).sort(), ["bright-green", "orange", "yellow"].sort());
assert.equal("pill-yellow" in captionPresets, false);
assert.equal("boxed-green" in captionPresets, false);
assert.equal("stroked-yellow" in captionPresets, false);
assert.equal("shorts-green" in captionPresets, false);

assert.equal(clean.preset, "clean");
assert.equal(clean.font.color, "#F5F4ED");
assert.equal(clean.font.sizeRatio, 0.0416);
assert.equal(clean.font.lineHeight, 1.32);
assert.equal(clean.background.enabled, false);
assert.equal(clean.background.theme, "gray");
assert.equal(clean.stroke.enabled, false);
assert.equal(clean.wordHighlight.activeColor, "#FF7A45");
assert.equal(clean.wordHighlight.activeScale, 1.12);
assert.equal("karaoke" in captionPresets, false);

const pill = resolveCaptionStyle({ preset: "pill" });
assert.equal(pill.background.enabled, true);
assert.equal(pill.background.shape, "pill");
assert.equal(pill.background.theme, "gray");
assert.equal(pill.background.color, "#111827");
assert.equal(pill.background.opacity, 0.62);
assert.equal(pill.font.sizeRatio, 0.0416);
assert.equal(pill.font.lineHeight, 1.298);
assert.equal(pill.background.paddingYRatio, 0.0126);
assert.equal(pill.stroke.enabled, false);

const boxed = resolveCaptionStyle({ preset: "boxed" });
assert.equal(boxed.background.enabled, true);
assert.equal(boxed.background.shape, "rounded");
assert.equal(boxed.background.theme, "gray");
assert.equal(boxed.background.color, "#111827");
assert.equal(boxed.background.opacity, 0.62);
assert.equal(boxed.font.sizeRatio, 0.0416);
assert.equal(boxed.font.lineHeight, 1.298);
assert.equal(boxed.background.paddingYRatio, 0.0112);
assert.equal(boxed.stroke.enabled, false);

const pillYellow = resolveCaptionStyle({
  preset: "pill",
  overrides: { background: { theme: "yellow" } },
});
assert.equal(pillYellow.preset, "pill");
assert.equal(pillYellow.background.theme, "yellow");
assert.equal(pillYellow.background.shape, "pill");
assert.equal(pillYellow.background.color, captionBackgroundThemes.yellow.background.color);
assert.equal(pillYellow.background.opacity, captionBackgroundThemes.yellow.background.opacity);
assert.equal(pillYellow.font.color, captionBackgroundThemes.yellow.font?.color);
const pillYellowPreview = resolveCaptionStyle({
  preset: "pill",
  overrides: previewConfig.candidates.find((candidate) => candidate.id === "pill-yellow")?.overrides,
});
assert.equal(pillYellowPreview.effects.shadow.strength, "none");
assert.equal(pillYellowPreview.effects.shadow.opacity, 0);

const boxedBlue = resolveCaptionStyle({
  preset: "boxed",
  overrides: { background: { theme: "blue" } },
});
assert.equal(boxedBlue.preset, "boxed");
assert.equal(boxedBlue.background.theme, "blue");
assert.equal(boxedBlue.background.shape, "rounded");
assert.equal(boxedBlue.background.color, captionBackgroundThemes.blue.background.color);

const socialBold = resolveCaptionStyle({ preset: "social-bold" });
assert.equal(socialBold.font.lineHeight, 1.232);
assert.equal(socialBold.wordHighlight.activeScale, 1.14);

const minimal = resolveCaptionStyle({ preset: "minimal" });
assert.equal(minimal.font.lineHeight, 1.342);

const stroked = resolveCaptionStyle({ preset: "stroked" });
assert.equal(stroked.preset, "stroked");
assert.equal(stroked.background.enabled, false);
assert.equal(stroked.font.sizeRatio, 0.0416);
assert.equal(stroked.stroke.enabled, true);
assert.equal(stroked.stroke.theme, "black");
assert.equal(stroked.stroke.color, captionStrokeThemes.black.stroke.color);
assert.equal(stroked.stroke.opacity, captionStrokeThemes.black.stroke.opacity);
assert.equal(stroked.stroke.widthRatio, 0.009);

const strokedYellow = resolveCaptionStyle({
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: { enabled: true, theme: "yellow" },
  },
});
assert.equal(strokedYellow.preset, "stroked");
assert.equal(strokedYellow.background.enabled, false);
assert.equal(strokedYellow.stroke.theme, "yellow");
assert.equal(strokedYellow.stroke.color, captionStrokeThemes.yellow.stroke.color);
assert.equal(strokedYellow.stroke.opacity, captionStrokeThemes.yellow.stroke.opacity);
assert.equal(strokedYellow.stroke.color, "#CA8A04");

const shorts = resolveCaptionStyle({ preset: "shorts" });
assert.equal(shorts.preset, "shorts");
assert.equal(shorts.font.family.includes("Cal_Sans"), true);
assert.equal(shorts.font.sizeRatio, 0.022875);
assert.equal(shorts.background.enabled, false);
assert.equal(shorts.stroke.enabled, true);
assert.equal(shorts.stroke.theme, "black");
assert.equal(shorts.stroke.color, captionStrokeThemes.black.stroke.color);
assert.equal(shorts.stroke.widthRatio, 0.008);
assert.equal(shorts.wordHighlight.enabled, true);
assert.equal(shorts.wordHighlight.activeColor, captionHighlightThemes["bright-green"].wordHighlight.activeColor);
assert.equal(shorts.layout.anchor, "bottom");
assert.equal(shorts.layout.paddingBottomRatio, 0.2);

const shortsOrange = resolveCaptionStyle({
  preset: "shorts",
  overrides: captionHighlightThemes.orange,
});
assert.equal(shortsOrange.wordHighlight.activeColor, "#F8BD6D");

const shortsYellow = resolveCaptionStyle({
  preset: "shorts",
  overrides: captionHighlightThemes.yellow,
});
assert.equal(shortsYellow.wordHighlight.activeColor, "#F8F54F");

assert.equal(selectedCaptionStyle.preset, "clean");
assert.equal(selectedCaptionStyle.karaoke, true);

const fallback = resolveCaptionStyle({ preset: "missing-preset" });
assert.equal(fallback.preset, "clean");

assert.throws(
  () => resolveCaptionStyle({ preset: "missing-preset" }, { unknownPreset: "throw" }),
  /unknown caption style preset/
);

const customized = resolveCaptionStyle({
  preset: "pill",
  overrides: {
    font: { color: "#FFFF00" },
    background: { opacity: 0.25 },
    wordHighlight: { activeColor: "#00FF00" },
  },
});
assert.equal(customized.preset, "pill");
assert.equal(customized.font.color, "#FFFF00");
assert.equal(customized.font.family, captionPresets.pill.font.family);
assert.equal(customized.background.enabled, true);
assert.equal(customized.background.opacity, 0.25);
assert.equal(customized.background.shape, captionPresets.pill.background.shape);
assert.equal(customized.wordHighlight.activeColor, "#00FF00");
assert.equal(customized.wordHighlight.mode, captionPresets.pill.wordHighlight.mode);
assert.equal(customized.effects.shadow.strength, captionPresets.pill.effects.shadow.strength);

const cleanAgain = resolveCaptionStyle({ preset: "clean" });
assert.equal(cleanAgain.font.color, "#F5F4ED");
assert.equal(cleanAgain.background.opacity, 0.48);

const stableKeys = [
  "preset",
  "font",
  "layout",
  "background",
  "effects",
  "stroke",
  "wordHighlight",
  "animation",
];
assert.deepEqual(Object.keys(clean).sort(), stableKeys.sort());

const captionSource = readFileSync(new URL("../examples/Caption.tsx", import.meta.url), "utf8");
assert.match(captionSource, /styleSelection = selectedCaptionStyle/);
assert.match(captionSource, /resolveCaptionStyle\(styleSelection\)/);
assert.match(captionSource, /karaoke \?\? styleSelection\.karaoke \?\? style\.wordHighlight\.enabled/);
assert.match(captionSource, /style\.preset === "shorts"/);
assert.match(captionSource, /staticFile\("fonts\/CalSans-Regular\.ttf"\)/);
assert.match(captionSource, /font-family: "Cal_Sans"/);
assert.match(captionSource, /word\.toUpperCase\(\)/);
assert.doesNotMatch(captionSource, /CREAM|CLAY|DIM|TIMING/);
assert.match(captionSource, /style\.font\.family/);
assert.match(captionSource, /style\.wordHighlight\.activeColor/);
assert.doesNotMatch(captionSource, /style\.wordHighlight\.activeScale/);
assert.doesNotMatch(captionSource, /activeSpacing/);
assert.doesNotMatch(captionSource, /scale\(/);
assert.match(captionSource, /style\.effects\.shadow/);
assert.match(captionSource, /style\.background\.enabled/);
assert.match(captionSource, /style\.background\.shape/);
assert.match(captionSource, /style\.background\.opacity/);
assert.match(captionSource, /WebkitTextStroke/);
assert.match(captionSource, /style\.stroke\.enabled/);
assert.doesNotMatch(captionSource, /captionBackgroundThemes|captionStrokeThemes|caption-color-themes|backgroundThemes|strokeThemes/);
assert.match(captionSource, /styleSelection\?:/);

const resolverSource = readFileSync(new URL("../examples/caption-style-resolver.ts", import.meta.url), "utf8");
assert.match(resolverSource, /resolveCaptionBackgroundThemeOverrides/);
assert.match(resolverSource, /resolveCaptionStrokeThemeOverrides/);

const previewSource = readFileSync(new URL("../examples/CaptionPreview.tsx", import.meta.url), "utf8");
assert.match(previewSource, /<Caption/);
assert.match(previewSource, /karaoke=\{karaoke\}/);
assert.match(previewSource, /styleSelection=\{\{ preset, overrides \}\}/);
assert.match(previewSource, /sampleText = previewConfig\.sampleText/);
assert.match(previewSource, /export const cueForPreview/);

const previewGridSource = readFileSync(new URL("../examples/CaptionPreviewGrid.tsx", import.meta.url), "utf8");
assert.match(previewGridSource, /<Caption/);
assert.match(previewGridSource, /previewConfig\.grids\[gridId\]/);
assert.match(previewGridSource, /cueForPreview/);
assert.match(previewGridSource, /candidate\.id/);
assert.doesNotMatch(previewGridSource, /textShadow|WebkitTextStroke|backgroundColor: style|wordHighlight/);
assert.doesNotMatch(previewGridSource, /style\.font|style\.background|style\.stroke|style\.wordHighlight/);

const captionsSource = readFileSync(new URL("../examples/Captions.tsx", import.meta.url), "utf8");
assert.match(captionsSource, /<Caption\s+captions=\{captions as Cue\[\]\}/);
assert.doesNotMatch(captionsSource, /<Caption[^>]*karaoke/);
assert.doesNotMatch(captionsSource, /resolveCaptionStyle/);

const overlaySource = readFileSync(new URL("../examples/CaptionsOverlay.tsx", import.meta.url), "utf8");
assert.match(overlaySource, /<Caption\s+captions=\{captions as Cue\[\]\}/);
assert.doesNotMatch(overlaySource, /<Caption[^>]*karaoke/);
assert.doesNotMatch(overlaySource, /resolveCaptionStyle/);

const previewScript = readFileSync(new URL("./render-caption-previews.mjs", import.meta.url), "utf8");
assert.match(previewScript, /preview-\$\{candidate\.id\}\.png/);
assert.match(previewScript, /--frame=\$\{frame\}/);
assert.match(previewScript, /sampleText: candidate\.sampleText \?\? previewConfig\.sampleText/);
assert.match(previewScript, /readdirSync\(previewConfig\.outputDir\)/);
assert.match(previewScript, /args\.has\("--grid"\)/);
assert.match(previewScript, /previewConfig\.grids/);
assert.match(previewScript, /build-preview-contact-sheets\.ps1/);
assert.match(previewScript, /props-contact-sheets\.json/);
assert.match(previewScript, /preview-\$\{id\}\.png/);

const contactSheetScript = readFileSync(new URL("./build-preview-contact-sheets.ps1", import.meta.url), "utf8");
assert.match(contactSheetScript, /DrawImage/);
assert.match(contactSheetScript, /ConvertFrom-Json/);
assert.match(contactSheetScript, /ImageFormat\]::Png/);

assert.deepEqual(previewConfig.candidates.map((candidate) => candidate.id), [
  "clean",
  "minimal",
  "social-bold",
  "pill-gray",
  "pill-yellow",
  "pill-blue",
  "pill-pink",
  "pill-green",
  "boxed-gray",
  "boxed-yellow",
  "boxed-blue",
  "boxed-pink",
  "boxed-green",
  "stroked-black",
  "stroked-yellow",
  "stroked-blue",
  "stroked-pink",
  "stroked-green",
  "stroked-black-karaoke",
  "social-bold-karaoke",
  "shorts-green",
  "shorts-orange",
  "shorts-yellow",
]);
assert.deepEqual(previewConfig.candidates.map((candidate) => candidate.preset), [
  "clean",
  "minimal",
  "social-bold",
  "pill",
  "pill",
  "pill",
  "pill",
  "pill",
  "boxed",
  "boxed",
  "boxed",
  "boxed",
  "boxed",
  "stroked",
  "stroked",
  "stroked",
  "stroked",
  "stroked",
  "stroked",
  "social-bold",
  "shorts",
  "shorts",
  "shorts",
]);
for (const theme of backgroundThemes) {
  assert.equal(previewConfig.candidates.some((candidate) => candidate.id === `pill-${theme}`), true);
  assert.equal(previewConfig.candidates.some((candidate) => candidate.id === `boxed-${theme}`), true);
}
for (const theme of strokeThemes) {
  assert.equal(previewConfig.candidates.some((candidate) => candidate.id === `stroked-${theme}`), true);
}
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "stroked-black-karaoke")?.karaoke, true);
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "social-bold-karaoke")?.karaoke, true);
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "social-bold")?.karaoke, false);
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-green")?.compositionId, "CaptionPreviewVertical");
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-green")?.sampleText, "This is how captions look");
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-orange")?.overrides?.wordHighlight?.activeColor, "#F8BD6D");
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-orange")?.sampleText, "This is how captions look");
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-yellow")?.overrides?.wordHighlight?.activeColor, "#F8F54F");
assert.equal(previewConfig.candidates.find((candidate) => candidate.id === "shorts-yellow")?.sampleText, "This is how captions look");
assert.equal(typeof previewConfig.sampleText, "string");
assert.ok(previewConfig.sampleText.length > 0);
assert.equal(existsSync(new URL("../public/fonts/CalSans-Regular.ttf", import.meta.url)), true);
assert.deepEqual(previewConfig.grids.landscape.candidateIds, [
  "clean",
  "minimal",
  "social-bold",
  "pill-gray",
  "boxed-gray",
  "stroked-black",
]);
assert.equal(previewConfig.grids.landscape.columns, 3);
assert.equal(previewConfig.grids.landscape.sampleText, "This is how captions will look");
assert.equal(previewConfig.grids.landscape.outputFile, "out/style-previews/preview-grid-landscape.png");
assert.equal(previewConfig.grids.landscape.intentGroups.clean.includes("minimal"), true);
assert.equal(previewConfig.grids.landscape.intentGroups.background.includes("pill-yellow"), true);
assert.equal(previewConfig.grids.landscape.intentGroups.stroke.includes("stroked-blue"), true);
assert.equal(previewConfig.grids.landscape.intentGroups.karaoke.includes("social-bold-karaoke"), true);
assert.deepEqual(previewConfig.grids.shorts.candidateIds, [
  "shorts-green",
  "shorts-yellow",
  "shorts-orange",
]);
assert.equal(previewConfig.grids.shorts.columns, 3);
assert.equal(previewConfig.grids.shorts.sampleText, "This is how captions look");
assert.equal(previewConfig.grids.shorts.outputFile, "out/style-previews/preview-grid-shorts.png");
assert.equal(previewConfig.grids.shorts.intentGroups.shorts.includes("shorts-green"), true);
for (const grid of Object.values(previewConfig.grids)) {
  for (const id of grid.candidateIds) {
    assert.equal(previewConfig.candidates.some((candidate) => candidate.id === id), true);
  }
}
for (const id of previewConfig.grids.landscape.candidateIds) {
  assert.equal(id.startsWith("shorts-"), false);
}
for (const id of previewConfig.grids.shorts.candidateIds) {
  assert.equal(previewConfig.candidates.some((candidate) => candidate.id === id), true);
  assert.equal(id.startsWith("shorts-"), true);
}

const skillDoc = readFileSync(new URL("../SKILL.md", import.meta.url), "utf8");
const feedbackDoc = readFileSync(new URL("../reference/caption-feedback-mapping.md", import.meta.url), "utf8");
const themeDoc = readFileSync(new URL("../reference/caption-style-themes.md", import.meta.url), "utf8");
const docs = `${skillDoc}\n${feedbackDoc}\n${themeDoc}`;

for (const preset of Object.keys(captionPresets).filter((preset) => preset !== "shorts")) {
  assert.match(feedbackDoc, new RegExp(`\`${preset}\``));
}
for (const theme of backgroundThemes) {
  assert.match(feedbackDoc, new RegExp(`background\\.theme = "${theme}"|theme: "${theme}"`));
}
for (const theme of strokeThemes) {
  assert.match(feedbackDoc, new RegExp(`stroke\\.theme = "${theme}"|theme: "${theme}"`));
}

assert.match(feedbackDoc, /Karaoke is an option, not a preset/);
assert.match(skillDoc, /Karaoke is an option/);
for (const line of docs.split(/\r?\n/).filter((item) => /^Official presets/i.test(item))) {
  assert.doesNotMatch(line, /(karaoke|pill-yellow|boxed-green|stroked-blue|social-bold-karaoke)/i);
}
assert.match(docs, /pill-yellow[\s\S]*preview candidate ids only|preview candidate ids such as `pill-yellow`/);
assert.match(docs, /boxed-green[\s\S]*preview candidate ids only|preview candidate ids such as `pill-yellow`/);
assert.match(docs, /stroked-blue[\s\S]*preview candidate ids only|preview candidate ids such as `pill-yellow`/);
assert.match(docs, /social-bold-karaoke[\s\S]*preview candidate ids only|preview candidate ids such as `pill-yellow`/);
assert.match(feedbackDoc, /Do not ask\s+the user to edit `Caption\.tsx`/);
assert.doesNotMatch(docs, /ask the user to edit `Caption\.tsx` for ordinary style feedback/i);
assert.match(feedbackDoc, /preset: "stroked"/);
assert.match(feedbackDoc, /background: \{ enabled: false \}/);
assert.match(feedbackDoc, /stroke: \{/);
assert.match(feedbackDoc, /wordHighlight\.activeScale = 1/);

console.log("[captions] caption style config checks passed");
