// BeforeAfter.tsx — 对照卡(t037)。props:before + after(+ 各自 label/sub 可选)。
// 一张奶油卡,中间一条 hairline 分两栏。左:删除线 + 次色墨字,标签 "BEFORE";
// 右:满墨字 + 珊瑚 kicker 标签(默认 "AFTER",作者可传品牌语)。样式全来自 T。
// ponytail:后段的"珊瑚高亮词"由 PromptCard 的 segments 模式负责(那才是逐词高亮的家);
// 这里对照卡的主信号是"删除线↔干净"+珊瑚标签,不再重复造一个逐词高亮器。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Surface, Kicker, useUnit, useFade, anchorJustify, anchorPad } from "../anim";

export const BeforeAfter: React.FC<{
  before: string; after: string;
  beforeLabel?: string; afterLabel?: string;
  beforeSub?: string; afterSub?: string; durFrames?: number;
}> = ({ before, after, beforeLabel = "BEFORE", afterLabel = "AFTER", beforeSub, afterSub, durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);

  const colLabelMuted: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 2.2, fontWeight: T.kicker.weight,
    letterSpacing: `${T.kicker.spacingEm}em`,
    textTransform: T.kicker.case === "upper" ? "uppercase" : "none", marginBottom: u * 1.2,
  };
  const valueBase: React.CSSProperties = {
    fontFamily: T.font, fontSize: u * 4.6, fontWeight: T.weight.med, lineHeight: 1.15,
  };
  const subBase: React.CSSProperties = {
    color: T.color.textMuted, fontFamily: T.font, fontSize: u * 2.6, fontWeight: T.weight.light, marginTop: u * 1,
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 6, u * 6) }}>
      <Surface style={{ opacity: o, padding: `${u * 3}px ${u * 3.6}px`, display: "flex", gap: u * 3.6 }}>
        <div style={{ flex: 1 }}>
          <div style={colLabelMuted}>{beforeLabel}</div>
          <div style={{ ...valueBase, color: T.color.textMuted, textDecoration: "line-through" }}>{before}</div>
          {beforeSub ? <div style={subBase}>{beforeSub}</div> : null}
        </div>
        <div style={{ width: u * 0.15, alignSelf: "stretch", background: T.color.textMuted, opacity: 0.35 }} />
        <div style={{ flex: 1 }}>
          <Kicker style={{ fontSize: u * 2.2, marginBottom: u * 1.2 }}>{afterLabel}</Kicker>
          <div style={{ ...valueBase, color: T.color.text }}>{after}</div>
          {afterSub ? <div style={subBase}>{afterSub}</div> : null}
        </div>
      </Surface>
    </AbsoluteFill>
  );
};
