/* DailyTwist chess: rules engine + simple AI + board UI. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'chess') return;
  var G = window.DTG; // shared helpers from games.js
  var t = G.t, el = G.el;

  // ---------------------------------------------------------------- rules
  // board: 64 array, index = r*8+c, r=0 is rank 8. Pieces: 'P','N','B','R','Q','K' white, lowercase black, '' empty
  var N = [-17, -15, -10, -6, 6, 10, 15, 17], KD = [-9, -8, -7, -1, 1, 7, 8, 9];
  function col(p) { return p ? (p === p.toUpperCase() ? 'w' : 'b') : ''; }
  function newState() {
    var b = 'rnbqkbnrpppppppp' + new Array(33).join(' ') + 'PPPPPPPPRNBQKBNR';
    return { b: b.split('').map(function (x) { return x === ' ' ? '' : x; }), turn: 'w', castle: { K: 1, Q: 1, k: 1, q: 1 }, ep: -1, half: 0, hist: [] };
  }
  function inside(i, d, step) { // guard board wrap-around for a single step from i
    var r = i >> 3, c = i & 7, j = i + d; if (j < 0 || j > 63) return false;
    return Math.abs((j & 7) - c) <= step && Math.abs((j >> 3) - r) <= step;
  }
  function attacked(s, sq, by) {
    var b = s.b, i, j, p;
    // pawns
    var dir = by === 'w' ? 8 : -8;
    [-1, 1].forEach(function () {});
    for (var dc = -1; dc <= 1; dc += 2) { j = sq + dir + dc; if (inside(sq, dir + dc, 1) && b[j] === (by === 'w' ? 'P' : 'p')) return true; }
    for (i = 0; i < 8; i++) { j = sq + N[i]; if (inside(sq, N[i], 2) && b[j] === (by === 'w' ? 'N' : 'n')) return true; }
    for (i = 0; i < 8; i++) { j = sq + KD[i]; if (inside(sq, KD[i], 1) && b[j] === (by === 'w' ? 'K' : 'k')) return true; }
    for (i = 0; i < 8; i++) {
      var d = KD[i], diag = d === -9 || d === -7 || d === 7 || d === 9, cur = sq;
      while (inside(cur, d, 1)) {
        cur += d; p = b[cur]; if (!p) continue;
        if (col(p) === by) { var u = p.toUpperCase(); if (u === 'Q' || (diag ? u === 'B' : u === 'R')) return true; }
        break;
      }
    }
    return false;
  }
  function kingSq(s, c) { return s.b.indexOf(c === 'w' ? 'K' : 'k'); }
  function inCheck(s, c) { return attacked(s, kingSq(s, c), c === 'w' ? 'b' : 'w'); }
  function pseudo(s) {
    var b = s.b, me = s.turn, op = me === 'w' ? 'b' : 'w', mv = [];
    function add(f, to, extra) { mv.push(Object.assign({ f: f, t: to, cap: b[to] }, extra || {})); }
    for (var i = 0; i < 64; i++) {
      var p = b[i]; if (col(p) !== me) continue; var u = p.toUpperCase(), r = i >> 3;
      if (u === 'P') {
        var d = me === 'w' ? -8 : 8, start = me === 'w' ? 6 : 1, last = me === 'w' ? 0 : 7;
        var one = i + d;
        if (one >= 0 && one < 64 && !b[one]) {
          if ((one >> 3) === last) add(i, one, { promo: me === 'w' ? 'Q' : 'q' }); else add(i, one);
          if (r === start && !b[one + d]) add(i, one + d, { dbl: 1 });
        }
        [-1, 1].forEach(function (dc) {
          if (!inside(i, d + dc, 1)) return; var j = i + d + dc;
          if (col(b[j]) === op) { if ((j >> 3) === last) add(i, j, { promo: me === 'w' ? 'Q' : 'q' }); else add(i, j); }
          else if (j === s.ep) add(i, j, { epCap: j - d });
        });
      } else if (u === 'N' || u === 'K') {
        var D = u === 'N' ? N : KD, st = u === 'N' ? 2 : 1;
        for (var k = 0; k < 8; k++) { if (!inside(i, D[k], st)) continue; var j = i + D[k]; if (col(b[j]) !== me) add(i, j); }
        if (u === 'K') {
          var rk = me === 'w' ? 7 : 0, home = rk * 8 + 4;
          if (i === home && !inCheck(s, me)) {
            var K = me === 'w' ? 'K' : 'k', Q = me === 'w' ? 'Q' : 'q';
            if (s.castle[K] && !b[home + 1] && !b[home + 2] && b[home + 3] === (me === 'w' ? 'R' : 'r') && !attacked(s, home + 1, op) && !attacked(s, home + 2, op)) add(i, home + 2, { castle: 'k' });
            if (s.castle[Q] && !b[home - 1] && !b[home - 2] && !b[home - 3] && b[home - 4] === (me === 'w' ? 'R' : 'r') && !attacked(s, home - 1, op) && !attacked(s, home - 2, op)) add(i, home - 2, { castle: 'q' });
          }
        }
      } else {
        var dirs = u === 'B' ? [-9, -7, 7, 9] : u === 'R' ? [-8, -1, 1, 8] : KD;
        dirs.forEach(function (d) { var cur = i; while (inside(cur, d, 1)) { cur += d; if (!b[cur]) add(i, cur); else { if (col(b[cur]) === op) add(i, cur); break; } } });
      }
    }
    return mv;
  }
  function make(s, m) {
    var b = s.b, p = b[m.f];
    s.hist.push({ b: b.slice(), castle: Object.assign({}, s.castle), ep: s.ep, turn: s.turn, half: s.half });
    b[m.t] = m.promo || p; b[m.f] = '';
    if (m.epCap !== undefined) b[m.epCap] = '';
    if (m.castle) { var rk = m.t >> 3 << 3; if (m.castle === 'k') { b[rk + 5] = b[rk + 7]; b[rk + 7] = ''; } else { b[rk + 3] = b[rk]; b[rk] = ''; } }
    if (p === 'K') s.castle.K = s.castle.Q = 0; if (p === 'k') s.castle.k = s.castle.q = 0;
    [[63, 'K'], [56, 'Q'], [7, 'k'], [0, 'q']].forEach(function (x) { if (m.f === x[0] || m.t === x[0]) s.castle[x[1]] = 0; });
    s.ep = m.dbl ? (m.f + m.t) / 2 : -1;
    s.half = (p.toUpperCase() === 'P' || m.cap) ? 0 : s.half + 1;
    s.turn = s.turn === 'w' ? 'b' : 'w';
  }
  function unmake(s) { var h = s.hist.pop(); s.b = h.b; s.castle = h.castle; s.ep = h.ep; s.turn = h.turn; s.half = h.half; }
  function legal(s) {
    var me = s.turn;
    return pseudo(s).filter(function (m) { make(s, m); var ok = !inCheck(s, me); unmake(s); return ok; });
  }

  // ---------------------------------------------------------------- AI
  var V = { P: 100, N: 320, B: 330, R: 500, Q: 900, K: 0 };
  var PST_P = [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10, 5, 5, 10, 25, 25, 10, 5, 5, 0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5, 5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0];
  var PST_N = [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40, -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30, -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30, -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50];
  var PST_C = [-10, -5, -5, -5, -5, -5, -5, -10, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 5, 5, 5, 5, 0, -5, -5, 5, 5, 10, 10, 5, 5, -5, -5, 5, 5, 10, 10, 5, 5, -5, -5, 0, 5, 5, 5, 5, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -10, -5, -5, -5, -5, -5, -5, -10];
  function evalB(s) {
    var sc = 0;
    for (var i = 0; i < 64; i++) {
      var p = s.b[i]; if (!p) continue; var u = p.toUpperCase(), w = p === u, idx = w ? i : (7 - (i >> 3)) * 8 + (i & 7);
      var v = V[u] + (u === 'P' ? PST_P[idx] : u === 'N' ? PST_N[idx] : u === 'K' ? 0 : PST_C[idx]);
      sc += w ? v : -v;
    }
    return sc;
  }
  function search(s, depth, a, b, color) {
    if (depth === 0) return color * evalB(s);
    var ms = legal(s);
    if (!ms.length) return inCheck(s, s.turn) ? -99999 - depth : 0;
    ms.sort(function (x, y) { return (y.cap ? V[y.cap.toUpperCase()] : 0) - (x.cap ? V[x.cap.toUpperCase()] : 0); });
    for (var i = 0; i < ms.length; i++) {
      make(s, ms[i]); var v = -search(s, depth - 1, -b, -a, -color); unmake(s);
      if (v >= b) return v; if (v > a) a = v;
    }
    return a;
  }
  function best(s, depth, noise) {
    var ms = legal(s), color = s.turn === 'w' ? 1 : -1, top = -1e9, pick = [];
    ms.sort(function (x, y) { return (y.cap ? 1 : 0) - (x.cap ? 1 : 0); });
    ms.forEach(function (m) {
      make(s, m); var v = -search(s, depth - 1, -1e9, 1e9, -color) + Math.random() * noise; unmake(s);
      if (v > top + 0.5) { top = v; pick = [m]; } else if (Math.abs(v - top) <= 0.5) pick.push(m);
    });
    return pick[Math.floor(Math.random() * pick.length)];
  }

  // ---------------------------------------------------------------- UI
  var GLYPH = { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟' };
  var diff = G.get('dt-chess-diff', 'medium'), DEPTH = { easy: 1, medium: 2, hard: 3 }, NOISE = { easy: 120, medium: 25, hard: 4 };
  var score = G.get('dt-chess-score', { w: 0, l: 0, d: 0 });
  var status = el('span', 'stat big'), undoB = el('button', 'btn small ghost', '↶ ' + t('undo')), nb = el('button', 'btn small', t('new_game'));
  var sw = G.stat(t('wins')), sl = G.stat(t('losses')), sd = G.stat(t('draws'));
  root.append(G.pills(G.DIFF, diff, function (d) { diff = d; G.set('dt-chess-diff', d); start(); }), G.bar([sw, sl, sd, undoB, nb]), status);
  var board = el('div', 'cboard'), cells = []; root.appendChild(board);
  var S, sel = -1, moves = [], last = null, busy = false, over = false;
  for (var i = 0; i < 64; i++) (function (i) {
    var c = el('button', 'cs ' + (((i >> 3) + (i & 7)) % 2 ? 'dk' : 'lt')); c.onclick = function () { tap(i); }; cells.push(c); board.appendChild(c);
  })(i);
  function draw() {
    var chk = inCheck(S, S.turn) ? kingSq(S, S.turn) : -1;
    var targets = moves.filter(function (m) { return m.f === sel; }).map(function (m) { return m.t; });
    cells.forEach(function (c, i) {
      var p = S.b[i];
      c.innerHTML = p ? '<span class="pc ' + col(p) + '">' + GLYPH[p.toLowerCase()] + '</span>' : '';
      c.classList.toggle('sel', i === sel); c.classList.toggle('chk', i === chk);
      c.classList.toggle('last', !!last && (i === last.f || i === last.t));
      c.classList.toggle('dot', targets.indexOf(i) > -1 && !p); c.classList.toggle('hit', targets.indexOf(i) > -1 && !!p);
    });
    sw.set(score.w); sl.set(score.l); sd.set(score.d); undoB.disabled = S.hist.length < 2 || busy;
  }
  function finish() {
    var ms = legal(S);
    if (ms.length && S.half < 100) { status.textContent = busy ? '🤔 ' + t('thinking') : (inCheck(S, 'w') ? '⚠️ ' + t('check') + ' — ' : '') + t('your_move'); return false; }
    over = true;
    if (!ms.length && inCheck(S, S.turn)) {
      if (S.turn === 'b') { score.w++; status.textContent = '🏆 ' + t('checkmate_win'); G.fanfare(); G.confetti(); G.addXP({ easy: 30, medium: 70, hard: 150 }[diff]); }
      else { score.l++; status.textContent = '🤖 ' + t('checkmate_lose'); G.bad(); }
    } else { score.d++; status.textContent = '🤝 ' + t('draw'); G.addXP(10); }
    G.set('dt-chess-score', score); draw(); return true;
  }
  function tap(i) {
    if (busy || over || S.turn !== 'w') return;
    var m = moves.filter(function (x) { return x.f === sel && x.t === i; })[0];
    if (m) { play(m); return; }
    sel = col(S.b[i]) === 'w' ? i : -1; G.beep(600, .03); draw();
  }
  function play(m) {
    make(S, m); last = m; sel = -1; G.beep(m.cap ? 260 : 420, .07, 'triangle'); moves = []; draw();
    if (finish()) return;
    busy = true; draw(); finish();
    setTimeout(function () {
      var r = best(S, DEPTH[diff], NOISE[diff]); make(S, r); last = r; G.beep(r.cap ? 230 : 360, .07, 'triangle');
      busy = false; moves = legal(S); draw(); finish();
    }, 60);
  }
  undoB.onclick = function () { if (busy || S.hist.length < 2) return; unmake(S); unmake(S); over = false; last = null; sel = -1; moves = legal(S); draw(); finish(); };
  function start() { S = newState(); sel = -1; last = null; over = false; busy = false; moves = legal(S); draw(); finish(); }
  nb.onclick = start; start();
})();
