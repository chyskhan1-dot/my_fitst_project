# Рисует футболки в цветах клубов и сборных для вопросов «Узнай по форме» (пакет football.json) → media/kits/*.svg.
# Рисуем сами: только цвета и узор (полосы, обручи, лента), без эмблем, надписей и логотипов — их брать нельзя.
# Запуск из папки quiz: python3 tools/make_kits.py
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "kits")

# футболка: корпус и рукава (координаты в поле 300×300)
BODY = "M95 62 L125 48 Q150 64 175 48 L205 62 L205 262 L95 262 Z"
LEFT = "M95 62 L42 92 L62 140 L95 124 Z"
RIGHT = "M205 62 L258 92 L238 140 L205 124 Z"
SHIRT = BODY + " " + LEFT + " " + RIGHT

# узор: вид и цвета; sleeves — цвет рукавов (если не как у корпуса), collar — воротник, trim — кайма рукавов
KITS = {
    "barcelona": dict(kind="stripes", colors=["#a50044", "#004d98"], n=5),
    "juventus": dict(kind="stripes", colors=["#111111", "#ffffff"], n=7),
    "inter": dict(kind="stripes", colors=["#0b3fa8", "#111111"], n=7),
    "milan": dict(kind="stripes", colors=["#d0102b", "#111111"], n=7),
    "atletico": dict(kind="stripes", colors=["#cb3524", "#ffffff"], n=7, collar="#26357a"),
    "celtic": dict(kind="hoops", colors=["#018749", "#ffffff"], n=7),
    "arsenal": dict(kind="solid", colors=["#db0007"], sleeves="#ffffff"),
    "dortmund": dict(kind="solid", colors=["#fde100"], collar="#111111"),
    "spartak": dict(kind="band", colors=["#d71920", "#ffffff"]),
    "river": dict(kind="sash", colors=["#ffffff", "#e30613"]),
    "boca": dict(kind="band", colors=["#103f79", "#f3b229"]),
    "ajax": dict(kind="center", colors=["#ffffff", "#d2122e"], wide=True),
    "psg": dict(kind="center", colors=["#0b1f4b", "#d71920"], edge="#ffffff"),
    "argentina": dict(kind="stripes", colors=["#75aadb", "#ffffff"], n=7),
    "croatia": dict(kind="checks", colors=["#e2231a", "#ffffff"]),
    "netherlands": dict(kind="solid", colors=["#f36c21"]),
    "brazil": dict(kind="solid", colors=["#ffdf00"], collar="#009c3b", trim="#009c3b"),
}


def pattern(k):
    c = k["colors"]
    out = [f'<rect x="0" y="0" width="300" height="300" fill="{c[0]}"/>']
    if k["kind"] == "stripes":  # вертикальные полосы по корпусу и рукавам
        n, w = k["n"], 110 / k["n"]
        for i in range(-6, n + 6):
            if i % 2:
                out.append(f'<rect x="{95 + i * w:.1f}" y="0" width="{w:.1f}" height="300" fill="{c[1]}"/>')
    elif k["kind"] == "hoops":  # горизонтальные обручи
        h = 214 / k["n"]
        for i in range(k["n"] + 2):
            if i % 2:
                out.append(f'<rect x="0" y="{48 + i * h:.1f}" width="300" height="{h:.1f}" fill="{c[1]}"/>')
    elif k["kind"] == "band":  # одна широкая полоса поперёк груди
        out.append(f'<rect x="0" y="112" width="300" height="44" fill="{c[1]}"/>')
    elif k["kind"] == "sash":  # диагональная лента через плечо
        out.append(f'<polygon points="95,36 95,96 205,250 205,190" fill="{c[1]}"/>')
    elif k["kind"] == "center":  # широкая вертикальная полоса посередине
        w = 52 if k.get("wide") else 30
        if k.get("edge"):
            out.append(f'<rect x="{150 - w / 2 - 8}" y="0" width="{w + 16}" height="300" fill="{k["edge"]}"/>')
        out.append(f'<rect x="{150 - w / 2}" y="0" width="{w}" height="300" fill="{c[1]}"/>')
    elif k["kind"] == "checks":  # шахматка
        s = 22
        for i in range(14):
            for j in range(14):
                if (i + j) % 2:
                    out.append(f'<rect x="{40 + i * s}" y="{40 + j * s}" width="{s}" height="{s}" fill="{c[1]}"/>')
    return "".join(out)


def kit(name, k):
    sleeves = k.get("sleeves")
    sl = (f'<path d="{LEFT}" fill="{sleeves}"/><path d="{RIGHT}" fill="{sleeves}"/>') if sleeves else ""
    trim = k.get("trim")
    collar = k.get("collar") or ("#ffffff" if k["colors"][0] != "#ffffff" else "#cccccc")
    body = (f'<clipPath id="s"><path d="{SHIRT}"/></clipPath>'
            f'<g clip-path="url(#s)">{pattern(k)}{sl}</g>'
            + (f'<path d="M62 140 L42 92 M238 140 L258 92" stroke="{trim}" stroke-width="8"/>' if trim else "")
            + f'<path d="{SHIRT}" fill="none" stroke="#1d2433" stroke-opacity=".35" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M125 48 Q150 64 175 48" fill="none" stroke="{collar}" stroke-width="9" stroke-linecap="round"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">'
            f'<rect width="300" height="300" rx="18" fill="#e9edf2"/>{body}</svg>\n')


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, k in KITS.items():
        with open(os.path.join(OUT, name + ".svg"), "w") as f:
            f.write(kit(name, k))
    print(f"футболок: {len(KITS)} → media/kits/")
