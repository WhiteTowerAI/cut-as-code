/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
var tabs=[].slice.call(document.querySelectorAll('.ui-tabs .tb'));var ind=document.querySelector('.ui-tabs .ind');var i=0;
function go(n){i=n;tabs.forEach(function(t,k){t.classList.toggle('on',k===n);});ind.style.transform='translateX('+(n*62)+'px)';}
tabs.forEach(function(t,k){t.addEventListener('click',function(){go(k);});});
__hf.setInterval(function(){go((i+1)%tabs.length);},1500);
}
];
