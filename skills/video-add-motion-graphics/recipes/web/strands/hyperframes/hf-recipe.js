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
/* strands.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='#version 300 es\nprecision highp float;\n\nuniform float uTime;\nuniform vec2 uResolution;\nuniform vec3 uColors[8];\nuniform int uColorCount;\nuniform int uStrandCount;\nuniform float uSpeed;\nuniform float uAmplitude;\nuniform float uWaviness;\nuniform float uThickness;\nuniform float uGlow;\nuniform float uTaper;\nuniform float uSpread;\nuniform float uHueShift;\nuniform float uIntensity;\nuniform float uOpacity;\nuniform float uScale;\nuniform float uSaturation;\n\nout vec4 fragColor;\n\nconst float PI = 3.14159265;\n\nvec3 spectrum(float t) {\n  return 0.5 + 0.5 * cos(2.0 * PI * (t + vec3(0.00, 0.33, 0.67)));\n}\n\nvec3 samplePalette(float t) {\n  t = fract(t);\n  float scaled = t * float(uColorCount);\n  int idx = int(floor(scaled));\n  float blend = fract(scaled);\n  int nextIdx = idx + 1;\n  if (nextIdx >= uColorCount) nextIdx = 0;\n  return mix(uColors[idx], uColors[nextIdx], blend);\n}\n\nvec3 strandColor(float t) {\n  if (uColorCount > 0) return samplePalette(t);\n  return spectrum(t);\n}\n\nvoid main() {\n  vec2 uv = (gl_FragCoord.xy - 0.5 * uResolution) / uResolution.y;\n  uv /= max(uScale, 0.0001);\n\n  float e = 0.06 + uIntensity * 0.94;\n  float env = pow(max(cos(uv.x * PI * 1.3), 0.0), uTaper);\n\n  vec3 col = vec3(0.0);\n\n  for (int i = 0; i < 12; i++) {\n    if (i >= uStrandCount) break;\n\n    float fi = float(i);\n    float ph = fi * 1.7 * uSpread;\n    float freq = (2.0 + fi * 0.35) * uWaviness;\n    float spd = 1.4 + fi * 1.2;\n\n    float tt = uTime * uSpeed;\n    float w = sin(uv.x * freq + tt * spd + ph) * 0.60\n            + sin(uv.x * freq * 1.1 - tt * spd * 0.7 + ph * 1.7) * 0.40;\n\n    float amp = (0.1 + 0.02 * e) * env * uAmplitude;\n    float y = w * amp;\n\n    float d = abs(uv.y - y);\n    float thick = (0.001 + 0.05 * e) * (0.35 + env) * uThickness;\n    float g = thick / (d + thick * 0.45);\n    g = g * g;\n\n    float h = fi / float(uStrandCount) + uv.x * 0.30 + uTime * 0.04 + uHueShift;\n    col += strandColor(h) * g * env;\n  }\n\n  col *= 0.45 + 0.7 * e;\n  col = 1.0 - exp(-col * uGlow);\n\n  float gray = dot(col, vec3(0.2126, 0.7152, 0.0722));\n  col = max(mix(vec3(gray), col, uSaturation), 0.0);\n\n  float lum = max(max(col.r, col.g), col.b);\n  float alpha = clamp(lum, 0.0, 1.0) * uOpacity;\n\n  fragColor = vec4(col * uOpacity, alpha);\n}\n';
  function init(){ var els=document.querySelectorAll('.strands'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uColors":{"t":"3fv","v":[1,0.25882352941176473,0.25882352941176473,0.48627450980392156,0.22745098039215686,0.9294117647058824,0.023529411764705882,0.7137254901960784,0.8313725490196079,0.9176470588235294,0.7019607843137254,0.03137254901960784,0.9176470588235294,0.7019607843137254,0.03137254901960784,0.9176470588235294,0.7019607843137254,0.03137254901960784,0.9176470588235294,0.7019607843137254,0.03137254901960784,0.9176470588235294,0.7019607843137254,0.03137254901960784]},"uColorCount":{"t":"1i","v":4},"uStrandCount":{"t":"1i","v":3},"uSpeed":{"t":"1f","v":0.5},"uAmplitude":{"t":"1f","v":1},"uWaviness":{"t":"1f","v":1},"uThickness":{"t":"1f","v":0.7},"uGlow":{"t":"1f","v":2.6},"uTaper":{"t":"1f","v":3},"uSpread":{"t":"1f","v":1},"uHueShift":{"t":"1f","v":0},"uIntensity":{"t":"1f","v":0.6},"uOpacity":{"t":"1f","v":1},"uScale":{"t":"1f","v":1.5},"uSaturation":{"t":"1f","v":1.5}} });  } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
