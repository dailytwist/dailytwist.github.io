/* DailyTwist Word Search: a new themed grid every day, in the page language. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'wordsearch') return;
  var G = window.DTG, t = G.t, el = G.el, get = G.get, set = G.set;
  var THEMES = JSON.parse(document.getElementById('ws-data').textContent);
  var N = 10, today = new Date().toISOString().slice(0, 10), KEY = 'dt-ws-' + (document.documentElement.lang || 'en');
  var dayNo = Math.floor(Date.now() / 864e5), extra = 0;
  var COLORS = ['#ff5e7e', '#3fc1c9', '#ffc53d', '#7c5cff', '#2fbf71', '#ff8a3d', '#4c8dff', '#d36bff'];

  function rnd(seed) { return function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }
  function letters(w) { return Array.from(w); }
  function build(seedN) {
    var th = THEMES[seedN % THEMES.length], R = rnd(seedN * 7919 + 17);
    var alphabet = Array.from(new Set(letters(th.words.join(''))));
    for (var attempt = 0; attempt < 60; attempt++) {
      var g = new Array(N * N).fill(''), placed = [], ok = true;
      var dirs = [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [1, -1], [-1, -1]];
      var words = th.words.slice().sort(function (a, b) { return letters(b).length - letters(a).length; });
      for (var i = 0; i < words.length && ok; i++) {
        var L = letters(words[i]), done = false;
        for (var tries = 0; tries < 300 && !done; tries++) {
          var d = dirs[Math.floor(R() * (attempt < 30 ? 4 : 8))], r = Math.floor(R() * N), c = Math.floor(R() * N);
          var er = r + d[0] * (L.length - 1), ec = c + d[1] * (L.length - 1);
          if (er < 0 || er >= N || ec < 0 || ec >= N) continue;
          var fits = true;
          for (var k = 0; k < L.length; k++) { var x = g[(r + d[0] * k) * N + c + d[1] * k]; if (x && x !== L[k]) { fits = false; break; } }
          if (!fits) continue;
          var cells = [];
          for (k = 0; k < L.length; k++) { var idx = (r + d[0] * k) * N + c + d[1] * k; g[idx] = L[k]; cells.push(idx); }
          placed.push({ w: words[i], cells: cells }); done = true;
        }
        if (!done) ok = false;
      }
      if (ok) { for (var j = 0; j < g.length; j++) if (!g[j]) g[j] = alphabet[Math.floor(R() * alphabet.length)]; return { theme: th.theme, g: g, words: placed }; }
    }
    return null;
  }

  var P, found, saved = get(KEY, null);
  var info = el('p', 'ws-theme'), fs = G.stat(t('ws_found')), tm = G.stat(t('time')), nb = el('button', 'btn small ghost', '↻ ' + t('new_game'));
  var board = el('div', 'ws-board'), list = el('div', 'ws-list'), cells = [], secs = 0, timer = null;
  root.append(info, G.bar([fs, tm, nb]), board, list);

  function start(seedN, keep) {
    P = build(seedN); if (!P) return;
    found = keep && keep.found ? keep.found : []; secs = keep && keep.secs || 0;
    board.innerHTML = ''; cells = [];
    P.g.forEach(function (ch, i) { var c = el('div', 'ws-cell', ch); c.dataset.i = i; cells.push(c); board.appendChild(c); });
    info.innerHTML = '🔤 ' + t('ws_theme') + ': <b>' + P.theme + '</b>';
    found.forEach(function (w, n) { mark(w, n); });
    drawList(); clearInterval(timer); timer = null; tm.set(fmt(secs));
    if (found.length === P.words.length) tm.set(fmt(secs));
  }
  function fmt(s) { return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function save() { set(KEY, { d: today, extra: extra, found: found, secs: secs }); }
  function drawList() {
    list.innerHTML = '';
    P.words.forEach(function (p) { var s = el('span', found.indexOf(p.w) > -1 ? 'done' : '', p.w); list.appendChild(s); });
    fs.set(found.length + '/' + P.words.length);
  }
  function mark(w, n) {
    var p = P.words.filter(function (x) { return x.w === w; })[0]; if (!p) return;
    p.cells.forEach(function (i) { cells[i].classList.add('found'); cells[i].style.setProperty('--c', COLORS[n % COLORS.length]); });
  }

  // selection: drag or tap-tap; snaps to straight lines
  var a = -1, cur = [];
  function line(i, j) {
    var r1 = Math.floor(i / N), c1 = i % N, r2 = Math.floor(j / N), c2 = j % N, dr = r2 - r1, dc = c2 - c1;
    if (!(dr === 0 || dc === 0 || Math.abs(dr) === Math.abs(dc))) return null;
    var n = Math.max(Math.abs(dr), Math.abs(dc)), sr = Math.sign(dr), sc = Math.sign(dc), out = [];
    for (var k = 0; k <= n; k++) out.push((r1 + sr * k) * N + c1 + sc * k);
    return out;
  }
  function paint(list2) { cells.forEach(function (c) { c.classList.remove('sel'); }); (list2 || []).forEach(function (i) { cells[i].classList.add('sel'); }); }
  function cellAt(x, y) { var e2 = document.elementFromPoint(x, y); return e2 && e2.classList && e2.classList.contains('ws-cell') ? +e2.dataset.i : -1; }
  var dragging = false, moved = false;
  board.addEventListener('pointerdown', function (e) {
    var i = cellAt(e.clientX, e.clientY); if (i < 0) return;
    e.preventDefault();
    if (!timer && found.length < P.words.length) timer = setInterval(function () { secs++; tm.set(fmt(secs)); if (secs % 5 === 0) save(); }, 1000);
    if (a >= 0 && !dragging) { finish(line(a, i)); a = -1; return; } // second tap
    a = i; dragging = true; moved = false; cur = [i]; paint(cur);
  });
  window.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    var i = cellAt(e.clientX, e.clientY); if (i < 0) return;
    if (i !== a) moved = true;
    var l = line(a, i); if (l) { cur = l; paint(cur); }
  });
  window.addEventListener('pointerup', function () {
    if (!dragging) return; dragging = false;
    if (moved) { finish(cur); a = -1; } // drag finished; otherwise wait for the second tap
  });
  function finish(sel) {
    paint(null); if (!sel || sel.length < 2) { G.bad(); return; }
    var str = sel.map(function (i) { return P.g[i]; }).join(''), rev = Array.from(str).reverse().join('');
    var hit = P.words.filter(function (p) { return (p.w === str || p.w === rev) && found.indexOf(p.w) < 0 && samecells(p.cells, sel); })[0];
    if (!hit) { G.bad(); return; }
    found.push(hit.w); mark(hit.w, found.length - 1); drawList(); G.good(); save();
    if (found.length === P.words.length) {
      clearInterval(timer); timer = null; G.fanfare(); G.confetti(); G.addXP(60);
      var best = get('dt-ws-best', null); if (best === null || secs < best) set('dt-ws-best', secs);
      setTimeout(function () { G.winBox('🎉 ' + t('you_won'), [t('time') + ': ' + fmt(secs)], function () { extra++; start(dayNo + extra * 3); save(); }); }, 500);
    }
  }
  function samecells(a1, b1) { var x = a1.slice().sort(), y = b1.slice().sort(); return x.length === y.length && x.every(function (v, k) { return v === y[k]; }); }
  nb.onclick = function () { extra++; start(dayNo + extra * 3); save(); };

  if (saved && saved.d === today) { extra = saved.extra || 0; start(dayNo + extra * 3, saved); } else start(dayNo);
})();
