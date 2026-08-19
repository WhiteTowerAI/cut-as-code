/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
var p=document.querySelector('.ui-phone');
function cycle(){p.classList.add('open');__hf.setTimeout(function(){p.classList.remove('open');},1900);}
__hf.setTimeout(cycle,300);__hf.setInterval(cycle,3000);
}
];
