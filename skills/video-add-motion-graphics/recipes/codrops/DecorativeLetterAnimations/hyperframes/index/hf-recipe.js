/* Generated from the original Codrops entry scripts. */
window.__hfRecipeFactories = [
function (__hf) {

document.documentElement.className="js";var supportsCssVars=function(){var e,t=document.createElement("style");return t.innerHTML="root: { --tmp-var: bold; }",document.head.appendChild(t),e=!!(window.CSS&&window.CSS.supports&&window.CSS.supports("font-weight","var(--tmp-var)")),t.parentNode.removeChild(t),e};supportsCssVars()||alert("Please view this demo in a modern browser that supports CSS Variables.");;
!function(e){"undefined"==typeof module?this.charming=e:module.exports=e}(function(e,n){"use strict";n=n||{};var t=n.tagName||"span",o=null!=n.classPrefix?n.classPrefix:"char",r=1,a=function(e){for(var n=e.parentNode,a=e.nodeValue,c=a.length,l=-1;++l<c;){var d=document.createElement(t);o&&(d.className=o+r,r++),d.appendChild(document.createTextNode(a[l])),n.insertBefore(d,e)}n.removeChild(e)};return function c(e){for(var n=[].slice.call(e.childNodes),t=n.length,o=-1;++o<t;)c(n[o]);e.nodeType===Node.TEXT_NODE&&a(e)}(e),e});;
/*
 2017 Julian Garnier
 Released under the MIT license
*/
var $jscomp={scope:{}};$jscomp.defineProperty="function"==typeof Object.defineProperties?Object.defineProperty:function(e,r,p){if(p.get||p.set)throw new TypeError("ES3 does not support getters and setters.");e!=Array.prototype&&e!=Object.prototype&&(e[r]=p.value)};$jscomp.getGlobal=function(e){return"undefined"!=typeof window&&window===e?e:"undefined"!=typeof global&&null!=global?global:e};$jscomp.global=$jscomp.getGlobal(this);$jscomp.SYMBOL_PREFIX="jscomp_symbol_";
$jscomp.initSymbol=function(){$jscomp.initSymbol=function(){};$jscomp.global.Symbol||($jscomp.global.Symbol=$jscomp.Symbol)};$jscomp.symbolCounter_=0;$jscomp.Symbol=function(e){return $jscomp.SYMBOL_PREFIX+(e||"")+$jscomp.symbolCounter_++};
$jscomp.initSymbolIterator=function(){$jscomp.initSymbol();var e=$jscomp.global.Symbol.iterator;e||(e=$jscomp.global.Symbol.iterator=$jscomp.global.Symbol("iterator"));"function"!=typeof Array.prototype[e]&&$jscomp.defineProperty(Array.prototype,e,{configurable:!0,writable:!0,value:function(){return $jscomp.arrayIterator(this)}});$jscomp.initSymbolIterator=function(){}};$jscomp.arrayIterator=function(e){var r=0;return $jscomp.iteratorPrototype(function(){return r<e.length?{done:!1,value:e[r++]}:{done:!0}})};
$jscomp.iteratorPrototype=function(e){$jscomp.initSymbolIterator();e={next:e};e[$jscomp.global.Symbol.iterator]=function(){return this};return e};$jscomp.array=$jscomp.array||{};$jscomp.iteratorFromArray=function(e,r){$jscomp.initSymbolIterator();e instanceof String&&(e+="");var p=0,m={next:function(){if(p<e.length){var u=p++;return{value:r(u,e[u]),done:!1}}m.next=function(){return{done:!0,value:void 0}};return m.next()}};m[Symbol.iterator]=function(){return m};return m};
$jscomp.polyfill=function(e,r,p,m){if(r){p=$jscomp.global;e=e.split(".");for(m=0;m<e.length-1;m++){var u=e[m];u in p||(p[u]={});p=p[u]}e=e[e.length-1];m=p[e];r=r(m);r!=m&&null!=r&&$jscomp.defineProperty(p,e,{configurable:!0,writable:!0,value:r})}};$jscomp.polyfill("Array.prototype.keys",function(e){return e?e:function(){return $jscomp.iteratorFromArray(this,function(e){return e})}},"es6-impl","es3");var $jscomp$this=this;
(function(e,r){"function"===typeof define&&define.amd?define([],r):"object"===typeof module&&module.exports?module.exports=r():e.anime=r()})(this,function(){function e(a){if(!h.col(a))try{return document.querySelectorAll(a)}catch(c){}}function r(a,c){for(var d=a.length,b=2<=arguments.length?arguments[1]:void 0,f=[],n=0;n<d;n++)if(n in a){var k=a[n];c.call(b,k,n,a)&&f.push(k)}return f}function p(a){return a.reduce(function(a,d){return a.concat(h.arr(d)?p(d):d)},[])}function m(a){if(h.arr(a))return a;
h.str(a)&&(a=e(a)||a);return a instanceof NodeList||a instanceof HTMLCollection?[].slice.call(a):[a]}function u(a,c){return a.some(function(a){return a===c})}function C(a){var c={},d;for(d in a)c[d]=a[d];return c}function D(a,c){var d=C(a),b;for(b in a)d[b]=c.hasOwnProperty(b)?c[b]:a[b];return d}function z(a,c){var d=C(a),b;for(b in c)d[b]=h.und(a[b])?c[b]:a[b];return d}function T(a){a=a.replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i,function(a,c,d,k){return c+c+d+d+k+k});var c=/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(a);
a=parseInt(c[1],16);var d=parseInt(c[2],16),c=parseInt(c[3],16);return"rgba("+a+","+d+","+c+",1)"}function U(a){function c(a,c,b){0>b&&(b+=1);1<b&&--b;return b<1/6?a+6*(c-a)*b:.5>b?c:b<2/3?a+(c-a)*(2/3-b)*6:a}var d=/hsl\((\d+),\s*([\d.]+)%,\s*([\d.]+)%\)/g.exec(a)||/hsla\((\d+),\s*([\d.]+)%,\s*([\d.]+)%,\s*([\d.]+)\)/g.exec(a);a=parseInt(d[1])/360;var b=parseInt(d[2])/100,f=parseInt(d[3])/100,d=d[4]||1;if(0==b)f=b=a=f;else{var n=.5>f?f*(1+b):f+b-f*b,k=2*f-n,f=c(k,n,a+1/3),b=c(k,n,a);a=c(k,n,a-1/3)}return"rgba("+
255*f+","+255*b+","+255*a+","+d+")"}function y(a){if(a=/([\+\-]?[0-9#\.]+)(%|px|pt|em|rem|in|cm|mm|ex|ch|pc|vw|vh|vmin|vmax|deg|rad|turn)?$/.exec(a))return a[2]}function V(a){if(-1<a.indexOf("translate")||"perspective"===a)return"px";if(-1<a.indexOf("rotate")||-1<a.indexOf("skew"))return"deg"}function I(a,c){return h.fnc(a)?a(c.target,c.id,c.total):a}function E(a,c){if(c in a.style)return getComputedStyle(a).getPropertyValue(c.replace(/([a-z])([A-Z])/g,"$1-$2").toLowerCase())||"0"}function J(a,c){if(h.dom(a)&&
u(W,c))return"transform";if(h.dom(a)&&(a.getAttribute(c)||h.svg(a)&&a[c]))return"attribute";if(h.dom(a)&&"transform"!==c&&E(a,c))return"css";if(null!=a[c])return"object"}function X(a,c){var d=V(c),d=-1<c.indexOf("scale")?1:0+d;a=a.style.transform;if(!a)return d;for(var b=[],f=[],n=[],k=/(\w+)\((.+?)\)/g;b=k.exec(a);)f.push(b[1]),n.push(b[2]);a=r(n,function(a,b){return f[b]===c});return a.length?a[0]:d}function K(a,c){switch(J(a,c)){case "transform":return X(a,c);case "css":return E(a,c);case "attribute":return a.getAttribute(c)}return a[c]||
0}function L(a,c){var d=/^(\*=|\+=|-=)/.exec(a);if(!d)return a;var b=y(a)||0;c=parseFloat(c);a=parseFloat(a.replace(d[0],""));switch(d[0][0]){case "+":return c+a+b;case "-":return c-a+b;case "*":return c*a+b}}function F(a,c){return Math.sqrt(Math.pow(c.x-a.x,2)+Math.pow(c.y-a.y,2))}function M(a){a=a.points;for(var c=0,d,b=0;b<a.numberOfItems;b++){var f=a.getItem(b);0<b&&(c+=F(d,f));d=f}return c}function N(a){if(a.getTotalLength)return a.getTotalLength();switch(a.tagName.toLowerCase()){case "circle":return 2*
Math.PI*a.getAttribute("r");case "rect":return 2*a.getAttribute("width")+2*a.getAttribute("height");case "line":return F({x:a.getAttribute("x1"),y:a.getAttribute("y1")},{x:a.getAttribute("x2"),y:a.getAttribute("y2")});case "polyline":return M(a);case "polygon":var c=a.points;return M(a)+F(c.getItem(c.numberOfItems-1),c.getItem(0))}}function Y(a,c){function d(b){b=void 0===b?0:b;return a.el.getPointAtLength(1<=c+b?c+b:0)}var b=d(),f=d(-1),n=d(1);switch(a.property){case "x":return b.x;case "y":return b.y;
case "angle":return 180*Math.atan2(n.y-f.y,n.x-f.x)/Math.PI}}function O(a,c){var d=/-?\d*\.?\d+/g,b;b=h.pth(a)?a.totalLength:a;if(h.col(b))if(h.rgb(b)){var f=/rgb\((\d+,\s*[\d]+,\s*[\d]+)\)/g.exec(b);b=f?"rgba("+f[1]+",1)":b}else b=h.hex(b)?T(b):h.hsl(b)?U(b):void 0;else f=(f=y(b))?b.substr(0,b.length-f.length):b,b=c&&!/\s/g.test(b)?f+c:f;b+="";return{original:b,numbers:b.match(d)?b.match(d).map(Number):[0],strings:h.str(a)||c?b.split(d):[]}}function P(a){a=a?p(h.arr(a)?a.map(m):m(a)):[];return r(a,
function(a,d,b){return b.indexOf(a)===d})}function Z(a){var c=P(a);return c.map(function(a,b){return{target:a,id:b,total:c.length}})}function aa(a,c){var d=C(c);if(h.arr(a)){var b=a.length;2!==b||h.obj(a[0])?h.fnc(c.duration)||(d.duration=c.duration/b):a={value:a}}return m(a).map(function(a,b){b=b?0:c.delay;a=h.obj(a)&&!h.pth(a)?a:{value:a};h.und(a.delay)&&(a.delay=b);return a}).map(function(a){return z(a,d)})}function ba(a,c){var d={},b;for(b in a){var f=I(a[b],c);h.arr(f)&&(f=f.map(function(a){return I(a,
c)}),1===f.length&&(f=f[0]));d[b]=f}d.duration=parseFloat(d.duration);d.delay=parseFloat(d.delay);return d}function ca(a){return h.arr(a)?A.apply(this,a):Q[a]}function da(a,c){var d;return a.tweens.map(function(b){b=ba(b,c);var f=b.value,e=K(c.target,a.name),k=d?d.to.original:e,k=h.arr(f)?f[0]:k,w=L(h.arr(f)?f[1]:f,k),e=y(w)||y(k)||y(e);b.from=O(k,e);b.to=O(w,e);b.start=d?d.end:a.offset;b.end=b.start+b.delay+b.duration;b.easing=ca(b.easing);b.elasticity=(1E3-Math.min(Math.max(b.elasticity,1),999))/
1E3;b.isPath=h.pth(f);b.isColor=h.col(b.from.original);b.isColor&&(b.round=1);return d=b})}function ea(a,c){return r(p(a.map(function(a){return c.map(function(b){var c=J(a.target,b.name);if(c){var d=da(b,a);b={type:c,property:b.name,animatable:a,tweens:d,duration:d[d.length-1].end,delay:d[0].delay}}else b=void 0;return b})})),function(a){return!h.und(a)})}function R(a,c,d,b){var f="delay"===a;return c.length?(f?Math.min:Math.max).apply(Math,c.map(function(b){return b[a]})):f?b.delay:d.offset+b.delay+
b.duration}function fa(a){var c=D(ga,a),d=D(S,a),b=Z(a.targets),f=[],e=z(c,d),k;for(k in a)e.hasOwnProperty(k)||"targets"===k||f.push({name:k,offset:e.offset,tweens:aa(a[k],d)});a=ea(b,f);return z(c,{children:[],animatables:b,animations:a,duration:R("duration",a,c,d),delay:R("delay",a,c,d)})}function q(a){function c(){return window.Promise&&new Promise(function(a){return p=a})}function d(a){return g.reversed?g.duration-a:a}function b(a){for(var b=0,c={},d=g.animations,f=d.length;b<f;){var e=d[b],
k=e.animatable,h=e.tweens,n=h.length-1,l=h[n];n&&(l=r(h,function(b){return a<b.end})[0]||l);for(var h=Math.min(Math.max(a-l.start-l.delay,0),l.duration)/l.duration,w=isNaN(h)?1:l.easing(h,l.elasticity),h=l.to.strings,p=l.round,n=[],m=void 0,m=l.to.numbers.length,t=0;t<m;t++){var x=void 0,x=l.to.numbers[t],q=l.from.numbers[t],x=l.isPath?Y(l.value,w*x):q+w*(x-q);p&&(l.isColor&&2<t||(x=Math.round(x*p)/p));n.push(x)}if(l=h.length)for(m=h[0],w=0;w<l;w++)p=h[w+1],t=n[w],isNaN(t)||(m=p?m+(t+p):m+(t+" "));
else m=n[0];ha[e.type](k.target,e.property,m,c,k.id);e.currentValue=m;b++}if(b=Object.keys(c).length)for(d=0;d<b;d++)H||(H=E(document.body,"transform")?"transform":"-webkit-transform"),g.animatables[d].target.style[H]=c[d].join(" ");g.currentTime=a;g.progress=a/g.duration*100}function f(a){if(g[a])g[a](g)}function e(){g.remaining&&!0!==g.remaining&&g.remaining--}function k(a){var k=g.duration,n=g.offset,w=n+g.delay,r=g.currentTime,x=g.reversed,q=d(a);if(g.children.length){var u=g.children,v=u.length;
if(q>=g.currentTime)for(var G=0;G<v;G++)u[G].seek(q);else for(;v--;)u[v].seek(q)}if(q>=w||!k)g.began||(g.began=!0,f("begin")),f("run");if(q>n&&q<k)b(q);else if(q<=n&&0!==r&&(b(0),x&&e()),q>=k&&r!==k||!k)b(k),x||e();f("update");a>=k&&(g.remaining?(t=h,"alternate"===g.direction&&(g.reversed=!g.reversed)):(g.pause(),g.completed||(g.completed=!0,f("complete"),"Promise"in window&&(p(),m=c()))),l=0)}a=void 0===a?{}:a;var h,t,l=0,p=null,m=c(),g=fa(a);g.reset=function(){var a=g.direction,c=g.loop;g.currentTime=
0;g.progress=0;g.paused=!0;g.began=!1;g.completed=!1;g.reversed="reverse"===a;g.remaining="alternate"===a&&1===c?2:c;b(0);for(a=g.children.length;a--;)g.children[a].reset()};g.tick=function(a){h=a;t||(t=h);k((l+h-t)*q.speed)};g.seek=function(a){k(d(a))};g.pause=function(){var a=v.indexOf(g);-1<a&&v.splice(a,1);g.paused=!0};g.play=function(){g.paused&&(g.paused=!1,t=0,l=d(g.currentTime),v.push(g),B||ia())};g.reverse=function(){g.reversed=!g.reversed;t=0;l=d(g.currentTime)};g.restart=function(){g.pause();
g.reset();g.play()};g.finished=m;g.reset();g.autoplay&&g.play();return g}var ga={update:void 0,begin:void 0,run:void 0,complete:void 0,loop:1,direction:"normal",autoplay:!0,offset:0},S={duration:1E3,delay:0,easing:"easeOutElastic",elasticity:500,round:0},W="translateX translateY translateZ rotate rotateX rotateY rotateZ scale scaleX scaleY scaleZ skewX skewY perspective".split(" "),H,h={arr:function(a){return Array.isArray(a)},obj:function(a){return-1<Object.prototype.toString.call(a).indexOf("Object")},
pth:function(a){return h.obj(a)&&a.hasOwnProperty("totalLength")},svg:function(a){return a instanceof SVGElement},dom:function(a){return a.nodeType||h.svg(a)},str:function(a){return"string"===typeof a},fnc:function(a){return"function"===typeof a},und:function(a){return"undefined"===typeof a},hex:function(a){return/(^#[0-9A-F]{6}$)|(^#[0-9A-F]{3}$)/i.test(a)},rgb:function(a){return/^rgb/.test(a)},hsl:function(a){return/^hsl/.test(a)},col:function(a){return h.hex(a)||h.rgb(a)||h.hsl(a)}},A=function(){function a(a,
d,b){return(((1-3*b+3*d)*a+(3*b-6*d))*a+3*d)*a}return function(c,d,b,f){if(0<=c&&1>=c&&0<=b&&1>=b){var e=new Float32Array(11);if(c!==d||b!==f)for(var k=0;11>k;++k)e[k]=a(.1*k,c,b);return function(k){if(c===d&&b===f)return k;if(0===k)return 0;if(1===k)return 1;for(var h=0,l=1;10!==l&&e[l]<=k;++l)h+=.1;--l;var l=h+(k-e[l])/(e[l+1]-e[l])*.1,n=3*(1-3*b+3*c)*l*l+2*(3*b-6*c)*l+3*c;if(.001<=n){for(h=0;4>h;++h){n=3*(1-3*b+3*c)*l*l+2*(3*b-6*c)*l+3*c;if(0===n)break;var m=a(l,c,b)-k,l=l-m/n}k=l}else if(0===
n)k=l;else{var l=h,h=h+.1,g=0;do m=l+(h-l)/2,n=a(m,c,b)-k,0<n?h=m:l=m;while(1e-7<Math.abs(n)&&10>++g);k=m}return a(k,d,f)}}}}(),Q=function(){function a(a,b){return 0===a||1===a?a:-Math.pow(2,10*(a-1))*Math.sin(2*(a-1-b/(2*Math.PI)*Math.asin(1))*Math.PI/b)}var c="Quad Cubic Quart Quint Sine Expo Circ Back Elastic".split(" "),d={In:[[.55,.085,.68,.53],[.55,.055,.675,.19],[.895,.03,.685,.22],[.755,.05,.855,.06],[.47,0,.745,.715],[.95,.05,.795,.035],[.6,.04,.98,.335],[.6,-.28,.735,.045],a],Out:[[.25,
.46,.45,.94],[.215,.61,.355,1],[.165,.84,.44,1],[.23,1,.32,1],[.39,.575,.565,1],[.19,1,.22,1],[.075,.82,.165,1],[.175,.885,.32,1.275],function(b,c){return 1-a(1-b,c)}],InOut:[[.455,.03,.515,.955],[.645,.045,.355,1],[.77,0,.175,1],[.86,0,.07,1],[.445,.05,.55,.95],[1,0,0,1],[.785,.135,.15,.86],[.68,-.55,.265,1.55],function(b,c){return.5>b?a(2*b,c)/2:1-a(-2*b+2,c)/2}]},b={linear:A(.25,.25,.75,.75)},f={},e;for(e in d)f.type=e,d[f.type].forEach(function(a){return function(d,f){b["ease"+a.type+c[f]]=h.fnc(d)?
d:A.apply($jscomp$this,d)}}(f)),f={type:f.type};return b}(),ha={css:function(a,c,d){return a.style[c]=d},attribute:function(a,c,d){return a.setAttribute(c,d)},object:function(a,c,d){return a[c]=d},transform:function(a,c,d,b,f){b[f]||(b[f]=[]);b[f].push(c+"("+d+")")}},v=[],B=0,ia=function(){function a(){B=__hf.requestAnimationFrame(c)}function c(c){var b=v.length;if(b){for(var d=0;d<b;)v[d]&&v[d].tick(c),d++;a()}else __hf.cancelAnimationFrame(B),B=0}return a}();q.version="2.2.0";q.speed=1;q.running=v;q.remove=
function(a){a=P(a);for(var c=v.length;c--;)for(var d=v[c],b=d.animations,f=b.length;f--;)u(a,b[f].animatable.target)&&(b.splice(f,1),b.length||d.pause())};q.getValue=K;q.path=function(a,c){var d=h.str(a)?e(a)[0]:a,b=c||100;return function(a){return{el:d,property:a,totalLength:N(d)*(b/100)}}};q.setDashoffset=function(a){var c=N(a);a.setAttribute("stroke-dasharray",c);return c};q.bezier=A;q.easings=Q;q.timeline=function(a){var c=q(a);c.pause();c.duration=0;c.add=function(d){c.children.forEach(function(a){a.began=
!0;a.completed=!0});m(d).forEach(function(b){var d=z(b,D(S,a||{}));d.targets=d.targets||a.targets;b=c.duration;var e=d.offset;d.autoplay=!1;d.direction=c.direction;d.offset=h.und(e)?b:L(e,b);c.began=!0;c.completed=!0;c.seek(d.offset);d=q(d);d.began=!0;d.completed=!0;d.duration>b&&(c.duration=d.duration);c.children.push(d)});c.seek(0);c.reset();c.autoplay&&c.restart();return c};return c};q.random=function(a,c){return Math.floor(__hf.random()*(c-a+1))+a};return q});;
/**
 * wordFx.js
 * http://www.codrops.com
 *
 * Licensed under the MIT license.
 * http://www.opensource.org/licenses/mit-license.php
 * 
 * Copyright 2017, Codrops
 * http://www.codrops.com
 */
{
    // From https://davidwalsh.name/javascript-debounce-function.
	function debounce(func, wait, immediate) {
		var timeout;
		return function() {
			var context = this, args = arguments;
			var later = function() {
				timeout = null;
				if (!immediate) func.apply(context, args);
			};
			var callNow = immediate && !timeout;
			__hf.clearTimeout(timeout);
			timeout = __hf.setTimeout(later, wait);
			if (callNow) func.apply(context, args);
		};
    };

    // From http://snipplr.com/view/37687/random-number-float-generator/
    function randomBetween(minValue,maxValue,precision) {
        if( typeof(precision) == 'undefined' ) {
            precision = 2;
        }
        return parseFloat(Math.min(minValue + (__hf.random() * (maxValue - minValue)),maxValue).toFixed(precision));
    }

    let winsize = {width: window.innerWidth, height: window.innerHeight};

    class Shape {
        constructor(type, letterRect, options) {
            this.DOM = {};
            this.options = {
                shapeTypes: ['circle', 'rect', 'polygon'],
                shapeColors: ['#e07272', '#0805b5', '#49c6ff', '#8bc34a', '#1e1e21', '#e24e81', '#e0cd24'],
                shapeFill: true,
                shapeStrokeWidth: 1
            }
            Object.assign(this.options, options);
            this.type = type || this.options.shapeTypes[0];
            if ( this.type !== 'random' && !this.options.types.includes(this.type) ) return;
            if (this.type === 'random') this.type = this.options.shapeTypes[randomBetween(0,this.options.shapeTypes.length-1,0)];
            this.letterRect = letterRect;
            this.init();
        }
        init() {
            this.DOM.el = document.createElementNS('http://www.w3.org/2000/svg', this.type);
            this.DOM.el.style.opacity = 0;
            this.configureShapeType();
            
            if ( this.options.shapeFill ) {
                this.DOM.el.setAttribute('fill', this.options.shapeColors[randomBetween(0,this.options.shapeColors.length-1,0)]);
            }
            else {
                this.DOM.el.setAttribute('fill', 'none');
                this.DOM.el.setAttribute('stroke-width', this.options.shapeStrokeWidth);
                this.DOM.el.setAttribute('stroke', this.options.shapeColors[randomBetween(0,this.options.shapeColors.length-1,0)]);
            }
        }
        configureShapeType() {
            this.DOM.el.style.transformOrigin = `${this.letterRect.left + this.letterRect.width/2}px ${this.letterRect.top + this.letterRect.height/2}px`;

            if ( this.type === 'circle' ) {
                const r = 0.5*this.letterRect.width;
                this.DOM.el.setAttribute('r', r);
                this.DOM.el.setAttribute('cx', this.letterRect.left + this.letterRect.width/2);
                this.DOM.el.setAttribute('cy', this.letterRect.top + this.letterRect.height/2);
            }
            else if ( this.type === 'rect' ) {
                const w = randomBetween(0.05,0.5,3)*this.letterRect.width;
                const h = randomBetween(0.05,0.5,3)*this.letterRect.height;
                this.DOM.el.setAttribute('width', w);
                this.DOM.el.setAttribute('height', h);
                this.DOM.el.setAttribute('x', this.letterRect.left + (this.letterRect.width-w)/2);
                this.DOM.el.setAttribute('y', this.letterRect.top + (this.letterRect.height-h)/2);
            }
            else if ( this.type === 'polygon' ) {
                this.DOM.el.setAttribute('points', `${this.letterRect.left} ${this.letterRect.top+this.letterRect.height}, ${this.letterRect.left+this.letterRect.width/2} ${this.letterRect.bottom-this.letterRect.width}, ${this.letterRect.left+this.letterRect.width} ${this.letterRect.top+this.letterRect.height}`);
            }
        }
        onResize( letterRect ) {
            this.letterRect = letterRect;
            this.configureShapeType();
        }
    };

    class Letter {
        constructor(el, svg, options) {
            this.DOM = {};
            this.DOM.el = el;
            this.DOM.svg = svg;
            this.options = {
                totalShapes: 10
            }
            Object.assign(this.options, options);
            this.rect = this.DOM.el.getBoundingClientRect();
            this.totalShapes = this.options.totalShapes;
            this.init();
            this.initEvents();
        }
        init() {
            this.shapes = [];
            for (let i = 0; i <= this.totalShapes-1; ++i) {
                const shape = new Shape('random', this.rect, this.options);
                this.shapes.push(shape);
                this.DOM.svg.appendChild(shape.DOM.el);
            }
        }
        initEvents() {
            window.addEventListener('resize', debounce(() => {
                this.rect = this.DOM.el.getBoundingClientRect();
                for (let i = 0; i <= this.totalShapes-1; ++i) {
                    const shape = this.shapes[i];
                    shape.onResize(this.rect);
                }
            }, 20));
        }
    };

    class Word {
        constructor(el, options) {
            this.DOM = {};
            this.DOM.el = el;
            this.options = {
                shapesOnTop: false
            }
            Object.assign(this.options, options);
            this.init();
            this.initEvents();
        }
        init() {
            this.createSVG();
            charming(this.DOM.el);
            this.letters = [];
            Array.from(this.DOM.el.querySelectorAll('span')).forEach(letter => this.letters.push(new Letter(letter, this.DOM.svg, this.options)));
        }
        initEvents() {
            window.addEventListener('resize', debounce(() => {
                winsize = {width: window.innerWidth, height: window.innerHeight};
                this.DOM.svg.setAttribute('width', `${winsize.width}px`);
                this.DOM.svg.setAttribute('height',`${winsize.width}px`);
                this.DOM.svg.setAttribute('viewbox',`0 0 ${winsize.width} ${winsize.height}`);
            }, 20));
        }
        createSVG() {
            this.DOM.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            this.DOM.svg.setAttribute('class', 'shapes');
            this.DOM.svg.setAttribute('width', `${winsize.width}px`);
            this.DOM.svg.setAttribute('height',`${winsize.width}px`);
            this.DOM.svg.setAttribute('viewbox',`0 0 ${winsize.width} ${winsize.height}`);
            if ( this.options.shapesOnTop ) {
                this.DOM.el.parentNode.insertBefore(this.DOM.svg, this.DOM.el.nextSibling);
            }
            else {
                this.DOM.el.parentNode.insertBefore(this.DOM.svg, this.DOM.el);
            }
        }
        show(config) {
            return this.toggle('show', config);
        }
        hide(config) {
            return this.toggle('hide', config);
        }
        toggle(action = 'show', config) {
            return new Promise((resolve, reject) => {
                const toggleNow = () => {
                    for (let i = 0, len = this.letters.length; i <= len-1; ++i) {
                        this.letters[i].DOM.el.style.opacity = action === 'show' ? 1 : 0;
                    }
                    resolve();
                };

                if ( config && Object.keys(config).length !== 0 ) {
                    if ( config.shapesAnimationOpts ) {
                        for (let i = 0, len = this.letters.length; i <= len-1; ++i) {
                            const letter = this.letters[i];
                            __hf.setTimeout( function(letter) {
                                return () => {
                                    config.shapesAnimationOpts.targets = letter.shapes.map(shape => shape.DOM.el);
                                    anime.remove(config.shapesAnimationOpts.targets);
                                    anime(config.shapesAnimationOpts);
                                }
                            }(letter), config.lettersAnimationOpts && config.lettersAnimationOpts.delay ? config.lettersAnimationOpts.delay(letter.DOM.el,i) : 0);        
                        }
                    }
                    if ( config.lettersAnimationOpts ) {
                        config.lettersAnimationOpts.targets = this.letters.map(letter => letter.DOM.el);
                        config.lettersAnimationOpts.complete = () => {
                            if (action === 'hide' ) {
                                for (let i = 0, len = config.lettersAnimationOpts.targets.length; i <= len-1; ++i) {
                                    config.lettersAnimationOpts.targets[i].style.transform = 'none';
                                }
                            }
                            resolve();
                        };
                        anime(config.lettersAnimationOpts);
                    }
                    else {
                        toggleNow();
                    }
                }
                else {
                    toggleNow();
                }
            });
        }
    };

    window.Word = Word;
};;

			{
				const effects = [
					// Effect 1
					{
						options: {
							shapeColors: ['#6435ea','#295ddc','#9fd7ff','#d65380','#0228f7','#242627']
						},
						hide: {
							lettersAnimationOpts: {
								duration: 800,
								delay: (t,i) => i*40,
								easing: 'easeOutExpo',
								opacity: {
									value: 0, 
									duration: 100,
									delay: (t,i) => i*40,
									easing: 'linear'
								},
								translateY: ['0%', '100%']
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 800,
								delay: (t,i) => i*40,
								easing: 'easeOutElastic',
								opacity: [0,1],
								translateY: ['100%', '0%']
							},
							shapesAnimationOpts: {
								duration: 300,
								delay: (t,i) => i*30+100,
								easing: 'easeOutQuad',
								translateY: () => [anime.random(-15,15),anime.random(-200,200)],
								scale: () => [0.2,randomBetween(0.5,1)],
								opacity: [
									{
										value: 1, 
										duration:1, 
										delay: (t,i) => i*30+100
									}, 
									{
										value: 0,
										duration: 200, 
										delay:200,
										easing: 'linear'}
								]
							}
						}
					},
					// Effect 2
					{
						options: {
							shapeColors: ['#0671e6'],
							shapeTypes: ['circle'],
							shapeFill: false,
							shapeStrokeWidth: 3
						},
						hide: {
							lettersAnimationOpts: {
								duration: 300,
								delay: (t,i,total) => i*25,
								easing: 'easeOutQuad',
								opacity: {
									value: 0, 
									duration: 100, 
									delay: (t,i,total) => i*25,
									easing: 'linear'
								},
								translateY: ['0%','-50%']
							},
							shapesAnimationOpts: {
								duration: 300,
								delay: (t,i) => i*20,
								easing: 'easeOutExpo',
								translateX: t => anime.random(-10,10),
								translateY: t => -1*anime.random(400,800),
								scale: [0.3,0.3],
								opacity: [
									{
										value: 1, 
										duration:1, 
										delay: (t,i) => i*20
									}, 
									{
										value: 0,
										duration: 300, 
										easing: 'linear'
									}
								]
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 800,
								delay: (t,i,total) => Math.abs(total/2-i)*60,
								easing: 'easeOutElastic',
								opacity: [0,1],
								translateY: ['50%', '0%']
							},
							shapesAnimationOpts: {
								duration: 700,
								delay: (t,i) => i*60,
								easing: 'easeOutExpo',
								translateX: () => {
									const rand = anime.random(-100,100);
									return [rand,rand];
								},
								translateY: () => {
									const rand = anime.random(-100,100);
									return [rand,rand];
								},
								scale: () => [randomBetween(0.1,0.3),randomBetween(0.5,0.8)],
								opacity: [{value: 1, duration:1, delay: (t,i) => i*80}, {value:0,duration: 700, easing: 'easeOutQuad',delay: 100}]
							}
						}
					},
					// Effect 3
					{
						options: {
							shapeColors: ['#111']
						},
						hide: {
							shapesAnimationOpts: {
								duration: 200,
								delay: (t,i) => i*20,
								easing: 'easeOutExpo',
								translateX: t => t.dataset.tx,
								translateY: t => t.dataset.ty - anime.random(400,800),
								scale: t => t.dataset.s,
								rotate: 0,
								opacity: {
									value: 0, 
									duration: 200, 
									easing: 'linear'
								}
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 500,
								delay: (t,i) => i*60,
								easing: 'easeOutExpo',
								opacity: {
									value: [0,1], 
									duration: 50,
									delay: (t,i) => i*60,
									easing: 'linear'
								},
								translateY: (t,i) => i%2 ? [anime.random(-350,-300),0] : [anime.random(300,350),0]
							},
							shapesAnimationOpts: {
								duration: () => anime.random(1000,4000),
								delay: (t,i) => i*20,
								easing: [0.2,1,0.3,1],
								translateX: t => {
									const tx = anime.random(-200,200);
									t.dataset.tx = tx;
									return [0,tx];
								},
								translateY: t => {
									const ty = anime.random(-300,300);
									t.dataset.ty = ty;
									return [0,ty];
								},
								scale: t => {
									const s = randomBetween(0.2,0.6);
									t.dataset.s = s;
									return [s,s];
								},  
								rotate: () => anime.random(-90,90),
								opacity: {
									value: 0.6, 
									duration: 1000, 
									easing: 'linear'
								}
							}
						}
					},
					// Effect 4
					{
						options: {
							// shape elements will be on top of the letters
							shapesOnTop: true,
							shapeColors: ['#ec4747','#5447ec','#ecb447','#a847ec','#635f65'],
							totalShapes: 20
						},
						hide: {
							lettersAnimationOpts: {
								duration: 200,
								delay: (t,i,total) => (total-i-1)*20,
								easing: 'easeOutExpo',
								opacity: {
									value: [1,0], 
									duration: 100, 
									delay: (t,i,total) => (total-i-1)*20,
									easing: 'linear'
								},
								scale: [1,0]
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 400,
								delay: (t,i) => i*60,
								easing: 'easeInOutExpo',
								opacity: [0,1],
								translateY: ['-100%', '0%']
							},
							shapesAnimationOpts: {
								duration: 400,
								delay: (t,i) => i*20,
								easing: 'easeOutBack',
								translateX: {
									value: () => [anime.random(-100,100),anime.random(-10,10)],
									easing: 'easeOutExpo',
								},
								translateY: () => [anime.random(-100,0),anime.random(-400,-50)],
								scale: () => {
									const rand = randomBetween(0.2,0.5);
									return [rand,rand];
								},
								rotate: () => anime.random(-15,15),
								opacity: [
									{
										value: 1, 
										duration:1, 
										delay: (t,i) => i*20
									}, 
									{
										value:0,
										duration: 500, 
										easing: 'linear'
									}
								]
							}
						}
					},
					// Effect 5
					{
						options: {
							shapesOnTop: true,
							shapeColors: ['#ec4747','#5447ec','#ecb447','#a847ec','#635f65'],
							shapeFill: false,
							shapeStrokeWidth: 4,
							totalShapes: 30
						},
						show: {
							lettersAnimationOpts: {
								duration: 300,
								delay: (t,i) => i*100,
								easing: 'easeInExpo',
								opacity: [0,1],
								translateY: ['-50%', '0%']
							},
							shapesAnimationOpts: {
								duration: 400,
								delay: (t,i) => i*5+300,
								easing: [0.2,1,0.3,1],
								translateX: () => [0, anime.random(-100,100)],
								translateY: () => [50,anime.random(-100,150)],
								scale: () => [randomBetween(0.2,0.4),randomBetween(0.2,0.4)],
								rotate: () => anime.random(-25,25),
								opacity: [
									{value: 1, duration: 1, easing: 'easeOutQuad', delay: (t,i) => i*5+300}, 
									{value: 0, duration: 250, easing: 'easeOutQuad', delay: 200}
								]
							}
						}
					},
					// Effect 6
					{
						options: {
							shapeColors: ['#fff','#dedede','#8c8c8c','#545454','#000','#dc2e2e']
						},
						hide: {
							lettersAnimationOpts: {
								duration: 200,
								delay: (t,i,total) => (total-i-1)*20,
								easing: 'easeOutExpo',
								opacity: {
									value: [1,0], 
									duration: 100, 
									delay: (t,i,total) => (total-i-1)*20,
									easing: 'linear'
								},
								scale: [1,0]
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 400,
								delay: (t,i) => i*60,
								easing: 'easeInExpo',
								opacity: [0,1],
								scale: [0,1]
							},
							shapesAnimationOpts: {
								duration: 700,
								delay: (t,i) => i*40,
								easing: 'easeOutExpo',
								translateX: () => [0,anime.random(-20,20)],
								translateY: () => [0,anime.random(-400,400)],
								scale: () => [randomBetween(0.2,0.6),randomBetween(0.2,0.6)],  
								rotate: () => [0,anime.random(-16,16)],
								opacity: [
									{value: 1, duration: 1, easing: 'linear'}, 
									{value: 0, duration: 700, easing: 'easeOutQuad'}
								]
							}
						}
					},
					// Effect 7
					{
						options: {
							shapeColors: ['red','#000','#fff'],
							shapeFill: false,
							shapeStrokeWidth: 10
						},
						hide: {
							shapesAnimationOpts: {
								duration: 250,
								delay: (t,i) => i*20,
								easing: 'easeOutExpo',
								translateX: () => [0,anime.random(-200,200)],
								translateY: () => [0,anime.random(-200,200)],
								scale: () => [randomBetween(0.2,0.6),randomBetween(0.2,0.6)],  
								rotate: () => [0,anime.random(-16,16)],
								opacity: [
									{value: 1, duration: 1, easing: 'linear', delay: (t,i) => i*20}, 
									{value: 0, duration: 150, delay: 100, easing: 'easeOutQuad'}
								]
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 400,
								delay: (t,i) => i*60,
								easing: 'easeOutExpo',
								opacity: {
									value: [0,1], 
									duration: 100, 
									easing: 'linear'
								},
								translateY: (t,i) => i%2 ? [anime.random(-350,-300),0] : [anime.random(300,350),0]
							},
							shapesAnimationOpts: {
								duration: 500,
								delay: (t,i) => i*30,
								easing: 'easeOutExpo',
								translateX: () => [0,anime.random(-200,200)],
								translateY: () => [0,anime.random(-200,200)],
								scale: () => [randomBetween(0.2,0.6),randomBetween(0.2,0.6)],  
								rotate: () => [0,anime.random(-16,16)],
								opacity: [
									{value: 1, duration: 1, easing: 'linear'}, 
									{value: 0, duration: 350, delay: 150, easing: 'easeOutQuad'}
								]
							}
						}
					},
					// Effect 8
					{
						options: {
							shapeColors: ['#35c394','#9985ee','#f54665','#4718f5','#f5aa18'],
							shapesOnTop: true
						},
						hide: {
							lettersAnimationOpts: {
								duration: 300,
								delay: (t,i)  => (t.parentNode.children.length-i-1)*30,
								easing: 'easeOutExpo',
								opacity: 0,
								translateY: (t,i) => i%2 === 0 ? '80%' : '-80%',
								rotate: (t,i) => i%2 === 0 ? -25 : 25
							},
							shapesAnimationOpts: {
								duration: 50,
								easing: 'easeOutExpo',
								translateX: t => t.dataset.tx,
								translateY: t => t.dataset.ty,
								scale: 0,
								rotate: 0,
								opacity: {
									value: 0, 
									duration: 50, 
									easing: 'linear'
								}
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 400,
								delay: (t,i)  => (t.parentNode.children.length-i-1)*80,
								easing: 'easeOutElastic',
								opacity: {
									value: [0,1], 
									duration: 100, 
									easing: 'linear'
								},
								translateY: (t,i) => i%2 === 0 ? ['-80%', '0%'] : ['80%', '0%'],
								rotate: [90,0]
							},
							shapesAnimationOpts: {
								duration: () => anime.random(1000,3000),
								delay: (t,i) => i*20,
								easing: 'easeOutElastic',
								translateX: t => {
									const tx = anime.random(-250,250);
									t.dataset.tx = tx;
									return [0,tx];
								},
								translateY: t => {
									const ty = anime.random(-250,250);
									t.dataset.ty = ty;
									return [0,ty];
								},
								scale: t => {
									const s = randomBetween(0.1,0.6);
									t.dataset.s = s;
									return [s,s];
								},  
								rotate: () => anime.random(-90,90),
								opacity: {
									value: 0.6, 
									duration: 1000, 
									easing: 'linear'
								}
							}
						}
					},
					// Effect 9
					{
						options: {
							shapeColors: ['#FD74FF','#3771FC','#7C5CE4','#542A95','#ACC7FE'],
							shapeTypes: ['rect','polygon'],
							totalShapes: 1
						},
						hide: {
							lettersAnimationOpts: {
								duration: () => anime.random(800,1000),
								delay: () => anime.random(0,80),
								easing: 'easeInOutExpo',
								opacity: 0,
								translateY: '300%',
								rotateZ: () => anime.random(-50,50)
							},
							shapesAnimationOpts: {
								duration: 350,
								easing: 'easeOutExpo',
								translateX: t => [t.dataset.tx,anime.random(-25,25)],
								translateY: t => [t.dataset.ty,anime.random(-25,25)],
								scale: 1,
								rotate: 0,
								opacity: {
									value: 0, 
									duration: 200, 
									easing: 'linear'
								}
							}
						},
						show: {
							lettersAnimationOpts: {
								duration: 800,
								delay: () => anime.random(0,75),
								easing: 'easeInOutExpo',
								opacity: [0,1],
								translateY: ['-300%','0%'],
								rotate: () => [anime.random(-50,50), 0]
							},
							shapesAnimationOpts: {
								duration: 2000,
								easing: 'easeOutExpo',
								translateY: t => {
									const ty = anime.random(-300,300);
									t.dataset.ty = ty;
									return [anime.random(-25,25),ty];
								},
								scale: t => {
									const s = randomBetween(1.5,2);
									t.dataset.s = s;
									return [s,s];
								},  
								rotate: () => anime.random(-45,45),
								opacity: {
									value: [0,0.9], 
									duration: 600,
									delay: 300,
									easing: 'linear'
								}
							}
						}
					}
				];

				class Slideshow {
					constructor(el) {
						this.DOM = {};
						this.DOM.el = el;
						this.DOM.slides = Array.from(this.DOM.el.querySelectorAll('.slide'));
						this.DOM.bgs = Array.from(this.DOM.el.querySelectorAll('.slide__bg'));
						this.DOM.words = Array.from(this.DOM.el.querySelectorAll('.word'));
						this.slidesTotal = this.DOM.slides.length;
						this.current = 0;
						this.words = [];
						this.DOM.words.forEach((word, pos) => {
							this.words.push(new Word(word, effects[pos].options));
						});
						
						this.isAnimating = true;
						this.words[this.current].show(effects[this.current].show).then(() => this.isAnimating = false);
					}
					show(direction) {
						if ( this.isAnimating ) return;
						this.isAnimating = true;
						
						let newPos;
						let currentPos = this.current;
						if ( direction === 'next' ) {
							newPos = currentPos < this.slidesTotal - 1 ? currentPos+1 : 0;
						}
						else if ( direction === 'prev' ) {
							newPos = currentPos > 0 ? currentPos-1 : this.slidesTotal - 1;
						}

						this.DOM.slides[newPos].style.opacity = 1;
						this.DOM.bgs[newPos].style.transform = 'none';
						anime({
							targets: this.DOM.bgs[currentPos],
							duration: 600,
							easing: [0.2,1,0.3,1],
							translateY: ['0%', direction === 'next' ? '-100%' : '100%'],
							complete: () => {
								this.DOM.slides[currentPos].classList.remove('slide--current');
								this.DOM.slides[currentPos].style.opacity = 0;
								this.DOM.slides[newPos].classList.add('slide--current');
								this.words[newPos].show(effects[newPos].show).then(() => this.isAnimating = false);
							}
						});

						this.words[newPos].hide();
						this.words[this.current].hide(effects[currentPos].hide).then(() => {
							
							this.current = newPos;
						});
					}
    			}

				const slideshow = new Slideshow(document.querySelector('.slideshow'));
				document.querySelector('.slidenav__item--prev').addEventListener('click', () => slideshow.show('prev') );
				document.querySelector('.slidenav__item--next').addEventListener('click', () => slideshow.show('next') );
				document.addEventListener('keydown', (ev) => {
					const keyCode = ev.keyCode || ev.which;
					if ( keyCode === 37 ) {
						slideshow.show('prev');
					}
					else if ( keyCode === 39 ) {
						slideshow.show('next');
					}
				});
			}
		
}
];
