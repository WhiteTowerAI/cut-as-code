/* Original Codrops project: 3DStackMotion. */
/* Generated deterministic HyperFrames adapter for codrops-3dstackmotion-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"scroll","duration":8,"actions":[]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]",".intro"],"data-layout-allow-occlusion":[".oh__inner"]};
  const SOURCE_BODY = "\n\t\t<main>\n\t\t\t<header class=\"frame\">\n\t\t\t\t<h1 class=\"frame__title\"><a href=\"https://tympanus.net/codrops/demos/?tag=3d\">#3D</a> <a href=\"https://tympanus.net/codrops/demos/?tag=stack\">#stack</a> Motion Effect on <a href=\"https://tympanus.net/codrops/demos/?tag=scroll\">#Scroll</a> <br>inspired by <a href=\"https://dribbble.com/shots/23641913-Looksrare-NFT-cards\">Looksrare: NFT cards</a></h1> \n\t\t\t\t<a class=\"frame__back\" href=\"https://tympanus.net/codrops/?p=75974\">Article</a>\n\t\t\t\t<a class=\"frame__archive\" href=\"https://tympanus.net/codrops/demos\">All demos</a>\n\t\t\t\t<a class=\"frame__sub\" href=\"https://tympanus.net/codrops/collective/\" aria-label=\"Subcribe to our frontend news\">\n\t\t\t\t\t<svg width=\"136\" height=\"136\" viewBox=\"0 0 136 136\">\n\t\t\t\t\t\t<path d=\"M126.102 47.94C123.846 49.0894 121.444 49.9281 118.962 50.4333C120.216 54.2766 120.866 58.2909 120.889 62.3333C120.803 68.1325 119.513 73.8505 117.1 79.1246C114.687 84.3988 111.205 89.114 106.873 92.9711C106.494 93.3234 106.19 93.7499 105.982 94.2244C105.774 94.6988 105.666 95.2109 105.665 95.7289V115.902L89.1179 105.362C88.6563 105.07 88.137 104.882 87.5957 104.811C87.0544 104.739 86.504 104.785 85.9823 104.947C80.1597 106.755 74.0971 107.672 68.0001 107.667C38.8357 107.667 15.1112 87.3422 15.1112 62.3333C15.1112 37.3245 38.8357 17 68.0001 17C73.8199 16.9993 79.6093 17.8391 85.189 19.4933C85.4247 16.9852 85.9965 14.5202 86.889 12.1645C80.7519 10.3744 74.393 9.45872 68.0001 9.44446C34.6801 9.44446 7.55566 33.1689 7.55566 62.3333C7.55566 91.4978 34.6801 115.222 68.0001 115.222C74.234 115.215 80.4373 114.351 86.4357 112.653L107.327 125.951C107.897 126.317 108.555 126.523 109.233 126.547C109.91 126.571 110.581 126.412 111.176 126.088C111.771 125.764 112.267 125.285 112.614 124.703C112.96 124.12 113.143 123.455 113.145 122.778V97.3533C117.871 92.8188 121.644 87.3845 124.239 81.3702C126.834 75.356 128.2 68.8834 128.256 62.3333C128.297 57.4523 127.57 52.5952 126.102 47.94Z\" />\n\t\t\t\t\t\t<path d=\"M113.333 41.5556C123.765 41.5556 132.222 33.0988 132.222 22.6667C132.222 12.2347 123.765 3.77783 113.333 3.77783C102.901 3.77783 94.4443 12.2347 94.4443 22.6667C94.4443 33.0988 102.901 41.5556 113.333 41.5556Z\"/>\n\t\t\t\t\t</svg>\n\t\t\t\t\t<div class=\"modal\">\n\t\t\t\t\t\t<strong>Psst...</strong>🤫 craving the latest in frontend wizardry? 🧙 Subscribe to the <strong>Codrops Collective</strong> for a bi-weekly blast of the best frontend articles, design trends, videos, and demo highlights that'll make your screen pop! 💥 Spice up your inbox with our mix of creativity and must-reads to stay ahead of the curve. 💌\n\t\t\t\t\t</div>\n\t\t\t\t</a>\n\t\t\t\t<div class=\"frame__hire\">Want magic like this on your website? <a href=\"mailto:contact@codrops.com\">Hire us</a></div>\n\t\t\t</header>\n\t\t\t<div class=\"intro\">\n\t\t\t\t<h2 class=\"intro__title\">The Next Evolution</h2>\n\t\t\t\t<p class=\"intro__hint\">Scroll into the future</p>\n\t\t\t\t<div class=\"grid\">\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Horizons</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Beyond Human Limits</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V1.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Explore the future where AI transforms imagination into reality.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">Tech Odyssey</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Unveiling Tomorrow</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V2.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Embark on a journey into the realm of cutting-edge technology reshaping our world.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">Digital Frontiers</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Pushing Boundaries</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V3.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Enter the realm where innovation meets possibility, shaping the future of humanity.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Nexus</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Bridging Realms</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V4.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Dive into the interconnected world of AI, where algorithms shape the future of human experience.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Innovate</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Pioneering Tomorrow</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V5.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Join the forefront of AI innovation, where creativity meets computational intelligence to shape a better future.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Horizons</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Beyond Human Limits</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V6.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Explore the future where AI transforms imagination into reality.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Frontier</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Exploring New Horizons</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V7.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Venture into uncharted territories where AI blazes trails towards unprecedented possibilities.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Visionary</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Envisioning Tomorrow</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V8.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Embrace the visionary realm of AI, where dreams of the future become the reality of today.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t<h3 class=\"card__title\">AI Odyssey</h3>\n\t\t\t\t\t\t<h4 class=\"card__subtitle\">Journey to Tomorrow</h4>\n\t\t\t\t\t\t<span class=\"card__meta\">V9.0</span>\n\t\t\t\t\t\t<p class=\"card__description\">Embark on an epic odyssey through the realms of AI, where innovation knows no bounds.</p>\n\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<h2 class=\"section-title\">A New Frontier</h2>\n\t\t\t<div class=\"wrap\">\n\t\t\t\t<div data-stack-1 class=\"wrap__inner\">\n\t\t\t\t\t<div class=\"content content--1\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<h2 class=\"section-title\">Chronicles of Circuitry</h2>\n\t\t\t<div class=\"wrap\">\n\t\t\t\t<div data-stack-2 class=\"wrap__inner\">\n\t\t\t\t\t<div class=\"content content--2\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<h2 class=\"section-title\">Synthetica Sapiens</h2>\n\t\t\t<div class=\"wrap\">\n\t\t\t\t<div data-stack-3 class=\"wrap__inner\">\n\t\t\t\t\t<div class=\"content content--3\">\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/1.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/2.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/3.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/4.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/5.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/6.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/7.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/8.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t\t<div class=\"card\">\n\t\t\t\t\t\t\t<div class=\"card__img\" style=\"background-image:url(img/9.jpg)\"></div>\n\t\t\t\t\t\t</div><!-- /card -->\n\t\t\t\t\t</div>\n\t\t\t\t</div>\n\t\t\t</div>\n\t\t\t<section class=\"outro\">\n\t\t\t\t<h2 class=\"outro__title\">More you might like</h2>\n\t\t\t\t<div class=\"card-wrap\">\n\t\t\t\t  <div class=\"card card--rel\">\n\t\t\t\t\t<a href=\"https://tympanus.net/codrops/2023/11/29/3d-glass-portal-card-effect-with-react-three-fiber-and-gaussian-splatting/\" class=\"card__img\" style=\"background-image: none;\"></a>\n\t\t\t\t\t<h3 class=\"card__title\">\n\t\t\t\t\t  <a href=\"https://tympanus.net/codrops/2023/11/29/3d-glass-portal-card-effect-with-react-three-fiber-and-gaussian-splatting/\">3D Glass Portal Card Effect with React Three Fiber and Gaussian Splatting</a>\n\t\t\t\t\t</h3>\n\t\t\t\t  </div>\n\t\t\t\t  <div class=\"card card--rel\">\n\t\t\t\t\t<a href=\"https://tympanus.net/Development/OnScrollColumnsRows/\" class=\"card__img\" style=\"\n\t\t\t\t\t\tbackground-image: none;\n\t\t\t\t\t  \"></a>\n\t\t\t\t\t<h3 class=\"card__title\">\n\t\t\t\t\t  <a href=\"https://tympanus.net/Development/OnScrollColumnsRows/\">On-Scroll Column & Row Animations</a>\n\t\t\t\t\t</h3>\n\t\t\t\t  </div>\n\t\t\t\t</div>\n\t\t\t</section>\n\t\t\t<p class=\"credits\">Made by <a href=\"https://twitter.com/codrops\">@codrops</a></p>\n\t\t</main>\n\t\t\n\t\t\n\t\t\n\t\t<!-- Image preloader -->\n\t\t\n\t\t\n\t\t<!-- Remove the following two lines if you don't want smooth scrolling -->\n\t\t\n\t\t\n\t\t\n\t";
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
