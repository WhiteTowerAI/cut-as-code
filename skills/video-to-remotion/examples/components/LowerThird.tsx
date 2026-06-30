// LowerThird.tsx — name bar at the first mention of a person/team/key fact.
// Props: { line1, line2? } — line1 is the entity, line2 a one-line editorial
// gloss (WRITE it from the transcript; don't paste a raw fragment). Dark card,
// bottom-left, teal edge — readable over any footage, never covers the face.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, MUTED, CARD, useUnit, useFade, anchorJustify, anchorPad } from "../anim";

export const LowerThird: React.FC<{ line1: string; line2?: string; durFrames?: number }> = ({
  line1, line2, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.8, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 5) }}>
      <div style={{
        opacity: o, transform: `translateX(${slide}px)`,
        background: CARD, borderRadius: u * 1.2, borderLeft: `${u * 0.8}px solid ${ACCENT}`,
        padding: `${u * 2.2}px ${u * 3}px`, boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
      }}>
        <div style={{ color: WHITE, fontSize: u * 6, fontWeight: 800, letterSpacing: -0.5, lineHeight: 1.05 }}>
          {line1}
        </div>
        {line2 ? (
          <div style={{ color: MUTED, fontSize: u * 3.6, fontWeight: 500, marginTop: u * 0.8 }}>{line2}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
