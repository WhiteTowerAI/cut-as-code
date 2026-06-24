// anim.tsx — shared design system: timing + palette + helpers.
//
// Every generated component imports from here, so the whole piece keeps ONE
// rhythm and ONE look. The golden rule (because overlays sit on REAL footage,
// not light designer frames): every element rides on its OWN background — a
// bottom scrim or a card — and is BOTTOM-ANCHORED, never centered over the
// face. Sizes are a % of canvas height, so the look auto-scales to any output
// resolution (render at the source's size, not 4K — see Root.tsx).
import * as React from "react";
import {
  AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig,
} from "remotion";

// --- timing (frames @ 24fps) — tweak the feel in one place -----------------
export const TIMING = {
  reveal: 13,        // element entrance
  stagger: 4,        // gap between siblings (list items)
  overlayIn: 10,     // panel slide-in (~430ms)
  overlayOut: 8,     // fade-out
  fade: 7,           // ~0.3s card fade in/out (the card-language fade)
};

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

// --- palette: one teal accent on dark cards; white / muted text ------------
// (aligned to the video-overlay-cards look: INK card + WHITE text + teal bar)
export const INK    = "#0C141C";   // dark card / scrim base
export const ACCENT = "#26CAA8";   // teal accent
export const WHITE  = "#F5F8F9";
export const MUTED  = "#B7C6CE";
export const CARD   = "rgba(12,20,28,0.82)";   // semi-opaque card fill

// --- resolution-independent sizing -----------------------------------------
// u(6) === 6% of canvas height. Author every size in these fractions so the
// design reads identically at 640x298 or 1920x896 — never hardcode px.
export const useUnit = () => useVideoConfig().height / 100;

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

// A soft bottom scrim (transparent -> INK) so text stays legible on busy
// footage. Used by full-width cards (chapter / intro / outro / list).
export const Scrim: React.FC<{ heightPct?: number; maxOpacity?: number }> = ({
  heightPct = 45, maxOpacity = 0.88,
}) => (
  <AbsoluteFill style={{
    top: `${100 - heightPct}%`,
    background: `linear-gradient(to bottom, rgba(12,20,28,0), rgba(12,20,28,${maxOpacity}))`,
  }} />
);
