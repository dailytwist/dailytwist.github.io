(function(){
  var el=document.querySelector('[data-target]');if(!el)return;
  var t=new Date(el.dataset.target);
  function pad(n){return n<10?'0'+n:n}
  function tick(){
    var ms=Math.max(0,t-new Date()),s=Math.floor(ms/1000);
    document.getElementById('d').textContent=Math.floor(s/86400);
    document.getElementById('h').textContent=pad(Math.floor(s%86400/3600));
    document.getElementById('m').textContent=pad(Math.floor(s%3600/60));
    document.getElementById('s').textContent=pad(s%60);
  }
  tick();setInterval(tick,1000);
})();
