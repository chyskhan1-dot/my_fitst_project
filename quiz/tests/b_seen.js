const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const errs = [];
  const H = await b.newContext({ viewport: { width: 1280, height: 720 } });
  const P = await b.newContext({ viewport: { width: 390, height: 800 } });
  const h = await H.newPage(), p = await P.newPage();
  for (const pg of [h, p]) pg.on('pageerror', e => errs.push(e.message));
  const B = 'http://localhost:8000';
  async function game(n) {
    await h.goto(B + '/');
    const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
    await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
    const api = (path, body) => h.evaluate(([path, body]) => fetch(path, { method: 'POST', body: JSON.stringify(body) }).then(x => x.json()), [path, { room: r.room, token: r.token, ...body }]);
    await api('/api/host/configure', { settings: { mode: 'quiz', count: 5, themes: ['Интернет'], auto: false } });
    await h.goto(B + '/host?room=' + r.room);
    await p.goto(B + '/?room=' + r.room);
    await p.fill('#name', 'Игрок'); await p.press('#name', 'Enter');
    await p.waitForTimeout(1500);
    for (let i = 0; i < 12; i++) { await api('/api/host/next', {}); await p.waitForTimeout(900); }
    const hs = await h.evaluate(() => JSON.parse(localStorage.getItem('quiz-seen') || '[]').length);
    const ps = await p.evaluate(() => JSON.parse(localStorage.getItem('quiz-seen') || '[]').length);
    console.log('game', n, 'room', r.room, 'host seen', hs, 'phone seen', ps);
    await p.screenshot({ path: process.argv[2] + '/phone' + n + '.png' });
  }
  await game(1); await game(2);
  console.log('errors', errs);
  await b.close();
})();
