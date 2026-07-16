import type { CaptionPresetName, CaptionStyleOverrides } from "./caption-presets.ts";
import type { CaptionBackgroundTheme, CaptionStrokeTheme } from "./caption-presets.ts";
import { captionHighlightThemes } from "./caption-color-themes.ts";

export type CaptionPreviewCandidate = {
  id: string;
  preset: CaptionPresetName;
  karaoke?: boolean;
  overrides?: CaptionStyleOverrides;
  compositionId?: "CaptionPreview" | "CaptionPreviewVertical";
  sampleText?: string;
};

export type CaptionPreviewConfig = {
  candidates: CaptionPreviewCandidate[];
  grids: Record<string, {
    candidateIds: string[];
    columns: number;
    sampleText: string;
    outputFile: string;
    intentGroups: Record<string, string[]>;
  }>;
  timeSec: number;
  sampleText: string;
  durationSec: number;
  outputDir: string;
};

const backgroundThemes: CaptionBackgroundTheme[] = ["gray", "yellow", "blue", "pink", "green"];
const strokeThemes: CaptionStrokeTheme[] = ["black", "yellow", "blue", "pink", "green"];
const themedCandidates = (preset: "pill" | "boxed"): CaptionPreviewCandidate[] =>
  backgroundThemes.map((theme) => ({
    id: `${preset}-${theme}`,
    preset,
    karaoke: false,
    overrides: {
      background: { theme },
      effects: preset === "pill" && theme === "yellow"
        ? {
          shadow: {
            strength: "none",
            opacity: 0,
            offsetYRatio: 0,
            blurRatio: 0,
          },
        }
        : undefined,
    },
  }));
const strokedCandidates = (): CaptionPreviewCandidate[] =>
  strokeThemes.map((theme) => ({
    id: `stroked-${theme}`,
    preset: "stroked",
    karaoke: false,
    overrides: {
      background: { enabled: false },
      stroke: { enabled: true, theme },
    },
  }));
const shortsCandidates = (): CaptionPreviewCandidate[] => [
  {
    id: "shorts-green",
    preset: "shorts",
    compositionId: "CaptionPreviewVertical",
    sampleText: "This is how captions look",
  },
  {
    id: "shorts-orange",
    preset: "shorts",
    compositionId: "CaptionPreviewVertical",
    sampleText: "This is how captions look",
    overrides: captionHighlightThemes.orange,
  },
  {
    id: "shorts-yellow",
    preset: "shorts",
    compositionId: "CaptionPreviewVertical",
    sampleText: "This is how captions look",
    overrides: captionHighlightThemes.yellow,
  },
];

export const previewConfig: CaptionPreviewConfig = {
  candidates: [
    { id: "clean", preset: "clean", karaoke: false },
    { id: "minimal", preset: "minimal", karaoke: false },
    { id: "social-bold", preset: "social-bold", karaoke: false },
    ...themedCandidates("pill"),
    ...themedCandidates("boxed"),
    ...strokedCandidates(),
    {
      id: "stroked-black-karaoke",
      preset: "stroked",
      karaoke: true,
      overrides: {
        background: { enabled: false },
        stroke: { enabled: true, theme: "black" },
      },
    },
    { id: "social-bold-karaoke", preset: "social-bold", karaoke: true },
    ...shortsCandidates(),
  ],
  grids: {
    landscape: {
      candidateIds: [
        "clean",
        "minimal",
        "social-bold",
        "pill-gray",
        "boxed-gray",
        "stroked-black",
      ],
      columns: 3,
      sampleText: "This is how captions will look",
      outputFile: "out/style-previews/preview-grid-landscape.png",
      intentGroups: {
        clean: ["clean", "minimal"],
        background: ["pill-gray", "pill-yellow", "boxed-gray", "boxed-blue"],
        stroke: ["stroked-black", "stroked-blue", "stroked-green"],
        karaoke: ["social-bold-karaoke", "stroked-black-karaoke"],
      },
    },
    shorts: {
      candidateIds: [
        "shorts-green",
        "shorts-yellow",
        "shorts-orange",
      ],
      columns: 3,
      sampleText: "This is how captions look",
      outputFile: "out/style-previews/preview-grid-shorts.png",
      intentGroups: {
        shorts: ["shorts-green", "shorts-orange", "shorts-yellow"],
        karaoke: ["shorts-green"],
      },
    },
  },
  timeSec: 5,
  sampleText: "This is how your captions will look on the final video.",
  durationSec: 4,
  outputDir: "out/style-previews",
};
