// Смайлики → объёмные картинки Microsoft Fluent Emoji (лицензия MIT, media/emoji/LICENSE): аватарки и ребусы.
// Картинки — media/emoji/<коды символа>.webp; каких нет в наборе (например, флаги стран) — остаются смайликами.
// Список ниже — какие картинки лежат в папке (его пишет tools/fetch_emoji.py).
(function () {
  const HAVE = new Set("1f308 1f315 1f332 1f340 1f37f 1f3b6 1f3b8 1f3b9 1f3ba 1f3c0 1f3c6 1f402 1f409 1f40d 1f40f 1f413 1f415 1f419 1f41d 1f427 1f428 1f42f 1f430 1f431 1f432 1f434 1f435 1f436 1f438 1f439 1f43a 1f43b 1f43c 1f446 1f44b 1f451 1f475 1f476 1f47d 1f483 1f4b0 1f4c8 1f525 1f534 1f535 1f576 1f577 1f57a 1f608 1f60f 1f610 1f633 1f680 1f682 1f6b6 1f6cb 1f6cf 1f7e2 1f7e5 1f916 1f976 1f981 1f984 1f985 1f989 1f98a 1f993 1f9b7 1f9ca 1f9e4 1fa99 1faa3 23f3 2615 2692 26aa 26ab 26b0 26bd 270b".split(" "));
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
