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
/* light-rays.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='precision highp float;\n\nuniform float iTime;\nuniform vec2  iResolution;\n\nuniform vec3  raysColor;\nuniform float raysSpeed;\nuniform float lightSpread;\nuniform float rayLength;\nuniform float pulsating;\nuniform float fadeDistance;\nuniform float saturation;\nuniform vec2  mousePos;\nuniform float mouseInfluence;\nuniform float noiseAmount;\nuniform float distortion;\n\nvarying vec2 vUv;\n\nfloat noise(vec2 st) {\n  return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);\n}\n\nfloat rayStrength(vec2 raySource, vec2 rayRefDirection, vec2 coord,\n                  float seedA, float seedB, float speed) {\n  vec2 sourceToCoord = coord - raySource;\n  vec2 dirNorm = normalize(sourceToCoord);\n  float cosAngle = dot(dirNorm, rayRefDirection);\n\n  float distortedAngle = cosAngle + distortion * sin(iTime * 2.0 + length(sourceToCoord) * 0.01) * 0.2;\n  \n  float spreadFactor = pow(max(distortedAngle, 0.0), 1.0 / max(lightSpread, 0.001));\n\n  float distance = length(sourceToCoord);\n  float maxDistance = iResolution.x * rayLength;\n  float lengthFalloff = clamp((maxDistance - distance) / maxDistance, 0.0, 1.0);\n  \n  float fadeFalloff = clamp((iResolution.x * fadeDistance - distance) / (iResolution.x * fadeDistance), 0.5, 1.0);\n  float pulse = pulsating > 0.5 ? (0.8 + 0.2 * sin(iTime * speed * 3.0)) : 1.0;\n\n  float baseStrength = clamp(\n    (0.45 + 0.15 * sin(distortedAngle * seedA + iTime * speed)) +\n    (0.3 + 0.2 * cos(-distortedAngle * seedB + iTime * speed)),\n    0.0, 1.0\n  );\n\n  return baseStrength * lengthFalloff * fadeFalloff * spreadFactor * pulse;\n}\n\nvoid mainImage(out vec4 fragColor, in vec2 fragCoord) {\n  vec2 coord = vec2(fragCoord.x, iResolution.y - fragCoord.y);\n  vec2 rayPos = vec2(iResolution.x * 0.5, -0.2 * iResolution.y);\n  vec2 rayDir = vec2(0.0, 1.0);\n  \n  vec2 finalRayDir = rayDir;\n  if (mouseInfluence > 0.0) {\n    vec2 mouseScreenPos = mousePos * iResolution.xy;\n    vec2 mouseDirection = normalize(mouseScreenPos - rayPos);\n    finalRayDir = normalize(mix(rayDir, mouseDirection, mouseInfluence));\n  }\n\n  vec4 rays1 = vec4(1.0) *\n               rayStrength(rayPos, finalRayDir, coord, 36.2214, 21.11349,\n                           1.5 * raysSpeed);\n  vec4 rays2 = vec4(1.0) *\n               rayStrength(rayPos, finalRayDir, coord, 22.3991, 18.0234,\n                           1.1 * raysSpeed);\n\n  fragColor = rays1 * 0.5 + rays2 * 0.4;\n\n  if (noiseAmount > 0.0) {\n    float n = noise(coord * 0.01 + iTime * 0.1);\n    fragColor.rgb *= (1.0 - noiseAmount + noiseAmount * n);\n  }\n\n  float brightness = 1.0 - (coord.y / iResolution.y);\n  fragColor.x *= 0.1 + brightness * 0.8;\n  fragColor.y *= 0.3 + brightness * 0.6;\n  fragColor.z *= 0.5 + brightness * 0.5;\n\n  if (saturation != 1.0) {\n    float gray = dot(fragColor.rgb, vec3(0.299, 0.587, 0.114));\n    fragColor.rgb = mix(vec3(gray), fragColor.rgb, saturation);\n  }\n\n  fragColor.rgb *= raysColor;\n}\n\nvoid main() {\n  vec4 color;\n  mainImage(color, gl_FragCoord.xy);\n  gl_FragColor  = color;\n}';
  function init(){ var els=document.querySelectorAll('.light-rays'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"raysColor":{"t":"3f","v":[1,1,1]},"raysSpeed":{"t":"1f","v":1},"lightSpread":{"t":"1f","v":1},"rayLength":{"t":"1f","v":2},"pulsating":{"t":"1f","v":0},"fadeDistance":{"t":"1f","v":1},"saturation":{"t":"1f","v":1},"mousePos":{"t":"2f","v":[0.5,0.5]},"mouseInfluence":{"t":"1f","v":0},"noiseAmount":{"t":"1f","v":0},"distortion":{"t":"1f","v":0}} });  } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
