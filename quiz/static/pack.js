// Работа с пакетами вопросов: чтение файлов .json и .csv (Google Таблицы, Excel)
// и подготовка картинок и аудио. Используется в меню ведущего и в редакторе.
(function () {
  const MAX_IMAGE_SIDE = 1280; // картинки больше уменьшаем, чтобы пакет грузился быстро
  const MAX_AUDIO_MB = 8;

  const CSV_HEADER = ["Вопрос", "Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Правильный (1-4)", "Картинка (ссылка)", "Аудио (ссылка)", "Тип", "Тема", "Сложность", "Время (с)"];
  // Тип: пусто — один верный; «несколько» — верных несколько (номера через запятую);
  // «порядок» — варианты записаны в правильном порядке; «текст» — в вариантах верные написания ответа;
  // «число» — в «Варианте 1» правильное число, в «Варианте 2» единицы (м, км, год), побеждает ближайший;
  // «карта» — точка на карте: в «Варианте 1» широта, во «2» долгота, в «3» название места (показывается в ответе).
  // Сложность: лёгкий, средний, сложный
  const TEMPLATE_CSV = [
    CSV_HEADER,
    ["Какая планета самая большая?", "Сатурн", "Юпитер", "Нептун", "Земля", "2", "", "", "", "Космос"],
    ["Столица Франции?", "Париж", "Лион", "", "", "1", "", "", "", "География"],
    ["Какие из этих городов — столицы?", "Москва", "Милан", "Мадрид", "Сидней", "1,3", "", "", "несколько", "География"],
    ["Расставь планеты по удалённости от Солнца", "Меркурий", "Венера", "Земля", "Марс", "", "", "", "порядок", "Космос"],
    ["Кто написал «Евгения Онегина»? Напиши фамилию", "Пушкин", "Александр Пушкин", "", "", "", "", "", "текст", "Литература", "лёгкий"],
    ["Какова высота Эвереста?", "8849", "м", "", "", "", "", "", "число", "География", "средний"],
    ["Где находится Эйфелева башня?", "48.858", "2.294", "Париж, Франция", "", "", "", "", "карта", "Где на карте", "лёгкий"],
  ].map((r) => r.map(csvCell).join(";")).join("\r\n");

  const TYPE_NAMES = { choice: "", multi: "несколько", order: "порядок", text: "текст", number: "число", map: "карта" };
  const LEVEL_NAMES = { easy: "лёгкий", normal: "средний", hard: "сложный" };
  function levelOf(value) {
    const v = String(value || "").trim().toLowerCase();
    if (/^(л|easy)/.test(v)) return "easy";
    if (/^(ср|норм|norm)/.test(v)) return "normal";
    if (/^(сл|hard)/.test(v)) return "hard";
    return null;
  }
  const toNumber = (v) => { const n = Number(String(v || "").replace(/\s/g, "").replace(",", ".")); return String(v || "").trim() && Number.isFinite(n) ? n : null; };
  function typeOf(value) {
    const v = String(value || "").trim().toLowerCase();
    if (/^(несколько|multi)/.test(v)) return "multi";
    if (/^(порядок|order|по порядку)/.test(v)) return "order";
    if (/^(текст|text|свой)/.test(v)) return "text";
    if (/^(число|number|ближе)/.test(v)) return "number";
    if (/^(карта|map|где)/.test(v)) return "map";
    return "choice";
  }

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
      if (i === 0 && /^вопрос/i.test((r[0] || "").trim())) return; // строка заголовков
      const options = r.slice(1, 5).map((o) => (o || "").trim());
      const filled = options.filter(Boolean);
      const type = typeOf(r[8]);
      const q = { type, q: (r[0] || "").trim(), image: (r[6] || "").trim() || null, audio: (r[7] || "").trim() || null };
      if ((r[9] || "").trim()) q.theme = r[9].trim();
      if (levelOf(r[10])) q.level = levelOf(r[10]);
      if (Number(r[11]) > 0) q.seconds = Math.round(Number(r[11]));
      if (type === "number") {
        q.answer = toNumber(options[0]);
        if (options[1]) q.unit = options[1];
      } else if (type === "map") {
        q.answer = [toNumber(options[0]), toNumber(options[1])];
        if (options[2]) q.place = options[2];
      } else if (type === "text") {
        q.answer = filled;
      } else if (type === "order") {
        q.options = filled;
      } else if (type === "multi") {
        // номера считаем по исходным колонкам, а пустые варианты убираем
        const picked = String(r[5] || "").split(/[^0-9а-яa-z]+/i).map((v) => answerIndex(v, options)).filter((k) => k >= 0 && options[k]);
        q.options = filled;
        q.answer = [...new Set(picked.map((k) => filled.indexOf(options[k])))];
      } else {
        const answer = answerIndex(r[5], options);
        q.options = filled;
        q.answer = options[answer] ? filled.indexOf(options[answer]) : -1;
      }
      questions.push(q);
    });
    return { title, questions };
  }

  function packToCSV(pack) {
    const rows = [CSV_HEADER];
    for (const q of pack.questions) {
      const type = q.type || "choice";
      const src = type === "text" ? q.answer : type === "number" ? [q.answer, q.unit || ""]
        : type === "map" ? [...(q.answer || []), q.place || ""] : q.options;
      const opts = [0, 1, 2, 3].map((i) => (src || [])[i] ?? "");
      const media = (v) => (v && !String(v).startsWith("data:") ? v : "");
      const right = type === "multi" ? q.answer.map((a) => a + 1).join(",") : type === "choice" ? q.answer + 1 : "";
      rows.push([q.q, ...opts.map((o) => (o == null ? "" : o)), right, media(q.image), media(q.audio), TYPE_NAMES[type], q.theme || "", LEVEL_NAMES[q.level] || "", q.seconds || ""]);
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

  // «100 к 1» в таблице: Вопрос; Ответ 1; Очки 1; Ответ 2; Очки 2; …
  // Другие написания ответа — через «/»: «Пицца/pizza»
  function csvToFeud(text, title) {
    const rows = parseCSV(text);
    if (rows.length && !/^\s*\d+\s*$/.test(rows[0][2] || "")) rows.shift(); // строка заголовков
    const questions = rows.map((r, n) => {
      const answers = [];
      for (let i = 1; i + 1 < r.length; i += 2) {
        const [name, ...alt] = r[i].split("/").map((x) => x.trim()).filter(Boolean);
        const points = parseInt(r[i + 1], 10);
        if (name && points > 0) answers.push({ text: name, points, alt });
      }
      if (!r[0].trim()) throw new Error(`Строка ${n + 2}: нет вопроса`);
      return { q: r[0].trim(), answers };
    });
    return { title, questions };
  }

  function feudToCSV(pack) {
    const max = Math.max(...pack.questions.map((q) => q.answers.length));
    const head = ["Вопрос", ...Array.from({ length: max }, (_, i) => [`Ответ ${i + 1}`, `Очки ${i + 1}`]).flat()];
    const rows = pack.questions.map((q) => [q.q, ...q.answers.flatMap((a) => [[a.text, ...(a.alt || [])].join("/"), a.points])]);
    return [head, ...rows].map((r) => r.map(csvCell).join(";")).join("\r\n") + "\r\n";
  }

  async function readFeudFile(file) {
    const name = file.name.toLowerCase(), title = file.name.replace(/\.[^.]+$/, "");
    if (name.endsWith(".xlsx") || name.endsWith(".xls")) throw new Error("Сохрани таблицу как CSV");
    const text = await file.text();
    if (name.endsWith(".csv") || name.endsWith(".txt")) return csvToFeud(text, title);
    let data;
    try { data = JSON.parse(text); } catch { throw new Error("Файл повреждён или это не пакет «100 к 1»"); }
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

  window.QuizPack = { TEMPLATE_CSV, parseCSV, csvToPack, packToCSV, readPackFile, csvToFeud, feudToCSV, readFeudFile, fileToDataURL, mediaSrc, download };
})();
