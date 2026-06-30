// SectionCard.tsx — chapter divider at a topic switch. Bottom-anchored over a
// soft scrim (NOT a full-frame black card that hides the speaker). Props:
// { kicker?, title } — kicker like "PART 2", title an editorial label that
// describes what's actually said next.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, useUnit, useFade, Scrim, anchorJustify, anchorPad } from "../anim";

export const SectionCard: React.FC<{ kicker?: string; title: string; durFrames?: number }> = ({
  kicker, title, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const p = interpolate(f, [0, TIMING.overlayIn], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={46} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 9, u * 6) }}>
        {kicker ? (
          <div style={{ color: ACCENT, fontSize: u * 2.6, fontWeight: 700,
                        letterSpacing: u * 0.4, marginBottom: u * 1.2 }}>{kicker}</div>
        ) : null}
        <div style={{ color: WHITE, fontSize: u * 8.5, fontWeight: 800, letterSpacing: -1, lineHeight: 1.0 }}>
          {title}
        </div>
        <div style={{ height: u * 0.6, width: u * 36 * p, background: ACCENT, marginTop: u * 2, borderRadius: u * 0.3 }} />
      </div>
    </AbsoluteFill>
  );
};
