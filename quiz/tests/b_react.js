// Реакции: телефон жмёт 👏 на разных этапах — долетает ли до ТВ
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000';
(async () => {
  const b = await chromium.launch(); const errs = [];
  const h = await (await b.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
  h.on('pageerror', e => errs.push('host: ' + e.message));
  await h.goto(B + '/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  const H = (a, body = {}) => h.evaluate(([a, body, r]) => fetch('/api/host/' + a, { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, ...body }) }).then(x => x.json()), [a, body, r]);
  const qs = []; for (let i = 0; i < 6; i++) qs.push({ q: 'Вопрос ' + i + '?', options: ['Верно', 'Б', 'В', 'Г'], answer: 0 });
  await H('upload', { pack: { title: 'T', questions: qs } });
  await H('configure', { settings: { mode: 'quiz', pack: 'custom', count: 0, auto: false, sabotage: false } });
  await h.goto(B + '/host?room=' + r.room);
  const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true, isMobile: true })).newPage();
  p.on('pageerror', e => errs.push('phone: ' + e.message));
  p.on('response', async (x) => { if (x.url().includes('/api/react')) console.log('  ответ /api/react:', x.status(), await x.text()); });
  await p.goto(B + '/?room=' + r.room); await p.fill('#name', 'Аня'); await p.tap('#join button[type=submit]'); await p.waitForTimeout(800);
  const where = async (tag) => {
    const n = await p.locator('[data-react]').count();
    console.log(tag, 'этап', await h.evaluate(() => lastState.phase), 'кнопок реакций:', n);
    if (!n) return;
    await p.locator('[data-react]').first().tap(); await h.waitForTimeout(1200);
    console.log('  у Бориса на телефоне:', await globalThis.ph2.locator('.react-fly').count(), ' на ТВ всплыло:', await h.locator('.react-fly').count(), 'в состоянии:', JSON.stringify(await h.evaluate(() => lastState.reactions)));
  };
  const ph2 = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage(); await ph2.goto(B + '/?room=' + r.room); await ph2.fill('#name', 'Борис'); await ph2.tap('#join button[type=submit]'); await ph2.waitForTimeout(800); globalThis.ph2 = ph2;
  await where('лобби');
  await H('next'); await h.waitForTimeout(900);
  await where('вопрос');
  await p.tap('[data-choice]').catch(() => {}); await p.waitForTimeout(800);
  await where('ждём остальных/ответ');
  await H('next'); await h.waitForTimeout(900); await where('ответ');
  await H('next'); await h.waitForTimeout(1500); await where('лидеры');
  for (let i = 0; i < 20; i++) { const s = await h.evaluate(() => lastState); if (s.phase === 'final') break; if (s.phase === 'question') { await p.tap('[data-choice]').catch(() => {}); await p.waitForTimeout(600); } await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(500); }
  await h.waitForTimeout(1500); await where('финал');
  await p.screenshot({ path: S + '/final_phone.png' });
  console.log('прокрутка телефона на финале: высота страницы', await p.evaluate(() => document.documentElement.scrollHeight), 'окно', 800,
    'overflow body', await p.evaluate(() => getComputedStyle(document.body).overflow + '/' + getComputedStyle(document.documentElement).overflow));
  console.log('ТВ финал: высота', await h.evaluate(() => document.documentElement.scrollHeight), 'overflow', await h.evaluate(() => getComputedStyle(document.body).overflow + '/' + getComputedStyle(document.documentElement).overflow));
  await h.screenshot({ path: S + '/final_tv.png' });
  console.log('errors', errs); await b.close();
})();
