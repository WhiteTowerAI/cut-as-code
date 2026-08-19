/* Adapted from @mojs/core 1.7.1; see vendor.js and shared license. */
const spec = {"count":10,"radius":135,"childShape":"polygon","childRadius":12,"childPoints":3,"rings":4,"degree":360,"angle":0,"positions":[[960,540]],"colors":["#ffb703","#fb8500"]};
const parent = document.getElementById("sticker-stage");
spec.positions.forEach(([x, y], positionIndex) => {
  const shiftX = x - 960;
  const shiftY = y - 540;
  setTimeout(() => {
    if (spec.count > 0) {
      new mojs.Burst({
        parent, x: shiftX, y: shiftY, count: spec.count, degree: spec.degree, angle: spec.angle,
        radius: { 0: spec.radius }, duration: 1250,
        children: {
          shape: spec.childShape || "circle", points: spec.childPoints || 5,
          radius: { [spec.childRadius || 10]: 0 }, fill: spec.colors,
          stroke: spec.childShape === "line" ? spec.colors : "none",
          strokeWidth: spec.childShape === "line" ? { 5: 0 } : 0,
          duration: 1150, easing: "quad.out",
        },
      }).play();
    }
    for (let ring = 0; ring < spec.rings; ring += 1) {
      new mojs.Shape({
        parent, x: shiftX, y: shiftY, shape: "circle", fill: "none", stroke: spec.colors[ring % spec.colors.length],
        radius: { 0: spec.radius * (0.58 + ring * 0.13) }, strokeWidth: { [14 - ring * 2]: 0 },
        duration: 900 + ring * 180, delay: ring * 90, easing: "cubic.out",
      }).play();
    }
  }, positionIndex * 220);
});
