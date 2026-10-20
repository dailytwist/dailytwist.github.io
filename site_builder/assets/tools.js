/* DailyTwist fun tools: love calculator, age calculator, zodiac personality quiz, love message cards. Original code. */
(function () {
  var dataEl = document.getElementById('tools-data'); if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  function $(s, r) { return (r || document).querySelector(s); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function share(text, url) {
    url = url || location.href.split('#')[0];
    if (navigator.share) navigator.share({ text: text, url: url }).catch(function () {});
    else window.open('https://wa.me/?text=' + encodeURIComponent(text + ' ' + url), '_blank', 'noopener');
  }

  // ---------------------------------------------------------------- love calculator (names)
  var lc = document.getElementById('lovecalc');
  if (lc) {
    var out = $('.compat-out', lc);
    $('.compat-go', lc).onclick = function () {
      var a = $('[name=a]', lc).value.trim(), b = $('[name=b]', lc).value.trim();
      if (!a || !b) { (a ? $('[name=b]', lc) : $('[name=a]', lc)).focus(); return; }
      var key = [a.toLowerCase(), b.toLowerCase()].sort().join('❤'), h = 0;
      for (var i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
      var score = 45 + h % 55, tier = score >= 92 ? 4 : score >= 80 ? 3 : score >= 68 ? 2 : score >= 55 ? 1 : 0;
      out.innerHTML = '<div class="compat-card"><p class="cc-names">' + esc(a) + ' ❤ ' + esc(b) + '</p><div class="cc-ring" style="--p:' + score + '"><b>0%</b></div>' +
        '<p>' + esc(D.r[tier]) + '</p><button class="btn small">📤 ' + esc(D.share) + '</button></div>';
      var n = 0, num = $('.cc-ring b', out), tmr = setInterval(function () { n = Math.min(score, n + 2); num.textContent = n + '%'; if (n >= score) clearInterval(tmr); }, 20);
      $('button', out).onclick = function () { share('💘 ' + a + ' + ' + b + ' = ' + score + '% — ' + D.title); };
      out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
  }

  // ---------------------------------------------------------------- age & birthday calculator
  var bd = document.getElementById('bday');
  if (bd) {
    var bout = $('.bday-out', bd), L = D.l;
    function signOf(m, d) {
      var v = m * 100 + d;
      for (var s in D.ranges) { var r = D.ranges[s], a = r[0][0] * 100 + r[0][1], b = r[1][0] * 100 + r[1][1]; if (a <= b ? v >= a && v <= b : v >= a || v <= b) return s; }
    }
    function animalOf(y, m, d) { var ny = D.cny[y]; if (!ny) return null; if (m * 100 + d < ny) y--; return D.animals[((y - 1936) % 12 + 12) % 12]; }
    function lifePath(str) {
      function sum(s) { return String(s).split('').reduce(function (a, c) { return a + (+c || 0); }, 0); }
      function red(n) { while (n > 9 && n !== 11 && n !== 22 && n !== 33) n = sum(n); return n; }
      var p = str.split('-'); return red(red(sum(p[0])) + red(sum(p[1])) + red(sum(p[2])));
    }
    $('button', bd).onclick = function () {
      var v = $('input', bd).value; if (!v) return;
      var p = v.split('-').map(Number), birth = new Date(p[0], p[1] - 1, p[2]), now = new Date(), today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      if (birth > today) return;
      var y = today.getFullYear() - p[0], m = today.getMonth() - (p[1] - 1), d = today.getDate() - p[2];
      if (d < 0) { m--; d += new Date(today.getFullYear(), today.getMonth(), 0).getDate(); }
      if (m < 0) { y--; m += 12; }
      var days = Math.round((today - birth) / 864e5);
      var next = new Date(today.getFullYear(), p[1] - 1, p[2]); if (next < today) next.setFullYear(today.getFullYear() + 1);
      var toNext = Math.round((next - today) / 864e5);
      var wd; try { wd = birth.toLocaleDateString(D.lang, { weekday: 'long' }); } catch (e) { wd = birth.toDateString().slice(0, 3); }
      var fmtN = function (n) { try { return n.toLocaleString(D.lang); } catch (e) { return String(n); } };
      var s = signOf(p[1], p[2]), an = animalOf(p[0], p[1], p[2]), lp = lifePath(v);
      try { localStorage.setItem('dt-sign', s); } catch (e) {}
      var box = function (ic, k, val, href) { return (href ? '<a href="' + href + '">' : '<div>') + '<span>' + ic + '</span><small>' + esc(k) + '</small><b>' + val + '</b>' + (href ? '</a>' : '</div>'); };
      bout.innerHTML = (toNext === 0 ? '<p class="bday-party">' + esc(L.today_bday) + '</p>' : '') +
        '<div class="facts">' +
        box('🎂', L.age, esc(L.age_exact.replace('{y}', y).replace('{m}', m).replace('{d}', d))) +
        box('📆', L.days_lived, fmtN(days)) +
        box('🗓️', L.born_on, esc(wd)) +
        box('🎁', L.next_bday, toNext === 0 ? '🎉' : esc(L.in_days.replace('{n}', toNext))) +
        box('❤️', L.heartbeats, fmtN(days * 24 * 60 * 80)) +
        box(D.glyph[s], L.your_zodiac, esc(D.names[s]), D.pre + '/zodiac/' + s + '/') +
        (an ? box('🐉', L.your_animal, esc(D.an[an]), D.pre + '/chinese-zodiac/' + an + '/') : '') +
        box('🔢', L.your_number, lp, D.pre + '/numerology/' + lp + '/') + '</div>';
      if (toNext === 0 && window.DTG) window.DTG.confetti();
      bout.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
  }

  // ---------------------------------------------------------------- personality quiz
  var pq = document.getElementById('pquiz');
  if (pq) {
    var EL = ['fire', 'earth', 'air', 'water'], BY = { fire: ['aries', 'leo', 'sagittarius'], earth: ['capricorn', 'taurus', 'virgo'],
      air: ['libra', 'aquarius', 'gemini'], water: ['cancer', 'scorpio', 'pisces'] };
    var qi, score, mod;
    function ask() {
      var q = D.q[qi];
      pq.innerHTML = '<div class="pq-bar"><i style="width:' + (qi / D.q.length * 100) + '%"></i></div><p class="muted small">' + esc(D.of.replace('{n}', qi + 1).replace('{t}', D.q.length)) +
        '</p><h2>' + esc(q.t) + '</h2><div class="pq-opts">' + q.o.map(function (o, j) { return '<button class="pq-opt" data-j="' + j + '">' + esc(o) + '</button>'; }).join('') + '</div>';
      pq.querySelectorAll('.pq-opt').forEach(function (b) {
        b.onclick = function () {
          var j = +b.dataset.j; b.classList.add('on');
          if (qi < 7) score[EL[j]]++; else mod = j;
          setTimeout(function () { qi++; if (qi < D.q.length) ask(); else result(); }, 220);
        };
      });
    }
    function result() {
      var best = EL.slice().sort(function (a, b) { return score[b] - score[a]; })[0], s = BY[best][mod];
      pq.innerHTML = '<div class="compat-card"><img src="/assets/signs/' + s + '.webp" width="160" height="160" alt="" class="pq-img"><h2>' + esc(D.res.replace('{sign}', D.names[s])) + '</h2>' +
        '<a class="btn small ghost" href="' + D.pre + '/zodiac/' + s + '/">📖 ' + esc(D.read.replace('{sign}', D.names[s])) + '</a> ' +
        '<button class="btn small pq-share">📤 ' + esc(D.share) + '</button><p><button class="btn small ghost pq-again">↻ ' + esc(D.again) + '</button></p></div>';
      $('.pq-share', pq).onclick = function () { share('✨ ' + D.res.replace('{sign}', D.names[s]) + ' — ' + D.title); };
      $('.pq-again', pq).onclick = start;
      if (window.DTG) { window.DTG.confetti(); window.DTG.addXP(15); }
    }
    function start() { qi = 0; score = { fire: 0, earth: 0, air: 0, water: 0 }; mod = 0; ask(); }
    $('.pq-start', pq).onclick = start;
  }

  // ---------------------------------------------------------------- love message cards (canvas image)
  var lmb = document.getElementById('lovemsg');
  if (lmb) {
    var cv = $('canvas', lmb), cx = cv.getContext('2d'), acts = $('.lm-actions', lmb), cur = null, idx = 0;
    function wrap(text, maxW) {
      var words = text.split(' '), lines = [], line = '';
      words.forEach(function (w) { var t2 = line ? line + ' ' + w : w; if (cx.measureText(t2).width > maxW && line) { lines.push(line); line = w; } else line = t2; });
      if (line) lines.push(line); return lines;
    }
    function drawCard() {
      var s = cur, msg = D.m[s][idx % 3], img = new Image();
      img.onload = img.onerror = function () {
        var g = cx.createLinearGradient(0, 0, 1080, 1080); g.addColorStop(0, '#3b0a45'); g.addColorStop(.55, '#8a1c5a'); g.addColorStop(1, '#ff6b8b');
        cx.fillStyle = g; cx.fillRect(0, 0, 1080, 1080);
        for (var i = 0; i < 70; i++) { cx.fillStyle = 'rgba(255,220,240,' + (Math.random() * .5 + .1) + ')'; cx.beginPath(); cx.arc(Math.random() * 1080, Math.random() * 1080, Math.random() * 3 + 1, 0, 7); cx.fill(); }
        if (img.naturalWidth) { cx.save(); cx.beginPath(); cx.arc(540, 330, 190, 0, 7); cx.clip(); cx.drawImage(img, 350, 140, 380, 380); cx.restore();
          cx.strokeStyle = '#f5d98b'; cx.lineWidth = 8; cx.beginPath(); cx.arc(540, 330, 190, 0, 7); cx.stroke(); }
        cx.fillStyle = '#fff'; cx.textAlign = 'center'; cx.direction = D.rtl ? 'rtl' : 'ltr';
        cx.font = '700 64px Georgia, "Noto Kufi Arabic", serif';
        var lines = wrap(msg, 900), y = 640 - (lines.length - 1) * 40;
        lines.forEach(function (l2, k) { cx.fillText(l2, 540, y + k * 82); });
        cx.font = '600 40px system-ui, "Noto Kufi Arabic", sans-serif'; cx.fillStyle = '#f5d98b';
        cx.fillText('💞 ' + D.glyph[s] + ' ' + D.names[s] + ' 💞', 540, 930);
        cx.font = '500 30px system-ui, sans-serif'; cx.fillStyle = 'rgba(255,255,255,.75)'; cx.fillText(D.site, 540, 1020);
        cv.hidden = false; acts.hidden = false;
      };
      img.src = '/assets/signs/' + s + '.webp';
    }
    lmb.querySelectorAll('.lm-signs .mchip').forEach(function (b) {
      b.onclick = function () { lmb.querySelectorAll('.lm-signs .mchip').forEach(function (x) { x.classList.remove('on'); }); b.classList.add('on'); cur = b.dataset.s; idx = 0; drawCard(); setTimeout(function () { cv.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 200); };
    });
    $('.lm-next', lmb).onclick = function () { idx++; drawCard(); };
    $('.lm-save', lmb).onclick = function () { var a = document.createElement('a'); a.href = cv.toDataURL('image/png'); a.download = 'love-' + cur + '.png'; a.click(); };
    $('.lm-share', lmb).onclick = function () {
      cv.toBlob(function (blob) {
        var file = new File([blob], 'love-' + cur + '.png', { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [file] })) navigator.share({ files: [file], text: D.m[cur][idx % 3] }).catch(function () {});
        else $('.lm-save', lmb).click();
      }, 'image/png');
    };
  }
})();
