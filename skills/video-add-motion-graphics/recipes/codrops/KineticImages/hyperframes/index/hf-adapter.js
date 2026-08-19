/* Deterministic HyperFrames Three.js adapter for KineticImages. */
(function () {
  "use strict";
  const DURATION_S = 6;
  let renderAt = null;
  let currentTime = Math.max(0, Math.min(DURATION_S, Number(window.__hfThreeTime) || 0));

  function seek(time) {
    currentTime = Math.max(0, Math.min(DURATION_S, Number(time) || 0));
    window.__hfThreeTime = currentTime;
    if (renderAt) renderAt(currentTime);
  }

  window.__hfThreeRegister = function (callback) {
    renderAt = callback;
    renderAt(currentTime);
  };
  window.__hf = { duration: DURATION_S, seek };
  window.addEventListener("hf-seek", (event) => seek(event.detail.time));
  seek(currentTime);
})();
