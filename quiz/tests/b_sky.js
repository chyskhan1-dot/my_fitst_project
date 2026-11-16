// Гора в четырёх временах суток: ТВ и телефон, подъём и салют на вершине
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const S = process.argv[2], B = 'http://localhost:8000';
(async () => {
  const b = await chromium.launch(); const errs = [];
  for (const [vw, vh, compact, tag] of [[1280, 720, false, 'tv'], [390, 800, true, 'ph']]) {
    const p = await (await b.newContext({ viewport: { width: vw, height: vh } })).newPage();
    p.on('pageerror', e => errs.push(tag + ': ' + e.message));
    await p.goto(B + '/static/soundtest.html');
    await p.evaluate(() => { document.body.innerHTML = '<div id="m" style="padding:16px;--muted:#aab;--accent:#ffd23f;color:#fff;font:16px system-ui"></div>'; document.body.style.background = '#12163a'; });
    for (const f of ['emoji.js', 'avatar.js', 'rope.js']) await p.addScriptTag({ url: '/static/' + f });
    for (const [sky, prog, night] of [['dawn', .1], ['day', .5], ['dusk', .75], ['night', .95, true]]) {
      await p.evaluate(([sky, prog, night, compact]) => {
        const av = ['🦊', '🐼', '🐯', '🦁', '🐸', '🐵'], names = ['Аня', 'Борис', 'Вика', 'Гена', 'Даша', 'Егор'];
        const k = prog * 50;
        const rows = names.map((n, i) => ({ name: n, score: Math.max(0, Math.round(k - i * 4 + (i === 0 && night ? 50 : 0))), last: 5 - i, color: QuizAva.PALETTE[i], me: i === 2 }))
          .map((r) => ({ ...r, score: Math.min(50, r.score), face: QuizAva.html({ avatar: av[names.indexOf(r.name)], color: r.color, name: r.name }) }));
        rows.sort((a, b) => b.score - a.score);
        document.getElementById('m').innerHTML = QuizRope.html(rows, 50, sky + Math.random(), { race: true, compact, height: compact ? '60vh' : '470px', progress: prog, night });
        QuizRope.climb(document.getElementById('m'));
      }, [sky, prog, !!night, compact]);
      await p.waitForTimeout(sky === 'night' ? 2900 : 3300);
      await p.screenshot({ path: `${S}/sky_${tag}_${sky}.png` });
    }
  }
  console.log('errors', errs); await b.close();
})();
