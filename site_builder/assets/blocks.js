/* DailyTwist Block Puzzle: drag blocks onto an 8x8 board, fill rows or columns to clear them. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'blocks') return;
  var G = window.DTG, t = G.t, el = G.el, get = G.get, set = G.set;
  var N = 8, KEY = 'dt-blocks-state', BEST = 'dt-blocks-best';

  // shapes as [row, col] cells; weight = how often it appears
  var SHAPES = [
    [[[0, 0]], 2],
    [[[0, 0], [0, 1]], 3], [[[0, 0], [1, 0]], 3],
    [[[0, 0], [0, 1], [0, 2]], 3], [[[0, 0], [1, 0], [2, 0]], 3],
    [[[0, 0], [0, 1], [0, 2], [0, 3]], 2], [[[0, 0], [1, 0], [2, 0], [3, 0]], 2],
    [[[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]], 1], [[[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]], 1],
    [[[0, 0], [0, 1], [1, 0], [1, 1]], 3],
    [[[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]], 1],
    [[[0, 0], [1, 0], [1, 1]], 2], [[[0, 1], [1, 0], [1, 1]], 2], [[[0, 0], [0, 1], [1, 0]], 2], [[[0, 0], [0, 1], [1, 1]], 2],
    [[[0, 0], [1, 0], [2, 0], [2, 1]], 1], [[[0, 1], [1, 1], [2, 1], [2, 0]], 1], [[[0, 0], [0, 1], [0, 2], [1, 0]], 1], [[[0, 0], [0, 1], [0, 2], [1, 2]], 1],
    [[[0, 0], [0, 1], [0, 2], [1, 1]], 1], [[[1, 0], [1, 1], [1, 2], [0, 1]], 1],
    [[[0, 0], [0, 1], [1, 1], [1, 2]], 1], [[[0, 1], [0, 2], [1, 0], [1, 1]], 1],
    [[[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]], 1], [[[0, 2], [1, 2], [2, 0], [2, 1], [2, 2]], 1],
    [[[0, 0], [0, 1], [0, 2], [1, 0], [2, 0]], 1], [[[0, 0], [0, 1], [0, 2], [1, 2], [2, 2]], 1]
  ];
  var COLORS = ['#7c5cff', '#ff5e7e', '#ff8a3d', '#ffc53d', '#2fbf71', '#3fc1c9', '#4c8dff', '#d36bff'];
  var BAG = []; SHAPES.forEach(function (s, i) { for (var k = 0; k < s[1]; k++) BAG.push(i); });

  var S; // state: { g: [64] color index+1 or 0, tray: [{s, c} | null] x3, score, combo, best }
  var sc = G.stat(t('score')), bs = G.stat(t('best')), nb = el('button', 'btn small ghost', '↻ ' + t('new_game'));
  var top = G.bar([sc, bs, nb]);
  var board = el('div', 'bp-board'), tray = el('div', 'bp-tray'), msg = el('p', 'msg');
  var cells = [];
  for (var i = 0; i < N * N; i++) { var c = el('div', 'bp-cell'); cells.push(c); board.appendChild(c); }
  root.append(top, board, msg, tray);

  function shape(p) { return SHAPES[p.s][0]; }
  function fits(g, p, r, c) {
    return shape(p).every(function (q) { var rr = r + q[0], cc = c + q[1]; return rr >= 0 && cc >= 0 && rr < N && cc < N && !g[rr * N + cc]; });
  }
  function canPlaceAnywhere(g, p) { for (var r = 0; r < N; r++) for (var c = 0; c < N; c++) if (fits(g, p, r, c)) return true; return false; }
  function newPiece() { return { s: BAG[Math.floor(Math.random() * BAG.length)], c: Math.floor(Math.random() * COLORS.length) }; }
  function newTray() {
    for (var tries = 0; tries < 30; tries++) {
      var tr = [newPiece(), newPiece(), newPiece()];
      if (tr.some(function (p) { return canPlaceAnywhere(S.g, p); })) return tr;
    }
    return [newPiece(), newPiece(), newPiece()];
  }
  function save() { set(KEY, S); }
  function fresh() { S = { g: new Array(N * N).fill(0), tray: [], score: 0, combo: 0 }; S.tray = newTray(); save(); draw(); msg.textContent = ''; }

  function draw(ghost) {
    for (var i = 0; i < N * N; i++) {
      var v = S.g[i], c = cells[i];
      c.className = 'bp-cell' + (v ? ' on' : '');
      c.style.setProperty('--c', v ? COLORS[v - 1] : '');
    }
    if (ghost) ghost.cells.forEach(function (i) { cells[i].classList.add('ghost'); cells[i].style.setProperty('--c', COLORS[ghost.c]); });
    if (ghost && ghost.lines) ghost.lines.forEach(function (i) { cells[i].classList.add('hot'); });
    sc.set(S.score); bs.set(Math.max(S.score, get(BEST, 0)));
    drawTray();
  }
  function pieceEl(p, size) {
    var cs = shape(p), h = 0, w = 0; cs.forEach(function (q) { h = Math.max(h, q[0] + 1); w = Math.max(w, q[1] + 1); });
    var d = el('div', 'bp-piece'); d.style.gridTemplateColumns = 'repeat(' + w + ',' + size + 'px)'; d.style.gridTemplateRows = 'repeat(' + h + ',' + size + 'px)';
    cs.forEach(function (q) { var b = el('i'); b.style.gridRow = q[0] + 1; b.style.gridColumn = q[1] + 1; d.appendChild(b); });
    d.style.setProperty('--c', COLORS[p.c]); d.dims = [h, w];
    return d;
  }
  function drawTray() {
    tray.innerHTML = '';
    S.tray.forEach(function (p, k) {
      var slot = el('div', 'bp-slot');
      if (p) {
        var pe = pieceEl(p, 20); slot.appendChild(pe);
        if (!canPlaceAnywhere(S.g, p)) slot.classList.add('dead');
        if (sel === k) slot.classList.add('sel');
        slot.addEventListener('pointerdown', function (e) { startDrag(e, k); });
      }
      tray.appendChild(slot);
    });
  }

  // ---------------------------------------------------------------- dragging (mouse + touch through pointer events)
  var drag = null, sel = -1;
  function cellSize() { return board.getBoundingClientRect().width / N; }
  function anchorFor(x, y) { // top-left cell of the piece for the floating piece's top-left corner
    var r = board.getBoundingClientRect(), s = cellSize();
    return [Math.round((y - r.top) / s), Math.round((x - r.left) / s)];
  }
  function previewAt(k, r, c) {
    var p = S.tray[k];
    if (!fits(S.g, p, r, c)) { draw(); return null; }
    var g = S.g.slice(), idx = shape(p).map(function (q) { return (r + q[0]) * N + c + q[1]; });
    idx.forEach(function (i) { g[i] = p.c + 1; });
    draw({ cells: idx, c: p.c, lines: fullLines(g) });
    return [r, c];
  }
  function startDrag(e, k) {
    e.preventDefault();
    var p = S.tray[k], s = cellSize(), f = pieceEl(p, Math.max(18, s - 3));
    f.classList.add('bp-float'); document.body.appendChild(f);
    var lift = e.pointerType === 'touch' ? s * 1.7 : s * .6;
    var w = f.dims[1] * s, h = f.dims[0] * s;
    drag = { k: k, f: f, x0: e.clientX, y0: e.clientY, moved: false, ox: w / 2, oy: h + lift - h / 2, at: null, s: s };
    move(e);
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up); window.addEventListener('pointercancel', cancel);
  }
  function move(e) {
    if (!drag) return;
    if (Math.abs(e.clientX - drag.x0) + Math.abs(e.clientY - drag.y0) > 6) drag.moved = true;
    var x = e.clientX - drag.ox, y = e.clientY - drag.oy - drag.f.dims[0] * drag.s / 2;
    drag.f.style.transform = 'translate(' + x + 'px,' + y + 'px)';
    var a = anchorFor(x + drag.s / 2 - drag.s / 2, y);
    drag.at = drag.moved ? previewAt(drag.k, a[0], a[1]) : null;
  }
  function end() {
    window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); window.removeEventListener('pointercancel', cancel);
    if (drag) drag.f.remove();
  }
  function up() {
    var d = drag; end(); drag = null;
    if (!d) return;
    if (!d.moved) { sel = sel === d.k ? -1 : d.k; draw(); return; } // tap = select, then tap the board
    sel = -1;
    if (d.at) place(d.k, d.at[0], d.at[1]); else { draw(); G.bad(); }
  }
  function cancel() { end(); drag = null; draw(); }
  board.addEventListener('click', function (e) {
    if (sel < 0) return;
    var i = cells.indexOf(e.target); if (i < 0) return;
    var r = Math.floor(i / N), c = i % N, p = S.tray[sel];
    // try the tapped cell as the top-left, then shift so the tap lands inside the piece
    var tries = [[r, c]]; shape(p).forEach(function (q) { tries.push([r - q[0], c - q[1]]); });
    for (var j = 0; j < tries.length; j++) if (fits(S.g, p, tries[j][0], tries[j][1])) { var k = sel; sel = -1; place(k, tries[j][0], tries[j][1]); return; }
    G.bad();
  });

  // ---------------------------------------------------------------- rules
  function fullLines(g) {
    var out = [];
    for (var r = 0; r < N; r++) { var ok = true; for (var c = 0; c < N; c++) if (!g[r * N + c]) { ok = false; break; } if (ok) for (c = 0; c < N; c++) out.push(r * N + c); }
    for (c = 0; c < N; c++) { ok = true; for (r = 0; r < N; r++) if (!g[r * N + c]) { ok = false; break; } if (ok) for (r = 0; r < N; r++) out.push(r * N + c); }
    return out;
  }
  function countLines(g) {
    var n = 0;
    for (var r = 0; r < N; r++) { var ok = true; for (var c = 0; c < N; c++) if (!g[r * N + c]) ok = false; if (ok) n++; }
    for (c = 0; c < N; c++) { ok = true; for (r = 0; r < N; r++) if (!g[r * N + c]) ok = false; if (ok) n++; }
    return n;
  }
  var busy = false;
  function place(k, r, c) {
    if (busy) return;
    var p = S.tray[k];
    shape(p).forEach(function (q) { S.g[(r + q[0]) * N + c + q[1]] = p.c + 1; });
    S.tray[k] = null; S.score += shape(p).length;
    var lines = countLines(S.g), clear = fullLines(S.g);
    draw();
    shape(p).forEach(function (q) { var x = cells[(r + q[0]) * N + c + q[1]]; x.classList.add('pop'); });
    if (lines) {
      S.combo++;
      var pts = lines * 10 * lines * Math.min(S.combo, 8);
      S.score += pts; busy = true;
      clear.forEach(function (i) { cells[i].classList.add('clear'); });
      G.good(); if (lines >= 2 || S.combo >= 3) G.fanfare();
      var word = lines >= 3 ? t('amazing') : lines === 2 || S.combo >= 3 ? t('great') : t('nice');
      showFloat(word + (S.combo > 1 ? ' · ' + t('combo') + ' ×' + S.combo : '') + '  +' + pts);
      setTimeout(function () {
        clear.forEach(function (i) { S.g[i] = 0; });
        if (!S.g.some(Boolean)) { S.score += 300; showFloat('✨ ' + t('amazing') + ' +300'); G.confetti(); }
        busy = false; after();
      }, 380);
    } else { S.combo = 0; G.beep(440, .05, 'triangle', .04); after(); }
  }
  function after() {
    if (S.tray.every(function (x) { return !x; })) S.tray = newTray();
    save(); draw();
    var alive = S.tray.some(function (p) { return p && canPlaceAnywhere(S.g, p); });
    if (!alive) setTimeout(over, 450);
  }
  function over() {
    var best = get(BEST, 0), rec = S.score > best;
    if (rec) { set(BEST, S.score); G.confetti(); G.fanfare(); } else G.bad();
    G.addXP(Math.min(150, S.score / 20));
    var score = S.score; set(KEY, null);
    G.winBox(rec ? '🏆 ' + t('new_record') : t('no_moves'), [t('score') + ': ' + score, t('best') + ': ' + Math.max(score, best)], fresh);
  }
  function showFloat(txt) {
    var f = el('div', 'bp-pop', txt); board.appendChild(f); setTimeout(function () { f.remove(); }, 1100);
  }

  nb.onclick = function () { if (S.score < 50 || confirm(t('new_game') + '?')) fresh(); };
  var saved = get(KEY, null);
  if (saved && saved.g && saved.g.length === N * N && saved.tray) { S = saved; draw(); if (!S.tray.some(function (p) { return p && canPlaceAnywhere(S.g, p); })) over(); }
  else fresh();
})();
