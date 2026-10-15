// Смайлики → объёмные картинки Microsoft Fluent Emoji (лицензия MIT, media/emoji/LICENSE): аватарки и ребусы.
// Картинки — media/emoji/<коды символа>.webp; каких нет в наборе (например, флаги стран) — остаются смайликами.
// Список ниже — какие картинки лежат в папке (его пишет tools/fetch_emoji.py).
(function () {
  const HAVE = new Set("1f170 1f171 1f30a 1f315 1f327 1f32c 1f333 1f334 1f338 1f339 1f34b 1f377 1f3b6 1f3b8 1f3c0 1f3e8 1f419 1f422 1f427 1f428 1f42f 1f430 1f431 1f432 1f434 1f435 1f438 1f43a 1f43b 1f43c 1f44b 1f451 1f476 1f47d 1f49b 1f49c 1f4de 1f504 1f50b 1f525 1f57a 1f608 1f631 1f680 1f6a2 1f6e3 1f90d 1f916 1f981 1f984 1f989 1f98a 1f9ca 1f9d9 1f9df 1fa78 1fa86 2600 2602 2614 26bd 27a1 30-20e3 31-20e3".split(" "));
  const key = (g) => [...g].map((c) => c.codePointAt(0)).filter((c) => c !== 0xfe0f).map((c) => c.toString(16)).join("-");
  const seg = window.Intl && Intl.Segmenter ? new Intl.Segmenter("ru", { granularity: "grapheme" }) : null;
  const split = (s) => (seg ? [...seg.segment(s)].map((x) => x.segment) : Array.from(s));
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const style = document.createElement("style");
  style.textContent = ".emo-img { width: 1.15em; height: 1.15em; vertical-align: -0.2em; object-fit: contain; }";
  document.head.appendChild(style);
  // строка со смайликами → HTML, где смайлики заменены картинками (остальной текст экранирован)
  function html(s) {
    return split(String(s ?? "")).map((g) => {
      const k = key(g);
      return HAVE.has(k) ? `<img class="emo-img" src="/media/emoji/${k}.webp" alt="${esc(g)}" draggable="false">` : esc(g);
    }).join("");
  }
  window.QuizEmoji = { html };
})();
