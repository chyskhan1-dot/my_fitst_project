// Сервис-воркер установленного приложения (значок на телефоне).
// Трогает только открытие страниц: без интернета показывает «Нет связи» вместо ошибки браузера.
// Запросы игры (/api/…) и картинки идут как обычно — ничего не кэшируем, чтобы всегда была свежая версия.
const OFFLINE = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Квиз</title></head><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#0e1330;color:#f4f5ff;font:600 18px system-ui,sans-serif;text-align:center">
<div><div style="font-size:56px">📡</div><p>Нет связи с интернетом</p><button onclick="location.reload()" style="font:700 17px system-ui;padding:12px 22px;border:0;border-radius:12px;background:#ffd23f;color:#0e1330">Попробовать снова</button></div></body></html>`;
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  if (e.request.mode !== "navigate") return;
  e.respondWith(fetch(e.request).catch(() => new Response(OFFLINE, { headers: { "Content-Type": "text/html; charset=utf-8" } })));
});
