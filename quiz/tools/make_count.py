# Рисует картинки «На внимательность» (media/count/*.svg) и считает к ним правильные ответы.
# Запуск из папки quiz: python3 tools/make_count.py [файл.json] — в файл пишутся вопросы для add_questions.py.
# Случайность с постоянным зерном: повторный запуск рисует те же картинки.
import json, math, os, random, sys

OUT = os.path.join(os.path.dirname(__file__), "..", "media", "count")
W, H = 640, 400
INK = "#1d2433"
COLORS = {"красных": "#e5484d", "синих": "#3e7bfa", "жёлтых": "#f2a516", "зелёных": "#26a269", "фиолетовых": "#a855f7"}
COLOR_NAMES = {"красных": "Красных", "синих": "Синих", "жёлтых": "Жёлтых", "зелёных": "Зелёных", "фиолетовых": "Фиолетовых"}
rnd = random.Random(2024)
questions = []
os.makedirs(OUT, exist_ok=True)


def svg(name, body):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
                f'<rect width="{W}" height="{H}" rx="24" fill="#f7f4ea"/>{body}</svg>')
    return f"media/count/{name}.svg"


def add(name, body, q, answer, level, note, unit=None):
    item = {"q": q, "type": "number", "answer": answer, "theme": "На внимательность", "level": level,
            "image": svg(name, body), "note": note}
    if unit:
        item["unit"] = unit
    questions.append(item)


def add_choice(name, body, q, right, wrong, level, note):
    questions.append({"q": q, "right": right, "wrong": wrong, "theme": "На внимательность", "level": level,
                      "image": svg(name, body), "note": note})


def spots(n, r, margin=30, gap=6):
    """n точек, не налезающих друг на друга."""
    pts = []
    while len(pts) < n:
        x, y = rnd.uniform(margin + r, W - margin - r), rnd.uniform(margin + r, H - margin - r)
        if all(math.hypot(x - a, y - b) > 2 * r + gap for a, b in pts):
            pts.append((x, y))
    return pts


def polygon(cx, cy, r, k, rot=-90, fill="#fff"):
    pts = " ".join(f"{cx + r * math.cos(math.radians(rot + 360 * i / k)):.1f},{cy + r * math.sin(math.radians(rot + 360 * i / k)):.1f}" for i in range(k))
    return f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'


def shape(kind, x, y, r, fill):
    if kind == "circle":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{INK}" stroke-width="4"/>'
    if kind == "star":
        pts = " ".join(f"{x + (r if i % 2 == 0 else r * .45) * math.cos(math.radians(-90 + 36 * i)):.1f},"
                       f"{y + (r if i % 2 == 0 else r * .45) * math.sin(math.radians(-90 + 36 * i)):.1f}" for i in range(10))
        return f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    k = {"triangle": 3, "square": 4, "pentagon": 5, "hexagon": 6}[kind]
    return polygon(x, y, r, k, -90 if k != 4 else -45, fill)


def word(n, one, few, many):
    n10, n100 = n % 10, n % 100
    return one if n10 == 1 and n100 != 11 else few if 2 <= n10 <= 4 and not 12 <= n100 <= 14 else many


# 1. Точки одного цвета среди разноцветных
for i in range(9):
    names = list(COLORS)
    rnd.shuffle(names)
    target, others = names[0], names[1:1 + rnd.choice([2, 3])]
    counts = {target: rnd.randint(7, 15), **{o: rnd.randint(5, 13) for o in others}}
    kinds = [c for c, k in counts.items() for _ in range(k)]
    rnd.shuffle(kinds)
    body = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="15" fill="{COLORS[c]}" stroke="{INK}" stroke-width="3"/>'
                   for (x, y), c in zip(spots(len(kinds), 15), kinds))
    n = counts[target]
    add(f"color-dots-{i + 1}", body, f"Сколько {target} точек на картинке?", n, "normal" if n < 11 else "hard",
        f"{COLOR_NAMES[target]} точек — {n}. Всего на картинке {len(kinds)} {word(len(kinds), 'точка', 'точки', 'точек')}: проще считать, вычёркивая взглядом по рядам.")

# 2. Фигуры одного вида среди других
SHAPES = {"triangle": ("треугольников", "Треугольников"), "square": ("квадратов", "Квадратов"), "circle": ("кругов", "Кругов"),
          "star": ("звёздочек", "Звёздочек"), "pentagon": ("пятиугольников", "Пятиугольников"), "hexagon": ("шестиугольников", "Шестиугольников")}
for i in range(8):
    kinds_all = list(SHAPES)
    rnd.shuffle(kinds_all)
    target, others = kinds_all[0], kinds_all[1:4]
    counts = {target: rnd.randint(5, 11), **{o: rnd.randint(3, 8) for o in others}}
    items = [k for k, c in counts.items() for _ in range(c)]
    rnd.shuffle(items)
    body = "".join(shape(k, x, y, 22, rnd.choice(list(COLORS.values()))) for (x, y), k in zip(spots(len(items), 24, gap=8), items))
    n = counts[target]
    add(f"shapes-{i + 1}", body, f"Сколько {SHAPES[target][0]} на картинке?", n, "normal",
        f"{SHAPES[target][1]} — {n}. Цвет не важен: смотреть нужно на форму.")


# 3. Квадраты в сетке n×n: 1² + 2² + … + n²
def grid(cols, rows, size):
    x0, y0 = (W - cols * size) / 2, (H - rows * size) / 2
    lines = [f'<line x1="{x0 + c * size}" y1="{y0}" x2="{x0 + c * size}" y2="{y0 + rows * size}"/>' for c in range(cols + 1)]
    lines += [f'<line x1="{x0}" y1="{y0 + r * size}" x2="{x0 + cols * size}" y2="{y0 + r * size}"/>' for r in range(rows + 1)]
    return f'<rect x="{x0}" y="{y0}" width="{cols * size}" height="{rows * size}" fill="#fff"/><g stroke="{INK}" stroke-width="6" stroke-linecap="round">{"".join(lines)}</g>'


for n, level in ((2, "normal"), (4, "hard")):
    total = sum(k * k for k in range(1, n + 1))
    parts = " + ".join(f"{(n - k + 1) ** 2} ({k}×{k})" for k in range(1, n + 1))
    add(f"grid-squares-{n}", grid(n, n, 300 // n), "Сколько всего квадратов на картинке? Большие тоже считаются", total, level,
        f"Квадраты разного размера: {parts} — всего {total}.")

# 4. Прямоугольники в сетке a×b: C(a+1,2) · C(b+1,2)
for a, b, level in ((3, 1, "normal"), (3, 2, "hard"), (2, 2, "hard")):
    total = (a * (a + 1) // 2) * (b * (b + 1) // 2)
    size = min(420 // a, 280 // b)
    add(f"grid-rects-{a}x{b}", grid(a, b, size), "Сколько всего прямоугольников на картинке? Квадраты тоже считаются", total, level,
        f"По горизонтали можно выбрать {a * (a + 1) // 2} {word(a * (a + 1) // 2, 'полосу', 'полосы', 'полос')}, по вертикали — {b * (b + 1) // 2}: {a * (a + 1) // 2} × {b * (b + 1) // 2} = {total}.")


# 5. Треугольники-веер: из вершины k линий → (k+1)(k+2)/2; с поперечной линией — вдвое больше
def fan(k, cross):
    top, left, right = (320, 40), (70, 360), (570, 360)
    body = f'<polygon points="{top[0]},{top[1]} {left[0]},{left[1]} {right[0]},{right[1]}" fill="#fff" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
    for i in range(1, k + 1):
        x = left[0] + (right[0] - left[0]) * i / (k + 1)
        body += f'<line x1="{top[0]}" y1="{top[1]}" x2="{x:.1f}" y2="{left[1]}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    if cross:
        y = 220
        t = (y - top[1]) / (left[1] - top[1])
        body += f'<line x1="{top[0] + (left[0] - top[0]) * t:.1f}" y1="{y}" x2="{top[0] + (right[0] - top[0]) * t:.1f}" y2="{y}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    return body


for k, cross, level in ((1, False, "easy"), (3, False, "normal"), (4, False, "hard"), (2, True, "hard")):
    m = k + 1
    one = m * (m + 1) // 2
    total = one * (2 if cross else 1)
    note = f"Из вершины выходят {m} {word(m, 'часть', 'части', 'частей')}: треугольников из соседних частей 1 + 2 + … + {m} = {one}."
    if cross:
        note += f" Поперечная линия даёт столько же маленьких сверху: {one} + {one} = {total}."
    add(f"fan-{k}{'-cross' if cross else ''}", fan(k, cross), "Сколько всего треугольников на картинке?", total, level, note)

# 6. Кубики: сумма точек
PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (0, 2), (2, 0), (2, 2)],
        5: [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)], 6: [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)]}


def die(x, y, v, s=110):
    pad = s * .22
    body = f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="18" fill="#fff" stroke="{INK}" stroke-width="5"/>'
    for cx, cy in PIPS[v]:
        body += f'<circle cx="{x + pad + cx * (s - 2 * pad) / 2:.1f}" cy="{y + pad + cy * (s - 2 * pad) / 2:.1f}" r="{s * .085:.1f}" fill="{INK}"/>'
    return body


for i, n in enumerate((3, 4, 4, 5, 5)):
    vals = [rnd.randint(1, 6) for _ in range(n)]
    s, gap = 100, 22
    x0 = (W - n * s - (n - 1) * gap) / 2
    body = "".join(die(x0 + j * (s + gap), 150, v, s) for j, v in enumerate(vals))
    add(f"dice-{i + 1}", body, "Сколько всего точек на кубиках?", sum(vals), "normal" if n < 5 else "hard",
        f"{' + '.join(map(str, vals))} = {sum(vals)}.")


# 7. Буквы и цифры в таблице
def table(chars, cols):
    rows = math.ceil(len(chars) / cols)
    cw, ch = min(56, 560 / cols), min(60, 330 / rows)
    x0, y0 = (W - cols * cw) / 2, (H - rows * ch) / 2
    return "".join(f'<text x="{x0 + (i % cols + .5) * cw:.0f}" y="{y0 + (i // cols + .72) * ch:.0f}" text-anchor="middle" '
                   f'font-family="DejaVu Sans, Arial, sans-serif" font-size="{ch * .62:.0f}" font-weight="700" fill="{INK}">{c}</text>'
                   for i, c in enumerate(chars))


LETTER_SETS = [("О", "ОСЕВ"), ("Ш", "ШЩЖМ"), ("Р", "РВБЬ"), ("Ё", "ЁЕЭЄ".replace("Є", "Е")), ("Н", "НИПМ"), ("З", "З3ЭВ")]
for i, (target, pool) in enumerate(LETTER_SETS):
    n = rnd.randint(6, 12)
    others = [c for c in pool if c != target]
    chars = [target] * n + [rnd.choice(others) for _ in range(40 - n)]
    rnd.shuffle(chars)
    add(f"letters-{i + 1}", table(chars, 8), f"Сколько раз на картинке встречается буква «{target}»?", n, "hard",
        f"Буква «{target}» встречается {n} {word(n, 'раз', 'раза', 'раз')}; похожие буквы рядом нарочно сбивают с толку.")

for i, (target, pool) in enumerate((("6", "689"), ("1", "17I"), ("8", "830"), ("5", "56S"), ("2", "27Z"))):
    n = rnd.randint(6, 12)
    others = [c for c in pool if c != target]
    chars = [target] * n + [rnd.choice(others) for _ in range(36 - n)]
    rnd.shuffle(chars)
    add(f"digits-{i + 1}", table(chars, 9), f"Сколько раз на картинке встречается цифра {target}?", n, "hard",
        f"Цифра {target} встречается {n} {word(n, 'раз', 'раза', 'раз')}.")

# 8. Каких точек больше всего
for i in range(5):
    names = list(COLORS)
    rnd.shuffle(names)
    use = names[:4]
    base = rnd.randint(6, 9)
    counts = dict(zip(use, [base + 2, base, base - 1, base - 2]))
    kinds = [c for c, k in counts.items() for _ in range(k)]
    rnd.shuffle(kinds)
    body = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="15" fill="{COLORS[c]}" stroke="{INK}" stroke-width="3"/>'
                   for (x, y), c in zip(spots(len(kinds), 15), kinds))
    add_choice(f"most-{i + 1}", body, "Каких точек на картинке больше всего?", COLOR_NAMES[use[0]], [COLOR_NAMES[c] for c in use[1:]], "hard",
               ", ".join(f"{COLOR_NAMES[c].lower()} — {counts[c]}" for c in use).capitalize() + ".")

# 9. Вложенные фигуры
for i, k in enumerate((5, 7)):
    body = "".join(f'<circle cx="320" cy="200" r="{170 - j * (150 / k):.0f}" fill="none" stroke="{INK}" stroke-width="5"/>' for j in range(k))
    add(f"rings-{k}", body, "Сколько окружностей на картинке?", k, "normal", f"Окружности вложены друг в друга: их {k}.")
body, k = "", 6
for j in range(k):
    s = 320 - j * 50
    body += f'<rect x="{320 - s / 2}" y="{200 - s / 2 * 1.0}" width="{s}" height="{s}" fill="none" stroke="{INK}" stroke-width="5" transform="rotate({j * 15} 320 200)"/>'
add("nested-squares", body, "Сколько квадратов на картинке?", k, "normal", f"Квадраты повёрнуты и вложены друг в друга, но их всего {k}.")

# --- Вторая порция: своё зерно, чтобы картинки выше не менялись ---
rnd = random.Random(2025)
COLOR_ONE = {"красных": "красный", "синих": "синий", "жёлтых": "жёлтый", "зелёных": "зелёный", "фиолетовых": "фиолетовый"}

# 10. Фигуры заданного цвета и формы
for i in range(8):
    kinds_all, names = list(SHAPES), list(COLORS)
    rnd.shuffle(kinds_all)
    rnd.shuffle(names)
    kinds, cols = kinds_all[:3], names[:3]
    items = [(rnd.choice(kinds), rnd.choice(cols)) for _ in range(rnd.randint(24, 30))]
    tk, tc = kinds[0], cols[0]
    n = sum(1 for it in items if it == (tk, tc))
    if n < 3:  # гарантируем хотя бы три нужные фигуры
        items[:3 - n] = [(tk, tc)] * (3 - n)
        n = sum(1 for it in items if it == (tk, tc))
    rnd.shuffle(items)
    body = "".join(shape(k, x, y, 22, COLORS[c]) for (x, y), (k, c) in zip(spots(len(items), 24, gap=8), items))
    same_shape = sum(1 for k, _ in items if k == tk)
    add(f"color-shapes-{i + 1}", body, f"Сколько {tc} {SHAPES[tk][0]} на картинке?", n, "hard",
        f"{tc.capitalize()} {SHAPES[tk][0]} — {n}, хотя всего {SHAPES[tk][0]} {same_shape}: важны и цвет, и форма.")

# 11. Каких фигур больше всего
for i in range(5):
    kinds_all = list(SHAPES)
    rnd.shuffle(kinds_all)
    use = kinds_all[:4]
    base = rnd.randint(5, 7)
    counts = dict(zip(use, [base + 2, base, base - 1, base - 2]))
    items = [k for k, c in counts.items() for _ in range(c)]
    rnd.shuffle(items)
    body = "".join(shape(k, x, y, 22, rnd.choice(list(COLORS.values()))) for (x, y), k in zip(spots(len(items), 24, gap=8), items))
    add_choice(f"most-shapes-{i + 1}", body, "Каких фигур на картинке больше всего?", SHAPES[use[0]][1], [SHAPES[k][1] for k in use[1:]], "hard",
               ", ".join(f"{SHAPES[k][0]} — {counts[k]}" for k in use).capitalize() + ".")


# 12. Часы
def clock(h, m):
    body = f'<circle cx="320" cy="200" r="160" fill="#fff" stroke="{INK}" stroke-width="8"/>'
    for t in range(60):
        a = math.radians(t * 6 - 90)
        r1 = 136 if t % 5 == 0 else 146
        body += (f'<line x1="{320 + r1 * math.cos(a):.1f}" y1="{200 + r1 * math.sin(a):.1f}" x2="{320 + 152 * math.cos(a):.1f}" '
                 f'y2="{200 + 152 * math.sin(a):.1f}" stroke="{INK}" stroke-width="{5 if t % 5 == 0 else 2}"/>')
    for t in (12, 3, 6, 9):
        a = math.radians(t * 30 - 90)
        body += (f'<text x="{320 + 112 * math.cos(a):.0f}" y="{200 + 112 * math.sin(a) + 14:.0f}" text-anchor="middle" '
                 f'font-family="DejaVu Sans, Arial, sans-serif" font-size="40" font-weight="700" fill="{INK}">{t}</text>')
    ah, am = math.radians((h % 12 + m / 60) * 30 - 90), math.radians(m * 6 - 90)
    body += f'<line x1="320" y1="200" x2="{320 + 78 * math.cos(ah):.1f}" y2="{200 + 78 * math.sin(ah):.1f}" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>'
    body += f'<line x1="320" y1="200" x2="{320 + 128 * math.cos(am):.1f}" y2="{200 + 128 * math.sin(am):.1f}" stroke="#e5484d" stroke-width="7" stroke-linecap="round"/>'
    return body + f'<circle cx="320" cy="200" r="10" fill="{INK}"/>'


for i, (h, m) in enumerate(((2, 50), (4, 15), (7, 10), (10, 5), (11, 35), (8, 20))):
    t = lambda hh, mm: f"{(hh - 1) % 12 + 1}:{mm:02d}"
    swap = t(m // 5 or 12, (h % 12) * 5)  # перепутаны стрелки
    wrong = []
    for w in (swap, t(h + 1, m), t(h - 1, m), t(h, (60 - m) % 60)):
        if w != t(h, m) and w not in wrong:
            wrong.append(w)
    add_choice(f"clock-{i + 1}", clock(h, m), "Который час на часах?", t(h, m), wrong[:3], "normal",
               f"Короткая чёрная стрелка — часы, длинная красная — минуты: {t(h, m)}."
               + (" Часовая стрелка уже прошла больше половины пути к следующему числу." if m >= 30 else ""))


# 13. Домино
def domino(x, y, a, b, s=70):
    body = f'<rect x="{x}" y="{y}" width="{2 * s}" height="{s}" rx="12" fill="#fff" stroke="{INK}" stroke-width="5"/>'
    body += f'<line x1="{x + s}" y1="{y + 8}" x2="{x + s}" y2="{y + s - 8}" stroke="{INK}" stroke-width="4"/>'
    pad = s * .24
    for k, v in enumerate((a, b)):
        for cx, cy in PIPS.get(v, []):
            body += f'<circle cx="{x + k * s + pad + cx * (s - 2 * pad) / 2:.1f}" cy="{y + pad + cy * (s - 2 * pad) / 2:.1f}" r="{s * .08:.1f}" fill="{INK}"/>'
    return body


for i, n in enumerate((3, 3, 4, 4)):
    tiles = [(rnd.randint(0, 6), rnd.randint(0, 6)) for _ in range(n)]
    s, gap = 70, 16
    per_row = 2
    body = ""
    for j, (a, b) in enumerate(tiles):
        r, c = divmod(j, per_row)
        row_n = min(per_row, n - r * per_row)
        x0 = (W - row_n * 2 * s - (row_n - 1) * gap) / 2
        body += domino(x0 + c * (2 * s + gap), 110 + r * (s + 40), a, b, s)
    total = sum(a + b for a, b in tiles)
    add(f"domino-{i + 1}", body, "Сколько всего точек на костяшках домино?", total, "normal",
        " + ".join(f"{a} + {b}" for a, b in tiles) + f" = {total}. Пустая половинка — это ноль.")

# 14. Стрелки
ARROW = '<path d="M0 -26 L20 -4 H8 V26 H-8 V-4 H-20 Z" fill="{c}" transform="translate({x:.0f} {y:.0f}) rotate({r})"/>'
DIRS = {0: "вверх", 90: "вправо", 180: "вниз", 270: "влево"}
for i in range(6):
    cols, rows = 8, 5
    target = list(DIRS)[i % 4]
    rots = [rnd.choice(list(DIRS)) for _ in range(cols * rows)]
    n = rots.count(target)
    body = "".join(ARROW.format(c=INK, x=80 + (k % cols) * 69, y=64 + (k // cols) * 68, r=r) for k, r in enumerate(rots))
    add(f"arrows-{i + 1}", body, f"Сколько стрелок смотрят {DIRS[target]}?", n, "hard",
        f"Стрелок «{DIRS[target]}» — {n} из {cols * rows}.")

# 15. Слова в таблице
WORD_SETS = [("КОТ", ["КИТ", "ТОК", "КТО"]), ("НОС", ["СОН", "СОК", "НОЖ"]), ("ЛЕС", ["ВЕС", "СЕЛ", "ЛЕВ"]),
             ("МАК", ["РАК", "МАГ", "ЛАК"]), ("ДОМ", ["ДЫМ", "ДОК", "МОД"])]
for i, (target, pool) in enumerate(WORD_SETS):
    n = rnd.randint(5, 9)
    words = [target] * n + [rnd.choice(pool) for _ in range(25 - n)]
    rnd.shuffle(words)
    cols = 5
    body = "".join(f'<text x="{80 + (k % cols) * 120}" y="{78 + (k // cols) * 68}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" '
                   f'font-size="30" font-weight="700" fill="{INK}">{w}</text>' for k, w in enumerate(words))
    add(f"words-{i + 1}", body, f"Сколько раз на картинке написано слово «{target}»?", n, "hard",
        f"Слово «{target}» — {n} {word(n, 'раз', 'раза', 'раз')}; остальные слова из похожих букв.")

# 16. Монеты
for i in range(6):
    vals = [rnd.choice((1, 2, 5, 10)) for _ in range(rnd.randint(5, 8))]
    body = ""
    for (x, y), v in zip(spots(len(vals), 46, gap=10), vals):
        gold = v == 10
        body += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{40 + (v == 5) * 4}" fill="{"#e9c46a" if gold else "#d9dde3"}" stroke="{"#9c7a1c" if gold else "#7d8590"}" stroke-width="5"/>'
                 f'<text x="{x:.0f}" y="{y + 14:.0f}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-size="38" font-weight="700" fill="{INK}">{v}</text>')
    add(f"coins-{i + 1}", body, "Сколько рублей на картинке?", sum(vals), "normal" if len(vals) < 7 else "hard",
        f"{' + '.join(map(str, sorted(vals, reverse=True)))} = {sum(vals)} ₽.", unit="₽")

# 17. Ещё квадраты, прямоугольники и треугольники-веера
total = 14
add("grid-squares-3", grid(3, 3, 100), "Сколько всего квадратов на картинке? Большие тоже считаются", total, "hard",
    "Квадраты разного размера: 9 (1×1) + 4 (2×2) + 1 (3×3) — всего 14.")
for a, b, level in ((4, 1, "normal"), (4, 2, "hard")):
    total = (a * (a + 1) // 2) * (b * (b + 1) // 2)
    size = min(420 // a, 280 // b)
    add(f"grid-rects-{a}x{b}", grid(a, b, size), "Сколько всего прямоугольников на картинке? Квадраты тоже считаются", total, level,
        f"По горизонтали можно выбрать {a * (a + 1) // 2} {word(a * (a + 1) // 2, 'полосу', 'полосы', 'полос')}, по вертикали — {b * (b + 1) // 2}: {a * (a + 1) // 2} × {b * (b + 1) // 2} = {total}.")
for k, cross, level in ((5, False, "hard"), (3, True, "hard")):
    m = k + 1
    one = m * (m + 1) // 2
    total = one * (2 if cross else 1)
    note = f"Из вершины выходят {m} {word(m, 'часть', 'части', 'частей')}: треугольников из соседних частей 1 + 2 + … + {m} = {one}."
    if cross:
        note += f" Поперечная линия даёт столько же маленьких сверху: {one} + {one} = {total}."
    add(f"fan-{k}{'-cross' if cross else ''}", fan(k, cross), "Сколько всего треугольников на картинке?", total, level, note)


# 18. Треугольник, разбитый на маленькие: все треугольники (и «вверх», и «вниз»)
def tri_grid(n):
    top, left, right = (320, 40), (120, 360), (520, 360)
    lerp = lambda p, q, t: (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    body = f'<polygon points="{top[0]},{top[1]} {left[0]},{left[1]} {right[0]},{right[1]}" fill="#fff" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
    for i in range(1, n):
        t = i / n
        for a, b in ((lerp(top, left, t), lerp(top, right, t)), (lerp(left, top, t), lerp(left, right, t)), (lerp(right, top, t), lerp(right, left, t))):
            body += f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    return body


for n, total, parts in ((2, 5, "4 маленьких (3 «вверх» и 1 «вниз») + 1 большой = 5"),
                        (3, 13, "9 маленьких (6 «вверх» и 3 «вниз»), 3 средних и 1 большой: 9 + 3 + 1 = 13")):
    add(f"tri-grid-{n}", tri_grid(n), "Сколько всего треугольников на картинке?", total, "hard", f"Треугольники разного размера: {parts}.")

# 19. Чётные числа
for i in range(3):
    nums = [rnd.randint(1, 99) for _ in range(20)]
    n = sum(1 for v in nums if v % 2 == 0)
    body = "".join(f'<rect x="{30 + (k % 5) * 118}" y="{36 + (k // 5) * 84}" width="104" height="68" rx="12" fill="#fff" stroke="{INK}" stroke-width="3"/>'
                   f'<text x="{82 + (k % 5) * 118}" y="{85 + (k // 5) * 84}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" '
                   f'font-size="40" font-weight="700" fill="{INK}">{v}</text>' for k, v in enumerate(nums))
    add(f"even-{i + 1}", body, "Сколько чётных чисел на картинке?", n, "hard",
        f"Чётных чисел — {n}: смотреть нужно только на последнюю цифру (0, 2, 4, 6, 8).")

if len(sys.argv) > 1:
    json.dump(questions, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("картинок:", len(questions))
