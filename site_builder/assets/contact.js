(function(){
  var f=document.getElementById('cf');if(!f)return;
  f.addEventListener('submit',function(ev){
    ev.preventDefault();var m=document.getElementById('cf-msg'),b=f.querySelector('button');
    b.disabled=true;m.textContent=f.dataset.sending;
    fetch('https://api.web3forms.com/submit',{method:'POST',body:new FormData(f)})
      .then(function(r){return r.json()})
      .then(function(d){if(d.success){f.reset();m.textContent=f.dataset.ok;}else{m.textContent=f.dataset.err;}b.disabled=false;})
      .catch(function(){m.textContent=f.dataset.err;b.disabled=false;});
  });
})();
