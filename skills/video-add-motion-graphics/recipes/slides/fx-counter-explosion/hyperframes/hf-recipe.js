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
  window.HPX['counter-explosion'] = function(el){
    const U = window.HPX._u;
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const target = parseInt(el.getAttribute('data-fx-to') || '2400', 10);
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    // number overlay
    const num = document.createElement('div');
    num.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font:900 120px system-ui,sans-serif;color:var(--text-1,#fff);pointer-events:none;text-shadow:0 4px 40px rgba(124,92,255,0.5);';
    num.textContent = '0';
    el.appendChild(num);
    let parts = [];
    let state = 'count'; // count | burst | hold
    let stateT = 0;
    let value = 0;
    let cycle = 0;
    const burst = () => {
      const cx = k.w/2, cy = k.h/2;
      for (let i=0;i<120;i++){
        const a = __hf.random()*Math.PI*2;
        const s = U.rand(120, 400);
        parts.push({x:cx,y:cy,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:1,r:U.rand(2,5),c:pal[(__hf.random()*pal.length)|0]});
      }
    };
    const stop = U.loop(() => {
      ctx.clearRect(0,0,k.w,k.h);
      const dt = 1/60;
      stateT += dt;
      if (state === 'count'){
        const dur = 2.2;
        const p = Math.min(1, stateT/dur);
        const eased = 1 - Math.pow(1-p,3);
        value = Math.round(target*eased);
        num.textContent = value.toLocaleString();
        if (p >= 1){ state='burst'; stateT=0; burst(); }
      } else if (state === 'burst'){
        if (stateT > 0.05 && stateT < 0.3 && parts.length < 200) {}
        if (stateT > 2.5){ state='hold'; stateT=0; }
      } else if (state === 'hold'){
        if (stateT > 1.5){
          state='count'; stateT=0; value=0; num.textContent='0'; cycle++;
        }
      }
      parts = parts.filter(p => p.life > 0);
      for (const p of parts){
        p.vy += 260*dt; p.vx *= 0.985; p.vy *= 0.985;
        p.x += p.vx*dt; p.y += p.vy*dt; p.life -= 0.01;
        ctx.globalAlpha = Math.max(0,p.life);
        ctx.fillStyle = p.c;
        ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
    return { stop(){ stop(); k.destroy(); if (num.parentNode) num.parentNode.removeChild(num); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['counter-explosion'](document.querySelector('.stage'));
    }
  
}
];
