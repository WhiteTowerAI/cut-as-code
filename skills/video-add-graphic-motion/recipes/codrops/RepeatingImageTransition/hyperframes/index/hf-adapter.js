/* Original Codrops project: RepeatingImageTransition. */
/* Generated deterministic HyperFrames adapter for codrops-repeatingimagetransition-index. */
(function () {
  "use strict";
  const FRAME_STEP = 0.016666666666666666;
  const TRACK_CSS = true;
  const INTERACTION = {"mode":"transition","duration":6,"actions":[{"at":0.8,"type":"click","selector":".grid__item"}]};
  const AUDIT_ALLOWANCES = {"data-layout-allow-overlap":[".char",".word",".oh",".oh__inner","[data-splitting]"],"data-layout-allow-occlusion":[".oh__inner"]};
  const SOURCE_BODY = "\n    <main>\n      <header class=\"frame\">\n        <h1 class=\"frame__title\">Repeating Image Transition</h1>\n        <nav class=\"frame__links\">\n          <a class=\"line\" href=\"https://tympanus.net/codrops/?p=92571\">More info,</a>\n          <a class=\"line\" href=\"https://github.com/codrops/RepeatingImageTransition/\">Code,</a>\n          <a class=\"line\" href=\"https://tympanus.net/codrops/demos/\">All demos</a>\n        </nav>\n        <nav class=\"frame__tags\">\n          <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=page-transition\">page-transition,</a>\n          <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=repetition\">repetition,</a>\n          <a class=\"line\" href=\"https://tympanus.net/codrops/demos/?tag=grid\">grid</a>\n        </nav>\n      </header>\n      <div class=\"heading\">\n        <h2 class=\"heading__title\">Shane Weber</h2>\n        <span class=\"heading__meta\">\n          effect 01: straight linear paths, smooth easing, clean timing, minimal rotation.\n        </span>\n      </div>\n      <div class=\"grid\">\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption1\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img1.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption1\">\n            <h3>Drift — A04</h3>\n            <p>Model: Amelia Hart</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption2\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img2.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption2\">\n            <h3>Veil — K18</h3>\n            <p>Model: Irina Volkova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption3\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img3.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption3\">\n            <h3>Ember — M45</h3>\n            <p>Model: Charlotte Byrne</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption4\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img4.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption4\">\n            <h3>Gleam — S12</h3>\n            <p>Model: Anastasia Morozova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption5\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img5.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption5\">\n            <h3>Bloom — J29</h3>\n            <p>Model: Eva Ramirez</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption6\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img6.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption6\">\n            <h3>Whisper — V87</h3>\n            <p>Model: Milana Petrova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption7\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img7.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption7\">\n            <h3>Trace — Z05</h3>\n            <p>Model: Sofia Carter</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption8\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img8.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption8\">\n            <h3>Flicker — Q62</h3>\n            <p>Model: Alina Kuznetsova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption9\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img9.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption9\">\n            <h3>Grain — H71</h3>\n            <p>Model: Isabella Novak</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption10\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img10.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption10\">\n            <h3>Pulse — B90</h3>\n            <p>Model: Daria Sokolova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption11\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img11.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption11\">\n            <h3>Mist — L36</h3>\n            <p>Model: Victoria Fields</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption12\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img12.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption12\">\n            <h3>Shard — Y22</h3>\n            <p>Model: Natalia Popova & Emily Stone</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption13\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img13.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption13\">\n            <h3>Vapor — X79</h3>\n            <p>Model: Yulia Orlova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption14\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img14.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption14\">\n            <h3>Glow — F13</h3>\n            <p>Model: Camila Ford</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption15\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img15.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption15\">\n            <h3>Flux — N48</h3>\n            <p>Model: Sofia Mikhailova</p>\n          </figcaption>\n        </figure>\n\n        <figure class=\"grid__item\" role=\"img\" aria-labelledby=\"caption16\">\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img16.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption16\">\n            <h3>Spire — C65</h3>\n            <p>Model: Ava Bennett</p>\n          </figcaption>\n        </figure>\n      </div>\n      <div class=\"heading\">\n        <h2 class=\"heading__title\">Manika Jorge</h2>\n        <span class=\"heading__meta\">effect 02: Adjusts mover count, rotation, timing, and animation feel.</span>\n      </div>\n      <div class=\"grid\">\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption17\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img17.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption17\">\n            <h3>Driftwood — W50</h3>\n            <p>Model: Valeria Smirnova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption18\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img18.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption18\">\n            <h3>Fold — T81</h3>\n            <p>Model: Emma Chase</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption19\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img19.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption19\">\n            <h3>Shroud — E26</h3>\n            <p>Model: Marina Belova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption20\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img20.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption20\">\n            <h3>Ripple — P34</h3>\n            <p>Model: Chloe Martin</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption21\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img21.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption21\">\n            <h3>Fray — U07</h3>\n            <p>Model: Alexandra Dmitrieva</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption22\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img22.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption22\">\n            <h3>Wane — R52</h3>\n            <p>Model: Isabella Moore</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption23\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img23.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption23\">\n            <h3>Tide — S33</h3>\n            <p>Model: Ksenia Egorova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption24\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img24.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption24\">\n            <h3>Rift — G08</h3>\n            <p>Model: Mia Anderson</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption25\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img25.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption25\">\n            <h3>Spool — H94</h3>\n            <p>Model: Anna Mikhailova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption26\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img26.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption26\">\n            <h3>Glitch — M70</h3>\n            <p>Model: Emily Brown</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption27\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img27.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption27\">\n            <h3>Slip — F02</h3>\n            <p>Model: Ekaterina Ivanova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption28\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img28.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption28\">\n            <h3>Husk — C15</h3>\n            <p>Model: Olivia Reed</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption29\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img29.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption29\">\n            <h3>Blur — V86</h3>\n            <p>Model: Sofia Lebedeva</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption30\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img30.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption30\">\n            <h3>Fracture — A63</h3>\n            <p>Model: Harper Gray</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption31\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img31.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption31\">\n            <h3>Mote — Y39</h3>\n            <p>Model: Elizaveta Petrova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption32\"\n          data-steps=\"8\"\n          data-rotation-range=\"7\"\n          data-step-interval=\"0.05\"\n          data-mover-pause-before-exit=\"0.25\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"power2\"\n          data-panel-reveal-ease=\"power2\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img32.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption32\">\n            <h3>Aura — K21</h3>\n            <p>Model: Lily Cooper</p>\n          </figcaption>\n        </figure>\n      </div>\n      <div class=\"heading\">\n        <h2 class=\"heading__title\">Angela Wong</h2>\n        <span class=\"heading__meta\">effect 03: Big arcs, smooth start, powerful snap, slow reveal.</span>\n      </div>\n      <div class=\"grid\">\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption33\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img33.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption33\">\n            <h3>Whorl — B45</h3>\n            <p>Model: Anastasia Volkova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption34\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img1.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption34\">\n            <h3>Flicker — D17</h3>\n            <p>Model: Sophia White</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption35\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img2.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption35\">\n            <h3>Gleam — Z58</h3>\n            <p>Model: Polina Sokolova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption36\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img3.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption36\">\n            <h3>Shard — J03</h3>\n            <p>Model: Ava Mitchell</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption37\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img4.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption37\">\n            <h3>Trace — Q29</h3>\n            <p>Model: Maria Ivanenko</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption38\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img5.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption38\">\n            <h3>Crush — W92</h3>\n            <p>Model: Ella Foster</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption39\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img6.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption39\">\n            <h3>Veil — X16</h3>\n            <p>Model: Yulia Morozova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption40\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img7.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption40\">\n            <h3>Clasp — S84</h3>\n            <p>Model: Charlotte Hayes</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption41\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img8.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption41\">\n            <h3>Flint — T66</h3>\n            <p>Model: Viktoria Kuznetsova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption42\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img9.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption42\">\n            <h3>Spire — E49</h3>\n            <p>Model: Amelia Parker</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption43\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img10.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption43\">\n            <h3>Plume — N22</h3>\n            <p>Model: Daria Smirnova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption44\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img11.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption44\">\n            <h3>Hollow — B75</h3>\n            <p>Model: Zoe Adams</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption45\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img12.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption45\">\n            <h3>Brume — K10</h3>\n            <p>Model: Anastasiya Orlova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption46\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img13.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption46\">\n            <h3>Crave — F37</h3>\n            <p>Model: Mia Bennett</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption47\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img14.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption47\">\n            <h3>Quiver — R19</h3>\n            <p>Model: Natalia Volkova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption48\"\n          data-steps=\"10\"\n          data-step-duration=\"0.3\"\n          data-path-motion=\"sine\"\n          data-sine-amplitude=\"300\"\n          data-clip-path-direction=\"left-right\"\n          data-auto-adjust-horizontal-clip-path=\"true\"\n          data-step-interval=\"0.07\"\n          data-mover-pause-before-exit=\"0.3\"\n          data-mover-enter-ease=\"sine\"\n          data-mover-exit-ease=\"power4\"\n          data-panel-reveal-ease=\"power4\"\n          data-panel-reveal-duration-factor=\"4\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img15.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption48\">\n            <h3>Fathom — L52</h3>\n            <p>Model: Isabella Young</p>\n          </figcaption>\n        </figure>\n      </div>\n      <div class=\"heading\">\n        <h2 class=\"heading__title\">Kaito Nakamo</h2>\n        <span class=\"heading__meta\">effect 04: Quick upward motion with bold blending and smooth slow reveal.</span>\n      </div>\n      <div class=\"grid\">\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption49\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img16.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption49\">\n            <h3>Pulse — D61</h3>\n            <p>Model: Sofia Makarova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption50\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img17.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption50\">\n            <h3>Fade — P42</h3>\n            <p>Model: Scarlett James</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption51\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img18.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption51\">\n            <h3>Wisp — T14</h3>\n            <p>Model: Ekaterina Romanova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption52\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img19.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption52\">\n            <h3>Fragment — G77</h3>\n            <p>Model: Aria Robinson</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption53\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img20.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption53\">\n            <h3>Spiral — Y24</h3>\n            <p>Model: Daria Petrova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption54\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img21.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption54\">\n            <h3>Trace — Z85</h3>\n            <p>Model: Chloe Evans</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption55\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img22.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption55\">\n            <h3>Flare — C11</h3>\n            <p>Model: Sofia Orlova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption56\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img23.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption56\">\n            <h3>Chasm — R05</h3>\n            <p>Model: Grace Walker</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption57\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img24.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption57\">\n            <h3>Bloom — N38</h3>\n            <p>Model: Yana Melnikova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption58\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img25.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption58\">\n            <h3>Shard — W20</h3>\n            <p>Model: Mila Scott</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption59\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img26.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption59\">\n            <h3>Mist — S12</h3>\n            <p>Model: Natalia Ivanova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption60\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img27.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption60\">\n            <h3>Crush — E31</h3>\n            <p>Model: Ava Thompson</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption61\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img28.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption61\">\n            <h3>Ripple — F68</h3>\n            <p>Model: Anastasia Novikova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption62\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img29.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption62\">\n            <h3>Gossamer — A07</h3>\n            <p>Model: Madison Brooks</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption63\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img30.webp)\"></div>\n          <figcaption class=\"grid__item-caption\" id=\"caption63\">\n            <h3>Floe — K96</h3>\n            <p>Model: Ekaterina Smirnova</p>\n          </figcaption>\n        </figure>\n\n        <figure\n          class=\"grid__item\"\n          role=\"img\"\n          aria-labelledby=\"caption64\"\n          data-steps=\"4\"\n          data-clip-path-direction=\"bottom-top\"\n          data-step-duration=\"0.25\"\n          data-step-interval=\"0.06\"\n          data-mover-pause-before-exit=\"0.2\"\n          data-mover-enter-ease=\"sine.in\"\n          data-mover-exit-ease=\"expo\"\n          data-panel-reveal-ease=\"expo\"\n          data-panel-reveal-duration-factor=\"4\"\n          data-mover-blend-mode=\"hard-light\"\n        >\n          <div class=\"grid__item-image\" style=\"background-image: url(assets/img31.webp)\"></div>\n          <figcaption\n            class=\"grid__item-caption\"\n            id=\"caption64\"\n            data-steps=\"4\"\n            data-clip-path-direction=\"bottom-top\"\n            data-step-duration=\"0.25\"\n            data-step-interval=\"0.06\"\n            data-mover-pause-before-exit=\"0.2\"\n            data-mover-enter-ease=\"sine.in\"\n            data-mover-exit-ease=\"expo\"\n            data-panel-reveal-ease=\"expo\"\n            data-panel-reveal-duration-factor=\"4\"\n            data-mover-blend-mode=\"hard-light\"\n          >\n            <h3>Shiver — V44</h3>\n            <p>Model: Emily Robinson</p>\n          </figcaption>\n        </figure>\n      </div>\n      <!-- panel for large preview -->\n      <figure class=\"panel\" role=\"img\" aria-labelledby=\"caption\">\n        <div class=\"panel__img\" style=\"background-image: url(assets/img1.webp)\"></div>\n        <figcaption class=\"panel__content\" id=\"caption\">\n          <h3>murmur—207</h3>\n          <p>\n            Beneath the soft static of this lies a fragmented recollection of motion—faded pulses echoing through\n            time-warped layers of light and silence. A stillness wrapped in artifact.\n          </p>\n          <button type=\"button\" class=\"panel__close\" aria-label=\"Close preview\">Close</button>\n        </figcaption>\n      </figure>\n      <footer class=\"frame frame--footer\">\n        <span>\n          Made by\n          <a href=\"https://codrops.com/\" class=\"line\">@codrops</a>\n        </span>\n        <span><a href=\"https://tympanus.net/codrops/demos/\" class=\"line\">All demos</a></span>\n      </footer>\n    </main>\n    <!-- GSAP library -->\n    \n    <!-- ImagesLoaded -->\n    \n    <!-- Add (Lenis) smooth scroll -->\n    \n    \n    <!-- Scripts for the effect -->\n    \n  ";
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
      duration: 6,
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
    const target = Math.max(0, Math.min(6, Number(time) || 0));
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
