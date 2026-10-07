import { createKineticImagesRecipe } from "./scene.js";

const canvas = document.getElementById("codrops-kineticimages-index-three-layer");
const { renderAt } = await createKineticImagesRecipe({ canvas });
const startedAt = performance.now();

function frame(now) {
  renderAt(((now - startedAt) / 1000) % 6);
  requestAnimationFrame(frame);
}

requestAnimationFrame(frame);
