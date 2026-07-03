// KeypointCallout.tsx — 金句/问题卡。props 不变:text。
// teal=实心卡+左accent+上浮;editorial=无卡骑 scrim + title 擦入。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const KeypointCallout: React.FC<{ text: string; durFrames?: number }> = ({ text, durFrames }) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const rise = interpolate(f, [0, TIMING.reveal], [u * 1.4, 0],
    { easing: EASE_OUT, extrapolateRight: "clamp" });
  const e = useEntrance("title");

  const cardStyle: React.CSSProperties = stagger
    ? { opacity: o, maxWidth: "72%" }
    : { opacity: o, transform: `translateY(${rise}px)`, maxWidth: "72%" };
  const textStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 5, fontWeight: T.weight.med, lineHeight: 1.18,
    ...(stagger ? { opacity: e.opacity, clipPath: e.clipPath } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-start",
                           padding: anchorPad(u * 8, u * 5, u * 8) }}>
      {!T.card ? <Scrim heightPct={45} maxOpacity={0.9} /> : null}
      <Surface side="left" style={{ ...cardStyle, padding: `${u * 2.4}px ${u * 3}px` }}>
        <div style={textStyle}>{text}</div>
      </Surface>
    </AbsoluteFill>
  );
};
