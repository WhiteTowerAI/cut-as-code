/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {

    var el=document.getElementById("el");
    var reduce=window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if(!reduce){
      el.classList.add("xyz-in");
      __hf.setInterval(function(){ var inn=el.classList.contains("xyz-in"); el.classList.toggle("xyz-in",!inn); el.classList.toggle("xyz-out",inn); }, 1900);
    }
  
}
];
