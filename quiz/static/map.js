// Глобус для вопросов «Где на карте?» — один и тот же у ведущего, на телефоне и в редакторе.
// Рисуется в браузере на canvas из той же картинки карты (равнопромежуточная проекция, tools/make_map.py):
// ортографическая проекция — шар, который крутится пальцем. Сервер только отдаёт картинку, считать ему нечего.
// Крутить — пальцем или мышью; увеличить — колесом, щипком или кнопками +/−; короткое касание — поставить точку.
(function () {
  // сначала лёгкая карта (~150 КБ, быстро грузится даже по мобильному интернету), подробная — только при увеличении
  const SRC = "/media/map/world-2k.jpg", SRC_FULL = "/media/map/world.jpg";
  const MAX_ZOOM = 12, FIT = 0.92; // FIT — какую долю меньшей стороны занимает шар без увеличения
  const D = Math.PI / 180;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const round4 = (v) => Math.round(v * 1e4) / 1e4;

  function distance(a, b) {
    const h = Math.sin((b[0] - a[0]) * D / 2) ** 2 + Math.cos(a[0] * D) * Math.cos(b[0] * D) * Math.sin((b[1] - a[1]) * D / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  const km = (n) => (n < 1 ? "меньше 1 км" : `${Math.round(n).toLocaleString("ru-RU")} км`);

  // текстура карты: пиксели картинки, общие для всех глобусов на странице
  const textures = {};
  function texture(src) {
    if (!textures[src]) {
      textures[src] = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          const c = document.createElement("canvas");
          c.width = img.naturalWidth; c.height = img.naturalHeight;
          const g = c.getContext("2d"); g.drawImage(img, 0, 0);
          resolve({ w: c.width, h: c.height, px: new Uint32Array(g.getImageData(0, 0, c.width, c.height).data.buffer) });
        };
        img.onerror = () => { delete textures[src]; reject(new Error("карта не загрузилась")); };
        img.src = src;
      });
    }
    return textures[src];
  }

  const CSS = `
.qmap { position: relative; overflow: hidden; touch-action: none; user-select: none; -webkit-user-select: none;
  background: radial-gradient(circle at 50% 50%, #1d2a5c 0%, #0b1030 70%); border-radius: 16px; cursor: grab; }
.qmap.pick { cursor: crosshair; }
.qmap canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.qmap-wait { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; font: 700 15px system-ui, sans-serif; pointer-events: none; }
.qmap-pins { position: absolute; inset: 0; pointer-events: none; }
.qpin { position: absolute; transform: translate(-50%, -100%); display: flex; flex-direction: column; align-items: center; pointer-events: none; }
.qpin span { display: grid; place-items: center; min-width: 30px; height: 30px; padding: 0 4px; border-radius: 50% 50% 50% 6px;
  transform: rotate(-45deg); background: #b9a6ff; border: 2px solid #1b1f3a; box-shadow: 0 3px 8px rgba(0,0,0,.35); }
.qpin span i { transform: rotate(45deg); font-style: normal; font-size: 16px; line-height: 1; color: #1b1f3a; font-weight: 800; }
.qpin small { margin-top: 3px; padding: 1px 6px; border-radius: 8px; background: rgba(14,19,48,.82); color: #fff; font: 700 12px/1.3 system-ui, sans-serif; white-space: nowrap; }
.qpin.right span { background: #3ddc84; }
.qpin.me span { background: #ff6b9a; }
.qpin.best span { background: #ffd23f; }
.qmap-zoom { position: absolute; right: 8px; bottom: 8px; display: flex; flex-direction: column; gap: 6px; }
.qmap-zoom button { width: 40px; height: 40px; border-radius: 12px; border: 0; background: rgba(14,19,48,.78); color: #fff;
  font: 800 22px/1 system-ui, sans-serif; cursor: pointer; }
`;
  let styled = false;

  function create(box, opts = {}) {
    if (!styled) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    box.classList.add("qmap");
    box.classList.toggle("pick", !!opts.onPick);
    box.innerHTML = `<canvas></canvas><div class="qmap-wait">Карта загружается…</div><div class="qmap-pins"></div>
      <div class="qmap-zoom"><button type="button" data-qz="1" aria-label="Приблизить">+</button><button type="button" data-qz="-1" aria-label="Отдалить">−</button></div>`;
    const canvas = box.querySelector("canvas"), g = canvas.getContext("2d"), pinsEl = box.querySelector(".qmap-pins");
    let tex = null, full = false, pins = [], lines = [];
    let lat0 = 20, lon0 = 15, z = 1, fast = false, queued = false; // центр вида, увеличение, черновая отрисовка при движении
    texture(SRC).then((t) => { tex = tex || t; const w = box.querySelector(".qmap-wait"); if (w) w.remove(); draw(); }).catch(() => {});

    const geo = () => {
      const w = box.clientWidth, h = box.clientHeight;
      return { w, h, cx: w / 2, cy: h / 2, r: (Math.min(w, h) / 2) * FIT * z };
    };
    // точка [широта, долгота] → экран (в CSS-пикселях); front — на видимой стороне шара
    function project(p, G = geo()) {
      const f = p[0] * D, l = (p[1] - lon0) * D, f0 = lat0 * D;
      const cosc = Math.sin(f0) * Math.sin(f) + Math.cos(f0) * Math.cos(f) * Math.cos(l);
      return { x: G.cx + G.r * Math.cos(f) * Math.sin(l), y: G.cy - G.r * (Math.cos(f0) * Math.sin(f) - Math.sin(f0) * Math.cos(f) * Math.cos(l)), front: cosc > 0 };
    }
    // экран → [широта, долгота], или null мимо шара
    function unproject(px, py, G = geo()) {
      const x = (px - G.cx) / G.r, y = (G.cy - py) / G.r, rr = x * x + y * y;
      if (rr > 1) return null;
      const zz = Math.sqrt(1 - rr), f0 = lat0 * D;
      const lat = Math.asin(zz * Math.sin(f0) + y * Math.cos(f0)) / D;
      let lon = lon0 + Math.atan2(x, zz * Math.cos(f0) - y * Math.sin(f0)) / D;
      lon = ((lon + 540) % 360) - 180;
      return [round4(lat), round4(lon)];
    }

    function draw() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(render);
    }
    function render() {
      queued = false;
      const G = geo();
      if (!G.w || !G.h) return;
      const k = Math.min(window.devicePixelRatio || 1, 2) * (fast ? 0.5 : 1); // при движении — вдвое грубее, зато плавно
      const W = Math.max(1, Math.round(G.w * k)), H = Math.max(1, Math.round(G.h * k));
      if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
      g.clearRect(0, 0, W, H);
      const cx = G.cx * k, cy = G.cy * k, R = G.r * k;
      if (tex) {
        const img = g.createImageData(W, H), out = new Uint32Array(img.data.buffer);
        const f0 = lat0 * D, s0 = Math.sin(f0), c0 = Math.cos(f0), l0 = lon0 * D;
        const TW = tex.w, TH = tex.h, px = tex.px, tu = TW / (2 * Math.PI), tv = TH / Math.PI;
        const y0 = Math.max(0, Math.floor(cy - R)), y1 = Math.min(H - 1, Math.ceil(cy + R));
        for (let py = y0; py <= y1; py++) {
          const y = (cy - py - 0.5) / R, yy = 1 - y * y;
          if (yy <= 0) continue;
          const half = Math.sqrt(yy) * R;
          const x0 = Math.max(0, Math.floor(cx - half)), x1 = Math.min(W - 1, Math.ceil(cx + half));
          const ys0 = y * s0, yc0 = y * c0;
          let i = py * W + x0;
          for (let pxl = x0; pxl <= x1; pxl++, i++) {
            const x = (pxl + 0.5 - cx) / R, q = yy - x * x;
            if (q <= 0) continue;
            const zz = Math.sqrt(q);
            const lat = Math.asin(zz * s0 + yc0);
            let u = ((l0 + Math.atan2(x, zz * c0 - ys0) + Math.PI) * tu) | 0;
            u %= TW; if (u < 0) u += TW;
            let v = ((Math.PI / 2 - lat) * tv) | 0;
            if (v >= TH) v = TH - 1;
            out[i] = px[v * TW + u];
          }
        }
        g.putImageData(img, 0, 0);
      } else {
        g.fillStyle = "#5f9ccc"; g.beginPath(); g.arc(cx, cy, R, 0, 2 * Math.PI); g.fill();
      }
      // объём: тень к краю шара и светлый ободок атмосферы
      const shade = g.createRadialGradient(cx - R * 0.3, cy - R * 0.35, R * 0.1, cx, cy, R);
      shade.addColorStop(0, "rgba(255,255,255,0.10)"); shade.addColorStop(0.65, "rgba(0,0,20,0)"); shade.addColorStop(1, "rgba(0,0,30,0.45)");
      g.fillStyle = shade; g.beginPath(); g.arc(cx, cy, R, 0, 2 * Math.PI); g.fill();
      g.strokeStyle = "rgba(160,200,255,0.55)"; g.lineWidth = 2 * k; g.beginPath(); g.arc(cx, cy, R + k, 0, 2 * Math.PI); g.stroke();
      // линии «точка игрока → правильный ответ» — по дуге большого круга
      g.setLineDash([6 * k, 5 * k]); g.strokeStyle = "rgba(255,255,255,0.9)"; g.lineWidth = 2.5 * k;
      for (const [a, b] of lines) {
        const pts = arc(a, b);
        g.beginPath();
        let on = false;
        for (const p of pts) {
          const s = project(p, G);
          if (!s.front) { on = false; continue; }
          if (on) g.lineTo(s.x * k, s.y * k); else g.moveTo(s.x * k, s.y * k);
          on = true;
        }
        g.stroke();
      }
      g.setLineDash([]);
      // метки — HTML поверх шара; на обратной стороне прячем
      pinsEl.innerHTML = pins.map((p) => {
        const s = project(p.point, G);
        if (!s.front) return "";
        return `<div class="qpin ${p.kind || ""}" style="left:${s.x}px;top:${s.y}px"><span><i>${window.QuizEmoji ? QuizEmoji.html(p.icon || "") : esc(p.icon || "")}</i></span>${p.label ? `<small>${esc(p.label)}</small>` : ""}</div>`;
      }).join("");
      // увеличили — подгружаем подробную карту
      if (!full && G.r * 2 * k > 1800) {
        full = true;
        texture(SRC_FULL).then((t) => { tex = t; draw(); }).catch(() => {});
      }
    }
    // точки дуги большого круга между a и b
    function arc(a, b) {
      const v = (p) => [Math.cos(p[0] * D) * Math.cos(p[1] * D), Math.cos(p[0] * D) * Math.sin(p[1] * D), Math.sin(p[0] * D)];
      const A = v(a), B = v(b), w = Math.acos(Math.max(-1, Math.min(1, A[0] * B[0] + A[1] * B[1] + A[2] * B[2])));
      if (w < 1e-6) return [a, b];
      const n = Math.max(2, Math.ceil(w / D / 2)), out = [];
      for (let i = 0; i <= n; i++) {
        const t = i / n, sa = Math.sin((1 - t) * w) / Math.sin(w), sb = Math.sin(t * w) / Math.sin(w);
        const x = sa * A[0] + sb * B[0], y = sa * A[1] + sb * B[1], zz = sa * A[2] + sb * B[2];
        out.push([Math.atan2(zz, Math.hypot(x, y)) / D, Math.atan2(y, x) / D]);
      }
      return out;
    }

    function zoomBy(f) { z = Math.max(1, Math.min(MAX_ZOOM, z * f)); fitTo = null; draw(); }
    // показать точки: повернуть к их середине и увеличить, чтобы поместились
    let fitTo = null;
    function view(points, maxZoom = 6) {
      fitTo = [points, maxZoom];
      if (!points.length) { lat0 = 20; lon0 = 15; z = 1; return draw(); }
      let x = 0, y = 0, q = 0;
      for (const p of points) { x += Math.cos(p[0] * D) * Math.cos(p[1] * D); y += Math.cos(p[0] * D) * Math.sin(p[1] * D); q += Math.sin(p[0] * D); }
      lat0 = Math.atan2(q, Math.hypot(x, y)) / D; lon0 = Math.atan2(y, x) / D;
      if (!isFinite(lat0) || !isFinite(lon0)) { lat0 = points[0][0]; lon0 = points[0][1]; }
      const far = Math.max(...points.map((p) => distance(p, [lat0, lon0]) / 6371)); // угол до самой дальней точки
      z = far >= Math.PI / 2 ? 1 : Math.max(1, Math.min(maxZoom, 0.6 / FIT / Math.max(Math.sin(far), 0.02)));
      draw();
    }
    function setPins(list) { pins = list; draw(); }
    function setLines(pairs) { lines = pairs; draw(); }

    // жесты: один палец — крутить, два — увеличивать, короткое касание — поставить точку
    const ptrs = new Map();
    let drag = null, pinch = null;
    box.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".qmap-zoom")) return;
      box.setPointerCapture(e.pointerId);
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (ptrs.size === 1) drag = { x: e.clientX, y: e.clientY, moved: false };
      else if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()];
        pinch = Math.hypot(a.x - b.x, a.y - b.y);
        if (drag) drag.moved = true;
      }
    });
    box.addEventListener("pointermove", (e) => {
      if (!ptrs.has(e.pointerId)) return;
      const prev = ptrs.get(e.pointerId);
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (ptrs.size >= 2 && pinch) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        fast = true; zoomBy(d / (pinch || d)); pinch = d;
      } else if (drag) {
        if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 6) drag.moved = true;
        if (drag.moved) {
          const r = geo().r;
          lon0 -= (e.clientX - prev.x) / r / D / Math.max(0.2, Math.cos(lat0 * D));
          lat0 = Math.max(-85, Math.min(85, lat0 + (e.clientY - prev.y) / r / D));
          lon0 = ((lon0 + 540) % 360) - 180;
          fast = true; fitTo = null; draw();
        }
      }
    });
    const up = (e) => {
      if (!ptrs.has(e.pointerId)) return;
      ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch = null;
      if (ptrs.size === 1) { const [p] = [...ptrs.values()]; drag = { x: p.x, y: p.y, moved: true }; return; }
      if (ptrs.size) return;
      if (drag && !drag.moved && e.type === "pointerup" && opts.onPick) {
        const r = box.getBoundingClientRect(), p = unproject(e.clientX - r.left, e.clientY - r.top);
        if (p) opts.onPick(p);
      }
      drag = null;
      if (fast) { fast = false; draw(); } // отпустили — дорисовать чётко
    };
    box.addEventListener("pointerup", up);
    box.addEventListener("pointercancel", up);
    let wheelT = null;
    box.addEventListener("wheel", (e) => {
      e.preventDefault();
      fast = true; zoomBy(e.deltaY < 0 ? 1.25 : 0.8);
      clearTimeout(wheelT); wheelT = setTimeout(() => { fast = false; draw(); }, 150);
    }, { passive: false });
    box.querySelector(".qmap-zoom").addEventListener("click", (e) => {
      const b = e.target.closest("[data-qz]");
      if (b) zoomBy(b.dataset.qz === "1" ? 1.6 : 1 / 1.6);
    });
    if (window.ResizeObserver) new ResizeObserver(() => (fitTo ? view(...fitTo) : draw())).observe(box);
    draw();
    // toScreen — где на экране точка (для проверок и подсказок); el.quizMap — сам глобус
    const api = { setPins, setLines, view, el: box, toScreen: (p) => project(p) };
    box.quizMap = api;
    return api;
  }

  // заранее скачать и разобрать лёгкую карту, пока идёт лобби (чтобы на вопросе глобус появился сразу)
  const prefetch = () => { texture(SRC).catch(() => {}); };
  window.QuizMap = { create, distance, km, prefetch };
})();
