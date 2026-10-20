/* DailyTwist: Life Path Number calculator. Original code. */
(function () {
  var box = document.getElementById('nfinder'); if (!box) return;
  var D = JSON.parse(document.getElementById('nfinder-data').textContent);
  var inp = box.querySelector('input'), out = box.querySelector('.finder-out');
  function sum(s) { return String(s).split('').reduce(function (a, c) { return a + (+c || 0); }, 0); }
  function reduce(n) { while (n > 9 && n !== 11 && n !== 22 && n !== 33) n = sum(n); return n; }
  box.querySelector('button').onclick = function () {
    var v = (inp.value || '').replace(/-/g, ''); if (v.length < 8) return;
    var p = inp.value.split('-'), n = reduce(reduce(sum(p[0])) + reduce(sum(p[1])) + reduce(sum(p[2])));
    out.innerHTML = '<a class="finder-res" href="' + D.pre + '/numerology/' + n + '/"><span class="bignum sm">' + n + '</span><span><b>' +
      D.res.replace('{n}', n) + '</b><small>' + (D.names[n] || '') + ' · ' + D.read + ' →</small></span></a>';
    out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };
})();
