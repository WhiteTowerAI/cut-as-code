// PromptCard.tsx — 提示词卡。props:segments[{t,hl?}] + kicker?(默认 "TRY PROMPTING")。
// 一张奶油卡,正文由内联片段拼成;hl:true 的片段着珊瑚(逐词高亮的家——BeforeAfter 指到
// 这里)。整段以引号排版,珊瑚高亮词是关键短语。颜色/字体/字重全来自 T,卡片淡入。
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { T, Surface, Kicker, useUnit, useFade, anchorJustify, anchorPad } from "../anim";

export const PromptCard: React.FC<{
  segments: { t: string; hl?: boolean }[]; kicker?: string; durFrames?: number;
}> = ({ segments, kicker = "TRY PROMPTING", durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 6, u * 6) }}>
      <Surface style={{ opacity: o, padding: `${u * 3.2}px ${u * 4}px`, maxWidth: "78%" }}>
        {kicker ? <Kicker style={{ marginBottom: u * 1.6 }}>{kicker}</Kicker> : null}
        <div style={{ fontFamily: T.font, fontSize: u * 4.4, fontWeight: T.weight.med,
                      lineHeight: 1.32, color: T.color.text }}>
          {segments.map((s, i) => (
            <span key={i} style={s.hl
              ? { color: T.color.accent, fontWeight: T.weight.heavy }
              : undefined}>
              {s.t}
            </span>
          ))}
        </div>
      </Surface>
    </AbsoluteFill>
  );
};
