/* Adapted from canvas-confetti 1.9.4; see vendor.js and shared license. */
const canvas = document.getElementById("sticker-canvas");
const fire = confetti.create(canvas, { resize: false, useWorker: false });
const customShapes = {
  star: confetti.shapeFromPath({ path: "M10 0L12.35 6.76L19.51 6.91L13.8 11.24L15.88 18.09L10 14L4.12 18.09L6.2 11.24L0.49 6.91L7.65 6.76Z" }),
  heart: confetti.shapeFromPath({ path: "M10 18S1 12.7 1 6.8C1 3.6 4.8 1.8 7.2 4.1L10 6.8L12.8 4.1C15.2 1.8 19 3.6 19 6.8C19 12.7 10 18 10 18Z" }),
};
const bursts = [{"delay":0,"options":{"colors":["#ff4d6d","#ffd166","#06d6a0","#118ab2"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":90,"angle":55,"spread":55,"startVelocity":65,"origin":{"x":0,"y":0.82}}},{"delay":0,"options":{"colors":["#ff4d6d","#ffd166","#06d6a0","#118ab2"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":90,"angle":125,"spread":55,"startVelocity":65,"origin":{"x":1,"y":0.82}}}];
for (const burst of bursts) {
  setTimeout(() => {
    const options = { ...burst.options };
    
    fire(options);
  }, burst.delay);
}
