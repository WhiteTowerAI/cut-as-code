// Intro.tsx — title card over the cold open (show/brand + host). Bottom-band
// over a scrim. Props: { kicker?, title, sub? }. Ground the text: real show
// name, real host name (correct ASR mis-hearings; verify a headline name).
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, MUTED, useUnit, useFade, Scrim } from "../anim";

export const Intro: React.FC<{ kicker?: string; title: string; sub?: string; durFrames?: number }> = ({
  kicker, title, sub, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const slide = interpolate(f, [0, TIMING.overlayIn], [u * 1.6, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={{ opacity: o, transform: `translateY(${slide}px)`, display: "flex",
                    gap: u * 2.4, padding: `0 0 ${u * 9}px ${u * 6}px` }}>
        <div style={{ width: u * 0.8, background: ACCENT, borderRadius: u * 0.4 }} />
        <div>
          {kicker ? (
            <div style={{ color: ACCENT, fontSize: u * 2.6, fontWeight: 700,
                          letterSpacing: u * 0.4, marginBottom: u * 1 }}>{kicker}</div>
          ) : null}
          <div style={{ color: WHITE, fontSize: u * 10, fontWeight: 800, letterSpacing: -1.5, lineHeight: 0.98 }}>
            {title}
          </div>
          {sub ? (
            <div style={{ color: MUTED, fontSize: u * 3.4, fontWeight: 500, marginTop: u * 1.4 }}>{sub}</div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
