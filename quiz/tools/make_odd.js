// Рисует картинки к вопросам «Убери лишнее» (media/odd/*.webp): четыре смайлика с подписями,
// рамки — в цвет кнопок ответа (1-й вариант красный, 2-й синий, 3-й жёлтый, 4-й зелёный).
// Смайлики — Microsoft Fluent Emoji (MIT), качаются с GitHub в tools/.cache (в репозиторий не попадают).
// Какой смайлик к какому слову — tools/odd_pics.json.
// Запуск из папки quiz: node tools/make_odd.js [новые.json] (нужен Playwright: npm root -g).
//   без аргумента — перерисовать картинки всех вопросов темы в packs/general.json (по порядку их вариантов);
//   с файлом вопросов для add_questions.py — дописать им поле image и нарисовать (порядок: верный, потом неверные).
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const root = execFileSync('npm', ['root', '-g']).toString().trim();
const { chromium } = require(root + '/playwright');
const QUIZ = path.join(__dirname, '..');
const THEME = 'Убери лишнее';
const PICS = JSON.parse(fs.readFileSync(path.join(__dirname, 'odd_pics.json'), 'utf8'));
const CACHE = path.join(__dirname, '.cache', 'fluent');
const COLORS = ['#e5484d', '#3e7bfa', '#f2a516', '#26a269'];

const folder = (name) => { if (!PICS[name]) throw new Error(`нет смайлика для «${name}» в tools/odd_pics.json`); return PICS[name]; };
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
// имя файла не зависит от порядка вариантов: перерисовка после раскладки ответов пишет в тот же файл
const imagePath = (names) => `media/odd/${names.map((n) => slug(folder(n))).sort().join('_')}.webp`;

function emoji(name) {
  const f = folder(name), file = path.join(CACHE, slug(f) + '.png');
  if (fs.existsSync(file)) return file;
  fs.mkdirSync(CACHE, { recursive: true });
  const base = 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/';
  const low = f.toLowerCase().replace(/[ -]/g, '_');
  for (const p of [`${f}/3D/${low}_3d.png`, `${f}/Default/3D/${low}_3d_default.png`]) {
    try { execFileSync('curl', ['-sfL', '-o', file, base + encodeURI(p)]); return file; } catch {}
  }
  throw new Error(`нет такого смайлика в Fluent Emoji: «${f}»`);
}

(async () => {
  const newFile = process.argv[2];
  const all = newFile ? JSON.parse(fs.readFileSync(newFile, 'utf8')) : null;
  const items = all && all.filter((q) => q.theme === THEME);
  const pack = JSON.parse(fs.readFileSync(path.join(QUIZ, 'packs', 'general.json'), 'utf8'));
  const jobs = items
    ? items.map((q) => { const names = [q.right, ...q.wrong]; q.image = imagePath(names); return names; })
    : pack.questions.filter((q) => q.theme === THEME).map((q) => q.options);
  fs.mkdirSync(path.join(QUIZ, 'media', 'odd'), { recursive: true });
  const b = await chromium.launch();
  const page = await b.newPage();
  for (const names of jobs) {
    const pics = names.map((n) => 'data:image/png;base64,' + fs.readFileSync(emoji(n)).toString('base64'));
    const data = await page.evaluate(async ({ names, pics, COLORS }) => {
      const W = 800, H = 560, c = document.createElement('canvas'); c.width = W; c.height = H;
      const x = c.getContext('2d');
      x.fillStyle = '#f7f4ea'; x.beginPath(); x.roundRect(0, 0, W, H, 28); x.fill();
      const tw = 372, th = 252, gap = 18;
      for (let i = 0; i < 4; i++) {
        const left = gap + (i % 2) * (tw + gap), top = gap + Math.floor(i / 2) * (th + gap);
        x.fillStyle = '#fff'; x.strokeStyle = COLORS[i]; x.lineWidth = 10;
        x.beginPath(); x.roundRect(left + 5, top + 5, tw - 10, th - 10, 22); x.fill(); x.stroke();
        const img = new Image(); img.src = pics[i]; await img.decode();
        x.drawImage(img, left + tw / 2 - 80, top + 22, 160, 160);
        x.fillStyle = '#1d2433'; x.textAlign = 'center'; x.font = 'bold 30px "DejaVu Sans", Arial, sans-serif';
        x.fillText(names[i], left + tw / 2, top + th - 30, tw - 40);
      }
      return c.toDataURL('image/webp', 0.85);
    }, { names, pics, COLORS });
    fs.writeFileSync(path.join(QUIZ, imagePath(names)), Buffer.from(data.split(',')[1], 'base64'));
  }
  await b.close();
  if (all) fs.writeFileSync(newFile, JSON.stringify(all, null, 1));
  console.log(`«${THEME}»: нарисовано ${jobs.length} → media/odd/`);
})();
