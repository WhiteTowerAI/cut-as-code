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
/* faulty-terminal.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision mediump float;\n\nvarying vec2 vUv;\n\nuniform float iTime;\nuniform vec3  iResolution;\nuniform float uScale;\n\nuniform vec2  uGridMul;\nuniform float uDigitSize;\nuniform float uScanlineIntensity;\nuniform float uGlitchAmount;\nuniform float uFlickerAmount;\nuniform float uNoiseAmp;\nuniform float uChromaticAberration;\nuniform float uDither;\nuniform float uCurvature;\nuniform vec3  uTint;\nuniform vec2  uMouse;\nuniform float uMouseStrength;\nuniform float uUseMouse;\nuniform float uPageLoadProgress;\nuniform float uUsePageLoadAnimation;\nuniform float uBrightness;\n\nfloat time;\n\nfloat hash21(vec2 p){\n  p = fract(p * 234.56);\n  p += dot(p, p + 34.56);\n  return fract(p.x * p.y);\n}\n\nfloat noise(vec2 p)\n{\n  return sin(p.x * 10.0) * sin(p.y * (3.0 + sin(time * 0.090909))) + 0.2; \n}\n\nmat2 rotate(float angle)\n{\n  float c = cos(angle);\n  float s = sin(angle);\n  return mat2(c, -s, s, c);\n}\n\nfloat fbm(vec2 p)\n{\n  p *= 1.1;\n  float f = 0.0;\n  float amp = 0.5 * uNoiseAmp;\n  \n  mat2 modify0 = rotate(time * 0.02);\n  f += amp * noise(p);\n  p = modify0 * p * 2.0;\n  amp *= 0.454545;\n  \n  mat2 modify1 = rotate(time * 0.02);\n  f += amp * noise(p);\n  p = modify1 * p * 2.0;\n  amp *= 0.454545;\n  \n  mat2 modify2 = rotate(time * 0.08);\n  f += amp * noise(p);\n  \n  return f;\n}\n\nfloat pattern(vec2 p, out vec2 q, out vec2 r) {\n  vec2 offset1 = vec2(1.0);\n  vec2 offset0 = vec2(0.0);\n  mat2 rot01 = rotate(0.1 * time);\n  mat2 rot1 = rotate(0.1);\n  \n  q = vec2(fbm(p + offset1), fbm(rot01 * p + offset1));\n  r = vec2(fbm(rot1 * q + offset0), fbm(q + offset0));\n  return fbm(p + r);\n}\n\nfloat digit(vec2 p){\n    vec2 grid = uGridMul * 15.0;\n    vec2 s = floor(p * grid) / grid;\n    p = p * grid;\n    vec2 q, r;\n    float intensity = pattern(s * 0.1, q, r) * 1.3 - 0.03;\n    \n    if(uUseMouse > 0.5){\n        vec2 mouseWorld = uMouse * uScale;\n        float distToMouse = distance(s, mouseWorld);\n        float mouseInfluence = exp(-distToMouse * 8.0) * uMouseStrength * 10.0;\n        intensity += mouseInfluence;\n        \n        float ripple = sin(distToMouse * 20.0 - iTime * 5.0) * 0.1 * mouseInfluence;\n        intensity += ripple;\n    }\n    \n    if(uUsePageLoadAnimation > 0.5){\n        float cellRandom = fract(sin(dot(s, vec2(12.9898, 78.233))) * 43758.5453);\n        float cellDelay = cellRandom * 0.8;\n        float cellProgress = clamp((uPageLoadProgress - cellDelay) / 0.2, 0.0, 1.0);\n        \n        float fadeAlpha = smoothstep(0.0, 1.0, cellProgress);\n        intensity *= fadeAlpha;\n    }\n    \n    p = fract(p);\n    p *= uDigitSize;\n    \n    float px5 = p.x * 5.0;\n    float py5 = (1.0 - p.y) * 5.0;\n    float x = fract(px5);\n    float y = fract(py5);\n    \n    float i = floor(py5) - 2.0;\n    float j = floor(px5) - 2.0;\n    float n = i * i + j * j;\n    float f = n * 0.0625;\n    \n    float isOn = step(0.1, intensity - f);\n    float brightness = isOn * (0.2 + y * 0.8) * (0.75 + x * 0.25);\n    \n    return step(0.0, p.x) * step(p.x, 1.0) * step(0.0, p.y) * step(p.y, 1.0) * brightness;\n}\n\nfloat onOff(float a, float b, float c)\n{\n  return step(c, sin(iTime + a * cos(iTime * b))) * uFlickerAmount;\n}\n\nfloat displace(vec2 look)\n{\n    float y = look.y - mod(iTime * 0.25, 1.0);\n    float window = 1.0 / (1.0 + 50.0 * y * y);\n    return sin(look.y * 20.0 + iTime) * 0.0125 * onOff(4.0, 2.0, 0.8) * (1.0 + cos(iTime * 60.0)) * window;\n}\n\nvec3 getColor(vec2 p){\n    \n    float bar = step(mod(p.y + time * 20.0, 1.0), 0.2) * 0.4 + 1.0;\n    bar *= uScanlineIntensity;\n    \n    float displacement = displace(p);\n    p.x += displacement;\n\n    if (uGlitchAmount != 1.0) {\n      float extra = displacement * (uGlitchAmount - 1.0);\n      p.x += extra;\n    }\n\n    float middle = digit(p);\n    \n    const float off = 0.002;\n    float sum = digit(p + vec2(-off, -off)) + digit(p + vec2(0.0, -off)) + digit(p + vec2(off, -off)) +\n                digit(p + vec2(-off, 0.0)) + digit(p + vec2(0.0, 0.0)) + digit(p + vec2(off, 0.0)) +\n                digit(p + vec2(-off, off)) + digit(p + vec2(0.0, off)) + digit(p + vec2(off, off));\n    \n    vec3 baseColor = vec3(0.9) * middle + sum * 0.1 * vec3(1.0) * bar;\n    return baseColor;\n}\n\nvec2 barrel(vec2 uv){\n  vec2 c = uv * 2.0 - 1.0;\n  float r2 = dot(c, c);\n  c *= 1.0 + uCurvature * r2;\n  return c * 0.5 + 0.5;\n}\n\nvoid main() {\n    time = iTime * 0.333333;\n    vec2 uv = vUv;\n\n    if(uCurvature != 0.0){\n      uv = barrel(uv);\n    }\n    \n    vec2 p = uv * uScale;\n    vec3 col = getColor(p);\n\n    if(uChromaticAberration != 0.0){\n      vec2 ca = vec2(uChromaticAberration) / iResolution.xy;\n      col.r = getColor(p + ca).r;\n      col.b = getColor(p - ca).b;\n    }\n\n    col *= uTint;\n    col *= uBrightness;\n\n    if(uDither > 0.0){\n      float rnd = hash21(gl_FragCoord.xy);\n      col += (rnd - 0.5) * (uDither * 0.003922);\n    }\n\n    gl_FragColor = vec4(col, 1.0);\n}\n';
  function init(){ var els=document.querySelectorAll('.faulty-terminal'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uScale":{"t":"1f","v":1},"uGridMul":{"t":"2f","v":[0.5,0.5]},"uDigitSize":{"t":"1f","v":1},"uScanlineIntensity":{"t":"1f","v":0.2},"uGlitchAmount":{"t":"1f","v":1},"uFlickerAmount":{"t":"1f","v":1},"uNoiseAmp":{"t":"1f","v":0.3},"uChromaticAberration":{"t":"1f","v":1},"uDither":{"t":"1f","v":1},"uCurvature":{"t":"1f","v":1},"uTint":{"t":"3f","v":[1,1,1]},"uMouseStrength":{"t":"1f","v":1},"uUseMouse":{"t":"1f","v":1},"uPageLoadProgress":{"t":"1f","v":1},"uUsePageLoadAnimation":{"t":"1f","v":1},"uBrightness":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
