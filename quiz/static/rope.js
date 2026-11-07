// Гора вместо таблицы лидеров: одна общая тропа-серпантин от подножия (0) до вершины (цель «Царя горы» или максимум
// очков за игру). Все на одной тропе: больше очков — выше. После вопроса игроки по очереди поднимаются по тропе на
// заработанные очки (значок «+N»), обгон — вспышка. Близкие по очкам не налезают: встают «стопкой» по 3, остальные — «+N».
// Общая для ТВ и телефонов. Имя файла и QuizRope — со времён верёвок.
(function () {
  const CSS = `
.rope-stage { width: 100%; display: flex; flex-direction: column; gap: 6px; }
.rope-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; color: var(--muted); font-weight: 800; font-size: .9em; }
.rope-top b { color: var(--accent); }
.mt { position: relative; width: 100%; height: var(--h, 60vh); border-radius: 18px; overflow: hidden; background: var(--sky);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .08); isolation: isolate; }
.mt svg.land { position: absolute; inset: 0; width: 100%; height: 100%; }
.mt .sun { position: absolute; width: calc(var(--s) * 1.5); height: calc(var(--s) * 1.5); transform: translate(-50%, -50%); border-radius: 50%;
  background: var(--sun); box-shadow: 0 0 calc(var(--s) * .9) calc(var(--s) * .35) var(--sun); opacity: .95; }
.mt .sun.moon { background: transparent; box-shadow: inset calc(var(--s) * -.32) calc(var(--s) * -.12) 0 0 #f4f1d8; filter: drop-shadow(0 0 10px rgba(244, 241, 216, .5)); }
.mt .star { position: absolute; width: 3px; height: 3px; border-radius: 50%; background: #fff; animation: mt-tw 2.6s ease-in-out infinite alternate; }
@keyframes mt-tw { from { opacity: .25; } to { opacity: 1; } }
.mt .cloud { position: absolute; width: calc(var(--s) * 3.2); color: var(--cloud); animation: mt-cloud 46s ease-in-out infinite alternate; pointer-events: none; }
.mt .cloud svg { display: block; width: 100%; }
@keyframes mt-cloud { from { transform: translateX(-35%); } to { transform: translateX(35%); } }
.mt .pine { position: absolute; width: calc(var(--s) * .55); transform: translate(-50%, -100%); color: var(--pine); pointer-events: none; }
.mt .pine svg { display: block; width: 100%; }
.mt .mk { position: absolute; transform: translate(-50%, -100%); display: flex; flex-direction: column; align-items: center; z-index: 1; pointer-events: none; }
.mt .mk b { padding: 1px 6px; border-radius: 4px; background: linear-gradient(#e0ad73, #b07440); border: 2px solid #6b3f1f; color: #2b1608;
  font-weight: 800; font-size: calc(var(--s) * .3); line-height: 1.2; box-shadow: 0 2px 0 rgba(0, 0, 0, .3); }
.mt .mk::after { content: ""; width: 3px; height: calc(var(--s) * .32); background: #6b3f1f; border-radius: 0 0 2px 2px; }
.mt .peak { position: absolute; transform: translate(-8%, -100%); z-index: 1; display: flex; align-items: flex-start; gap: 3px; line-height: 1; pointer-events: none; }
.mt .peak svg { width: calc(var(--s) * .95); display: block; overflow: visible; }
.mt .peak .cloth { transform-origin: 6px 12px; animation: mt-wave 1.6s ease-in-out infinite alternate; }
@keyframes mt-wave { from { transform: skewY(-4deg) scaleX(.96); } to { transform: skewY(5deg) scaleX(1.02); } }
.mt .peak b { background: #ffd23f; color: #1b1b1b; border-radius: 99px; padding: 2px 8px; font-size: calc(var(--s) * .34); margin-top: 2px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, .35); }
.mt .fw { position: absolute; width: 0; height: 0; z-index: 5; pointer-events: none; }
.mt .fw i { position: absolute; left: -3px; top: -3px; width: 6px; height: 6px; border-radius: 50%; background: var(--fc); box-shadow: 0 0 8px var(--fc);
  opacity: 0; animation: mt-fw 1.3s var(--d) ease-out forwards; }
@keyframes mt-fw { 0% { opacity: 1; transform: rotate(var(--a)) translateY(0) scale(1); } 70% { opacity: 1; }
  100% { opacity: 0; transform: rotate(var(--a)) translateY(calc(var(--s) * -2.2)) scale(.4); } }
.climber { position: absolute; left: 0; top: 0; width: var(--s); height: var(--s); z-index: 2; will-change: transform; }
.climber::before { content: ""; position: absolute; left: 12%; right: 12%; bottom: -4%; height: 14%; border-radius: 50%; background: rgba(0, 0, 0, .35); filter: blur(2px); } /* тень на тропе */
.climber .face { display: block; }
.climber .face .ava, .climber .team-face { --s: inherit; width: var(--s); height: var(--s); font-size: calc(var(--s) * .42); }
.climber .face .ava { background: rgba(14, 19, 48, .55); background-image: linear-gradient(var(--cb), var(--cb)); } /* круг не прозрачный на светлом небе */
.climber.walk .face { animation: mt-step .28s ease-in-out infinite alternate; }
@keyframes mt-step { from { transform: translateY(0) rotate(-6deg); } to { transform: translateY(-16%) rotate(6deg); } }
.climber .puff { position: absolute; left: 50%; bottom: 0; width: 0; height: 0; pointer-events: none; }
.climber .puff i { position: absolute; width: calc(var(--s) * .28); height: calc(var(--s) * .28); margin: calc(var(--s) * -.14); border-radius: 50%;
  background: rgba(240, 225, 200, .75); animation: mt-puff .7s ease-out forwards; }
@keyframes mt-puff { from { opacity: .9; transform: translate(0, 0) scale(.4); } to { opacity: 0; transform: translate(var(--px), -6px) scale(1.4); } }
.climber.me { z-index: 4; } .climber.lead { z-index: 3; }
.climber.me .ava { box-shadow: 0 0 0 3px #fff, 0 0 16px 4px var(--c); }
.climber.hid { display: none; }
.climber .crown { position: absolute; left: 50%; bottom: 100%; transform: translate(-50%, 18%); font-size: calc(var(--s) * .55); line-height: 1; z-index: 1;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, .4)); }
.climber .gain { position: absolute; left: 50%; bottom: 100%; transform: translate(-50%, -2px); padding: 1px 7px; border-radius: 99px; font-weight: 800;
  font-size: calc(var(--s) * .32); white-space: nowrap; background: var(--good, #3ddc84); color: #0e1330; opacity: 0; transition: opacity .3s; z-index: 2;
  box-shadow: 0 2px 4px rgba(0, 0, 0, .3); }
.climber.lead .gain { bottom: auto; top: 0; left: auto; right: 78%; transform: translateY(-40%); } /* у лидера над головой корона — «+N» сбоку */
.climber .gain.minus { background: var(--bad, #ff6b6b); }
.climber.go .gain { opacity: 1; }
.climber.done.under .gain { opacity: 0; } /* в стопке «+N» видно только у верхнего */
.climber .tag { position: absolute; top: 50%; left: calc(100% + 4px); transform: translateY(-50%); white-space: nowrap; padding: 2px 8px; border-radius: 99px;
  background: rgba(14, 19, 48, .85); border: 2px solid var(--c, #8a90c8); color: #fff; font-weight: 800; font-size: calc(var(--s) * .3); line-height: 1.25;
  box-shadow: 0 2px 6px rgba(0, 0, 0, .3); }
.climber.left .tag { left: auto; right: calc(100% + 4px); }
.climber.below .tag { left: 50%; top: calc(100% + 3px); transform: translateX(-50%); }
.climber .tag b { color: var(--accent, #ffd23f); font-variant-numeric: tabular-nums; }
.climber.me .tag { background: var(--c); color: #0e1330; } .climber.me .tag b { color: #0e1330; }
.climber.notag .tag { display: none; }
.climber .more { position: absolute; right: -6px; bottom: -6px; min-width: 1.6em; padding: 0 4px; border-radius: 99px; background: #fff; color: #0e1330;
  font-weight: 800; font-size: calc(var(--s) * .28); line-height: 1.5; text-align: center; box-shadow: 0 1px 4px rgba(0, 0, 0, .4); z-index: 3; }
.climber.over .face { animation: mt-over .9s ease-out; }
.climber.over::after { content: "⚡ Обгон!"; position: absolute; left: 50%; top: 100%; transform: translateX(-50%); white-space: nowrap;
  background: #ffd23f; color: #1b1b1b; border-radius: 99px; padding: 1px 7px; font-weight: 800; font-size: calc(var(--s) * .28);
  animation: mt-pop 2.2s ease-out forwards; z-index: 3; }
@keyframes mt-over { 0% { transform: scale(1); filter: drop-shadow(0 0 0 #ffd23f); } 40% { transform: scale(1.35); filter: drop-shadow(0 0 14px #ffd23f); } 100% { transform: scale(1); } }
@keyframes mt-pop { 0% { opacity: 0; transform: translate(-50%, 6px) scale(.6); } 15% { opacity: 1; transform: translate(-50%, 0) scale(1.1); } 80% { opacity: 1; } 100% { opacity: 0; } }
.team-face { border-radius: 50%; background: var(--c); border: 3px solid #fff; display: block; box-sizing: border-box; }
/* телевизоры и «меньше движения»: без постоянных анимаций — слабому ТВ легче */
.mt.lite .cloud, .mt.lite .star, .mt.lite .peak .cloth, .mt.lite .climber.walk .face { animation: none; }
.mt.lite .sun { box-shadow: none; } .mt.lite .climber::before { filter: none; }
@media (prefers-reduced-motion: reduce) { .mt .cloud, .mt .star, .mt .peak .cloth, .climber.walk .face, .climber.over .face { animation: none; } }
`;
  // тропа: углы серпантина в процентах поля (x, y сверху вниз) — от подножия слева внизу к вершине; повороты скруглены
  const CORNERS = [[13, 95.5], [80, 88.3], [25, 78.4], [72, 68.5], [33, 58.6], [65, 49.6], [42, 40.6], [57, 32.5], [46, 24.4], [50, 17.2]];
  function smooth(p, r = 0.24) {
    const out = [p[0]];
    for (let i = 1; i < p.length - 1; i++) {
      const [a, b, c] = [p[i - 1], p[i], p[i + 1]];
      const s = [b[0] + (a[0] - b[0]) * r, b[1] + (a[1] - b[1]) * r], e = [b[0] + (c[0] - b[0]) * r, b[1] + (c[1] - b[1]) * r];
      for (let k = 0; k <= 8; k++) { // кривая Безье через угол
        const t = k / 8, u = 1 - t;
        out.push([u * u * s[0] + 2 * u * t * b[0] + t * t * e[0], u * u * s[1] + 2 * u * t * b[1] + t * t * e[1]]);
      }
    }
    out.push(p[p.length - 1]);
    return out;
  }
  const TRAIL = smooth(CORNERS);
  const PEAK = TRAIL[TRAIL.length - 1];
  const pts = (a) => a.map((p) => p.map((v) => +v.toFixed(2)).join(",")).join(" ");
  const MOUNT = [[-2, 100], [6, 89.2], [16, 76.6], [26, 63.1], [34, 51.4], [41, 38.8], [46.5, 25.3], [50, 15.4], [53.5, 23.5], [59, 37], [66, 49.6], [74, 62.2], [84, 75.7], [94, 89.2], [102, 100]];
  const SHADE = [[50, 15.4], [53.5, 23.5], [59, 37], [66, 49.6], [74, 62.2], [84, 75.7], [94, 89.2], [102, 100], [61, 100], [58, 80], [56.5, 62], [54, 44], [52.5, 30]];
  const ROCKS = ["M29 70 l3 -2.5 l2.5 1.5", "M38 56 l2.5 -2 l2 1.5", "M20 84 l3 -2 l2 1", "M62 74 l3 1.5 l2.5 -1", "M70 84 l3 1 l2 -1.5",
    "M57 52 l2 1.5 l2 -1", "M44 40 l2 -2 l1.5 1", "M86 92 l3 1 l2 -1"];
  // время суток по ходу игры: рассвет → день → закат → ночь (кто-то у вершины или финал)
  const SKIES = {
    dawn: { sky: "#1f2560, #5b4f9a 55%, #f0a27e", m1: "#6b67a8", m2: "#2a2a5e", d1: "#45427e", d2: "#1c1b45", far: "#4f4c8e", r1: "#433f80", r2: "#2a2960",
      snow: "#fff1ea", snow2: "#d9c8e6", path: "#ecca9c", edge: "#3a2c4a", pine: "#24304f", hill: "#202652", cloud: "rgba(255, 214, 205, .55)", sun: "#ffc98a", at: [18, 60] },
    day: { sky: "#2a58a6, #5f9bd6 55%, #b9dcf0", m1: "#7486c6", m2: "#33417f", d1: "#4b5a96", d2: "#222c5c", far: "#87a6d6", r1: "#5f7bbb", r2: "#3c5590",
      snow: "#ffffff", snow2: "#d6def5", path: "#f3d79c", edge: "#3b3550", pine: "#1d4b47", hill: "#24456b", cloud: "rgba(255, 255, 255, .8)", sun: "#fff3b0", at: [80, 13] },
    dusk: { sky: "#2a1f5e, #9a4c80 55%, #ff9a5c", m1: "#7c5ca0", m2: "#2c2052", d1: "#4c3672", d2: "#1b1336", far: "#6e4a8c", r1: "#523b7a", r2: "#2e2355",
      snow: "#ffd9df", snow2: "#c9a0c4", path: "#f0c48f", edge: "#33203f", pine: "#2a1f3f", hill: "#241a42", cloud: "rgba(255, 190, 170, .5)", sun: "#ff8a4c", at: [85, 58] },
    night: { sky: "#060a24, #141b4d 60%, #2c2766", m1: "#3e4486", m2: "#151a40", d1: "#272b5e", d2: "#0d1030", far: "#272d66", r1: "#20265a", r2: "#121640",
      snow: "#cfd7ff", snow2: "#8f99d6", path: "#cdbb8f", edge: "#191733", pine: "#0f1530", hill: "#0c1030", cloud: "rgba(200, 210, 255, .16)", moon: true, at: [80, 14] },
  };
  const skyOf = (p, night) => (night || p >= 0.88 ? "night" : p >= 0.66 ? "dusk" : p >= 0.33 ? "day" : "dawn");
  const LITE = /Web0S|webOS|SmartTV|SMART-TV|Tizen|NetCast|HbbTV|BRAVIA/i.test(navigator.userAgent);
  const PINES = [[3, 99, 1.1], [7, 97, .8], [10, 100, 1.25], [93, 98, 1], [97, 100, 1.3], [89, 100, .75], [20, 91, .6], [86, 86, .6]];
  const CLOUD = `<svg viewBox="0 -12 120 64"><path fill="currentColor" d="M22 50a20 20 0 0 1-2-40 26 26 0 0 1 48-6 20 20 0 0 1 34 12 17 17 0 0 1 0 34Z"/></svg>`;
  const PINE = `<svg viewBox="0 0 20 34"><path fill="currentColor" d="M10 0 17 11H13.5L19 21H14.5L20 29H0L5.5 21H1L6.5 11H3Z"/><rect x="8.6" y="28" width="2.8" height="6" fill="#3b2a20"/></svg>`;
  const FLAG = `<svg viewBox="0 0 40 50"><rect x="3" y="1" width="3" height="49" rx="1.5" fill="#efe8d6"/><circle cx="4.5" cy="2" r="2.4" fill="#ffd23f"/>
    <path class="cloth" fill="#ff5b5b" d="M6 4C14 1 20 8 29 5 33 4 36 3 38 4V21C34 20 31 22 27 23 19 25 14 18 6 21Z"/></svg>`;
  function scenery(sky) {
    const P = SKIES[sky];
    let rnd = 7; const R = () => (rnd = (rnd * 9301 + 49297) % 233280) / 233280; // звёзды всегда на тех же местах
    const stars = P.moon ? Array.from({ length: 26 }, () => `<span class="star" style="left:${(R() * 100).toFixed(1)}%;top:${(R() * 55).toFixed(1)}%;animation-delay:-${(R() * 3).toFixed(1)}s"></span>`).join("") : "";
    const style = ["m1", "m2", "d1", "d2", "far", "r1", "r2", "snow", "snow2", "path", "edge", "pine", "hill", "cloud"].map((k) => `--${k}:${P[k]}`).join(";")
      + `;--sky:linear-gradient(180deg, ${P.sky});--sun:${P.sun || "#fff"}`;
    const stop = (v) => `style="stop-color:var(--${v})"`;
    return {
      style,
      html: `${stars}<span class="sun ${P.moon ? "moon" : ""}" style="left:${P.at[0]}%;top:${P.at[1]}%"></span>
    <span class="cloud" style="left:4%;top:9%">${CLOUD}</span><span class="cloud" style="left:66%;top:22%;animation-duration:60s;width:calc(var(--s) * 2.4)">${CLOUD}</span>
    <span class="cloud" style="left:28%;top:36%;animation-duration:75s;width:calc(var(--s) * 1.8);opacity:.7">${CLOUD}</span>
    <svg class="land" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="mt-l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" ${stop("m1")}/><stop offset="1" ${stop("m2")}/></linearGradient>
        <linearGradient id="mt-d" x1="0" y1="0" x2="0" y2="1"><stop offset="0" ${stop("d1")}/><stop offset="1" ${stop("d2")}/></linearGradient>
        <linearGradient id="mt-r" x1="0" y1="0" x2="0" y2="1"><stop offset="0" ${stop("r1")}/><stop offset="1" ${stop("r2")}/></linearGradient></defs>
      <polygon points="-2,100 -2,58 8,50 15,55 24,44 33,52 42,40 50,47 58,36 68,48 78,38 88,47 96,40 102,44 102,100" style="fill:var(--far)" opacity=".6"/>
      <polygon points="-2,100 -2,70 9,62 19,68 28,58 36,66 64,64 74,56 84,64 93,58 102,64 102,100" fill="url(#mt-r)"/>
      <polygon points="${pts(MOUNT)}" fill="url(#mt-l)"/>
      <polygon points="${pts(SHADE)}" fill="url(#mt-d)"/>
      ${ROCKS.map((d) => `<path d="${d}" fill="none" stroke="#0b0d26" stroke-opacity=".35" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`).join("")}
      <polygon points="50,15.4 46.5,25.3 44.5,29.8 47,28.4 49,31.6 51.5,28 54,30.7 55.5,28 53.5,23.5" style="fill:var(--snow)"/>
      <polygon points="50,15.4 53.5,23.5 55.5,28 54,30.7 52.6,29 51.5,24" style="fill:var(--snow2)"/>
      <path d="M-2 100V93Q8 88 18 92T38 95Q46 96 50 100ZM60 100Q70 93 82 94T102 90V100Z" style="fill:var(--hill)"/>
      <polyline points="${pts(TRAIL)}" fill="none" style="stroke:var(--edge)" stroke-width="12" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" opacity=".55"/>
      <polyline points="${pts(TRAIL)}" fill="none" style="stroke:var(--path)" stroke-width="6" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" opacity=".9"/>
      <polyline points="${pts(TRAIL)}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.5" stroke-dasharray="5 7" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
    </svg>${PINES.map(([x, y, k]) => `<span class="pine" style="left:${x}%;top:${y}%;width:calc(var(--s) * ${(0.55 * k).toFixed(2)})">${PINE}</span>`).join("")}`,
    };
  }
  let styled = false;
  // когда начался подъём (по ключу вопроса): перерисовка экрана посреди подъёма продолжает его с того же места,
  // а давно закончившийся — сразу на местах
  const started = new Map();
  const finished = (key) => started.has(key) && performance.now() - started.get(key) > 8000;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (n) => Number(n).toLocaleString("ru-RU");
  const clamp = (v) => Math.max(0, Math.min(1, v));

  // низ тропы растянут: в начале игры у всех мало очков — так они не толпятся у подножия, а верх короче.
  // Отметки высоты ставятся так же, поэтому высота честная (10 — у камня «10»)
  const bend = (t) => 1 - Math.pow(1 - clamp(t), 1.7);
  // точка тропы на доле пути t (0 — подножие, 1 — вершина) в процентах поля; длина считается с учётом пропорций поля
  function trail(aspect) {
    const seg = [];
    let total = 0;
    for (let i = 1; i < TRAIL.length; i++) {
      const [x0, y0] = TRAIL[i - 1], [x1, y1] = TRAIL[i];
      const len = Math.hypot((x1 - x0) * aspect, y1 - y0);
      seg.push({ x0, y0, x1, y1, len, start: total });
      total += len;
    }
    const at = (t) => {
      const d = bend(t) * total;
      const s = seg.find((g) => d <= g.start + g.len) || seg[seg.length - 1];
      const k = s.len ? (d - s.start) / s.len : 0;
      return [s.x0 + (s.x1 - s.x0) * k, s.y0 + (s.y1 - s.y0) * k];
    };
    return { at, total };
  }

  // rows: [{name, score, last, prev, color, face (HTML аватарки), me}] — по местам; top — сколько очков у вершины;
  // key — один подъём на вопрос (по нему не повторяем); opts: {height, compact, race, progress (0…1 — доля игры), night (финал)}
  function html(rows, top, key, opts = {}) {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    top = Math.max(1, top || 1);
    const order = rows.map((r, i) => i).sort((a, b) => (rows[a].last - rows[b].last) || (rows[a].score - rows[b].score)); // большой рывок — в конце
    const turn = new Map(order.map((idx, k) => [idx, k]));
    const again = finished(key);
    const g = trail(opts.compact ? 1.4 : 2.4);
    const marks = [1, 2, 3, 4].map((k) => {
      const [x, y] = g.at(k / 5);
      return `<span class="mk" data-t="${k / 5}" style="left:${x}%;top:${y}%"><b>${num(Math.round(top * k / 5))}</b></span>`;
    }).join("");
    const lead = rows.length && rows[0].score > 0;
    const climbers = rows.map((r, i) => {
      const from = clamp((r.score - (r.last || 0)) / top), to = clamp(r.score / top);
      const gain = r.last ? `<span class="gain ${r.last < 0 ? "minus" : ""}">${r.last > 0 ? "+" : "−"}${num(Math.abs(r.last))}</span>` : "";
      const was = r.score - (r.last || 0); // обогнал: кто-то был выше, а теперь ниже
      const over = r.last > 0 && rows.some((o) => o !== r && o.score - (o.last || 0) > was && o.score < r.score) ? 1 : 0;
      const crown = i === 0 && lead ? `<span class="crown">${to >= 1 ? "🏆" : "👑"}</span>` : "";
      return `<div class="climber ${r.me ? "me" : ""} ${i === 0 && lead ? "lead" : ""} ${again ? "go done" : ""}" style="--c:${esc(r.color || "#8a90c8")}"
        data-from="${from}" data-to="${to}" data-turn="${turn.get(i)}" data-place="${i}" data-score="${r.score}" data-over="${over}">
        ${crown}${gain}<span class="face">${r.face}</span><span class="tag"><span>${esc(r.me && opts.compact ? "Ты" : r.name)}</span> · <b>${num(again ? r.score : r.score - (r.last || 0))}</b></span></div>`;
    }).join("");
    const n = rows.length;
    const sky = skyOf(Math.max(opts.progress || 0, rows.length ? clamp(rows[0].score / top) : 0), opts.night), view = scenery(sky);
    const size = opts.compact ? (n > 8 ? 34 : n > 4 ? 40 : 46) : (n > 20 ? 34 : n > 12 ? 40 : 48); // аватарка, px
    return `<div class="rope-stage ${opts.compact ? "compact" : ""}" data-key="${esc(key)}" style="--h:${opts.height || "60vh"};--s:${size}px">
      <div class="rope-top"><span>⛰️ ${opts.race ? "Кто первым на вершину — царь горы" : "Вершина"}</span><b>${num(top)}</b></div>
      <div class="mt ${sky} ${LITE ? "lite" : ""}" style="${view.style}">${view.html}${marks}
        <span class="peak" style="left:${PEAK[0]}%;top:${PEAK[1]}%">${FLAG}<b>${num(top)}</b></span>${climbers}</div></div>`;
  }

  // кто где стоит: близкие по тропе — в одну кучку; в кучке видно до 3 (стопкой), остальные — значок «+N»
  function arrange(stage) {
    const box = stage.querySelector(".mt"), W = box.clientWidth, H = box.clientHeight;
    if (!W || !H) return null;
    const S = parseFloat(getComputedStyle(stage).getPropertyValue("--s")) || 44;
    const g = trail(W / H), lenPx = g.total * H / 100; // длина тропы в пикселях
    const items = [...stage.querySelectorAll(".climber")].map((el) => ({ el, t: +el.dataset.to, place: +el.dataset.place, me: el.classList.contains("me") }));
    const sorted = [...items].sort((a, b) => b.t - a.t || a.place - b.place);
    const groups = [];
    for (const it of sorted) {
      const last = groups[groups.length - 1];
      if (last && (bend(last[0].t) - bend(it.t)) * lenPx < S * 1.1) last.push(it); else groups.push([it]);
    }
    for (const grp of groups) {
      grp.sort((a, b) => b.me - a.me || a.place - b.place); // «я» — всегда на виду
      const vis = grp.slice(0, 3), rest = grp.length - vis.length;
      vis.sort((a, b) => a.place - b.place);
      vis.forEach((it, k) => { it.dx = k * S * 0.42; it.dy = -k * S * 0.62; it.el.classList.remove("hid"); it.el.classList.toggle("under", k < vis.length - 1); }); // стопка вверх-вправо
      grp.slice(3).forEach((it) => it.el.classList.add("hid"));
      grp.forEach((it) => { const m = it.el.querySelector(".more"); if (m) m.remove(); });
      if (rest > 0) vis[vis.length - 1].el.insertAdjacentHTML("beforeend", `<span class="more">+${rest}</span>`);
    }
    stage.querySelectorAll(".mk").forEach((m) => { const [x, y] = g.at(+m.dataset.t); m.style.left = x + "%"; m.style.top = y + "%"; });
    // подписи «имя · очки»: сначала своя и лидеры; не влезает ни справа, ни слева — без подписи (её видно в «Вся таблица»)
    const boxes = [], hit = (r, own) => r[0] < -5 || r[2] > W + 5 || r[3] > H + 5 || boxes.some((b) => b.it !== own && r[0] < b[2] && r[2] > b[0] && r[1] < b[3] && r[3] > b[1]);
    const vis = items.filter((it) => !it.el.classList.contains("hid"));
    for (const it of vis) {
      const [x, y] = g.at(it.t);
      it.px = x * W / 100 - S / 2 + (it.dx || 0); it.py = y * H / 100 - S * 0.9 + (it.dy || 0);
      const box = [it.px, it.py, it.px + S, it.py + S]; box.it = it; boxes.push(box);
      if (it.el.querySelector(".gain") && !it.el.classList.contains("under") && !it.el.classList.contains("lead")) // «+N» над головой
        boxes.push([it.px + S * .1, it.py - S * .42, it.px + S * .9, it.py]);
    }
    const pad = 5;
    for (const it of [...vis].sort((a, b) => b.me - a.me || a.place - b.place)) {
      const tag = it.el.querySelector(".tag"), tw = tag.offsetWidth || S * 2, th = tag.offsetHeight || S * .45;
      const ty = it.py + S / 2 - th / 2, bx = it.px + S / 2 - tw / 2;
      const spots = {
        right: [it.px + S + 4, ty, it.px + S + 4 + tw, ty + th],
        left: [it.px - 4 - tw, ty, it.px - 4, ty + th],
        below: [bx, it.py + S + 3, bx + tw, it.py + S + 3 + th],
      };
      const order = it.px > W * 0.6 ? ["left", "right", "below"] : ["right", "left", "below"];
      const side = order.find((k) => { const r = spots[k]; return !hit([r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad], it); });
      it.side = side || null;
      if (side) boxes.push(spots[side]);
      it.el.classList.toggle("notag", !side && !it.me);
    }
    return { g, W, H, S, items };
  }

  function place(el, lay, t, withOffset) {
    const it = lay.items.find((x) => x.el === el);
    const [x, y] = lay.g.at(t);
    const px = x * lay.W / 100, py = y * lay.H / 100;
    const dx = withOffset ? it.dx || 0 : 0, dy = withOffset ? it.dy || 0 : 0;
    el.style.transform = `translate(${px - lay.S / 2 + dx}px, ${py - lay.S * 0.9 + dy}px)`; // стоит на тропе
    const side = withOffset && it.side ? it.side : x > 62 ? "left" : "right";
    el.classList.toggle("left", side === "left"); el.classList.toggle("below", side === "below");
  }

  // по очереди: каждый поднимается по тропе на свои очки; уже показанный подъём — сразу на месте
  function climb(root) {
    const stage = root && root.querySelector(".rope-stage");
    if (!stage) return;
    const lay = arrange(stage);
    if (!lay) return;
    const key = stage.dataset.key;
    const finish = (el) => {
      place(el, lay, +el.dataset.to, true);
      el.classList.add("go", "done");
      el.querySelector(".tag b").textContent = num(el.dataset.score);
    };
    stage._lay = lay;
    if (finished(key) || matchMedia("(prefers-reduced-motion: reduce)").matches) { lay.items.forEach((it) => finish(it.el)); return; }
    if (!started.has(key)) started.set(key, performance.now());
    const start = started.get(key);
    // много игроков — лезут чаще и быстрее: весь подъём укладывается в ~2,5 с (таблица на экране 4 с)
    const n = lay.items.length, step = Math.min(600, 1600 / n), dur = n > 12 ? 550 : n > 6 ? 750 : 900, wait = n > 12 ? 250 : 500;
    lay.items.forEach((it) => {
      const el = it.el, a = +el.dataset.from, b = +el.dataset.to;
      const t0 = start + wait + Number(el.dataset.turn) * step, now = performance.now();
      if (now >= t0 + dur) { finish(el); return; } // уже долез до перерисовки
      place(el, lay, a, false);
      const frame = (now) => {
        if (!el.isConnected) return;
        const k = Math.max(0, Math.min(1, (now - t0) / dur)), e = 1 - Math.pow(1 - k, 3);
        place(el, lay, a + (b - a) * e, false);
        if (k < 1) return requestAnimationFrame(frame);
        finish(el);
        el.classList.remove("walk");
        if (b > a) puff(el);
        if (el.dataset.over === "1") el.classList.add("over");
        if (b >= 1 && a < 1) fireworks(stage); // дошёл до вершины — салют
      };
      setTimeout(() => { if (el.isConnected) { el.classList.add("go"); if (b > a) el.classList.add("walk"); requestAnimationFrame(frame); } }, Math.max(0, t0 - now));
    });
  }

  // пыль из-под ног, когда дошёл
  function puff(el) {
    if (LITE) return;
    const p = document.createElement("span");
    p.className = "puff";
    p.innerHTML = ["-14px", "0px", "14px"].map((x) => `<i style="--px:${x}"></i>`).join("");
    el.appendChild(p);
    setTimeout(() => p.remove(), 800);
  }
  // салют над вершиной: три вспышки разного цвета (на ТВ — одна)
  function fireworks(stage) {
    const mt = stage.querySelector(".mt");
    if (!mt || mt.querySelector(".fw")) return;
    const colors = ["#ffd23f", "#ff6fb5", "#5ac8fa"], bursts = LITE ? 1 : 3;
    let html = "";
    for (let b = 0; b < bursts; b++) {
      const x = PEAK[0] + (b - 1) * 9, y = PEAK[1] + 4 - (b % 2) * 6;
      html += `<span class="fw" style="left:${x}%;top:${y}%">${Array.from({ length: 14 }, (_, i) =>
        `<i style="--a:${i * 360 / 14}deg;--d:${b * 0.35}s;--fc:${colors[b % 3]}"></i>`).join("")}</span>`;
    }
    mt.insertAdjacentHTML("beforeend", html);
    setTimeout(() => mt.querySelectorAll(".fw").forEach((f) => f.remove()), 2600);
  }

  // поворот экрана или новый размер окна — расставить заново, без подъёма
  addEventListener("resize", () => {
    document.querySelectorAll(".rope-stage").forEach((stage) => {
      if (!stage._lay) return;
      const lay = arrange(stage);
      if (!lay) return;
      stage._lay = lay;
      lay.items.forEach((it) => { if (it.el.classList.contains("done")) place(it.el, lay, +it.el.dataset.to, true); });
    });
  });

  window.QuizRope = { html, climb };
})();
