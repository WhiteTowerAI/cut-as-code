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
/* orb.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='\n    precision highp float;\n\n    uniform float iTime;\n    uniform vec3 iResolution;\n    uniform float hue;\n    uniform float hover;\n    uniform float rot;\n    uniform float hoverIntensity;\n    uniform vec3 backgroundColor;\n    varying vec2 vUv;\n\n    vec3 rgb2yiq(vec3 c) {\n      float y = dot(c, vec3(0.299, 0.587, 0.114));\n      float i = dot(c, vec3(0.596, -0.274, -0.322));\n      float q = dot(c, vec3(0.211, -0.523, 0.312));\n      return vec3(y, i, q);\n    }\n    \n    vec3 yiq2rgb(vec3 c) {\n      float r = c.x + 0.956 * c.y + 0.621 * c.z;\n      float g = c.x - 0.272 * c.y - 0.647 * c.z;\n      float b = c.x - 1.106 * c.y + 1.703 * c.z;\n      return vec3(r, g, b);\n    }\n    \n    vec3 adjustHue(vec3 color, float hueDeg) {\n      float hueRad = hueDeg * 3.14159265 / 180.0;\n      vec3 yiq = rgb2yiq(color);\n      float cosA = cos(hueRad);\n      float sinA = sin(hueRad);\n      float i = yiq.y * cosA - yiq.z * sinA;\n      float q = yiq.y * sinA + yiq.z * cosA;\n      yiq.y = i;\n      yiq.z = q;\n      return yiq2rgb(yiq);\n    }\n\n    vec3 hash33(vec3 p3) {\n      p3 = fract(p3 * vec3(0.1031, 0.11369, 0.13787));\n      p3 += dot(p3, p3.yxz + 19.19);\n      return -1.0 + 2.0 * fract(vec3(\n        p3.x + p3.y,\n        p3.x + p3.z,\n        p3.y + p3.z\n      ) * p3.zyx);\n    }\n\n    float snoise3(vec3 p) {\n      const float K1 = 0.333333333;\n      const float K2 = 0.166666667;\n      vec3 i = floor(p + (p.x + p.y + p.z) * K1);\n      vec3 d0 = p - (i - (i.x + i.y + i.z) * K2);\n      vec3 e = step(vec3(0.0), d0 - d0.yzx);\n      vec3 i1 = e * (1.0 - e.zxy);\n      vec3 i2 = 1.0 - e.zxy * (1.0 - e);\n      vec3 d1 = d0 - (i1 - K2);\n      vec3 d2 = d0 - (i2 - K1);\n      vec3 d3 = d0 - 0.5;\n      vec4 h = max(0.6 - vec4(\n        dot(d0, d0),\n        dot(d1, d1),\n        dot(d2, d2),\n        dot(d3, d3)\n      ), 0.0);\n      vec4 n = h * h * h * h * vec4(\n        dot(d0, hash33(i)),\n        dot(d1, hash33(i + i1)),\n        dot(d2, hash33(i + i2)),\n        dot(d3, hash33(i + 1.0))\n      );\n      return dot(vec4(31.316), n);\n    }\n\n    vec4 extractAlpha(vec3 colorIn) {\n      float a = max(max(colorIn.r, colorIn.g), colorIn.b);\n      return vec4(colorIn.rgb / (a + 1e-5), a);\n    }\n\n    const vec3 baseColor1 = vec3(0.611765, 0.262745, 0.996078);\n    const vec3 baseColor2 = vec3(0.298039, 0.760784, 0.913725);\n    const vec3 baseColor3 = vec3(0.062745, 0.078431, 0.600000);\n    const float innerRadius = 0.6;\n    const float noiseScale = 0.65;\n\n    float light1(float intensity, float attenuation, float dist) {\n      return intensity / (1.0 + dist * attenuation);\n    }\n    float light2(float intensity, float attenuation, float dist) {\n      return intensity / (1.0 + dist * dist * attenuation);\n    }\n\n    vec4 draw(vec2 uv) {\n      vec3 color1 = adjustHue(baseColor1, hue);\n      vec3 color2 = adjustHue(baseColor2, hue);\n      vec3 color3 = adjustHue(baseColor3, hue);\n      \n      float ang = atan(uv.y, uv.x);\n      float len = length(uv);\n      float invLen = len > 0.0 ? 1.0 / len : 0.0;\n\n      float bgLuminance = dot(backgroundColor, vec3(0.299, 0.587, 0.114));\n      \n      float n0 = snoise3(vec3(uv * noiseScale, iTime * 0.5)) * 0.5 + 0.5;\n      float r0 = mix(mix(innerRadius, 1.0, 0.4), mix(innerRadius, 1.0, 0.6), n0);\n      float d0 = distance(uv, (r0 * invLen) * uv);\n      float v0 = light1(1.0, 10.0, d0);\n\n      v0 *= smoothstep(r0 * 1.05, r0, len);\n      float innerFade = smoothstep(r0 * 0.8, r0 * 0.95, len);\n      v0 *= mix(innerFade, 1.0, bgLuminance * 0.7);\n      float cl = cos(ang + iTime * 2.0) * 0.5 + 0.5;\n      \n      float a = iTime * -1.0;\n      vec2 pos = vec2(cos(a), sin(a)) * r0;\n      float d = distance(uv, pos);\n      float v1 = light2(1.5, 5.0, d);\n      v1 *= light1(1.0, 50.0, d0);\n      \n      float v2 = smoothstep(1.0, mix(innerRadius, 1.0, n0 * 0.5), len);\n      float v3 = smoothstep(innerRadius, mix(innerRadius, 1.0, 0.5), len);\n      \n      vec3 colBase = mix(color1, color2, cl);\n      float fadeAmount = mix(1.0, 0.1, bgLuminance);\n      \n      vec3 darkCol = mix(color3, colBase, v0);\n      darkCol = (darkCol + v1) * v2 * v3;\n      darkCol = clamp(darkCol, 0.0, 1.0);\n      \n      vec3 lightCol = (colBase + v1) * mix(1.0, v2 * v3, fadeAmount);\n      lightCol = mix(backgroundColor, lightCol, v0);\n      lightCol = clamp(lightCol, 0.0, 1.0);\n      \n      vec3 finalCol = mix(darkCol, lightCol, bgLuminance);\n      \n      return extractAlpha(finalCol);\n    }\n\n    vec4 mainImage(vec2 fragCoord) {\n      vec2 center = iResolution.xy * 0.5;\n      float size = min(iResolution.x, iResolution.y);\n      vec2 uv = (fragCoord - center) / size * 2.0;\n      \n      float angle = rot;\n      float s = sin(angle);\n      float c = cos(angle);\n      uv = vec2(c * uv.x - s * uv.y, s * uv.x + c * uv.y);\n      \n      uv.x += hover * hoverIntensity * 0.1 * sin(uv.y * 10.0 + iTime);\n      uv.y += hover * hoverIntensity * 0.1 * sin(uv.x * 10.0 + iTime);\n      \n      return draw(uv);\n    }\n\n    void main() {\n      vec2 fragCoord = vUv * iResolution.xy;\n      vec4 col = mainImage(fragCoord);\n      gl_FragColor = vec4(col.rgb * col.a, col.a);\n    }\n  ';
  function init(){ var els=document.querySelectorAll('.orb'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"hue":{"t":"1f","v":0},"hover":{"t":"1f","v":1},"rot":{"t":"1f","v":1},"hoverIntensity":{"t":"1f","v":1},"backgroundColor":{"t":"3f","v":[0,0,0]}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
