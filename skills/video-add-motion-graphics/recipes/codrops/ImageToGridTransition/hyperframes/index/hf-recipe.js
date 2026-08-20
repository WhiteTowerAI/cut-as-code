/* Generated from the original Codrops entry scripts. */
window.__hfRecipeFactories = [
function (__hf) {
delete globalThis.parcelRequirec455;
document.documentElement.className="js";var supportsCssVars=function(){var e,t=document.createElement("style");return t.innerHTML="root: { --tmp-var: bold; }",document.head.appendChild(t),e=!!(window.CSS&&window.CSS.supports&&window.CSS.supports("font-weight","var(--tmp-var)")),t.parentNode.removeChild(t),e};supportsCssVars()||alert("Please view this demo in a modern browser that supports CSS Variables.");;
(() => {
  // index.e9a2d1b4.js
  var t = "undefined" != typeof globalThis ? globalThis : "undefined" != typeof self ? self : "undefined" != typeof window ? window : "undefined" != typeof global ? global : {};
  var e = {};
  var i = {};
  var n = t.parcelRequirec455;
  null == n && ((n = function(t21) {
    if (t21 in e) return e[t21].exports;
    if (t21 in i) {
      var n2 = i[t21];
      delete i[t21];
      var r2 = { id: t21, exports: {} };
      return e[t21] = r2, n2.call(r2.exports, r2, r2.exports), r2.exports;
    }
    var s2 = new Error("Cannot find module '" + t21 + "'");
    throw s2.code = "MODULE_NOT_FOUND", s2;
  }).register = function(t21, e2) {
    i[t21] = e2;
  }, t.parcelRequirec455 = n), n.register("4hJWI", (function(t21, e2) {
    !(function(e3, i2) {
      t21.exports ? t21.exports = i2() : e3.EvEmitter = i2();
    })("undefined" != typeof window ? window : t21.exports, (function() {
      function t22() {
      }
      let e3 = t22.prototype;
      return e3.on = function(t23, e4) {
        if (!t23 || !e4) return this;
        let i2 = this._events = this._events || {}, n2 = i2[t23] = i2[t23] || [];
        return n2.includes(e4) || n2.push(e4), this;
      }, e3.once = function(t23, e4) {
        if (!t23 || !e4) return this;
        this.on(t23, e4);
        let i2 = this._onceEvents = this._onceEvents || {};
        return (i2[t23] = i2[t23] || {})[e4] = true, this;
      }, e3.off = function(t23, e4) {
        let i2 = this._events && this._events[t23];
        if (!i2 || !i2.length) return this;
        let n2 = i2.indexOf(e4);
        return -1 != n2 && i2.splice(n2, 1), this;
      }, e3.emitEvent = function(t23, e4) {
        let i2 = this._events && this._events[t23];
        if (!i2 || !i2.length) return this;
        i2 = i2.slice(0), e4 = e4 || [];
        let n2 = this._onceEvents && this._onceEvents[t23];
        for (let r2 of i2) {
          n2 && n2[r2] && (this.off(t23, r2), delete n2[r2]), r2.apply(this, e4);
        }
        return this;
      }, e3.allOff = function() {
        return delete this._events, delete this._onceEvents, this;
      }, t22;
    }));
  }));
  var r = {};
  !(function(t21, e2) {
    r ? r = e2(t21, n("4hJWI")) : t21.imagesLoaded = e2(t21, t21.EvEmitter);
  })("undefined" != typeof window ? window : r, (function(t21, e2) {
    let i2 = t21.jQuery, n2 = t21.console;
    function r2(t22, e3, s3) {
      if (!(this instanceof r2)) return new r2(t22, e3, s3);
      let a3 = t22;
      var o3;
      ("string" == typeof t22 && (a3 = document.querySelectorAll(t22)), a3) ? (this.elements = (o3 = a3, Array.isArray(o3) ? o3 : "object" == typeof o3 && "number" == typeof o3.length ? [...o3] : [o3]), this.options = {}, "function" == typeof e3 ? s3 = e3 : Object.assign(this.options, e3), s3 && this.on("always", s3), this.getImages(), i2 && (this.jqDeferred = new i2.Deferred()), __hf.setTimeout(this.check.bind(this))) : n2.error(`Bad element for imagesLoaded ${a3 || t22}`);
    }
    r2.prototype = Object.create(e2.prototype), r2.prototype.getImages = function() {
      this.images = [], this.elements.forEach(this.addElementImages, this);
    };
    const s2 = [1, 9, 11];
    r2.prototype.addElementImages = function(t22) {
      "IMG" === t22.nodeName && this.addImage(t22), true === this.options.background && this.addElementBackgroundImages(t22);
      let { nodeType: e3 } = t22;
      if (!e3 || !s2.includes(e3)) return;
      let i3 = t22.querySelectorAll("img");
      for (let t23 of i3) this.addImage(t23);
      if ("string" == typeof this.options.background) {
        let e4 = t22.querySelectorAll(this.options.background);
        for (let t23 of e4) this.addElementBackgroundImages(t23);
      }
    };
    const a2 = /url\((['"])?(.*?)\1\)/gi;
    function o2(t22) {
      this.img = t22;
    }
    function u2(t22, e3) {
      this.url = t22, this.element = e3, this.img = new Image();
    }
    return r2.prototype.addElementBackgroundImages = function(t22) {
      let e3 = getComputedStyle(t22);
      if (!e3) return;
      let i3 = a2.exec(e3.backgroundImage);
      for (; null !== i3; ) {
        let n3 = i3 && i3[2];
        n3 && this.addBackground(n3, t22), i3 = a2.exec(e3.backgroundImage);
      }
    }, r2.prototype.addImage = function(t22) {
      let e3 = new o2(t22);
      this.images.push(e3);
    }, r2.prototype.addBackground = function(t22, e3) {
      let i3 = new u2(t22, e3);
      this.images.push(i3);
    }, r2.prototype.check = function() {
      if (this.progressedCount = 0, this.hasAnyBroken = false, !this.images.length) return void this.complete();
      let t22 = (t23, e3, i3) => {
        __hf.setTimeout((() => {
          this.progress(t23, e3, i3);
        }));
      };
      this.images.forEach((function(e3) {
        e3.once("progress", t22), e3.check();
      }));
    }, r2.prototype.progress = function(t22, e3, i3) {
      this.progressedCount++, this.hasAnyBroken = this.hasAnyBroken || !t22.isLoaded, this.emitEvent("progress", [this, t22, e3]), this.jqDeferred && this.jqDeferred.notify && this.jqDeferred.notify(this, t22), this.progressedCount === this.images.length && this.complete(), this.options.debug && n2 && n2.log(`progress: ${i3}`, t22, e3);
    }, r2.prototype.complete = function() {
      let t22 = this.hasAnyBroken ? "fail" : "done";
      if (this.isComplete = true, this.emitEvent(t22, [this]), this.emitEvent("always", [this]), this.jqDeferred) {
        let t23 = this.hasAnyBroken ? "reject" : "resolve";
        this.jqDeferred[t23](this);
      }
    }, o2.prototype = Object.create(e2.prototype), o2.prototype.check = function() {
      this.getIsImageComplete() ? this.confirm(0 !== this.img.naturalWidth, "naturalWidth") : (this.proxyImage = new Image(), this.img.crossOrigin && (this.proxyImage.crossOrigin = this.img.crossOrigin), this.proxyImage.addEventListener("load", this), this.proxyImage.addEventListener("error", this), this.img.addEventListener("load", this), this.img.addEventListener("error", this), this.proxyImage.src = this.img.currentSrc || this.img.src);
    }, o2.prototype.getIsImageComplete = function() {
      return this.img.complete && this.img.naturalWidth;
    }, o2.prototype.confirm = function(t22, e3) {
      this.isLoaded = t22;
      let { parentNode: i3 } = this.img, n3 = "PICTURE" === i3.nodeName ? i3 : this.img;
      this.emitEvent("progress", [this, n3, e3]);
    }, o2.prototype.handleEvent = function(t22) {
      let e3 = "on" + t22.type;
      this[e3] && this[e3](t22);
    }, o2.prototype.onload = function() {
      this.confirm(true, "onload"), this.unbindEvents();
    }, o2.prototype.onerror = function() {
      this.confirm(false, "onerror"), this.unbindEvents();
    }, o2.prototype.unbindEvents = function() {
      this.proxyImage.removeEventListener("load", this), this.proxyImage.removeEventListener("error", this), this.img.removeEventListener("load", this), this.img.removeEventListener("error", this);
    }, u2.prototype = Object.create(o2.prototype), u2.prototype.check = function() {
      this.img.addEventListener("load", this), this.img.addEventListener("error", this), this.img.src = this.url, this.getIsImageComplete() && (this.confirm(0 !== this.img.naturalWidth, "naturalWidth"), this.unbindEvents());
    }, u2.prototype.unbindEvents = function() {
      this.img.removeEventListener("load", this), this.img.removeEventListener("error", this);
    }, u2.prototype.confirm = function(t22, e3) {
      this.isLoaded = t22, this.emitEvent("progress", [this, this.element, e3]);
    }, r2.makeJQueryPlugin = function(e3) {
      (e3 = e3 || t21.jQuery) && (i2 = e3, i2.fn.imagesLoaded = function(t22, e4) {
        return new r2(this, t22, e4).jqDeferred.promise(i2(this));
      });
    }, r2.makeJQueryPlugin(), r2;
  }));
  var s = (t21, e2, i2, n2, r2) => (t21 - e2) * (r2 - n2) / (i2 - e2) + n2;
  function a(t21) {
    if (void 0 === t21) throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
    return t21;
  }
  function o(t21, e2) {
    t21.prototype = Object.create(e2.prototype), t21.prototype.constructor = t21, t21.__proto__ = e2;
  }
  var u;
  var h;
  var l;
  var f;
  var c;
  var p;
  var d;
  var m;
  var g;
  var _;
  var v;
  var y;
  var x;
  var b;
  var w;
  var T;
  var k;
  var C;
  var S;
  var O;
  var E;
  var M;
  var A;
  var P;
  var I;
  var D;
  var L;
  var B;
  var R = { autoSleep: 120, force3D: "auto", nullTargetWarn: 1, units: { lineHeight: "" } };
  var z = { duration: 0.5, overwrite: false, delay: 0 };
  var F = 2 * Math.PI;
  var V = F / 4;
  var N = 0;
  var q = Math.sqrt;
  var X = Math.cos;
  var Y = Math.sin;
  var j = function(t21) {
    return "string" == typeof t21;
  };
  var U = function(t21) {
    return "function" == typeof t21;
  };
  var W = function(t21) {
    return "number" == typeof t21;
  };
  var H = function(t21) {
    return void 0 === t21;
  };
  var Q = function(t21) {
    return "object" == typeof t21;
  };
  var G = function(t21) {
    return false !== t21;
  };
  var $ = function() {
    return "undefined" != typeof window;
  };
  var J = function(t21) {
    return U(t21) || j(t21);
  };
  var Z = "function" == typeof ArrayBuffer && ArrayBuffer.isView || function() {
  };
  var K = Array.isArray;
  var tt = /(?:-?\.?\d|\.)+/gi;
  var et = /[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/g;
  var it = /[-+=.]*\d+[.e-]*\d*[a-z%]*/g;
  var nt = /[-+=.]*\d+\.?\d*(?:e-|e\+)?\d*/gi;
  var rt = /[+-]=-?[.\d]+/;
  var st = /[^,'"\[\]\s]+/gi;
  var at = /^[+\-=e\s\d]*\d+[.\d]*([a-z]*|%)\s*$/i;
  var ot = {};
  var ut = {};
  var ht = function(t21) {
    return (ut = Bt(t21, ot)) && ki;
  };
  var lt = function(t21, e2) {
    return console.warn("Invalid property", t21, "set to", e2, "Missing plugin? gsap.registerPlugin()");
  };
  var ft = function(t21, e2) {
    return !e2 && console.warn(t21);
  };
  var ct = function(t21, e2) {
    return t21 && (ot[t21] = e2) && ut && (ut[t21] = e2) || ot;
  };
  var pt = function() {
    return 0;
  };
  var dt = {};
  var mt = [];
  var gt = {};
  var _t = {};
  var vt = {};
  var yt = 30;
  var xt = [];
  var bt = "";
  var wt = function(t21) {
    var e2, i2, n2 = t21[0];
    if (Q(n2) || U(n2) || (t21 = [t21]), !(e2 = (n2._gsap || {}).harness)) {
      for (i2 = xt.length; i2-- && !xt[i2].targetTest(n2); ) ;
      e2 = xt[i2];
    }
    for (i2 = t21.length; i2--; ) t21[i2] && (t21[i2]._gsap || (t21[i2]._gsap = new He(t21[i2], e2))) || t21.splice(i2, 1);
    return t21;
  };
  var Tt = function(t21) {
    return t21._gsap || wt(pe(t21))[0]._gsap;
  };
  var kt = function(t21, e2, i2) {
    return (i2 = t21[e2]) && U(i2) ? t21[e2]() : H(i2) && t21.getAttribute && t21.getAttribute(e2) || i2;
  };
  var Ct = function(t21, e2) {
    return (t21 = t21.split(",")).forEach(e2) || t21;
  };
  var St = function(t21) {
    return Math.round(1e5 * t21) / 1e5 || 0;
  };
  var Ot = function(t21) {
    return Math.round(1e7 * t21) / 1e7 || 0;
  };
  var Et = function(t21, e2) {
    var i2 = e2.charAt(0), n2 = parseFloat(e2.substr(2));
    return t21 = parseFloat(t21), "+" === i2 ? t21 + n2 : "-" === i2 ? t21 - n2 : "*" === i2 ? t21 * n2 : t21 / n2;
  };
  var Mt = function(t21, e2) {
    for (var i2 = e2.length, n2 = 0; t21.indexOf(e2[n2]) < 0 && ++n2 < i2; ) ;
    return n2 < i2;
  };
  var At = function() {
    var t21, e2, i2 = mt.length, n2 = mt.slice(0);
    for (gt = {}, mt.length = 0, t21 = 0; t21 < i2; t21++) (e2 = n2[t21]) && e2._lazy && (e2.render(e2._lazy[0], e2._lazy[1], true)._lazy = 0);
  };
  var Pt = function(t21, e2, i2, n2) {
    mt.length && At(), t21.render(e2, i2, n2), mt.length && At();
  };
  var It = function(t21) {
    var e2 = parseFloat(t21);
    return (e2 || 0 === e2) && (t21 + "").match(st).length < 2 ? e2 : j(t21) ? t21.trim() : t21;
  };
  var Dt = function(t21) {
    return t21;
  };
  var Lt = function(t21, e2) {
    for (var i2 in e2) i2 in t21 || (t21[i2] = e2[i2]);
    return t21;
  };
  var Bt = function(t21, e2) {
    for (var i2 in e2) t21[i2] = e2[i2];
    return t21;
  };
  var Rt = function t2(e2, i2) {
    for (var n2 in i2) "__proto__" !== n2 && "constructor" !== n2 && "prototype" !== n2 && (e2[n2] = Q(i2[n2]) ? t2(e2[n2] || (e2[n2] = {}), i2[n2]) : i2[n2]);
    return e2;
  };
  var zt = function(t21, e2) {
    var i2, n2 = {};
    for (i2 in t21) i2 in e2 || (n2[i2] = t21[i2]);
    return n2;
  };
  var Ft = function(t21) {
    var e2, i2 = t21.parent || h, n2 = t21.keyframes ? (e2 = K(t21.keyframes), function(t22, i3) {
      for (var n3 in i3) n3 in t22 || "duration" === n3 && e2 || "ease" === n3 || (t22[n3] = i3[n3]);
    }) : Lt;
    if (G(t21.inherit)) for (; i2; ) n2(t21, i2.vars.defaults), i2 = i2.parent || i2._dp;
    return t21;
  };
  var Vt = function(t21, e2, i2, n2, r2) {
    void 0 === i2 && (i2 = "_first"), void 0 === n2 && (n2 = "_last");
    var s2, a2 = t21[n2];
    if (r2) for (s2 = e2[r2]; a2 && a2[r2] > s2; ) a2 = a2._prev;
    return a2 ? (e2._next = a2._next, a2._next = e2) : (e2._next = t21[i2], t21[i2] = e2), e2._next ? e2._next._prev = e2 : t21[n2] = e2, e2._prev = a2, e2.parent = e2._dp = t21, e2;
  };
  var Nt = function(t21, e2, i2, n2) {
    void 0 === i2 && (i2 = "_first"), void 0 === n2 && (n2 = "_last");
    var r2 = e2._prev, s2 = e2._next;
    r2 ? r2._next = s2 : t21[i2] === e2 && (t21[i2] = s2), s2 ? s2._prev = r2 : t21[n2] === e2 && (t21[n2] = r2), e2._next = e2._prev = e2.parent = null;
  };
  var qt = function(t21, e2) {
    t21.parent && (!e2 || t21.parent.autoRemoveChildren) && t21.parent.remove(t21), t21._act = 0;
  };
  var Xt = function(t21, e2) {
    if (t21 && (!e2 || e2._end > t21._dur || e2._start < 0)) for (var i2 = t21; i2; ) i2._dirty = 1, i2 = i2.parent;
    return t21;
  };
  var Yt = function(t21) {
    for (var e2 = t21.parent; e2 && e2.parent; ) e2._dirty = 1, e2.totalDuration(), e2 = e2.parent;
    return t21;
  };
  var jt = function t3(e2) {
    return !e2 || e2._ts && t3(e2.parent);
  };
  var Ut = function(t21) {
    return t21._repeat ? Wt(t21._tTime, t21 = t21.duration() + t21._rDelay) * t21 : 0;
  };
  var Wt = function(t21, e2) {
    var i2 = Math.floor(t21 /= e2);
    return t21 && i2 === t21 ? i2 - 1 : i2;
  };
  var Ht = function(t21, e2) {
    return (t21 - e2._start) * e2._ts + (e2._ts >= 0 ? 0 : e2._dirty ? e2.totalDuration() : e2._tDur);
  };
  var Qt = function(t21) {
    return t21._end = Ot(t21._start + (t21._tDur / Math.abs(t21._ts || t21._rts || 1e-8) || 0));
  };
  var Gt = function(t21, e2) {
    var i2 = t21._dp;
    return i2 && i2.smoothChildTiming && t21._ts && (t21._start = Ot(i2._time - (t21._ts > 0 ? e2 / t21._ts : ((t21._dirty ? t21.totalDuration() : t21._tDur) - e2) / -t21._ts)), Qt(t21), i2._dirty || Xt(i2, t21)), t21;
  };
  var $t = function(t21, e2) {
    var i2;
    if ((e2._time || e2._initted && !e2._dur) && (i2 = Ht(t21.rawTime(), e2), (!e2._dur || ue(0, e2.totalDuration(), i2) - e2._tTime > 1e-8) && e2.render(i2, true)), Xt(t21, e2)._dp && t21._initted && t21._time >= t21._dur && t21._ts) {
      if (t21._dur < t21.duration()) for (i2 = t21; i2._dp; ) i2.rawTime() >= 0 && i2.totalTime(i2._tTime), i2 = i2._dp;
      t21._zTime = -1e-8;
    }
  };
  var Jt = function(t21, e2, i2, n2) {
    return e2.parent && qt(e2), e2._start = Ot((W(i2) ? i2 : i2 || t21 !== h ? se(t21, i2, e2) : t21._time) + e2._delay), e2._end = Ot(e2._start + (e2.totalDuration() / Math.abs(e2.timeScale()) || 0)), Vt(t21, e2, "_first", "_last", t21._sort ? "_start" : 0), ee(e2) || (t21._recent = e2), n2 || $t(t21, e2), t21;
  };
  var Zt = function(t21, e2) {
    return (ot.ScrollTrigger || lt("scrollTrigger", e2)) && ot.ScrollTrigger.create(e2, t21);
  };
  var Kt = function(t21, e2, i2, n2) {
    return ei(t21, e2), t21._initted ? !i2 && t21._pt && (t21._dur && false !== t21.vars.lazy || !t21._dur && t21.vars.lazy) && d !== Le.frame ? (mt.push(t21), t21._lazy = [e2, n2], 1) : void 0 : 1;
  };
  var te = function t4(e2) {
    var i2 = e2.parent;
    return i2 && i2._ts && i2._initted && !i2._lock && (i2.rawTime() < 0 || t4(i2));
  };
  var ee = function(t21) {
    var e2 = t21.data;
    return "isFromStart" === e2 || "isStart" === e2;
  };
  var ie = function(t21, e2, i2, n2) {
    var r2 = t21._repeat, s2 = Ot(e2) || 0, a2 = t21._tTime / t21._tDur;
    return a2 && !n2 && (t21._time *= s2 / t21._dur), t21._dur = s2, t21._tDur = r2 ? r2 < 0 ? 1e10 : Ot(s2 * (r2 + 1) + t21._rDelay * r2) : s2, a2 > 0 && !n2 ? Gt(t21, t21._tTime = t21._tDur * a2) : t21.parent && Qt(t21), i2 || Xt(t21.parent, t21), t21;
  };
  var ne = function(t21) {
    return t21 instanceof Ge ? Xt(t21) : ie(t21, t21._dur);
  };
  var re = { _start: 0, endTime: pt, totalDuration: pt };
  var se = function t5(e2, i2, n2) {
    var r2, s2, a2, o2 = e2.labels, u2 = e2._recent || re, h2 = e2.duration() >= 1e8 ? u2.endTime(false) : e2._dur;
    return j(i2) && (isNaN(i2) || i2 in o2) ? (s2 = i2.charAt(0), a2 = "%" === i2.substr(-1), r2 = i2.indexOf("="), "<" === s2 || ">" === s2 ? (r2 >= 0 && (i2 = i2.replace(/=/, "")), ("<" === s2 ? u2._start : u2.endTime(u2._repeat >= 0)) + (parseFloat(i2.substr(1)) || 0) * (a2 ? (r2 < 0 ? u2 : n2).totalDuration() / 100 : 1)) : r2 < 0 ? (i2 in o2 || (o2[i2] = h2), o2[i2]) : (s2 = parseFloat(i2.charAt(r2 - 1) + i2.substr(r2 + 1)), a2 && n2 && (s2 = s2 / 100 * (K(n2) ? n2[0] : n2).totalDuration()), r2 > 1 ? t5(e2, i2.substr(0, r2 - 1), n2) + s2 : h2 + s2)) : null == i2 ? h2 : +i2;
  };
  var ae = function(t21, e2, i2) {
    var n2, r2, s2 = W(e2[1]), a2 = (s2 ? 2 : 1) + (t21 < 2 ? 0 : 1), o2 = e2[a2];
    if (s2 && (o2.duration = e2[1]), o2.parent = i2, t21) {
      for (n2 = o2, r2 = i2; r2 && !("immediateRender" in n2); ) n2 = r2.vars.defaults || {}, r2 = G(r2.vars.inherit) && r2.parent;
      o2.immediateRender = G(n2.immediateRender), t21 < 2 ? o2.runBackwards = 1 : o2.startAt = e2[a2 - 1];
    }
    return new ai(e2[0], o2, e2[a2 + 1]);
  };
  var oe = function(t21, e2) {
    return t21 || 0 === t21 ? e2(t21) : e2;
  };
  var ue = function(t21, e2, i2) {
    return i2 < t21 ? t21 : i2 > e2 ? e2 : i2;
  };
  var he = function(t21, e2) {
    return j(t21) && (e2 = at.exec(t21)) ? e2[1] : "";
  };
  var le = [].slice;
  var fe = function(t21, e2) {
    return t21 && Q(t21) && "length" in t21 && (!e2 && !t21.length || t21.length - 1 in t21 && Q(t21[0])) && !t21.nodeType && t21 !== l;
  };
  var ce = function(t21, e2, i2) {
    return void 0 === i2 && (i2 = []), t21.forEach((function(t22) {
      var n2;
      return j(t22) && !e2 || fe(t22, 1) ? (n2 = i2).push.apply(n2, pe(t22)) : i2.push(t22);
    })) || i2;
  };
  var pe = function(t21, e2, i2) {
    return !j(t21) || i2 || !f && Be() ? K(t21) ? ce(t21, i2) : fe(t21) ? le.call(t21, 0) : t21 ? [t21] : [] : le.call((e2 || c).querySelectorAll(t21), 0);
  };
  var de = function(t21) {
    return t21.sort((function() {
      return 0.5 - __hf.random();
    }));
  };
  var me = function(t21) {
    if (U(t21)) return t21;
    var e2 = Q(t21) ? t21 : { each: t21 }, i2 = Xe(e2.ease), n2 = e2.from || 0, r2 = parseFloat(e2.base) || 0, s2 = {}, a2 = n2 > 0 && n2 < 1, o2 = isNaN(n2) || a2, u2 = e2.axis, h2 = n2, l2 = n2;
    return j(n2) ? h2 = l2 = { center: 0.5, edges: 0.5, end: 1 }[n2] || 0 : !a2 && o2 && (h2 = n2[0], l2 = n2[1]), function(t22, a3, f2) {
      var c2, p2, d2, m2, g2, _2, v2, y2, x2, b2 = (f2 || e2).length, w2 = s2[b2];
      if (!w2) {
        if (!(x2 = "auto" === e2.grid ? 0 : (e2.grid || [1, 1e8])[1])) {
          for (v2 = -1e8; v2 < (v2 = f2[x2++].getBoundingClientRect().left) && x2 < b2; ) ;
          x2--;
        }
        for (w2 = s2[b2] = [], c2 = o2 ? Math.min(x2, b2) * h2 - 0.5 : n2 % x2, p2 = 1e8 === x2 ? 0 : o2 ? b2 * l2 / x2 - 0.5 : n2 / x2 | 0, v2 = 0, y2 = 1e8, _2 = 0; _2 < b2; _2++) d2 = _2 % x2 - c2, m2 = p2 - (_2 / x2 | 0), w2[_2] = g2 = u2 ? Math.abs("y" === u2 ? m2 : d2) : q(d2 * d2 + m2 * m2), g2 > v2 && (v2 = g2), g2 < y2 && (y2 = g2);
        "random" === n2 && de(w2), w2.max = v2 - y2, w2.min = y2, w2.v = b2 = (parseFloat(e2.amount) || parseFloat(e2.each) * (x2 > b2 ? b2 - 1 : u2 ? "y" === u2 ? b2 / x2 : x2 : Math.max(x2, b2 / x2)) || 0) * ("edges" === n2 ? -1 : 1), w2.b = b2 < 0 ? r2 - b2 : r2, w2.u = he(e2.amount || e2.each) || 0, i2 = i2 && b2 < 0 ? Ne(i2) : i2;
      }
      return b2 = (w2[t22] - w2.min) / w2.max || 0, Ot(w2.b + (i2 ? i2(b2) : b2) * w2.v) + w2.u;
    };
  };
  var ge = function(t21) {
    var e2 = Math.pow(10, ((t21 + "").split(".")[1] || "").length);
    return function(i2) {
      var n2 = Math.round(parseFloat(i2) / t21) * t21 * e2;
      return (n2 - n2 % 1) / e2 + (W(i2) ? 0 : he(i2));
    };
  };
  var _e = function(t21, e2) {
    var i2, n2, r2 = K(t21);
    return !r2 && Q(t21) && (i2 = r2 = t21.radius || 1e8, t21.values ? (t21 = pe(t21.values), (n2 = !W(t21[0])) && (i2 *= i2)) : t21 = ge(t21.increment)), oe(e2, r2 ? U(t21) ? function(e3) {
      return n2 = t21(e3), Math.abs(n2 - e3) <= i2 ? n2 : e3;
    } : function(e3) {
      for (var r3, s2, a2 = parseFloat(n2 ? e3.x : e3), o2 = parseFloat(n2 ? e3.y : 0), u2 = 1e8, h2 = 0, l2 = t21.length; l2--; ) (r3 = n2 ? (r3 = t21[l2].x - a2) * r3 + (s2 = t21[l2].y - o2) * s2 : Math.abs(t21[l2] - a2)) < u2 && (u2 = r3, h2 = l2);
      return h2 = !i2 || u2 <= i2 ? t21[h2] : e3, n2 || h2 === e3 || W(e3) ? h2 : h2 + he(e3);
    } : ge(t21));
  };
  var ve = function(t21, e2, i2, n2) {
    return oe(K(t21) ? !e2 : true === i2 ? (i2 = 0, false) : !n2, (function() {
      return K(t21) ? t21[~~(__hf.random() * t21.length)] : (n2 = (i2 = i2 || 1e-5) < 1 ? Math.pow(10, (i2 + "").length - 2) : 1) && Math.floor(Math.round((t21 - i2 / 2 + __hf.random() * (e2 - t21 + 0.99 * i2)) / i2) * i2 * n2) / n2;
    }));
  };
  var ye = function(t21, e2, i2) {
    return oe(i2, (function(i3) {
      return t21[~~e2(i3)];
    }));
  };
  var xe = function(t21) {
    for (var e2, i2, n2, r2, s2 = 0, a2 = ""; ~(e2 = t21.indexOf("random(", s2)); ) n2 = t21.indexOf(")", e2), r2 = "[" === t21.charAt(e2 + 7), i2 = t21.substr(e2 + 7, n2 - e2 - 7).match(r2 ? st : tt), a2 += t21.substr(s2, e2 - s2) + ve(r2 ? i2 : +i2[0], r2 ? 0 : +i2[1], +i2[2] || 1e-5), s2 = n2 + 1;
    return a2 + t21.substr(s2, t21.length - s2);
  };
  var be = function(t21, e2, i2, n2, r2) {
    var s2 = e2 - t21, a2 = n2 - i2;
    return oe(r2, (function(e3) {
      return i2 + ((e3 - t21) / s2 * a2 || 0);
    }));
  };
  var we = function(t21, e2, i2) {
    var n2, r2, s2, a2 = t21.labels, o2 = 1e8;
    for (n2 in a2) (r2 = a2[n2] - e2) < 0 == !!i2 && r2 && o2 > (r2 = Math.abs(r2)) && (s2 = n2, o2 = r2);
    return s2;
  };
  var Te = function(t21, e2, i2) {
    var n2, r2, s2 = t21.vars, a2 = s2[e2];
    if (a2) return n2 = s2[e2 + "Params"], r2 = s2.callbackScope || t21, i2 && mt.length && At(), n2 ? a2.apply(r2, n2) : a2.call(r2);
  };
  var ke = function(t21) {
    return qt(t21), t21.scrollTrigger && t21.scrollTrigger.kill(false), t21.progress() < 1 && Te(t21, "onInterrupt"), t21;
  };
  var Ce = function(t21) {
    var e2 = (t21 = !t21.name && t21.default || t21).name, i2 = U(t21), n2 = e2 && !i2 && t21.init ? function() {
      this._props = [];
    } : t21, r2 = { init: pt, render: mi, add: Ke, kill: _i, modifier: gi, rawVars: 0 }, s2 = { targetTest: 0, get: 0, getSetter: fi, aliases: {}, register: 0 };
    if (Be(), t21 !== n2) {
      if (_t[e2]) return;
      Lt(n2, Lt(zt(t21, r2), s2)), Bt(n2.prototype, Bt(r2, zt(t21, s2))), _t[n2.prop = e2] = n2, t21.targetTest && (xt.push(n2), dt[e2] = 1), e2 = ("css" === e2 ? "CSS" : e2.charAt(0).toUpperCase() + e2.substr(1)) + "Plugin";
    }
    ct(e2, n2), t21.register && t21.register(ki, n2, xi);
  };
  var Se = { aqua: [0, 255, 255], lime: [0, 255, 0], silver: [192, 192, 192], black: [0, 0, 0], maroon: [128, 0, 0], teal: [0, 128, 128], blue: [0, 0, 255], navy: [0, 0, 128], white: [255, 255, 255], olive: [128, 128, 0], yellow: [255, 255, 0], orange: [255, 165, 0], gray: [128, 128, 128], purple: [128, 0, 128], green: [0, 128, 0], red: [255, 0, 0], pink: [255, 192, 203], cyan: [0, 255, 255], transparent: [255, 255, 255, 0] };
  var Oe = function(t21, e2, i2) {
    return 255 * (6 * (t21 += t21 < 0 ? 1 : t21 > 1 ? -1 : 0) < 1 ? e2 + (i2 - e2) * t21 * 6 : t21 < 0.5 ? i2 : 3 * t21 < 2 ? e2 + (i2 - e2) * (2 / 3 - t21) * 6 : e2) + 0.5 | 0;
  };
  var Ee = function(t21, e2, i2) {
    var n2, r2, s2, a2, o2, u2, h2, l2, f2, c2, p2 = t21 ? W(t21) ? [t21 >> 16, t21 >> 8 & 255, 255 & t21] : 0 : Se.black;
    if (!p2) {
      if ("," === t21.substr(-1) && (t21 = t21.substr(0, t21.length - 1)), Se[t21]) p2 = Se[t21];
      else if ("#" === t21.charAt(0)) {
        if (t21.length < 6 && (n2 = t21.charAt(1), r2 = t21.charAt(2), s2 = t21.charAt(3), t21 = "#" + n2 + n2 + r2 + r2 + s2 + s2 + (5 === t21.length ? t21.charAt(4) + t21.charAt(4) : "")), 9 === t21.length) return [(p2 = parseInt(t21.substr(1, 6), 16)) >> 16, p2 >> 8 & 255, 255 & p2, parseInt(t21.substr(7), 16) / 255];
        p2 = [(t21 = parseInt(t21.substr(1), 16)) >> 16, t21 >> 8 & 255, 255 & t21];
      } else if ("hsl" === t21.substr(0, 3)) if (p2 = c2 = t21.match(tt), e2) {
        if (~t21.indexOf("=")) return p2 = t21.match(et), i2 && p2.length < 4 && (p2[3] = 1), p2;
      } else a2 = +p2[0] % 360 / 360, o2 = +p2[1] / 100, n2 = 2 * (u2 = +p2[2] / 100) - (r2 = u2 <= 0.5 ? u2 * (o2 + 1) : u2 + o2 - u2 * o2), p2.length > 3 && (p2[3] *= 1), p2[0] = Oe(a2 + 1 / 3, n2, r2), p2[1] = Oe(a2, n2, r2), p2[2] = Oe(a2 - 1 / 3, n2, r2);
      else p2 = t21.match(tt) || Se.transparent;
      p2 = p2.map(Number);
    }
    return e2 && !c2 && (n2 = p2[0] / 255, r2 = p2[1] / 255, s2 = p2[2] / 255, u2 = ((h2 = Math.max(n2, r2, s2)) + (l2 = Math.min(n2, r2, s2))) / 2, h2 === l2 ? a2 = o2 = 0 : (f2 = h2 - l2, o2 = u2 > 0.5 ? f2 / (2 - h2 - l2) : f2 / (h2 + l2), a2 = h2 === n2 ? (r2 - s2) / f2 + (r2 < s2 ? 6 : 0) : h2 === r2 ? (s2 - n2) / f2 + 2 : (n2 - r2) / f2 + 4, a2 *= 60), p2[0] = ~~(a2 + 0.5), p2[1] = ~~(100 * o2 + 0.5), p2[2] = ~~(100 * u2 + 0.5)), i2 && p2.length < 4 && (p2[3] = 1), p2;
  };
  var Me = function(t21) {
    var e2 = [], i2 = [], n2 = -1;
    return t21.split(Pe).forEach((function(t22) {
      var r2 = t22.match(it) || [];
      e2.push.apply(e2, r2), i2.push(n2 += r2.length + 1);
    })), e2.c = i2, e2;
  };
  var Ae = function(t21, e2, i2) {
    var n2, r2, s2, a2, o2 = "", u2 = (t21 + o2).match(Pe), h2 = e2 ? "hsla(" : "rgba(", l2 = 0;
    if (!u2) return t21;
    if (u2 = u2.map((function(t22) {
      return (t22 = Ee(t22, e2, 1)) && h2 + (e2 ? t22[0] + "," + t22[1] + "%," + t22[2] + "%," + t22[3] : t22.join(",")) + ")";
    })), i2 && (s2 = Me(t21), (n2 = i2.c).join(o2) !== s2.c.join(o2))) for (a2 = (r2 = t21.replace(Pe, "1").split(it)).length - 1; l2 < a2; l2++) o2 += r2[l2] + (~n2.indexOf(l2) ? u2.shift() || h2 + "0,0,0,0)" : (s2.length ? s2 : u2.length ? u2 : i2).shift());
    if (!r2) for (a2 = (r2 = t21.split(Pe)).length - 1; l2 < a2; l2++) o2 += r2[l2] + u2[l2];
    return o2 + r2[a2];
  };
  var Pe = (function() {
    var t21, e2 = "(?:\\b(?:(?:rgb|rgba|hsl|hsla)\\(.+?\\))|\\B#(?:[0-9a-f]{3,4}){1,2}\\b";
    for (t21 in Se) e2 += "|" + t21 + "\\b";
    return new RegExp(e2 + ")", "gi");
  })();
  var Ie = /hsl[a]?\(/;
  var De = function(t21) {
    var e2, i2 = t21.join(" ");
    if (Pe.lastIndex = 0, Pe.test(i2)) return e2 = Ie.test(i2), t21[1] = Ae(t21[1], e2), t21[0] = Ae(t21[0], e2, Me(t21[1])), true;
  };
  var Le = (T = Date.now, k = 500, C = 33, S = T(), O = S, M = E = 1e3 / 240, P = function t6(e2) {
    var i2, n2, r2, s2, a2 = T() - O, o2 = true === e2;
    if (a2 > k && (S += a2 - C), ((i2 = (r2 = (O += a2) - S) - M) > 0 || o2) && (s2 = ++x.frame, b = r2 - 1e3 * x.time, x.time = r2 /= 1e3, M += i2 + (i2 >= E ? 4 : E - i2), n2 = 1), o2 || (_ = v(t6)), n2) for (w = 0; w < A.length; w++) A[w](r2, b, s2, e2);
  }, x = { time: 0, frame: 0, tick: function() {
    P(true);
  }, deltaRatio: function(t21) {
    return b / (1e3 / (t21 || 60));
  }, wake: function() {
    p && (!f && $() && (l = f = window, c = l.document || {}, ot.gsap = ki, (l.gsapVersions || (l.gsapVersions = [])).push(ki.version), ht(ut || l.GreenSockGlobals || !l.gsap && l || {}), y = l.requestAnimationFrame), _ && x.sleep(), v = y || function(t21) {
      return __hf.setTimeout(t21, M - 1e3 * x.time + 1 | 0);
    }, g = 1, P(2));
  }, sleep: function() {
    (y ? l.cancelAnimationFrame : clearTimeout)(_), g = 0, v = pt;
  }, lagSmoothing: function(t21, e2) {
    k = t21 || 1 / 1e-8, C = Math.min(e2, k, 0);
  }, fps: function(t21) {
    E = 1e3 / (t21 || 240), M = 1e3 * x.time + E;
  }, add: function(t21, e2, i2) {
    var n2 = e2 ? function(e3, i3, r2, s2) {
      t21(e3, i3, r2, s2), x.remove(n2);
    } : t21;
    return x.remove(t21), A[i2 ? "unshift" : "push"](n2), Be(), n2;
  }, remove: function(t21, e2) {
    ~(e2 = A.indexOf(t21)) && A.splice(e2, 1) && w >= e2 && w--;
  }, _listeners: A = [] });
  var Be = function() {
    return !g && Le.wake();
  };
  var Re = {};
  var ze = /^[\d.\-M][\d.\-,\s]/;
  var Fe = /["']/g;
  var Ve = function(t21) {
    for (var e2, i2, n2, r2 = {}, s2 = t21.substr(1, t21.length - 3).split(":"), a2 = s2[0], o2 = 1, u2 = s2.length; o2 < u2; o2++) i2 = s2[o2], e2 = o2 !== u2 - 1 ? i2.lastIndexOf(",") : i2.length, n2 = i2.substr(0, e2), r2[a2] = isNaN(n2) ? n2.replace(Fe, "").trim() : +n2, a2 = i2.substr(e2 + 1).trim();
    return r2;
  };
  var Ne = function(t21) {
    return function(e2) {
      return 1 - t21(1 - e2);
    };
  };
  var qe = function t7(e2, i2) {
    for (var n2, r2 = e2._first; r2; ) r2 instanceof Ge ? t7(r2, i2) : !r2.vars.yoyoEase || r2._yoyo && r2._repeat || r2._yoyo === i2 || (r2.timeline ? t7(r2.timeline, i2) : (n2 = r2._ease, r2._ease = r2._yEase, r2._yEase = n2, r2._yoyo = i2)), r2 = r2._next;
  };
  var Xe = function(t21, e2) {
    return t21 && (U(t21) ? t21 : Re[t21] || (function(t22) {
      var e3, i2, n2, r2, s2 = (t22 + "").split("("), a2 = Re[s2[0]];
      return a2 && s2.length > 1 && a2.config ? a2.config.apply(null, ~t22.indexOf("{") ? [Ve(s2[1])] : (e3 = t22, i2 = e3.indexOf("(") + 1, n2 = e3.indexOf(")"), r2 = e3.indexOf("(", i2), e3.substring(i2, ~r2 && r2 < n2 ? e3.indexOf(")", n2 + 1) : n2)).split(",").map(It)) : Re._CE && ze.test(t22) ? Re._CE("", t22) : a2;
    })(t21)) || e2;
  };
  var Ye = function(t21, e2, i2, n2) {
    void 0 === i2 && (i2 = function(t22) {
      return 1 - e2(1 - t22);
    }), void 0 === n2 && (n2 = function(t22) {
      return t22 < 0.5 ? e2(2 * t22) / 2 : 1 - e2(2 * (1 - t22)) / 2;
    });
    var r2, s2 = { easeIn: e2, easeOut: i2, easeInOut: n2 };
    return Ct(t21, (function(t22) {
      for (var e3 in Re[t22] = ot[t22] = s2, Re[r2 = t22.toLowerCase()] = i2, s2) Re[r2 + ("easeIn" === e3 ? ".in" : "easeOut" === e3 ? ".out" : ".inOut")] = Re[t22 + "." + e3] = s2[e3];
    })), s2;
  };
  var je = function(t21) {
    return function(e2) {
      return e2 < 0.5 ? (1 - t21(1 - 2 * e2)) / 2 : 0.5 + t21(2 * (e2 - 0.5)) / 2;
    };
  };
  var Ue = function t8(e2, i2, n2) {
    var r2 = i2 >= 1 ? i2 : 1, s2 = (n2 || (e2 ? 0.3 : 0.45)) / (i2 < 1 ? i2 : 1), a2 = s2 / F * (Math.asin(1 / r2) || 0), o2 = function(t21) {
      return 1 === t21 ? 1 : r2 * Math.pow(2, -10 * t21) * Y((t21 - a2) * s2) + 1;
    }, u2 = "out" === e2 ? o2 : "in" === e2 ? function(t21) {
      return 1 - o2(1 - t21);
    } : je(o2);
    return s2 = F / s2, u2.config = function(i3, n3) {
      return t8(e2, i3, n3);
    }, u2;
  };
  var We = function t9(e2, i2) {
    void 0 === i2 && (i2 = 1.70158);
    var n2 = function(t21) {
      return t21 ? --t21 * t21 * ((i2 + 1) * t21 + i2) + 1 : 0;
    }, r2 = "out" === e2 ? n2 : "in" === e2 ? function(t21) {
      return 1 - n2(1 - t21);
    } : je(n2);
    return r2.config = function(i3) {
      return t9(e2, i3);
    }, r2;
  };
  Ct("Linear,Quad,Cubic,Quart,Quint,Strong", (function(t21, e2) {
    var i2 = e2 < 5 ? e2 + 1 : e2;
    Ye(t21 + ",Power" + (i2 - 1), e2 ? function(t22) {
      return Math.pow(t22, i2);
    } : function(t22) {
      return t22;
    }, (function(t22) {
      return 1 - Math.pow(1 - t22, i2);
    }), (function(t22) {
      return t22 < 0.5 ? Math.pow(2 * t22, i2) / 2 : 1 - Math.pow(2 * (1 - t22), i2) / 2;
    }));
  })), Re.Linear.easeNone = Re.none = Re.Linear.easeIn, Ye("Elastic", Ue("in"), Ue("out"), Ue()), I = 7.5625, L = 1 / (D = 2.75), Ye("Bounce", (function(t21) {
    return 1 - B(1 - t21);
  }), B = function(t21) {
    return t21 < L ? I * t21 * t21 : t21 < 0.7272727272727273 ? I * Math.pow(t21 - 1.5 / D, 2) + 0.75 : t21 < 0.9090909090909092 ? I * (t21 -= 2.25 / D) * t21 + 0.9375 : I * Math.pow(t21 - 2.625 / D, 2) + 0.984375;
  }), Ye("Expo", (function(t21) {
    return t21 ? Math.pow(2, 10 * (t21 - 1)) : 0;
  })), Ye("Circ", (function(t21) {
    return -(q(1 - t21 * t21) - 1);
  })), Ye("Sine", (function(t21) {
    return 1 === t21 ? 1 : 1 - X(t21 * V);
  })), Ye("Back", We("in"), We("out"), We()), Re.SteppedEase = Re.steps = ot.SteppedEase = { config: function(t21, e2) {
    void 0 === t21 && (t21 = 1);
    var i2 = 1 / t21, n2 = t21 + (e2 ? 0 : 1), r2 = e2 ? 1 : 0;
    return function(t22) {
      return ((n2 * ue(0, 0.99999999, t22) | 0) + r2) * i2;
    };
  } }, z.ease = Re["quad.out"], Ct("onComplete,onUpdate,onStart,onRepeat,onReverseComplete,onInterrupt", (function(t21) {
    return bt += t21 + "," + t21 + "Params,";
  }));
  var He = function(t21, e2) {
    this.id = N++, t21._gsap = this, this.target = t21, this.harness = e2, this.get = e2 ? e2.get : kt, this.set = e2 ? e2.getSetter : fi;
  };
  var Qe = (function() {
    function t21(t22) {
      this.vars = t22, this._delay = +t22.delay || 0, (this._repeat = t22.repeat === 1 / 0 ? -2 : t22.repeat || 0) && (this._rDelay = t22.repeatDelay || 0, this._yoyo = !!t22.yoyo || !!t22.yoyoEase), this._ts = 1, ie(this, +t22.duration, 1, 1), this.data = t22.data, g || Le.wake();
    }
    var e2 = t21.prototype;
    return e2.delay = function(t22) {
      return t22 || 0 === t22 ? (this.parent && this.parent.smoothChildTiming && this.startTime(this._start + t22 - this._delay), this._delay = t22, this) : this._delay;
    }, e2.duration = function(t22) {
      return arguments.length ? this.totalDuration(this._repeat > 0 ? t22 + (t22 + this._rDelay) * this._repeat : t22) : this.totalDuration() && this._dur;
    }, e2.totalDuration = function(t22) {
      return arguments.length ? (this._dirty = 0, ie(this, this._repeat < 0 ? t22 : (t22 - this._repeat * this._rDelay) / (this._repeat + 1))) : this._tDur;
    }, e2.totalTime = function(t22, e3) {
      if (Be(), !arguments.length) return this._tTime;
      var i2 = this._dp;
      if (i2 && i2.smoothChildTiming && this._ts) {
        for (Gt(this, t22), !i2._dp || i2.parent || $t(i2, this); i2 && i2.parent; ) i2.parent._time !== i2._start + (i2._ts >= 0 ? i2._tTime / i2._ts : (i2.totalDuration() - i2._tTime) / -i2._ts) && i2.totalTime(i2._tTime, true), i2 = i2.parent;
        !this.parent && this._dp.autoRemoveChildren && (this._ts > 0 && t22 < this._tDur || this._ts < 0 && t22 > 0 || !this._tDur && !t22) && Jt(this._dp, this, this._start - this._delay);
      }
      return (this._tTime !== t22 || !this._dur && !e3 || this._initted && 1e-8 === Math.abs(this._zTime) || !t22 && !this._initted && (this.add || this._ptLookup)) && (this._ts || (this._pTime = t22), Pt(this, t22, e3)), this;
    }, e2.time = function(t22, e3) {
      return arguments.length ? this.totalTime(Math.min(this.totalDuration(), t22 + Ut(this)) % (this._dur + this._rDelay) || (t22 ? this._dur : 0), e3) : this._time;
    }, e2.totalProgress = function(t22, e3) {
      return arguments.length ? this.totalTime(this.totalDuration() * t22, e3) : this.totalDuration() ? Math.min(1, this._tTime / this._tDur) : this.ratio;
    }, e2.progress = function(t22, e3) {
      return arguments.length ? this.totalTime(this.duration() * (!this._yoyo || 1 & this.iteration() ? t22 : 1 - t22) + Ut(this), e3) : this.duration() ? Math.min(1, this._time / this._dur) : this.ratio;
    }, e2.iteration = function(t22, e3) {
      var i2 = this.duration() + this._rDelay;
      return arguments.length ? this.totalTime(this._time + (t22 - 1) * i2, e3) : this._repeat ? Wt(this._tTime, i2) + 1 : 1;
    }, e2.timeScale = function(t22) {
      if (!arguments.length) return -1e-8 === this._rts ? 0 : this._rts;
      if (this._rts === t22) return this;
      var e3 = this.parent && this._ts ? Ht(this.parent._time, this) : this._tTime;
      return this._rts = +t22 || 0, this._ts = this._ps || -1e-8 === t22 ? 0 : this._rts, this.totalTime(ue(-this._delay, this._tDur, e3), true), Qt(this), Yt(this);
    }, e2.paused = function(t22) {
      return arguments.length ? (this._ps !== t22 && (this._ps = t22, t22 ? (this._pTime = this._tTime || Math.max(-this._delay, this.rawTime()), this._ts = this._act = 0) : (Be(), this._ts = this._rts, this.totalTime(this.parent && !this.parent.smoothChildTiming ? this.rawTime() : this._tTime || this._pTime, 1 === this.progress() && 1e-8 !== Math.abs(this._zTime) && (this._tTime -= 1e-8)))), this) : this._ps;
    }, e2.startTime = function(t22) {
      if (arguments.length) {
        this._start = t22;
        var e3 = this.parent || this._dp;
        return e3 && (e3._sort || !this.parent) && Jt(e3, this, t22 - this._delay), this;
      }
      return this._start;
    }, e2.endTime = function(t22) {
      return this._start + (G(t22) ? this.totalDuration() : this.duration()) / Math.abs(this._ts || 1);
    }, e2.rawTime = function(t22) {
      var e3 = this.parent || this._dp;
      return e3 ? t22 && (!this._ts || this._repeat && this._time && this.totalProgress() < 1) ? this._tTime % (this._dur + this._rDelay) : this._ts ? Ht(e3.rawTime(t22), this) : this._tTime : this._tTime;
    }, e2.globalTime = function(t22) {
      for (var e3 = this, i2 = arguments.length ? t22 : e3.rawTime(); e3; ) i2 = e3._start + i2 / (e3._ts || 1), e3 = e3._dp;
      return i2;
    }, e2.repeat = function(t22) {
      return arguments.length ? (this._repeat = t22 === 1 / 0 ? -2 : t22, ne(this)) : -2 === this._repeat ? 1 / 0 : this._repeat;
    }, e2.repeatDelay = function(t22) {
      if (arguments.length) {
        var e3 = this._time;
        return this._rDelay = t22, ne(this), e3 ? this.time(e3) : this;
      }
      return this._rDelay;
    }, e2.yoyo = function(t22) {
      return arguments.length ? (this._yoyo = t22, this) : this._yoyo;
    }, e2.seek = function(t22, e3) {
      return this.totalTime(se(this, t22), G(e3));
    }, e2.restart = function(t22, e3) {
      return this.play().totalTime(t22 ? -this._delay : 0, G(e3));
    }, e2.play = function(t22, e3) {
      return null != t22 && this.seek(t22, e3), this.reversed(false).paused(false);
    }, e2.reverse = function(t22, e3) {
      return null != t22 && this.seek(t22 || this.totalDuration(), e3), this.reversed(true).paused(false);
    }, e2.pause = function(t22, e3) {
      return null != t22 && this.seek(t22, e3), this.paused(true);
    }, e2.resume = function() {
      return this.paused(false);
    }, e2.reversed = function(t22) {
      return arguments.length ? (!!t22 !== this.reversed() && this.timeScale(-this._rts || (t22 ? -1e-8 : 0)), this) : this._rts < 0;
    }, e2.invalidate = function() {
      return this._initted = this._act = 0, this._zTime = -1e-8, this;
    }, e2.isActive = function() {
      var t22, e3 = this.parent || this._dp, i2 = this._start;
      return !(e3 && !(this._ts && this._initted && e3.isActive() && (t22 = e3.rawTime(true)) >= i2 && t22 < this.endTime(true) - 1e-8));
    }, e2.eventCallback = function(t22, e3, i2) {
      var n2 = this.vars;
      return arguments.length > 1 ? (e3 ? (n2[t22] = e3, i2 && (n2[t22 + "Params"] = i2), "onUpdate" === t22 && (this._onUpdate = e3)) : delete n2[t22], this) : n2[t22];
    }, e2.then = function(t22) {
      var e3 = this;
      return new Promise((function(i2) {
        var n2 = U(t22) ? t22 : Dt, r2 = function() {
          var t23 = e3.then;
          e3.then = null, U(n2) && (n2 = n2(e3)) && (n2.then || n2 === e3) && (e3.then = t23), i2(n2), e3.then = t23;
        };
        e3._initted && 1 === e3.totalProgress() && e3._ts >= 0 || !e3._tTime && e3._ts < 0 ? r2() : e3._prom = r2;
      }));
    }, e2.kill = function() {
      ke(this);
    }, t21;
  })();
  Lt(Qe.prototype, { _time: 0, _start: 0, _end: 0, _tTime: 0, _tDur: 0, _dirty: 0, _repeat: 0, _yoyo: false, parent: null, _initted: false, _rDelay: 0, _ts: 1, _dp: 0, ratio: 0, _zTime: -1e-8, _prom: 0, _ps: false, _rts: 1 });
  var Ge = (function(t21) {
    function e2(e3, i3) {
      var n2;
      return void 0 === e3 && (e3 = {}), (n2 = t21.call(this, e3) || this).labels = {}, n2.smoothChildTiming = !!e3.smoothChildTiming, n2.autoRemoveChildren = !!e3.autoRemoveChildren, n2._sort = G(e3.sortChildren), h && Jt(e3.parent || h, a(n2), i3), e3.reversed && n2.reverse(), e3.paused && n2.paused(true), e3.scrollTrigger && Zt(a(n2), e3.scrollTrigger), n2;
    }
    o(e2, t21);
    var i2 = e2.prototype;
    return i2.to = function(t22, e3, i3) {
      return ae(0, arguments, this), this;
    }, i2.from = function(t22, e3, i3) {
      return ae(1, arguments, this), this;
    }, i2.fromTo = function(t22, e3, i3, n2) {
      return ae(2, arguments, this), this;
    }, i2.set = function(t22, e3, i3) {
      return e3.duration = 0, e3.parent = this, Ft(e3).repeatDelay || (e3.repeat = 0), e3.immediateRender = !!e3.immediateRender, new ai(t22, e3, se(this, i3), 1), this;
    }, i2.call = function(t22, e3, i3) {
      return Jt(this, ai.delayedCall(0, t22, e3), i3);
    }, i2.staggerTo = function(t22, e3, i3, n2, r2, s2, a2) {
      return i3.duration = e3, i3.stagger = i3.stagger || n2, i3.onComplete = s2, i3.onCompleteParams = a2, i3.parent = this, new ai(t22, i3, se(this, r2)), this;
    }, i2.staggerFrom = function(t22, e3, i3, n2, r2, s2, a2) {
      return i3.runBackwards = 1, Ft(i3).immediateRender = G(i3.immediateRender), this.staggerTo(t22, e3, i3, n2, r2, s2, a2);
    }, i2.staggerFromTo = function(t22, e3, i3, n2, r2, s2, a2, o2) {
      return n2.startAt = i3, Ft(n2).immediateRender = G(n2.immediateRender), this.staggerTo(t22, e3, n2, r2, s2, a2, o2);
    }, i2.render = function(t22, e3, i3) {
      var n2, r2, s2, a2, o2, u2, l2, f2, c2, p2, d2, m2, g2 = this._time, _2 = this._dirty ? this.totalDuration() : this._tDur, v2 = this._dur, y2 = t22 <= 0 ? 0 : Ot(t22), x2 = this._zTime < 0 != t22 < 0 && (this._initted || !v2);
      if (this !== h && y2 > _2 && t22 >= 0 && (y2 = _2), y2 !== this._tTime || i3 || x2) {
        if (g2 !== this._time && v2 && (y2 += this._time - g2, t22 += this._time - g2), n2 = y2, c2 = this._start, u2 = !(f2 = this._ts), x2 && (v2 || (g2 = this._zTime), (t22 || !e3) && (this._zTime = t22)), this._repeat) {
          if (d2 = this._yoyo, o2 = v2 + this._rDelay, this._repeat < -1 && t22 < 0) return this.totalTime(100 * o2 + t22, e3, i3);
          if (n2 = Ot(y2 % o2), y2 === _2 ? (a2 = this._repeat, n2 = v2) : ((a2 = ~~(y2 / o2)) && a2 === y2 / o2 && (n2 = v2, a2--), n2 > v2 && (n2 = v2)), p2 = Wt(this._tTime, o2), !g2 && this._tTime && p2 !== a2 && (p2 = a2), d2 && 1 & a2 && (n2 = v2 - n2, m2 = 1), a2 !== p2 && !this._lock) {
            var b2 = d2 && 1 & p2, w2 = b2 === (d2 && 1 & a2);
            if (a2 < p2 && (b2 = !b2), g2 = b2 ? 0 : v2, this._lock = 1, this.render(g2 || (m2 ? 0 : Ot(a2 * o2)), e3, !v2)._lock = 0, this._tTime = y2, !e3 && this.parent && Te(this, "onRepeat"), this.vars.repeatRefresh && !m2 && (this.invalidate()._lock = 1), g2 && g2 !== this._time || u2 !== !this._ts || this.vars.onRepeat && !this.parent && !this._act) return this;
            if (v2 = this._dur, _2 = this._tDur, w2 && (this._lock = 2, g2 = b2 ? v2 : -1e-4, this.render(g2, true), this.vars.repeatRefresh && !m2 && this.invalidate()), this._lock = 0, !this._ts && !u2) return this;
            qe(this, m2);
          }
        }
        if (this._hasPause && !this._forcing && this._lock < 2 && (l2 = (function(t23, e4, i4) {
          var n3;
          if (i4 > e4) for (n3 = t23._first; n3 && n3._start <= i4; ) {
            if ("isPause" === n3.data && n3._start > e4) return n3;
            n3 = n3._next;
          }
          else for (n3 = t23._last; n3 && n3._start >= i4; ) {
            if ("isPause" === n3.data && n3._start < e4) return n3;
            n3 = n3._prev;
          }
        })(this, Ot(g2), Ot(n2)), l2 && (y2 -= n2 - (n2 = l2._start))), this._tTime = y2, this._time = n2, this._act = !f2, this._initted || (this._onUpdate = this.vars.onUpdate, this._initted = 1, this._zTime = t22, g2 = 0), !g2 && n2 && !e3 && (Te(this, "onStart"), this._tTime !== y2)) return this;
        if (n2 >= g2 && t22 >= 0) for (r2 = this._first; r2; ) {
          if (s2 = r2._next, (r2._act || n2 >= r2._start) && r2._ts && l2 !== r2) {
            if (r2.parent !== this) return this.render(t22, e3, i3);
            if (r2.render(r2._ts > 0 ? (n2 - r2._start) * r2._ts : (r2._dirty ? r2.totalDuration() : r2._tDur) + (n2 - r2._start) * r2._ts, e3, i3), n2 !== this._time || !this._ts && !u2) {
              l2 = 0, s2 && (y2 += this._zTime = -1e-8);
              break;
            }
          }
          r2 = s2;
        }
        else {
          r2 = this._last;
          for (var T2 = t22 < 0 ? t22 : n2; r2; ) {
            if (s2 = r2._prev, (r2._act || T2 <= r2._end) && r2._ts && l2 !== r2) {
              if (r2.parent !== this) return this.render(t22, e3, i3);
              if (r2.render(r2._ts > 0 ? (T2 - r2._start) * r2._ts : (r2._dirty ? r2.totalDuration() : r2._tDur) + (T2 - r2._start) * r2._ts, e3, i3), n2 !== this._time || !this._ts && !u2) {
                l2 = 0, s2 && (y2 += this._zTime = T2 ? -1e-8 : 1e-8);
                break;
              }
            }
            r2 = s2;
          }
        }
        if (l2 && !e3 && (this.pause(), l2.render(n2 >= g2 ? 0 : -1e-8)._zTime = n2 >= g2 ? 1 : -1, this._ts)) return this._start = c2, Qt(this), this.render(t22, e3, i3);
        this._onUpdate && !e3 && Te(this, "onUpdate", true), (y2 === _2 && this._tTime >= this.totalDuration() || !y2 && g2) && (c2 !== this._start && Math.abs(f2) === Math.abs(this._ts) || this._lock || ((t22 || !v2) && (y2 === _2 && this._ts > 0 || !y2 && this._ts < 0) && qt(this, 1), e3 || t22 < 0 && !g2 || !y2 && !g2 && _2 || (Te(this, y2 === _2 && t22 >= 0 ? "onComplete" : "onReverseComplete", true), this._prom && !(y2 < _2 && this.timeScale() > 0) && this._prom())));
      }
      return this;
    }, i2.add = function(t22, e3) {
      var i3 = this;
      if (W(e3) || (e3 = se(this, e3, t22)), !(t22 instanceof Qe)) {
        if (K(t22)) return t22.forEach((function(t23) {
          return i3.add(t23, e3);
        })), this;
        if (j(t22)) return this.addLabel(t22, e3);
        if (!U(t22)) return this;
        t22 = ai.delayedCall(0, t22);
      }
      return this !== t22 ? Jt(this, t22, e3) : this;
    }, i2.getChildren = function(t22, e3, i3, n2) {
      void 0 === t22 && (t22 = true), void 0 === e3 && (e3 = true), void 0 === i3 && (i3 = true), void 0 === n2 && (n2 = -1e8);
      for (var r2 = [], s2 = this._first; s2; ) s2._start >= n2 && (s2 instanceof ai ? e3 && r2.push(s2) : (i3 && r2.push(s2), t22 && r2.push.apply(r2, s2.getChildren(true, e3, i3)))), s2 = s2._next;
      return r2;
    }, i2.getById = function(t22) {
      for (var e3 = this.getChildren(1, 1, 1), i3 = e3.length; i3--; ) if (e3[i3].vars.id === t22) return e3[i3];
    }, i2.remove = function(t22) {
      return j(t22) ? this.removeLabel(t22) : U(t22) ? this.killTweensOf(t22) : (Nt(this, t22), t22 === this._recent && (this._recent = this._last), Xt(this));
    }, i2.totalTime = function(e3, i3) {
      return arguments.length ? (this._forcing = 1, !this._dp && this._ts && (this._start = Ot(Le.time - (this._ts > 0 ? e3 / this._ts : (this.totalDuration() - e3) / -this._ts))), t21.prototype.totalTime.call(this, e3, i3), this._forcing = 0, this) : this._tTime;
    }, i2.addLabel = function(t22, e3) {
      return this.labels[t22] = se(this, e3), this;
    }, i2.removeLabel = function(t22) {
      return delete this.labels[t22], this;
    }, i2.addPause = function(t22, e3, i3) {
      var n2 = ai.delayedCall(0, e3 || pt, i3);
      return n2.data = "isPause", this._hasPause = 1, Jt(this, n2, se(this, t22));
    }, i2.removePause = function(t22) {
      var e3 = this._first;
      for (t22 = se(this, t22); e3; ) e3._start === t22 && "isPause" === e3.data && qt(e3), e3 = e3._next;
    }, i2.killTweensOf = function(t22, e3, i3) {
      for (var n2 = this.getTweensOf(t22, i3), r2 = n2.length; r2--; ) $e !== n2[r2] && n2[r2].kill(t22, e3);
      return this;
    }, i2.getTweensOf = function(t22, e3) {
      for (var i3, n2 = [], r2 = pe(t22), s2 = this._first, a2 = W(e3); s2; ) s2 instanceof ai ? Mt(s2._targets, r2) && (a2 ? (!$e || s2._initted && s2._ts) && s2.globalTime(0) <= e3 && s2.globalTime(s2.totalDuration()) > e3 : !e3 || s2.isActive()) && n2.push(s2) : (i3 = s2.getTweensOf(r2, e3)).length && n2.push.apply(n2, i3), s2 = s2._next;
      return n2;
    }, i2.tweenTo = function(t22, e3) {
      e3 = e3 || {};
      var i3, n2 = this, r2 = se(n2, t22), s2 = e3, a2 = s2.startAt, o2 = s2.onStart, u2 = s2.onStartParams, h2 = s2.immediateRender, l2 = ai.to(n2, Lt({ ease: e3.ease || "none", lazy: false, immediateRender: false, time: r2, overwrite: "auto", duration: e3.duration || Math.abs((r2 - (a2 && "time" in a2 ? a2.time : n2._time)) / n2.timeScale()) || 1e-8, onStart: function() {
        if (n2.pause(), !i3) {
          var t23 = e3.duration || Math.abs((r2 - (a2 && "time" in a2 ? a2.time : n2._time)) / n2.timeScale());
          l2._dur !== t23 && ie(l2, t23, 0, 1).render(l2._time, true, true), i3 = 1;
        }
        o2 && o2.apply(l2, u2 || []);
      } }, e3));
      return h2 ? l2.render(0) : l2;
    }, i2.tweenFromTo = function(t22, e3, i3) {
      return this.tweenTo(e3, Lt({ startAt: { time: se(this, t22) } }, i3));
    }, i2.recent = function() {
      return this._recent;
    }, i2.nextLabel = function(t22) {
      return void 0 === t22 && (t22 = this._time), we(this, se(this, t22));
    }, i2.previousLabel = function(t22) {
      return void 0 === t22 && (t22 = this._time), we(this, se(this, t22), 1);
    }, i2.currentLabel = function(t22) {
      return arguments.length ? this.seek(t22, true) : this.previousLabel(this._time + 1e-8);
    }, i2.shiftChildren = function(t22, e3, i3) {
      void 0 === i3 && (i3 = 0);
      for (var n2, r2 = this._first, s2 = this.labels; r2; ) r2._start >= i3 && (r2._start += t22, r2._end += t22), r2 = r2._next;
      if (e3) for (n2 in s2) s2[n2] >= i3 && (s2[n2] += t22);
      return Xt(this);
    }, i2.invalidate = function() {
      var e3 = this._first;
      for (this._lock = 0; e3; ) e3.invalidate(), e3 = e3._next;
      return t21.prototype.invalidate.call(this);
    }, i2.clear = function(t22) {
      void 0 === t22 && (t22 = true);
      for (var e3, i3 = this._first; i3; ) e3 = i3._next, this.remove(i3), i3 = e3;
      return this._dp && (this._time = this._tTime = this._pTime = 0), t22 && (this.labels = {}), Xt(this);
    }, i2.totalDuration = function(t22) {
      var e3, i3, n2, r2 = 0, s2 = this, a2 = s2._last, o2 = 1e8;
      if (arguments.length) return s2.timeScale((s2._repeat < 0 ? s2.duration() : s2.totalDuration()) / (s2.reversed() ? -t22 : t22));
      if (s2._dirty) {
        for (n2 = s2.parent; a2; ) e3 = a2._prev, a2._dirty && a2.totalDuration(), (i3 = a2._start) > o2 && s2._sort && a2._ts && !s2._lock ? (s2._lock = 1, Jt(s2, a2, i3 - a2._delay, 1)._lock = 0) : o2 = i3, i3 < 0 && a2._ts && (r2 -= i3, (!n2 && !s2._dp || n2 && n2.smoothChildTiming) && (s2._start += i3 / s2._ts, s2._time -= i3, s2._tTime -= i3), s2.shiftChildren(-i3, false, -1 / 0), o2 = 0), a2._end > r2 && a2._ts && (r2 = a2._end), a2 = e3;
        ie(s2, s2 === h && s2._time > r2 ? s2._time : r2, 1, 1), s2._dirty = 0;
      }
      return s2._tDur;
    }, e2.updateRoot = function(t22) {
      if (h._ts && (Pt(h, Ht(t22, h)), d = Le.frame), Le.frame >= yt) {
        yt += R.autoSleep || 120;
        var e3 = h._first;
        if ((!e3 || !e3._ts) && R.autoSleep && Le._listeners.length < 2) {
          for (; e3 && !e3._ts; ) e3 = e3._next;
          e3 || Le.sleep();
        }
      }
    }, e2;
  })(Qe);
  Lt(Ge.prototype, { _lock: 0, _hasPause: 0, _forcing: 0 });
  var $e;
  var Je;
  var Ze = function(t21, e2, i2, n2, r2, s2, a2) {
    var o2, u2, h2, l2, f2, c2, p2, d2, m2 = new xi(this._pt, t21, e2, 0, 1, di, null, r2), g2 = 0, _2 = 0;
    for (m2.b = i2, m2.e = n2, i2 += "", (p2 = ~(n2 += "").indexOf("random(")) && (n2 = xe(n2)), s2 && (s2(d2 = [i2, n2], t21, e2), i2 = d2[0], n2 = d2[1]), u2 = i2.match(nt) || []; o2 = nt.exec(n2); ) l2 = o2[0], f2 = n2.substring(g2, o2.index), h2 ? h2 = (h2 + 1) % 5 : "rgba(" === f2.substr(-5) && (h2 = 1), l2 !== u2[_2++] && (c2 = parseFloat(u2[_2 - 1]) || 0, m2._pt = { _next: m2._pt, p: f2 || 1 === _2 ? f2 : ",", s: c2, c: "=" === l2.charAt(1) ? Et(c2, l2) - c2 : parseFloat(l2) - c2, m: h2 && h2 < 4 ? Math.round : 0 }, g2 = nt.lastIndex);
    return m2.c = g2 < n2.length ? n2.substring(g2, n2.length) : "", m2.fp = a2, (rt.test(n2) || p2) && (m2.e = 0), this._pt = m2, m2;
  };
  var Ke = function(t21, e2, i2, n2, r2, s2, a2, o2, u2) {
    U(n2) && (n2 = n2(r2 || 0, t21, s2));
    var h2, l2 = t21[e2], f2 = "get" !== i2 ? i2 : U(l2) ? u2 ? t21[e2.indexOf("set") || !U(t21["get" + e2.substr(3)]) ? e2 : "get" + e2.substr(3)](u2) : t21[e2]() : l2, c2 = U(l2) ? u2 ? hi : ui : oi;
    if (j(n2) && (~n2.indexOf("random(") && (n2 = xe(n2)), "=" === n2.charAt(1) && ((h2 = Et(f2, n2) + (he(f2) || 0)) || 0 === h2) && (n2 = h2)), f2 !== n2 || Je) return isNaN(f2 * n2) || "" === n2 ? (!l2 && !(e2 in t21) && lt(e2, n2), Ze.call(this, t21, e2, f2, n2, c2, o2 || R.stringFilter, u2)) : (h2 = new xi(this._pt, t21, e2, +f2 || 0, n2 - (f2 || 0), "boolean" == typeof l2 ? pi : ci, 0, c2), u2 && (h2.fp = u2), a2 && h2.modifier(a2, this, t21), this._pt = h2);
  };
  var ti = function(t21, e2, i2, n2, r2, s2) {
    var a2, o2, u2, h2;
    if (_t[t21] && false !== (a2 = new _t[t21]()).init(r2, a2.rawVars ? e2[t21] : (function(t22, e3, i3, n3, r3) {
      if (U(t22) && (t22 = ni(t22, r3, e3, i3, n3)), !Q(t22) || t22.style && t22.nodeType || K(t22) || Z(t22)) return j(t22) ? ni(t22, r3, e3, i3, n3) : t22;
      var s3, a3 = {};
      for (s3 in t22) a3[s3] = ni(t22[s3], r3, e3, i3, n3);
      return a3;
    })(e2[t21], n2, r2, s2, i2), i2, n2, s2) && (i2._pt = o2 = new xi(i2._pt, r2, t21, 0, 1, a2.render, a2, 0, a2.priority), i2 !== m)) for (u2 = i2._ptLookup[i2._targets.indexOf(r2)], h2 = a2._props.length; h2--; ) u2[a2._props[h2]] = o2;
    return a2;
  };
  var ei = function t10(e2, i2) {
    var n2, r2, s2, a2, o2, l2, f2, c2, p2, d2, m2, g2, _2, v2 = e2.vars, y2 = v2.ease, x2 = v2.startAt, b2 = v2.immediateRender, w2 = v2.lazy, T2 = v2.onUpdate, k2 = v2.onUpdateParams, C2 = v2.callbackScope, S2 = v2.runBackwards, O2 = v2.yoyoEase, E2 = v2.keyframes, M2 = v2.autoRevert, A2 = e2._dur, P2 = e2._startAt, I2 = e2._targets, D2 = e2.parent, L2 = D2 && "nested" === D2.data ? D2.parent._targets : I2, B2 = "auto" === e2._overwrite && !u, R2 = e2.timeline;
    if (R2 && (!E2 || !y2) && (y2 = "none"), e2._ease = Xe(y2, z.ease), e2._yEase = O2 ? Ne(Xe(true === O2 ? y2 : O2, z.ease)) : 0, O2 && e2._yoyo && !e2._repeat && (O2 = e2._yEase, e2._yEase = e2._ease, e2._ease = O2), e2._from = !R2 && !!v2.runBackwards, !R2 || E2 && !v2.stagger) {
      if (g2 = (c2 = I2[0] ? Tt(I2[0]).harness : 0) && v2[c2.prop], n2 = zt(v2, dt), P2 && (qt(P2.render(-1, true)), P2._lazy = 0), x2) if (qt(e2._startAt = ai.set(I2, Lt({ data: "isStart", overwrite: false, parent: D2, immediateRender: true, lazy: G(w2), startAt: null, delay: 0, onUpdate: T2, onUpdateParams: k2, callbackScope: C2, stagger: 0 }, x2))), i2 < 0 && !b2 && !M2 && e2._startAt.render(-1, true), b2) {
        if (i2 > 0 && !M2 && (e2._startAt = 0), A2 && i2 <= 0) return void (i2 && (e2._zTime = i2));
      } else false === M2 && (e2._startAt = 0);
      else if (S2 && A2) if (P2) !M2 && (e2._startAt = 0);
      else if (i2 && (b2 = false), s2 = Lt({ overwrite: false, data: "isFromStart", lazy: b2 && G(w2), immediateRender: b2, stagger: 0, parent: D2 }, n2), g2 && (s2[c2.prop] = g2), qt(e2._startAt = ai.set(I2, s2)), i2 < 0 && e2._startAt.render(-1, true), e2._zTime = i2, b2) {
        if (!i2) return;
      } else t10(e2._startAt, 1e-8);
      for (e2._pt = e2._ptCache = 0, w2 = A2 && G(w2) || w2 && !A2, r2 = 0; r2 < I2.length; r2++) {
        if (f2 = (o2 = I2[r2])._gsap || wt(I2)[r2]._gsap, e2._ptLookup[r2] = d2 = {}, gt[f2.id] && mt.length && At(), m2 = L2 === I2 ? r2 : L2.indexOf(o2), c2 && false !== (p2 = new c2()).init(o2, g2 || n2, e2, m2, L2) && (e2._pt = a2 = new xi(e2._pt, o2, p2.name, 0, 1, p2.render, p2, 0, p2.priority), p2._props.forEach((function(t21) {
          d2[t21] = a2;
        })), p2.priority && (l2 = 1)), !c2 || g2) for (s2 in n2) _t[s2] && (p2 = ti(s2, n2, e2, m2, o2, L2)) ? p2.priority && (l2 = 1) : d2[s2] = a2 = Ke.call(e2, o2, s2, "get", n2[s2], m2, L2, 0, v2.stringFilter);
        e2._op && e2._op[r2] && e2.kill(o2, e2._op[r2]), B2 && e2._pt && ($e = e2, h.killTweensOf(o2, d2, e2.globalTime(i2)), _2 = !e2.parent, $e = 0), e2._pt && w2 && (gt[f2.id] = 1);
      }
      l2 && yi(e2), e2._onInit && e2._onInit(e2);
    }
    e2._onUpdate = T2, e2._initted = (!e2._op || e2._pt) && !_2, E2 && i2 <= 0 && R2.render(1e8, true, true);
  };
  var ii = function(t21, e2, i2, n2) {
    var r2, s2, a2 = e2.ease || n2 || "power1.inOut";
    if (K(e2)) s2 = i2[t21] || (i2[t21] = []), e2.forEach((function(t22, i3) {
      return s2.push({ t: i3 / (e2.length - 1) * 100, v: t22, e: a2 });
    }));
    else for (r2 in e2) s2 = i2[r2] || (i2[r2] = []), "ease" === r2 || s2.push({ t: parseFloat(t21), v: e2[r2], e: a2 });
  };
  var ni = function(t21, e2, i2, n2, r2) {
    return U(t21) ? t21.call(e2, i2, n2, r2) : j(t21) && ~t21.indexOf("random(") ? xe(t21) : t21;
  };
  var ri = bt + "repeat,repeatDelay,yoyo,repeatRefresh,yoyoEase,autoRevert";
  var si = {};
  Ct(ri + ",id,stagger,delay,duration,paused,scrollTrigger", (function(t21) {
    return si[t21] = 1;
  }));
  var ai = (function(t21) {
    function e2(e3, i3, n2, r2) {
      var s2;
      "number" == typeof i3 && (n2.duration = i3, i3 = n2, n2 = null);
      var o2, l2, f2, c2, p2, d2, m2, g2, _2 = (s2 = t21.call(this, r2 ? i3 : Ft(i3)) || this).vars, v2 = _2.duration, y2 = _2.delay, x2 = _2.immediateRender, b2 = _2.stagger, w2 = _2.overwrite, T2 = _2.keyframes, k2 = _2.defaults, C2 = _2.scrollTrigger, S2 = _2.yoyoEase, O2 = i3.parent || h, E2 = (K(e3) || Z(e3) ? W(e3[0]) : "length" in i3) ? [e3] : pe(e3);
      if (s2._targets = E2.length ? wt(E2) : ft("GSAP target " + e3 + " not found. https://greensock.com", !R.nullTargetWarn) || [], s2._ptLookup = [], s2._overwrite = w2, T2 || b2 || J(v2) || J(y2)) {
        if (i3 = s2.vars, (o2 = s2.timeline = new Ge({ data: "nested", defaults: k2 || {} })).kill(), o2.parent = o2._dp = a(s2), o2._start = 0, b2 || J(v2) || J(y2)) {
          if (c2 = E2.length, m2 = b2 && me(b2), Q(b2)) for (p2 in b2) ~ri.indexOf(p2) && (g2 || (g2 = {}), g2[p2] = b2[p2]);
          for (l2 = 0; l2 < c2; l2++) (f2 = zt(i3, si)).stagger = 0, S2 && (f2.yoyoEase = S2), g2 && Bt(f2, g2), d2 = E2[l2], f2.duration = +ni(v2, a(s2), l2, d2, E2), f2.delay = (+ni(y2, a(s2), l2, d2, E2) || 0) - s2._delay, !b2 && 1 === c2 && f2.delay && (s2._delay = y2 = f2.delay, s2._start += y2, f2.delay = 0), o2.to(d2, f2, m2 ? m2(l2, d2, E2) : 0), o2._ease = Re.none;
          o2.duration() ? v2 = y2 = 0 : s2.timeline = 0;
        } else if (T2) {
          Ft(Lt(o2.vars.defaults, { ease: "none" })), o2._ease = Xe(T2.ease || i3.ease || "none");
          var M2, A2, P2, I2 = 0;
          if (K(T2)) T2.forEach((function(t22) {
            return o2.to(E2, t22, ">");
          }));
          else {
            for (p2 in f2 = {}, T2) "ease" === p2 || "easeEach" === p2 || ii(p2, T2[p2], f2, T2.easeEach);
            for (p2 in f2) for (M2 = f2[p2].sort((function(t22, e4) {
              return t22.t - e4.t;
            })), I2 = 0, l2 = 0; l2 < M2.length; l2++) (P2 = { ease: (A2 = M2[l2]).e, duration: (A2.t - (l2 ? M2[l2 - 1].t : 0)) / 100 * v2 })[p2] = A2.v, o2.to(E2, P2, I2), I2 += P2.duration;
            o2.duration() < v2 && o2.to({}, { duration: v2 - o2.duration() });
          }
        }
        v2 || s2.duration(v2 = o2.duration());
      } else s2.timeline = 0;
      return true !== w2 || u || ($e = a(s2), h.killTweensOf(E2), $e = 0), Jt(O2, a(s2), n2), i3.reversed && s2.reverse(), i3.paused && s2.paused(true), (x2 || !v2 && !T2 && s2._start === Ot(O2._time) && G(x2) && jt(a(s2)) && "nested" !== O2.data) && (s2._tTime = -1e-8, s2.render(Math.max(0, -y2))), C2 && Zt(a(s2), C2), s2;
    }
    o(e2, t21);
    var i2 = e2.prototype;
    return i2.render = function(t22, e3, i3) {
      var n2, r2, s2, a2, o2, u2, h2, l2, f2, c2 = this._time, p2 = this._tDur, d2 = this._dur, m2 = t22 > p2 - 1e-8 && t22 >= 0 ? p2 : t22 < 1e-8 ? 0 : t22;
      if (d2) {
        if (m2 !== this._tTime || !t22 || i3 || !this._initted && this._tTime || this._startAt && this._zTime < 0 != t22 < 0) {
          if (n2 = m2, l2 = this.timeline, this._repeat) {
            if (a2 = d2 + this._rDelay, this._repeat < -1 && t22 < 0) return this.totalTime(100 * a2 + t22, e3, i3);
            if (n2 = Ot(m2 % a2), m2 === p2 ? (s2 = this._repeat, n2 = d2) : ((s2 = ~~(m2 / a2)) && s2 === m2 / a2 && (n2 = d2, s2--), n2 > d2 && (n2 = d2)), (u2 = this._yoyo && 1 & s2) && (f2 = this._yEase, n2 = d2 - n2), o2 = Wt(this._tTime, a2), n2 === c2 && !i3 && this._initted) return this._tTime = m2, this;
            s2 !== o2 && (l2 && this._yEase && qe(l2, u2), !this.vars.repeatRefresh || u2 || this._lock || (this._lock = i3 = 1, this.render(Ot(a2 * s2), true).invalidate()._lock = 0));
          }
          if (!this._initted) {
            if (Kt(this, t22 < 0 ? t22 : n2, i3, e3)) return this._tTime = 0, this;
            if (c2 !== this._time) return this;
            if (d2 !== this._dur) return this.render(t22, e3, i3);
          }
          if (this._tTime = m2, this._time = n2, !this._act && this._ts && (this._act = 1, this._lazy = 0), this.ratio = h2 = (f2 || this._ease)(n2 / d2), this._from && (this.ratio = h2 = 1 - h2), n2 && !c2 && !e3 && (Te(this, "onStart"), this._tTime !== m2)) return this;
          for (r2 = this._pt; r2; ) r2.r(h2, r2.d), r2 = r2._next;
          l2 && l2.render(t22 < 0 ? t22 : !n2 && u2 ? -1e-8 : l2._dur * l2._ease(n2 / this._dur), e3, i3) || this._startAt && (this._zTime = t22), this._onUpdate && !e3 && (t22 < 0 && this._startAt && this._startAt.render(t22, true, i3), Te(this, "onUpdate")), this._repeat && s2 !== o2 && this.vars.onRepeat && !e3 && this.parent && Te(this, "onRepeat"), m2 !== this._tDur && m2 || this._tTime !== m2 || (t22 < 0 && this._startAt && !this._onUpdate && this._startAt.render(t22, true, true), (t22 || !d2) && (m2 === this._tDur && this._ts > 0 || !m2 && this._ts < 0) && qt(this, 1), e3 || t22 < 0 && !c2 || !m2 && !c2 || (Te(this, m2 === p2 ? "onComplete" : "onReverseComplete", true), this._prom && !(m2 < p2 && this.timeScale() > 0) && this._prom()));
        }
      } else !(function(t23, e4, i4, n3) {
        var r3, s3, a3, o3 = t23.ratio, u3 = e4 < 0 || !e4 && (!t23._start && te(t23) && (t23._initted || !ee(t23)) || (t23._ts < 0 || t23._dp._ts < 0) && !ee(t23)) ? 0 : 1, h3 = t23._rDelay, l3 = 0;
        if (h3 && t23._repeat && (l3 = ue(0, t23._tDur, e4), s3 = Wt(l3, h3), t23._yoyo && 1 & s3 && (u3 = 1 - u3), s3 !== Wt(t23._tTime, h3) && (o3 = 1 - u3, t23.vars.repeatRefresh && t23._initted && t23.invalidate())), u3 !== o3 || n3 || 1e-8 === t23._zTime || !e4 && t23._zTime) {
          if (!t23._initted && Kt(t23, e4, n3, i4)) return;
          for (a3 = t23._zTime, t23._zTime = e4 || (i4 ? 1e-8 : 0), i4 || (i4 = e4 && !a3), t23.ratio = u3, t23._from && (u3 = 1 - u3), t23._time = 0, t23._tTime = l3, r3 = t23._pt; r3; ) r3.r(u3, r3.d), r3 = r3._next;
          t23._startAt && e4 < 0 && t23._startAt.render(e4, true, true), t23._onUpdate && !i4 && Te(t23, "onUpdate"), l3 && t23._repeat && !i4 && t23.parent && Te(t23, "onRepeat"), (e4 >= t23._tDur || e4 < 0) && t23.ratio === u3 && (u3 && qt(t23, 1), i4 || (Te(t23, u3 ? "onComplete" : "onReverseComplete", true), t23._prom && t23._prom()));
        } else t23._zTime || (t23._zTime = e4);
      })(this, t22, e3, i3);
      return this;
    }, i2.targets = function() {
      return this._targets;
    }, i2.invalidate = function() {
      return this._pt = this._op = this._startAt = this._onUpdate = this._lazy = this.ratio = 0, this._ptLookup = [], this.timeline && this.timeline.invalidate(), t21.prototype.invalidate.call(this);
    }, i2.resetTo = function(t22, e3, i3, n2) {
      g || Le.wake(), this._ts || this.play();
      var r2 = Math.min(this._dur, (this._dp._time - this._start) * this._ts);
      return this._initted || ei(this, r2), (function(t23, e4, i4, n3, r3, s2, a2) {
        var o2, u2, h2, l2 = (t23._pt && t23._ptCache || (t23._ptCache = {}))[e4];
        if (!l2) for (l2 = t23._ptCache[e4] = [], u2 = t23._ptLookup, h2 = t23._targets.length; h2--; ) {
          if ((o2 = u2[h2][e4]) && o2.d && o2.d._pt) for (o2 = o2.d._pt; o2 && o2.p !== e4; ) o2 = o2._next;
          if (!o2) return Je = 1, t23.vars[e4] = "+=0", ei(t23, a2), Je = 0, 1;
          l2.push(o2);
        }
        for (h2 = l2.length; h2--; ) (o2 = l2[h2]).s = !n3 && 0 !== n3 || r3 ? o2.s + (n3 || 0) + s2 * o2.c : n3, o2.c = i4 - o2.s, o2.e && (o2.e = St(i4) + he(o2.e)), o2.b && (o2.b = o2.s + he(o2.b));
      })(this, t22, e3, i3, n2, this._ease(r2 / this._dur), r2) ? this.resetTo(t22, e3, i3, n2) : (Gt(this, 0), this.parent || Vt(this._dp, this, "_first", "_last", this._dp._sort ? "_start" : 0), this.render(0));
    }, i2.kill = function(t22, e3) {
      if (void 0 === e3 && (e3 = "all"), !(t22 || e3 && "all" !== e3)) return this._lazy = this._pt = 0, this.parent ? ke(this) : this;
      if (this.timeline) {
        var i3 = this.timeline.totalDuration();
        return this.timeline.killTweensOf(t22, e3, $e && true !== $e.vars.overwrite)._first || ke(this), this.parent && i3 !== this.timeline.totalDuration() && ie(this, this._dur * this.timeline._tDur / i3, 0, 1), this;
      }
      var n2, r2, s2, a2, o2, u2, h2, l2 = this._targets, f2 = t22 ? pe(t22) : l2, c2 = this._ptLookup, p2 = this._pt;
      if ((!e3 || "all" === e3) && (function(t23, e4) {
        for (var i4 = t23.length, n3 = i4 === e4.length; n3 && i4-- && t23[i4] === e4[i4]; ) ;
        return i4 < 0;
      })(l2, f2)) return "all" === e3 && (this._pt = 0), ke(this);
      for (n2 = this._op = this._op || [], "all" !== e3 && (j(e3) && (o2 = {}, Ct(e3, (function(t23) {
        return o2[t23] = 1;
      })), e3 = o2), e3 = (function(t23, e4) {
        var i4, n3, r3, s3, a3 = t23[0] ? Tt(t23[0]).harness : 0, o3 = a3 && a3.aliases;
        if (!o3) return e4;
        for (n3 in i4 = Bt({}, e4), o3) if (n3 in i4) for (r3 = (s3 = o3[n3].split(",")).length; r3--; ) i4[s3[r3]] = i4[n3];
        return i4;
      })(l2, e3)), h2 = l2.length; h2--; ) if (~f2.indexOf(l2[h2])) for (o2 in r2 = c2[h2], "all" === e3 ? (n2[h2] = e3, a2 = r2, s2 = {}) : (s2 = n2[h2] = n2[h2] || {}, a2 = e3), a2) (u2 = r2 && r2[o2]) && ("kill" in u2.d && true !== u2.d.kill(o2) || Nt(this, u2, "_pt"), delete r2[o2]), "all" !== s2 && (s2[o2] = 1);
      return this._initted && !this._pt && p2 && ke(this), this;
    }, e2.to = function(t22, i3) {
      return new e2(t22, i3, arguments[2]);
    }, e2.from = function(t22, e3) {
      return ae(1, arguments);
    }, e2.delayedCall = function(t22, i3, n2, r2) {
      return new e2(i3, 0, { immediateRender: false, lazy: false, overwrite: false, delay: t22, onComplete: i3, onReverseComplete: i3, onCompleteParams: n2, onReverseCompleteParams: n2, callbackScope: r2 });
    }, e2.fromTo = function(t22, e3, i3) {
      return ae(2, arguments);
    }, e2.set = function(t22, i3) {
      return i3.duration = 0, i3.repeatDelay || (i3.repeat = 0), new e2(t22, i3);
    }, e2.killTweensOf = function(t22, e3, i3) {
      return h.killTweensOf(t22, e3, i3);
    }, e2;
  })(Qe);
  Lt(ai.prototype, { _targets: [], _lazy: 0, _startAt: 0, _op: 0, _onInit: 0 }), Ct("staggerTo,staggerFrom,staggerFromTo", (function(t21) {
    ai[t21] = function() {
      var e2 = new Ge(), i2 = le.call(arguments, 0);
      return i2.splice("staggerFromTo" === t21 ? 5 : 4, 0, 0), e2[t21].apply(e2, i2);
    };
  }));
  var oi = function(t21, e2, i2) {
    return t21[e2] = i2;
  };
  var ui = function(t21, e2, i2) {
    return t21[e2](i2);
  };
  var hi = function(t21, e2, i2, n2) {
    return t21[e2](n2.fp, i2);
  };
  var li = function(t21, e2, i2) {
    return t21.setAttribute(e2, i2);
  };
  var fi = function(t21, e2) {
    return U(t21[e2]) ? ui : H(t21[e2]) && t21.setAttribute ? li : oi;
  };
  var ci = function(t21, e2) {
    return e2.set(e2.t, e2.p, Math.round(1e6 * (e2.s + e2.c * t21)) / 1e6, e2);
  };
  var pi = function(t21, e2) {
    return e2.set(e2.t, e2.p, !!(e2.s + e2.c * t21), e2);
  };
  var di = function(t21, e2) {
    var i2 = e2._pt, n2 = "";
    if (!t21 && e2.b) n2 = e2.b;
    else if (1 === t21 && e2.e) n2 = e2.e;
    else {
      for (; i2; ) n2 = i2.p + (i2.m ? i2.m(i2.s + i2.c * t21) : Math.round(1e4 * (i2.s + i2.c * t21)) / 1e4) + n2, i2 = i2._next;
      n2 += e2.c;
    }
    e2.set(e2.t, e2.p, n2, e2);
  };
  var mi = function(t21, e2) {
    for (var i2 = e2._pt; i2; ) i2.r(t21, i2.d), i2 = i2._next;
  };
  var gi = function(t21, e2, i2, n2) {
    for (var r2, s2 = this._pt; s2; ) r2 = s2._next, s2.p === n2 && s2.modifier(t21, e2, i2), s2 = r2;
  };
  var _i = function(t21) {
    for (var e2, i2, n2 = this._pt; n2; ) i2 = n2._next, n2.p === t21 && !n2.op || n2.op === t21 ? Nt(this, n2, "_pt") : n2.dep || (e2 = 1), n2 = i2;
    return !e2;
  };
  var vi = function(t21, e2, i2, n2) {
    n2.mSet(t21, e2, n2.m.call(n2.tween, i2, n2.mt), n2);
  };
  var yi = function(t21) {
    for (var e2, i2, n2, r2, s2 = t21._pt; s2; ) {
      for (e2 = s2._next, i2 = n2; i2 && i2.pr > s2.pr; ) i2 = i2._next;
      (s2._prev = i2 ? i2._prev : r2) ? s2._prev._next = s2 : n2 = s2, (s2._next = i2) ? i2._prev = s2 : r2 = s2, s2 = e2;
    }
    t21._pt = n2;
  };
  var xi = (function() {
    function t21(t22, e2, i2, n2, r2, s2, a2, o2, u2) {
      this.t = e2, this.s = n2, this.c = r2, this.p = i2, this.r = s2 || ci, this.d = a2 || this, this.set = o2 || oi, this.pr = u2 || 0, this._next = t22, t22 && (t22._prev = this);
    }
    return t21.prototype.modifier = function(t22, e2, i2) {
      this.mSet = this.mSet || this.set, this.set = vi, this.m = t22, this.mt = i2, this.tween = e2;
    }, t21;
  })();
  Ct(bt + "parent,duration,ease,delay,overwrite,runBackwards,startAt,yoyo,immediateRender,repeat,repeatDelay,data,paused,reversed,lazy,callbackScope,stringFilter,id,yoyoEase,stagger,inherit,repeatRefresh,keyframes,autoRevert,scrollTrigger", (function(t21) {
    return dt[t21] = 1;
  })), ot.TweenMax = ot.TweenLite = ai, ot.TimelineLite = ot.TimelineMax = Ge, h = new Ge({ sortChildren: false, defaults: z, autoRemoveChildren: true, id: "root", smoothChildTiming: true }), R.stringFilter = De;
  var bi = { registerPlugin: function() {
    for (var t21 = arguments.length, e2 = new Array(t21), i2 = 0; i2 < t21; i2++) e2[i2] = arguments[i2];
    e2.forEach((function(t22) {
      return Ce(t22);
    }));
  }, timeline: function(t21) {
    return new Ge(t21);
  }, getTweensOf: function(t21, e2) {
    return h.getTweensOf(t21, e2);
  }, getProperty: function(t21, e2, i2, n2) {
    j(t21) && (t21 = pe(t21)[0]);
    var r2 = Tt(t21 || {}).get, s2 = i2 ? Dt : It;
    return "native" === i2 && (i2 = ""), t21 ? e2 ? s2((_t[e2] && _t[e2].get || r2)(t21, e2, i2, n2)) : function(e3, i3, n3) {
      return s2((_t[e3] && _t[e3].get || r2)(t21, e3, i3, n3));
    } : t21;
  }, quickSetter: function(t21, e2, i2) {
    if ((t21 = pe(t21)).length > 1) {
      var n2 = t21.map((function(t22) {
        return ki.quickSetter(t22, e2, i2);
      })), r2 = n2.length;
      return function(t22) {
        for (var e3 = r2; e3--; ) n2[e3](t22);
      };
    }
    t21 = t21[0] || {};
    var s2 = _t[e2], a2 = Tt(t21), o2 = a2.harness && (a2.harness.aliases || {})[e2] || e2, u2 = s2 ? function(e3) {
      var n3 = new s2();
      m._pt = 0, n3.init(t21, i2 ? e3 + i2 : e3, m, 0, [t21]), n3.render(1, n3), m._pt && mi(1, m);
    } : a2.set(t21, o2);
    return s2 ? u2 : function(e3) {
      return u2(t21, o2, i2 ? e3 + i2 : e3, a2, 1);
    };
  }, quickTo: function(t21, e2, i2) {
    var n2, r2 = ki.to(t21, Bt(((n2 = {})[e2] = "+=0.1", n2.paused = true, n2), i2 || {})), s2 = function(t22, i3, n3) {
      return r2.resetTo(e2, t22, i3, n3);
    };
    return s2.tween = r2, s2;
  }, isTweening: function(t21) {
    return h.getTweensOf(t21, true).length > 0;
  }, defaults: function(t21) {
    return t21 && t21.ease && (t21.ease = Xe(t21.ease, z.ease)), Rt(z, t21 || {});
  }, config: function(t21) {
    return Rt(R, t21 || {});
  }, registerEffect: function(t21) {
    var e2 = t21.name, i2 = t21.effect, n2 = t21.plugins, r2 = t21.defaults, s2 = t21.extendTimeline;
    (n2 || "").split(",").forEach((function(t22) {
      return t22 && !_t[t22] && !ot[t22] && ft(e2 + " effect requires " + t22 + " plugin.");
    })), vt[e2] = function(t22, e3, n3) {
      return i2(pe(t22), Lt(e3 || {}, r2), n3);
    }, s2 && (Ge.prototype[e2] = function(t22, i3, n3) {
      return this.add(vt[e2](t22, Q(i3) ? i3 : (n3 = i3) && {}, this), n3);
    });
  }, registerEase: function(t21, e2) {
    Re[t21] = Xe(e2);
  }, parseEase: function(t21, e2) {
    return arguments.length ? Xe(t21, e2) : Re;
  }, getById: function(t21) {
    return h.getById(t21);
  }, exportRoot: function(t21, e2) {
    void 0 === t21 && (t21 = {});
    var i2, n2, r2 = new Ge(t21);
    for (r2.smoothChildTiming = G(t21.smoothChildTiming), h.remove(r2), r2._dp = 0, r2._time = r2._tTime = h._time, i2 = h._first; i2; ) n2 = i2._next, !e2 && !i2._dur && i2 instanceof ai && i2.vars.onComplete === i2._targets[0] || Jt(r2, i2, i2._start - i2._delay), i2 = n2;
    return Jt(h, r2, 0), r2;
  }, utils: { wrap: function t11(e2, i2, n2) {
    var r2 = i2 - e2;
    return K(e2) ? ye(e2, t11(0, e2.length), i2) : oe(n2, (function(t21) {
      return (r2 + (t21 - e2) % r2) % r2 + e2;
    }));
  }, wrapYoyo: function t12(e2, i2, n2) {
    var r2 = i2 - e2, s2 = 2 * r2;
    return K(e2) ? ye(e2, t12(0, e2.length - 1), i2) : oe(n2, (function(t21) {
      return e2 + ((t21 = (s2 + (t21 - e2) % s2) % s2 || 0) > r2 ? s2 - t21 : t21);
    }));
  }, distribute: me, random: ve, snap: _e, normalize: function(t21, e2, i2) {
    return be(t21, e2, 0, 1, i2);
  }, getUnit: he, clamp: function(t21, e2, i2) {
    return oe(i2, (function(i3) {
      return ue(t21, e2, i3);
    }));
  }, splitColor: Ee, toArray: pe, selector: function(t21) {
    return t21 = pe(t21)[0] || ft("Invalid scope") || {}, function(e2) {
      var i2 = t21.current || t21.nativeElement || t21;
      return pe(e2, i2.querySelectorAll ? i2 : i2 === t21 ? ft("Invalid scope") || c.createElement("div") : t21);
    };
  }, mapRange: be, pipe: function() {
    for (var t21 = arguments.length, e2 = new Array(t21), i2 = 0; i2 < t21; i2++) e2[i2] = arguments[i2];
    return function(t22) {
      return e2.reduce((function(t23, e3) {
        return e3(t23);
      }), t22);
    };
  }, unitize: function(t21, e2) {
    return function(i2) {
      return t21(parseFloat(i2)) + (e2 || he(i2));
    };
  }, interpolate: function t13(e2, i2, n2, r2) {
    var s2 = isNaN(e2 + i2) ? 0 : function(t21) {
      return (1 - t21) * e2 + t21 * i2;
    };
    if (!s2) {
      var a2, o2, u2, h2, l2, f2 = j(e2), c2 = {};
      if (true === n2 && (r2 = 1) && (n2 = null), f2) e2 = { p: e2 }, i2 = { p: i2 };
      else if (K(e2) && !K(i2)) {
        for (u2 = [], h2 = e2.length, l2 = h2 - 2, o2 = 1; o2 < h2; o2++) u2.push(t13(e2[o2 - 1], e2[o2]));
        h2--, s2 = function(t21) {
          t21 *= h2;
          var e3 = Math.min(l2, ~~t21);
          return u2[e3](t21 - e3);
        }, n2 = i2;
      } else r2 || (e2 = Bt(K(e2) ? [] : {}, e2));
      if (!u2) {
        for (a2 in i2) Ke.call(c2, e2, a2, "get", i2[a2]);
        s2 = function(t21) {
          return mi(t21, c2) || (f2 ? e2.p : e2);
        };
      }
    }
    return oe(n2, s2);
  }, shuffle: de }, install: ht, effects: vt, ticker: Le, updateRoot: Ge.updateRoot, plugins: _t, globalTimeline: h, core: { PropTween: xi, globals: ct, Tween: ai, Timeline: Ge, Animation: Qe, getCache: Tt, _removeLinkedListItem: Nt, suppressOverwrites: function(t21) {
    return u = t21;
  } } };
  Ct("to,from,fromTo,delayedCall,set,killTweensOf", (function(t21) {
    return bi[t21] = ai[t21];
  })), Le.add(Ge.updateRoot), m = bi.to({}, { duration: 0 });
  var wi = function(t21, e2) {
    for (var i2 = t21._pt; i2 && i2.p !== e2 && i2.op !== e2 && i2.fp !== e2; ) i2 = i2._next;
    return i2;
  };
  var Ti = function(t21, e2) {
    return { name: t21, rawVars: 1, init: function(t22, i2, n2) {
      n2._onInit = function(t23) {
        var n3, r2;
        if (j(i2) && (n3 = {}, Ct(i2, (function(t24) {
          return n3[t24] = 1;
        })), i2 = n3), e2) {
          for (r2 in n3 = {}, i2) n3[r2] = e2(i2[r2]);
          i2 = n3;
        }
        !(function(t24, e3) {
          var i3, n4, r3, s2 = t24._targets;
          for (i3 in e3) for (n4 = s2.length; n4--; ) (r3 = t24._ptLookup[n4][i3]) && (r3 = r3.d) && (r3._pt && (r3 = wi(r3, i3)), r3 && r3.modifier && r3.modifier(e3[i3], t24, s2[n4], i3));
        })(t23, i2);
      };
    } };
  };
  var ki = bi.registerPlugin({ name: "attr", init: function(t21, e2, i2, n2, r2) {
    var s2, a2;
    for (s2 in e2) (a2 = this.add(t21, "setAttribute", (t21.getAttribute(s2) || 0) + "", e2[s2], n2, r2, 0, 0, s2)) && (a2.op = s2), this._props.push(s2);
  } }, { name: "endArray", init: function(t21, e2) {
    for (var i2 = e2.length; i2--; ) this.add(t21, i2, t21[i2] || 0, e2[i2]);
  } }, Ti("roundProps", ge), Ti("modifiers"), Ti("snap", _e)) || bi;
  ai.version = Ge.version = ki.version = "3.10.4", p = 1, $() && Be();
  Re.Power0, Re.Power1, Re.Power2, Re.Power3, Re.Power4, Re.Linear, Re.Quad, Re.Cubic, Re.Quart, Re.Quint, Re.Strong, Re.Elastic, Re.Back, Re.SteppedEase, Re.Bounce, Re.Sine, Re.Expo, Re.Circ;
  var Ci;
  var Si;
  var Oi;
  var Ei;
  var Mi;
  var Ai;
  var Pi;
  var Ii = {};
  var Di = 180 / Math.PI;
  var Li = Math.PI / 180;
  var Bi = Math.atan2;
  var Ri = /([A-Z])/g;
  var zi = /(left|right|width|margin|padding|x)/i;
  var Fi = /[\s,\(]\S/;
  var Vi = { autoAlpha: "opacity,visibility", scale: "scaleX,scaleY", alpha: "opacity" };
  var Ni = function(t21, e2) {
    return e2.set(e2.t, e2.p, Math.round(1e4 * (e2.s + e2.c * t21)) / 1e4 + e2.u, e2);
  };
  var qi = function(t21, e2) {
    return e2.set(e2.t, e2.p, 1 === t21 ? e2.e : Math.round(1e4 * (e2.s + e2.c * t21)) / 1e4 + e2.u, e2);
  };
  var Xi = function(t21, e2) {
    return e2.set(e2.t, e2.p, t21 ? Math.round(1e4 * (e2.s + e2.c * t21)) / 1e4 + e2.u : e2.b, e2);
  };
  var Yi = function(t21, e2) {
    var i2 = e2.s + e2.c * t21;
    e2.set(e2.t, e2.p, ~~(i2 + (i2 < 0 ? -0.5 : 0.5)) + e2.u, e2);
  };
  var ji = function(t21, e2) {
    return e2.set(e2.t, e2.p, t21 ? e2.e : e2.b, e2);
  };
  var Ui = function(t21, e2) {
    return e2.set(e2.t, e2.p, 1 !== t21 ? e2.b : e2.e, e2);
  };
  var Wi = function(t21, e2, i2) {
    return t21.style[e2] = i2;
  };
  var Hi = function(t21, e2, i2) {
    return t21.style.setProperty(e2, i2);
  };
  var Qi = function(t21, e2, i2) {
    return t21._gsap[e2] = i2;
  };
  var Gi = function(t21, e2, i2) {
    return t21._gsap.scaleX = t21._gsap.scaleY = i2;
  };
  var $i = function(t21, e2, i2, n2, r2) {
    var s2 = t21._gsap;
    s2.scaleX = s2.scaleY = i2, s2.renderTransform(r2, s2);
  };
  var Ji = function(t21, e2, i2, n2, r2) {
    var s2 = t21._gsap;
    s2[e2] = i2, s2.renderTransform(r2, s2);
  };
  var Zi = "transform";
  var Ki = Zi + "Origin";
  var tn = function(t21, e2) {
    var i2 = Si.createElementNS ? Si.createElementNS((e2 || "http://www.w3.org/1999/xhtml").replace(/^https/, "http"), t21) : Si.createElement(t21);
    return i2.style ? i2 : Si.createElement(t21);
  };
  var en = function t14(e2, i2, n2) {
    var r2 = getComputedStyle(e2);
    return r2[i2] || r2.getPropertyValue(i2.replace(Ri, "-$1").toLowerCase()) || r2.getPropertyValue(i2) || !n2 && t14(e2, rn(i2) || i2, 1) || "";
  };
  var nn = "O,Moz,ms,Ms,Webkit".split(",");
  var rn = function(t21, e2, i2) {
    var n2 = (e2 || Mi).style, r2 = 5;
    if (t21 in n2 && !i2) return t21;
    for (t21 = t21.charAt(0).toUpperCase() + t21.substr(1); r2-- && !(nn[r2] + t21 in n2); ) ;
    return r2 < 0 ? null : (3 === r2 ? "ms" : r2 >= 0 ? nn[r2] : "") + t21;
  };
  var sn = function() {
    "undefined" != typeof window && window.document && (Ci = window, Si = Ci.document, Oi = Si.documentElement, Mi = tn("div") || { style: {} }, tn("div"), Zi = rn(Zi), Ki = Zi + "Origin", Mi.style.cssText = "border-width:0;line-height:0;position:absolute;padding:0", Pi = !!rn("perspective"), Ei = 1);
  };
  var an = function t15(e2) {
    var i2, n2 = tn("svg", this.ownerSVGElement && this.ownerSVGElement.getAttribute("xmlns") || "http://www.w3.org/2000/svg"), r2 = this.parentNode, s2 = this.nextSibling, a2 = this.style.cssText;
    if (Oi.appendChild(n2), n2.appendChild(this), this.style.display = "block", e2) try {
      i2 = this.getBBox(), this._gsapBBox = this.getBBox, this.getBBox = t15;
    } catch (t21) {
    }
    else this._gsapBBox && (i2 = this._gsapBBox());
    return r2 && (s2 ? r2.insertBefore(this, s2) : r2.appendChild(this)), Oi.removeChild(n2), this.style.cssText = a2, i2;
  };
  var on = function(t21, e2) {
    for (var i2 = e2.length; i2--; ) if (t21.hasAttribute(e2[i2])) return t21.getAttribute(e2[i2]);
  };
  var un = function(t21) {
    var e2;
    try {
      e2 = t21.getBBox();
    } catch (i2) {
      e2 = an.call(t21, true);
    }
    return e2 && (e2.width || e2.height) || t21.getBBox === an || (e2 = an.call(t21, true)), !e2 || e2.width || e2.x || e2.y ? e2 : { x: +on(t21, ["x", "cx", "x1"]) || 0, y: +on(t21, ["y", "cy", "y1"]) || 0, width: 0, height: 0 };
  };
  var hn = function(t21) {
    return !(!t21.getCTM || t21.parentNode && !t21.ownerSVGElement || !un(t21));
  };
  var ln = function(t21, e2) {
    if (e2) {
      var i2 = t21.style;
      e2 in Ii && e2 !== Ki && (e2 = Zi), i2.removeProperty ? ("ms" !== e2.substr(0, 2) && "webkit" !== e2.substr(0, 6) || (e2 = "-" + e2), i2.removeProperty(e2.replace(Ri, "-$1").toLowerCase())) : i2.removeAttribute(e2);
    }
  };
  var fn = function(t21, e2, i2, n2, r2, s2) {
    var a2 = new xi(t21._pt, e2, i2, 0, 1, s2 ? Ui : ji);
    return t21._pt = a2, a2.b = n2, a2.e = r2, t21._props.push(i2), a2;
  };
  var cn = { deg: 1, rad: 1, turn: 1 };
  var pn = function t16(e2, i2, n2, r2) {
    var s2, a2, o2, u2, h2 = parseFloat(n2) || 0, l2 = (n2 + "").trim().substr((h2 + "").length) || "px", f2 = Mi.style, c2 = zi.test(i2), p2 = "svg" === e2.tagName.toLowerCase(), d2 = (p2 ? "client" : "offset") + (c2 ? "Width" : "Height"), m2 = 100, g2 = "px" === r2, _2 = "%" === r2;
    return r2 === l2 || !h2 || cn[r2] || cn[l2] ? h2 : ("px" !== l2 && !g2 && (h2 = t16(e2, i2, n2, "px")), u2 = e2.getCTM && hn(e2), !_2 && "%" !== l2 || !Ii[i2] && !~i2.indexOf("adius") ? (f2[c2 ? "width" : "height"] = m2 + (g2 ? l2 : r2), a2 = ~i2.indexOf("adius") || "em" === r2 && e2.appendChild && !p2 ? e2 : e2.parentNode, u2 && (a2 = (e2.ownerSVGElement || {}).parentNode), a2 && a2 !== Si && a2.appendChild || (a2 = Si.body), (o2 = a2._gsap) && _2 && o2.width && c2 && o2.time === Le.time ? St(h2 / o2.width * m2) : ((_2 || "%" === l2) && (f2.position = en(e2, "position")), a2 === e2 && (f2.position = "static"), a2.appendChild(Mi), s2 = Mi[d2], a2.removeChild(Mi), f2.position = "absolute", c2 && _2 && ((o2 = Tt(a2)).time = Le.time, o2.width = a2[d2]), St(g2 ? s2 * h2 / m2 : s2 && h2 ? m2 / s2 * h2 : 0))) : (s2 = u2 ? e2.getBBox()[c2 ? "width" : "height"] : e2[d2], St(_2 ? h2 / s2 * m2 : h2 / 100 * s2)));
  };
  var dn = function(t21, e2, i2, n2) {
    var r2;
    return Ei || sn(), e2 in Vi && "transform" !== e2 && ~(e2 = Vi[e2]).indexOf(",") && (e2 = e2.split(",")[0]), Ii[e2] && "transform" !== e2 ? (r2 = Cn(t21, n2), r2 = "transformOrigin" !== e2 ? r2[e2] : r2.svg ? r2.origin : Sn(en(t21, Ki)) + " " + r2.zOrigin + "px") : (!(r2 = t21.style[e2]) || "auto" === r2 || n2 || ~(r2 + "").indexOf("calc(")) && (r2 = vn[e2] && vn[e2](t21, e2, i2) || en(t21, e2) || kt(t21, e2) || ("opacity" === e2 ? 1 : 0)), i2 && !~(r2 + "").trim().indexOf(" ") ? pn(t21, e2, r2, i2) + i2 : r2;
  };
  var mn = function(t21, e2, i2, n2) {
    if (!i2 || "none" === i2) {
      var r2 = rn(e2, t21, 1), s2 = r2 && en(t21, r2, 1);
      s2 && s2 !== i2 ? (e2 = r2, i2 = s2) : "borderColor" === e2 && (i2 = en(t21, "borderTopColor"));
    }
    var a2, o2, u2, h2, l2, f2, c2, p2, d2, m2, g2, _2 = new xi(this._pt, t21.style, e2, 0, 1, di), v2 = 0, y2 = 0;
    if (_2.b = i2, _2.e = n2, i2 += "", "auto" === (n2 += "") && (t21.style[e2] = n2, n2 = en(t21, e2) || n2, t21.style[e2] = i2), De(a2 = [i2, n2]), n2 = a2[1], u2 = (i2 = a2[0]).match(it) || [], (n2.match(it) || []).length) {
      for (; o2 = it.exec(n2); ) c2 = o2[0], d2 = n2.substring(v2, o2.index), l2 ? l2 = (l2 + 1) % 5 : "rgba(" !== d2.substr(-5) && "hsla(" !== d2.substr(-5) || (l2 = 1), c2 !== (f2 = u2[y2++] || "") && (h2 = parseFloat(f2) || 0, g2 = f2.substr((h2 + "").length), "=" === c2.charAt(1) && (c2 = Et(h2, c2) + g2), p2 = parseFloat(c2), m2 = c2.substr((p2 + "").length), v2 = it.lastIndex - m2.length, m2 || (m2 = m2 || R.units[e2] || g2, v2 === n2.length && (n2 += m2, _2.e += m2)), g2 !== m2 && (h2 = pn(t21, e2, f2, m2) || 0), _2._pt = { _next: _2._pt, p: d2 || 1 === y2 ? d2 : ",", s: h2, c: p2 - h2, m: l2 && l2 < 4 || "zIndex" === e2 ? Math.round : 0 });
      _2.c = v2 < n2.length ? n2.substring(v2, n2.length) : "";
    } else _2.r = "display" === e2 && "none" === n2 ? Ui : ji;
    return rt.test(n2) && (_2.e = 0), this._pt = _2, _2;
  };
  var gn = { top: "0%", bottom: "100%", left: "0%", right: "100%", center: "50%" };
  var _n = function(t21, e2) {
    if (e2.tween && e2.tween._time === e2.tween._dur) {
      var i2, n2, r2, s2 = e2.t, a2 = s2.style, o2 = e2.u, u2 = s2._gsap;
      if ("all" === o2 || true === o2) a2.cssText = "", n2 = 1;
      else for (r2 = (o2 = o2.split(",")).length; --r2 > -1; ) i2 = o2[r2], Ii[i2] && (n2 = 1, i2 = "transformOrigin" === i2 ? Ki : Zi), ln(s2, i2);
      n2 && (ln(s2, Zi), u2 && (u2.svg && s2.removeAttribute("transform"), Cn(s2, 1), u2.uncache = 1));
    }
  };
  var vn = { clearProps: function(t21, e2, i2, n2, r2) {
    if ("isFromStart" !== r2.data) {
      var s2 = t21._pt = new xi(t21._pt, e2, i2, 0, 0, _n);
      return s2.u = n2, s2.pr = -10, s2.tween = r2, t21._props.push(i2), 1;
    }
  } };
  var yn = [1, 0, 0, 1, 0, 0];
  var xn = {};
  var bn = function(t21) {
    return "matrix(1, 0, 0, 1, 0, 0)" === t21 || "none" === t21 || !t21;
  };
  var wn = function(t21) {
    var e2 = en(t21, Zi);
    return bn(e2) ? yn : e2.substr(7).match(et).map(St);
  };
  var Tn = function(t21, e2) {
    var i2, n2, r2, s2, a2 = t21._gsap || Tt(t21), o2 = t21.style, u2 = wn(t21);
    return a2.svg && t21.getAttribute("transform") ? "1,0,0,1,0,0" === (u2 = [(r2 = t21.transform.baseVal.consolidate().matrix).a, r2.b, r2.c, r2.d, r2.e, r2.f]).join(",") ? yn : u2 : (u2 !== yn || t21.offsetParent || t21 === Oi || a2.svg || (r2 = o2.display, o2.display = "block", (i2 = t21.parentNode) && t21.offsetParent || (s2 = 1, n2 = t21.nextSibling, Oi.appendChild(t21)), u2 = wn(t21), r2 ? o2.display = r2 : ln(t21, "display"), s2 && (n2 ? i2.insertBefore(t21, n2) : i2 ? i2.appendChild(t21) : Oi.removeChild(t21))), e2 && u2.length > 6 ? [u2[0], u2[1], u2[4], u2[5], u2[12], u2[13]] : u2);
  };
  var kn = function(t21, e2, i2, n2, r2, s2) {
    var a2, o2, u2, h2 = t21._gsap, l2 = r2 || Tn(t21, true), f2 = h2.xOrigin || 0, c2 = h2.yOrigin || 0, p2 = h2.xOffset || 0, d2 = h2.yOffset || 0, m2 = l2[0], g2 = l2[1], _2 = l2[2], v2 = l2[3], y2 = l2[4], x2 = l2[5], b2 = e2.split(" "), w2 = parseFloat(b2[0]) || 0, T2 = parseFloat(b2[1]) || 0;
    i2 ? l2 !== yn && (o2 = m2 * v2 - g2 * _2) && (u2 = w2 * (-g2 / o2) + T2 * (m2 / o2) - (m2 * x2 - g2 * y2) / o2, w2 = w2 * (v2 / o2) + T2 * (-_2 / o2) + (_2 * x2 - v2 * y2) / o2, T2 = u2) : (w2 = (a2 = un(t21)).x + (~b2[0].indexOf("%") ? w2 / 100 * a2.width : w2), T2 = a2.y + (~(b2[1] || b2[0]).indexOf("%") ? T2 / 100 * a2.height : T2)), n2 || false !== n2 && h2.smooth ? (y2 = w2 - f2, x2 = T2 - c2, h2.xOffset = p2 + (y2 * m2 + x2 * _2) - y2, h2.yOffset = d2 + (y2 * g2 + x2 * v2) - x2) : h2.xOffset = h2.yOffset = 0, h2.xOrigin = w2, h2.yOrigin = T2, h2.smooth = !!n2, h2.origin = e2, h2.originIsAbsolute = !!i2, t21.style[Ki] = "0px 0px", s2 && (fn(s2, h2, "xOrigin", f2, w2), fn(s2, h2, "yOrigin", c2, T2), fn(s2, h2, "xOffset", p2, h2.xOffset), fn(s2, h2, "yOffset", d2, h2.yOffset)), t21.setAttribute("data-svg-origin", w2 + " " + T2);
  };
  var Cn = function(t21, e2) {
    var i2 = t21._gsap || new He(t21);
    if ("x" in i2 && !e2 && !i2.uncache) return i2;
    var n2, r2, s2, a2, o2, u2, h2, l2, f2, c2, p2, d2, m2, g2, _2, v2, y2, x2, b2, w2, T2, k2, C2, S2, O2, E2, M2, A2, P2, I2, D2, L2, B2 = t21.style, z2 = i2.scaleX < 0, F2 = "px", V2 = "deg", N2 = en(t21, Ki) || "0";
    return n2 = r2 = s2 = u2 = h2 = l2 = f2 = c2 = p2 = 0, a2 = o2 = 1, i2.svg = !(!t21.getCTM || !hn(t21)), g2 = Tn(t21, i2.svg), i2.svg && (S2 = (!i2.uncache || "0px 0px" === N2) && !e2 && t21.getAttribute("data-svg-origin"), kn(t21, S2 || N2, !!S2 || i2.originIsAbsolute, false !== i2.smooth, g2)), d2 = i2.xOrigin || 0, m2 = i2.yOrigin || 0, g2 !== yn && (x2 = g2[0], b2 = g2[1], w2 = g2[2], T2 = g2[3], n2 = k2 = g2[4], r2 = C2 = g2[5], 6 === g2.length ? (a2 = Math.sqrt(x2 * x2 + b2 * b2), o2 = Math.sqrt(T2 * T2 + w2 * w2), u2 = x2 || b2 ? Bi(b2, x2) * Di : 0, (f2 = w2 || T2 ? Bi(w2, T2) * Di + u2 : 0) && (o2 *= Math.abs(Math.cos(f2 * Li))), i2.svg && (n2 -= d2 - (d2 * x2 + m2 * w2), r2 -= m2 - (d2 * b2 + m2 * T2))) : (L2 = g2[6], I2 = g2[7], M2 = g2[8], A2 = g2[9], P2 = g2[10], D2 = g2[11], n2 = g2[12], r2 = g2[13], s2 = g2[14], h2 = (_2 = Bi(L2, P2)) * Di, _2 && (S2 = k2 * (v2 = Math.cos(-_2)) + M2 * (y2 = Math.sin(-_2)), O2 = C2 * v2 + A2 * y2, E2 = L2 * v2 + P2 * y2, M2 = k2 * -y2 + M2 * v2, A2 = C2 * -y2 + A2 * v2, P2 = L2 * -y2 + P2 * v2, D2 = I2 * -y2 + D2 * v2, k2 = S2, C2 = O2, L2 = E2), l2 = (_2 = Bi(-w2, P2)) * Di, _2 && (v2 = Math.cos(-_2), D2 = T2 * (y2 = Math.sin(-_2)) + D2 * v2, x2 = S2 = x2 * v2 - M2 * y2, b2 = O2 = b2 * v2 - A2 * y2, w2 = E2 = w2 * v2 - P2 * y2), u2 = (_2 = Bi(b2, x2)) * Di, _2 && (S2 = x2 * (v2 = Math.cos(_2)) + b2 * (y2 = Math.sin(_2)), O2 = k2 * v2 + C2 * y2, b2 = b2 * v2 - x2 * y2, C2 = C2 * v2 - k2 * y2, x2 = S2, k2 = O2), h2 && Math.abs(h2) + Math.abs(u2) > 359.9 && (h2 = u2 = 0, l2 = 180 - l2), a2 = St(Math.sqrt(x2 * x2 + b2 * b2 + w2 * w2)), o2 = St(Math.sqrt(C2 * C2 + L2 * L2)), _2 = Bi(k2, C2), f2 = Math.abs(_2) > 2e-4 ? _2 * Di : 0, p2 = D2 ? 1 / (D2 < 0 ? -D2 : D2) : 0), i2.svg && (S2 = t21.getAttribute("transform"), i2.forceCSS = t21.setAttribute("transform", "") || !bn(en(t21, Zi)), S2 && t21.setAttribute("transform", S2))), Math.abs(f2) > 90 && Math.abs(f2) < 270 && (z2 ? (a2 *= -1, f2 += u2 <= 0 ? 180 : -180, u2 += u2 <= 0 ? 180 : -180) : (o2 *= -1, f2 += f2 <= 0 ? 180 : -180)), e2 = e2 || i2.uncache, i2.x = n2 - ((i2.xPercent = n2 && (!e2 && i2.xPercent || (Math.round(t21.offsetWidth / 2) === Math.round(-n2) ? -50 : 0))) ? t21.offsetWidth * i2.xPercent / 100 : 0) + F2, i2.y = r2 - ((i2.yPercent = r2 && (!e2 && i2.yPercent || (Math.round(t21.offsetHeight / 2) === Math.round(-r2) ? -50 : 0))) ? t21.offsetHeight * i2.yPercent / 100 : 0) + F2, i2.z = s2 + F2, i2.scaleX = St(a2), i2.scaleY = St(o2), i2.rotation = St(u2) + V2, i2.rotationX = St(h2) + V2, i2.rotationY = St(l2) + V2, i2.skewX = f2 + V2, i2.skewY = c2 + V2, i2.transformPerspective = p2 + F2, (i2.zOrigin = parseFloat(N2.split(" ")[2]) || 0) && (B2[Ki] = Sn(N2)), i2.xOffset = i2.yOffset = 0, i2.force3D = R.force3D, i2.renderTransform = i2.svg ? An : Pi ? Mn : En, i2.uncache = 0, i2;
  };
  var Sn = function(t21) {
    return (t21 = t21.split(" "))[0] + " " + t21[1];
  };
  var On = function(t21, e2, i2) {
    var n2 = he(e2);
    return St(parseFloat(e2) + parseFloat(pn(t21, "x", i2 + "px", n2))) + n2;
  };
  var En = function(t21, e2) {
    e2.z = "0px", e2.rotationY = e2.rotationX = "0deg", e2.force3D = 0, Mn(t21, e2);
  };
  var Mn = function(t21, e2) {
    var i2 = e2 || this, n2 = i2.xPercent, r2 = i2.yPercent, s2 = i2.x, a2 = i2.y, o2 = i2.z, u2 = i2.rotation, h2 = i2.rotationY, l2 = i2.rotationX, f2 = i2.skewX, c2 = i2.skewY, p2 = i2.scaleX, d2 = i2.scaleY, m2 = i2.transformPerspective, g2 = i2.force3D, _2 = i2.target, v2 = i2.zOrigin, y2 = "", x2 = "auto" === g2 && t21 && 1 !== t21 || true === g2;
    if (v2 && ("0deg" !== l2 || "0deg" !== h2)) {
      var b2, w2 = parseFloat(h2) * Li, T2 = Math.sin(w2), k2 = Math.cos(w2);
      w2 = parseFloat(l2) * Li, b2 = Math.cos(w2), s2 = On(_2, s2, T2 * b2 * -v2), a2 = On(_2, a2, -Math.sin(w2) * -v2), o2 = On(_2, o2, k2 * b2 * -v2 + v2);
    }
    "0px" !== m2 && (y2 += "perspective(" + m2 + ") "), (n2 || r2) && (y2 += "translate(" + n2 + "%, " + r2 + "%) "), (x2 || "0px" !== s2 || "0px" !== a2 || "0px" !== o2) && (y2 += "0px" !== o2 || x2 ? "translate3d(" + s2 + ", " + a2 + ", " + o2 + ") " : "translate(" + s2 + ", " + a2 + ") "), "0deg" !== u2 && (y2 += "rotate(" + u2 + ") "), "0deg" !== h2 && (y2 += "rotateY(" + h2 + ") "), "0deg" !== l2 && (y2 += "rotateX(" + l2 + ") "), "0deg" === f2 && "0deg" === c2 || (y2 += "skew(" + f2 + ", " + c2 + ") "), 1 === p2 && 1 === d2 || (y2 += "scale(" + p2 + ", " + d2 + ") "), _2.style[Zi] = y2 || "translate(0, 0)";
  };
  var An = function(t21, e2) {
    var i2, n2, r2, s2, a2, o2 = e2 || this, u2 = o2.xPercent, h2 = o2.yPercent, l2 = o2.x, f2 = o2.y, c2 = o2.rotation, p2 = o2.skewX, d2 = o2.skewY, m2 = o2.scaleX, g2 = o2.scaleY, _2 = o2.target, v2 = o2.xOrigin, y2 = o2.yOrigin, x2 = o2.xOffset, b2 = o2.yOffset, w2 = o2.forceCSS, T2 = parseFloat(l2), k2 = parseFloat(f2);
    c2 = parseFloat(c2), p2 = parseFloat(p2), (d2 = parseFloat(d2)) && (p2 += d2 = parseFloat(d2), c2 += d2), c2 || p2 ? (c2 *= Li, p2 *= Li, i2 = Math.cos(c2) * m2, n2 = Math.sin(c2) * m2, r2 = Math.sin(c2 - p2) * -g2, s2 = Math.cos(c2 - p2) * g2, p2 && (d2 *= Li, a2 = Math.tan(p2 - d2), r2 *= a2 = Math.sqrt(1 + a2 * a2), s2 *= a2, d2 && (a2 = Math.tan(d2), i2 *= a2 = Math.sqrt(1 + a2 * a2), n2 *= a2)), i2 = St(i2), n2 = St(n2), r2 = St(r2), s2 = St(s2)) : (i2 = m2, s2 = g2, n2 = r2 = 0), (T2 && !~(l2 + "").indexOf("px") || k2 && !~(f2 + "").indexOf("px")) && (T2 = pn(_2, "x", l2, "px"), k2 = pn(_2, "y", f2, "px")), (v2 || y2 || x2 || b2) && (T2 = St(T2 + v2 - (v2 * i2 + y2 * r2) + x2), k2 = St(k2 + y2 - (v2 * n2 + y2 * s2) + b2)), (u2 || h2) && (a2 = _2.getBBox(), T2 = St(T2 + u2 / 100 * a2.width), k2 = St(k2 + h2 / 100 * a2.height)), a2 = "matrix(" + i2 + "," + n2 + "," + r2 + "," + s2 + "," + T2 + "," + k2 + ")", _2.setAttribute("transform", a2), w2 && (_2.style[Zi] = a2);
  };
  var Pn = function(t21, e2, i2, n2, r2) {
    var s2, a2, o2 = 360, u2 = j(r2), h2 = parseFloat(r2) * (u2 && ~r2.indexOf("rad") ? Di : 1) - n2, l2 = n2 + h2 + "deg";
    return u2 && ("short" === (s2 = r2.split("_")[1]) && (h2 %= o2) !== h2 % 180 && (h2 += h2 < 0 ? o2 : -360), "cw" === s2 && h2 < 0 ? h2 = (h2 + 36e9) % o2 - ~~(h2 / o2) * o2 : "ccw" === s2 && h2 > 0 && (h2 = (h2 - 36e9) % o2 - ~~(h2 / o2) * o2)), t21._pt = a2 = new xi(t21._pt, e2, i2, n2, h2, qi), a2.e = l2, a2.u = "deg", t21._props.push(i2), a2;
  };
  var In = function(t21, e2) {
    for (var i2 in e2) t21[i2] = e2[i2];
    return t21;
  };
  var Dn = function(t21, e2, i2) {
    var n2, r2, s2, a2, o2, u2, h2, l2 = In({}, i2._gsap), f2 = i2.style;
    for (r2 in l2.svg ? (s2 = i2.getAttribute("transform"), i2.setAttribute("transform", ""), f2[Zi] = e2, n2 = Cn(i2, 1), ln(i2, Zi), i2.setAttribute("transform", s2)) : (s2 = getComputedStyle(i2)[Zi], f2[Zi] = e2, n2 = Cn(i2, 1), f2[Zi] = s2), Ii) (s2 = l2[r2]) !== (a2 = n2[r2]) && "perspective,force3D,transformOrigin,svgOrigin".indexOf(r2) < 0 && (o2 = he(s2) !== (h2 = he(a2)) ? pn(i2, r2, s2, h2) : parseFloat(s2), u2 = parseFloat(a2), t21._pt = new xi(t21._pt, n2, r2, o2, u2 - o2, Ni), t21._pt.u = h2 || 0, t21._props.push(r2));
    In(n2, l2);
  };
  Ct("padding,margin,Width,Radius", (function(t21, e2) {
    var i2 = "Top", n2 = "Right", r2 = "Bottom", s2 = "Left", a2 = (e2 < 3 ? [i2, n2, r2, s2] : [i2 + s2, i2 + n2, r2 + n2, r2 + s2]).map((function(i3) {
      return e2 < 2 ? t21 + i3 : "border" + i3 + t21;
    }));
    vn[e2 > 1 ? "border" + t21 : t21] = function(t22, e3, i3, n3, r3) {
      var s3, o2;
      if (arguments.length < 4) return s3 = a2.map((function(e4) {
        return dn(t22, e4, i3);
      })), 5 === (o2 = s3.join(" ")).split(s3[0]).length ? s3[0] : o2;
      s3 = (n3 + "").split(" "), o2 = {}, a2.forEach((function(t23, e4) {
        return o2[t23] = s3[e4] = s3[e4] || s3[(e4 - 1) / 2 | 0];
      })), t22.init(e3, o2, r3);
    };
  }));
  var Ln;
  var Bn;
  var Rn;
  var zn = { name: "css", register: sn, targetTest: function(t21) {
    return t21.style && t21.nodeType;
  }, init: function(t21, e2, i2, n2, r2) {
    var s2, a2, o2, u2, h2, l2, f2, c2, p2, d2, m2, g2, _2, v2, y2, x2, b2, w2, T2, k2 = this._props, C2 = t21.style, S2 = i2.vars.startAt;
    for (f2 in Ei || sn(), e2) if ("autoRound" !== f2 && (a2 = e2[f2], !_t[f2] || !ti(f2, e2, i2, n2, t21, r2))) {
      if (h2 = typeof a2, l2 = vn[f2], "function" === h2 && (h2 = typeof (a2 = a2.call(i2, n2, t21, r2))), "string" === h2 && ~a2.indexOf("random(") && (a2 = xe(a2)), l2) l2(this, t21, f2, a2, i2) && (y2 = 1);
      else if ("--" === f2.substr(0, 2)) s2 = (getComputedStyle(t21).getPropertyValue(f2) + "").trim(), a2 += "", Pe.lastIndex = 0, Pe.test(s2) || (c2 = he(s2), p2 = he(a2)), p2 ? c2 !== p2 && (s2 = pn(t21, f2, s2, p2) + p2) : c2 && (a2 += c2), this.add(C2, "setProperty", s2, a2, n2, r2, 0, 0, f2), k2.push(f2);
      else if ("undefined" !== h2) {
        if (S2 && f2 in S2 ? (s2 = "function" == typeof S2[f2] ? S2[f2].call(i2, n2, t21, r2) : S2[f2], j(s2) && ~s2.indexOf("random(") && (s2 = xe(s2)), he(s2 + "") || (s2 += R.units[f2] || he(dn(t21, f2)) || ""), "=" === (s2 + "").charAt(1) && (s2 = dn(t21, f2))) : s2 = dn(t21, f2), u2 = parseFloat(s2), (d2 = "string" === h2 && "=" === a2.charAt(1) && a2.substr(0, 2)) && (a2 = a2.substr(2)), o2 = parseFloat(a2), f2 in Vi && ("autoAlpha" === f2 && (1 === u2 && "hidden" === dn(t21, "visibility") && o2 && (u2 = 0), fn(this, C2, "visibility", u2 ? "inherit" : "hidden", o2 ? "inherit" : "hidden", !o2)), "scale" !== f2 && "transform" !== f2 && ~(f2 = Vi[f2]).indexOf(",") && (f2 = f2.split(",")[0])), m2 = f2 in Ii) if (g2 || ((_2 = t21._gsap).renderTransform && !e2.parseTransform || Cn(t21, e2.parseTransform), v2 = false !== e2.smoothOrigin && _2.smooth, (g2 = this._pt = new xi(this._pt, C2, Zi, 0, 1, _2.renderTransform, _2, 0, -1)).dep = 1), "scale" === f2) this._pt = new xi(this._pt, _2, "scaleY", _2.scaleY, (d2 ? Et(_2.scaleY, d2 + o2) : o2) - _2.scaleY || 0), k2.push("scaleY", f2), f2 += "X";
        else {
          if ("transformOrigin" === f2) {
            b2 = void 0, w2 = void 0, T2 = void 0, b2 = (x2 = a2).split(" "), w2 = b2[0], T2 = b2[1] || "50%", "top" !== w2 && "bottom" !== w2 && "left" !== T2 && "right" !== T2 || (x2 = w2, w2 = T2, T2 = x2), b2[0] = gn[w2] || w2, b2[1] = gn[T2] || T2, a2 = b2.join(" "), _2.svg ? kn(t21, a2, 0, v2, 0, this) : ((p2 = parseFloat(a2.split(" ")[2]) || 0) !== _2.zOrigin && fn(this, _2, "zOrigin", _2.zOrigin, p2), fn(this, C2, f2, Sn(s2), Sn(a2)));
            continue;
          }
          if ("svgOrigin" === f2) {
            kn(t21, a2, 1, v2, 0, this);
            continue;
          }
          if (f2 in xn) {
            Pn(this, _2, f2, u2, d2 ? Et(u2, d2 + a2) : a2);
            continue;
          }
          if ("smoothOrigin" === f2) {
            fn(this, _2, "smooth", _2.smooth, a2);
            continue;
          }
          if ("force3D" === f2) {
            _2[f2] = a2;
            continue;
          }
          if ("transform" === f2) {
            Dn(this, a2, t21);
            continue;
          }
        }
        else f2 in C2 || (f2 = rn(f2) || f2);
        if (m2 || (o2 || 0 === o2) && (u2 || 0 === u2) && !Fi.test(a2) && f2 in C2) o2 || (o2 = 0), (c2 = (s2 + "").substr((u2 + "").length)) !== (p2 = he(a2) || (f2 in R.units ? R.units[f2] : c2)) && (u2 = pn(t21, f2, s2, p2)), this._pt = new xi(this._pt, m2 ? _2 : C2, f2, u2, (d2 ? Et(u2, d2 + o2) : o2) - u2, m2 || "px" !== p2 && "zIndex" !== f2 || false === e2.autoRound ? Ni : Yi), this._pt.u = p2 || 0, c2 !== p2 && "%" !== p2 && (this._pt.b = s2, this._pt.r = Xi);
        else if (f2 in C2) mn.call(this, t21, f2, s2, d2 ? d2 + a2 : a2);
        else {
          if (!(f2 in t21)) {
            lt(f2, a2);
            continue;
          }
          this.add(t21, f2, s2 || t21[f2], d2 ? d2 + a2 : a2, n2, r2);
        }
        k2.push(f2);
      }
    }
    y2 && yi(this);
  }, get: dn, aliases: Vi, getSetter: function(t21, e2, i2) {
    var n2 = Vi[e2];
    return n2 && n2.indexOf(",") < 0 && (e2 = n2), e2 in Ii && e2 !== Ki && (t21._gsap.x || dn(t21, "x")) ? i2 && Ai === i2 ? "scale" === e2 ? Gi : Qi : (Ai = i2 || {}, "scale" === e2 ? $i : Ji) : t21.style && !H(t21.style[e2]) ? Wi : ~e2.indexOf("-") ? Hi : fi(t21, e2);
  }, core: { _removeProperty: ln, _getMatrix: Tn } };
  ki.utils.checkPrefix = rn, Rn = Ct((Ln = "x,y,z,scale,scaleX,scaleY,xPercent,yPercent") + "," + (Bn = "rotation,rotationX,rotationY,skewX,skewY") + ",transform,transformOrigin,svgOrigin,force3D,smoothOrigin,transformPerspective", (function(t21) {
    Ii[t21] = 1;
  })), Ct(Bn, (function(t21) {
    R.units[t21] = "deg", xn[t21] = 1;
  })), Vi[Rn[13]] = Ln + "," + Bn, Ct("0:translateX,1:translateY,2:translateZ,8:rotate,8:rotationZ,8:rotateZ,9:rotateX,10:rotateY", (function(t21) {
    var e2 = t21.split(":");
    Vi[e2[1]] = Rn[e2[0]];
  })), Ct("x,y,z,top,right,bottom,left,width,height,fontSize,padding,margin,perspective", (function(t21) {
    R.units[t21] = "px";
  })), ki.registerPlugin(zn);
  var Fn;
  var Vn;
  var Nn;
  var qn;
  var Xn;
  var Yn;
  var jn;
  var Un;
  var Wn;
  var Hn = ki.registerPlugin(zn) || ki;
  var Qn = (Hn.core.Tween, "transform");
  var Gn = Qn + "Origin";
  var $n = function(t21) {
    var e2 = t21.ownerDocument || t21;
    !(Qn in t21.style) && "msTransform" in t21.style && (Gn = (Qn = "msTransform") + "Origin");
    for (; e2.parentNode && (e2 = e2.parentNode); ) ;
    if (Vn = window, jn = new or(), e2) {
      Fn = e2, Nn = e2.documentElement, qn = e2.body, (Un = Fn.createElementNS("http://www.w3.org/2000/svg", "g")).style.transform = "none";
      var i2 = e2.createElement("div"), n2 = e2.createElement("div");
      qn.appendChild(i2), i2.appendChild(n2), i2.style.position = "static", i2.style[Qn] = "translate3d(0,0,1px)", Wn = n2.offsetParent !== i2, qn.removeChild(i2);
    }
    return e2;
  };
  var Jn = [];
  var Zn = [];
  var Kn = function() {
    return Vn.pageYOffset || Fn.scrollTop || Nn.scrollTop || qn.scrollTop || 0;
  };
  var tr = function() {
    return Vn.pageXOffset || Fn.scrollLeft || Nn.scrollLeft || qn.scrollLeft || 0;
  };
  var er = function(t21) {
    return t21.ownerSVGElement || ("svg" === (t21.tagName + "").toLowerCase() ? t21 : null);
  };
  var ir = function t17(e2) {
    return "fixed" === Vn.getComputedStyle(e2).position || ((e2 = e2.parentNode) && 1 === e2.nodeType ? t17(e2) : void 0);
  };
  var nr = function t18(e2, i2) {
    if (e2.parentNode && (Fn || $n(e2))) {
      var n2 = er(e2), r2 = n2 ? n2.getAttribute("xmlns") || "http://www.w3.org/2000/svg" : "http://www.w3.org/1999/xhtml", s2 = n2 ? i2 ? "rect" : "g" : "div", a2 = 2 !== i2 ? 0 : 100, o2 = 3 === i2 ? 100 : 0, u2 = "position:absolute;display:block;pointer-events:none;margin:0;padding:0;", h2 = Fn.createElementNS ? Fn.createElementNS(r2.replace(/^https/, "http"), s2) : Fn.createElement(s2);
      return i2 && (n2 ? (Yn || (Yn = t18(e2)), h2.setAttribute("width", 0.01), h2.setAttribute("height", 0.01), h2.setAttribute("transform", "translate(" + a2 + "," + o2 + ")"), Yn.appendChild(h2)) : (Xn || ((Xn = t18(e2)).style.cssText = u2), h2.style.cssText = u2 + "width:0.1px;height:0.1px;top:" + o2 + "px;left:" + a2 + "px", Xn.appendChild(h2))), h2;
    }
    throw "Need document and parent.";
  };
  var rr = function(t21) {
    var e2, i2 = t21.getCTM();
    return i2 || (e2 = t21.style[Qn], t21.style[Qn] = "none", t21.appendChild(Un), i2 = Un.getCTM(), t21.removeChild(Un), e2 ? t21.style[Qn] = e2 : t21.style.removeProperty(Qn.replace(/([A-Z])/g, "-$1").toLowerCase())), i2 || jn.clone();
  };
  var sr = function(t21, e2) {
    var i2, n2, r2, s2, a2, o2, u2 = er(t21), h2 = t21 === u2, l2 = u2 ? Jn : Zn, f2 = t21.parentNode;
    if (t21 === Vn) return t21;
    if (l2.length || l2.push(nr(t21, 1), nr(t21, 2), nr(t21, 3)), i2 = u2 ? Yn : Xn, u2) h2 ? (s2 = -(r2 = rr(t21)).e / r2.a, a2 = -r2.f / r2.d, n2 = jn) : t21.getBBox ? (r2 = t21.getBBox(), n2 = (n2 = t21.transform ? t21.transform.baseVal : {}).numberOfItems ? n2.numberOfItems > 1 ? (function(t22) {
      for (var e3 = new or(), i3 = 0; i3 < t22.numberOfItems; i3++) e3.multiply(t22.getItem(i3).matrix);
      return e3;
    })(n2) : n2.getItem(0).matrix : jn, s2 = n2.a * r2.x + n2.c * r2.y, a2 = n2.b * r2.x + n2.d * r2.y) : (n2 = new or(), s2 = a2 = 0), e2 && "g" === t21.tagName.toLowerCase() && (s2 = a2 = 0), (h2 ? u2 : f2).appendChild(i2), i2.setAttribute("transform", "matrix(" + n2.a + "," + n2.b + "," + n2.c + "," + n2.d + "," + (n2.e + s2) + "," + (n2.f + a2) + ")");
    else {
      if (s2 = a2 = 0, Wn) for (n2 = t21.offsetParent, r2 = t21; r2 && (r2 = r2.parentNode) && r2 !== n2 && r2.parentNode; ) (Vn.getComputedStyle(r2)[Qn] + "").length > 4 && (s2 = r2.offsetLeft, a2 = r2.offsetTop, r2 = 0);
      if ("absolute" !== (o2 = Vn.getComputedStyle(t21)).position && "fixed" !== o2.position) for (n2 = t21.offsetParent; f2 && f2 !== n2; ) s2 += f2.scrollLeft || 0, a2 += f2.scrollTop || 0, f2 = f2.parentNode;
      (r2 = i2.style).top = t21.offsetTop - a2 + "px", r2.left = t21.offsetLeft - s2 + "px", r2[Qn] = o2[Qn], r2[Gn] = o2[Gn], r2.position = "fixed" === o2.position ? "fixed" : "absolute", t21.parentNode.appendChild(i2);
    }
    return i2;
  };
  var ar = function(t21, e2, i2, n2, r2, s2, a2) {
    return t21.a = e2, t21.b = i2, t21.c = n2, t21.d = r2, t21.e = s2, t21.f = a2, t21;
  };
  var or = (function() {
    function t21(t22, e3, i2, n2, r2, s2) {
      void 0 === t22 && (t22 = 1), void 0 === e3 && (e3 = 0), void 0 === i2 && (i2 = 0), void 0 === n2 && (n2 = 1), void 0 === r2 && (r2 = 0), void 0 === s2 && (s2 = 0), ar(this, t22, e3, i2, n2, r2, s2);
    }
    var e2 = t21.prototype;
    return e2.inverse = function() {
      var t22 = this.a, e3 = this.b, i2 = this.c, n2 = this.d, r2 = this.e, s2 = this.f, a2 = t22 * n2 - e3 * i2 || 1e-10;
      return ar(this, n2 / a2, -e3 / a2, -i2 / a2, t22 / a2, (i2 * s2 - n2 * r2) / a2, -(t22 * s2 - e3 * r2) / a2);
    }, e2.multiply = function(t22) {
      var e3 = this.a, i2 = this.b, n2 = this.c, r2 = this.d, s2 = this.e, a2 = this.f, o2 = t22.a, u2 = t22.c, h2 = t22.b, l2 = t22.d, f2 = t22.e, c2 = t22.f;
      return ar(this, o2 * e3 + h2 * n2, o2 * i2 + h2 * r2, u2 * e3 + l2 * n2, u2 * i2 + l2 * r2, s2 + f2 * e3 + c2 * n2, a2 + f2 * i2 + c2 * r2);
    }, e2.clone = function() {
      return new t21(this.a, this.b, this.c, this.d, this.e, this.f);
    }, e2.equals = function(t22) {
      var e3 = this.a, i2 = this.b, n2 = this.c, r2 = this.d, s2 = this.e, a2 = this.f;
      return e3 === t22.a && i2 === t22.b && n2 === t22.c && r2 === t22.d && s2 === t22.e && a2 === t22.f;
    }, e2.apply = function(t22, e3) {
      void 0 === e3 && (e3 = {});
      var i2 = t22.x, n2 = t22.y, r2 = this.a, s2 = this.b, a2 = this.c, o2 = this.d, u2 = this.e, h2 = this.f;
      return e3.x = i2 * r2 + n2 * a2 + u2 || 0, e3.y = i2 * s2 + n2 * o2 + h2 || 0, e3;
    }, t21;
  })();
  function ur(t21, e2, i2, n2) {
    if (!t21 || !t21.parentNode || (Fn || $n(t21)).documentElement === t21) return new or();
    var r2 = (function(t22) {
      for (var e3, i3; t22 && t22 !== qn; ) (i3 = t22._gsap) && i3.uncache && i3.get(t22, "x"), i3 && !i3.scaleX && !i3.scaleY && i3.renderTransform && (i3.scaleX = i3.scaleY = 1e-4, i3.renderTransform(1, i3), e3 ? e3.push(i3) : e3 = [i3]), t22 = t22.parentNode;
      return e3;
    })(t21), s2 = er(t21) ? Jn : Zn, a2 = sr(t21, i2), o2 = s2[0].getBoundingClientRect(), u2 = s2[1].getBoundingClientRect(), h2 = s2[2].getBoundingClientRect(), l2 = a2.parentNode, f2 = !n2 && ir(t21), c2 = new or((u2.left - o2.left) / 100, (u2.top - o2.top) / 100, (h2.left - o2.left) / 100, (h2.top - o2.top) / 100, o2.left + (f2 ? 0 : tr()), o2.top + (f2 ? 0 : Kn()));
    if (l2.removeChild(a2), r2) for (o2 = r2.length; o2--; ) (u2 = r2[o2]).scaleX = u2.scaleY = 0, u2.renderTransform(1, u2);
    return e2 ? c2.inverse() : c2;
  }
  var hr;
  var lr;
  var fr;
  var cr;
  var pr;
  var dr;
  var mr;
  var gr = 1;
  var _r = function(t21, e2) {
    return t21.actions.forEach((function(t22) {
      return t22.vars[e2] && t22.vars[e2](t22);
    }));
  };
  var vr = {};
  var yr = 180 / Math.PI;
  var xr = Math.PI / 180;
  var br = {};
  var wr = {};
  var Tr = {};
  var kr = function(t21) {
    return "string" == typeof t21 ? t21.split(" ").join("").split(",") : t21;
  };
  var Cr = kr("onStart,onUpdate,onComplete,onReverseComplete,onInterrupt");
  var Sr = kr("transform,transformOrigin,width,height,position,top,left,opacity,zIndex,maxWidth,maxHeight,minWidth,minHeight");
  var Or = function(t21) {
    return hr(t21)[0] || console.warn("Element not found:", t21);
  };
  var Er = function(t21) {
    return Math.round(1e4 * t21) / 1e4 || 0;
  };
  var Mr = function(t21, e2, i2) {
    return t21.forEach((function(t22) {
      return t22.classList[i2](e2);
    }));
  };
  var Ar = { zIndex: 1, kill: 1, simple: 1, spin: 1, clearProps: 1, targets: 1, toggleClass: 1, onComplete: 1, onUpdate: 1, onInterrupt: 1, onStart: 1, delay: 1, repeat: 1, repeatDelay: 1, yoyo: 1, scale: 1, fade: 1, absolute: 1, props: 1, onEnter: 1, onLeave: 1, custom: 1, paused: 1, nested: 1, prune: 1, absoluteOnLeave: 1 };
  var Pr = { zIndex: 1, simple: 1, clearProps: 1, scale: 1, absolute: 1, fitChild: 1, getVars: 1, props: 1 };
  var Ir = function(t21) {
    return t21.replace(/([A-Z])/g, "-$1").toLowerCase();
  };
  var Dr = function(t21, e2) {
    var i2, n2 = {};
    for (i2 in t21) e2[i2] || (n2[i2] = t21[i2]);
    return n2;
  };
  var Lr = {};
  var Br = function(t21) {
    var e2 = Lr[t21] = kr(t21);
    return Tr[t21] = e2.concat(Sr), e2;
  };
  var Rr = function t19(e2, i2, n2) {
    void 0 === n2 && (n2 = 0);
    for (var r2 = e2.parentNode, s2 = 1e3 * Math.pow(10, n2) * (i2 ? -1 : 1), a2 = i2 ? 900 * -s2 : 0; e2; ) a2 += s2, e2 = e2.previousSibling;
    return r2 ? a2 + t19(r2, i2, n2 + 1) : a2;
  };
  var zr = function(t21, e2, i2) {
    return t21.forEach((function(t22) {
      return t22.d = Rr(i2 ? t22.element : t22.t, e2);
    })), t21.sort((function(t22, e3) {
      return t22.d - e3.d;
    })), t21;
  };
  var Fr = function(t21, e2) {
    for (var i2, n2, r2 = t21.element.style, s2 = t21.css = t21.css || [], a2 = e2.length; a2--; ) n2 = r2[i2 = e2[a2]] || r2.getPropertyValue(i2), s2.push(n2 ? i2 : wr[i2] || (wr[i2] = Ir(i2)), n2);
    return r2;
  };
  var Vr = function(t21) {
    var e2 = t21.css, i2 = t21.element.style, n2 = 0;
    for (t21.cache.uncache = 1; n2 < e2.length; n2 += 2) e2[n2 + 1] ? i2[e2[n2]] = e2[n2 + 1] : i2.removeProperty(e2[n2]);
  };
  var Nr = function(t21, e2) {
    t21.forEach((function(t22) {
      return t22.a.cache.uncache = 1;
    })), e2 || t21.finalStates.forEach(Vr);
  };
  var qr = "paddingTop,paddingRight,paddingBottom,paddingLeft,gridArea,transition".split(",");
  var Xr = function(t21, e2, i2) {
    var n2, r2, s2, a2 = t21.element, o2 = t21.width, u2 = t21.height, h2 = t21.uncache, l2 = t21.getProp, f2 = a2.style, c2 = 4;
    if ("object" != typeof e2 && (e2 = t21), fr && 1 !== i2) return fr._abs.push({ t: a2, b: t21, a: t21, sd: 0 }), fr._final.push((function() {
      return t21.cache.uncache = 1, Vr(t21);
    })), a2;
    for (r2 = "none" === l2("display"), t21.isVisible && !r2 || (r2 && (Fr(t21, ["display"]).display = e2.display), t21.matrix = e2.matrix, t21.width = o2 = t21.width || e2.width, t21.height = u2 = t21.height || e2.height), Fr(t21, qr), s2 = window.getComputedStyle(a2); c2--; ) f2[qr[c2]] = s2[qr[c2]];
    if (f2.gridArea = "1 / 1 / 1 / 1", f2.transition = "none", f2.position = "absolute", f2.width = o2 + "px", f2.height = u2 + "px", f2.top || (f2.top = "0px"), f2.left || (f2.left = "0px"), h2) n2 = new as(a2);
    else if ((n2 = Dr(t21, br)).position = "absolute", t21.simple) {
      var p2 = a2.getBoundingClientRect();
      n2.matrix = new or(1, 0, 0, 1, p2.left + tr(), p2.top + Kn());
    } else n2.matrix = ur(a2, false, false, true);
    return n2 = Gr(n2, t21, true), t21.x = dr(n2.x, 0.01), t21.y = dr(n2.y, 0.01), a2;
  };
  var Yr = function(t21, e2) {
    return true !== e2 && (e2 = hr(e2), t21 = t21.filter((function(t22) {
      if (-1 !== e2.indexOf((t22.sd < 0 ? t22.b : t22.a).element)) return true;
      t22.t._gsap.renderTransform(1), t22.t.style.width = t22.b.width + "px", t22.t.style.height = t22.b.height + "px";
    }))), t21;
  };
  var jr = function(t21) {
    return zr(t21, true).forEach((function(t22) {
      return (t22.a.isVisible || t22.b.isVisible) && Xr(t22.sd < 0 ? t22.b : t22.a, t22.b, 1);
    }));
  };
  var Ur = function(t21, e2, i2, n2) {
    return t21 instanceof as ? t21 : t21 instanceof ss ? (function(t22, e3) {
      return e3 && t22.idLookup[Ur(e3).id] || t22.elementStates[0];
    })(t21, n2) : new as("string" == typeof t21 ? Or(t21) || console.warn(t21 + " not found") : t21, e2, i2);
  };
  var Wr = function(t21, e2) {
    var i2, n2 = t21.style || t21;
    for (i2 in e2) n2[i2] = e2[i2];
  };
  var Hr = function(t21) {
    return t21.map((function(t22) {
      return t22.element;
    }));
  };
  var Qr = function(t21, e2, i2) {
    return t21 && e2.length && i2.add(t21(Hr(e2), i2, new ss(e2, 0, true)), 0);
  };
  var Gr = function(t21, e2, i2, n2, r2, s2) {
    var a2, o2, u2, h2, l2, f2, c2, p2 = t21.element, d2 = t21.cache, m2 = t21.parent, g2 = t21.x, _2 = t21.y, v2 = e2.width, y2 = e2.height, x2 = e2.scaleX, b2 = e2.scaleY, w2 = e2.rotation, T2 = e2.bounds, k2 = s2 && p2.style.cssText, C2 = s2 && p2.getBBox && p2.getAttribute("transform"), S2 = t21, O2 = e2.matrix, E2 = O2.e, M2 = O2.f, A2 = t21.bounds.width !== T2.width || t21.bounds.height !== T2.height || t21.scaleX !== x2 || t21.scaleY !== b2 || t21.rotation !== w2, P2 = !A2 && t21.simple && e2.simple && !r2;
    return P2 || !m2 ? (x2 = b2 = 1, w2 = a2 = 0) : (l2 = (function(t22) {
      var e3 = t22._gsap || lr.core.getCache(t22);
      return e3.gmCache === lr.ticker.frame ? e3.gMatrix : (e3.gmCache = lr.ticker.frame, e3.gMatrix = ur(t22, true, false, true));
    })(m2), f2 = l2.clone().multiply(e2.ctm ? e2.matrix.clone().multiply(e2.ctm) : e2.matrix), w2 = Er(Math.atan2(f2.b, f2.a) * yr), a2 = Er(Math.atan2(f2.c, f2.d) * yr + w2) % 360, x2 = Math.sqrt(Math.pow(f2.a, 2) + Math.pow(f2.b, 2)), b2 = Math.sqrt(Math.pow(f2.c, 2) + Math.pow(f2.d, 2)) * Math.cos(a2 * xr), r2 && (r2 = hr(r2)[0], h2 = lr.getProperty(r2), c2 = r2.getBBox && "function" == typeof r2.getBBox && r2.getBBox(), S2 = { scaleX: h2("scaleX"), scaleY: h2("scaleY"), width: c2 ? c2.width : Math.ceil(parseFloat(h2("width", "px"))), height: c2 ? c2.height : parseFloat(h2("height", "px")) }), d2.rotation = w2 + "deg", d2.skewX = a2 + "deg"), i2 ? (x2 *= v2 !== S2.width && S2.width ? v2 / S2.width : 1, b2 *= y2 !== S2.height && S2.height ? y2 / S2.height : 1, d2.scaleX = x2, d2.scaleY = b2) : (v2 = dr(v2 * x2 / S2.scaleX, 0), y2 = dr(y2 * b2 / S2.scaleY, 0), p2.style.width = v2 + "px", p2.style.height = y2 + "px"), n2 && Wr(p2, e2.props), P2 || !m2 ? (g2 += E2 - t21.matrix.e, _2 += M2 - t21.matrix.f) : A2 || m2 !== e2.parent ? (d2.renderTransform(1, d2), f2 = ur(r2 || p2, false, false, true), o2 = l2.apply({ x: f2.e, y: f2.f }), g2 += (u2 = l2.apply({ x: E2, y: M2 })).x - o2.x, _2 += u2.y - o2.y) : (l2.e = l2.f = 0, g2 += (u2 = l2.apply({ x: E2 - t21.matrix.e, y: M2 - t21.matrix.f })).x, _2 += u2.y), g2 = dr(g2, 0.02), _2 = dr(_2, 0.02), !s2 || s2 instanceof as ? (d2.x = g2 + "px", d2.y = _2 + "px", d2.renderTransform(1, d2)) : (p2.style.cssText = k2, p2.getBBox && p2.setAttribute("transform", C2 || ""), d2.uncache = 1), s2 && (s2.x = g2, s2.y = _2, s2.rotation = w2, s2.skewX = a2, i2 ? (s2.scaleX = x2, s2.scaleY = b2) : (s2.width = v2, s2.height = y2)), s2 || d2;
  };
  var $r = function(t21, e2) {
    return t21 instanceof ss ? t21 : new ss(t21, e2);
  };
  var Jr = function(t21, e2, i2) {
    var n2 = t21.idLookup[i2], r2 = t21.alt[i2];
    return !r2.isVisible || (e2.getElementState(r2.element) || r2).isVisible && n2.isVisible ? n2 : r2;
  };
  var Zr = [];
  var Kr = "width,height,overflowX,overflowY".split(",");
  var ts = function(t21) {
    if (t21 !== mr) {
      var e2 = pr.style, i2 = pr.clientWidth === window.outerWidth, n2 = pr.clientHeight === window.outerHeight, r2 = 4;
      if (t21 && (i2 || n2)) {
        for (; r2--; ) Zr[r2] = e2[Kr[r2]];
        i2 && (e2.width = pr.clientWidth + "px", e2.overflowY = "hidden"), n2 && (e2.height = pr.clientHeight + "px", e2.overflowX = "hidden"), mr = t21;
      } else if (mr) {
        for (; r2--; ) Zr[r2] ? e2[Kr[r2]] = Zr[r2] : e2.removeProperty(Ir(Kr[r2]));
        mr = t21;
      }
    }
  };
  var es = function(t21, e2, i2, n2) {
    t21 instanceof ss && e2 instanceof ss || console.warn("Not a valid state object.");
    var r2, s2, a2, o2, u2, h2, l2, f2, c2, p2, d2, m2, g2, _2, v2, y2 = i2 = i2 || {}, x2 = y2.clearProps, b2 = y2.onEnter, w2 = y2.onLeave, T2 = y2.absolute, k2 = y2.absoluteOnLeave, C2 = y2.custom, S2 = y2.delay, O2 = y2.paused, E2 = y2.repeat, M2 = y2.repeatDelay, A2 = y2.yoyo, P2 = y2.toggleClass, I2 = y2.nested, D2 = y2.zIndex, L2 = y2.scale, B2 = y2.fade, R2 = y2.stagger, z2 = y2.spin, F2 = y2.prune, V2 = ("props" in i2 ? i2 : t21).props, N2 = Dr(i2, Ar), q2 = lr.timeline({ delay: S2, paused: O2, repeat: E2, repeatDelay: M2, yoyo: A2 }), X2 = N2, Y2 = [], j2 = [], U2 = [], W2 = [], H2 = true === z2 ? 1 : z2 || 0, Q2 = "function" == typeof z2 ? z2 : function() {
      return H2;
    }, G2 = t21.interrupted || e2.interrupted, $2 = q2[1 !== n2 ? "to" : "from"];
    for (s2 in e2.idLookup) d2 = e2.alt[s2] ? Jr(e2, t21, s2) : e2.idLookup[s2], u2 = d2.element, p2 = t21.idLookup[s2], t21.alt[s2] && u2 === p2.element && (t21.alt[s2].isVisible || !d2.isVisible) && (p2 = t21.alt[s2]), p2 ? (h2 = { t: u2, b: p2, a: d2, sd: p2.element === u2 ? 0 : d2.isVisible ? 1 : -1 }, U2.push(h2), h2.sd && (h2.sd < 0 && (h2.b = d2, h2.a = p2), G2 && Fr(h2.b, V2 ? Tr[V2] : Sr), B2 && U2.push(h2.swap = { t: p2.element, b: h2.b, a: h2.a, sd: -h2.sd, swap: h2 })), u2._flip = p2.element._flip = fr ? fr.timeline : q2) : d2.isVisible && (U2.push({ t: u2, b: Dr(d2, { isVisible: 1 }), a: d2, sd: 0, entering: 1 }), u2._flip = fr ? fr.timeline : q2);
    (V2 && (Lr[V2] || Br(V2)).forEach((function(t22) {
      return N2[t22] = function(e3) {
        return U2[e3].a.props[t22];
      };
    })), U2.finalStates = c2 = [], m2 = function() {
      for (zr(U2), ts(true), o2 = 0; o2 < U2.length; o2++) h2 = U2[o2], g2 = h2.a, _2 = h2.b, !F2 || g2.isDifferent(_2) || h2.entering ? (u2 = h2.t, I2 && !(h2.sd < 0) && o2 && (g2.matrix = ur(u2, false, false, true)), h2.sd || _2.isVisible && g2.isVisible ? (h2.sd < 0 ? (l2 = new as(u2, V2, t21.simple), Gr(l2, g2, L2, 0, 0, l2), l2.matrix = ur(u2, false, false, true), l2.css = h2.b.css, h2.a = g2 = l2, B2 && (u2.style.opacity = G2 ? _2.opacity : g2.opacity), R2 && W2.push(u2)) : h2.sd > 0 && B2 && (u2.style.opacity = G2 ? g2.opacity - _2.opacity : "0"), Gr(g2, _2, L2, V2)) : _2.isVisible !== g2.isVisible && (_2.isVisible ? g2.isVisible || (_2.css = g2.css, j2.push(_2), U2.splice(o2--, 1), T2 && I2 && Gr(g2, _2, L2, V2)) : (g2.isVisible && Y2.push(g2), U2.splice(o2--, 1))), L2 || (u2.style.maxWidth = Math.max(g2.width, _2.width) + "px", u2.style.maxHeight = Math.max(g2.height, _2.height) + "px", u2.style.minWidth = Math.min(g2.width, _2.width) + "px", u2.style.minHeight = Math.min(g2.height, _2.height) + "px"), I2 && P2 && u2.classList.add(P2)) : U2.splice(o2--, 1), c2.push(g2);
      var e3;
      if (P2 && (e3 = c2.map((function(t22) {
        return t22.element;
      })), I2 && e3.forEach((function(t22) {
        return t22.classList.remove(P2);
      }))), ts(false), L2 ? (N2.scaleX = function(t22) {
        return U2[t22].a.scaleX;
      }, N2.scaleY = function(t22) {
        return U2[t22].a.scaleY;
      }) : (N2.width = function(t22) {
        return U2[t22].a.width + "px";
      }, N2.height = function(t22) {
        return U2[t22].a.height + "px";
      }, N2.autoRound = i2.autoRound || false), N2.x = function(t22) {
        return U2[t22].a.x + "px";
      }, N2.y = function(t22) {
        return U2[t22].a.y + "px";
      }, N2.rotation = function(t22) {
        return U2[t22].a.rotation + (z2 ? 360 * Q2(t22, f2[t22], f2) : 0);
      }, N2.skewX = function(t22) {
        return U2[t22].a.skewX;
      }, f2 = U2.map((function(t22) {
        return t22.t;
      })), (D2 || 0 === D2) && (N2.modifiers = { zIndex: function() {
        return D2;
      } }, N2.zIndex = D2, N2.immediateRender = false !== i2.immediateRender), B2 && (N2.opacity = function(t22) {
        return U2[t22].sd < 0 ? 0 : U2[t22].sd > 0 ? U2[t22].a.opacity : "+=0";
      }), W2.length) {
        R2 = lr.utils.distribute(R2);
        var n3 = f2.slice(W2.length);
        N2.stagger = function(t22, e4) {
          return R2(~W2.indexOf(e4) ? f2.indexOf(U2[t22].swap.t) : t22, e4, n3);
        };
      }
      if (Cr.forEach((function(t22) {
        return i2[t22] && q2.eventCallback(t22, i2[t22], i2[t22 + "Params"]);
      })), C2 && f2.length) for (s2 in X2 = Dr(N2, Ar), "scale" in C2 && (C2.scaleX = C2.scaleY = C2.scale, delete C2.scale), C2) (r2 = Dr(C2[s2], Pr))[s2] = N2[s2], !("duration" in r2) && "duration" in N2 && (r2.duration = N2.duration), r2.stagger = N2.stagger, $2.call(q2, f2, r2, 0), delete X2[s2];
      (f2.length || j2.length || Y2.length) && (P2 && q2.add((function() {
        return Mr(e3, P2, q2._zTime < 0 ? "remove" : "add");
      }), 0) && !O2 && Mr(e3, P2, "add"), f2.length && $2.call(q2, f2, X2, 0)), Qr(b2, Y2, q2), Qr(w2, j2, q2);
      var p3 = fr && fr.timeline;
      p3 && (p3.add(q2, 0), fr._final.push((function() {
        return Nr(U2, !x2);
      }))), a2 = q2.duration(), q2.call((function() {
        var t22 = q2.time() >= a2;
        t22 && !p3 && Nr(U2, !x2), P2 && Mr(e3, P2, t22 ? "remove" : "add");
      }));
    }, k2 && (T2 = U2.filter((function(t22) {
      return !t22.sd && !t22.a.isVisible && t22.b.isVisible;
    })).map((function(t22) {
      return t22.a.element;
    }))), fr) ? (T2 && (v2 = fr._abs).push.apply(v2, Yr(U2, T2)), fr._run.push(m2)) : (T2 && jr(Yr(U2, T2)), m2());
    return fr ? fr.timeline : q2;
  };
  var is = function t20(e2) {
    e2.vars.onInterrupt && e2.vars.onInterrupt.apply(e2, e2.vars.onInterruptParams || []), e2.getChildren(true, false, true).forEach(t20);
  };
  var ns = function(t21, e2) {
    if (t21 && t21.progress() < 1 && !t21.paused()) return e2 && (is(t21), e2 < 2 && t21.progress(1), t21.kill()), true;
  };
  var rs = function(t21) {
    for (var e2, i2 = t21.idLookup = {}, n2 = t21.alt = {}, r2 = t21.elementStates, s2 = r2.length; s2--; ) i2[(e2 = r2[s2]).id] ? n2[e2.id] = e2 : i2[e2.id] = e2;
  };
  var ss = (function() {
    function t21(t22, e3, i2) {
      if (this.props = e3 && e3.props, this.simple = !(!e3 || !e3.simple), i2) this.targets = Hr(t22), this.elementStates = t22, rs(this);
      else {
        this.targets = hr(t22);
        var n2 = e3 && (false === e3.kill || e3.batch && !e3.kill);
        fr && !n2 && fr._kill.push(this), this.update(n2 || !!fr);
      }
    }
    var e2 = t21.prototype;
    return e2.update = function(t22) {
      var e3 = this;
      return this.elementStates = this.targets.map((function(t23) {
        return new as(t23, e3.props, e3.simple);
      })), rs(this), this.interrupt(t22), this.recordInlineStyles(), this;
    }, e2.clear = function() {
      return this.targets.length = this.elementStates.length = 0, rs(this), this;
    }, e2.fit = function(t22, e3, i2) {
      for (var n2, r2, s2 = zr(this.elementStates.slice(0), false, true), a2 = (t22 || this).idLookup, o2 = 0; o2 < s2.length; o2++) n2 = s2[o2], i2 && (n2.matrix = ur(n2.element, false, false, true)), (r2 = a2[n2.id]) && Gr(n2, r2, e3, true, 0, n2), n2.matrix = ur(n2.element, false, false, true);
      return this;
    }, e2.getProperty = function(t22, e3) {
      var i2 = this.getElementState(t22) || br;
      return (e3 in i2 ? i2 : i2.props || br)[e3];
    }, e2.add = function(t22) {
      for (var e3, i2, n2, r2 = t22.targets.length, s2 = this.idLookup, a2 = this.alt; r2--; ) (n2 = s2[(i2 = t22.elementStates[r2]).id]) && (i2.element === n2.element || a2[i2.id] && a2[i2.id].element === i2.element) ? (e3 = this.elementStates.indexOf(i2.element === n2.element ? n2 : a2[i2.id]), this.targets.splice(e3, 1, t22.targets[r2]), this.elementStates.splice(e3, 1, i2)) : (this.targets.push(t22.targets[r2]), this.elementStates.push(i2));
      return t22.interrupted && (this.interrupted = true), t22.simple || (this.simple = false), rs(this), this;
    }, e2.compare = function(t22) {
      var e3, i2, n2, r2, s2, a2, o2, u2, h2 = t22.idLookup, l2 = this.idLookup, f2 = [], c2 = [], p2 = [], d2 = [], m2 = [], g2 = t22.alt, _2 = this.alt, v2 = function(t23, e4, i3) {
        return (t23.isVisible !== e4.isVisible ? t23.isVisible ? p2 : d2 : t23.isVisible ? c2 : f2).push(i3) && m2.push(i3);
      }, y2 = function(t23, e4, i3) {
        return m2.indexOf(i3) < 0 && v2(t23, e4, i3);
      };
      for (n2 in h2) s2 = g2[n2], a2 = _2[n2], r2 = (e3 = s2 ? Jr(t22, this, n2) : h2[n2]).element, i2 = l2[n2], a2 ? (u2 = i2.isVisible || !a2.isVisible && r2 === i2.element ? i2 : a2, (o2 = !s2 || e3.isVisible || s2.isVisible || u2.element !== s2.element ? e3 : s2).isVisible && u2.isVisible && o2.element !== u2.element ? ((o2.isDifferent(u2) ? c2 : f2).push(o2.element, u2.element), m2.push(o2.element, u2.element)) : v2(o2, u2, o2.element), s2 && o2.element === s2.element && (s2 = h2[n2]), y2(o2.element !== i2.element && s2 ? s2 : o2, i2, i2.element), y2(s2 && s2.element === a2.element ? s2 : o2, a2, a2.element), s2 && y2(s2, a2.element === s2.element ? a2 : i2, s2.element)) : (i2 ? i2.isDifferent(e3) ? v2(e3, i2, r2) : f2.push(r2) : p2.push(r2), s2 && y2(s2, i2, s2.element));
      for (n2 in l2) h2[n2] || (d2.push(l2[n2].element), _2[n2] && d2.push(_2[n2].element));
      return { changed: c2, unchanged: f2, enter: p2, leave: d2 };
    }, e2.recordInlineStyles = function() {
      for (var t22 = Tr[this.props] || Sr, e3 = this.elementStates.length; e3--; ) Fr(this.elementStates[e3], t22);
    }, e2.interrupt = function(t22) {
      var e3 = this, i2 = [];
      this.targets.forEach((function(n2) {
        var r2 = n2._flip, s2 = ns(r2, t22 ? 0 : 1);
        t22 && s2 && i2.indexOf(r2) < 0 && r2.add((function() {
          return e3.updateVisibility();
        })), s2 && i2.push(r2);
      })), !t22 && i2.length && this.updateVisibility(), this.interrupted || (this.interrupted = !!i2.length);
    }, e2.updateVisibility = function() {
      this.elementStates.forEach((function(t22) {
        var e3 = t22.element.getBoundingClientRect();
        t22.isVisible = !!(e3.width || e3.height || e3.top || e3.left), t22.uncache = 1;
      }));
    }, e2.getElementState = function(t22) {
      return this.elementStates[this.targets.indexOf(Or(t22))];
    }, e2.makeAbsolute = function() {
      return zr(this.elementStates.slice(0), true, true).map(Xr);
    }, t21;
  })();
  var as = (function() {
    function t21(t22, e3, i2) {
      this.element = t22, this.update(e3, i2);
    }
    var e2 = t21.prototype;
    return e2.isDifferent = function(t22) {
      var e3 = this.bounds, i2 = t22.bounds;
      return e3.top !== i2.top || e3.left !== i2.left || e3.width !== i2.width || e3.height !== i2.height || !this.matrix.equals(t22.matrix) || this.opacity !== t22.opacity || this.props && t22.props && JSON.stringify(this.props) !== JSON.stringify(t22.props);
    }, e2.update = function(t22, e3) {
      var i2, n2, r2 = this, s2 = r2.element, a2 = lr.getProperty(s2), o2 = lr.core.getCache(s2), u2 = s2.getBoundingClientRect(), h2 = s2.getBBox && "function" == typeof s2.getBBox && "svg" !== s2.nodeName.toLowerCase() && s2.getBBox(), l2 = e3 ? new or(1, 0, 0, 1, u2.left + tr(), u2.top + Kn()) : ur(s2, false, false, true);
      r2.getProp = a2, r2.element = s2, r2.id = ((n2 = (i2 = s2).getAttribute("data-flip-id")) || i2.setAttribute("data-flip-id", n2 = "auto-" + gr++), n2), r2.matrix = l2, r2.cache = o2, r2.bounds = u2, r2.isVisible = !!(u2.width || u2.height || u2.left || u2.top), r2.display = a2("display"), r2.position = a2("position"), r2.parent = s2.parentNode, r2.x = a2("x"), r2.y = a2("y"), r2.scaleX = o2.scaleX, r2.scaleY = o2.scaleY, r2.rotation = a2("rotation"), r2.skewX = a2("skewX"), r2.opacity = a2("opacity"), r2.width = h2 ? h2.width : dr(a2("width", "px"), 0.04), r2.height = h2 ? h2.height : dr(a2("height", "px"), 0.04), t22 && (function(t23, e4) {
        for (var i3 = lr.getProperty(t23.element, null, "native"), n3 = t23.props = {}, r3 = e4.length; r3--; ) n3[e4[r3]] = (i3(e4[r3]) + "").trim();
        n3.zIndex && (n3.zIndex = parseFloat(n3.zIndex) || 0);
      })(r2, Lr[t22] || Br(t22)), r2.ctm = s2.getCTM && "svg" === s2.nodeName.toLowerCase() && rr(s2).inverse(), r2.simple = e3 || 1 === Er(l2.a) && !Er(l2.b) && !Er(l2.c) && 1 === Er(l2.d), r2.uncache = 0;
    }, t21;
  })();
  var os = (function() {
    function t21(t22, e3) {
      this.vars = t22, this.batch = e3, this.states = [], this.timeline = e3.timeline;
    }
    var e2 = t21.prototype;
    return e2.getStateById = function(t22) {
      for (var e3 = this.states.length; e3--; ) if (this.states[e3].idLookup[t22]) return this.states[e3];
    }, e2.kill = function() {
      this.batch.remove(this);
    }, t21;
  })();
  var us = (function() {
    function t21(t22) {
      this.id = t22, this.actions = [], this._kill = [], this._final = [], this._abs = [], this._run = [], this.data = {}, this.state = new ss(), this.timeline = lr.timeline();
    }
    var e2 = t21.prototype;
    return e2.add = function(t22) {
      var e3 = this.actions.filter((function(e4) {
        return e4.vars === t22;
      }));
      return e3.length ? e3[0] : (e3 = new os("function" == typeof t22 ? { animate: t22 } : t22, this), this.actions.push(e3), e3);
    }, e2.remove = function(t22) {
      var e3 = this.actions.indexOf(t22);
      return e3 >= 0 && this.actions.splice(e3, 1), this;
    }, e2.getState = function(t22) {
      var e3 = this, i2 = fr, n2 = cr;
      return fr = this, this.state.clear(), this._kill.length = 0, this.actions.forEach((function(i3) {
        i3.vars.getState && (i3.states.length = 0, cr = i3, i3.state = i3.vars.getState(i3)), t22 && i3.states.forEach((function(t23) {
          return e3.state.add(t23);
        }));
      })), cr = n2, fr = i2, this.killConflicts(), this;
    }, e2.animate = function() {
      var t22, e3, i2 = this, n2 = fr, r2 = this.timeline, s2 = this.actions.length;
      for (fr = this, r2.clear(), this._abs.length = this._final.length = this._run.length = 0, this.actions.forEach((function(t23) {
        t23.vars.animate && t23.vars.animate(t23);
        var e4, i3, n3 = t23.vars.onEnter, r3 = t23.vars.onLeave, s3 = t23.targets;
        s3 && s3.length && (n3 || r3) && (e4 = new ss(), t23.states.forEach((function(t24) {
          return e4.add(t24);
        })), (i3 = e4.compare(hs.getState(s3))).enter.length && n3 && n3(i3.enter), i3.leave.length && r3 && r3(i3.leave));
      })), jr(this._abs), this._run.forEach((function(t23) {
        return t23();
      })), e3 = r2.duration(), t22 = this._final.slice(0), r2.add((function() {
        e3 <= r2.time() && (t22.forEach((function(t23) {
          return t23();
        })), _r(i2, "onComplete"));
      })), fr = n2; s2--; ) this.actions[s2].vars.once && this.actions[s2].kill();
      return _r(this, "onStart"), r2.restart(), this;
    }, e2.loadState = function(t22) {
      t22 || (t22 = function() {
        return 0;
      });
      var e3 = [];
      return this.actions.forEach((function(i2) {
        if (i2.vars.loadState) {
          var n2, r2 = function r3(s2) {
            s2 && (i2.targets = s2), ~(n2 = e3.indexOf(r3)) && (e3.splice(n2, 1), e3.length || t22());
          };
          e3.push(r2), i2.vars.loadState(r2);
        }
      })), e3.length || t22(), this;
    }, e2.setState = function() {
      return this.actions.forEach((function(t22) {
        return t22.targets = t22.vars.setState && t22.vars.setState(t22);
      })), this;
    }, e2.killConflicts = function(t22) {
      return this.state.interrupt(t22), this._kill.forEach((function(e3) {
        return e3.interrupt(t22);
      })), this;
    }, e2.run = function(t22, e3) {
      var i2 = this;
      return this !== fr && (t22 || this.getState(e3), this.loadState((function() {
        i2._killed || (i2.setState(), i2.animate());
      }))), this;
    }, e2.clear = function(t22) {
      this.state.clear(), t22 || (this.actions.length = 0);
    }, e2.getStateById = function(t22) {
      for (var e3, i2 = this.actions.length; i2--; ) if (e3 = this.actions[i2].getStateById(t22)) return e3;
      return this.state.idLookup[t22] && this.state;
    }, e2.kill = function() {
      this._killed = 1, this.clear(), delete vr[this.id];
    }, t21;
  })();
  var hs = (function() {
    function t21() {
    }
    return t21.getState = function(e2, i2) {
      var n2 = $r(e2, i2);
      return cr && cr.states.push(n2), i2 && i2.batch && t21.batch(i2.batch).state.add(n2), n2;
    }, t21.from = function(t22, e2) {
      return "clearProps" in (e2 = e2 || {}) || (e2.clearProps = true), es(t22, $r(e2.targets || t22.targets, { props: e2.props || t22.props, simple: e2.simple, kill: !!e2.kill }), e2, -1);
    }, t21.to = function(t22, e2) {
      return es(t22, $r(e2.targets || t22.targets, { props: e2.props || t22.props, simple: e2.simple, kill: !!e2.kill }), e2, 1);
    }, t21.fromTo = function(t22, e2, i2) {
      return es(t22, e2, i2);
    }, t21.fit = function(t22, e2, i2) {
      var n2 = i2 ? Dr(i2, Pr) : {}, r2 = i2 || n2, s2 = r2.absolute, a2 = r2.scale, o2 = r2.getVars, u2 = r2.props, h2 = r2.runBackwards, l2 = r2.onComplete, f2 = r2.simple, c2 = i2 && i2.fitChild && Or(i2.fitChild), p2 = Ur(e2, u2, f2, t22), d2 = Ur(t22, 0, f2, p2), m2 = u2 ? Tr[u2] : Sr;
      return u2 && Wr(n2, p2.props), h2 && (Fr(d2, m2), "immediateRender" in n2 || (n2.immediateRender = true), n2.onComplete = function() {
        Vr(d2), l2 && l2.apply(this, arguments);
      }), s2 && Xr(d2, p2), n2 = Gr(d2, p2, a2 || c2, u2, c2, n2.duration || o2 ? n2 : 0), o2 ? n2 : n2.duration ? lr.to(d2.element, n2) : null;
    }, t21.makeAbsolute = function(t22, e2) {
      return (t22 instanceof ss ? t22 : new ss(t22, e2)).makeAbsolute();
    }, t21.batch = function(t22) {
      return t22 || (t22 = "default"), vr[t22] || (vr[t22] = new us(t22));
    }, t21.killFlipsOf = function(t22, e2) {
      (t22 instanceof ss ? t22.targets : hr(t22)).forEach((function(t23) {
        return t23 && ns(t23._flip, false !== e2 ? 1 : 2);
      }));
    }, t21.isFlipping = function(e2) {
      var i2 = t21.getByTarget(e2);
      return !!i2 && i2.isActive();
    }, t21.getByTarget = function(t22) {
      return (Or(t22) || br)._flip;
    }, t21.getElementState = function(t22, e2) {
      return new as(Or(t22), e2);
    }, t21.convertCoordinates = function(t22, e2, i2) {
      var n2 = ur(e2, true, true).multiply(ur(t22));
      return i2 ? n2.apply(i2) : n2;
    }, t21.register = function(t22) {
      if (pr = "undefined" != typeof document && document.body) {
        lr = t22, $n(pr), hr = lr.utils.toArray;
        var e2 = lr.utils.snap(0.1);
        dr = function(t23, i2) {
          return e2(parseFloat(t23) + i2);
        };
      }
    }, t21;
  })();
  hs.version = "3.10.4", "undefined" != typeof window && window.gsap && window.gsap.registerPlugin(hs), Hn.registerPlugin(hs);
  var ls = { width: window.innerWidth, height: window.innerHeight };
  window.addEventListener("resize", (() => ls = { width: window.innerWidth, height: window.innerHeight }));
  var fs = { grid: document.querySelector(".grid"), enterCtrl: document.querySelector(".content__enter"), backCtrl: document.querySelector(".button-back"), contentItem: document.querySelector(".content__item-img"), gridItemTarget: document.querySelector(".grid__item--target"), gridItemOriginalTarget: document.querySelector(".content__item"), contentTitleTexts: document.querySelectorAll(".content__item-title > span"), gridTitleTexts: document.querySelectorAll(".grid__item--title > span"), gridItems: document.querySelectorAll(".grid > .grid__item:not(.grid__item--target):not(.grid__item--title):not(.grid__item--back)") };
  var cs = 1;
  var ps = "expo.inOut";
  var ds = document.body;
  var ms = getComputedStyle(ds).getPropertyValue("--color-bg");
  var gs = false;
  var _s = (t21, e2 = 400) => {
    const i2 = t21.offsetLeft + t21.offsetWidth / 2, n2 = t21.offsetTop + t21.offsetHeight / 2, r2 = Math.atan2(Math.abs(ls.height / 2 - n2), Math.abs(ls.width / 2 - i2));
    let s2 = Math.abs(Math.cos(r2) * e2), a2 = Math.abs(Math.sin(r2) * e2);
    return { x: i2 < ls.width / 2 ? -1 * s2 : s2, y: n2 < ls.height / 2 ? -1 * a2 : a2 };
  };
  var vs = (t21) => {
    const e2 = t21.offsetLeft + t21.offsetWidth / 2, i2 = t21.offsetTop + t21.offsetHeight / 2;
    return Math.hypot(e2 - ls.width / 2, i2 - ls.height / 2);
  };
  fs.enterCtrl.addEventListener("click", (() => (() => {
    if (gs) return;
    gs = true;
    const t21 = Hn.timeline({ onComplete: () => {
      gs = false;
    } }).addLabel("start", 0).to(fs.enterCtrl, { duration: cs, ease: ps, opacity: 0, onComplete: () => Hn.set(fs.enterCtrl, { pointerEvents: "none" }) }, "start").add((() => {
      fs.grid.classList.add("grid--open");
      const t22 = hs.getState(fs.contentItem);
      fs.gridItemTarget.appendChild(fs.contentItem), hs.from(t22, { duration: cs, ease: ps });
    }), "start");
    for (let e2 of fs.gridItems) {
      const { x: i2, y: n2 } = _s(e2), r2 = s(vs(e2), 0, 1e3, 0, 0.4);
      t21.to(e2.querySelector(".oh__inner"), { duration: 1.7 * cs, ease: ps, startAt: { yPercent: 101 }, yPercent: 0, delay: r2 }, "start").set(e2, { x: i2, y: n2, opacity: 0 }, "start").to(e2, { duration: cs, ease: "expo", x: 0, y: 0, delay: r2, opacity: 1 }, "start+=0.4");
    }
    t21.to(fs.gridItemTarget.querySelector(".oh__inner"), { duration: 1.7 * cs, ease: ps, startAt: { yPercent: 101 }, yPercent: 0 }, "start").to(fs.contentTitleTexts, { duration: cs, ease: ps, yPercent: (t22) => t22 % 2 ? 100 : -100, opacity: 0 }, "start").to(fs.gridTitleTexts, { duration: cs, ease: ps, startAt: { xPercent: (t22) => t22 % 2 ? 50 : -50, opacity: 0 }, xPercent: 0, opacity: 1 }, "start").to(fs.backCtrl, { duration: cs, ease: ps, startAt: { xPercent: 40, opacity: 0 }, xPercent: 0, opacity: 1 }, "start").to(ds, { duration: cs, ease: ps, backgroundColor: "#CDD1CD" }, "start");
  })())), fs.backCtrl.addEventListener("click", (() => (() => {
    if (gs) return;
    gs = true;
    const t21 = Hn.timeline({ onComplete: () => {
      fs.grid.classList.remove("grid--open"), gs = false;
    } }).addLabel("start", 0).to(ds, { duration: cs, ease: ps, backgroundColor: ms }, "start").to(fs.gridItemTarget.querySelector(".oh__inner"), { duration: cs, ease: ps, yPercent: 101 }, "start");
    for (let e2 of fs.gridItems) {
      const { x: i2, y: n2 } = _s(e2), r2 = s(vs(e2), 0, 1e3, 0.4, 0);
      t21.to(e2, { duration: cs, ease: ps, x: i2, y: n2, opacity: 0, delay: r2 }, "start").to(e2.querySelector(".oh__inner"), { duration: 0.5 * cs, ease: ps, yPercent: 101, delay: r2 }, "start");
    }
    t21.to(fs.gridTitleTexts, { duration: cs, ease: ps, xPercent: (t22) => t22 % 2 ? 50 : -50, opacity: 0 }, "start").to(fs.backCtrl, { duration: cs, ease: ps, xPercent: 20, opacity: 0 }, "start").to(fs.contentTitleTexts, { duration: cs, ease: ps, yPercent: 0, opacity: 1 }, "start+=0.4").to(fs.enterCtrl, { duration: cs, ease: ps, opacity: 1, onComplete: () => Hn.set(fs.enterCtrl, { pointerEvents: "auto" }) }, "start+=0.4").add((() => {
      const t22 = hs.getState(fs.contentItem);
      fs.gridItemOriginalTarget.appendChild(fs.contentItem), hs.from(t22, { duration: cs, ease: ps });
    }), "start+=0.4");
  })())), ((t21 = "img") => new Promise(((e2) => {
    r(document.querySelectorAll(t21), { background: true }, e2);
  })))(".grid__item-img").then(((t21) => document.body.classList.remove("loading")));
})();
/*!
 * imagesLoaded v5.0.0
 * JavaScript is all like "You images are done yet or what?"
 * MIT License
 */
/*!
 * GSAP 3.10.4
 * https://greensock.com
 *
 * @license Copyright 2008-2022, GreenSock. All rights reserved.
 * Subject to the terms at https://greensock.com/standard-license or for
 * Club GreenSock members, the agreement issued with that membership.
 * @author: Jack Doyle, jack@greensock.com
*/
/*!
 * matrix 3.10.4
 * https://greensock.com
 *
 * Copyright 2008-2022, GreenSock. All rights reserved.
 * Subject to the terms at https://greensock.com/standard-license or for
 * Club GreenSock members, the agreement issued with that membership.
 * @author: Jack Doyle, jack@greensock.com
*/
;
!function(){var t="undefined"!=typeof globalThis?globalThis:"undefined"!=typeof self?self:"undefined"!=typeof window?window:"undefined"!=typeof global?global:{},e={},i={},n=t.parcelRequirec455;null==n&&((n=function(t){if(t in e)return e[t].exports;if(t in i){var n=i[t];delete i[t];var r={id:t,exports:{}};return e[t]=r,n.call(r.exports,r,r.exports),r.exports}var s=new Error("Cannot find module '"+t+"'");throw s.code="MODULE_NOT_FOUND",s}).register=function(t,e){i[t]=e},t.parcelRequirec455=n),n.register("hobco",(function(t,e){!function(e,i){t.exports?t.exports=i():e.EvEmitter=i()}("undefined"!=typeof window?window:t.exports,(function(){function t(){}var e=t.prototype;return e.on=function(t,e){if(!t||!e)return this;var i=this._events=this._events||{},n=i[t]=i[t]||[];return n.includes(e)||n.push(e),this},e.once=function(t,e){if(!t||!e)return this;this.on(t,e);var i=this._onceEvents=this._onceEvents||{};return(i[t]=i[t]||{})[e]=!0,this},e.off=function(t,e){var i=this._events&&this._events[t];if(!i||!i.length)return this;var n=i.indexOf(e);return-1!=n&&i.splice(n,1),this},e.emitEvent=function(t,e){var i=this._events&&this._events[t];if(!i||!i.length)return this;i=i.slice(0),e=e||[];var n=this._onceEvents&&this._onceEvents[t],r=!0,s=!1,a=void 0;try{for(var o,u=i[Symbol.iterator]();!(r=(o=u.next()).done);r=!0){var h=o.value;n&&n[h]&&(this.off(t,h),delete n[h]),h.apply(this,e)}}catch(t){s=!0,a=t}finally{try{r||null==u.return||u.return()}finally{if(s)throw a}}return this},e.allOff=function(){return delete this._events,delete this._onceEvents,this},t}))}));var r={};function s(t,e){(null==e||e>t.length)&&(e=t.length);for(var i=0,n=new Array(e);i<e;i++)n[i]=t[i];return n}function a(t){return function(t){if(Array.isArray(t))return s(t)}(t)||function(t){if("undefined"!=typeof Symbol&&null!=t[Symbol.iterator]||null!=t["@@iterator"])return Array.from(t)}(t)||function(t,e){if(t){if("string"==typeof t)return s(t,e);var i=Object.prototype.toString.call(t).slice(8,-1);return"Object"===i&&t.constructor&&(i=t.constructor.name),"Map"===i||"Set"===i?Array.from(i):"Arguments"===i||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(i)?s(t,e):void 0}}(t)||function(){throw new TypeError("Invalid attempt to spread non-iterable instance.\\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")}()}function o(t){return t&&t.constructor===Symbol?"symbol":typeof t}
/*!
 * imagesLoaded v5.0.0
 * JavaScript is all like "You images are done yet or what?"
 * MIT License
 */!function(t,e){r?r=e(t,n("hobco")):t.imagesLoaded=e(t,t.EvEmitter)}("undefined"!=typeof window?window:void 0,(function(t,e){var i=t.jQuery,n=t.console;function r(t,e,s){if(!(this instanceof r))return new r(t,e,s);var o,u=t;("string"==typeof t&&(u=document.querySelectorAll(t)),u)?(this.elements=(o=u,Array.isArray(o)?o:"object"==typeof o&&"number"==typeof o.length?a(o):[o]),this.options={},"function"==typeof e?s=e:Object.assign(this.options,e),s&&this.on("always",s),this.getImages(),i&&(this.jqDeferred=new i.Deferred),__hf.setTimeout(this.check.bind(this))):n.error("Bad element for imagesLoaded ".concat(u||t))}r.prototype=Object.create(e.prototype),r.prototype.getImages=function(){this.images=[],this.elements.forEach(this.addElementImages,this)};var s=[1,9,11];r.prototype.addElementImages=function(t){"IMG"===t.nodeName&&this.addImage(t),!0===this.options.background&&this.addElementBackgroundImages(t);var e=t.nodeType;if(e&&s.includes(e)){var i=t.querySelectorAll("img"),n=!0,r=!1,a=void 0;try{for(var o,u=i[Symbol.iterator]();!(n=(o=u.next()).done);n=!0){var h=o.value;this.addImage(h)}}catch(t){r=!0,a=t}finally{try{n||null==u.return||u.return()}finally{if(r)throw a}}if("string"==typeof this.options.background){var l=t.querySelectorAll(this.options.background),f=!0,c=!1,p=void 0;try{for(var d,m=l[Symbol.iterator]();!(f=(d=m.next()).done);f=!0){var g=d.value;this.addElementBackgroundImages(g)}}catch(t){c=!0,p=t}finally{try{f||null==m.return||m.return()}finally{if(c)throw p}}}}};var o=/url\((['"])?(.*?)\1\)/gi;function u(t){this.img=t}function h(t,e){this.url=t,this.element=e,this.img=new Image}return r.prototype.addElementBackgroundImages=function(t){var e=getComputedStyle(t);if(e)for(var i=o.exec(e.backgroundImage);null!==i;){var n=i&&i[2];n&&this.addBackground(n,t),i=o.exec(e.backgroundImage)}},r.prototype.addImage=function(t){var e=new u(t);this.images.push(e)},r.prototype.addBackground=function(t,e){var i=new h(t,e);this.images.push(i)},r.prototype.check=function(){var t=this;if(this.progressedCount=0,this.hasAnyBroken=!1,this.images.length){var e=function(e,i,n){var r=t;__hf.setTimeout((function(){r.progress(e,i,n)}))};this.images.forEach((function(t){t.once("progress",e),t.check()}))}else this.complete()},r.prototype.progress=function(t,e,i){this.progressedCount++,this.hasAnyBroken=this.hasAnyBroken||!t.isLoaded,this.emitEvent("progress",[this,t,e]),this.jqDeferred&&this.jqDeferred.notify&&this.jqDeferred.notify(this,t),this.progressedCount===this.images.length&&this.complete(),this.options.debug&&n&&n.log("progress: ".concat(i),t,e)},r.prototype.complete=function(){var t=this.hasAnyBroken?"fail":"done";if(this.isComplete=!0,this.emitEvent(t,[this]),this.emitEvent("always",[this]),this.jqDeferred){var e=this.hasAnyBroken?"reject":"resolve";this.jqDeferred[e](this)}},u.prototype=Object.create(e.prototype),u.prototype.check=function(){this.getIsImageComplete()?this.confirm(0!==this.img.naturalWidth,"naturalWidth"):(this.proxyImage=new Image,this.img.crossOrigin&&(this.proxyImage.crossOrigin=this.img.crossOrigin),this.proxyImage.addEventListener("load",this),this.proxyImage.addEventListener("error",this),this.img.addEventListener("load",this),this.img.addEventListener("error",this),this.proxyImage.src=this.img.currentSrc||this.img.src)},u.prototype.getIsImageComplete=function(){return this.img.complete&&this.img.naturalWidth},u.prototype.confirm=function(t,e){this.isLoaded=t;var i=this.img.parentNode,n="PICTURE"===i.nodeName?i:this.img;this.emitEvent("progress",[this,n,e])},u.prototype.handleEvent=function(t){var e="on"+t.type;this[e]&&this[e](t)},u.prototype.onload=function(){this.confirm(!0,"onload"),this.unbindEvents()},u.prototype.onerror=function(){this.confirm(!1,"onerror"),this.unbindEvents()},u.prototype.unbindEvents=function(){this.proxyImage.removeEventListener("load",this),this.proxyImage.removeEventListener("error",this),this.img.removeEventListener("load",this),this.img.removeEventListener("error",this)},h.prototype=Object.create(u.prototype),h.prototype.check=function(){this.img.addEventListener("load",this),this.img.addEventListener("error",this),this.img.src=this.url,this.getIsImageComplete()&&(this.confirm(0!==this.img.naturalWidth,"naturalWidth"),this.unbindEvents())},h.prototype.unbindEvents=function(){this.img.removeEventListener("load",this),this.img.removeEventListener("error",this)},h.prototype.confirm=function(t,e){this.isLoaded=t,this.emitEvent("progress",[this,this.element,e])},r.makeJQueryPlugin=function(e){(e=e||t.jQuery)&&((i=e).fn.imagesLoaded=function(t,e){return new r(this,t,e).jqDeferred.promise(i(this))})},r.makeJQueryPlugin(),r}));var u=function(t,e,i,n,r){return(t-e)*(r-n)/(i-e)+n};function h(t){if(void 0===t)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return t}function l(t,e){t.prototype=Object.create(e.prototype),t.prototype.constructor=t,t.__proto__=e}
/*!
 * GSAP 3.10.4
 * https://greensock.com
 *
 * @license Copyright 2008-2022, GreenSock. All rights reserved.
 * Subject to the terms at https://greensock.com/standard-license or for
 * Club GreenSock members, the agreement issued with that membership.
 * @author: Jack Doyle, jack@greensock.com
*/var f,c,p,d,m,g,_,v,y,b,x,w,T,k,C,S,O,E,M,A,P,I,D,L,B,R,z,F,V={autoSleep:120,force3D:"auto",nullTargetWarn:1,units:{lineHeight:""}},N={duration:.5,overwrite:!1,delay:0},q=1e8,X=1e-8,Y=2*Math.PI,j=Y/4,U=0,W=Math.sqrt,H=Math.cos,Q=Math.sin,G=function(t){return"string"==typeof t},Z=function(t){return"function"==typeof t},$=function(t){return"number"==typeof t},J=function(t){return void 0===t},K=function(t){return"object"==typeof t},tt=function(t){return!1!==t},et=function(){return"undefined"!=typeof window},it=function(t){return Z(t)||G(t)},nt="function"==typeof ArrayBuffer&&ArrayBuffer.isView||function(){},rt=Array.isArray,st=/(?:-?\.?\d|\.)+/gi,at=/[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/g,ot=/[-+=.]*\d+[.e-]*\d*[a-z%]*/g,ut=/[-+=.]*\d+\.?\d*(?:e-|e\+)?\d*/gi,ht=/[+-]=-?[.\d]+/,lt=/[^,'"\[\]\s]+/gi,ft=/^[+\-=e\s\d]*\d+[.\d]*([a-z]*|%)\s*$/i,ct={},pt={},dt=function(t){return(pt=Nt(t,ct))&&Ai},mt=function(t,e){return console.warn("Invalid property",t,"set to",e,"Missing plugin? gsap.registerPlugin()")},gt=function(t,e){return!e&&console.warn(t)},_t=function(t,e){return t&&(ct[t]=e)&&pt&&(pt[t]=e)||ct},vt=function(){return 0},yt={},bt=[],xt={},wt={},Tt={},kt=30,Ct=[],St="",Ot=function(t){var e,i,n=t[0];if(K(n)||Z(n)||(t=[t]),!(e=(n._gsap||{}).harness)){for(i=Ct.length;i--&&!Ct[i].targetTest(n););e=Ct[i]}for(i=t.length;i--;)t[i]&&(t[i]._gsap||(t[i]._gsap=new Ke(t[i],e)))||t.splice(i,1);return t},Et=function(t){return t._gsap||Ot(ve(t))[0]._gsap},Mt=function(t,e,i){return(i=t[e])&&Z(i)?t[e]():J(i)&&t.getAttribute&&t.getAttribute(e)||i},At=function(t,e){return(t=t.split(",")).forEach(e)||t},Pt=function(t){return Math.round(1e5*t)/1e5||0},It=function(t){return Math.round(1e7*t)/1e7||0},Dt=function(t,e){var i=e.charAt(0),n=parseFloat(e.substr(2));return t=parseFloat(t),"+"===i?t+n:"-"===i?t-n:"*"===i?t*n:t/n},Lt=function(t,e){for(var i=e.length,n=0;t.indexOf(e[n])<0&&++n<i;);return n<i},Bt=function(){var t,e,i=bt.length,n=bt.slice(0);for(xt={},bt.length=0,t=0;t<i;t++)(e=n[t])&&e._lazy&&(e.render(e._lazy[0],e._lazy[1],!0)._lazy=0)},Rt=function(t,e,i,n){bt.length&&Bt(),t.render(e,i,n),bt.length&&Bt()},zt=function(t){var e=parseFloat(t);return(e||0===e)&&(t+"").match(lt).length<2?e:G(t)?t.trim():t},Ft=function(t){return t},Vt=function(t,e){for(var i in e)i in t||(t[i]=e[i]);return t},Nt=function(t,e){for(var i in e)t[i]=e[i];return t},qt=function t(e,i){for(var n in i)"__proto__"!==n&&"constructor"!==n&&"prototype"!==n&&(e[n]=K(i[n])?t(e[n]||(e[n]={}),i[n]):i[n]);return e},Xt=function(t,e){var i,n={};for(i in t)i in e||(n[i]=t[i]);return n},Yt=function(t){var e,i=t.parent||c,n=t.keyframes?(e=rt(t.keyframes),function(t,i){for(var n in i)n in t||"duration"===n&&e||"ease"===n||(t[n]=i[n])}):Vt;if(tt(t.inherit))for(;i;)n(t,i.vars.defaults),i=i.parent||i._dp;return t},jt=function(t,e,i,n,r){void 0===i&&(i="_first"),void 0===n&&(n="_last");var s,a=t[n];if(r)for(s=e[r];a&&a[r]>s;)a=a._prev;return a?(e._next=a._next,a._next=e):(e._next=t[i],t[i]=e),e._next?e._next._prev=e:t[n]=e,e._prev=a,e.parent=e._dp=t,e},Ut=function(t,e,i,n){void 0===i&&(i="_first"),void 0===n&&(n="_last");var r=e._prev,s=e._next;r?r._next=s:t[i]===e&&(t[i]=s),s?s._prev=r:t[n]===e&&(t[n]=r),e._next=e._prev=e.parent=null},Wt=function(t,e){t.parent&&(!e||t.parent.autoRemoveChildren)&&t.parent.remove(t),t._act=0},Ht=function(t,e){if(t&&(!e||e._end>t._dur||e._start<0))for(var i=t;i;)i._dirty=1,i=i.parent;return t},Qt=function(t){for(var e=t.parent;e&&e.parent;)e._dirty=1,e.totalDuration(),e=e.parent;return t},Gt=function t(e){return!e||e._ts&&t(e.parent)},Zt=function(t){return t._repeat?$t(t._tTime,t=t.duration()+t._rDelay)*t:0},$t=function(t,e){var i=Math.floor(t/=e);return t&&i===t?i-1:i},Jt=function(t,e){return(t-e._start)*e._ts+(e._ts>=0?0:e._dirty?e.totalDuration():e._tDur)},Kt=function(t){return t._end=It(t._start+(t._tDur/Math.abs(t._ts||t._rts||X)||0))},te=function(t,e){var i=t._dp;return i&&i.smoothChildTiming&&t._ts&&(t._start=It(i._time-(t._ts>0?e/t._ts:((t._dirty?t.totalDuration():t._tDur)-e)/-t._ts)),Kt(t),i._dirty||Ht(i,t)),t},ee=function(t,e){var i;if((e._time||e._initted&&!e._dur)&&(i=Jt(t.rawTime(),e),(!e._dur||pe(0,e.totalDuration(),i)-e._tTime>X)&&e.render(i,!0)),Ht(t,e)._dp&&t._initted&&t._time>=t._dur&&t._ts){if(t._dur<t.duration())for(i=t;i._dp;)i.rawTime()>=0&&i.totalTime(i._tTime),i=i._dp;t._zTime=-1e-8}},ie=function(t,e,i,n){return e.parent&&Wt(e),e._start=It(($(i)?i:i||t!==c?le(t,i,e):t._time)+e._delay),e._end=It(e._start+(e.totalDuration()/Math.abs(e.timeScale())||0)),jt(t,e,"_first","_last",t._sort?"_start":0),ae(e)||(t._recent=e),n||ee(t,e),t},ne=function(t,e){return(ct.ScrollTrigger||mt("scrollTrigger",e))&&ct.ScrollTrigger.create(e,t)},re=function(t,e,i,n){return oi(t,e),t._initted?!i&&t._pt&&(t._dur&&!1!==t.vars.lazy||!t._dur&&t.vars.lazy)&&_!==Ne.frame?(bt.push(t),t._lazy=[e,n],1):void 0:1},se=function t(e){var i=e.parent;return i&&i._ts&&i._initted&&!i._lock&&(i.rawTime()<0||t(i))},ae=function(t){var e=t.data;return"isFromStart"===e||"isStart"===e},oe=function(t,e,i,n){var r=t._repeat,s=It(e)||0,a=t._tTime/t._tDur;return a&&!n&&(t._time*=s/t._dur),t._dur=s,t._tDur=r?r<0?1e10:It(s*(r+1)+t._rDelay*r):s,a>0&&!n?te(t,t._tTime=t._tDur*a):t.parent&&Kt(t),i||Ht(t.parent,t),t},ue=function(t){return t instanceof ei?Ht(t):oe(t,t._dur)},he={_start:0,endTime:vt,totalDuration:vt},le=function t(e,i,n){var r,s,a,o=e.labels,u=e._recent||he,h=e.duration()>=q?u.endTime(!1):e._dur;return G(i)&&(isNaN(i)||i in o)?(s=i.charAt(0),a="%"===i.substr(-1),r=i.indexOf("="),"<"===s||">"===s?(r>=0&&(i=i.replace(/=/,"")),("<"===s?u._start:u.endTime(u._repeat>=0))+(parseFloat(i.substr(1))||0)*(a?(r<0?u:n).totalDuration()/100:1)):r<0?(i in o||(o[i]=h),o[i]):(s=parseFloat(i.charAt(r-1)+i.substr(r+1)),a&&n&&(s=s/100*(rt(n)?n[0]:n).totalDuration()),r>1?t(e,i.substr(0,r-1),n)+s:h+s)):null==i?h:+i},fe=function(t,e,i){var n,r,s=$(e[1]),a=(s?2:1)+(t<2?0:1),o=e[a];if(s&&(o.duration=e[1]),o.parent=i,t){for(n=o,r=i;r&&!("immediateRender"in n);)n=r.vars.defaults||{},r=tt(r.vars.inherit)&&r.parent;o.immediateRender=tt(n.immediateRender),t<2?o.runBackwards=1:o.startAt=e[a-1]}return new ci(e[0],o,e[a+1])},ce=function(t,e){return t||0===t?e(t):e},pe=function(t,e,i){return i<t?t:i>e?e:i},de=function(t,e){return G(t)&&(e=ft.exec(t))?e[1]:""},me=[].slice,ge=function(t,e){return t&&K(t)&&"length"in t&&(!e&&!t.length||t.length-1 in t&&K(t[0]))&&!t.nodeType&&t!==p},_e=function(t,e,i){return void 0===i&&(i=[]),t.forEach((function(t){var n;return G(t)&&!e||ge(t,1)?(n=i).push.apply(n,ve(t)):i.push(t)}))||i},ve=function(t,e,i){return!G(t)||i||!d&&qe()?rt(t)?_e(t,i):ge(t)?me.call(t,0):t?[t]:[]:me.call((e||m).querySelectorAll(t),0)},ye=function(t){return t.sort((function(){return.5-__hf.random()}))},be=function(t){if(Z(t))return t;var e=K(t)?t:{each:t},i=Qe(e.ease),n=e.from||0,r=parseFloat(e.base)||0,s={},a=n>0&&n<1,o=isNaN(n)||a,u=e.axis,h=n,l=n;return G(n)?h=l={center:.5,edges:.5,end:1}[n]||0:!a&&o&&(h=n[0],l=n[1]),function(t,a,f){var c,p,d,m,g,_,v,y,b,x=(f||e).length,w=s[x];if(!w){if(!(b="auto"===e.grid?0:(e.grid||[1,q])[1])){for(v=-1e8;v<(v=f[b++].getBoundingClientRect().left)&&b<x;);b--}for(w=s[x]=[],c=o?Math.min(b,x)*h-.5:n%b,p=b===q?0:o?x*l/b-.5:n/b|0,v=0,y=q,_=0;_<x;_++)d=_%b-c,m=p-(_/b|0),w[_]=g=u?Math.abs("y"===u?m:d):W(d*d+m*m),g>v&&(v=g),g<y&&(y=g);"random"===n&&ye(w),w.max=v-y,w.min=y,w.v=x=(parseFloat(e.amount)||parseFloat(e.each)*(b>x?x-1:u?"y"===u?x/b:b:Math.max(b,x/b))||0)*("edges"===n?-1:1),w.b=x<0?r-x:r,w.u=de(e.amount||e.each)||0,i=i&&x<0?We(i):i}return x=(w[t]-w.min)/w.max||0,It(w.b+(i?i(x):x)*w.v)+w.u}},xe=function(t){var e=Math.pow(10,((t+"").split(".")[1]||"").length);return function(i){var n=Math.round(parseFloat(i)/t)*t*e;return(n-n%1)/e+($(i)?0:de(i))}},we=function(t,e){var i,n,r=rt(t);return!r&&K(t)&&(i=r=t.radius||q,t.values?(t=ve(t.values),(n=!$(t[0]))&&(i*=i)):t=xe(t.increment)),ce(e,r?Z(t)?function(e){return n=t(e),Math.abs(n-e)<=i?n:e}:function(e){for(var r,s,a=parseFloat(n?e.x:e),o=parseFloat(n?e.y:0),u=q,h=0,l=t.length;l--;)(r=n?(r=t[l].x-a)*r+(s=t[l].y-o)*s:Math.abs(t[l]-a))<u&&(u=r,h=l);return h=!i||u<=i?t[h]:e,n||h===e||$(e)?h:h+de(e)}:xe(t))},Te=function(t,e,i,n){return ce(rt(t)?!e:!0===i?(i=0,!1):!n,(function(){return rt(t)?t[~~(__hf.random()*t.length)]:(n=(i=i||1e-5)<1?Math.pow(10,(i+"").length-2):1)&&Math.floor(Math.round((t-i/2+__hf.random()*(e-t+.99*i))/i)*i*n)/n}))},ke=function(t,e,i){return ce(i,(function(i){return t[~~e(i)]}))},Ce=function(t){for(var e,i,n,r,s=0,a="";~(e=t.indexOf("random(",s));)n=t.indexOf(")",e),r="["===t.charAt(e+7),i=t.substr(e+7,n-e-7).match(r?lt:st),a+=t.substr(s,e-s)+Te(r?i:+i[0],r?0:+i[1],+i[2]||1e-5),s=n+1;return a+t.substr(s,t.length-s)},Se=function(t,e,i,n,r){var s=e-t,a=n-i;return ce(r,(function(e){return i+((e-t)/s*a||0)}))},Oe=function(t,e,i){var n,r,s,a=t.labels,o=q;for(n in a)(r=a[n]-e)<0==!!i&&r&&o>(r=Math.abs(r))&&(s=n,o=r);return s},Ee=function(t,e,i){var n,r,s=t.vars,a=s[e];if(a)return n=s[e+"Params"],r=s.callbackScope||t,i&&bt.length&&Bt(),n?a.apply(r,n):a.call(r)},Me=function(t){return Wt(t),t.scrollTrigger&&t.scrollTrigger.kill(!1),t.progress()<1&&Ee(t,"onInterrupt"),t},Ae=function(t){var e=(t=!t.name&&t.default||t).name,i=Z(t),n=e&&!i&&t.init?function(){this._props=[]}:t,r={init:vt,render:xi,add:si,kill:Ti,modifier:wi,rawVars:0},s={targetTest:0,get:0,getSetter:_i,aliases:{},register:0};if(qe(),t!==n){if(wt[e])return;Vt(n,Vt(Xt(t,r),s)),Nt(n.prototype,Nt(r,Xt(t,s))),wt[n.prop=e]=n,t.targetTest&&(Ct.push(n),yt[e]=1),e=("css"===e?"CSS":e.charAt(0).toUpperCase()+e.substr(1))+"Plugin"}_t(e,n),t.register&&t.register(Ai,n,Si)},Pe=255,Ie={aqua:[0,Pe,Pe],lime:[0,Pe,0],silver:[192,192,192],black:[0,0,0],maroon:[128,0,0],teal:[0,128,128],blue:[0,0,Pe],navy:[0,0,128],white:[Pe,Pe,Pe],olive:[128,128,0],yellow:[Pe,Pe,0],orange:[Pe,165,0],gray:[128,128,128],purple:[128,0,128],green:[0,128,0],red:[Pe,0,0],pink:[Pe,192,203],cyan:[0,Pe,Pe],transparent:[Pe,Pe,Pe,0]},De=function(t,e,i){return(6*(t+=t<0?1:t>1?-1:0)<1?e+(i-e)*t*6:t<.5?i:3*t<2?e+(i-e)*(2/3-t)*6:e)*Pe+.5|0},Le=function(t,e,i){var n,r,s,a,o,u,h,l,f,c,p=t?$(t)?[t>>16,t>>8&Pe,t&Pe]:0:Ie.black;if(!p){if(","===t.substr(-1)&&(t=t.substr(0,t.length-1)),Ie[t])p=Ie[t];else if("#"===t.charAt(0)){if(t.length<6&&(n=t.charAt(1),r=t.charAt(2),s=t.charAt(3),t="#"+n+n+r+r+s+s+(5===t.length?t.charAt(4)+t.charAt(4):"")),9===t.length)return[(p=parseInt(t.substr(1,6),16))>>16,p>>8&Pe,p&Pe,parseInt(t.substr(7),16)/255];p=[(t=parseInt(t.substr(1),16))>>16,t>>8&Pe,t&Pe]}else if("hsl"===t.substr(0,3))if(p=c=t.match(st),e){if(~t.indexOf("="))return p=t.match(at),i&&p.length<4&&(p[3]=1),p}else a=+p[0]%360/360,o=+p[1]/100,n=2*(u=+p[2]/100)-(r=u<=.5?u*(o+1):u+o-u*o),p.length>3&&(p[3]*=1),p[0]=De(a+1/3,n,r),p[1]=De(a,n,r),p[2]=De(a-1/3,n,r);else p=t.match(st)||Ie.transparent;p=p.map(Number)}return e&&!c&&(n=p[0]/Pe,r=p[1]/Pe,s=p[2]/Pe,u=((h=Math.max(n,r,s))+(l=Math.min(n,r,s)))/2,h===l?a=o=0:(f=h-l,o=u>.5?f/(2-h-l):f/(h+l),a=h===n?(r-s)/f+(r<s?6:0):h===r?(s-n)/f+2:(n-r)/f+4,a*=60),p[0]=~~(a+.5),p[1]=~~(100*o+.5),p[2]=~~(100*u+.5)),i&&p.length<4&&(p[3]=1),p},Be=function(t){var e=[],i=[],n=-1;return t.split(ze).forEach((function(t){var r=t.match(ot)||[];e.push.apply(e,r),i.push(n+=r.length+1)})),e.c=i,e},Re=function(t,e,i){var n,r,s,a,o="",u=(t+o).match(ze),h=e?"hsla(":"rgba(",l=0;if(!u)return t;if(u=u.map((function(t){return(t=Le(t,e,1))&&h+(e?t[0]+","+t[1]+"%,"+t[2]+"%,"+t[3]:t.join(","))+")"})),i&&(s=Be(t),(n=i.c).join(o)!==s.c.join(o)))for(a=(r=t.replace(ze,"1").split(ot)).length-1;l<a;l++)o+=r[l]+(~n.indexOf(l)?u.shift()||h+"0,0,0,0)":(s.length?s:u.length?u:i).shift());if(!r)for(a=(r=t.split(ze)).length-1;l<a;l++)o+=r[l]+u[l];return o+r[a]},ze=function(){var t,e="(?:\\b(?:(?:rgb|rgba|hsl|hsla)\\(.+?\\))|\\B#(?:[0-9a-f]{3,4}){1,2}\\b";for(t in Ie)e+="|"+t+"\\b";return new RegExp(e+")","gi")}(),Fe=/hsl[a]?\(/,Ve=function(t){var e,i=t.join(" ");if(ze.lastIndex=0,ze.test(i))return e=Fe.test(i),t[1]=Re(t[1],e),t[0]=Re(t[0],e,Be(t[1])),!0},Ne=(S=Date.now,O=500,E=33,M=S(),A=M,I=P=1e3/240,L=function t(e){var i,n,r,s,a=S()-A,o=!0===e;if(a>O&&(M+=a-E),((i=(r=(A+=a)-M)-I)>0||o)&&(s=++T.frame,k=r-1e3*T.time,T.time=r/=1e3,I+=i+(i>=P?4:P-i),n=1),o||(b=x(t)),n)for(C=0;C<D.length;C++)D[C](r,k,s,e)},T={time:0,frame:0,tick:function(){L(!0)},deltaRatio:function(t){return k/(1e3/(t||60))},wake:function(){g&&(!d&&et()&&(p=d=window,m=p.document||{},ct.gsap=Ai,(p.gsapVersions||(p.gsapVersions=[])).push(Ai.version),dt(pt||p.GreenSockGlobals||!p.gsap&&p||{}),w=p.requestAnimationFrame),b&&T.sleep(),x=w||function(t){return __hf.setTimeout(t,I-1e3*T.time+1|0)},y=1,L(2))},sleep:function(){(w?p.cancelAnimationFrame:clearTimeout)(b),y=0,x=vt},lagSmoothing:function(t,e){O=t||1e8,E=Math.min(e,O,0)},fps:function(t){P=1e3/(t||240),I=1e3*T.time+P},add:function(t,e,i){var n=e?function(e,i,r,s){t(e,i,r,s),T.remove(n)}:t;return T.remove(t),D[i?"unshift":"push"](n),qe(),n},remove:function(t,e){~(e=D.indexOf(t))&&D.splice(e,1)&&C>=e&&C--},_listeners:D=[]}),qe=function(){return!y&&Ne.wake()},Xe={},Ye=/^[\d.\-M][\d.\-,\s]/,je=/["']/g,Ue=function(t){for(var e,i,n,r={},s=t.substr(1,t.length-3).split(":"),a=s[0],o=1,u=s.length;o<u;o++)i=s[o],e=o!==u-1?i.lastIndexOf(","):i.length,n=i.substr(0,e),r[a]=isNaN(n)?n.replace(je,"").trim():+n,a=i.substr(e+1).trim();return r},We=function(t){return function(e){return 1-t(1-e)}},He=function t(e,i){for(var n,r=e._first;r;)r instanceof ei?t(r,i):!r.vars.yoyoEase||r._yoyo&&r._repeat||r._yoyo===i||(r.timeline?t(r.timeline,i):(n=r._ease,r._ease=r._yEase,r._yEase=n,r._yoyo=i)),r=r._next},Qe=function(t,e){return t&&(Z(t)?t:Xe[t]||function(t){var e,i,n,r,s=(t+"").split("("),a=Xe[s[0]];return a&&s.length>1&&a.config?a.config.apply(null,~t.indexOf("{")?[Ue(s[1])]:(e=t,i=e.indexOf("(")+1,n=e.indexOf(")"),r=e.indexOf("(",i),e.substring(i,~r&&r<n?e.indexOf(")",n+1):n)).split(",").map(zt)):Xe._CE&&Ye.test(t)?Xe._CE("",t):a}(t))||e},Ge=function(t,e,i,n){void 0===i&&(i=function(t){return 1-e(1-t)}),void 0===n&&(n=function(t){return t<.5?e(2*t)/2:1-e(2*(1-t))/2});var r,s={easeIn:e,easeOut:i,easeInOut:n};return At(t,(function(t){for(var e in Xe[t]=ct[t]=s,Xe[r=t.toLowerCase()]=i,s)Xe[r+("easeIn"===e?".in":"easeOut"===e?".out":".inOut")]=Xe[t+"."+e]=s[e]})),s},Ze=function(t){return function(e){return e<.5?(1-t(1-2*e))/2:.5+t(2*(e-.5))/2}},$e=function t(e,i,n){var r=i>=1?i:1,s=(n||(e?.3:.45))/(i<1?i:1),a=s/Y*(Math.asin(1/r)||0),o=function(t){return 1===t?1:r*Math.pow(2,-10*t)*Q((t-a)*s)+1},u="out"===e?o:"in"===e?function(t){return 1-o(1-t)}:Ze(o);return s=Y/s,u.config=function(i,n){return t(e,i,n)},u},Je=function t(e,i){void 0===i&&(i=1.70158);var n=function(t){return t?--t*t*((i+1)*t+i)+1:0},r="out"===e?n:"in"===e?function(t){return 1-n(1-t)}:Ze(n);return r.config=function(i){return t(e,i)},r};At("Linear,Quad,Cubic,Quart,Quint,Strong",(function(t,e){var i=e<5?e+1:e;Ge(t+",Power"+(i-1),e?function(t){return Math.pow(t,i)}:function(t){return t},(function(t){return 1-Math.pow(1-t,i)}),(function(t){return t<.5?Math.pow(2*t,i)/2:1-Math.pow(2*(1-t),i)/2}))})),Xe.Linear.easeNone=Xe.none=Xe.Linear.easeIn,Ge("Elastic",$e("in"),$e("out"),$e()),B=7.5625,z=1/(R=2.75),Ge("Bounce",(function(t){return 1-F(1-t)}),F=function(t){return t<z?B*t*t:t<.7272727272727273?B*Math.pow(t-1.5/R,2)+.75:t<.9090909090909092?B*(t-=2.25/R)*t+.9375:B*Math.pow(t-2.625/R,2)+.984375}),Ge("Expo",(function(t){return t?Math.pow(2,10*(t-1)):0})),Ge("Circ",(function(t){return-(W(1-t*t)-1)})),Ge("Sine",(function(t){return 1===t?1:1-H(t*j)})),Ge("Back",Je("in"),Je("out"),Je()),Xe.SteppedEase=Xe.steps=ct.SteppedEase={config:function(t,e){void 0===t&&(t=1);var i=1/t,n=t+(e?0:1),r=e?1:0;return function(t){return((n*pe(0,.99999999,t)|0)+r)*i}}},N.ease=Xe["quad.out"],At("onComplete,onUpdate,onStart,onRepeat,onReverseComplete,onInterrupt",(function(t){return St+=t+","+t+"Params,"}));var Ke=function(t,e){this.id=U++,t._gsap=this,this.target=t,this.harness=e,this.get=e?e.get:Mt,this.set=e?e.getSetter:_i},ti=function(){function t(t){this.vars=t,this._delay=+t.delay||0,(this._repeat=t.repeat===1/0?-2:t.repeat||0)&&(this._rDelay=t.repeatDelay||0,this._yoyo=!!t.yoyo||!!t.yoyoEase),this._ts=1,oe(this,+t.duration,1,1),this.data=t.data,y||Ne.wake()}var e=t.prototype;return e.delay=function(t){return t||0===t?(this.parent&&this.parent.smoothChildTiming&&this.startTime(this._start+t-this._delay),this._delay=t,this):this._delay},e.duration=function(t){return arguments.length?this.totalDuration(this._repeat>0?t+(t+this._rDelay)*this._repeat:t):this.totalDuration()&&this._dur},e.totalDuration=function(t){return arguments.length?(this._dirty=0,oe(this,this._repeat<0?t:(t-this._repeat*this._rDelay)/(this._repeat+1))):this._tDur},e.totalTime=function(t,e){if(qe(),!arguments.length)return this._tTime;var i=this._dp;if(i&&i.smoothChildTiming&&this._ts){for(te(this,t),!i._dp||i.parent||ee(i,this);i&&i.parent;)i.parent._time!==i._start+(i._ts>=0?i._tTime/i._ts:(i.totalDuration()-i._tTime)/-i._ts)&&i.totalTime(i._tTime,!0),i=i.parent;!this.parent&&this._dp.autoRemoveChildren&&(this._ts>0&&t<this._tDur||this._ts<0&&t>0||!this._tDur&&!t)&&ie(this._dp,this,this._start-this._delay)}return(this._tTime!==t||!this._dur&&!e||this._initted&&Math.abs(this._zTime)===X||!t&&!this._initted&&(this.add||this._ptLookup))&&(this._ts||(this._pTime=t),Rt(this,t,e)),this},e.time=function(t,e){return arguments.length?this.totalTime(Math.min(this.totalDuration(),t+Zt(this))%(this._dur+this._rDelay)||(t?this._dur:0),e):this._time},e.totalProgress=function(t,e){return arguments.length?this.totalTime(this.totalDuration()*t,e):this.totalDuration()?Math.min(1,this._tTime/this._tDur):this.ratio},e.progress=function(t,e){return arguments.length?this.totalTime(this.duration()*(!this._yoyo||1&this.iteration()?t:1-t)+Zt(this),e):this.duration()?Math.min(1,this._time/this._dur):this.ratio},e.iteration=function(t,e){var i=this.duration()+this._rDelay;return arguments.length?this.totalTime(this._time+(t-1)*i,e):this._repeat?$t(this._tTime,i)+1:1},e.timeScale=function(t){if(!arguments.length)return-1e-8===this._rts?0:this._rts;if(this._rts===t)return this;var e=this.parent&&this._ts?Jt(this.parent._time,this):this._tTime;return this._rts=+t||0,this._ts=this._ps||-1e-8===t?0:this._rts,this.totalTime(pe(-this._delay,this._tDur,e),!0),Kt(this),Qt(this)},e.paused=function(t){return arguments.length?(this._ps!==t&&(this._ps=t,t?(this._pTime=this._tTime||Math.max(-this._delay,this.rawTime()),this._ts=this._act=0):(qe(),this._ts=this._rts,this.totalTime(this.parent&&!this.parent.smoothChildTiming?this.rawTime():this._tTime||this._pTime,1===this.progress()&&Math.abs(this._zTime)!==X&&(this._tTime-=X)))),this):this._ps},e.startTime=function(t){if(arguments.length){this._start=t;var e=this.parent||this._dp;return e&&(e._sort||!this.parent)&&ie(e,this,t-this._delay),this}return this._start},e.endTime=function(t){return this._start+(tt(t)?this.totalDuration():this.duration())/Math.abs(this._ts||1)},e.rawTime=function(t){var e=this.parent||this._dp;return e?t&&(!this._ts||this._repeat&&this._time&&this.totalProgress()<1)?this._tTime%(this._dur+this._rDelay):this._ts?Jt(e.rawTime(t),this):this._tTime:this._tTime},e.globalTime=function(t){for(var e=this,i=arguments.length?t:e.rawTime();e;)i=e._start+i/(e._ts||1),e=e._dp;return i},e.repeat=function(t){return arguments.length?(this._repeat=t===1/0?-2:t,ue(this)):-2===this._repeat?1/0:this._repeat},e.repeatDelay=function(t){if(arguments.length){var e=this._time;return this._rDelay=t,ue(this),e?this.time(e):this}return this._rDelay},e.yoyo=function(t){return arguments.length?(this._yoyo=t,this):this._yoyo},e.seek=function(t,e){return this.totalTime(le(this,t),tt(e))},e.restart=function(t,e){return this.play().totalTime(t?-this._delay:0,tt(e))},e.play=function(t,e){return null!=t&&this.seek(t,e),this.reversed(!1).paused(!1)},e.reverse=function(t,e){return null!=t&&this.seek(t||this.totalDuration(),e),this.reversed(!0).paused(!1)},e.pause=function(t,e){return null!=t&&this.seek(t,e),this.paused(!0)},e.resume=function(){return this.paused(!1)},e.reversed=function(t){return arguments.length?(!!t!==this.reversed()&&this.timeScale(-this._rts||(t?-1e-8:0)),this):this._rts<0},e.invalidate=function(){return this._initted=this._act=0,this._zTime=-1e-8,this},e.isActive=function(){var t,e=this.parent||this._dp,i=this._start;return!(e&&!(this._ts&&this._initted&&e.isActive()&&(t=e.rawTime(!0))>=i&&t<this.endTime(!0)-X))},e.eventCallback=function(t,e,i){var n=this.vars;return arguments.length>1?(e?(n[t]=e,i&&(n[t+"Params"]=i),"onUpdate"===t&&(this._onUpdate=e)):delete n[t],this):n[t]},e.then=function(t){var e=this;return new Promise((function(i){var n=Z(t)?t:Ft,r=function(){var t=e.then;e.then=null,Z(n)&&(n=n(e))&&(n.then||n===e)&&(e.then=t),i(n),e.then=t};e._initted&&1===e.totalProgress()&&e._ts>=0||!e._tTime&&e._ts<0?r():e._prom=r}))},e.kill=function(){Me(this)},t}();Vt(ti.prototype,{_time:0,_start:0,_end:0,_tTime:0,_tDur:0,_dirty:0,_repeat:0,_yoyo:!1,parent:null,_initted:!1,_rDelay:0,_ts:1,_dp:0,ratio:0,_zTime:-1e-8,_prom:0,_ps:!1,_rts:1});var ei=function(t){function e(e,i){var n;return void 0===e&&(e={}),(n=t.call(this,e)||this).labels={},n.smoothChildTiming=!!e.smoothChildTiming,n.autoRemoveChildren=!!e.autoRemoveChildren,n._sort=tt(e.sortChildren),c&&ie(e.parent||c,h(n),i),e.reversed&&n.reverse(),e.paused&&n.paused(!0),e.scrollTrigger&&ne(h(n),e.scrollTrigger),n}l(e,t);var i=e.prototype;return i.to=function(t,e,i){return fe(0,arguments,this),this},i.from=function(t,e,i){return fe(1,arguments,this),this},i.fromTo=function(t,e,i,n){return fe(2,arguments,this),this},i.set=function(t,e,i){return e.duration=0,e.parent=this,Yt(e).repeatDelay||(e.repeat=0),e.immediateRender=!!e.immediateRender,new ci(t,e,le(this,i),1),this},i.call=function(t,e,i){return ie(this,ci.delayedCall(0,t,e),i)},i.staggerTo=function(t,e,i,n,r,s,a){return i.duration=e,i.stagger=i.stagger||n,i.onComplete=s,i.onCompleteParams=a,i.parent=this,new ci(t,i,le(this,r)),this},i.staggerFrom=function(t,e,i,n,r,s,a){return i.runBackwards=1,Yt(i).immediateRender=tt(i.immediateRender),this.staggerTo(t,e,i,n,r,s,a)},i.staggerFromTo=function(t,e,i,n,r,s,a,o){return n.startAt=i,Yt(n).immediateRender=tt(n.immediateRender),this.staggerTo(t,e,n,r,s,a,o)},i.render=function(t,e,i){var n,r,s,a,o,u,h,l,f,p,d,m,g=this._time,_=this._dirty?this.totalDuration():this._tDur,v=this._dur,y=t<=0?0:It(t),b=this._zTime<0!=t<0&&(this._initted||!v);if(this!==c&&y>_&&t>=0&&(y=_),y!==this._tTime||i||b){if(g!==this._time&&v&&(y+=this._time-g,t+=this._time-g),n=y,f=this._start,u=!(l=this._ts),b&&(v||(g=this._zTime),(t||!e)&&(this._zTime=t)),this._repeat){if(d=this._yoyo,o=v+this._rDelay,this._repeat<-1&&t<0)return this.totalTime(100*o+t,e,i);if(n=It(y%o),y===_?(a=this._repeat,n=v):((a=~~(y/o))&&a===y/o&&(n=v,a--),n>v&&(n=v)),p=$t(this._tTime,o),!g&&this._tTime&&p!==a&&(p=a),d&&1&a&&(n=v-n,m=1),a!==p&&!this._lock){var x=d&&1&p,w=x===(d&&1&a);if(a<p&&(x=!x),g=x?0:v,this._lock=1,this.render(g||(m?0:It(a*o)),e,!v)._lock=0,this._tTime=y,!e&&this.parent&&Ee(this,"onRepeat"),this.vars.repeatRefresh&&!m&&(this.invalidate()._lock=1),g&&g!==this._time||u!==!this._ts||this.vars.onRepeat&&!this.parent&&!this._act)return this;if(v=this._dur,_=this._tDur,w&&(this._lock=2,g=x?v:-1e-4,this.render(g,!0),this.vars.repeatRefresh&&!m&&this.invalidate()),this._lock=0,!this._ts&&!u)return this;He(this,m)}}if(this._hasPause&&!this._forcing&&this._lock<2&&(h=function(t,e,i){var n;if(i>e)for(n=t._first;n&&n._start<=i;){if("isPause"===n.data&&n._start>e)return n;n=n._next}else for(n=t._last;n&&n._start>=i;){if("isPause"===n.data&&n._start<e)return n;n=n._prev}}(this,It(g),It(n)),h&&(y-=n-(n=h._start))),this._tTime=y,this._time=n,this._act=!l,this._initted||(this._onUpdate=this.vars.onUpdate,this._initted=1,this._zTime=t,g=0),!g&&n&&!e&&(Ee(this,"onStart"),this._tTime!==y))return this;if(n>=g&&t>=0)for(r=this._first;r;){if(s=r._next,(r._act||n>=r._start)&&r._ts&&h!==r){if(r.parent!==this)return this.render(t,e,i);if(r.render(r._ts>0?(n-r._start)*r._ts:(r._dirty?r.totalDuration():r._tDur)+(n-r._start)*r._ts,e,i),n!==this._time||!this._ts&&!u){h=0,s&&(y+=this._zTime=-1e-8);break}}r=s}else{r=this._last;for(var T=t<0?t:n;r;){if(s=r._prev,(r._act||T<=r._end)&&r._ts&&h!==r){if(r.parent!==this)return this.render(t,e,i);if(r.render(r._ts>0?(T-r._start)*r._ts:(r._dirty?r.totalDuration():r._tDur)+(T-r._start)*r._ts,e,i),n!==this._time||!this._ts&&!u){h=0,s&&(y+=this._zTime=T?-1e-8:X);break}}r=s}}if(h&&!e&&(this.pause(),h.render(n>=g?0:-1e-8)._zTime=n>=g?1:-1,this._ts))return this._start=f,Kt(this),this.render(t,e,i);this._onUpdate&&!e&&Ee(this,"onUpdate",!0),(y===_&&this._tTime>=this.totalDuration()||!y&&g)&&(f!==this._start&&Math.abs(l)===Math.abs(this._ts)||this._lock||((t||!v)&&(y===_&&this._ts>0||!y&&this._ts<0)&&Wt(this,1),e||t<0&&!g||!y&&!g&&_||(Ee(this,y===_&&t>=0?"onComplete":"onReverseComplete",!0),this._prom&&!(y<_&&this.timeScale()>0)&&this._prom())))}return this},i.add=function(t,e){var i=this;if($(e)||(e=le(this,e,t)),!(t instanceof ti)){if(rt(t))return t.forEach((function(t){return i.add(t,e)})),this;if(G(t))return this.addLabel(t,e);if(!Z(t))return this;t=ci.delayedCall(0,t)}return this!==t?ie(this,t,e):this},i.getChildren=function(t,e,i,n){void 0===t&&(t=!0),void 0===e&&(e=!0),void 0===i&&(i=!0),void 0===n&&(n=-1e8);for(var r=[],s=this._first;s;)s._start>=n&&(s instanceof ci?e&&r.push(s):(i&&r.push(s),t&&r.push.apply(r,s.getChildren(!0,e,i)))),s=s._next;return r},i.getById=function(t){for(var e=this.getChildren(1,1,1),i=e.length;i--;)if(e[i].vars.id===t)return e[i]},i.remove=function(t){return G(t)?this.removeLabel(t):Z(t)?this.killTweensOf(t):(Ut(this,t),t===this._recent&&(this._recent=this._last),Ht(this))},i.totalTime=function(e,i){return arguments.length?(this._forcing=1,!this._dp&&this._ts&&(this._start=It(Ne.time-(this._ts>0?e/this._ts:(this.totalDuration()-e)/-this._ts))),t.prototype.totalTime.call(this,e,i),this._forcing=0,this):this._tTime},i.addLabel=function(t,e){return this.labels[t]=le(this,e),this},i.removeLabel=function(t){return delete this.labels[t],this},i.addPause=function(t,e,i){var n=ci.delayedCall(0,e||vt,i);return n.data="isPause",this._hasPause=1,ie(this,n,le(this,t))},i.removePause=function(t){var e=this._first;for(t=le(this,t);e;)e._start===t&&"isPause"===e.data&&Wt(e),e=e._next},i.killTweensOf=function(t,e,i){for(var n=this.getTweensOf(t,i),r=n.length;r--;)ii!==n[r]&&n[r].kill(t,e);return this},i.getTweensOf=function(t,e){for(var i,n=[],r=ve(t),s=this._first,a=$(e);s;)s instanceof ci?Lt(s._targets,r)&&(a?(!ii||s._initted&&s._ts)&&s.globalTime(0)<=e&&s.globalTime(s.totalDuration())>e:!e||s.isActive())&&n.push(s):(i=s.getTweensOf(r,e)).length&&n.push.apply(n,i),s=s._next;return n},i.tweenTo=function(t,e){e=e||{};var i,n=this,r=le(n,t),s=e,a=s.startAt,o=s.onStart,u=s.onStartParams,h=s.immediateRender,l=ci.to(n,Vt({ease:e.ease||"none",lazy:!1,immediateRender:!1,time:r,overwrite:"auto",duration:e.duration||Math.abs((r-(a&&"time"in a?a.time:n._time))/n.timeScale())||X,onStart:function(){if(n.pause(),!i){var t=e.duration||Math.abs((r-(a&&"time"in a?a.time:n._time))/n.timeScale());l._dur!==t&&oe(l,t,0,1).render(l._time,!0,!0),i=1}o&&o.apply(l,u||[])}},e));return h?l.render(0):l},i.tweenFromTo=function(t,e,i){return this.tweenTo(e,Vt({startAt:{time:le(this,t)}},i))},i.recent=function(){return this._recent},i.nextLabel=function(t){return void 0===t&&(t=this._time),Oe(this,le(this,t))},i.previousLabel=function(t){return void 0===t&&(t=this._time),Oe(this,le(this,t),1)},i.currentLabel=function(t){return arguments.length?this.seek(t,!0):this.previousLabel(this._time+X)},i.shiftChildren=function(t,e,i){void 0===i&&(i=0);for(var n,r=this._first,s=this.labels;r;)r._start>=i&&(r._start+=t,r._end+=t),r=r._next;if(e)for(n in s)s[n]>=i&&(s[n]+=t);return Ht(this)},i.invalidate=function(){var e=this._first;for(this._lock=0;e;)e.invalidate(),e=e._next;return t.prototype.invalidate.call(this)},i.clear=function(t){void 0===t&&(t=!0);for(var e,i=this._first;i;)e=i._next,this.remove(i),i=e;return this._dp&&(this._time=this._tTime=this._pTime=0),t&&(this.labels={}),Ht(this)},i.totalDuration=function(t){var e,i,n,r=0,s=this,a=s._last,o=q;if(arguments.length)return s.timeScale((s._repeat<0?s.duration():s.totalDuration())/(s.reversed()?-t:t));if(s._dirty){for(n=s.parent;a;)e=a._prev,a._dirty&&a.totalDuration(),(i=a._start)>o&&s._sort&&a._ts&&!s._lock?(s._lock=1,ie(s,a,i-a._delay,1)._lock=0):o=i,i<0&&a._ts&&(r-=i,(!n&&!s._dp||n&&n.smoothChildTiming)&&(s._start+=i/s._ts,s._time-=i,s._tTime-=i),s.shiftChildren(-i,!1,-1/0),o=0),a._end>r&&a._ts&&(r=a._end),a=e;oe(s,s===c&&s._time>r?s._time:r,1,1),s._dirty=0}return s._tDur},e.updateRoot=function(t){if(c._ts&&(Rt(c,Jt(t,c)),_=Ne.frame),Ne.frame>=kt){kt+=V.autoSleep||120;var e=c._first;if((!e||!e._ts)&&V.autoSleep&&Ne._listeners.length<2){for(;e&&!e._ts;)e=e._next;e||Ne.sleep()}}},e}(ti);Vt(ei.prototype,{_lock:0,_hasPause:0,_forcing:0});var ii,ni,ri=function(t,e,i,n,r,s,a){var o,u,h,l,f,c,p,d,m=new Si(this._pt,t,e,0,1,bi,null,r),g=0,_=0;for(m.b=i,m.e=n,i+="",(p=~(n+="").indexOf("random("))&&(n=Ce(n)),s&&(s(d=[i,n],t,e),i=d[0],n=d[1]),u=i.match(ut)||[];o=ut.exec(n);)l=o[0],f=n.substring(g,o.index),h?h=(h+1)%5:"rgba("===f.substr(-5)&&(h=1),l!==u[_++]&&(c=parseFloat(u[_-1])||0,m._pt={_next:m._pt,p:f||1===_?f:",",s:c,c:"="===l.charAt(1)?Dt(c,l)-c:parseFloat(l)-c,m:h&&h<4?Math.round:0},g=ut.lastIndex);return m.c=g<n.length?n.substring(g,n.length):"",m.fp=a,(ht.test(n)||p)&&(m.e=0),this._pt=m,m},si=function(t,e,i,n,r,s,a,o,u){Z(n)&&(n=n(r||0,t,s));var h,l=t[e],f="get"!==i?i:Z(l)?u?t[e.indexOf("set")||!Z(t["get"+e.substr(3)])?e:"get"+e.substr(3)](u):t[e]():l,c=Z(l)?u?mi:di:pi;if(G(n)&&(~n.indexOf("random(")&&(n=Ce(n)),"="===n.charAt(1)&&((h=Dt(f,n)+(de(f)||0))||0===h)&&(n=h)),f!==n||ni)return isNaN(f*n)||""===n?(!l&&!(e in t)&&mt(e,n),ri.call(this,t,e,f,n,c,o||V.stringFilter,u)):(h=new Si(this._pt,t,e,+f||0,n-(f||0),"boolean"==typeof l?yi:vi,0,c),u&&(h.fp=u),a&&h.modifier(a,this,t),this._pt=h)},ai=function(t,e,i,n,r,s){var a,o,u,h;if(wt[t]&&!1!==(a=new wt[t]).init(r,a.rawVars?e[t]:function(t,e,i,n,r){if(Z(t)&&(t=hi(t,r,e,i,n)),!K(t)||t.style&&t.nodeType||rt(t)||nt(t))return G(t)?hi(t,r,e,i,n):t;var s,a={};for(s in t)a[s]=hi(t[s],r,e,i,n);return a}(e[t],n,r,s,i),i,n,s)&&(i._pt=o=new Si(i._pt,r,t,0,1,a.render,a,0,a.priority),i!==v))for(u=i._ptLookup[i._targets.indexOf(r)],h=a._props.length;h--;)u[a._props[h]]=o;return a},oi=function t(e,i){var n,r,s,a,o,u,h,l,p,d,m,g,_,v=e.vars,y=v.ease,b=v.startAt,x=v.immediateRender,w=v.lazy,T=v.onUpdate,k=v.onUpdateParams,C=v.callbackScope,S=v.runBackwards,O=v.yoyoEase,E=v.keyframes,M=v.autoRevert,A=e._dur,P=e._startAt,I=e._targets,D=e.parent,L=D&&"nested"===D.data?D.parent._targets:I,B="auto"===e._overwrite&&!f,R=e.timeline;if(R&&(!E||!y)&&(y="none"),e._ease=Qe(y,N.ease),e._yEase=O?We(Qe(!0===O?y:O,N.ease)):0,O&&e._yoyo&&!e._repeat&&(O=e._yEase,e._yEase=e._ease,e._ease=O),e._from=!R&&!!v.runBackwards,!R||E&&!v.stagger){if(g=(l=I[0]?Et(I[0]).harness:0)&&v[l.prop],n=Xt(v,yt),P&&(Wt(P.render(-1,!0)),P._lazy=0),b)if(Wt(e._startAt=ci.set(I,Vt({data:"isStart",overwrite:!1,parent:D,immediateRender:!0,lazy:tt(w),startAt:null,delay:0,onUpdate:T,onUpdateParams:k,callbackScope:C,stagger:0},b))),i<0&&!x&&!M&&e._startAt.render(-1,!0),x){if(i>0&&!M&&(e._startAt=0),A&&i<=0)return void(i&&(e._zTime=i))}else!1===M&&(e._startAt=0);else if(S&&A)if(P)!M&&(e._startAt=0);else if(i&&(x=!1),s=Vt({overwrite:!1,data:"isFromStart",lazy:x&&tt(w),immediateRender:x,stagger:0,parent:D},n),g&&(s[l.prop]=g),Wt(e._startAt=ci.set(I,s)),i<0&&e._startAt.render(-1,!0),e._zTime=i,x){if(!i)return}else t(e._startAt,X);for(e._pt=e._ptCache=0,w=A&&tt(w)||w&&!A,r=0;r<I.length;r++){if(h=(o=I[r])._gsap||Ot(I)[r]._gsap,e._ptLookup[r]=d={},xt[h.id]&&bt.length&&Bt(),m=L===I?r:L.indexOf(o),l&&!1!==(p=new l).init(o,g||n,e,m,L)&&(e._pt=a=new Si(e._pt,o,p.name,0,1,p.render,p,0,p.priority),p._props.forEach((function(t){d[t]=a})),p.priority&&(u=1)),!l||g)for(s in n)wt[s]&&(p=ai(s,n,e,m,o,L))?p.priority&&(u=1):d[s]=a=si.call(e,o,s,"get",n[s],m,L,0,v.stringFilter);e._op&&e._op[r]&&e.kill(o,e._op[r]),B&&e._pt&&(ii=e,c.killTweensOf(o,d,e.globalTime(i)),_=!e.parent,ii=0),e._pt&&w&&(xt[h.id]=1)}u&&Ci(e),e._onInit&&e._onInit(e)}e._onUpdate=T,e._initted=(!e._op||e._pt)&&!_,E&&i<=0&&R.render(q,!0,!0)},ui=function(t,e,i,n){var r,s,a=e.ease||n||"power1.inOut";if(rt(e))s=i[t]||(i[t]=[]),e.forEach((function(t,i){return s.push({t:i/(e.length-1)*100,v:t,e:a})}));else for(r in e)s=i[r]||(i[r]=[]),"ease"===r||s.push({t:parseFloat(t),v:e[r],e:a})},hi=function(t,e,i,n,r){return Z(t)?t.call(e,i,n,r):G(t)&&~t.indexOf("random(")?Ce(t):t},li=St+"repeat,repeatDelay,yoyo,repeatRefresh,yoyoEase,autoRevert",fi={};At(li+",id,stagger,delay,duration,paused,scrollTrigger",(function(t){return fi[t]=1}));var ci=function(t){function e(e,i,n,r){var s;"number"==typeof i&&(n.duration=i,i=n,n=null);var a,o,u,l,p,d,m,g,_=(s=t.call(this,r?i:Yt(i))||this).vars,v=_.duration,y=_.delay,b=_.immediateRender,x=_.stagger,w=_.overwrite,T=_.keyframes,k=_.defaults,C=_.scrollTrigger,S=_.yoyoEase,O=i.parent||c,E=(rt(e)||nt(e)?$(e[0]):"length"in i)?[e]:ve(e);if(s._targets=E.length?Ot(E):gt("GSAP target "+e+" not found. https://greensock.com",!V.nullTargetWarn)||[],s._ptLookup=[],s._overwrite=w,T||x||it(v)||it(y)){if(i=s.vars,(a=s.timeline=new ei({data:"nested",defaults:k||{}})).kill(),a.parent=a._dp=h(s),a._start=0,x||it(v)||it(y)){if(l=E.length,m=x&&be(x),K(x))for(p in x)~li.indexOf(p)&&(g||(g={}),g[p]=x[p]);for(o=0;o<l;o++)(u=Xt(i,fi)).stagger=0,S&&(u.yoyoEase=S),g&&Nt(u,g),d=E[o],u.duration=+hi(v,h(s),o,d,E),u.delay=(+hi(y,h(s),o,d,E)||0)-s._delay,!x&&1===l&&u.delay&&(s._delay=y=u.delay,s._start+=y,u.delay=0),a.to(d,u,m?m(o,d,E):0),a._ease=Xe.none;a.duration()?v=y=0:s.timeline=0}else if(T){Yt(Vt(a.vars.defaults,{ease:"none"})),a._ease=Qe(T.ease||i.ease||"none");var M,A,P,I=0;if(rt(T))T.forEach((function(t){return a.to(E,t,">")}));else{for(p in u={},T)"ease"===p||"easeEach"===p||ui(p,T[p],u,T.easeEach);for(p in u)for(M=u[p].sort((function(t,e){return t.t-e.t})),I=0,o=0;o<M.length;o++)(P={ease:(A=M[o]).e,duration:(A.t-(o?M[o-1].t:0))/100*v})[p]=A.v,a.to(E,P,I),I+=P.duration;a.duration()<v&&a.to({},{duration:v-a.duration()})}}v||s.duration(v=a.duration())}else s.timeline=0;return!0!==w||f||(ii=h(s),c.killTweensOf(E),ii=0),ie(O,h(s),n),i.reversed&&s.reverse(),i.paused&&s.paused(!0),(b||!v&&!T&&s._start===It(O._time)&&tt(b)&&Gt(h(s))&&"nested"!==O.data)&&(s._tTime=-1e-8,s.render(Math.max(0,-y))),C&&ne(h(s),C),s}l(e,t);var i=e.prototype;return i.render=function(t,e,i){var n,r,s,a,o,u,h,l,f,c=this._time,p=this._tDur,d=this._dur,m=t>p-X&&t>=0?p:t<X?0:t;if(d){if(m!==this._tTime||!t||i||!this._initted&&this._tTime||this._startAt&&this._zTime<0!=t<0){if(n=m,l=this.timeline,this._repeat){if(a=d+this._rDelay,this._repeat<-1&&t<0)return this.totalTime(100*a+t,e,i);if(n=It(m%a),m===p?(s=this._repeat,n=d):((s=~~(m/a))&&s===m/a&&(n=d,s--),n>d&&(n=d)),(u=this._yoyo&&1&s)&&(f=this._yEase,n=d-n),o=$t(this._tTime,a),n===c&&!i&&this._initted)return this._tTime=m,this;s!==o&&(l&&this._yEase&&He(l,u),!this.vars.repeatRefresh||u||this._lock||(this._lock=i=1,this.render(It(a*s),!0).invalidate()._lock=0))}if(!this._initted){if(re(this,t<0?t:n,i,e))return this._tTime=0,this;if(c!==this._time)return this;if(d!==this._dur)return this.render(t,e,i)}if(this._tTime=m,this._time=n,!this._act&&this._ts&&(this._act=1,this._lazy=0),this.ratio=h=(f||this._ease)(n/d),this._from&&(this.ratio=h=1-h),n&&!c&&!e&&(Ee(this,"onStart"),this._tTime!==m))return this;for(r=this._pt;r;)r.r(h,r.d),r=r._next;l&&l.render(t<0?t:!n&&u?-1e-8:l._dur*l._ease(n/this._dur),e,i)||this._startAt&&(this._zTime=t),this._onUpdate&&!e&&(t<0&&this._startAt&&this._startAt.render(t,!0,i),Ee(this,"onUpdate")),this._repeat&&s!==o&&this.vars.onRepeat&&!e&&this.parent&&Ee(this,"onRepeat"),m!==this._tDur&&m||this._tTime!==m||(t<0&&this._startAt&&!this._onUpdate&&this._startAt.render(t,!0,!0),(t||!d)&&(m===this._tDur&&this._ts>0||!m&&this._ts<0)&&Wt(this,1),e||t<0&&!c||!m&&!c||(Ee(this,m===p?"onComplete":"onReverseComplete",!0),this._prom&&!(m<p&&this.timeScale()>0)&&this._prom()))}}else!function(t,e,i,n){var r,s,a,o=t.ratio,u=e<0||!e&&(!t._start&&se(t)&&(t._initted||!ae(t))||(t._ts<0||t._dp._ts<0)&&!ae(t))?0:1,h=t._rDelay,l=0;if(h&&t._repeat&&(l=pe(0,t._tDur,e),s=$t(l,h),t._yoyo&&1&s&&(u=1-u),s!==$t(t._tTime,h)&&(o=1-u,t.vars.repeatRefresh&&t._initted&&t.invalidate())),u!==o||n||t._zTime===X||!e&&t._zTime){if(!t._initted&&re(t,e,n,i))return;for(a=t._zTime,t._zTime=e||(i?X:0),i||(i=e&&!a),t.ratio=u,t._from&&(u=1-u),t._time=0,t._tTime=l,r=t._pt;r;)r.r(u,r.d),r=r._next;t._startAt&&e<0&&t._startAt.render(e,!0,!0),t._onUpdate&&!i&&Ee(t,"onUpdate"),l&&t._repeat&&!i&&t.parent&&Ee(t,"onRepeat"),(e>=t._tDur||e<0)&&t.ratio===u&&(u&&Wt(t,1),i||(Ee(t,u?"onComplete":"onReverseComplete",!0),t._prom&&t._prom()))}else t._zTime||(t._zTime=e)}(this,t,e,i);return this},i.targets=function(){return this._targets},i.invalidate=function(){return this._pt=this._op=this._startAt=this._onUpdate=this._lazy=this.ratio=0,this._ptLookup=[],this.timeline&&this.timeline.invalidate(),t.prototype.invalidate.call(this)},i.resetTo=function(t,e,i,n){y||Ne.wake(),this._ts||this.play();var r=Math.min(this._dur,(this._dp._time-this._start)*this._ts);return this._initted||oi(this,r),function(t,e,i,n,r,s,a){var o,u,h,l=(t._pt&&t._ptCache||(t._ptCache={}))[e];if(!l)for(l=t._ptCache[e]=[],u=t._ptLookup,h=t._targets.length;h--;){if((o=u[h][e])&&o.d&&o.d._pt)for(o=o.d._pt;o&&o.p!==e;)o=o._next;if(!o)return ni=1,t.vars[e]="+=0",oi(t,a),ni=0,1;l.push(o)}for(h=l.length;h--;)(o=l[h]).s=!n&&0!==n||r?o.s+(n||0)+s*o.c:n,o.c=i-o.s,o.e&&(o.e=Pt(i)+de(o.e)),o.b&&(o.b=o.s+de(o.b))}(this,t,e,i,n,this._ease(r/this._dur),r)?this.resetTo(t,e,i,n):(te(this,0),this.parent||jt(this._dp,this,"_first","_last",this._dp._sort?"_start":0),this.render(0))},i.kill=function(t,e){if(void 0===e&&(e="all"),!(t||e&&"all"!==e))return this._lazy=this._pt=0,this.parent?Me(this):this;if(this.timeline){var i=this.timeline.totalDuration();return this.timeline.killTweensOf(t,e,ii&&!0!==ii.vars.overwrite)._first||Me(this),this.parent&&i!==this.timeline.totalDuration()&&oe(this,this._dur*this.timeline._tDur/i,0,1),this}var n,r,s,a,o,u,h,l=this._targets,f=t?ve(t):l,c=this._ptLookup,p=this._pt;if((!e||"all"===e)&&function(t,e){for(var i=t.length,n=i===e.length;n&&i--&&t[i]===e[i];);return i<0}(l,f))return"all"===e&&(this._pt=0),Me(this);for(n=this._op=this._op||[],"all"!==e&&(G(e)&&(o={},At(e,(function(t){return o[t]=1})),e=o),e=function(t,e){var i,n,r,s,a=t[0]?Et(t[0]).harness:0,o=a&&a.aliases;if(!o)return e;for(n in i=Nt({},e),o)if(n in i)for(r=(s=o[n].split(",")).length;r--;)i[s[r]]=i[n];return i}(l,e)),h=l.length;h--;)if(~f.indexOf(l[h]))for(o in r=c[h],"all"===e?(n[h]=e,a=r,s={}):(s=n[h]=n[h]||{},a=e),a)(u=r&&r[o])&&("kill"in u.d&&!0!==u.d.kill(o)||Ut(this,u,"_pt"),delete r[o]),"all"!==s&&(s[o]=1);return this._initted&&!this._pt&&p&&Me(this),this},e.to=function(t,i){return new e(t,i,arguments[2])},e.from=function(t,e){return fe(1,arguments)},e.delayedCall=function(t,i,n,r){return new e(i,0,{immediateRender:!1,lazy:!1,overwrite:!1,delay:t,onComplete:i,onReverseComplete:i,onCompleteParams:n,onReverseCompleteParams:n,callbackScope:r})},e.fromTo=function(t,e,i){return fe(2,arguments)},e.set=function(t,i){return i.duration=0,i.repeatDelay||(i.repeat=0),new e(t,i)},e.killTweensOf=function(t,e,i){return c.killTweensOf(t,e,i)},e}(ti);Vt(ci.prototype,{_targets:[],_lazy:0,_startAt:0,_op:0,_onInit:0}),At("staggerTo,staggerFrom,staggerFromTo",(function(t){ci[t]=function(){var e=new ei,i=me.call(arguments,0);return i.splice("staggerFromTo"===t?5:4,0,0),e[t].apply(e,i)}}));var pi=function(t,e,i){return t[e]=i},di=function(t,e,i){return t[e](i)},mi=function(t,e,i,n){return t[e](n.fp,i)},gi=function(t,e,i){return t.setAttribute(e,i)},_i=function(t,e){return Z(t[e])?di:J(t[e])&&t.setAttribute?gi:pi},vi=function(t,e){return e.set(e.t,e.p,Math.round(1e6*(e.s+e.c*t))/1e6,e)},yi=function(t,e){return e.set(e.t,e.p,!!(e.s+e.c*t),e)},bi=function(t,e){var i=e._pt,n="";if(!t&&e.b)n=e.b;else if(1===t&&e.e)n=e.e;else{for(;i;)n=i.p+(i.m?i.m(i.s+i.c*t):Math.round(1e4*(i.s+i.c*t))/1e4)+n,i=i._next;n+=e.c}e.set(e.t,e.p,n,e)},xi=function(t,e){for(var i=e._pt;i;)i.r(t,i.d),i=i._next},wi=function(t,e,i,n){for(var r,s=this._pt;s;)r=s._next,s.p===n&&s.modifier(t,e,i),s=r},Ti=function(t){for(var e,i,n=this._pt;n;)i=n._next,n.p===t&&!n.op||n.op===t?Ut(this,n,"_pt"):n.dep||(e=1),n=i;return!e},ki=function(t,e,i,n){n.mSet(t,e,n.m.call(n.tween,i,n.mt),n)},Ci=function(t){for(var e,i,n,r,s=t._pt;s;){for(e=s._next,i=n;i&&i.pr>s.pr;)i=i._next;(s._prev=i?i._prev:r)?s._prev._next=s:n=s,(s._next=i)?i._prev=s:r=s,s=e}t._pt=n},Si=function(){function t(t,e,i,n,r,s,a,o,u){this.t=e,this.s=n,this.c=r,this.p=i,this.r=s||vi,this.d=a||this,this.set=o||pi,this.pr=u||0,this._next=t,t&&(t._prev=this)}return t.prototype.modifier=function(t,e,i){this.mSet=this.mSet||this.set,this.set=ki,this.m=t,this.mt=i,this.tween=e},t}();At(St+"parent,duration,ease,delay,overwrite,runBackwards,startAt,yoyo,immediateRender,repeat,repeatDelay,data,paused,reversed,lazy,callbackScope,stringFilter,id,yoyoEase,stagger,inherit,repeatRefresh,keyframes,autoRevert,scrollTrigger",(function(t){return yt[t]=1})),ct.TweenMax=ct.TweenLite=ci,ct.TimelineLite=ct.TimelineMax=ei,c=new ei({sortChildren:!1,defaults:N,autoRemoveChildren:!0,id:"root",smoothChildTiming:!0}),V.stringFilter=Ve;var Oi={registerPlugin:function(){for(var t=arguments.length,e=new Array(t),i=0;i<t;i++)e[i]=arguments[i];e.forEach((function(t){return Ae(t)}))},timeline:function(t){return new ei(t)},getTweensOf:function(t,e){return c.getTweensOf(t,e)},getProperty:function(t,e,i,n){G(t)&&(t=ve(t)[0]);var r=Et(t||{}).get,s=i?Ft:zt;return"native"===i&&(i=""),t?e?s((wt[e]&&wt[e].get||r)(t,e,i,n)):function(e,i,n){return s((wt[e]&&wt[e].get||r)(t,e,i,n))}:t},quickSetter:function(t,e,i){if((t=ve(t)).length>1){var n=t.map((function(t){return Ai.quickSetter(t,e,i)})),r=n.length;return function(t){for(var e=r;e--;)n[e](t)}}t=t[0]||{};var s=wt[e],a=Et(t),o=a.harness&&(a.harness.aliases||{})[e]||e,u=s?function(e){var n=new s;v._pt=0,n.init(t,i?e+i:e,v,0,[t]),n.render(1,n),v._pt&&xi(1,v)}:a.set(t,o);return s?u:function(e){return u(t,o,i?e+i:e,a,1)}},quickTo:function(t,e,i){var n,r=Ai.to(t,Nt(((n={})[e]="+=0.1",n.paused=!0,n),i||{})),s=function(t,i,n){return r.resetTo(e,t,i,n)};return s.tween=r,s},isTweening:function(t){return c.getTweensOf(t,!0).length>0},defaults:function(t){return t&&t.ease&&(t.ease=Qe(t.ease,N.ease)),qt(N,t||{})},config:function(t){return qt(V,t||{})},registerEffect:function(t){var e=t.name,i=t.effect,n=t.plugins,r=t.defaults,s=t.extendTimeline;(n||"").split(",").forEach((function(t){return t&&!wt[t]&&!ct[t]&&gt(e+" effect requires "+t+" plugin.")})),Tt[e]=function(t,e,n){return i(ve(t),Vt(e||{},r),n)},s&&(ei.prototype[e]=function(t,i,n){return this.add(Tt[e](t,K(i)?i:(n=i)&&{},this),n)})},registerEase:function(t,e){Xe[t]=Qe(e)},parseEase:function(t,e){return arguments.length?Qe(t,e):Xe},getById:function(t){return c.getById(t)},exportRoot:function(t,e){void 0===t&&(t={});var i,n,r=new ei(t);for(r.smoothChildTiming=tt(t.smoothChildTiming),c.remove(r),r._dp=0,r._time=r._tTime=c._time,i=c._first;i;)n=i._next,!e&&!i._dur&&i instanceof ci&&i.vars.onComplete===i._targets[0]||ie(r,i,i._start-i._delay),i=n;return ie(c,r,0),r},utils:{wrap:function t(e,i,n){var r=i-e;return rt(e)?ke(e,t(0,e.length),i):ce(n,(function(t){return(r+(t-e)%r)%r+e}))},wrapYoyo:function t(e,i,n){var r=i-e,s=2*r;return rt(e)?ke(e,t(0,e.length-1),i):ce(n,(function(t){return e+((t=(s+(t-e)%s)%s||0)>r?s-t:t)}))},distribute:be,random:Te,snap:we,normalize:function(t,e,i){return Se(t,e,0,1,i)},getUnit:de,clamp:function(t,e,i){return ce(i,(function(i){return pe(t,e,i)}))},splitColor:Le,toArray:ve,selector:function(t){return t=ve(t)[0]||gt("Invalid scope")||{},function(e){var i=t.current||t.nativeElement||t;return ve(e,i.querySelectorAll?i:i===t?gt("Invalid scope")||m.createElement("div"):t)}},mapRange:Se,pipe:function(){for(var t=arguments.length,e=new Array(t),i=0;i<t;i++)e[i]=arguments[i];return function(t){return e.reduce((function(t,e){return e(t)}),t)}},unitize:function(t,e){return function(i){return t(parseFloat(i))+(e||de(i))}},interpolate:function t(e,i,n,r){var s=isNaN(e+i)?0:function(t){return(1-t)*e+t*i};if(!s){var a,o,u,h,l,f=G(e),c={};if(!0===n&&(r=1)&&(n=null),f)e={p:e},i={p:i};else if(rt(e)&&!rt(i)){for(u=[],h=e.length,l=h-2,o=1;o<h;o++)u.push(t(e[o-1],e[o]));h--,s=function(t){t*=h;var e=Math.min(l,~~t);return u[e](t-e)},n=i}else r||(e=Nt(rt(e)?[]:{},e));if(!u){for(a in i)si.call(c,e,a,"get",i[a]);s=function(t){return xi(t,c)||(f?e.p:e)}}}return ce(n,s)},shuffle:ye},install:dt,effects:Tt,ticker:Ne,updateRoot:ei.updateRoot,plugins:wt,globalTimeline:c,core:{PropTween:Si,globals:_t,Tween:ci,Timeline:ei,Animation:ti,getCache:Et,_removeLinkedListItem:Ut,suppressOverwrites:function(t){return f=t}}};At("to,from,fromTo,delayedCall,set,killTweensOf",(function(t){return Oi[t]=ci[t]})),Ne.add(ei.updateRoot),v=Oi.to({},{duration:0});var Ei=function(t,e){for(var i=t._pt;i&&i.p!==e&&i.op!==e&&i.fp!==e;)i=i._next;return i},Mi=function(t,e){return{name:t,rawVars:1,init:function(t,i,n){n._onInit=function(t){var n,r;if(G(i)&&(n={},At(i,(function(t){return n[t]=1})),i=n),e){for(r in n={},i)n[r]=e(i[r]);i=n}!function(t,e){var i,n,r,s=t._targets;for(i in e)for(n=s.length;n--;)(r=t._ptLookup[n][i])&&(r=r.d)&&(r._pt&&(r=Ei(r,i)),r&&r.modifier&&r.modifier(e[i],t,s[n],i))}(t,i)}}}},Ai=Oi.registerPlugin({name:"attr",init:function(t,e,i,n,r){var s,a;for(s in e)(a=this.add(t,"setAttribute",(t.getAttribute(s)||0)+"",e[s],n,r,0,0,s))&&(a.op=s),this._props.push(s)}},{name:"endArray",init:function(t,e){for(var i=e.length;i--;)this.add(t,i,t[i]||0,e[i])}},Mi("roundProps",xe),Mi("modifiers"),Mi("snap",we))||Oi;ci.version=ei.version=Ai.version="3.10.4",g=1,et()&&qe();Xe.Power0,Xe.Power1,Xe.Power2,Xe.Power3,Xe.Power4,Xe.Linear,Xe.Quad,Xe.Cubic,Xe.Quart,Xe.Quint,Xe.Strong,Xe.Elastic,Xe.Back,Xe.SteppedEase,Xe.Bounce,Xe.Sine,Xe.Expo,Xe.Circ;var Pi,Ii,Di,Li,Bi,Ri,zi,Fi={},Vi=180/Math.PI,Ni=Math.PI/180,qi=Math.atan2,Xi=/([A-Z])/g,Yi=/(left|right|width|margin|padding|x)/i,ji=/[\s,\(]\S/,Ui={autoAlpha:"opacity,visibility",scale:"scaleX,scaleY",alpha:"opacity"},Wi=function(t,e){return e.set(e.t,e.p,Math.round(1e4*(e.s+e.c*t))/1e4+e.u,e)},Hi=function(t,e){return e.set(e.t,e.p,1===t?e.e:Math.round(1e4*(e.s+e.c*t))/1e4+e.u,e)},Qi=function(t,e){return e.set(e.t,e.p,t?Math.round(1e4*(e.s+e.c*t))/1e4+e.u:e.b,e)},Gi=function(t,e){var i=e.s+e.c*t;e.set(e.t,e.p,~~(i+(i<0?-.5:.5))+e.u,e)},Zi=function(t,e){return e.set(e.t,e.p,t?e.e:e.b,e)},$i=function(t,e){return e.set(e.t,e.p,1!==t?e.b:e.e,e)},Ji=function(t,e,i){return t.style[e]=i},Ki=function(t,e,i){return t.style.setProperty(e,i)},tn=function(t,e,i){return t._gsap[e]=i},en=function(t,e,i){return t._gsap.scaleX=t._gsap.scaleY=i},nn=function(t,e,i,n,r){var s=t._gsap;s.scaleX=s.scaleY=i,s.renderTransform(r,s)},rn=function(t,e,i,n,r){var s=t._gsap;s[e]=i,s.renderTransform(r,s)},sn="transform",an=sn+"Origin",on=function(t,e){var i=Ii.createElementNS?Ii.createElementNS((e||"http://www.w3.org/1999/xhtml").replace(/^https/,"http"),t):Ii.createElement(t);return i.style?i:Ii.createElement(t)},un=function t(e,i,n){var r=getComputedStyle(e);return r[i]||r.getPropertyValue(i.replace(Xi,"-$1").toLowerCase())||r.getPropertyValue(i)||!n&&t(e,ln(i)||i,1)||""},hn="O,Moz,ms,Ms,Webkit".split(","),ln=function(t,e,i){var n=(e||Bi).style,r=5;if(t in n&&!i)return t;for(t=t.charAt(0).toUpperCase()+t.substr(1);r--&&!(hn[r]+t in n););return r<0?null:(3===r?"ms":r>=0?hn[r]:"")+t},fn=function(){"undefined"!=typeof window&&window.document&&(Pi=window,Ii=Pi.document,Di=Ii.documentElement,Bi=on("div")||{style:{}},on("div"),sn=ln(sn),an=sn+"Origin",Bi.style.cssText="border-width:0;line-height:0;position:absolute;padding:0",zi=!!ln("perspective"),Li=1)},cn=function t(e){var i,n=on("svg",this.ownerSVGElement&&this.ownerSVGElement.getAttribute("xmlns")||"http://www.w3.org/2000/svg"),r=this.parentNode,s=this.nextSibling,a=this.style.cssText;if(Di.appendChild(n),n.appendChild(this),this.style.display="block",e)try{i=this.getBBox(),this._gsapBBox=this.getBBox,this.getBBox=t}catch(t){}else this._gsapBBox&&(i=this._gsapBBox());return r&&(s?r.insertBefore(this,s):r.appendChild(this)),Di.removeChild(n),this.style.cssText=a,i},pn=function(t,e){for(var i=e.length;i--;)if(t.hasAttribute(e[i]))return t.getAttribute(e[i])},dn=function(t){var e;try{e=t.getBBox()}catch(i){e=cn.call(t,!0)}return e&&(e.width||e.height)||t.getBBox===cn||(e=cn.call(t,!0)),!e||e.width||e.x||e.y?e:{x:+pn(t,["x","cx","x1"])||0,y:+pn(t,["y","cy","y1"])||0,width:0,height:0}},mn=function(t){return!(!t.getCTM||t.parentNode&&!t.ownerSVGElement||!dn(t))},gn=function(t,e){if(e){var i=t.style;e in Fi&&e!==an&&(e=sn),i.removeProperty?("ms"!==e.substr(0,2)&&"webkit"!==e.substr(0,6)||(e="-"+e),i.removeProperty(e.replace(Xi,"-$1").toLowerCase())):i.removeAttribute(e)}},_n=function(t,e,i,n,r,s){var a=new Si(t._pt,e,i,0,1,s?$i:Zi);return t._pt=a,a.b=n,a.e=r,t._props.push(i),a},vn={deg:1,rad:1,turn:1},yn=function t(e,i,n,r){var s,a,o,u,h=parseFloat(n)||0,l=(n+"").trim().substr((h+"").length)||"px",f=Bi.style,c=Yi.test(i),p="svg"===e.tagName.toLowerCase(),d=(p?"client":"offset")+(c?"Width":"Height"),m=100,g="px"===r,_="%"===r;return r===l||!h||vn[r]||vn[l]?h:("px"!==l&&!g&&(h=t(e,i,n,"px")),u=e.getCTM&&mn(e),!_&&"%"!==l||!Fi[i]&&!~i.indexOf("adius")?(f[c?"width":"height"]=m+(g?l:r),a=~i.indexOf("adius")||"em"===r&&e.appendChild&&!p?e:e.parentNode,u&&(a=(e.ownerSVGElement||{}).parentNode),a&&a!==Ii&&a.appendChild||(a=Ii.body),(o=a._gsap)&&_&&o.width&&c&&o.time===Ne.time?Pt(h/o.width*m):((_||"%"===l)&&(f.position=un(e,"position")),a===e&&(f.position="static"),a.appendChild(Bi),s=Bi[d],a.removeChild(Bi),f.position="absolute",c&&_&&((o=Et(a)).time=Ne.time,o.width=a[d]),Pt(g?s*h/m:s&&h?m/s*h:0))):(s=u?e.getBBox()[c?"width":"height"]:e[d],Pt(_?h/s*m:h/100*s)))},bn=function(t,e,i,n){var r;return Li||fn(),e in Ui&&"transform"!==e&&~(e=Ui[e]).indexOf(",")&&(e=e.split(",")[0]),Fi[e]&&"transform"!==e?(r=Pn(t,n),r="transformOrigin"!==e?r[e]:r.svg?r.origin:In(un(t,an))+" "+r.zOrigin+"px"):(!(r=t.style[e])||"auto"===r||n||~(r+"").indexOf("calc("))&&(r=kn[e]&&kn[e](t,e,i)||un(t,e)||Mt(t,e)||("opacity"===e?1:0)),i&&!~(r+"").trim().indexOf(" ")?yn(t,e,r,i)+i:r},xn=function(t,e,i,n){if(!i||"none"===i){var r=ln(e,t,1),s=r&&un(t,r,1);s&&s!==i?(e=r,i=s):"borderColor"===e&&(i=un(t,"borderTopColor"))}var a,o,u,h,l,f,c,p,d,m,g,_=new Si(this._pt,t.style,e,0,1,bi),v=0,y=0;if(_.b=i,_.e=n,i+="","auto"===(n+="")&&(t.style[e]=n,n=un(t,e)||n,t.style[e]=i),Ve(a=[i,n]),n=a[1],u=(i=a[0]).match(ot)||[],(n.match(ot)||[]).length){for(;o=ot.exec(n);)c=o[0],d=n.substring(v,o.index),l?l=(l+1)%5:"rgba("!==d.substr(-5)&&"hsla("!==d.substr(-5)||(l=1),c!==(f=u[y++]||"")&&(h=parseFloat(f)||0,g=f.substr((h+"").length),"="===c.charAt(1)&&(c=Dt(h,c)+g),p=parseFloat(c),m=c.substr((p+"").length),v=ot.lastIndex-m.length,m||(m=m||V.units[e]||g,v===n.length&&(n+=m,_.e+=m)),g!==m&&(h=yn(t,e,f,m)||0),_._pt={_next:_._pt,p:d||1===y?d:",",s:h,c:p-h,m:l&&l<4||"zIndex"===e?Math.round:0});_.c=v<n.length?n.substring(v,n.length):""}else _.r="display"===e&&"none"===n?$i:Zi;return ht.test(n)&&(_.e=0),this._pt=_,_},wn={top:"0%",bottom:"100%",left:"0%",right:"100%",center:"50%"},Tn=function(t,e){if(e.tween&&e.tween._time===e.tween._dur){var i,n,r,s=e.t,a=s.style,o=e.u,u=s._gsap;if("all"===o||!0===o)a.cssText="",n=1;else for(r=(o=o.split(",")).length;--r>-1;)i=o[r],Fi[i]&&(n=1,i="transformOrigin"===i?an:sn),gn(s,i);n&&(gn(s,sn),u&&(u.svg&&s.removeAttribute("transform"),Pn(s,1),u.uncache=1))}},kn={clearProps:function(t,e,i,n,r){if("isFromStart"!==r.data){var s=t._pt=new Si(t._pt,e,i,0,0,Tn);return s.u=n,s.pr=-10,s.tween=r,t._props.push(i),1}}},Cn=[1,0,0,1,0,0],Sn={},On=function(t){return"matrix(1, 0, 0, 1, 0, 0)"===t||"none"===t||!t},En=function(t){var e=un(t,sn);return On(e)?Cn:e.substr(7).match(at).map(Pt)},Mn=function(t,e){var i,n,r,s,a=t._gsap||Et(t),o=t.style,u=En(t);return a.svg&&t.getAttribute("transform")?"1,0,0,1,0,0"===(u=[(r=t.transform.baseVal.consolidate().matrix).a,r.b,r.c,r.d,r.e,r.f]).join(",")?Cn:u:(u!==Cn||t.offsetParent||t===Di||a.svg||(r=o.display,o.display="block",(i=t.parentNode)&&t.offsetParent||(s=1,n=t.nextSibling,Di.appendChild(t)),u=En(t),r?o.display=r:gn(t,"display"),s&&(n?i.insertBefore(t,n):i?i.appendChild(t):Di.removeChild(t))),e&&u.length>6?[u[0],u[1],u[4],u[5],u[12],u[13]]:u)},An=function(t,e,i,n,r,s){var a,o,u,h=t._gsap,l=r||Mn(t,!0),f=h.xOrigin||0,c=h.yOrigin||0,p=h.xOffset||0,d=h.yOffset||0,m=l[0],g=l[1],_=l[2],v=l[3],y=l[4],b=l[5],x=e.split(" "),w=parseFloat(x[0])||0,T=parseFloat(x[1])||0;i?l!==Cn&&(o=m*v-g*_)&&(u=w*(-g/o)+T*(m/o)-(m*b-g*y)/o,w=w*(v/o)+T*(-_/o)+(_*b-v*y)/o,T=u):(w=(a=dn(t)).x+(~x[0].indexOf("%")?w/100*a.width:w),T=a.y+(~(x[1]||x[0]).indexOf("%")?T/100*a.height:T)),n||!1!==n&&h.smooth?(y=w-f,b=T-c,h.xOffset=p+(y*m+b*_)-y,h.yOffset=d+(y*g+b*v)-b):h.xOffset=h.yOffset=0,h.xOrigin=w,h.yOrigin=T,h.smooth=!!n,h.origin=e,h.originIsAbsolute=!!i,t.style[an]="0px 0px",s&&(_n(s,h,"xOrigin",f,w),_n(s,h,"yOrigin",c,T),_n(s,h,"xOffset",p,h.xOffset),_n(s,h,"yOffset",d,h.yOffset)),t.setAttribute("data-svg-origin",w+" "+T)},Pn=function(t,e){var i=t._gsap||new Ke(t);if("x"in i&&!e&&!i.uncache)return i;var n,r,s,a,o,u,h,l,f,c,p,d,m,g,_,v,y,b,x,w,T,k,C,S,O,E,M,A,P,I,D,L,B=t.style,R=i.scaleX<0,z="px",F="deg",N=un(t,an)||"0";return n=r=s=u=h=l=f=c=p=0,a=o=1,i.svg=!(!t.getCTM||!mn(t)),g=Mn(t,i.svg),i.svg&&(S=(!i.uncache||"0px 0px"===N)&&!e&&t.getAttribute("data-svg-origin"),An(t,S||N,!!S||i.originIsAbsolute,!1!==i.smooth,g)),d=i.xOrigin||0,m=i.yOrigin||0,g!==Cn&&(b=g[0],x=g[1],w=g[2],T=g[3],n=k=g[4],r=C=g[5],6===g.length?(a=Math.sqrt(b*b+x*x),o=Math.sqrt(T*T+w*w),u=b||x?qi(x,b)*Vi:0,(f=w||T?qi(w,T)*Vi+u:0)&&(o*=Math.abs(Math.cos(f*Ni))),i.svg&&(n-=d-(d*b+m*w),r-=m-(d*x+m*T))):(L=g[6],I=g[7],M=g[8],A=g[9],P=g[10],D=g[11],n=g[12],r=g[13],s=g[14],h=(_=qi(L,P))*Vi,_&&(S=k*(v=Math.cos(-_))+M*(y=Math.sin(-_)),O=C*v+A*y,E=L*v+P*y,M=k*-y+M*v,A=C*-y+A*v,P=L*-y+P*v,D=I*-y+D*v,k=S,C=O,L=E),l=(_=qi(-w,P))*Vi,_&&(v=Math.cos(-_),D=T*(y=Math.sin(-_))+D*v,b=S=b*v-M*y,x=O=x*v-A*y,w=E=w*v-P*y),u=(_=qi(x,b))*Vi,_&&(S=b*(v=Math.cos(_))+x*(y=Math.sin(_)),O=k*v+C*y,x=x*v-b*y,C=C*v-k*y,b=S,k=O),h&&Math.abs(h)+Math.abs(u)>359.9&&(h=u=0,l=180-l),a=Pt(Math.sqrt(b*b+x*x+w*w)),o=Pt(Math.sqrt(C*C+L*L)),_=qi(k,C),f=Math.abs(_)>2e-4?_*Vi:0,p=D?1/(D<0?-D:D):0),i.svg&&(S=t.getAttribute("transform"),i.forceCSS=t.setAttribute("transform","")||!On(un(t,sn)),S&&t.setAttribute("transform",S))),Math.abs(f)>90&&Math.abs(f)<270&&(R?(a*=-1,f+=u<=0?180:-180,u+=u<=0?180:-180):(o*=-1,f+=f<=0?180:-180)),e=e||i.uncache,i.x=n-((i.xPercent=n&&(!e&&i.xPercent||(Math.round(t.offsetWidth/2)===Math.round(-n)?-50:0)))?t.offsetWidth*i.xPercent/100:0)+z,i.y=r-((i.yPercent=r&&(!e&&i.yPercent||(Math.round(t.offsetHeight/2)===Math.round(-r)?-50:0)))?t.offsetHeight*i.yPercent/100:0)+z,i.z=s+z,i.scaleX=Pt(a),i.scaleY=Pt(o),i.rotation=Pt(u)+F,i.rotationX=Pt(h)+F,i.rotationY=Pt(l)+F,i.skewX=f+F,i.skewY=c+F,i.transformPerspective=p+z,(i.zOrigin=parseFloat(N.split(" ")[2])||0)&&(B[an]=In(N)),i.xOffset=i.yOffset=0,i.force3D=V.force3D,i.renderTransform=i.svg?Vn:zi?Fn:Ln,i.uncache=0,i},In=function(t){return(t=t.split(" "))[0]+" "+t[1]},Dn=function(t,e,i){var n=de(e);return Pt(parseFloat(e)+parseFloat(yn(t,"x",i+"px",n)))+n},Ln=function(t,e){e.z="0px",e.rotationY=e.rotationX="0deg",e.force3D=0,Fn(t,e)},Bn="0deg",Rn="0px",zn=") ",Fn=function(t,e){var i=e||this,n=i.xPercent,r=i.yPercent,s=i.x,a=i.y,o=i.z,u=i.rotation,h=i.rotationY,l=i.rotationX,f=i.skewX,c=i.skewY,p=i.scaleX,d=i.scaleY,m=i.transformPerspective,g=i.force3D,_=i.target,v=i.zOrigin,y="",b="auto"===g&&t&&1!==t||!0===g;if(v&&(l!==Bn||h!==Bn)){var x,w=parseFloat(h)*Ni,T=Math.sin(w),k=Math.cos(w);w=parseFloat(l)*Ni,x=Math.cos(w),s=Dn(_,s,T*x*-v),a=Dn(_,a,-Math.sin(w)*-v),o=Dn(_,o,k*x*-v+v)}m!==Rn&&(y+="perspective("+m+zn),(n||r)&&(y+="translate("+n+"%, "+r+"%) "),(b||s!==Rn||a!==Rn||o!==Rn)&&(y+=o!==Rn||b?"translate3d("+s+", "+a+", "+o+") ":"translate("+s+", "+a+zn),u!==Bn&&(y+="rotate("+u+zn),h!==Bn&&(y+="rotateY("+h+zn),l!==Bn&&(y+="rotateX("+l+zn),f===Bn&&c===Bn||(y+="skew("+f+", "+c+zn),1===p&&1===d||(y+="scale("+p+", "+d+zn),_.style[sn]=y||"translate(0, 0)"},Vn=function(t,e){var i,n,r,s,a,o=e||this,u=o.xPercent,h=o.yPercent,l=o.x,f=o.y,c=o.rotation,p=o.skewX,d=o.skewY,m=o.scaleX,g=o.scaleY,_=o.target,v=o.xOrigin,y=o.yOrigin,b=o.xOffset,x=o.yOffset,w=o.forceCSS,T=parseFloat(l),k=parseFloat(f);c=parseFloat(c),p=parseFloat(p),(d=parseFloat(d))&&(p+=d=parseFloat(d),c+=d),c||p?(c*=Ni,p*=Ni,i=Math.cos(c)*m,n=Math.sin(c)*m,r=Math.sin(c-p)*-g,s=Math.cos(c-p)*g,p&&(d*=Ni,a=Math.tan(p-d),r*=a=Math.sqrt(1+a*a),s*=a,d&&(a=Math.tan(d),i*=a=Math.sqrt(1+a*a),n*=a)),i=Pt(i),n=Pt(n),r=Pt(r),s=Pt(s)):(i=m,s=g,n=r=0),(T&&!~(l+"").indexOf("px")||k&&!~(f+"").indexOf("px"))&&(T=yn(_,"x",l,"px"),k=yn(_,"y",f,"px")),(v||y||b||x)&&(T=Pt(T+v-(v*i+y*r)+b),k=Pt(k+y-(v*n+y*s)+x)),(u||h)&&(a=_.getBBox(),T=Pt(T+u/100*a.width),k=Pt(k+h/100*a.height)),a="matrix("+i+","+n+","+r+","+s+","+T+","+k+")",_.setAttribute("transform",a),w&&(_.style[sn]=a)},Nn=function(t,e,i,n,r){var s,a,o=360,u=G(r),h=parseFloat(r)*(u&&~r.indexOf("rad")?Vi:1)-n,l=n+h+"deg";return u&&("short"===(s=r.split("_")[1])&&(h%=o)!==h%180&&(h+=h<0?o:-360),"cw"===s&&h<0?h=(h+36e9)%o-~~(h/o)*o:"ccw"===s&&h>0&&(h=(h-36e9)%o-~~(h/o)*o)),t._pt=a=new Si(t._pt,e,i,n,h,Hi),a.e=l,a.u="deg",t._props.push(i),a},qn=function(t,e){for(var i in e)t[i]=e[i];return t},Xn=function(t,e,i){var n,r,s,a,o,u,h,l=qn({},i._gsap),f=i.style;for(r in l.svg?(s=i.getAttribute("transform"),i.setAttribute("transform",""),f[sn]=e,n=Pn(i,1),gn(i,sn),i.setAttribute("transform",s)):(s=getComputedStyle(i)[sn],f[sn]=e,n=Pn(i,1),f[sn]=s),Fi)(s=l[r])!==(a=n[r])&&"perspective,force3D,transformOrigin,svgOrigin".indexOf(r)<0&&(o=de(s)!==(h=de(a))?yn(i,r,s,h):parseFloat(s),u=parseFloat(a),t._pt=new Si(t._pt,n,r,o,u-o,Wi),t._pt.u=h||0,t._props.push(r));qn(n,l)};At("padding,margin,Width,Radius",(function(t,e){var i="Top",n="Right",r="Bottom",s="Left",a=(e<3?[i,n,r,s]:[i+s,i+n,r+n,r+s]).map((function(i){return e<2?t+i:"border"+i+t}));kn[e>1?"border"+t:t]=function(t,e,i,n,r){var s,o;if(arguments.length<4)return s=a.map((function(e){return bn(t,e,i)})),5===(o=s.join(" ")).split(s[0]).length?s[0]:o;s=(n+"").split(" "),o={},a.forEach((function(t,e){return o[t]=s[e]=s[e]||s[(e-1)/2|0]})),t.init(e,o,r)}}));var Yn,jn,Un,Wn={name:"css",register:fn,targetTest:function(t){return t.style&&t.nodeType},init:function(t,e,i,n,r){var s,a,u,h,l,f,c,p,d,m,g,_,v,y,b,x,w,T,k,C=this._props,S=t.style,O=i.vars.startAt;for(c in Li||fn(),e)if("autoRound"!==c&&(a=e[c],!wt[c]||!ai(c,e,i,n,t,r)))if(l=void 0===a?"undefined":o(a),f=kn[c],"function"===l&&(l=void 0===(a=a.call(i,n,t,r))?"undefined":o(a)),"string"===l&&~a.indexOf("random(")&&(a=Ce(a)),f)f(this,t,c,a,i)&&(b=1);else if("--"===c.substr(0,2))s=(getComputedStyle(t).getPropertyValue(c)+"").trim(),a+="",ze.lastIndex=0,ze.test(s)||(p=de(s),d=de(a)),d?p!==d&&(s=yn(t,c,s,d)+d):p&&(a+=p),this.add(S,"setProperty",s,a,n,r,0,0,c),C.push(c);else if("undefined"!==l){if(O&&c in O?(s="function"==typeof O[c]?O[c].call(i,n,t,r):O[c],G(s)&&~s.indexOf("random(")&&(s=Ce(s)),de(s+"")||(s+=V.units[c]||de(bn(t,c))||""),"="===(s+"").charAt(1)&&(s=bn(t,c))):s=bn(t,c),h=parseFloat(s),(m="string"===l&&"="===a.charAt(1)&&a.substr(0,2))&&(a=a.substr(2)),u=parseFloat(a),c in Ui&&("autoAlpha"===c&&(1===h&&"hidden"===bn(t,"visibility")&&u&&(h=0),_n(this,S,"visibility",h?"inherit":"hidden",u?"inherit":"hidden",!u)),"scale"!==c&&"transform"!==c&&~(c=Ui[c]).indexOf(",")&&(c=c.split(",")[0])),g=c in Fi)if(_||((v=t._gsap).renderTransform&&!e.parseTransform||Pn(t,e.parseTransform),y=!1!==e.smoothOrigin&&v.smooth,(_=this._pt=new Si(this._pt,S,sn,0,1,v.renderTransform,v,0,-1)).dep=1),"scale"===c)this._pt=new Si(this._pt,v,"scaleY",v.scaleY,(m?Dt(v.scaleY,m+u):u)-v.scaleY||0),C.push("scaleY",c),c+="X";else{if("transformOrigin"===c){w=void 0,T=void 0,k=void 0,w=(x=a).split(" "),T=w[0],k=w[1]||"50%","top"!==T&&"bottom"!==T&&"left"!==k&&"right"!==k||(x=T,T=k,k=x),w[0]=wn[T]||T,w[1]=wn[k]||k,a=w.join(" "),v.svg?An(t,a,0,y,0,this):((d=parseFloat(a.split(" ")[2])||0)!==v.zOrigin&&_n(this,v,"zOrigin",v.zOrigin,d),_n(this,S,c,In(s),In(a)));continue}if("svgOrigin"===c){An(t,a,1,y,0,this);continue}if(c in Sn){Nn(this,v,c,h,m?Dt(h,m+a):a);continue}if("smoothOrigin"===c){_n(this,v,"smooth",v.smooth,a);continue}if("force3D"===c){v[c]=a;continue}if("transform"===c){Xn(this,a,t);continue}}else c in S||(c=ln(c)||c);if(g||(u||0===u)&&(h||0===h)&&!ji.test(a)&&c in S)u||(u=0),(p=(s+"").substr((h+"").length))!==(d=de(a)||(c in V.units?V.units[c]:p))&&(h=yn(t,c,s,d)),this._pt=new Si(this._pt,g?v:S,c,h,(m?Dt(h,m+u):u)-h,g||"px"!==d&&"zIndex"!==c||!1===e.autoRound?Wi:Gi),this._pt.u=d||0,p!==d&&"%"!==d&&(this._pt.b=s,this._pt.r=Qi);else if(c in S)xn.call(this,t,c,s,m?m+a:a);else{if(!(c in t)){mt(c,a);continue}this.add(t,c,s||t[c],m?m+a:a,n,r)}C.push(c)}b&&Ci(this)},get:bn,aliases:Ui,getSetter:function(t,e,i){var n=Ui[e];return n&&n.indexOf(",")<0&&(e=n),e in Fi&&e!==an&&(t._gsap.x||bn(t,"x"))?i&&Ri===i?"scale"===e?en:tn:(Ri=i||{},"scale"===e?nn:rn):t.style&&!J(t.style[e])?Ji:~e.indexOf("-")?Ki:_i(t,e)},core:{_removeProperty:gn,_getMatrix:Mn}};Ai.utils.checkPrefix=ln,Un=At((Yn="x,y,z,scale,scaleX,scaleY,xPercent,yPercent")+","+(jn="rotation,rotationX,rotationY,skewX,skewY")+",transform,transformOrigin,svgOrigin,force3D,smoothOrigin,transformPerspective",(function(t){Fi[t]=1})),At(jn,(function(t){V.units[t]="deg",Sn[t]=1})),Ui[Un[13]]=Yn+","+jn,At("0:translateX,1:translateY,2:translateZ,8:rotate,8:rotationZ,8:rotateZ,9:rotateX,10:rotateY",(function(t){var e=t.split(":");Ui[e[1]]=Un[e[0]]})),At("x,y,z,top,right,bottom,left,width,height,fontSize,padding,margin,perspective",(function(t){V.units[t]="px"})),Ai.registerPlugin(Wn);var Hn,Qn,Gn,Zn,$n,Jn,Kn,tr,er,ir=Ai.registerPlugin(Wn)||Ai,nr=(ir.core.Tween,"transform"),rr=nr+"Origin",sr=function(t){var e=t.ownerDocument||t;!(nr in t.style)&&"msTransform"in t.style&&(rr=(nr="msTransform")+"Origin");for(;e.parentNode&&(e=e.parentNode););if(Qn=window,Kn=new gr,e){Hn=e,Gn=e.documentElement,Zn=e.body,(tr=Hn.createElementNS("http://www.w3.org/2000/svg","g")).style.transform="none";var i=e.createElement("div"),n=e.createElement("div");Zn.appendChild(i),i.appendChild(n),i.style.position="static",i.style[nr]="translate3d(0,0,1px)",er=n.offsetParent!==i,Zn.removeChild(i)}return e},ar=[],or=[],ur=function(){return Qn.pageYOffset||Hn.scrollTop||Gn.scrollTop||Zn.scrollTop||0},hr=function(){return Qn.pageXOffset||Hn.scrollLeft||Gn.scrollLeft||Zn.scrollLeft||0},lr=function(t){return t.ownerSVGElement||("svg"===(t.tagName+"").toLowerCase()?t:null)},fr=function t(e){return"fixed"===Qn.getComputedStyle(e).position||((e=e.parentNode)&&1===e.nodeType?t(e):void 0)},cr=function t(e,i){if(e.parentNode&&(Hn||sr(e))){var n=lr(e),r=n?n.getAttribute("xmlns")||"http://www.w3.org/2000/svg":"http://www.w3.org/1999/xhtml",s=n?i?"rect":"g":"div",a=2!==i?0:100,o=3===i?100:0,u="position:absolute;display:block;pointer-events:none;margin:0;padding:0;",h=Hn.createElementNS?Hn.createElementNS(r.replace(/^https/,"http"),s):Hn.createElement(s);return i&&(n?(Jn||(Jn=t(e)),h.setAttribute("width",.01),h.setAttribute("height",.01),h.setAttribute("transform","translate("+a+","+o+")"),Jn.appendChild(h)):($n||(($n=t(e)).style.cssText=u),h.style.cssText=u+"width:0.1px;height:0.1px;top:"+o+"px;left:"+a+"px",$n.appendChild(h))),h}throw"Need document and parent."},pr=function(t){var e,i=t.getCTM();return i||(e=t.style[nr],t.style[nr]="none",t.appendChild(tr),i=tr.getCTM(),t.removeChild(tr),e?t.style[nr]=e:t.style.removeProperty(nr.replace(/([A-Z])/g,"-$1").toLowerCase())),i||Kn.clone()},dr=function(t,e){var i,n,r,s,a,o,u=lr(t),h=t===u,l=u?ar:or,f=t.parentNode;if(t===Qn)return t;if(l.length||l.push(cr(t,1),cr(t,2),cr(t,3)),i=u?Jn:$n,u)h?(s=-(r=pr(t)).e/r.a,a=-r.f/r.d,n=Kn):t.getBBox?(r=t.getBBox(),n=(n=t.transform?t.transform.baseVal:{}).numberOfItems?n.numberOfItems>1?function(t){for(var e=new gr,i=0;i<t.numberOfItems;i++)e.multiply(t.getItem(i).matrix);return e}(n):n.getItem(0).matrix:Kn,s=n.a*r.x+n.c*r.y,a=n.b*r.x+n.d*r.y):(n=new gr,s=a=0),e&&"g"===t.tagName.toLowerCase()&&(s=a=0),(h?u:f).appendChild(i),i.setAttribute("transform","matrix("+n.a+","+n.b+","+n.c+","+n.d+","+(n.e+s)+","+(n.f+a)+")");else{if(s=a=0,er)for(n=t.offsetParent,r=t;r&&(r=r.parentNode)&&r!==n&&r.parentNode;)(Qn.getComputedStyle(r)[nr]+"").length>4&&(s=r.offsetLeft,a=r.offsetTop,r=0);if("absolute"!==(o=Qn.getComputedStyle(t)).position&&"fixed"!==o.position)for(n=t.offsetParent;f&&f!==n;)s+=f.scrollLeft||0,a+=f.scrollTop||0,f=f.parentNode;(r=i.style).top=t.offsetTop-a+"px",r.left=t.offsetLeft-s+"px",r[nr]=o[nr],r[rr]=o[rr],r.position="fixed"===o.position?"fixed":"absolute",t.parentNode.appendChild(i)}return i},mr=function(t,e,i,n,r,s,a){return t.a=e,t.b=i,t.c=n,t.d=r,t.e=s,t.f=a,t},gr=function(){function t(t,e,i,n,r,s){void 0===t&&(t=1),void 0===e&&(e=0),void 0===i&&(i=0),void 0===n&&(n=1),void 0===r&&(r=0),void 0===s&&(s=0),mr(this,t,e,i,n,r,s)}var e=t.prototype;return e.inverse=function(){var t=this.a,e=this.b,i=this.c,n=this.d,r=this.e,s=this.f,a=t*n-e*i||1e-10;return mr(this,n/a,-e/a,-i/a,t/a,(i*s-n*r)/a,-(t*s-e*r)/a)},e.multiply=function(t){var e=this.a,i=this.b,n=this.c,r=this.d,s=this.e,a=this.f,o=t.a,u=t.c,h=t.b,l=t.d,f=t.e,c=t.f;return mr(this,o*e+h*n,o*i+h*r,u*e+l*n,u*i+l*r,s+f*e+c*n,a+f*i+c*r)},e.clone=function(){return new t(this.a,this.b,this.c,this.d,this.e,this.f)},e.equals=function(t){var e=this.a,i=this.b,n=this.c,r=this.d,s=this.e,a=this.f;return e===t.a&&i===t.b&&n===t.c&&r===t.d&&s===t.e&&a===t.f},e.apply=function(t,e){void 0===e&&(e={});var i=t.x,n=t.y,r=this.a,s=this.b,a=this.c,o=this.d,u=this.e,h=this.f;return e.x=i*r+n*a+u||0,e.y=i*s+n*o+h||0,e},t}();
/*!
 * matrix 3.10.4
 * https://greensock.com
 *
 * Copyright 2008-2022, GreenSock. All rights reserved.
 * Subject to the terms at https://greensock.com/standard-license or for
 * Club GreenSock members, the agreement issued with that membership.
 * @author: Jack Doyle, jack@greensock.com
*/function _r(t,e,i,n){if(!t||!t.parentNode||(Hn||sr(t)).documentElement===t)return new gr;var r=function(t){for(var e,i;t&&t!==Zn;)(i=t._gsap)&&i.uncache&&i.get(t,"x"),i&&!i.scaleX&&!i.scaleY&&i.renderTransform&&(i.scaleX=i.scaleY=1e-4,i.renderTransform(1,i),e?e.push(i):e=[i]),t=t.parentNode;return e}(t),s=lr(t)?ar:or,a=dr(t,i),o=s[0].getBoundingClientRect(),u=s[1].getBoundingClientRect(),h=s[2].getBoundingClientRect(),l=a.parentNode,f=!n&&fr(t),c=new gr((u.left-o.left)/100,(u.top-o.top)/100,(h.left-o.left)/100,(h.top-o.top)/100,o.left+(f?0:hr()),o.top+(f?0:ur()));if(l.removeChild(a),r)for(o=r.length;o--;)(u=r[o]).scaleX=u.scaleY=0,u.renderTransform(1,u);return e?c.inverse():c}var vr,yr,br,xr,wr,Tr,kr,Cr=1,Sr=function(t,e){return t.actions.forEach((function(t){return t.vars[e]&&t.vars[e](t)}))},Or={},Er=180/Math.PI,Mr=Math.PI/180,Ar={},Pr={},Ir={},Dr=function(t){return"string"==typeof t?t.split(" ").join("").split(","):t},Lr=Dr("onStart,onUpdate,onComplete,onReverseComplete,onInterrupt"),Br=Dr("transform,transformOrigin,width,height,position,top,left,opacity,zIndex,maxWidth,maxHeight,minWidth,minHeight"),Rr=function(t){return vr(t)[0]||console.warn("Element not found:",t)},zr=function(t){return Math.round(1e4*t)/1e4||0},Fr=function(t,e,i){return t.forEach((function(t){return t.classList[i](e)}))},Vr={zIndex:1,kill:1,simple:1,spin:1,clearProps:1,targets:1,toggleClass:1,onComplete:1,onUpdate:1,onInterrupt:1,onStart:1,delay:1,repeat:1,repeatDelay:1,yoyo:1,scale:1,fade:1,absolute:1,props:1,onEnter:1,onLeave:1,custom:1,paused:1,nested:1,prune:1,absoluteOnLeave:1},Nr={zIndex:1,simple:1,clearProps:1,scale:1,absolute:1,fitChild:1,getVars:1,props:1},qr=function(t){return t.replace(/([A-Z])/g,"-$1").toLowerCase()},Xr=function(t,e){var i,n={};for(i in t)e[i]||(n[i]=t[i]);return n},Yr={},jr=function(t){var e=Yr[t]=Dr(t);return Ir[t]=e.concat(Br),e},Ur=function t(e,i,n){void 0===n&&(n=0);for(var r=e.parentNode,s=1e3*Math.pow(10,n)*(i?-1:1),a=i?900*-s:0;e;)a+=s,e=e.previousSibling;return r?a+t(r,i,n+1):a},Wr=function(t,e,i){return t.forEach((function(t){return t.d=Ur(i?t.element:t.t,e)})),t.sort((function(t,e){return t.d-e.d})),t},Hr=function(t,e){for(var i,n,r=t.element.style,s=t.css=t.css||[],a=e.length;a--;)n=r[i=e[a]]||r.getPropertyValue(i),s.push(n?i:Pr[i]||(Pr[i]=qr(i)),n);return r},Qr=function(t){var e=t.css,i=t.element.style,n=0;for(t.cache.uncache=1;n<e.length;n+=2)e[n+1]?i[e[n]]=e[n+1]:i.removeProperty(e[n])},Gr=function(t,e){t.forEach((function(t){return t.a.cache.uncache=1})),e||t.finalStates.forEach(Qr)},Zr="paddingTop,paddingRight,paddingBottom,paddingLeft,gridArea,transition".split(","),$r=function(t,e,i){var n,r,s,a=t.element,o=t.width,u=t.height,h=t.uncache,l=t.getProp,f=a.style,c=4;if("object"!=typeof e&&(e=t),br&&1!==i)return br._abs.push({t:a,b:t,a:t,sd:0}),br._final.push((function(){return t.cache.uncache=1,Qr(t)})),a;for(r="none"===l("display"),t.isVisible&&!r||(r&&(Hr(t,["display"]).display=e.display),t.matrix=e.matrix,t.width=o=t.width||e.width,t.height=u=t.height||e.height),Hr(t,Zr),s=window.getComputedStyle(a);c--;)f[Zr[c]]=s[Zr[c]];if(f.gridArea="1 / 1 / 1 / 1",f.transition="none",f.position="absolute",f.width=o+"px",f.height=u+"px",f.top||(f.top="0px"),f.left||(f.left="0px"),h)n=new ms(a);else if((n=Xr(t,Ar)).position="absolute",t.simple){var p=a.getBoundingClientRect();n.matrix=new gr(1,0,0,1,p.left+hr(),p.top+ur())}else n.matrix=_r(a,!1,!1,!0);return n=rs(n,t,!0),t.x=Tr(n.x,.01),t.y=Tr(n.y,.01),a},Jr=function(t,e){return!0!==e&&(e=vr(e),t=t.filter((function(t){if(-1!==e.indexOf((t.sd<0?t.b:t.a).element))return!0;t.t._gsap.renderTransform(1),t.t.style.width=t.b.width+"px",t.t.style.height=t.b.height+"px"}))),t},Kr=function(t){return Wr(t,!0).forEach((function(t){return(t.a.isVisible||t.b.isVisible)&&$r(t.sd<0?t.b:t.a,t.b,1)}))},ts=function(t,e,i,n){return t instanceof ms?t:t instanceof ds?function(t,e){return e&&t.idLookup[ts(e).id]||t.elementStates[0]}(t,n):new ms("string"==typeof t?Rr(t)||console.warn(t+" not found"):t,e,i)},es=function(t,e){var i,n=t.style||t;for(i in e)n[i]=e[i]},is=function(t){return t.map((function(t){return t.element}))},ns=function(t,e,i){return t&&e.length&&i.add(t(is(e),i,new ds(e,0,!0)),0)},rs=function(t,e,i,n,r,s){var a,o,u,h,l,f,c,p=t.element,d=t.cache,m=t.parent,g=t.x,_=t.y,v=e.width,y=e.height,b=e.scaleX,x=e.scaleY,w=e.rotation,T=e.bounds,k=s&&p.style.cssText,C=s&&p.getBBox&&p.getAttribute("transform"),S=t,O=e.matrix,E=O.e,M=O.f,A=t.bounds.width!==T.width||t.bounds.height!==T.height||t.scaleX!==b||t.scaleY!==x||t.rotation!==w,P=!A&&t.simple&&e.simple&&!r;return P||!m?(b=x=1,w=a=0):(l=function(t){var e=t._gsap||yr.core.getCache(t);return e.gmCache===yr.ticker.frame?e.gMatrix:(e.gmCache=yr.ticker.frame,e.gMatrix=_r(t,!0,!1,!0))}(m),f=l.clone().multiply(e.ctm?e.matrix.clone().multiply(e.ctm):e.matrix),w=zr(Math.atan2(f.b,f.a)*Er),a=zr(Math.atan2(f.c,f.d)*Er+w)%360,b=Math.sqrt(Math.pow(f.a,2)+Math.pow(f.b,2)),x=Math.sqrt(Math.pow(f.c,2)+Math.pow(f.d,2))*Math.cos(a*Mr),r&&(r=vr(r)[0],h=yr.getProperty(r),c=r.getBBox&&"function"==typeof r.getBBox&&r.getBBox(),S={scaleX:h("scaleX"),scaleY:h("scaleY"),width:c?c.width:Math.ceil(parseFloat(h("width","px"))),height:c?c.height:parseFloat(h("height","px"))}),d.rotation=w+"deg",d.skewX=a+"deg"),i?(b*=v!==S.width&&S.width?v/S.width:1,x*=y!==S.height&&S.height?y/S.height:1,d.scaleX=b,d.scaleY=x):(v=Tr(v*b/S.scaleX,0),y=Tr(y*x/S.scaleY,0),p.style.width=v+"px",p.style.height=y+"px"),n&&es(p,e.props),P||!m?(g+=E-t.matrix.e,_+=M-t.matrix.f):A||m!==e.parent?(d.renderTransform(1,d),f=_r(r||p,!1,!1,!0),o=l.apply({x:f.e,y:f.f}),g+=(u=l.apply({x:E,y:M})).x-o.x,_+=u.y-o.y):(l.e=l.f=0,g+=(u=l.apply({x:E-t.matrix.e,y:M-t.matrix.f})).x,_+=u.y),g=Tr(g,.02),_=Tr(_,.02),!s||s instanceof ms?(d.x=g+"px",d.y=_+"px",d.renderTransform(1,d)):(p.style.cssText=k,p.getBBox&&p.setAttribute("transform",C||""),d.uncache=1),s&&(s.x=g,s.y=_,s.rotation=w,s.skewX=a,i?(s.scaleX=b,s.scaleY=x):(s.width=v,s.height=y)),s||d},ss=function(t,e){return t instanceof ds?t:new ds(t,e)},as=function(t,e,i){var n=t.idLookup[i],r=t.alt[i];return!r.isVisible||(e.getElementState(r.element)||r).isVisible&&n.isVisible?n:r},os=[],us="width,height,overflowX,overflowY".split(","),hs=function(t){if(t!==kr){var e=wr.style,i=wr.clientWidth===window.outerWidth,n=wr.clientHeight===window.outerHeight,r=4;if(t&&(i||n)){for(;r--;)os[r]=e[us[r]];i&&(e.width=wr.clientWidth+"px",e.overflowY="hidden"),n&&(e.height=wr.clientHeight+"px",e.overflowX="hidden"),kr=t}else if(kr){for(;r--;)os[r]?e[us[r]]=os[r]:e.removeProperty(qr(us[r]));kr=t}}},ls=function(t,e,i,n){t instanceof ds&&e instanceof ds||console.warn("Not a valid state object.");var r,s,a,o,u,h,l,f,c,p,d,m,g,_,v,y=i=i||{},b=y.clearProps,x=y.onEnter,w=y.onLeave,T=y.absolute,k=y.absoluteOnLeave,C=y.custom,S=y.delay,O=y.paused,E=y.repeat,M=y.repeatDelay,A=y.yoyo,P=y.toggleClass,I=y.nested,D=y.zIndex,L=y.scale,B=y.fade,R=y.stagger,z=y.spin,F=y.prune,V=("props"in i?i:t).props,N=Xr(i,Vr),q=yr.timeline({delay:S,paused:O,repeat:E,repeatDelay:M,yoyo:A}),X=N,Y=[],j=[],U=[],W=[],H=!0===z?1:z||0,Q="function"==typeof z?z:function(){return H},G=t.interrupted||e.interrupted,Z=q[1!==n?"to":"from"];for(s in e.idLookup)d=e.alt[s]?as(e,t,s):e.idLookup[s],u=d.element,p=t.idLookup[s],t.alt[s]&&u===p.element&&(t.alt[s].isVisible||!d.isVisible)&&(p=t.alt[s]),p?(h={t:u,b:p,a:d,sd:p.element===u?0:d.isVisible?1:-1},U.push(h),h.sd&&(h.sd<0&&(h.b=d,h.a=p),G&&Hr(h.b,V?Ir[V]:Br),B&&U.push(h.swap={t:p.element,b:h.b,a:h.a,sd:-h.sd,swap:h})),u._flip=p.element._flip=br?br.timeline:q):d.isVisible&&(U.push({t:u,b:Xr(d,{isVisible:1}),a:d,sd:0,entering:1}),u._flip=br?br.timeline:q);(V&&(Yr[V]||jr(V)).forEach((function(t){return N[t]=function(e){return U[e].a.props[t]}})),U.finalStates=c=[],m=function(){for(Wr(U),hs(!0),o=0;o<U.length;o++)h=U[o],g=h.a,_=h.b,!F||g.isDifferent(_)||h.entering?(u=h.t,I&&!(h.sd<0)&&o&&(g.matrix=_r(u,!1,!1,!0)),h.sd||_.isVisible&&g.isVisible?(h.sd<0?(l=new ms(u,V,t.simple),rs(l,g,L,0,0,l),l.matrix=_r(u,!1,!1,!0),l.css=h.b.css,h.a=g=l,B&&(u.style.opacity=G?_.opacity:g.opacity),R&&W.push(u)):h.sd>0&&B&&(u.style.opacity=G?g.opacity-_.opacity:"0"),rs(g,_,L,V)):_.isVisible!==g.isVisible&&(_.isVisible?g.isVisible||(_.css=g.css,j.push(_),U.splice(o--,1),T&&I&&rs(g,_,L,V)):(g.isVisible&&Y.push(g),U.splice(o--,1))),L||(u.style.maxWidth=Math.max(g.width,_.width)+"px",u.style.maxHeight=Math.max(g.height,_.height)+"px",u.style.minWidth=Math.min(g.width,_.width)+"px",u.style.minHeight=Math.min(g.height,_.height)+"px"),I&&P&&u.classList.add(P)):U.splice(o--,1),c.push(g);var e;if(P&&(e=c.map((function(t){return t.element})),I&&e.forEach((function(t){return t.classList.remove(P)}))),hs(!1),L?(N.scaleX=function(t){return U[t].a.scaleX},N.scaleY=function(t){return U[t].a.scaleY}):(N.width=function(t){return U[t].a.width+"px"},N.height=function(t){return U[t].a.height+"px"},N.autoRound=i.autoRound||!1),N.x=function(t){return U[t].a.x+"px"},N.y=function(t){return U[t].a.y+"px"},N.rotation=function(t){return U[t].a.rotation+(z?360*Q(t,f[t],f):0)},N.skewX=function(t){return U[t].a.skewX},f=U.map((function(t){return t.t})),(D||0===D)&&(N.modifiers={zIndex:function(){return D}},N.zIndex=D,N.immediateRender=!1!==i.immediateRender),B&&(N.opacity=function(t){return U[t].sd<0?0:U[t].sd>0?U[t].a.opacity:"+=0"}),W.length){R=yr.utils.distribute(R);var n=f.slice(W.length);N.stagger=function(t,e){return R(~W.indexOf(e)?f.indexOf(U[t].swap.t):t,e,n)}}if(Lr.forEach((function(t){return i[t]&&q.eventCallback(t,i[t],i[t+"Params"])})),C&&f.length)for(s in X=Xr(N,Vr),"scale"in C&&(C.scaleX=C.scaleY=C.scale,delete C.scale),C)(r=Xr(C[s],Nr))[s]=N[s],!("duration"in r)&&"duration"in N&&(r.duration=N.duration),r.stagger=N.stagger,Z.call(q,f,r,0),delete X[s];(f.length||j.length||Y.length)&&(P&&q.add((function(){return Fr(e,P,q._zTime<0?"remove":"add")}),0)&&!O&&Fr(e,P,"add"),f.length&&Z.call(q,f,X,0)),ns(x,Y,q),ns(w,j,q);var p=br&&br.timeline;p&&(p.add(q,0),br._final.push((function(){return Gr(U,!b)}))),a=q.duration(),q.call((function(){var t=q.time()>=a;t&&!p&&Gr(U,!b),P&&Fr(e,P,t?"remove":"add")}))},k&&(T=U.filter((function(t){return!t.sd&&!t.a.isVisible&&t.b.isVisible})).map((function(t){return t.a.element}))),br)?(T&&(v=br._abs).push.apply(v,Jr(U,T)),br._run.push(m)):(T&&Kr(Jr(U,T)),m());return br?br.timeline:q},fs=function t(e){e.vars.onInterrupt&&e.vars.onInterrupt.apply(e,e.vars.onInterruptParams||[]),e.getChildren(!0,!1,!0).forEach(t)},cs=function(t,e){if(t&&t.progress()<1&&!t.paused())return e&&(fs(t),e<2&&t.progress(1),t.kill()),!0},ps=function(t){for(var e,i=t.idLookup={},n=t.alt={},r=t.elementStates,s=r.length;s--;)i[(e=r[s]).id]?n[e.id]=e:i[e.id]=e},ds=function(){function t(t,e,i){if(this.props=e&&e.props,this.simple=!(!e||!e.simple),i)this.targets=is(t),this.elementStates=t,ps(this);else{this.targets=vr(t);var n=e&&(!1===e.kill||e.batch&&!e.kill);br&&!n&&br._kill.push(this),this.update(n||!!br)}}var e=t.prototype;return e.update=function(t){var e=this;return this.elementStates=this.targets.map((function(t){return new ms(t,e.props,e.simple)})),ps(this),this.interrupt(t),this.recordInlineStyles(),this},e.clear=function(){return this.targets.length=this.elementStates.length=0,ps(this),this},e.fit=function(t,e,i){for(var n,r,s=Wr(this.elementStates.slice(0),!1,!0),a=(t||this).idLookup,o=0;o<s.length;o++)n=s[o],i&&(n.matrix=_r(n.element,!1,!1,!0)),(r=a[n.id])&&rs(n,r,e,!0,0,n),n.matrix=_r(n.element,!1,!1,!0);return this},e.getProperty=function(t,e){var i=this.getElementState(t)||Ar;return(e in i?i:i.props||Ar)[e]},e.add=function(t){for(var e,i,n,r=t.targets.length,s=this.idLookup,a=this.alt;r--;)(n=s[(i=t.elementStates[r]).id])&&(i.element===n.element||a[i.id]&&a[i.id].element===i.element)?(e=this.elementStates.indexOf(i.element===n.element?n:a[i.id]),this.targets.splice(e,1,t.targets[r]),this.elementStates.splice(e,1,i)):(this.targets.push(t.targets[r]),this.elementStates.push(i));return t.interrupted&&(this.interrupted=!0),t.simple||(this.simple=!1),ps(this),this},e.compare=function(t){var e,i,n,r,s,a,o,u,h=t.idLookup,l=this.idLookup,f=[],c=[],p=[],d=[],m=[],g=t.alt,_=this.alt,v=function(t,e,i){return(t.isVisible!==e.isVisible?t.isVisible?p:d:t.isVisible?c:f).push(i)&&m.push(i)},y=function(t,e,i){return m.indexOf(i)<0&&v(t,e,i)};for(n in h)s=g[n],a=_[n],r=(e=s?as(t,this,n):h[n]).element,i=l[n],a?(u=i.isVisible||!a.isVisible&&r===i.element?i:a,(o=!s||e.isVisible||s.isVisible||u.element!==s.element?e:s).isVisible&&u.isVisible&&o.element!==u.element?((o.isDifferent(u)?c:f).push(o.element,u.element),m.push(o.element,u.element)):v(o,u,o.element),s&&o.element===s.element&&(s=h[n]),y(o.element!==i.element&&s?s:o,i,i.element),y(s&&s.element===a.element?s:o,a,a.element),s&&y(s,a.element===s.element?a:i,s.element)):(i?i.isDifferent(e)?v(e,i,r):f.push(r):p.push(r),s&&y(s,i,s.element));for(n in l)h[n]||(d.push(l[n].element),_[n]&&d.push(_[n].element));return{changed:c,unchanged:f,enter:p,leave:d}},e.recordInlineStyles=function(){for(var t=Ir[this.props]||Br,e=this.elementStates.length;e--;)Hr(this.elementStates[e],t)},e.interrupt=function(t){var e=this,i=[];this.targets.forEach((function(n){var r=n._flip,s=cs(r,t?0:1);t&&s&&i.indexOf(r)<0&&r.add((function(){return e.updateVisibility()})),s&&i.push(r)})),!t&&i.length&&this.updateVisibility(),this.interrupted||(this.interrupted=!!i.length)},e.updateVisibility=function(){this.elementStates.forEach((function(t){var e=t.element.getBoundingClientRect();t.isVisible=!!(e.width||e.height||e.top||e.left),t.uncache=1}))},e.getElementState=function(t){return this.elementStates[this.targets.indexOf(Rr(t))]},e.makeAbsolute=function(){return Wr(this.elementStates.slice(0),!0,!0).map($r)},t}(),ms=function(){function t(t,e,i){this.element=t,this.update(e,i)}var e=t.prototype;return e.isDifferent=function(t){var e=this.bounds,i=t.bounds;return e.top!==i.top||e.left!==i.left||e.width!==i.width||e.height!==i.height||!this.matrix.equals(t.matrix)||this.opacity!==t.opacity||this.props&&t.props&&JSON.stringify(this.props)!==JSON.stringify(t.props)},e.update=function(t,e){var i,n,r=this,s=r.element,a=yr.getProperty(s),o=yr.core.getCache(s),u=s.getBoundingClientRect(),h=s.getBBox&&"function"==typeof s.getBBox&&"svg"!==s.nodeName.toLowerCase()&&s.getBBox(),l=e?new gr(1,0,0,1,u.left+hr(),u.top+ur()):_r(s,!1,!1,!0);r.getProp=a,r.element=s,r.id=((n=(i=s).getAttribute("data-flip-id"))||i.setAttribute("data-flip-id",n="auto-"+Cr++),n),r.matrix=l,r.cache=o,r.bounds=u,r.isVisible=!!(u.width||u.height||u.left||u.top),r.display=a("display"),r.position=a("position"),r.parent=s.parentNode,r.x=a("x"),r.y=a("y"),r.scaleX=o.scaleX,r.scaleY=o.scaleY,r.rotation=a("rotation"),r.skewX=a("skewX"),r.opacity=a("opacity"),r.width=h?h.width:Tr(a("width","px"),.04),r.height=h?h.height:Tr(a("height","px"),.04),t&&function(t,e){for(var i=yr.getProperty(t.element,null,"native"),n=t.props={},r=e.length;r--;)n[e[r]]=(i(e[r])+"").trim();n.zIndex&&(n.zIndex=parseFloat(n.zIndex)||0)}(r,Yr[t]||jr(t)),r.ctm=s.getCTM&&"svg"===s.nodeName.toLowerCase()&&pr(s).inverse(),r.simple=e||1===zr(l.a)&&!zr(l.b)&&!zr(l.c)&&1===zr(l.d),r.uncache=0},t}(),gs=function(){function t(t,e){this.vars=t,this.batch=e,this.states=[],this.timeline=e.timeline}var e=t.prototype;return e.getStateById=function(t){for(var e=this.states.length;e--;)if(this.states[e].idLookup[t])return this.states[e]},e.kill=function(){this.batch.remove(this)},t}(),_s=function(){function t(t){this.id=t,this.actions=[],this._kill=[],this._final=[],this._abs=[],this._run=[],this.data={},this.state=new ds,this.timeline=yr.timeline()}var e=t.prototype;return e.add=function(t){var e=this.actions.filter((function(e){return e.vars===t}));return e.length?e[0]:(e=new gs("function"==typeof t?{animate:t}:t,this),this.actions.push(e),e)},e.remove=function(t){var e=this.actions.indexOf(t);return e>=0&&this.actions.splice(e,1),this},e.getState=function(t){var e=this,i=br,n=xr;return br=this,this.state.clear(),this._kill.length=0,this.actions.forEach((function(i){i.vars.getState&&(i.states.length=0,xr=i,i.state=i.vars.getState(i)),t&&i.states.forEach((function(t){return e.state.add(t)}))})),xr=n,br=i,this.killConflicts(),this},e.animate=function(){var t,e,i=this,n=br,r=this.timeline,s=this.actions.length;for(br=this,r.clear(),this._abs.length=this._final.length=this._run.length=0,this.actions.forEach((function(t){t.vars.animate&&t.vars.animate(t);var e,i,n=t.vars.onEnter,r=t.vars.onLeave,s=t.targets;s&&s.length&&(n||r)&&(e=new ds,t.states.forEach((function(t){return e.add(t)})),(i=e.compare(vs.getState(s))).enter.length&&n&&n(i.enter),i.leave.length&&r&&r(i.leave))})),Kr(this._abs),this._run.forEach((function(t){return t()})),e=r.duration(),t=this._final.slice(0),r.add((function(){e<=r.time()&&(t.forEach((function(t){return t()})),Sr(i,"onComplete"))})),br=n;s--;)this.actions[s].vars.once&&this.actions[s].kill();return Sr(this,"onStart"),r.restart(),this},e.loadState=function(t){t||(t=function(){return 0});var e=[];return this.actions.forEach((function(i){if(i.vars.loadState){var n,r=function r(s){s&&(i.targets=s),~(n=e.indexOf(r))&&(e.splice(n,1),e.length||t())};e.push(r),i.vars.loadState(r)}})),e.length||t(),this},e.setState=function(){return this.actions.forEach((function(t){return t.targets=t.vars.setState&&t.vars.setState(t)})),this},e.killConflicts=function(t){return this.state.interrupt(t),this._kill.forEach((function(e){return e.interrupt(t)})),this},e.run=function(t,e){var i=this;return this!==br&&(t||this.getState(e),this.loadState((function(){i._killed||(i.setState(),i.animate())}))),this},e.clear=function(t){this.state.clear(),t||(this.actions.length=0)},e.getStateById=function(t){for(var e,i=this.actions.length;i--;)if(e=this.actions[i].getStateById(t))return e;return this.state.idLookup[t]&&this.state},e.kill=function(){this._killed=1,this.clear(),delete Or[this.id]},t}(),vs=function(){function t(){}return t.getState=function(e,i){var n=ss(e,i);return xr&&xr.states.push(n),i&&i.batch&&t.batch(i.batch).state.add(n),n},t.from=function(t,e){return"clearProps"in(e=e||{})||(e.clearProps=!0),ls(t,ss(e.targets||t.targets,{props:e.props||t.props,simple:e.simple,kill:!!e.kill}),e,-1)},t.to=function(t,e){return ls(t,ss(e.targets||t.targets,{props:e.props||t.props,simple:e.simple,kill:!!e.kill}),e,1)},t.fromTo=function(t,e,i){return ls(t,e,i)},t.fit=function(t,e,i){var n=i?Xr(i,Nr):{},r=i||n,s=r.absolute,a=r.scale,o=r.getVars,u=r.props,h=r.runBackwards,l=r.onComplete,f=r.simple,c=i&&i.fitChild&&Rr(i.fitChild),p=ts(e,u,f,t),d=ts(t,0,f,p),m=u?Ir[u]:Br;return u&&es(n,p.props),h&&(Hr(d,m),"immediateRender"in n||(n.immediateRender=!0),n.onComplete=function(){Qr(d),l&&l.apply(this,arguments)}),s&&$r(d,p),n=rs(d,p,a||c,u,c,n.duration||o?n:0),o?n:n.duration?yr.to(d.element,n):null},t.makeAbsolute=function(t,e){return(t instanceof ds?t:new ds(t,e)).makeAbsolute()},t.batch=function(t){return t||(t="default"),Or[t]||(Or[t]=new _s(t))},t.killFlipsOf=function(t,e){(t instanceof ds?t.targets:vr(t)).forEach((function(t){return t&&cs(t._flip,!1!==e?1:2)}))},t.isFlipping=function(e){var i=t.getByTarget(e);return!!i&&i.isActive()},t.getByTarget=function(t){return(Rr(t)||Ar)._flip},t.getElementState=function(t,e){return new ms(Rr(t),e)},t.convertCoordinates=function(t,e,i){var n=_r(e,!0,!0).multiply(_r(t));return i?n.apply(i):n},t.register=function(t){if(wr="undefined"!=typeof document&&document.body){yr=t,sr(wr),vr=yr.utils.toArray;var e=yr.utils.snap(.1);Tr=function(t,i){return e(parseFloat(t)+i)}}},t}();vs.version="3.10.4","undefined"!=typeof window&&window.gsap&&window.gsap.registerPlugin(vs),ir.registerPlugin(vs);var ys={width:window.innerWidth,height:window.innerHeight};window.addEventListener("resize",(function(){return ys={width:window.innerWidth,height:window.innerHeight}}));var bs={grid:document.querySelector(".grid"),enterCtrl:document.querySelector(".content__enter"),backCtrl:document.querySelector(".button-back"),contentItem:document.querySelector(".content__item-img"),gridItemTarget:document.querySelector(".grid__item--target"),gridItemOriginalTarget:document.querySelector(".content__item"),contentTitleTexts:document.querySelectorAll(".content__item-title > span"),gridTitleTexts:document.querySelectorAll(".grid__item--title > span"),gridItems:document.querySelectorAll(".grid > .grid__item:not(.grid__item--target):not(.grid__item--title):not(.grid__item--back)")},xs=1,ws="expo.inOut",Ts=document.body,ks=getComputedStyle(Ts).getPropertyValue("--color-bg"),Cs=!1,Ss=function(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:400,i={x:t.offsetLeft+t.offsetWidth/2,y:t.offsetTop+t.offsetHeight/2},n=Math.atan2(Math.abs(ys.height/2-i.y),Math.abs(ys.width/2-i.x)),r=Math.abs(Math.cos(n)*e),s=Math.abs(Math.sin(n)*e);return{x:i.x<ys.width/2?-1*r:r,y:i.y<ys.height/2?-1*s:s}},Os=function(t){var e=t.offsetLeft+t.offsetWidth/2,i=t.offsetTop+t.offsetHeight/2;return Math.hypot(e-ys.width/2,i-ys.height/2)};bs.enterCtrl.addEventListener("click",(function(){return function(){if(!Cs){Cs=!0;var t=ir.timeline({onComplete:function(){Cs=!1}}).addLabel("start",0).to(bs.enterCtrl,{duration:xs,ease:ws,opacity:0,onComplete:function(){return ir.set(bs.enterCtrl,{pointerEvents:"none"})}},"start").add((function(){bs.grid.classList.add("grid--open");var t=vs.getState(bs.contentItem);bs.gridItemTarget.appendChild(bs.contentItem),vs.from(t,{duration:xs,ease:ws})}),"start"),e=!0,i=!1,n=void 0;try{for(var r,s=bs.gridItems[Symbol.iterator]();!(e=(r=s.next()).done);e=!0){var a=r.value,o=Ss(a),h=o.x,l=o.y,f=u(Os(a),0,1e3,0,.4);t.to(a.querySelector(".oh__inner"),{duration:1.7*xs,ease:ws,startAt:{yPercent:101},yPercent:0,delay:f},"start").set(a,{x:h,y:l,opacity:0},"start").to(a,{duration:xs,ease:"expo",x:0,y:0,delay:f,opacity:1},"start+=0.4")}}catch(t){i=!0,n=t}finally{try{e||null==s.return||s.return()}finally{if(i)throw n}}t.to(bs.gridItemTarget.querySelector(".oh__inner"),{duration:1.7*xs,ease:ws,startAt:{yPercent:101},yPercent:0},"start").to(bs.contentTitleTexts,{duration:xs,ease:ws,yPercent:function(t){return t%2?100:-100},opacity:0},"start").to(bs.gridTitleTexts,{duration:xs,ease:ws,startAt:{xPercent:function(t){return t%2?50:-50},opacity:0},xPercent:0,opacity:1},"start").to(bs.backCtrl,{duration:xs,ease:ws,startAt:{xPercent:40,opacity:0},xPercent:0,opacity:1},"start").to(Ts,{duration:xs,ease:ws,backgroundColor:"#CDD1CD"},"start")}}()})),bs.backCtrl.addEventListener("click",(function(){return function(){if(!Cs){Cs=!0;var t=ir.timeline({onComplete:function(){bs.grid.classList.remove("grid--open"),Cs=!1}}).addLabel("start",0).to(Ts,{duration:xs,ease:ws,backgroundColor:ks},"start").to(bs.gridItemTarget.querySelector(".oh__inner"),{duration:xs,ease:ws,yPercent:101},"start"),e=!0,i=!1,n=void 0;try{for(var r,s=bs.gridItems[Symbol.iterator]();!(e=(r=s.next()).done);e=!0){var a=r.value,o=Ss(a),h=o.x,l=o.y,f=u(Os(a),0,1e3,.4,0);t.to(a,{duration:xs,ease:ws,x:h,y:l,opacity:0,delay:f},"start").to(a.querySelector(".oh__inner"),{duration:.5*xs,ease:ws,yPercent:101,delay:f},"start")}}catch(t){i=!0,n=t}finally{try{e||null==s.return||s.return()}finally{if(i)throw n}}t.to(bs.gridTitleTexts,{duration:xs,ease:ws,xPercent:function(t){return t%2?50:-50},opacity:0},"start").to(bs.backCtrl,{duration:xs,ease:ws,xPercent:20,opacity:0},"start").to(bs.contentTitleTexts,{duration:xs,ease:ws,yPercent:0,opacity:1},"start+=0.4").to(bs.enterCtrl,{duration:xs,ease:ws,opacity:1,onComplete:function(){return ir.set(bs.enterCtrl,{pointerEvents:"auto"})}},"start+=0.4").add((function(){var t=vs.getState(bs.contentItem);bs.gridItemOriginalTarget.appendChild(bs.contentItem),vs.from(t,{duration:xs,ease:ws})}),"start+=0.4")}}()})),function(){var t=arguments.length>0&&void 0!==arguments[0]?arguments[0]:"img";return new Promise((function(e){r(document.querySelectorAll(t),{background:!0},e)}))}(".grid__item-img").then((function(t){return document.body.classList.remove("loading")}))}();
}
];
