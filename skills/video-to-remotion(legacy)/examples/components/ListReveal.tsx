// ListReveal.tsx — 枚举列表。props 不变:title + items[]。scrim 类。
// 逐条错峰入场(两主题都保留);颜色/字体来自 T。title 不走 <Kicker>(它是混合大小写
// 且更大,u*3),内联一个 div 但仍读 T.color.accent/T.font/T.kicker.weight。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Backdrop, useUnit, useFade, bodyFont, dispItalic, TIMING, EASE_OUT, anchorJustify, anchorPad,
} from "../anim";

export const ListReveal: React.FC<{ title?: string; items: string[]; durFrames?: number }> = ({
  title, items, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Backdrop heightPct={62} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 8, u * 6),
                    display: "flex", flexDirection: "column", gap: u * 1.6 }}>
        {title ? (
          <div style={{ color: T.color.accent, fontFamily: T.font, fontStyle: dispItalic(), fontSize: u * 3, fontWeight: T.kicker.weight,
                        letterSpacing: u * 0.3, marginBottom: u * 1 }}>{title}</div>
        ) : null}
        {items.map((it, i) => {
          const at = TIMING.reveal + i * TIMING.stagger;
          const p = interpolate(frame, [at, at + TIMING.reveal], [0, 1],
            { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ opacity: p, transform: `translateX(${interpolate(p, [0, 1], [u * 2, 0])}px)`,
                                  display: "flex", alignItems: "baseline", gap: u * 2 }}>
              <span style={{ color: T.listNumColors?.[i] ?? T.color.accent, fontFamily: T.font, fontStyle: dispItalic(), fontSize: u * 4, fontWeight: T.weight.heavy }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ color: T.color.text, fontFamily: bodyFont(), fontSize: u * 5, fontWeight: T.weight.med }}>{it}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
