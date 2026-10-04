// Работа с пакетами вопросов: чтение файлов .json и .csv (Google Таблицы, Excel)
// и подготовка картинок и аудио. Используется в меню ведущего и в редакторе.
(function () {
  const MAX_IMAGE_SIDE = 1280; // картинки больше уменьшаем, чтобы пакет грузился быстро
  const MAX_AUDIO_MB = 8;

  const CSV_HEADER = ["Вопрос", "Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Правильный (1-4)", "Картинка (ссылка)", "Аудио (ссылка)"];
  const TEMPLATE_CSV = [
    CSV_HEADER,
    ["Какая планета самая большая?", "Сатурн", "Юпитер", "Нептун", "Земля", "2", "", ""],
    ["Сколько струн у классической гитары?", "4", "5", "6", "7", "3", "", ""],
    ["Столица Франции?", "Париж", "Лион", "", "", "1", "", ""],
  ].map((r) => r.map(csvCell).join(";")).join("\r\n");

  function csvCell(v) {
    v = String(v ?? "");
    return /[";,\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  }

  // Разбор CSV с кавычками; разделитель — «;» (русский Excel) или «,» (Google Таблицы)
  function parseCSV(text) {
    text = text.replace(/^﻿/, "");
    const firstLine = text.split(/\r?\n/, 1)[0];
    const sep = (firstLine.match(/;/g) || []).length >= (firstLine.match(/,/g) || []).length ? ";" : ",";
    const rows = [];
    let row = [], cell = "", quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"') quoted = true;
      else if (ch === sep) { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += ch;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return rows.filter((r) => r.some((c) => c.trim()));
  }

  // «2», «Б», «B» или сам текст варианта → номер правильного ответа (с нуля)
  function answerIndex(value, options) {
    const v = String(value || "").trim().toLowerCase();
    if (/^[1-4]$/.test(v)) return Number(v) - 1;
    const ru = "абвг".indexOf(v), en = "abcd".indexOf(v);
    if (v.length === 1 && ru >= 0) return ru;
    if (v.length === 1 && en >= 0) return en;
    const byText = options.findIndex((o) => o.trim().toLowerCase() === v);
    return byText >= 0 ? byText : -1;
  }

  function csvToPack(text, title) {
    const rows = parseCSV(text);
    const questions = [];
    rows.forEach((r, i) => {
      const options = r.slice(1, 5).map((o) => (o || "").trim());
      const filled = options.filter(Boolean);
      const answer = answerIndex(r[5], options);
      if (i === 0 && answer < 0) return; // строка заголовков
      // правильный ответ считаем по исходным колонкам, а пустые варианты убираем
      const correct = options[answer];
      questions.push({
        q: (r[0] || "").trim(),
        options: filled,
        answer: correct ? filled.indexOf(correct) : -1,
        image: (r[6] || "").trim() || null,
        audio: (r[7] || "").trim() || null,
      });
    });
    return { title, questions };
  }

  function packToCSV(pack) {
    const rows = [CSV_HEADER];
    for (const q of pack.questions) {
      const opts = [0, 1, 2, 3].map((i) => q.options[i] || "");
      const media = (v) => (v && !String(v).startsWith("data:") ? v : "");
      rows.push([q.q, ...opts, q.answer + 1, media(q.image), media(q.audio)]);
    }
    return rows.map((r) => r.map(csvCell).join(";")).join("\r\n");
  }

  async function readPackFile(file) {
    const name = file.name.toLowerCase();
    const title = file.name.replace(/\.[^.]+$/, "");
    if (name.endsWith(".xlsx") || name.endsWith(".xls")) {
      throw new Error("Сохрани таблицу как CSV: в Excel «Файл → Сохранить как → CSV», в Google Таблицах «Файл → Скачать → CSV»");
    }
    const text = await file.text();
    if (name.endsWith(".csv") || name.endsWith(".txt")) return csvToPack(text, title);
    let data;
    try { data = JSON.parse(text); } catch { throw new Error("Файл повреждён или это не пакет вопросов"); }
    if (Array.isArray(data)) data = { title, questions: data };
    return data;
  }

  const readAsDataURL = (blob) => new Promise((ok, fail) => {
    const r = new FileReader();
    r.onload = () => ok(r.result);
    r.onerror = () => fail(new Error("Не удалось прочитать файл"));
    r.readAsDataURL(blob);
  });

  // Картинку уменьшаем до 1280 px по большей стороне и сохраняем в JPEG
  async function fileToDataURL(file, kind) {
    if (kind === "audio") {
      if (!file.type.startsWith("audio/")) throw new Error("Это не аудиофайл");
      if (file.size > MAX_AUDIO_MB * 1024 * 1024) throw new Error(`Аудио больше ${MAX_AUDIO_MB} МБ, обрежь его`);
      return readAsDataURL(file);
    }
    if (!file.type.startsWith("image/")) throw new Error("Это не картинка");
    if (file.type === "image/gif") return readAsDataURL(file); // анимацию не трогаем
    const url = URL.createObjectURL(file);
    try {
      const img = await new Promise((ok, fail) => {
        const i = new Image();
        i.onload = () => ok(i);
        i.onerror = () => fail(new Error("Не удалось открыть картинку"));
        i.src = url;
      });
      const k = Math.min(1, MAX_IMAGE_SIDE / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      return c.toDataURL("image/jpeg", 0.85);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  // Адрес для показа в браузере: файлы из папки media/ лежат по адресу /media/...
  function mediaSrc(v) {
    if (!v) return "";
    return /^(data:|https?:|\/)/.test(v) ? v : "/" + v;
  }

  function download(name, text, type) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  window.QuizPack = { TEMPLATE_CSV, parseCSV, csvToPack, packToCSV, readPackFile, fileToDataURL, mediaSrc, download };
})();
