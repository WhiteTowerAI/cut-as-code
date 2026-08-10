/* Original Codrops project: 3DCarousel. */
/* Generated deterministic HyperFrames adapter for codrops-3dcarousel-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"scroll","duration":8,"actions":[],"synchronousInitialization":true,"bidirectionalSeek":true};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]"],"data-layout-allow-occlusion":[".oh__inner"],"data-layout-ignore-text":[".scene__title .char"]};
  const RESET_RUNTIME_GLOBALS = ["gsap","Observer","ScrollTrigger","ScrollSmoother","ScrollToPlugin","SplitText","imagesLoaded"];
  const SOURCE_BODY = "\n    <header class=\"frame\">\n      <h1 class=\"frame__title\">On-Scroll 3D Carousel</h1>\n      <nav class=\"frame__links\">\n        <a class=\"line\" href=\"https://tympanus.net/codrops/?p=93330\">Article</a>\n        <a class=\"line\" href=\"https://github.com/codrops/3DCarousel/\">Code</a>\n        <a class=\"line\" href=\"https://tympanus.net/codrops/demos/\">All demos</a>\n      </nav>\n      <nav class=\"frame__tags\">\n        <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=3d\">#3d</a>\n        <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=carousel\">#carousel</a>\n        <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=page-transition\">#page-transition</a>\n      </nav>\n    </header>\n    <main id=\"smooth-content\">\n      <div class=\"scene-wrapper\">\n        <!-- Carousel 1 -->\n        <div class=\"scene\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-1\"><span>Haute Couture Nights — Paris</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img1.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img2.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img3.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img4.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>\n        </div>        \n        <!-- Carousel 2 -->\n        <div class=\"scene\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-2\"><span>Vogue Evolution — New York City</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img13.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img14.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img15.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img16.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>          \n        </div>\n        <!-- Carousel 3 -->\n        <div class=\"scene\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-3\"><span>Glamour in the Desert — Dubai</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img25.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img26.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img27.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img28.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>          \n        </div>\n        <!-- Carousel 4 -->\n        <div class=\"scene\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-4\"><span>Chic Couture Runway — Milan</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img37.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img38.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img39.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img40.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>          \n        </div>\n        <!-- Carousel 5 (6 cells) -->\n        <div class=\"scene\" data-radius=\"650\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-5\"><span>Style Showcase — London</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img49.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img50.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img51.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img52.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img53.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img54.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>          \n        </div>\n        <!-- Carousel 6 -->\n        <div class=\"scene\">\n          <h2 class=\"scene__title\" data-speed=\"0.7\">\n            <a href=\"#preview-6\"><span>Future Fashion Forward — Tokyo</span></a>\n          </h2>\n          <div class=\"carousel\">\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img61.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img62.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img63.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n            <div class=\"carousel__cell\">\n              <div class=\"card\" style=\"--img: url(../assets/img64.webp)\">\n                <div class=\"card__face card__face--front\"></div>\n                <div class=\"card__face card__face--back\"></div>\n              </div>\n            </div>\n          </div>          \n      </div>\n      <!-- / scenes-wrapper -->\n    </main>\n    <div class=\"preview-wrapper\">\n      <div class=\"preview\" id=\"preview-1\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Haute Couture Nights — Paris</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption1\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img1.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption1\">\n              <h3>Kai Vega</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption2\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img2.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption2\">\n              <h3>Riven Juno</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption3\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img3.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption3\">\n              <h3>Lex Orion</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption4\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img4.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption4\">\n              <h3>Ash Kairos</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption5\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img5.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption5\">\n              <h3>Juno Sol</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption6\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img6.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption6\">\n              <h3>Soren Nyx</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption7\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img7.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption7\">\n              <h3>Quinn Axon</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption8\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img8.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption8\">\n              <h3>Zara Voss</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption9\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img9.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption9\">\n              <h3>Hale B.</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption10\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img10.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption10\">\n              <h3>Gundra Wex</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption61\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img11.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption61\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption62\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img12.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption62\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-1 -->\n      <div class=\"preview\" id=\"preview-2\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Vogue Evolution — New York City</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption11\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img13.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption11\">\n              <h3>Arlo Quinn</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption12\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img14.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption12\">\n              <h3>Vera Kline</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption13\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img15.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption13\">\n              <h3>Juno Vale</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption14\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img16.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption14\">\n              <h3>Ember Dash</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption15\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img17.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption15\">\n              <h3>Rylee Voss</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption16\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img18.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption16\">\n              <h3>Harlow Nova</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption17\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img19.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption17\">\n              <h3>Blake Lune</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption18\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img22.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption18\">\n              <h3>Zephyr Kade</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption19\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img21.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption19\">\n              <h3>Indigo Rae</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption20\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img22.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption20\">\n              <h3>Kairo Jett</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption63\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img23.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption63\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption64\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img24.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption64\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-2 -->\n      <div class=\"preview\" id=\"preview-3\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Glamour in the Desert — Dubai</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption21\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img25.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption21\">\n              <h3>Luca Raine</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption22\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img26.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption22\">\n              <h3>Rory Vale</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption23\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img27.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption23\">\n              <h3>Sable Zev</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption24\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img28.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption24\">\n              <h3>Ellis Nova</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption25\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img29.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption25\">\n              <h3>Wren Asher</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption26\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img30.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption26\">\n              <h3>Zane Sky</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption27\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img31.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption27\">\n              <h3>Rowan Juno</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption28\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img32.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption28\">\n              <h3>Fenix Blade</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption29\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img33.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption29\">\n              <h3>Alix Storm</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption30\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img34.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption30\">\n              <h3>Nova Ray</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption65\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img35.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption65\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption66\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img36.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption66\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-3 -->\n      <div class=\"preview\" id=\"preview-4\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Chic Couture Runway — Milan</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption31\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img37.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption31\">\n              <h3>Aeris Flint</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption32\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img38.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption32\">\n              <h3>Jett Voss</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption33\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img39.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption33\">\n              <h3>Caius Storm</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption34\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img40.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption34\">\n              <h3>Mira Celeste</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption35\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img41.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption35\">\n              <h3>Liam Ashford</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption36\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img42.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption36\">\n              <h3>Vega Dawn</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption37\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img43.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption37\">\n              <h3>Orion Phoenix</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption38\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img44.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption38\">\n              <h3>Rex Solara</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption39\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img45.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption39\">\n              <h3>Elara Finch</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption40\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img46.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption40\">\n              <h3>Zoe Star</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption67\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img47.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption67\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption68\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img48.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption68\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-4 -->\n      <div class=\"preview\" id=\"preview-5\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Style Showcase — London</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption41\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img49.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption41\">\n              <h3>Rylan Ash</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption42\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img50.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption42\">\n              <h3>Lyra Wren</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption43\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img51.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption43\">\n              <h3>Axel Orion</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption44\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img52.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption44\">\n              <h3>Nova Sky</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption45\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img53.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption45\">\n              <h3>Kael Dray</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption46\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img54.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption46\">\n              <h3>Vesper Quill</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption47\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img55.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption47\">\n              <h3>Lira Wilder</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption48\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img56.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption48\">\n              <h3>Indigo Raye</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption49\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img57.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption49\">\n              <h3>Juno Storm</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption50\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img58.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption50\">\n              <h3>Ollie Lune</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption69\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img59.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption69\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption70\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img60.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption70\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-5 -->\n      <div class=\"preview\" id=\"preview-6\">\n        <header class=\"preview__header\">\n          <h2 class=\"preview__title\"><span>Future Fashion Forward — Tokyo</span></h2>\n          <button class=\"preview__close\">Close ×</button>\n        </header>\n        <div class=\"grid\">\n          <figure aria-labelledby=\"caption51\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img61.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption51\">\n              <h3>Corin Blaize</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption52\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img62.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption52\">\n              <h3>Tess Kade</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption53\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img63.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption53\">\n              <h3>Juno Hale</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption54\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img64.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption54\">\n              <h3>Coral Vale</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption55\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img65.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption55\">\n              <h3>Ari Lennox</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption56\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img66.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption56\">\n              <h3>Ronan Aster</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption57\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img67.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption57\">\n              <h3>Arius Quill</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption58\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img68.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption58\">\n              <h3>Rex Ember</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption59\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img69.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption59\">\n              <h3>Vega Ashford</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption60\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img70.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption60\">\n              <h3>Finn Fenix</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption71\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img71.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption71\">\n              <h3>Extra One</h3>\n            </figcaption>\n          </figure>\n          <figure aria-labelledby=\"caption72\" class=\"grid__item\" role=\"img\">\n            <div class=\"grid__item-image\" style=\"background-image: url(assets/img72.webp)\"></div>\n            <figcaption class=\"grid__item-caption\" id=\"caption72\">\n              <h3>Extra Two</h3>\n            </figcaption>\n          </figure>\n        </div>\n      </div>\n      <!--/ preview-6 -->\n    </div>\n  ";
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
        if (target < from - 1e-9) return step(target);
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
    const complete = await current.runTo(
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
