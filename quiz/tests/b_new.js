const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const fs = require('fs');
(async () => {
  const S = process.argv[2], pack = JSON.parse(fs.readFileSync(S + '/testpack.json', 'utf8'));
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const errs = [];
  const H = await b.newContext({ viewport: { width: 1280, height: 720 } }), P = await b.newContext({ viewport: { width: 390, height: 800 } });
  const h = await H.newPage(), p = await P.newPage();
  for (const pg of [h, p]) pg.on('pageerror', e => errs.push(e.message));
  const B = 'http://localhost:8000';
  await h.goto(B + '/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  const api = (path, body) => h.evaluate(([path, body]) => fetch(path, { method: 'POST', body: JSON.stringify(body) }).then(x => x.json()), [path, { room: r.room, token: r.token, ...body }]);
  console.log(await api('/api/host/upload', { pack }));
  console.log(await api('/api/host/configure', { settings: { mode: 'quiz', pack: 'custom', count: 0, auto: false, levels: ['easy', 'normal', 'hard'], seconds: 30 } }));
  await h.goto(B + '/host?room=' + r.room);
  await p.goto(B + '/?room=' + r.room);
  await p.fill('#name', 'Игрок'); await p.press('#name', 'Enter');
  await p.waitForTimeout(1500);
  for (let i = 0; i < pack.questions.length; i++) {
    let s;
    do { await api('/api/host/next', {}); await p.waitForTimeout(700); s = await h.evaluate(r => fetch('/api/state?room=' + r).then(x => x.json()), r.room); } while (s.phase !== 'question');
    await p.waitForTimeout(s.images ? 9000 : 2000);
    await h.screenshot({ path: `${S}/host_q${i}.png` }); await p.screenshot({ path: `${S}/phone_q${i}.png` });
    await api('/api/host/next', {}); await p.waitForTimeout(1500);
    await h.screenshot({ path: `${S}/host_a${i}.png` }); await p.screenshot({ path: `${S}/phone_a${i}.png` });
  }
  console.log('errors', errs);
  await b.close();
})();
