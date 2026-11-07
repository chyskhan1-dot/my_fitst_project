// Аватарка игрока — смайлик в цветном круге: заливка цветом игрока ~22%, обводка 3 px тем же цветом, смайлик ~70% круга.
// Цвет даёт сервер по порядку входа (PLAYER_COLORS в server.py — та же палитра); нет цвета — по имени.
// Один и тот же цвет на всех экранах: лобби, гора, списки ответов, подписи. Общая для ТВ и телефонов.
(function () {
  const PALETTE = ["#ff6b6b", "#2ed3c6", "#ffd23f", "#a46bff", "#4cd964", "#ff6fb5", "#5ac8fa", "#ff9f43", "#c3e84a", "#4f7cff"];
  const CSS = `
.ava { width: var(--s, 32px); height: var(--s, 32px); border-radius: 50%; flex: none; display: inline-grid; place-items: center; box-sizing: border-box;
  border: 3px solid var(--c, #8a90c8); background: var(--cb, rgba(138, 144, 200, .22)); color: #fff; line-height: 1;
  font-family: var(--display, inherit); font-weight: 800; font-size: calc(var(--s, 32px) * .42); }
.ava .emo-img { width: 70%; height: 70%; vertical-align: 0; }
.ava.me { box-shadow: 0 0 0 2px #fff, 0 0 14px 2px var(--c); }
`;
  const st = document.createElement("style");
  st.textContent = CSS;
  document.head.prepend(st); // в начало: размеры под свой экран задают страницы
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function color(p) {
    if (p && /^#[0-9a-f]{6}$/i.test(p.color || "")) return p.color;
    let h = 0;
    for (const ch of String((p && p.name) || "?")) h = (h * 31 + ch.codePointAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }
  // какой цвет получит новый игрок (для выбора аватарки до входа): первый свободный, как на сервере
  function next(players) {
    const used = (players || []).map((p) => p.color);
    return PALETTE.find((c) => !used.includes(c)) || PALETTE[used.length % PALETTE.length];
  }
  const vars = (c) => `--c:${c};--cb:${c}38`; // 38 в hex ≈ 22% непрозрачности
  // p: {name, avatar, color}; cls — дополнительные классы (xl, me…)
  function html(p, cls = "") {
    const c = color(p);
    const inner = p && p.avatar ? QuizEmoji.html(p.avatar) : esc([...String((p && p.name) || "?")][0].toUpperCase());
    return `<span class="ava ${cls}" style="${vars(c)}">${inner}</span>`;
  }
  window.QuizAva = { PALETTE, color, next, vars, html };
})();
