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
/* pixel-snow.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='#version 300 es\nprecision highp float;\nout vec4 fragColor;\nprecision mediump float;\n\nuniform float uTime;\nuniform vec2 uResolution;\nuniform float uFlakeSize;\nuniform float uMinFlakeSize;\nuniform float uPixelResolution;\nuniform float uSpeed;\nuniform float uDepthFade;\nuniform float uFarPlane;\nuniform vec3 uColor;\nuniform float uBrightness;\nuniform float uGamma;\nuniform float uDensity;\nuniform float uVariant;\nuniform float uDirection;\n\n// Precomputed constants\n#define PI 3.14159265\n#define PI_OVER_6 0.5235988\n#define PI_OVER_3 1.0471976\n#define INV_SQRT3 0.57735027\n#define M1 1597334677U\n#define M2 3812015801U\n#define M3 3299493293U\n#define F0 2.3283064e-10\n\n// Optimized hash - inline multiplication\n#define hash(n) (n * (n ^ (n >> 15)))\n#define coord3(p) (uvec3(p).x * M1 ^ uvec3(p).y * M2 ^ uvec3(p).z * M3)\n\n// Precomputed camera basis vectors (normalized vec3(1,1,1), vec3(1,0,-1))\nconst vec3 camK = vec3(0.57735027, 0.57735027, 0.57735027);\nconst vec3 camI = vec3(0.70710678, 0.0, -0.70710678);\nconst vec3 camJ = vec3(-0.40824829, 0.81649658, -0.40824829);\n\n// Precomputed branch direction\nconst vec2 b1d = vec2(0.574, 0.819);\n\nvec3 hash3(uint n) {\n  uvec3 hashed = hash(n) * uvec3(1U, 511U, 262143U);\n  return vec3(hashed) * F0;\n}\n\nfloat snowflakeDist(vec2 p) {\n  float r = length(p);\n  float a = atan(p.y, p.x);\n  a = abs(mod(a + PI_OVER_6, PI_OVER_3) - PI_OVER_6);\n  vec2 q = r * vec2(cos(a), sin(a));\n  float dMain = max(abs(q.y), max(-q.x, q.x - 1.0));\n  float b1t = clamp(dot(q - vec2(0.4, 0.0), b1d), 0.0, 0.4);\n  float dB1 = length(q - vec2(0.4, 0.0) - b1t * b1d);\n  float b2t = clamp(dot(q - vec2(0.7, 0.0), b1d), 0.0, 0.25);\n  float dB2 = length(q - vec2(0.7, 0.0) - b2t * b1d);\n  return min(dMain, min(dB1, dB2)) * 10.0;\n}\n\nvoid main() {\n  // Precompute reciprocals to avoid division\n  float invPixelRes = 1.0 / uPixelResolution;\n  float pixelSize = max(1.0, floor(0.5 + uResolution.x * invPixelRes));\n  float invPixelSize = 1.0 / pixelSize;\n  \n  vec2 fragCoord = floor(gl_FragCoord.xy * invPixelSize);\n  vec2 res = uResolution * invPixelSize;\n  float invResX = 1.0 / res.x;\n\n  vec3 ray = normalize(vec3((fragCoord - res * 0.5) * invResX, 1.0));\n  ray = ray.x * camI + ray.y * camJ + ray.z * camK;\n\n  // Precompute time-based values\n  float timeSpeed = uTime * uSpeed;\n  float windX = cos(uDirection) * 0.4;\n  float windY = sin(uDirection) * 0.4;\n  vec3 camPos = (windX * camI + windY * camJ + 0.1 * camK) * timeSpeed;\n  vec3 pos = camPos;\n\n  // Precompute ray reciprocal for strides\n  vec3 absRay = max(abs(ray), vec3(0.001));\n  vec3 strides = 1.0 / absRay;\n  vec3 raySign = step(ray, vec3(0.0));\n  vec3 phase = fract(pos) * strides;\n  phase = mix(strides - phase, phase, raySign);\n\n  // Precompute for intersection test\n  float rayDotCamK = dot(ray, camK);\n  float invRayDotCamK = 1.0 / rayDotCamK;\n  float invDepthFade = 1.0 / uDepthFade;\n  float halfInvResX = 0.5 * invResX;\n  vec3 timeAnim = timeSpeed * 0.1 * vec3(7.0, 8.0, 5.0);\n\n  float t = 0.0;\n  for (int i = 0; i < 128; i++) {\n    if (t >= uFarPlane) break;\n    \n    vec3 fpos = floor(pos);\n    uint cellCoord = coord3(fpos);\n    float cellHash = hash3(cellCoord).x;\n\n    if (cellHash < uDensity) {\n      vec3 h = hash3(cellCoord);\n      \n      // Optimized flake position calculation\n      vec3 sinArg1 = fpos.yzx * 0.073;\n      vec3 sinArg2 = fpos.zxy * 0.27;\n      vec3 flakePos = 0.5 - 0.5 * cos(4.0 * sin(sinArg1) + 4.0 * sin(sinArg2) + 2.0 * h + timeAnim);\n      flakePos = flakePos * 0.8 + 0.1 + fpos;\n\n      float toIntersection = dot(flakePos - pos, camK) * invRayDotCamK;\n      \n      if (toIntersection > 0.0) {\n        vec3 testPos = pos + ray * toIntersection - flakePos;\n        float testX = dot(testPos, camI);\n        float testY = dot(testPos, camJ);\n        vec2 testUV = abs(vec2(testX, testY));\n        \n        float depth = dot(flakePos - camPos, camK);\n        float flakeSize = max(uFlakeSize, uMinFlakeSize * depth * halfInvResX);\n        \n        // Avoid branching with step functions where possible\n        float dist;\n        if (uVariant < 0.5) {\n          dist = max(testUV.x, testUV.y);\n        } else if (uVariant < 1.5) {\n          dist = length(testUV);\n        } else {\n          float invFlakeSize = 1.0 / flakeSize;\n          dist = snowflakeDist(vec2(testX, testY) * invFlakeSize) * flakeSize;\n        }\n\n        if (dist < flakeSize) {\n          float flakeSizeRatio = uFlakeSize / flakeSize;\n          float intensity = exp2(-(t + toIntersection) * invDepthFade) *\n                           min(1.0, flakeSizeRatio * flakeSizeRatio) * uBrightness;\n          fragColor = vec4(uColor * pow(vec3(intensity), vec3(uGamma)), 1.0);\n          return;\n        }\n      }\n    }\n\n    float nextStep = min(min(phase.x, phase.y), phase.z);\n    vec3 sel = step(phase, vec3(nextStep));\n    phase = phase - nextStep + strides * sel;\n    t += nextStep;\n    pos = mix(pos + ray * nextStep, floor(pos + ray * nextStep + 0.5), sel);\n  }\n\n  fragColor = vec4(0.0);\n}\n';
  function init(){ var els=document.querySelectorAll('.pixel-snow'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    var h=g.ShaderBG(els[i], FRAG, {"uniforms":{"uFlakeSize":{"t":"1f","v":0.01},"uMinFlakeSize":{"t":"1f","v":1.25},"uPixelResolution":{"t":"1f","v":200},"uSpeed":{"t":"1f","v":1.25},"uDepthFade":{"t":"1f","v":8},"uFarPlane":{"t":"1f","v":20},"uColor":{"t":"3f","v":[1,1,1]},"uBrightness":{"t":"1f","v":1},"uGamma":{"t":"1f","v":0.4545},"uDensity":{"t":"1f","v":0.3},"uVariant":{"t":"1f","v":0},"uDirection":{"t":"1f","v":2.1816615649929116}}}); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
