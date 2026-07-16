import {
  titleOverlayPresets,
  titleOverlayThemes,
  type TitleOverlayPresetName,
  type TitleOverlayStyle,
  type TitleOverlayStyleSelection,
  type TitleOverlayTheme,
} from "./overlay-presets.ts";

export type ResolveTitleOverlayStyleOptions = {
  unknownPreset?: "throw";
  unknownTheme?: "throw";
};

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

const mergeDeep = <T extends Record<string, unknown>>(
  base: T,
  overrides?: Record<string, unknown>
): T => {
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
  preset: string,
  _options: ResolveTitleOverlayStyleOptions
): TitleOverlayStyle => {
  if (preset in titleOverlayPresets) {
    return titleOverlayPresets[preset as TitleOverlayPresetName];
  }
  throw new Error(`[video-overlay] unknown title overlay preset: ${preset}`);
};

const getTheme = (
  theme: string,
  _options: ResolveTitleOverlayStyleOptions
): Record<string, unknown> => {
  if (theme in titleOverlayThemes) {
    return titleOverlayThemes[theme as TitleOverlayTheme] as Record<string, unknown>;
  }
  throw new Error(`[video-overlay] unknown title overlay theme: ${theme}`);
};

export const resolveTitleOverlayStyle = (
  selection: TitleOverlayStyleSelection,
  options: ResolveTitleOverlayStyleOptions = {}
): TitleOverlayStyle => {
  const preset = getPreset(selection.preset, options);
  const theme = getTheme(selection.theme, options);
  const themed = mergeDeep(
    preset as unknown as Record<string, unknown>,
    theme
  );
  const resolved = mergeDeep(
    themed,
    selection.overrides as Record<string, unknown> | undefined
  ) as unknown as TitleOverlayStyle;

  resolved.preset = preset.preset;
  resolved.theme = selection.theme as TitleOverlayTheme;
  resolved.layout.avoidBottomCaptionArea = true;
  resolved.animation.type = "none";

  return resolved;
};
