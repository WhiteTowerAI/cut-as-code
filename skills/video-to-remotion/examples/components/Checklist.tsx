// Checklist.tsx — 编号清单卡。props:items[] + kicker?。珊瑚 01/02/03 序号 + 墨字条目,
// 一张奶油卡上逐条错峰入场(与 ListReveal 同一 stagger 数学,但骑在实心 Surface 上而非
// 整条 Backdrop)。ListReveal 是"全宽 scrim/整屏"列表;Checklist 是"卡片内"列表——
// 作者按构图挑一个。序号补零走 String(i+1).padStart(2,"0"),颜色/字体全来自 T。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { T, Surface, Kicker, useUnit, useFade, TIMING, EASE_OUT, anchorJustify, anchorPad } from "../anim";

export const Checklist: React.FC<{ items: string[]; kicker?: string; durFrames?: number }> = ({
  items, kicker, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 6) }}>
      <Surface style={{ opacity: o, padding: `${u * 3}px ${u * 4}px`,
                        display: "flex", flexDirection: "column", gap: u * 1.8 }}>
        {kicker ? <Kicker style={{ marginBottom: u * 0.6 }}>{kicker}</Kicker> : null}
        {items.map((it, i) => {
          const at = TIMING.reveal + i * TIMING.stagger;
          const p = interpolate(frame, [at, at + TIMING.reveal], [0, 1],
            { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ opacity: p, transform: `translateX(${interpolate(p, [0, 1], [u * 2, 0])}px)`,
                                  display: "flex", alignItems: "baseline", gap: u * 2 }}>
              <span style={{ color: T.color.accent, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.heavy,
                             fontVariantNumeric: "tabular-nums" }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span style={{ color: T.color.text, fontFamily: T.font, fontSize: u * 4, fontWeight: T.weight.med }}>{it}</span>
            </div>
          );
        })}
      </Surface>
    </AbsoluteFill>
  );
};
