// CaptionsOverlay.tsx - transparent caption-only composition for ffmpeg overlay.
//
// No video background and no opaque fill: alpha must stay transparent for the
// ProRes 4444 + PNG-frame render path.
import * as React from "react";
import { AbsoluteFill } from "remotion";
import captions from "./captions.json";
import { Caption, Cue } from "./Caption";

export const CaptionsOverlay: React.FC = () => (
  <AbsoluteFill>
    <Caption captions={captions as Cue[]} />
  </AbsoluteFill>
);
