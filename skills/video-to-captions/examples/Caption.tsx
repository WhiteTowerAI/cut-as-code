// Caption.tsx — one renderer that spans the whole video and draws the active
// caption cue, picked from the absolute frame. With `karaoke`, the word being
// spoken is highlighted and not-yet-spoken words are dimmed.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { TIMING, EASE_OUT, CREAM, CLAY, DIM } from "./anim";

type Word = { word: string; start: number; end: number };
export type Cue = { index: number; start: number; end: number; text: string; lines: string[]; words: Word[] };

export const Caption: React.FC<{ captions: Cue[]; karaoke?: boolean }> = ({ captions, karaoke = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const cue = captions.find((c) => t >= c.start && t < c.end);
  if (!cue) return null;

  const startF = cue.start * fps;
  const pop = interpolate(frame, [startF, startF + TIMING.popIn], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
      <div style={{
        opacity: pop,
        transform: `translateY(${interpolate(pop, [0, 1], [22, 0])}px)`,
        maxWidth: "80%", textAlign: "center",
        fontFamily: "Inter, system-ui, sans-serif", fontWeight: 800,
        fontSize: 66, lineHeight: 1.2, letterSpacing: -0.5, color: CREAM,
        textShadow: "0 2px 14px rgba(0,0,0,.6), 0 0 2px rgba(0,0,0,.5)",
      }}>
        {cue.words.map((w, i) => {
          const active = karaoke && t >= w.start && t < w.end;
          const upcoming = karaoke && t < w.start;
          return (
            <span key={i} style={{ color: active ? CLAY : CREAM, opacity: upcoming ? DIM : 1 }}>
              {w.word}{i < cue.words.length - 1 ? " " : ""}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
