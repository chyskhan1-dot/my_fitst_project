# Рисует дорожные знаки и сигналы светофора для вопросов «ПДД» в media/signs/*.svg.
# Знаки — как в Венской конвенции о дорожном движении (официальные символы, рисуем сами).
# Запуск из папки quiz: python3 tools/make_signs.py
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "signs")
RED, BLUE, YELLOW, BLACK, WHITE = "#d21f26", "#1f5fb4", "#ffcc00", "#1b1b1b", "#ffffff"


def card(body, w=300, h=300):
    """Знак на светлом фоне «неба» — чтобы белая кайма была видна на тёмном экране."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" rx="18" fill="#cfdbe8"/>{body}</svg>\n')


def disc(fill, ring=RED):
    """Круглый знак: белая кромка, красная кайма, внутри — fill."""
    return (f'<circle cx="150" cy="150" r="128" fill="{WHITE}" stroke="#9aa5b1" stroke-width="2"/>'
            f'<circle cx="150" cy="150" r="104" fill="{fill}" stroke="{ring}" stroke-width="22"/>')


def car(x, color):
    """Машина сзади: кузов, крыша, колёса."""
    return (f'<g fill="{color}"><path d="M{x - 26} 160 l8 -26 h36 l8 26 z"/>'
            f'<rect x="{x - 34}" y="158" width="68" height="28" rx="7"/>'
            f'<rect x="{x - 30}" y="184" width="14" height="14" rx="3"/><rect x="{x + 16}" y="184" width="14" height="14" rx="3"/></g>'
            f'<path d="M{x - 18} 157 l5 -16 h26 l5 16 z" fill="#cfe3f5"/>')


def lights(top, mid, bottom, blink=False, arrow=False):
    """Светофор: три секции сверху вниз; цвет — горит, None — погашен. arrow — дополнительная секция со стрелкой."""
    dim = {"top": "#4a1d1d", "mid": "#4a3d12", "bottom": "#173d22"}
    lit = {"top": "#ff3b30", "mid": "#ffc400", "bottom": "#2ee66b"}
    w = 300
    body = f'<rect x="{105 if not arrow else 70}" y="22" width="90" height="256" rx="20" fill="{BLACK}"/>'
    xs = 150 if not arrow else 115
    for name, cy, on in (("top", 70, top), ("mid", 150, mid), ("bottom", 230, bottom)):
        color = lit[name] if on else dim[name]
        anim = ('<animate attributeName="fill" values="#ffc400;#4a3d12;#ffc400" keyTimes="0;0.5;1" dur="1.2s" '
                'calcMode="discrete" repeatCount="indefinite"/>' if blink and name == "mid" else "")
        glow = f' filter="url(#glow)"' if on else ""
        body += f'<circle cx="{xs}" cy="{cy}" r="31" fill="{color}"{glow}>{anim}</circle>'
    if arrow:  # справа от нижней секции — секция с зелёной стрелкой вправо
        body += ('<rect x="170" y="196" width="72" height="68" rx="14" fill="#1b1b1b"/>'
                 '<circle cx="206" cy="230" r="27" fill="#0f2a17"/>'
                 '<path d="M190 224 h18 v-10 l18 16 -18 16 v-10 h-18 z" fill="#2ee66b" filter="url(#glow)"/>')
    defs = '<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
    return card(defs + body, w)


SIGNS = {
    # «Уступи дорогу»: треугольник вершиной вниз
    "yield": card('<path d="M30 52 H270 L150 262 Z" fill="#fff" stroke="#9aa5b1" stroke-width="2" stroke-linejoin="round"/>'
                  '<path d="M54 66 H246 L150 234 Z" fill="#fff" stroke="' + RED + '" stroke-width="22" stroke-linejoin="round"/>'),
    # «Главная дорога»: жёлтый ромб в белой рамке
    "priority": card('<rect x="62" y="62" width="176" height="176" transform="rotate(45 150 150)" fill="#fff" stroke="#555" stroke-width="3"/>'
                     '<rect x="90" y="90" width="120" height="120" transform="rotate(45 150 150)" fill="' + YELLOW + '" stroke="#333" stroke-width="2"/>'),
    # «Въезд запрещён» («кирпич»)
    "no-entry": card(f'<circle cx="150" cy="150" r="128" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><circle cx="150" cy="150" r="116" fill="{RED}"/>'
                     '<rect x="62" y="132" width="176" height="36" fill="#fff"/>'),
    # «Движение запрещено»: белый круг с красной каймой
    "closed": card(disc(WHITE)),
    # «Конец всех ограничений»: белый круг с чёрными диагональными полосами
    "end-all": card('<circle cx="150" cy="150" r="128" fill="#fff" stroke="#555" stroke-width="5"/>'
                    '<clipPath id="c"><circle cx="150" cy="150" r="124"/></clipPath><g clip-path="url(#c)" stroke="#222" stroke-width="7">'
                    + "".join(f'<line x1="{60 + d}" y1="270" x2="{240 + d}" y2="30"/>' for d in (-30, -15, 0, 15, 30)) + '</g>'),
    # «Стоянка запрещена»: синий круг, красная кайма и одна диагональ
    "no-parking": card(disc(BLUE) + f'<clipPath id="c"><circle cx="150" cy="150" r="93"/></clipPath>'
                       f'<line x1="70" y1="70" x2="230" y2="230" stroke="{RED}" stroke-width="22" clip-path="url(#c)"/>'),
    # «Остановка запрещена»: синий круг, красная кайма и крест
    "no-stopping": card(disc(BLUE) + f'<clipPath id="c"><circle cx="150" cy="150" r="93"/></clipPath><g stroke="{RED}" stroke-width="22" clip-path="url(#c)">'
                        '<line x1="70" y1="70" x2="230" y2="230"/><line x1="230" y1="70" x2="70" y2="230"/></g>'),
    # «Обгон запрещён»: красная машина слева, чёрная справа
    "no-overtaking": card(disc(WHITE) + car(112, RED) + car(188, BLACK)),
    # «Место стоянки»: синий квадрат с белой «P»
    "parking": card('<rect x="40" y="40" width="220" height="220" rx="20" fill="#fff" stroke="#9aa5b1" stroke-width="2"/>'
                    f'<rect x="52" y="52" width="196" height="196" rx="14" fill="{BLUE}"/>'
                    '<path d="M112 222 V78 h46 a40 40 0 0 1 0 80 h-18 v64 z M140 102 v32 h16 a16 16 0 0 0 0 -32 z" fill="#fff" fill-rule="evenodd"/>'),
    # светофоры
    "lights-yellow-blink": lights(False, True, False, blink=True),
    "lights-red-yellow": lights(True, True, False),
    "lights-arrow": lights(True, False, False, arrow=True),
}

os.makedirs(OUT, exist_ok=True)
for name, svg in SIGNS.items():
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg)
print("знаков:", len(SIGNS), "→", os.path.normpath(OUT))
