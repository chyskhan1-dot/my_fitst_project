// Гора вместо таблицы лидеров: одна общая тропа-серпантин от подножия (0) до вершины (цель «Царя горы» или максимум
// очков за игру). Все на одной тропе: больше очков — выше. После вопроса игроки по очереди поднимаются по тропе на
// заработанные очки (значок «+N»), обгон — вспышка. Близкие по очкам не налезают: встают «стопкой» по 3, остальные — «+N».
// Общая для ТВ и телефонов. Имя файла и QuizRope — со времён верёвок.
(function () {
  const CSS = `
.rope-stage { width: 100%; display: flex; flex-direction: column; gap: 6px; }
.rope-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; color: var(--muted); font-weight: 800; font-size: .9em; }
.rope-top b { color: var(--accent); }
.mt { position: relative; width: 100%; height: var(--h, 60vh); border-radius: 18px; overflow: hidden;
  background: linear-gradient(180deg, #1b2668 0%, #3a4ba3 55%, #8d78bd 100%); }
.mt svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.mt .cloud { position: absolute; width: 22%; height: 9%; border-radius: 50%; background: rgba(255, 255, 255, .22); filter: blur(6px);
  animation: mt-cloud 40s linear infinite; pointer-events: none; }
.mt .cloud::after { content: ""; position: absolute; left: 25%; top: -45%; width: 50%; height: 120%; border-radius: 50%; background: inherit; }
@keyframes mt-cloud { from { transform: translateX(-30%); } 50% { transform: translateX(30%); } to { transform: translateX(-30%); } }
.mt .mk { position: absolute; transform: translate(-50%, -50%); display: grid; place-items: center; min-width: 1.9em; height: 1.9em; padding: 0 .3em;
  border-radius: 40% 45% 35% 40%; background: linear-gradient(#9aa0b8, #5d6280); border: 2px solid rgba(255, 255, 255, .35);
  color: #fff; font-weight: 800; font-size: calc(var(--s) * .3); text-shadow: 0 1px 2px rgba(0, 0, 0, .5); z-index: 1; }
.mt .peak { position: absolute; transform: translate(-12%, -100%); z-index: 1; display: flex; align-items: flex-end; gap: 2px; line-height: 1; }
.mt .peak i { font-style: normal; font-size: calc(var(--s) * .8); }
.mt .peak b { background: #ffd23f; color: #1b1b1b; border-radius: 99px; padding: 2px 8px; font-size: calc(var(--s) * .34); margin-bottom: 4px; }
.climber { position: absolute; left: 0; top: 0; width: var(--s); height: var(--s); z-index: 2; will-change: transform; }
.climber .face .ava, .climber .team-face { --s: inherit; width: var(--s); height: var(--s); font-size: calc(var(--s) * .42); }
.climber.me { z-index: 4; } .climber.lead { z-index: 3; }
.climber.me .ava { box-shadow: 0 0 0 3px #fff, 0 0 16px 4px var(--c); }
.climber.hid { display: none; }
.climber .crown { position: absolute; left: 50%; bottom: 100%; transform: translate(-50%, 18%); font-size: calc(var(--s) * .55); line-height: 1; z-index: 1; }
.climber .gain { position: absolute; left: 50%; bottom: 100%; transform: translate(-50%, -2px); padding: 1px 7px; border-radius: 99px; font-weight: 800;
  font-size: calc(var(--s) * .32); white-space: nowrap; background: var(--good, #3ddc84); color: #0e1330; opacity: 0; transition: opacity .3s; z-index: 2; }
.climber.lead .gain { bottom: calc(100% + var(--s) * .45); }
.climber .gain.minus { background: var(--bad, #ff6b6b); }
.climber.go .gain { opacity: 1; }
.climber.done.under .gain { opacity: 0; } /* в стопке «+N» видно только у верхнего */
.climber .tag { position: absolute; top: 50%; left: calc(100% + 4px); transform: translateY(-50%); white-space: nowrap; padding: 2px 8px; border-radius: 99px;
  background: rgba(14, 19, 48, .78); border: 2px solid var(--c, #8a90c8); color: #fff; font-weight: 800; font-size: calc(var(--s) * .3); line-height: 1.25; }
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
@media (prefers-reduced-motion: reduce) { .mt .cloud, .climber.over .face { animation: none; } }
`;
  // тропа: точки в процентах поля (x, y сверху вниз) — от подножия слева внизу зигзагом к вершине
  const TRAIL = [[13, 95.5], [80, 88.3], [25, 78.4], [72, 68.5], [33, 58.6], [65, 49.6], [42, 40.6], [57, 32.5], [46, 24.4], [50, 17.2]];
  const PEAK = TRAIL[TRAIL.length - 1];
  const pts = (a) => a.map((p) => p.join(",")).join(" ");
  const MOUNT = [[-2, 100], [6, 89.2], [16, 76.6], [26, 63.1], [34, 51.4], [41, 38.8], [46.5, 25.3], [50, 15.4], [53.5, 23.5], [59, 37], [66, 49.6], [74, 62.2], [84, 75.7], [94, 89.2], [102, 100]];
  const SVG = `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="mt-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a5fa6"/><stop offset="1" stop-color="#20235a"/></linearGradient>
      <linearGradient id="mt-b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b4290"/><stop offset="1" stop-color="#262b66"/></linearGradient></defs>
    <polygon points="-2,100 -2,62 10,50 20,58 31,40 38,48 46,38 54,47 63,34 74,50 84,40 93,52 102,46 102,100" fill="url(#mt-b)" opacity=".7"/>
    <polygon points="${pts(MOUNT)}" fill="url(#mt-g)"/>
    <polygon points="50,15.4 46.5,25.3 44.5,29.8 47,28.4 49,31.6 51.5,28 54,30.7 55.5,28 53.5,23.5" fill="#f2f4ff"/>
    <polyline points="${pts(TRAIL)}" fill="none" stroke="#2a2347" stroke-width="9" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" opacity=".55"/>
    <polyline points="${pts(TRAIL)}" fill="none" stroke="#f3d79c" stroke-width="3" stroke-dasharray="7 6" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
  </svg><span class="cloud" style="left:6%;top:10%"></span><span class="cloud" style="left:70%;top:18%;animation-duration:55s"></span><span class="cloud" style="left:30%;top:40%;opacity:.6;animation-duration:70s"></span>`;
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
  // key — один подъём на вопрос (по нему не повторяем); opts: {height, compact, race}
  function html(rows, top, key, opts = {}) {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    top = Math.max(1, top || 1);
    const order = rows.map((r, i) => i).sort((a, b) => (rows[a].last - rows[b].last) || (rows[a].score - rows[b].score)); // большой рывок — в конце
    const turn = new Map(order.map((idx, k) => [idx, k]));
    const again = finished(key);
    const g = trail(opts.compact ? 1.4 : 2.4);
    const marks = [1, 2, 3, 4].map((k) => {
      const [x, y] = g.at(k / 5);
      return `<span class="mk" data-t="${k / 5}" style="left:${x}%;top:${y}%">${num(Math.round(top * k / 5))}</span>`;
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
    const size = opts.compact ? (n > 8 ? 34 : n > 4 ? 40 : 46) : (n > 20 ? 34 : n > 12 ? 40 : 48); // аватарка, px
    return `<div class="rope-stage ${opts.compact ? "compact" : ""}" data-key="${esc(key)}" style="--h:${opts.height || "60vh"};--s:${size}px">
      <div class="rope-top"><span>⛰️ ${opts.race ? "Кто первым на вершину — царь горы" : "Вершина"}</span><b>${num(top)}</b></div>
      <div class="mt">${SVG}${marks}<span class="peak" style="left:${PEAK[0]}%;top:${PEAK[1]}%"><i>🚩</i><b>${num(top)}</b></span>${climbers}</div></div>`;
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
        if (el.dataset.over === "1") el.classList.add("over");
      };
      setTimeout(() => { if (el.isConnected) { el.classList.add("go"); requestAnimationFrame(frame); } }, Math.max(0, t0 - now));
    });
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
