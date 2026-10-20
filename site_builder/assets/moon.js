/* DailyTwist: today's moon phase, computed from a known new moon. Original code. */
(function () {
  var box = document.getElementById('moon'); if (!box) return;
  var D = JSON.parse(document.getElementById('moon-data').textContent);
  var SYN = 29.530588853, REF = Date.UTC(2000, 0, 6, 18, 14) / 864e5; // new moon, 6 Jan 2000 18:14 UTC
  var now = Date.now() / 864e5, age = ((now - REF) % SYN + SYN) % SYN;
  var frac = age / SYN, illum = Math.round((1 - Math.cos(2 * Math.PI * frac)) / 2 * 100);
  var idx = Math.floor(frac * 8 + 0.5) % 8;
  function fmt(daysFromNow) {
    var d = new Date(Date.now() + daysFromNow * 864e5);
    try { return d.toLocaleDateString(D.lang, { weekday: 'long', month: 'long', day: 'numeric' }); } catch (e) { return d.toDateString(); }
  }
  var toFull = (SYN / 2 - age + SYN) % SYN, toNew = SYN - age;
  // draw: lit part as an ellipse terminator
  var r = 90, k = Math.cos(2 * Math.PI * frac), waxing = frac < .5;
  var lit = 'M100,10 A90,90 0 0,' + (waxing ? 1 : 0) + ' 100,190 A' + Math.abs(k * r) + ',90 0 0,' + ((k > 0) === waxing ? 0 : 1) + ' 100,10';
  box.innerHTML = '<svg viewBox="0 0 200 200" width="220" height="220" aria-hidden="true"><defs><radialGradient id="mg" cx=".4" cy=".35"><stop offset="0" stop-color="#fffbe6"/><stop offset="1" stop-color="#e9dca8"/></radialGradient></defs>' +
    '<circle cx="100" cy="100" r="90" fill="#2a2547"/><path d="' + lit + '" fill="url(#mg)"/></svg>' +
    '<h2>' + D.p[idx] + '</h2><p class="lead">' + D.m[idx] + '</p>' +
    '<div class="facts"><div><span>💡</span><small>' + D.l.moon_illum + '</small><b>' + illum + '%</b></div>' +
    '<div><span>🌒</span><small>' + D.l.moon_age + '</small><b>' + age.toFixed(1) + ' ' + D.l.days + '</b></div>' +
    '<div><span>🌕</span><small>' + D.l.moon_next_full + '</small><b>' + fmt(toFull < .5 ? toFull + SYN : toFull) + '</b></div>' +
    '<div><span>🌑</span><small>' + D.l.moon_next_new + '</small><b>' + fmt(toNew) + '</b></div></div>';
})();
