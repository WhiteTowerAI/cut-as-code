// anim.tsx — shared design system: timing + palette + helpers.
//
// Every generated component imports from here, so the whole piece keeps ONE
// rhythm and ONE look. The golden rule (because overlays sit on REAL footage,
// not light designer frames): every element rides on its OWN background — a
// scrim or a card — and is ANCHORED to one edge, never centered over the face.
// Default anchor is the BOTTOM (the lower-third safe zone on a talking-head).
// Flip the whole piece to the TOP by setting ANCHOR below — e.g. to clear
// bottom captions when combining with video-to-captions (see that recipe in
// SKILL.md). Sizes are a % of canvas height, so the look auto-scales to any
// output resolution (render at the source's size, not 4K — see Root.tsx).
import * as React from "react";
import {
  AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig,
} from "remotion";
import { T } from "./themes";

// --- timing (frames @ 24fps) — tweak the feel in one place -----------------
export const TIMING = {
  reveal: 13,        // element entrance
  stagger: 4,        // gap between siblings (list items)
  overlayIn: 10,     // panel slide-in (~430ms)
  overlayOut: 8,     // fade-out
  fade: 7,           // ~0.3s card fade in/out (the card-language fade)
};

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

// --- palette: 由当前主题 T 提供(themes.ts)。保留旧常量名,组件无需改 import。
export const INK    = T.color.scrimBase;   // 深色卡/scrim 底
export const ACCENT = T.color.accent;      // 强调色
export const WHITE  = T.color.text;         // 主文字
export const MUTED  = T.color.textMuted;    // 次文字
// CARD: teal 为半透卡填色;editorial(card=null)退化为透明——迁移后组件不再用它。
export const CARD   = T.card ? T.card.bg : "transparent";

// --- resolution-independent sizing -----------------------------------------
// u(6) === 6% of canvas height. Author every size in these fractions so the
// design reads identically at 640x298 or 1920x896 — never hardcode px.
export const useUnit = () => useVideoConfig().height / 100;

// --- anchor: which edge the whole piece rides on ---------------------------
// ONE knob for the entire design. "bottom" = the lower-third safe zone (default).
// Set "top" to clear bottom captions when compositing captions + cards on one
// video (video-to-captions). Every component reads it via the two helpers below
// (justify + padding) and Scrim flips with it, so this single line moves them all.
// To flip, change only the VALUE ("bottom" -> "top"). The `as "bottom" | "top"`
// widening is load-bearing: a plain annotated `const ANCHOR: ... = "bottom"` gets
// narrowed by TS to the literal "bottom" at the comparison sites below, so every
// `=== "top"` branch trips a TS2367 "no overlap" error, breaking the top path.
// The `as` keeps the const's static type wide so both branches stay reachable.
export const ANCHOR = "bottom" as "bottom" | "top";

// justifyContent for a card's AbsoluteFill so it sits on the anchored edge.
export const anchorJustify = (): "flex-start" | "flex-end" =>
  ANCHOR === "top" ? "flex-start" : "flex-end";

// CSS padding (top right bottom left) that puts `block` px between the card and
// the anchored edge, with optional `left`/`right` insets. Honors ANCHOR, so the
// same call gives a bottom gap by default and a top gap when flipped.
export const anchorPad = (block: number, left = 0, right = 0): string =>
  ANCHOR === "top"
    ? `${block}px ${right}px 0 ${left}px`
    : `0 ${right}px ${block}px ${left}px`;

// Card fade: fades in over TIMING.fade, and (if the cue's length is passed)
// out over the last TIMING.fade frames. durFrames comes from FinalEdit, which
// knows each cue's duration — robust inside a <Sequence> (frame starts at 0).
export const useFade = (durFrames?: number): number => {
  const f = useCurrentFrame();
  const fin = interpolate(f, [0, TIMING.fade], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (!durFrames) return fin;
  const fout = interpolate(f, [durFrames - TIMING.fade, durFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return Math.min(fin, fout);
};

// #RRGGBB + alpha(0..1) → rgba(),供渐变用(scrimBase 是 hex)。
const hexA = (hex: string, a: number): string => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
};

// A soft scrim (transparent -> INK) on the anchored edge so text stays legible
// on busy footage. Used by full-width cards (chapter / intro / outro / list).
// Follows ANCHOR: a bottom band by default, a top band (reversed gradient) when
// flipped — INK is always densest at the anchored edge, fading toward center.
export const Scrim: React.FC<{ heightPct?: number; maxOpacity?: number }> = ({
  heightPct = 45, maxOpacity = 0.88,
}) => {
  const base = T.color.scrimBase;
  const grad = (op: number) =>
    ANCHOR === "top"
      ? `linear-gradient(to top, ${hexA(base, 0)}, ${hexA(base, op)})`
      : `linear-gradient(to bottom, ${hexA(base, 0)}, ${hexA(base, op)})`;
  return (
    <AbsoluteFill style={
      ANCHOR === "top"
        ? { top: 0, bottom: "auto", height: `${heightPct}%`, background: grad(maxOpacity) }
        : { top: `${100 - heightPct}%`, background: grad(maxOpacity) }
    } />
  );
};
