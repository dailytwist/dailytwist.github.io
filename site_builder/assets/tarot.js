/* DailyTwist tarot card of the day. Original code. */
(function () {
  var box = document.getElementById('tarot'); if (!box) return;
  var D = JSON.parse(document.getElementById('tarot-data').textContent);
  var ICONS = ['🎒', '🪄', '🌙', '🌸', '👑', '📜', '💞', '🏇', '🦁', '🏮', '🎡', '⚖️', '🙃', '🦋', '🏺', '⛓️', '🗼', '⭐', '🌕', '☀️', '📯', '🌍'];
  var ROMAN = ['0', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX', 'XXI'];
  function get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  var today = new Date().toISOString().slice(0, 10), saved = get('dt-tarot');
  var deck = box.querySelector('.tarot-deck'), msg = box.querySelector('.tarot-msg'), out = box.querySelector('.tarot-out');
  function face(i) {
    return '<div class="tc-face"><small>' + ROMAN[i] + '</small><span>' + ICONS[i] + '</span><b>' + D.cards[i][0] + '</b></div>';
  }
  function reveal(i, el, animate) {
    deck.querySelectorAll('.tc').forEach(function (c) { if (c !== el) c.classList.add('gone'); });
    el.classList.add('chosen'); el.innerHTML = '<div class="tc-in"><div class="tc-back"></div>' + face(i) + '</div>';
    setTimeout(function () { el.classList.add('flip'); }, animate ? 60 : 0);
    msg.textContent = D.l.again;
    out.innerHTML = '<h2>' + ICONS[i] + ' ' + D.cards[i][0] + '</h2><p class="lead">' + D.cards[i][1] + '</p>' + (D.links && D.links[i] ? '<a class="btn small light" href="' + D.links[i] + '">📖 ' + D.l.more + '</a>' : '') + '<p class="muted small">' + D.l.back + ' · ' + D.l.note + '</p>';
    out.hidden = false;
  }
  if (saved && saved.d === today) {
    var only = deck.querySelector('.tc'); reveal(saved.i, only, false);
  } else {
    msg.textContent = D.l.tap;
    deck.querySelectorAll('.tc').forEach(function (c) {
      c.onclick = function () {
        if (deck.classList.contains('done')) return; deck.classList.add('done');
        var i = Math.floor(Math.random() * D.cards.length); set('dt-tarot', { d: today, i: i }); reveal(i, c, true);
      };
    });
  }
})();
