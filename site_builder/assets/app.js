(function () {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () {}); });
  }
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  var standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone ||
                   document.referrer.indexOf('android-app://') === 0 || location.search.indexOf('source=android') > -1;
  if (standalone) set('dt-installed', '1');

  var deferred = null;
  var topBtn = document.getElementById('install');
  var banner = document.getElementById('appbanner');
  var ua = navigator.userAgent;
  var isIOS = /iPhone|iPad|iPod/i.test(ua), isAndroid = /Android/i.test(ua), isMobile = isIOS || isAndroid;
  var play = banner ? banner.dataset.play : '';

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault(); deferred = e;
    if (topBtn) topBtn.hidden = false;
  });

  function install() {
    if (deferred) {
      deferred.prompt();
      deferred.userChoice.then(function (c) { if (c.outcome === 'accepted') set('dt-installed', '1'); }).finally(function () { deferred = null; });
      hide();
      return;
    }
    if (isAndroid && play) { location.href = play; hide(); return; }
    if (isIOS && banner) { banner.querySelector('.ab-text span').textContent = banner.dataset.ios; return; }
    hide();
  }
  function hide(remember) {
    if (banner) banner.hidden = true;
    if (remember) set('dt-banner-later', String(Date.now()));
  }

  if (topBtn) topBtn.addEventListener('click', install);
  window.addEventListener('appinstalled', function () { set('dt-installed', '1'); if (topBtn) topBtn.hidden = true; hide(); });

  if (!banner || standalone || get('dt-installed') || !isMobile) return;
  var later = +get('dt-banner-later') || 0;
  if (Date.now() - later < 3 * 24 * 3600 * 1000) return;
  if (/\/puzzle\/|\/games\/.+/.test(location.pathname)) return; // never interrupt a game
  document.getElementById('ab-install').addEventListener('click', install);
  document.getElementById('ab-later').addEventListener('click', function () { hide(true); });
  setTimeout(function () {
    if (deferred || play || isIOS) banner.hidden = false;
  }, 8000);
})();
