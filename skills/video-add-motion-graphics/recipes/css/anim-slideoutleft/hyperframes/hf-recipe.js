/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {

    var el=document.getElementById("el");
    var reduce=window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    function play(){ el.classList.remove("slideOutLeft"); void el.offsetWidth; el.classList.add("slideOutLeft"); }
    if(!reduce) __hf.setInterval(play, 2400);
  
}
];
