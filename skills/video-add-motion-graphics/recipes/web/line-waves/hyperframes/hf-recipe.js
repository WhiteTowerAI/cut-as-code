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
/* line-waves.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform float uTime;\nuniform vec3 uResolution;\nuniform float uSpeed;\nuniform float uInnerLines;\nuniform float uOuterLines;\nuniform float uWarpIntensity;\nuniform float uRotation;\nuniform float uEdgeFadeWidth;\nuniform float uColorCycleSpeed;\nuniform float uBrightness;\nuniform vec3 uColor1;\nuniform vec3 uColor2;\nuniform vec3 uColor3;\nuniform vec2 uMouse;\nuniform float uMouseInfluence;\nuniform bool uEnableMouse;\n\n#define HALF_PI 1.5707963\n\nfloat hashF(float n) {\n  return fract(sin(n * 127.1) * 43758.5453123);\n}\n\nfloat smoothNoise(float x) {\n  float i = floor(x);\n  float f = fract(x);\n  float u = f * f * (3.0 - 2.0 * f);\n  return mix(hashF(i), hashF(i + 1.0), u);\n}\n\nfloat displaceA(float coord, float t) {\n  float result = sin(coord * 2.123) * 0.2;\n  result += sin(coord * 3.234 + t * 4.345) * 0.1;\n  result += sin(coord * 0.589 + t * 0.934) * 0.5;\n  return result;\n}\n\nfloat displaceB(float coord, float t) {\n  float result = sin(coord * 1.345) * 0.3;\n  result += sin(coord * 2.734 + t * 3.345) * 0.2;\n  result += sin(coord * 0.189 + t * 0.934) * 0.3;\n  return result;\n}\n\nvec2 rotate2D(vec2 p, float angle) {\n  float c = cos(angle);\n  float s = sin(angle);\n  return vec2(p.x * c - p.y * s, p.x * s + p.y * c);\n}\n\nvoid main() {\n  vec2 coords = gl_FragCoord.xy / uResolution.xy;\n  coords = coords * 2.0 - 1.0;\n  coords = rotate2D(coords, uRotation);\n\n  float halfT = uTime * uSpeed * 0.5;\n  float fullT = uTime * uSpeed;\n\n  float mouseWarp = 0.0;\n  if (uEnableMouse) {\n    vec2 mPos = rotate2D(uMouse * 2.0 - 1.0, uRotation);\n    float mDist = length(coords - mPos);\n    mouseWarp = uMouseInfluence * exp(-mDist * mDist * 4.0);\n  }\n\n  float warpAx = coords.x + displaceA(coords.y, halfT) * uWarpIntensity + mouseWarp;\n  float warpAy = coords.y - displaceA(coords.x * cos(fullT) * 1.235, halfT) * uWarpIntensity;\n  float warpBx = coords.x + displaceB(coords.y, halfT) * uWarpIntensity + mouseWarp;\n  float warpBy = coords.y - displaceB(coords.x * sin(fullT) * 1.235, halfT) * uWarpIntensity;\n\n  vec2 fieldA = vec2(warpAx, warpAy);\n  vec2 fieldB = vec2(warpBx, warpBy);\n  vec2 blended = mix(fieldA, fieldB, mix(fieldA, fieldB, 0.5));\n\n  float fadeTop = smoothstep(uEdgeFadeWidth, uEdgeFadeWidth + 0.4, blended.y);\n  float fadeBottom = smoothstep(-uEdgeFadeWidth, -(uEdgeFadeWidth + 0.4), blended.y);\n  float vMask = 1.0 - max(fadeTop, fadeBottom);\n\n  float tileCount = mix(uOuterLines, uInnerLines, vMask);\n  float scaledY = blended.y * tileCount;\n  float nY = smoothNoise(abs(scaledY));\n\n  float ridge = pow(\n    step(abs(nY - blended.x) * 2.0, HALF_PI) * cos(2.0 * (nY - blended.x)),\n    5.0\n  );\n\n  float lines = 0.0;\n  for (float i = 1.0; i < 3.0; i += 1.0) {\n    lines += pow(max(fract(scaledY), fract(-scaledY)), i * 2.0);\n  }\n\n  float pattern = vMask * lines;\n\n  float cycleT = fullT * uColorCycleSpeed;\n  float rChannel = (pattern + lines * ridge) * (cos(blended.y + cycleT * 0.234) * 0.5 + 1.0);\n  float gChannel = (pattern + vMask * ridge) * (sin(blended.x + cycleT * 1.745) * 0.5 + 1.0);\n  float bChannel = (pattern + lines * ridge) * (cos(blended.x + cycleT * 0.534) * 0.5 + 1.0);\n\n  vec3 col = (rChannel * uColor1 + gChannel * uColor2 + bChannel * uColor3) * uBrightness;\n  float alpha = clamp(length(col), 0.0, 1.0);\n\n  gl_FragColor = vec4(col, alpha);\n}\n';
  function init(){ var els=document.querySelectorAll('.line-waves'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uSpeed":{"t":"1f","v":0.3},"uInnerLines":{"t":"1f","v":32},"uOuterLines":{"t":"1f","v":36},"uWarpIntensity":{"t":"1f","v":1},"uRotation":{"t":"1f","v":0},"uEdgeFadeWidth":{"t":"1f","v":0},"uColorCycleSpeed":{"t":"1f","v":1},"uBrightness":{"t":"1f","v":0.2},"uColor1":{"t":"3f","v":[1,1,1]},"uColor2":{"t":"3f","v":[1,1,1]},"uColor3":{"t":"3f","v":[1,1,1]},"uMouseInfluence":{"t":"1f","v":0},"uEnableMouse":{"t":"1i","v":0}} });  } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
