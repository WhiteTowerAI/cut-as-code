/* Generated from the original recipe scripts. Source credit comments are preserved below. */
window.__hfRecipeFactories = [
function (__hf) {
var b=document.querySelector('.ui-rip');
function rip(x,y){var s=document.createElement('span');s.className='rp';var d=Math.max(b.clientWidth,b.clientHeight);s.style.width=s.style.height=d+'px';s.style.left=(x-d/2)+'px';s.style.top=(y-d/2)+'px';b.appendChild(s);__hf.setTimeout(function(){s.remove();},600);}
b.addEventListener('click',function(e){var r=b.getBoundingClientRect();rip(e.clientX-r.left,e.clientY-r.top);});
__hf.setInterval(function(){rip(b.clientWidth/2,b.clientHeight/2);},1500);
}
];
