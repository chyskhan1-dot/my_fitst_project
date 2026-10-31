// Экран не гаснет, пока открыта игра: ТВ с экраном ведущего и телефоны игроков (Screen Wake Lock, нужен https).
// Блокировка снимается, когда вкладку прячут, — при возвращении берём её снова; некоторые браузеры дают её только после нажатия.
(function () {
  let lock = null;
  async function keep() {
    if (lock || document.hidden || !("wakeLock" in navigator)) return;
    try {
      lock = await navigator.wakeLock.request("screen");
      lock.addEventListener("release", () => { lock = null; });
    } catch {}
  }
  document.addEventListener("visibilitychange", keep);
  ["pointerdown", "keydown", "click"].forEach((t) => document.addEventListener(t, keep, true));
  keep();
})();
