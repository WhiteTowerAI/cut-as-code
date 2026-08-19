/* Original Codrops project: ColumnScroll. */
/* Generated deterministic HyperFrames adapter for codrops-columnscroll-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"scroll","duration":8,"actions":[]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]",".heading"],"data-layout-allow-occlusion":[".oh__inner"]};
  const SOURCE_BODY = "\n\t\t<main>\n\t\t\t<div class=\"frame\">\n\t\t\t\t<h1 class=\"frame__title\">Alternate Column Scroll</h1>\n\t\t\t\t<nav class=\"frame__links\">\n\t\t\t\t\t<a href=\"https://tympanus.net/codrops/2021/12/01/grid-zoom-layout/\">Previous demo</a>\n\t\t\t\t\t<a href=\"https://tympanus.net/codrops/?p=57959\">Article</a>\n\t\t\t\t\t<a href=\"https://github.com/codrops/ColumnScroll/\">GitHub</a>\n\t\t\t\t</nav>\n\t\t\t\t<button class=\"unbutton button-menu\" aria-label=\"Open the menu\"><span></span></button>\n\t\t\t</div>\n\t\t\t<h2 class=\"heading heading--up\">Jack Ruthless</h2>\n\t\t\t<h2 class=\"heading heading--down\">Jack Ruthless</h2>\n\t\t\t<div class=\"columns\" data-scroll-container=\"\">\n\t\t\t\t<div class=\"column-wrap column-wrap--height\">\n\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"2\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(1.53204a33.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Cyber Blue</span>\n\t\t\t\t\t\t\t\t<span>2011</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"5\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(2.27d18610.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Gnostic Will</span>\n\t\t\t\t\t\t\t\t<span>2012</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"8\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(3.6b4ec20c.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>French Kiss</span>\n\t\t\t\t\t\t\t\t<span>2013</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"11\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(4.07f2953c.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Half Life</span>\n\t\t\t\t\t\t\t\t<span>2014</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"14\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(5.39e01abe.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Love Boat</span>\n\t\t\t\t\t\t\t\t<span>2015</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"17\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(6.5c217eac.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Golden Ray</span>\n\t\t\t\t\t\t\t\t<span>2016</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"20\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(7.fef528f6.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Blame Game</span>\n\t\t\t\t\t\t\t\t<span>2017</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"23\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(8.02c4f715.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Lone Dust</span>\n\t\t\t\t\t\t\t\t<span>2018</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t</div><!-- /column -->\n\t\t\t\t</div><!-- /column-wrap -->\n\t\t\t\t<div class=\"column-wrap\">\n\t\t\t\t\t<div class=\"column\" data-scroll-section=\"\">\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"1\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(9.a517ebd6.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Lucky Wood</span>\n\t\t\t\t\t\t\t\t<span>2019</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"4\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(10.43f5b1d4.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Good Earth</span>\n\t\t\t\t\t\t\t\t<span>2020</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"7\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(11.83fbf0d4.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Empty Words</span>\n\t\t\t\t\t\t\t\t<span>2021</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"10\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(12.055337de.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Nonage Line</span>\n\t\t\t\t\t\t\t\t<span>2009</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"13\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(13.5642ddda.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Blue Hell</span>\n\t\t\t\t\t\t\t\t<span>2010</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"16\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(14.79f0177d.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Cold Blood</span>\n\t\t\t\t\t\t\t\t<span>2011</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"19\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(15.228c6374.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Tulip Heat</span>\n\t\t\t\t\t\t\t\t<span>2012</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"22\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(16.1dcbcdf6.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Red Wrath</span>\n\t\t\t\t\t\t\t\t<span>2013</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t</div><!-- /column -->\n\t\t\t\t</div>\n\t\t\t\t<div class=\"column-wrap column-wrap--height\">\n\t\t\t\t\t<div class=\"column\">\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"3\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(17.90c9874f.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Bold Human</span>\n\t\t\t\t\t\t\t\t<span>2014</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"6\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(18.c9bfd088.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Loyal Royal</span>\n\t\t\t\t\t\t\t\t<span>2015</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"9\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(19.4b11b6f8.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Lone Cone</span>\n\t\t\t\t\t\t\t\t<span>2016</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"12\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(20.310ba92a.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Dutch Green</span>\n\t\t\t\t\t\t\t\t<span>2017</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"15\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(21.be5e842c.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Valley Hill</span>\n\t\t\t\t\t\t\t\t<span>2018</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"18\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(22.be99dbec.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Kale Hale</span>\n\t\t\t\t\t\t\t\t<span>2019</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"21\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(23.abefde6e.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Fake Cake</span>\n\t\t\t\t\t\t\t\t<span>2020</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t\t<figure class=\"column__item\">\n\t\t\t\t\t\t\t<div class=\"column__item-imgwrap\" data-pos=\"24\">\n\t\t\t\t\t\t\t\t<div class=\"column__item-img\" style=\"background-image:url(24.452cae66.jpg)\"></div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<figcaption class=\"column__item-caption\">\n\t\t\t\t\t\t\t\t<span>Book Belly</span>\n\t\t\t\t\t\t\t\t<span>2021</span>\n\t\t\t\t\t\t\t</figcaption>\n\t\t\t\t\t\t</figure>\n\t\t\t\t\t</div><!-- /column -->\n\t\t\t\t</div><!-- /column-wrap -->\n\t\t\t</div><!-- columns -->\n\t\t\t<div class=\"content\">\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Lucky Wood</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Faith, you're driving me away\n\t\t\t\t\t\tYou do it every day\n\t\t\t\t\t\tYou don't mean it\n\t\t\t\t\t\tBut it hurts like hell</span>\n\t\t\t\t\t\t<span>2019</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Cyber Blue</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>My brain says I'm receiving pain\n\t\t\t\t\t\tA lack of oxygen\n\t\t\t\t\t\tFrom my life support\n\t\t\t\t\t\tMy iron lung\n\t\t\t\t\t\t</span>\n\t\t\t\t\t\t<span>2011</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Bold Human</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>We're too young to fall asleep\n\t\t\t\t\t\tToo cynical to speak\n\t\t\t\t\t\tWe are losing it\n\t\t\t\t\t\tCan't you tell?</span>\n\t\t\t\t\t\t<span>2014</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Good Earth</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>We scratch our eternal itch\n\t\t\t\t\t\tA twentieth century bitch\n\t\t\t\t\t\tAnd we are grateful for\n\t\t\t\t\t\tOur iron lung</span>\n\t\t\t\t\t\t<span>2020</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Gnostic Will</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>The head shrinkers\n\t\t\t\t\t\tThey want everything\n\t\t\t\t\t\tMy Uncle Bill\n\t\t\t\t\t\tMy Belisha beacon</span>\n\t\t\t\t\t\t<span>2012</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Loyal Royal</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>The head shrinkers\n\t\t\t\t\t\tThey want everything\n\t\t\t\t\t\tMy Uncle Bill\n\t\t\t\t\t\tMy Belisha beacon</span>\n\t\t\t\t\t\t<span>2015</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Empty Words</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Suck, suck your teenage thumb\n\t\t\t\t\t\tToilet trained and dumb\n\t\t\t\t\t\tWhen the power runs out\n\t\t\t\t\t\tWe'll just hum</span>\n\t\t\t\t\t\t<span>2021</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">French Kiss</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>This, this is our new song\n\t\t\t\t\t\tJust like the last one\n\t\t\t\t\t\tA total waste of time\n\t\t\t\t\t\tMy iron lung</span>\n\t\t\t\t\t\t<span>2013</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Lone Cone</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>And if you're frightened\n\t\t\t\t\t\tYou can be frightened\n\t\t\t\t\t\tYou can be, it's OK</span>\n\t\t\t\t\t\t<span>2016</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Nonage Line</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Lost in the mountain\n\t\t\t\t\t\tRust in my brain\n\t\t\t\t\t\tThe air is sacred here\n\t\t\t\t\t\tIn spite of your claim</span>\n\t\t\t\t\t\t<span>2009</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Half Life</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Up on the rooftops\n\t\t\t\t\t\tOut of reach\n\t\t\t\t\t\tTrickster is meaningless\n\t\t\t\t\t\tTrickster is weak</span>\n\t\t\t\t\t\t<span>2014</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Dutch Green</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>He's talking out the world\n\t\t\t\t\t\tTalking out the world</span>\n\t\t\t\t\t\t<span>2017</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Blue Hell</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Hey, hey, hey\n\t\t\t\t\t\tThis is only halfway\n\t\t\t\t\t\tHey, hey, hey\n\t\t\t\t\t\tThis is only halfway</span>\n\t\t\t\t\t\t<span>2010</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Love Boat</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>I wanted you so bad\n\t\t\t\t\t\tThat I couldn't say\n\t\t\t\t\t\tAll these things fall apart</span>\n\t\t\t\t\t\t<span>2015</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Valley Hill</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>We wanted out so bad\n\t\t\t\t\t\tWe couldn't say\n\t\t\t\t\t\tThese things fall apart</span>\n\t\t\t\t\t\t<span>2018</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Cold Blood</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Truant kids\n\t\t\t\t\t\tA can of brick dust worms\n\t\t\t\t\t\tWho do not want to climb down from\n\t\t\t\t\t\tTheir chestnut tree</span>\n\t\t\t\t\t\t<span>2011</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Golden Ray</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Long white gloves\n\t\t\t\t\t\tPolice tread carefully\n\t\t\t\t\t\tEscaped from the zoo\n\t\t\t\t\t\tThe perfect child facsimile is</span>\n\t\t\t\t\t\t<span>2016</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Kale Hale</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Please could you stop the noise? \n\t\t\t\t\t\t\tI'm trying to get some rest\n\t\t\t\t\t\t\tFrom all the unborn chicken \n\t\t\t\t\t\t\tvoices in my head</span>\n\t\t\t\t\t\t<span>2019</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Tulip Heat</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>What's that?\n\t\t\t\t\t\tI may be paranoid, but not an android</span>\n\t\t\t\t\t\t<span>2012</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Blame Game</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>When I am king you will be first against the wall\n\t\t\t\t\t\tWith your opinion which is of no consequence at all</span>\n\t\t\t\t\t\t<span>2017</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Fake Cake</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Ambition makes you look pretty ugly\n\t\t\t\t\t\tKicking and squealing, Gucci little piggy</span>\n\t\t\t\t\t\t<span>2017</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Red Wrath</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>You don't remember, you don't remember\n\t\t\t\t\t\tWhy don't you remember my name?</span>\n\t\t\t\t\t\t<span>2013</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Lone Dust</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Off with his head, man, off with his head, man\n\t\t\t\t\t\tWhy don't you remember my name? I guess he does</span>\n\t\t\t\t\t\t<span>2018</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<div class=\"content__item\">\n\t\t\t\t\t<h2 class=\"content__item-title\">Book Belly</h2>\n\t\t\t\t\t<div class=\"content__item-text\">\n\t\t\t\t\t\t<span>Rain down, rain down\n\t\t\t\t\t\tCome on, rain down on me\n\t\t\t\t\t\tFrom a great height\n\t\t\t\t\t\tFrom a great height, height</span>\n\t\t\t\t\t\t<span>2021</span>\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t\t<nav class=\"content__nav\">\n\t\t\t\t\t<div class=\"content__nav-wrap\">\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(25.049bd621.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(26.675918dc.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(27.4476f7fa.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(28.0569fb92.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(29.abaebfc5.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(30.fa44d3b8.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(31.66323178.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(32.9631aae9.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(33.aa63b1de.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(34.30a68e1d.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(35.e24ff5d2.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(36.41d47983.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(37.2cf0710e.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(38.993b1591.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(39.cd39e269.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(40.4cf142b0.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(41.8f39ace9.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(42.6de94ea0.jpg)\"></div>\n\t\t\t\t\t\t<div class=\"content__nav-item\" style=\"background-image:url(43.189506c3.jpg)\"></div>\n\t\t\t\t\t</div>\n\t\t\t\t</nav>\n\t\t\t\t<button class=\"unbutton button-back\"><svg viewbox=\"0 0 50 9\" width=\"100%\"><path d=\"M0 4.5l5-3M0 4.5l5 3M50 4.5h-77\"></path></svg></button>\n\t\t\t</div>\n\t\t</main>\n\t\t\n\t";
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
