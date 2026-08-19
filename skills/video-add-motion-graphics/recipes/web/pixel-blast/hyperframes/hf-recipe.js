/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
/* shaderbg.js — motion-anything · a tiny dependency-free full-screen fragment-shader runner.
 * Replaces ogl/three for react-bits-style background shaders. Handles both WebGL1
 * (attribute/varying/gl_FragColor) and WebGL2 (#version 300 es / in / out) fragment shaders.
 *
 * Usage:  ShaderBG(container, FRAG, { uniforms:{ uColor:{t:'3f',v:[1,1,1]}, uSpeed:{t:'1f',v:1} } })
 *   - Auto uniforms (set each frame if present): uTime/iTime (seconds), uResolution/iResolution
 *     (vec2 or vec3, auto-detected), uMouse (vec2, 0..1, follows the pointer).
 *   - Renders a static frame under prefers-reduced-motion. Falls back to data-fallback bg if no WebGL. */
(function (g) {
  'use strict';
  function reduced(){ return g.matchMedia && g.matchMedia('(prefers-reduced-motion: reduce)').matches; }
  function compile(gl, type, src){ var s=gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if(!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.warn('[shaderbg]', gl.getShaderInfoLog(s)); return s; }

  g.ShaderBG = function (el, FRAG, opts) {
    if(!el || el.__sbg) return; el.__sbg = 1; opts = opts || {};
    var isGL2 = /#version\s+300/.test(FRAG);
    var canvas=document.createElement('canvas'); canvas.style.cssText='width:100%;height:100%;display:block'; el.appendChild(canvas);
    var gl = isGL2 ? canvas.getContext('webgl2', {alpha:true, premultipliedAlpha:true, antialias:true}) : null;
    if(!gl) gl = canvas.getContext('webgl', {alpha:true, premultipliedAlpha:true, antialias:true});
    if(!gl){ el.style.background = el.getAttribute('data-fallback') || '#0b0b12'; return; }
    var gl2 = isGL2 && (gl instanceof (g.WebGL2RenderingContext||function(){}));
    var VERT = gl2
      ? '#version 300 es\nin vec2 position;\nin vec2 uv;\nout vec2 vUv;\nvoid main(){ vUv=uv; gl_Position=vec4(position,0.0,1.0); }\n'
      : 'attribute vec2 position;\nattribute vec2 uv;\nvarying vec2 vUv;\nvoid main(){ vUv=uv; gl_Position=vec4(position,0.0,1.0); }\n';
    gl.clearColor(0,0,0,0); gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    var p=gl.createProgram(); gl.attachShader(p, compile(gl,gl.VERTEX_SHADER,VERT)); gl.attachShader(p, compile(gl,gl.FRAGMENT_SHADER,FRAG)); gl.linkProgram(p);
    if(!gl.getProgramParameter(p, gl.LINK_STATUS)){ console.warn('[shaderbg] link', gl.getProgramInfoLog(p)); el.style.background = el.getAttribute('data-fallback') || '#0b0b12'; return; }
    gl.useProgram(p);
    // full-screen triangle: position + matching uv
    var pos=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,pos); gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1, 3,-1, -1,3]),gl.STATIC_DRAW);
    var lp=gl.getAttribLocation(p,'position'); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp,2,gl.FLOAT,false,0,0);
    var lu=gl.getAttribLocation(p,'uv'); if(lu>=0){ var uvb=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,uvb); gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0, 2,0, 0,2]),gl.STATIC_DRAW); gl.enableVertexAttribArray(lu); gl.vertexAttribPointer(lu,2,gl.FLOAT,false,0,0); }
    // uniform locations
    var U={}; ['uTime','iTime','uResolution','iResolution','uMouse'].forEach(function(n){ U[n]=gl.getUniformLocation(p,n); });
    var resDim3 = /vec3\s+(uResolution|iResolution)/.test(FRAG);
    var custom=[]; var uni=opts.uniforms||{}; Object.keys(uni).forEach(function(n){ var loc=gl.getUniformLocation(p,n); if(loc!=null) custom.push({loc:loc, s:uni[n]}); });
    function setU(c){ var t=c.s.t, v=c.s.v; if(t==='1f') gl.uniform1f(c.loc,v); else if(t==='2f') gl.uniform2f(c.loc,v[0],v[1]); else if(t==='3f') gl.uniform3f(c.loc,v[0],v[1],v[2]); else if(t==='1i') gl.uniform1i(c.loc,v); else if(t==='3fv') gl.uniform3fv(c.loc,new Float32Array(v)); else if(t==='2fv') gl.uniform2fv(c.loc,new Float32Array(v)); else if(t==='1fv') gl.uniform1fv(c.loc,new Float32Array(v)); }
    custom.forEach(setU);
    var mouse=[0.5,0.5]; el.addEventListener('pointermove', function(e){ var r=el.getBoundingClientRect(); mouse=[(e.clientX-r.left)/r.width, 1.0-(e.clientY-r.top)/r.height]; });
    var W=1,H=1; function resize(){ W=Math.max(1,el.offsetWidth||600); H=Math.max(1,el.offsetHeight||360); canvas.width=W; canvas.height=H; gl.viewport(0,0,W,H); }
    g.addEventListener('resize', resize); resize();
    var red=reduced();
    var ts=opts.timeScale||1, lastTime=red?2.0:0;
    function frame(t){ var time = red ? 2.0 : t*0.001*ts; lastTime=time;
      if(U.uTime) gl.uniform1f(U.uTime, time); if(U.iTime) gl.uniform1f(U.iTime, time);
      if(U.uResolution){ resDim3 ? gl.uniform3f(U.uResolution,W,H,1) : gl.uniform2f(U.uResolution,W,H); }
      if(U.iResolution){ resDim3 ? gl.uniform3f(U.iResolution,W,H,1) : gl.uniform2f(U.iResolution,W,H); }
      if(U.uMouse) gl.uniform2f(U.uMouse, mouse[0], mouse[1]);
      gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLES,0,3); if(!red) __hf.requestAnimationFrame(frame);
    }
    __hf.requestAnimationFrame(frame);
    // Handle for interactive recipes (e.g. click-ripple uniforms): set a custom uniform at runtime.
    return { gl:gl, program:p, canvas:canvas, el:el,
      time:function(){ return lastTime; },
      set:function(name, spec){ var loc=gl.getUniformLocation(p,name); if(loc==null) return; setU({loc:loc, s:spec}); } };
  };
})(window);

},
function (__hf) {
/* pixel-blast.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='#version 300 es\nprecision highp float;\nprecision highp float;\n\nuniform vec3  uColor;\nuniform vec2  uResolution;\nuniform float uTime;\nuniform float uPixelSize;\nuniform float uScale;\nuniform float uDensity;\nuniform float uPixelJitter;\nuniform int   uEnableRipples;\nuniform float uRippleSpeed;\nuniform float uRippleThickness;\nuniform float uRippleIntensity;\nuniform float uEdgeFade;\n\nuniform int   uShapeType;\nconst int SHAPE_SQUARE   = 0;\nconst int SHAPE_CIRCLE   = 1;\nconst int SHAPE_TRIANGLE = 2;\nconst int SHAPE_DIAMOND  = 3;\n\nconst int   MAX_CLICKS = 10;\n\nuniform vec2  uClickPos  [MAX_CLICKS];\nuniform float uClickTimes[MAX_CLICKS];\n\nout vec4 fragColor;\n\nfloat Bayer2(vec2 a) {\n  a = floor(a);\n  return fract(a.x / 2. + a.y * a.y * .75);\n}\n#define Bayer4(a) (Bayer2(.5*(a))*0.25 + Bayer2(a))\n#define Bayer8(a) (Bayer4(.5*(a))*0.25 + Bayer2(a))\n\n#define FBM_OCTAVES     5\n#define FBM_LACUNARITY  1.25\n#define FBM_GAIN        1.0\n\nfloat hash11(float n){ return fract(sin(n)*43758.5453); }\n\nfloat vnoise(vec3 p){\n  vec3 ip = floor(p);\n  vec3 fp = fract(p);\n  float n000 = hash11(dot(ip + vec3(0.0,0.0,0.0), vec3(1.0,57.0,113.0)));\n  float n100 = hash11(dot(ip + vec3(1.0,0.0,0.0), vec3(1.0,57.0,113.0)));\n  float n010 = hash11(dot(ip + vec3(0.0,1.0,0.0), vec3(1.0,57.0,113.0)));\n  float n110 = hash11(dot(ip + vec3(1.0,1.0,0.0), vec3(1.0,57.0,113.0)));\n  float n001 = hash11(dot(ip + vec3(0.0,0.0,1.0), vec3(1.0,57.0,113.0)));\n  float n101 = hash11(dot(ip + vec3(1.0,0.0,1.0), vec3(1.0,57.0,113.0)));\n  float n011 = hash11(dot(ip + vec3(0.0,1.0,1.0), vec3(1.0,57.0,113.0)));\n  float n111 = hash11(dot(ip + vec3(1.0,1.0,1.0), vec3(1.0,57.0,113.0)));\n  vec3 w = fp*fp*fp*(fp*(fp*6.0-15.0)+10.0);\n  float x00 = mix(n000, n100, w.x);\n  float x10 = mix(n010, n110, w.x);\n  float x01 = mix(n001, n101, w.x);\n  float x11 = mix(n011, n111, w.x);\n  float y0  = mix(x00, x10, w.y);\n  float y1  = mix(x01, x11, w.y);\n  return mix(y0, y1, w.z) * 2.0 - 1.0;\n}\n\nfloat fbm2(vec2 uv, float t){\n  vec3 p = vec3(uv * uScale, t);\n  float amp = 1.0;\n  float freq = 1.0;\n  float sum = 1.0;\n  for (int i = 0; i < FBM_OCTAVES; ++i){\n    sum  += amp * vnoise(p * freq);\n    freq *= FBM_LACUNARITY;\n    amp  *= FBM_GAIN;\n  }\n  return sum * 0.5 + 0.5;\n}\n\nfloat maskCircle(vec2 p, float cov){\n  float r = sqrt(cov) * .25;\n  float d = length(p - 0.5) - r;\n  float aa = 0.5 * fwidth(d);\n  return cov * (1.0 - smoothstep(-aa, aa, d * 2.0));\n}\n\nfloat maskTriangle(vec2 p, vec2 id, float cov){\n  bool flip = mod(id.x + id.y, 2.0) > 0.5;\n  if (flip) p.x = 1.0 - p.x;\n  float r = sqrt(cov);\n  float d  = p.y - r*(1.0 - p.x);\n  float aa = fwidth(d);\n  return cov * clamp(0.5 - d/aa, 0.0, 1.0);\n}\n\nfloat maskDiamond(vec2 p, float cov){\n  float r = sqrt(cov) * 0.564;\n  return step(abs(p.x - 0.49) + abs(p.y - 0.49), r);\n}\n\nvoid main(){\n  float pixelSize = uPixelSize;\n  vec2 fragCoord = gl_FragCoord.xy - uResolution * .5;\n  float aspectRatio = uResolution.x / uResolution.y;\n\n  vec2 pixelId = floor(fragCoord / pixelSize);\n  vec2 pixelUV = fract(fragCoord / pixelSize);\n\n  float cellPixelSize = 8.0 * pixelSize;\n  vec2 cellId = floor(fragCoord / cellPixelSize);\n  vec2 cellCoord = cellId * cellPixelSize;\n  vec2 uv = cellCoord / uResolution * vec2(aspectRatio, 1.0);\n\n  float base = fbm2(uv, uTime * 0.05);\n  base = base * 0.5 - 0.65;\n\n  float feed = base + (uDensity - 0.5) * 0.3;\n\n  float speed     = uRippleSpeed;\n  float thickness = uRippleThickness;\n  const float dampT     = 1.0;\n  const float dampR     = 10.0;\n\n  if (uEnableRipples == 1) {\n    for (int i = 0; i < MAX_CLICKS; ++i){\n      vec2 pos = uClickPos[i];\n      if (pos.x < 0.0) continue;\n      float cellPixelSize = 8.0 * pixelSize;\n      vec2 cuv = (((pos - uResolution * .5 - cellPixelSize * .5) / (uResolution))) * vec2(aspectRatio, 1.0);\n      float t = max(uTime - uClickTimes[i], 0.0);\n      float r = distance(uv, cuv);\n      float waveR = speed * t;\n      float ring  = exp(-pow((r - waveR) / thickness, 2.0));\n      float atten = exp(-dampT * t) * exp(-dampR * r);\n      feed = max(feed, ring * atten * uRippleIntensity);\n    }\n  }\n\n  float bayer = Bayer8(fragCoord / uPixelSize) - 0.5;\n  float bw = step(0.5, feed + bayer);\n\n  float h = fract(sin(dot(floor(fragCoord / uPixelSize), vec2(127.1, 311.7))) * 43758.5453);\n  float jitterScale = 1.0 + (h - 0.5) * uPixelJitter;\n  float coverage = bw * jitterScale;\n  float M;\n  if      (uShapeType == SHAPE_CIRCLE)   M = maskCircle (pixelUV, coverage);\n  else if (uShapeType == SHAPE_TRIANGLE) M = maskTriangle(pixelUV, pixelId, coverage);\n  else if (uShapeType == SHAPE_DIAMOND)  M = maskDiamond(pixelUV, coverage);\n  else                                   M = coverage;\n\n  if (uEdgeFade > 0.0) {\n    vec2 norm = gl_FragCoord.xy / uResolution;\n    float edge = min(min(norm.x, norm.y), min(1.0 - norm.x, 1.0 - norm.y));\n    float fade = smoothstep(0.0, uEdgeFade, edge);\n    M *= fade;\n  }\n\n  vec3 color = uColor;\n\n  // sRGB gamma correction - convert linear to sRGB for accurate color output\n  vec3 srgbColor = mix(\n    color * 12.92,\n    1.055 * pow(color, vec3(1.0 / 2.4)) - 0.055,\n    step(0.0031308, color)\n  );\n\n  fragColor = vec4(srgbColor * M, M);\n}\n';
  function init(){ var els=document.querySelectorAll('.pixel-blast'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    var h=g.ShaderBG(els[i], FRAG, {"timeScale":0.5,"uniforms":{"uColor":{"t":"3f","v":[0.7058823529411765,0.592156862745098,0.8117647058823529]},"uShapeType":{"t":"1i","v":0},"uPixelSize":{"t":"1f","v":3},"uScale":{"t":"1f","v":2},"uDensity":{"t":"1f","v":1},"uPixelJitter":{"t":"1f","v":0},"uEnableRipples":{"t":"1i","v":1},"uRippleSpeed":{"t":"1f","v":0.3},"uRippleThickness":{"t":"1f","v":0.1},"uRippleIntensity":{"t":"1f","v":1},"uEdgeFade":{"t":"1f","v":0.5},"uClickPos":{"t":"2fv","v":[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]},"uClickTimes":{"t":"1fv","v":[0,0,0,0,0,0,0,0,0,0]}}});
    if(h){ (function(){ var N=10, pos=new Array(2*N), times=new Array(N), ix=0, k;
      for(k=0;k<N;k++){ pos[2*k]=-1; pos[2*k+1]=-1; times[k]=0; }
      h.el.addEventListener('pointerdown', function(e){ var r=h.el.getBoundingClientRect();
        var sx=h.canvas.width/r.width, sy=h.canvas.height/r.height;
        pos[2*ix]=(e.clientX-r.left)*sx; pos[2*ix+1]=(r.height-(e.clientY-r.top))*sy;
        times[ix]=h.time(); ix=(ix+1)%N;
        h.set('uClickPos',{t:'2fv',v:pos}); h.set('uClickTimes',{t:'1fv',v:times}); }); })(); } } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
