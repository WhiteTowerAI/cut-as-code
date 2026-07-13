// KeypointLedger.tsx — the real component (one static design PNG, rebuilt as code)
//
// The point of the whole workflow: a flat design frame becomes JSX where every
// word, color and beat is a *prop you can prompt*. Beats are frame-driven via
// interpolate() — no keyframes in a timeline, just numbers in code.
import * as React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { EASE_OUT } from "./anim";

const cream = "#F5F4ED";

const text: React.CSSProperties = {
  fontFamily: "var(--serif)",
  fontSize: 64,
  lineHeight: 1.15,
  color: cream,
};

export const KeypointLedger: React.FC<{
  // frame where beat 2 fires — set it to land on a spoken word
  // (frame = word_start_seconds * fps). See FinalEdit.tsx.
  beat2At: number;
}> = ({ beat2At }) => {
  const frame = useCurrentFrame();

  // Beat 2: right column lights up, left grays + strikes
  const beat2 = interpolate(frame,
    [beat2At, beat2At + 12], [0, 1],
    { easing: EASE_OUT });

  return (
    <>
      <div style={{ ...text, color: cream, opacity: 1 - beat2 }}>
        &ldquo;Is Claude doing the work right?&rdquo;
      </div>
      <div style={{ ...text, opacity: beat2,
                   textDecoration: "line-through" }}>
        &ldquo;Is Claude doing the work right?&rdquo;
      </div>
    </>
  );
};
