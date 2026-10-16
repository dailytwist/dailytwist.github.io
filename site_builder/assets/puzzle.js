var WORDS=["apple", "green", "brick", "whale", "snack", "daisy", "value", "wheat", "hotel", "bring", "stone", "cabin", "spoon", "frost", "prize", "fable", "urban", "eagle", "basil", "jelly", "sunny", "image", "sleep", "cocoa", "peace", "zebra", "swing", "dance", "badge", "torch", "shore", "gusto", "coral", "glide", "month", "focus", "globe", "spark", "mocha", "pearl", "noble", "maple", "heart", "royal", "piano", "trail", "olive", "plant", "amber", "watch", "camel", "tiger", "scene", "water", "track", "snake", "magic", "denim", "march", "earth", "knife", "brave", "metal", "cedar", "bunny", "tower", "river", "party", "guest", "jewel", "melon", "pizza", "nacho", "fruit", "radio", "jolly", "night", "mercy", "stars", "robin", "crane", "canoe", "raven", "orbit", "toast", "grass", "kitty", "lilac", "lunar", "horse", "climb", "uncle", "money", "flute", "steam", "baker", "coast", "tulip", "drift", "poems", "young", "power", "smile", "ocean", "panda", "field", "quest", "pilot", "shell", "lucky", "haven", "chalk", "plaza", "ivory", "blush", "karma", "stamp", "light", "cream", "koala", "space", "fairy", "feast", "quiet", "fancy", "moose", "juice", "otter", "sport", "story", "chime", "voice", "scarf", "house", "giant", "skate", "candy", "flame", "lotus", "igloo", "chair", "maize", "comet", "rocky", "paint", "bread", "happy", "lemon", "llama", "chess", "mango", "trees", "waltz", "latte", "treat", "dough", "storm", "laugh", "unity", "dream", "angel", "honey", "solar", "opera", "gecko", "mouse", "vivid", "table", "flora", "shine", "world", "spice", "pride", "glass", "fudge", "cheer", "blaze", "bloom", "music", "sound", "charm", "salad", "train", "cider", "crown", "ghost", "grape", "heron", "beach", "cloud", "sugar"];

(function(){
  var start=new Date(2025,0,1),now=new Date();
  var day=Math.floor((new Date(now.getFullYear(),now.getMonth(),now.getDate())-start)/86400000);
  var answer=WORDS[((day%WORDS.length)+WORDS.length)%WORDS.length].toUpperCase();
  var key='dt-puzzle-'+day,rows=[],cur='',over=false;
  try{var saved=JSON.parse(localStorage.getItem(key)||'null');if(saved){rows=saved.rows;over=saved.over;}}catch(e){}
  var board=document.getElementById('board'),msg=document.getElementById('msg'),kb=document.getElementById('kb');
  function score(g){
    var res=Array(5).fill('x'),pool={};
    for(var i=0;i<5;i++){if(g[i]===answer[i])res[i]='g';else pool[answer[i]]=(pool[answer[i]]||0)+1;}
    for(i=0;i<5;i++){if(res[i]!=='g'&&pool[g[i]]){res[i]='y';pool[g[i]]--;}}
    return res;
  }
  function save(){try{localStorage.setItem(key,JSON.stringify({rows:rows,over:over}))}catch(e){}}
  var keys={};
  function draw(){
    board.innerHTML='';
    for(var r=0;r<6;r++){
      var row=document.createElement('div');row.className='row';
      var word=r<rows.length?rows[r]:(r===rows.length?cur:''),sc=r<rows.length?score(rows[r]):null;
      for(var c=0;c<5;c++){var t=document.createElement('div');t.className='tile'+(sc?' '+sc[c]:'');t.textContent=word[c]||'';row.appendChild(t);}
      board.appendChild(row);
    }
    var best={};
    rows.forEach(function(w){var s=score(w);for(var i=0;i<5;i++){var o=best[w[i]];if(s[i]==='g'||(s[i]==='y'&&o!=='g')||!o)best[w[i]]=s[i];}});
    Object.keys(keys).forEach(function(k){keys[k].className=(keys[k].className.indexOf('wide')>-1?'wide ':'')+(best[k]||'');});
  }
  function finish(win){over=true;save();msg.textContent=win?'Brilliant! Solved in '+rows.length+'/6. Come back tomorrow!':'The word was '+answer+'. New puzzle tomorrow!';}
  function press(k){
    if(over)return;msg.textContent='';
    if(k==='ENTER'){
      if(cur.length<5){msg.textContent='Not enough letters';return;}
      rows.push(cur);cur='';save();draw();
      if(rows[rows.length-1]===answer)finish(true);else if(rows.length===6)finish(false);
      return;
    }
    if(k==='DEL'){cur=cur.slice(0,-1);draw();return;}
    if(/^[A-Z]$/.test(k)&&cur.length<5){cur+=k;draw();}
  }
  ['QWERTYUIOP','ASDFGHJKL','>ZXCVBNM<'].forEach(function(line){
    var d=document.createElement('div');
    line.split('').forEach(function(ch){
      var b=document.createElement('button'),k=ch==='>'?'ENTER':ch==='<'?'DEL':ch;
      b.textContent=ch==='>'?'Enter':ch==='<'?'⌫':ch;if(k.length>1)b.className='wide';
      b.addEventListener('click',function(){press(k)});keys[k]=b;d.appendChild(b);
    });
    kb.appendChild(d);
  });
  document.addEventListener('keydown',function(e){
    if(e.ctrlKey||e.metaKey||e.altKey)return;
    if(e.key==='Enter')press('ENTER');else if(e.key==='Backspace')press('DEL');else press(e.key.toUpperCase());
  });
  draw();
  if(over){var last=rows[rows.length-1];msg.textContent=last===answer?'Solved! Come back tomorrow for a new word.':'The word was '+answer+'. New puzzle tomorrow!';}
})();
