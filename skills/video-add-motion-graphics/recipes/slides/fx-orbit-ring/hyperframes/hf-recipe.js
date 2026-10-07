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
  window.HPX['orbit-ring'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    const rings = [
      {r:40,  n:3,  sp:1.2, c:pal[0]},
      {r:75,  n:5,  sp:0.8, c:pal[1]},
      {r:110, n:8,  sp:-0.6, c:pal[2]},
      {r:145, n:12, sp:0.4, c:pal[3]},
      {r:180, n:16, sp:-0.3, c:pal[4]}
    ];
    const stop = U.loop((t) => {
      ctx.clearRect(0,0,k.w,k.h);
      const cx=k.w/2, cy=k.h/2;
      // radial glow
      const g = ctx.createRadialGradient(cx,cy,0,cx,cy,210);
      g.addColorStop(0,'rgba(124,92,255,0.25)');
      g.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle = g; ctx.fillRect(0,0,k.w,k.h);
      for (const R of rings){
        ctx.strokeStyle = 'rgba(200,200,230,0.2)'; ctx.lineWidth=1;
        ctx.beginPath(); ctx.arc(cx,cy,R.r,0,Math.PI*2); ctx.stroke();
        for (let i=0;i<R.n;i++){
          const a = (i/R.n)*Math.PI*2 + t*R.sp;
          const x = cx + Math.cos(a)*R.r;
          const y = cy + Math.sin(a)*R.r;
          ctx.fillStyle = R.c;
          ctx.beginPath(); ctx.arc(x,y,4,0,Math.PI*2); ctx.fill();
        }
      }
      ctx.fillStyle = '#fff';
      ctx.beginPath(); ctx.arc(cx,cy,5,0,Math.PI*2); ctx.fill();
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['orbit-ring'](document.querySelector('.stage'));
    }
  
}
];
