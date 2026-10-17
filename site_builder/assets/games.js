(function () {
  var root = document.getElementById('game');
  var L = {};
  try { L = JSON.parse(document.getElementById('game-l').textContent); } catch (e) {}
  function t(k, v) { var s = L[k] || k; if (v) for (var x in v) s = s.replace('{' + x + '}', v[x]); return s; }
  function get(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function el(tag, cls, txt) { var x = document.createElement(tag); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; }
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var q = a[i]; a[i] = a[j]; a[j] = q; } return a; }
  function fmt(s) { return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }

  // ---------------------------------------------------------------- shared: sound, confetti, XP, streak
  var AC = null, sound = get('dt-sound', true);
  function beep(f, d, type, vol) {
    if (!sound) return;
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)();
      var o = AC.createOscillator(), g = AC.createGain();
      o.type = type || 'sine'; o.frequency.value = f; g.gain.value = vol || .06;
      o.connect(g); g.connect(AC.destination); o.start();
      g.gain.exponentialRampToValueAtTime(.0001, AC.currentTime + (d || .12)); o.stop(AC.currentTime + (d || .12));
    } catch (e) {}
  }
  function good() { beep(660, .08); setTimeout(function () { beep(880, .1); }, 70); }
  function bad() { beep(180, .18, 'square', .03); }
  function fanfare() { [523, 659, 784, 1047].forEach(function (f, i) { setTimeout(function () { beep(f, .16, 'triangle', .07); }, i * 110); }); }

  function confetti() {
    var c = el('canvas', 'confetti'); document.body.appendChild(c);
    var x = c.getContext('2d'), W = c.width = innerWidth, H = c.height = innerHeight, cols = ['#5b3df5', '#ff8a3d', '#3fc1c9', '#ff5e7e', '#ffd166', '#2fa36b'];
    var P = []; for (var i = 0; i < 140; i++) P.push({ x: W / 2, y: H / 3, vx: (Math.random() - .5) * 14, vy: Math.random() * -12 - 4, s: Math.random() * 7 + 4, c: cols[i % 6], r: Math.random() * 6 });
    var n = 0;
    (function f() {
      x.clearRect(0, 0, W, H);
      P.forEach(function (p) { p.vy += .35; p.x += p.vx; p.y += p.vy; p.r += .2; x.save(); x.translate(p.x, p.y); x.rotate(p.r); x.fillStyle = p.c; x.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); x.restore(); });
      if (++n < 110) requestAnimationFrame(f); else c.remove();
    })();
  }

  var profile = get('dt-profile', { xp: 0, streak: 0, last: '' });
  (function streak() {
    var today = new Date().toDateString(), y = new Date(Date.now() - 864e5).toDateString();
    if (profile.last !== today) { profile.streak = profile.last === y ? profile.streak + 1 : 1; profile.last = today; set('dt-profile', profile); }
  })();
  function level(xp) { return Math.floor(Math.sqrt(xp / 40)) + 1; }
  function toast(msg) {
    var b = el('div', 'toast', msg); document.body.appendChild(b);
    setTimeout(function () { b.classList.add('out'); }, 1600); setTimeout(function () { b.remove(); }, 2100);
  }
  function addXP(n) {
    n = Math.max(1, Math.round(n));
    var before = level(profile.xp); profile.xp += n; set('dt-profile', profile);
    toast('+' + n + ' XP');
    if (level(profile.xp) > before) setTimeout(function () { toast('⭐ ' + t('level_up', { n: level(profile.xp) })); fanfare(); }, 900);
    renderProfile();
  }
  function renderProfile() {
    document.querySelectorAll('[data-profile]').forEach(function (box) {
      var lv = level(profile.xp), lo = (lv - 1) * (lv - 1) * 40, hi = lv * lv * 40;
      box.innerHTML = '<div class="pf-item"><b>⭐ ' + t('level') + ' ' + lv + '</b><div class="xpbar"><span style="width:' + Math.round(100 * (profile.xp - lo) / (hi - lo)) + '%"></span></div><small>' + profile.xp + ' / ' + hi + ' XP</small></div>' +
        '<div class="pf-item"><b>🔥 ' + profile.streak + '</b><small>' + t('day_streak') + '</small></div>';
    });
    document.querySelectorAll('[data-best]').forEach(function (b) { var v = get(b.dataset.best, null); b.textContent = v === null ? '' : t('best') + ': ' + v; });
  }
  renderProfile();
  if (!root) return;

  function bar(items) {
    var b = el('div', 'gbar');
    items.forEach(function (i) { b.appendChild(i); });
    var s = el('button', 'icon-btn', sound ? '🔊' : '🔇'); s.title = 'Sound';
    s.onclick = function () { sound = !sound; set('dt-sound', sound); s.textContent = sound ? '🔊' : '🔇'; };
    b.appendChild(s); return b;
  }
  function pills(opts, cur, onPick) {
    var w = el('div', 'pills');
    opts.forEach(function (o) {
      var b = el('button', 'pill' + (o[0] === cur ? ' on' : ''), o[1]);
      b.onclick = function () { w.querySelectorAll('.pill').forEach(function (p) { p.classList.remove('on'); }); b.classList.add('on'); onPick(o[0]); };
      w.appendChild(b);
    });
    return w;
  }
  function stat(label) { var s = el('span', 'stat'); s.set = function (v) { s.innerHTML = '<small>' + label + '</small>' + v; }; s.set('–'); return s; }
  function winBox(title, lines, again) {
    var o = el('div', 'winbox');
    o.innerHTML = '<div class="wb-card"><div class="wb-emoji">🏆</div><h2>' + title + '</h2>' + lines.map(function (l) { return '<p>' + l + '</p>'; }).join('') + '</div>';
    var b = el('button', 'btn', t('play_again')); b.onclick = function () { o.remove(); again(); };
    o.firstChild.appendChild(b); root.appendChild(o);
  }
  var DIFF = [['easy', t('easy')], ['medium', t('medium')], ['hard', t('hard')]];

  // ---------------------------------------------------------------- memory match
  function memory() {
    var SETS = { easy: 6, medium: 8, hard: 12 }, COLS = { easy: 4, medium: 4, hard: 6 };
    var EMOJI = ['🦊', '🐼', '🦄', '🐙', '🌈', '🍉', '🚀', '🎈', '🐢', '🌻', '🍩', '⚽', '🦋', '🍓', '🎸', '🐳', '🌵', '🍕'];
    var diff = get('dt-mem-diff', 'medium');
    var mv = stat(t('moves')), tm = stat(t('time')), best = stat(t('best')), nb = el('button', 'btn small', t('new_game'));
    root.append(pills(DIFF, diff, function (d) { diff = d; set('dt-mem-diff', d); start(); }), bar([mv, tm, best, nb]));
    var grid = el('div', 'mgrid'); root.appendChild(grid);
    var open, moves, found, lock, secs, timer, pairs, combo;
    function start() {
      clearInterval(timer); grid.innerHTML = ''; open = []; moves = 0; found = 0; lock = false; secs = 0; combo = 0; pairs = SETS[diff];
      grid.style.gridTemplateColumns = 'repeat(' + COLS[diff] + ',1fr)';
      var b = get('dt-mem-best-' + diff, null); best.set(b ? b + ' ' + t('moves').toLowerCase() : '–'); mv.set(0); tm.set('0:00');
      var e = shuffle(EMOJI.slice()).slice(0, pairs);
      shuffle(e.concat(e)).forEach(function (em, i) {
        var c = el('button', 'mcard'); c.dataset.e = em; c.style.animationDelay = (i * 25) + 'ms';
        c.innerHTML = '<span class="front">' + em + '</span><span class="back"></span>';
        c.onclick = function () { flip(c); };
        grid.appendChild(c);
      });
    }
    function flip(c) {
      if (lock || c.classList.contains('open')) return;
      if (!timer || secs === 0 && moves === 0) { clearInterval(timer); timer = setInterval(function () { tm.set(fmt(++secs)); }, 1000); }
      c.classList.add('open'); beep(520, .05); open.push(c);
      if (open.length < 2) return;
      moves++; mv.set(moves);
      if (open[0].dataset.e === open[1].dataset.e) {
        open.forEach(function (x) { x.classList.add('done'); }); open = []; found++; combo++; good();
        if (combo > 1) toast('🔥 ' + t('combo') + ' x' + combo);
        if (found === pairs) win();
      } else {
        combo = 0; lock = true;
        setTimeout(function () { open.forEach(function (x) { x.classList.add('shake'); }); bad(); }, 250);
        setTimeout(function () { open.forEach(function (x) { x.classList.remove('open', 'shake'); }); open = []; lock = false; }, 850);
      }
    }
    function win() {
      clearInterval(timer); fanfare(); confetti();
      var stars = moves <= pairs * 1.4 ? 3 : moves <= pairs * 2 ? 2 : 1;
      var k = 'dt-mem-best-' + diff, b = get(k, null); if (!b || moves < b) set(k, moves);
      addXP(pairs * 3 * stars);
      winBox(t('you_won'), ['⭐'.repeat(stars) + '☆'.repeat(3 - stars), t('moves') + ': ' + moves + ' · ' + t('time') + ': ' + fmt(secs)], start);
    }
    nb.onclick = start; start();
  }

  // ---------------------------------------------------------------- 2048
  function g2048() {
    var sc = stat(t('score')), bs = stat(t('best')), undo = el('button', 'btn small ghost', '↶ ' + t('undo')), nb = el('button', 'btn small', t('new_game'));
    root.appendChild(bar([sc, bs, undo, nb]));
    var wrap = el('div', 'b2048wrap'), board = el('div', 'board2048'); wrap.appendChild(board); root.appendChild(wrap);
    var g, score, over, prev, won, fresh, merged;
    function draw() {
      board.innerHTML = '';
      for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) {
        var v = g[i][j], c = el('div', 't t' + Math.min(v, 8192) + (fresh === i * 4 + j ? ' new' : '') + (merged[i * 4 + j] ? ' pop' : ''), v || '');
        board.appendChild(c);
      }
      var best = Math.max(get('dt-2048-best', 0), score); set('dt-2048-best', best);
      sc.set(score); bs.set(best); undo.disabled = !prev;
    }
    function add() {
      var e = []; for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) if (!g[i][j]) e.push(i * 4 + j);
      if (!e.length) return; var p = e[Math.floor(Math.random() * e.length)]; g[Math.floor(p / 4)][p % 4] = Math.random() < .9 ? 2 : 4; fresh = p;
    }
    function move(dir) {
      if (over) return;
      var snapshot = JSON.stringify([g, score]), moved = false, gain = 0; merged = {};
      for (var a = 0; a < 4; a++) {
        var line = [];
        for (var b = 0; b < 4; b++) { var p = cell(dir, a, b); line.push(g[p[0]][p[1]]); }
        var vals = line.filter(Boolean), out = [], mpos = [];
        for (var k = 0; k < vals.length; k++) {
          if (vals[k] === vals[k + 1]) { out.push(vals[k] * 2); gain += vals[k] * 2; mpos.push(out.length - 1); k++; } else out.push(vals[k]);
        }
        while (out.length < 4) out.push(0);
        for (b = 0; b < 4; b++) { p = cell(dir, a, b); if (g[p[0]][p[1]] !== out[b]) moved = true; g[p[0]][p[1]] = out[b]; if (mpos.indexOf(b) > -1) merged[p[0] * 4 + p[1]] = 1; }
      }
      if (!moved) return;
      prev = snapshot; score += gain; add(); draw();
      if (gain) beep(300 + Math.min(gain, 2048) / 4, .07, 'triangle');
      if (!won && g.some(function (r) { return r.indexOf(2048) > -1; })) { won = true; fanfare(); confetti(); addXP(150); toast('🏆 2048!'); }
      if (!canMove()) { over = true; addXP(score / 80); winBox(t('game_over'), [t('score') + ': ' + score], start); }
    }
    function cell(dir, a, b) { return [[a, b], [b, a], [a, 3 - b], [3 - b, a]][dir]; } // 0 left,1 up,2 right,3 down
    function canMove() {
      for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) { if (!g[i][j] || (j < 3 && g[i][j] === g[i][j + 1]) || (i < 3 && g[i][j] === g[i + 1][j])) return true; }
      return false;
    }
    function start() { g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]; score = 0; over = false; won = false; prev = null; merged = {}; add(); add(); draw(); }
    undo.onclick = function () { if (!prev) return; var s = JSON.parse(prev); g = s[0]; score = s[1]; prev = null; over = false; merged = {}; fresh = -1; draw(); };
    document.addEventListener('keydown', function (e) { var k = { ArrowLeft: 0, ArrowUp: 1, ArrowRight: 2, ArrowDown: 3 }[e.key]; if (k !== undefined) { e.preventDefault(); move(k); } });
    var sx, sy;
    board.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    board.addEventListener('touchmove', function (e) { e.preventDefault(); }, { passive: false });
    board.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.max(Math.abs(dx), Math.abs(dy)) > 24) move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 2 : 0) : (dy > 0 ? 3 : 1));
    });
    nb.onclick = start; start();
  }

  // ---------------------------------------------------------------- tic-tac-toe
  function ttt() {
    var diff = get('dt-ttt-diff', 'medium'), score = get('dt-ttt-score', { w: 0, l: 0, d: 0 });
    var st = el('span', 'stat big'), sw = stat(t('wins')), sl = stat(t('losses')), sd = stat(t('draws')), nb = el('button', 'btn small', t('new_game'));
    root.append(pills(DIFF, diff, function (d) { diff = d; set('dt-ttt-diff', d); start(); }), bar([sw, sl, sd, nb]), st);
    var grid = el('div', 'tgrid'), cells = []; root.appendChild(grid);
    var b, done, LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
    function win(s) { for (var i = 0; i < 8; i++) { var l = LINES[i]; if (s[l[0]] && s[l[0]] === s[l[1]] && s[l[1]] === s[l[2]]) return { p: s[l[0]], l: l }; } return s.indexOf('') < 0 ? { p: 'D' } : null; }
    function minimax(s, me) {
      var w = win(s); if (w) return { v: w.p === 'O' ? 10 : w.p === 'X' ? -10 : 0 };
      var best = { v: me ? -99 : 99 };
      s.forEach(function (c, i) {
        if (c) return; s[i] = me ? 'O' : 'X'; var r = minimax(s, !me).v; s[i] = '';
        if (me ? r > best.v : r < best.v) best = { v: r, i: i };
      });
      return best;
    }
    function ai() {
      var free = []; b.forEach(function (c, i) { if (!c) free.push(i); });
      var rnd = diff === 'easy' ? .65 : diff === 'medium' ? .25 : 0;
      var m = Math.random() < rnd ? free[Math.floor(Math.random() * free.length)] : minimax(b.slice(), true).i;
      b[m] = 'O'; beep(330, .06);
    }
    function draw() {
      var w = win(b);
      cells.forEach(function (c, i) { c.textContent = b[i]; c.className = 'tc ' + (b[i] === 'X' ? 'x' : b[i] === 'O' ? 'o' : '') + (w && w.l && w.l.indexOf(i) > -1 ? ' winline' : ''); });
      sw.set(score.w); sl.set(score.l); sd.set(score.d);
      if (w && !done) {
        done = true;
        if (w.p === 'X') { score.w++; st.textContent = '🎉 ' + t('you_won'); fanfare(); confetti(); addXP({ easy: 5, medium: 12, hard: 30 }[diff]); }
        else if (w.p === 'O') { score.l++; st.textContent = '🤖 ' + t('you_lost'); bad(); }
        else { score.d++; st.textContent = '🤝 ' + t('draw'); if (diff === 'hard') addXP(8); }
        set('dt-ttt-score', score); sw.set(score.w); sl.set(score.l); sd.set(score.d);
        setTimeout(start, 1800);
      } else if (!w) st.textContent = t('your_turn');
    }
    for (var i = 0; i < 9; i++) (function (i) {
      var c = el('button', 'tc'); cells.push(c); grid.appendChild(c);
      c.onclick = function () { if (done || b[i]) return; b[i] = 'X'; beep(440, .06); draw(); if (!done) setTimeout(function () { ai(); draw(); }, 350); };
    })(i);
    function start() { b = ['', '', '', '', '', '', '', '', '']; done = false; draw(); }
    nb.onclick = function () { start(); }; start();
  }

  // ---------------------------------------------------------------- sudoku
  function sudoku() {
    var diff = get('dt-sdk-diff', 'easy'), HOLES = { easy: 36, medium: 46, hard: 53 };
    var tm = stat(t('time')), ms = stat(t('mistakes')), hn = el('button', 'btn small ghost', '💡 ' + t('hint')), nb = el('button', 'btn small', t('new_game'));
    root.append(pills(DIFF, diff, function (d) { diff = d; set('dt-sdk-diff', d); start(); }), bar([tm, ms, hn, nb]));
    var grid = el('div', 'sgrid'), pad = el('div', 'spad'); root.append(grid, pad);
    var sol, puz, cur, sel, mistakes, hints, secs, timer, cells = [];
    function ok(g, r, c, n) {
      for (var i = 0; i < 9; i++) { if (g[r * 9 + i] === n || g[i * 9 + c] === n) return false; }
      var br = r - r % 3, bc = c - c % 3; for (var y = 0; y < 3; y++) for (var x = 0; x < 3; x++) if (g[(br + y) * 9 + bc + x] === n) return false;
      return true;
    }
    function fill(g) {
      var i = g.indexOf(0); if (i < 0) return true;
      var ns = shuffle([1, 2, 3, 4, 5, 6, 7, 8, 9]);
      for (var k = 0; k < 9; k++) { if (ok(g, Math.floor(i / 9), i % 9, ns[k])) { g[i] = ns[k]; if (fill(g)) return true; g[i] = 0; } }
      return false;
    }
    function count(g, lim) {
      var i = g.indexOf(0); if (i < 0) return 1; var n = 0;
      for (var v = 1; v <= 9 && n < lim; v++) if (ok(g, Math.floor(i / 9), i % 9, v)) { g[i] = v; n += count(g, lim - n); g[i] = 0; }
      return n;
    }
    function make() {
      sol = new Array(81).fill(0); fill(sol); puz = sol.slice();
      var order = shuffle(Array.from({ length: 81 }, function (_, i) { return i; })), removed = 0;
      for (var k = 0; k < 81 && removed < HOLES[diff]; k++) {
        var i = order[k], keep = puz[i]; puz[i] = 0;
        if (count(puz.slice(), 2) !== 1) puz[i] = keep; else removed++;
      }
    }
    function render() {
      cells.forEach(function (c, i) {
        var v = cur[i], r = Math.floor(i / 9), col = i % 9, s = sel, sr = Math.floor(s / 9), sc = s % 9;
        c.textContent = v || '';
        c.className = 'sc' + (puz[i] ? ' given' : '') + (v && v !== sol[i] ? ' err' : '') + (i === s ? ' sel' : '') +
          (s >= 0 && i !== s && (r === sr || col === sc || (Math.floor(r / 3) === Math.floor(sr / 3) && Math.floor(col / 3) === Math.floor(sc / 3))) ? ' peer' : '') +
          (s >= 0 && v && v === cur[s] && i !== s ? ' same' : '') + (col % 3 === 2 && col < 8 ? ' br' : '') + (r % 3 === 2 && r < 8 ? ' bb' : '');
      });
      pad.querySelectorAll('button[data-n]').forEach(function (b) {
        var n = +b.dataset.n, used = cur.filter(function (v, i) { return v === n && v === sol[i]; }).length;
        b.classList.toggle('full', used >= 9); b.querySelector('small').textContent = 9 - used;
      });
      ms.set(mistakes + '/3'); hn.textContent = '💡 ' + t('hint') + ' (' + hints + ')'; hn.disabled = !hints;
    }
    function put(n) {
      if (sel < 0 || puz[sel] || cur[sel] === sol[sel]) return;
      cur[sel] = n;
      if (n && n !== sol[sel]) { mistakes++; bad(); if (mistakes >= 3) { clearInterval(timer); render(); winBox(t('game_over'), [t('too_many_mistakes')], start); return; } }
      else if (n) { good(); }
      render(); check();
    }
    function check() {
      for (var i = 0; i < 81; i++) if (cur[i] !== sol[i]) return;
      clearInterval(timer); fanfare(); confetti();
      var k = 'dt-sdk-best-' + diff, b = get(k, null); if (!b || secs < b) set(k, secs);
      addXP({ easy: 40, medium: 80, hard: 140 }[diff] - mistakes * 5);
      winBox(t('you_won'), [t('time') + ': ' + fmt(secs) + (b ? ' · ' + t('best') + ': ' + fmt(Math.min(b, secs)) : '')], start);
    }
    for (var i = 0; i < 81; i++) (function (i) { var c = el('button', 'sc'); c.onclick = function () { sel = i; beep(600, .03); render(); }; cells.push(c); grid.appendChild(c); })(i);
    for (var n = 1; n <= 9; n++) (function (n) { var b = el('button'); b.dataset.n = n; b.innerHTML = n + '<small></small>'; b.onclick = function () { put(n); }; pad.appendChild(b); })(n);
    var er = el('button', 'erase', '⌫'); er.onclick = function () { if (sel >= 0 && !puz[sel] && cur[sel] !== sol[sel]) { cur[sel] = 0; render(); } }; pad.appendChild(er);
    hn.onclick = function () {
      if (!hints) return; var empty = []; cur.forEach(function (v, i) { if (v !== sol[i]) empty.push(i); });
      var i = sel >= 0 && cur[sel] !== sol[sel] ? sel : empty[Math.floor(Math.random() * empty.length)];
      if (i === undefined) return; cur[i] = sol[i]; sel = i; hints--; good(); render(); check();
    };
    document.addEventListener('keydown', function (e) { if (/^[1-9]$/.test(e.key)) put(+e.key); if (e.key === 'Backspace') er.onclick(); });
    function start() {
      clearInterval(timer); make(); cur = puz.slice(); sel = -1; mistakes = 0; hints = 3; secs = 0; tm.set('0:00');
      timer = setInterval(function () { tm.set(fmt(++secs)); }, 1000); render();
    }
    nb.onclick = start; start();
  }

  // ---------------------------------------------------------------- math rush
  function math() {
    var sc = stat(t('score')), tm = stat(t('time')), bs = stat(t('best'));
    root.appendChild(bar([sc, tm, bs]));
    var area = el('div', 'mrush'); root.appendChild(area);
    var score, left, timer, streak, lvl;
    function intro() {
      clearInterval(timer); bs.set(get('dt-math-best', 0)); sc.set(0); tm.set('60');
      area.innerHTML = '<div class="mr-intro"><div class="wb-emoji">⚡</div><p>' + t('math_intro') + '</p></div>';
      var b = el('button', 'btn', '▶ ' + t('start')); b.onclick = go; area.firstChild.appendChild(b);
    }
    function go() {
      score = 0; left = 60; streak = 0; lvl = 1; sc.set(0);
      timer = setInterval(function () { tm.set(--left); if (left <= 0) end(); if (left <= 5 && left > 0) beep(900, .05); }, 1000);
      q();
    }
    function q() {
      var ops = lvl < 3 ? ['+', '-'] : lvl < 6 ? ['+', '-', '×'] : ['+', '-', '×', '÷'];
      var op = ops[Math.floor(Math.random() * ops.length)], m = 5 + lvl * 3, a, b, ans;
      function r(n) { return Math.floor(Math.random() * n) + 1; }
      if (op === '+') { a = r(m * 2); b = r(m * 2); ans = a + b; }
      else if (op === '-') { a = r(m * 2) + 5; b = r(a); ans = a - b; }
      else if (op === '×') { a = r(Math.min(12, 3 + lvl)); b = r(Math.min(12, 3 + lvl)); ans = a * b; }
      else { b = r(Math.min(12, 2 + lvl)); ans = r(Math.min(12, 2 + lvl)); a = b * ans; }
      var opts = [ans]; while (opts.length < 4) { var w = ans + (Math.floor(Math.random() * 9) - 4) * (op === '×' || op === '÷' ? Math.max(1, Math.round(ans / 10)) : 1); if (w >= 0 && opts.indexOf(w) < 0) opts.push(w); }
      area.innerHTML = '<div class="mr-q"><small>' + (streak >= 3 ? '🔥 x' + mult() : '&nbsp;') + '</small><div class="mr-eq">' + a + ' ' + op + ' ' + b + ' = ?</div></div>';
      var g = el('div', 'mr-opts');
      shuffle(opts).forEach(function (o) {
        var bt = el('button', 'mr-opt', o);
        bt.onclick = function () {
          if (o === ans) { streak++; score += 10 * mult(); lvl = 1 + Math.floor(score / 80); good(); bt.classList.add('right'); }
          else { streak = 0; left = Math.max(0, left - 3); bad(); bt.classList.add('wrong'); toast('-3s'); }
          sc.set(score); setTimeout(q, 180);
        };
        g.appendChild(bt);
      });
      area.appendChild(g);
    }
    function mult() { return streak >= 10 ? 3 : streak >= 3 ? 2 : 1; }
    function end() {
      clearInterval(timer); var b = get('dt-math-best', 0); if (score > b) { set('dt-math-best', score); confetti(); fanfare(); }
      addXP(score / 8);
      area.innerHTML = ''; winBox(score > b ? '🏆 ' + t('new_record') : t('times_up'), [t('score') + ': ' + score], intro);
    }
    intro();
  }

  // ---------------------------------------------------------------- color sequence (Simon)
  function simon() {
    var lv = stat(t('level')), bs = stat(t('best')), nb = el('button', 'btn small', '▶ ' + t('start'));
    root.appendChild(bar([lv, bs, nb]));
    var msg = el('p', 'msg'), board = el('div', 'simon'), pads = [];
    var COL = [['#ff5e7e', 330], ['#3fc1c9', 392], ['#ffd166', 494], ['#5b3df5', 587]];
    COL.forEach(function (c, i) { var p = el('button', 'pad'); p.style.setProperty('--c', c[0]); p.onclick = function () { press(i); }; pads.push(p); board.appendChild(p); });
    root.append(msg, board);
    var seq, pos, input;
    function light(i, d) { pads[i].classList.add('lit'); beep(COL[i][1], (d || 350) / 1000, 'sine', .09); setTimeout(function () { pads[i].classList.remove('lit'); }, d || 350); }
    function play() {
      input = false; msg.textContent = '👀 ' + t('watch'); var speed = Math.max(220, 520 - seq.length * 18);
      seq.forEach(function (s, k) { setTimeout(function () { light(s, speed * .8); }, 600 + k * speed); });
      setTimeout(function () { input = true; pos = 0; msg.textContent = '👆 ' + t('your_turn_repeat'); }, 600 + seq.length * speed);
    }
    function next() { seq.push(Math.floor(Math.random() * 4)); lv.set(seq.length); play(); }
    function press(i) {
      if (!input) return; light(i, 200);
      if (i !== seq[pos]) {
        input = false; bad(); var n = seq.length - 1, b = get('dt-simon-best', 0);
        if (n > b) { set('dt-simon-best', n); confetti(); } bs.set(Math.max(n, b)); addXP(n * 3);
        winBox(n > b ? '🏆 ' + t('new_record') : t('game_over'), [t('level') + ': ' + n], function () { msg.textContent = ''; });
        return;
      }
      if (++pos === seq.length) { input = false; msg.textContent = '✅'; setTimeout(next, 700); }
    }
    nb.onclick = function () { seq = []; next(); };
    bs.set(get('dt-simon-best', 0)); lv.set(0); msg.textContent = t('simon_intro');
  }

  ({ memory: memory, '2048': g2048, ttt: ttt, sudoku: sudoku, math: math, simon: simon })[root.dataset.game]();
})();
