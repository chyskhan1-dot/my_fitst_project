// «Царь горы»: голос отстающего ×2, «до соседа N очков», реакции на ТВ, финальный раунд ×2, награды
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
  const qs = [];
  for (let i = 0; i < 15; i++) qs.push({ q: 'Вопрос ' + (i + 1) + '?', options: ['Верно', 'Б', 'В', 'Г'], answer: 0, theme: ['Альфа', 'Бета', 'Гамма'][i % 3] });
  await H('upload', { pack: { title: 'Тест', questions: qs } });
  await H('configure', { settings: { mode: 'king', pack: 'custom', auto: false, sabotage: false } });
  await h.goto(B + '/host?room=' + r.room);
  const phones = [];
  for (const n of ['Аня', 'Борис', 'Вика']) {
    const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    await p.goto(B + '/?room=' + r.room); await p.fill('#name', n); await p.tap('#join button[type=submit]'); await p.waitForTimeout(600);
    phones.push(p);
  }
  const st = () => h.evaluate(() => lastState);
  const ans = async (p, wrong) => { await p.waitForFunction(() => lastState && lastState.phase === 'question' && lastState.options, null, { timeout: 15000 }); return p.evaluate(([w]) => fetch('/api/answer', { method: 'POST', body: JSON.stringify({ room: new URLSearchParams(location.search).get('room'), pid, answer: lastState.options.indexOf(w ? 'Б' : 'Верно') }) }), [wrong]); };
  const round = async (shotTag) => {
    await H('next'); await h.waitForTimeout(400); await H('next'); await h.waitForTimeout(6000); // голосование → колесо → вопрос
    for (let q = 0; q < 3; q++) {
      for (const [i, p] of phones.entries()) { await ans(p, i === 2); await p.waitForTimeout(150); }
      await h.waitForTimeout(1400);
      if (shotTag && q === 0) { // реакции и «до соседа»
        await phones[0].tap('[data-react="👏"]'); await phones[1].tap('[data-react="😂"]'); await h.waitForTimeout(700);
        await h.screenshot({ path: `${S}/psy_react_tv.png` }); await phones[2].screenshot({ path: `${S}/psy_reveal_phone.png` });
      }
      await H('next'); await h.waitForTimeout(300);
      if (q < 2) { await H('next'); await h.waitForTimeout(300); }
    }
  };
  await round(true);
  // раунд 2: голосование — Вика последняя, её голос ×2
  await H('next'); await h.waitForTimeout(1200);
  console.log('голосование, отстающий:', (await st()).underdog);
  await h.screenshot({ path: `${S}/psy_vote_tv.png` }); await phones[2].screenshot({ path: `${S}/psy_vote_phone.png` });
  await H('next'); await h.waitForTimeout(500);
  for (let guard = 0; guard < 120; guard++) { // доигрываем: на вопросе отвечаем, иначе «Дальше»
    const s = await st();
    if (s.phase === 'final') break;
    if (s.phase === 'question') {
      if (s.final_x2 && !globalThis.shot) { globalThis.shot = 1; await h.screenshot({ path: `${S}/psy_final_q_tv.png` }); }
      for (const [i, p] of phones.entries()) { await ans(p, i === 2); await p.waitForTimeout(120); }
      await h.waitForTimeout(1300);
    } else if (s.phase === 'topic_bet') { await h.waitForTimeout(1000); }
    else { await H('next', { from: s.phase, index: s.index }); await h.waitForTimeout(400); }
  }
  await h.waitForTimeout(3500);
  const s = await st(); console.log('этап', s.phase, 'награды', JSON.stringify((s.awards || []).map((a) => a.title + ':' + a.name)));
  await h.screenshot({ path: `${S}/psy_final_tv.png` }); await phones[2].screenshot({ path: `${S}/psy_final_phone.png`, fullPage: true });
  console.log('errors', errs); await b.close();
})();
