// «Случайный игрок»: в каждом режиме 3 телефона и ведущий жмут случайные кнопки, ловим ошибки страниц и консоли
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000', MODE = process.argv[3] || 'king', STEPS = Number(process.argv[4] || 90);
(async () => {
  const b = await chromium.launch(); const errs = [];
  const bad = (m) => m.type() === 'error' && !/favicon|404|Failed to load resource/.test(m.text());
  const h = await (await b.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
  h.on('pageerror', e => errs.push('host: ' + e.message));
  h.on('console', m => { if (bad(m)) errs.push('host console: ' + m.text()); });
  await h.goto(B + '/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  const H = (a, body = {}) => h.evaluate(([a, body, r]) => fetch('/api/host/' + a, { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, ...body }) }).then(x => x.json()), [a, body, r]);
  console.log('configure', JSON.stringify(await H('configure', { settings: { mode: MODE, auto: true, seconds: 10 } })).slice(0, 80));
  await h.goto(B + '/host?room=' + r.room);
  const ph = [];
  for (const n of ['Аня', 'Борис', 'Вика']) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    p.on('console', m => { if (bad(m)) errs.push(n + ' console: ' + m.text()); });
    await p.goto(B + '/?room=' + r.room); await p.fill('#name', n); await p.tap('#join button[type=submit]'); await p.waitForTimeout(400);
    ph.push(p);
  }
  await H('next'); // из лобби
  const SKIP = '.home-btn, #other, .leave, [data-host="reset"], [data-act="setup"], [data-act="reset"], [data-share-site], [data-install], [data-kick], a[href]';
  const phases = new Set(), overs = [], zooms = new Set();
  for (let i = 0; i < STEPS; i++) {
    const s = await h.evaluate(() => lastState).catch(() => null);
    if (s) phases.add(s.phase);
    if (s && s.phase === 'final') break;
    for (const p of ph) {
      const btns = await p.$$(`#main button:not([disabled]):not(${SKIP}), #main [data-choice], #main [data-si-cell]`);
      const ok = []; for (const x of btns) if (await x.isVisible().catch(() => false)) ok.push(x);
      if (ok.length) await ok[Math.floor(Math.random() * ok.length)].tap({ timeout: 1500 }).catch(() => {});
      const inp = await p.$('#main input:not([disabled]):not([type=hidden]):not([type=range])');
      if (inp && Math.random() < .5) { await inp.fill('Москва').catch(() => {}); await p.keyboard.press('Enter').catch(() => {}); }
    }
    if (Math.random() < .35) {
      const hb = await h.$$(`#actions button:not([disabled]):not(${SKIP}), #main [data-si-cell]:not([disabled])`);
      if (hb.length) await hb[Math.floor(Math.random() * hb.length)].click({ timeout: 1500 }).catch(() => {});
    }
    await h.waitForTimeout(450);
    const ov = await h.evaluate(() => [lastState && lastState.phase, document.documentElement.scrollHeight - innerHeight, getComputedStyle(document.getElementById('main')).zoom]).catch(() => null);
    if (ov && ov[1] > 4) overs.push(ov.join(':'));
    if (ov && ov[2] !== '1' && ov[2] !== 'normal') { zooms.add(ov[0] + ':' + ov[2]); if (+ov[2] < .72 && !globalThis.shot) { globalThis.shot = 1; await h.screenshot({ path: S + '/zoom_small.png' }); } }
  }
  console.log('не влезло в экран:', overs.slice(0, 8), 'уменьшено:', [...zooms].slice(0, 8));
  console.log(MODE, 'этапы:', [...phases].join(' '));
  await h.waitForTimeout(3000); await h.screenshot({ path: `${S}/monkey_${MODE}.png` }); console.log('команды', JSON.stringify(await h.evaluate(() => lastState.teams)));
  console.log('errors', errs.slice(0, 10)); await b.close();
})();
