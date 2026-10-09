// Bump VERSION whenever a page or data file changes so phones pick up the new copy.
const VERSION = 'v1';
const CACHE = 'ssp-' + VERSION;
const SHELL = [
  './home.html', './budget.html', './energy.html', './rooms.html', './contractor.html',
  './style.css', './pwa.js', './manifest.json', './model/energy.js', './model/budget.js',
  './icons/icon-180.png', './icons/icon-192.png', './icons/icon-512.png',
  './data/house-data.json', './data/weather-tmy3.json', './data/budget-seed.json'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('ssp-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
// Network first so edits show up when online; the cache covers offline use.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request)
    .then(res => {
      if (res && (res.ok || res.type === 'opaque')) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return res;
    })
    .catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || (e.request.mode === 'navigate' ? caches.match('./home.html') : undefined))));
});
