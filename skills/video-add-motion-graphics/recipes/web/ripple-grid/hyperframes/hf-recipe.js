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
/* ripple-grid.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='precision highp float;\nuniform float iTime;\nuniform vec2 iResolution;\nuniform bool enableRainbow;\nuniform vec3 gridColor;\nuniform float rippleIntensity;\nuniform float gridSize;\nuniform float gridThickness;\nuniform float fadeDistance;\nuniform float vignetteStrength;\nuniform float glowIntensity;\nuniform float opacity;\nuniform float gridRotation;\nuniform bool mouseInteraction;\nuniform vec2 mousePosition;\nuniform float mouseInfluence;\nuniform float mouseInteractionRadius;\nvarying vec2 vUv;\n\nfloat pi = 3.141592;\n\nmat2 rotate(float angle) {\n    float s = sin(angle);\n    float c = cos(angle);\n    return mat2(c, -s, s, c);\n}\n\nvoid main() {\n    vec2 uv = vUv * 2.0 - 1.0;\n    uv.x *= iResolution.x / iResolution.y;\n\n    if (gridRotation != 0.0) {\n        uv = rotate(gridRotation * pi / 180.0) * uv;\n    }\n\n    float dist = length(uv);\n    float func = sin(pi * (iTime - dist));\n    vec2 rippleUv = uv + uv * func * rippleIntensity;\n\n    if (mouseInteraction && mouseInfluence > 0.0) {\n        vec2 mouseUv = (mousePosition * 2.0 - 1.0);\n        mouseUv.x *= iResolution.x / iResolution.y;\n        float mouseDist = length(uv - mouseUv);\n        \n        float influence = mouseInfluence * exp(-mouseDist * mouseDist / (mouseInteractionRadius * mouseInteractionRadius));\n        \n        float mouseWave = sin(pi * (iTime * 2.0 - mouseDist * 3.0)) * influence;\n        rippleUv += normalize(uv - mouseUv) * mouseWave * rippleIntensity * 0.3;\n    }\n\n    vec2 a = sin(gridSize * 0.5 * pi * rippleUv - pi / 2.0);\n    vec2 b = abs(a);\n\n    float aaWidth = 0.5;\n    vec2 smoothB = vec2(\n        smoothstep(0.0, aaWidth, b.x),\n        smoothstep(0.0, aaWidth, b.y)\n    );\n\n    vec3 color = vec3(0.0);\n    color += exp(-gridThickness * smoothB.x * (0.8 + 0.5 * sin(pi * iTime)));\n    color += exp(-gridThickness * smoothB.y);\n    color += 0.5 * exp(-(gridThickness / 4.0) * sin(smoothB.x));\n    color += 0.5 * exp(-(gridThickness / 3.0) * smoothB.y);\n\n    if (glowIntensity > 0.0) {\n        color += glowIntensity * exp(-gridThickness * 0.5 * smoothB.x);\n        color += glowIntensity * exp(-gridThickness * 0.5 * smoothB.y);\n    }\n\n    float ddd = exp(-2.0 * clamp(pow(dist, fadeDistance), 0.0, 1.0));\n    \n    vec2 vignetteCoords = vUv - 0.5;\n    float vignetteDistance = length(vignetteCoords);\n    float vignette = 1.0 - pow(vignetteDistance * 2.0, vignetteStrength);\n    vignette = clamp(vignette, 0.0, 1.0);\n    \n    vec3 t;\n    if (enableRainbow) {\n        t = vec3(\n            uv.x * 0.5 + 0.5 * sin(iTime),\n            uv.y * 0.5 + 0.5 * cos(iTime),\n            pow(cos(iTime), 4.0)\n        ) + 0.5;\n    } else {\n        t = gridColor;\n    }\n\n    float finalFade = ddd * vignette;\n    float alpha = length(color) * finalFade * opacity;\n    gl_FragColor = vec4(color * t * finalFade * opacity, alpha);\n}';
  function init(){ var els=document.querySelectorAll('.ripple-grid'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"gridColor":{"t":"3f","v":[0.55,0.5,1]},"rippleIntensity":{"t":"1f","v":1},"gridSize":{"t":"1f","v":1},"gridThickness":{"t":"1f","v":1},"fadeDistance":{"t":"1f","v":0.5},"vignetteStrength":{"t":"1f","v":1},"glowIntensity":{"t":"1f","v":1},"opacity":{"t":"1f","v":1},"gridRotation":{"t":"1f","v":1},"mousePosition":{"t":"2f","v":[0.5,0.5]},"mouseInfluence":{"t":"1f","v":1},"mouseInteractionRadius":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
