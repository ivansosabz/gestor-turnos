// Service Worker para la PWA "No Me Olvido".
//
// Estrategia:
// - Estáticos (CSS/JS de CDN, manifest, /static/...): cache-first.
//   La primera vez se bajan; siguientes peticiones se sirven desde cache.
// - API (/api/...): network-first con fallback a cache. Esto permite
//   que la app siga mostrando el último calendario conocido si hay
//   problemas de red.
// - Otras URLs: best-effort cache, fallback a la red.

const CACHE_NAME = 'nmo-v1';

// Lista de assets que precacheamos al instalar el SW. Si querés
// invalidar el cache, basta con cambiar el nombre arriba (ej. 'nmo-v2').
const ASSETS = [
  '/',
  '/compartir/',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css',
  'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js',
  'https://cdn.jsdelivr.net/npm/dayjs@1.11.13/dayjs.min.js'
];

// --- install: precachear assets ---
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Usamos cache.add por separado dentro de un Promise.all para que
      // si UN asset falla (ej. CDN momentaneamente caído) no rompa la
      // instalación entera del SW.
      return Promise.all(
        ASSETS.map((url) =>
          cache.add(url).catch((err) => console.warn('Cache miss for', url, err))
        )
      );
    })
  );
  // Activar este SW inmediatamente, sin esperar a que se cierren las pestañas.
  self.skipWaiting();
});

// --- activate: limpiar caches viejos ---
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        // Borra cualquier cache cuyo nombre no sea el actual.
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  // Tomar control de las pestañas abiertas inmediatamente.
  self.clients.claim();
});

// --- fetch: estrategia de respuesta ---
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Solo manejamos GET. POSTs (registrar turno, crear ciclo) van directo a la red.
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // API: network-first (queremos datos frescos), fallback al cache.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          // Guardamos una copia en cache para tenerla disponible offline.
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Estáticos: cache-first.
  if (url.pathname.startsWith('/static/') || ASSETS.includes(request.url)) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  // Resto: cache si existe, si no fetch.
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
