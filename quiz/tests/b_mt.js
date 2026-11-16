// Гора и цветные аватарки: 6 игроков с аватарками, «Царь горы», два раунда; выбор аватарки, лобби, лидеры
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
  await H('configure', { settings: { mode: 'king', pack: 'custom', auto: false, sabotage: false } });
  await h.goto(B + '/host?room=' + r.room);
  const ph = [];
  const names = ['Аня', 'Борис', 'Вика', 'Гена', 'Даша', 'Егор'];
  for (const [i, n] of names.entries()) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    await p.goto(B + '/?room=' + r.room); await p.waitForSelector('[data-ava]');
    if (i === 2) await p.screenshot({ path: S + '/mt_pick.png' });
    await p.fill('#name', n); await p.tap(`[data-ava]:nth-child(${i * 3 + 1})`); await p.tap('#join button[type=submit]'); await p.waitForTimeout(500);
    ph.push(p);
  }
  await ph[0].waitForTimeout(800); await ph[0].screenshot({ path: S + '/mt_lobby_phone.png' });
  await h.waitForTimeout(800); await h.screenshot({ path: S + '/mt_lobby_tv.png' });
  const st = () => h.evaluate(() => lastState);
  const api = (p, path, body) => p.evaluate(([path, body]) => fetch(path, { method: 'POST', body: JSON.stringify({ room: new URLSearchParams(location.search).get('room'), pid, ...body }) }).then((x) => x.json()), [path, body]);
  let leaders = 0;
  for (let g = 0; g < 120 && leaders < 6; g++) {
    const s = await st();
    if (s.phase === 'question') {
      for (const [i, p] of ph.entries()) {
        await p.waitForFunction(() => lastState && lastState.phase === 'question' && lastState.options, null, { timeout: 8000 });
        const wrong = (i + s.index) % 4 === 3 || i === 5;
        await api(p, '/api/answer', { answer: await p.evaluate((w) => lastState.options.indexOf(w ? 'Б' : 'Верно'), wrong) });
        await p.waitForTimeout(100 + i * 60);
      }
      await h.waitForTimeout(1300);
    } else if (s.phase === 'leaders') {
      leaders++;
      await h.waitForTimeout(leaders === 6 ? 1500 : 300);
      if (leaders === 6) { await h.screenshot({ path: S + '/mt_mid_tv.png' }); await h.waitForTimeout(2500); await h.screenshot({ path: S + '/mt_tv.png' }); await ph[1].screenshot({ path: S + '/mt_phone.png' }); break; }
      await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(400);
    } else if (s.phase === 'topic_bet') await h.waitForTimeout(800);
    else if (s.phase === 'perks') { for (const p of ph) await api(p, '/api/perks_ready', {}); await h.waitForTimeout(800); }
    else { await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(400); }
  }
  const s = await st(); console.log('этап', s.phase, s.index, s.players.map((p) => p.name + ':' + p.score + ':' + p.color).join(' '));
  console.log('errors', errs); await b.close();
})();
