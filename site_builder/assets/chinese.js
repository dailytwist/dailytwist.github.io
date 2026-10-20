/* DailyTwist: Chinese zodiac animal from a birth date (uses Chinese New Year dates). Original code. */
(function () {
  var box = document.getElementById('cfinder'); if (!box) return;
  var D = JSON.parse(document.getElementById('cfinder-data').textContent);
  var inp = box.querySelector('input'), out = box.querySelector('.finder-out');
  function animalFor(y, m, d) {
    var ny = D.cny[y]; if (!ny) return null;
    if (m * 100 + d < ny) y--;
    return D.a[((y - 1936) % 12 + 12) % 12];
  }
  box.querySelector('button').onclick = function () {
    var p = (inp.value || '').split('-'); if (p.length < 3) return;
    var a = animalFor(+p[0], +p[1], +p[2]); if (!a) return;
    var txt = '<b>' + D.you.replace('{animal}', D.n[a]) + '</b>';
    out.innerHTML = '<a class="finder-res" href="' + D.pre + '/chinese-zodiac/' + (D.has.indexOf(a) > -1 ? a + '/' : '') + '"><span class="aemo" style="width:84px;height:84px;font-size:46px">' + D.emo[a] + '</span><span>' + txt + '</span></a>';
    document.querySelectorAll('.zcard').forEach(function (c) { c.classList.toggle('mine', c.dataset.animal === a); });
    out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };
})();
