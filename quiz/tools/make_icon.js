// Рисует иконку приложения (значок на телефоне) в media/app/: SVG и PNG нужных размеров.
// Запуск из папки quiz: node tools/make_icon.js (нужен Playwright: npm root -g).
// Рисунок — четыре цветные плитки, как кнопки ответов, и большой «?» поверх.
const fs = require('fs'), path = require('path');
const root = require('child_process').execSync('npm root -g').toString().trim();
const { chromium } = require(root + '/playwright');
const OUT = path.join(__dirname, '..', 'media', 'app');

// pad — поля внутри квадрата: для «maskable» (Android обрезает в круг) рисунок меньше
function svg(pad, rounded) {
  const s = 512, inner = s - 2 * pad, g = inner * 0.06, t = (inner - g) / 2, r = inner * 0.09;
  const colors = ['#e5484d', '#3e7bfa', '#f2a516', '#26a269'];
  const tiles = colors.map((c, i) => {
    const x = pad + (i % 2) * (t + g), y = pad + Math.floor(i / 2) * (t + g);
    return `<rect x="${x}" y="${y}" width="${t}" height="${t}" rx="${r}" fill="${c}"/>`;
  }).join('');
  const cx = s / 2, cy = s / 2, cr = inner * 0.3;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${s} ${s}" width="${s}" height="${s}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a1050"/><stop offset="1" stop-color="#0e1330"/></linearGradient></defs>
<rect width="${s}" height="${s}" rx="${rounded ? 112 : 0}" fill="url(#bg)"/>${tiles}
<circle cx="${cx}" cy="${cy}" r="${cr}" fill="#0e1330" stroke="#fff" stroke-width="${inner * 0.035}"/>
<text x="${cx}" y="${cy + cr * 0.36}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="${cr * 1.1}" fill="#fff">?</text>
</svg>\n`;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const files = { 'icon.svg': svg(72, true), 'icon-maskable.svg': svg(112, false), 'icon-square.svg': svg(56, false) };
  for (const [name, text] of Object.entries(files)) fs.writeFileSync(path.join(OUT, name), text);
  const b = await chromium.launch();
  const p = await b.newPage();
  // icon-*.png — обычный значок, maskable — с запасом полей для Android, apple-touch-icon — квадрат без скругления (iPhone скругляет сам)
  const pngs = [['icon-192.png', 'icon.svg', 192], ['icon-512.png', 'icon.svg', 512],
    ['icon-maskable-512.png', 'icon-maskable.svg', 512], ['apple-touch-icon.png', 'icon-square.svg', 180]];
  for (const [png, src, size] of pngs) {
    await p.setViewportSize({ width: size, height: size });
    await p.setContent(`<body style="margin:0;background:transparent">${files[src].replace('width="512" height="512"', `width="${size}" height="${size}"`)}</body>`);
    await p.screenshot({ path: path.join(OUT, png), omitBackground: true });
  }
  await b.close();
  console.log('иконки →', OUT);
})();
