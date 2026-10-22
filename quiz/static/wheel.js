// Колесо выбора темы раунда — одно и то же у ведущего и на телефонах.
// Сектор темы = число голосов (тем без голосов на колесе нет), победителя заранее выбирает сервер — колесо только показывает.
(function () {
  const COLORS = ["var(--a0)", "var(--a1)", "var(--a2)", "var(--a3)"];
  const ICONS = { "Космос": "🚀", "Искусство": "🎨", "География": "🗺️", "Литература": "📚", "Математика": "➗",
    "Физика и химия": "⚗️", "Еда": "🍕", "Животные и растения": "🦊", "Русский язык": "🔤", "История": "🏛️",
    "Страны и города": "🏙️", "Человек": "🫀", "Разное": "🎲", "Изобретения и техника": "💡", "Спорт": "🏅", "Футбол": "⚽",
    "На внимательность": "👀", "Кино и мультфильмы": "🎬", "Мифология": "⚡", "Флаги": "🏳️", "Столицы": "🏛",
    "ПДД": "🚦", "Где на карте": "📍", "Убери лишнее": "🧩", "Интернет": "🌐" };
  const icon = (t) => ICONS[t] || "❓";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const CSS = `
.wheel { position: relative; width: min(100%, var(--size, 420px)); aspect-ratio: 1; margin: 0 auto; }
.wheel svg { width: 100%; height: 100%; display: block; }
.wheel .spinner-g { transform-origin: 50% 50%; transform-box: view-box; }
.wheel text { font: 800 6.2px system-ui, sans-serif; fill: #fff; paint-order: stroke; stroke: rgba(0,0,0,.35); stroke-width: .6px; }
.wheel .pointer { position: absolute; left: 50%; top: -6px; transform: translateX(-50%); width: 0; height: 0;
  border-left: 14px solid transparent; border-right: 14px solid transparent; border-top: 26px solid #fff; filter: drop-shadow(0 3px 4px rgba(0,0,0,.4)); }
`;
  let styled = false;
  // секторы: [начало, конец] в градусах по часовой от верха
  function sectors(weights) {
    const sum = weights.reduce((a, b) => a + b, 0) || 1;
    let a = 0;
    return weights.map((w) => { const s = a; a += (w / sum) * 360; return [s, a]; });
  }
  function point(deg, r) { const t = (deg - 90) * Math.PI / 180; return [50 + r * Math.cos(t), 50 + r * Math.sin(t)]; }
  function html(options, weights, size) {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    const secs = sectors(weights), shown = weights.filter((w) => w > 0).length;
    const slices = secs.map(([s, e], i) => {
      if (!(weights[i] > 0)) return ""; // за тему никто не голосовал — её нет на колесе
      const [x1, y1] = point(s, 48), [x2, y2] = point(e, 48), big = e - s > 180 ? 1 : 0;
      const path = shown === 1 ? `<circle cx="50" cy="50" r="48" fill="${COLORS[i % 4]}"/>`
        : `<path d="M50 50 L${x1} ${y1} A48 48 0 ${big} 1 ${x2} ${y2} Z" fill="${COLORS[i % 4]}" stroke="rgba(255,255,255,.7)" stroke-width=".6"/>`;
      const mid = (s + e) / 2, [tx, ty] = point(mid, 30);
      const label = options[i].length > 14 ? options[i].slice(0, 13) + "…" : options[i];
      return `${path}<g transform="rotate(${mid} ${tx} ${ty})"><text x="${tx}" y="${ty - 3}" text-anchor="middle" style="font-size:9px">${icon(options[i])}</text>
        <text x="${tx}" y="${ty + 6}" text-anchor="middle">${esc(label)}</text></g>`;
    }).join("");
    return `<div class="wheel" style="--size:${size || 420}px"><div class="pointer"></div><svg viewBox="0 0 100 100">
      <g class="spinner-g">${slices}</g><circle cx="50" cy="50" r="6" fill="#1b1f3a" stroke="#fff" stroke-width="1.2"/></svg></div>`;
  }
  // крутим так, чтобы под стрелкой (сверху) остановился сектор победителя; left — сколько секунд осталось крутиться
  function spin(el, winner, weights, round, left) {
    const g = el.querySelector(".spinner-g");
    if (!g) return;
    const [s, e] = sectors(weights)[winner];
    const jitter = (Math.sin((round || 1) * 12.9898) * 0.5) * (e - s) * 0.6; // одинаково на всех экранах
    const target = 360 * 6 - ((s + e) / 2 + jitter);
    if (left <= 0.05) { g.style.transform = `rotate(${target}deg)`; return; }
    g.style.transition = "none"; g.style.transform = "rotate(0deg)";
    g.getBoundingClientRect();
    g.style.transition = `transform ${left}s cubic-bezier(.12,.6,.1,1)`;
    g.style.transform = `rotate(${target}deg)`;
  }
  window.QuizWheel = { html, spin, icon };
})();
