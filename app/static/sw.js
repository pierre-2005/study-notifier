/* Offline installation shell caches static resources only; private data is never cached. */
const CACHE='mlo-static-v3.7.0';
const ASSETS=['/static/product37.css?v=3.7.0','/static/study-planner.js?v=3.7.0','/static/task-inspector.js?v=3.7.0','/static/workspace37.css?v=3.7.0','/static/v37-board.css?v=3.7.0','/static/v37-board.js?v=3.7.0','/static/v37-onboarding.css?v=3.7.0','/static/v37-onboarding.js?v=3.7.0','/static/course-import.js?v=3.7.0','/static/theme.css?v=3.7.0','/static/life.css?v=3.7.0','/static/design32.css?v=3.7.0','/static/design33.css?v=3.7.0','/static/flow34.css?v=3.7.0','/static/flow34.js?v=3.7.0','/static/theme.js?v=3.7.0','/static/life.js?v=3.7.0','/static/customize.js?v=3.7.0','/static/apple-touch-icon.png','/static/icon-192.png','/static/icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key))))));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||!url.pathname.startsWith('/static/')||url.pathname.endsWith('.webmanifest'))return;
 event.respondWith(caches.match(event.request).then(hit=>hit||fetch(event.request).then(resp=>{
  if(resp.ok&&resp.type==='basic'){
   const copy=resp.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));
  }return resp;
 })));
});
