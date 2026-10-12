/* Asset-only service worker. Never store authenticated HTML or API responses. */
const CACHE='mlo-static-v3-preview1';
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(['/static/theme.css?v=3.0.0-preview.1','/static/life.css?v=3.0.0-preview.1','/static/theme.js?v=3.0.0-preview.1','/static/life.js?v=3.0.0-preview.1','/static/apple-touch-icon.png']))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin||!url.pathname.startsWith('/static/'))return;
  event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request).then(resp=>{
    if(resp.ok&&resp.type==='basic'){
      const copy=resp.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));
    }return resp;
  })));
});
