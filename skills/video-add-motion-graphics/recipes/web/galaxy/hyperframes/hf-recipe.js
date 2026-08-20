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
/* galaxy.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform float uTime;\nuniform vec3 uResolution;\nuniform vec2 uFocal;\nuniform vec2 uRotation;\nuniform float uStarSpeed;\nuniform float uDensity;\nuniform float uHueShift;\nuniform float uSpeed;\nuniform vec2 uMouse;\nuniform float uGlowIntensity;\nuniform float uSaturation;\nuniform bool uMouseRepulsion;\nuniform float uTwinkleIntensity;\nuniform float uRotationSpeed;\nuniform float uRepulsionStrength;\nuniform float uMouseActiveFactor;\nuniform float uAutoCenterRepulsion;\nuniform bool uTransparent;\n\nvarying vec2 vUv;\n\n#define NUM_LAYER 4.0\n#define STAR_COLOR_CUTOFF 0.2\n#define MAT45 mat2(0.7071, -0.7071, 0.7071, 0.7071)\n#define PERIOD 3.0\n\nfloat Hash21(vec2 p) {\n  p = fract(p * vec2(123.34, 456.21));\n  p += dot(p, p + 45.32);\n  return fract(p.x * p.y);\n}\n\nfloat tri(float x) {\n  return abs(fract(x) * 2.0 - 1.0);\n}\n\nfloat tris(float x) {\n  float t = fract(x);\n  return 1.0 - smoothstep(0.0, 1.0, abs(2.0 * t - 1.0));\n}\n\nfloat trisn(float x) {\n  float t = fract(x);\n  return 2.0 * (1.0 - smoothstep(0.0, 1.0, abs(2.0 * t - 1.0))) - 1.0;\n}\n\nvec3 hsv2rgb(vec3 c) {\n  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);\n  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);\n  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);\n}\n\nfloat Star(vec2 uv, float flare) {\n  float d = length(uv);\n  float m = (0.05 * uGlowIntensity) / d;\n  float rays = smoothstep(0.0, 1.0, 1.0 - abs(uv.x * uv.y * 1000.0));\n  m += rays * flare * uGlowIntensity;\n  uv *= MAT45;\n  rays = smoothstep(0.0, 1.0, 1.0 - abs(uv.x * uv.y * 1000.0));\n  m += rays * 0.3 * flare * uGlowIntensity;\n  m *= smoothstep(1.0, 0.2, d);\n  return m;\n}\n\nvec3 StarLayer(vec2 uv) {\n  vec3 col = vec3(0.0);\n\n  vec2 gv = fract(uv) - 0.5; \n  vec2 id = floor(uv);\n\n  for (int y = -1; y <= 1; y++) {\n    for (int x = -1; x <= 1; x++) {\n      vec2 offset = vec2(float(x), float(y));\n      vec2 si = id + vec2(float(x), float(y));\n      float seed = Hash21(si);\n      float size = fract(seed * 345.32);\n      float glossLocal = tri(uStarSpeed / (PERIOD * seed + 1.0));\n      float flareSize = smoothstep(0.9, 1.0, size) * glossLocal;\n\n      float red = smoothstep(STAR_COLOR_CUTOFF, 1.0, Hash21(si + 1.0)) + STAR_COLOR_CUTOFF;\n      float blu = smoothstep(STAR_COLOR_CUTOFF, 1.0, Hash21(si + 3.0)) + STAR_COLOR_CUTOFF;\n      float grn = min(red, blu) * seed;\n      vec3 base = vec3(red, grn, blu);\n      \n      float hue = atan(base.g - base.r, base.b - base.r) / (2.0 * 3.14159) + 0.5;\n      hue = fract(hue + uHueShift / 360.0);\n      float sat = length(base - vec3(dot(base, vec3(0.299, 0.587, 0.114)))) * uSaturation;\n      float val = max(max(base.r, base.g), base.b);\n      base = hsv2rgb(vec3(hue, sat, val));\n\n      vec2 pad = vec2(tris(seed * 34.0 + uTime * uSpeed / 10.0), tris(seed * 38.0 + uTime * uSpeed / 30.0)) - 0.5;\n\n      float star = Star(gv - offset - pad, flareSize);\n      vec3 color = base;\n\n      float twinkle = trisn(uTime * uSpeed + seed * 6.2831) * 0.5 + 1.0;\n      twinkle = mix(1.0, twinkle, uTwinkleIntensity);\n      star *= twinkle;\n      \n      col += star * size * color;\n    }\n  }\n\n  return col;\n}\n\nvoid main() {\n  vec2 focalPx = uFocal * uResolution.xy;\n  vec2 uv = (vUv * uResolution.xy - focalPx) / uResolution.y;\n\n  vec2 mouseNorm = uMouse - vec2(0.5);\n  \n  if (uAutoCenterRepulsion > 0.0) {\n    vec2 centerUV = vec2(0.0, 0.0);\n    float centerDist = length(uv - centerUV);\n    vec2 repulsion = normalize(uv - centerUV) * (uAutoCenterRepulsion / (centerDist + 0.1));\n    uv += repulsion * 0.05;\n  } else if (uMouseRepulsion) {\n    vec2 mousePosUV = (uMouse * uResolution.xy - focalPx) / uResolution.y;\n    float mouseDist = length(uv - mousePosUV);\n    vec2 repulsion = normalize(uv - mousePosUV) * (uRepulsionStrength / (mouseDist + 0.1));\n    uv += repulsion * 0.05 * uMouseActiveFactor;\n  } else {\n    vec2 mouseOffset = mouseNorm * 0.1 * uMouseActiveFactor;\n    uv += mouseOffset;\n  }\n\n  float autoRotAngle = uTime * uRotationSpeed;\n  mat2 autoRot = mat2(cos(autoRotAngle), -sin(autoRotAngle), sin(autoRotAngle), cos(autoRotAngle));\n  uv = autoRot * uv;\n\n  uv = mat2(uRotation.x, -uRotation.y, uRotation.y, uRotation.x) * uv;\n\n  vec3 col = vec3(0.0);\n\n  for (float i = 0.0; i < 1.0; i += 1.0 / NUM_LAYER) {\n    float depth = fract(i + uStarSpeed * uSpeed);\n    float scale = mix(20.0 * uDensity, 0.5 * uDensity, depth);\n    float fade = depth * smoothstep(1.0, 0.9, depth);\n    col += StarLayer(uv * scale + i * 453.32) * fade;\n  }\n\n  if (uTransparent) {\n    float alpha = length(col);\n    alpha = smoothstep(0.0, 0.3, alpha);\n    alpha = min(alpha, 1.0);\n    gl_FragColor = vec4(col, alpha);\n  } else {\n    gl_FragColor = vec4(col, 1.0);\n  }\n}\n';
  function init(){ var els=document.querySelectorAll('.galaxy'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uFocal":{"t":"2f","v":[0.5,0.5]},"uRotation":{"t":"2f","v":[0.5,0.5]},"uStarSpeed":{"t":"1f","v":1},"uDensity":{"t":"1f","v":1},"uHueShift":{"t":"1f","v":0},"uSpeed":{"t":"1f","v":1},"uGlowIntensity":{"t":"1f","v":1},"uSaturation":{"t":"1f","v":1},"uTwinkleIntensity":{"t":"1f","v":1},"uRotationSpeed":{"t":"1f","v":1},"uRepulsionStrength":{"t":"1f","v":1},"uMouseActiveFactor":{"t":"1f","v":1},"uAutoCenterRepulsion":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
