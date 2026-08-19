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
  window.HPX['matrix-rain'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const glyphs = 'アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEF'.split('');
    const fs = 16;
    let cols = 0, drops = [];
    const init = () => {
      cols = Math.ceil(k.w/fs);
      drops = Array.from({length:cols}, () => U.rand(-20, 0));
    };
    init();
    let lw = k.w, lh = k.h;
    const stop = U.loop(() => {
      if (k.w!==lw || k.h!==lh){ init(); lw=k.w; lh=k.h; }
      ctx.fillStyle = 'rgba(0,0,0,0.08)';
      ctx.fillRect(0,0,k.w,k.h);
      ctx.font = fs+'px monospace';
      for (let i=0;i<cols;i++){
        const ch = glyphs[(__hf.random()*glyphs.length)|0];
        const x = i*fs, y = drops[i]*fs;
        ctx.fillStyle = '#9fffc9';
        ctx.fillText(ch, x, y);
        ctx.fillStyle = '#00ff6a';
        ctx.fillText(ch, x, y - fs);
        drops[i] += 1;
        if (y > k.h && __hf.random() > 0.975) drops[i] = 0;
      }
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['matrix-rain'](document.querySelector('.stage'));
    }
  
}
];
