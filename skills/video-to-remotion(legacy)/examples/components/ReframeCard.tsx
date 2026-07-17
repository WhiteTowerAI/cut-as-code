// ReframeCard.tsx — 重构表达卡(t107)。props:instead(必填)+ avoid?(可选)+ kicker?
// (默认 "CONTEXT, NOT CONSTRAINTS")。一张奶油卡:可选的次色删除线 "avoid" 行 → 珊瑚小标
// "INSTEAD SAY" → 珊瑚强调的 instead 行。是 KeypointCallout 的 almanac 味渲染器(同类内容,
// 作者按主题挑一个)。颜色/字体来自 T,卡片淡入 + stagger 上浮。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Surface, Kicker, useUnit, useFade, useEntrance, anchorJustify, anchorPad } from "../anim";

export const ReframeCard: React.FC<{
  instead: string; avoid?: string; kicker?: string; durFrames?: number;
}> = ({ instead, avoid, kicker = "CONTEXT, NOT CONSTRAINTS", durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const stagger = T.motion === "stagger";
  const eSub = useEntrance("sub");
  const eTitle = useEntrance("title");

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 6, u * 6) }}>
      <Surface style={{ opacity: o, padding: `${u * 3.2}px ${u * 4}px`, maxWidth: "76%" }}>
        {kicker ? <Kicker style={{ marginBottom: u * 1.6 }}>{kicker}</Kicker> : null}
        {avoid ? (
          <div style={{ color: T.color.textMuted, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.light,
                        textDecoration: "line-through", marginBottom: u * 1.6,
                        ...(stagger ? { opacity: eSub.opacity, transform: eSub.transform } : null) }}>
            {avoid}
          </div>
        ) : null}
        <div style={{ color: T.color.textMuted, fontFamily: T.font, fontSize: u * 2.2, fontWeight: T.kicker.weight,
                      letterSpacing: `${T.kicker.spacingEm}em`,
                      textTransform: T.kicker.case === "upper" ? "uppercase" : "none", marginBottom: u * 1 }}>
          Instead say
        </div>
        <div style={{ color: T.color.accent, fontFamily: T.font, fontSize: u * 5, fontWeight: T.weight.heavy,
                      lineHeight: 1.15,
                      ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null) }}>
          {instead}
        </div>
      </Surface>
    </AbsoluteFill>
  );
};
