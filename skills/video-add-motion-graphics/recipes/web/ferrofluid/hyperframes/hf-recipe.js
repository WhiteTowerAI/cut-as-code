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
/* ferrofluid.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform vec3  iResolution;\nuniform vec2  iMouse;\nuniform float iTime;\n\nuniform vec3  uColor0;\nuniform vec3  uColor1;\nuniform vec3  uColor2;\nuniform vec3  uColor3;\nuniform vec3  uColor4;\nuniform vec3  uColor5;\nuniform vec3  uColor6;\nuniform vec3  uColor7;\nuniform int   uColorCount;\n\nuniform vec3  uMouseColor;\nuniform vec2  uFlow;\nuniform float uSpeed;\nuniform float uScale;\nuniform float uTurbulence;\nuniform float uFluidity;\nuniform float uRimWidth;\nuniform float uSharpness;\nuniform float uShimmer;\nuniform float uGlow;\nuniform float uOpacity;\nuniform float uMouseEnabled;\nuniform float uMouseStrength;\nuniform float uMouseRadius;\n\nvarying vec2 vUv;\n\n#define PI 3.14159265\n\nvec3 palette(float h) {\n  int count = uColorCount;\n  if (count < 1) count = 1;\n  int idx = int(floor(clamp(h, 0.0, 0.999999) * float(count)));\n  if (idx <= 0) return uColor0;\n  if (idx == 1) return uColor1;\n  if (idx == 2) return uColor2;\n  if (idx == 3) return uColor3;\n  if (idx == 4) return uColor4;\n  if (idx == 5) return uColor5;\n  if (idx == 6) return uColor6;\n  return uColor7;\n}\n\nfloat hash(vec3 p3) {\n  p3 = fract(p3 * 0.1031);\n  p3 += dot(p3, p3.zyx + 33.33);\n  return fract((p3.x + p3.y) * p3.z);\n}\n\nfloat smin(float a, float b, float k) {\n  float r = exp2(-a / k) + exp2(-b / k);\n  return -k * log2(r);\n}\n\nfloat sinlerp(float a, float b, float w) {\n  return mix(a, b, (sin(w * PI - PI / 2.0) + 1.0) / 2.0);\n}\n\nfloat vn(vec2 p, float s, float seed) {\n  vec2 cellp = floor(p / s);\n  vec2 relp = mod(p, s);\n  float g1 = hash(vec3(cellp, seed));\n  float g2 = hash(vec3(cellp.x + 1.0, cellp.y, seed));\n  float g3 = hash(vec3(cellp.x + 1.0, cellp.y + 1.0, seed));\n  float g4 = hash(vec3(cellp.x, cellp.y + 1.0, seed));\n  float bx = sinlerp(g1, g2, relp.x / s);\n  float tx = sinlerp(g4, g3, relp.x / s);\n  return sinlerp(bx, tx, relp.y / s);\n}\n\nfloat dbn(vec2 p, float s, float seed) {\n  float o = s / 2.0;\n  float n0 = vn(p, s, seed);\n  float n1 = vn(p + vec2(o, o), s, seed + 0.1);\n  float n2 = vn(p + vec2(-o, o), s, seed + 0.2);\n  float n3 = vn(p + vec2(o, -o), s, seed + 0.3);\n  float n4 = vn(p + vec2(-o, -o), s, seed + 0.4);\n  return (2.0 * n0 + 1.5 * n1 + 1.25 * n2 + 1.125 * n3 + n4) / 7.0;\n}\n\nvoid mainImage(out vec4 fragColor, in vec2 fragCoord) {\n  float ref = 700.0 / max(uScale, 0.05);\n  vec2 p = fragCoord / iResolution.y * ref;\n\n  float spd = 200.0 * uSpeed;\n  float t = iTime;\n\n  vec2 dir = uFlow;\n  vec2 perp = vec2(-dir.y, dir.x);\n\n  float distort1 = vn(p + perp * (t * spd), 60.0, 10.0) * 50.0 * uTurbulence;\n  float distort2 = vn(p - perp * (t * spd), 120.0, 15.0) * 100.0 * uTurbulence;\n\n  float peaks = dbn(p + distort1 + dir * (t * spd * 0.5), 40.0, 1.0);\n  float peaks2 = dbn(p + distort2 - dir * (t * spd * 0.5), 40.0, 0.0);\n\n  float mapeaks = smin(peaks, peaks2, max(uFluidity, 0.001));\n\n  float mGlow = 0.0;\n  if (uMouseEnabled > 0.5) {\n    vec2 mp = iMouse / iResolution.y * ref;\n    float md = length(p - mp) / ref;\n    float rr = max(uMouseRadius, 0.02);\n    mGlow = exp(-md * md / (rr * rr)) * uMouseStrength;\n  }\n\n  float band = (uRimWidth - abs((mapeaks - 0.4) * 2.0)) * 5.0;\n  float ltn = clamp(band - vn(p + dir * (t * spd * 0.5), 60.0, 12.0) * uShimmer, 0.0, 1.0);\n  ltn = pow(ltn, uSharpness) * uGlow;\n  ltn *= clamp(1.0 - mGlow, 0.0, 1.0);\n\n  float h = clamp(0.5 + (peaks - peaks2) * 0.8, 0.0, 1.0);\n  vec3 col = palette(h);\n\n  vec3 outc = col * ltn;\n  float a = clamp(max(outc.r, max(outc.g, outc.b)), 0.0, 1.0);\n  fragColor = vec4(outc, a * uOpacity);\n}\n\nvoid main() {\n  vec4 color;\n  mainImage(color, vUv * iResolution.xy);\n  gl_FragColor = color;\n}\n';
  function init(){ var els=document.querySelectorAll('.ferrofluid'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uColor0":{"t":"3f","v":[1,1,1]},"uColor1":{"t":"3f","v":[1,1,1]},"uColor2":{"t":"3f","v":[1,1,1]},"uColor3":{"t":"3f","v":[1,1,1]},"uColor4":{"t":"3f","v":[1,1,1]},"uColor5":{"t":"3f","v":[1,1,1]},"uColor6":{"t":"3f","v":[1,1,1]},"uColor7":{"t":"3f","v":[1,1,1]},"uColorCount":{"t":"1i","v":3},"uMouseColor":{"t":"3f","v":[1,1,1]},"uFlow":{"t":"2f","v":[0,-1]},"uSpeed":{"t":"1f","v":0.5},"uScale":{"t":"1f","v":1.6},"uTurbulence":{"t":"1f","v":1},"uFluidity":{"t":"1f","v":0.1},"uRimWidth":{"t":"1f","v":0.2},"uSharpness":{"t":"1f","v":2.5},"uShimmer":{"t":"1f","v":1.5},"uGlow":{"t":"1f","v":2},"uOpacity":{"t":"1f","v":1},"uMouseEnabled":{"t":"1f","v":0},"uMouseStrength":{"t":"1f","v":1},"uMouseRadius":{"t":"1f","v":0.35}} });  } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
