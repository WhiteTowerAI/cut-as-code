// CommandChips.tsx — 命令 + 说明清单卡。props:items[{cmd,desc}] + kicker?(默认
// "WHAT'S NEW")。每行:等宽 cmd chip(浅暖底 + 珊瑚描边)+ 衬线 desc。等宽体走系统栈
// (ui-monospace...)——主题字 T.font 是衬线,命令用等宽才读得像命令。颜色/间距来自 T,
// 逐行错峰入场(与 Checklist 同一 stagger 数学)。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { T, Surface, Kicker, useUnit, useFade, TIMING, EASE_OUT, anchorJustify, anchorPad, hexA } from "../anim";

const MONO = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace';

export const CommandChips: React.FC<{
  items: { cmd: string; desc: string }[]; kicker?: string; durFrames?: number;
}> = ({ items, kicker = "WHAT'S NEW", durFrames }) => {
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
                                  display: "flex", alignItems: "center", gap: u * 2 }}>
              <span style={{ fontFamily: MONO, fontSize: u * 2.8, fontWeight: 500, color: T.color.accent,
                             background: hexA(T.color.accent, 0.1), border: `${u * 0.12}px solid ${hexA(T.color.accent, 0.5)}`,
                             borderRadius: u * 0.6, padding: `${u * 0.6}px ${u * 1.2}px`, whiteSpace: "nowrap" }}>
                {it.cmd}
              </span>
              <span style={{ color: T.color.text, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.light }}>{it.desc}</span>
            </div>
          );
        })}
      </Surface>
    </AbsoluteFill>
  );
};
