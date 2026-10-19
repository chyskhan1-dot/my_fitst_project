# Копирует вопросы пакета «Футбол» в «Общие знания» темой «Футбол».
# Пока футбол живёт и отдельным квизом (packs/football.json), он — главный: правь вопросы там, потом запускай этот скрипт.
# Запуск из корня репозитория: python3 .claude/skills/quiz-questions/scripts/sync_football.py
# Старые вопросы темы «Футбол» в general.json заменяются целиком, потом нужен check_pack.js.
import json, os

PACKS = os.path.join(os.getcwd(), "quiz", "packs")
THEME = "Футбол"
general_path = os.path.join(PACKS, "general.json")
general = json.load(open(general_path, encoding="utf-8"))
football = json.load(open(os.path.join(PACKS, "football.json"), encoding="utf-8"))

rest = [q for q in general["questions"] if q.get("theme") != THEME]
copied = [{**q, "theme": THEME} for q in football["questions"]]
general["questions"] = rest + copied
with open(general_path, "w", encoding="utf-8") as f:
    f.write(json.dumps(general, ensure_ascii=False, indent=1) + "\n")
print(f"тема «{THEME}»: {len(copied)} вопросов | всего в general: {len(general['questions'])}")
