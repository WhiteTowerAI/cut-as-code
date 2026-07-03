// StatCallout.tsx — 数字 callout。props 不变:value(数字串) + label。
// 数字入场滚动(两主题都保留)。teal=实心卡+下accent;editorial=无卡骑 scrim。
import * as React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import {
  T, Surface, Scrim, useUnit, useFade, useEntrance, TIMING, EASE_OUT,
  anchorJustify, anchorPad,
} from "../anim";

export const StatCallout: React.FC<{ value: string; label?: string; durFrames?: number }> = ({
  value, label, durFrames,
}) => {
  const u = useUnit();
  const o = useFade(durFrames);
  const f = useCurrentFrame();
  const stagger = T.motion === "stagger";
  const p = interpolate(f, [0, TIMING.reveal], [0, 1], { easing: EASE_OUT, extrapolateRight: "clamp" });
  const num = parseFloat(value.replace(/[^\d.]/g, ""));
  const prefix = (value.match(/^\D*/) ?? [""])[0];
  const suffix = (value.match(/\D*$/) ?? [""])[0];
  const display = isNaN(num) ? value : prefix + Math.round(num * p).toLocaleString() + suffix;
  const eLabel = useEntrance("sub");

  const valueStyle: React.CSSProperties = {
    color: T.color.accent, fontFamily: T.font, fontSize: u * 9, fontWeight: T.weight.heavy,
    letterSpacing: -1, lineHeight: 1,
  };
  const labelStyle: React.CSSProperties = {
    color: T.color.text, fontFamily: T.font, fontSize: u * 3.4, fontWeight: T.weight.med,
    ...(stagger ? { opacity: eLabel.opacity, transform: eLabel.transform } : null),
  };

  return (
    <AbsoluteFill style={{ justifyContent: anchorJustify(), alignItems: "flex-end",
                           padding: anchorPad(u * 8, 0, u * 5) }}>
      {!T.card ? <Scrim heightPct={40} maxOpacity={0.9} /> : null}
      <Surface side="bottom" widthU={0.6} style={{
        opacity: o, display: "flex", alignItems: "baseline", gap: u * 1.6,
        padding: `${u * 1.8}px ${u * 3}px`,
      }}>
        <div style={valueStyle}>{display}</div>
        {label ? <div style={labelStyle}>{label}</div> : null}
      </Surface>
    </AbsoluteFill>
  );
};
