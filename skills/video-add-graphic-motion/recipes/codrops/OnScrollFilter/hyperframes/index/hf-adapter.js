/* Original Codrops project: OnScrollFilter. */
/* Generated deterministic HyperFrames adapter for codrops-onscrollfilter-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"scroll","duration":8,"actions":[]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]"],"data-layout-allow-occlusion":[".oh__inner"]};
  const SOURCE_BODY = "\n\t\t<main>\n\t\t\t<div class=\"frame\">\n\t\t\t\t<a class=\"frame__back\" href=\"https://tympanus.net/codrops/?p=72802\">Back to the article</a>\n\t\t\t\t<a class=\"frame__prev\" href=\"https://tympanus.net/Tutorials/WebGLBulge/\">Previous demo</a>\n\t\t\t</div>\n\t\t\t<div class=\"intro\"> \n\t\t\t\t<h1 class=\"intro__title\"> \n\t\t\t\t\t<span class=\"intro__title-pre\">On-Scroll Filter Effect</span> \n\t\t\t\t\t<span class=\"intro__title-sub\">Based on <a href=\"https://codepen.io/supah/pen/poxmKPQ\">this demo</a> by Fabio Ottaviani</span> \n\t\t\t\t</h1> \n\t\t\t\t<span class=\"intro__info\">Scroll moderately to fully experience the animations</span> \n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Foot</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Print</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-1\">\n\t\t\t\t\t<svg class=\"content__img content__img--1\" width=\"896\" height=\"1344\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 896 1344\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.03\" numOctaves=\"3\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"50\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"820\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/1.jpg\" width=\"896\" height=\"1344\" mask=\"url(#circleMask)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">As darkness cloaked the forsaken city, the crew huddled together, their eyes darting nervously into the murky abyss.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Storm</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Born</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-2\">\n\t\t\t\t\t<svg class=\"content__img content__img--2\" width=\"1000\" height=\"450\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 1000 450\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter2\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.1\" numOctaves=\"1\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" result=\"displacement\" scale=\"100\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t\t  <feMorphology operator=\"dilate\" radius=\"2\" result=\"morph\" in=\"displacement\"/>\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask2\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"950\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter2);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/2.jpg\" width=\"1000\" height=\"450\" mask=\"url(#circleMask2)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">The skies above were tinged with an otherworldly hue, casting an eerie glow on the jagged rock formations below.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Hind</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Sight</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-3\">\n\t\t\t\t\t<svg class=\"content__img content__img--3\" width=\"1000\" height=\"560\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 1000 560\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter3\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.02\" numOctaves=\"3\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"80\" result=\"displacement\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"pathMask\">\n\t\t\t\t\t\t\t<path d=\"M 0 280 Q 500 280 1000 280 Q 500 280 0 280\" data-value-final=\"M 0 280 Q 500 800 1000 280 Q 500 -200 0 280\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter3);\"/>\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/3.jpg\" width=\"1000\" height=\"560\" mask=\"url(#pathMask)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">The Forbidden Planet was not merely an ancient world lost to time—it was a prison, a gateway to realms beyond their understanding. They had unwittingly set loose a force that threatened not only their lives but the very fabric of the universe itself. The desert planet, a riddle waiting to be unraveled, held its secrets close, leaving the crew with a lingering sense of awe and dread, a constant reminder of their insignificance in the face of an unforgiving universe.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Heart</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Ache</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-4\">\n\t\t\t\t\t<svg class=\"content__img content__img--4\" width=\"1400\" height=\"560\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 1400 560\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter4\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.5\" numOctaves=\"1\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"50\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask4\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"770\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter4);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/4.jpg\" width=\"1400\" height=\"560\" mask=\"url(#circleMask4)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">Sandstorms raged across the barren landscape, their fury obscuring the horizon and leaving a veil of gritty particles that stung the skin. The sun, a distant orb of fiery intensity, cast an unforgiving glare that scorched the unforgiving land.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Night</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Fall</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-5\">\n\t\t\t\t\t<svg class=\"content__img content__img--5\" width=\"680\" height=\"920\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 680 920\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter5\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.1\" numOctaves=\"3\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"150\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask5\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"580\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter5);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/5.jpg\" width=\"680\" height=\"920\" mask=\"url(#circleMask5)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">From the shadows, strange shapes began to emerge, haunting figures that seemed to materialize from the very fabric of the night.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Fire</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Storm</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-6\">\n\t\t\t\t\t<svg class=\"content__img content__img--6\" width=\"1000\" height=\"1000\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 1000 1000\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter6\">\n\t\t\t\t\t\t  <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.01\" numOctaves=\"3\" result=\"noise\" />\n\t\t\t\t\t\t  <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" result=\"displacement\" scale=\"150\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t\t  <feGaussianBlur in=\"displacement\" stdDeviation=\"10\" /> \n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask6\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"720\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter6);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/6.jpg\" width=\"1000\" height=\"1000\" mask=\"url(#circleMask6)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">Visions of a vibrant world, once teeming with life, flickered in her mind's eye, only to be devoured by the relentless sands of time.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content-wrap\">\n\t\t\t\t<div class=\"content\">\n\t\t\t\t\t<div class=\"title-wrap\">\n\t\t\t\t\t\t<span class=\"title title--up\">Star</span>\n\t\t\t\t\t\t<span class=\"title title--down\">Light</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content content--layout content--layout-7\">\n\t\t\t\t\t<svg class=\"content__img content__img--7\" width=\"1400\" height=\"560\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" viewBox=\"0 0 1400 560\">\n\t\t\t\t\t  <defs>\n\t\t\t\t\t    <filter id=\"displacementFilter7\">\n\t\t\t\t\t      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.03\" numOctaves=\"1\" result=\"noise\" />\n\t\t\t\t\t      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"120\" xChannelSelector=\"R\" yChannelSelector=\"G\" />\n\t\t\t\t\t    </filter>\n\t\t\t\t\t    <mask id=\"circleMask7\">\n\t\t\t\t\t      <circle cx=\"50%\" cy=\"50%\" r=\"0\" data-value-final=\"770\" fill=\"white\" class=\"mask\" style=\"filter: url(#displacementFilter7);\" />\n\t\t\t\t\t    </mask>\n\t\t\t\t\t  </defs>\n\t\t\t\t\t  <image xlink:href=\"img/7.jpg\" width=\"1400\" height=\"560\" mask=\"url(#circleMask7)\" />\n\t\t\t\t\t</svg>\n\t\t\t\t\t<p class=\"content__text\">The desert world had claimed another fragment of history, another chapter buried beneath the sands of oblivion.</p>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"content\">\n\t\t\t\t<h2 class=\"content__title\">More you might like</h2>\n\t\t\t\t<div class=\"card-wrap\">\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<a href=\"http://tympanus.net/Development/GridToSlider/\" class=\"card__image\" style=\"background-image:none\"></a>\n\t\t\t\t\t\t<h3 class=\"card__title\"><a href=\"http://tympanus.net/Development/GridToSlider/\">Ideas for Grid to Slideshow Switch Animations</a></h3>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<a href=\"http://tympanus.net/Development/OnScrollTypographyAnimations/\" class=\"card__image\" style=\"background-image:none\"></a>\n\t\t\t\t\t\t<h3 class=\"card__title\"><a href=\"http://tympanus.net/Development/OnScrollTypographyAnimations/\">Ideas for Grid to Slideshow Switch Animations</a></h3>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<a href=\"http://tympanus.net/Development/ScrollPanels/\" class=\"card__image\" style=\"background-image:none\"></a>\n\t\t\t\t\t\t<h3 class=\"card__title\"><a href=\"http://tympanus.net/Development/ScrollPanels/\">Smooth Panel Scroll Effects</a></h3>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<p class=\"credits\">Made by <a href=\"https://twitter.com/codrops\">@codrops</a></p>\n\t\t</main>\n\t\t\n\t\t\n\t\t\n\t\t\n\t\t\n\t\t\n\t";
  const SOURCE_BODY_ATTRIBUTES = [...document.body.attributes]
    .map((attribute) => [attribute.name, attribute.value]);
  const FONT_WARMUP = document.fonts
    ? Promise.all([...document.fonts].map((fontFace) => fontFace.load().catch(() => null)))
    : Promise.resolve();
  const nativeDocumentGetAnimations = typeof document.getAnimations === "function"
    ? document.getAnimations.bind(document)
    : null;
  const NativeCSSAnimation = window.CSSAnimation;
  const NativeCSSTransition = window.CSSTransition;
  let state = null;
  let seekGeneration = 0;
  let renderedTime = null;

  function isCssManagedAnimation(animation) {
    return (NativeCSSAnimation && animation instanceof NativeCSSAnimation)
      || (NativeCSSTransition && animation instanceof NativeCSSTransition);
  }

  if (TRACK_CSS && nativeDocumentGetAnimations) {
    document.getAnimations = (...args) => nativeDocumentGetAnimations(...args)
      .filter((animation) => !isCssManagedAnimation(animation));
  }

  function applyAuditAllowances() {
    for (const [attribute, selectors] of Object.entries(AUDIT_ALLOWANCES)) {
      for (const selector of selectors) {
        for (const element of document.querySelectorAll(selector)) {
          if (attribute !== "data-layout-ignore-text") {
            element.setAttribute(attribute, "");
            continue;
          }
          for (const node of [...element.childNodes]) {
            if (node.nodeType !== 3 || !node.textContent?.trim()) continue;
            const wrapper = document.createElement("span");
            wrapper.style.display = "contents";
            wrapper.setAttribute("data-layout-ignore", "");
            node.replaceWith(wrapper);
            wrapper.append(node);
          }
        }
      }
    }
  }

  function createState() {
    let seed = 0x6d2b79f5;
    let nextTaskId = 1;
    const tasks = new Map();
    const listeners = [];
    const observers = new Set();
    const webglContexts = new Set();
    const animations = new Map();
    const nativeAdd = EventTarget.prototype.addEventListener;
    const nativeRemove = EventTarget.prototype.removeEventListener;
    const nativeGetContext = HTMLCanvasElement.prototype.getContext;
    const NativeImage = window.Image;
    const NativeResizeObserver = window.ResizeObserver;
    const NativeIntersectionObserver = window.IntersectionObserver;
    const NativeWheelEvent = window.WheelEvent;
    const NativePointerEvent = window.PointerEvent;
    const NativeMouseEvent = window.MouseEvent;
    const nativeScrollTo = typeof window.scrollTo === "function" ? window.scrollTo.bind(window) : null;
    const nativeRequestAnimationFrame = window.requestAnimationFrame;
    const nativeCancelAnimationFrame = window.cancelAnimationFrame;
    const nativeSetTimeout = window.setTimeout;
    const nativeClearTimeout = window.clearTimeout;
    const nativeSetInterval = window.setInterval;
    const nativeClearInterval = window.clearInterval;
    const nativeDateNow = Date.now;
    const NativeWebSocket = window.WebSocket;
    let disposed = false;
    let runtimeGlobalsInstalled = false;
    let actionCursor = 0;
    let scrollExtent = null;
    const imageReadiness = [];

    function trackedAdd(type, listener, options) {
      if (this === document && type === "DOMContentLoaded" && document.readyState !== "loading") {
        const event = new Event("DOMContentLoaded");
        if (typeof listener === "function") listener.call(this, event);
        else if (listener && typeof listener.handleEvent === "function") listener.handleEvent(event);
        return;
      }
      listeners.push({ target: this, type, listener, options });
      return nativeAdd.call(this, type, listener, options);
    }

    function trackedGetContext(type, options) {
      const webgl = /^(?:webgl2?|experimental-webgl)$/i.test(String(type));
      const resolvedOptions = webgl
        ? { ...(options && typeof options === "object" ? options : {}), preserveDrawingBuffer: true }
        : options;
      const context = nativeGetContext.call(this, type, resolvedOptions);
      if (webgl && context) webglContexts.add(context);
      return context;
    }

    function TrackedImage(...args) {
      const image = new NativeImage(...args);
      const readiness = new Promise((resolve) => {
        const settle = (event) => {
          nativeRemove.call(image, "load", settle);
          nativeRemove.call(image, "error", settle);
          if (disposed) {
            event.stopImmediatePropagation?.();
            resolve();
            return;
          }
          const restoreAfterEvent = !runtimeGlobalsInstalled;
          installRuntimeGlobals();
          nativeSetTimeout(() => {
            if (restoreAfterEvent) restoreRuntimeGlobals();
            resolve();
          }, 0);
        };
        nativeAdd.call(image, "load", settle);
        nativeAdd.call(image, "error", settle);
      });
      imageReadiness.push({ image, readiness });
      return image;
    }
    if (NativeImage) {
      TrackedImage.prototype = NativeImage.prototype;
      Object.setPrototypeOf(TrackedImage, NativeImage);
    }

    function installRuntimeGlobals() {
      if (runtimeGlobalsInstalled) return;
      runtimeGlobalsInstalled = true;
      window.requestAnimationFrame = api.requestAnimationFrame;
      window.cancelAnimationFrame = api.cancelAnimationFrame;
      window.setTimeout = api.setTimeout;
      window.clearTimeout = api.clearTimeout;
      window.setInterval = api.setInterval;
      window.clearInterval = api.clearInterval;
      if (NativeImage) window.Image = TrackedImage;
      Date.now = api.dateNow;
      window.WebSocket = undefined;
    }

    function restoreRuntimeGlobals() {
      if (!runtimeGlobalsInstalled) return;
      runtimeGlobalsInstalled = false;
      window.requestAnimationFrame = nativeRequestAnimationFrame;
      window.cancelAnimationFrame = nativeCancelAnimationFrame;
      window.setTimeout = nativeSetTimeout;
      window.clearTimeout = nativeClearTimeout;
      window.setInterval = nativeSetInterval;
      window.clearInterval = nativeClearInterval;
      if (window.Image === TrackedImage) window.Image = NativeImage;
      Date.now = nativeDateNow;
      window.WebSocket = NativeWebSocket;
    }

    class DeterministicResizeObserver {
      constructor(callback) {
        this.callback = callback;
        this.targets = new Set();
        observers.add(this);
      }
      observe(target) {
        this.targets.add(target);
        this.callback([{ target, contentRect: target.getBoundingClientRect() }], this);
      }
      unobserve(target) { this.targets.delete(target); }
      disconnect() { this.targets.clear(); observers.delete(this); }
    }

    class DeterministicIntersectionObserver {
      constructor(callback) {
        this.callback = callback;
        this.targets = new Set();
        this.root = null;
        this.rootMargin = "0px";
        this.thresholds = [0];
        observers.add(this);
      }
      observe(target) {
        this.targets.add(target);
        const rect = target.getBoundingClientRect();
        this.callback([{
          target,
          isIntersecting: true,
          intersectionRatio: 1,
          boundingClientRect: rect,
          intersectionRect: rect,
          rootBounds: null,
          time: api.now(),
        }], this);
      }
      unobserve(target) { this.targets.delete(target); }
      disconnect() { this.targets.clear(); observers.delete(this); }
      takeRecords() { return []; }
    }

    function smoothstep(value) {
      const clamped = Math.max(0, Math.min(1, value));
      return clamped * clamped * (3 - 2 * clamped);
    }

    function dispatchWheel(deltaY) {
      if (!NativeWheelEvent) return;
      window.dispatchEvent(new NativeWheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        deltaY,
        deltaMode: 0,
      }));
    }

    function dispatchPointer(time) {
      const progress = smoothstep(time / Math.max(FRAME_STEP, INTERACTION.duration || api.duration));
      const inverse = 1 - progress;
      const points = INTERACTION.pointerPath || [
        [0.12, 0.65], [0.32, 0.18], [0.72, 0.82], [0.88, 0.36],
      ];
      const x = (
        inverse * inverse * inverse * points[0][0]
        + 3 * inverse * inverse * progress * points[1][0]
        + 3 * inverse * progress * progress * points[2][0]
        + progress * progress * progress * points[3][0]
      ) * window.innerWidth;
      const y = (
        inverse * inverse * inverse * points[0][1]
        + 3 * inverse * inverse * progress * points[1][1]
        + 3 * inverse * progress * progress * points[2][1]
        + progress * progress * progress * points[3][1]
      ) * window.innerHeight;
      const target = document.elementFromPoint(x, y) || document.body;
      const init = { bubbles: true, cancelable: true, clientX: x, clientY: y };
      if (NativePointerEvent) target.dispatchEvent(new NativePointerEvent("pointermove", init));
      if (NativeMouseEvent) target.dispatchEvent(new NativeMouseEvent("mousemove", init));
    }

    function dispatchAction(action) {
      if (action.type === "wheel") {
        dispatchWheel(Number(action.deltaY) || 480);
        return;
      }
      const targets = document.querySelectorAll(action.selector || "body");
      const target = targets[Math.max(0, Number(action.index) || 0)] || targets[0];
      if (target && typeof target.click === "function") target.click();
    }

    const api = {
      time: 0,
      duration: 8,
      seek(time) { return queueSeek(time); },
      random() {
        seed |= 0;
        seed = (seed + 0x6d2b79f5) | 0;
        let value = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
        return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
      },
      now() { return api.time * 1000; },
      dateNow() { return 1700000000000 + api.now(); },
      requestAnimationFrame(callback) {
        const id = nextTaskId++;
        tasks.set(id, { id, kind: "raf", at: api.time + FRAME_STEP, callback });
        return id;
      },
      cancelAnimationFrame(id) { tasks.delete(id); },
      setTimeout(callback, delay = 0, ...args) {
        const id = nextTaskId++;
        tasks.set(id, { id, kind: "timeout", at: api.time + Math.max(0, Number(delay)) / 1000, callback, args });
        return id;
      },
      clearTimeout(id) { tasks.delete(id); },
      setInterval(callback, delay = 0, ...args) {
        const id = nextTaskId++;
        const interval = Math.max(FRAME_STEP, Number(delay) / 1000);
        tasks.set(id, { id, kind: "interval", at: api.time + interval, interval, callback, args });
        return id;
      },
      clearInterval(id) { tasks.delete(id); },
      captureAnimations() {
        if (!TRACK_CSS || !nativeDocumentGetAnimations) return;
        void document.body.offsetWidth;
        const current = new Set(nativeDocumentGetAnimations());
        for (const animation of animations.keys()) {
          if (!current.has(animation)) animations.delete(animation);
        }
        for (const animation of current) {
          if (animations.has(animation)) continue;
          try { animation.pause(); } catch {}
          animations.set(animation, api.time);
        }
      },
      seekAnimations(target) {
        api.captureAnimations();
        for (const [animation, startedAt] of animations) {
          try { animation.currentTime = Math.max(0, target - startedAt) * 1000; } catch {}
        }
      },
      applyInteraction(target) {
        if (INTERACTION.mode === "scroll") {
          const progress = smoothstep(
            (target + (Number(INTERACTION.startAt) || 0))
              / Math.max(FRAME_STEP, INTERACTION.duration || api.duration),
          );
          scrollExtent = Math.max(
            scrollExtent ?? 0,
            0,
            document.documentElement.scrollHeight - window.innerHeight,
            document.body.scrollHeight - window.innerHeight,
          );
          const maxScroll = scrollExtent;
          const scrollY = Math.max(0, maxScroll * progress);
          if (nativeScrollTo) nativeScrollTo(0, scrollY);
          document.documentElement.scrollTop = scrollY;
          document.body.scrollTop = scrollY;
          document.body.dispatchEvent(new Event("scroll"));
          window.dispatchEvent(new Event("scroll"));
          window.ScrollSmoother?.get?.()?.scrollTop?.(scrollY);
        } else if (INTERACTION.mode === "pointer") {
          dispatchPointer(target);
        }
        const actions = INTERACTION.actions || [];
        while (actionCursor < actions.length && actions[actionCursor].at <= target + 1e-9) {
          dispatchAction(actions[actionCursor++]);
        }
      },
      dispose() {
        disposed = true;
        try { window.ScrollTrigger?.disable?.(true, true); } catch {}
        restoreRuntimeGlobals();
        if (EventTarget.prototype.addEventListener === trackedAdd) {
          EventTarget.prototype.addEventListener = nativeAdd;
        }
        if (HTMLCanvasElement.prototype.getContext === trackedGetContext) {
          HTMLCanvasElement.prototype.getContext = nativeGetContext;
        }
        if (window.ResizeObserver === DeterministicResizeObserver) {
          window.ResizeObserver = NativeResizeObserver;
        }
        if (window.IntersectionObserver === DeterministicIntersectionObserver) {
          window.IntersectionObserver = NativeIntersectionObserver;
        }
        for (const item of listeners) nativeRemove.call(item.target, item.type, item.listener, item.options);
        listeners.length = 0;
        for (const observer of [...observers]) observer.disconnect();
        for (const context of webglContexts) {
          try { context.getExtension("WEBGL_lose_context")?.loseContext(); } catch {}
        }
        webglContexts.clear();
        tasks.clear();
      },
      runTasksTo(target) {
        let guard = 0;
        while (guard++ < 100000) {
          const due = [...tasks.values()]
            .filter((task) => task.at <= target + 1e-9)
            .sort((a, b) => a.at - b.at || a.id - b.id)[0];
          if (!due) break;
          tasks.delete(due.id);
          api.time = due.at;
          due.callback(...(due.kind === "raf" ? [api.now()] : due.args || []));
          api.captureAnimations();
          if (due.kind === "interval" && !tasks.has(due.id)) {
            due.at += due.interval;
            tasks.set(due.id, due);
          }
        }
        api.time = target;
      },
      async runTo(target, isCurrent, from = -FRAME_STEP) {
        const step = (time) => {
          if (!isCurrent()) return false;
          installRuntimeGlobals();
          try {
            api.time = time;
            if (INTERACTION.mode === "scroll") api.runTasksTo(time);
            api.applyInteraction(time);
            if (INTERACTION.mode !== "scroll") api.runTasksTo(time);
            api.seekAnimations(time);
          } finally {
            restoreRuntimeGlobals();
          }
          return isCurrent();
        };
        const frameCount = Math.floor(target / FRAME_STEP + 1e-9);
        let frameTime = from;
        const firstFrame = Math.max(0, Math.floor(from / FRAME_STEP + 1e-9) + 1);
        for (let frame = firstFrame; frame <= frameCount; frame += 1) {
          frameTime = frame * FRAME_STEP;
          if (!step(frameTime)) return false;
          if (INTERACTION.mode !== "scroll") await Promise.resolve();
        }
        if (target > frameTime + 1e-9) {
          if (!step(target)) return false;
          if (INTERACTION.mode !== "scroll") await Promise.resolve();
        }
        return true;
      },
      runToAsync(target, isCurrent) {
        return new Promise((resolve, reject) => {
          installRuntimeGlobals();
          try {
            api.time = 0;
            api.applyInteraction(0);
            api.runTasksTo(0);
            api.seekAnimations(0);
          } finally {
            restoreRuntimeGlobals();
          }
          async function replay() {
            if (!isCurrent()) {
              restoreRuntimeGlobals();
              resolve(false);
              return;
            }
            try {
              scrollExtent = Math.max(
                0,
                document.documentElement.scrollHeight,
                document.body.scrollHeight,
              ) - window.innerHeight;
              resolve(await api.runTo(target, isCurrent));
            } catch (error) {
              reject(error);
            } finally {
              restoreRuntimeGlobals();
            }
          }
          queueMicrotask(() => queueMicrotask(() => {
            const pendingImages = imageReadiness
              .filter(({ image }) => image.currentSrc || image.getAttribute?.("src"))
              .map(({ readiness }) => readiness);
            void document.body.offsetWidth;
            const pendingFonts = document.fonts
              ? [...document.fonts].map((fontFace) => fontFace.load().catch(() => null))
              : [];
            if (document.fonts) pendingFonts.push(document.fonts.ready);
            if (window.__hfWebFontReady) pendingFonts.push(window.__hfWebFontReady);
            Promise.all([...pendingFonts, ...pendingImages]).then(async () => {
              await Promise.resolve();
              if (document.fonts && document.body && typeof getComputedStyle === "function") {
                const usedFonts = new Map();
                for (const element of document.body.querySelectorAll("*")) {
                  const text = element.childElementCount === 0 ? element.textContent?.trim() : "";
                  const font = text && getComputedStyle(element).font;
                  if (font && !usedFonts.has(font)) usedFonts.set(font, text.slice(0, 128));
                }
                await Promise.all([...usedFonts].map(([font, text]) =>
                  document.fonts.load(font, text).catch(() => null)));
                await document.fonts.ready;
              }
              void document.body.offsetWidth;
              applyAuditAllowances();
              queueMicrotask(replay);
            }, reject).catch(reject);
          }));
        });
      },
      installRuntimeGlobals,
      restoreRuntimeGlobals,
    };

    EventTarget.prototype.addEventListener = trackedAdd;
    HTMLCanvasElement.prototype.getContext = trackedGetContext;
    if (NativeResizeObserver) window.ResizeObserver = DeterministicResizeObserver;
    if (NativeIntersectionObserver) window.IntersectionObserver = DeterministicIntersectionObserver;
    return api;
  }

  function reset() {
    if (state) state.dispose();
    for (const attribute of [...document.body.attributes]) {
      document.body.removeAttribute(attribute.name);
    }
    for (const [name, value] of SOURCE_BODY_ATTRIBUTES) document.body.setAttribute(name, value);
    document.body.innerHTML = SOURCE_BODY;
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    state = createState();
    window.__hf = state;
    state.installRuntimeGlobals();
    try {
      for (const factory of window.__hfRecipeFactories || []) factory(state);
    } finally {
      state.restoreRuntimeGlobals();
    }
    try { window.ScrollTrigger?.enable?.(); } catch {}
    applyAuditAllowances();
    state.captureAnimations();
  }

  async function renderAt(time) {
    const target = Math.max(0, Math.min(8, Number(time) || 0));
    const generation = ++seekGeneration;
    if (state && renderedTime !== null && Math.abs(target - renderedTime) <= 1e-9) {
      applyAuditAllowances();
      return true;
    }
    if (state && renderedTime !== null && target > renderedTime + 1e-9) {
      const current = state;
      const complete = await current.runTo(
        target,
        () => state === current && generation === seekGeneration,
        renderedTime,
      );
      if (complete && state === current && generation === seekGeneration) {
        applyAuditAllowances();
        renderedTime = target;
      }
      return complete;
    }
    renderedTime = null;
    reset();
    const current = state;
    const complete = await current.runToAsync(
      target,
      () => state === current && generation === seekGeneration,
    );
    if (complete && state === current && generation === seekGeneration) {
      applyAuditAllowances();
      renderedTime = target;
    }
    return complete;
  }

  let requestedTime = window.__hfThreeTime || 0;
  let fontsReady = false;
  let pendingSeek = Promise.resolve();

  function queueSeek(time) {
    requestedTime = time;
    pendingSeek = Promise.resolve(fontsReady ? renderAt(requestedTime) : readyForSeek);
    return pendingSeek;
  }

  window.addEventListener("hf-seek", (event) => {
    const completion = queueSeek(event.detail.time);
    event.detail.waitUntil?.(completion);
  });
  const readyForSeek = FONT_WARMUP.then(() => {
    fontsReady = true;
    return renderAt(requestedTime);
  });
  pendingSeek = readyForSeek;
  window.__hfWaitForSeekCompletion = () => pendingSeek;
})();
