# Скачивает картинки Microsoft Fluent Emoji (MIT) для смайликов игры: аватарки (AVATARS в server.py)
# и ребусы (поле "emoji" в packs/*.json) → media/emoji/<коды>.png, и обновляет список в static/emoji.js.
# Нужна копия репозитория с описаниями картинок:
#   git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/fluentui-emoji.git fluent
#   cd fluent && git sparse-checkout set --no-cone '/assets/*/metadata.json'
# Запуск из папки quiz: python3 tools/fetch_emoji.py <путь к fluent>
# Потом уменьшить картинки (ImageMagick): for f in media/emoji/*.png; do convert "$f" -resize 160x160 -strip "$f"; done
import glob, json, os, re, subprocess, sys, urllib.parse, urllib.request

QUIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FL = sys.argv[1]
OUT = os.path.join(QUIZ, "media", "emoji")
sys.path.insert(0, QUIZ)
import server  # noqa: E402  (нужен только список AVATARS)


def key(cps):
    return "-".join("%x" % c for c in cps if c != 0xFE0F)


def graphemes(s):
    """Смайлики по одному: с вариантами (FE0F), цифрами в квадрате (20E3), цветом кожи и склейками (200D)."""
    cps, out, i = [ord(c) for c in s], [], 0
    while i < len(cps):
        cur = [cps[i]]; i += 1
        if 0x1F1E6 <= cur[0] <= 0x1F1FF and i < len(cps) and 0x1F1E6 <= cps[i] <= 0x1F1FF:
            cur.append(cps[i]); i += 1
        while i < len(cps) and (cps[i] in (0xFE0F, 0x20E3, 0x200D) or 0x1F3FB <= cps[i] <= 0x1F3FF):
            cur.append(cps[i]); i += 1
            if cur[-1] == 0x200D and i < len(cps):
                cur.append(cps[i]); i += 1
        out.append(cur)
    return out


meta = {}
for f in glob.glob(os.path.join(FL, "assets", "*", "metadata.json")):
    m = json.load(open(f, encoding="utf-8"))
    meta[key(int(c, 16) for c in m["unicode"].split())] = os.path.basename(os.path.dirname(f))
paths = subprocess.run(["git", "-C", FL, "ls-tree", "-r", "--name-only", "HEAD", "assets"], capture_output=True, text=True).stdout.split("\n")
paths = [p for p in paths if "/3D/" in p and p.endswith(".png")]

need = {tuple(ord(c) for c in a) for a in server.AVATARS}
for f in glob.glob(os.path.join(QUIZ, "packs", "*.json")):
    for q in json.load(open(f, encoding="utf-8"))["questions"]:
        need |= {tuple(g) for g in graphemes(q.get("emoji") or "")}
os.makedirs(OUT, exist_ok=True)
have, missing = [], []
for g in sorted(need):
    k, folder = key(g), meta.get(key(g))
    cand = [p for p in paths if folder and p.startswith(f"assets/{folder}/")]
    p = next((x for x in cand if "/Default/" in x), cand[0] if cand else None)
    if not p:
        missing.append("".join(map(chr, g)))
        continue
    url = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/" + urllib.parse.quote(p)
    with urllib.request.urlopen(url, timeout=30) as r:
        open(os.path.join(OUT, k + ".png"), "wb").write(r.read())
    have.append(k)
js = os.path.join(QUIZ, "static", "emoji.js")
src = open(js, encoding="utf-8").read()
src = re.sub(r'const HAVE = new Set\("[^"]*"', 'const HAVE = new Set("' + " ".join(sorted(have)) + '"', src)
open(js, "w", encoding="utf-8").write(src)
print("картинок:", len(have), "| нет в наборе (останутся смайликами):", " ".join(missing) or "—")
