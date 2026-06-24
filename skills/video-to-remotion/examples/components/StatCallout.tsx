// StatCallout.tsx — a number worth flagging, as a bottom-right card (NOT a
// giant number centered over the face). Props: { value, label? }. The numeric
// part counts up on entrance. Often a stat reads better folded into a
// LowerThird's line2 ("Wellington College / a 62-19 blowout") — reach for that
// first; use this when the number itself is the point.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, CARD, useUnit, useFade } from "../anim";

export const StatCallout: React.FC<{ value: string; label?: string; durFrames?: number }> = ({
  value, label, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const p = interpolate(f, [0, TIMING.reveal], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  const num = parseFloat(value.replace(/[^\d.]/g, ""));
  const prefix = (value.match(/^\D*/) ?? [""])[0];
  const suffix = (value.match(/\D*$/) ?? [""])[0];
  const display = isNaN(num) ? value : prefix + Math.round(num * p).toLocaleString() + suffix;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-end",
                           padding: `0 ${u * 5}px ${u * 8}px 0` }}>
      <div style={{
        opacity: o, display: "flex", alignItems: "baseline", gap: u * 1.6,
        background: CARD, borderRadius: u * 1.2, borderBottom: `${u * 0.6}px solid ${ACCENT}`,
        padding: `${u * 1.8}px ${u * 3}px`, boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
      }}>
        <div style={{ color: ACCENT, fontSize: u * 9, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
          {display}
        </div>
        {label ? (
          <div style={{ color: WHITE, fontSize: u * 3.4, fontWeight: 600 }}>{label}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
