/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
/* html-ppt fx :: shared helpers */
(function(){
  window.HPX = window.HPX || {};
  const U = window.HPX._u = {};

  U.css = (el, name, fb) => {
    const v = getComputedStyle(el).getPropertyValue(name).trim();
    return v || fb;
  };

  U.accent = (el, fb) => U.css(el, '--accent', fb || '#7c5cff');
  U.accent2 = (el, fb) => U.css(el, '--accent-2', fb || '#22d3ee');
  U.text = (el, fb) => U.css(el, '--text-1', fb || '#eaeaf2');

  U.palette = (el) => [
    U.accent(el, '#7c5cff'),
    U.accent2(el, '#22d3ee'),
    U.css(el, '--ok', '#22c55e'),
    U.css(el, '--warn', '#f59e0b'),
    U.css(el, '--danger', '#ef4444'),
  ];

  U.canvas = (el) => {
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const c = document.createElement('canvas');
    c.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;display:block;';
    el.appendChild(c);
    const ctx = c.getContext('2d');
    let w = 0, h = 0, dpr = Math.max(1, Math.min(2, window.devicePixelRatio||1));
    const fit = () => {
      const r = el.getBoundingClientRect();
      w = Math.max(1, r.width|0);
      h = Math.max(1, r.height|0);
      c.width = (w*dpr)|0;
      c.height = (h*dpr)|0;
      ctx.setTransform(dpr,0,0,dpr,0,0);
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return {
      c, ctx,
      get w(){return w;}, get h(){return h;}, get dpr(){return dpr;},
      destroy(){
        try{ro.disconnect();}catch(e){}
        if (c.parentNode) c.parentNode.removeChild(c);
      }
    };
  };

  U.loop = (fn) => {
    let raf = 0, stopped = false, t0 = __hf.now();
    const tick = (t) => {
      if (stopped) return;
      fn((t - t0)/1000);
      raf = __hf.requestAnimationFrame(tick);
    };
    raf = __hf.requestAnimationFrame(tick);
    return () => { stopped = true; __hf.cancelAnimationFrame(raf); };
  };

  U.rand = (a,b) => a + __hf.random()*(b-a);
})();

},
function (__hf) {
(function(){
  window.HPX = window.HPX || {};
  window.HPX['firework'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    let rockets = [], sparks = [];
    const launch = () => {
      rockets.push({
        x: U.rand(k.w*0.2, k.w*0.8), y: k.h+10,
        vx: U.rand(-30,30), vy: U.rand(-520,-380),
        tgtY: U.rand(k.h*0.15, k.h*0.45),
        c: pal[(__hf.random()*pal.length)|0]
      });
    };
    const burst = (x, y, c) => {
      const n = 70;
      for (let i=0;i<n;i++){
        const a = __hf.random()*Math.PI*2;
        const s = U.rand(60, 240);
        sparks.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:1,c});
      }
    };
    let last = -1;
    const stop = U.loop((t) => {
      ctx.fillStyle = 'rgba(0,0,0,0.18)';
      ctx.fillRect(0,0,k.w,k.h);
      if (t - last > 0.7) { launch(); last = t; }
      const dt = 1/60;
      rockets = rockets.filter(r => {
        r.x += r.vx*dt; r.y += r.vy*dt; r.vy += 260*dt;
        ctx.fillStyle = r.c;
        ctx.beginPath(); ctx.arc(r.x, r.y, 2.5, 0, Math.PI*2); ctx.fill();
        if (r.y <= r.tgtY || r.vy >= 0) { burst(r.x, r.y, r.c); return false; }
        return true;
      });
      sparks = sparks.filter(p => p.life > 0);
      for (const p of sparks){
        p.vy += 90*dt;
        p.vx *= 0.98; p.vy *= 0.98;
        p.x += p.vx*dt; p.y += p.vy*dt;
        p.life -= 0.012;
        ctx.globalAlpha = Math.max(0, p.life);
        ctx.fillStyle = p.c;
        ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, Math.PI*2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['firework'](document.querySelector('.stage'));
    }
  
}
];
