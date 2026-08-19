import { readFileSync } from "node:fs";

const configText = readFileSync(new URL("./caption-styles.json", import.meta.url), "utf8").replace(/^\uFEFF/, "");
const config = JSON.parse(configText);

export const captionPresets = config.presets;
export const captionThemes = config.themes;
export const captionPresetNames = Object.freeze(Object.keys(captionPresets));
export const captionHighlightThemeNames = Object.freeze(Object.keys(captionThemes.highlight));
export const captionBackgroundThemeNames = Object.freeze(Object.keys(captionThemes.background));
export const captionStrokeThemeNames = Object.freeze(Object.keys(captionThemes.stroke));

const isPlainObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);

export const cloneValue = (value) => {
  if (Array.isArray(value)) {
    return value.map(cloneValue);
  }
  if (isPlainObject(value)) {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]));
  }
  return value;
};

export const captionExpressiveTreatments = Object.freeze(cloneValue(config.expressiveTreatments));

export const mergeDeep = (base, overrides) => {
  const output = cloneValue(base);
  if (!overrides) {
    return output;
  }

  for (const [key, value] of Object.entries(overrides)) {
    if (isPlainObject(output[key]) && isPlainObject(value)) {
      output[key] = mergeDeep(output[key], value);
    } else if (value !== undefined) {
      output[key] = cloneValue(value);
    }
  }
  return output;
};

const getPreset = (name, strict) => {
  if (name in captionPresets) {
    return captionPresets[name];
  }
  if (strict) {
    throw new Error(`[captions] unknown caption style preset: ${name}`);
  }
  return captionPresets.clean;
};

const getTheme = (group, name, fallback, strict) => {
  if (!name) {
    return undefined;
  }
  if (name in group) {
    return group[name];
  }
  if (strict) {
    throw new Error(`[captions] unknown caption theme: ${name}`);
  }
  return group[fallback];
};

export const resolveCaptionStyle = ({
  preset = "clean",
  highlightTheme,
  backgroundTheme,
  strokeTheme,
  overrides,
  strict = true,
} = {}) => {
  const presetStyle = getPreset(preset, strict);
  let resolved = cloneValue(presetStyle);

  if (resolved.background.enabled) {
    resolved = mergeDeep(resolved, getTheme(captionThemes.background, resolved.background.theme, "gray", strict));
  }

  if (backgroundTheme) {
    resolved = mergeDeep(resolved, {
      background: { enabled: true, theme: backgroundTheme },
    });
    resolved = mergeDeep(resolved, getTheme(captionThemes.background, backgroundTheme, "gray", strict));
  }

  if (resolved.stroke.enabled) {
    resolved = mergeDeep(resolved, getTheme(captionThemes.stroke, resolved.stroke.theme, "black", strict));
  }

  if (strokeTheme) {
    resolved = mergeDeep(resolved, {
      stroke: { enabled: true, theme: strokeTheme },
    });
    resolved = mergeDeep(resolved, getTheme(captionThemes.stroke, strokeTheme, "black", strict));
  }

  if (presetStyle.preset === "shorts" && !highlightTheme && overrides?.wordHighlight === undefined) {
    resolved = mergeDeep(resolved, { wordHighlight: presetStyle.wordHighlight });
  }

  if (highlightTheme) {
    resolved = mergeDeep(resolved, getTheme(captionThemes.highlight, highlightTheme, "green", strict));
  }

  resolved = mergeDeep(resolved, overrides);
  resolved.preset = presetStyle.preset;
  return resolved;
};

export const resolveKaraoke = (requested, style) => {
  if (requested === undefined || requested === "auto") {
    return Boolean(style.wordHighlight.enabled);
  }
  if (requested === true || requested === "true") {
    return true;
  }
  if (requested === false || requested === "false") {
    return false;
  }
  throw new Error(`[captions] invalid karaoke value: ${requested}`);
};
