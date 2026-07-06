// Outro.tsx — 片尾卡。props:title + sub + small(+ almanac 的 mark spark glyph)。
// teal:纯淡入(原样,左竖 accent 条);editorial:title 擦入 → sub/small 依次登场。
// almanac(fullBleed):整屏奶油底,居中 spark 字符 + wordmark 锁版(spark + 标题的收尾锁版)。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Backdrop, useUnit, useFade, useEntrance, anchorJustify, anchorPad } from "../anim";

export const Outro: React.FC<{
  title: string; sub?: string; small?: string; mark?: string; durFrames?: number;
}> = ({ title, sub, small, mark = "✳", durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const stagger = T.motion === "stagger";
  const eKicker = useEntrance("kicker");   // fullBleed 分支给 spark 用;其余主题算而不用
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

  // almanac:整屏奶油,居中 spark 字符 + wordmark 竖向锁版。spark 走 kicker 拍先登场,
  // title 擦入,sub/small 收尾。mark 是作者传入的普通字符(默认 ✳),非任何品牌 logo 重绘。
  if (T.fullBleed) {
    const sparkStyle: React.CSSProperties = {
      color: T.color.accent, fontFamily: T.font, fontSize: u * 9, lineHeight: 1, marginBottom: u * 2,
      ...(stagger ? { opacity: eKicker.opacity, transform: eKicker.transform } : null),
    };
    return (
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Backdrop heightPct={50} maxOpacity={0.92} />
        <div style={{ opacity: o, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
          {mark ? <div style={sparkStyle}>{mark}</div> : null}
          <div style={{ ...titleStyle, letterSpacing: -1 }}>{title}</div>
          {sub ? <div style={{ ...subStyle, marginTop: u * 1.4 }}>{sub}</div> : null}
          {small ? <div style={smallStyle}>{small}</div> : null}
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Backdrop heightPct={50} maxOpacity={0.92} />
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
