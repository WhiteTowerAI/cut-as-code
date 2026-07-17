import * as React from "react";
import { AbsoluteFill } from "remotion";
import { titleOverlayConfig } from "./overlay-config";
import { TitleOverlay } from "./TitleOverlay";
import sourceMeta from "./source-meta.json.example";
import type { TitleOverlayTheme } from "./overlay-presets";

type TitlePreviewProps = {
  theme?: TitleOverlayTheme;
  title?: string;
};

export const TitlePreview: React.FC<TitlePreviewProps> = ({ theme, title }) => {
  const meta = sourceMeta;
  const captionSafeAreaHeight = meta.height * 0.32;

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, #263241 0%, #52606d 42%, #151922 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: "8% 11% 39% 11%",
          border: "2px solid rgba(255,255,255,0.2)",
          borderRadius: 30,
          background: "rgba(255,255,255,0.08)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "10%",
          right: "10%",
          bottom: captionSafeAreaHeight * 0.35,
          height: captionSafeAreaHeight * 0.32,
          border: "2px dashed rgba(255,255,255,0.34)",
          borderRadius: 16,
          background: "rgba(0,0,0,0.18)",
        }}
      />
      <TitleOverlay
        config={titleOverlayConfig}
        meta={meta}
        theme={theme}
        title={title}
      />
    </AbsoluteFill>
  );
};
