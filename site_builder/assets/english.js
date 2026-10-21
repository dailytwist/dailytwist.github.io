/* DailyTwist Learn English: listen buttons, lesson quiz, progress and word of the day. Original code. */
(function () {
  var DONE = 'dt-en-done';
  function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k)); return v === null ? d : v; } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // text to speech with an English voice (free, built into the browser)
  var voice = null;
  function pickVoice() {
    if (!window.speechSynthesis) return;
    var vs = speechSynthesis.getVoices();
    voice = vs.filter(function (v) { return /^en[-_]US/i.test(v.lang); })[0] || vs.filter(function (v) { return /^en/i.test(v.lang); })[0] || null;
  }
  if (window.speechSynthesis) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
  function say(text, btn) {
    if (!window.speechSynthesis || !text) return;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text.replace(/_{2,}/g, ' blank '));
    u.lang = 'en-US'; u.rate = .9; if (voice) u.voice = voice;
    if (btn) { btn.classList.add('on'); u.onend = u.onerror = function () { btn.classList.remove('on'); }; }
    speechSynthesis.speak(u);
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.say');
    if (b && b.dataset.t) { ev.preventDefault(); say(b.dataset.t, b); }
  });
  if (!window.speechSynthesis) document.documentElement.classList.add('nosay');

  // hub: progress + word of the day
  var hub = document.getElementById('en-data');
  if (hub) {
    var H = JSON.parse(hub.textContent), done = get(DONE, {});
    var n = 0;
    document.querySelectorAll('.encard').forEach(function (c) { if (done[c.dataset.k]) { c.classList.add('done'); n++; } });
    var pr = document.querySelector('.enprog');
    if (pr) { pr.querySelector('i').style.width = (H.total ? n / H.total * 100 : 0) + '%'; pr.querySelector('span').textContent = H.l.progress.replace('{n}', n).replace('{total}', H.total); }
    var w = document.querySelector('.enwod');
    if (w && H.words.length) {
      var day = Math.floor(Date.now() / 864e5), x = H.words[(day * 37) % H.words.length];
      w.querySelector('b').textContent = x[0];
      w.querySelector('p').textContent = x[1];
      w.querySelector('.say').dataset.t = x[0];
      var a = w.querySelector('a'); a.href = H.pre + '/learn-english/' + x[2] + '/';
      var card = document.querySelector('.encard[data-k="' + x[2] + '"] b'); a.textContent = '📘 ' + (card ? card.textContent : '');
    }
  }

  // lesson quiz
  var qd = document.getElementById('enq-data'), box = document.getElementById('enquiz');
  if (qd && box) {
    var Q = JSON.parse(qd.textContent), answered = 0, right = 0;
    function render() {
      answered = 0; right = 0;
      box.innerHTML = Q.q.map(function (q, i) {
        return '<div class="enq" data-i="' + i + '"><small>' + (i + 1) + '. ' + esc(q.ask) + '</small>' +
          '<p><b lang="en" dir="ltr">' + esc(q.en) + '</b> <button class="say" type="button" data-t="' + esc(q.en) + '" aria-label="' + Q.l.listen + '">🔊</button></p>' +
          '<div class="enc">' + q.c.map(function (c, j) { return '<button type="button" lang="en" dir="ltr" data-j="' + j + '">' + esc(c) + '</button>'; }).join('') + '</div></div>';
      }).join('') + '<div class="enres" hidden></div>';
    }
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('.enc button'); if (!b) return;
      var wrap = b.closest('.enq'); if (wrap.classList.contains('ok') || wrap.classList.contains('no')) return;
      var q = Q.q[+wrap.dataset.i], j = +b.dataset.j, good = j === q.a;
      wrap.classList.add(good ? 'ok' : 'no');
      b.classList.add(good ? 'right' : 'wrong');
      wrap.querySelectorAll('.enc button')[q.a].classList.add('right');
      answered++; if (good) right++;
      say(q.en.replace(/_{2,}/, q.c[q.a]));
      if (answered === Q.q.length) {
        var res = box.querySelector('.enres'), pass = right >= Math.ceil(Q.q.length * .6);
        res.innerHTML = '<b>' + (pass ? '🎉 ' + Q.l.done + ' ' : '💪 ') + Q.l.score.replace('{n}', right).replace('{total}', Q.q.length) + '</b>' +
          '<button class="btn small ghost" type="button">↻ ' + Q.l.retry + '</button>';
        res.hidden = false; res.querySelector('button').onclick = function () { render(); box.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
        if (pass) { var d = get(DONE, {}); d[Q.k] = 1; set(DONE, d); }
        if (window.DTG && window.DTG.addXP && pass) window.DTG.addXP(20);
      }
    });
    render();
  }
})();
