// «Слово на лбу» с одного телефона: после последнего хода — сразу итоги со словами хода, слово можно поправить
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000';
(async () => {
  const b = await chromium.launch(); const errs = [];
  const ctx = await b.newContext({ viewport: { width: 800, height: 390 }, hasTouch: true, isMobile: true });
  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push(e.message));
  await p.clock.install();
  await p.goto(B + '/heads');
  await p.waitForTimeout(800);
  const theme = await p.evaluate(async () => (await (await fetch('/api/heads/words')).json())[0].name);
  // последний ход: раунд 1 из 1, ходит вторая команда
  await p.evaluate((theme) => localStorage.setItem('quiz-heads', JSON.stringify({ stage: 'turn', teams: 2, themes: [theme], names: ['Красные', 'Синие'], round: 0, team: 1, scores: [3, 0], cur: [], at: Date.now() })), theme);
  await p.reload(); await p.waitForTimeout(500);
  await p.click('#resume'); await p.waitForTimeout(300);
  await p.click('#start'); await p.waitForTimeout(500);
  const rot = await p.$('#hd-rotate button'); if (rot && await rot.isVisible()) await rot.click();
  await p.clock.runFor(4000);
  for (let i = 0; i < 3; i++) { await p.mouse.click(600, 200); await p.clock.runFor(1200); } // касание правой половины — угадал (или как на экране)
  await p.clock.runFor(65000); await p.waitForTimeout(300); await p.clock.runFor(3000); await p.waitForTimeout(500);
  const st = await p.evaluate(() => JSON.parse(localStorage.getItem('quiz-heads')));
  console.log('после хода: этап', st.stage, 'счёт', st.scores, 'слов', st.cur.length);
  console.log('на экране:', (await p.textContent('#app')).replace(/\s+/g, ' ').slice(0, 200));
  await p.setViewportSize({ width: 390, height: 800 }); await p.waitForTimeout(300);
  await p.screenshot({ path: S + '/heads_end.png', fullPage: true });
  const fix = await p.$('[data-fix]');
  if (fix) { await fix.click(); await p.waitForTimeout(300); console.log('после правки слова счёт', await p.evaluate(() => JSON.parse(localStorage.getItem('quiz-heads')).scores)); }
  console.log('errors', errs); await b.close();
})();
