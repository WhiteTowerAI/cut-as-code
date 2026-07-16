import type {
  TitleOverlayPosition,
  TitleOverlayStyleOverrides,
  TitleOverlayTheme,
} from "./overlay-presets.ts";

export type TitleSource =
  | { type: "manual" }
  | {
      type: "video-to-shorts";
      planPath?: string;
      previewHtmlPath?: string;
      selector: {
        by: "order" | "id" | "short_id" | "filename";
        value: string | number;
      };
    };

export type TitleOverlayVisibility =
  | { mode: "entire" }
  | { mode: "first-n-seconds"; durationSec: number }
  | { mode: "time-range"; startTimeSec: number; endTimeSec: number };

export type TitleOverlayConfig = {
  schemaVersion: "title-overlay.v1";
  source: {
    videoPath: string;
    sourceMetaPath: string;
  };
  title: {
    text: string;
    source: TitleSource;
  };
  style: {
    preset: "shorts-title";
    theme: TitleOverlayTheme;
    overrides?: TitleOverlayStyleOverrides;
  };
  layout: {
    position: TitleOverlayPosition;
    customYRatio?: number;
    avoidBottomCaptionArea: true;
  };
  visibility: TitleOverlayVisibility;
  animation: {
    type: "none";
  };
};

export const titleOverlayConfig: TitleOverlayConfig = {
  schemaVersion: "title-overlay.v1",
  source: {
    videoPath: "public/source.mp4",
    sourceMetaPath: "src/source-meta.json",
  },
  title: {
    text: "STOP SCROLLING",
    source: {
      type: "manual",
    },
  },
  style: {
    preset: "shorts-title",
    theme: "green",
    overrides: {},
  },
  layout: {
    position: "upper-third",
    avoidBottomCaptionArea: true,
  },
  visibility: {
    mode: "entire",
  },
  animation: {
    type: "none",
  },
};
