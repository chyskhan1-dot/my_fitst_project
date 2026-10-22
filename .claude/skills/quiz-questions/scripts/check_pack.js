// Проверка пакета викторины и пересборка CSV-копии.
// Запуск из корня репозитория: node .claude/skills/quiz-questions/scripts/check_pack.js [имя пакета, по умолчанию general]
// Пишет quiz/packs/<имя>.csv из .json через static/pack.js и проверяет, что CSV читается обратно в то же самое.
global.window = {};
require(process.cwd() + '/quiz/static/pack.js');
const P = window.QuizPack, fs = require('fs');
const name = process.argv[2] || 'general', base = process.cwd() + '/quiz/packs/' + name;
const pack = JSON.parse(fs.readFileSync(base + '.json', 'utf8'));
const problems = [], pos = [0, 0, 0, 0], seen = new Map();
let noNote = 0;
pack.questions.forEach((q, i) => {
  const at = `вопрос ${i + 1} «${q.q.slice(0, 50)}»`, type = q.type || 'choice';
  if (!q.theme) problems.push(`${at}: нет темы`);
  if (!['easy', 'normal', 'hard'].includes(q.level)) problems.push(`${at}: нет сложности`);
  if (!q.note) noNote++;
  if (type === 'choice') {
    if (!Array.isArray(q.options) || q.options.length < 2 || !(q.answer >= 0 && q.answer < q.options.length)) problems.push(`${at}: варианты или ответ`);
    else { if (q.options.length === 4) pos[q.answer]++; if (new Set(q.options).size !== q.options.length) problems.push(`${at}: одинаковые варианты`); }
  }
  if (type === 'map' && q.theme !== 'Где на карте') problems.push(`${at}: карта не в теме «Где на карте»`);
  for (const v of [q.image, q.answer_image, ...(q.images || [])]) {
    if (v && !/^(https?:|data:)/.test(v) && !fs.existsSync(process.cwd() + '/quiz/' + v)) problems.push(`${at}: нет файла ${v}`);
  }
  const key = q.q.trim().toLowerCase() + (q.image || '') + (q.emoji || '') + (q.images || []).join('|'); // один текст с разными картинками или ребусами — разные вопросы
  if (seen.has(key)) problems.push(`${at}: повтор вопроса ${seen.get(key) + 1}`); else seen.set(key, i);
});
const csv = P.packToCSV(pack);
fs.writeFileSync(base + '.csv', '﻿' + csv);
const back = P.csvToPack('﻿' + csv, pack.title);
const norm = (qs) => JSON.stringify(qs.map((q) => [q.type || 'choice', q.q, q.options || [], q.answer ?? null, q.theme || '', q.level || '', q.unit || '', q.place || '', q.answer_image || '', q.note || '']));
if (norm(pack.questions) !== norm(back.questions)) problems.push('CSV не совпадает с JSON после пересборки');
const spread = Math.max(...pos) - Math.min(...pos);
console.log(`${name}: вопросов ${pack.questions.length}, верные по позициям ${pos.join('/')}${spread > 4 ? ' — НЕРАВНОМЕРНО' : ''}${noNote ? `, без пояснения: ${noNote}` : ''}`);
if (spread > 4) problems.push('правильные ответы разложены неравномерно');
if (problems.length) { console.log('Проблемы:\n  ' + problems.slice(0, 40).join('\n  ')); process.exit(1); }
console.log('Всё в порядке, CSV пересобран.');
