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
/* plasma-wave.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision mediump float;\nuniform float iTime;\nuniform vec2  iResolution;\nuniform vec2  uOffset;\nuniform float uRotation;\nuniform float uFocalLength;\nuniform float uSpeed1;\nuniform float uSpeed2;\nuniform float uDir2;\nuniform float uBend1;\nuniform float uBend2;\nuniform vec3  uColor1;\nuniform vec3  uColor2;\n\nconst float lt   = 0.3;\nconst float pi   = 3.14159;\nconst float pi2  = 6.28318;\nconst float pi_2 = 1.5708;\n#define MAX_STEPS 14\n\nvoid mainImage(out vec4 C, in vec2 U) {\n  float t = iTime * pi;\n  float s = 1.0;\n  float d = 0.0;\n  vec2  R = iResolution;\n\n  vec3 o = vec3(0.0, 0.0, -7.0);\n  vec3 u = normalize(vec3((U - 0.5 * R) / R.y, uFocalLength));\n  vec2 k = vec2(0.0);\n  vec3 p;\n\n  float t1 = t * 0.7;\n  float t2 = t * 0.9;\n  float tSpeed1 = t * uSpeed1;\n  float tSpeed2 = t * uSpeed2 * uDir2;\n\n  for (int i = 0; i < MAX_STEPS; ++i) {\n    p = o + u * d;\n    p.x -= 15.0;\n\n    float px = p.x;\n    float wob1 = uBend1 + sin(t1 + px * 0.8) * 0.1;\n    float wob2 = uBend2 + cos(t2 + px * 1.1) * 0.1;\n\n    float px2 = px + pi_2;\n    vec2 sinOffset = sin(vec2(px, px2) + tSpeed1) * wob1;\n    vec2 cosOffset = cos(vec2(px, px2) + tSpeed2) * wob2;\n\n    vec2 yz = p.yz;\n    float pxLt = px + lt;\n    k.x = max(pxLt, length(yz - sinOffset) - lt);\n    k.y = max(pxLt, length(yz - cosOffset) - lt);\n\n    float current = min(k.x, k.y);\n    s = min(s, current);\n    if (s < 0.001 || d > 300.0) break;\n    d += s * 0.7;\n  }\n\n  float sqrtD = sqrt(d);\n  vec3 raw = max(cos(d * pi2) - s * sqrtD - vec3(k, 0.0), 0.0);\n  raw.gb += 0.1;\n  float maxC = max(raw.r, max(raw.g, raw.b));\n  if (maxC < 0.15) discard;\n  raw = raw * 0.4 + raw.brg * 0.6 + raw * raw;\n  float lum = dot(raw, vec3(0.299, 0.587, 0.114));\n  float w1 = max(0.0, 1.0 - k.x * 2.0);\n  float w2 = max(0.0, 1.0 - k.y * 2.0);\n  float wt = w1 + w2 + 0.001;\n  vec3 c = (uColor1 * w1 + uColor2 * w2) / wt * lum * 3.5;\n  C = vec4(c, 1.0);\n}\n\nvoid main() {\n  vec2 coord = gl_FragCoord.xy + uOffset;\n  coord -= 0.5 * iResolution;\n  float c = cos(uRotation), s = sin(uRotation);\n  coord = mat2(c, -s, s, c) * coord;\n  coord += 0.5 * iResolution;\n\n  vec4 color;\n  mainImage(color, coord);\n  gl_FragColor = color;\n}\n';
  function init(){ var els=document.querySelectorAll('.plasma-wave'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uOffset":{"t":"2f","v":[0.5,0.5]},"uRotation":{"t":"1f","v":1},"uFocalLength":{"t":"1f","v":1},"uSpeed1":{"t":"1f","v":1},"uSpeed2":{"t":"1f","v":1},"uDir2":{"t":"1f","v":1},"uBend1":{"t":"1f","v":1},"uBend2":{"t":"1f","v":1},"uColor1":{"t":"3f","v":[0.55,0.5,1]},"uColor2":{"t":"3f","v":[0.55,0.5,1]}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
