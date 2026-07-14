export type CaptionPresetName =
  | "clean"
  | "minimal"
  | "social-bold"
  | "pill"
  | "boxed"
  | "stroked"
  | "shorts";

export type CaptionAnchor = "top" | "center" | "bottom";
export type CaptionTextAlign = "left" | "center" | "right";
export type CaptionBackgroundShape = "square" | "rounded" | "pill";
export type CaptionBackgroundTheme = "gray" | "yellow" | "blue" | "pink" | "green";
export type CaptionStrokeTheme = "black" | "yellow" | "blue" | "pink" | "green";
export type CaptionShadowStrength = "none" | "soft" | "strong";
export type CaptionStrokeStrength = "none" | "soft" | "strong";
export type CaptionHighlightMode = "none" | "textColor" | "background";
export type CaptionAnimationType = "none" | "fade" | "pop" | "slideUp";

export type CaptionStyle = {
  preset: CaptionPresetName;
  font: {
    family: string;
    sizeRatio: number;
    weight: number;
    color: string;
    lineHeight: number;
    letterSpacing: number;
  };
  layout: {
    anchor: CaptionAnchor;
    align: CaptionTextAlign;
    maxWidth: number;
    paddingBottomRatio: number;
  };
  background: {
    enabled: boolean;
    theme: CaptionBackgroundTheme;
    shape: CaptionBackgroundShape;
    color: string;
    opacity: number;
    radiusRatio: number;
    paddingXRatio: number;
    paddingYRatio: number;
  };
  effects: {
    shadow: {
      strength: CaptionShadowStrength;
      color: string;
      opacity: number;
      offsetYRatio: number;
      blurRatio: number;
    };
    stroke: {
      strength: CaptionStrokeStrength;
      color: string;
      widthRatio: number;
    };
  };
  stroke: {
    enabled: boolean;
    theme: CaptionStrokeTheme;
    color: string;
    opacity: number;
    widthRatio: number;
    widthPx?: number;
  };
  wordHighlight: {
    enabled: boolean;
    mode: CaptionHighlightMode;
    activeColor: string;
    activeScale: number;
    upcomingOpacity: number;
    backgroundColor: string;
    backgroundOpacity: number;
    backgroundRadiusRatio: number;
  };
  animation: {
    type: CaptionAnimationType;
    popInFrames: number;
    popOutFrames: number;
    translateYPx: number;
  };
};

export type CaptionStyleOverrides = {
  font?: Partial<CaptionStyle["font"]>;
  layout?: Partial<CaptionStyle["layout"]>;
  background?: Partial<CaptionStyle["background"]>;
  effects?: {
    shadow?: Partial<CaptionStyle["effects"]["shadow"]>;
    stroke?: Partial<CaptionStyle["effects"]["stroke"]>;
  };
  stroke?: Partial<CaptionStyle["stroke"]>;
  wordHighlight?: Partial<CaptionStyle["wordHighlight"]>;
  animation?: Partial<CaptionStyle["animation"]>;
};

export type CaptionStyleSelection = {
  preset: CaptionPresetName | string;
  karaoke?: boolean;
  overrides?: CaptionStyleOverrides;
};

export const captionPresets: Record<CaptionPresetName, CaptionStyle> = {
  clean: {
    preset: "clean",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0416,
      weight: 800,
      color: "#F5F4ED",
      lineHeight: 1.32,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.92,
      paddingBottomRatio: 0.07,
    },
    background: {
      enabled: false,
      theme: "gray",
      shape: "rounded",
      color: "#000000",
      opacity: 0.48,
      radiusRatio: 0.018,
      paddingXRatio: 0.035,
      paddingYRatio: 0.018,
    },
    effects: {
      shadow: {
        strength: "soft",
        color: "#000000",
        opacity: 0.55,
        offsetYRatio: 0.02,
        blurRatio: 0.04,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: false,
      theme: "black",
      color: "#000000",
      opacity: 0.85,
      widthRatio: 0,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#FF7A45",
      activeScale: 1.12,
      upcomingOpacity: 0.55,
      backgroundColor: "#FF7A45",
      backgroundOpacity: 0.24,
      backgroundRadiusRatio: 0.01,
    },
    animation: {
      type: "pop",
      popInFrames: 6,
      popOutFrames: 4,
      translateYPx: 22,
    },
  },
  minimal: {
    preset: "minimal",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0352,
      weight: 650,
      color: "#FFFFFF",
      lineHeight: 1.342,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.86,
      paddingBottomRatio: 0.075,
    },
    background: {
      enabled: false,
      theme: "gray",
      shape: "rounded",
      color: "#000000",
      opacity: 0.32,
      radiusRatio: 0.014,
      paddingXRatio: 0.028,
      paddingYRatio: 0.014,
    },
    effects: {
      shadow: {
        strength: "none",
        color: "#000000",
        opacity: 0,
        offsetYRatio: 0,
        blurRatio: 0,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: false,
      theme: "black",
      color: "#000000",
      opacity: 0.85,
      widthRatio: 0,
    },
    wordHighlight: {
      enabled: false,
      mode: "none",
      activeColor: "#FFFFFF",
      activeScale: 1,
      upcomingOpacity: 1,
      backgroundColor: "#FFFFFF",
      backgroundOpacity: 0,
      backgroundRadiusRatio: 0.01,
    },
    animation: {
      type: "fade",
      popInFrames: 6,
      popOutFrames: 4,
      translateYPx: 0,
    },
  },
  "social-bold": {
    preset: "social-bold",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0826,
      weight: 850,
      color: "#FFFFFF",
      lineHeight: 1.232,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.94,
      paddingBottomRatio: 0.08,
    },
    background: {
      enabled: false,
      theme: "gray",
      shape: "rounded",
      color: "#000000",
      opacity: 0.5,
      radiusRatio: 0.018,
      paddingXRatio: 0.035,
      paddingYRatio: 0.018,
    },
    effects: {
      shadow: {
        strength: "strong",
        color: "#000000",
        opacity: 0.78,
        offsetYRatio: 0.04,
        blurRatio: 0.08,
      },
      stroke: {
        strength: "soft",
        color: "#000000",
        widthRatio: 0.0035,
      },
    },
    stroke: {
      enabled: false,
      theme: "black",
      color: "#000000",
      opacity: 0.85,
      widthRatio: 0,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#FFD43B",
      activeScale: 1.14,
      upcomingOpacity: 0.58,
      backgroundColor: "#FFD43B",
      backgroundOpacity: 0.28,
      backgroundRadiusRatio: 0.012,
    },
    animation: {
      type: "pop",
      popInFrames: 5,
      popOutFrames: 4,
      translateYPx: 24,
    },
  },
  pill: {
    preset: "pill",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0416,
      weight: 800,
      color: "#FFFFFF",
      lineHeight: 1.298,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.9,
      paddingBottomRatio: 0.075,
    },
    background: {
      enabled: true,
      theme: "gray",
      shape: "pill",
      color: "#111827",
      opacity: 0.62,
      radiusRatio: 0.04,
      paddingXRatio: 0.04,
      paddingYRatio: 0.0126,
    },
    effects: {
      shadow: {
        strength: "soft",
        color: "#000000",
        opacity: 0.34,
        offsetYRatio: 0.014,
        blurRatio: 0.035,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: false,
      theme: "black",
      color: "#000000",
      opacity: 0.85,
      widthRatio: 0,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#FFB000",
      activeScale: 1.12,
      upcomingOpacity: 0.62,
      backgroundColor: "#FFB000",
      backgroundOpacity: 0.28,
      backgroundRadiusRatio: 0.012,
    },
    animation: {
      type: "pop",
      popInFrames: 6,
      popOutFrames: 4,
      translateYPx: 18,
    },
  },
  boxed: {
    preset: "boxed",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0416,
      weight: 800,
      color: "#FFFFFF",
      lineHeight: 1.298,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.9,
      paddingBottomRatio: 0.07,
    },
    background: {
      enabled: true,
      theme: "gray",
      shape: "rounded",
      color: "#111111",
      opacity: 0.72,
      radiusRatio: 0.008,
      paddingXRatio: 0.032,
      paddingYRatio: 0.0112,
    },
    effects: {
      shadow: {
        strength: "none",
        color: "#000000",
        opacity: 0,
        offsetYRatio: 0,
        blurRatio: 0,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: false,
      theme: "black",
      color: "#000000",
      opacity: 0.85,
      widthRatio: 0,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#8BE9FD",
      activeScale: 1.12,
      upcomingOpacity: 0.68,
      backgroundColor: "#8BE9FD",
      backgroundOpacity: 0.22,
      backgroundRadiusRatio: 0.008,
    },
    animation: {
      type: "fade",
      popInFrames: 5,
      popOutFrames: 4,
      translateYPx: 0,
    },
  },
  stroked: {
    preset: "stroked",
    font: {
      family: "Inter, system-ui, sans-serif",
      sizeRatio: 0.0416,
      weight: 800,
      color: "#F5F4ED",
      lineHeight: 1.32,
      letterSpacing: 0,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.92,
      paddingBottomRatio: 0.07,
    },
    background: {
      enabled: false,
      theme: "gray",
      shape: "rounded",
      color: "#000000",
      opacity: 0.48,
      radiusRatio: 0.018,
      paddingXRatio: 0.035,
      paddingYRatio: 0.018,
    },
    effects: {
      shadow: {
        strength: "none",
        color: "#000000",
        opacity: 0,
        offsetYRatio: 0,
        blurRatio: 0,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: true,
      theme: "black",
      color: "#000000",
      opacity: 0.9,
      widthRatio: 0.009,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#FFD43B",
      activeScale: 1,
      upcomingOpacity: 0.58,
      backgroundColor: "#FFD43B",
      backgroundOpacity: 0.28,
      backgroundRadiusRatio: 0.012,
    },
    animation: {
      type: "pop",
      popInFrames: 6,
      popOutFrames: 4,
      translateYPx: 18,
    },
  },
  shorts: {
    preset: "shorts",
    font: {
      family: "Cal_Sans, Inter, system-ui, sans-serif",
      sizeRatio: 0.022875,
      weight: 900,
      color: "#FFFFFF",
      lineHeight: 1.18,
      letterSpacing: 0.012,
    },
    layout: {
      anchor: "bottom",
      align: "center",
      maxWidth: 0.9,
      paddingBottomRatio: 0.2,
    },
    background: {
      enabled: false,
      theme: "gray",
      shape: "rounded",
      color: "#000000",
      opacity: 0.48,
      radiusRatio: 0.018,
      paddingXRatio: 0.035,
      paddingYRatio: 0.018,
    },
    effects: {
      shadow: {
        strength: "soft",
        color: "#000000",
        opacity: 0.35,
        offsetYRatio: 0.014,
        blurRatio: 0.03,
      },
      stroke: {
        strength: "none",
        color: "#000000",
        widthRatio: 0,
      },
    },
    stroke: {
      enabled: true,
      theme: "black",
      color: "#000000",
      opacity: 0.92,
      widthRatio: 0.008,
    },
    wordHighlight: {
      enabled: true,
      mode: "textColor",
      activeColor: "#21D32E",
      activeScale: 1,
      upcomingOpacity: 0.62,
      backgroundColor: "#21D32E",
      backgroundOpacity: 0.28,
      backgroundRadiusRatio: 0.012,
    },
    animation: {
      type: "pop",
      popInFrames: 5,
      popOutFrames: 4,
      translateYPx: 20,
    },
  },
};
