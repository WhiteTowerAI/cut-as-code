import * as React from "react";
import { AbsoluteFill } from "remotion";
import { Caption, Cue } from "./Caption";
import { previewConfig } from "./preview-config.ts";
import type { CaptionPresetName, CaptionStyleOverrides } from "./caption-presets.ts";

type CaptionPreviewProps = {
  preset?: CaptionPresetName;
  karaoke?: boolean;
  overrides?: CaptionStyleOverrides;
  timeSec?: number;
  sampleText?: string;
};

export const cueForPreview = (text: string, timeSec: number, durationSec: number): Cue => {
  const tokens = text.split(/\s+/).filter(Boolean);
  const start = Math.max(0, timeSec - durationSec / 2);
  const step = durationSec / Math.max(tokens.length, 1);

  return {
    index: 1,
    start,
    end: start + durationSec,
    text,
    lines: [text],
    words: tokens.map((word, index) => ({
      word,
      start: start + index * step,
      end: start + (index + 1) * step,
    })),
  };
};

export const CaptionPreview: React.FC<CaptionPreviewProps> = ({
  preset = "clean",
  karaoke,
  overrides,
  timeSec = previewConfig.timeSec,
  sampleText = previewConfig.sampleText,
}) => (
  <AbsoluteFill style={{
    background: "linear-gradient(135deg, #20242d 0%, #454b5c 48%, #1b1d24 100%)",
  }}>
    <Caption
      captions={[cueForPreview(sampleText, timeSec, previewConfig.durationSec)]}
      karaoke={karaoke}
      styleSelection={{ preset, overrides }}
    />
  </AbsoluteFill>
);
