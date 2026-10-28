/* MLO caches public static assets only. Authenticated pages and APIs stay on the server. */
const CACHE='mlo-static-v4.0.0';
const ASSETS=['/static/app.css?v=4.0.0','/static/public.css?v=4.0.0','/static/onboarding.css?v=4.0.0','/static/app.js?v=4.0.0','/static/appearance.js?v=4.0.0','/static/tasks.js?v=4.0.0','/static/layout.js?v=4.0.0','/static/capture.js?v=4.0.0','/static/board.js?v=4.0.0','/static/onboarding.js?v=4.0.0','/static/budget.js?v=4.0.0','/static/notes.js?v=4.0.0','/static/task-inspector.js?v=4.0.0','/static/course-import.js?v=4.0.0','/static/study-planner.js?v=4.0.0','/static/apple-touch-icon.png','/static/icon-192.png','/static/icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('mlo-static-')&&key!==CACHE).map(key=>caches.delete(key))))));
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==self.location.origin||!url.pathname.startsWith('/static/')||url.pathname.endsWith('.webmanifest'))return;
 event.respondWith(caches.open(CACHE).then(async cache=>{
  const cached=await cache.match(event.request);if(cached)return cached;
  const response=await fetch(event.request);
  if(response.ok&&response.type==='basic')await cache.put(event.request,response.clone());
  return response;
 }));
});
