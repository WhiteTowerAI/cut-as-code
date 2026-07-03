// Intro.tsx — 片头卡。props 不变:kicker + title + sub。scrim 类,左侧竖 accent 条。
// teal:整体上滑淡入;editorial:kicker→title 擦入→sub 依次登场,竖条着 accent 色。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Scrim, Kicker, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const Intro: React.FC<{ kicker?: string; title: string; sub?: string; durFrames?: number }> = ({
  kicker, title, sub, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.6, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const eKicker = useEntrance("kicker");
  const eTitle = useEntrance("title");
  const eSub = useEntrance("sub");

  const outer: React.CSSProperties = stagger
    ? { opacity: o, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) }
    : { opacity: o, transform: `translateY(${slide}px)`, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) };
  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 10, fontWeight: T.weight.heavy,
    letterSpacing: -1.5, lineHeight: 0.98,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const subStyle: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.light, marginTop: u * 1.4,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={outer}>
        <div style={{ width: u * 0.8, background: T.color.accent, borderRadius: u * 0.4 }} />
        <div>
          {kicker ? <Kicker style={{ marginBottom: u * 1, ...(stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null) }}>{kicker}</Kicker> : null}
          <div style={titleStyle}>{title}</div>
          {sub ? <div style={subStyle}>{sub}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
