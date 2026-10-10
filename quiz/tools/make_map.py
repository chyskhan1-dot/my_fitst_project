# Рисует карту мира для вопросов «Где на карте?»: суша, горы, плато, пустыни, льды, озёра и реки —
# без границ и подписей. Данные — Natural Earth (общественное достояние), слои 1:50m в формате GeoJSON:
#   https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
# Запуск из папки quiz: python3 tools/make_map.py <папка с geojson>  → media/map/world.svg
# Картинку для игры (media/map/world.jpg, 4096×2048) снимает с этого SVG браузер: открыть SVG
# в Chromium с окном 4096×2048 и сохранить скриншот в JPEG (качество 85).
# Лёгкая версия для медленного интернета: convert media/map/world.jpg -resize 2048x1024 -quality 82 -strip media/map/world-2k.jpg
import json, os, sys

W, H = 4096, 2048  # равнопромежуточная проекция: долгота → x, широта → y
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "map", "world.svg")
SRC = sys.argv[1] if len(sys.argv) > 1 else "."


def load(name):
    with open(os.path.join(SRC, name + ".geojson"), encoding="utf-8") as f:
        return json.load(f)["features"]


def rings(geom):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly
    elif geom["type"] == "LineString":
        yield geom["coordinates"]
    elif geom["type"] == "MultiLineString":
        yield from geom["coordinates"]


def path(features, closed=True, step=1.2):
    """Контуры в путь SVG; точки ближе step пикселей выкидываем — файл меньше, на глаз не видно."""
    out = []
    for f in features:
        for ring in rings(f["geometry"]):
            pts, last = [], None
            for lon, lat in ((p[0], p[1]) for p in ring):
                x, y = (lon + 180) / 360 * W, (90 - lat) / 180 * H
                if last is None or abs(x - last[0]) + abs(y - last[1]) >= step:
                    pts.append((x, y))
                    last = (x, y)
            if len(pts) < (3 if closed else 2):
                continue
            out.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + ("Z" if closed else ""))
    return "".join(out)


def cla(f):
    return (f["properties"].get("FEATURECLA") or f["properties"].get("featurecla") or "").lower()


land = load("ne_50m_land")
regions = load("ne_50m_geography_regions_polys")
mountains = [f for f in regions if cla(f) in ("range/mtn", "foothills")]
plateaus = [f for f in regions if cla(f) == "plateau"]
deserts = [f for f in regions if cla(f) == "desert"]
ice = load("ne_50m_glaciated_areas") + load("ne_50m_antarctic_ice_shelves_polys")
lakes = load("ne_50m_lakes")
rivers = [f for f in load("ne_50m_rivers_lake_centerlines") if (f["properties"].get("scalerank") or 9) <= 4]

L = path(land)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
 <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fb2d6"/><stop offset=".5" stop-color="#5f9ccc"/><stop offset="1" stop-color="#7fb2d6"/></linearGradient>
 <clipPath id="land"><path d="{L}"/></clipPath>
 <filter id="b2" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2"/></filter>
 <filter id="b6" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="6"/></filter>
 <filter id="b14" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter>
</defs>
<rect width="{W}" height="{H}" fill="url(#sea)"/>
<path d="{L}" fill="none" stroke="#a9d0ea" stroke-width="18" stroke-linejoin="round" filter="url(#b14)" opacity=".9"/>
<path d="{L}" fill="#9fc27f"/>
<g clip-path="url(#land)">
 <path d="{path(deserts)}" fill="#e6d29b" filter="url(#b14)"/>
 <path d="{path(plateaus)}" fill="#d2c08a" filter="url(#b14)"/>
 <path d="{path(mountains)}" fill="#b98e5d" filter="url(#b14)"/>
 <path d="{path(mountains)}" fill="#8e6741" filter="url(#b6)" opacity=".75"/>
 <path d="{path(ice)}" fill="#f4f7fb" filter="url(#b2)"/>
</g>
<path d="{path(lakes)}" fill="#6fa8d3"/>
<path d="{path(rivers, closed=False)}" fill="none" stroke="#3f8fd6" stroke-width="1.4" stroke-linejoin="round" opacity=".9"/>
<path d="{L}" fill="none" stroke="#557a50" stroke-width="1.2" stroke-linejoin="round" opacity=".7"/>
</svg>
'''
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(OUT, len(svg) // 1024, "КБ")
