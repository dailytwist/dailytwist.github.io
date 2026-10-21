/* DailyTwist "your day" panel: date, streak, your sign's horoscope, word of the day. Original code. */
(function () {
  var box = document.querySelector('.today'), dEl = document.getElementById('today-data'); if (!box || !dEl) return;
  var D = JSON.parse(dEl.textContent);
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  var now = new Date(), day = Math.floor((now - now.getTimezoneOffset() * 6e4) / 864e5);
  var greg = new Intl.DateTimeFormat(D.locale + '-u-nu-latn', { weekday: 'long', day: 'numeric', month: 'long' }).format(now), hij = '';
  try { hij = ' · ' + new Intl.DateTimeFormat(D.locale + '-u-ca-islamic-umalqura-nu-latn', { day: 'numeric', month: 'long', year: 'numeric' }).format(now); } catch (e) {}
  box.querySelector('.td-date').textContent = greg + hij;
  // streak of daily visits
  var last = +get('dt-last-day') || 0, streak = +get('dt-streak') || 0;
  if (last !== day) { streak = last === day - 1 ? streak + 1 : 1; set('dt-last-day', day); set('dt-streak', streak); }
  var st = box.querySelector('.td-streak');
  if (last) { st.textContent = streak > 1 ? D.l.streak.replace('{n}', streak) : D.l.streak1; st.hidden = false; }
  // your sign
  var card = box.querySelector('.td-sign'), pick = box.querySelector('.td-pick'), list = box.querySelector('.td-signs');
  function showSign(s) {
    var x = D.signs[s]; if (!x) return;
    card.href = D.pre + '/horoscope/' + s + '/';
    card.querySelector('.td-sign-name').textContent = x[0] + ' ' + x[1];
    card.querySelector('.td-sign-text').textContent = x[2];
    pick.hidden = true; card.hidden = false;
  }
  Object.keys(D.signs).forEach(function (s) {
    var b = document.createElement('button'); b.type = 'button'; b.className = 'mchip'; b.textContent = D.signs[s][0] + ' ' + D.signs[s][1];
    b.onclick = function () { set('dt-sign', s); showSign(s); };
    list.appendChild(b);
  });
  var mine = get('dt-sign');
  if (mine && D.signs[mine]) showSign(mine); else { card.hidden = true; pick.hidden = false; }
  // word of the day
  var w = box.querySelector('.td-word');
  if (w && D.words.length) { var x = D.words[(day * 37) % D.words.length]; w.querySelector('b').textContent = x[0]; w.querySelector('p').textContent = x[1]; }
})();
