// ListReveal.tsx — staggered enumeration ("three ways ..."), bottom-anchored
// over a scrim so each item is legible on footage. Props: { title?, items[] }.
// The analyzer detects the count; the agent WRITES the items from the transcript.
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { TIMING, EASE_OUT, ACCENT, WHITE, useUnit, useFade, Scrim, anchorJustify, anchorPad } from "../anim";

export const ListReveal: React.FC<{ title?: string; items: string[]; durFrames?: number }> = ({
  title, items, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start" }}>
      <Scrim heightPct={62} maxOpacity={0.9} />
      <div style={{ opacity: o, padding: anchorPad(u * 8, u * 6),
                    display: "flex", flexDirection: "column", gap: u * 1.6 }}>
        {title ? (
          <div style={{ color: ACCENT, fontSize: u * 3, fontWeight: 700,
                        letterSpacing: u * 0.3, marginBottom: u * 1 }}>{title}</div>
        ) : null}
        {items.map((it, i) => {
          const at = TIMING.reveal + i * TIMING.stagger;
          const p = interpolate(frame, [at, at + TIMING.reveal], [0, 1],
            { easing: EASE_OUT, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={i} style={{ opacity: p, transform: `translateX(${interpolate(p, [0, 1], [u * 2, 0])}px)`,
                                  display: "flex", alignItems: "baseline", gap: u * 2 }}>
              <span style={{ color: ACCENT, fontSize: u * 4, fontWeight: 800 }}>{String(i + 1).padStart(2, "0")}</span>
              <span style={{ color: WHITE, fontSize: u * 5, fontWeight: 600 }}>{it}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
