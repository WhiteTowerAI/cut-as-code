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
/* dither.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js).
 * Hand-merged from the react-bits two-pass original (wave shader → retro Bayer-dither postprocess):
 * the wave is procedural, so sampling pass-1 at the pixelated uv == computing the wave AT that uv —
 * one #version 300 es frag replicates both passes with zero framebuffers. Real defaults from source. */
(function(g){ 'use strict';
  var FRAG = '#version 300 es\n'
  + 'precision highp float;\n'
  + 'out vec4 fragColor;\n'
  + 'uniform vec2 uResolution;\n'
  + 'uniform float uTime;\n'
  + 'uniform vec2 uMouse;\n'
  + 'uniform float waveSpeed;\n'
  + 'uniform float waveFrequency;\n'
  + 'uniform float waveAmplitude;\n'
  + 'uniform vec3 waveColor;\n'
  + 'uniform int enableMouseInteraction;\n'
  + 'uniform float mouseRadius;\n'
  + 'uniform float colorNum;\n'
  + 'uniform float pixelSize;\n'
  + 'vec4 mod289(vec4 x){ return x - floor(x * (1.0/289.0)) * 289.0; }\n'
  + 'vec4 permute(vec4 x){ return mod289(((x * 34.0) + 1.0) * x); }\n'
  + 'vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314 * r; }\n'
  + 'vec2 fade(vec2 t){ return t*t*t*(t*(t*6.0-15.0)+10.0); }\n'
  + 'float cnoise(vec2 P){\n'
  + '  vec4 Pi = floor(P.xyxy) + vec4(0.0,0.0,1.0,1.0);\n'
  + '  vec4 Pf = fract(P.xyxy) - vec4(0.0,0.0,1.0,1.0);\n'
  + '  Pi = mod289(Pi);\n'
  + '  vec4 ix = Pi.xzxz; vec4 iy = Pi.yyww; vec4 fx = Pf.xzxz; vec4 fy = Pf.yyww;\n'
  + '  vec4 i = permute(permute(ix) + iy);\n'
  + '  vec4 gx = fract(i * (1.0/41.0)) * 2.0 - 1.0;\n'
  + '  vec4 gy = abs(gx) - 0.5; vec4 tx = floor(gx + 0.5); gx = gx - tx;\n'
  + '  vec2 g00 = vec2(gx.x, gy.x); vec2 g10 = vec2(gx.y, gy.y);\n'
  + '  vec2 g01 = vec2(gx.z, gy.z); vec2 g11 = vec2(gx.w, gy.w);\n'
  + '  vec4 norm = taylorInvSqrt(vec4(dot(g00,g00), dot(g01,g01), dot(g10,g10), dot(g11,g11)));\n'
  + '  g00 *= norm.x; g01 *= norm.y; g10 *= norm.z; g11 *= norm.w;\n'
  + '  float n00 = dot(g00, vec2(fx.x, fy.x)); float n10 = dot(g10, vec2(fx.y, fy.y));\n'
  + '  float n01 = dot(g01, vec2(fx.z, fy.z)); float n11 = dot(g11, vec2(fx.w, fy.w));\n'
  + '  vec2 fade_xy = fade(Pf.xy);\n'
  + '  vec2 n_x = mix(vec2(n00, n01), vec2(n10, n11), fade_xy.x);\n'
  + '  return 2.3 * mix(n_x.x, n_x.y, fade_xy.y);\n'
  + '}\n'
  + 'const int OCTAVES = 4;\n'
  + 'float fbm(vec2 p){\n'
  + '  float value = 0.0; float amp = 1.0; float freq = waveFrequency;\n'
  + '  for (int i = 0; i < OCTAVES; i++){ value += amp * abs(cnoise(p)); p *= freq; amp *= waveAmplitude; }\n'
  + '  return value;\n'
  + '}\n'
  + 'float pattern(vec2 p){ vec2 p2 = p - uTime * waveSpeed; return fbm(p + fbm(p2)); }\n'
  + 'const float bayerMatrix8x8[64] = float[64](\n'
  + '  0.0/64.0, 48.0/64.0, 12.0/64.0, 60.0/64.0,  3.0/64.0, 51.0/64.0, 15.0/64.0, 63.0/64.0,\n'
  + '  32.0/64.0,16.0/64.0, 44.0/64.0, 28.0/64.0, 35.0/64.0,19.0/64.0, 47.0/64.0, 31.0/64.0,\n'
  + '  8.0/64.0, 56.0/64.0,  4.0/64.0, 52.0/64.0, 11.0/64.0,59.0/64.0,  7.0/64.0, 55.0/64.0,\n'
  + '  40.0/64.0,24.0/64.0, 36.0/64.0, 20.0/64.0, 43.0/64.0,27.0/64.0, 39.0/64.0, 23.0/64.0,\n'
  + '  2.0/64.0, 50.0/64.0, 14.0/64.0, 62.0/64.0,  1.0/64.0,49.0/64.0, 13.0/64.0, 61.0/64.0,\n'
  + '  34.0/64.0,18.0/64.0, 46.0/64.0, 30.0/64.0, 33.0/64.0,17.0/64.0, 45.0/64.0, 29.0/64.0,\n'
  + '  10.0/64.0,58.0/64.0,  6.0/64.0, 54.0/64.0,  9.0/64.0,57.0/64.0,  5.0/64.0, 53.0/64.0,\n'
  + '  42.0/64.0,26.0/64.0, 38.0/64.0, 22.0/64.0, 41.0/64.0,25.0/64.0, 37.0/64.0, 21.0/64.0\n'
  + ');\n'
  + 'vec3 dither(vec2 uv, vec3 color){\n'
  + '  vec2 scaledCoord = floor(uv * uResolution / pixelSize);\n'
  + '  int x = int(mod(scaledCoord.x, 8.0)); int y = int(mod(scaledCoord.y, 8.0));\n'
  + '  float threshold = bayerMatrix8x8[y * 8 + x] - 0.25;\n'
  + '  float step = 1.0 / (colorNum - 1.0);\n'
  + '  color += threshold * step;\n'
  + '  float bias = 0.2;\n'
  + '  color = clamp(color - bias, 0.0, 1.0);\n'
  + '  return floor(color * (colorNum - 1.0) + 0.5) / (colorNum - 1.0);\n'
  + '}\n'
  + 'void main(){\n'
  + '  vec2 uvScreen = gl_FragCoord.xy / uResolution;\n'
  + '  vec2 normalizedPixelSize = pixelSize / uResolution;\n'
  + '  vec2 uvPixel = normalizedPixelSize * floor(uvScreen / normalizedPixelSize);\n'
  + '  vec2 fragPix = uvPixel * uResolution;\n'
  + '  vec2 uv = fragPix / uResolution - 0.5;\n'
  + '  uv.x *= uResolution.x / uResolution.y;\n'
  + '  float f = pattern(uv);\n'
  + '  if (enableMouseInteraction == 1) {\n'
  + '    vec2 mouseNDC = uMouse - 0.5;\n'      /* shaderbg uMouse is 0..1, bottom-origin — already "up" */
  + '    mouseNDC.x *= uResolution.x / uResolution.y;\n'
  + '    float dist = length(uv - mouseNDC);\n'
  + '    float effect = 1.0 - smoothstep(0.0, mouseRadius, dist);\n'
  + '    f -= 0.5 * effect;\n'
  + '  }\n'
  + '  vec3 col = mix(vec3(0.0), waveColor, f);\n'
  + '  col = dither(uvScreen, col);\n'
  + '  fragColor = vec4(col, 1.0);\n'
  + '}\n';
  function init(){ var els=document.querySelectorAll('.dither'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{
      waveSpeed:{t:'1f',v:0.05}, waveFrequency:{t:'1f',v:3}, waveAmplitude:{t:'1f',v:0.3},
      waveColor:{t:'3f',v:[0.5,0.5,0.5]}, enableMouseInteraction:{t:'1i',v:1}, mouseRadius:{t:'1f',v:1},
      colorNum:{t:'1f',v:4}, pixelSize:{t:'1f',v:2} } }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
