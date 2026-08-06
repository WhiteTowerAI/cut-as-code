/* Generated from the original Codrops entry scripts. */
window.__hfRecipeFactories = [
function (__hf) {


window.WebFont = window.WebFont || {
  load(options = {}) {
    const usedFonts = new Map();
    if (document.fonts && document.body && typeof getComputedStyle === "function") {
      for (const element of document.body.querySelectorAll("*")) {
        const text = element.childElementCount === 0 ? element.textContent?.trim() : "";
        if (!text) continue;
        const font = getComputedStyle(element).font;
        if (font && !usedFonts.has(font)) usedFonts.set(font, text.slice(0, 128));
      }
    }
    const fonts = document.fonts
      ? [...document.fonts].map((fontFace) => fontFace.load().catch(() => null))
      : [];
    for (const [font, text] of usedFonts) {
      fonts.push(document.fonts.load(font, text).catch(() => null));
    }
    const ready = Promise.all(fonts)
      .then(() => document.fonts?.ready)
      .then(() => {
        if (typeof options.active === "function") options.active();
      })
      .then(() => Promise.resolve());
    window.__hfWebFontReady = ready;
    return ready;
  }
};
;
document.documentElement.className="js";var supportsCssVars=function(){var e,t=document.createElement("style");return t.innerHTML="root: { --tmp-var: bold; }",document.head.appendChild(t),e=!!(window.CSS&&window.CSS.supports&&window.CSS.supports("font-weight","var(--tmp-var)")),t.parentNode.removeChild(t),e};supportsCssVars()||alert("Please view this demo in a modern browser that supports CSS Variables.");;
(() => {
  // index.e9a2d1b4.js
  function t(t2) {
    return t2 && t2.__esModule ? t2.default : t2;
  }
  var e = (t2, e2) => Math.floor(__hf.random() * (e2 - t2 + 1)) + t2;
  function o(t2, e2, o2) {
    return e2 in t2 ? Object.defineProperty(t2, e2, { value: o2, enumerable: true, configurable: true, writable: true }) : t2[e2] = o2, t2;
  }
  var s;
  var i = {};
  i = (function() {
    var t2 = document, e2 = t2.createTextNode.bind(t2);
    function o2(t3, e3, o3) {
      t3.style.setProperty(e3, o3);
    }
    function s2(t3, e3) {
      return t3.appendChild(e3);
    }
    function i2(e3, o3, i3, n3) {
      var r3 = t2.createElement("span");
      return o3 && (r3.className = o3), i3 && (!n3 && r3.setAttribute("data-" + o3, i3), r3.textContent = i3), e3 && s2(e3, r3) || r3;
    }
    function n2(t3, e3) {
      return t3.getAttribute("data-" + e3);
    }
    function r2(e3, o3) {
      return e3 && 0 != e3.length ? e3.nodeName ? [e3] : [].slice.call(e3[0].nodeName ? e3 : (o3 || t2).querySelectorAll(e3)) : [];
    }
    function l2(t3) {
      for (var e3 = []; t3--; ) e3[t3] = [];
      return e3;
    }
    function c(t3, e3) {
      t3 && t3.some(e3);
    }
    function a(t3) {
      return function(e3) {
        return t3[e3];
      };
    }
    function h(t3, e3, s3) {
      var i3 = "--" + e3, n3 = i3 + "-index";
      c(s3, (function(t4, e4) {
        Array.isArray(t4) ? c(t4, (function(t5) {
          o2(t5, n3, e4);
        })) : o2(t4, n3, e4);
      })), o2(t3, i3 + "-total", s3.length);
    }
    var u = {};
    function f(t3, e3, o3) {
      var s3 = o3.indexOf(t3);
      if (-1 == s3) o3.unshift(t3), c(u[t3].depends, (function(e4) {
        f(e4, t3, o3);
      }));
      else {
        var i3 = o3.indexOf(e3);
        o3.splice(s3, 1), o3.splice(i3, 0, t3);
      }
      return o3;
    }
    function m(t3, e3, o3, s3) {
      return { by: t3, depends: e3, key: o3, split: s3 };
    }
    function d(t3) {
      return f(t3, 0, []).map(a(u));
    }
    function p(t3) {
      u[t3.by] = t3;
    }
    function g(t3, o3, n3, l3, a2) {
      t3.normalize();
      var h2 = [], u2 = document.createDocumentFragment();
      l3 && h2.push(t3.previousSibling);
      var f2 = [];
      return r2(t3.childNodes).some((function(t4) {
        if (!t4.tagName || t4.hasChildNodes()) {
          if (t4.childNodes && t4.childNodes.length) return f2.push(t4), void h2.push.apply(h2, g(t4, o3, n3, l3, a2));
          var s3 = t4.wholeText || "", r3 = s3.trim();
          r3.length && (" " === s3[0] && f2.push(e2(" ")), c(r3.split(n3), (function(t5, e3) {
            e3 && a2 && f2.push(i2(u2, "whitespace", " ", a2));
            var s4 = i2(u2, o3, t5);
            h2.push(s4), f2.push(s4);
          })), " " === s3[s3.length - 1] && f2.push(e2(" ")));
        } else f2.push(t4);
      })), c(f2, (function(t4) {
        s2(u2, t4);
      })), t3.innerHTML = "", s2(t3, u2), h2;
    }
    var v = 0;
    function C(t3, e3) {
      for (var o3 in e3) t3[o3] = e3[o3];
      return t3;
    }
    var M = "words", y = m(M, v, "word", (function(t3) {
      return g(t3, "word", /\s+/, 0, 1);
    })), b = "chars", x = m(b, [M], "char", (function(t3, e3, o3) {
      var s3 = [];
      return c(o3[M], (function(t4, o4) {
        s3.push.apply(s3, g(t4, "char", "", e3.whitespace && o4));
      })), s3;
    }));
    function T(t3) {
      var e3 = (t3 = t3 || {}).key;
      return r2(t3.target || "[data-splitting]").map((function(o3) {
        var s3 = o3["\u{1F34C}"];
        if (!t3.force && s3) return s3;
        s3 = o3["\u{1F34C}"] = { el: o3 };
        var i3 = d(t3.by || n2(o3, "splitting") || b), r3 = C({}, t3);
        return c(i3, (function(t4) {
          if (t4.split) {
            var i4 = t4.by, n3 = (e3 ? "-" + e3 : "") + t4.key, l3 = t4.split(o3, r3, s3);
            n3 && h(o3, n3, l3), s3[i4] = l3, o3.classList.add(i4);
          }
        })), o3.classList.add("splitting"), s3;
      }));
    }
    function w(t3) {
      var e3 = (t3 = t3 || {}).target = i2();
      return e3.innerHTML = t3.content, T(t3), e3.outerHTML;
    }
    function A(t3, e3, o3) {
      var s3 = r2(e3.matching || t3.children, t3), i3 = {};
      return c(s3, (function(t4) {
        var e4 = Math.round(t4[o3]);
        (i3[e4] || (i3[e4] = [])).push(t4);
      })), Object.keys(i3).map(Number).sort(O).map(a(i3));
    }
    function O(t3, e3) {
      return t3 - e3;
    }
    T.html = w, T.add = p;
    var D = m("lines", [M], "line", (function(t3, e3, o3) {
      return A(t3, { matching: o3[M] }, "offsetTop");
    })), P = m("items", v, "item", (function(t3, e3) {
      return r2(e3.matching || t3.children, t3);
    })), S = m("rows", v, "row", (function(t3, e3) {
      return A(t3, e3, "offsetTop");
    })), L = m("cols", v, "col", (function(t3, e3) {
      return A(t3, e3, "offsetLeft");
    })), N = m("grid", ["rows", "cols"]), R = "layout", k = m(R, v, v, (function(t3, e3) {
      var l3 = e3.rows = +(e3.rows || n2(t3, "rows") || 1), c2 = e3.columns = +(e3.columns || n2(t3, "columns") || 1);
      if (e3.image = e3.image || n2(t3, "image") || t3.currentSrc || t3.src, e3.image) {
        var a2 = r2("img", t3)[0];
        e3.image = a2 && (a2.currentSrc || a2.src);
      }
      e3.image && o2(t3, "background-image", "url(" + e3.image + ")");
      for (var h2 = l3 * c2, u2 = [], f2 = i2(v, "cell-grid"); h2--; ) {
        var m2 = i2(f2, "cell");
        i2(m2, "cell-inner"), u2.push(m2);
      }
      return s2(t3, f2), u2;
    })), E = m("cellRows", [R], "row", (function(t3, e3, o3) {
      var s3 = e3.rows, i3 = l2(s3);
      return c(o3[R], (function(t4, e4, o4) {
        i3[Math.floor(e4 / (o4.length / s3))].push(t4);
      })), i3;
    })), H = m("cellColumns", [R], "col", (function(t3, e3, o3) {
      var s3 = e3.columns, i3 = l2(s3);
      return c(o3[R], (function(t4, e4) {
        i3[e4 % s3].push(t4);
      })), i3;
    })), q = m("cells", ["cellRows", "cellColumns"], "cell", (function(t3, e3, o3) {
      return o3[R];
    }));
    return p(y), p(x), p(D), p(P), p(S), p(L), p(N), p(k), p(E), p(H), p(q), T;
  })();
  var n = class {
    constructor(t2) {
      o(this, "position", -1), o(this, "cells", []), this.position = t2;
    }
  };
  var r = class {
    set(t2) {
      this.state = t2, this.DOM.el.innerHTML = this.state;
    }
    constructor(t2, { position: e2, previousCellPosition: s2 } = {}) {
      o(this, "DOM", { el: null }), o(this, "position", -1), o(this, "previousCellPosition", -1), o(this, "original", void 0), o(this, "state", void 0), o(this, "color", void 0), o(this, "originalColor", void 0), o(this, "cache", void 0), this.DOM.el = t2, this.original = this.DOM.el.innerHTML, this.state = this.original, this.color = this.originalColor = getComputedStyle(document.documentElement).getPropertyValue("--color-text"), this.position = e2, this.previousCellPosition = s2;
    }
  };
  var l = class {
    clearCells() {
      for (const t2 of this.lines) for (const e2 of t2.cells) e2.set("&nbsp;");
    }
    getRandomChar() {
      return this.lettersAndSymbols[Math.floor(__hf.random() * this.lettersAndSymbols.length)];
    }
    fx1() {
      let t2 = 0;
      this.clearCells();
      const e2 = (o2, s2, i2 = 0) => {
        s2.cache = s2.state, 44 === i2 ? (s2.set(s2.original), ++t2, t2 === this.totalChars && (this.isAnimating = false)) : 0 === s2.position ? s2.set(i2 < 9 ? ["*", "-", "'", '"'][Math.floor(4 * __hf.random())] : this.getRandomChar()) : s2.set(o2.cells[s2.previousCellPosition].cache), "&nbsp;" != s2.cache && ++i2, i2 < 45 && __hf.setTimeout((() => e2(o2, s2, i2)), 15);
      };
      for (const t3 of this.lines) for (const o2 of t3.cells) __hf.setTimeout((() => e2(t3, o2)), 200 * (t3.position + 1));
    }
    fx2() {
      let t2 = 0;
      const e2 = (o2, s2, i2 = 0) => {
        19 === i2 ? (s2.set(s2.original), s2.DOM.el.style.opacity = 0, __hf.setTimeout((() => {
          s2.DOM.el.style.opacity = 1;
        }), 300), ++t2, t2 === this.totalChars && (this.isAnimating = false)) : s2.set(this.getRandomChar()), ++i2 < 20 && __hf.setTimeout((() => e2(o2, s2, i2)), 40);
      };
      for (const t3 of this.lines) for (const o2 of t3.cells) __hf.setTimeout((() => e2(t3, o2)), 30 * (o2.position + 1));
    }
    fx3() {
      let t2 = 0;
      this.clearCells();
      const o2 = (e2, s2, i2 = 0) => {
        9 === i2 ? (s2.set(s2.original), ++t2, t2 === this.totalChars && (this.isAnimating = false)) : s2.set(this.getRandomChar()), ++i2 < 10 && __hf.setTimeout((() => o2(e2, s2, i2)), 80);
      };
      for (const t3 of this.lines) for (const s2 of t3.cells) __hf.setTimeout((() => o2(t3, s2)), e(0, 2e3));
    }
    fx4() {
      let t2 = 0;
      this.clearCells();
      const e2 = (o2, s2, i2 = 0) => {
        s2.cache = s2.state, 29 === i2 ? (s2.set(s2.original), ++t2, t2 === this.totalChars && (this.isAnimating = false)) : 0 === s2.position ? s2.set(["*", ":"][Math.floor(2 * __hf.random())]) : s2.set(o2.cells[s2.previousCellPosition].cache), "&nbsp;" != s2.cache && ++i2, i2 < 30 && __hf.setTimeout((() => e2(o2, s2, i2)), 15);
      };
      for (const t3 of this.lines) for (const o2 of t3.cells) __hf.setTimeout((() => e2(t3, o2)), 400 * Math.abs(this.lines.length / 2 - t3.position));
    }
    fx5() {
      let t2 = 0;
      this.clearCells();
      const e2 = (o2, s2, i2 = 0) => {
        s2.cache = { state: s2.state, color: s2.color }, 29 === i2 ? (s2.color = s2.originalColor, s2.DOM.el.style.color = s2.color, s2.set(s2.original), ++t2, t2 === this.totalChars && (this.isAnimating = false)) : 0 === s2.position ? (s2.color = ["#3e775d", "#61dca3", "#61b3dc"][Math.floor(3 * __hf.random())], s2.DOM.el.style.color = s2.color, s2.set(i2 < 9 ? ["*", "-", "'", '"'][Math.floor(4 * __hf.random())] : this.getRandomChar())) : (s2.set(o2.cells[s2.previousCellPosition].cache.state), s2.color = o2.cells[s2.previousCellPosition].cache.color, s2.DOM.el.style.color = s2.color), "&nbsp;" != s2.cache.state && ++i2, i2 < 30 && __hf.setTimeout((() => e2(o2, s2, i2)), 10);
      };
      for (const t3 of this.lines) for (const o2 of t3.cells) __hf.setTimeout((() => e2(t3, o2)), 200 * (t3.position + 1));
    }
    fx6() {
      let t2 = 0;
      const o2 = (s2, i2, n2 = 0) => {
        i2.cache = { state: i2.state, color: i2.color }, 14 === n2 ? (i2.set(i2.original), i2.color = i2.originalColor, i2.DOM.el.style.color = i2.color, ++t2, t2 === this.totalChars && (this.isAnimating = false)) : (i2.set(this.getRandomChar()), i2.color = ["#2b4539", "#61dca3", "#61b3dc"][Math.floor(3 * __hf.random())], i2.DOM.el.style.color = i2.color), ++n2 < 15 && __hf.setTimeout((() => o2(s2, i2, n2)), e(30, 110));
      };
      for (const t3 of this.lines) for (const e2 of t3.cells) __hf.setTimeout((() => o2(t3, e2)), 80 * (t3.position + 1));
    }
    trigger(t2 = "fx1") {
      t2 in this.effects && !this.isAnimating && (this.isAnimating = true, this.effects[t2]());
    }
    constructor(e2) {
      o(this, "DOM", { el: null }), o(this, "lines", []), o(this, "lettersAndSymbols", ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "!", "@", "#", "$", "&", "*", "(", ")", "-", "_", "+", "=", "/", "[", "]", "{", "}", ";", ":", "<", ">", ",", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]), o(this, "effects", { fx1: () => this.fx1(), fx2: () => this.fx2(), fx3: () => this.fx3(), fx4: () => this.fx4(), fx5: () => this.fx5(), fx6: () => this.fx6() }), o(this, "totalChars", 0), this.DOM.el = e2;
      const s2 = t(i)({ target: this.DOM.el, by: "lines" });
      s2.forEach(((e3) => t(i)({ target: e3.words })));
      for (const [t2, e3] of s2[0].lines.entries()) {
        const o2 = new n(t2);
        let s3 = [], i2 = 0;
        for (const t3 of e3) for (const e4 of [...t3.querySelectorAll(".char")]) s3.push(new r(e4, { position: i2, previousCellPosition: 0 === i2 ? -1 : i2 - 1 })), ++i2;
        o2.cells = s3, this.lines.push(o2), this.totalChars += i2;
      }
    }
  };
  (s = "biu0hfr", new Promise(((t2) => {
    WebFont.load({ typekit: { id: s }, active: t2 });
  }))).then((() => {
    document.body.classList.remove("loading");
    const t2 = document.querySelector(".content"), e2 = new l(t2);
    e2.trigger("fx1"), [...document.querySelectorAll(".effects > button")].forEach(((t3) => {
      t3.addEventListener("click", (() => {
        e2.trigger(`fx${t3.dataset.fx}`);
      }));
    }));
  }));
})();
;
!function(){function t(t){return t&&t.__esModule?t.default:t}const e=(t,e)=>Math.floor(__hf.random()*(e-t+1))+t;function o(t,e,o){return e in t?Object.defineProperty(t,e,{value:o,enumerable:!0,configurable:!0,writable:!0}):t[e]=o,t}var s,i={};i=function(){"use strict";var t=document,e=t.createTextNode.bind(t);function o(t,e,o){t.style.setProperty(e,o)}function s(t,e){return t.appendChild(e)}function i(e,o,i,n){var r=t.createElement("span");return o&&(r.className=o),i&&(!n&&r.setAttribute("data-"+o,i),r.textContent=i),e&&s(e,r)||r}function n(t,e){return t.getAttribute("data-"+e)}function r(e,o){return e&&0!=e.length?e.nodeName?[e]:[].slice.call(e[0].nodeName?e:(o||t).querySelectorAll(e)):[]}function l(t){for(var e=[];t--;)e[t]=[];return e}function c(t,e){t&&t.some(e)}function a(t){return function(e){return t[e]}}function h(t,e,s){var i="--"+e,n=i+"-index";c(s,(function(t,e){Array.isArray(t)?c(t,(function(t){o(t,n,e)})):o(t,n,e)})),o(t,i+"-total",s.length)}var u={};function f(t,e,o){var s=o.indexOf(t);if(-1==s)o.unshift(t),c(u[t].depends,(function(e){f(e,t,o)}));else{var i=o.indexOf(e);o.splice(s,1),o.splice(i,0,t)}return o}function m(t,e,o,s){return{by:t,depends:e,key:o,split:s}}function d(t){return f(t,0,[]).map(a(u))}function p(t){u[t.by]=t}function g(t,o,n,l,a){t.normalize();var h=[],u=document.createDocumentFragment();l&&h.push(t.previousSibling);var f=[];return r(t.childNodes).some((function(t){if(!t.tagName||t.hasChildNodes()){if(t.childNodes&&t.childNodes.length)return f.push(t),void h.push.apply(h,g(t,o,n,l,a));var s=t.wholeText||"",r=s.trim();r.length&&(" "===s[0]&&f.push(e(" ")),c(r.split(n),(function(t,e){e&&a&&f.push(i(u,"whitespace"," ",a));var s=i(u,o,t);h.push(s),f.push(s)}))," "===s[s.length-1]&&f.push(e(" ")))}else f.push(t)})),c(f,(function(t){s(u,t)})),t.innerHTML="",s(t,u),h}var v=0;function C(t,e){for(var o in e)t[o]=e[o];return t}var M="words",y=m(M,v,"word",(function(t){return g(t,"word",/\s+/,0,1)})),b="chars",x=m(b,[M],"char",(function(t,e,o){var s=[];return c(o[M],(function(t,o){s.push.apply(s,g(t,"char","",e.whitespace&&o))})),s}));function T(t){var e=(t=t||{}).key;return r(t.target||"[data-splitting]").map((function(o){var s=o["🍌"];if(!t.force&&s)return s;s=o["🍌"]={el:o};var i=d(t.by||n(o,"splitting")||b),r=C({},t);return c(i,(function(t){if(t.split){var i=t.by,n=(e?"-"+e:"")+t.key,l=t.split(o,r,s);n&&h(o,n,l),s[i]=l,o.classList.add(i)}})),o.classList.add("splitting"),s}))}function w(t){var e=(t=t||{}).target=i();return e.innerHTML=t.content,T(t),e.outerHTML}function A(t,e,o){var s=r(e.matching||t.children,t),i={};return c(s,(function(t){var e=Math.round(t[o]);(i[e]||(i[e]=[])).push(t)})),Object.keys(i).map(Number).sort(O).map(a(i))}function O(t,e){return t-e}T.html=w,T.add=p;var D=m("lines",[M],"line",(function(t,e,o){return A(t,{matching:o[M]},"offsetTop")})),P=m("items",v,"item",(function(t,e){return r(e.matching||t.children,t)})),S=m("rows",v,"row",(function(t,e){return A(t,e,"offsetTop")})),L=m("cols",v,"col",(function(t,e){return A(t,e,"offsetLeft")})),N=m("grid",["rows","cols"]),R="layout",k=m(R,v,v,(function(t,e){var l=e.rows=+(e.rows||n(t,"rows")||1),c=e.columns=+(e.columns||n(t,"columns")||1);if(e.image=e.image||n(t,"image")||t.currentSrc||t.src,e.image){var a=r("img",t)[0];e.image=a&&(a.currentSrc||a.src)}e.image&&o(t,"background-image","url("+e.image+")");for(var h=l*c,u=[],f=i(v,"cell-grid");h--;){var m=i(f,"cell");i(m,"cell-inner"),u.push(m)}return s(t,f),u})),E=m("cellRows",[R],"row",(function(t,e,o){var s=e.rows,i=l(s);return c(o[R],(function(t,e,o){i[Math.floor(e/(o.length/s))].push(t)})),i})),H=m("cellColumns",[R],"col",(function(t,e,o){var s=e.columns,i=l(s);return c(o[R],(function(t,e){i[e%s].push(t)})),i})),q=m("cells",["cellRows","cellColumns"],"cell",(function(t,e,o){return o[R]}));return p(y),p(x),p(D),p(P),p(S),p(L),p(N),p(k),p(E),p(H),p(q),T}();class n{constructor(t){o(this,"position",-1),o(this,"cells",[]),this.position=t}}class r{set(t){this.state=t,this.DOM.el.innerHTML=this.state}constructor(t,{position:e,previousCellPosition:s}={}){o(this,"DOM",{el:null}),o(this,"position",-1),o(this,"previousCellPosition",-1),o(this,"original",void 0),o(this,"state",void 0),o(this,"color",void 0),o(this,"originalColor",void 0),o(this,"cache",void 0),this.DOM.el=t,this.original=this.DOM.el.innerHTML,this.state=this.original,this.color=this.originalColor=getComputedStyle(document.documentElement).getPropertyValue("--color-text"),this.position=e,this.previousCellPosition=s}}class l{clearCells(){for(const t of this.lines)for(const e of t.cells)e.set("&nbsp;")}getRandomChar(){return this.lettersAndSymbols[Math.floor(__hf.random()*this.lettersAndSymbols.length)]}fx1(){let t=0;this.clearCells();const e=(o,s,i=0)=>{s.cache=s.state,44===i?(s.set(s.original),++t,t===this.totalChars&&(this.isAnimating=!1)):0===s.position?s.set(i<9?["*","-","'",'"'][Math.floor(4*__hf.random())]:this.getRandomChar()):s.set(o.cells[s.previousCellPosition].cache),"&nbsp;"!=s.cache&&++i,i<45&&__hf.setTimeout((()=>e(o,s,i)),15)};for(const t of this.lines)for(const o of t.cells)__hf.setTimeout((()=>e(t,o)),200*(t.position+1))}fx2(){let t=0;const e=(o,s,i=0)=>{19===i?(s.set(s.original),s.DOM.el.style.opacity=0,__hf.setTimeout((()=>{s.DOM.el.style.opacity=1}),300),++t,t===this.totalChars&&(this.isAnimating=!1)):s.set(this.getRandomChar()),++i<20&&__hf.setTimeout((()=>e(o,s,i)),40)};for(const t of this.lines)for(const o of t.cells)__hf.setTimeout((()=>e(t,o)),30*(o.position+1))}fx3(){let t=0;this.clearCells();const o=(e,s,i=0)=>{9===i?(s.set(s.original),++t,t===this.totalChars&&(this.isAnimating=!1)):s.set(this.getRandomChar()),++i<10&&__hf.setTimeout((()=>o(e,s,i)),80)};for(const t of this.lines)for(const s of t.cells)__hf.setTimeout((()=>o(t,s)),e(0,2e3))}fx4(){let t=0;this.clearCells();const e=(o,s,i=0)=>{s.cache=s.state,29===i?(s.set(s.original),++t,t===this.totalChars&&(this.isAnimating=!1)):0===s.position?s.set(["*",":"][Math.floor(2*__hf.random())]):s.set(o.cells[s.previousCellPosition].cache),"&nbsp;"!=s.cache&&++i,i<30&&__hf.setTimeout((()=>e(o,s,i)),15)};for(const t of this.lines)for(const o of t.cells)__hf.setTimeout((()=>e(t,o)),400*Math.abs(this.lines.length/2-t.position))}fx5(){let t=0;this.clearCells();const e=(o,s,i=0)=>{s.cache={state:s.state,color:s.color},29===i?(s.color=s.originalColor,s.DOM.el.style.color=s.color,s.set(s.original),++t,t===this.totalChars&&(this.isAnimating=!1)):0===s.position?(s.color=["#3e775d","#61dca3","#61b3dc"][Math.floor(3*__hf.random())],s.DOM.el.style.color=s.color,s.set(i<9?["*","-","'",'"'][Math.floor(4*__hf.random())]:this.getRandomChar())):(s.set(o.cells[s.previousCellPosition].cache.state),s.color=o.cells[s.previousCellPosition].cache.color,s.DOM.el.style.color=s.color),"&nbsp;"!=s.cache.state&&++i,i<30&&__hf.setTimeout((()=>e(o,s,i)),10)};for(const t of this.lines)for(const o of t.cells)__hf.setTimeout((()=>e(t,o)),200*(t.position+1))}fx6(){let t=0;const o=(s,i,n=0)=>{i.cache={state:i.state,color:i.color},14===n?(i.set(i.original),i.color=i.originalColor,i.DOM.el.style.color=i.color,++t,t===this.totalChars&&(this.isAnimating=!1)):(i.set(this.getRandomChar()),i.color=["#2b4539","#61dca3","#61b3dc"][Math.floor(3*__hf.random())],i.DOM.el.style.color=i.color),++n<15&&__hf.setTimeout((()=>o(s,i,n)),e(30,110))};for(const t of this.lines)for(const e of t.cells)__hf.setTimeout((()=>o(t,e)),80*(t.position+1))}trigger(t="fx1"){t in this.effects&&!this.isAnimating&&(this.isAnimating=!0,this.effects[t]())}constructor(e){o(this,"DOM",{el:null}),o(this,"lines",[]),o(this,"lettersAndSymbols",["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","!","@","#","$","&","*","(",")","-","_","+","=","/","[","]","{","}",";",":","<",">",",","0","1","2","3","4","5","6","7","8","9"]),o(this,"effects",{fx1:()=>this.fx1(),fx2:()=>this.fx2(),fx3:()=>this.fx3(),fx4:()=>this.fx4(),fx5:()=>this.fx5(),fx6:()=>this.fx6()}),o(this,"totalChars",0),this.DOM.el=e;const s=t(i)({target:this.DOM.el,by:"lines"});s.forEach((e=>t(i)({target:e.words})));for(const[t,e]of s[0].lines.entries()){const o=new n(t);let s=[],i=0;for(const t of e)for(const e of[...t.querySelectorAll(".char")])s.push(new r(e,{position:i,previousCellPosition:0===i?-1:i-1})),++i;o.cells=s,this.lines.push(o),this.totalChars+=i}}}(s="biu0hfr",new Promise((t=>{WebFont.load({typekit:{id:s},active:t})}))).then((()=>{document.body.classList.remove("loading");const t=document.querySelector(".content"),e=new l(t);e.trigger("fx1"),[...document.querySelectorAll(".effects > button")].forEach((t=>{t.addEventListener("click",(()=>{e.trigger(`fx${t.dataset.fx}`)}))}))}))}();
}
];
