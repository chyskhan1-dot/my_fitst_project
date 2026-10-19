# Рисует дорожные знаки и сигналы светофора для вопросов «ПДД» в media/signs/*.svg.
# Знаки — как в Венской конвенции о дорожном движении (официальные символы, рисуем сами).
# Запуск из папки quiz: python3 tools/make_signs.py
import math, os

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
        anim = (f'<animate attributeName="fill" values="{lit[name]};{dim[name]};{lit[name]}" keyTimes="0;0.5;1" dur="1.2s" '
                'calcMode="discrete" repeatCount="indefinite"/>' if blink and on else "")
        glow = f' filter="url(#glow)"' if on else ""
        body += f'<circle cx="{xs}" cy="{cy}" r="31" fill="{color}"{glow}>{anim}</circle>'
    if arrow:  # справа от нижней секции — секция с зелёной стрелкой вправо
        body += ('<rect x="170" y="196" width="72" height="68" rx="14" fill="#1b1b1b"/>'
                 '<circle cx="206" cy="230" r="27" fill="#0f2a17"/>'
                 '<path d="M190 224 h18 v-10 l18 16 -18 16 v-10 h-18 z" fill="#2ee66b" filter="url(#glow)"/>')
    defs = '<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
    return card(defs + body, w)


def roundabout_arrow(a0, r=64, span=78):
    """Дуга от угла a0 (градусы, против часовой) на span градусов и наконечник по ходу движения."""
    pt = lambda a, rr=r: (150 + rr * math.cos(math.radians(a)), 150 - rr * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = pt(a0), pt(a0 + span)
    t = math.radians(a0 + span)
    tx, ty = -math.sin(t), -math.cos(t)  # направление движения в конце дуги
    nx, ny = math.cos(t), -math.sin(t)   # от центра наружу
    tip = (x1 + tx * 26, y1 + ty * 26)
    b1, b2 = (x1 + nx * 20, y1 + ny * 20), (x1 - nx * 20, y1 - ny * 20)
    return (f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 0 {x1:.1f} {y1:.1f}" fill="none" stroke="#fff" stroke-width="18"/>'
            f'<path d="M{tip[0]:.1f} {tip[1]:.1f} L{b1[0]:.1f} {b1[1]:.1f} L{b2[0]:.1f} {b2[1]:.1f} Z" fill="#fff"/>')


def octagon(r, fill):
    pts = " ".join(f"{150 + r * math.cos(math.radians(22.5 + 45 * i)):.1f},{150 + r * math.sin(math.radians(22.5 + 45 * i)):.1f}" for i in range(8))
    return f'<polygon points="{pts}" fill="{fill}" stroke="#9aa5b1" stroke-width="2"/>'


def number(text, color=BLACK):
    return (f'<text x="150" y="182" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" '
            f'font-size="96" fill="{color}">{text}</text>')


def blue_disc():
    return f'<circle cx="150" cy="150" r="128" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><circle cx="150" cy="150" r="116" fill="{BLUE}"/>'


def slash():
    """Красная полоса «запрещено» поверх символа."""
    return f'<line x1="78" y1="78" x2="222" y2="222" stroke="{RED}" stroke-width="20"/>'


def bike(color):
    """Велосипед: два колеса, рама, руль и седло."""
    return (f'<g fill="none" stroke="{color}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="104" cy="178" r="30"/><circle cx="196" cy="178" r="30"/>'
            '<path d="M104 178 L136 124 H184 L196 178 M136 124 L150 178 L184 124 M128 110 H148 M184 124 L176 104 H192"/></g>')


def triangle_warn():
    """Предупреждающий треугольник без символа."""
    return ('<path d="M150 38 L270 248 H30 Z" fill="#fff" stroke="#9aa5b1" stroke-width="2" stroke-linejoin="round"/>'
            '<path d="M150 66 L246 234 H54 Z" fill="#fff" stroke="' + RED + '" stroke-width="22" stroke-linejoin="round"/>')


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
    # «Прочие опасности»: треугольник вершиной вверх с красной каймой и «!»
    "warning": card('<path d="M150 38 L270 248 H30 Z" fill="#fff" stroke="#9aa5b1" stroke-width="2" stroke-linejoin="round"/>'
                    '<path d="M150 66 L246 234 H54 Z" fill="#fff" stroke="' + RED + '" stroke-width="22" stroke-linejoin="round"/>'
                    f'<rect x="141" y="118" width="18" height="62" rx="6" fill="{BLACK}"/><circle cx="150" cy="202" r="11" fill="{BLACK}"/>'),
    # «Движение прямо»: синий круг с белой стрелкой вверх
    "ahead": card(f'<circle cx="150" cy="150" r="128" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><circle cx="150" cy="150" r="116" fill="{BLUE}"/>'
                  '<path d="M150 62 L208 128 H170 V236 H130 V128 H92 Z" fill="#fff"/>'),
    # «Круговое движение»: синий круг с тремя белыми стрелками против часовой стрелки
    "roundabout": card(f'<circle cx="150" cy="150" r="128" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><circle cx="150" cy="150" r="116" fill="{BLUE}"/>'
                       + "".join(roundabout_arrow(a) for a in (100, 220, 340))),
    # «STOP»: красный восьмиугольник
    "stop": card(octagon(118, "#fff") + octagon(108, RED) +
                 '<text x="150" y="172" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="64" fill="#fff">STOP</text>'),
    # «Конец главной дороги»: жёлтый ромб, перечёркнутый чёрными полосами
    "end-priority": card('<rect x="62" y="62" width="176" height="176" transform="rotate(45 150 150)" fill="#fff" stroke="#555" stroke-width="3"/>'
                         '<rect x="90" y="90" width="120" height="120" transform="rotate(45 150 150)" fill="' + YELLOW + '" stroke="#333" stroke-width="2"/>'
                         '<g stroke="#222" stroke-width="6">' + "".join(f'<line x1="{88 + d}" y1="{212 + d}" x2="{212 + d}" y2="{88 + d}"/>' for d in (-12, 0, 12)) + '</g>'),
    # «Ограничение скорости 60»
    "speed-60": card(disc(WHITE) + number("60")),
    # «Минимальная скорость 50»: синий круг с белым числом
    "min-speed-50": card(blue_disc() + number("50", "#fff")),
    # «Поворот налево запрещён»
    "no-left": card(disc(WHITE) + '<path d="M196 214 V138 H126 V112 L84 150 L126 188 V162 H172 V214 Z" fill="' + BLACK + '"/>' + slash()),
    # «Разворот запрещён»
    "no-u-turn": card(disc(WHITE) + '<path d="M118 214 V136 a32 32 0 0 1 64 0 V160 h18 l-30 36 -30 -36 h18 V136 a8 8 0 0 0 -16 0 V214 Z" fill="' + BLACK + '"/>' + slash()),
    # «Движение направо»
    "turn-right": card(blue_disc() + '<path d="M112 236 V146 a26 26 0 0 1 26 -26 H176 V92 L222 134 L176 176 V148 H140 V236 Z" fill="#fff"/>'),
    # «Пересечение равнозначных дорог»: треугольник с крестом
    "crossroads": card(triangle_warn() + f'<rect x="141" y="114" width="18" height="104" fill="{BLACK}"/><rect x="104" y="160" width="92" height="18" fill="{BLACK}"/>'),
    # «Однопутная железная дорога» — Андреевский крест у переезда без шлагбаума
    "rail-cross": card('<g transform="rotate(35 150 150)"><rect x="40" y="128" width="220" height="44" fill="#fff" stroke="' + RED + '" stroke-width="6"/>'
                       + "".join(f'<rect x="{x}" y="131" width="24" height="38" fill="{RED}"/>' for x in (58, 108, 158, 208)) + '</g>'
                       '<g transform="rotate(-35 150 150)"><rect x="40" y="128" width="220" height="44" fill="#fff" stroke="' + RED + '" stroke-width="6"/>'
                       + "".join(f'<rect x="{x}" y="131" width="24" height="38" fill="{RED}"/>' for x in (58, 108, 158, 208)) + '</g>'),
    # «Дорога с односторонним движением»
    "one-way": card(f'<rect x="78" y="34" width="144" height="232" rx="14" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="88" y="44" width="124" height="212" rx="10" fill="{BLUE}"/>'
                    '<path d="M150 62 L196 118 H166 V238 H134 V118 H104 Z" fill="#fff"/>'),
    # «Тупик»
    "dead-end": card(f'<rect x="40" y="40" width="220" height="220" rx="20" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="52" y="52" width="196" height="196" rx="14" fill="{BLUE}"/>'
                     f'<rect x="134" y="118" width="32" height="112" fill="#fff"/><rect x="88" y="86" width="124" height="34" fill="{RED}"/>'),
    # «Двустороннее движение»: треугольник со стрелками вверх и вниз
    "two-way": card(triangle_warn() + f'<path d="M126 220 V142 H112 L130 112 L148 142 H134 V220 Z M174 112 V190 H188 L170 220 L152 190 H166 V112 Z" fill="{BLACK}"/>'),
    # «Преимущество встречного движения»: красная стрелка вверх, чёрная вниз
    "oncoming-priority": card(disc(WHITE) + f'<path d="M124 226 V136 H106 L130 96 L154 136 H136 V226 Z" fill="{RED}"/><path d="M176 74 V164 H194 L170 204 L146 164 H164 V74 Z" fill="{BLACK}"/>'),
    # «Преимущество перед встречным движением»: синий квадрат, белая стрелка вверх, красная вниз
    "priority-over-oncoming": card(f'<rect x="40" y="40" width="220" height="220" rx="20" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="52" y="52" width="196" height="196" rx="14" fill="{BLUE}"/>'
                                   f'<path d="M124 226 V136 H106 L130 96 L154 136 H136 V226 Z" fill="#fff"/><path d="M176 74 V164 H194 L170 204 L146 164 H164 V74 Z" fill="{RED}"/>'),
    # «Пешеходный переход»: синий квадрат, белый треугольник, пешеход на «зебре»
    "crosswalk": card(f'<rect x="40" y="40" width="220" height="220" rx="20" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="52" y="52" width="196" height="196" rx="14" fill="{BLUE}"/>'
                      '<path d="M150 66 L238 228 H62 Z" fill="#fff"/>'
                      + "".join(f'<rect x="{x}" y="206" width="14" height="14" fill="{BLACK}"/>' for x in (96, 120, 144, 168, 192))
                      + f'<circle cx="152" cy="112" r="11" fill="{BLACK}"/><path d="M146 126 L136 168 L120 200 M140 150 L164 178 L172 202 M144 132 L126 150 M150 130 L174 146" stroke="{BLACK}" stroke-width="9" stroke-linecap="round" fill="none"/>'),
    # «Поворот направо запрещён»
    "no-right": card(disc(WHITE) + '<path d="M104 214 V138 H174 V112 L216 150 L174 188 V162 H128 V214 Z" fill="' + BLACK + '"/>' + slash()),
    # «Движение налево»
    "turn-left": card(blue_disc() + '<path d="M188 236 V146 a26 26 0 0 0 -26 -26 H124 V92 L78 134 L124 176 V148 H160 V236 Z" fill="#fff"/>'),
    # «Объезд препятствия справа»: стрелка вниз-вправо
    "keep-right": card(blue_disc() + '<path d="M78 106 L104 80 L184 160 L184 120 L220 120 L220 220 L120 220 L120 184 L160 184 Z" fill="#fff"/>'),
    # «Конец ограничения скорости 60»: серые цифры, чёрные полосы
    "end-speed-60": card('<circle cx="150" cy="150" r="128" fill="#fff" stroke="#555" stroke-width="5"/>' + number("60", "#9a9a9a")
                         + '<clipPath id="c"><circle cx="150" cy="150" r="124"/></clipPath><g clip-path="url(#c)" stroke="#222" stroke-width="6">'
                         + "".join(f'<line x1="{60 + d}" y1="270" x2="{240 + d}" y2="30"/>' for d in (-16, 0, 16)) + '</g>'),
    # «Искусственная неровность»: треугольник с «горбом»
    "bumps": card(triangle_warn() + f'<path d="M92 214 H118 Q150 150 182 214 H208 V224 H92 Z" fill="{BLACK}"/>'),
    # «Сужение дороги»: края дороги сходятся
    "road-narrows": card(triangle_warn() + f'<path d="M112 224 V186 L134 150 V112 H146 V154 L124 190 V224 Z M188 224 V186 L166 150 V112 H154 V154 L176 190 V224 Z" fill="{BLACK}"/>'),
    # «Крутой спуск»: склон и «10%»
    "steep-descent": card(triangle_warn() + f'<path d="M80 222 L220 222 L80 150 Z" fill="{BLACK}"/>'
                          '<text x="190" y="180" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="32" fill="#1b1b1b">10%</text>'),
    # «Опасный поворот направо»
    "bend-right": card(triangle_warn() + f'<path d="M136 224 V164 a26 26 0 0 1 26 -26 H168 V116 L200 148 L168 180 V158 H162 a6 6 0 0 0 -6 6 V224 Z" fill="{BLACK}"/>'),
    # «Светофорное регулирование»: треугольник с красным, жёлтым и зелёным
    "signals-ahead": card(triangle_warn() + f'<rect x="132" y="104" width="36" height="120" rx="8" fill="{BLACK}"/>'
                          '<circle cx="150" cy="124" r="12" fill="#ff3b30"/><circle cx="150" cy="164" r="12" fill="#ffc400"/><circle cx="150" cy="204" r="12" fill="#2ee66b"/>'),
    # «Ограничение высоты 3,5 м»
    "height-limit": card(disc(WHITE) + f'<path d="M150 60 L166 80 H134 Z M150 240 L166 220 H134 Z" fill="{BLACK}"/>'
                         '<text x="150" y="168" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="48" fill="#1b1b1b">3,5 м</text>'),
    # «Ограничение массы 5 т»
    "weight-limit": card(disc(WHITE) + number("5 т")),
    # «Больница»: синий прямоугольник, белый квадрат, красный крест
    "hospital": card(f'<rect x="64" y="34" width="172" height="232" rx="14" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="74" y="44" width="152" height="212" rx="10" fill="{BLUE}"/>'
                     f'<rect x="96" y="74" width="108" height="108" fill="#fff"/><path d="M138 86 H162 V116 H192 V140 H162 V170 H138 V140 H108 V116 H138 Z" fill="{RED}"/>'),
    # «Автозаправочная станция»: синий прямоугольник, белый квадрат, колонка
    "fuel": card(f'<rect x="64" y="34" width="172" height="232" rx="14" fill="#fff" stroke="#9aa5b1" stroke-width="2"/><rect x="74" y="44" width="152" height="212" rx="10" fill="{BLUE}"/>'
                 f'<rect x="96" y="74" width="108" height="108" fill="#fff"/><path d="M116 170 V92 a6 6 0 0 1 6 -6 H156 a6 6 0 0 1 6 6 V170 Z M124 96 V118 H154 V96 Z" fill="{BLACK}" fill-rule="evenodd"/>'
                 f'<path d="M162 112 H172 a8 8 0 0 1 8 8 V156 a6 6 0 0 0 12 0 V110 L180 98" fill="none" stroke="{BLACK}" stroke-width="7" stroke-linejoin="round"/>'),
    # «Велосипедная дорожка»: синий круг с белым велосипедом
    "bike-path": card(blue_disc() + bike("#fff")),
    # «Движение на велосипедах запрещено»
    "no-bikes": card(disc(WHITE) + bike(BLACK)),
    # «Конец зоны запрещения обгона»: серые машины, чёрные полосы
    "end-no-overtaking": card('<circle cx="150" cy="150" r="128" fill="#fff" stroke="#555" stroke-width="5"/>' + car(112, "#9a9a9a") + car(188, "#9a9a9a")
                              + '<clipPath id="c"><circle cx="150" cy="150" r="124"/></clipPath><g clip-path="url(#c)" stroke="#222" stroke-width="6">'
                              + "".join(f'<line x1="{60 + d}" y1="270" x2="{240 + d}" y2="30"/>' for d in (-16, 0, 16)) + '</g>'),
    # светофоры
    "lights-yellow-blink": lights(False, True, False, blink=True),
    "lights-red-yellow": lights(True, True, False),
    "lights-arrow": lights(True, False, False, arrow=True),
    "lights-green-blink": lights(False, False, True, blink=True),
    "lights-red": lights(True, False, False),
}

os.makedirs(OUT, exist_ok=True)
for name, svg in SIGNS.items():
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg)
print("знаков:", len(SIGNS), "→", os.path.normpath(OUT))
