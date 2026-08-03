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
/* lightfall.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform vec3  iResolution;\nuniform vec2  iMouse;\nuniform float iTime;\n\nuniform vec3  uColor0;\nuniform vec3  uColor1;\nuniform vec3  uColor2;\nuniform vec3  uColor3;\nuniform vec3  uColor4;\nuniform vec3  uColor5;\nuniform vec3  uColor6;\nuniform vec3  uColor7;\nuniform int   uColorCount;\n\nuniform vec3  uBgColor;\nuniform vec3  uMouseColor;\nuniform float uSpeed;\nuniform int   uStreakCount;\nuniform float uStreakWidth;\nuniform float uStreakLength;\nuniform float uGlow;\nuniform float uDensity;\nuniform float uTwinkle;\nuniform float uZoom;\nuniform float uBgGlow;\nuniform float uOpacity;\nuniform float uMouseEnabled;\nuniform float uMouseStrength;\nuniform float uMouseRadius;\n\nvarying vec2 vUv;\n\nvec3 palette(float h) {\n  int count = uColorCount;\n  if (count < 1) count = 1;\n  int idx = int(floor(clamp(h, 0.0, 0.999999) * float(count)));\n  if (idx <= 0) return uColor0;\n  if (idx == 1) return uColor1;\n  if (idx == 2) return uColor2;\n  if (idx == 3) return uColor3;\n  if (idx == 4) return uColor4;\n  if (idx == 5) return uColor5;\n  if (idx == 6) return uColor6;\n  return uColor7;\n}\n\nvec3 tanhv(vec3 x) {\n  vec3 e = exp(-2.0 * x);\n  return (1.0 - e) / (1.0 + e);\n}\n\nvec2 sceneC(vec2 frag, vec2 r) {\n  vec2 P = (frag + frag - r) / r.x;\n  float z = 0.0;\n  float d = 1e3;\n  vec4 O = vec4(0.0);\n  for (int k = 0; k < 39; k++) {\n    if (d <= 1e-4) break;\n    O = z * normalize(vec4(P, uZoom, 0.0)) - vec4(0.0, 4.0, 1.0, 0.0) / 4.5;\n    d = 1.0 - sqrt(length(O * O));\n    z += d;\n  }\n  return vec2(O.x, atan(O.z, O.y));\n}\n\nvoid mainImage(out vec4 o, vec2 C) {\n  vec2 r = iResolution.xy;\n  vec2 uv0 = (C + C - r) / r.x;\n  float T = 0.1 * iTime * uSpeed + 9.0;\n  float angRings = max(1.0, floor(6.28318530718 * max(uDensity, 0.05) + 0.5));\n  vec2 Y = vec2(5e-3, 6.28318530718 / angRings);\n\n  vec2 c0 = sceneC(C, r);\n  vec2 cdx = sceneC(C + vec2(1.0, 0.0), r);\n  vec2 cdy = sceneC(C + vec2(0.0, 1.0), r);\n  vec2 dCx = cdx - c0;\n  vec2 dCy = cdy - c0;\n  dCx.y -= 6.28318530718 * floor(dCx.y / 6.28318530718 + 0.5);\n  dCy.y -= 6.28318530718 * floor(dCy.y / 6.28318530718 + 0.5);\n  vec2 fw = abs(dCx) + abs(dCy);\n  C = c0;\n\n  vec2 P = vec2(2.0, 1.0) * uv0 - (r / r.x) * vec2(0.0, 1.0);\n  vec4 O = vec4(uBgColor * 90.0 * uBgGlow / (1e3 * dot(P, P) + 6.0), 0.0);\n\n  float mGlow = 0.0;\n  if (uMouseEnabled > 0.5) {\n    vec2 mN = (iMouse + iMouse - r) / r.x;\n    float md = length(uv0 - mN);\n    mGlow = exp(-md * md / max(uMouseRadius * uMouseRadius, 1e-4)) * uMouseStrength;\n    O.rgb += uMouseColor * mGlow * 0.25;\n  }\n\n  float zr = 5e-4 * uStreakWidth;\n  vec2 rr = vec2(max(length(fw), 1e-5));\n  float tail = 19.0 / max(uStreakLength, 0.05);\n\n  for (int m = 0; m < 16; m++) {\n    if (m >= uStreakCount) break;\n    float jf = float(m) + 1.0;\n    float ic = fract(sin(dot(vec2(jf, floor(C.x / Y.x + 0.5)), vec2(7.0, 11.0)) * 73.0));\n    vec2 Pp = C - (T + T * ic) * vec2(0.0, 1.0);\n    Pp -= floor(Pp / Y + 0.5) * Y;\n    float h = fract(8663.0 * ic);\n    vec3 col = palette(h);\n    float weight = mix(1.5, 1.0 + sin(T + 7.0 * h + 4.0), uTwinkle);\n    weight *= (1.0 + mGlow * 2.0);\n    vec2 inner = vec2(length(max(Pp, vec2(-1.0, 0.0))), length(Pp) - zr) - zr;\n    vec2 sm = vec2(1.0) - smoothstep(-rr, rr, inner);\n    O.rgb += dot(sm, vec2(exp(tail * Pp.y), 3.0)) * col * weight;\n    C.x += Y.x / 8.0;\n  }\n\n  vec3 colr = sqrt(tanhv(max(O.rgb * uGlow - vec3(0.04, 0.08, 0.02), 0.0)));\n  o = vec4(colr, uOpacity);\n}\n\nvoid main() {\n  vec4 color;\n  mainImage(color, vUv * iResolution.xy);\n  gl_FragColor = color;\n}\n';
  function init(){ var els=document.querySelectorAll('.lightfall'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"iMouse":{"t":"2f","v":[0.5,0.5]},"uColor0":{"t":"3f","v":[0.55,0.5,1]},"uColor1":{"t":"3f","v":[0.55,0.5,1]},"uColor2":{"t":"3f","v":[0.55,0.5,1]},"uColor3":{"t":"3f","v":[0.55,0.5,1]},"uColor4":{"t":"3f","v":[0.55,0.5,1]},"uColor5":{"t":"3f","v":[0.55,0.5,1]},"uColor6":{"t":"3f","v":[0.55,0.5,1]},"uColor7":{"t":"3f","v":[0.55,0.5,1]},"uColorCount":{"t":"1i","v":1},"uBgColor":{"t":"3f","v":[0.55,0.5,1]},"uMouseColor":{"t":"3f","v":[0.55,0.5,1]},"uSpeed":{"t":"1f","v":1},"uStreakCount":{"t":"1i","v":1},"uStreakWidth":{"t":"1f","v":1},"uStreakLength":{"t":"1f","v":1},"uGlow":{"t":"1f","v":1},"uDensity":{"t":"1f","v":1},"uTwinkle":{"t":"1f","v":1},"uZoom":{"t":"1f","v":1},"uBgGlow":{"t":"1f","v":1},"uOpacity":{"t":"1f","v":1},"uMouseEnabled":{"t":"1f","v":1},"uMouseStrength":{"t":"1f","v":1},"uMouseRadius":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
