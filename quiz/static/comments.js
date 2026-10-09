// Комментарии к таблице лидеров: кто взлетел, кто упал, серии, самый быстрый.
// Общие для экрана ведущего и телефонов.
(function () {
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const plural = (n, one, few, many) => (n % 10 === 1 && n % 100 !== 11 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? few : many);
  const places = (n) => plural(n, "место", "места", "мест");
  function comments(s) {
    const pick = (list, salt) => list[(s.index + salt.length) % list.length]; // фраза не меняется при перерисовке
    const b = (t) => `<b>${esc(t)}</b>`;
    const rows = s.players.map((p, i) => ({ ...p, place: i + 1, d: p.prev ? p.prev - (i + 1) : 0 }));
    const out = [], first = s.index === 0; // после первого вопроса места ещё не с чем сравнивать
    const leader = rows[0];
    if (!first && leader && leader.prev > 1 && leader.score > 0) out.push(pick([`👑 ${b(leader.name)} захватывает лидерство!`, `👑 Новый лидер — ${b(leader.name)}!`, `👑 ${b(leader.name)} выходит на первое место!`], leader.name));
    const lost = rows.find((r) => r.prev === 1 && r.place > 1);
    if (!first && lost) out.push(pick([`😱 ${b(lost.name)} теряет лидерство`, `😱 ${b(lost.name)} уступает первое место`], lost.name));
    const up = first ? null : rows.filter((r) => r.d >= 2 && r !== (leader && leader.prev > 1 ? leader : null)).sort((a, c) => c.d - a.d)[0];
    if (up) out.push(pick([`🚀 ${b(up.name)} взлетает на ${up.d} ${places(up.d)} — теперь ${up.place}-е`, `🚀 Рывок! ${b(up.name)} +${up.d} ${places(up.d)}`, `🚀 ${b(up.name)} обходит сразу ${up.d} соперников`], up.name));
    const small = !first && !up && rows.find((r) => r.d === 1 && r.place > 1);
    if (small) out.push(pick([`⬆️ ${b(small.name)} поднимается на ${small.place}-е место`, `⬆️ ${b(small.name)} обходит соперника — теперь ${small.place}-е`], small.name));
    const down = first ? null : rows.filter((r) => r.d <= -2 && r !== lost).sort((a, c) => a.d - c.d)[0];
    if (down) out.push(pick([`📉 ${b(down.name)} теряет ${-down.d} ${places(-down.d)} и опускается на ${down.place}-е`, `📉 Ой! ${b(down.name)} падает на ${-down.d} ${places(-down.d)}`, `📉 ${b(down.name)} сдаёт позиции: −${-down.d} ${places(-down.d)}`], down.name));
    const hot = rows.filter((r) => r.streak >= 3).sort((a, c) => c.streak - a.streak)[0];
    if (hot) out.push(pick([`🔥 ${b(hot.name)}: ${hot.streak} верных подряд!`, `🔥 ${b(hot.name)} не остановить — серия из ${hot.streak}`], hot.name));
    const bet = rows.filter((r) => r.doubled).sort((a, c) => Math.abs(c.last) - Math.abs(a.last))[0];
    if (bet) out.push(bet.last > 0 ? `🎲 Ставка ×2 сыграла: ${b(bet.name)} +${bet.last}` : `💸 Ставка ×2 не сыграла: ${b(bet.name)} ${bet.last ? "−" + -bet.last : "остаётся при своих"}`);
    if (s.fastest) out.push(`⚡ Быстрее всех — ${b(s.fastest.name)}, ${String(s.fastest.time).replace(".", ",")} с`);
    if (s.answers_total && !s.right_total) out.push(pick(["😶 Этот вопрос не взял никто", "🤯 Вопрос оказался никому не по зубам"], "x"));
    else if (s.answers_total >= 2 && s.right_total === s.players.filter((p) => p.online).length) out.push("💯 Все ответили верно!");
    if (rows.length >= 2 && rows[0].score > 0 && rows[0].score - rows[1].score <= 200) out.push(`🤏 Борьба за первое место: разрыв всего ${rows[0].score - rows[1].score} очков`);
    const big = rows.filter((r) => r.last >= 900 && !r.doubled).sort((a, c) => c.last - a.last)[0];
    if (out.length < 3 && big && big !== hot && (!s.fastest || s.fastest.name !== big.name)) out.push(`💥 ${b(big.name)} забирает +${big.last}`);
    return out.slice(0, 4);
  }

  window.QuizComments = { comments, plural };
})();
