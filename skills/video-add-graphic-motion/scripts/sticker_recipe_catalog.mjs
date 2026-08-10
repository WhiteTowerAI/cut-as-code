export const CANVAS_CONFETTI_RECIPES = [
  { id: "confetti-side-cannons", name: "Side Confetti Cannons", pattern: "side-cannons", colors: ["#ff4d6d", "#ffd166", "#06d6a0", "#118ab2"] },
  { id: "confetti-center-burst", name: "Center Confetti Burst", pattern: "center-burst", colors: ["#ff595e", "#ffca3a", "#8ac926", "#1982c4"] },
  { id: "confetti-top-rain", name: "Confetti Rain", pattern: "top-rain", colors: ["#f72585", "#7209b7", "#4cc9f0", "#f9c74f"] },
  { id: "confetti-bottom-fountain", name: "Confetti Fountain", pattern: "bottom-fountain", colors: ["#ff6b6b", "#feca57", "#48dbfb", "#1dd1a1"] },
  { id: "confetti-star-burst", name: "Star Confetti Burst", pattern: "center-burst", shape: "star", colors: ["#fff3b0", "#ffd60a", "#ff9f1c"] },
  { id: "confetti-heart-burst", name: "Heart Confetti Burst", pattern: "center-burst", shape: "heart", colors: ["#ff4d6d", "#ff758f", "#ff8fa3"] },
  { id: "confetti-firework-triple", name: "Confetti Firework Triple", pattern: "firework-triple", colors: ["#ff006e", "#fb5607", "#ffbe0b", "#3a86ff"] },
  { id: "confetti-realistic", name: "Realistic Confetti", pattern: "realistic", colors: ["#a8dadc", "#f1faee", "#e63946", "#ffb703"] },
  { id: "confetti-mini-pop", name: "Mini Confetti Pop", pattern: "mini-pop", colors: ["#ff70a6", "#ff9770", "#ffd670", "#70d6ff"] },
  { id: "confetti-slow-fall", name: "Slow Falling Confetti", pattern: "slow-fall", colors: ["#f6bd60", "#f7ede2", "#f5cac3", "#84a59d"] },
];

export const MOJS_RECIPES = [
  { id: "mojs-spark-ring", name: "Spark Ring", count: 16, radius: 170, childShape: "line", childRadius: 18, rings: 1, colors: ["#ffd166", "#ffffff"] },
  { id: "mojs-shockwave", name: "Shockwave", count: 0, radius: 190, rings: 3, colors: ["#4cc9f0", "#ffffff"] },
  { id: "mojs-orbit-burst", name: "Orbit Burst", count: 12, radius: 210, childShape: "circle", childRadius: 10, rings: 1, degree: 300, colors: ["#7209b7", "#4cc9f0"] },
  { id: "mojs-celebration-burst", name: "Celebration Burst", count: 22, radius: 230, childShape: "circle", childRadius: 13, rings: 2, colors: ["#ff4d6d", "#ffd166", "#06d6a0"] },
  { id: "mojs-star-burst", name: "Star Polygon Burst", count: 14, radius: 190, childShape: "polygon", childRadius: 14, childPoints: 5, rings: 1, colors: ["#ffd60a", "#ffffff"] },
  { id: "mojs-ripple-ring", name: "Ripple Ring", count: 8, radius: 140, childShape: "circle", childRadius: 7, rings: 4, colors: ["#90e0ef", "#0077b6"] },
  { id: "mojs-comet-trail", name: "Comet Trail", count: 18, radius: 250, childShape: "line", childRadius: 25, rings: 1, degree: 120, angle: 210, colors: ["#ffffff", "#4cc9f0"] },
  { id: "mojs-success-pop", name: "Success Pop", count: 14, radius: 150, childShape: "line", childRadius: 17, rings: 2, colors: ["#2dc653", "#ffffff"] },
  { id: "mojs-warning-pulse", name: "Warning Pulse", count: 10, radius: 135, childShape: "polygon", childRadius: 12, childPoints: 3, rings: 4, colors: ["#ffb703", "#fb8500"] },
  { id: "mojs-corner-sparks", name: "Corner Sparks", count: 12, radius: 125, childShape: "line", childRadius: 18, rings: 1, positions: [[260, 220], [1660, 220], [260, 860], [1660, 860]], colors: ["#ffffff", "#4cc9f0"] },
];

export const LINE_MD_COUNT = 1222;

export const METEOCONS_ICONS = [
  "clear-day", "clear-night", "partly-cloudy-day", "rain", "thunderstorms", "snow",
  "snowflake", "lightning-bolt", "wind", "fog", "rainbow", "tornado",
];

export const TSPARTICLES_RECIPES = [
  { id: "tsparticles-fireworks", name: "Complex Fireworks", profile: "fireworks", preset: "fireworks" },
  { id: "tsparticles-fountain", name: "Particle Fountain", profile: "fountain", preset: "fountain" },
  { id: "tsparticles-fireflies", name: "Firefly Field", profile: "fireflies", preset: "firefly" },
  { id: "tsparticles-linked-field", name: "Linked Particle Field", profile: "links", preset: "links" },
];

export const STICKER_COUNTS = Object.freeze({
  "canvas-confetti": CANVAS_CONFETTI_RECIPES.length,
  mojs: MOJS_RECIPES.length,
  "line-md": LINE_MD_COUNT,
  meteocons: METEOCONS_ICONS.length,
  tsparticles: TSPARTICLES_RECIPES.length,
});

export const STICKER_TOTAL = Object.values(STICKER_COUNTS).reduce((total, count) => total + count, 0);
