// LowerThird.tsx — 实体名条。props 不变:line1(实体) + line2(编辑体注解)。
// 样式全来自当前主题 T:teal=实心卡+左accent+左滑入;editorial=无卡骑 Scrim+stagger。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, usePop, bodyFont, dispItalic, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const LowerThird: React.FC<{ line1: string; line2?: string; durFrames?: number }> = ({
  line1, line2, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.8, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const e1 = useEntrance("title");   // 无条件调用(hook 规则);仅 stagger 用
  const e2 = useEntrance("sub");
  const pop = usePop();   // 主题设了 T.pop 才 ≠1;整卡 spring 缩放弹入(名条 pop-in)

  // 卡外层:fade=整卡淡入+左滑;stagger=整卡只淡入(元素各自动画)。pop 主题额外叠 spring 缩放。
  const cardStyle: React.CSSProperties = stagger
    ? { opacity: o, transform: `scale(${pop})`, transformOrigin: "left center" }
    : { opacity: o, transform: `translateX(${slide}px) scale(${pop})`, transformOrigin: "left center" };

  const line1Style: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontStyle: dispItalic(), fontSize: u * 6, fontWeight: T.weight.heavy,
    letterSpacing: -0.5, lineHeight: 1.05,
    ...(stagger ? { opacity: e1.opacity, clipPath: e1.clipPath } : null),
  };
  const line2Style: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: bodyFont(), fontSize: u * 3.6, fontWeight: T.weight.light,
    marginTop: u * 0.8,
    ...(stagger ? { opacity: e2.opacity, transform: e2.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 5) }}>
      {!T.card ? <Scrim heightPct={40} maxOpacity={0.9} /> : null}
      <Surface side="left" style={{ ...cardStyle, padding: `${u * 2.2}px ${u * 3}px` }}>
        <div style={line1Style}>{line1}</div>
        {line2 ? <div style={line2Style}>{line2}</div> : null}
      </Surface>
    </AbsoluteFill>
  );
};
