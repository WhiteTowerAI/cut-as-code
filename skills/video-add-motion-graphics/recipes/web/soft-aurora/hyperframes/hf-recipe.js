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
/* soft-aurora.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform float uTime;\nuniform vec3 uResolution;\nuniform float uSpeed;\nuniform float uScale;\nuniform float uBrightness;\nuniform vec3 uColor1;\nuniform vec3 uColor2;\nuniform float uNoiseFreq;\nuniform float uNoiseAmp;\nuniform float uBandHeight;\nuniform float uBandSpread;\nuniform float uOctaveDecay;\nuniform float uLayerOffset;\nuniform float uColorSpeed;\nuniform vec2 uMouse;\nuniform float uMouseInfluence;\nuniform bool uEnableMouse;\n\n#define TAU 6.28318\n\nvec3 gradientHash(vec3 p) {\n  p = vec3(\n    dot(p, vec3(127.1, 311.7, 234.6)),\n    dot(p, vec3(269.5, 183.3, 198.3)),\n    dot(p, vec3(169.5, 283.3, 156.9))\n  );\n  vec3 h = fract(sin(p) * 43758.5453123);\n  float phi = acos(2.0 * h.x - 1.0);\n  float theta = TAU * h.y;\n  return vec3(cos(theta) * sin(phi), sin(theta) * cos(phi), cos(phi));\n}\n\nfloat quinticSmooth(float t) {\n  float t2 = t * t;\n  float t3 = t * t2;\n  return 6.0 * t3 * t2 - 15.0 * t2 * t2 + 10.0 * t3;\n}\n\nvec3 cosineGradient(float t, vec3 a, vec3 b, vec3 c, vec3 d) {\n  return a + b * cos(TAU * (c * t + d));\n}\n\nfloat perlin3D(float amplitude, float frequency, float px, float py, float pz) {\n  float x = px * frequency;\n  float y = py * frequency;\n\n  float fx = floor(x); float fy = floor(y); float fz = floor(pz);\n  float cx = ceil(x);  float cy = ceil(y);  float cz = ceil(pz);\n\n  vec3 g000 = gradientHash(vec3(fx, fy, fz));\n  vec3 g100 = gradientHash(vec3(cx, fy, fz));\n  vec3 g010 = gradientHash(vec3(fx, cy, fz));\n  vec3 g110 = gradientHash(vec3(cx, cy, fz));\n  vec3 g001 = gradientHash(vec3(fx, fy, cz));\n  vec3 g101 = gradientHash(vec3(cx, fy, cz));\n  vec3 g011 = gradientHash(vec3(fx, cy, cz));\n  vec3 g111 = gradientHash(vec3(cx, cy, cz));\n\n  float d000 = dot(g000, vec3(x - fx, y - fy, pz - fz));\n  float d100 = dot(g100, vec3(x - cx, y - fy, pz - fz));\n  float d010 = dot(g010, vec3(x - fx, y - cy, pz - fz));\n  float d110 = dot(g110, vec3(x - cx, y - cy, pz - fz));\n  float d001 = dot(g001, vec3(x - fx, y - fy, pz - cz));\n  float d101 = dot(g101, vec3(x - cx, y - fy, pz - cz));\n  float d011 = dot(g011, vec3(x - fx, y - cy, pz - cz));\n  float d111 = dot(g111, vec3(x - cx, y - cy, pz - cz));\n\n  float sx = quinticSmooth(x - fx);\n  float sy = quinticSmooth(y - fy);\n  float sz = quinticSmooth(pz - fz);\n\n  float lx00 = mix(d000, d100, sx);\n  float lx10 = mix(d010, d110, sx);\n  float lx01 = mix(d001, d101, sx);\n  float lx11 = mix(d011, d111, sx);\n\n  float ly0 = mix(lx00, lx10, sy);\n  float ly1 = mix(lx01, lx11, sy);\n\n  return amplitude * mix(ly0, ly1, sz);\n}\n\nfloat auroraGlow(float t, vec2 shift) {\n  vec2 uv = gl_FragCoord.xy / uResolution.y;\n  uv += shift;\n\n  float noiseVal = 0.0;\n  float freq = uNoiseFreq;\n  float amp = uNoiseAmp;\n  vec2 samplePos = uv * uScale;\n\n  for (float i = 0.0; i < 3.0; i += 1.0) {\n    noiseVal += perlin3D(amp, freq, samplePos.x, samplePos.y, t);\n    amp *= uOctaveDecay;\n    freq *= 2.0;\n  }\n\n  float yBand = uv.y * 10.0 - uBandHeight * 10.0;\n  return 0.3 * max(exp(uBandSpread * (1.0 - 1.1 * abs(noiseVal + yBand))), 0.0);\n}\n\nvoid main() {\n  vec2 uv = gl_FragCoord.xy / uResolution.xy;\n  float t = uSpeed * 0.4 * uTime;\n\n  vec2 shift = vec2(0.0);\n  if (uEnableMouse) {\n    shift = (uMouse - 0.5) * uMouseInfluence;\n  }\n\n  vec3 col = vec3(0.0);\n  col += 0.99 * auroraGlow(t, shift) * cosineGradient(uv.x + uTime * uSpeed * 0.2 * uColorSpeed, vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.3, 0.20, 0.20)) * uColor1;\n  col += 0.99 * auroraGlow(t + uLayerOffset, shift) * cosineGradient(uv.x + uTime * uSpeed * 0.1 * uColorSpeed, vec3(0.5), vec3(0.5), vec3(2.0, 1.0, 0.0), vec3(0.5, 0.20, 0.25)) * uColor2;\n\n  col *= uBrightness;\n  float alpha = clamp(length(col), 0.0, 1.0);\n  gl_FragColor = vec4(col, alpha);\n}\n';
  function init(){ var els=document.querySelectorAll('.soft-aurora'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uSpeed":{"t":"1f","v":1},"uScale":{"t":"1f","v":1},"uBrightness":{"t":"1f","v":1},"uColor1":{"t":"3f","v":[0.55,0.5,1]},"uColor2":{"t":"3f","v":[0.55,0.5,1]},"uNoiseFreq":{"t":"1f","v":2},"uNoiseAmp":{"t":"1f","v":0.3},"uBandHeight":{"t":"1f","v":1},"uBandSpread":{"t":"1f","v":1},"uOctaveDecay":{"t":"1f","v":1},"uLayerOffset":{"t":"1f","v":1},"uColorSpeed":{"t":"1f","v":1},"uMouseInfluence":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
