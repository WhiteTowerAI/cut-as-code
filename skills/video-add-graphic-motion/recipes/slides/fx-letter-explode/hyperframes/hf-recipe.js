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
  window.HPX['letter-explode'] = function(el){
    const U = window.HPX._u;
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const src = el.querySelector('[data-fx-text]') || el;
    const text = (el.getAttribute('data-fx-text-value') || src.textContent || 'EXPLODE').trim();
    // Build a container, hide source text
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;';
    const inner = document.createElement('div');
    inner.style.cssText = 'font-size:64px;font-weight:900;letter-spacing:0.02em;color:var(--text-1,#fff);white-space:nowrap;';
    wrap.appendChild(inner);
    el.appendChild(wrap);
    const spans = [];
    for (const ch of text){
      const s = document.createElement('span');
      s.textContent = ch === ' ' ? '\u00A0' : ch;
      s.style.display='inline-block';
      s.style.transform='translate(0,0)';
      s.style.transition='transform 900ms cubic-bezier(.2,.9,.3,1), opacity 900ms';
      s.style.opacity='0';
      inner.appendChild(s);
      spans.push(s);
    }
    let stopped = false;
    const run = () => {
      if (stopped) return;
      spans.forEach((s,i) => {
        const dx = U.rand(-400, 400), dy = U.rand(-300, 300);
        s.style.transition='none';
        s.style.transform=`translate(${dx}px,${dy}px) rotate(${U.rand(-180,180)}deg)`;
        s.style.opacity='0';
      });
      // force reflow
      void inner.offsetWidth;
      spans.forEach((s,i) => {
        __hf.setTimeout(() => {
          if (stopped) return;
          s.style.transition='transform 900ms cubic-bezier(.2,.9,.3,1), opacity 900ms';
          s.style.transform='translate(0,0) rotate(0deg)';
          s.style.opacity='1';
        }, i*35);
      });
    };
    run();
    const iv = __hf.setInterval(run, 4500);
    return { stop(){ stopped=true; __hf.clearInterval(iv); if (wrap.parentNode) wrap.parentNode.removeChild(wrap); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['letter-explode'](document.querySelector('.stage'));
    }
  
}
];
