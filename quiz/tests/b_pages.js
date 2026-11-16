const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
(async () => {
  const b = await chromium.launch(); const errs = [];
  const p = await (await b.newContext({ viewport: { width: 390, height: 800 }, hasTouch: true })).newPage();
  p.on('pageerror', e => errs.push(e.message));
  for (const u of ['/', '/heads', '/learn', '/editor']) { await p.goto('http://localhost:8000' + u); await p.waitForTimeout(800); await p.tap('body', { position: { x: 10, y: 10 } }).catch(() => {}); }
  console.log('pages errors', errs); await b.close();
})();
