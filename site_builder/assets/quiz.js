(function(){
  var qs=document.querySelectorAll('.q'),done=0,score=0;
  qs.forEach(function(q){
    var ans=+q.dataset.answer;
    q.querySelectorAll('.opt').forEach(function(b){
      b.addEventListener('click',function(){
        var pick=+b.dataset.i;
        q.querySelectorAll('.opt').forEach(function(o){o.disabled=true;if(+o.dataset.i===ans)o.classList.add('right');});
        if(pick===ans)score++;else b.classList.add('wrong');
        q.querySelector('.fact').hidden=false;
        if(++done===qs.length){var s=document.querySelector('.score');document.getElementById('sc').textContent=score;s.hidden=false;s.scrollIntoView({behavior:'smooth',block:'center'});}
      });
    });
  });
})();
