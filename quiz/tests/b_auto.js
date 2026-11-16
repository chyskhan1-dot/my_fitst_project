// Автопереход по умолчанию: 2 игрока отвечают, смотрим очки на ТВ и телефоне; ловим ошибки
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
(async () => {
  const S = process.argv[2];
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }); const errs = [];
  const H = await b.newContext({ viewport: { width: 1280, height: 720 } }), h = await H.newPage();
  const pages = [];
  h.on('pageerror', e => errs.push(e.message));
  await h.goto('http://localhost:8000/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  await h.evaluate(r => fetch('/api/host/configure', { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, settings: { mode: 'quiz', count: 10, sabotage: false } }) }), r);
  await h.goto('http://localhost:8000/host?room=' + r.room);
  for (const n of ['Аня', 'Борис']) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(e.message)); pages.push(p);
    await p.goto('http://localhost:8000/?room=' + r.room); await p.fill('#name', n); await p.tap('#join button[type=submit]'); await p.waitForTimeout(800);
  }
  await h.click('[data-act=next]'); await h.waitForTimeout(1500);
  for (const p of pages) { const btn = await p.$('[data-choice], .opt, .answers button'); if (btn) await btn.tap().catch(() => {}); await p.waitForTimeout(400); }
  await h.waitForTimeout(2500); await h.screenshot({ path: S + '/auto_reveal.png' }); await pages[0].screenshot({ path: S + '/auto_phone.png' });
  await h.waitForTimeout(3500); await h.screenshot({ path: S + '/auto_leaders.png' });
  const t0 = Date.now(); let ph;
  do { await h.waitForTimeout(300); ph = await h.evaluate(() => lastState && lastState.phase); } while (ph !== 'question' && Date.now() - t0 < 15000);
  console.log('ответ→таблица→следующий вопрос сам за', ((Date.now() - t0) / 1000 + 6).toFixed(1), 'с; этап', ph);
  console.log('errors', errs); await b.close();
})();
