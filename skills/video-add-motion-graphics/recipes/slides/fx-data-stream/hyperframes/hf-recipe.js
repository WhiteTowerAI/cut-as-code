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
  window.HPX['data-stream'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el,'#22d3ee'), ac2 = U.accent2(el,'#7c5cff');
    const rows = [];
    const rh = 22;
    const genRow = (y) => ({
      y, dir: __hf.random()<0.5?-1:1,
      speed: U.rand(30, 90),
      offset: __hf.random()*2000,
      text: Array.from({length:120}, () => {
        const r = __hf.random();
        if (r<0.3) return __hf.random()<0.5?'0':'1';
        if (r<0.6) return '0x' + Math.floor(__hf.random()*256).toString(16).padStart(2,'0');
        return __hf.random().toString(16).slice(2,6);
      }).join(' ')
    });
    const init = () => {
      rows.length = 0;
      const n = Math.ceil(k.h/rh);
      for (let i=0;i<n;i++) rows.push(genRow(i*rh + rh*0.7));
    };
    init();
    let lh = k.h;
    const stop = U.loop((t) => {
      if (k.h!==lh){ init(); lh=k.h; }
      ctx.fillStyle = 'rgba(5,8,14,0.35)';
      ctx.fillRect(0,0,k.w,k.h);
      ctx.font = '13px ui-monospace,Menlo,monospace';
      for (let i=0;i<rows.length;i++){
        const r = rows[i];
        const x = r.dir>0
          ? ((t*r.speed + r.offset) % (k.w+400)) - 400
          : k.w - (((t*r.speed + r.offset) % (k.w+400)) - 400);
        ctx.fillStyle = (i%3===0)?ac:ac2;
        ctx.globalAlpha = 0.65 + (i%2)*0.3;
        ctx.fillText(r.text, x, r.y);
      }
      ctx.globalAlpha = 1;
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['data-stream'](document.querySelector('.stage'));
    }
  
}
];
