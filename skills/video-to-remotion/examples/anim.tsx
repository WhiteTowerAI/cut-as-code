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

// --- 第 2 层积木:组件只用这些拼装,样式值全来自 T ------------------------

// Surface: 文字底板。实心卡(teal)或透明(editorial,靠 Scrim 保证可读)。
// 只管主题化的卡片外观(底色/圆角/投影/强调边)+ card=null 的透明退化。
// padding 与其它布局由调用方经 `style` 传入(那是第 3 层组件的职责),这样每个
// 组件都能保留自己今天的精确 padding/边宽,teal 零回归。side/widthU 可覆盖,
// 因为各卡片的强调边位置与粗细本就不同(LowerThird 0.8u左、Stat 0.6u下)。
export const Surface: React.FC<{
  side?: "left" | "bottom"; widthU?: number;
  style?: React.CSSProperties; children: React.ReactNode;
}> = ({ side, widthU, style, children }) => {
  const u = useUnit();
  const c = T.card;
  if (!c) return <div style={style}>{children}</div>;   // editorial:透明,靠 Scrim
  const s = side ?? c.borderSide;
  const w = u * (widthU ?? c.borderWidthU);
  const border =
    s === "left"
      ? { borderLeft: `${w}px solid ${c.borderColor}` }
      : { borderBottom: `${w}px solid ${c.borderColor}` };
  return (
    <div style={{
      background: c.bg, borderRadius: u * c.radiusU, boxShadow: c.shadow,
      ...border, ...style,
    }}>{children}</div>
  );
};

// Rule: 分隔/强调线。bar=粗竖条(teal 的左边条);hairline=细线+accent 小段(editorial)。
// progress(0..1):stagger 入场时由 useDraw 传入,做 0→满宽的描线;fade 主题默认 1。
export const Rule: React.FC<{ widthU?: number; progress?: number }> = ({
  widthU = 36, progress = 1,
}) => {
  const u = useUnit();
  if (T.rule === "bar") {
    // teal:细高的一段(SectionCard 用作 title 下的强调条)。
    return <div style={{ height: u * 0.6, width: u * widthU * progress,
      background: T.color.accent, borderRadius: u * 0.3 }} />;
  }
  // editorial hairline:整条细线(淡文字色) + 左端一小段 accent。淡色由 T 派生,
  // 不写死(hexA 在本文件 Task 3 已定义)。
  const seg = u * 6; // accent 段长(u=6)
  const full = u * widthU * progress;
  return (
    <div style={{ position: "relative", height: u * 0.35, width: full,
      background: hexA(T.color.text, 0.32) }}>
      <div style={{ position: "absolute", left: 0, top: 0, height: "100%",
        width: Math.min(seg, full), background: T.color.accent }} />
    </div>
  );
};

// Kicker: 小标题(EPISODE 14 / PART 1 …)。大小写与字距来自 T.kicker。
export const Kicker: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children, style,
}) => {
  const u = useUnit();
  return (
    <div style={{
      color: T.color.accent, fontFamily: T.font, fontSize: u * 2.6, fontWeight: T.weight.med,
      letterSpacing: T.kicker.case === "upper" ? `${T.kicker.spacingEm}em` : u * 0.2,
      textTransform: T.kicker.case === "upper" ? "uppercase" : "none",
      ...style,
    }}>{children}</div>
  );
};

// --- 第 2 层:stagger 入场编排(editorial)。fade 主题的组件不调用这些。------
// 统一用 EASE_OUT,不 bounce(纪录片规矩)。所有位移用 useUnit 派生,分辨率无关。

// 0→1 绘出进度,delay 帧后开始,历时 TIMING.overlayIn。
export const useDraw = (delay = 0): number => {
  const f = useCurrentFrame();
  return interpolate(f, [delay, delay + TIMING.overlayIn], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
};

// 左→右擦入:inset(0 <right>% 0 0),right 从 100→0。
export const useClipReveal = (delay = 0): string => {
  const f = useCurrentFrame();
  const p = interpolate(f, [delay, delay + TIMING.reveal], [100, 0],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return `inset(0 ${p}% 0 0)`;
};

export type EntranceRole = "kicker" | "title" | "rule" | "sub";

// stagger 家族:每个角色错开 TIMING.stagger 帧登场。返回该帧的样式片段。
// title 用 clipPath 擦入,其余用 淡入+上浮。clip 在顶层无条件计算(满足 hook 规则)。
export const useEntrance = (role: EntranceRole): {
  opacity: number; transform: string; clipPath?: string;
} => {
  const f = useCurrentFrame();
  const u = useUnit();
  const order: Record<EntranceRole, number> = { kicker: 0, title: 1, rule: 2, sub: 3 };
  const delay = order[role] * TIMING.stagger;
  const clip = useClipReveal(delay);            // 无条件调用,满足 hook 规则
  const p = interpolate(f, [delay, delay + TIMING.reveal], [0, 1],
    { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (role === "title") return { opacity: p, transform: "none", clipPath: clip };
  const rise = interpolate(p, [0, 1], [u * 1.2, 0]);
  return { opacity: p, transform: `translateY(${rise}px)` };
};
