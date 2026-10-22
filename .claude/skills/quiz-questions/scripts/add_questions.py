# Добавляет вопросы в пакет викторины по правилам проекта.
# Запуск из корня репозитория: python3 .claude/skills/quiz-questions/scripts/add_questions.py <новые.json> [пакет]
# Пакет по умолчанию — quiz/packs/general.json. Повторный запуск не дублирует (сверка по тексту и картинке вопроса).
#
# <новые.json> — список вопросов. Для «один верный» (choice) верный ответ пишется отдельно,
# а место среди вариантов скрипт выбирает сам — так, чтобы правильные ответы лежали по позициям поровну:
#   {"q": "…?", "right": "Верный", "wrong": ["Неверный 1", "Неверный 2", "Неверный 3"],
#    "theme": "Космос", "level": "easy|normal|hard", "answer_image": "<картинка>", "image": "<картинка>",
#    "note": "Пояснение к ответу — одно-два предложения, показываем после ответа"}
# Другие типы — как в пакете (type: number/text/multi/order/map, answer, unit, place…), их скрипт добавляет как есть.
# <картинка> — путь в media/ (media/flags/italy.svg) или «emoji:Название папки Fluent» (emoji:Red apple):
# такой смайлик скачивается с GitHub microsoft/fluentui-emoji (лицензия MIT) в media/pics/ans-<имя>.png.
# --new-theme "Тема" — разрешить новую тему (только когда владелец попросил новый раздел).
import collections, json, os, random, subprocess, sys, urllib.parse, urllib.request

ROOT = os.getcwd()
QUIZ = os.path.join(ROOT, "quiz")
args = sys.argv[1:]
new_theme = None
if "--new-theme" in args:
    k = args.index("--new-theme"); new_theme = args[k + 1]; del args[k:k + 2]
new_path = args[0]
pack_path = args[1] if len(args) > 1 else os.path.join(QUIZ, "packs", "general.json")
LEVELS = {"easy", "normal", "hard"}
TYPES = {"choice", "multi", "order", "text", "number", "map"}


def emoji(folder):
    """Fluent Emoji 3D → media/pics/ans-<имя>.png (200×200)."""
    slug = folder.lower().replace(" ", "-")
    rel = f"media/pics/ans-{slug}.png"
    dst = os.path.join(QUIZ, rel)
    if os.path.exists(dst):
        return rel
    base = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"
    name = folder.lower().replace(" ", "_").replace("-", "_")
    for path in (f"{folder}/3D/{name}_3d.png", f"{folder}/Default/3D/{name}_3d_default.png"):
        try:
            with urllib.request.urlopen(base + urllib.parse.quote(path), timeout=30) as r:
                data = r.read()
            break
        except Exception:
            data = None
    if data is None:
        sys.exit(f"нет такого смайлика в Fluent Emoji: «{folder}» — проверь название папки на GitHub")
    tmp = dst + ".tmp.png"
    open(tmp, "wb").write(data)
    subprocess.run(["convert", tmp, "-resize", "200x200", "-strip", dst], check=True)
    os.remove(tmp)
    return rel


def picture(v):
    if not v:
        return None
    if v.startswith("emoji:"):
        return emoji(v[6:].strip())
    if not os.path.exists(os.path.join(QUIZ, v)):
        sys.exit(f"нет файла {v} (пути пишутся от папки quiz/, например media/flags/italy.svg)")
    return v


pack = json.load(open(pack_path, encoding="utf-8"))
Q = pack["questions"]
themes = {q.get("theme") for q in Q if q.get("theme")} | ({new_theme} if new_theme else set())
qkey = lambda text, image, emoji="": text.strip().lower() + "|" + (image or "") + (emoji or "")  # один текст с разными картинками или ребусами — разные вопросы
have = {qkey(q["q"], q.get("image"), q.get("emoji")) + "|".join(q.get("images") or []) for q in Q}
counts = collections.Counter(q["answer"] for q in Q if q.get("type", "choice") == "choice")
right_of = lambda q: q["options"][q["answer"]] if q.get("type", "choice") == "choice" else None
by_answer = collections.defaultdict(list)  # (тема, верный ответ) → вопросы: ловим повторы другими словами
for q in Q:
    if right_of(q):
        by_answer[(q.get("theme"), right_of(q).lower())].append(q["q"])
similar = []
rnd = random.Random(len(Q))
added, skipped = [], []
for n, item in enumerate(json.load(open(new_path, encoding="utf-8")), 1):
    text = item["q"].strip()
    image = item.get("image")
    if image and image.startswith("emoji:"):
        image = picture(image)
    if qkey(text, image, item.get("emoji")) + "|".join(item.get("images") or []) in have:
        skipped.append(text)
        continue
    if item.get("theme") not in themes:
        sys.exit(f"вопрос {n}: тема «{item.get('theme')}» не из пакета. Есть: {', '.join(sorted(themes))}")
    if item.get("level") not in LEVELS:
        sys.exit(f"вопрос {n}: level должен быть easy, normal или hard")
    qtype = item.get("type", "choice")
    if qtype not in TYPES:
        sys.exit(f"вопрос {n}: неизвестный тип {qtype}")
    if not str(item.get("note") or "").strip():
        sys.exit(f"вопрос {n}: нет пояснения note — коротко объясни ответ (покажем после ответа)")
    if qtype == "map" and item["theme"] != "Где на карте":
        sys.exit(f"вопрос {n}: вопросы на карте — только в теме «Где на карте»")
    if qtype == "choice":
        wrong = item["wrong"]
        if len(wrong) != 3 or item["right"] in wrong or len(set(wrong)) != 3:
            sys.exit(f"вопрос {n}: нужно ровно 3 разных неверных варианта, не совпадающих с верным")
        a = min(range(4), key=lambda i: (counts[i], rnd.random()))
        counts[a] += 1
        q = {"q": text, "options": wrong[:a] + [item["right"]] + wrong[a:], "answer": a}
        if item.get("emoji"):
            q["emoji"] = item["emoji"]  # ребус из смайликов
        if item.get("images"):
            q["images"] = item["images"]  # «Где логика»: 2–3 картинки по очереди
        if item.get("seconds"):
            q["seconds"] = item["seconds"]  # своё время на вопрос
        for old_q in by_answer[(item["theme"], item["right"].lower())]:
            similar.append((text, old_q))
    else:
        q = {k: v for k, v in item.items() if k not in ("right", "wrong", "theme", "level", "image", "answer_image")}
        q["q"] = text
    q["theme"], q["level"], q["note"] = item["theme"], item["level"], item["note"].strip()
    for key in ("image", "answer_image"):
        p = picture(item.get(key))
        if p:
            q[key] = p
    Q.append(q)
    have.add(qkey(text, q.get("image"), q.get("emoji")) + "|".join(q.get("images") or []))
    added.append(text)
json.dump(pack, open(pack_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"добавлено: {len(added)} | уже были: {len(skipped)} | всего: {len(Q)} | позиции верных: {dict(sorted(counts.items()))}")
for t in skipped:
    print("  уже есть:", t)
for t, old_q in similar:
    print(f"  ПРОВЕРЬ, не повтор ли: «{t}» ↔ «{old_q}»")
