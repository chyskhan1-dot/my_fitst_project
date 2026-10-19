// Верёвка вместо таблицы лидеров: у каждого своя верёвка, после вопроса игроки по очереди лезут вверх
// на заработанные очки. Вершина — цель «Царя горы» или максимум очков за игру. За верёвками — гора. Общая для ТВ и телефонов.
(function () {
  const CSS = `
.rope-stage { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.rope-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; color: var(--muted); font-weight: 800; font-size: .9em; }
.rope-top b { color: var(--accent); }
.ropes { position: relative; display: flex; justify-content: center; gap: 10px; width: 100%; padding-top: 34px; }
.ropes::before { content: ""; position: absolute; left: 0; right: 0; top: 34px; border-top: 3px dashed rgba(255, 210, 63, .55); } /* финиш */
.mount { position: absolute; left: 0; right: 0; top: 34px; height: var(--h, 46vh); width: 100%; z-index: 0; pointer-events: none; }
.summit { position: absolute; left: 50%; top: 2px; transform: translateX(-35%); font-size: 26px; z-index: 0; line-height: 1; }
.rope-stage.compact .summit { font-size: 20px; top: 8px; }
.rope-col { position: relative; z-index: 1; flex: 1; min-width: 0; max-width: 96px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.rope { position: relative; width: 100%; height: var(--h, 46vh); }
.rope::before { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 6px; transform: translateX(-50%); border-radius: 3px;
  background: repeating-linear-gradient(to bottom, #c9a26b 0 12px, #8d6a3c 12px 16px); opacity: .85; }
.rope-col.lead .rope::before { box-shadow: 0 0 12px rgba(255, 210, 63, .6); }
.climber { position: absolute; left: 50%; bottom: calc(var(--y, 0) * (100% - var(--face, 48px))); transform: translateX(-50%);
  transition: bottom 1s cubic-bezier(.3, 1.25, .5, 1); display: flex; flex-direction: column; align-items: center; z-index: 1; }
.climber .face { display: grid; place-items: center; }
.climber .face .ava { width: var(--face, 48px); height: var(--face, 48px); font-size: calc(var(--face, 48px) * .45); }
.climber .gain { position: absolute; bottom: 100%; margin-bottom: 4px; padding: 2px 8px; border-radius: 99px; font-weight: 800; font-size: .8em;
  white-space: nowrap; background: var(--good, #3ddc84); color: #0e1330; opacity: 0; transform: translateY(6px); transition: opacity .3s, transform .3s; }
.climber .gain.minus { background: var(--bad, #ff6b6b); }
.climber.go .gain { opacity: 1; transform: none; }
.climber .crown { position: absolute; right: -1.2em; top: -.3em; font-size: 1.1em; }
.rope-name { width: 100%; text-align: center; font-weight: 800; font-size: .85em; line-height: 1.2; }
.rope-name span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rope-name b { display: block; color: var(--muted); font-variant-numeric: tabular-nums; }
.rope-col.me .rope-name span { color: var(--accent); }
.team-face { width: var(--face, 48px); height: var(--face, 48px); border-radius: 50%; background: var(--c); border: 3px solid #fff; display: block; }
.rope-stage.compact { --face: 34px; font-size: 14px; }
.rope-stage.compact .ropes { gap: 6px; }
@media (prefers-reduced-motion: reduce) { .climber { transition: none; } }
`;
  // гора за верёвками: дальний хребет, главная вершина со снежной шапкой — пик ровно на финишной черте
  const MOUNTAIN = `<svg class="mount" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="mnt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5b5f9c"/><stop offset="1" stop-color="#1d2050"/></linearGradient>
      <linearGradient id="mnt2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34386e"/><stop offset="1" stop-color="#161936"/></linearGradient></defs>
    <polygon points="0,100 0,52 9,40 18,50 30,26 40,40 50,14 60,34 71,22 82,44 91,32 100,46 100,100" fill="url(#mnt2)" opacity=".75"/>
    <polygon points="0,100 0,80 14,62 27,72 50,0 73,68 86,58 100,76 100,100" fill="url(#mnt)" opacity=".9"/>
    <polygon points="50,0 42,20 46,18 49,24 52,17 55,22 58,19" fill="#eef1ff" opacity=".9"/>
  </svg><span class="summit">🚩</span>`;
  let styled = false;
  const shown = new Set(); // какие подъёмы уже показали: при перерисовке экрана не лезем заново
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Number(n).toLocaleString("ru-RU");
  const clamp = (v) => Math.max(0, Math.min(1, v));

  // rows: [{name, score, last, face (готовый HTML аватарки), me}] — по местам; top — сколько очков у вершины;
  // key — один подъём на вопрос (по нему не повторяем); opts: {height, compact, race, mountain}
  function html(rows, top, key, opts = {}) {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    const order = rows.map((r, i) => i).sort((a, b) => (rows[a].last - rows[b].last) || (rows[a].score - rows[b].score)); // большой рывок — в конце
    const turn = new Map(order.map((idx, k) => [idx, k]));
    const cols = rows.map((r, i) => {
      const from = clamp((r.score - (r.last || 0)) / top), to = clamp(r.score / top);
      const gain = r.last ? `<span class="gain ${r.last < 0 ? "minus" : ""}">${r.last > 0 ? "+" : "−"}${num(Math.abs(r.last))}</span>` : "";
      const again = shown.has(key); // уже лезли — сразу на месте
      return `<div class="rope-col ${i === 0 && r.score > 0 ? "lead" : ""} ${r.me ? "me" : ""}">
        <div class="rope"><div class="climber ${again ? "go" : ""}" data-from="${from}" data-to="${to}" data-turn="${turn.get(i)}" data-score="${r.score}" style="--y:${again ? to : from}">
          ${i === 0 && r.score > 0 ? `<span class="crown">${to >= 1 ? "🏆" : "👑"}</span>` : ""}${gain}<span class="face">${r.face}</span></div></div>
        <div class="rope-name"><span>${esc(r.name)}</span><b>${num(again ? r.score : r.score - (r.last || 0))}</b></div></div>`;
    }).join("");
    return `<div class="rope-stage ${opts.compact ? "compact" : ""}" data-key="${esc(key)}" style="--h:${opts.height || "46vh"}">
      <div class="rope-top"><span>⛰️ ${opts.race ? "Вершина — царь горы" : "Вершина"}</span><b>${num(top)}</b></div>
      <div class="ropes">${opts.mountain ? MOUNTAIN : ""}${cols}</div></div>`;
  }

  // по очереди: каждый поднимается на свои очки; уже показанный подъём — сразу в конечном положении
  function climb(root) {
    const stage = root && root.querySelector(".rope-stage");
    if (!stage) return;
    const climbers = [...stage.querySelectorAll(".climber")];
    const finish = (el) => {
      el.style.setProperty("--y", el.dataset.to);
      el.classList.add("go");
      el.closest(".rope-col").querySelector(".rope-name b").textContent = num(el.dataset.score);
    };
    const key = stage.dataset.key;
    if (shown.has(key) || matchMedia("(prefers-reduced-motion: reduce)").matches) { climbers.forEach(finish); return; }
    shown.add(key);
    climbers.forEach((el) => setTimeout(() => { if (el.isConnected) finish(el); }, 500 + Number(el.dataset.turn) * 700));
  }

  window.QuizRope = { html, climb };
})();
