import assert from "node:assert/strict";
import test from "node:test";

let sceneStateAt;
let showcaseStateAt;
try {
  ({ sceneStateAt, showcaseStateAt } = await import("../recipes/codrops/kinetic-images/scene-time.js"));
} catch (error) {
  assert.fail(`kinetic-images scene-time.js is missing: ${error.message}`);
}

test("maps every kinetic-images mode directly from absolute time", () => {
  assert.deepEqual(sceneStateAt("cylinders", 6), {
    billboardOffsetX: 0.06,
    bannerOffsetX: 0.2,
  });
  assert.deepEqual(sceneStateAt("paper", 6), { textureOffsetY: 0.2 });
  assert.deepEqual(sceneStateAt("spiral", 6), { textureOffsetX: -0.12 });
  assert.deepEqual(sceneStateAt("spiral", 1.5), { textureOffsetX: -0.03 });
});

test("rejects unsupported kinetic-images modes", () => {
  assert.throws(() => sceneStateAt("unknown", 1), /unsupported kinetic-images mode/);
});

test("holds the spiral pose at the exact showcase final frame", () => {
  assert.deepEqual(showcaseStateAt(0), { mode: "cylinders", localTime: 0 });
  assert.deepEqual(showcaseStateAt(2), { mode: "paper", localTime: 0 });
  assert.deepEqual(showcaseStateAt(4), { mode: "spiral", localTime: 0 });
  assert.deepEqual(showcaseStateAt(6), { mode: "spiral", localTime: 2 });
});
