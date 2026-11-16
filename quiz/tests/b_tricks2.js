// Подлянки у двоих: оба кидают одним касанием по имени, на ТВ — обе
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
  const qs = []; for (let i = 0; i < 15; i++) qs.push({ q: 'Вопрос ' + (i + 1) + '?', options: ['Верно', 'Б', 'В', 'Г'], answer: 0, theme: ['Альфа', 'Бета', 'Гамма'][i % 3] });
  await H('upload', { pack: { title: 'Тест', questions: qs } });
  await H('configure', { settings: { mode: 'king', pack: 'custom', auto: false } });
  await h.goto(B + '/host?room=' + r.room);
  const ph = {};
  for (const n of ['Аня', 'Борис', 'Вика', 'Гена']) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    await p.goto(B + '/?room=' + r.room); await p.fill('#name', n); await p.tap('#join button[type=submit]'); await p.waitForTimeout(500);
    ph[n] = p;
  }
  const st = () => h.evaluate(() => lastState);
  const api = (p, path, body) => p.evaluate(([path, body]) => fetch(path, { method: 'POST', body: JSON.stringify({ room: new URLSearchParams(location.search).get('room'), pid, ...body }) }).then((x) => x.json()), [path, body]);
  const playUntil = async (want) => {
    for (let g = 0; g < 80; g++) {
      const s = await st();
      if (s.phase === want) return s;
      if (s.phase === 'question') {
        for (const [n, p] of Object.entries(ph)) {
          await p.waitForFunction(() => lastState && lastState.phase === 'question', null, { timeout: 8000 });
          const body = n === 'Борис' || n === 'Вика' ? { skip: true } : { answer: await p.evaluate(() => lastState.options.indexOf('Верно')) };
          await api(p, '/api/answer', body);
        }
        await h.waitForTimeout(1300);
      } else if (s.phase === 'topic_bet') await h.waitForTimeout(800);
      else if (s.phase === 'perks') { for (const p of Object.values(ph)) await api(p, '/api/perks_ready', {}); await h.waitForTimeout(800); }
      else { await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(400); }
    }
  };
  await playUntil('leaders'); // после первого вопроса — дальше доигрываем раунд
  for (let k = 0; k < 3; k++) { const s = await st(); if (s.phase === 'perks' && s.index >= 2) break; await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(400); await playUntil('perks'); }
  let s = await st();
  console.log('перки второго раунда:', s.phase, s.index, 'ждём:', s.perks && s.perks.waiting);
  await ph['Борис'].waitForTimeout(800);
  await ph['Борис'].screenshot({ path: S + '/t2_boris.png' });
  const ids = await h.evaluate(() => Object.fromEntries(lastState.players.map((p) => [p.name, p.id])));
  await ph['Борис'].tap(`[data-trick="${ids['Аня']}"]`); await ph['Борис'].waitForTimeout(900);
  await ph['Вика'].waitForTimeout(400); await ph['Вика'].screenshot({ path: S + '/t2_vika.png' });
  await ph['Вика'].tap(`[data-trick="${ids['Гена']}"]`); await ph['Вика'].waitForTimeout(900);
  await h.waitForTimeout(800); await h.screenshot({ path: S + '/t2_tv_perks.png' });
  for (const p of Object.values(ph)) await api(p, '/api/perks_ready', {});
  await h.waitForTimeout(1500);
  s = await st(); console.log('вопрос:', s.phase, 'подлянки:', JSON.stringify(s.tricks_now));
  await h.screenshot({ path: S + '/t2_tv_q.png' }); await ph['Гена'].screenshot({ path: S + '/t2_gena.png' });
  console.log('errors', errs); await b.close();
})();
