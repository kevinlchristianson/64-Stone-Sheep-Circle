// Makes the pages an installable home-screen app: registers the service worker
// (only when served on its own, not inside a frame) and adds a Home button
// on every page but the home screen (a home-screen app has no back button).
(() => {
  const framed = (() => { try { return window.top !== window.self; } catch { return true; } })();
  if (framed) return;
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    addEventListener('load', () => { navigator.serviceWorker.register('./sw.js').catch(() => {}); });
  }
  if (/\/(home\.html)?$/.test(location.pathname) || document.body?.hasAttribute('data-own-nav')) return;
  const add = () => {
    const a = document.createElement('a');
    a.href = './home.html'; a.textContent = '‹ Home'; a.setAttribute('aria-label', 'Back to the home screen');
    a.style.cssText = 'position:fixed;z-index:50;left:12px;bottom:calc(12px + env(safe-area-inset-bottom, 0px));padding:9px 14px 8px;border-radius:999px;background:var(--ink,#23201d);color:var(--sheet,#fbfaf7);font:600 14px/1 "Barlow Condensed","Arial Narrow",sans-serif;letter-spacing:.06em;text-transform:uppercase;text-decoration:none;box-shadow:0 2px 10px rgba(0,0,0,.25)';
    document.body.append(a);
  };
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
})();
