// Аудит дизайна: экраны телефона (390×800 и маленький 320×568) по ходу «Царя горы» + меню ведущего с телефона, /heads, /learn, /editor
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000';
(async () => {
  const b = await chromium.launch(); const errs = [];
  const mk = async (w, h, tag) => { const p = await (await b.newContext({ viewport: { width: w, height: h }, hasTouch: true, isMobile: true })).newPage(); p.on('pageerror', e => errs.push(tag + ': ' + e.message)); return p; };
  const over = async (p, tag) => { const o = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, w: innerWidth, sh: document.documentElement.scrollHeight, h: innerHeight,
    small: [...document.querySelectorAll('button, a, [data-choice]')].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.height < 40 || r.width < 40); }).map((e) => (e.textContent || e.id).trim().slice(0, 14)).slice(0, 6),
    tiny: [...document.querySelectorAll('#main *, #app *')].filter((e) => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 12).length }));
    console.log(tag, 'гориз.прокрутка:', o.sw > o.w + 1, 'высота', o.sh + '/' + o.h, 'мелкие кнопки:', JSON.stringify(o.small), 'текст <12px:', o.tiny); };
  const shot = async (p, name) => { await p.screenshot({ path: `${S}/au_${name}.png` }); await over(p, name); };
  // главная и экран игры
  const home = await mk(390, 800, 'home'); await home.goto(B + '/'); await home.waitForTimeout(900); await shot(home, 'home');
  await home.tap('[data-game]'); await home.waitForTimeout(600); await shot(home, 'game');
  // ведущий с телефона: меню
  const hp = await mk(390, 800, 'hostphone'); await hp.goto(B + '/'); await hp.waitForTimeout(500);
  await hp.tap('[data-game]'); await hp.waitForTimeout(400); await hp.tap('#as-host'); await hp.waitForTimeout(2500); await shot(hp, 'hostsetup');
  await hp.screenshot({ path: `${S}/au_hostsetup_full.png`, fullPage: true });
  // игра
  const h = await (await b.newContext({ viewport: { width: 1280, height: 720 } })).newPage(); h.on('pageerror', e => errs.push('tv: ' + e.message));
  await h.goto(B + '/');
  const r = await h.evaluate(async () => (await fetch('/api/rooms', { method: 'POST', body: '{}' })).json());
  await h.evaluate(r => localStorage.setItem('quiz-host-' + r.room, r.token), r);
  const H = (a, body = {}) => h.evaluate(([a, body, r]) => fetch('/api/host/' + a, { method: 'POST', body: JSON.stringify({ room: r.room, token: r.token, ...body }) }).then(x => x.json()), [a, body, r]);
  await H('configure', { settings: { mode: 'king', auto: false, doubles: true } });
  await h.goto(B + '/host?room=' + r.room);
  const p = await mk(390, 800, 'phone'), p2 = await mk(320, 568, 'small');
  for (const [x, n] of [[p, 'Александра'], [p2, 'Борис']]) { await x.goto(B + '/?room=' + r.room); await x.waitForTimeout(500); if (x === p2) await shot(x, 'join_small'); await x.fill('#name', n); await x.tap('#join button[type=submit]'); await x.waitForTimeout(500); }
  await shot(p2, 'lobby_small');
  const seen = new Set();
  for (let i = 0; i < 60 && seen.size < 7; i++) {
    const s = await h.evaluate(() => lastState); const ph = s.phase + (s.phase === 'question' ? ':' + s.qtype : '');
    if (!seen.has(ph) && seen.size < 9) { seen.add(ph); await p.waitForTimeout(700); await shot(p, 'ph_' + ph.replace(':', '_')); await shot(p2, 'sm_' + ph.replace(':', '_')); if (['question:choice', 'reveal', 'topic_vote', 'perks'].includes(ph)) await h.screenshot({ path: `${S}/au_tv_${ph.replace(':', '_')}.png` }); }
    if (s.phase === 'question') { await p.tap('#main [data-choice]').catch(() => {}); await p.waitForTimeout(500); if (!seen.has('wait')) { seen.add('wait'); await shot(p, 'ph_wait'); } }
    if (s.phase === 'topic_bet') { await h.waitForTimeout(900); continue; }
    await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(500);
  }
  for (const [u, n] of [['/heads', 'heads'], ['/learn', 'learn'], ['/editor', 'editor']]) { const x = await mk(390, 800, n); await x.goto(B + u); await x.waitForTimeout(1200); await shot(x, n); }
  console.log('этапы:', [...seen].join(' ')); console.log('errors', errs); await b.close();
})();
