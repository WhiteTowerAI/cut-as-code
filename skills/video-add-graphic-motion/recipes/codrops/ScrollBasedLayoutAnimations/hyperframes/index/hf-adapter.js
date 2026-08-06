/* Original Codrops project: ScrollBasedLayoutAnimations. */
/* Generated deterministic HyperFrames adapter for codrops-scrollbasedlayoutanimations-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"scroll","duration":8,"actions":[]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]"],"data-layout-allow-occlusion":[".oh__inner"],"data-layout-ignore":["main > section:nth-of-type(1) > div"]};
  const SOURCE_BODY = "\n\t\t<main>\n\t\t\t<div class=\"frame\">\n\t\t\t\t<div class=\"frame__title\"> \n\t\t\t\t\t<h1 class=\"frame__title-main\">On-Scroll Image Layout Animations</h1> \n\t\t\t\t\t<a aria-label=\"Back to the article\" class=\"frame__title-back\" href=\"https://tympanus.net/codrops/?p=72941\"> \n\t\t\t\t\t\t<span class=\"oh__inner\">Back to the article</span> \n\t\t\t\t\t\t<svg width=\"18px\" height=\"18px\" viewBox=\"0 0 24 24\"><path vector-effect=\"non-scaling-stroke\" d=\"M18.25 15.5a.75.75 0 00.75-.75v-9a.75.75 0 00-.75-.75h-9a.75.75 0 000 1.5h7.19L6.22 16.72a.75.75 0 101.06 1.06L17.5 7.56v7.19c0 .414.336.75.75.75z\"></path>\n\t\t\t\t\t\t</svg>\n\t\t\t\t\t</a>\n\t\t\t\t</div>\n\t\t\t\t<a class=\"frame__prev\" href=\"https://tympanus.net/Development/TextBlockTransitions/\">Previous demo</a>\n\t\t\t</div>\n\t\t\t<section class=\"project project--intro\">\n\t\t\t\t<span class=\"project__label project__label--name\">Project</span>\n\t\t\t\t<span class=\"project__name\">AI Art</span>\n\t\t\t\t<span class=\"project__label project__label--date\">Date</span>\n\t\t\t\t<span class=\"project__date\">July, 2023</span>\n\t\t\t\t<h2 class=\"project__title\">\n\t\t\t\t\t<span class=\"project__title-line\">Creativity</span>\n\t\t\t\t\t<span class=\"project__title-line\">Redefined</span>\n\t\t\t\t</h2>\n\t\t\t\t<span class=\"project__label project__label--mission\">Mission</span>\n\t\t\t\t<div class=\"project__mission\">\n\t\t\t\t\t<p>The AI-Art Project is a transformative initiative dedicated to exploring the immense impact of AI-generated art on the art world and artists. We aim to discover and promote exceptional AI-generated artworks that push the boundaries of creativity, redefine traditional practices, and provoke thought. </p>\n\t\t\t\t\t<p>Through collaborations with artists, workshops, and educational programs, we empower artists to leverage AI as a tool for exploration, expanding their artistic horizons and embracing new forms of expression.</p>\n\t\t\t\t</div>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap\">\n\t\t\t\t<div class=\"gallery gallery--row\" id=\"gallery-1\">\n\t\t\t\t\t<div class=\"gallery__item gallery__item--s\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--m\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--l\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--xl gallery__item--center\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--l\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--m\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item--s\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">\n\t\t\t\t\t\tWithin this meticulously arranged AI-generated ensemble lies a tantalizing facade, captivating our gaze. Yet, as we search for the soul of human expression, we question whether algorithms can truly embody the essence of authentic art.\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--left\">\n\t\t\t\t<span class=\"project__label project__label--default\">Ethical Considerations</span>\n\t\t\t\t<p>The emergence of AI-generated art raises ethical questions and concerns. One of the key challenges is navigating the boundaries of authorship and ownership. Determining the role of AI algorithms and their creators in the artistic process, as well as addressing issues of attribution and intellectual property, requires careful deliberation. Additionally, ensuring that AI-generated art does not perpetuate bias, discrimination, or harmful content is crucial for fostering a responsible and inclusive artistic landscape.</p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap gallery-wrap--large\">\n\t\t\t\t<div class=\"gallery gallery--grid gallery--breakout\" id=\"gallery-2\">\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/8.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/7.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/15.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/9.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/12.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/14.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/10.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/13.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"gallery__item gallery__item-cut\"><div class=\"gallery__item-inner\" style=\"background-image:url(img/11.jpg)\"></div></div>\n\t\t\t\t\t<div class=\"caption\">\n\t\t\t\t\t\t<p>Devoid of inherent knowledge, the language model relies solely on probabilities to craft a peculiar vision. As a result, the earrings hang in curious defiance of physics, inviting us to ponder the implications of relinquishing human understanding in the pursuit of artificial creativity.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--right\">\n\t\t\t\t<span class=\"project__label project__label--default\">Preserving Artistic Identity</span>\n\t\t\t\t<p>While AI offers new avenues for artistic exploration, there is a concern that it may overshadow or replace human creativity. Balancing the integration of AI tools and techniques with preserving the unique perspectives, emotional depth, and artistic identity of human artists is a significant challenge. Striking the right balance between AI-generated art and the irreplaceable human touch requires thoughtful consideration and an ongoing dialogue between artists, technologists, and the wider art community.</p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap\">\n\t\t\t\t<div class=\"gallery gallery--grid10\" id=\"gallery-3\">\n\t\t\t\t\t<div class=\"gallery__item pos-1\" style=\"background-image:url(img/16.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-2\" style=\"background-image:url(img/17.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-3\" style=\"background-image:url(img/18.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-4\" style=\"background-image:url(img/30.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-5\" style=\"background-image:url(img/20.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-6\" style=\"background-image:url(img/21.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-7\" style=\"background-image:url(img/22.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-8\" style=\"background-image:url(img/23.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-9\" style=\"background-image:url(img/24.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-10\" style=\"background-image:url(img/25.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-11\" style=\"background-image:url(img/26.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-12\" style=\"background-image:url(img/31.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-13\" style=\"background-image:url(img/28.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-14\" style=\"background-image:url(img/29.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-15\" style=\"background-image:url(img/19.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item pos-16\" style=\"background-image:url(img/27.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">The Art of Perfection?</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details\">\n\t\t\t\t<span class=\"project__label project__label--default\">Societal Impact</span>\n\t\t\t\t<p>As AI-generated art becomes more prevalent, its long-term impact on the art market, art institutions, and the broader societal perception of art needs to be carefully examined. Understanding the implications of AI-generated art for art sales, copyright laws, and the dynamics of the art market is crucial for shaping future policies and practices. Additionally, exploring the ways in which AI-generated art can democratize artistic expression and challenge traditional hierarchies is an ongoing challenge that requires proactive engagement and collaboration.</p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap gallery-wrap--dense\">\n\t\t\t\t<div class=\"gallery gallery--stack gallery--stack-inverse gallery--stack-dark\" id=\"gallery-4\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/33.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/34.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/35.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/36.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/37.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/38.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">\n\t\t\t\t\t\t<p>AI-generated art captivates with varied creations, sometimes senseless, yet impressively enigmatic.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"gallery-wrap gallery-wrap--dense\">\n\t\t\t\t<div class=\"gallery gallery--stack gallery--stack-glass\" id=\"gallery-5\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/39.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/40.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/41.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/42.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/43.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/44.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">\n\t\t\t\t\t\t<p>In the realm of unpredictable algorithms, some variations may appear random or without purpose, challenging traditional notions of beauty and meaning.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<div class=\"gallery-wrap gallery-wrap--dense\">\n\t\t\t\t<div class=\"gallery gallery--stack gallery--stack-inverse gallery--stack-scale gallery--stack-dark\" id=\"gallery-6\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/45.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/46.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/47.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/48.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/49.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/50.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">\n\t\t\t\t\t\t<p>This uncharted territory challenges artists and art enthusiasts alike, igniting debates about the role of intention and chance in the artistic process.</p>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--right\">\n\t\t\t\t<span class=\"project__label project__label--default\">Unmasking the Void of Authenticity</span>\n\t\t\t\t<p>While AI-generated art showcases impressive technical prowess, it leaves behind an unsettling void in the quest for authenticity. As humans, we seek the genuine touch of human hands and the depth of emotional connection embedded within traditional art forms. The lack of human essence in AI-generated creations may leave us yearning for the profound human expression that sparks true resonance, evoking a sense of emptiness in the face of machine-driven artistry.</p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap\">\n\t\t\t\t<div class=\"gallery gallery--gridtiny\" id=\"gallery-7\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/59.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/60.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/61.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/51.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/52.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/53.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/54.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/55.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/56.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/57.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/58.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">What is creativity?</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--left\">\n\t\t\t\t<span class=\"project__label project__label--default\">Photographic Flaws in Perfect Harmony</span>\n\t\t\t\t<p>In the realm of AI-generated photography, the quest for flawlessness inadvertently unveils a striking paradox - the absence of authentic imperfections. Even in the most human-like subjects, wrinkles and blemishes appear too immaculate, leaving us yearning for the raw, unfiltered beauty that only true imperfection can evoke. </p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap\">\n\t\t\t\t<div class=\"gallery gallery--bento\" id=\"gallery-8\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/64.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/63.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/62.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/69.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/65.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/67.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/68.jpg)\"></div>\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/66.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">Perfect Imperfections</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--right\">\n\t\t\t\t<span class=\"project__label project__label--default\">Moving forward</span>\n\t\t\t\t<p>As we conclude this transformative project, we are left with profound questions that continue to shape our understanding of AI-generated art and its place in the artistic landscape. How do we reconcile the precision of algorithms with the intangible spark of human creativity? Can machines truly grasp the depth of emotion and meaning that art evokes within us? And as AI continues to advance, how do we preserve the authenticity and soul that define artistic expression? </p>\n\t\t\t</section>\n\t\t\t<section class=\"project project--details project--left\">\n\t\t\t\t<span class=\"project__label project__label--default\">Photo credits</span>\n\t\t\t\t<p>All images except one were generated with <a href=\"https://midjourney.com\">Midjourney</a>. The only \"real\" image was taken by <a href=\"https://unsplash.com/@karsten116\">Karsten Winegeart</a>. <strong>Can you spot which one?</strong> Hint: it's one of the portraits in the last image grid. Let us know via <a href=\"https://twitter.com/intent/tweet?text=@codrops\">@codrops</a>.</p>\n\t\t\t</section>\n\t\t\t<div class=\"gallery-wrap\">\n\t\t\t\t<div class=\"gallery gallery--one\" id=\"gallery-9\">\n\t\t\t\t\t<div class=\"gallery__item\" style=\"background-image:url(img/70.jpg)\"></div>\n\t\t\t\t\t<div class=\"caption\">Made by @codrops</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"project project--details project--left\">\n\t\t\t\t<p>Like AI-generated art? Get a <a href=\"https://tympanus.net/codrops/2023/06/12/free-ai-generated-images-vol-1/\">free AI Art collection</a> plus prompts to get inspired.</p>\n\t\t\t</section>\n\t\t</main>\n\t\t\n\t\t\n\t\t\n\t\t\n\t\t\n\t\t\n\t\t\n\t";
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
