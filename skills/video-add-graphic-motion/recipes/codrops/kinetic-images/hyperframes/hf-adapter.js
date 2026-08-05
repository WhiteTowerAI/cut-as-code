/* Deterministic HyperFrames Three.js adapter for kinetic-images. */
(function () {
  "use strict";
  const duration = 6;
  let renderAt = null;
  let currentTime = Math.max(0, Math.min(duration, Number(window.__hfThreeTime) || 0));

  function seek(time) {
    currentTime = Math.max(0, Math.min(duration, Number(time) || 0));
    window.__hfThreeTime = currentTime;
    if (renderAt) renderAt(currentTime);
  }

  window.__hfThreeRegister = function (callback) {
    renderAt = callback;
    renderAt(currentTime);
  };
  window.__hf = { duration, seek };
  window.addEventListener("hf-seek", (event) => seek(event.detail.time));
  seek(currentTime);
})();
