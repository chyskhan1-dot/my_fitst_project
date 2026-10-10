// Карта мира для вопросов «Где на карте?» — одна и та же у ведущего, на телефоне и в редакторе.
// Равнопромежуточная проекция: долгота → x, широта → y. Карта без подписей и границ (tools/make_map.py).
// Увеличение — колесом, щипком или кнопками +/−; перетаскивание пальцем или мышью; касание — точка.
(function () {
  // сначала лёгкая карта (~150 КБ, быстро грузится даже по мобильному интернету), подробная — только при увеличении
  const SRC = "/media/map/world-2k.jpg", SRC_FULL = "/media/map/world.jpg";
  const MAX_ZOOM = 12;
  const frac = (p) => [(p[1] + 180) / 360, (90 - p[0]) / 180]; // [широта, долгота] → доли ширины и высоты
  const toPoint = (fx, fy) => [Math.round((90 - fy * 180) * 1e4) / 1e4, Math.round((fx * 360 - 180) * 1e4) / 1e4];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function distance(a, b) {
    const r = Math.PI / 180, h = Math.sin((b[0] - a[0]) * r / 2) ** 2
      + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin((b[1] - a[1]) * r / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  const km = (n) => (n < 1 ? "меньше 1 км" : `${Math.round(n).toLocaleString("ru-RU")} км`);

  const CSS = `
.qmap { position: relative; overflow: hidden; touch-action: none; user-select: none; -webkit-user-select: none;
  background: #6fa6d3; border-radius: 16px; cursor: grab; }
.qmap.pick { cursor: crosshair; }
.qmap-in { position: absolute; left: 0; top: 0; transform-origin: 0 0; }
.qmap-in img { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.qmap-wait { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; font: 700 15px system-ui, sans-serif; pointer-events: none; }
.qmap-lines { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
.qmap-lines line { stroke: #fff; stroke-width: 2.5; stroke-dasharray: 6 5; vector-effect: non-scaling-stroke; opacity: .9; }
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
    box.innerHTML = `<div class="qmap-in"><img src="${SRC}" alt="Карта мира" draggable="false">
      <div class="qmap-wait">Карта загружается…</div><svg class="qmap-lines" viewBox="0 0 1000 500" preserveAspectRatio="none"></svg><div class="qmap-pins"></div></div>
      <div class="qmap-zoom"><button type="button" data-qz="1" aria-label="Приблизить">+</button><button type="button" data-qz="-1" aria-label="Отдалить">−</button></div>`;
    const img = box.querySelector("img"), wait = box.querySelector(".qmap-wait");
    const shown = () => wait && wait.remove();
    if (img.complete && img.naturalWidth) shown(); else img.addEventListener("load", shown, { once: true });
    let full = false;
    const inner = box.querySelector(".qmap-in"), pinsEl = box.querySelector(".qmap-pins"), linesEl = box.querySelector(".qmap-lines");
    let z = 1, tx = 0, ty = 0, fitTo = null;
    const dims = () => {
      const bw = box.clientWidth, bh = box.clientHeight, base = Math.min(bw, bh * 2); // без увеличения виден весь мир
      return { bw, bh, w: base * z, h: (base * z) / 2 };
    };
    function apply() {
      const d = dims();
      tx = d.w <= d.bw ? (d.bw - d.w) / 2 : Math.min(0, Math.max(d.bw - d.w, tx));
      ty = d.h <= d.bh ? (d.bh - d.h) / 2 : Math.min(0, Math.max(d.bh - d.h, ty));
      inner.style.width = d.w + "px"; inner.style.height = d.h + "px";
      inner.style.transform = `translate(${tx}px, ${ty}px)`;
      if (!full && d.w * (window.devicePixelRatio || 1) > 2600) { // увеличили — подгружаем подробную карту, потом подменяем
        full = true;
        const big = new Image();
        big.onload = () => { img.src = SRC_FULL; };
        big.src = SRC_FULL;
      }
    }
    function zoomAt(k, cx, cy) {
      const nz = Math.max(1, Math.min(MAX_ZOOM, z * k)), f = nz / z;
      tx = cx - (cx - tx) * f; ty = cy - (cy - ty) * f; z = nz; fitTo = null;
      apply();
    }
    // показать точки целиком (с запасом по краям)
    function view(points, maxZoom = 6) {
      fitTo = [points, maxZoom];
      const d0 = dims(); z = 1;
      if (!d0.bw) return;
      if (!points.length) { tx = 0; ty = 0; return apply(); }
      const f = points.map(frac), xs = f.map((p) => p[0]), ys = f.map((p) => p[1]);
      const sx = Math.max(Math.max(...xs) - Math.min(...xs), 0.04), sy = Math.max(Math.max(...ys) - Math.min(...ys), 0.06);
      const base = Math.min(d0.bw, d0.bh * 2);
      z = Math.max(1, Math.min(maxZoom * (d0.bh * 2 > d0.bw ? d0.bh * 2 / d0.bw : 1), (d0.bw * 0.7) / (base * sx), (d0.bh * 0.6) / ((base / 2) * sy)));
      const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
      tx = d0.bw / 2 - cx * base * z; ty = d0.bh / 2 - cy * (base / 2) * z + 12; // +12: метки висят над точкой
      apply();
      fitTo = [points, maxZoom];
    }
    function setPins(list) {
      pinsEl.innerHTML = list.map((p) => {
        const [x, y] = frac(p.point);
        return `<div class="qpin ${p.kind || ""}" style="left:${x * 100}%;top:${y * 100}%"><span><i>${esc(p.icon || "")}</i></span>${p.label ? `<small>${esc(p.label)}</small>` : ""}</div>`;
      }).join("");
    }
    function setLines(pairs) {
      linesEl.innerHTML = pairs.map(([a, b]) => {
        const [x1, y1] = frac(a), [x2, y2] = frac(b);
        return `<line x1="${x1 * 1000}" y1="${y1 * 500}" x2="${x2 * 1000}" y2="${y2 * 500}"/>`;
      }).join("");
    }

    // жесты: один палец — двигать, два — увеличивать, короткое касание — поставить точку
    const ptrs = new Map();
    let drag = null, pinch = null;
    box.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".qmap-zoom")) return;
      box.setPointerCapture(e.pointerId);
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (ptrs.size === 1) drag = { x: e.clientX, y: e.clientY, tx, ty, moved: false };
      else if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()];
        pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
        if (drag) drag.moved = true;
      }
    });
    box.addEventListener("pointermove", (e) => {
      if (!ptrs.has(e.pointerId)) return;
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const r = box.getBoundingClientRect();
      if (ptrs.size >= 2 && pinch) {
        const [a, b] = [...ptrs.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        tx += mx - pinch.mx; ty += my - pinch.my;
        zoomAt(d / (pinch.d || d), mx - r.left, my - r.top);
        pinch = { d, mx, my };
      } else if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.hypot(dx, dy) > 6) drag.moved = true;
        if (drag.moved) { tx = drag.tx + dx; ty = drag.ty + dy; fitTo = null; apply(); }
      }
    });
    const up = (e) => {
      if (!ptrs.has(e.pointerId)) return;
      ptrs.delete(e.pointerId);
      if (ptrs.size < 2) pinch = null;
      if (ptrs.size === 1) { const [p] = [...ptrs.values()]; drag = { x: p.x, y: p.y, tx, ty, moved: true }; return; }
      if (ptrs.size) return;
      if (drag && !drag.moved && e.type === "pointerup" && opts.onPick) {
        const r = inner.getBoundingClientRect();
        const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
        if (fx >= 0 && fx <= 1 && fy >= 0 && fy <= 1) opts.onPick(toPoint(fx, fy));
      }
      drag = null;
    };
    box.addEventListener("pointerup", up);
    box.addEventListener("pointercancel", up);
    box.addEventListener("wheel", (e) => {
      e.preventDefault();
      const r = box.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    box.querySelector(".qmap-zoom").addEventListener("click", (e) => {
      const b = e.target.closest("[data-qz]");
      if (b) zoomAt(b.dataset.qz === "1" ? 1.6 : 1 / 1.6, box.clientWidth / 2, box.clientHeight / 2);
    });
    if (window.ResizeObserver) new ResizeObserver(() => (fitTo ? view(...fitTo) : apply())).observe(box);
    apply();
    return { setPins, setLines, view, el: box };
  }

  // заранее скачать лёгкую карту, пока идёт лобби (чтобы на вопросе она появилась сразу)
  const prefetch = () => { const i = new Image(); i.src = SRC; };
  window.QuizMap = { create, distance, km, prefetch };
})();
