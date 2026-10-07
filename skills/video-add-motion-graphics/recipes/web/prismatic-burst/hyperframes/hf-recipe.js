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
/* prismatic-burst.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='#version 300 es\nprecision highp float;\nprecision highp int;\n\nout vec4 fragColor;\n\nuniform vec2  uResolution;\nuniform float uTime;\n\nuniform float uIntensity;\nuniform float uSpeed;\nuniform int   uAnimType;\nuniform vec2  uMouse;\nuniform int   uColorCount;\nuniform float uDistort;\nuniform vec2  uOffset;\nuniform sampler2D uGradient;\nuniform float uNoiseAmount;\nuniform int   uRayCount;\n\nfloat hash21(vec2 p){\n    p = floor(p);\n    float f = 52.9829189 * fract(dot(p, vec2(0.065, 0.005)));\n    return fract(f);\n}\n\nmat2 rot30(){ return mat2(0.8, -0.5, 0.5, 0.8); }\n\nfloat layeredNoise(vec2 fragPx){\n    vec2 p = mod(fragPx + vec2(uTime * 30.0, -uTime * 21.0), 1024.0);\n    vec2 q = rot30() * p;\n    float n = 0.0;\n    n += 0.40 * hash21(q);\n    n += 0.25 * hash21(q * 2.0 + 17.0);\n    n += 0.20 * hash21(q * 4.0 + 47.0);\n    n += 0.10 * hash21(q * 8.0 + 113.0);\n    n += 0.05 * hash21(q * 16.0 + 191.0);\n    return n;\n}\n\nvec3 rayDir(vec2 frag, vec2 res, vec2 offset, float dist){\n    float focal = res.y * max(dist, 1e-3);\n    return normalize(vec3(2.0 * (frag - offset) - res, focal));\n}\n\nfloat edgeFade(vec2 frag, vec2 res, vec2 offset){\n    vec2 toC = frag - 0.5 * res - offset;\n    float r = length(toC) / (0.5 * min(res.x, res.y));\n    float x = clamp(r, 0.0, 1.0);\n    float q = x * x * x * (x * (x * 6.0 - 15.0) + 10.0);\n    float s = q * 0.5;\n    s = pow(s, 1.5);\n    float tail = 1.0 - pow(1.0 - s, 2.0);\n    s = mix(s, tail, 0.2);\n    float dn = (layeredNoise(frag * 0.15) - 0.5) * 0.0015 * s;\n    return clamp(s + dn, 0.0, 1.0);\n}\n\nmat3 rotX(float a){ float c = cos(a), s = sin(a); return mat3(1.0,0.0,0.0, 0.0,c,-s, 0.0,s,c); }\nmat3 rotY(float a){ float c = cos(a), s = sin(a); return mat3(c,0.0,s, 0.0,1.0,0.0, -s,0.0,c); }\nmat3 rotZ(float a){ float c = cos(a), s = sin(a); return mat3(c,-s,0.0, s,c,0.0, 0.0,0.0,1.0); }\n\nvec3 sampleGradient(float t){\n    t = clamp(t, 0.0, 1.0);\n    return 0.5 + 0.5 * cos(6.28318 * (t + vec3(0.0, 0.33, 0.67)));\n}\n\nvec2 rot2(vec2 v, float a){\n    float s = sin(a), c = cos(a);\n    return mat2(c, -s, s, c) * v;\n}\n\nfloat bendAngle(vec3 q, float t){\n    float a = 0.8 * sin(q.x * 0.55 + t * 0.6)\n            + 0.7 * sin(q.y * 0.50 - t * 0.5)\n            + 0.6 * sin(q.z * 0.60 + t * 0.7);\n    return a;\n}\n\nvoid main(){\n    vec2 frag = gl_FragCoord.xy;\n    float t = uTime * uSpeed;\n    float jitterAmp = 0.1 * clamp(uNoiseAmount, 0.0, 1.0);\n    vec3 dir = rayDir(frag, uResolution, uOffset, 1.0);\n    float marchT = 0.0;\n    vec3 col = vec3(0.0);\n    float n = layeredNoise(frag);\n    vec4 c = cos(t * 0.2 + vec4(0.0, 33.0, 11.0, 0.0));\n    mat2 M2 = mat2(c.x, c.y, c.z, c.w);\n    float amp = clamp(uDistort, 0.0, 50.0) * 0.15;\n\n    mat3 rot3dMat = mat3(1.0);\n    if(uAnimType == 1){\n      vec3 ang = vec3(t * 0.31, t * 0.21, t * 0.17);\n      rot3dMat = rotZ(ang.z) * rotY(ang.y) * rotX(ang.x);\n    }\n    mat3 hoverMat = mat3(1.0);\n    if(uAnimType == 2){\n      vec2 m = uMouse * 2.0 - 1.0;\n      vec3 ang = vec3(m.y * 0.6, m.x * 0.6, 0.0);\n      hoverMat = rotY(ang.y) * rotX(ang.x);\n    }\n\n    for (int i = 0; i < 44; ++i) {\n        vec3 P = marchT * dir;\n        P.z -= 2.0;\n        float rad = length(P);\n        vec3 Pl = P * (10.0 / max(rad, 1e-6));\n\n        if(uAnimType == 0){\n            Pl.xz *= M2;\n        } else if(uAnimType == 1){\n      Pl = rot3dMat * Pl;\n        } else {\n      Pl = hoverMat * Pl;\n        }\n\n        float stepLen = min(rad - 0.3, n * jitterAmp) + 0.1;\n\n        float grow = smoothstep(0.35, 3.0, marchT);\n        float a1 = amp * grow * bendAngle(Pl * 0.6, t);\n        float a2 = 0.5 * amp * grow * bendAngle(Pl.zyx * 0.5 + 3.1, t * 0.9);\n        vec3 Pb = Pl;\n        Pb.xz = rot2(Pb.xz, a1);\n        Pb.xy = rot2(Pb.xy, a2);\n\n        float rayPattern = smoothstep(\n            0.5, 0.7,\n            sin(Pb.x + cos(Pb.y) * cos(Pb.z)) *\n            sin(Pb.z + sin(Pb.y) * cos(Pb.x + t))\n        );\n\n        if (uRayCount > 0) {\n            float ang = atan(Pb.y, Pb.x);\n            float comb = 0.5 + 0.5 * cos(float(uRayCount) * ang);\n            comb = pow(comb, 3.0);\n            rayPattern *= smoothstep(0.15, 0.95, comb);\n        }\n\n        vec3 spectralDefault = 1.0 + vec3(\n            cos(marchT * 3.0 + 0.0),\n            cos(marchT * 3.0 + 1.0),\n            cos(marchT * 3.0 + 2.0)\n        );\n\n        float saw = fract(marchT * 0.25);\n        float tRay = saw * saw * (3.0 - 2.0 * saw);\n        vec3 userGradient = 2.0 * sampleGradient(tRay);\n        vec3 spectral = (uColorCount > 0) ? userGradient : spectralDefault;\n        vec3 base = (0.05 / (0.4 + stepLen))\n                  * smoothstep(5.0, 0.0, rad)\n                  * spectral;\n\n        col += base * rayPattern;\n        marchT += stepLen;\n    }\n\n    col *= edgeFade(frag, uResolution, uOffset);\n    col *= uIntensity;\n\n    fragColor = vec4(clamp(col, 0.0, 1.0), 1.0);\n}';
  function init(){ var els=document.querySelectorAll('.prismatic-burst'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uIntensity":{"t":"1f","v":1},"uSpeed":{"t":"1f","v":1},"uAnimType":{"t":"1i","v":1},"uColorCount":{"t":"1i","v":1},"uDistort":{"t":"1f","v":0.5},"uOffset":{"t":"2f","v":[0.5,0.5]},"uNoiseAmount":{"t":"1f","v":0.12},"uRayCount":{"t":"1i","v":1}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
