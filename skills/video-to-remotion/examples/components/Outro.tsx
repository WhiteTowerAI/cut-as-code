// Outro.tsx — 片尾卡。props 不变:title + sub + small。scrim 类,左竖 accent 条。
// teal:纯淡入(原样);editorial:title 擦入 → sub/small 依次登场。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Scrim, useUnit, useFade, useEntrance, anchorJustify, anchorPad } from "../anim";

export const Outro: React.FC<{ title: string; sub?: string; small?: string; durFrames?: number }> = ({
  title, sub, small, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const stagger = T.motion === "stagger";
  const eTitle = useEntrance("title");
  const eSub = useEntrance("sub");

  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 8.5, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1,
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };
  const subStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 3.6, fontWeight: T.weight.med, marginTop: u * 1.4,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };
  const smallStyle: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 2.8, fontWeight: T.weight.light, marginTop: u * 0.8,
    ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={{ opacity: o, display: "flex", gap: u * 2.4, padding: anchorPad(u * 9, u * 6) }}>
        <div style={{ width: u * 0.8, background: T.color.accent, borderRadius: u * 0.4 }} />
        <div>
          <div style={titleStyle}>{title}</div>
          {sub ? <div style={subStyle}>{sub}</div> : null}
          {small ? <div style={smallStyle}>{small}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
