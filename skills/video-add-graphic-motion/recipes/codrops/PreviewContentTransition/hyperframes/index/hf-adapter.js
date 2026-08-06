/* Original Codrops project: PreviewContentTransition. */
/* Generated deterministic HyperFrames adapter for codrops-previewcontenttransition-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"pointer","duration":8,"actions":[{"at":2.4,"type":"click","selector":".item__enter"}]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]",".item__excerpt",".content__text"],"data-layout-allow-occlusion":[".oh__inner"],"data-layout-ignore":[".heading--item"]};
  const SOURCE_BODY = " <main> <div class=\"frame\"> <div class=\"frame__title-wrap\"> <h1 class=\"frame__title\">Preview to Content Transition</h1> <p class=\"frame__tagline\">An experimental page transition concept for magazines and blogs where a preview item opens for a full page view.</p> </div> <nav class=\"frame__links\"> <a href=\"https://tympanus.net/Development/LettersAnimationLayout/\">Previous demo</a> <a href=\"https://tympanus.net/codrops/?p=54117\">Article</a> <a href=\"https://github.com/codrops/PreviewContentTransition/\">GitHub</a> </nav> </div> <section class=\"items\"> <article class=\"item\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(1.d7eef1a3.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Hypercritical</span> <span data-splitting=\"\">mass</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Caroline Balliste</span></span> <span class=\"item__meta-row\"><span>April &mdash; 2023</span></span> </div> <div class=\"item__excerpt\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge.</p> <a class=\"item__excerpt-link\" href=\"#content-1\"><span>Read more</span></a> </div> </article> <article class=\"item item--invert\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(2.02d9df87.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Proselyte</span> <span data-splitting=\"\">times</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Andrew Lewis</span></span> <span class=\"item__meta-row\"><span>March &mdash; 2023</span></span> </div> <div class=\"item__excerpt\"> <p>Seeing, therefore, that those books, and those in great abundance, which are likeliest to taint both life and doctrine, cannot be suppressed without the fall of learning and of all ability in disputation, and that these books of either sort are most and soonest catching to the learned.</p> <a class=\"item__excerpt-link\" href=\"#content-2\"><span>Read more</span></a> </div> </article> <article class=\"item\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(3.aa978150.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Arcadias</span> <span data-splitting=\"\">future</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Frank W. Marigold</span></span> <span class=\"item__meta-row\"><span>February &mdash; 2023</span></span> </div> <div class=\"item__excerpt\"> <p>Besides another inconvenience, if learned men be the first receivers out of books and dispreaders both of vice and error, how shall the licensers themselves be confided in, unless we can confer upon them, or they assume to themselves above all others in the land, the grace of infallibility and uncorruptedness?</p> <a class=\"item__excerpt-link\" href=\"#content-3\"><span>Read more</span></a> </div> </article> <article class=\"item item--invert\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(4.8bd42ed5.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Epistletic</span> <span data-splitting=\"\">crave</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Andrew Lewis</span> <span class=\"item__meta-row\"><span>January &mdash; 2023</span> </span></span></div> <div class=\"item__excerpt\"> <p>If every action, which is good or evil in man at ripe years, were to be under pittance and prescription and compulsion, what were virtue but a name, what praise could be then due to well-doing, what gramercy to be sober, just, or continent? </p> <a class=\"item__excerpt-link\" href=\"#content-4\"><span>Read more</span></a> </div> </article> <article class=\"item\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(5.949baea4.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Temperance</span> <span data-splitting=\"\">prime</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Sally Mullis</span></span> <span class=\"item__meta-row\"><span>December &mdash; 2022</span></span> </div> <div class=\"item__excerpt\"> <p>And albeit whatever thing we hear or see, sitting, walking, travelling, or conversing, may be fitly called our book, and is of the same effect that writings are, yet grant the thing to be prohibited were only books, it appears that this Order hitherto is far insufficient to the end which it intends.</p> <a class=\"item__excerpt-link\" href=\"#content-5\"><span>Read more</span></a> </div> </article> <article class=\"item item--invert\"> <div class=\"item__imgwrap\"> <div class=\"item__img\" style=\"background-image:url(6.924e64bf.jpg)\"></div> </div> <button class=\"item__enter unbutton\"> <svg class=\"item__enter-circle\" vector-effect=\"non-scaling-stroke\" width=\"800\" height=\"800\"><circle vector-effect=\"non-scaling-stroke\" cx=\"400\" cy=\"400\" r=\"150\"/></svg> </button> <h2 class=\"heading heading--item\"> <span data-splitting=\"\">Quantum</span> <span data-splitting=\"\">leap</span> </h2> <div class=\"item__meta\"> <span class=\"item__meta-row\"><span>By Lorenzo Augusto</span></span> <span class=\"item__meta-row\"><span>January &mdash; 2023</span></span> </div> <div class=\"item__excerpt\"> <p>And how can a man teach with authority, which is the life of teaching; how can he be a doctor in his book as he ought to be, or else had better be silent, whenas all he teaches, all he delivers, is but under the tuition, under the correction of his patriarchal licenser to blot or alter what precisely accords not with the hidebound humour which he calls his judgment?</p> <a class=\"item__excerpt-link\" href=\"#content-6\"><span>Read more</span></a> </div> </article> </section> <section class=\"content\"> <article class=\"content__article\" id=\"content-1\"> <h2 class=\"heading\"> <span data-splitting=\"\">Hypercritical</span> <span data-splitting=\"\">mass</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. </p> <p>These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made; and besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's; so apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"1.d7eef1a3.jpg\" alt=\"Some image\"> <p>And thus ye have the inventors and the original of book-licensing ripped up and drawn as lineally as any pedigree. We have it not, that can be heard of, from any ancient state, or polity or church; nor by any statute left us by our ancestors elder or later; nor from the modern custom of any reformed city or church abroad, but from the most anti-christian council and the most tyrannous inquisition that ever inquired.</p><p> Till then books were ever as freely admitted into the world as any other birth; the issue of the brain was no more stifled than the issue of the womb: no envious Juno sat cross-legged over the nativity of any man's intellectual offspring; but if it proved a monster, who denies, but that it was justly burnt, or sunk into the sea? </p><p>But that a book, in worse condition than a peccant soul, should be to stand before a jury ere it be born to the world, and undergo yet in darkness the judgment of Radamanth and his colleagues, ere it can pass the ferry backward into light, was never heard before, till that mysterious iniquity, provoked and troubled at the first entrance of Reformation, sought out new limbos and new hells wherein they might include our books also within the number of their damned. And this was the rare morsel so officiously snatched up, and so ill-favouredly imitated by our inquisiturient bishops, and the attendant minorites their chaplains. That ye like not now these most certain authors of this licensing order, and that all sinister intention was far distant from your thoughts, when ye were importuned the passing it, all men who know the integrity of your actions, and how ye honour truth, will clear ye readily.</p> </div> </article> <article class=\"content__article content__article--invert\" id=\"content-2\"> <h2 class=\"heading\"> <span data-splitting=\"\">Proselyte</span> <span data-splitting=\"\">times</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made; and besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's. </p><p>So apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"2.02d9df87.jpg\" alt=\"Some image\"> <p>They are not skilful considerers of human things, who imagine to remove sin by removing the matter of sin; for, besides that it is a huge heap increasing under the very act of diminishing, though some part of it may for a time be withdrawn from some persons, it cannot from all, in such a universal thing as books are; and when this is done, yet the sin remains entire. Though ye take from a covetous man all his treasure, he has yet one jewel left, ye cannot bereave him of his covetousness.</p><p> Banish all objects of lust, shut up all youth into the severest discipline that can be exercised in any hermitage, ye cannot make them chaste, that came not hither so; such great care and wisdom is required to the right managing of this point. Suppose we could expel sin by this means; look how much we thus expel of sin, so much we expel of virtue: for the matter of them both is the same; remove that, and ye remove them both alike.</p> </div> </article> <article class=\"content__article\" id=\"content-3\"> <h2 class=\"heading\"> <span data-splitting=\"\">Arcadias</span> <span data-splitting=\"\">future</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made.</p><p> And besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's; so apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"3.aa978150.jpg\" alt=\"Some image\"> <p>Nay, which is more lamentable, if the work of any deceased author, though never so famous in his lifetime and even to this day, come to their hands for licence to be printed, or reprinted, if there be found in his book one sentence of a venturous edge, uttered in the height of zeal (and who knows whether it might not be the dictate of a divine spirit?). </p><p>Yet not suiting with every low decrepit humour of their own, though it were Knox himself, the reformer of a kingdom, that spake it, they will not pardon him their dash: the sense of that great man shall to all posterity be lost, for the fearfulness or the presumptuous rashness of a perfunctory licenser. And to what an author this violence hath been lately done, and in what book of greatest consequence to be faithfully published, I could now instance, but shall forbear till a more convenient season.</p> </div> </article> <article class=\"content__article content__article--invert\" id=\"content-4\"> <h2 class=\"heading\"> <span data-splitting=\"\">Antiphonies</span> <span data-splitting=\"\">thought</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made; and besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's. </p><p>So apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"4.8bd42ed5.jpg\" alt=\"Some image\"> <p>And it is a particular disesteem of every knowing person alive, and most injurious to the written labours and monuments of the dead, so to me it seems an undervaluing and vilifying of the whole nation. I cannot set so light by all the invention, the art, the wit, the grave and solid judgment which is in England, as that it can be comprehended in any twenty capacities how good soever, much less that it should not pass except their superintendence be over it, except it be sifted and strained with their strainers, that it should be uncurrent without their manual stamp. </p><p>Truth and understanding are not such wares as to be monopolized and traded in by tickets and statutes and standards. We must not think to make a staple commodity of all the knowledge in the land, to mark and licence it like our broadcloth and our woolpacks. What is it but a servitude like that imposed by the Philistines, not to be allowed the sharpening of our own axes and coulters, but we must repair from all quarters to twenty licensing forges? </p><p>Had anyone written and divulged erroneous things and scandalous to honest life, misusing and forfeiting the esteem had of his reason among men, if after conviction this only censure were adjudged him that he should never henceforth write but what were first examined by an appointed officer, whose hand should be annexed to pass his credit for him that now he might be safely read; it could not be apprehended less than a disgraceful punishment. Whence to include the whole nation, and those that never yet thus offended, under such a diffident and suspectful prohibition, may plainly be understood what a disparagement it is. So much the more, whenas debtors and delinquents may walk abroad without a keeper, but unoffensive books must not stir forth without a visible jailer in their title.</p> </div> </article> <article class=\"content__article\" id=\"content-5\"> <h2 class=\"heading\"> <span data-splitting=\"\">Temperance</span> <span data-splitting=\"\">prime</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made; and besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's. </p><p>So apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"5.949baea4.jpg\" alt=\"Some image\"> <p>And in conclusion it reflects to the disrepute of our ministers also, of whose labours we should hope better, and of the proficiency which their flock reaps by them, than that after all this light of the Gospel which is, and is to be, and all this continual preaching, they should still be frequented with such an unprincipled, unedified and laic rabble, as that the whiff of every new pamphlet should stagger them out of their catechism and Christian walking. </p><p>This may have much reason to discourage the ministers when such a low conceit is had of all their exhortations, and the benefiting of their hearers, as that they are not thought fit to be turned loose to three sheets of paper without a licenser; that all the sermons, all the lectures preached, printed, vented in such numbers, and such volumes, as have now well nigh made all other books unsaleable, should not be armour enough against one single Enchiridion, without the castle of St. Angelo of an Imprimatur.</p> </div> </article> <article class=\"content__article content__article--invert\" id=\"content-6\"> <h2 class=\"heading\"> <span data-splitting=\"\">Quantum</span> <span data-splitting=\"\">leap</span> </h2> <div class=\"content__text\"> <p>Sometimes five Imprimaturs are seen together dialogue-wise in the piazza of one title-page, complimenting and ducking each to other with their shaven reverences, whether the author, who stands by in perplexity at the foot of his epistle, shall to the press or to the sponge. These are the pretty responsories, these are the dear antiphonies, that so bewitched of late our prelates and their chaplains with the goodly echo they made; and besotted us to the gay imitation of a lordly Imprimatur, one from Lambeth House, another from the west end of Paul's.</p><p> So apishly Romanizing, that the word of command still was set down in Latin; as if the learned grammatical pen that wrote it would cast no ink without Latin; or perhaps, as they thought, because no vulgar tongue was worthy to express the pure conceit of an Imprimatur, but rather, as I hope, for that our English, the language of men ever famous and foremost in the achievements of liberty, will not easily find servile letters enow to spell such a dictatory presumption English.</p> <img src=\"6.924e64bf.jpg\" alt=\"Some image\"> <p>Next, what more national corruption, for which England hears ill abroad, than household gluttony: who shall be the rectors of our daily rioting? And what shall be done to inhibit the multitudes that frequent those houses where drunkenness is sold and harboured? Our garments also should be referred to the licensing of some more sober workmasters to see them cut into a less wanton garb. </p><p>Who shall regulate all the mixed conversation of our youth, male and female together, as is the fashion of this country? Who shall still appoint what shall be discoursed, what presumed, and no further? Lastly, who shall forbid and separate all idle resort, all evil company? These things will be, and must be; but how they shall be least hurtful, how least enticing, herein consists the grave and governing wisdom of a state.</p> </div> </article> <button class=\"content__back unbutton\"> <svg width=\"108\" height=\"23\"><path stroke=\"#000\" fill=\"none\" d=\"M107.5 11.5H1.5m0 0c8.975-.536 15.087-1.364 18.336-2.484C23.086 7.896 26.64 5.39 30.5 1.5m-29 10c8.975.536 15.087 1.364 18.336 2.484 3.25 1.12 6.804 3.626 10.664 7.516\"/></svg> </button> </section> <div class=\"frame frame--footer\"> <p>Excerpts from <a href=\"https://www.gutenberg.org/files/608/608-h/608-h.htm\">Areopagitica</a> by John Milton, <a href=\"https://www.gutenberg.org/\">The Project Gutenberg</a></p> <p>Images from <a href=\"https://www.unsplash.com/\">Unsplash</a></p> <p><a href=\"https://twitter.com/codrops\">@codrops</a> 2021</p> </div> </main> <svg class=\"cursor\" width=\"80\" height=\"80\"><circle class=\"cursor__inner\" cx=\"40\" cy=\"40\" r=\"20\"/></svg>  ";
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
