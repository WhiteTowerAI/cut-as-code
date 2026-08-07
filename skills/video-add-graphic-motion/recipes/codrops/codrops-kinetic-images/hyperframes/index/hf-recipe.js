/* Generated HyperFrames entry; scene implementation remains in source/scene.js. */
import { createRecipe } from "../source/scene.js";

const canvas = document.getElementById("three-layer");
createRecipe({ canvas })
  .then(({ renderAt }) => window.__hfThreeRegister(renderAt))
  .catch((error) => {
    window.__hfThreeError = error;
    console.error(error);
  });
