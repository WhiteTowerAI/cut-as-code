import {
  captionPresets,
  type CaptionPresetName,
  type CaptionStyle,
  type CaptionStyleOverrides,
  type CaptionStyleSelection,
} from "./caption-presets.ts";
import {
  resolveCaptionBackgroundThemeOverrides,
  resolveCaptionStrokeThemeOverrides,
} from "./caption-color-themes.ts";

export type UnknownPresetStrategy = "fallback" | "throw";

export type ResolveCaptionStyleOptions = {
  unknownPreset?: UnknownPresetStrategy;
  fallbackPreset?: CaptionPresetName;
};

const DEFAULT_FALLBACK_PRESET: CaptionPresetName = "clean";

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const clone = <T>(value: T): T => {
  if (Array.isArray(value)) {
    return value.map((item) => clone(item)) as T;
  }
  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, clone(item)])
    ) as T;
  }
  return value;
};

const mergeDeep = <T extends Record<string, unknown>>(base: T, overrides?: Record<string, unknown>): T => {
  const out = clone(base);
  if (!overrides) {
    return out;
  }

  for (const [key, value] of Object.entries(overrides)) {
    const current = out[key];
    if (isPlainObject(current) && isPlainObject(value)) {
      out[key] = mergeDeep(current, value);
    } else if (value !== undefined) {
      out[key] = clone(value);
    }
  }

  return out;
};

const getPreset = (
  name: string,
  options: ResolveCaptionStyleOptions
): CaptionStyle => {
  if (name in captionPresets) {
    return captionPresets[name as CaptionPresetName];
  }

  if (options.unknownPreset === "throw") {
    throw new Error(`[captions] unknown caption style preset: ${name}`);
  }

  const fallback = options.fallbackPreset ?? DEFAULT_FALLBACK_PRESET;
  return captionPresets[fallback];
};

export const resolveCaptionStyle = (
  selection: CaptionStyleSelection,
  options: ResolveCaptionStyleOptions = {}
): CaptionStyle => {
  const preset = getPreset(selection.preset, options);
  const presetWithTheme = preset.background.enabled
    ? mergeDeep(
      preset as unknown as Record<string, unknown>,
      resolveCaptionBackgroundThemeOverrides(preset.background.theme) as unknown as Record<string, unknown>
    )
    : preset as unknown as Record<string, unknown>;
  const resolved = mergeDeep(
    presetWithTheme,
    selection.overrides as CaptionStyleOverrides as unknown as Record<string, unknown>
  ) as unknown as CaptionStyle;
  const shouldApplyTheme =
    resolved.background.enabled &&
    (!preset.background.enabled ||
      selection.overrides?.background?.theme !== undefined ||
      selection.overrides?.background?.enabled !== undefined);
  const themed = shouldApplyTheme
    ? mergeDeep(
      mergeDeep(
        resolved as unknown as Record<string, unknown>,
        resolveCaptionBackgroundThemeOverrides(resolved.background.theme) as unknown as Record<string, unknown>
      ),
      selection.overrides as CaptionStyleOverrides as unknown as Record<string, unknown>
    ) as unknown as CaptionStyle
    : resolved;

  const withStrokeTheme = themed.stroke.enabled
    ? mergeDeep(
      mergeDeep(
        themed as unknown as Record<string, unknown>,
        resolveCaptionStrokeThemeOverrides(themed.stroke.theme) as unknown as Record<string, unknown>
      ),
      selection.overrides as CaptionStyleOverrides as unknown as Record<string, unknown>
    ) as unknown as CaptionStyle
    : themed;

  const withPresetDefaults = preset.preset === "shorts" && selection.overrides?.wordHighlight === undefined
    ? mergeDeep(
      withStrokeTheme as unknown as Record<string, unknown>,
      { wordHighlight: preset.wordHighlight } as unknown as Record<string, unknown>
    ) as unknown as CaptionStyle
    : withStrokeTheme;

  withPresetDefaults.preset = preset.preset;
  return withPresetDefaults;
};
