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
  window.HPX['word-cascade'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    const WORDS = ['AI','知识','Graph','Claude','LLM','Agent','Vector','RAG','Token','神经',
      'Prompt','Chain','Skill','Code','Cloud','GPU','Flow','推理','Data','Model'];
    let items = [];
    let last = -1;
    let piles = {}; // column -> stack height
    const stop = U.loop((t) => {
      ctx.clearRect(0,0,k.w,k.h);
      if (t - last > 0.18){
        last = t;
        const w = WORDS[(__hf.random()*WORDS.length)|0];
        items.push({
          text: w, x: U.rand(40, k.w-40), y: -20,
          vy: 0, c: pal[(__hf.random()*pal.length)|0],
          size: U.rand(16,26), landed: false
        });
      }
      ctx.textAlign='center'; ctx.textBaseline='middle';
      for (const it of items){
        if (!it.landed){
          it.vy += 0.4;
          it.y += it.vy;
          const col = Math.round(it.x/60);
          const floor = k.h - (piles[col]||0) - it.size*0.6;
          if (it.y >= floor){
            it.y = floor; it.landed = true;
            piles[col] = (piles[col]||0) + it.size*1.1;
            if ((piles[col]||0) > k.h*0.8) piles[col] = 0; // reset if too high
          }
        }
        ctx.fillStyle = it.c;
        ctx.font = `700 ${it.size}px system-ui,sans-serif`;
        ctx.fillText(it.text, it.x, it.y);
      }
      // prune old landed
      if (items.length > 120){
        items = items.filter(i => !i.landed).concat(items.filter(i=>i.landed).slice(-60));
      }
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['word-cascade'](document.querySelector('.stage'));
    }
  
}
];
