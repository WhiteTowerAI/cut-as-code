// SectionCard.tsx — 章节卡。props 不变:kicker + title。scrim 类(两主题都骑 Scrim)。
// teal:title 下青色条按 overlayIn 描出;editorial:kicker→title 擦入→hairline 描出。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Backdrop, Kicker, Rule, useUnit, useFade, useEntrance, useDraw, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const SectionCard: React.FC<{ kicker?: string; title: string; durFrames?: number }> = ({
  kicker, title, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const pFade = interpolate(f, [0, TIMING.overlayIn], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  const eKicker = useEntrance("kicker");
  const eTitle = useEntrance("title");
  const drawStagger = useDraw(2 * TIMING.stagger);          // rule 在第 3 拍描出

  const kickerExtra = stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null;
  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 8.5, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1.0,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const ruleProgress = stagger ? drawStagger : pFade;        // teal 用旧的 overlayIn 描出

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Backdrop heightPct={46} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 9, u * 6) }}>
        {kicker ? <Kicker style={{ marginBottom: u * 1.2, ...kickerExtra }}>{kicker}</Kicker> : null}
        <div style={titleStyle}>{title}</div>
        <div style={{ marginTop: u * 2 }}><Rule widthU={36} progress={ruleProgress} /></div>
      </div>
    </AbsoluteFill>
  );
};
