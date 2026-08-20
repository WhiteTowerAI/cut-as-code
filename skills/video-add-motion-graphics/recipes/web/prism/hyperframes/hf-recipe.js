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
/* prism.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\n      precision highp float;\n\n      uniform vec2  iResolution;\n      uniform float iTime;\n\n      uniform float uHeight;\n      uniform float uBaseHalf;\n      uniform mat3  uRot;\n      uniform int   uUseBaseWobble;\n      uniform float uGlow;\n      uniform vec2  uOffsetPx;\n      uniform float uNoise;\n      uniform float uSaturation;\n      uniform float uScale;\n      uniform float uHueShift;\n      uniform float uColorFreq;\n      uniform float uBloom;\n      uniform float uCenterShift;\n      uniform float uInvBaseHalf;\n      uniform float uInvHeight;\n      uniform float uMinAxis;\n      uniform float uPxScale;\n      uniform float uTimeScale;\n\n      vec4 tanh4(vec4 x){\n        vec4 e2x = exp(2.0*x);\n        return (e2x - 1.0) / (e2x + 1.0);\n      }\n\n      float rand(vec2 co){\n        return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453123);\n      }\n\n      float sdOctaAnisoInv(vec3 p){\n        vec3 q = vec3(abs(p.x) * uInvBaseHalf, abs(p.y) * uInvHeight, abs(p.z) * uInvBaseHalf);\n        float m = q.x + q.y + q.z - 1.0;\n        return m * uMinAxis * 0.5773502691896258;\n      }\n\n      float sdPyramidUpInv(vec3 p){\n        float oct = sdOctaAnisoInv(p);\n        float halfSpace = -p.y;\n        return max(oct, halfSpace);\n      }\n\n      mat3 hueRotation(float a){\n        float c = cos(a), s = sin(a);\n        mat3 W = mat3(\n          0.299, 0.587, 0.114,\n          0.299, 0.587, 0.114,\n          0.299, 0.587, 0.114\n        );\n        mat3 U = mat3(\n           0.701, -0.587, -0.114,\n          -0.299,  0.413, -0.114,\n          -0.300, -0.588,  0.886\n        );\n        mat3 V = mat3(\n           0.168, -0.331,  0.500,\n           0.328,  0.035, -0.500,\n          -0.497,  0.296,  0.201\n        );\n        return W + U * c + V * s;\n      }\n\n      void main(){\n        vec2 f = (gl_FragCoord.xy - 0.5 * iResolution.xy - uOffsetPx) * uPxScale;\n\n        float z = 5.0;\n        float d = 0.0;\n\n        vec3 p;\n        vec4 o = vec4(0.0);\n\n        float centerShift = uCenterShift;\n        float cf = uColorFreq;\n\n        mat2 wob = mat2(1.0);\n        if (uUseBaseWobble == 1) {\n          float t = iTime * uTimeScale;\n          float c0 = cos(t + 0.0);\n          float c1 = cos(t + 33.0);\n          float c2 = cos(t + 11.0);\n          wob = mat2(c0, c1, c2, c0);\n        }\n\n        const int STEPS = 100;\n        for (int i = 0; i < STEPS; i++) {\n          p = vec3(f, z);\n          p.xz = p.xz * wob;\n          p = uRot * p;\n          vec3 q = p;\n          q.y += centerShift;\n          d = 0.1 + 0.2 * abs(sdPyramidUpInv(q));\n          z -= d;\n          o += (sin((p.y + z) * cf + vec4(0.0, 1.0, 2.0, 3.0)) + 1.0) / d;\n        }\n\n        o = tanh4(o * o * (uGlow * uBloom) / 1e5);\n\n        vec3 col = o.rgb;\n        float n = rand(gl_FragCoord.xy + vec2(iTime));\n        col += (n - 0.5) * uNoise;\n        col = clamp(col, 0.0, 1.0);\n\n        float L = dot(col, vec3(0.2126, 0.7152, 0.0722));\n        col = clamp(mix(vec3(L), col, uSaturation), 0.0, 1.0);\n\n        if(abs(uHueShift) > 0.0001){\n          col = clamp(hueRotation(uHueShift) * col, 0.0, 1.0);\n        }\n\n        gl_FragColor = vec4(col, o.a);\n      }\n    ';
  function init(){ var els=document.querySelectorAll('.prism'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uHeight":{"t":"1f","v":1},"uBaseHalf":{"t":"1f","v":1},"uUseBaseWobble":{"t":"1i","v":1},"uGlow":{"t":"1f","v":1},"uOffsetPx":{"t":"2f","v":[0.5,0.5]},"uNoise":{"t":"1f","v":0.12},"uSaturation":{"t":"1f","v":1},"uScale":{"t":"1f","v":1},"uHueShift":{"t":"1f","v":0},"uColorFreq":{"t":"1f","v":2},"uBloom":{"t":"1f","v":1},"uCenterShift":{"t":"1f","v":1},"uInvBaseHalf":{"t":"1f","v":1},"uInvHeight":{"t":"1f","v":1},"uMinAxis":{"t":"1f","v":1},"uPxScale":{"t":"1f","v":1},"uTimeScale":{"t":"1f","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
