/* Deterministic HyperFrames SVG SMIL adapter for line-md-filter-remove-filled. */
(function () {
  "use strict";
  const duration = 6;
  const svg = document.querySelector("svg");

  function seek(time) {
    if (!svg) return;
    const target = Math.max(0, Math.min(duration, Number(time) || 0));
    const nativeDuration = Number(svg.dataset.nativeDuration) || duration;
    const localTime = nativeDuration > 0 ? target % nativeDuration : target;
    if (typeof svg.pauseAnimations === "function") svg.pauseAnimations();
    if (typeof svg.setCurrentTime === "function") svg.setCurrentTime(localTime);
  }

  window.__hf = { duration, seek };
  window.addEventListener("hf-seek", (event) => seek(event.detail.time));
  seek(0);
})();
