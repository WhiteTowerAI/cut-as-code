/* Original Codrops project: LayerMotionSlideshow. */
/* Generated deterministic HyperFrames adapter for codrops-layermotionslideshow-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"pointer","duration":8,"actions":[{"at":2.4,"type":"click","selector":".nav__arrow--next"}]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]"],"data-layout-allow-occlusion":[".oh__inner"],"data-layout-ignore":["span[class^=\"char\"]","main > div:nth-of-type(2) > div:nth-of-type(1) > h2 > span:nth-of-type(3) > span","main > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(5) > p:nth-of-type(2)"]};
  const RESET_RUNTIME_GLOBALS = ["_gsDefine","_gsQueue","TweenLite","TweenMax","TimelineLite","TimelineMax"];
  const SOURCE_BODY = "\n\t\t<svg class=\"hidden\">\n\t\t\t<symbol id=\"icon-arrow\" viewBox=\"0 0 24 24\">\n\t\t\t\t<title>arrow</title>\n\t\t\t\t<polygon points=\"6.3,12.8 20.9,12.8 20.9,11.2 6.3,11.2 10.2,7.2 9,6 3.1,12 9,18 10.2,16.8 \"/>\n\t\t\t</symbol>\n\t\t\t<symbol id=\"icon-nav\" viewBox=\"0 0 407 660\">\n\t\t\t\t<title>caret</title>\n\t\t\t\t<path d=\"M77 0L0 77l253 253L0 583l77 77 330-330z\"/>\n\t\t\t</symbol>\n\t\t</svg>\n\t\t<main>\n\t\t\t<p class=\"message\">Please view on desktop to see the full layout</p>\n\t\t\t<div class=\"frame\">\n\t\t\t\t<div class=\"frame__title-wrap\">\n\t\t\t\t\t<h1 class=\"frame__title\">Layer Motion Slideshow</h1>\n\t\t\t\t\t<div class=\"nav\">\n\t\t\t\t\t\t<div class=\"nav__counter\">\n\t\t\t\t\t\t\t<span>0</span>/<span>0</span>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t<div class=\"nav__arrows\">\n\t\t\t\t\t\t\t<button class=\"nav__arrow nav__arrow--prev\" data-hover>\n\t\t\t\t\t\t\t\t<svg class=\"icon icon--rotated icon--nav\"><use xlink:href=\"#icon-nav\"></use></svg>\n\t\t\t\t\t\t\t</button>\n\t\t\t\t\t\t\t<button class=\"nav__arrow nav__arrow--next\" data-hover>\n\t\t\t\t\t\t\t\t<svg class=\"icon icon--nav\"><use xlink:href=\"#icon-nav\"></use></svg>\n\t\t\t\t\t\t\t</button>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>\n\t\t\t\t</div><!-- /frame__title-wrap -->\n\t\t\t\t<div class=\"frame__links\">\n\t\t\t\t\t<a href=\"https://tympanus.net/Tutorials/InteractiveParticles/\" title=\"Previous Demo\" data-hover>Previous demo</a>\n\t\t\t\t\t<a href=\"https://tympanus.net/codrops/?p=37953\" title=\"Back to the article\" data-hover>Article</a>\n\t\t\t\t\t<a href=\"https://github.com/codrops/LayerMotionSlideshow/\" title=\"Find this project on GitHub\" data-hover>GitHub</a>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"index\" data-hover>index</div>\n\t\t\t</div><!--/frame-->\n\t\t\t<div class=\"slideshow\">\n\t\t\t\t<div class=\"slide slide--layout-1\" data-contentcolor=\"#e88655\">\n\t\t\t\t\t<div class=\"slide__figure slide__figure--main\" data-sort=\"3\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/1.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"2\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/3.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"4\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/2.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"1\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/4.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<h2 class=\"slide__title\">Monachopsis</h2>\n\t\t\t\t\t<div class=\"slide__text slide__text--right\">\n\t\t\t\t\t\t<p class=\"slide__text-meta\">by Andrew Moore on 2/21</p>\n\t\t\t\t\t\t<p class=\"slide__text-description\">Thoughts in time and out of season. The Hitchhiker stood by the side of the road and leveled his thumb in the calm calculus of reason. Hi. How you doin’?</p>\n\t\t\t\t\t\t<a class=\"slide__text-link\" data-hover href=\"#\">+</a>\n\t\t\t\t\t</div>\n\t\t\t\t\t<button class=\"slide__back\" data-hover>\n\t\t\t\t\t\t<svg class=\"icon icon--back\"><use xlink:href=\"#icon-arrow\"></use></svg>\n\t\t\t\t\t</button>\n\t\t\t\t\t<div class=\"slide__content\">\n\t\t\t\t\t\t<p>They would all have been delighted to have little Elfie with them in these last hours, but the fond grandfather could not spare her, and one of the girls, who had a message to deliver to Mrs. Abbott in the parlor, reported that the child lay fast asleep in Mr. Bellamy’s arms, while he was trying, at great inconvenience to himself, to write letters at a table, and black Candace sat patiently in the hall waiting for the long-delayed summons to put her little missy to bed.</p>\n\t\t\t\t\t\t<p>It was late when the day scholars went home, and the others went up-stairs to their rooms very quietly. They all had to pass the large corner room which was always given to visitors, and, although the light was turned very low, they could see through the half-closed door that Candace was trying to undress the little girl without waking her, and the senator, whose broad back was toward the door, was bending down to unbutton the little shoes, one of which he lifted and pressed to his lips just as the last pair of girls went by.</p>\n\t\t\t\t\t\t<p>The collector of old silver must have a pretty taste and a fine judgment. It is not an absolute law that age determines beauty. Hall-marks, though they denote date, do not guarantee excellence of design. Everything that bears the hall-mark of the Goldsmiths’ Hall of London is not beautiful, whether it be old or whether it be new. The connoisseur must digest the fact that the assay marks of the lion, the leopard’s head, the date-mark, and the rest, are so many official symbols, accurate as to date and sufficient guarantee as to the standard of the metal, but meaningless in regard to the art of the piece on which they stand. The assay offices are merely stamping machines. What Somerset House is to legal documents so the assay offices are to silver and gold plate, and nothing more. Hence the necessity of placing such mechanical control under Government supervision.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"slide slide--layout-2\" data-contentcolor=\"#7dd2dc\">\n\t\t\t\t\t<div class=\"slide__figure slide__figure--main\" data-sort=\"1\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/5.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"2\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/6.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"3\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/7.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"4\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/8.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<h2 class=\"slide__title\">Scabulous</h2>\n\t\t\t\t\t</h2>\n\t\t\t\t\t<div class=\"slide__text\">\n\t\t\t\t\t\t<p class=\"slide__text-meta\">by Carol Tuksinam on 2/21</p>\n\t\t\t\t\t\t<p class=\"slide__text-description\">Awake. Shake dreams from your hair my pretty child, my sweet one. Choose the day and choose the sign of your day the day's divinity. First thing you see.</p>\n\t\t\t\t\t\t<a class=\"slide__text-link\" data-hover href=\"#\">+</a>\n\t\t\t\t\t</div>\n\t\t\t\t\t<button class=\"slide__back\" data-hover>\n\t\t\t\t\t\t<svg class=\"icon icon--back\"><use xlink:href=\"#icon-arrow\"></use></svg>\n\t\t\t\t\t</button>\n\t\t\t\t\t<div class=\"slide__content\">\n\t\t\t\t\t\t<p>I have given sufficient space to marks in the present volume to indicate those used by the London and other assay offices. Some marks are given which do not appear elsewhere, and the arrangement of the tables should enable the beginner to come to a definite conclusion as to the date of his silver. In especial, the Table of variations in the shapes of shields in the hall-mark and standard-mark employed at the London Assay Office from the accession of Queen Elizabeth to the present day, is a feature not before given in so concise a form in any other volume.</p>\n\t\t\t\t\t\t<p>The marks on silver are stamped, the design thus appears in relief, while the edges of the shield on which it appears are sunk. The reproduction of this has offered a difficulty in illustration in all volumes on old silver. To print black letters or designs on a white background, although easy, is unsatisfactory. On the contrary, to print the raised design in white on a dead black background is not a realistic presentation of the mark as it appears to the eye. After many experiments I have reproduced the marks in a manner more closely approaching their actual appearance, and less suggestive of black-and-white designs on paper.</p>\n\t\t\t\t\t\t<p>The result of the somewhat chaotic alphabet marks has been to focus the attention of the collector too much on this particular side of the subject. The identification of marks, the outward symbols of time and place, have reduced the study of old silver to a somewhat lower plane than it should occupy by right. It is proper that such determining factors should have their place, but not the first place. There was a time when china collectors ignored paste and glaze and laid particular stress on marks, and it is a very happy accident that a great portion of English porcelain and much of English earthenware is unmarked. It has eventually led collectors to think for themselves and know something more of the technique and to learn to appreciate the artistic value of specimens of the potter’s art coming under their hand.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"slide slide--layout-3\" data-contentcolor=\"#dc9d7f\">\n\t\t\t\t\t<div class=\"slide__figure slide__figure--main\" data-sort=\"1\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/13.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"2\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/14.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"3\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/15.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"4\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/16.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<h2 class=\"slide__title\">Zenosyne</h2>\n\t\t\t\t\t</h2>\n\t\t\t\t\t<div class=\"slide__text\">\n\t\t\t\t\t\t<p class=\"slide__text-meta\">by Cindy Brighton on 2/21</p>\n\t\t\t\t\t\t<p class=\"slide__text-description\">A vast radiant beach and cooled jeweled moon. Couples naked race down by its quiet side. And we laugh like soft, mad children. Smug in the wooly cotton brains of infancy.</p>\n\t\t\t\t\t\t<a class=\"slide__text-link\" data-hover href=\"#\">+</a>\n\t\t\t\t\t</div>\n\t\t\t\t\t<button class=\"slide__back\" data-hover>\n\t\t\t\t\t\t<svg class=\"icon icon--back\"><use xlink:href=\"#icon-arrow\"></use></svg>\n\t\t\t\t\t</button>\n\t\t\t\t\t<div class=\"slide__content\">\n\t\t\t\t\t\t<p>What would one give for a few human touches in connexion with our old silver! We may imagine that our candlesticks of the year 1750 held the flickering wax candles which were guttering when the dawn broke when our great-great-grandfather lost his fortune at cards in the county of —, or maybe it was somebody else’s grandfather. But this is in the realms of fancy, and the fortune is literally fabulous. Why are there no George Morlands in the silversmith’s craft? Cannot the guilds dig out their romantic history from their archives? Just to think that our designer of candelabra and flagons ran a fine career on Hounslow Heath with gamesters and fighting men; or did he, just that once, have a duel with young Lord What’s-his-Name in the Guards, and pinked him? Did not the story get to White’s and to the Cocoa Tree Clubs, how the tradesman scored! But no such thing. All these initials of makers are empty of such vanities. We can do better with prints. Those who possess the engraved work of Ryland have the satisfaction of knowing that he was hounded by Bow Street runners and hid, like the modern Lefroy, at Stepney, and that he was hanged for forgery.</p>\n\t\t\t\t\t\t<p>The scene may readily be imagined. The second of May 1696 had been fixed by Parliament as the last day in which the crowns, half-crowns, and shillings were to be received in payment of taxes for face value. The guards had to be called in to keep order. The Exchequer was besieged by a vast multitude from dawn to midnight. The Act provided that the money was to be brought in by before the 4th of May. The 3rd was a Sunday, therefore Saturday, the 2nd of May, was actually the last day.</p>\n\t\t\t\t\t\t<p>A remarkable use of conjurators to confirm the evidence of witnesses occurs in 850 in a dispute between Cantius, Bishop of Siena, and Peter, Bishop of Arezzo, concerning certain parishes claimed by both. The occasion was a solemn one, for it was before a council held in Rome presided over jointly by Pope Leo IV. and the Emperor Louis II. Peter relied upon written charters, while Cantius produced witnesses. The Emperor pronounced the claim of the latter to be just, when he and twelve priests swore that the oaths of the witnesses were true and without deceit, whereupon the disputed parishes were adjudged to him.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"slide slide--layout-4\" data-contentcolor=\"#e4d0a2\">\n\t\t\t\t\t<div class=\"slide__figure slide__figure--main\" data-sort=\"4\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/9.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"3\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/10.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"2\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/11.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class=\"slide__figure slide__figure--box\" data-sort=\"1\">\n\t\t\t\t\t\t<div class=\"slide__figure-img\" style=\"background-image: url(img/12.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t\t<h2 class=\"slide__title\">Chrysalism</h2>\n\t\t\t\t\t</h2>\n\t\t\t\t\t<div class=\"slide__text slide__text--right\">\n\t\t\t\t\t\t<p class=\"slide__text-meta\">by Tamara Kaufmann on 2/21</p>\n\t\t\t\t\t\t<p class=\"slide__text-description\">The barns have stormed the windows kept, and only one of all the rest to dance and save us from the divine mockery of words.</p>\n\t\t\t\t\t\t<a class=\"slide__text-link\" data-hover href=\"#\">+</a>\n\t\t\t\t\t</div>\n\t\t\t\t\t<button class=\"slide__back\" data-hover>\n\t\t\t\t\t\t<svg class=\"icon icon--back\"><use xlink:href=\"#icon-arrow\"></use></svg>\n\t\t\t\t\t</button>\n\t\t\t\t\t<div class=\"slide__content\">\n\t\t\t\t\t\t<p>The intense veneration with which relics were regarded, however, caused them to be generally adopted as the most effective means of adding security to oaths, and so little respect was felt for the simple oath that, ere long, the adjuncts came to be looked upon as the essential feature, and the imprecation itself to be divested of binding force without them. Thus, in 680, when Ebroin, mayor of the palace of Burgundy, had defeated Martin, Duke of Austrasia, and desired to entice him from his refuge in the stronghold of Laon, two bishops were sent to him bearing the royal reliquaries, on which they swore that his life should be safe. Ebroin, however, had astutely removed the holy remains from their cases in advance, and when he thus got his enemy in his power, he held it but a venial indiscretion to expose Martin to a shameful death.</p>\n\t\t\t\t\t\t<p>It was late when the day scholars went home, and the others went up-stairs to their rooms very quietly. They all had to pass the large corner room which was always given to visitors, and, although the light was turned very low, they could see through the half-closed door that Candace was trying to undress the little girl without waking her, and the senator, whose broad back was toward the door, was bending down to unbutton the little shoes, one of which he lifted and pressed to his lips just as the last pair of girls went by.</p>\n\t\t\t\t\t\t<p>Notwithstanding the earnestness with which these teachings were enforced, it may readily be believed that the wild barbarian, who was clamoring for the restoration of stolen cattle, or the angry relatives, eager to share the wer-gild of some murdered kinsman, would scarce submit to be balked of their rights at the cost of simple perjury on the part of the criminal. We have seen that both before and after their conversion to Christianity they had little scruple in defiling the most sacred sanctions of the oath with cunning fraud, and they could repose little confidence in the most elaborate devices which superstition could invent to render perjury more to be dreaded than defeat. It was therefore natural that they should perpetuate an ancestral custom, which had arisen from the structure of their society, and which derived its guarantee from the solidarity of families alluded to above. This was the custom which was subsequently known as canonical compurgation, and which long remained a part of English jurisprudence, under the name of the Wager of Law. The defendant, when denying the allegation under oath,34 appeared surrounded by a number of companions—juratores, conjuratores, sacramentales, collaudantes, compurgatores, as they were variously termed—who swore, not to their knowledge of the facts, but as sharers and partakers in the oath of denial.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div><!--/slideshow-->\n\t\t</main>\n\t\t<div class=\"cursor\">\n\t\t\t<div class=\"cursor__inner cursor__inner--circle\"></div>\n\t\t\t<div class=\"cursor__inner cursor__inner--dot\"></div>\n\t\t</div>\n\t\t\n\t\t\n\t\t\n\t\t\n\t";
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
    for (const name of RESET_RUNTIME_GLOBALS) {
      try { delete window[name]; } catch {}
      if (Object.prototype.hasOwnProperty.call(window, name)) {
        try { window[name] = undefined; } catch {}
      }
    }
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
    if (state && renderedTime !== null && (target > renderedTime + 1e-9 || INTERACTION.bidirectionalSeek)) {
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
