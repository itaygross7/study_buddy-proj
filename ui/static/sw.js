// StudyBuddy Service Worker
// Version 1.0.1
const CACHE_NAME = 'studybuddy-v1.0.1';
const RUNTIME_CACHE = 'studybuddy-runtime-v1.0.1';

// Essential files to cache on install
const PRECACHE_URLS = [
  '/',
  '/static/css/styles.css',
  '/static/js/avner_animations.js',
  '/avner/app_logo.jpeg',
  '/avner/avner_waving.jpeg',
  '/avner/mobile_bacround.jpeg',
  '/avner/desktop_ui_backround.jpeg',
  '/offline'
];

// Install event - cache essential files
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing service worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Precaching app shell');
        return cache.addAll(PRECACHE_URLS.map(url => new Request(url, {cache: 'reload'})));
      })
      .catch(err => {
        console.warn('[Service Worker] Precache failed for some resources:', err);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating service worker...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE)
          .map(cacheName => {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    })
  );
  return self.clients.claim();
});

// Fetch event - network first, fall back to cache
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }
  
  // Skip API calls for real-time data
  if (url.pathname.startsWith('/api/') || 
      url.pathname.startsWith('/auth/') ||
      url.pathname.startsWith('/oauth/')) {
    return;
  }
  
  // Network-first strategy for HTML pages
  const acceptHeader = request.headers.get('Accept');
  if (acceptHeader && acceptHeader.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Clone the response before caching
          const responseClone = response.clone();
          caches.open(RUNTIME_CACHE).then(cache => {
            cache.put(request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // Fall back to cache if network fails
          return caches.match(request)
            .then(cached => {
              if (cached) {
                return cached;
              }
              // If no cached page, show offline page
              return caches.match('/offline');
            });
        })
    );
    return;
  }
  
  // Cache-first strategy for static assets
  event.respondWith(
    caches.match(request)
      .then(cached => {
        if (cached) {
          // Update cache in background
          fetch(request).then(response => {
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, response);
            });
          }).catch(() => {
            // Fail silently if network update fails
          });
          return cached;
        }
        
        // Not in cache, fetch from network
        return fetch(request).then(response => {
          // Cache successful responses
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(RUNTIME_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        });
      })
  );
});

// Handle messages from clients
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(RUNTIME_CACHE).then(cache => {
        return cache.addAll(event.data.urls);
      })
    );
  }
});

// Background sync for offline actions (future enhancement)
self.addEventListener('sync', event => {
  console.log('[Service Worker] Background sync:', event.tag);
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData());
  }
});

async function syncData() {
  // Placeholder for future offline sync functionality
  console.log('[Service Worker] Syncing data...');
}

// Push notifications (future enhancement)
self.addEventListener('push', event => {
  console.log('[Service Worker] Push notification received');
  const options = {
    body: event.data ? event.data.text() : 'הודעה חדשה מ-StudyBuddy',
    icon: '/avner/app_logo.jpeg',
    badge: '/avner/app_logo.jpeg',
    vibrate: [200, 100, 200],
    tag: 'studybuddy-notification',
    requireInteraction: false
  };
  
  event.waitUntil(
    self.registration.showNotification('StudyBuddy', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked');
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});
