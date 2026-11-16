// Перки перед раундом, подлянка «туман», таблица на 20 игроков — ТВ и телефон
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000';
(async () => {
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }); const errs = [];
  const h = await (await b.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
  h.on('pageerror', e => errs.push('host: ' + e.message));
  await h.goto(B + '/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  const H = (a, body = {}) => h.evaluate(([a, body, r]) => fetch('/api/host/' + a, { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, ...body }) }).then(x => x.json()), [a, body, r]);
  await H('configure', { settings: { mode: 'king', doubles: true, auto: false } });
  await h.goto(B + '/host?room=' + r.room);
  const phones = [];
  for (const n of ['Аня', 'Борис', 'Вика']) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    await p.goto(B + '/?room=' + r.room); await p.fill('#name', n); await p.tap('#join button[type=submit]'); await p.waitForTimeout(700);
    phones.push(p);
  }
  const st = () => h.evaluate(() => lastState);
  const pid = (p) => p.evaluate(() => pid);
  const api = (p, path, body) => p.evaluate(([path, body]) => fetch(path, { method: 'POST', body: JSON.stringify({ room: new URLSearchParams(location.search).get('room') || room, pid, ...body }) }).then(x => x.json()), [path, body]);
  // раунд 1: голосование → колесо → перки
  await H('next'); await h.waitForTimeout(500); await H('next'); await h.waitForTimeout(6500); // колесо докрутилось → перки
  await h.waitForTimeout(800);
  console.log('этап', (await st()).phase);
  await h.screenshot({ path: S + '/pk_tv.png' }); await phones[0].screenshot({ path: S + '/pk_phone.png' });
  await phones[0].tap('[data-bet-next="1"]'); await phones[0].waitForTimeout(900);
  await phones[0].screenshot({ path: S + '/pk_phone2.png' }); await h.waitForTimeout(500); await h.screenshot({ path: S + '/pk_tv2.png' });
  for (const p of phones.slice(1)) { await p.tap('[data-perks-ready]'); await p.waitForTimeout(400); }
  await h.waitForTimeout(1200); console.log('после «Готово»', (await st()).phase);
  // раунд 1: Борис дважды пропускает → подлянка
  for (let q = 0; q < 3; q++) {
    for (const [i, p] of phones.entries()) await api(p, '/api/answer', i === 1 ? { skip: true } : { answer: 0 });
    await h.waitForTimeout(1500); await H('next'); await h.waitForTimeout(300); // таблица
    if (q < 2) { await H('next'); await h.waitForTimeout(500); }
  }
  await H('next'); await h.waitForTimeout(500); await H('next'); await h.waitForTimeout(6500); await h.waitForTimeout(800);
  console.log('раунд 2:', (await st()).phase, 'подлянка у Бориса:', JSON.stringify((await phones[1].evaluate(() => lastState.me)).can_trick));
  await phones[1].screenshot({ path: S + '/pk_trick_phone.png' }); await h.screenshot({ path: S + '/pk_trick_tv.png' });
  const vika = await pid(phones[2]);
  await api(phones[1], '/api/trick', { to: vika });
  await phones[1].waitForTimeout(800); await phones[1].screenshot({ path: S + '/pk_trick_phone2.png' });
  for (const p of phones) await api(p, '/api/perks_ready', {});
  await h.waitForTimeout(1500);
  console.log('вопрос с подлянкой:', (await st()).phase, (await st()).trick_now && JSON.stringify((await st()).trick_now));
  await h.screenshot({ path: S + '/pk_q_tv.png' }); await phones[2].screenshot({ path: S + '/pk_q_victim.png' });
  await phones[2].waitForTimeout(5500); await phones[2].screenshot({ path: S + '/pk_q_victim2.png' });
  // 20 игроков — таблица
  const r2 = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r2);
  const H2 = (a, body = {}) => h.evaluate(([a, body, r]) => fetch('/api/host/' + a, { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, ...body }) }).then(x => x.json()), [a, body, r2]);
  await H2('configure', { settings: { mode: 'quiz', count: 10, auto: false, sabotage: false } });
  const ctxs = [];
  for (let i = 0; i < 20; i++) {
    const c = await b.newContext({ viewport: { width: 390, height: 800 } }); const p = await c.newPage();
    await p.goto(B + '/'); const id = await p.evaluate(async ([room, i]) => (await (await fetch('/api/join', { method: 'POST', body: JSON.stringify({ room, name: 'Игрок' + (i + 1) }) })).json()).pid, [r2.room, i]);
    ctxs.push([p, id]);
  }
  await h.goto(B + '/host?room=' + r2.room); await H2('next'); await h.waitForTimeout(600);
  for (const [i, [p, id]] of ctxs.entries()) await p.evaluate(async ([room, id, i]) => fetch('/api/answer', { method: 'POST', body: JSON.stringify({ room, pid: id, answer: i % 4 }) }), [r2.room, id, i]);
  await h.waitForTimeout(1200); await H2('next'); await h.waitForTimeout(400); await H2('next'); await h.waitForTimeout(6000);
  await h.screenshot({ path: S + '/pk_rope_tv.png' });
  const ph = ctxs[0][0]; await ph.evaluate(([room, id]) => { localStorage.setItem('quiz-room', room); }, [r2.room, ctxs[0][1]]);
  await ph.goto(B + '/?room=' + r2.room); await ph.waitForTimeout(800);
  if (await ph.$('#name')) { await ph.fill('#name', 'Игрок1'); await ph.click('#join button[type=submit]'); }
  await ph.waitForTimeout(6000); await ph.screenshot({ path: S + '/pk_rope_phone.png', fullPage: true });
  console.log('errors', errs);
  await b.close();
})();
