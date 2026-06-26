// KeypointCallout.tsx — pins a punchy line / question, as a bottom-left quote
// card (NOT dark text floating over the footage). Props: { text }. Keep it
// short and rewritten — a tight paraphrase reads better than a raw clause.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, CARD, useUnit, useFade } from "../anim";

export const KeypointCallout: React.FC<{ text: string; durFrames?: number }> = ({ text, durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const rise = interpolate(f, [0, TIMING.reveal], [u * 1.4, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start",
                           padding: `0 ${u * 8}px ${u * 8}px ${u * 5}px` }}>
      <div style={{
        opacity: o, transform: `translateY(${rise}px)`, maxWidth: "72%",
        background: CARD, borderLeft: `${u * 0.8}px solid ${ACCENT}`, borderRadius: u * 1.2,
        padding: `${u * 2.4}px ${u * 3}px`, boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
      }}>
        <div style={{ color: WHITE, fontSize: u * 5, fontWeight: 600, lineHeight: 1.18 }}>{text}</div>
      </div>
    </AbsoluteFill>
  );
};
