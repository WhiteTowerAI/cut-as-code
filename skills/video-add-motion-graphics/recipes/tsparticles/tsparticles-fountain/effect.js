/* Deterministic HyperFrames canvas port of the tsParticles fountain preset; see upstream-options.ts. */
const canvas = document.getElementById("sticker-canvas");
const ctx = canvas.getContext("2d");
const width = canvas.width;
const height = canvas.height;
const profile = "fountain";
const colors = ["#ff4d6d", "#ffd166", "#06d6a0", "#4cc9f0", "#9b5de5", "#ffffff"];
const particles = Array.from({ length: profile === "links" ? 64 : profile === "fireflies" ? 80 : 150 }, (_, index) => ({
  index,
  x: Math.random() * width,
  y: Math.random() * height,
  vx: (Math.random() - 0.5) * 95,
  vy: (Math.random() - 0.5) * 95,
  speed: 110 + Math.random() * 240,
  angle: Math.random() * Math.PI * 2,
  phase: Math.random() * 4.8,
  life: 1.2 + Math.random() * 2.2,
  radius: 2 + Math.random() * 5,
  color: colors[index % colors.length],
}));

function dot(x, y, radius, color, alpha = 1) {
  ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

function renderFireworks(t) {
  const centers = [[420, 390], [960, 260], [1500, 420], [720, 520], [1240, 560]];
  particles.forEach((particle) => {
    const burst = particle.index % centers.length;
    const start = 0.25 + burst * 0.62;
    const age = t - start;
    if (age < 0 || age > particle.life) return;
    const center = centers[burst];
    const x = center[0] + Math.cos(particle.angle) * particle.speed * age;
    const y = center[1] + Math.sin(particle.angle) * particle.speed * age + 58 * age * age;
    dot(x, y, particle.radius, particle.color, 1 - age / particle.life);
  });
}

function renderFountain(t) {
  particles.forEach((particle) => {
    const age = (t + particle.phase) % particle.life;
    const x = width / 2 + particle.vx * age + Math.sin(particle.phase * 4) * 55;
    const y = height - 25 - particle.speed * age + 170 * age * age;
    dot(x, y, particle.radius, particle.color, 1 - age / particle.life);
  });
}

function renderFireflies(t) {
  particles.forEach((particle) => {
    const x = (particle.x + Math.sin(t * 0.8 + particle.phase) * 110 + width) % width;
    const y = (particle.y + Math.cos(t * 0.65 + particle.phase) * 75 + height) % height;
    const pulse = 0.25 + 0.75 * Math.abs(Math.sin(t * 1.8 + particle.phase));
    dot(x, y, particle.radius * 2.8, particle.color, pulse * 0.14);
    dot(x, y, particle.radius, particle.color, pulse);
  });
}

function renderLinks(t) {
  const points = particles.map((particle) => ({
    x: (particle.x + Math.sin(t * 0.34 + particle.phase) * 125 + width) % width,
    y: (particle.y + Math.cos(t * 0.29 + particle.phase) * 90 + height) % height,
    particle,
  }));
  ctx.lineWidth = 1.5;
  for (let i = 0; i < points.length; i += 1) {
    for (let j = i + 1; j < points.length; j += 1) {
      const dx = points[i].x - points[j].x;
      const dy = points[i].y - points[j].y;
      const distance = Math.hypot(dx, dy);
      if (distance > 180) continue;
      ctx.globalAlpha = (1 - distance / 180) * 0.45;
      ctx.strokeStyle = "#4cc9f0";
      ctx.beginPath();
      ctx.moveTo(points[i].x, points[i].y);
      ctx.lineTo(points[j].x, points[j].y);
      ctx.stroke();
    }
  }
  points.forEach(({ x, y, particle }) => dot(x, y, particle.radius, particle.color, 0.9));
}

function frame(milliseconds) {
  const t = milliseconds / 1000;
  ctx.clearRect(0, 0, width, height);
  if (profile === "fireworks") renderFireworks(t);
  else if (profile === "fountain") renderFountain(t);
  else if (profile === "fireflies") renderFireflies(t);
  else renderLinks(t);
  ctx.globalAlpha = 1;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
