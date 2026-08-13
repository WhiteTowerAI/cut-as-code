/* Generated HyperFrames entry; scene implementation remains in source/scene.js. */
import { createKineticImagesRecipe } from "../source/scene.js";

const canvas = document.getElementById("codrops-kineticimages-index-three-layer");
createKineticImagesRecipe({ canvas })
  .then(({ renderAt }) => window.__hfThreeRegister(renderAt))
  .catch((error) => {
    window.__hfThreeError = error;
    console.error(error);
  });
