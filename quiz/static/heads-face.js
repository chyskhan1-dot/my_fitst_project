// «Слово на лбу»: экран телефона у лба — слово во весь экран, таймер, наклоны и касания.
// Общий для игры в комнате (play.html, слова с сервера) и игры с одного телефона (heads.html, слова на самом телефоне).
// Угадал — наклон вниз (экраном к полу), не знаешь — вверх. Наклон считаем по датчику ориентации:
// v = cos(beta)·cos(gamma) — куда смотрит экран (1 — в потолок, −1 — в пол, 0 — вперёд). Новый наклон засчитывается,
// только когда телефон вернули прямо. Запасной вариант — касание верхней («угадал») или нижней («пропуск») половины экрана.
(function () {
  const CSS = `
#hd-face { position: fixed; inset: 0; z-index: 14; /* под «Паузой» */ background: #0e1330; color: #fff; display: flex; align-items: center; justify-content: center;
  user-select: none; -webkit-user-select: none; touch-action: none; transition: background .15s; }
#hd-face[data-flash="ok"] { background: #1f9d57; }
#hd-face[data-flash="pass"] { background: #c93a3a; }
#hd-face .hd-word { width: 92vw; height: 70vh; display: flex; align-items: center; justify-content: center; text-align: center; white-space: pre-line;
  font-family: var(--display); font-weight: 800; line-height: 1.05; overflow: hidden; pointer-events: none; }
#hd-face .hd-bar { position: absolute; left: 0; right: 0; top: 0; height: 10px; background: rgba(255, 255, 255, .15); }
#hd-face .hd-bar i { display: block; height: 100%; background: var(--accent); transition: width .2s linear; }
#hd-face .hd-left { position: absolute; top: 18px; right: 22px; font: 800 48px var(--display); line-height: 1; color: #ffd23f; pointer-events: none; }
#hd-face .hd-left.low { color: #ff6b6b; }
#hd-face .hd-zone { position: absolute; left: 0; right: 0; height: 50%; border: 0; background: transparent; color: rgba(255, 255, 255, .6);
  font: 800 18px var(--body); display: flex; justify-content: center; padding: 22px; }
#hd-face.taps .hd-zone { color: #fff; }
#hd-face.taps .hd-zone.up { background: linear-gradient(rgba(61, 220, 132, .18), transparent); }
#hd-face.taps .hd-zone.down { background: linear-gradient(transparent, rgba(255, 107, 107, .18)); }
#hd-face .hd-zone.up { top: 0; align-items: flex-start; padding-top: 30px; }
#hd-face .hd-zone.down { bottom: 0; align-items: flex-end; }
body:has(#hd-face) #hostbar { display: none; } /* у лба кнопки ведущего не нужны — легко задеть */
#hd-rotate { position: fixed; inset: 0; z-index: 14; background: #0e1330; color: #fff; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 18px; padding: 24px; text-align: center; font: 700 20px var(--body); }
#hd-rotate small { font: 600 15px var(--body); color: #c2c8ec; max-width: 320px; line-height: 1.4; }
#hd-rotate .ok { font: 800 18px var(--body); color: #1a1400; background: #ffd23f; border: 0; padding: 14px 24px; }
#hd-rotate .ph { font-size: 72px; animation: hd-turn 1.6s ease-in-out infinite; }
#hd-rotate button { font: 700 15px var(--body); color: #a7aedb; background: transparent; border: 1px solid rgba(255, 255, 255, .2); border-radius: 12px; padding: 10px 16px; }
@keyframes hd-turn { 0%, 30% { transform: rotate(0); } 60%, 100% { transform: rotate(-90deg); } }
`;
  const hd = { taps: false, word: null, end: 0, ready: 0, total: 60, armed: false, busy: false, flashUntil: 0, timer: null, wake: null, onMark: null, onEnd: null, ended: false };
  let styled = false;
  const face = () => document.getElementById("hd-face");
  const buzz = (ms) => { try { navigator.vibrate && navigator.vibrate(ms); } catch {} };

  const portrait = () => innerHeight > innerWidth;
  // по нажатию «Старт»: iPhone спрашивает разрешение на датчики, экран не гаснет, на Android — полный экран и
  // закреплённое горизонтальное положение. Играем горизонтально: держать у лба удобнее, и экран не повернётся посреди хода.
  async function prepare() {
    style();
    let allowed = true;
    try {
      if (window.DeviceOrientationEvent && typeof DeviceOrientationEvent.requestPermission === "function") allowed = (await DeviceOrientationEvent.requestPermission()) === "granted";
    } catch { allowed = false; }
    hd.taps = !allowed;
    if (!allowed) await notice("Наклоны выключены", "Телефон не дал доступ к датчику движения. Играем касаниями: верх экрана — угадал, низ — пропуск. Включить наклоны: закрой и снова открой сайт и нажми «Разрешить»");
    try { hd.wake = await navigator.wakeLock.request("screen"); } catch {}
    try { if (document.documentElement.requestFullscreen && !document.fullscreenElement) await document.documentElement.requestFullscreen({ navigationUI: "hide" }); } catch {}
    try { await screen.orientation.lock("landscape"); } catch {} // iPhone так не умеет — тогда просим повернуть
    if (portrait()) await askRotate();
  }

  // сообщение с кнопкой «Понятно»
  function notice(title, text) {
    return new Promise((done) => {
      const box = document.createElement("div"); box.id = "hd-rotate";
      box.innerHTML = `<span class="ph">✋</span><span>${title}</span><small>${text}</small><button type="button" class="ok">Понятно</button>`;
      document.body.appendChild(box);
      box.querySelector("button").addEventListener("click", () => { box.remove(); done(); });
    });
  }

  // «Поверни телефон боком» — ждём горизонтального положения; если автоповорот выключен — можно играть вертикально
  function askRotate() {
    return new Promise((done) => {
      const box = document.createElement("div"); box.id = "hd-rotate";
      box.innerHTML = `<span class="ph">📱</span><span>Поверни телефон горизонтально</span>
        <small>Не поворачивается? Выключи блокировку поворота экрана или играй вертикально — тоже работает</small>
        <button type="button">Играть вертикально</button>`;
      document.body.appendChild(box);
      const finish = () => { removeEventListener("resize", check); box.remove(); done(); };
      const check = () => { if (!portrait()) setTimeout(finish, 300); }; // дать экрану довернуться
      addEventListener("resize", check);
      box.querySelector("button").addEventListener("click", finish);
    });
  }

  function style() {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
  }

  async function mark(ok) {
    if (hd.busy || !hd.word || Date.now() < hd.ready || Date.now() >= hd.end) return;
    hd.busy = true; hd.armed = false;
    flash(ok);
    try { window.QuizMusic && QuizMusic.sting(ok ? "reveal" : "wrong"); } catch {} // звук на самом телефоне
    try {
      const next = await hd.onMark(ok);
      if (next !== undefined) hd.word = next;
    } catch {}
    hd.busy = false;
    setTimeout(paint, Math.max(0, hd.flashUntil - Date.now()));
  }

  function flash(ok) {
    const f = face();
    if (!f) return;
    buzz(ok ? 80 : [40, 60, 40]);
    hd.flashUntil = Date.now() + 700;
    f.dataset.flash = ok ? "ok" : "pass";
    f.querySelector(".hd-word").textContent = ok ? "Угадано! ✓" : "Пропуск";
  }

  function paint() {
    const f = face();
    if (!f) return;
    if (Date.now() >= hd.end && !hd.ended) { hd.ended = true; if (hd.onEnd) hd.onEnd(); }
    if (!face() || Date.now() < hd.flashUntil) return;
    const left = Math.max(0, (hd.end - Date.now()) / 1000), wait = (hd.ready - Date.now()) / 1000;
    f.dataset.flash = "";
    const w = f.querySelector(".hd-word"), text = wait > 0 ? `Приложи ко лбу\n${Math.ceil(wait)}` : hd.word || "";
    if (w.textContent !== text) { w.textContent = text; w.style.fontSize = ""; fitWord(w); }
    const lt = f.querySelector(".hd-left");
    lt.textContent = wait > 0 ? "" : Math.ceil(left);
    lt.classList.toggle("low", wait <= 0 && left <= 10);
    f.querySelector(".hd-bar i").style.width = (wait > 0 ? 100 : (left / hd.total) * 100) + "%";
  }

  function fitWord(w) { // слово во всю ширину, но целиком: длинное слово не переносится посреди
    let size = Math.min(innerWidth / 5, innerHeight / 3);
    w.style.fontSize = size + "px";
    while (size > 18 && (w.scrollWidth > w.clientWidth || w.scrollHeight > w.clientHeight)) { size *= 0.9; w.style.fontSize = size + "px"; }
  }

  // телефон повернули посреди хода — слово заново подгоняем под экран
  addEventListener("resize", () => {
    const f = face(), w = f && f.querySelector(".hd-word");
    if (w && w.textContent) { w.style.fontSize = ""; fitWord(w); }
  });

  window.addEventListener("deviceorientation", (e) => {
    if (e.beta == null || !face()) return;
    const v = Math.cos(e.beta * Math.PI / 180) * Math.cos(e.gamma * Math.PI / 180);
    if (Math.abs(v) < 0.4) hd.armed = true; // телефон снова прямо — можно следующий наклон
    else if (hd.armed && Math.abs(v) > 0.7) mark(v < 0);
  });

  // показать или обновить экран у лба. word — текущее слово (undefined — оставить как есть), left — секунд до конца хода,
  // readyLeft — секунд на «приложи ко лбу», onMark(ok) → следующее слово, onEnd — время вышло (для игры без сервера)
  function show({ word, left, readyLeft = 0, total = 60, onMark, onEnd = null }) {
    style();
    hd.total = total; hd.end = Date.now() + left * 1000; hd.ready = Date.now() + readyLeft * 1000;
    hd.onMark = onMark; hd.onEnd = onEnd;
    if (word !== undefined && !hd.busy) hd.word = word;
    let f = face();
    if (!f) {
      f = document.createElement("div"); f.id = "hd-face";
      f.innerHTML = `<div class="hd-bar"><i></i></div><span class="hd-left"></span><div class="hd-word"></div>
        <button type="button" class="hd-zone up" aria-label="Угадал">✓ Угадал</button><button type="button" class="hd-zone down" aria-label="Пропустить">✗ Пропуск</button>`;
      document.body.appendChild(f);
      f.querySelector(".up").addEventListener("pointerdown", (e) => { e.preventDefault(); mark(true); });
      f.querySelector(".down").addEventListener("pointerdown", (e) => { e.preventDefault(); mark(false); });
      f.classList.toggle("taps", hd.taps); // без датчика — касания подсвечены
      hd.armed = false; hd.ended = false; clearInterval(hd.timer); hd.timer = setInterval(paint, 200);
    }
    paint();
  }

  function hide() {
    const f = face();
    if (!f) return;
    f.remove(); clearInterval(hd.timer);
    try { hd.wake && hd.wake.release(); } catch {}
    hd.wake = null; hd.word = null;
    try { screen.orientation.unlock(); } catch {}
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  }

  window.QuizHeads = { prepare, show, hide, fitWord, get busy() { return hd.busy; } };
})();
