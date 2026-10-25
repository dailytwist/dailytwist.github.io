/* DailyTwist Snake: eat the fruit, grow longer, don't hit yourself. Swipe, arrow keys or on-screen pad. Original code. */
(function () {
  var root = document.getElementById('game');
  if (!root || root.dataset.game !== 'snake') return;
  var G = window.DTG, t = G.t, el = G.el, get = G.get, set = G.set;
  var N = 17, BEST = 'dt-snake-best';
  var SPEED = { easy: 170, medium: 120, hard: 85 }, MULT = { easy: 1, medium: 2, hard: 3 };
  var FRUIT = ['🍎', '🍓', '🍒', '🍊', '🍇', '🍉', '🍋', '🥝'];
  var diff = get('dt-snake-diff', 'medium');

  var sc = G.stat(t('score')), bs = G.stat(t('best')), nb = el('button', 'btn small', t('new_game'));
  root.append(G.pills(G.DIFF, diff, function (d) { diff = d; set('dt-snake-diff', d); start(); }), G.bar([sc, bs, nb]));
  var wrap = el('div', 'sn-wrap'), cv = el('canvas', 'sn-board'), msg = el('p', 'msg sn-msg');
  wrap.appendChild(cv);
  var pad = el('div', 'sn-pad');
  [['↑', 0, -1], ['←', -1, 0], ['↓', 0, 1], ['→', 1, 0]].forEach(function (d) {
    var b = el('button', 'sn-key', d[0]); b.type = 'button'; b.setAttribute('aria-label', d[0]);
    b.addEventListener('pointerdown', function (ev) { ev.preventDefault(); turn(d[1], d[2]); });
    pad.appendChild(b);
  });
  root.append(wrap, msg, pad);
  var css = document.createElement('style');
  css.textContent = '.sn-wrap{position:relative;max-width:420px;margin:12px auto 0;aspect-ratio:1;border-radius:18px;overflow:hidden;box-shadow:0 8px 24px #0002;touch-action:none}' +
    '.sn-board{display:block;width:100%;height:100%}.sn-msg{text-align:center;min-height:1.6em}' +
    '.sn-pad{display:grid;grid-template-columns:repeat(3,64px);grid-template-rows:repeat(2,56px);gap:8px;justify-content:center;margin:8px auto 4px}' +
    '.sn-key{font-size:24px;border:0;border-radius:14px;background:var(--card,#fff);color:inherit;box-shadow:0 3px 10px #0002;cursor:pointer;touch-action:manipulation}' +
    '.sn-key:nth-child(1){grid-column:2}.sn-key:nth-child(2){grid-column:1;grid-row:2}.sn-key:nth-child(3){grid-column:2;grid-row:2}.sn-key:nth-child(4){grid-column:3;grid-row:2}' +
    '@media (hover:hover) and (pointer:fine){.sn-pad{display:none}}';
  document.head.appendChild(css);

  var ctx = cv.getContext('2d'), px, snake, dir, queue, food, fruit, score, timer, running, over, eaten;
  function size() {
    var w = wrap.clientWidth || 360, r = window.devicePixelRatio || 1;
    cv.width = w * r; cv.height = w * r; px = cv.width / N; draw();
  }
  function freeCell() {
    var c;
    do { c = [Math.floor(Math.random() * N), Math.floor(Math.random() * N)]; }
    while (snake.some(function (s) { return s[0] === c[0] && s[1] === c[1]; }));
    return c;
  }
  function start() {
    clearInterval(timer);
    var m = Math.floor(N / 2);
    snake = [[m, m], [m - 1, m], [m - 2, m]]; dir = [1, 0]; queue = []; score = 0; eaten = 0; over = false; running = false;
    food = freeCell(); fruit = FRUIT[Math.floor(Math.random() * FRUIT.length)];
    sc.set(0); bs.set(get(BEST, 0)); msg.textContent = '👆 ' + t('start');
    var old = root.querySelector('.winbox'); if (old) old.remove();
    size();
  }
  function go() {
    if (running || over) return;
    running = true; msg.textContent = '';
    timer = setInterval(step, Math.max(55, SPEED[diff] - Math.floor(eaten / 5) * 6));
  }
  function turn(x, y) {
    if (over) return;
    var last = queue.length ? queue[queue.length - 1] : dir;
    if (last[0] === -x && last[1] === -y) return; // no instant reverse
    if (last[0] === x && last[1] === y) { go(); return; }
    if (queue.length < 3) queue.push([x, y]);
    go();
  }
  function step() {
    if (queue.length) dir = queue.shift();
    var h = snake[0], n = [h[0] + dir[0], h[1] + dir[1]];
    var grow = n[0] === food[0] && n[1] === food[1];
    var body = grow ? snake : snake.slice(0, -1);
    if (n[0] < 0 || n[1] < 0 || n[0] >= N || n[1] >= N || body.some(function (s) { return s[0] === n[0] && s[1] === n[1]; })) return end();
    snake.unshift(n);
    if (grow) {
      eaten++; score += 10 * MULT[diff]; sc.set(score); G.good();
      if (eaten % 5 === 0) { clearInterval(timer); timer = setInterval(step, Math.max(55, SPEED[diff] - Math.floor(eaten / 5) * 6)); }
      if (snake.length >= N * N) return end(true);
      food = freeCell(); fruit = FRUIT[Math.floor(Math.random() * FRUIT.length)];
    } else snake.pop();
    draw();
  }
  function end(full) {
    clearInterval(timer); running = false; over = true; G.bad(); draw();
    var best = get(BEST, 0), rec = score > best;
    if (rec) { set(BEST, score); bs.set(score); G.fanfare(); G.confetti(); }
    G.addXP(Math.round(score / 10));
    G.winBox(full ? '🏆 ' + t('you_won') : rec ? '🏆 ' + t('new_record') : t('game_over'),
      [t('score') + ': ' + score, t('best') + ': ' + Math.max(score, best)], start);
  }
  function rr(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function draw() {
    if (!px) return;
    for (var y = 0; y < N; y++) for (var x = 0; x < N; x++) { ctx.fillStyle = (x + y) % 2 ? '#a8d86e' : '#b5e27a'; ctx.fillRect(x * px, y * px, px + 1, px + 1); }
    ctx.font = Math.floor(px * .85) + 'px serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(fruit, food[0] * px + px / 2, food[1] * px + px / 2 + px * .05);
    for (var i = snake.length - 1; i >= 0; i--) {
      var s = snake[i], k = 1 - i / Math.max(snake.length, 8) * .45;
      ctx.fillStyle = 'rgb(' + Math.round(70 * k) + ',' + Math.round(110 + 60 * k) + ',' + Math.round(230 * k) + ')';
      rr(s[0] * px + 1.5, s[1] * px + 1.5, px - 3, px - 3, px * .35); ctx.fill();
    }
    var h = snake[0], cx = h[0] * px + px / 2, cy = h[1] * px + px / 2, ox = dir[1] * px * .18, oy = dir[0] * px * .18, fx = dir[0] * px * .15, fy = dir[1] * px * .15;
    [[1], [-1]].forEach(function (sgn) {
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(cx + fx + ox * sgn[0], cy + fy - oy * sgn[0], px * .14, 0, 7); ctx.fill();
      ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(cx + fx * 1.4 + ox * sgn[0], cy + fy * 1.4 - oy * sgn[0], px * .07, 0, 7); ctx.fill();
    });
  }

  document.addEventListener('keydown', function (e) {
    var k = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0], w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0] }[e.key];
    if (!k || !document.body.contains(root)) return;
    e.preventDefault(); turn(k[0], k[1]);
  });
  var sx, sy;
  wrap.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; go(); }, { passive: true });
  wrap.addEventListener('touchmove', function (e) { e.preventDefault(); }, { passive: false });
  wrap.addEventListener('touchend', function (e) {
    var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 20) return;
    if (Math.abs(dx) > Math.abs(dy)) turn(dx > 0 ? 1 : -1, 0); else turn(0, dy > 0 ? 1 : -1);
  });
  wrap.addEventListener('click', go);
  nb.onclick = start;
  window.addEventListener('resize', size);
  document.addEventListener('visibilitychange', function () { if (document.hidden && running) { clearInterval(timer); running = false; msg.textContent = '⏸ ' + t('start'); } });
  start();
})();
