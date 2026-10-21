/* DailyTwist prayer times: astronomical calculation in the browser (no external service). Original code. */
(function () {
  var box = document.getElementById('prayer'); if (!box) return;
  var D = JSON.parse(document.getElementById('prayer-data').textContent);
  var rad = Math.PI / 180, deg = 180 / Math.PI;
  function sin(d) { return Math.sin(d * rad); } function cos(d) { return Math.cos(d * rad); } function tan(d) { return Math.tan(d * rad); }
  function asin(x) { return Math.asin(x) * deg; } function acos(x) { return Math.acos(x) * deg; } function atan2(y, x) { return Math.atan2(y, x) * deg; }
  function fix(a, b) { a = a - b * Math.floor(a / b); return a < 0 ? a + b : a; }
  function sun(jd) { // declination and equation of time
    var d = jd - 2451545.0, g = fix(357.529 + 0.98560028 * d, 360), q = fix(280.459 + 0.98564736 * d, 360);
    var L = fix(q + 1.915 * sin(g) + 0.020 * sin(2 * g), 360), e = 23.439 - 0.00000036 * d;
    var RA = atan2(cos(e) * sin(L), cos(L)) / 15;
    return { decl: asin(sin(e) * sin(L)), eqt: q / 15 - fix(RA, 24) };
  }
  function julian(y, m, d) { if (m <= 2) { y -= 1; m += 12; } var A = Math.floor(y / 100), B = 2 - A + Math.floor(A / 4); return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + B - 1524.5; }
  // times in UTC hours for a calendar date at lat/lng
  function times(y, m, d, lat, lng, M) {
    var jd = julian(y, m, d) - lng / 360;
    function noon(t) { var s = sun(jd + t / 24); return 12 - s.eqt - lng / 15; }
    function at(angle, t, ccw) {
      var s = sun(jd + t / 24), n = noon(t);
      var v = acos((-sin(angle) - sin(s.decl) * sin(lat)) / (cos(s.decl) * cos(lat))) / 15;
      return n + (ccw ? -v : v);
    }
    function asr(f, t) { var s = sun(jd + t / 24); return Math.atan(1 / (f + tan(Math.abs(lat - s.decl)))) * deg; }
    var dh = noon(12), sr = at(0.833, 6, true), ss = at(0.833, 18, false);
    var fa = at(M.f, 5, true);
    var as = (function () { var s = sun(jd + 13 / 24), a = asr(M.asr || 1, 13), n = noon(13); return n + acos((sin(a) - sin(s.decl) * sin(lat)) / (cos(s.decl) * cos(lat))) / 15; })();
    var mg = ss + (M.mg || 0) / 60;
    var is = typeof M.i === 'number' ? at(M.i, 18, false) : mg + parseFloat(M.i) / 60;
    var night = 24 - (ss - sr);
    if (isNaN(fa) || sr - fa > M.f / 60 * night) fa = sr - M.f / 60 * night; // high latitudes
    if (typeof M.i === 'number' && (isNaN(is) || is - ss > M.i / 60 * night)) is = ss + M.i / 60 * night;
    var adj = M.adj || {};
    return { fajr: fa + (adj.fajr || 0) / 60, sunrise: sr, dhuhr: dh + (1 + (adj.dhuhr || 0)) / 60, asr: as + (adj.asr || 0) / 60, maghrib: mg, isha: is + (adj.isha || 0) / 60 };
  }
  var NAMES = ['fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha'];
  function fmt(date, tz) { return new Intl.DateTimeFormat(D.locale + '-u-nu-latn', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: tz }).format(date); }
  function ymdIn(tz, date) { var p = {}; new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date).forEach(function (x) { p[x.type] = +x.value; }); return p; }
  function dates(y, m, d, c) { // Date objects for each prayer
    var t = times(y, m, d, c.lat, c.lng, D.methods[c.m]), base = Date.UTC(y, m - 1, d), o = {};
    NAMES.forEach(function (n) { o[n] = new Date(base + t[n] * 3600e3); });
    return o;
  }
  var C = D.city, timer;
  function render() {
    var now = new Date(), tz = C.tz, p = ymdIn(tz, now), today = dates(p.year, p.month, p.day, C);
    var next = NAMES.filter(function (n) { return n !== 'sunrise' && today[n] > now; })[0], nextAt = next ? today[next] : null;
    if (!next) { var tm = new Date(Date.UTC(p.year, p.month - 1, p.day + 1)); next = 'fajr'; nextAt = dates(tm.getUTCFullYear(), tm.getUTCMonth() + 1, tm.getUTCDate(), C).fajr; }
    box.querySelector('.pt-date').textContent = new Intl.DateTimeFormat(D.locale + '-u-nu-latn', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: tz }).format(now) +
      (function () { try { return ' · ' + new Intl.DateTimeFormat(D.locale + '-u-ca-islamic-umalqura-nu-latn', { day: 'numeric', month: 'long', year: 'numeric', timeZone: tz }).format(now); } catch (e) { return ''; } })();
    box.querySelector('.pt-grid').innerHTML = NAMES.map(function (n) {
      return '<div class="pt' + (n === next ? ' next' : '') + (n === 'sunrise' ? ' rise' : '') + '"><span>' + D.icons[n] + '</span><small>' + D.l[n] + '</small><b>' + fmt(today[n], tz) + '</b></div>';
    }).join('');
    function tick() {
      var s = Math.max(0, Math.round((nextAt - new Date()) / 1000));
      if (s === 0) { clearInterval(timer); render(); return; }
      var h = Math.floor(s / 3600), mi = Math.floor(s % 3600 / 60), se = s % 60;
      box.querySelector('.pt-next').innerHTML = D.l.next.replace('{name}', '<b>' + D.l[next] + '</b>') + ' <span class="pt-cd">' + h + ':' + ('0' + mi).slice(-2) + ':' + ('0' + se).slice(-2) + '</span>';
    }
    clearInterval(timer); tick(); timer = setInterval(tick, 1000);
    // month table
    var days = new Date(Date.UTC(p.year, p.month, 0)).getUTCDate(), rows = '';
    for (var d = 1; d <= days; d++) {
      var t = dates(p.year, p.month, d, C);
      rows += '<tr' + (d === p.day ? ' class="on"' : '') + '><td>' + d + '</td>' + NAMES.map(function (n) { return '<td>' + fmt(t[n], tz) + '</td>'; }).join('') + '</tr>';
    }
    var tbl = box.querySelector('.pt-month');
    if (tbl) tbl.innerHTML = '<thead><tr><th>#</th>' + NAMES.map(function (n) { return '<th>' + D.l[n] + '</th>'; }).join('') + '</tr></thead><tbody>' + rows + '</tbody>';
  }
  var loc = box.querySelector('.pt-locate');
  if (loc) loc.onclick = function () {
    if (!navigator.geolocation) return;
    loc.disabled = true;
    navigator.geolocation.getCurrentPosition(function (pos) {
      C = { lat: pos.coords.latitude, lng: pos.coords.longitude, tz: Intl.DateTimeFormat().resolvedOptions().timeZone, m: 'mwl' };
      box.querySelector('.pt-city').textContent = '📍 ' + D.l.here; loc.hidden = true; render();
    }, function () { loc.disabled = false; });
  };
  render();
})();
