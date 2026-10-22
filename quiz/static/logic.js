// «Где логика»: три картинки открываются по одной (каждые четверть времени вопроса) — кто раньше угадал связь, тот больше очков.
// Общий для экрана ведущего (host.html) и телефона (play.html).
(function () {
  const CSS = `
.logic { display: grid; grid-template-columns: repeat(var(--n, 3), minmax(0, 1fr)); gap: 12px; width: 100%; }
.logic .lc { position: relative; aspect-ratio: 4 / 3; max-height: 34vh; border-radius: 16px; overflow: hidden; background: rgba(255, 255, 255, .07);
  border: 2px dashed rgba(255, 255, 255, .18); display: flex; align-items: center; justify-content: center; }
.logic .lc img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; opacity: 0; transform: scale(.92);
  transition: opacity .6s, transform .6s cubic-bezier(.3, 1.5, .5, 1); }
.logic .lc.on { border: 0; }
.logic .lc.on img { opacity: 1; transform: none; }
.logic .lc .q { font: 800 3em var(--display, sans-serif); color: rgba(255, 255, 255, .45); }
.logic .lc.on .q { display: none; }
.logic-next { margin: 6px 0 0; text-align: center; font-weight: 700; color: var(--muted); font-size: .9em; min-height: 1.3em; }`;
  let styled = false;
  const style = () => { if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; } };
  const step = (s) => (s.seconds || 30) / (s.images.length + 1);
  // сколько картинок уже открыто: на вопросе — по времени, после вопроса — все
  function shown(s) {
    if (s.phase !== "question" || s.left == null) return s.images.length;
    return Math.min(s.images.length, Math.floor(Math.max(0, s.seconds - s.left) / step(s)) + 1);
  }
  function nextText(s) {
    const k = shown(s);
    if (s.phase !== "question" || k >= s.images.length) return "";
    const wait = Math.ceil(k * step(s) - (s.seconds - s.left));
    return `Следующая картинка через ${Math.max(1, wait)} с — угадаешь раньше, получишь больше очков`;
  }
  function html(s, src) {
    style();
    const k = shown(s);
    return `<div class="logic" data-logic style="--n:${s.images.length}">${s.images.map((p, i) =>
      `<div class="lc ${i < k ? "on" : ""}" data-i="${i}"><img src="${src(p)}" alt=""><span class="q">?</span></div>`).join("")}</div>
      <p class="logic-next" id="logic-next">${nextText(s)}</p>`;
  }
  function update(s) {
    if (!s.images) return;
    const k = shown(s);
    document.querySelectorAll("[data-logic] .lc").forEach((el) => el.classList.toggle("on", Number(el.dataset.i) < k));
    const nx = document.getElementById("logic-next");
    if (nx) nx.textContent = nextText(s);
  }
  window.QuizLogic = { html, update };
})();
