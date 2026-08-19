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
  window.HPX['typewriter-multi'] = function(el){
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    const lines = [
      (el.getAttribute('data-fx-line1') || '> initializing knowledge graph...'),
      (el.getAttribute('data-fx-line2') || '> loading 28 concept nodes'),
      (el.getAttribute('data-fx-line3') || '> agent ready. awaiting prompt_'),
    ];
    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;gap:14px;padding:32px 48px;font:600 22px ui-monospace,Menlo,monospace;color:var(--text-1,#e7e7ef);';
    el.appendChild(wrap);
    const rows = lines.map((txt) => {
      const row = document.createElement('div');
      row.style.cssText = 'white-space:pre;display:flex;align-items:center;';
      const span = document.createElement('span'); span.textContent = '';
      const cur = document.createElement('span');
      cur.textContent = '\u2588';
      cur.style.cssText = 'display:inline-block;margin-left:2px;color:var(--accent,#22d3ee);animation:hpxBlink 1s steps(2) infinite;';
      row.appendChild(span); row.appendChild(cur);
      wrap.appendChild(row);
      return {row, span, txt, i:0};
    });
    // inject blink keyframes once
    if (!document.getElementById('hpx-blink-kf')){
      const st = document.createElement('style');
      st.id = 'hpx-blink-kf';
      st.textContent = '@keyframes hpxBlink{50%{opacity:0}}';
      document.head.appendChild(st);
    }
    let stopped = false;
    const speeds = [55, 70, 45];
    rows.forEach((r, idx) => {
      const tick = () => {
        if (stopped) return;
        if (r.i < r.txt.length){
          r.span.textContent += r.txt[r.i++];
          __hf.setTimeout(tick, speeds[idx]);
        } else {
          __hf.setTimeout(() => {
            if (stopped) return;
            r.i = 0; r.span.textContent = '';
            tick();
          }, 2200);
        }
      };
      __hf.setTimeout(tick, idx*400);
    });
    return { stop(){ stopped = true; if (wrap.parentNode) wrap.parentNode.removeChild(wrap); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['typewriter-multi'](document.querySelector('.stage'));
    }
  
}
];
