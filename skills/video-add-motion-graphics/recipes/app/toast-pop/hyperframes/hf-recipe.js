/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
var t=document.querySelector('.ui-toast');
function cycle(){t.classList.add('show');__hf.setTimeout(function(){t.classList.remove('show');},1700);}
cycle();__hf.setInterval(cycle,2600);
}
];
