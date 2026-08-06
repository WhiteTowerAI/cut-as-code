import { createRecipe } from "./scene.js";

const canvas = document.getElementById("three-layer");
const { renderAt } = await createRecipe({ canvas });
const startedAt = performance.now();

function frame(now) {
  renderAt(((now - startedAt) / 1000) % 6);
  requestAnimationFrame(frame);
}

requestAnimationFrame(frame);

