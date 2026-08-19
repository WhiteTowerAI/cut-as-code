/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
var b=document.querySelector('.ui-btn');
function press(on){b.classList.toggle('pressed',on);}
b.addEventListener('pointerdown',function(){press(true);});
b.addEventListener('pointerup',function(){press(false);});
b.addEventListener('pointerleave',function(){press(false);});
__hf.setInterval(function(){press(true);__hf.setTimeout(function(){press(false);},150);},1500);
}
];
