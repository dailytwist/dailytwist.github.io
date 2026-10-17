/* DailyTwist Ludo / Parchís: you (red) vs 3 computer players. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'ludo') return;
  var G = window.DTG, t = G.t, el = G.el;

  var PATH = [[6,1],[6,2],[6,3],[6,4],[6,5],[5,6],[4,6],[3,6],[2,6],[1,6],[0,6],[0,7],[0,8],[1,8],[2,8],[3,8],[4,8],[5,8],
    [6,9],[6,10],[6,11],[6,12],[6,13],[6,14],[7,14],[8,14],[8,13],[8,12],[8,11],[8,10],[8,9],[9,8],[10,8],[11,8],[12,8],[13,8],
    [14,8],[14,7],[14,6],[13,6],[12,6],[11,6],[10,6],[9,6],[8,5],[8,4],[8,3],[8,2],[8,1],[8,0],[7,0],[6,0]];
  var P = [ // color, start index on PATH, home column cells, base spots, label key
    { c: '#e5484d', s: 0, home: [[7,1],[7,2],[7,3],[7,4],[7,5]], base: [[1.5,1.5],[1.5,3.5],[3.5,1.5],[3.5,3.5]], name: 'you' },
    { c: '#2fa36b', s: 13, home: [[1,7],[2,7],[3,7],[4,7],[5,7]], base: [[1.5,10.5],[1.5,12.5],[3.5,10.5],[3.5,12.5]], name: 'bot' },
    { c: '#f5b301', s: 26, home: [[7,13],[7,12],[7,11],[7,10],[7,9]], base: [[10.5,10.5],[10.5,12.5],[12.5,10.5],[12.5,12.5]], name: 'bot' },
    { c: '#3a6ff7', s: 39, home: [[13,7],[12,7],[11,7],[10,7],[9,7]], base: [[10.5,1.5],[10.5,3.5],[12.5,1.5],[12.5,3.5]], name: 'bot' }];
  var CENTER = [[7.5, 6.6], [6.6, 7.5], [7.5, 8.4], [8.4, 7.5]];
  var SAFE = [0, 8, 13, 21, 26, 34, 39, 47];
  var FINISH = 56; // relative steps: -1 base, 0..50 track, 51..55 home column, 56 done

  var count = G.get('dt-ludo-tokens', 4);
  var dieBtn = el('button', 'die', '🎲'), status = el('span', 'stat big'), nb = el('button', 'btn small', t('new_game'));
  var wins = G.stat(t('wins'));
  root.append(G.pills([[2, t('quick')], [4, t('classic')]], count, function (n) { count = n; G.set('dt-ludo-tokens', n); start(); }), G.bar([wins, nb]), status);
  var board = el('div', 'lboard'); root.appendChild(board);
  var dock = el('div', 'ldock'); dock.appendChild(dieBtn); root.appendChild(dock);

  // static board
  for (var r = 0; r < 15; r++) for (var c = 0; c < 15; c++) {
    var cls = 'lc', st = '';
    var ti = PATH.findIndex(function (p) { return p[0] === r && p[1] === c; });
    if (r < 6 && c < 6) { cls += ' base'; st = P[0].c; } else if (r < 6 && c > 8) { cls += ' base'; st = P[1].c; }
    else if (r > 8 && c > 8) { cls += ' base'; st = P[2].c; } else if (r > 8 && c < 6) { cls += ' base'; st = P[3].c; }
    else if (r >= 6 && r <= 8 && c >= 6 && c <= 8) cls += ' mid';
    else cls += ' track';
    P.forEach(function (p) { p.home.forEach(function (h) { if (h[0] === r && h[1] === c) { cls += ' homec'; st = p.c; } }); if (ti === p.s) { cls += ' startc'; st = p.c; } });
    if (ti > -1 && SAFE.indexOf(ti) > -1 && P.every(function (p) { return p.s !== ti; })) cls += ' safe';
    var d = el('div', cls); d.style.gridArea = (r + 1) + '/' + (c + 1); if (st) d.style.setProperty('--pc', st); board.appendChild(d);
  }
  var centre = el('div', 'lcenter'); board.appendChild(centre);
  P.forEach(function (p, i) { var y = el('div', 'lyard'); y.style.setProperty('--pc', p.c); y.style.gridArea = ['1/1/7/7', '1/10/7/16', '10/10/16/16', '10/1/16/7'][i]; board.appendChild(y); });

  var tokens, turn, dice, phase, sixes, tokEls = [];
  function pos(pl, k) {
    var rp = tokens[pl][k];
    if (rp < 0) return P[pl].base[k];
    if (rp >= FINISH) return CENTER[pl];
    if (rp > 50) { var h = P[pl].home[rp - 51]; return [h[0] + .5, h[1] + .5]; }
    var q = PATH[(P[pl].s + rp) % 52]; return [q[0] + .5, q[1] + .5];
  }
  function cellOf(pl, k) { var rp = tokens[pl][k]; return rp < 0 || rp > 50 ? -1 : (P[pl].s + rp) % 52; }
  function draw() {
    var stack = {};
    tokens.forEach(function (ts, pl) { ts.forEach(function (_, k) {
      var e = tokEls[pl][k], xy = pos(pl, k), key = xy.join(','), n = stack[key] = (stack[key] || 0) + 1;
      e.style.top = ((xy[0] / 15) * 100) + '%'; e.style.left = ((xy[1] / 15) * 100 + (n - 1) * 1.2) + '%';
      e.classList.toggle('done', tokens[pl][k] >= FINISH);
    }); });
    wins.set(G.get('dt-ludo-wins', 0));
  }
  function canMove(pl, k, d) { var rp = tokens[pl][k]; if (rp >= FINISH) return false; if (rp < 0) return d === 6; return rp + d <= FINISH; }
  function movable(pl, d) { var out = []; for (var k = 0; k < count; k++) if (canMove(pl, k, d)) out.push(k); return out; }
  function setStatus() {
    tokEls.forEach(function (ts) { ts.forEach(function (e) { e.classList.remove('can'); }); });
    if (phase === 'over') return;
    var who = turn === 0 ? t('your_turn') : t('computer_turn');
    status.innerHTML = '<span class="ldot" style="background:' + P[turn].c + '"></span>' + who;
    dieBtn.disabled = !(turn === 0 && phase === 'roll');
    dieBtn.style.setProperty('--pc', P[turn].c);
    if (turn === 0 && phase === 'move') movable(0, dice).forEach(function (k) { tokEls[0][k].classList.add('can'); });
  }
  function roll() {
    phase = 'rolling'; dieBtn.disabled = true; var n = 0;
    var faces = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];
    var iv = setInterval(function () {
      dieBtn.textContent = faces[Math.floor(Math.random() * 6)]; G.beep(500 + Math.random() * 300, .03);
      if (++n > 7) {
        clearInterval(iv); dice = Math.floor(Math.random() * 6) + 1; dieBtn.textContent = faces[dice - 1];
        sixes = dice === 6 ? sixes + 1 : 0;
        var ms = movable(turn, dice);
        if (sixes === 3) { G.toast('3 × 6 😬'); sixes = 0; return setTimeout(next, 700); }
        if (!ms.length) { phase = 'wait'; setStatus(); return setTimeout(function () { next(); }, 800); }
        phase = 'move'; setStatus();
        if (turn !== 0) setTimeout(function () { move(turn, choose(turn, ms)); }, 550);
        else if (ms.length === 1 && tokens[0][ms[0]] >= 0) setTimeout(function () { if (phase === 'move') move(0, ms[0]); }, 450);
      }
    }, 70);
  }
  function choose(pl, ms) {
    var bestK = ms[0], bestV = -1e9;
    ms.forEach(function (k) {
      var rp = tokens[pl][k], to = rp < 0 ? 0 : rp + dice, v = 0;
      if (to >= FINISH) v += 1000;
      if (rp < 0) v += 500;
      if (to <= 50) {
        var cell = (P[pl].s + to) % 52;
        tokens.forEach(function (ts, o) { if (o === pl) return; ts.forEach(function (_, j) { if (cellOf(o, j) === cell && SAFE.indexOf(cell) < 0) v += 800; }); });
        if (SAFE.indexOf(cell) > -1) v += 120;
        // danger: opponents 1..6 behind the destination
        tokens.forEach(function (ts, o) { if (o === pl) return; ts.forEach(function (_, j) { var oc = cellOf(o, j); if (oc < 0) return; var gap = (cell - oc + 52) % 52; if (gap >= 1 && gap <= 6 && SAFE.indexOf(cell) < 0) v -= 150; }); });
      } else v += 200;
      v += to * 2 + Math.random() * 10;
      if (v > bestV) { bestV = v; bestK = k; }
    });
    return bestK;
  }
  function move(pl, k) {
    if (phase !== 'move' || !canMove(pl, k, dice)) return;
    phase = 'anim'; var steps = tokens[pl][k] < 0 ? 1 : dice, from = tokens[pl][k], bonus = false;
    (function step(i) {
      tokens[pl][k] = from < 0 ? 0 : from + i; draw(); G.beep(620 + i * 30, .04);
      if ((from < 0 ? 1 : i) < steps) return setTimeout(function () { step(i + 1); }, 150);
      var cell = cellOf(pl, k);
      if (cell > -1 && SAFE.indexOf(cell) < 0) {
        tokens.forEach(function (ts, o) { if (o === pl) return; ts.forEach(function (_, j) { if (cellOf(o, j) === cell) { ts[j] = -1; bonus = true; G.toast(pl === 0 ? '💥 ' + t('captured') : '😱'); if (pl === 0) G.addXP(5); else G.bad(); } }); });
      }
      if (tokens[pl][k] >= FINISH) { bonus = true; G.good(); if (pl === 0) G.addXP(5); }
      draw();
      if (tokens[pl].slice(0, count).every(function (x) { return x >= FINISH; })) return win(pl);
      setTimeout(function () { (dice === 6 || bonus) ? again() : next(); }, 350);
    })(1);
  }
  function again() { phase = 'roll'; setStatus(); if (turn !== 0) setTimeout(roll, 600); }
  function next() { sixes = 0; turn = (turn + 1) % 4; again(); }
  function win(pl) {
    phase = 'over'; dieBtn.disabled = true;
    if (pl === 0) { G.set('dt-ludo-wins', G.get('dt-ludo-wins', 0) + 1); G.fanfare(); G.confetti(); G.addXP(count === 4 ? 120 : 60); }
    else G.bad();
    draw();
    G.winBox(pl === 0 ? t('you_won') : t('you_lost'), [pl === 0 ? '🏆' : '🎲 ' + t('try_again')], start);
  }
  dieBtn.onclick = function () { if (turn === 0 && phase === 'roll') roll(); };
  function start() {
    tokEls.forEach(function (ts) { ts.forEach(function (e) { e.remove(); }); });
    tokens = P.map(function () { return [-1, -1, -1, -1].slice(0, count); });
    tokEls = P.map(function (p, pl) {
      return tokens[pl].map(function (_, k) {
        var e = el('button', 'tok'); e.style.setProperty('--pc', p.c);
        e.onclick = function () { if (pl === 0 && turn === 0) move(0, k); };
        board.appendChild(e); return e;
      });
    });
    turn = 0; phase = 'roll'; sixes = 0; dieBtn.textContent = '🎲'; draw(); setStatus();
  }
  nb.onclick = start; start();
})();
