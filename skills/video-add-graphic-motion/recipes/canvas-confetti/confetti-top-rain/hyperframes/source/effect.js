/* Adapted from canvas-confetti 1.9.4; see vendor.js and shared license. */
const canvas = document.getElementById("sticker-canvas");
const fire = confetti.create(canvas, { resize: false, useWorker: false });
const customShapes = {
  star: confetti.shapeFromPath({ path: "M10 0L12.35 6.76L19.51 6.91L13.8 11.24L15.88 18.09L10 14L4.12 18.09L6.2 11.24L0.49 6.91L7.65 6.76Z" }),
  heart: confetti.shapeFromPath({ path: "M10 18S1 12.7 1 6.8C1 3.6 4.8 1.8 7.2 4.1L10 6.8L12.8 4.1C15.2 1.8 19 3.6 19 6.8C19 12.7 10 18 10 18Z" }),
};
const bursts = [{"delay":0,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.08,"y":0.02},"scalar":0.9}},{"delay":180,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.2,"y":0.02},"scalar":0.9}},{"delay":360,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.32,"y":0.02},"scalar":0.9}},{"delay":540,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.44,"y":0.02},"scalar":0.9}},{"delay":720,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.5599999999999999,"y":0.02},"scalar":0.9}},{"delay":900,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.6799999999999999,"y":0.02},"scalar":0.9}},{"delay":1080,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.7999999999999999,"y":0.02},"scalar":0.9}},{"delay":1260,"options":{"colors":["#f72585","#7209b7","#4cc9f0","#f9c74f"],"disableForReducedMotion":false,"ticks":180,"zIndex":0,"particleCount":24,"angle":270,"spread":70,"startVelocity":18,"gravity":1.15,"origin":{"x":0.9199999999999999,"y":0.02},"scalar":0.9}}];
for (const burst of bursts) {
  setTimeout(() => {
    const options = { ...burst.options };
    
    fire(options);
  }, burst.delay);
}
