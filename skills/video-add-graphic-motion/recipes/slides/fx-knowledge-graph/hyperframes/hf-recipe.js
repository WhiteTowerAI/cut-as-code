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
  window.HPX['knowledge-graph'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const pal = U.palette(el);
    const tx = U.text(el, '#e7e7ef');
    const labels = ['AI','ML','LLM','Graph','Node','Edge','Claude','GPT','RAG','Vector',
      'Embed','Neural','Agent','Tool','Memory','Logic','Data','Train','Infer','Token',
      'Prompt','Chain','Plan','Skill','Cloud','Edge','GPU','Code','Task','Flow'];
    const N = 28;
    const nodes = Array.from({length:N}, (_,i) => ({
      x: U.rand(40, 300), y: U.rand(40, 200),
      vx: 0, vy: 0, label: labels[i%labels.length],
      c: pal[i%pal.length]
    }));
    const edges = [];
    const made = new Set();
    while (edges.length < 50){
      const a = (__hf.random()*N)|0, b = (__hf.random()*N)|0;
      if (a===b) continue;
      const key = a<b ? a+'-'+b : b+'-'+a;
      if (made.has(key)) continue;
      made.add(key); edges.push([a,b]);
    }
    const stop = U.loop(() => {
      // physics
      for (let i=0;i<N;i++){
        for (let j=i+1;j<N;j++){
          const a=nodes[i], b=nodes[j];
          const dx=b.x-a.x, dy=b.y-a.y;
          let d2=dx*dx+dy*dy; if (d2<1) d2=1;
          const d=Math.sqrt(d2);
          const f=1600/d2;
          const fx=(dx/d)*f, fy=(dy/d)*f;
          a.vx-=fx; a.vy-=fy; b.vx+=fx; b.vy+=fy;
        }
      }
      for (const [i,j] of edges){
        const a=nodes[i], b=nodes[j];
        const dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||1;
        const f=(d-90)*0.008;
        const fx=(dx/d)*f, fy=(dy/d)*f;
        a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;
      }
      const cx=k.w/2, cy=k.h/2;
      for (const n of nodes){
        n.vx += (cx-n.x)*0.002;
        n.vy += (cy-n.y)*0.002;
        n.vx *= 0.85; n.vy *= 0.85;
        n.x += n.vx; n.y += n.vy;
      }
      ctx.clearRect(0,0,k.w,k.h);
      ctx.strokeStyle = 'rgba(180,180,220,0.25)'; ctx.lineWidth=1;
      for (const [i,j] of edges){
        const a=nodes[i], b=nodes[j];
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
      }
      ctx.font='11px system-ui,sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
      for (const n of nodes){
        ctx.fillStyle = n.c;
        ctx.beginPath(); ctx.arc(n.x,n.y,7,0,Math.PI*2); ctx.fill();
        ctx.fillStyle = tx;
        ctx.fillText(n.label, n.x, n.y-14);
      }
    });
    return { stop(){ stop(); k.destroy(); } };
  };
})();

},
function (__hf) {

    if (!window.matchMedia || !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      HPX['knowledge-graph'](document.querySelector('.stage'));
    }
  
}
];
