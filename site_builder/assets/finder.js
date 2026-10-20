/* DailyTwist: find your zodiac sign from a birthday. Original code. */
(function () {
  var box = document.getElementById('finder'); if (!box) return;
  var D = JSON.parse(document.getElementById('finder-data').textContent);
  var inp = box.querySelector('input'), btn = box.querySelector('button'), out = box.querySelector('.finder-out');
  function md(m, d) { return m * 100 + d; }
  function signOf(m, d) {
    var v = md(m, d), keys = Object.keys(D.r);
    for (var i = 0; i < keys.length; i++) {
      var r = D.r[keys[i]], a = md(r[0][0], r[0][1]), b = md(r[1][0], r[1][1]);
      if (a <= b ? v >= a && v <= b : v >= a || v <= b) return keys[i];
    }
    return null;
  }
  function show(scroll) {
    var p = (inp.value || '').split('-'); if (p.length < 3) return;
    var s = signOf(+p[1], +p[2]); if (!s) return;
    try { localStorage.setItem('dt-sign', s); } catch (e) {}
    var name = D.n[s];
    out.innerHTML = '<a class="finder-res" href="' + D.pre + '/zodiac/' + s + '/"><img src="/assets/signs/' + s + '.webp" width="96" height="96" alt="">' +
      '<span><b>' + D.you.replace('{sign}', name) + '</b><small>' + D.read.replace('{sign}', name) + ' →</small></span></a>';
    document.querySelectorAll('.zcard').forEach(function (c) { c.classList.toggle('mine', c.dataset.sign === s); });
    if (scroll) out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  btn.onclick = function () { show(true); };
  try { var mine = localStorage.getItem('dt-sign'); if (mine) document.querySelectorAll('.zcard').forEach(function (c) { c.classList.toggle('mine', c.dataset.sign === mine); }); } catch (e) {}
})();
