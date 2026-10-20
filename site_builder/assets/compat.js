/* DailyTwist zodiac love compatibility. Original code. */
(function () {
  var box = document.getElementById('compat'); if (!box) return;
  var D = JSON.parse(document.getElementById('compat-data').textContent);
  var a = box.querySelector('[name=a]'), b = box.querySelector('[name=b]'), go = box.querySelector('.compat-go'), out = box.querySelector('.compat-out');
  var BASE = { 'fire_fire': 86, 'earth_earth': 87, 'air_air': 85, 'water_water': 89, 'fire_air': 93, 'earth_water': 94,
               'fire_earth': 58, 'fire_water': 52, 'earth_air': 55, 'air_water': 60 };
  var ORDER = ['fire', 'earth', 'air', 'water'];
  function key(e1, e2) { var x = [e1, e2].sort(function (p, q) { return ORDER.indexOf(p) - ORDER.indexOf(q); }); return x[0] + '_' + x[1]; }
  function jitter(s1, s2, salt) { // stable small variation per pair so every pair feels unique
    var str = [s1, s2].sort().join('-') + salt, h = 0;
    for (var i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
    return h % 13 - 6;
  }
  function clamp(v) { return Math.max(35, Math.min(99, v)); }
  try { var mine = localStorage.getItem('dt-sign'); if (mine && D.signs[mine]) a.value = mine; } catch (e) {}
  function guideLink(s1, s2) {
    var ks = Object.keys(D.signs), slug = [s1, s2].sort(function (p, q) { return ks.indexOf(p) - ks.indexOf(q); }).join('-');
    return (D.pairs || []).indexOf(slug) > -1 ? ' <a class="btn small ghost" href="' + D.pre + '/compatibility/' + slug + '/">📖 ' + D.l.open + '</a>' : '';
  }
  function bar(label, v) { return '<div class="cb"><span>' + label + '</span><div class="cb-track"><i style="width:' + v + '%"></i></div><b>' + v + '%</b></div>'; }
  function run(scroll) {
    var s1 = a.value, s2 = b.value, e1 = D.signs[s1][1], e2 = D.signs[s2][1], k = key(e1, e2), base = BASE[k];
    var love = clamp(base + jitter(s1, s2, 'l')), friend = clamp(base + 4 + jitter(s1, s2, 'f')), work = clamp(base - 2 + jitter(s1, s2, 'w'));
    var total = Math.round((love * 2 + friend + work) / 4);
    var heart = total >= 85 ? '💞' : total >= 70 ? '❤️' : total >= 55 ? '🧡' : '💛';
    out.innerHTML = '<div class="compat-card"><div class="cc-signs"><span>' + D.signs[s1][0] + '</span><em>' + heart + '</em><span>' + D.signs[s2][0] + '</span></div>' +
      '<p class="cc-names">' + D.signs[s1][2] + ' + ' + D.signs[s2][2] + '</p>' +
      '<div class="cc-ring" style="--p:' + total + '"><b>0%</b></div>' +
      bar(D.l.love, love) + bar(D.l.friend, friend) + bar(D.l.work, work) +
      '<h3>💡 ' + D.l.tip + '</h3><p>' + D.t[k] + '</p>' +
      '<button class="btn small compat-share">📤 ' + D.l.share + '</button>' + guideLink(s1, s2) + '</div>';
    var num = out.querySelector('.cc-ring b'), n = 0, timer = setInterval(function () { n = Math.min(total, n + 3); num.textContent = n + '%'; if (n >= total) clearInterval(timer); }, 18);
    out.querySelector('.compat-share').onclick = function () {
      var text = heart + ' ' + D.signs[s1][2] + ' + ' + D.signs[s2][2] + ' = ' + total + '% — ' + D.l.title, url = location.href.split('#')[0];
      if (navigator.share) navigator.share({ title: D.l.title, text: text, url: url }).catch(function () {});
      else window.open('https://wa.me/?text=' + encodeURIComponent(text + ' ' + url), '_blank', 'noopener');
    };
    try { localStorage.setItem('dt-sign', s1); } catch (e) {}
    if (scroll) out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  go.onclick = function () { run(true); };
})();
