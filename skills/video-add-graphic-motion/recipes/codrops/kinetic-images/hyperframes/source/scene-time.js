export function sceneStateAt(mode, time) {
  const seconds = Math.max(0, Number(time) || 0);
  if (mode === "cylinders") {
    return {
      billboardOffsetX: seconds * 0.01,
      bannerOffsetX: seconds / 30,
    };
  }
  if (mode === "paper") return { textureOffsetY: seconds / 30 };
  if (mode === "spiral") return { textureOffsetX: -seconds / 50 };
  throw new Error(`unsupported kinetic-images mode: ${mode}`);
}

export function showcaseStateAt(time) {
  const modes = ["cylinders", "paper", "spiral"];
  const seconds = Math.max(0, Math.min(6, Number(time) || 0));
  const index = Math.min(2, Math.floor(seconds / 2));
  return { mode: modes[index], localTime: seconds - index * 2 };
}
