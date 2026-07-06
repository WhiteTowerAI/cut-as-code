// TitleBumper.tsx — 整屏标题接管(almanac 的招牌时刻)。props:title + kicker?。
// 用 <Backdrop>:fullBleed 主题铺满不透明奶油底,画面消失;非 fullBleed 主题退化为
// Scrim 渐变(仍可用,只是不再整屏接管)。大号 Newsreader 墨字,左对齐落在左下三分区
// (对齐视频构图,非居中)。stagger:kicker → title 擦入。尺寸全用 u,分辨率无关。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import {
  T, Backdrop, Kicker, useUnit, useFade, useEntrance, anchorJustify, anchorPad,
} from "../anim";

export const TitleBumper: React.FC<{ title: string; kicker?: string; durFrames?: number }> = ({
  title, kicker, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const stagger = T.motion === "stagger";
  const eKicker = useEntrance("kicker");
  const eTitle = useEntrance("title");

  const titleStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 10, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1.0, maxWidth: "72%",
    ...(stagger ? { opacity: eTitle.opacity, clipPath: eTitle.clipPath } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Backdrop />
      <div style={{ opacity: o, padding: anchorPad(u * 12, u * 8) }}>
        {kicker ? (
          <Kicker style={{ marginBottom: u * 1.6,
            ...(stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null) }}>
            {kicker}
          </Kicker>
        ) : null}
        <div style={titleStyle}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};
