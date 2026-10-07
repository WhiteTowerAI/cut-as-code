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
/* gradient-blinds.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\n#ifdef GL_ES\nprecision mediump float;\n#endif\n\nuniform vec3  iResolution;\nuniform vec2  iMouse;\nuniform float iTime;\n\nuniform float uAngle;\nuniform float uNoise;\nuniform float uBlindCount;\nuniform float uSpotlightRadius;\nuniform float uSpotlightSoftness;\nuniform float uSpotlightOpacity;\nuniform float uMirror;\nuniform float uDistort;\nuniform float uShineFlip;\nuniform vec3  uColor0;\nuniform vec3  uColor1;\nuniform vec3  uColor2;\nuniform vec3  uColor3;\nuniform vec3  uColor4;\nuniform vec3  uColor5;\nuniform vec3  uColor6;\nuniform vec3  uColor7;\nuniform int   uColorCount;\n\nvarying vec2 vUv;\n\nfloat rand(vec2 co){\n  return fract(sin(dot(co, vec2(12.9898,78.233))) * 43758.5453);\n}\n\nvec2 rotate2D(vec2 p, float a){\n  float c = cos(a);\n  float s = sin(a);\n  return mat2(c, -s, s, c) * p;\n}\n\nvec3 getGradientColor(float t){\n  float tt = clamp(t, 0.0, 1.0);\n  int count = uColorCount;\n  if (count < 2) count = 2;\n  float scaled = tt * float(count - 1);\n  float seg = floor(scaled);\n  float f = fract(scaled);\n\n  if (seg < 1.0) return mix(uColor0, uColor1, f);\n  if (seg < 2.0 && count > 2) return mix(uColor1, uColor2, f);\n  if (seg < 3.0 && count > 3) return mix(uColor2, uColor3, f);\n  if (seg < 4.0 && count > 4) return mix(uColor3, uColor4, f);\n  if (seg < 5.0 && count > 5) return mix(uColor4, uColor5, f);\n  if (seg < 6.0 && count > 6) return mix(uColor5, uColor6, f);\n  if (seg < 7.0 && count > 7) return mix(uColor6, uColor7, f);\n  if (count > 7) return uColor7;\n  if (count > 6) return uColor6;\n  if (count > 5) return uColor5;\n  if (count > 4) return uColor4;\n  if (count > 3) return uColor3;\n  if (count > 2) return uColor2;\n  return uColor1;\n}\n\nvoid mainImage( out vec4 fragColor, in vec2 fragCoord )\n{\n    vec2 uv0 = fragCoord.xy / iResolution.xy;\n\n    float aspect = iResolution.x / iResolution.y;\n    vec2 p = uv0 * 2.0 - 1.0;\n    p.x *= aspect;\n    vec2 pr = rotate2D(p, uAngle);\n    pr.x /= aspect;\n    vec2 uv = pr * 0.5 + 0.5;\n\n    vec2 uvMod = uv;\n    if (uDistort > 0.0) {\n      float a = uvMod.y * 6.0;\n      float b = uvMod.x * 6.0;\n      float w = 0.01 * uDistort;\n      uvMod.x += sin(a) * w;\n      uvMod.y += cos(b) * w;\n    }\n    float t = uvMod.x;\n    if (uMirror > 0.5) {\n      t = 1.0 - abs(1.0 - 2.0 * fract(t));\n    }\n    vec3 base = getGradientColor(t);\n\n    vec2 offset = vec2(iMouse.x/iResolution.x, iMouse.y/iResolution.y);\n  float d = length(uv0 - offset);\n  float r = max(uSpotlightRadius, 1e-4);\n  float dn = d / r;\n  float spot = (1.0 - 2.0 * pow(dn, uSpotlightSoftness)) * uSpotlightOpacity;\n  vec3 cir = vec3(spot);\n  float stripe = fract(uvMod.x * max(uBlindCount, 1.0));\n  if (uShineFlip > 0.5) stripe = 1.0 - stripe;\n    vec3 ran = vec3(stripe);\n\n    vec3 col = cir + base - ran;\n    col += (rand(gl_FragCoord.xy + iTime) - 0.5) * uNoise;\n\n    fragColor = vec4(col, 1.0);\n}\n\nvoid main() {\n    vec4 color;\n    mainImage(color, vUv * iResolution.xy);\n    gl_FragColor = color;\n}\n';
  function init(){ var els=document.querySelectorAll('.gradient-blinds'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"iMouse":{"t":"2f","v":[0,0]},"uAngle":{"t":"1f","v":0},"uNoise":{"t":"1f","v":0.3},"uBlindCount":{"t":"1f","v":16},"uSpotlightRadius":{"t":"1f","v":0.5},"uSpotlightSoftness":{"t":"1f","v":1},"uSpotlightOpacity":{"t":"1f","v":1},"uMirror":{"t":"1f","v":0},"uDistort":{"t":"1f","v":0},"uShineFlip":{"t":"1f","v":0},"uColor0":{"t":"3f","v":[1,0.6235294117647059,0.9882352941176471]},"uColor1":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor2":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor3":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor4":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor5":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor6":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColor7":{"t":"3f","v":[0.3215686274509804,0.15294117647058825,1]},"uColorCount":{"t":"1i","v":2}} });  } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
