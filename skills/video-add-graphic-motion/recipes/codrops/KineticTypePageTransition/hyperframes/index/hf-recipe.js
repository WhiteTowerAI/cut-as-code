/* Generated from the original Codrops entry scripts. */
window.__hfRecipeFactories = [
function (__hf) {
delete globalThis.parcelRequire5b73;
document.documentElement.className="js";var supportsCssVars=function(){var e,t=document.createElement("style");return t.innerHTML="root: { --tmp-var: bold; }",document.head.appendChild(t),e=!!(window.CSS&&window.CSS.supports&&window.CSS.supports("font-weight","var(--tmp-var)")),t.parentNode.removeChild(t),e};supportsCssVars()||alert("Please view this demo in a modern browser that supports CSS Variables.");;
(() => {
  var __defProp = Object.defineProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // index.e8e8a74c.js
  var t = "undefined" != typeof globalThis ? globalThis : "undefined" != typeof self ? self : "undefined" != typeof window ? window : "undefined" != typeof global ? global : {};
  var e = {};
  var i = {};
  var r = t.parcelRequire5b73;
  null == r && ((r = function(t17) {
    if (t17 in e) return e[t17].exports;
    if (t17 in i) {
      var r2 = i[t17];
      delete i[t17];
      var n2 = { id: t17, exports: {} };
      return e[t17] = n2, r2.call(n2.exports, n2, n2.exports), n2.exports;
    }
    var s2 = new Error("Cannot find module '" + t17 + "'");
    throw s2.code = "MODULE_NOT_FOUND", s2;
  }).register = function(t17, e2) {
    i[t17] = e2;
  }, t.parcelRequire5b73 = r);
  var n = {};
  r.register("6lggo", (function(t17, e2) {
    !(function(e3, i2) {
      "function" == typeof define && define.amd ? define(i2) : t17.exports ? t17.exports = i2() : e3.EvEmitter = i2();
    })("undefined" != typeof window ? window : t17.exports, (function() {
      function t18() {
      }
      var e3 = t18.prototype;
      return e3.on = function(t19, e4) {
        if (t19 && e4) {
          var i2 = this._events = this._events || {}, r2 = i2[t19] = i2[t19] || [];
          return -1 == r2.indexOf(e4) && r2.push(e4), this;
        }
      }, e3.once = function(t19, e4) {
        if (t19 && e4) {
          this.on(t19, e4);
          var i2 = this._onceEvents = this._onceEvents || {};
          return (i2[t19] = i2[t19] || {})[e4] = true, this;
        }
      }, e3.off = function(t19, e4) {
        var i2 = this._events && this._events[t19];
        if (i2 && i2.length) {
          var r2 = i2.indexOf(e4);
          return -1 != r2 && i2.splice(r2, 1), this;
        }
      }, e3.emitEvent = function(t19, e4) {
        var i2 = this._events && this._events[t19];
        if (i2 && i2.length) {
          i2 = i2.slice(0), e4 = e4 || [];
          for (var r2 = this._onceEvents && this._onceEvents[t19], n2 = 0; n2 < i2.length; n2++) {
            var s2 = i2[n2];
            r2 && r2[s2] && (this.off(t19, s2), delete r2[s2]), s2.apply(this, e4);
          }
          return this;
        }
      }, e3.allOff = function() {
        delete this._events, delete this._onceEvents;
      }, t18;
    }));
  })), /*!
   * imagesLoaded v4.1.4
   * JavaScript is all like "You images are done yet or what?"
   * MIT License
   */
  (function(t17, e2) {
    "function" == typeof define && define.amd ? define(["ev-emitter/ev-emitter"], (function(i2) {
      return e2(t17, i2);
    })) : n ? n = e2(t17, r("6lggo")) : t17.imagesLoaded = e2(t17, t17.EvEmitter);
  })("undefined" != typeof window ? window : n, (function(t17, e2) {
    var i2 = t17.jQuery, r2 = t17.console;
    function n2(t18, e3) {
      for (var i3 in e3) t18[i3] = e3[i3];
      return t18;
    }
    var s2 = Array.prototype.slice;
    function a2(t18, e3, o3) {
      if (!(this instanceof a2)) return new a2(t18, e3, o3);
      var u3, h3 = t18;
      ("string" == typeof t18 && (h3 = document.querySelectorAll(t18)), h3) ? (this.elements = (u3 = h3, Array.isArray(u3) ? u3 : "object" == typeof u3 && "number" == typeof u3.length ? s2.call(u3) : [u3]), this.options = n2({}, this.options), "function" == typeof e3 ? o3 = e3 : n2(this.options, e3), o3 && this.on("always", o3), this.getImages(), i2 && (this.jqDeferred = new i2.Deferred()), __hf.setTimeout(this.check.bind(this))) : r2.error("Bad element for imagesLoaded " + (h3 || t18));
    }
    a2.prototype = Object.create(e2.prototype), a2.prototype.options = {}, a2.prototype.getImages = function() {
      this.images = [], this.elements.forEach(this.addElementImages, this);
    }, a2.prototype.addElementImages = function(t18) {
      "IMG" == t18.nodeName && this.addImage(t18), true === this.options.background && this.addElementBackgroundImages(t18);
      var e3 = t18.nodeType;
      if (e3 && o2[e3]) {
        for (var i3 = t18.querySelectorAll("img"), r3 = 0; r3 < i3.length; r3++) {
          var n3 = i3[r3];
          this.addImage(n3);
        }
        if ("string" == typeof this.options.background) {
          var s3 = t18.querySelectorAll(this.options.background);
          for (r3 = 0; r3 < s3.length; r3++) {
            var a3 = s3[r3];
            this.addElementBackgroundImages(a3);
          }
        }
      }
    };
    var o2 = { 1: true, 9: true, 11: true };
    function u2(t18) {
      this.img = t18;
    }
    function h2(t18, e3) {
      this.url = t18, this.element = e3, this.img = new Image();
    }
    return a2.prototype.addElementBackgroundImages = function(t18) {
      var e3 = getComputedStyle(t18);
      if (e3) for (var i3 = /url\((['"])?(.*?)\1\)/gi, r3 = i3.exec(e3.backgroundImage); null !== r3; ) {
        var n3 = r3 && r3[2];
        n3 && this.addBackground(n3, t18), r3 = i3.exec(e3.backgroundImage);
      }
    }, a2.prototype.addImage = function(t18) {
      var e3 = new u2(t18);
      this.images.push(e3);
    }, a2.prototype.addBackground = function(t18, e3) {
      var i3 = new h2(t18, e3);
      this.images.push(i3);
    }, a2.prototype.check = function() {
      var t18 = this;
      function e3(e4, i3, r3) {
        __hf.setTimeout((function() {
          t18.progress(e4, i3, r3);
        }));
      }
      this.progressedCount = 0, this.hasAnyBroken = false, this.images.length ? this.images.forEach((function(t19) {
        t19.once("progress", e3), t19.check();
      })) : this.complete();
    }, a2.prototype.progress = function(t18, e3, i3) {
      this.progressedCount++, this.hasAnyBroken = this.hasAnyBroken || !t18.isLoaded, this.emitEvent("progress", [this, t18, e3]), this.jqDeferred && this.jqDeferred.notify && this.jqDeferred.notify(this, t18), this.progressedCount == this.images.length && this.complete(), this.options.debug && r2 && r2.log("progress: " + i3, t18, e3);
    }, a2.prototype.complete = function() {
      var t18 = this.hasAnyBroken ? "fail" : "done";
      if (this.isComplete = true, this.emitEvent(t18, [this]), this.emitEvent("always", [this]), this.jqDeferred) {
        var e3 = this.hasAnyBroken ? "reject" : "resolve";
        this.jqDeferred[e3](this);
      }
    }, u2.prototype = Object.create(e2.prototype), u2.prototype.check = function() {
      this.getIsImageComplete() ? this.confirm(0 !== this.img.naturalWidth, "naturalWidth") : (this.proxyImage = new Image(), this.proxyImage.addEventListener("load", this), this.proxyImage.addEventListener("error", this), this.img.addEventListener("load", this), this.img.addEventListener("error", this), this.proxyImage.src = this.img.src);
    }, u2.prototype.getIsImageComplete = function() {
      return this.img.complete && this.img.naturalWidth;
    }, u2.prototype.confirm = function(t18, e3) {
      this.isLoaded = t18, this.emitEvent("progress", [this, this.img, e3]);
    }, u2.prototype.handleEvent = function(t18) {
      var e3 = "on" + t18.type;
      this[e3] && this[e3](t18);
    }, u2.prototype.onload = function() {
      this.confirm(true, "onload"), this.unbindEvents();
    }, u2.prototype.onerror = function() {
      this.confirm(false, "onerror"), this.unbindEvents();
    }, u2.prototype.unbindEvents = function() {
      this.proxyImage.removeEventListener("load", this), this.proxyImage.removeEventListener("error", this), this.img.removeEventListener("load", this), this.img.removeEventListener("error", this);
    }, h2.prototype = Object.create(u2.prototype), h2.prototype.check = function() {
      this.img.addEventListener("load", this), this.img.addEventListener("error", this), this.img.src = this.url, this.getIsImageComplete() && (this.confirm(0 !== this.img.naturalWidth, "naturalWidth"), this.unbindEvents());
    }, h2.prototype.unbindEvents = function() {
      this.img.removeEventListener("load", this), this.img.removeEventListener("error", this);
    }, h2.prototype.confirm = function(t18, e3) {
      this.isLoaded = t18, this.emitEvent("progress", [this, this.element, e3]);
    }, a2.makeJQueryPlugin = function(e3) {
      (e3 = e3 || t17.jQuery) && ((i2 = e3).fn.imagesLoaded = function(t18, e4) {
        return new a2(this, t18, e4).jqDeferred.promise(i2(this));
      });
    }, a2.makeJQueryPlugin(), a2;
  }));
  function s(t17) {
    if (void 0 === t17) throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
    return t17;
  }
  function a(t17, e2) {
    t17.prototype = Object.create(e2.prototype), t17.prototype.constructor = t17, t17.__proto__ = e2;
  }
  var o;
  var u;
  var h;
  var l;
  var f;
  var c;
  var p;
  var d;
  var _;
  var m;
  var g;
  var v;
  var y;
  var w;
  var b;
  var x;
  var T;
  var O;
  var M;
  var D;
  var k;
  var A;
  var E;
  var C;
  var S;
  var P;
  var I;
  var L;
  var R = { autoSleep: 120, force3D: "auto", nullTargetWarn: 1, units: { lineHeight: "" } };
  var z = { duration: 0.5, overwrite: false, delay: 0 };
  var F = 2 * Math.PI;
  var B = F / 4;
  var q = 0;
  var j = Math.sqrt;
  var N = Math.cos;
  var U = Math.sin;
  var Y = function(t17) {
    return "string" == typeof t17;
  };
  var X = function(t17) {
    return "function" == typeof t17;
  };
  var W = function(t17) {
    return "number" == typeof t17;
  };
  var V = function(t17) {
    return void 0 === t17;
  };
  var Q = function(t17) {
    return "object" == typeof t17;
  };
  var G = function(t17) {
    return false !== t17;
  };
  var H = function() {
    return "undefined" != typeof window;
  };
  var Z = function(t17) {
    return X(t17) || Y(t17);
  };
  var J = "function" == typeof ArrayBuffer && ArrayBuffer.isView || function() {
  };
  var $ = Array.isArray;
  var K = /(?:-?\.?\d|\.)+/gi;
  var tt = /[-+=.]*\d+[.e\-+]*\d*[e\-+]*\d*/g;
  var et = /[-+=.]*\d+[.e-]*\d*[a-z%]*/g;
  var it = /[-+=.]*\d+\.?\d*(?:e-|e\+)?\d*/gi;
  var rt = /[+-]=-?[.\d]+/;
  var nt = /[^,'"\[\]\s]+/gi;
  var st = /[\d.+\-=]+(?:e[-+]\d*)*/i;
  var at = {};
  var ot = {};
  var ut = function(t17) {
    return (ot = It(t17, at)) && vi;
  };
  var ht = function(t17, e2) {
    return console.warn("Invalid property", t17, "set to", e2, "Missing plugin? gsap.registerPlugin()");
  };
  var lt = function(t17, e2) {
    return !e2 && console.warn(t17);
  };
  var ft = function(t17, e2) {
    return t17 && (at[t17] = e2) && ot && (ot[t17] = e2) || at;
  };
  var ct = function() {
    return 0;
  };
  var pt = {};
  var dt = [];
  var _t = {};
  var mt = {};
  var gt = {};
  var vt = 30;
  var yt = [];
  var wt = "";
  var bt = function(t17) {
    var e2, i2, r2 = t17[0];
    if (Q(r2) || X(r2) || (t17 = [t17]), !(e2 = (r2._gsap || {}).harness)) {
      for (i2 = yt.length; i2-- && !yt[i2].targetTest(r2); ) ;
      e2 = yt[i2];
    }
    for (i2 = t17.length; i2--; ) t17[i2] && (t17[i2]._gsap || (t17[i2]._gsap = new Ye(t17[i2], e2))) || t17.splice(i2, 1);
    return t17;
  };
  var xt = function(t17) {
    return t17._gsap || bt(he(t17))[0]._gsap;
  };
  var Tt = function(t17, e2, i2) {
    return (i2 = t17[e2]) && X(i2) ? t17[e2]() : V(i2) && t17.getAttribute && t17.getAttribute(e2) || i2;
  };
  var Ot = function(t17, e2) {
    return (t17 = t17.split(",")).forEach(e2) || t17;
  };
  var Mt = function(t17) {
    return Math.round(1e5 * t17) / 1e5 || 0;
  };
  var Dt = function(t17, e2) {
    for (var i2 = e2.length, r2 = 0; t17.indexOf(e2[r2]) < 0 && ++r2 < i2; ) ;
    return r2 < i2;
  };
  var kt = function() {
    var t17, e2, i2 = dt.length, r2 = dt.slice(0);
    for (_t = {}, dt.length = 0, t17 = 0; t17 < i2; t17++) (e2 = r2[t17]) && e2._lazy && (e2.render(e2._lazy[0], e2._lazy[1], true)._lazy = 0);
  };
  var At = function(t17, e2, i2, r2) {
    dt.length && kt(), t17.render(e2, i2, r2), dt.length && kt();
  };
  var Et = function(t17) {
    var e2 = parseFloat(t17);
    return (e2 || 0 === e2) && (t17 + "").match(nt).length < 2 ? e2 : Y(t17) ? t17.trim() : t17;
  };
  var Ct = function(t17) {
    return t17;
  };
  var St = function(t17, e2) {
    for (var i2 in e2) i2 in t17 || (t17[i2] = e2[i2]);
    return t17;
  };
  var Pt = function(t17, e2) {
    for (var i2 in e2) i2 in t17 || "duration" === i2 || "ease" === i2 || (t17[i2] = e2[i2]);
  };
  var It = function(t17, e2) {
    for (var i2 in e2) t17[i2] = e2[i2];
    return t17;
  };
  var Lt = function t2(e2, i2) {
    for (var r2 in i2) "__proto__" !== r2 && "constructor" !== r2 && "prototype" !== r2 && (e2[r2] = Q(i2[r2]) ? t2(e2[r2] || (e2[r2] = {}), i2[r2]) : i2[r2]);
    return e2;
  };
  var Rt = function(t17, e2) {
    var i2, r2 = {};
    for (i2 in t17) i2 in e2 || (r2[i2] = t17[i2]);
    return r2;
  };
  var zt = function(t17) {
    var e2 = t17.parent || u, i2 = t17.keyframes ? Pt : St;
    if (G(t17.inherit)) for (; e2; ) i2(t17, e2.vars.defaults), e2 = e2.parent || e2._dp;
    return t17;
  };
  var Ft = function(t17, e2, i2, r2) {
    void 0 === i2 && (i2 = "_first"), void 0 === r2 && (r2 = "_last");
    var n2 = e2._prev, s2 = e2._next;
    n2 ? n2._next = s2 : t17[i2] === e2 && (t17[i2] = s2), s2 ? s2._prev = n2 : t17[r2] === e2 && (t17[r2] = n2), e2._next = e2._prev = e2.parent = null;
  };
  var Bt = function(t17, e2) {
    t17.parent && (!e2 || t17.parent.autoRemoveChildren) && t17.parent.remove(t17), t17._act = 0;
  };
  var qt = function(t17, e2) {
    if (t17 && (!e2 || e2._end > t17._dur || e2._start < 0)) for (var i2 = t17; i2; ) i2._dirty = 1, i2 = i2.parent;
    return t17;
  };
  var jt = function(t17) {
    for (var e2 = t17.parent; e2 && e2.parent; ) e2._dirty = 1, e2.totalDuration(), e2 = e2.parent;
    return t17;
  };
  var Nt = function t3(e2) {
    return !e2 || e2._ts && t3(e2.parent);
  };
  var Ut = function(t17) {
    return t17._repeat ? Yt(t17._tTime, t17 = t17.duration() + t17._rDelay) * t17 : 0;
  };
  var Yt = function(t17, e2) {
    var i2 = Math.floor(t17 /= e2);
    return t17 && i2 === t17 ? i2 - 1 : i2;
  };
  var Xt = function(t17, e2) {
    return (t17 - e2._start) * e2._ts + (e2._ts >= 0 ? 0 : e2._dirty ? e2.totalDuration() : e2._tDur);
  };
  var Wt = function(t17) {
    return t17._end = Mt(t17._start + (t17._tDur / Math.abs(t17._ts || t17._rts || 1e-8) || 0));
  };
  var Vt = function(t17, e2) {
    var i2 = t17._dp;
    return i2 && i2.smoothChildTiming && t17._ts && (t17._start = Mt(i2._time - (t17._ts > 0 ? e2 / t17._ts : ((t17._dirty ? t17.totalDuration() : t17._tDur) - e2) / -t17._ts)), Wt(t17), i2._dirty || qt(i2, t17)), t17;
  };
  var Qt = function(t17, e2) {
    var i2;
    if ((e2._time || e2._initted && !e2._dur) && (i2 = Xt(t17.rawTime(), e2), (!e2._dur || se(0, e2.totalDuration(), i2) - e2._tTime > 1e-8) && e2.render(i2, true)), qt(t17, e2)._dp && t17._initted && t17._time >= t17._dur && t17._ts) {
      if (t17._dur < t17.duration()) for (i2 = t17; i2._dp; ) i2.rawTime() >= 0 && i2.totalTime(i2._tTime), i2 = i2._dp;
      t17._zTime = -1e-8;
    }
  };
  var Gt = function(t17, e2, i2, r2) {
    return e2.parent && Bt(e2), e2._start = Mt((W(i2) ? i2 : i2 || t17 !== u ? ie(t17, i2, e2) : t17._time) + e2._delay), e2._end = Mt(e2._start + (e2.totalDuration() / Math.abs(e2.timeScale()) || 0)), (function(t18, e3, i3, r3, n2) {
      void 0 === i3 && (i3 = "_first"), void 0 === r3 && (r3 = "_last");
      var s2, a2 = t18[r3];
      if (n2) for (s2 = e3[n2]; a2 && a2[n2] > s2; ) a2 = a2._prev;
      a2 ? (e3._next = a2._next, a2._next = e3) : (e3._next = t18[i3], t18[i3] = e3), e3._next ? e3._next._prev = e3 : t18[r3] = e3, e3._prev = a2, e3.parent = e3._dp = t18;
    })(t17, e2, "_first", "_last", t17._sort ? "_start" : 0), $t(e2) || (t17._recent = e2), r2 || Qt(t17, e2), t17;
  };
  var Ht = function(t17, e2) {
    return (at.ScrollTrigger || ht("scrollTrigger", e2)) && at.ScrollTrigger.create(e2, t17);
  };
  var Zt = function(t17, e2, i2, r2) {
    return Ze(t17, e2), t17._initted ? !i2 && t17._pt && (t17._dur && false !== t17.vars.lazy || !t17._dur && t17.vars.lazy) && p !== Ce.frame ? (dt.push(t17), t17._lazy = [e2, r2], 1) : void 0 : 1;
  };
  var Jt = function t4(e2) {
    var i2 = e2.parent;
    return i2 && i2._ts && i2._initted && !i2._lock && (i2.rawTime() < 0 || t4(i2));
  };
  var $t = function(t17) {
    var e2 = t17.data;
    return "isFromStart" === e2 || "isStart" === e2;
  };
  var Kt = function(t17, e2, i2, r2) {
    var n2 = t17._repeat, s2 = Mt(e2) || 0, a2 = t17._tTime / t17._tDur;
    return a2 && !r2 && (t17._time *= s2 / t17._dur), t17._dur = s2, t17._tDur = n2 ? n2 < 0 ? 1e10 : Mt(s2 * (n2 + 1) + t17._rDelay * n2) : s2, a2 && !r2 ? Vt(t17, t17._tTime = t17._tDur * a2) : t17.parent && Wt(t17), i2 || qt(t17.parent, t17), t17;
  };
  var te = function(t17) {
    return t17 instanceof We ? qt(t17) : Kt(t17, t17._dur);
  };
  var ee = { _start: 0, endTime: ct, totalDuration: ct };
  var ie = function t5(e2, i2, r2) {
    var n2, s2, a2, o2 = e2.labels, u2 = e2._recent || ee, h2 = e2.duration() >= 1e8 ? u2.endTime(false) : e2._dur;
    return Y(i2) && (isNaN(i2) || i2 in o2) ? (s2 = i2.charAt(0), a2 = "%" === i2.substr(-1), n2 = i2.indexOf("="), "<" === s2 || ">" === s2 ? (n2 >= 0 && (i2 = i2.replace(/=/, "")), ("<" === s2 ? u2._start : u2.endTime(u2._repeat >= 0)) + (parseFloat(i2.substr(1)) || 0) * (a2 ? (n2 < 0 ? u2 : r2).totalDuration() / 100 : 1)) : n2 < 0 ? (i2 in o2 || (o2[i2] = h2), o2[i2]) : (s2 = parseFloat(i2.charAt(n2 - 1) + i2.substr(n2 + 1)), a2 && r2 && (s2 = s2 / 100 * ($(r2) ? r2[0] : r2).totalDuration()), n2 > 1 ? t5(e2, i2.substr(0, n2 - 1), r2) + s2 : h2 + s2)) : null == i2 ? h2 : +i2;
  };
  var re = function(t17, e2, i2) {
    var r2, n2, s2 = W(e2[1]), a2 = (s2 ? 2 : 1) + (t17 < 2 ? 0 : 1), o2 = e2[a2];
    if (s2 && (o2.duration = e2[1]), o2.parent = i2, t17) {
      for (r2 = o2, n2 = i2; n2 && !("immediateRender" in r2); ) r2 = n2.vars.defaults || {}, n2 = G(n2.vars.inherit) && n2.parent;
      o2.immediateRender = G(r2.immediateRender), t17 < 2 ? o2.runBackwards = 1 : o2.startAt = e2[a2 - 1];
    }
    return new ti(e2[0], o2, e2[a2 + 1]);
  };
  var ne = function(t17, e2) {
    return t17 || 0 === t17 ? e2(t17) : e2;
  };
  var se = function(t17, e2, i2) {
    return i2 < t17 ? t17 : i2 > e2 ? e2 : i2;
  };
  var ae = function(t17) {
    if ("string" != typeof t17) return "";
    var e2 = st.exec(t17);
    return e2 ? t17.substr(e2.index + e2[0].length) : "";
  };
  var oe = [].slice;
  var ue = function(t17, e2) {
    return t17 && Q(t17) && "length" in t17 && (!e2 && !t17.length || t17.length - 1 in t17 && Q(t17[0])) && !t17.nodeType && t17 !== h;
  };
  var he = function(t17, e2, i2) {
    return !Y(t17) || i2 || !l && Se() ? $(t17) ? (function(t18, e3, i3) {
      return void 0 === i3 && (i3 = []), t18.forEach((function(t19) {
        var r2;
        return Y(t19) && !e3 || ue(t19, 1) ? (r2 = i3).push.apply(r2, he(t19)) : i3.push(t19);
      })) || i3;
    })(t17, i2) : ue(t17) ? oe.call(t17, 0) : t17 ? [t17] : [] : oe.call((e2 || f).querySelectorAll(t17), 0);
  };
  var le = function(t17) {
    return t17.sort((function() {
      return 0.5 - __hf.random();
    }));
  };
  var fe = function(t17) {
    if (X(t17)) return t17;
    var e2 = Q(t17) ? t17 : { each: t17 }, i2 = Be(e2.ease), r2 = e2.from || 0, n2 = parseFloat(e2.base) || 0, s2 = {}, a2 = r2 > 0 && r2 < 1, o2 = isNaN(r2) || a2, u2 = e2.axis, h2 = r2, l2 = r2;
    return Y(r2) ? h2 = l2 = { center: 0.5, edges: 0.5, end: 1 }[r2] || 0 : !a2 && o2 && (h2 = r2[0], l2 = r2[1]), function(t18, a3, f2) {
      var c2, p2, d2, _2, m2, g2, v2, y2, w2, b2 = (f2 || e2).length, x2 = s2[b2];
      if (!x2) {
        if (!(w2 = "auto" === e2.grid ? 0 : (e2.grid || [1, 1e8])[1])) {
          for (v2 = -1e8; v2 < (v2 = f2[w2++].getBoundingClientRect().left) && w2 < b2; ) ;
          w2--;
        }
        for (x2 = s2[b2] = [], c2 = o2 ? Math.min(w2, b2) * h2 - 0.5 : r2 % w2, p2 = o2 ? b2 * l2 / w2 - 0.5 : r2 / w2 | 0, v2 = 0, y2 = 1e8, g2 = 0; g2 < b2; g2++) d2 = g2 % w2 - c2, _2 = p2 - (g2 / w2 | 0), x2[g2] = m2 = u2 ? Math.abs("y" === u2 ? _2 : d2) : j(d2 * d2 + _2 * _2), m2 > v2 && (v2 = m2), m2 < y2 && (y2 = m2);
        "random" === r2 && le(x2), x2.max = v2 - y2, x2.min = y2, x2.v = b2 = (parseFloat(e2.amount) || parseFloat(e2.each) * (w2 > b2 ? b2 - 1 : u2 ? "y" === u2 ? b2 / w2 : w2 : Math.max(w2, b2 / w2)) || 0) * ("edges" === r2 ? -1 : 1), x2.b = b2 < 0 ? n2 - b2 : n2, x2.u = ae(e2.amount || e2.each) || 0, i2 = i2 && b2 < 0 ? ze(i2) : i2;
      }
      return b2 = (x2[t18] - x2.min) / x2.max || 0, Mt(x2.b + (i2 ? i2(b2) : b2) * x2.v) + x2.u;
    };
  };
  var ce = function(t17) {
    var e2 = t17 < 1 ? Math.pow(10, (t17 + "").length - 2) : 1;
    return function(i2) {
      var r2 = Math.round(parseFloat(i2) / t17) * t17 * e2;
      return (r2 - r2 % 1) / e2 + (W(i2) ? 0 : ae(i2));
    };
  };
  var pe = function(t17, e2) {
    var i2, r2, n2 = $(t17);
    return !n2 && Q(t17) && (i2 = n2 = t17.radius || 1e8, t17.values ? (t17 = he(t17.values), (r2 = !W(t17[0])) && (i2 *= i2)) : t17 = ce(t17.increment)), ne(e2, n2 ? X(t17) ? function(e3) {
      return r2 = t17(e3), Math.abs(r2 - e3) <= i2 ? r2 : e3;
    } : function(e3) {
      for (var n3, s2, a2 = parseFloat(r2 ? e3.x : e3), o2 = parseFloat(r2 ? e3.y : 0), u2 = 1e8, h2 = 0, l2 = t17.length; l2--; ) (n3 = r2 ? (n3 = t17[l2].x - a2) * n3 + (s2 = t17[l2].y - o2) * s2 : Math.abs(t17[l2] - a2)) < u2 && (u2 = n3, h2 = l2);
      return h2 = !i2 || u2 <= i2 ? t17[h2] : e3, r2 || h2 === e3 || W(e3) ? h2 : h2 + ae(e3);
    } : ce(t17));
  };
  var de = function(t17, e2, i2, r2) {
    return ne($(t17) ? !e2 : true === i2 ? (i2 = 0, false) : !r2, (function() {
      return $(t17) ? t17[~~(__hf.random() * t17.length)] : (r2 = (i2 = i2 || 1e-5) < 1 ? Math.pow(10, (i2 + "").length - 2) : 1) && Math.floor(Math.round((t17 - i2 / 2 + __hf.random() * (e2 - t17 + 0.99 * i2)) / i2) * i2 * r2) / r2;
    }));
  };
  var _e = function(t17, e2, i2) {
    return ne(i2, (function(i3) {
      return t17[~~e2(i3)];
    }));
  };
  var me = function(t17) {
    for (var e2, i2, r2, n2, s2 = 0, a2 = ""; ~(e2 = t17.indexOf("random(", s2)); ) r2 = t17.indexOf(")", e2), n2 = "[" === t17.charAt(e2 + 7), i2 = t17.substr(e2 + 7, r2 - e2 - 7).match(n2 ? nt : K), a2 += t17.substr(s2, e2 - s2) + de(n2 ? i2 : +i2[0], n2 ? 0 : +i2[1], +i2[2] || 1e-5), s2 = r2 + 1;
    return a2 + t17.substr(s2, t17.length - s2);
  };
  var ge = function(t17, e2, i2, r2, n2) {
    var s2 = e2 - t17, a2 = r2 - i2;
    return ne(n2, (function(e3) {
      return i2 + ((e3 - t17) / s2 * a2 || 0);
    }));
  };
  var ve = function(t17, e2, i2) {
    var r2, n2, s2, a2 = t17.labels, o2 = 1e8;
    for (r2 in a2) (n2 = a2[r2] - e2) < 0 == !!i2 && n2 && o2 > (n2 = Math.abs(n2)) && (s2 = r2, o2 = n2);
    return s2;
  };
  var ye = function(t17, e2, i2) {
    var r2, n2, s2 = t17.vars, a2 = s2[e2];
    if (a2) return r2 = s2[e2 + "Params"], n2 = s2.callbackScope || t17, i2 && dt.length && kt(), r2 ? a2.apply(n2, r2) : a2.call(n2);
  };
  var we = function(t17) {
    return Bt(t17), t17.scrollTrigger && t17.scrollTrigger.kill(false), t17.progress() < 1 && ye(t17, "onInterrupt"), t17;
  };
  var be = function(t17) {
    var e2 = (t17 = !t17.name && t17.default || t17).name, i2 = X(t17), r2 = e2 && !i2 && t17.init ? function() {
      this._props = [];
    } : t17, n2 = { init: ct, render: hi, add: Ge, kill: fi, modifier: li, rawVars: 0 }, s2 = { targetTest: 0, get: 0, getSetter: si, aliases: {}, register: 0 };
    if (Se(), t17 !== r2) {
      if (mt[e2]) return;
      St(r2, St(Rt(t17, n2), s2)), It(r2.prototype, It(n2, Rt(t17, s2))), mt[r2.prop = e2] = r2, t17.targetTest && (yt.push(r2), pt[e2] = 1), e2 = ("css" === e2 ? "CSS" : e2.charAt(0).toUpperCase() + e2.substr(1)) + "Plugin";
    }
    ft(e2, r2), t17.register && t17.register(vi, r2, di);
  };
  var xe = { aqua: [0, 255, 255], lime: [0, 255, 0], silver: [192, 192, 192], black: [0, 0, 0], maroon: [128, 0, 0], teal: [0, 128, 128], blue: [0, 0, 255], navy: [0, 0, 128], white: [255, 255, 255], olive: [128, 128, 0], yellow: [255, 255, 0], orange: [255, 165, 0], gray: [128, 128, 128], purple: [128, 0, 128], green: [0, 128, 0], red: [255, 0, 0], pink: [255, 192, 203], cyan: [0, 255, 255], transparent: [255, 255, 255, 0] };
  var Te = function(t17, e2, i2) {
    return 255 * (6 * (t17 = t17 < 0 ? t17 + 1 : t17 > 1 ? t17 - 1 : t17) < 1 ? e2 + (i2 - e2) * t17 * 6 : t17 < 0.5 ? i2 : 3 * t17 < 2 ? e2 + (i2 - e2) * (2 / 3 - t17) * 6 : e2) + 0.5 | 0;
  };
  var Oe = function(t17, e2, i2) {
    var r2, n2, s2, a2, o2, u2, h2, l2, f2, c2, p2 = t17 ? W(t17) ? [t17 >> 16, t17 >> 8 & 255, 255 & t17] : 0 : xe.black;
    if (!p2) {
      if ("," === t17.substr(-1) && (t17 = t17.substr(0, t17.length - 1)), xe[t17]) p2 = xe[t17];
      else if ("#" === t17.charAt(0)) {
        if (t17.length < 6 && (r2 = t17.charAt(1), n2 = t17.charAt(2), s2 = t17.charAt(3), t17 = "#" + r2 + r2 + n2 + n2 + s2 + s2 + (5 === t17.length ? t17.charAt(4) + t17.charAt(4) : "")), 9 === t17.length) return [(p2 = parseInt(t17.substr(1, 6), 16)) >> 16, p2 >> 8 & 255, 255 & p2, parseInt(t17.substr(7), 16) / 255];
        p2 = [(t17 = parseInt(t17.substr(1), 16)) >> 16, t17 >> 8 & 255, 255 & t17];
      } else if ("hsl" === t17.substr(0, 3)) if (p2 = c2 = t17.match(K), e2) {
        if (~t17.indexOf("=")) return p2 = t17.match(tt), i2 && p2.length < 4 && (p2[3] = 1), p2;
      } else a2 = +p2[0] % 360 / 360, o2 = +p2[1] / 100, r2 = 2 * (u2 = +p2[2] / 100) - (n2 = u2 <= 0.5 ? u2 * (o2 + 1) : u2 + o2 - u2 * o2), p2.length > 3 && (p2[3] *= 1), p2[0] = Te(a2 + 1 / 3, r2, n2), p2[1] = Te(a2, r2, n2), p2[2] = Te(a2 - 1 / 3, r2, n2);
      else p2 = t17.match(K) || xe.transparent;
      p2 = p2.map(Number);
    }
    return e2 && !c2 && (r2 = p2[0] / 255, n2 = p2[1] / 255, s2 = p2[2] / 255, u2 = ((h2 = Math.max(r2, n2, s2)) + (l2 = Math.min(r2, n2, s2))) / 2, h2 === l2 ? a2 = o2 = 0 : (f2 = h2 - l2, o2 = u2 > 0.5 ? f2 / (2 - h2 - l2) : f2 / (h2 + l2), a2 = h2 === r2 ? (n2 - s2) / f2 + (n2 < s2 ? 6 : 0) : h2 === n2 ? (s2 - r2) / f2 + 2 : (r2 - n2) / f2 + 4, a2 *= 60), p2[0] = ~~(a2 + 0.5), p2[1] = ~~(100 * o2 + 0.5), p2[2] = ~~(100 * u2 + 0.5)), i2 && p2.length < 4 && (p2[3] = 1), p2;
  };
  var Me = function(t17) {
    var e2 = [], i2 = [], r2 = -1;
    return t17.split(ke).forEach((function(t18) {
      var n2 = t18.match(et) || [];
      e2.push.apply(e2, n2), i2.push(r2 += n2.length + 1);
    })), e2.c = i2, e2;
  };
  var De = function(t17, e2, i2) {
    var r2, n2, s2, a2, o2 = "", u2 = (t17 + o2).match(ke), h2 = e2 ? "hsla(" : "rgba(", l2 = 0;
    if (!u2) return t17;
    if (u2 = u2.map((function(t18) {
      return (t18 = Oe(t18, e2, 1)) && h2 + (e2 ? t18[0] + "," + t18[1] + "%," + t18[2] + "%," + t18[3] : t18.join(",")) + ")";
    })), i2 && (s2 = Me(t17), (r2 = i2.c).join(o2) !== s2.c.join(o2))) for (a2 = (n2 = t17.replace(ke, "1").split(et)).length - 1; l2 < a2; l2++) o2 += n2[l2] + (~r2.indexOf(l2) ? u2.shift() || h2 + "0,0,0,0)" : (s2.length ? s2 : u2.length ? u2 : i2).shift());
    if (!n2) for (a2 = (n2 = t17.split(ke)).length - 1; l2 < a2; l2++) o2 += n2[l2] + u2[l2];
    return o2 + n2[a2];
  };
  var ke = (function() {
    var t17, e2 = "(?:\\b(?:(?:rgb|rgba|hsl|hsla)\\(.+?\\))|\\B#(?:[0-9a-f]{3,4}){1,2}\\b";
    for (t17 in xe) e2 += "|" + t17 + "\\b";
    return new RegExp(e2 + ")", "gi");
  })();
  var Ae = /hsl[a]?\(/;
  var Ee = function(t17) {
    var e2, i2 = t17.join(" ");
    if (ke.lastIndex = 0, ke.test(i2)) return e2 = Ae.test(i2), t17[1] = De(t17[1], e2), t17[0] = De(t17[0], e2, Me(t17[1])), true;
  };
  var Ce = (x = Date.now, T = 500, O = 33, M = x(), D = M, A = k = 1e3 / 240, C = function t6(e2) {
    var i2, r2, n2, s2, a2 = x() - D, o2 = true === e2;
    if (a2 > T && (M += a2 - O), ((i2 = (n2 = (D += a2) - M) - A) > 0 || o2) && (s2 = ++y.frame, w = n2 - 1e3 * y.time, y.time = n2 /= 1e3, A += i2 + (i2 >= k ? 4 : k - i2), r2 = 1), o2 || (m = g(t6)), r2) for (b = 0; b < E.length; b++) E[b](n2, w, s2, e2);
  }, y = { time: 0, frame: 0, tick: function() {
    C(true);
  }, deltaRatio: function(t17) {
    return w / (1e3 / (t17 || 60));
  }, wake: function() {
    c && (!l && H() && (h = l = window, f = h.document || {}, at.gsap = vi, (h.gsapVersions || (h.gsapVersions = [])).push(vi.version), ut(ot || h.GreenSockGlobals || !h.gsap && h || {}), v = h.requestAnimationFrame), m && y.sleep(), g = v || function(t17) {
      return __hf.setTimeout(t17, A - 1e3 * y.time + 1 | 0);
    }, _ = 1, C(2));
  }, sleep: function() {
    (v ? h.cancelAnimationFrame : clearTimeout)(m), _ = 0, g = ct;
  }, lagSmoothing: function(t17, e2) {
    T = t17 || 1 / 1e-8, O = Math.min(e2, T, 0);
  }, fps: function(t17) {
    k = 1e3 / (t17 || 240), A = 1e3 * y.time + k;
  }, add: function(t17) {
    E.indexOf(t17) < 0 && E.push(t17), Se();
  }, remove: function(t17) {
    var e2;
    ~(e2 = E.indexOf(t17)) && E.splice(e2, 1) && b >= e2 && b--;
  }, _listeners: E = [] });
  var Se = function() {
    return !_ && Ce.wake();
  };
  var Pe = {};
  var Ie = /^[\d.\-M][\d.\-,\s]/;
  var Le = /["']/g;
  var Re = function(t17) {
    for (var e2, i2, r2, n2 = {}, s2 = t17.substr(1, t17.length - 3).split(":"), a2 = s2[0], o2 = 1, u2 = s2.length; o2 < u2; o2++) i2 = s2[o2], e2 = o2 !== u2 - 1 ? i2.lastIndexOf(",") : i2.length, r2 = i2.substr(0, e2), n2[a2] = isNaN(r2) ? r2.replace(Le, "").trim() : +r2, a2 = i2.substr(e2 + 1).trim();
    return n2;
  };
  var ze = function(t17) {
    return function(e2) {
      return 1 - t17(1 - e2);
    };
  };
  var Fe = function t7(e2, i2) {
    for (var r2, n2 = e2._first; n2; ) n2 instanceof We ? t7(n2, i2) : !n2.vars.yoyoEase || n2._yoyo && n2._repeat || n2._yoyo === i2 || (n2.timeline ? t7(n2.timeline, i2) : (r2 = n2._ease, n2._ease = n2._yEase, n2._yEase = r2, n2._yoyo = i2)), n2 = n2._next;
  };
  var Be = function(t17, e2) {
    return t17 && (X(t17) ? t17 : Pe[t17] || (function(t18) {
      var e3, i2, r2, n2, s2 = (t18 + "").split("("), a2 = Pe[s2[0]];
      return a2 && s2.length > 1 && a2.config ? a2.config.apply(null, ~t18.indexOf("{") ? [Re(s2[1])] : (e3 = t18, i2 = e3.indexOf("(") + 1, r2 = e3.indexOf(")"), n2 = e3.indexOf("(", i2), e3.substring(i2, ~n2 && n2 < r2 ? e3.indexOf(")", r2 + 1) : r2)).split(",").map(Et)) : Pe._CE && Ie.test(t18) ? Pe._CE("", t18) : a2;
    })(t17)) || e2;
  };
  var qe = function(t17, e2, i2, r2) {
    void 0 === i2 && (i2 = function(t18) {
      return 1 - e2(1 - t18);
    }), void 0 === r2 && (r2 = function(t18) {
      return t18 < 0.5 ? e2(2 * t18) / 2 : 1 - e2(2 * (1 - t18)) / 2;
    });
    var n2, s2 = { easeIn: e2, easeOut: i2, easeInOut: r2 };
    return Ot(t17, (function(t18) {
      for (var e3 in Pe[t18] = at[t18] = s2, Pe[n2 = t18.toLowerCase()] = i2, s2) Pe[n2 + ("easeIn" === e3 ? ".in" : "easeOut" === e3 ? ".out" : ".inOut")] = Pe[t18 + "." + e3] = s2[e3];
    })), s2;
  };
  var je = function(t17) {
    return function(e2) {
      return e2 < 0.5 ? (1 - t17(1 - 2 * e2)) / 2 : 0.5 + t17(2 * (e2 - 0.5)) / 2;
    };
  };
  var Ne = function t8(e2, i2, r2) {
    var n2 = i2 >= 1 ? i2 : 1, s2 = (r2 || (e2 ? 0.3 : 0.45)) / (i2 < 1 ? i2 : 1), a2 = s2 / F * (Math.asin(1 / n2) || 0), o2 = function(t17) {
      return 1 === t17 ? 1 : n2 * Math.pow(2, -10 * t17) * U((t17 - a2) * s2) + 1;
    }, u2 = "out" === e2 ? o2 : "in" === e2 ? function(t17) {
      return 1 - o2(1 - t17);
    } : je(o2);
    return s2 = F / s2, u2.config = function(i3, r3) {
      return t8(e2, i3, r3);
    }, u2;
  };
  var Ue = function t9(e2, i2) {
    void 0 === i2 && (i2 = 1.70158);
    var r2 = function(t17) {
      return t17 ? --t17 * t17 * ((i2 + 1) * t17 + i2) + 1 : 0;
    }, n2 = "out" === e2 ? r2 : "in" === e2 ? function(t17) {
      return 1 - r2(1 - t17);
    } : je(r2);
    return n2.config = function(i3) {
      return t9(e2, i3);
    }, n2;
  };
  Ot("Linear,Quad,Cubic,Quart,Quint,Strong", (function(t17, e2) {
    var i2 = e2 < 5 ? e2 + 1 : e2;
    qe(t17 + ",Power" + (i2 - 1), e2 ? function(t18) {
      return Math.pow(t18, i2);
    } : function(t18) {
      return t18;
    }, (function(t18) {
      return 1 - Math.pow(1 - t18, i2);
    }), (function(t18) {
      return t18 < 0.5 ? Math.pow(2 * t18, i2) / 2 : 1 - Math.pow(2 * (1 - t18), i2) / 2;
    }));
  })), Pe.Linear.easeNone = Pe.none = Pe.Linear.easeIn, qe("Elastic", Ne("in"), Ne("out"), Ne()), S = 7.5625, I = 1 / (P = 2.75), qe("Bounce", (function(t17) {
    return 1 - L(1 - t17);
  }), L = function(t17) {
    return t17 < I ? S * t17 * t17 : t17 < 0.7272727272727273 ? S * Math.pow(t17 - 1.5 / P, 2) + 0.75 : t17 < 0.9090909090909092 ? S * (t17 -= 2.25 / P) * t17 + 0.9375 : S * Math.pow(t17 - 2.625 / P, 2) + 0.984375;
  }), qe("Expo", (function(t17) {
    return t17 ? Math.pow(2, 10 * (t17 - 1)) : 0;
  })), qe("Circ", (function(t17) {
    return -(j(1 - t17 * t17) - 1);
  })), qe("Sine", (function(t17) {
    return 1 === t17 ? 1 : 1 - N(t17 * B);
  })), qe("Back", Ue("in"), Ue("out"), Ue()), Pe.SteppedEase = Pe.steps = at.SteppedEase = { config: function(t17, e2) {
    void 0 === t17 && (t17 = 1);
    var i2 = 1 / t17, r2 = t17 + (e2 ? 0 : 1), n2 = e2 ? 1 : 0;
    return function(t18) {
      return ((r2 * se(0, 0.99999999, t18) | 0) + n2) * i2;
    };
  } }, z.ease = Pe["quad.out"], Ot("onComplete,onUpdate,onStart,onRepeat,onReverseComplete,onInterrupt", (function(t17) {
    return wt += t17 + "," + t17 + "Params,";
  }));
  var Ye = function(t17, e2) {
    this.id = q++, t17._gsap = this, this.target = t17, this.harness = e2, this.get = e2 ? e2.get : Tt, this.set = e2 ? e2.getSetter : si;
  };
  var Xe = (function() {
    function t17(t18) {
      this.vars = t18, this._delay = +t18.delay || 0, (this._repeat = t18.repeat === 1 / 0 ? -2 : t18.repeat || 0) && (this._rDelay = t18.repeatDelay || 0, this._yoyo = !!t18.yoyo || !!t18.yoyoEase), this._ts = 1, Kt(this, +t18.duration, 1, 1), this.data = t18.data, _ || Ce.wake();
    }
    var e2 = t17.prototype;
    return e2.delay = function(t18) {
      return t18 || 0 === t18 ? (this.parent && this.parent.smoothChildTiming && this.startTime(this._start + t18 - this._delay), this._delay = t18, this) : this._delay;
    }, e2.duration = function(t18) {
      return arguments.length ? this.totalDuration(this._repeat > 0 ? t18 + (t18 + this._rDelay) * this._repeat : t18) : this.totalDuration() && this._dur;
    }, e2.totalDuration = function(t18) {
      return arguments.length ? (this._dirty = 0, Kt(this, this._repeat < 0 ? t18 : (t18 - this._repeat * this._rDelay) / (this._repeat + 1))) : this._tDur;
    }, e2.totalTime = function(t18, e3) {
      if (Se(), !arguments.length) return this._tTime;
      var i2 = this._dp;
      if (i2 && i2.smoothChildTiming && this._ts) {
        for (Vt(this, t18), !i2._dp || i2.parent || Qt(i2, this); i2.parent; ) i2.parent._time !== i2._start + (i2._ts >= 0 ? i2._tTime / i2._ts : (i2.totalDuration() - i2._tTime) / -i2._ts) && i2.totalTime(i2._tTime, true), i2 = i2.parent;
        !this.parent && this._dp.autoRemoveChildren && (this._ts > 0 && t18 < this._tDur || this._ts < 0 && t18 > 0 || !this._tDur && !t18) && Gt(this._dp, this, this._start - this._delay);
      }
      return (this._tTime !== t18 || !this._dur && !e3 || this._initted && 1e-8 === Math.abs(this._zTime) || !t18 && !this._initted && (this.add || this._ptLookup)) && (this._ts || (this._pTime = t18), At(this, t18, e3)), this;
    }, e2.time = function(t18, e3) {
      return arguments.length ? this.totalTime(Math.min(this.totalDuration(), t18 + Ut(this)) % (this._dur + this._rDelay) || (t18 ? this._dur : 0), e3) : this._time;
    }, e2.totalProgress = function(t18, e3) {
      return arguments.length ? this.totalTime(this.totalDuration() * t18, e3) : this.totalDuration() ? Math.min(1, this._tTime / this._tDur) : this.ratio;
    }, e2.progress = function(t18, e3) {
      return arguments.length ? this.totalTime(this.duration() * (!this._yoyo || 1 & this.iteration() ? t18 : 1 - t18) + Ut(this), e3) : this.duration() ? Math.min(1, this._time / this._dur) : this.ratio;
    }, e2.iteration = function(t18, e3) {
      var i2 = this.duration() + this._rDelay;
      return arguments.length ? this.totalTime(this._time + (t18 - 1) * i2, e3) : this._repeat ? Yt(this._tTime, i2) + 1 : 1;
    }, e2.timeScale = function(t18) {
      if (!arguments.length) return -1e-8 === this._rts ? 0 : this._rts;
      if (this._rts === t18) return this;
      var e3 = this.parent && this._ts ? Xt(this.parent._time, this) : this._tTime;
      return this._rts = +t18 || 0, this._ts = this._ps || -1e-8 === t18 ? 0 : this._rts, jt(this.totalTime(se(-this._delay, this._tDur, e3), true));
    }, e2.paused = function(t18) {
      return arguments.length ? (this._ps !== t18 && (this._ps = t18, t18 ? (this._pTime = this._tTime || Math.max(-this._delay, this.rawTime()), this._ts = this._act = 0) : (Se(), this._ts = this._rts, this.totalTime(this.parent && !this.parent.smoothChildTiming ? this.rawTime() : this._tTime || this._pTime, 1 === this.progress() && 1e-8 !== Math.abs(this._zTime) && (this._tTime -= 1e-8)))), this) : this._ps;
    }, e2.startTime = function(t18) {
      if (arguments.length) {
        this._start = t18;
        var e3 = this.parent || this._dp;
        return e3 && (e3._sort || !this.parent) && Gt(e3, this, t18 - this._delay), this;
      }
      return this._start;
    }, e2.endTime = function(t18) {
      return this._start + (G(t18) ? this.totalDuration() : this.duration()) / Math.abs(this._ts);
    }, e2.rawTime = function(t18) {
      var e3 = this.parent || this._dp;
      return e3 ? t18 && (!this._ts || this._repeat && this._time && this.totalProgress() < 1) ? this._tTime % (this._dur + this._rDelay) : this._ts ? Xt(e3.rawTime(t18), this) : this._tTime : this._tTime;
    }, e2.globalTime = function(t18) {
      for (var e3 = this, i2 = arguments.length ? t18 : e3.rawTime(); e3; ) i2 = e3._start + i2 / (e3._ts || 1), e3 = e3._dp;
      return i2;
    }, e2.repeat = function(t18) {
      return arguments.length ? (this._repeat = t18 === 1 / 0 ? -2 : t18, te(this)) : -2 === this._repeat ? 1 / 0 : this._repeat;
    }, e2.repeatDelay = function(t18) {
      if (arguments.length) {
        var e3 = this._time;
        return this._rDelay = t18, te(this), e3 ? this.time(e3) : this;
      }
      return this._rDelay;
    }, e2.yoyo = function(t18) {
      return arguments.length ? (this._yoyo = t18, this) : this._yoyo;
    }, e2.seek = function(t18, e3) {
      return this.totalTime(ie(this, t18), G(e3));
    }, e2.restart = function(t18, e3) {
      return this.play().totalTime(t18 ? -this._delay : 0, G(e3));
    }, e2.play = function(t18, e3) {
      return null != t18 && this.seek(t18, e3), this.reversed(false).paused(false);
    }, e2.reverse = function(t18, e3) {
      return null != t18 && this.seek(t18 || this.totalDuration(), e3), this.reversed(true).paused(false);
    }, e2.pause = function(t18, e3) {
      return null != t18 && this.seek(t18, e3), this.paused(true);
    }, e2.resume = function() {
      return this.paused(false);
    }, e2.reversed = function(t18) {
      return arguments.length ? (!!t18 !== this.reversed() && this.timeScale(-this._rts || (t18 ? -1e-8 : 0)), this) : this._rts < 0;
    }, e2.invalidate = function() {
      return this._initted = this._act = 0, this._zTime = -1e-8, this;
    }, e2.isActive = function() {
      var t18, e3 = this.parent || this._dp, i2 = this._start;
      return !(e3 && !(this._ts && this._initted && e3.isActive() && (t18 = e3.rawTime(true)) >= i2 && t18 < this.endTime(true) - 1e-8));
    }, e2.eventCallback = function(t18, e3, i2) {
      var r2 = this.vars;
      return arguments.length > 1 ? (e3 ? (r2[t18] = e3, i2 && (r2[t18 + "Params"] = i2), "onUpdate" === t18 && (this._onUpdate = e3)) : delete r2[t18], this) : r2[t18];
    }, e2.then = function(t18) {
      var e3 = this;
      return new Promise((function(i2) {
        var r2 = X(t18) ? t18 : Ct, n2 = function() {
          var t19 = e3.then;
          e3.then = null, X(r2) && (r2 = r2(e3)) && (r2.then || r2 === e3) && (e3.then = t19), i2(r2), e3.then = t19;
        };
        e3._initted && 1 === e3.totalProgress() && e3._ts >= 0 || !e3._tTime && e3._ts < 0 ? n2() : e3._prom = n2;
      }));
    }, e2.kill = function() {
      we(this);
    }, t17;
  })();
  St(Xe.prototype, { _time: 0, _start: 0, _end: 0, _tTime: 0, _tDur: 0, _dirty: 0, _repeat: 0, _yoyo: false, parent: null, _initted: false, _rDelay: 0, _ts: 1, _dp: 0, ratio: 0, _zTime: -1e-8, _prom: 0, _ps: false, _rts: 1 });
  var We = (function(t17) {
    function e2(e3, i3) {
      var r2;
      return void 0 === e3 && (e3 = {}), (r2 = t17.call(this, e3) || this).labels = {}, r2.smoothChildTiming = !!e3.smoothChildTiming, r2.autoRemoveChildren = !!e3.autoRemoveChildren, r2._sort = G(e3.sortChildren), u && Gt(e3.parent || u, s(r2), i3), e3.reversed && r2.reverse(), e3.paused && r2.paused(true), e3.scrollTrigger && Ht(s(r2), e3.scrollTrigger), r2;
    }
    a(e2, t17);
    var i2 = e2.prototype;
    return i2.to = function(t18, e3, i3) {
      return re(0, arguments, this), this;
    }, i2.from = function(t18, e3, i3) {
      return re(1, arguments, this), this;
    }, i2.fromTo = function(t18, e3, i3, r2) {
      return re(2, arguments, this), this;
    }, i2.set = function(t18, e3, i3) {
      return e3.duration = 0, e3.parent = this, zt(e3).repeatDelay || (e3.repeat = 0), e3.immediateRender = !!e3.immediateRender, new ti(t18, e3, ie(this, i3), 1), this;
    }, i2.call = function(t18, e3, i3) {
      return Gt(this, ti.delayedCall(0, t18, e3), i3);
    }, i2.staggerTo = function(t18, e3, i3, r2, n2, s2, a2) {
      return i3.duration = e3, i3.stagger = i3.stagger || r2, i3.onComplete = s2, i3.onCompleteParams = a2, i3.parent = this, new ti(t18, i3, ie(this, n2)), this;
    }, i2.staggerFrom = function(t18, e3, i3, r2, n2, s2, a2) {
      return i3.runBackwards = 1, zt(i3).immediateRender = G(i3.immediateRender), this.staggerTo(t18, e3, i3, r2, n2, s2, a2);
    }, i2.staggerFromTo = function(t18, e3, i3, r2, n2, s2, a2, o2) {
      return r2.startAt = i3, zt(r2).immediateRender = G(r2.immediateRender), this.staggerTo(t18, e3, r2, n2, s2, a2, o2);
    }, i2.render = function(t18, e3, i3) {
      var r2, n2, s2, a2, o2, h2, l2, f2, c2, p2, d2, _2, m2 = this._time, g2 = this._dirty ? this.totalDuration() : this._tDur, v2 = this._dur, y2 = this !== u && t18 > g2 - 1e-8 && t18 >= 0 ? g2 : t18 < 1e-8 ? 0 : t18, w2 = this._zTime < 0 != t18 < 0 && (this._initted || !v2);
      if (y2 !== this._tTime || i3 || w2) {
        if (m2 !== this._time && v2 && (y2 += this._time - m2, t18 += this._time - m2), r2 = y2, c2 = this._start, h2 = !(f2 = this._ts), w2 && (v2 || (m2 = this._zTime), (t18 || !e3) && (this._zTime = t18)), this._repeat) {
          if (d2 = this._yoyo, o2 = v2 + this._rDelay, this._repeat < -1 && t18 < 0) return this.totalTime(100 * o2 + t18, e3, i3);
          if (r2 = Mt(y2 % o2), y2 === g2 ? (a2 = this._repeat, r2 = v2) : ((a2 = ~~(y2 / o2)) && a2 === y2 / o2 && (r2 = v2, a2--), r2 > v2 && (r2 = v2)), p2 = Yt(this._tTime, o2), !m2 && this._tTime && p2 !== a2 && (p2 = a2), d2 && 1 & a2 && (r2 = v2 - r2, _2 = 1), a2 !== p2 && !this._lock) {
            var b2 = d2 && 1 & p2, x2 = b2 === (d2 && 1 & a2);
            if (a2 < p2 && (b2 = !b2), m2 = b2 ? 0 : v2, this._lock = 1, this.render(m2 || (_2 ? 0 : Mt(a2 * o2)), e3, !v2)._lock = 0, this._tTime = y2, !e3 && this.parent && ye(this, "onRepeat"), this.vars.repeatRefresh && !_2 && (this.invalidate()._lock = 1), m2 && m2 !== this._time || h2 !== !this._ts || this.vars.onRepeat && !this.parent && !this._act) return this;
            if (v2 = this._dur, g2 = this._tDur, x2 && (this._lock = 2, m2 = b2 ? v2 : -1e-4, this.render(m2, true), this.vars.repeatRefresh && !_2 && this.invalidate()), this._lock = 0, !this._ts && !h2) return this;
            Fe(this, _2);
          }
        }
        if (this._hasPause && !this._forcing && this._lock < 2 && (l2 = (function(t19, e4, i4) {
          var r3;
          if (i4 > e4) for (r3 = t19._first; r3 && r3._start <= i4; ) {
            if (!r3._dur && "isPause" === r3.data && r3._start > e4) return r3;
            r3 = r3._next;
          }
          else for (r3 = t19._last; r3 && r3._start >= i4; ) {
            if (!r3._dur && "isPause" === r3.data && r3._start < e4) return r3;
            r3 = r3._prev;
          }
        })(this, Mt(m2), Mt(r2)), l2 && (y2 -= r2 - (r2 = l2._start))), this._tTime = y2, this._time = r2, this._act = !f2, this._initted || (this._onUpdate = this.vars.onUpdate, this._initted = 1, this._zTime = t18, m2 = 0), !m2 && r2 && !e3 && (ye(this, "onStart"), this._tTime !== y2)) return this;
        if (r2 >= m2 && t18 >= 0) for (n2 = this._first; n2; ) {
          if (s2 = n2._next, (n2._act || r2 >= n2._start) && n2._ts && l2 !== n2) {
            if (n2.parent !== this) return this.render(t18, e3, i3);
            if (n2.render(n2._ts > 0 ? (r2 - n2._start) * n2._ts : (n2._dirty ? n2.totalDuration() : n2._tDur) + (r2 - n2._start) * n2._ts, e3, i3), r2 !== this._time || !this._ts && !h2) {
              l2 = 0, s2 && (y2 += this._zTime = -1e-8);
              break;
            }
          }
          n2 = s2;
        }
        else {
          n2 = this._last;
          for (var T2 = t18 < 0 ? t18 : r2; n2; ) {
            if (s2 = n2._prev, (n2._act || T2 <= n2._end) && n2._ts && l2 !== n2) {
              if (n2.parent !== this) return this.render(t18, e3, i3);
              if (n2.render(n2._ts > 0 ? (T2 - n2._start) * n2._ts : (n2._dirty ? n2.totalDuration() : n2._tDur) + (T2 - n2._start) * n2._ts, e3, i3), r2 !== this._time || !this._ts && !h2) {
                l2 = 0, s2 && (y2 += this._zTime = T2 ? -1e-8 : 1e-8);
                break;
              }
            }
            n2 = s2;
          }
        }
        if (l2 && !e3 && (this.pause(), l2.render(r2 >= m2 ? 0 : -1e-8)._zTime = r2 >= m2 ? 1 : -1, this._ts)) return this._start = c2, Wt(this), this.render(t18, e3, i3);
        this._onUpdate && !e3 && ye(this, "onUpdate", true), (y2 === g2 && g2 >= this.totalDuration() || !y2 && m2) && (c2 !== this._start && Math.abs(f2) === Math.abs(this._ts) || this._lock || ((t18 || !v2) && (y2 === g2 && this._ts > 0 || !y2 && this._ts < 0) && Bt(this, 1), e3 || t18 < 0 && !m2 || !y2 && !m2 && g2 || (ye(this, y2 === g2 && t18 >= 0 ? "onComplete" : "onReverseComplete", true), this._prom && !(y2 < g2 && this.timeScale() > 0) && this._prom())));
      }
      return this;
    }, i2.add = function(t18, e3) {
      var i3 = this;
      if (W(e3) || (e3 = ie(this, e3, t18)), !(t18 instanceof Xe)) {
        if ($(t18)) return t18.forEach((function(t19) {
          return i3.add(t19, e3);
        })), this;
        if (Y(t18)) return this.addLabel(t18, e3);
        if (!X(t18)) return this;
        t18 = ti.delayedCall(0, t18);
      }
      return this !== t18 ? Gt(this, t18, e3) : this;
    }, i2.getChildren = function(t18, e3, i3, r2) {
      void 0 === t18 && (t18 = true), void 0 === e3 && (e3 = true), void 0 === i3 && (i3 = true), void 0 === r2 && (r2 = -1e8);
      for (var n2 = [], s2 = this._first; s2; ) s2._start >= r2 && (s2 instanceof ti ? e3 && n2.push(s2) : (i3 && n2.push(s2), t18 && n2.push.apply(n2, s2.getChildren(true, e3, i3)))), s2 = s2._next;
      return n2;
    }, i2.getById = function(t18) {
      for (var e3 = this.getChildren(1, 1, 1), i3 = e3.length; i3--; ) if (e3[i3].vars.id === t18) return e3[i3];
    }, i2.remove = function(t18) {
      return Y(t18) ? this.removeLabel(t18) : X(t18) ? this.killTweensOf(t18) : (Ft(this, t18), t18 === this._recent && (this._recent = this._last), qt(this));
    }, i2.totalTime = function(e3, i3) {
      return arguments.length ? (this._forcing = 1, !this._dp && this._ts && (this._start = Mt(Ce.time - (this._ts > 0 ? e3 / this._ts : (this.totalDuration() - e3) / -this._ts))), t17.prototype.totalTime.call(this, e3, i3), this._forcing = 0, this) : this._tTime;
    }, i2.addLabel = function(t18, e3) {
      return this.labels[t18] = ie(this, e3), this;
    }, i2.removeLabel = function(t18) {
      return delete this.labels[t18], this;
    }, i2.addPause = function(t18, e3, i3) {
      var r2 = ti.delayedCall(0, e3 || ct, i3);
      return r2.data = "isPause", this._hasPause = 1, Gt(this, r2, ie(this, t18));
    }, i2.removePause = function(t18) {
      var e3 = this._first;
      for (t18 = ie(this, t18); e3; ) e3._start === t18 && "isPause" === e3.data && Bt(e3), e3 = e3._next;
    }, i2.killTweensOf = function(t18, e3, i3) {
      for (var r2 = this.getTweensOf(t18, i3), n2 = r2.length; n2--; ) Ve !== r2[n2] && r2[n2].kill(t18, e3);
      return this;
    }, i2.getTweensOf = function(t18, e3) {
      for (var i3, r2 = [], n2 = he(t18), s2 = this._first, a2 = W(e3); s2; ) s2 instanceof ti ? Dt(s2._targets, n2) && (a2 ? (!Ve || s2._initted && s2._ts) && s2.globalTime(0) <= e3 && s2.globalTime(s2.totalDuration()) > e3 : !e3 || s2.isActive()) && r2.push(s2) : (i3 = s2.getTweensOf(n2, e3)).length && r2.push.apply(r2, i3), s2 = s2._next;
      return r2;
    }, i2.tweenTo = function(t18, e3) {
      e3 = e3 || {};
      var i3, r2 = this, n2 = ie(r2, t18), s2 = e3, a2 = s2.startAt, o2 = s2.onStart, u2 = s2.onStartParams, h2 = s2.immediateRender, l2 = ti.to(r2, St({ ease: e3.ease || "none", lazy: false, immediateRender: false, time: n2, overwrite: "auto", duration: e3.duration || Math.abs((n2 - (a2 && "time" in a2 ? a2.time : r2._time)) / r2.timeScale()) || 1e-8, onStart: function() {
        if (r2.pause(), !i3) {
          var t19 = e3.duration || Math.abs((n2 - (a2 && "time" in a2 ? a2.time : r2._time)) / r2.timeScale());
          l2._dur !== t19 && Kt(l2, t19, 0, 1).render(l2._time, true, true), i3 = 1;
        }
        o2 && o2.apply(l2, u2 || []);
      } }, e3));
      return h2 ? l2.render(0) : l2;
    }, i2.tweenFromTo = function(t18, e3, i3) {
      return this.tweenTo(e3, St({ startAt: { time: ie(this, t18) } }, i3));
    }, i2.recent = function() {
      return this._recent;
    }, i2.nextLabel = function(t18) {
      return void 0 === t18 && (t18 = this._time), ve(this, ie(this, t18));
    }, i2.previousLabel = function(t18) {
      return void 0 === t18 && (t18 = this._time), ve(this, ie(this, t18), 1);
    }, i2.currentLabel = function(t18) {
      return arguments.length ? this.seek(t18, true) : this.previousLabel(this._time + 1e-8);
    }, i2.shiftChildren = function(t18, e3, i3) {
      void 0 === i3 && (i3 = 0);
      for (var r2, n2 = this._first, s2 = this.labels; n2; ) n2._start >= i3 && (n2._start += t18, n2._end += t18), n2 = n2._next;
      if (e3) for (r2 in s2) s2[r2] >= i3 && (s2[r2] += t18);
      return qt(this);
    }, i2.invalidate = function() {
      var e3 = this._first;
      for (this._lock = 0; e3; ) e3.invalidate(), e3 = e3._next;
      return t17.prototype.invalidate.call(this);
    }, i2.clear = function(t18) {
      void 0 === t18 && (t18 = true);
      for (var e3, i3 = this._first; i3; ) e3 = i3._next, this.remove(i3), i3 = e3;
      return this._dp && (this._time = this._tTime = this._pTime = 0), t18 && (this.labels = {}), qt(this);
    }, i2.totalDuration = function(t18) {
      var e3, i3, r2, n2 = 0, s2 = this, a2 = s2._last, o2 = 1e8;
      if (arguments.length) return s2.timeScale((s2._repeat < 0 ? s2.duration() : s2.totalDuration()) / (s2.reversed() ? -t18 : t18));
      if (s2._dirty) {
        for (r2 = s2.parent; a2; ) e3 = a2._prev, a2._dirty && a2.totalDuration(), (i3 = a2._start) > o2 && s2._sort && a2._ts && !s2._lock ? (s2._lock = 1, Gt(s2, a2, i3 - a2._delay, 1)._lock = 0) : o2 = i3, i3 < 0 && a2._ts && (n2 -= i3, (!r2 && !s2._dp || r2 && r2.smoothChildTiming) && (s2._start += i3 / s2._ts, s2._time -= i3, s2._tTime -= i3), s2.shiftChildren(-i3, false, -1 / 0), o2 = 0), a2._end > n2 && a2._ts && (n2 = a2._end), a2 = e3;
        Kt(s2, s2 === u && s2._time > n2 ? s2._time : n2, 1, 1), s2._dirty = 0;
      }
      return s2._tDur;
    }, e2.updateRoot = function(t18) {
      if (u._ts && (At(u, Xt(t18, u)), p = Ce.frame), Ce.frame >= vt) {
        vt += R.autoSleep || 120;
        var e3 = u._first;
        if ((!e3 || !e3._ts) && R.autoSleep && Ce._listeners.length < 2) {
          for (; e3 && !e3._ts; ) e3 = e3._next;
          e3 || Ce.sleep();
        }
      }
    }, e2;
  })(Xe);
  St(We.prototype, { _lock: 0, _hasPause: 0, _forcing: 0 });
  var Ve;
  var Qe = function(t17, e2, i2, r2, n2, s2, a2) {
    var o2, u2, h2, l2, f2, c2, p2, d2, _2 = new di(this._pt, t17, e2, 0, 1, ui, null, n2), m2 = 0, g2 = 0;
    for (_2.b = i2, _2.e = r2, i2 += "", (p2 = ~(r2 += "").indexOf("random(")) && (r2 = me(r2)), s2 && (s2(d2 = [i2, r2], t17, e2), i2 = d2[0], r2 = d2[1]), u2 = i2.match(it) || []; o2 = it.exec(r2); ) l2 = o2[0], f2 = r2.substring(m2, o2.index), h2 ? h2 = (h2 + 1) % 5 : "rgba(" === f2.substr(-5) && (h2 = 1), l2 !== u2[g2++] && (c2 = parseFloat(u2[g2 - 1]) || 0, _2._pt = { _next: _2._pt, p: f2 || 1 === g2 ? f2 : ",", s: c2, c: "=" === l2.charAt(1) ? parseFloat(l2.substr(2)) * ("-" === l2.charAt(0) ? -1 : 1) : parseFloat(l2) - c2, m: h2 && h2 < 4 ? Math.round : 0 }, m2 = it.lastIndex);
    return _2.c = m2 < r2.length ? r2.substring(m2, r2.length) : "", _2.fp = a2, (rt.test(r2) || p2) && (_2.e = 0), this._pt = _2, _2;
  };
  var Ge = function(t17, e2, i2, r2, n2, s2, a2, o2, u2) {
    X(r2) && (r2 = r2(n2 || 0, t17, s2));
    var h2, l2 = t17[e2], f2 = "get" !== i2 ? i2 : X(l2) ? u2 ? t17[e2.indexOf("set") || !X(t17["get" + e2.substr(3)]) ? e2 : "get" + e2.substr(3)](u2) : t17[e2]() : l2, c2 = X(l2) ? u2 ? ri : ii : ei;
    if (Y(r2) && (~r2.indexOf("random(") && (r2 = me(r2)), "=" === r2.charAt(1) && ((h2 = parseFloat(f2) + parseFloat(r2.substr(2)) * ("-" === r2.charAt(0) ? -1 : 1) + (ae(f2) || 0)) || 0 === h2) && (r2 = h2)), f2 !== r2) return isNaN(f2 * r2) || "" === r2 ? (!l2 && !(e2 in t17) && ht(e2, r2), Qe.call(this, t17, e2, f2, r2, c2, o2 || R.stringFilter, u2)) : (h2 = new di(this._pt, t17, e2, +f2 || 0, r2 - (f2 || 0), "boolean" == typeof l2 ? oi : ai, 0, c2), u2 && (h2.fp = u2), a2 && h2.modifier(a2, this, t17), this._pt = h2);
  };
  var He = function(t17, e2, i2, r2, n2, s2) {
    var a2, o2, u2, h2;
    if (mt[t17] && false !== (a2 = new mt[t17]()).init(n2, a2.rawVars ? e2[t17] : (function(t18, e3, i3, r3, n3) {
      if (X(t18) && (t18 = Je(t18, n3, e3, i3, r3)), !Q(t18) || t18.style && t18.nodeType || $(t18) || J(t18)) return Y(t18) ? Je(t18, n3, e3, i3, r3) : t18;
      var s3, a3 = {};
      for (s3 in t18) a3[s3] = Je(t18[s3], n3, e3, i3, r3);
      return a3;
    })(e2[t17], r2, n2, s2, i2), i2, r2, s2) && (i2._pt = o2 = new di(i2._pt, n2, t17, 0, 1, a2.render, a2, 0, a2.priority), i2 !== d)) for (u2 = i2._ptLookup[i2._targets.indexOf(n2)], h2 = a2._props.length; h2--; ) u2[a2._props[h2]] = o2;
    return a2;
  };
  var Ze = function t10(e2, i2) {
    var r2, n2, s2, a2, h2, l2, f2, c2, p2, d2, _2, m2, g2, v2 = e2.vars, y2 = v2.ease, w2 = v2.startAt, b2 = v2.immediateRender, x2 = v2.lazy, T2 = v2.onUpdate, O2 = v2.onUpdateParams, M2 = v2.callbackScope, D2 = v2.runBackwards, k2 = v2.yoyoEase, A2 = v2.keyframes, E2 = v2.autoRevert, C2 = e2._dur, S2 = e2._startAt, P2 = e2._targets, I2 = e2.parent, L2 = I2 && "nested" === I2.data ? I2.parent._targets : P2, R2 = "auto" === e2._overwrite && !o, F2 = e2.timeline;
    if (F2 && (!A2 || !y2) && (y2 = "none"), e2._ease = Be(y2, z.ease), e2._yEase = k2 ? ze(Be(true === k2 ? y2 : k2, z.ease)) : 0, k2 && e2._yoyo && !e2._repeat && (k2 = e2._yEase, e2._yEase = e2._ease, e2._ease = k2), e2._from = !F2 && !!v2.runBackwards, !F2) {
      if (m2 = (c2 = P2[0] ? xt(P2[0]).harness : 0) && v2[c2.prop], r2 = Rt(v2, pt), S2 && S2.render(-1, true).kill(), w2) if (Bt(e2._startAt = ti.set(P2, St({ data: "isStart", overwrite: false, parent: I2, immediateRender: true, lazy: G(x2), startAt: null, delay: 0, onUpdate: T2, onUpdateParams: O2, callbackScope: M2, stagger: 0 }, w2))), i2 < 0 && !b2 && !E2 && e2._startAt.render(-1, true), b2) {
        if (i2 > 0 && !E2 && (e2._startAt = 0), C2 && i2 <= 0) return void (i2 && (e2._zTime = i2));
      } else false === E2 && (e2._startAt = 0);
      else if (D2 && C2) if (S2) !E2 && (e2._startAt = 0);
      else if (i2 && (b2 = false), s2 = St({ overwrite: false, data: "isFromStart", lazy: b2 && G(x2), immediateRender: b2, stagger: 0, parent: I2 }, r2), m2 && (s2[c2.prop] = m2), Bt(e2._startAt = ti.set(P2, s2)), i2 < 0 && e2._startAt.render(-1, true), b2) {
        if (!i2) return;
      } else t10(e2._startAt, 1e-8);
      for (e2._pt = 0, x2 = C2 && G(x2) || x2 && !C2, n2 = 0; n2 < P2.length; n2++) {
        if (f2 = (h2 = P2[n2])._gsap || bt(P2)[n2]._gsap, e2._ptLookup[n2] = d2 = {}, _t[f2.id] && dt.length && kt(), _2 = L2 === P2 ? n2 : L2.indexOf(h2), c2 && false !== (p2 = new c2()).init(h2, m2 || r2, e2, _2, L2) && (e2._pt = a2 = new di(e2._pt, h2, p2.name, 0, 1, p2.render, p2, 0, p2.priority), p2._props.forEach((function(t17) {
          d2[t17] = a2;
        })), p2.priority && (l2 = 1)), !c2 || m2) for (s2 in r2) mt[s2] && (p2 = He(s2, r2, e2, _2, h2, L2)) ? p2.priority && (l2 = 1) : d2[s2] = a2 = Ge.call(e2, h2, s2, "get", r2[s2], _2, L2, 0, v2.stringFilter);
        e2._op && e2._op[n2] && e2.kill(h2, e2._op[n2]), R2 && e2._pt && (Ve = e2, u.killTweensOf(h2, d2, e2.globalTime(0)), g2 = !e2.parent, Ve = 0), e2._pt && x2 && (_t[f2.id] = 1);
      }
      l2 && pi(e2), e2._onInit && e2._onInit(e2);
    }
    e2._onUpdate = T2, e2._initted = (!e2._op || e2._pt) && !g2;
  };
  var Je = function(t17, e2, i2, r2, n2) {
    return X(t17) ? t17.call(e2, i2, r2, n2) : Y(t17) && ~t17.indexOf("random(") ? me(t17) : t17;
  };
  var $e = wt + "repeat,repeatDelay,yoyo,repeatRefresh,yoyoEase";
  var Ke = ($e + ",id,stagger,delay,duration,paused,scrollTrigger").split(",");
  var ti = (function(t17) {
    function e2(e3, i3, r2, n2) {
      var a2;
      "number" == typeof i3 && (r2.duration = i3, i3 = r2, r2 = null);
      var h2, l2, f2, c2, p2, d2, _2, m2, g2 = (a2 = t17.call(this, n2 ? i3 : zt(i3)) || this).vars, v2 = g2.duration, y2 = g2.delay, w2 = g2.immediateRender, b2 = g2.stagger, x2 = g2.overwrite, T2 = g2.keyframes, O2 = g2.defaults, M2 = g2.scrollTrigger, D2 = g2.yoyoEase, k2 = i3.parent || u, A2 = ($(e3) || J(e3) ? W(e3[0]) : "length" in i3) ? [e3] : he(e3);
      if (a2._targets = A2.length ? bt(A2) : lt("GSAP target " + e3 + " not found. https://greensock.com", !R.nullTargetWarn) || [], a2._ptLookup = [], a2._overwrite = x2, T2 || b2 || Z(v2) || Z(y2)) {
        if (i3 = a2.vars, (h2 = a2.timeline = new We({ data: "nested", defaults: O2 || {} })).kill(), h2.parent = h2._dp = s(a2), h2._start = 0, T2) St(h2.vars.defaults, { ease: "none" }), b2 ? A2.forEach((function(t18, e4) {
          return T2.forEach((function(i4, r3) {
            return h2.to(t18, i4, r3 ? ">" : e4 * b2);
          }));
        })) : T2.forEach((function(t18) {
          return h2.to(A2, t18, ">");
        }));
        else {
          if (c2 = A2.length, _2 = b2 ? fe(b2) : ct, Q(b2)) for (p2 in b2) ~$e.indexOf(p2) && (m2 || (m2 = {}), m2[p2] = b2[p2]);
          for (l2 = 0; l2 < c2; l2++) {
            for (p2 in f2 = {}, i3) Ke.indexOf(p2) < 0 && (f2[p2] = i3[p2]);
            f2.stagger = 0, D2 && (f2.yoyoEase = D2), m2 && It(f2, m2), d2 = A2[l2], f2.duration = +Je(v2, s(a2), l2, d2, A2), f2.delay = (+Je(y2, s(a2), l2, d2, A2) || 0) - a2._delay, !b2 && 1 === c2 && f2.delay && (a2._delay = y2 = f2.delay, a2._start += y2, f2.delay = 0), h2.to(d2, f2, _2(l2, d2, A2));
          }
          h2.duration() ? v2 = y2 = 0 : a2.timeline = 0;
        }
        v2 || a2.duration(v2 = h2.duration());
      } else a2.timeline = 0;
      return true !== x2 || o || (Ve = s(a2), u.killTweensOf(A2), Ve = 0), Gt(k2, s(a2), r2), i3.reversed && a2.reverse(), i3.paused && a2.paused(true), (w2 || !v2 && !T2 && a2._start === Mt(k2._time) && G(w2) && Nt(s(a2)) && "nested" !== k2.data) && (a2._tTime = -1e-8, a2.render(Math.max(0, -y2))), M2 && Ht(s(a2), M2), a2;
    }
    a(e2, t17);
    var i2 = e2.prototype;
    return i2.render = function(t18, e3, i3) {
      var r2, n2, s2, a2, o2, u2, h2, l2, f2, c2 = this._time, p2 = this._tDur, d2 = this._dur, _2 = t18 > p2 - 1e-8 && t18 >= 0 ? p2 : t18 < 1e-8 ? 0 : t18;
      if (d2) {
        if (_2 !== this._tTime || !t18 || i3 || !this._initted && this._tTime || this._startAt && this._zTime < 0 != t18 < 0) {
          if (r2 = _2, l2 = this.timeline, this._repeat) {
            if (a2 = d2 + this._rDelay, this._repeat < -1 && t18 < 0) return this.totalTime(100 * a2 + t18, e3, i3);
            if (r2 = Mt(_2 % a2), _2 === p2 ? (s2 = this._repeat, r2 = d2) : ((s2 = ~~(_2 / a2)) && s2 === _2 / a2 && (r2 = d2, s2--), r2 > d2 && (r2 = d2)), (u2 = this._yoyo && 1 & s2) && (f2 = this._yEase, r2 = d2 - r2), o2 = Yt(this._tTime, a2), r2 === c2 && !i3 && this._initted) return this;
            s2 !== o2 && (l2 && this._yEase && Fe(l2, u2), !this.vars.repeatRefresh || u2 || this._lock || (this._lock = i3 = 1, this.render(Mt(a2 * s2), true).invalidate()._lock = 0));
          }
          if (!this._initted) {
            if (Zt(this, t18 < 0 ? t18 : r2, i3, e3)) return this._tTime = 0, this;
            if (d2 !== this._dur) return this.render(t18, e3, i3);
          }
          if (this._tTime = _2, this._time = r2, !this._act && this._ts && (this._act = 1, this._lazy = 0), this.ratio = h2 = (f2 || this._ease)(r2 / d2), this._from && (this.ratio = h2 = 1 - h2), r2 && !c2 && !e3 && (ye(this, "onStart"), this._tTime !== _2)) return this;
          for (n2 = this._pt; n2; ) n2.r(h2, n2.d), n2 = n2._next;
          l2 && l2.render(t18 < 0 ? t18 : !r2 && u2 ? -1e-8 : l2._dur * h2, e3, i3) || this._startAt && (this._zTime = t18), this._onUpdate && !e3 && (t18 < 0 && this._startAt && this._startAt.render(t18, true, i3), ye(this, "onUpdate")), this._repeat && s2 !== o2 && this.vars.onRepeat && !e3 && this.parent && ye(this, "onRepeat"), _2 !== this._tDur && _2 || this._tTime !== _2 || (t18 < 0 && this._startAt && !this._onUpdate && this._startAt.render(t18, true, true), (t18 || !d2) && (_2 === this._tDur && this._ts > 0 || !_2 && this._ts < 0) && Bt(this, 1), e3 || t18 < 0 && !c2 || !_2 && !c2 || (ye(this, _2 === p2 ? "onComplete" : "onReverseComplete", true), this._prom && !(_2 < p2 && this.timeScale() > 0) && this._prom()));
        }
      } else !(function(t19, e4, i4, r3) {
        var n3, s3, a3, o3 = t19.ratio, u3 = e4 < 0 || !e4 && (!t19._start && Jt(t19) && (t19._initted || !$t(t19)) || (t19._ts < 0 || t19._dp._ts < 0) && !$t(t19)) ? 0 : 1, h3 = t19._rDelay, l3 = 0;
        if (h3 && t19._repeat && (l3 = se(0, t19._tDur, e4), s3 = Yt(l3, h3), a3 = Yt(t19._tTime, h3), t19._yoyo && 1 & s3 && (u3 = 1 - u3), s3 !== a3 && (o3 = 1 - u3, t19.vars.repeatRefresh && t19._initted && t19.invalidate())), u3 !== o3 || r3 || 1e-8 === t19._zTime || !e4 && t19._zTime) {
          if (!t19._initted && Zt(t19, e4, r3, i4)) return;
          for (a3 = t19._zTime, t19._zTime = e4 || (i4 ? 1e-8 : 0), i4 || (i4 = e4 && !a3), t19.ratio = u3, t19._from && (u3 = 1 - u3), t19._time = 0, t19._tTime = l3, n3 = t19._pt; n3; ) n3.r(u3, n3.d), n3 = n3._next;
          t19._startAt && e4 < 0 && t19._startAt.render(e4, true, true), t19._onUpdate && !i4 && ye(t19, "onUpdate"), l3 && t19._repeat && !i4 && t19.parent && ye(t19, "onRepeat"), (e4 >= t19._tDur || e4 < 0) && t19.ratio === u3 && (u3 && Bt(t19, 1), i4 || (ye(t19, u3 ? "onComplete" : "onReverseComplete", true), t19._prom && t19._prom()));
        } else t19._zTime || (t19._zTime = e4);
      })(this, t18, e3, i3);
      return this;
    }, i2.targets = function() {
      return this._targets;
    }, i2.invalidate = function() {
      return this._pt = this._op = this._startAt = this._onUpdate = this._lazy = this.ratio = 0, this._ptLookup = [], this.timeline && this.timeline.invalidate(), t17.prototype.invalidate.call(this);
    }, i2.kill = function(t18, e3) {
      if (void 0 === e3 && (e3 = "all"), !(t18 || e3 && "all" !== e3)) return this._lazy = this._pt = 0, this.parent ? we(this) : this;
      if (this.timeline) {
        var i3 = this.timeline.totalDuration();
        return this.timeline.killTweensOf(t18, e3, Ve && true !== Ve.vars.overwrite)._first || we(this), this.parent && i3 !== this.timeline.totalDuration() && Kt(this, this._dur * this.timeline._tDur / i3, 0, 1), this;
      }
      var r2, n2, s2, a2, o2, u2, h2, l2 = this._targets, f2 = t18 ? he(t18) : l2, c2 = this._ptLookup, p2 = this._pt;
      if ((!e3 || "all" === e3) && (function(t19, e4) {
        for (var i4 = t19.length, r3 = i4 === e4.length; r3 && i4-- && t19[i4] === e4[i4]; ) ;
        return i4 < 0;
      })(l2, f2)) return "all" === e3 && (this._pt = 0), we(this);
      for (r2 = this._op = this._op || [], "all" !== e3 && (Y(e3) && (o2 = {}, Ot(e3, (function(t19) {
        return o2[t19] = 1;
      })), e3 = o2), e3 = (function(t19, e4) {
        var i4, r3, n3, s3, a3 = t19[0] ? xt(t19[0]).harness : 0, o3 = a3 && a3.aliases;
        if (!o3) return e4;
        for (r3 in i4 = It({}, e4), o3) if (r3 in i4) for (n3 = (s3 = o3[r3].split(",")).length; n3--; ) i4[s3[n3]] = i4[r3];
        return i4;
      })(l2, e3)), h2 = l2.length; h2--; ) if (~f2.indexOf(l2[h2])) for (o2 in n2 = c2[h2], "all" === e3 ? (r2[h2] = e3, a2 = n2, s2 = {}) : (s2 = r2[h2] = r2[h2] || {}, a2 = e3), a2) (u2 = n2 && n2[o2]) && ("kill" in u2.d && true !== u2.d.kill(o2) || Ft(this, u2, "_pt"), delete n2[o2]), "all" !== s2 && (s2[o2] = 1);
      return this._initted && !this._pt && p2 && we(this), this;
    }, e2.to = function(t18, i3) {
      return new e2(t18, i3, arguments[2]);
    }, e2.from = function(t18, e3) {
      return re(1, arguments);
    }, e2.delayedCall = function(t18, i3, r2, n2) {
      return new e2(i3, 0, { immediateRender: false, lazy: false, overwrite: false, delay: t18, onComplete: i3, onReverseComplete: i3, onCompleteParams: r2, onReverseCompleteParams: r2, callbackScope: n2 });
    }, e2.fromTo = function(t18, e3, i3) {
      return re(2, arguments);
    }, e2.set = function(t18, i3) {
      return i3.duration = 0, i3.repeatDelay || (i3.repeat = 0), new e2(t18, i3);
    }, e2.killTweensOf = function(t18, e3, i3) {
      return u.killTweensOf(t18, e3, i3);
    }, e2;
  })(Xe);
  St(ti.prototype, { _targets: [], _lazy: 0, _startAt: 0, _op: 0, _onInit: 0 }), Ot("staggerTo,staggerFrom,staggerFromTo", (function(t17) {
    ti[t17] = function() {
      var e2 = new We(), i2 = oe.call(arguments, 0);
      return i2.splice("staggerFromTo" === t17 ? 5 : 4, 0, 0), e2[t17].apply(e2, i2);
    };
  }));
  var ei = function(t17, e2, i2) {
    return t17[e2] = i2;
  };
  var ii = function(t17, e2, i2) {
    return t17[e2](i2);
  };
  var ri = function(t17, e2, i2, r2) {
    return t17[e2](r2.fp, i2);
  };
  var ni = function(t17, e2, i2) {
    return t17.setAttribute(e2, i2);
  };
  var si = function(t17, e2) {
    return X(t17[e2]) ? ii : V(t17[e2]) && t17.setAttribute ? ni : ei;
  };
  var ai = function(t17, e2) {
    return e2.set(e2.t, e2.p, Math.round(1e6 * (e2.s + e2.c * t17)) / 1e6, e2);
  };
  var oi = function(t17, e2) {
    return e2.set(e2.t, e2.p, !!(e2.s + e2.c * t17), e2);
  };
  var ui = function(t17, e2) {
    var i2 = e2._pt, r2 = "";
    if (!t17 && e2.b) r2 = e2.b;
    else if (1 === t17 && e2.e) r2 = e2.e;
    else {
      for (; i2; ) r2 = i2.p + (i2.m ? i2.m(i2.s + i2.c * t17) : Math.round(1e4 * (i2.s + i2.c * t17)) / 1e4) + r2, i2 = i2._next;
      r2 += e2.c;
    }
    e2.set(e2.t, e2.p, r2, e2);
  };
  var hi = function(t17, e2) {
    for (var i2 = e2._pt; i2; ) i2.r(t17, i2.d), i2 = i2._next;
  };
  var li = function(t17, e2, i2, r2) {
    for (var n2, s2 = this._pt; s2; ) n2 = s2._next, s2.p === r2 && s2.modifier(t17, e2, i2), s2 = n2;
  };
  var fi = function(t17) {
    for (var e2, i2, r2 = this._pt; r2; ) i2 = r2._next, r2.p === t17 && !r2.op || r2.op === t17 ? Ft(this, r2, "_pt") : r2.dep || (e2 = 1), r2 = i2;
    return !e2;
  };
  var ci = function(t17, e2, i2, r2) {
    r2.mSet(t17, e2, r2.m.call(r2.tween, i2, r2.mt), r2);
  };
  var pi = function(t17) {
    for (var e2, i2, r2, n2, s2 = t17._pt; s2; ) {
      for (e2 = s2._next, i2 = r2; i2 && i2.pr > s2.pr; ) i2 = i2._next;
      (s2._prev = i2 ? i2._prev : n2) ? s2._prev._next = s2 : r2 = s2, (s2._next = i2) ? i2._prev = s2 : n2 = s2, s2 = e2;
    }
    t17._pt = r2;
  };
  var di = (function() {
    function t17(t18, e2, i2, r2, n2, s2, a2, o2, u2) {
      this.t = e2, this.s = r2, this.c = n2, this.p = i2, this.r = s2 || ai, this.d = a2 || this, this.set = o2 || ei, this.pr = u2 || 0, this._next = t18, t18 && (t18._prev = this);
    }
    return t17.prototype.modifier = function(t18, e2, i2) {
      this.mSet = this.mSet || this.set, this.set = ci, this.m = t18, this.mt = i2, this.tween = e2;
    }, t17;
  })();
  Ot(wt + "parent,duration,ease,delay,overwrite,runBackwards,startAt,yoyo,immediateRender,repeat,repeatDelay,data,paused,reversed,lazy,callbackScope,stringFilter,id,yoyoEase,stagger,inherit,repeatRefresh,keyframes,autoRevert,scrollTrigger", (function(t17) {
    return pt[t17] = 1;
  })), at.TweenMax = at.TweenLite = ti, at.TimelineLite = at.TimelineMax = We, u = new We({ sortChildren: false, defaults: z, autoRemoveChildren: true, id: "root", smoothChildTiming: true }), R.stringFilter = Ee;
  var _i = { registerPlugin: function() {
    for (var t17 = arguments.length, e2 = new Array(t17), i2 = 0; i2 < t17; i2++) e2[i2] = arguments[i2];
    e2.forEach((function(t18) {
      return be(t18);
    }));
  }, timeline: function(t17) {
    return new We(t17);
  }, getTweensOf: function(t17, e2) {
    return u.getTweensOf(t17, e2);
  }, getProperty: function(t17, e2, i2, r2) {
    Y(t17) && (t17 = he(t17)[0]);
    var n2 = xt(t17 || {}).get, s2 = i2 ? Ct : Et;
    return "native" === i2 && (i2 = ""), t17 ? e2 ? s2((mt[e2] && mt[e2].get || n2)(t17, e2, i2, r2)) : function(e3, i3, r3) {
      return s2((mt[e3] && mt[e3].get || n2)(t17, e3, i3, r3));
    } : t17;
  }, quickSetter: function(t17, e2, i2) {
    if ((t17 = he(t17)).length > 1) {
      var r2 = t17.map((function(t18) {
        return vi.quickSetter(t18, e2, i2);
      })), n2 = r2.length;
      return function(t18) {
        for (var e3 = n2; e3--; ) r2[e3](t18);
      };
    }
    t17 = t17[0] || {};
    var s2 = mt[e2], a2 = xt(t17), o2 = a2.harness && (a2.harness.aliases || {})[e2] || e2, u2 = s2 ? function(e3) {
      var r3 = new s2();
      d._pt = 0, r3.init(t17, i2 ? e3 + i2 : e3, d, 0, [t17]), r3.render(1, r3), d._pt && hi(1, d);
    } : a2.set(t17, o2);
    return s2 ? u2 : function(e3) {
      return u2(t17, o2, i2 ? e3 + i2 : e3, a2, 1);
    };
  }, isTweening: function(t17) {
    return u.getTweensOf(t17, true).length > 0;
  }, defaults: function(t17) {
    return t17 && t17.ease && (t17.ease = Be(t17.ease, z.ease)), Lt(z, t17 || {});
  }, config: function(t17) {
    return Lt(R, t17 || {});
  }, registerEffect: function(t17) {
    var e2 = t17.name, i2 = t17.effect, r2 = t17.plugins, n2 = t17.defaults, s2 = t17.extendTimeline;
    (r2 || "").split(",").forEach((function(t18) {
      return t18 && !mt[t18] && !at[t18] && lt(e2 + " effect requires " + t18 + " plugin.");
    })), gt[e2] = function(t18, e3, r3) {
      return i2(he(t18), St(e3 || {}, n2), r3);
    }, s2 && (We.prototype[e2] = function(t18, i3, r3) {
      return this.add(gt[e2](t18, Q(i3) ? i3 : (r3 = i3) && {}, this), r3);
    });
  }, registerEase: function(t17, e2) {
    Pe[t17] = Be(e2);
  }, parseEase: function(t17, e2) {
    return arguments.length ? Be(t17, e2) : Pe;
  }, getById: function(t17) {
    return u.getById(t17);
  }, exportRoot: function(t17, e2) {
    void 0 === t17 && (t17 = {});
    var i2, r2, n2 = new We(t17);
    for (n2.smoothChildTiming = G(t17.smoothChildTiming), u.remove(n2), n2._dp = 0, n2._time = n2._tTime = u._time, i2 = u._first; i2; ) r2 = i2._next, !e2 && !i2._dur && i2 instanceof ti && i2.vars.onComplete === i2._targets[0] || Gt(n2, i2, i2._start - i2._delay), i2 = r2;
    return Gt(u, n2, 0), n2;
  }, utils: { wrap: function t11(e2, i2, r2) {
    var n2 = i2 - e2;
    return $(e2) ? _e(e2, t11(0, e2.length), i2) : ne(r2, (function(t17) {
      return (n2 + (t17 - e2) % n2) % n2 + e2;
    }));
  }, wrapYoyo: function t12(e2, i2, r2) {
    var n2 = i2 - e2, s2 = 2 * n2;
    return $(e2) ? _e(e2, t12(0, e2.length - 1), i2) : ne(r2, (function(t17) {
      return e2 + ((t17 = (s2 + (t17 - e2) % s2) % s2 || 0) > n2 ? s2 - t17 : t17);
    }));
  }, distribute: fe, random: de, snap: pe, normalize: function(t17, e2, i2) {
    return ge(t17, e2, 0, 1, i2);
  }, getUnit: ae, clamp: function(t17, e2, i2) {
    return ne(i2, (function(i3) {
      return se(t17, e2, i3);
    }));
  }, splitColor: Oe, toArray: he, selector: function(t17) {
    return t17 = he(t17)[0] || lt("Invalid scope") || {}, function(e2) {
      var i2 = t17.current || t17.nativeElement || t17;
      return he(e2, i2.querySelectorAll ? i2 : i2 === t17 ? lt("Invalid scope") || f.createElement("div") : t17);
    };
  }, mapRange: ge, pipe: function() {
    for (var t17 = arguments.length, e2 = new Array(t17), i2 = 0; i2 < t17; i2++) e2[i2] = arguments[i2];
    return function(t18) {
      return e2.reduce((function(t19, e3) {
        return e3(t19);
      }), t18);
    };
  }, unitize: function(t17, e2) {
    return function(i2) {
      return t17(parseFloat(i2)) + (e2 || ae(i2));
    };
  }, interpolate: function t13(e2, i2, r2, n2) {
    var s2 = isNaN(e2 + i2) ? 0 : function(t17) {
      return (1 - t17) * e2 + t17 * i2;
    };
    if (!s2) {
      var a2, o2, u2, h2, l2, f2 = Y(e2), c2 = {};
      if (true === r2 && (n2 = 1) && (r2 = null), f2) e2 = { p: e2 }, i2 = { p: i2 };
      else if ($(e2) && !$(i2)) {
        for (u2 = [], h2 = e2.length, l2 = h2 - 2, o2 = 1; o2 < h2; o2++) u2.push(t13(e2[o2 - 1], e2[o2]));
        h2--, s2 = function(t17) {
          t17 *= h2;
          var e3 = Math.min(l2, ~~t17);
          return u2[e3](t17 - e3);
        }, r2 = i2;
      } else n2 || (e2 = It($(e2) ? [] : {}, e2));
      if (!u2) {
        for (a2 in i2) Ge.call(c2, e2, a2, "get", i2[a2]);
        s2 = function(t17) {
          return hi(t17, c2) || (f2 ? e2.p : e2);
        };
      }
    }
    return ne(r2, s2);
  }, shuffle: le }, install: ut, effects: gt, ticker: Ce, updateRoot: We.updateRoot, plugins: mt, globalTimeline: u, core: { PropTween: di, globals: ft, Tween: ti, Timeline: We, Animation: Xe, getCache: xt, _removeLinkedListItem: Ft, suppressOverwrites: function(t17) {
    return o = t17;
  } } };
  Ot("to,from,fromTo,delayedCall,set,killTweensOf", (function(t17) {
    return _i[t17] = ti[t17];
  })), Ce.add(We.updateRoot), d = _i.to({}, { duration: 0 });
  var mi = function(t17, e2) {
    for (var i2 = t17._pt; i2 && i2.p !== e2 && i2.op !== e2 && i2.fp !== e2; ) i2 = i2._next;
    return i2;
  };
  var gi = function(t17, e2) {
    return { name: t17, rawVars: 1, init: function(t18, i2, r2) {
      r2._onInit = function(t19) {
        var r3, n2;
        if (Y(i2) && (r3 = {}, Ot(i2, (function(t20) {
          return r3[t20] = 1;
        })), i2 = r3), e2) {
          for (n2 in r3 = {}, i2) r3[n2] = e2(i2[n2]);
          i2 = r3;
        }
        !(function(t20, e3) {
          var i3, r4, n3, s2 = t20._targets;
          for (i3 in e3) for (r4 = s2.length; r4--; ) (n3 = t20._ptLookup[r4][i3]) && (n3 = n3.d) && (n3._pt && (n3 = mi(n3, i3)), n3 && n3.modifier && n3.modifier(e3[i3], t20, s2[r4], i3));
        })(t19, i2);
      };
    } };
  };
  var vi = _i.registerPlugin({ name: "attr", init: function(t17, e2, i2, r2, n2) {
    var s2, a2;
    for (s2 in e2) (a2 = this.add(t17, "setAttribute", (t17.getAttribute(s2) || 0) + "", e2[s2], r2, n2, 0, 0, s2)) && (a2.op = s2), this._props.push(s2);
  } }, { name: "endArray", init: function(t17, e2) {
    for (var i2 = e2.length; i2--; ) this.add(t17, i2, t17[i2] || 0, e2[i2]);
  } }, gi("roundProps", ce), gi("modifiers"), gi("snap", pe)) || _i;
  ti.version = We.version = vi.version = "3.7.1", c = 1, H() && Se();
  Pe.Power0, Pe.Power1, Pe.Power2, Pe.Power3, Pe.Power4, Pe.Linear, Pe.Quad, Pe.Cubic, Pe.Quart, Pe.Quint, Pe.Strong, Pe.Elastic, Pe.Back, Pe.SteppedEase, Pe.Bounce, Pe.Sine, Pe.Expo, Pe.Circ;
  var yi;
  var wi;
  var bi;
  var xi;
  var Ti;
  var Oi;
  var Mi;
  var Di = {};
  var ki = 180 / Math.PI;
  var Ai = Math.PI / 180;
  var Ei = Math.atan2;
  var Ci = /([A-Z])/g;
  var Si = /(?:left|right|width|margin|padding|x)/i;
  var Pi = /[\s,\(]\S/;
  var Ii = { autoAlpha: "opacity,visibility", scale: "scaleX,scaleY", alpha: "opacity" };
  var Li = function(t17, e2) {
    return e2.set(e2.t, e2.p, Math.round(1e4 * (e2.s + e2.c * t17)) / 1e4 + e2.u, e2);
  };
  var Ri = function(t17, e2) {
    return e2.set(e2.t, e2.p, 1 === t17 ? e2.e : Math.round(1e4 * (e2.s + e2.c * t17)) / 1e4 + e2.u, e2);
  };
  var zi = function(t17, e2) {
    return e2.set(e2.t, e2.p, t17 ? Math.round(1e4 * (e2.s + e2.c * t17)) / 1e4 + e2.u : e2.b, e2);
  };
  var Fi = function(t17, e2) {
    var i2 = e2.s + e2.c * t17;
    e2.set(e2.t, e2.p, ~~(i2 + (i2 < 0 ? -0.5 : 0.5)) + e2.u, e2);
  };
  var Bi = function(t17, e2) {
    return e2.set(e2.t, e2.p, t17 ? e2.e : e2.b, e2);
  };
  var qi = function(t17, e2) {
    return e2.set(e2.t, e2.p, 1 !== t17 ? e2.b : e2.e, e2);
  };
  var ji = function(t17, e2, i2) {
    return t17.style[e2] = i2;
  };
  var Ni = function(t17, e2, i2) {
    return t17.style.setProperty(e2, i2);
  };
  var Ui = function(t17, e2, i2) {
    return t17._gsap[e2] = i2;
  };
  var Yi = function(t17, e2, i2) {
    return t17._gsap.scaleX = t17._gsap.scaleY = i2;
  };
  var Xi = function(t17, e2, i2, r2, n2) {
    var s2 = t17._gsap;
    s2.scaleX = s2.scaleY = i2, s2.renderTransform(n2, s2);
  };
  var Wi = function(t17, e2, i2, r2, n2) {
    var s2 = t17._gsap;
    s2[e2] = i2, s2.renderTransform(n2, s2);
  };
  var Vi = "transform";
  var Qi = Vi + "Origin";
  var Gi = function(t17, e2) {
    var i2 = wi.createElementNS ? wi.createElementNS((e2 || "http://www.w3.org/1999/xhtml").replace(/^https/, "http"), t17) : wi.createElement(t17);
    return i2.style ? i2 : wi.createElement(t17);
  };
  var Hi = function t14(e2, i2, r2) {
    var n2 = getComputedStyle(e2);
    return n2[i2] || n2.getPropertyValue(i2.replace(Ci, "-$1").toLowerCase()) || n2.getPropertyValue(i2) || !r2 && t14(e2, Ji(i2) || i2, 1) || "";
  };
  var Zi = "O,Moz,ms,Ms,Webkit".split(",");
  var Ji = function(t17, e2, i2) {
    var r2 = (e2 || Ti).style, n2 = 5;
    if (t17 in r2 && !i2) return t17;
    for (t17 = t17.charAt(0).toUpperCase() + t17.substr(1); n2-- && !(Zi[n2] + t17 in r2); ) ;
    return n2 < 0 ? null : (3 === n2 ? "ms" : n2 >= 0 ? Zi[n2] : "") + t17;
  };
  var $i = function() {
    "undefined" != typeof window && window.document && (yi = window, wi = yi.document, bi = wi.documentElement, Ti = Gi("div") || { style: {} }, Gi("div"), Vi = Ji(Vi), Qi = Vi + "Origin", Ti.style.cssText = "border-width:0;line-height:0;position:absolute;padding:0", Mi = !!Ji("perspective"), xi = 1);
  };
  var Ki = function t15(e2) {
    var i2, r2 = Gi("svg", this.ownerSVGElement && this.ownerSVGElement.getAttribute("xmlns") || "http://www.w3.org/2000/svg"), n2 = this.parentNode, s2 = this.nextSibling, a2 = this.style.cssText;
    if (bi.appendChild(r2), r2.appendChild(this), this.style.display = "block", e2) try {
      i2 = this.getBBox(), this._gsapBBox = this.getBBox, this.getBBox = t15;
    } catch (t17) {
    }
    else this._gsapBBox && (i2 = this._gsapBBox());
    return n2 && (s2 ? n2.insertBefore(this, s2) : n2.appendChild(this)), bi.removeChild(r2), this.style.cssText = a2, i2;
  };
  var tr = function(t17, e2) {
    for (var i2 = e2.length; i2--; ) if (t17.hasAttribute(e2[i2])) return t17.getAttribute(e2[i2]);
  };
  var er = function(t17) {
    var e2;
    try {
      e2 = t17.getBBox();
    } catch (i2) {
      e2 = Ki.call(t17, true);
    }
    return e2 && (e2.width || e2.height) || t17.getBBox === Ki || (e2 = Ki.call(t17, true)), !e2 || e2.width || e2.x || e2.y ? e2 : { x: +tr(t17, ["x", "cx", "x1"]) || 0, y: +tr(t17, ["y", "cy", "y1"]) || 0, width: 0, height: 0 };
  };
  var ir = function(t17) {
    return !(!t17.getCTM || t17.parentNode && !t17.ownerSVGElement || !er(t17));
  };
  var rr = function(t17, e2) {
    if (e2) {
      var i2 = t17.style;
      e2 in Di && e2 !== Qi && (e2 = Vi), i2.removeProperty ? ("ms" !== e2.substr(0, 2) && "webkit" !== e2.substr(0, 6) || (e2 = "-" + e2), i2.removeProperty(e2.replace(Ci, "-$1").toLowerCase())) : i2.removeAttribute(e2);
    }
  };
  var nr = function(t17, e2, i2, r2, n2, s2) {
    var a2 = new di(t17._pt, e2, i2, 0, 1, s2 ? qi : Bi);
    return t17._pt = a2, a2.b = r2, a2.e = n2, t17._props.push(i2), a2;
  };
  var sr = { deg: 1, rad: 1, turn: 1 };
  var ar = function t16(e2, i2, r2, n2) {
    var s2, a2, o2, u2, h2 = parseFloat(r2) || 0, l2 = (r2 + "").trim().substr((h2 + "").length) || "px", f2 = Ti.style, c2 = Si.test(i2), p2 = "svg" === e2.tagName.toLowerCase(), d2 = (p2 ? "client" : "offset") + (c2 ? "Width" : "Height"), _2 = 100, m2 = "px" === n2, g2 = "%" === n2;
    return n2 === l2 || !h2 || sr[n2] || sr[l2] ? h2 : ("px" !== l2 && !m2 && (h2 = t16(e2, i2, r2, "px")), u2 = e2.getCTM && ir(e2), !g2 && "%" !== l2 || !Di[i2] && !~i2.indexOf("adius") ? (f2[c2 ? "width" : "height"] = _2 + (m2 ? l2 : n2), a2 = ~i2.indexOf("adius") || "em" === n2 && e2.appendChild && !p2 ? e2 : e2.parentNode, u2 && (a2 = (e2.ownerSVGElement || {}).parentNode), a2 && a2 !== wi && a2.appendChild || (a2 = wi.body), (o2 = a2._gsap) && g2 && o2.width && c2 && o2.time === Ce.time ? Mt(h2 / o2.width * _2) : ((g2 || "%" === l2) && (f2.position = Hi(e2, "position")), a2 === e2 && (f2.position = "static"), a2.appendChild(Ti), s2 = Ti[d2], a2.removeChild(Ti), f2.position = "absolute", c2 && g2 && ((o2 = xt(a2)).time = Ce.time, o2.width = a2[d2]), Mt(m2 ? s2 * h2 / _2 : s2 && h2 ? _2 / s2 * h2 : 0))) : (s2 = u2 ? e2.getBBox()[c2 ? "width" : "height"] : e2[d2], Mt(g2 ? h2 / s2 * _2 : h2 / 100 * s2)));
  };
  var or = function(t17, e2, i2, r2) {
    var n2;
    return xi || $i(), e2 in Ii && "transform" !== e2 && ~(e2 = Ii[e2]).indexOf(",") && (e2 = e2.split(",")[0]), Di[e2] && "transform" !== e2 ? (n2 = vr(t17, r2), n2 = "transformOrigin" !== e2 ? n2[e2] : n2.svg ? n2.origin : yr(Hi(t17, Qi)) + " " + n2.zOrigin + "px") : (!(n2 = t17.style[e2]) || "auto" === n2 || r2 || ~(n2 + "").indexOf("calc(")) && (n2 = fr[e2] && fr[e2](t17, e2, i2) || Hi(t17, e2) || Tt(t17, e2) || ("opacity" === e2 ? 1 : 0)), i2 && !~(n2 + "").trim().indexOf(" ") ? ar(t17, e2, n2, i2) + i2 : n2;
  };
  var ur = function(t17, e2, i2, r2) {
    if (!i2 || "none" === i2) {
      var n2 = Ji(e2, t17, 1), s2 = n2 && Hi(t17, n2, 1);
      s2 && s2 !== i2 ? (e2 = n2, i2 = s2) : "borderColor" === e2 && (i2 = Hi(t17, "borderTopColor"));
    }
    var a2, o2, u2, h2, l2, f2, c2, p2, d2, _2, m2, g2, v2 = new di(this._pt, t17.style, e2, 0, 1, ui), y2 = 0, w2 = 0;
    if (v2.b = i2, v2.e = r2, i2 += "", "auto" === (r2 += "") && (t17.style[e2] = r2, r2 = Hi(t17, e2) || r2, t17.style[e2] = i2), Ee(a2 = [i2, r2]), r2 = a2[1], u2 = (i2 = a2[0]).match(et) || [], (r2.match(et) || []).length) {
      for (; o2 = et.exec(r2); ) c2 = o2[0], d2 = r2.substring(y2, o2.index), l2 ? l2 = (l2 + 1) % 5 : "rgba(" !== d2.substr(-5) && "hsla(" !== d2.substr(-5) || (l2 = 1), c2 !== (f2 = u2[w2++] || "") && (h2 = parseFloat(f2) || 0, m2 = f2.substr((h2 + "").length), (g2 = "=" === c2.charAt(1) ? +(c2.charAt(0) + "1") : 0) && (c2 = c2.substr(2)), p2 = parseFloat(c2), _2 = c2.substr((p2 + "").length), y2 = et.lastIndex - _2.length, _2 || (_2 = _2 || R.units[e2] || m2, y2 === r2.length && (r2 += _2, v2.e += _2)), m2 !== _2 && (h2 = ar(t17, e2, f2, _2) || 0), v2._pt = { _next: v2._pt, p: d2 || 1 === w2 ? d2 : ",", s: h2, c: g2 ? g2 * p2 : p2 - h2, m: l2 && l2 < 4 || "zIndex" === e2 ? Math.round : 0 });
      v2.c = y2 < r2.length ? r2.substring(y2, r2.length) : "";
    } else v2.r = "display" === e2 && "none" === r2 ? qi : Bi;
    return rt.test(r2) && (v2.e = 0), this._pt = v2, v2;
  };
  var hr = { top: "0%", bottom: "100%", left: "0%", right: "100%", center: "50%" };
  var lr = function(t17, e2) {
    if (e2.tween && e2.tween._time === e2.tween._dur) {
      var i2, r2, n2, s2 = e2.t, a2 = s2.style, o2 = e2.u, u2 = s2._gsap;
      if ("all" === o2 || true === o2) a2.cssText = "", r2 = 1;
      else for (n2 = (o2 = o2.split(",")).length; --n2 > -1; ) i2 = o2[n2], Di[i2] && (r2 = 1, i2 = "transformOrigin" === i2 ? Qi : Vi), rr(s2, i2);
      r2 && (rr(s2, Vi), u2 && (u2.svg && s2.removeAttribute("transform"), vr(s2, 1), u2.uncache = 1));
    }
  };
  var fr = { clearProps: function(t17, e2, i2, r2, n2) {
    if ("isFromStart" !== n2.data) {
      var s2 = t17._pt = new di(t17._pt, e2, i2, 0, 0, lr);
      return s2.u = r2, s2.pr = -10, s2.tween = n2, t17._props.push(i2), 1;
    }
  } };
  var cr = [1, 0, 0, 1, 0, 0];
  var pr = {};
  var dr = function(t17) {
    return "matrix(1, 0, 0, 1, 0, 0)" === t17 || "none" === t17 || !t17;
  };
  var _r = function(t17) {
    var e2 = Hi(t17, Vi);
    return dr(e2) ? cr : e2.substr(7).match(tt).map(Mt);
  };
  var mr = function(t17, e2) {
    var i2, r2, n2, s2, a2 = t17._gsap || xt(t17), o2 = t17.style, u2 = _r(t17);
    return a2.svg && t17.getAttribute("transform") ? "1,0,0,1,0,0" === (u2 = [(n2 = t17.transform.baseVal.consolidate().matrix).a, n2.b, n2.c, n2.d, n2.e, n2.f]).join(",") ? cr : u2 : (u2 !== cr || t17.offsetParent || t17 === bi || a2.svg || (n2 = o2.display, o2.display = "block", (i2 = t17.parentNode) && t17.offsetParent || (s2 = 1, r2 = t17.nextSibling, bi.appendChild(t17)), u2 = _r(t17), n2 ? o2.display = n2 : rr(t17, "display"), s2 && (r2 ? i2.insertBefore(t17, r2) : i2 ? i2.appendChild(t17) : bi.removeChild(t17))), e2 && u2.length > 6 ? [u2[0], u2[1], u2[4], u2[5], u2[12], u2[13]] : u2);
  };
  var gr = function(t17, e2, i2, r2, n2, s2) {
    var a2, o2, u2, h2 = t17._gsap, l2 = n2 || mr(t17, true), f2 = h2.xOrigin || 0, c2 = h2.yOrigin || 0, p2 = h2.xOffset || 0, d2 = h2.yOffset || 0, _2 = l2[0], m2 = l2[1], g2 = l2[2], v2 = l2[3], y2 = l2[4], w2 = l2[5], b2 = e2.split(" "), x2 = parseFloat(b2[0]) || 0, T2 = parseFloat(b2[1]) || 0;
    i2 ? l2 !== cr && (o2 = _2 * v2 - m2 * g2) && (u2 = x2 * (-m2 / o2) + T2 * (_2 / o2) - (_2 * w2 - m2 * y2) / o2, x2 = x2 * (v2 / o2) + T2 * (-g2 / o2) + (g2 * w2 - v2 * y2) / o2, T2 = u2) : (x2 = (a2 = er(t17)).x + (~b2[0].indexOf("%") ? x2 / 100 * a2.width : x2), T2 = a2.y + (~(b2[1] || b2[0]).indexOf("%") ? T2 / 100 * a2.height : T2)), r2 || false !== r2 && h2.smooth ? (y2 = x2 - f2, w2 = T2 - c2, h2.xOffset = p2 + (y2 * _2 + w2 * g2) - y2, h2.yOffset = d2 + (y2 * m2 + w2 * v2) - w2) : h2.xOffset = h2.yOffset = 0, h2.xOrigin = x2, h2.yOrigin = T2, h2.smooth = !!r2, h2.origin = e2, h2.originIsAbsolute = !!i2, t17.style[Qi] = "0px 0px", s2 && (nr(s2, h2, "xOrigin", f2, x2), nr(s2, h2, "yOrigin", c2, T2), nr(s2, h2, "xOffset", p2, h2.xOffset), nr(s2, h2, "yOffset", d2, h2.yOffset)), t17.setAttribute("data-svg-origin", x2 + " " + T2);
  };
  var vr = function(t17, e2) {
    var i2 = t17._gsap || new Ye(t17);
    if ("x" in i2 && !e2 && !i2.uncache) return i2;
    var r2, n2, s2, a2, o2, u2, h2, l2, f2, c2, p2, d2, _2, m2, g2, v2, y2, w2, b2, x2, T2, O2, M2, D2, k2, A2, E2, C2, S2, P2, I2, L2, z2 = t17.style, F2 = i2.scaleX < 0, B2 = "px", q2 = "deg", j2 = Hi(t17, Qi) || "0";
    return r2 = n2 = s2 = u2 = h2 = l2 = f2 = c2 = p2 = 0, a2 = o2 = 1, i2.svg = !(!t17.getCTM || !ir(t17)), m2 = mr(t17, i2.svg), i2.svg && (D2 = (!i2.uncache || "0px 0px" === j2) && !e2 && t17.getAttribute("data-svg-origin"), gr(t17, D2 || j2, !!D2 || i2.originIsAbsolute, false !== i2.smooth, m2)), d2 = i2.xOrigin || 0, _2 = i2.yOrigin || 0, m2 !== cr && (w2 = m2[0], b2 = m2[1], x2 = m2[2], T2 = m2[3], r2 = O2 = m2[4], n2 = M2 = m2[5], 6 === m2.length ? (a2 = Math.sqrt(w2 * w2 + b2 * b2), o2 = Math.sqrt(T2 * T2 + x2 * x2), u2 = w2 || b2 ? Ei(b2, w2) * ki : 0, (f2 = x2 || T2 ? Ei(x2, T2) * ki + u2 : 0) && (o2 *= Math.abs(Math.cos(f2 * Ai))), i2.svg && (r2 -= d2 - (d2 * w2 + _2 * x2), n2 -= _2 - (d2 * b2 + _2 * T2))) : (L2 = m2[6], P2 = m2[7], E2 = m2[8], C2 = m2[9], S2 = m2[10], I2 = m2[11], r2 = m2[12], n2 = m2[13], s2 = m2[14], h2 = (g2 = Ei(L2, S2)) * ki, g2 && (D2 = O2 * (v2 = Math.cos(-g2)) + E2 * (y2 = Math.sin(-g2)), k2 = M2 * v2 + C2 * y2, A2 = L2 * v2 + S2 * y2, E2 = O2 * -y2 + E2 * v2, C2 = M2 * -y2 + C2 * v2, S2 = L2 * -y2 + S2 * v2, I2 = P2 * -y2 + I2 * v2, O2 = D2, M2 = k2, L2 = A2), l2 = (g2 = Ei(-x2, S2)) * ki, g2 && (v2 = Math.cos(-g2), I2 = T2 * (y2 = Math.sin(-g2)) + I2 * v2, w2 = D2 = w2 * v2 - E2 * y2, b2 = k2 = b2 * v2 - C2 * y2, x2 = A2 = x2 * v2 - S2 * y2), u2 = (g2 = Ei(b2, w2)) * ki, g2 && (D2 = w2 * (v2 = Math.cos(g2)) + b2 * (y2 = Math.sin(g2)), k2 = O2 * v2 + M2 * y2, b2 = b2 * v2 - w2 * y2, M2 = M2 * v2 - O2 * y2, w2 = D2, O2 = k2), h2 && Math.abs(h2) + Math.abs(u2) > 359.9 && (h2 = u2 = 0, l2 = 180 - l2), a2 = Mt(Math.sqrt(w2 * w2 + b2 * b2 + x2 * x2)), o2 = Mt(Math.sqrt(M2 * M2 + L2 * L2)), g2 = Ei(O2, M2), f2 = Math.abs(g2) > 2e-4 ? g2 * ki : 0, p2 = I2 ? 1 / (I2 < 0 ? -I2 : I2) : 0), i2.svg && (D2 = t17.getAttribute("transform"), i2.forceCSS = t17.setAttribute("transform", "") || !dr(Hi(t17, Vi)), D2 && t17.setAttribute("transform", D2))), Math.abs(f2) > 90 && Math.abs(f2) < 270 && (F2 ? (a2 *= -1, f2 += u2 <= 0 ? 180 : -180, u2 += u2 <= 0 ? 180 : -180) : (o2 *= -1, f2 += f2 <= 0 ? 180 : -180)), i2.x = r2 - ((i2.xPercent = r2 && (i2.xPercent || (Math.round(t17.offsetWidth / 2) === Math.round(-r2) ? -50 : 0))) ? t17.offsetWidth * i2.xPercent / 100 : 0) + B2, i2.y = n2 - ((i2.yPercent = n2 && (i2.yPercent || (Math.round(t17.offsetHeight / 2) === Math.round(-n2) ? -50 : 0))) ? t17.offsetHeight * i2.yPercent / 100 : 0) + B2, i2.z = s2 + B2, i2.scaleX = Mt(a2), i2.scaleY = Mt(o2), i2.rotation = Mt(u2) + q2, i2.rotationX = Mt(h2) + q2, i2.rotationY = Mt(l2) + q2, i2.skewX = f2 + q2, i2.skewY = c2 + q2, i2.transformPerspective = p2 + B2, (i2.zOrigin = parseFloat(j2.split(" ")[2]) || 0) && (z2[Qi] = yr(j2)), i2.xOffset = i2.yOffset = 0, i2.force3D = R.force3D, i2.renderTransform = i2.svg ? Tr : Mi ? xr : br, i2.uncache = 0, i2;
  };
  var yr = function(t17) {
    return (t17 = t17.split(" "))[0] + " " + t17[1];
  };
  var wr = function(t17, e2, i2) {
    var r2 = ae(e2);
    return Mt(parseFloat(e2) + parseFloat(ar(t17, "x", i2 + "px", r2))) + r2;
  };
  var br = function(t17, e2) {
    e2.z = "0px", e2.rotationY = e2.rotationX = "0deg", e2.force3D = 0, xr(t17, e2);
  };
  var xr = function(t17, e2) {
    var i2 = e2 || this, r2 = i2.xPercent, n2 = i2.yPercent, s2 = i2.x, a2 = i2.y, o2 = i2.z, u2 = i2.rotation, h2 = i2.rotationY, l2 = i2.rotationX, f2 = i2.skewX, c2 = i2.skewY, p2 = i2.scaleX, d2 = i2.scaleY, _2 = i2.transformPerspective, m2 = i2.force3D, g2 = i2.target, v2 = i2.zOrigin, y2 = "", w2 = "auto" === m2 && t17 && 1 !== t17 || true === m2;
    if (v2 && ("0deg" !== l2 || "0deg" !== h2)) {
      var b2, x2 = parseFloat(h2) * Ai, T2 = Math.sin(x2), O2 = Math.cos(x2);
      x2 = parseFloat(l2) * Ai, b2 = Math.cos(x2), s2 = wr(g2, s2, T2 * b2 * -v2), a2 = wr(g2, a2, -Math.sin(x2) * -v2), o2 = wr(g2, o2, O2 * b2 * -v2 + v2);
    }
    "0px" !== _2 && (y2 += "perspective(" + _2 + ") "), (r2 || n2) && (y2 += "translate(" + r2 + "%, " + n2 + "%) "), (w2 || "0px" !== s2 || "0px" !== a2 || "0px" !== o2) && (y2 += "0px" !== o2 || w2 ? "translate3d(" + s2 + ", " + a2 + ", " + o2 + ") " : "translate(" + s2 + ", " + a2 + ") "), "0deg" !== u2 && (y2 += "rotate(" + u2 + ") "), "0deg" !== h2 && (y2 += "rotateY(" + h2 + ") "), "0deg" !== l2 && (y2 += "rotateX(" + l2 + ") "), "0deg" === f2 && "0deg" === c2 || (y2 += "skew(" + f2 + ", " + c2 + ") "), 1 === p2 && 1 === d2 || (y2 += "scale(" + p2 + ", " + d2 + ") "), g2.style[Vi] = y2 || "translate(0, 0)";
  };
  var Tr = function(t17, e2) {
    var i2, r2, n2, s2, a2, o2 = e2 || this, u2 = o2.xPercent, h2 = o2.yPercent, l2 = o2.x, f2 = o2.y, c2 = o2.rotation, p2 = o2.skewX, d2 = o2.skewY, _2 = o2.scaleX, m2 = o2.scaleY, g2 = o2.target, v2 = o2.xOrigin, y2 = o2.yOrigin, w2 = o2.xOffset, b2 = o2.yOffset, x2 = o2.forceCSS, T2 = parseFloat(l2), O2 = parseFloat(f2);
    c2 = parseFloat(c2), p2 = parseFloat(p2), (d2 = parseFloat(d2)) && (p2 += d2 = parseFloat(d2), c2 += d2), c2 || p2 ? (c2 *= Ai, p2 *= Ai, i2 = Math.cos(c2) * _2, r2 = Math.sin(c2) * _2, n2 = Math.sin(c2 - p2) * -m2, s2 = Math.cos(c2 - p2) * m2, p2 && (d2 *= Ai, a2 = Math.tan(p2 - d2), n2 *= a2 = Math.sqrt(1 + a2 * a2), s2 *= a2, d2 && (a2 = Math.tan(d2), i2 *= a2 = Math.sqrt(1 + a2 * a2), r2 *= a2)), i2 = Mt(i2), r2 = Mt(r2), n2 = Mt(n2), s2 = Mt(s2)) : (i2 = _2, s2 = m2, r2 = n2 = 0), (T2 && !~(l2 + "").indexOf("px") || O2 && !~(f2 + "").indexOf("px")) && (T2 = ar(g2, "x", l2, "px"), O2 = ar(g2, "y", f2, "px")), (v2 || y2 || w2 || b2) && (T2 = Mt(T2 + v2 - (v2 * i2 + y2 * n2) + w2), O2 = Mt(O2 + y2 - (v2 * r2 + y2 * s2) + b2)), (u2 || h2) && (a2 = g2.getBBox(), T2 = Mt(T2 + u2 / 100 * a2.width), O2 = Mt(O2 + h2 / 100 * a2.height)), a2 = "matrix(" + i2 + "," + r2 + "," + n2 + "," + s2 + "," + T2 + "," + O2 + ")", g2.setAttribute("transform", a2), x2 && (g2.style[Vi] = a2);
  };
  var Or = function(t17, e2, i2, r2, n2, s2) {
    var a2, o2, u2 = 360, h2 = Y(n2), l2 = parseFloat(n2) * (h2 && ~n2.indexOf("rad") ? ki : 1), f2 = s2 ? l2 * s2 : l2 - r2, c2 = r2 + f2 + "deg";
    return h2 && ("short" === (a2 = n2.split("_")[1]) && (f2 %= u2) !== f2 % 180 && (f2 += f2 < 0 ? u2 : -360), "cw" === a2 && f2 < 0 ? f2 = (f2 + 36e9) % u2 - ~~(f2 / u2) * u2 : "ccw" === a2 && f2 > 0 && (f2 = (f2 - 36e9) % u2 - ~~(f2 / u2) * u2)), t17._pt = o2 = new di(t17._pt, e2, i2, r2, f2, Ri), o2.e = c2, o2.u = "deg", t17._props.push(i2), o2;
  };
  var Mr = function(t17, e2) {
    for (var i2 in e2) t17[i2] = e2[i2];
    return t17;
  };
  var Dr = function(t17, e2, i2) {
    var r2, n2, s2, a2, o2, u2, h2, l2 = Mr({}, i2._gsap), f2 = i2.style;
    for (n2 in l2.svg ? (s2 = i2.getAttribute("transform"), i2.setAttribute("transform", ""), f2[Vi] = e2, r2 = vr(i2, 1), rr(i2, Vi), i2.setAttribute("transform", s2)) : (s2 = getComputedStyle(i2)[Vi], f2[Vi] = e2, r2 = vr(i2, 1), f2[Vi] = s2), Di) (s2 = l2[n2]) !== (a2 = r2[n2]) && "perspective,force3D,transformOrigin,svgOrigin".indexOf(n2) < 0 && (o2 = ae(s2) !== (h2 = ae(a2)) ? ar(i2, n2, s2, h2) : parseFloat(s2), u2 = parseFloat(a2), t17._pt = new di(t17._pt, r2, n2, o2, u2 - o2, Li), t17._pt.u = h2 || 0, t17._props.push(n2));
    Mr(r2, l2);
  };
  Ot("padding,margin,Width,Radius", (function(t17, e2) {
    var i2 = "Top", r2 = "Right", n2 = "Bottom", s2 = "Left", a2 = (e2 < 3 ? [i2, r2, n2, s2] : [i2 + s2, i2 + r2, n2 + r2, n2 + s2]).map((function(i3) {
      return e2 < 2 ? t17 + i3 : "border" + i3 + t17;
    }));
    fr[e2 > 1 ? "border" + t17 : t17] = function(t18, e3, i3, r3, n3) {
      var s3, o2;
      if (arguments.length < 4) return s3 = a2.map((function(e4) {
        return or(t18, e4, i3);
      })), 5 === (o2 = s3.join(" ")).split(s3[0]).length ? s3[0] : o2;
      s3 = (r3 + "").split(" "), o2 = {}, a2.forEach((function(t19, e4) {
        return o2[t19] = s3[e4] = s3[e4] || s3[(e4 - 1) / 2 | 0];
      })), t18.init(e3, o2, n3);
    };
  }));
  var kr;
  var Ar;
  var Er;
  var Cr = { name: "css", register: $i, targetTest: function(t17) {
    return t17.style && t17.nodeType;
  }, init: function(t17, e2, i2, r2, n2) {
    var s2, a2, o2, u2, h2, l2, f2, c2, p2, d2, _2, m2, g2, v2, y2, w2, b2, x2, T2, O2 = this._props, M2 = t17.style, D2 = i2.vars.startAt;
    for (f2 in xi || $i(), e2) if ("autoRound" !== f2 && (a2 = e2[f2], !mt[f2] || !He(f2, e2, i2, r2, t17, n2))) {
      if (h2 = typeof a2, l2 = fr[f2], "function" === h2 && (h2 = typeof (a2 = a2.call(i2, r2, t17, n2))), "string" === h2 && ~a2.indexOf("random(") && (a2 = me(a2)), l2) l2(this, t17, f2, a2, i2) && (y2 = 1);
      else if ("--" === f2.substr(0, 2)) s2 = (getComputedStyle(t17).getPropertyValue(f2) + "").trim(), a2 += "", ke.lastIndex = 0, ke.test(s2) || (c2 = ae(s2), p2 = ae(a2)), p2 ? c2 !== p2 && (s2 = ar(t17, f2, s2, p2) + p2) : c2 && (a2 += c2), this.add(M2, "setProperty", s2, a2, r2, n2, 0, 0, f2), O2.push(f2);
      else if ("undefined" !== h2) {
        if (D2 && f2 in D2 ? (s2 = "function" == typeof D2[f2] ? D2[f2].call(i2, r2, t17, n2) : D2[f2], f2 in R.units && !ae(s2) && (s2 += R.units[f2]), "=" === (s2 + "").charAt(1) && (s2 = or(t17, f2))) : s2 = or(t17, f2), u2 = parseFloat(s2), (d2 = "string" === h2 && "=" === a2.charAt(1) ? +(a2.charAt(0) + "1") : 0) && (a2 = a2.substr(2)), o2 = parseFloat(a2), f2 in Ii && ("autoAlpha" === f2 && (1 === u2 && "hidden" === or(t17, "visibility") && o2 && (u2 = 0), nr(this, M2, "visibility", u2 ? "inherit" : "hidden", o2 ? "inherit" : "hidden", !o2)), "scale" !== f2 && "transform" !== f2 && ~(f2 = Ii[f2]).indexOf(",") && (f2 = f2.split(",")[0])), _2 = f2 in Di) if (m2 || ((g2 = t17._gsap).renderTransform && !e2.parseTransform || vr(t17, e2.parseTransform), v2 = false !== e2.smoothOrigin && g2.smooth, (m2 = this._pt = new di(this._pt, M2, Vi, 0, 1, g2.renderTransform, g2, 0, -1)).dep = 1), "scale" === f2) this._pt = new di(this._pt, g2, "scaleY", g2.scaleY, (d2 ? d2 * o2 : o2 - g2.scaleY) || 0), O2.push("scaleY", f2), f2 += "X";
        else {
          if ("transformOrigin" === f2) {
            b2 = void 0, x2 = void 0, T2 = void 0, b2 = (w2 = a2).split(" "), x2 = b2[0], T2 = b2[1] || "50%", "top" !== x2 && "bottom" !== x2 && "left" !== T2 && "right" !== T2 || (w2 = x2, x2 = T2, T2 = w2), b2[0] = hr[x2] || x2, b2[1] = hr[T2] || T2, a2 = b2.join(" "), g2.svg ? gr(t17, a2, 0, v2, 0, this) : ((p2 = parseFloat(a2.split(" ")[2]) || 0) !== g2.zOrigin && nr(this, g2, "zOrigin", g2.zOrigin, p2), nr(this, M2, f2, yr(s2), yr(a2)));
            continue;
          }
          if ("svgOrigin" === f2) {
            gr(t17, a2, 1, v2, 0, this);
            continue;
          }
          if (f2 in pr) {
            Or(this, g2, f2, u2, a2, d2);
            continue;
          }
          if ("smoothOrigin" === f2) {
            nr(this, g2, "smooth", g2.smooth, a2);
            continue;
          }
          if ("force3D" === f2) {
            g2[f2] = a2;
            continue;
          }
          if ("transform" === f2) {
            Dr(this, a2, t17);
            continue;
          }
        }
        else f2 in M2 || (f2 = Ji(f2) || f2);
        if (_2 || (o2 || 0 === o2) && (u2 || 0 === u2) && !Pi.test(a2) && f2 in M2) o2 || (o2 = 0), (c2 = (s2 + "").substr((u2 + "").length)) !== (p2 = ae(a2) || (f2 in R.units ? R.units[f2] : c2)) && (u2 = ar(t17, f2, s2, p2)), this._pt = new di(this._pt, _2 ? g2 : M2, f2, u2, d2 ? d2 * o2 : o2 - u2, _2 || "px" !== p2 && "zIndex" !== f2 || false === e2.autoRound ? Li : Fi), this._pt.u = p2 || 0, c2 !== p2 && (this._pt.b = s2, this._pt.r = zi);
        else if (f2 in M2) ur.call(this, t17, f2, s2, a2);
        else {
          if (!(f2 in t17)) {
            ht(f2, a2);
            continue;
          }
          this.add(t17, f2, s2 || t17[f2], a2, r2, n2);
        }
        O2.push(f2);
      }
    }
    y2 && pi(this);
  }, get: or, aliases: Ii, getSetter: function(t17, e2, i2) {
    var r2 = Ii[e2];
    return r2 && r2.indexOf(",") < 0 && (e2 = r2), e2 in Di && e2 !== Qi && (t17._gsap.x || or(t17, "x")) ? i2 && Oi === i2 ? "scale" === e2 ? Yi : Ui : (Oi = i2 || {}, "scale" === e2 ? Xi : Wi) : t17.style && !V(t17.style[e2]) ? ji : ~e2.indexOf("-") ? Ni : si(t17, e2);
  }, core: { _removeProperty: rr, _getMatrix: mr } };
  vi.utils.checkPrefix = Ji, Er = Ot((kr = "x,y,z,scale,scaleX,scaleY,xPercent,yPercent") + "," + (Ar = "rotation,rotationX,rotationY,skewX,skewY") + ",transform,transformOrigin,svgOrigin,force3D,smoothOrigin,transformPerspective", (function(t17) {
    Di[t17] = 1;
  })), Ot(Ar, (function(t17) {
    R.units[t17] = "deg", pr[t17] = 1;
  })), Ii[Er[13]] = kr + "," + Ar, Ot("0:translateX,1:translateY,2:translateZ,8:rotate,8:rotationZ,8:rotateZ,9:rotateX,10:rotateY", (function(t17) {
    var e2 = t17.split(":");
    Ii[e2[1]] = Er[e2[0]];
  })), Ot("x,y,z,top,right,bottom,left,width,height,fontSize,padding,margin,perspective", (function(t17) {
    R.units[t17] = "px";
  })), vi.registerPlugin(Cr);
  var Sr = vi.registerPlugin(Cr) || vi;
  Sr.core.Tween;
  var Pr = getComputedStyle(document.body).getPropertyValue("--type-line-opacity");
  var Ir = class {
    constructor(t17) {
      __publicField(this, "DOM", { el: null, imageWrap: null, image: null, number: null, title: null, intro: null, description: null });
      this.DOM.el = t17, this.DOM.imageWrap = this.DOM.el.querySelector(".article__img-wrap"), this.DOM.image = this.DOM.el.querySelector(".article__img"), this.DOM.number = this.DOM.el.querySelector(".article__number"), this.DOM.title = this.DOM.el.querySelector(".article__title"), this.DOM.intro = this.DOM.el.querySelector(".article__intro"), this.DOM.description = this.DOM.el.querySelector(".article__description");
    }
  };
  var Lr = class {
    constructor(t17) {
      __publicField(this, "DOM", { el: null, image: null, title: null, description: null, article: null });
      __publicField(this, "article");
      this.DOM.el = t17, this.DOM.image = this.DOM.el.querySelector(".item__img"), this.DOM.title = this.DOM.el.querySelector(".item__caption-title"), this.DOM.description = this.DOM.el.querySelector(".item__caption-description"), this.DOM.article = document.getElementById(this.DOM.el.dataset.article), this.article = new Ir(this.DOM.article);
      const e2 = { duration: 1, ease: "expo" };
      this.DOM.el.addEventListener("mouseenter", (() => {
        vi.timeline({ defaults: e2 }).to([this.DOM.image, this.DOM.title, this.DOM.description], { y: (t18) => 8 * t18 - 4 });
      })), this.DOM.el.addEventListener("mouseleave", (() => {
        vi.timeline({ defaults: e2 }).to([this.DOM.image, this.DOM.title, this.DOM.description], { y: 0 });
      }));
    }
  };
  ((t17 = "img") => new Promise(((e2) => {
    n(document.querySelectorAll(t17), { background: true }, e2);
  })))(".item__img, .article__img").then((() => document.body.classList.remove("loading")));
  var Rr = new class {
    constructor(t17) {
      __publicField(this, "DOM", {});
      this.DOM.el = t17, this.DOM.lines = [...document.querySelectorAll(".type__line")];
    }
    in() {
      return Sr.timeline({ paused: true }).to(this.DOM.el, { duration: 1.4, ease: "power2.inOut", scale: 2.7, rotate: -90 }).to(this.DOM.lines, { keyframes: [{ x: "20%", duration: 1, ease: "power1.inOut" }, { x: "-200%", duration: 1.5, ease: "power1.in" }], stagger: 0.04 }, 0).to(this.DOM.lines, { keyframes: [{ opacity: 1, duration: 1, ease: "power1.in" }, { opacity: 0, duration: 1.5, ease: "power1.in" }] }, 0);
    }
    out() {
      return Sr.timeline({ paused: true }).to(this.DOM.el, { duration: 1.4, ease: "power2.inOut", scale: 1, rotate: 0 }, 1.2).to(this.DOM.lines, { duration: 2.3, ease: "back", x: "0%", stagger: -0.04 }, 0).to(this.DOM.lines, { keyframes: [{ opacity: 1, duration: 1, ease: "power1.in" }, { opacity: Pr, duration: 1.5, ease: "power1.in" }] }, 0);
    }
  }(document.querySelector("[data-type-transition]"));
  var zr = false;
  var Fr = document.querySelector(".frame");
  var Br = [];
  var qr = -1;
  var jr = document.querySelector(".item-wrap");
  [...jr.querySelectorAll(".item")].forEach(((t17) => {
    const e2 = new Lr(t17);
    Br.push(e2), e2.DOM.el.addEventListener("click", (() => Nr(e2)));
  }));
  var Nr = (t17) => {
    if (zr) return;
    zr = true, qr = Br.indexOf(t17);
    const e2 = vi.timeline({ onComplete: () => zr = false });
    e2.addLabel("start", 0).addLabel("typeTransition", 0.3).addLabel("articleOpening", 0.75 * Rr.in().totalDuration() + e2.labels.typeTransition).to(Br.map(((t18) => t18.DOM.el)), { duration: 0.8, ease: "power2.inOut", opacity: 0, y: (t18) => t18 % 2 ? "25%" : "-25%" }, "start").to(Fr, { duration: 0.8, ease: "power3", opacity: 0, onComplete: () => vi.set(Fr, { pointerEvents: "none" }) }, "start").add(Rr.in().play(), "typeTransition").add((() => {
      vi.set(Ur, { pointerEvents: "auto" }), vi.set(jr, { pointerEvents: "none" }), Br[qr].DOM.article.classList.add("article--current");
    }), "articleOpening").to(Ur, { duration: 0.7, opacity: 1 }, "articleOpening").set([t17.article.DOM.title, t17.article.DOM.number, t17.article.DOM.intro, t17.article.DOM.description], { opacity: 0, y: "50%" }, "articleOpening").set(t17.article.DOM.imageWrap, { y: "100%" }, 2).set(t17.article.DOM.image, { y: "-100%" }, 2).to([t17.article.DOM.title, t17.article.DOM.number, t17.article.DOM.intro, t17.article.DOM.description], { duration: 1, ease: "expo", opacity: 1, y: "0%", stagger: 0.04 }, "articleOpening").to([t17.article.DOM.imageWrap, t17.article.DOM.image], { duration: 1, ease: "expo", y: "0%" }, "articleOpening");
  };
  var Ur = document.querySelector(".back");
  Ur.addEventListener("click", (() => (() => {
    if (zr) return;
    zr = true;
    const t17 = Br[qr], e2 = vi.timeline({ onComplete: () => zr = false });
    e2.addLabel("start", 0).addLabel("typeTransition", 0.5).addLabel("showItems", 0.7 * Rr.out().totalDuration() + e2.labels.typeTransition).to(Ur, { duration: 0.7, ease: "power1", opacity: 0 }, "start").to([t17.article.DOM.title, t17.article.DOM.number, t17.article.DOM.intro, t17.article.DOM.description], { duration: 1, ease: "power4.in", opacity: 0, y: "50%", stagger: -0.04 }, "start").to(t17.article.DOM.imageWrap, { duration: 1, ease: "power4.in", y: "100%" }, "start").to(t17.article.DOM.image, { duration: 1, ease: "power4.in", y: "-100%" }, "start").add((() => {
      vi.set(Ur, { pointerEvents: "none" }), vi.set(jr, { pointerEvents: "auto" }), t17.DOM.article.classList.remove("article--current");
    })).add(Rr.out().play(), "typeTransition").to(Fr, { duration: 0.8, ease: "power3", opacity: 1, onStart: () => vi.set(Fr, { pointerEvents: "auto" }) }, "showItems").to(Br.map(((t18) => t18.DOM.el)), { duration: 1, ease: "power3.inOut", opacity: 1, y: "0%" }, "showItems");
  })()));
})();
/*!
 * GSAP 3.7.1
 * https://greensock.com
 *
 * @license Copyright 2008-2021, GreenSock. All rights reserved.
 * Subject to the terms at https://greensock.com/standard-license or for
 * Club GreenSock members, the agreement issued with that membership.
 * @author: Jack Doyle, jack@greensock.com
*/

}
];
