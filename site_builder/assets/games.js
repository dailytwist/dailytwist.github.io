(function () {
  var root = document.getElementById('game');
  if (!root) return;
  var L = root.dataset;
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  function el(tag, cls, txt) { var x = document.createElement(tag); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; }
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  // ---------------------------------------------------------------- memory match
  function memory() {
    var EMOJI = ['🦊', '🐼', '🦄', '🐙', '🌈', '🍉', '🚀', '🎈', '🐢', '🌻', '🍩', '⚽'];
    var bar = el('div', 'gbar'), movesEl = el('span'), bestEl = el('span'), btn = el('button', 'btn small', L.newGame);
    bar.append(movesEl, bestEl, btn);
    var grid = el('div', 'mgrid'), msg = el('p', 'msg');
    root.append(bar, grid, msg);
    var open = [], moves = 0, found = 0, lock = false;
    function upd() { movesEl.textContent = L.moves + ': ' + moves; var b = store('dt-mem-best'); bestEl.textContent = L.best + ': ' + (b || '–'); }
    function start() {
      grid.innerHTML = ''; msg.textContent = ''; open = []; moves = 0; found = 0; lock = false;
      var set = shuffle(EMOJI.slice()).slice(0, 8);
      shuffle(set.concat(set)).forEach(function (e) {
        var c = el('button', 'mcard'); c.dataset.e = e;
        c.innerHTML = '<span class="front">' + e + '</span><span class="back">✦</span>';
        c.addEventListener('click', function () {
          if (lock || c.classList.contains('open')) return;
          c.classList.add('open'); open.push(c);
          if (open.length === 2) {
            moves++; upd();
            if (open[0].dataset.e === open[1].dataset.e) {
              open.forEach(function (x) { x.classList.add('done'); }); open = []; found++;
              if (found === 8) {
                msg.textContent = L.won;
                var b = +store('dt-mem-best'); if (!b || moves < b) store('dt-mem-best', moves); upd();
              }
            } else {
              lock = true;
              setTimeout(function () { open.forEach(function (x) { x.classList.remove('open'); }); open = []; lock = false; }, 750);
            }
          }
        });
        grid.append(c);
      });
      upd();
    }
    btn.addEventListener('click', start); start();
  }

  // ---------------------------------------------------------------- 2048
  function g2048() {
    var bar = el('div', 'gbar'), scoreEl = el('span'), bestEl = el('span'), btn = el('button', 'btn small', L.newGame);
    bar.append(scoreEl, bestEl, btn);
    var board = el('div', 'board2048'), msg = el('p', 'msg');
    root.append(bar, board, msg);
    var g, score, over;
    function upd() {
      board.innerHTML = '';
      g.forEach(function (row) { row.forEach(function (v) { var t = el('div', 't t' + Math.min(v, 4096), v || ''); board.append(t); }); });
      var best = Math.max(+store('dt-2048-best') || 0, score); store('dt-2048-best', best);
      scoreEl.textContent = L.score + ': ' + score; bestEl.textContent = L.best + ': ' + best;
    }
    function add() {
      var empty = [];
      g.forEach(function (r, i) { r.forEach(function (v, j) { if (!v) empty.push([i, j]); }); });
      if (!empty.length) return;
      var p = empty[Math.floor(Math.random() * empty.length)]; g[p[0]][p[1]] = Math.random() < .9 ? 2 : 4;
    }
    function slide(row) {
      var a = row.filter(Boolean);
      for (var i = 0; i < a.length - 1; i++) if (a[i] === a[i + 1]) { a[i] *= 2; score += a[i]; if (a[i] === 2048) msg.textContent = L.won; a.splice(i + 1, 1); }
      while (a.length < 4) a.push(0);
      return a;
    }
    function rotate(m) { return m[0].map(function (_, i) { return m.map(function (r) { return r[i]; }).reverse(); }); }
    function move(dir) { // 0 left, 1 up, 2 right, 3 down
      if (over) return;
      var m = g, turns = [0, 3, 2, 1][dir];
      for (var i = 0; i < turns; i++) m = rotate(m);
      var before = JSON.stringify(m);
      m = m.map(slide);
      var changed = JSON.stringify(m) !== before;
      for (i = 0; i < (4 - turns) % 4; i++) m = rotate(m);
      if (changed) { g = m; add(); upd(); if (!canMove()) { over = true; msg.textContent = msg.textContent || '🙂 ' + L.newGame + '?'; } }
    }
    function canMove() {
      for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) {
        if (!g[i][j]) return true;
        if (j < 3 && g[i][j] === g[i][j + 1]) return true;
        if (i < 3 && g[i][j] === g[i + 1][j]) return true;
      }
      return false;
    }
    function start() { g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]; score = 0; over = false; msg.textContent = ''; add(); add(); upd(); }
    document.addEventListener('keydown', function (e) {
      var k = { ArrowLeft: 0, ArrowUp: 1, ArrowRight: 2, ArrowDown: 3 }[e.key];
      if (k !== undefined) { e.preventDefault(); move(k); }
    });
    var sx, sy;
    board.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    board.addEventListener('touchmove', function (e) { e.preventDefault(); }, { passive: false });
    board.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 25) return;
      move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 2 : 0) : (dy > 0 ? 3 : 1));
    });
    btn.addEventListener('click', start); start();
  }

  // ---------------------------------------------------------------- tic-tac-toe
  function ttt() {
    var bar = el('div', 'gbar'), status = el('span'), btn = el('button', 'btn small', L.newGame);
    bar.append(status, btn);
    var grid = el('div', 'tgrid'), cells = [];
    root.append(bar, grid);
    var b, done;
    var LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
    function winner(s) { for (var i = 0; i < 8; i++) { var l = LINES[i]; if (s[l[0]] && s[l[0]] === s[l[1]] && s[l[1]] === s[l[2]]) return s[l[0]]; } return s.indexOf('') < 0 ? 'D' : null; }
    function find(p) { for (var i = 0; i < 8; i++) { var l = LINES[i], v = l.map(function (x) { return b[x]; }); if (v.filter(function (x) { return x === p; }).length === 2 && v.indexOf('') > -1) return l[v.indexOf('')]; } return -1; }
    function ai() {
      var m = find('O'); if (m < 0) m = find('X');
      if (m < 0 && !b[4]) m = 4;
      if (m < 0 || Math.random() < .12) { var free = []; b.forEach(function (v, i) { if (!v) free.push(i); }); m = free[Math.floor(Math.random() * free.length)]; }
      b[m] = 'O';
    }
    function draw() {
      cells.forEach(function (c, i) { c.textContent = b[i]; c.className = 'tc ' + (b[i] === 'X' ? 'x' : b[i] === 'O' ? 'o' : ''); });
      var w = winner(b);
      if (w) { done = true; status.textContent = w === 'X' ? L.won : w === 'O' ? L.lost : L.draw; }
      else status.textContent = L.turn;
    }
    for (var i = 0; i < 9; i++) (function (i) {
      var c = el('button', 'tc'); cells.push(c); grid.append(c);
      c.addEventListener('click', function () {
        if (done || b[i]) return;
        b[i] = 'X'; draw(); if (done) return;
        setTimeout(function () { ai(); draw(); }, 300);
      });
    })(i);
    function start() { b = ['', '', '', '', '', '', '', '', '']; done = false; draw(); }
    btn.addEventListener('click', start); start();
  }

  ({ memory: memory, '2048': g2048, ttt: ttt })[L.game]();
})();
