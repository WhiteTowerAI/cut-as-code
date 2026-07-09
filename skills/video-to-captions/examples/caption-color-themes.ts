import type { CaptionBackgroundTheme, CaptionStrokeTheme, CaptionStyleOverrides } from "./caption-presets.ts";

export type CaptionHighlightTheme = "bright-green" | "orange" | "yellow";

export type CaptionBackgroundThemeDefinition = {
  background: {
    color: string;
    opacity: number;
  };
  font?: {
    color: string;
  };
  wordHighlight?: {
    activeColor: string;
  };
};

export type CaptionStrokeThemeDefinition = {
  stroke: {
    color: string;
    opacity: number;
  };
  wordHighlight?: {
    activeColor: string;
  };
};

export type CaptionHighlightThemeDefinition = {
  wordHighlight: {
    activeColor: string;
    backgroundColor: string;
  };
};

export const captionHighlightThemes: Record<CaptionHighlightTheme, CaptionHighlightThemeDefinition> = {
  "bright-green": {
    wordHighlight: { activeColor: "#21D32E", backgroundColor: "#21D32E" },
  },
  orange: {
    wordHighlight: { activeColor: "#F8BD6D", backgroundColor: "#F8BD6D" },
  },
  yellow: {
    wordHighlight: { activeColor: "#F8F54F", backgroundColor: "#F8F54F" },
  },
};

export const captionBackgroundThemes: Record<CaptionBackgroundTheme, CaptionBackgroundThemeDefinition> = {
  gray: {
    background: { color: "#111827", opacity: 0.62 },
    font: { color: "#FFFFFF" },
    wordHighlight: { activeColor: "#FFD43B" },
  },
  yellow: {
    background: { color: "#FACC15", opacity: 0.82 },
    font: { color: "#1A1A1A" },
    wordHighlight: { activeColor: "#B45309" },
  },
  blue: {
    background: { color: "#2563EB", opacity: 0.72 },
    font: { color: "#FFFFFF" },
    wordHighlight: { activeColor: "#BFDBFE" },
  },
  pink: {
    background: { color: "#DB2777", opacity: 0.72 },
    font: { color: "#FFFFFF" },
    wordHighlight: { activeColor: "#FBCFE8" },
  },
  green: {
    background: { color: "#16A34A", opacity: 0.72 },
    font: { color: "#FFFFFF" },
    wordHighlight: { activeColor: "#BBF7D0" },
  },
};

export const captionStrokeThemes: Record<CaptionStrokeTheme, CaptionStrokeThemeDefinition> = {
  black: {
    stroke: { color: "#000000", opacity: 0.9 },
    wordHighlight: { activeColor: "#FFD43B" },
  },
  yellow: {
    stroke: { color: "#CA8A04", opacity: 0.95 },
    wordHighlight: { activeColor: "#CA8A04" },
  },
  blue: {
    stroke: { color: "#2563EB", opacity: 0.95 },
    wordHighlight: { activeColor: "#93C5FD" },
  },
  pink: {
    stroke: { color: "#DB2777", opacity: 0.95 },
    wordHighlight: { activeColor: "#F9A8D4" },
  },
  green: {
    stroke: { color: "#16A34A", opacity: 0.95 },
    wordHighlight: { activeColor: "#86EFAC" },
  },
};

export const resolveCaptionBackgroundThemeOverrides = (
  theme: CaptionBackgroundTheme
): CaptionStyleOverrides => {
  const resolved = captionBackgroundThemes[theme] ?? captionBackgroundThemes.gray;

  return {
    background: {
      color: resolved.background.color,
      opacity: resolved.background.opacity,
    },
    font: resolved.font,
    wordHighlight: resolved.wordHighlight,
  };
};

export const resolveCaptionStrokeThemeOverrides = (
  theme: CaptionStrokeTheme
): CaptionStyleOverrides => {
  const resolved = captionStrokeThemes[theme] ?? captionStrokeThemes.black;

  return {
    stroke: {
      color: resolved.stroke.color,
      opacity: resolved.stroke.opacity,
    },
    wordHighlight: resolved.wordHighlight,
  };
};
