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
/* threads.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\nprecision highp float;\n\nuniform float iTime;\nuniform vec3 iResolution;\nuniform vec3 uColor;\nuniform float uAmplitude;\nuniform float uDistance;\nuniform vec2 uMouse;\n\n#define PI 3.1415926538\n\nconst int u_line_count = 40;\nconst float u_line_width = 7.0;\nconst float u_line_blur = 10.0;\n\nfloat Perlin2D(vec2 P) {\n    vec2 Pi = floor(P);\n    vec4 Pf_Pfmin1 = P.xyxy - vec4(Pi, Pi + 1.0);\n    vec4 Pt = vec4(Pi.xy, Pi.xy + 1.0);\n    Pt = Pt - floor(Pt * (1.0 / 71.0)) * 71.0;\n    Pt += vec2(26.0, 161.0).xyxy;\n    Pt *= Pt;\n    Pt = Pt.xzxz * Pt.yyww;\n    vec4 hash_x = fract(Pt * (1.0 / 951.135664));\n    vec4 hash_y = fract(Pt * (1.0 / 642.949883));\n    vec4 grad_x = hash_x - 0.49999;\n    vec4 grad_y = hash_y - 0.49999;\n    vec4 grad_results = inversesqrt(grad_x * grad_x + grad_y * grad_y)\n        * (grad_x * Pf_Pfmin1.xzxz + grad_y * Pf_Pfmin1.yyww);\n    grad_results *= 1.4142135623730950;\n    vec2 blend = Pf_Pfmin1.xy * Pf_Pfmin1.xy * Pf_Pfmin1.xy\n               * (Pf_Pfmin1.xy * (Pf_Pfmin1.xy * 6.0 - 15.0) + 10.0);\n    vec4 blend2 = vec4(blend, vec2(1.0 - blend));\n    return dot(grad_results, blend2.zxzx * blend2.wwyy);\n}\n\nfloat pixel(float count, vec2 resolution) {\n    return (1.0 / max(resolution.x, resolution.y)) * count;\n}\n\nfloat lineFn(vec2 st, float width, float perc, float offset, vec2 mouse, float time, float amplitude, float distance) {\n    float split_offset = (perc * 0.4);\n    float split_point = 0.1 + split_offset;\n\n    float amplitude_normal = smoothstep(split_point, 0.7, st.x);\n    float amplitude_strength = 0.5;\n    float finalAmplitude = amplitude_normal * amplitude_strength\n                           * amplitude * (1.0 + (mouse.y - 0.5) * 0.2);\n\n    float time_scaled = time / 10.0 + (mouse.x - 0.5) * 1.0;\n    float blur = smoothstep(split_point, split_point + 0.05, st.x) * perc;\n\n    float xnoise = mix(\n        Perlin2D(vec2(time_scaled, st.x + perc) * 2.5),\n        Perlin2D(vec2(time_scaled, st.x + time_scaled) * 3.5) / 1.5,\n        st.x * 0.3\n    );\n\n    float y = 0.5 + (perc - 0.5) * distance + xnoise / 2.0 * finalAmplitude;\n\n    float line_start = smoothstep(\n        y + (width / 2.0) + (u_line_blur * pixel(1.0, iResolution.xy) * blur),\n        y,\n        st.y\n    );\n\n    float line_end = smoothstep(\n        y,\n        y - (width / 2.0) - (u_line_blur * pixel(1.0, iResolution.xy) * blur),\n        st.y\n    );\n\n    return clamp(\n        (line_start - line_end) * (1.0 - smoothstep(0.0, 1.0, pow(perc, 0.3))),\n        0.0,\n        1.0\n    );\n}\n\nvoid mainImage(out vec4 fragColor, in vec2 fragCoord) {\n    vec2 uv = fragCoord / iResolution.xy;\n\n    float line_strength = 1.0;\n    for (int i = 0; i < u_line_count; i++) {\n        float p = float(i) / float(u_line_count);\n        line_strength *= (1.0 - lineFn(\n            uv,\n            u_line_width * pixel(1.0, iResolution.xy) * (1.0 - p),\n            p,\n            (PI * 1.0) * p,\n            uMouse,\n            iTime,\n            uAmplitude,\n            uDistance\n        ));\n    }\n\n    float colorVal = 1.0 - line_strength;\n    fragColor = vec4(uColor * colorVal, colorVal);\n}\n\nvoid main() {\n    mainImage(gl_FragColor, gl_FragCoord.xy);\n}\n';
  function init(){ var els=document.querySelectorAll('.threads'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uColor":{"t":"3f","v":[0.55,0.5,1]},"uAmplitude":{"t":"1f","v":0.3},"uDistance":{"t":"1f","v":0.5}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
