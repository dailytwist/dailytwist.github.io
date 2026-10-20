/* DailyTwist Mahjong Solitaire: match pairs of free tiles. Every deal is solvable. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'mahjong') return;
  var G = window.DTG, t = G.t, el = G.el, get = G.get, set = G.set;
  var FACES = ['🍎', '🍋', '🍇', '🍓', '🍒', '🍑', '🌸', '🌻', '🍀', '⭐', '🌙', '☀️', '🐟', '🦋', '🐱', '🐶', '🔔', '💎'];
  var KEY = 'dt-mj-state';

  // layout in half-tile units: each tile covers x..x+2, y..y+2 on layer z
  function layout() {
    var P = [];
    function rect(z, x0, y0, cols, rows) { for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) P.push({ x: x0 + c * 2, y: y0 + r * 2, z: z }); }
    rect(0, 2, 0, 8, 5);          // 40
    P.push({ x: 0, y: 3, z: 0 }, { x: 18, y: 3, z: 0 }, { x: 0, y: 5, z: 0 }, { x: 18, y: 5, z: 0 }); // wings: 44
    rect(1, 4, 1, 6, 3);          // 18 -> 62
    rect(2, 6, 2, 4, 2);          // 8 -> 70
    P.push({ x: 9, y: 4, z: 3 }, { x: 9, y: 2, z: 3 }); // 72
    return P;
  }
  var POS = layout();
  function overlapsXY(a, b) { return Math.abs(a.x - b.x) < 2 && Math.abs(a.y - b.y) < 2; }
  function isFree(i, alive) {
    var a = POS[i], left = false, right = false;
    for (var j = 0; j < POS.length; j++) {
      if (!alive[j] || j === i) continue;
      var b = POS[j];
      if (b.z === a.z + 1 && overlapsXY(a, b)) return false;
      if (b.z > a.z + 1 && overlapsXY(a, b)) return false;
      if (b.z === a.z && Math.abs(a.y - b.y) < 2) { if (b.x === a.x - 2) left = true; if (b.x === a.x + 2) right = true; }
    }
    return !(left && right);
  }
  function deal() { // reverse-removal guarantees a solution
    for (var tries = 0; tries < 200; tries++) {
      var alive = POS.map(function () { return true; }), kinds = new Array(POS.length), left = POS.length;
      var bag = []; FACES.forEach(function (f, k) { bag.push(k, k); }); G.shuffle(bag); // 36 pair-kinds (each face twice = 4 tiles)
      var ok = true, pi = 0;
      while (left > 0) {
        var free = []; for (var i = 0; i < POS.length; i++) if (alive[i] && isFree(i, alive)) free.push(i);
        if (free.length < 2) { ok = false; break; }
        G.shuffle(free); var a = free[0], b = free[1], k = bag[pi++];
        kinds[a] = k; kinds[b] = k; alive[a] = alive[b] = false; left -= 2;
      }
      if (ok) return kinds;
    }
    return null;
  }

  var S, hist = [], sel = -1, timer = null;
  var pr = G.stat(t('mj_pairs')), tm = G.stat(t('time')), bt = G.stat(t('best'));
  var hint = el('button', 'btn small ghost', '💡 ' + t('hint')), undo = el('button', 'btn small ghost', '↶ ' + t('undo'));
  var shuf = el('button', 'btn small ghost', '🔀 ' + t('mj_shuffle')), nb = el('button', 'btn small', '↻ ' + t('new_game'));
  var row2 = el('div', 'gbar'); [hint, undo, shuf, nb].forEach(function (x) { row2.appendChild(x); });
  root.append(G.bar([pr, tm, bt]), row2);
  var board = el('div', 'mj'), msg = el('p', 'msg'); root.append(board, msg);

  function fmt(s) { return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function save() { set(KEY, S); }
  function fresh() { S = { k: deal(), alive: POS.map(function () { return true; }), secs: 0, won: false }; hist = []; sel = -1; stop(); save(); draw(); }
  function stop() { clearInterval(timer); timer = null; }
  function tick() { if (!timer && !S.won) timer = setInterval(function () { S.secs++; tm.set(fmt(S.secs)); if (S.secs % 5 === 0) save(); }, 1000); }
  function moves() {
    var free = []; for (var i = 0; i < POS.length; i++) if (S.alive[i] && isFree(i, S.alive)) free.push(i);
    for (var a = 0; a < free.length; a++) for (var b = a + 1; b < free.length; b++) if (S.k[free[a]] === S.k[free[b]]) return [free[a], free[b]];
    return null;
  }
  function draw() {
    var W = board.clientWidth || 340, tw = Math.min(56, W / 10.6), th = tw * 1.3, d = Math.max(3, tw * .09);
    board.style.height = (5 * 2 / 2 * th + th * .3 + 8) + 'px';
    board.innerHTML = '';
    var order = POS.map(function (p, i) { return i; }).sort(function (a, b) { return POS[a].z - POS[b].z || POS[a].y - POS[b].y || POS[b].x - POS[a].x; });
    order.forEach(function (i) {
      if (!S.alive[i]) return;
      var p = POS[i], free = isFree(i, S.alive), c = el('button', 'mt' + (free ? ' free' : '') + (i === sel ? ' on' : ''));
      c.style.width = tw + 'px'; c.style.height = th + 'px'; c.style.fontSize = tw * .55 + 'px';
      c.style.left = (p.x / 2 * tw + 4 - p.z * d + d * 2) + 'px'; c.style.top = (p.y / 2 * th + 4 - p.z * d + d * 2) + 'px';
      c.style.zIndex = p.z * 100 + p.y * 2 + (20 - p.x);
      c.textContent = FACES[S.k[i]]; c.dataset.i = i;
      c.onclick = function () { tap(i); };
      board.appendChild(c);
    });
    var left = S.alive.filter(Boolean).length / 2;
    pr.set(left); tm.set(fmt(S.secs)); var b = get('dt-mj-best', null); bt.set(b === null ? '–' : fmt(b));
    undo.disabled = !hist.length;
    msg.textContent = !S.won && left && !moves() ? '🔀 ' + t('mj_stuck') : '';
  }
  function tap(i) {
    if (S.won) return;
    if (!isFree(i, S.alive)) { var n = board.querySelector('[data-i="' + i + '"]'); if (n) { n.classList.remove('shake'); void n.offsetWidth; n.classList.add('shake'); } G.bad(); return; }
    tick();
    if (sel < 0 || sel === i) { sel = sel === i ? -1 : i; G.beep(500, .04, 'triangle', .03); draw(); return; }
    if (S.k[sel] === S.k[i]) {
      hist.push(JSON.stringify(S)); S.alive[sel] = S.alive[i] = false; sel = -1; G.good(); save(); draw();
      if (!S.alive.some(Boolean)) win();
    } else { sel = i; G.bad(); draw(); }
  }
  function win() {
    S.won = true; stop(); save();
    var b = get('dt-mj-best', null), rec = b === null || S.secs < b; if (rec) set('dt-mj-best', S.secs);
    G.fanfare(); G.confetti(); G.addXP(120);
    setTimeout(function () { G.winBox(rec ? '🏆 ' + t('new_record') : '🎉 ' + t('you_won'), [t('time') + ': ' + fmt(S.secs)], fresh); }, 500);
  }
  hint.onclick = function () {
    var m = moves(); if (!m) { G.bad(); return; }
    m.forEach(function (i) { var n = board.querySelector('[data-i="' + i + '"]'); if (n) { n.classList.add('hint'); setTimeout(function () { n.classList.remove('hint'); }, 1200); } });
    S.secs += 10; tm.set(fmt(S.secs));
  };
  undo.onclick = function () { if (!hist.length) return; S = JSON.parse(hist.pop()); sel = -1; save(); draw(); };
  shuf.onclick = function () { // reshuffle remaining faces; keep trying until a move exists
    var idx = [], ks = []; S.alive.forEach(function (a, i) { if (a) { idx.push(i); ks.push(S.k[i]); } });
    for (var tries = 0; tries < 50; tries++) { G.shuffle(ks); idx.forEach(function (i, j) { S.k[i] = ks[j]; }); if (moves()) break; }
    hist = []; sel = -1; save(); draw();
  };
  nb.onclick = function () { if (S.alive.filter(Boolean).length > 66 && !S.won || confirm(t('new_game') + '?')) fresh(); };
  window.addEventListener('resize', function () { if (S) draw(); });

  var saved = get(KEY, null);
  if (saved && saved.k && saved.k.length === POS.length && !saved.won) { S = saved; draw(); } else fresh();
})();
