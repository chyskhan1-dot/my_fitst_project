// Память устройства: какие вопросы оно уже видело (localStorage `quiz-seen`, последние 1500).
// Входя в комнату, устройство один раз отправляет список (/api/seen) — сервер берёт такие вопросы в последнюю очередь.
// Так вопросы не повторяются от игры к игре, даже после новой комнаты или перезапуска сервера.
window.QuizSeen = (() => {
  const KEY = "quiz-seen", MAX = 1500;
  let sent = null;
  const load = () => {
    try { const a = JSON.parse(localStorage.getItem(KEY) || "[]"); return Array.isArray(a) ? a : []; } catch { return []; }
  };
  function track(room, s) {
    if (room && sent !== room) {
      sent = room;
      fetch("/api/seen", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room, keys: load() }) }).catch(() => { sent = null; });
    }
    const si = s && s.si;
    const k = s && (s.qkey || (si && ((si.cur && si.cur.key) || (si.final && si.final.key))));
    if (!k) return;
    const list = load();
    if (list[list.length - 1] === k) return;
    const i = list.indexOf(k);
    if (i >= 0) list.splice(i, 1);
    list.push(k);
    try { localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX))); } catch {}
  }
  return { track };
})();
