// Outro.tsx — sign-off card over the closing. Bottom-band over a scrim.
// Props: { title, sub?, small? }. Grounded in the actual sign-off.
import * as React from "react";
import { AbsoluteFill } from "remotion";
import { ACCENT, WHITE, MUTED, useUnit, useFade, Scrim } from "../anim";

export const Outro: React.FC<{ title: string; sub?: string; small?: string; durFrames?: number }> = ({
  title, sub, small, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start" }}>
      <Scrim heightPct={50} maxOpacity={0.92} />
      <div style={{ opacity: o, display: "flex", gap: u * 2.4, padding: `0 0 ${u * 9}px ${u * 6}px` }}>
        <div style={{ width: u * 0.8, background: ACCENT, borderRadius: u * 0.4 }} />
        <div>
          <div style={{ color: WHITE, fontSize: u * 8.5, fontWeight: 800, letterSpacing: -1, lineHeight: 1 }}>
            {title}
          </div>
          {sub ? (
            <div style={{ color: WHITE, fontSize: u * 3.6, fontWeight: 600, marginTop: u * 1.4 }}>{sub}</div>
          ) : null}
          {small ? (
            <div style={{ color: MUTED, fontSize: u * 2.8, fontWeight: 500, marginTop: u * 0.8 }}>{small}</div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};
