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
  window.HPX['sparkle-trail'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    k.c.style.pointerEvents = 'none';
    el.style.cursor = 'crosshair';
    const pal = U.palette(el);
    let sparks = [];
    const onMove = (e) => {
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      for (let i=0;i<3;i++){
        sparks.push({
          x, y,
          vx: U.rand(-60,60), vy: U.rand(-80,20),
          life: 1, c: pal[(__hf.random()*pal.length)|0],
          r: U.rand(1.5,3.5)
        });
      }
    };
    // auto-wiggle if no mouse moves
    let auto = true, autoT = 0;
    const onAny = () => { auto = false; };
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerenter', onAny);
    const stop = U.loop(() => {
      ctx.fillStyle = 'rgba(0,0,0,0.15)';
      ctx.fillRect(0,0,k.w,k.h);
      if (auto){
        autoT += 0.04;
        const x = k.w/2 + Math.cos(autoT)*k.w*0.3;
        const y = k.h/2 + Math.sin(autoT*1.3)*k.h*0.3;
        for (let i=0;i<3;i++){
          sparks.push({
            x, y,
            vx: U.rand(-60,60), vy: U.rand(-80,20),
            life: 1, c: pal[(__hf.random()*pal.length)|0],
            r: U.rand(1.5,3.5)
          });
        }
      }
      const dt = 1/60;
      sparks = sparks.filter(s => s.life > 0);
      for (const s of sparks){
        s.vy += 160*dt;
        s.x += s.vx*dt; s.y += s.vy*dt;
        s.life -= 0.018;
        ctx.globalAlpha = Math.max(0, s.life);
        ctx.fillStyle = s.c;
        ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,Math.PI*2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
    return { stop(){
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerenter', onAny);
      el.style.cursor = '';
      stop(); k.destroy();
    }};
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['sparkle-trail'](document.querySelector('.stage'));
    }
  
}
];
