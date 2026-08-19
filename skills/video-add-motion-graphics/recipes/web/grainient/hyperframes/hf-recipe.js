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
/* grainient.js — motion-anything recipe · ambient · faithful GPU shader (dependency-free WebGL via _fx/shaderbg.js). */
(function(g){ 'use strict';
  var FRAG='#version 300 es\nprecision highp float;\nuniform vec2 iResolution;\nuniform float iTime;\nuniform float uTimeSpeed;\nuniform float uColorBalance;\nuniform float uWarpStrength;\nuniform float uWarpFrequency;\nuniform float uWarpSpeed;\nuniform float uWarpAmplitude;\nuniform float uBlendAngle;\nuniform float uBlendSoftness;\nuniform float uRotationAmount;\nuniform float uNoiseScale;\nuniform float uGrainAmount;\nuniform float uGrainScale;\nuniform float uGrainAnimated;\nuniform float uContrast;\nuniform float uGamma;\nuniform float uSaturation;\nuniform vec2 uCenterOffset;\nuniform float uZoom;\nuniform vec3 uColor1;\nuniform vec3 uColor2;\nuniform vec3 uColor3;\nout vec4 fragColor;\n#define S(a,b,t) smoothstep(a,b,t)\nmat2 Rot(float a){float s=sin(a),c=cos(a);return mat2(c,-s,s,c);} \nvec2 hash(vec2 p){p=vec2(dot(p,vec2(2127.1,81.17)),dot(p,vec2(1269.5,283.37)));return fract(sin(p)*43758.5453);} \nfloat noise(vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*(3.0-2.0*f);float n=mix(mix(dot(-1.0+2.0*hash(i+vec2(0.0,0.0)),f-vec2(0.0,0.0)),dot(-1.0+2.0*hash(i+vec2(1.0,0.0)),f-vec2(1.0,0.0)),u.x),mix(dot(-1.0+2.0*hash(i+vec2(0.0,1.0)),f-vec2(0.0,1.0)),dot(-1.0+2.0*hash(i+vec2(1.0,1.0)),f-vec2(1.0,1.0)),u.x),u.y);return 0.5+0.5*n;}\nvoid mainImage(out vec4 o, vec2 C){\n  float t=iTime*uTimeSpeed;\n  vec2 uv=C/iResolution.xy;\n  float ratio=iResolution.x/iResolution.y;\n  vec2 tuv=uv-0.5+uCenterOffset;\n  tuv/=max(uZoom,0.001);\n\n  float degree=noise(vec2(t*0.1,tuv.x*tuv.y)*uNoiseScale);\n  tuv.y*=1.0/ratio;\n  tuv*=Rot(radians((degree-0.5)*uRotationAmount+180.0));\n  tuv.y*=ratio;\n\n  float frequency=uWarpFrequency;\n  float ws=max(uWarpStrength,0.001);\n  float amplitude=uWarpAmplitude/ws;\n  float warpTime=t*uWarpSpeed;\n  tuv.x+=sin(tuv.y*frequency+warpTime)/amplitude;\n  tuv.y+=sin(tuv.x*(frequency*1.5)+warpTime)/(amplitude*0.5);\n\n  vec3 colLav=uColor1;\n  vec3 colOrg=uColor2;\n  vec3 colDark=uColor3;\n  float b=uColorBalance;\n  float s=max(uBlendSoftness,0.0);\n  mat2 blendRot=Rot(radians(uBlendAngle));\n  float blendX=(tuv*blendRot).x;\n  float edge0=-0.3-b-s;\n  float edge1=0.2-b+s;\n  float v0=0.5-b+s;\n  float v1=-0.3-b-s;\n  vec3 layer1=mix(colDark,colOrg,S(edge0,edge1,blendX));\n  vec3 layer2=mix(colOrg,colLav,S(edge0,edge1,blendX));\n  vec3 col=mix(layer1,layer2,S(v0,v1,tuv.y));\n\n  vec2 grainUv=uv*max(uGrainScale,0.001);\n  if(uGrainAnimated>0.5){grainUv+=vec2(iTime*0.05);} \n  float grain=fract(sin(dot(grainUv,vec2(12.9898,78.233)))*43758.5453);\n  col+=(grain-0.5)*uGrainAmount;\n\n  col=(col-0.5)*uContrast+0.5;\n  float luma=dot(col,vec3(0.2126,0.7152,0.0722));\n  col=mix(vec3(luma),col,uSaturation);\n  col=pow(max(col,0.0),vec3(1.0/max(uGamma,0.001)));\n  col=clamp(col,0.0,1.0);\n\n  o=vec4(col,1.0);\n}\nvoid main(){\n  vec4 o=vec4(0.0);\n  mainImage(o,gl_FragCoord.xy);\n  fragColor=o;\n}\n';
  function init(){ var els=document.querySelectorAll('.grainient'); for(var i=0;i<els.length;i++){ if(els[i].__sbg) continue;
    g.ShaderBG(els[i], FRAG, { uniforms:{"uTimeSpeed":{"t":"1f","v":1},"uColorBalance":{"t":"1f","v":1},"uWarpStrength":{"t":"1f","v":0.3},"uWarpFrequency":{"t":"1f","v":2},"uWarpSpeed":{"t":"1f","v":1},"uWarpAmplitude":{"t":"1f","v":0.3},"uBlendAngle":{"t":"1f","v":0.5},"uBlendSoftness":{"t":"1f","v":0.5},"uRotationAmount":{"t":"1f","v":1},"uNoiseScale":{"t":"1f","v":1},"uGrainAmount":{"t":"1f","v":1},"uGrainScale":{"t":"1f","v":1},"uGrainAnimated":{"t":"1f","v":1},"uContrast":{"t":"1f","v":1},"uGamma":{"t":"1f","v":1},"uSaturation":{"t":"1f","v":1},"uCenterOffset":{"t":"2f","v":[0.5,0.5]},"uZoom":{"t":"1f","v":1},"uColor1":{"t":"3f","v":[0.55,0.5,1]},"uColor2":{"t":"3f","v":[0.55,0.5,1]},"uColor3":{"t":"3f","v":[0.55,0.5,1]}} }); } }
  if(document.readyState!=='loading') init(); else document.addEventListener('DOMContentLoaded', init);
})(window);

}
];
