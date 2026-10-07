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
  window.HPX['chain-react'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el,'#7c5cff'), ac2 = U.accent2(el,'#22d3ee');
    const N = 8;
    const stop = U.loop((t) => {
      ctx.clearRect(0,0,k.w,k.h);
      const cy = k.h/2;
      const pad = 60;
      const dx = (k.w - pad*2)/(N-1);
      const period = 2.4;
      const phase = (t % period) / period; // 0..1
      for (let i=0;i<N;i++){
        const x = pad + i*dx;
        const my = i/(N-1);
        const d = Math.abs(phase - my);
        const pulse = Math.max(0, 1 - d*6);
        const r = 18 + pulse*18;
        // glow
        const g = ctx.createRadialGradient(x,cy,0,x,cy,r*2);
        g.addColorStop(0, `rgba(124,92,255,${0.4*pulse})`);
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(x-r*2, cy-r*2, r*4, r*4);
        // circle
        ctx.fillStyle = pulse>0.1 ? ac2 : ac;
        ctx.beginPath(); ctx.arc(x,cy,r,0,Math.PI*2); ctx.fill();
        ctx.strokeStyle='rgba(255,255,255,0.4)'; ctx.lineWidth=2;
        ctx.stroke();
        // connectors
        if (i<N-1){
          ctx.strokeStyle='rgba(200,200,230,0.3)'; ctx.lineWidth=2;
          ctx.beginPath(); ctx.moveTo(x+r,cy); ctx.lineTo(x+dx-r,cy); ctx.stroke();
        }
      }
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['chain-react'](document.querySelector('.stage'));
    }
  
}
];
