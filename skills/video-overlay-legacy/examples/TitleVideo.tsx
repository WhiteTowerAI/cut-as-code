import * as React from "react";
import { AbsoluteFill, OffthreadVideo, staticFile } from "remotion";
import { titleOverlayConfig } from "./overlay-config";
import { TitleOverlay } from "./TitleOverlay";
import sourceMeta from "./source-meta.json.example";
import type { TitleOverlayTheme } from "./overlay-presets";

type TitleVideoProps = {
  theme?: TitleOverlayTheme;
  title?: string;
};

const publicSource = titleOverlayConfig.source.videoPath.replace(/^public[\\/]/, "");

export const TitleVideo: React.FC<TitleVideoProps> = ({ theme, title }) => (
  <AbsoluteFill style={{ backgroundColor: "#111827" }}>
    <OffthreadVideo
      src={staticFile(publicSource)}
      style={{
        width: "100%",
        height: "100%",
        objectFit: "cover",
      }}
    />
    <TitleOverlay
      config={titleOverlayConfig}
      meta={sourceMeta}
      theme={theme}
      title={title}
    />
  </AbsoluteFill>
);
