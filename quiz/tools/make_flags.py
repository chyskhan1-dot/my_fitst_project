# Рисует флаги стран в media/flags/*.svg — только флаги из простых фигур (без гербов).
# Запуск из папки quiz: python3 tools/make_flags.py  (рядом появится flags_meta.json со списком стран)
import json, math, os, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "flags")
FLAGS = {}  # код -> (название по-русски, часть света, сложность, svg)


def svg(w, h, body, defs=""):
    d = f"<defs>{defs}</defs>" if defs else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{d}{body}</svg>\n'


def rect(x, y, w, h, c):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{c}"/>'


def hbands(w, h, colors, weights=None):
    weights = weights or [1] * len(colors)
    total, y, out = sum(weights), 0.0, []
    for c, k in zip(colors, weights):
        bh = h * k / total
        out.append(rect(0, y, w, bh + 0.5, c))
        y += bh
    return "".join(out)


def vbands(w, h, colors, weights=None):
    weights = weights or [1] * len(colors)
    total, x, out = sum(weights), 0.0, []
    for c, k in zip(colors, weights):
        bw = w * k / total
        out.append(rect(x, 0, bw + 0.5, h, c))
        x += bw
    return "".join(out)


def star_pts(cx, cy, r, n=5, rot=0.0, inner=None):
    inner = r * (0.382 if n == 5 else 0.5) if inner is None else inner
    pts = []
    for k in range(2 * n):
        a = math.radians(-90 + rot + k * 180 / n)
        rr = r if k % 2 == 0 else inner
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)


def star(cx, cy, r, c, n=5, rot=0.0, inner=None, extra=""):
    return f'<polygon points="{star_pts(cx, cy, r, n, rot, inner)}" fill="{c}"{extra}/>'


def poly(pts, c):
    return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{c}"/>'


def circle(cx, cy, r, c):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{c}"/>'


def crescent(mid, cx, cy, r, cx2, cy2, r2, c):
    """Полумесяц: круг, из которого вырезан другой круг (маска, чтобы работало на любом фоне)."""
    defs = (f'<mask id="{mid}"><rect x="-10%" y="-10%" width="120%" height="120%" fill="#fff"/>'
            f'<circle cx="{cx2:.1f}" cy="{cy2:.1f}" r="{r2:.1f}" fill="#000"/></mask>')
    return defs, f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{c}" mask="url(#{mid})"/>'


def union_jack(x, y, w, h):
    """Британский флаг в прямоугольнике (как в каноническом SVG 60×30)."""
    return (f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 60 30" preserveAspectRatio="none">'
            '<clipPath id="uj-t"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath>'
            '<rect width="60" height="30" fill="#012169"/>'
            '<path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>'
            '<path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#uj-t)" stroke="#C8102E" stroke-width="4"/>'
            '<path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>'
            '<path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></svg>')


def add(code, name, region, level, content):
    FLAGS[code] = (name, region, level, content)


E, A, F, AM, O = "Европа", "Азия", "Африка", "Америка", "Океания"

# ---------- горизонтальные полосы ----------
for code, name, reg, lvl, w, h, cols, wts in [
    ("russia", "Россия", E, "easy", 900, 600, ["#fff", "#0039A6", "#D52B1E"], None),
    ("germany", "Германия", E, "easy", 1000, 600, ["#000", "#DD0000", "#FFCE00"], None),
    ("netherlands", "Нидерланды", E, "normal", 900, 600, ["#AE1C28", "#fff", "#21468B"], None),
    ("austria", "Австрия", E, "normal", 900, 600, ["#ED2939", "#fff", "#ED2939"], None),
    ("hungary", "Венгрия", E, "normal", 1200, 600, ["#CE2939", "#fff", "#477050"], None),
    ("bulgaria", "Болгария", E, "normal", 1000, 600, ["#fff", "#00966E", "#D62612"], None),
    ("lithuania", "Литва", E, "normal", 1000, 600, ["#FDB913", "#006A44", "#C1272D"], None),
    ("estonia", "Эстония", E, "normal", 1100, 700, ["#0072CE", "#000", "#fff"], None),
    ("luxembourg", "Люксембург", E, "hard", 1000, 600, ["#EA141D", "#fff", "#51ADDA"], None),
    ("latvia", "Латвия", E, "hard", 1000, 500, ["#9E3039", "#fff", "#9E3039"], [2, 1, 2]),
    ("poland", "Польша", E, "easy", 800, 500, ["#fff", "#DC143C"], None),
    ("ukraine", "Украина", E, "easy", 900, 600, ["#0057B7", "#FFD700"], None),
    ("armenia", "Армения", A, "normal", 1200, 600, ["#D90012", "#0033A0", "#F2A800"], None),
    ("yemen", "Йемен", A, "hard", 900, 600, ["#CE1126", "#fff", "#000"], None),
    ("indonesia", "Индонезия", A, "normal", 900, 600, ["#FF0000", "#fff"], None),
    ("thailand", "Таиланд", A, "normal", 900, 600, ["#A51931", "#F4F5F8", "#2D2A4A", "#F4F5F8", "#A51931"], [1, 1, 2, 1, 1]),
    ("sierra-leone", "Сьерра-Леоне", F, "hard", 900, 600, ["#1EB53A", "#fff", "#0072C6"], None),
    ("gabon", "Габон", F, "hard", 800, 600, ["#009E60", "#FCD116", "#3A75C4"], None),
    ("mauritius", "Маврикий", F, "hard", 900, 600, ["#EA2839", "#1A206D", "#FFD500", "#00A551"], None),
    ("botswana", "Ботсвана", F, "hard", 900, 600, ["#75AADB", "#fff", "#000", "#fff", "#75AADB"], [9, 1, 4, 1, 9]),
    ("colombia", "Колумбия", AM, "normal", 900, 600, ["#FCD116", "#003893", "#CE1126"], [2, 1, 1]),
]:
    add(code, name, reg, lvl, svg(w, h, hbands(w, h, cols, wts)))

# ---------- вертикальные полосы ----------
for code, name, reg, lvl, w, h, cols in [
    ("france", "Франция", E, "easy", 900, 600, ["#0055A4", "#fff", "#EF4135"]),
    ("italy", "Италия", E, "easy", 900, 600, ["#009246", "#fff", "#CE2B37"]),
    ("ireland", "Ирландия", E, "normal", 1200, 600, ["#169B62", "#fff", "#FF883E"]),
    ("belgium", "Бельгия", E, "normal", 900, 780, ["#000", "#FDDA24", "#EF3340"]),
    ("romania", "Румыния", E, "normal", 900, 600, ["#002B7F", "#FCD116", "#CE1126"]),
    ("nigeria", "Нигерия", F, "normal", 1200, 600, ["#008751", "#fff", "#008751"]),
    ("mali", "Мали", F, "hard", 900, 600, ["#14B53A", "#FCD116", "#CE1126"]),
    ("guinea", "Гвинея", F, "hard", 900, 600, ["#CE1126", "#FCD116", "#009460"]),
    ("ivory-coast", "Кот-д’Ивуар", F, "hard", 900, 600, ["#F77F00", "#fff", "#009E60"]),
    ("peru", "Перу", AM, "normal", 900, 600, ["#D91023", "#fff", "#D91023"]),
]:
    add(code, name, reg, lvl, svg(w, h, vbands(w, h, cols)))

# ---------- кресты ----------
def nordic(w, h, bg, cross, vx, cw, inner=None, ivx=None, icw=None):
    hy = (h - cw) / 2
    out = rect(0, 0, w, h, bg) + rect(vx, 0, cw, h, cross) + rect(0, hy, w, cw, cross)
    if inner:
        ihy = (h - icw) / 2
        out += rect(ivx, 0, icw, h, inner) + rect(0, ihy, w, icw, inner)
    return out

add("denmark", "Дания", E, "normal", svg(740, 560, nordic(740, 560, "#C8102E", "#fff", 240, 80)))
add("sweden", "Швеция", E, "easy", svg(800, 500, nordic(800, 500, "#006AA7", "#FECC00", 250, 100)))
add("norway", "Норвегия", E, "normal", svg(1100, 800, nordic(1100, 800, "#BA0C2F", "#fff", 300, 200, "#00205B", 350, 100)))
add("finland", "Финляндия", E, "normal", svg(900, 550, nordic(900, 550, "#fff", "#002F6C", 250, 150)))
add("iceland", "Исландия", E, "hard", svg(1000, 720, nordic(1000, 720, "#02529C", "#fff", 280, 160, "#DC1E35", 320, 80)))
add("switzerland", "Швейцария", E, "easy", svg(640, 640, rect(0, 0, 640, 640, "#DA291C") + rect(260, 120, 120, 400, "#fff") + rect(120, 260, 400, 120, "#fff")))
g = hbands(900, 600, ["#0D5EAF", "#fff"] * 4 + ["#0D5EAF"])
s6 = 600 / 9
g += rect(0, 0, 5 * s6, 5 * s6, "#0D5EAF") + rect(2 * s6, 0, s6, 5 * s6, "#fff") + rect(0, 2 * s6, 5 * s6, s6, "#fff")
add("greece", "Греция", E, "normal", svg(900, 600, g))

# ---------- круги ----------
add("japan", "Япония", A, "easy", svg(900, 600, rect(0, 0, 900, 600, "#fff") + circle(450, 300, 180, "#BC002D")))
add("bangladesh", "Бангладеш", A, "hard", svg(1000, 600, rect(0, 0, 1000, 600, "#006A4E") + circle(450, 300, 200, "#F42A41")))
add("palau", "Палау", O, "hard", svg(800, 500, rect(0, 0, 800, 500, "#4AADD6") + circle(350, 250, 150, "#FFDE00")))
add("laos", "Лаос", A, "hard", svg(900, 600, hbands(900, 600, ["#CE1126", "#002868", "#CE1126"], [1, 2, 1]) + circle(450, 300, 120, "#fff")))

# ---------- звёзды ----------
add("vietnam", "Вьетнам", A, "normal", svg(900, 600, rect(0, 0, 900, 600, "#DA251D") + star(450, 300, 180, "#FFFF00")))
add("somalia", "Сомали", F, "hard", svg(900, 600, rect(0, 0, 900, 600, "#4189DD") + star(450, 300, 160, "#fff")))
add("myanmar", "Мьянма", A, "hard", svg(900, 600, hbands(900, 600, ["#FECB00", "#34B233", "#EA2839"]) + star(450, 330, 250, "#fff")))
add("ghana", "Гана", F, "normal", svg(900, 600, hbands(900, 600, ["#CE1126", "#FCD116", "#006B3F"]) + star(450, 300, 100, "#000")))
add("burkina-faso", "Буркина-Фасо", F, "hard", svg(900, 600, hbands(900, 600, ["#EF2B2D", "#009E49"]) + star(450, 300, 100, "#FCD116")))
add("cameroon", "Камерун", F, "hard", svg(900, 600, vbands(900, 600, ["#007A5E", "#CE1126", "#FCD116"]) + star(450, 300, 90, "#FCD116")))
add("senegal", "Сенегал", F, "normal", svg(900, 600, vbands(900, 600, ["#00853F", "#FDEF42", "#E31B23"]) + star(450, 300, 100, "#00853F")))
add("guinea-bissau", "Гвинея-Бисау", F, "hard", svg(1200, 600, hbands(1200, 600, ["#FCD116", "#009E49"]) + rect(0, 0, 400, 600, "#CE1126") + star(200, 300, 100, "#000")))
t = hbands(809, 500, ["#006A4E", "#FFCE00"] * 2 + ["#006A4E"]) + rect(0, 0, 300, 300, "#D21034") + star(150, 150, 100, "#fff")
add("togo", "Того", F, "hard", svg(809, 500, t))
c = hbands(1000, 500, ["#002A8F", "#fff"] * 2 + ["#002A8F"]) + poly([(0, 0), (433, 250), (0, 500)], "#CF142B") + star(144, 250, 70, "#fff")
add("cuba", "Куба", AM, "normal", svg(1000, 500, c))
c = hbands(900, 600, ["#fff", "#D52B1E"]) + rect(0, 0, 300, 300, "#0039A6") + star(150, 150, 75, "#fff")
add("chile", "Чили", AM, "normal", svg(900, 600, c))
c = (rect(0, 0, 450, 300, "#fff") + rect(450, 0, 450, 300, "#D21034") + rect(0, 300, 450, 300, "#005293") + rect(450, 300, 450, 300, "#fff")
     + star(225, 150, 60, "#005293") + star(675, 450, 60, "#D21034"))
add("panama", "Панама", AM, "hard", svg(900, 600, c))

# США: 13 полос, 50 звёзд
u = hbands(1235, 650, ["#B22234", "#fff"] * 6 + ["#B22234"]) + rect(0, 0, 494, 350, "#3C3B6E")
for r in range(9):
    cols = [1, 3, 5, 7, 9, 11] if r % 2 == 0 else [2, 4, 6, 8, 10]
    for k in cols:
        u += star(494 / 12 * k, 35 * (r + 1), 20, "#fff")
add("usa", "США", AM, "easy", svg(1235, 650, u))

# Китай
ch = rect(0, 0, 900, 600, "#EE1C25") + star(150, 150, 90, "#FFFF00")
for x, y in [(10, 2), (12, 4), (12, 7), (10, 9)]:
    a = math.degrees(math.atan2(5 - y, 5 - x))
    ch += star(x * 30, y * 30, 30, "#FFFF00", rot=a + 90)
add("china", "Китай", A, "easy", svg(900, 600, ch))

# КНДР
k = hbands(1200, 600, ["#024FA2", "#fff", "#ED1C27", "#fff", "#024FA2"], [6, 1, 22, 1, 6]) + circle(400, 300, 120, "#fff") + star(400, 300, 115, "#ED1C27")
add("north-korea", "КНДР", A, "normal", svg(1200, 600, k))

# ---------- треугольники и клинья ----------
add("czechia", "Чехия", E, "normal", svg(900, 600, hbands(900, 600, ["#fff", "#D7141A"]) + poly([(0, 0), (450, 300), (0, 600)], "#11457E")))
add("sudan", "Судан", F, "hard", svg(1200, 600, hbands(1200, 600, ["#D21034", "#fff", "#000"]) + poly([(0, 0), (400, 300), (0, 600)], "#007229")))
add("kuwait", "Кувейт", A, "hard", svg(1200, 600, hbands(1200, 600, ["#007A3D", "#fff", "#CE1126"]) + poly([(0, 0), (300, 200), (300, 400), (0, 600)], "#000")))
add("uae", "ОАЭ", A, "normal", svg(1200, 600, hbands(1200, 600, ["#00732F", "#fff", "#000"]) + rect(0, 0, 300, 600, "#FF0000")))
add("bahamas", "Багамы", AM, "hard", svg(1200, 600, hbands(1200, 600, ["#00ABC9", "#FFC72C", "#00ABC9"]) + poly([(0, 0), (520, 300), (0, 600)], "#000")))
j = (rect(0, 0, 1200, 600, "#009B3A") + poly([(0, 0), (600, 300), (0, 600)], "#000") + poly([(1200, 0), (600, 300), (1200, 600)], "#000")
     + '<path d="M0,0 L1200,600 M1200,0 L0,600" stroke="#FED100" stroke-width="100"/>')
add("jamaica", "Ямайка", AM, "normal", svg(1200, 600, j))
tz = (poly([(0, 0), (900, 0), (0, 600)], "#1EB53A") + poly([(900, 0), (900, 600), (0, 600)], "#00A3DD")
      + '<path d="M0,600 L900,0" stroke="#FCD116" stroke-width="190"/><path d="M0,600 L900,0" stroke="#000" stroke-width="130"/>')
add("tanzania", "Танзания", F, "hard", svg(900, 600, tz))
add("congo", "Республика Конго", F, "hard", svg(900, 600, rect(0, 0, 900, 600, "#FBDE4A") + poly([(0, 0), (600, 0), (0, 600)], "#009543") + poly([(300, 600), (900, 0), (900, 600)], "#DC241F")))
add("benin", "Бенин", F, "hard", svg(900, 600, hbands(900, 600, ["#FCD116", "#E8112D"]) + rect(0, 0, 360, 600, "#008751")))
add("madagascar", "Мадагаскар", F, "normal", svg(900, 600, hbands(900, 600, ["#FC3D32", "#007E3A"]) + rect(0, 0, 300, 600, "#fff")))

def serrated(w, h, white_w, tip, points, bg):
    pts = [(0, 0), (white_w, 0)]
    for i in range(points):
        pts += [(tip, (i + 0.5) * h / points), (white_w, (i + 1) * h / points)]
    pts.append((0, h))
    return rect(0, 0, w, h, bg) + poly(pts, "#fff")

add("qatar", "Катар", A, "hard", svg(1120, 440, serrated(1120, 440, 320, 440, 9, "#8A1538")))
add("bahrain", "Бахрейн", A, "hard", svg(1000, 600, serrated(1000, 600, 250, 400, 5, "#CE1126")))

# ---------- полумесяцы ----------
d1, cr = crescent("m", 450, 300, 150, 487.5, 300, 120, "#fff")
add("turkey", "Турция", A, "easy", svg(900, 600, rect(0, 0, 900, 600, "#E30A17") + cr + star(600, 300, 75, "#fff", rot=-90), d1))
d1, cr = crescent("m", 300, 300, 150, 340, 300, 125, "#D21034")
add("algeria", "Алжир", F, "normal", svg(900, 600, vbands(900, 600, ["#006233", "#fff"]) + cr + star(465, 300, 75, "#D21034", rot=-90), d1))
d1, cr = crescent("m", 450, 300, 110, 480, 300, 88, "#E70013")
add("tunisia", "Тунис", F, "normal", svg(900, 600, rect(0, 0, 900, 600, "#E70013") + circle(450, 300, 150, "#fff") + cr + star(495, 300, 55, "#E70013", rot=-90), d1))
d1, cr = crescent("m", 560, 300, 95, 590, 300, 76, "#fff")
add("libya", "Ливия", F, "hard", svg(1200, 600, hbands(1200, 600, ["#E70013", "#000", "#239E46"], [1, 2, 1]) + cr + star(655, 300, 42, "#fff", rot=-90), d1))
d1, cr = crescent("m", 560, 300, 165, 600, 262, 145, "#fff")
add("pakistan", "Пакистан", A, "normal", svg(900, 600, rect(0, 0, 900, 600, "#01411C") + rect(0, 0, 225, 600, "#fff") + cr + star(650, 215, 55, "#fff", rot=40), d1))
d1, cr = crescent("m", 570, 300, 90, 595, 300, 75, "#fff")
add("azerbaijan", "Азербайджан", A, "normal", svg(1200, 600, hbands(1200, 600, ["#00B5E2", "#EF3340", "#509E2F"]) + cr + star(650, 300, 40, "#fff", n=8, inner=18), d1))
m = hbands(1400, 700, ["#CC0001", "#fff"] * 7) + rect(0, 0, 700, 400, "#010066")
d1, cr = crescent("m", 255, 200, 150, 290, 200, 125, "#FFCC00")
m += cr + star(450, 200, 95, "#FFCC00", n=14, inner=45)
add("malaysia", "Малайзия", A, "normal", svg(1400, 700, m, d1))
sg = hbands(900, 600, ["#EF3340", "#fff"])
d1, cr = crescent("m", 190, 150, 105, 230, 150, 100, "#fff")
sg += cr
for i in range(5):
    a = math.radians(-90 + 72 * i)
    sg += star(290 + 55 * math.cos(a), 150 + 55 * math.sin(a), 20, "#fff")
add("singapore", "Сингапур", A, "normal", svg(900, 600, sg, d1))

# ---------- прочие ----------
il = rect(0, 0, 1100, 800, "#fff") + rect(0, 75, 1100, 125, "#0038B8") + rect(0, 600, 1100, 125, "#0038B8")
for rot in (0, 180):
    pts = [(550 + 155 * math.cos(math.radians(-90 + rot + 120 * k)), 400 + 155 * math.sin(math.radians(-90 + rot + 120 * k))) for k in range(3)]
    il += f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="#0038B8" stroke-width="24"/>'
add("israel", "Израиль", A, "normal", svg(1100, 800, il))
mo = rect(0, 0, 900, 600, "#C1272D")
p = [(450 + 170 * math.cos(math.radians(-90 + 72 * k)), 305 + 170 * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]
order = [p[0], p[2], p[4], p[1], p[3]]
mo += f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in order)}" fill="none" stroke="#006233" stroke-width="24" stroke-linejoin="miter"/>'
add("morocco", "Марокко", F, "normal", svg(900, 600, mo))
ind = hbands(900, 600, ["#FF9933", "#fff", "#138808"]) + '<circle cx="450" cy="300" r="80" fill="none" stroke="#000080" stroke-width="10"/>'
for i in range(24):
    a = math.radians(15 * i)
    ind += f'<line x1="450" y1="300" x2="{450 + 78 * math.cos(a):.1f}" y2="{300 + 78 * math.sin(a):.1f}" stroke="#000080" stroke-width="4"/>'
ind += circle(450, 300, 14, "#000080")
add("india", "Индия", A, "easy", svg(900, 600, ind))
bh = rect(0, 0, 1000, 500, "#002395") + poly([(270, 0), (770, 0), (770, 500)], "#FECB00")
for i in range(-1, 9):
    bh += star(185 + 62.5 * i, 62.5 * i + 31, 30, "#fff")
add("bosnia", "Босния и Герцеговина", E, "hard", svg(1000, 500, bh))
mk = rect(0, 0, 1000, 500, "#D20000")
for pts in [[(500, 250), (0, 190), (0, 310)], [(500, 250), (1000, 190), (1000, 310)], [(500, 250), (455, 0), (545, 0)], [(500, 250), (455, 500), (545, 500)],
            [(500, 250), (0, 0), (110, 0)], [(500, 250), (1000, 0), (890, 0)], [(500, 250), (0, 500), (110, 500)], [(500, 250), (1000, 500), (890, 500)]]:
    mk += poly(pts, "#FFE600")
mk += circle(500, 250, 85, "#D20000") + circle(500, 250, 70, "#FFE600")
add("north-macedonia", "Северная Македония", E, "hard", svg(1000, 500, mk))

# Великобритания, Австралия, Новая Зеландия
add("uk", "Великобритания", E, "easy", svg(1200, 600, union_jack(0, 0, 1200, 600)))
au = rect(0, 0, 1200, 600, "#012169") + union_jack(0, 0, 600, 300) + star(300, 450, 128, "#fff", n=7, inner=57)
for x, y in [(900, 100), (900, 500), (750, 262), (1033, 222)]:
    au += star(x, y, 57, "#fff", n=7, inner=25)
au += star(960, 330, 25, "#fff")
add("australia", "Австралия", O, "normal", svg(1200, 600, au))
nz = rect(0, 0, 1200, 600, "#00247D") + union_jack(0, 0, 600, 300)
for x, y, r in [(900, 135, 42), (1005, 255, 38), (790, 290, 38), (900, 505, 46)]:
    nz += star(x, y, r + 8, "#fff") + star(x, y, r, "#CC142B")
add("new-zealand", "Новая Зеландия", O, "normal", svg(1200, 600, nz))

# Южная Корея: тхэгык и четыре триграммы
kr = rect(0, 0, 900, 600, "#fff")
ang = math.degrees(math.atan2(2, 3))
kr += (f'<g transform="translate(450,300) rotate({ang:.2f}) scale(150)">'
       '<circle r="1" fill="#0047A0"/>'
       '<path d="M-1,0 A1,1 0 0 1 1,0 A0.5,0.5 0 0 0 0,0 A0.5,0.5 0 0 1 -1,0 Z" fill="#CD2E3A"/></g>')
def trigram(cx, cy, rot, lines):
    out = f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({rot:.2f})">'
    for i, solid in enumerate(lines):
        y = -62.5 + i * 50
        if solid:
            out += rect(-75, y, 150, 25, "#000")
        else:
            out += rect(-75, y, 68, 25, "#000") + rect(7, y, 68, 25, "#000")
    return out + "</g>"
dist = 312.5
for sx, sy, lines in [(-1, -1, [1, 1, 1]), (1, 1, [0, 0, 0]), (1, -1, [0, 1, 0]), (-1, 1, [1, 0, 1])]:
    a = math.atan2(sy * 2, sx * 3)
    kr += trigram(450 + dist * math.cos(a), 300 + dist * math.sin(a), math.degrees(a) + 90, lines)
add("south-korea", "Южная Корея", A, "normal", svg(900, 600, kr))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for code, (name, reg, lvl, content) in FLAGS.items():
        open(os.path.join(OUT, code + ".svg"), "w").write(content)
    meta = {code: {"name": n, "region": r, "level": l} for code, (n, r, l, _) in FLAGS.items()}
    json.dump(meta, open(sys.argv[1] if len(sys.argv) > 1 else "flags_meta.json", "w"), ensure_ascii=False, indent=1)
    print("флагов:", len(FLAGS), {r: sum(1 for v in FLAGS.values() if v[1] == r) for r in (E, A, F, AM, O)})
