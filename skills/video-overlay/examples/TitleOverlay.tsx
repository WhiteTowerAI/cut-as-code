import * as React from "react";
import { AbsoluteFill } from "remotion";
import { titleOverlayConfig, type TitleOverlayConfig } from "./overlay-config";
import { resolveTitleOverlayStyle } from "./overlay-style-resolver";
import type { TitleOverlayTheme } from "./overlay-presets";

type SourceMeta = {
  width: number;
  height: number;
  fps?: number;
  durationInSeconds: number;
};

type TitleOverlayProps = {
  config?: TitleOverlayConfig;
  meta?: SourceMeta;
  theme?: TitleOverlayTheme;
  title?: string;
};

const estimateCharsPerLine = (fontPx: number, maxWidthPx: number) =>
  Math.max(4, Math.floor(maxWidthPx / Math.max(1, fontPx * 0.82)));

const fitFontPx = (fontPx: number, maxWidthPx: number, lines: string[]) => {
  const longest = Math.max(...lines.map((line) => line.length), 1);
  return Math.floor(Math.min(fontPx, maxWidthPx / Math.max(1, longest * 0.86)));
};

const wrapTitle = (text: string, maxChars: number) => {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return { lines: [""], overflow: false };
  }

  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length <= maxChars || current === "") {
      current = next;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) {
    lines.push(current);
  }

  return {
    lines,
    overflow: lines.length > 2,
  };
};

export const TitleOverlay: React.FC<TitleOverlayProps> = ({
  config = titleOverlayConfig,
  meta,
  theme,
  title,
}) => {
  const selectedTheme = theme ?? config.style.theme;
  const style = resolveTitleOverlayStyle({
    preset: config.style.preset,
    theme: selectedTheme,
    overrides: config.style.overrides,
  });
  const width = meta?.width ?? 1080;
  const height = meta?.height ?? 1920;
  const baseFontPx = Math.round(height * style.font.sizeRatio);
  const maxWidthPx = Math.round(width * style.layout.maxWidthRatio);
  const position = config.layout.position;
  const centerYRatio = position === "custom"
    ? config.layout.customYRatio ?? style.layout.yRatio
    : position === "top"
      ? null
      : style.layout.yRatio;
  const displayTitle = title ?? config.title.text;
  const wrap = wrapTitle(displayTitle, estimateCharsPerLine(baseFontPx, maxWidthPx));
  const fontPx = fitFontPx(baseFontPx, maxWidthPx, wrap.lines);
  const safeAreaTop = height * (1 - style.layout.bottomCaptionSafeAreaRatio);
  const titleBlockHeight = fontPx * style.font.lineHeight * wrap.lines.length;
  const topPx = position === "top"
    ? height * 0.02
    : Math.min(
      height * (centerYRatio ?? style.layout.yRatio) - titleBlockHeight / 2,
      safeAreaTop - titleBlockHeight
    );
  const strokePx = Math.max(1, Math.round(width * style.effects.stroke.widthRatio));
  const shadowY = Math.round(height * style.effects.shadow.offsetYRatio);
  const blurPx = Math.round(height * style.effects.shadow.blurRatio);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "transparent",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: Math.max(0, topPx),
          width: maxWidthPx,
          transform: "translateX(-50%)",
          textAlign: style.layout.align,
          fontFamily: style.font.family,
          fontSize: fontPx,
          fontWeight: style.font.weight,
          lineHeight: style.font.lineHeight,
          letterSpacing: style.font.letterSpacing,
          color: style.font.color,
          textTransform: style.font.textTransform,
          textShadow: `0 ${shadowY}px ${blurPx}px rgba(0,0,0,${style.effects.shadow.opacity})`,
          WebkitTextStroke: `${strokePx}px rgba(0,0,0,${style.effects.stroke.opacity})`,
        }}
      >
        {wrap.lines.map((line, index) => (
          <div key={`${line}-${index}`}>
            <span
              style={{
                boxDecorationBreak: "clone",
                WebkitBoxDecorationBreak: "clone",
                backgroundColor: `color-mix(in srgb, ${style.accent.backgroundColor} ${Math.round(style.accent.backgroundOpacity * 100)}%, transparent)`,
                padding: `0 ${Math.round(fontPx * 0.08)}px`,
              }}
            >
              {line}
            </span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
