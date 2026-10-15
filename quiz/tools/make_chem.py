# Рисует таблицу Менделеева и карточки элементов для вопросов по химии → media/chem/*.svg.
# Таблица — только символы, без номеров (иначе вопрос «Сколько элементов?» подсказан последней клеткой).
# Запуск из папки quiz: python3 tools/make_chem.py
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "chem")
SYMBOLS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
           "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu "
           "Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr "
           "Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
# цвета групп: щелочные, щёлочноземельные, переходные, другие металлы, полуметаллы, неметаллы, галогены, благородные газы,
# лантаноиды, актиноиды
COLORS = {"alk": "#ff8a65", "ae": "#ffb74d", "tr": "#f4d35e", "pt": "#a5d6a7", "md": "#80cbc4", "nm": "#81d4fa",
          "hal": "#90caf9", "ng": "#ce93d8", "la": "#f8bbd0", "ac": "#e1bee7"}
SETS = {"alk": "Li Na K Rb Cs Fr", "ae": "Be Mg Ca Sr Ba Ra", "md": "B Si Ge As Sb Te",
        "nm": "H C N O P S Se", "hal": "F Cl Br I At Ts", "ng": "He Ne Ar Kr Xe Rn Og",
        "pt": "Al Ga In Sn Tl Pb Bi Po Nh Fl Mc Lv"}


def kind(z, sym):
    if 57 <= z <= 71:
        return "la"
    if 89 <= z <= 103:
        return "ac"
    return next((k for k, v in SETS.items() if sym in v.split()), "tr")


def place(z):
    """Строка и столбец (с 1) в длинной форме таблицы; лантаноиды и актиноиды — отдельными строками 8 и 9."""
    if z == 1:
        return 1, 1
    if z == 2:
        return 1, 18
    for start, row in ((3, 2), (11, 3)):
        if start <= z < start + 8:
            i = z - start
            return row, i + 1 if i < 2 else i + 11
    for start, row in ((19, 4), (37, 5)):
        if start <= z < start + 18:
            return row, z - start + 1
    for start, row in ((55, 6), (87, 7)):
        if not start <= z < start + 32:
            continue
        if z < start + 2:
            return row, z - start + 1
        if z <= start + 16:  # La…Lu, Ac…Lr
            return row + 2, z - start + 1
        return row, z - start - 13
    raise ValueError(z)


def table():
    cell, gap, top = 46, 3, 14
    w, h = 18 * (cell + gap) + 20, 9 * (cell + gap) + top + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
           f'<rect width="{w}" height="{h}" rx="18" fill="#f3f1ea"/>']
    for z, sym in enumerate(SYMBOLS, 1):
        r, c = place(z)
        x = 10 + (c - 1) * (cell + gap)
        y = top + (r - 1) * (cell + gap) + (14 if r >= 8 else 0)
        out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="6" fill="{COLORS[kind(z, sym)]}" stroke="#00000022"/>'
                   f'<text x="{x + cell / 2}" y="{y + cell / 2 + 7}" text-anchor="middle" font-family="Arial, sans-serif" '
                   f'font-weight="700" font-size="20" fill="#1b1f3a">{sym}</text>')
    out.append("</svg>\n")
    return "".join(out)


def tile(sym, number, name):
    """Клетка таблицы крупно: номер, символ, название («?» — то, что нужно угадать)."""
    z = SYMBOLS.index(sym) + 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">'
            f'<rect x="10" y="10" width="280" height="280" rx="26" fill="{COLORS[kind(z, sym)]}" stroke="#1b1f3a" stroke-width="6"/>'
            f'<text x="34" y="66" font-family="Arial, sans-serif" font-weight="700" font-size="40" fill="#1b1f3a">{number}</text>'
            f'<text x="150" y="190" text-anchor="middle" font-family="Arial, sans-serif" font-weight="800" font-size="130" fill="#1b1f3a">{sym}</text>'
            f'<text x="150" y="262" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="34" fill="#1b1f3a">{name}</text>'
            "</svg>\n")


FILES = {
    "table": table(),
    "o": tile("O", 8, "?"),      # «Какой элемент обозначается символом O?»
    "fe": tile("Fe", 26, "?"),   # «… символом Fe?»
    "au": tile("Au", "?", "Золото"),  # «Какой номер у золота?»
}
os.makedirs(OUT, exist_ok=True)
for name, svg in FILES.items():
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg)
print("картинок:", len(FILES), "→", os.path.normpath(OUT))
