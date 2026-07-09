import * as React from "react";
import { AbsoluteFill } from "remotion";
import { Caption } from "./Caption";
import { cueForPreview } from "./CaptionPreview";
import { previewConfig } from "./preview-config.ts";

const candidatesById = new Map(previewConfig.candidates.map((candidate) => [candidate.id, candidate]));

type CaptionPreviewGridProps = {
  gridId?: keyof typeof previewConfig.grids;
};

export const CaptionPreviewGrid: React.FC<CaptionPreviewGridProps> = ({ gridId = "landscape" }) => {
  const grid = previewConfig.grids[gridId];
  const candidates = grid.candidateIds.map((id) => {
    const candidate = candidatesById.get(id);
    if (!candidate) {
      throw new Error(`[captions] missing preview grid candidate: ${id}`);
    }
    return candidate;
  });
  const columns = grid.columns;
  const rows = Math.ceil(candidates.length / columns);
  const cue = cueForPreview(
    grid.sampleText,
    previewConfig.timeSec,
    previewConfig.durationSec
  );
  const isShortsGrid = gridId === "shorts";

  return (
    <AbsoluteFill style={{
      background: "#10131a",
      padding: isShortsGrid ? 34 : 28,
      boxSizing: "border-box",
      fontFamily: "Inter, system-ui, sans-serif",
    }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${columns}, 1fr)`,
        gridTemplateRows: `repeat(${rows}, 1fr)`,
        gap: 18,
        width: "100%",
        height: "100%",
      }}>
        {candidates.map((candidate) => (
          <div key={candidate.id} style={{
            position: "relative",
            overflow: "hidden",
            borderRadius: isShortsGrid ? 22 : 10,
            background: "linear-gradient(135deg, #20242d 0%, #454b5c 48%, #1b1d24 100%)",
            border: "1px solid rgba(255,255,255,0.16)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.22)",
          }}>
            <Caption
              captions={[cue]}
              karaoke={candidate.karaoke}
              styleSelection={{
                preset: candidate.preset,
                overrides: candidate.overrides,
              }}
            />
            <div style={{
              position: "absolute",
              left: 14,
              top: 12,
              padding: "6px 10px",
              borderRadius: 6,
              background: "rgba(0,0,0,0.62)",
              color: "#FFFFFF",
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 1,
              letterSpacing: 0,
            }}>
              {candidate.id}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
