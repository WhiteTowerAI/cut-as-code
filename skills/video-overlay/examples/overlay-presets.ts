export type TitleOverlayPresetName = "shorts-title";
export type TitleOverlayTheme = "green" | "yellow" | "orange";
export type TitleOverlayPosition = "top" | "upper-third" | "custom";
export type TitleOverlayAnimationType = "none";

export type TitleOverlayStyle = {
  preset: TitleOverlayPresetName;
  theme: TitleOverlayTheme;
  font: {
    family: string;
    sizeRatio: number;
    weight: number;
    color: string;
    lineHeight: number;
    letterSpacing: number;
    textTransform: "none" | "uppercase";
  };
  layout: {
    position: TitleOverlayPosition;
    align: "center";
    maxWidthRatio: number;
    yRatio: number;
    avoidBottomCaptionArea: true;
    bottomCaptionSafeAreaRatio: number;
  };
  accent: {
    color: string;
    backgroundColor: string;
    backgroundOpacity: number;
  };
  effects: {
    shadow: {
      strength: "soft" | "strong";
      color: string;
      opacity: number;
      offsetYRatio: number;
      blurRatio: number;
    };
    stroke: {
      color: string;
      opacity: number;
      widthRatio: number;
    };
  };
  animation: {
    type: TitleOverlayAnimationType;
  };
};

export type TitleOverlayStyleOverrides = {
  font?: Partial<TitleOverlayStyle["font"]>;
  layout?: Partial<Omit<TitleOverlayStyle["layout"], "avoidBottomCaptionArea">> & {
    avoidBottomCaptionArea?: true;
  };
  accent?: Partial<TitleOverlayStyle["accent"]>;
  effects?: {
    shadow?: Partial<TitleOverlayStyle["effects"]["shadow"]>;
    stroke?: Partial<TitleOverlayStyle["effects"]["stroke"]>;
  };
  animation?: Partial<TitleOverlayStyle["animation"]>;
};

export type TitleOverlayStyleSelection = {
  preset: TitleOverlayPresetName | string;
  theme: TitleOverlayTheme | string;
  overrides?: TitleOverlayStyleOverrides;
};

export const titleOverlayThemes: Record<TitleOverlayTheme, TitleOverlayStyleOverrides> = {
  green: {
    accent: {
      color: "#20D42C",
      backgroundColor: "#20D42C",
      backgroundOpacity: 0.55,
    },
  },
  yellow: {
    accent: {
      color: "#F8F44C",
      backgroundColor: "#F8F44C",
      backgroundOpacity: 0.55,
    },
  },
  orange: {
    accent: {
      color: "#F8BC6C",
      backgroundColor: "#F8BC6C",
      backgroundOpacity: 0.55,
    },
  },
};

export const titleOverlayPresets: Record<TitleOverlayPresetName, TitleOverlayStyle> = {
  "shorts-title": {
    preset: "shorts-title",
    theme: "green",
    font: {
      family: "Cal_Sans, Inter, system-ui, sans-serif",
      sizeRatio: 0.0325,
      weight: 900,
      color: "#FFFFFF",
      lineHeight: 1.02,
      letterSpacing: 0,
      textTransform: "none",
    },
    layout: {
      position: "upper-third",
      align: "center",
      maxWidthRatio: 0.9,
      yRatio: 0.2,
      avoidBottomCaptionArea: true,
      bottomCaptionSafeAreaRatio: 0.32,
    },
    accent: {
      color: "#20D42C",
      backgroundColor: "#20D42C",
      backgroundOpacity: 0.55,
    },
    effects: {
      shadow: {
        strength: "strong",
        color: "#000000",
        opacity: 0.62,
        offsetYRatio: 0.014,
        blurRatio: 0.034,
      },
      stroke: {
        color: "#000000",
        opacity: 0.92,
        widthRatio: 0.008,
      },
    },
    animation: {
      type: "none",
    },
  },
};
