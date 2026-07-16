// Caption.tsx — one renderer that spans the whole video and draws the active
// caption cue, picked from the absolute frame. With `karaoke`, the word being
// spoken is highlighted and not-yet-spoken words are dimmed.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, staticFile } from "remotion";
import { EASE_OUT } from "./anim";
import { selectedCaptionStyle } from "./caption-style.ts";
import { resolveCaptionStyle } from "./caption-style-resolver.ts";
import type { CaptionStyleSelection } from "./caption-presets.ts";

type Word = { word: string; start: number; end: number };
export type Cue = { index: number; start: number; end: number; text: string; lines: string[]; words: Word[] };

export const Caption: React.FC<{ captions: Cue[]; karaoke?: boolean; styleSelection?: CaptionStyleSelection }> = ({ captions, karaoke, styleSelection = selectedCaptionStyle }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const t = frame / fps;
  const style = resolveCaptionStyle(styleSelection);
  const isShorts = style.preset === "shorts";

  // Size everything off frame HEIGHT so captions read at any resolution
  // (was hard-coded 66px / paddingBottom 200 — only valid on a 2160px-tall 4K
  // frame; on a 298px source that overflowed off-screen).
  const fontSize = Math.round(height * style.font.sizeRatio);
  const paddingBottom = Math.round(height * style.layout.paddingBottomRatio);
  const backgroundPaddingX = Math.round(height * style.background.paddingXRatio);
  const backgroundPaddingY = Math.round(height * style.background.paddingYRatio);
  const backgroundRadius = style.background.shape === "square"
    ? 0
    : style.background.shape === "pill"
      ? 9999
      : Math.round(height * style.background.radiusRatio);
  const shadowOffset = Math.round(height * style.effects.shadow.offsetYRatio);
  const shadowBlur = Math.round(height * style.effects.shadow.blurRatio);
  const strokeWidth = style.stroke.widthPx ?? Math.round(height * style.stroke.widthRatio);

  const cue = captions.find((c) => t >= c.start && t < c.end);
  if (!cue) return null;

  const karaokeEnabled = karaoke ?? styleSelection.karaoke ?? style.wordHighlight.enabled;
  const formatWord = isShorts
    ? (word: string) => word.toUpperCase()
    : (word: string) => word;
  const startF = cue.start * fps;
  const pop = interpolate(frame, [startF, startF + style.animation.popInFrames], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const shadowColor = toRgba(style.effects.shadow.color, style.effects.shadow.opacity);
  const outlineShadow = toRgba(style.effects.shadow.color, style.effects.shadow.opacity * 0.83);
  const textShadow = style.effects.shadow.strength === "none"
    ? undefined
    : `0 ${shadowOffset}px ${shadowBlur}px ${shadowColor}, 0 0 2px ${outlineShadow}`;
  const textStroke = style.stroke.enabled
    ? `${strokeWidth}px ${toRgba(style.stroke.color, style.stroke.opacity)}`
    : undefined;
  const justifyContent = style.layout.anchor === "top"
    ? "flex-start"
    : style.layout.anchor === "center"
      ? "center"
      : "flex-end";
  const alignItems = style.layout.align === "left"
    ? "flex-start"
    : style.layout.align === "right"
      ? "flex-end"
      : "center";

  return (
    <AbsoluteFill style={{ justifyContent, alignItems, paddingBottom }}>
      {isShorts ? (
        <style>{`
          @font-face {
            font-family: "Cal_Sans";
            src: url("${staticFile("fonts/CalSans-Regular.ttf")}") format("truetype");
            font-weight: 900;
            font-style: normal;
            font-display: block;
          }
        `}</style>
      ) : null}
      <div style={{
        opacity: pop,
        transform: `translateY(${interpolate(pop, [0, 1], [style.animation.translateYPx, 0])}px)`,
        maxWidth: `${style.layout.maxWidth * 100}%`, textAlign: style.layout.align,
        boxSizing: "border-box",
        backgroundColor: style.background.enabled ? toRgba(style.background.color, style.background.opacity) : undefined,
        borderRadius: style.background.enabled ? backgroundRadius : undefined,
        padding: style.background.enabled ? `${backgroundPaddingY}px ${backgroundPaddingX}px` : undefined,
        fontFamily: style.font.family, fontWeight: style.font.weight,
        fontSize, lineHeight: style.font.lineHeight, letterSpacing: style.font.letterSpacing, color: style.font.color,
        WebkitTextStroke: textStroke,
        paintOrder: style.stroke.enabled ? "stroke fill" : undefined,
        textShadow,
      }}>
        {cue.words.map((w, i) => {
          const canHighlight = karaokeEnabled && style.wordHighlight.enabled && style.wordHighlight.mode === "textColor";
          const active = canHighlight && t >= w.start && t < w.end;
          const upcoming = canHighlight && t < w.start;
          return (
            <React.Fragment key={i}>
              <span style={{
                color: active ? style.wordHighlight.activeColor : style.font.color,
                opacity: upcoming ? style.wordHighlight.upcomingOpacity : 1,
              }}>
                {formatWord(w.word)}
              </span>
              {i < cue.words.length - 1 ? " " : ""}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const toRgba = (color: string, opacity: number) => {
  if (!color.startsWith("#")) {
    return color;
  }

  const hex = color.slice(1);
  const full = hex.length === 3
    ? hex.split("").map((ch) => ch + ch).join("")
    : hex;
  const value = Number.parseInt(full, 16);

  if (Number.isNaN(value) || full.length !== 6) {
    return color;
  }

  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r},${g},${b},${opacity})`;
};
