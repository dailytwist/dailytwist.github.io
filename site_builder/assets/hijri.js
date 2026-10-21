/* DailyTwist Hijri calendar: today's Hijri date and a two-way converter (Umm al-Qura, built into the browser). Original code. */
(function () {
  var box = document.getElementById('hijri'); if (!box) return;
  var D = JSON.parse(document.getElementById('hijri-data').textContent);
  var loc = D.locale, CAL = loc + '-u-ca-islamic-umalqura-nu-latn';
  var ok = true;
  try { new Intl.DateTimeFormat(CAL, { month: 'long' }).format(new Date()); } catch (e) { ok = false; }
  if (!ok) { box.innerHTML = '<p>' + D.l.unsupported + '</p>'; return; }
  var fmtFull = new Intl.DateTimeFormat(CAL, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var fmtG = new Intl.DateTimeFormat(loc + '-u-nu-latn', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var num = new Intl.DateTimeFormat('en-u-ca-islamic-umalqura-nu-latn', { day: 'numeric', month: 'numeric', year: 'numeric' });
  function parts(d) { // {d, m, y} in the Hijri calendar
    var o = {}; num.formatToParts(d).forEach(function (p) { if (p.type === 'day') o.d = +p.value; if (p.type === 'month') o.m = +p.value; if (p.type === 'year') o.y = parseInt(p.value, 10); });
    return o;
  }
  function noon(y, m, d) { return new Date(y, m - 1, d, 12); }
  function toGreg(hy, hm, hd) { // walk from an estimate to the exact day
    var est = new Date((hy - 1) * 354.367 * 864e5 + Date.UTC(622, 6, 19) + ((hm - 1) * 29.53 + hd - 1) * 864e5);
    var d = noon(est.getUTCFullYear(), est.getUTCMonth() + 1, est.getUTCDate());
    for (var i = 0; i < 80; i++) {
      var p = parts(d), diff = (hy - p.y) * 354 + (hm - p.m) * 29.5 + (hd - p.d);
      if (p.y === hy && p.m === hm && p.d === hd) return d;
      d = new Date(d.getTime() + Math.max(-30, Math.min(30, Math.round(diff) || (diff > 0 ? 1 : -1))) * 864e5);
    }
    return null;
  }
  // month names from the browser, in the page language
  var months = [], today = new Date(), tp = parts(today);
  var mf = new Intl.DateTimeFormat(CAL, { month: 'long' });
  for (var m = 1; m <= 12; m++) { var g = toGreg(tp.y, m, 15); months.push(g ? mf.format(g) : String(m)); }

  box.querySelector('.hj-today b').textContent = fmtFull.format(today);
  box.querySelector('.hj-today small').textContent = fmtG.format(today);

  var gIn = box.querySelector('[name=g]'), gOut = box.querySelector('.hj-g2h-out');
  gIn.value = today.toISOString().slice(0, 10);
  function g2h() {
    var v = gIn.value.split('-'); if (v.length < 3) return;
    var d = noon(+v[0], +v[1], +v[2]); gOut.innerHTML = '🌙 <b>' + fmtFull.format(d) + '</b>';
  }
  gIn.oninput = g2h; g2h();

  var hd = box.querySelector('[name=hd]'), hm = box.querySelector('[name=hm]'), hy = box.querySelector('[name=hy]'), hOut = box.querySelector('.hj-h2g-out');
  for (var i = 1; i <= 30; i++) hd.add(new Option(i, i));
  months.forEach(function (n, i) { hm.add(new Option(n, i + 1)); });
  hd.value = tp.d; hm.value = tp.m; hy.value = tp.y;
  function h2g() {
    var d = toGreg(+hy.value, +hm.value, +hd.value);
    hOut.innerHTML = d ? '📅 <b>' + fmtG.format(d) + '</b>' : D.l.invalid;
  }
  [hd, hm, hy].forEach(function (x) { x.oninput = x.onchange = h2g; }); h2g();

  // fill Hijri dates next to each event
  box.parentNode.querySelectorAll('[data-iso]').forEach(function (el) {
    var v = el.dataset.iso.split('-'); el.textContent = fmtFull.format(noon(+v[0], +v[1], +v[2]));
  });
})();
