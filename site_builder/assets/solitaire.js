/* DailyTwist Solitaire (Klondike). Tap a card to send it to the best place. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'solitaire') return;
  var G = window.DTG, t = G.t, el = G.el, get = G.get, set = G.set;
  var KEY = 'dt-sol-state', SUITS = ['♠', '♥', '♦', '♣'], RANKS = ['', 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

  var S, hist = [], timer = null, mode = get('dt-sol-mode', 'easy');
  var mv = G.stat(t('moves')), tm = G.stat(t('time')), bt = G.stat(t('best'));
  var undo = el('button', 'btn small ghost', '↶ ' + t('undo')), nb = el('button', 'btn small', '↻ ' + t('new_game'));
  var auto = el('button', 'btn small sol-auto', '⚡ ' + t('auto_finish'));
  var modes = G.pills([['easy', t('draw_1')], ['hard', t('draw_3')]], mode, function (m) { mode = m; set('dt-sol-mode', m); deal(); });
  root.append(modes, G.bar([mv, tm, bt, undo, nb]));
  var table = el('div', 'sol'); root.appendChild(table); root.appendChild(auto);

  function red(c) { return c.s === 1 || c.s === 2; }
  function deal() {
    var deck = []; for (var s = 0; s < 4; s++) for (var r = 1; r <= 13; r++) deck.push({ s: s, r: r, up: false });
    G.shuffle(deck);
    S = { tab: [[], [], [], [], [], [], []], fnd: [[], [], [], []], stock: [], waste: [], moves: 0, secs: 0, mode: mode, won: false };
    for (var i = 0; i < 7; i++) for (var j = i; j < 7; j++) S.tab[j].push(deck.pop());
    S.tab.forEach(function (col) { col[col.length - 1].up = true; });
    S.stock = deck; hist = []; stopClock(); save(); draw();
  }
  function snap() { hist.push(JSON.stringify(S)); if (hist.length > 200) hist.shift(); }
  function save() { set(KEY, S); }
  function startClock() { if (!timer && !S.won) timer = setInterval(function () { S.secs++; tm.set(fmt(S.secs)); if (S.secs % 5 === 0) save(); }, 1000); }
  function stopClock() { clearInterval(timer); timer = null; }
  function fmt(s) { return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }

  // ---------------------------------------------------------------- rules
  function canFnd(c, f) { var top = S.fnd[f][S.fnd[f].length - 1]; return top ? top.s === c.s && c.r === top.r + 1 : c.r === 1; }
  function canTab(c, col) { var top = S.tab[col][S.tab[col].length - 1]; return top ? top.up && red(top) !== red(c) && c.r === top.r - 1 : c.r === 13; }
  function fndFor(c) { for (var f = 0; f < 4; f++) if (canFnd(c, f)) return f; return -1; }
  function flipTops() { S.tab.forEach(function (col) { var c = col[col.length - 1]; if (c && !c.up) c.up = true; }); }
  function did() { S.moves++; flipTops(); startClock(); save(); draw(); checkWin(); }

  function tapStock() {
    snap();
    if (S.stock.length) {
      var n = S.mode === 'hard' ? 3 : 1;
      for (var i = 0; i < n && S.stock.length; i++) { var c = S.stock.pop(); c.up = true; S.waste.push(c); }
    } else if (S.waste.length) {
      S.stock = S.waste.reverse().map(function (c) { c.up = false; return c; }); S.waste = [];
    } else { hist.pop(); return; }
    G.beep(520, .04, 'triangle', .03); did();
  }
  // move the card(s) from a source to the best destination
  function tapCard(src, idx) {
    var pile = src[0] === 't' ? S.tab[src[1]] : src[0] === 'w' ? S.waste : S.fnd[src[1]];
    var c = pile[idx]; if (!c || !c.up) return;
    var single = idx === pile.length - 1, dest = null;
    if (single && src[0] !== 'f') { var f = fndFor(c); if (f >= 0) dest = ['f', f]; }
    if (!dest) {
      var best = -1, bestScore = -1;
      for (var k = 0; k < 7; k++) {
        if (src[0] === 't' && src[1] === k) continue;
        if (!canTab(c, k)) continue;
        var score = S.tab[k].length ? 2 : 1; // prefer building on cards over using an empty column
        if (c.r === 13 && src[0] === 't' && idx === 0) score = 0; // a king already on an empty column has nowhere better
        if (score > bestScore) { bestScore = score; best = k; }
      }
      if (best >= 0 && bestScore > 0) dest = ['t', best];
    }
    if (!dest) { shake(src, idx); G.bad(); return; }
    snap();
    var moving = pile.splice(idx);
    if (dest[0] === 'f') S.fnd[dest[1]].push(moving[0]); else S.tab[dest[1]] = S.tab[dest[1]].concat(moving);
    last = dest; G.good(); did();
  }
  var last = null;
  function shake(src, idx) { var n = table.querySelector('[data-src="' + src.join('') + '"][data-i="' + idx + '"]'); if (n) { n.classList.remove('shake'); void n.offsetWidth; n.classList.add('shake'); } }

  function allOpen() { return !S.stock.length && !S.waste.length && S.tab.every(function (col) { return col.every(function (c) { return c.up; }); }); }
  function checkWin() {
    auto.style.display = !S.won && allOpen() && S.fnd.some(function (f) { return f.length < 13; }) ? '' : 'none';
    if (S.fnd.every(function (f) { return f.length === 13; }) && !S.won) {
      S.won = true; stopClock(); save();
      var bestT = get('dt-sol-best', null), rec = bestT === null || S.secs < bestT;
      if (rec) set('dt-sol-best', S.secs);
      bt.set(fmt(rec ? S.secs : bestT));
      G.fanfare(); G.confetti(); G.addXP(S.mode === 'hard' ? 160 : 100);
      setTimeout(function () { G.winBox((rec ? '🏆 ' + t('new_record') : '🎉 ' + t('you_won')), [t('moves') + ': ' + S.moves, t('time') + ': ' + fmt(S.secs)], deal); }, 600);
    }
  }
  auto.onclick = function () {
    auto.disabled = true;
    (function step() {
      for (var k = 0; k < 7; k++) { var col = S.tab[k], c = col[col.length - 1]; if (c) { var f = fndFor(c); if (f >= 0) { col.pop(); S.fnd[f].push(c); S.moves++; draw(); G.beep(600 + S.moves % 8 * 40, .05, 'triangle', .04); return setTimeout(step, 90); } } }
      auto.disabled = false; save(); checkWin();
    })();
  };

  // ---------------------------------------------------------------- drawing
  function face(c) {
    var d = el('div', 'card ' + (c.up ? 'up' : 'down') + (c.up && red(c) ? ' red' : ''));
    if (c.up) d.innerHTML = '<b>' + RANKS[c.r] + '<i>' + SUITS[c.s] + '</i></b><span>' + (c.r > 10 ? '<em>' + RANKS[c.r] + '</em>' : '') + SUITS[c.s] + '</span>';
    return d;
  }
  function slot(cls, label) { var d = el('div', 'slot ' + cls); if (label) d.textContent = label; return d; }
  function draw() {
    var W = table.clientWidth || 340, cw = Math.min(84, (W - 6 * 6) / 7), ch = cw * 1.4;
    table.style.setProperty('--cw', cw + 'px'); table.style.setProperty('--ch', ch + 'px');
    table.innerHTML = '';
    var row = el('div', 'sol-top');
    var st = slot('stock', S.stock.length ? '' : '↻');
    if (S.stock.length) { var b = face({ up: false }); b.classList.add('stack'); st.appendChild(b); }
    st.onclick = tapStock; row.appendChild(st);
    var wa = slot('waste'); var show = S.waste.slice(S.mode === 'hard' ? -3 : -1);
    show.forEach(function (c, i) {
      var f = face(c); f.style.left = i * cw * .28 + 'px';
      if (i === show.length - 1) { var idx = S.waste.length - 1; f.dataset.src = 'w'; f.dataset.i = idx; f.onclick = function () { tapCard(['w'], idx); }; } else f.classList.add('muted');
      wa.appendChild(f);
    });
    row.appendChild(wa); row.appendChild(el('div', 'slot gap'));
    S.fnd.forEach(function (fp, k) {
      var s = slot('fnd', 'A'); var c = fp[fp.length - 1];
      if (c) { var f = face(c); f.dataset.src = 'f' + k; f.dataset.i = fp.length - 1; f.onclick = function () { tapFnd(k); }; if (last && last[0] === 'f' && last[1] === k) f.classList.add('pop'); s.appendChild(f); }
      row.appendChild(s);
    });
    table.appendChild(row);
    var tab = el('div', 'sol-tab'), maxH = Math.max(ch * 3.2, Math.min(window.innerHeight * .62, 560));
    S.tab.forEach(function (col, k) {
      var cdiv = slot('col'), down = 0, up = 0; col.forEach(function (c) { if (c.up) up++; else down++; });
      var dStep = Math.min(ch * .12, 10), uStep = up > 1 ? Math.min(ch * .3, (maxH - ch - down * dStep) / (up - 1)) : 0, y = 0;
      col.forEach(function (c, i) {
        var f = face(c); f.style.top = y + 'px'; y += c.up ? uStep : dStep;
        if (c.up) { f.dataset.src = 't' + k; f.dataset.i = i; f.onclick = function () { tapCard(['t', k], i); }; }
        if (last && last[0] === 't' && last[1] === k && i === col.length - 1) f.classList.add('pop');
        cdiv.appendChild(f);
      });
      cdiv.style.height = Math.max(ch, y - (col.length && col[col.length - 1].up ? uStep : dStep) + ch) + 'px';
      tab.appendChild(cdiv);
    });
    table.appendChild(tab);
    mv.set(S.moves); tm.set(fmt(S.secs)); var b2 = get('dt-sol-best', null); bt.set(b2 === null ? '–' : fmt(b2));
    undo.disabled = !hist.length; last = null;
  }
  function tapFnd(k) { // bring a card back from a foundation onto the tableau
    var fp = S.fnd[k], c = fp[fp.length - 1]; if (!c) return;
    for (var j = 0; j < 7; j++) if (S.tab[j].length && canTab(c, j)) { snap(); S.tab[j].push(fp.pop()); last = ['t', j]; G.good(); did(); return; }
    shake(['f', k], fp.length - 1); G.bad();
  }
  undo.onclick = function () { if (!hist.length) return; S = JSON.parse(hist.pop()); S.moves++; save(); draw(); checkWin(); };
  nb.onclick = function () { if (S.moves < 5 || S.won || confirm(t('new_game') + '?')) deal(); };
  window.addEventListener('resize', function () { if (S) draw(); });

  var saved = get(KEY, null);
  if (saved && saved.tab && saved.fnd && !saved.won && saved.mode === mode) { S = saved; draw(); checkWin(); if (S.moves) startClock(); }
  else deal();
  checkWin();
})();
