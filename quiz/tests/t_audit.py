# Порция 1: перемешанные варианты, «кто ближе», возврат очков, лимиты, закрытые пакеты
import json, sys, urllib.request, urllib.error, http.cookiejar

B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
def call(op, path, body=None):
    try:
        r = op.open(urllib.request.Request(B + path, json.dumps(body).encode()) if body is not None else B + path, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
ok = lambda name, cond, extra="": print(("✓ " if cond else "✗ ОШИБКА ") + name, extra)

host = client(); _, r = call(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
H = lambda a, **kw: call(host, "/api/host/" + a, {"room": room, "token": tok, **kw})[1]
S = lambda op=None, pid=None: call(op or host, f"/api/state?room={room}" + (f"&pid={pid}" if pid else ""))[1]
qs = [{"q": f"Выбор {i}?", "options": ["Верно", "Б", "В", "Г"], "answer": 0} for i in range(8)]
qs += [{"type": "multi", "q": "Несколько?", "options": ["Да1", "Да2", "Нет1", "Нет2"], "answer": [0, 1]},
       {"q": "Оба?", "options": ["А", "Б", "Оба варианта", "Ни один"], "answer": 2},
       {"type": "number", "q": "Число?", "answer": 1000}, {"type": "number", "q": "Число2?", "answer": 1000}]
print(H("upload", pack={"title": "T", "questions": qs}))
H("configure", settings={"mode": "quiz", "pack": "custom", "count": 0, "auto": False, "rounds": False, "sabotage": False, "leaders": False})
a, b = client(), client()
pa = call(a, "/api/join", {"room": room, "name": "Аня"})[1]["pid"]; pb = call(b, "/api/join", {"room": room, "name": "Борис"})[1]["pid"]
H("next")
orders, right = set(), 0
for i in range(8):
    s = S(); opts = s["options"]; orders.add(tuple(opts))
    call(a, "/api/answer", {"room": room, "pid": pa, "answer": opts.index("Верно")}); call(b, "/api/answer", {"room": room, "pid": pb, "answer": opts.index("Б")})
    H("next"); s = S(a, pa)
    right += s["me"]["result"] == "right" and s["options"][s["correct"]] == "Верно" and S(b, pb)["me"]["result"] == "wrong" and s["counts"][opts.index("Верно")] == 1
    H("next")
ok("варианты перемешиваются", len(orders) > 2, f"разных порядков: {len(orders)} из 8"); ok("верный ответ засчитан при любом порядке", right == 8, right)
s = S(); opts = s["options"]
call(a, "/api/answer", {"room": room, "pid": pa, "answer": [opts.index("Да1"), opts.index("Да2")]}); call(b, "/api/answer", {"room": room, "pid": pb, "answer": [opts.index("Да1"), opts.index("Нет1")]})
H("next"); s = S(a, pa); ok("несколько верных", s["me"]["result"] == "right" and sorted(s["options"][i] for i in s["correct"]) == ["Да1", "Да2"] and S(b, pb)["me"]["result"] != "right"); H("next")
s = S(); ok("«оба варианта» не перемешиваются", s["options"] == ["А", "Б", "Оба варианта", "Ни один"]); H("next"); H("next")
call(a, "/api/answer", {"room": room, "pid": pa, "answer": "950"}); call(b, "/api/answer", {"room": room, "pid": pb, "answer": "100"}); H("next")
sa, sb = S(a, pa), S(b, pb); ok("число: ближе всех и близко — полные очки", sa["me"]["result"] == "right" and sa["me"]["last"] in (5, 10), sa["me"]["last"])  # 10 — финальные вопросы, очки ×2; ok("число: далёкий ответ — мало", sb["me"]["last"] <= 2, sb["me"]["last"]); H("next")
call(a, "/api/answer", {"room": room, "pid": pa, "answer": "300"}); H("next")
sa = S(a, pa); ok("число: ближе всех, но далеко — не полные очки", sa["me"]["result"] == "partial" and sa["me"]["last"] < 5, (sa["me"]["result"], sa["me"]["last"]))
# возврат очков
import time; time.sleep(9)  # Аня «вышла» (молчит > 8 с), Борис на связи
S(b, pb)
c = client(); code, j = call(c, "/api/join", {"room": room, "name": "Аня"}); ok("чужой телефон не забирает очки по имени", code == 400 and "pid" not in j, j.get("error"))
code, j = call(a, "/api/join", {"room": room, "name": "Аня"}); ok("свой телефон возвращается", j.get("pid") == pa)
# лимит игроков
host2 = client(); _, r2 = call(host2, "/api/rooms", {}); n = 0
for i in range(63):
    code, j = call(client(), "/api/join", {"room": r2["room"], "name": f"И{i}"}); n += "pid" in j
ok("лимит игроков в комнате", n == 60, n)
# большое тело от не-ведущего
big = client()
try:
    req = urllib.request.Request(B + "/api/join", b'{"room":"' + room.encode() + b'","name":"' + b"x" * 400000 + b'"}'); code = big.open(req, timeout=5).status
except urllib.error.HTTPError as e: code = e.code
except Exception as e: code = repr(e)[:40]
ok("большой запрос от игрока отклонён", code == 413 or "reset" in str(code).lower() or "Broken" in str(code), code)
# перебор кодов
x = client(); codes = [call(x, f"/api/state?room={7000 + i}")[0] for i in range(40)]
ok("перебор кодов останавливается", 429 in codes and codes[0] == 404, f"первый отказ на попытке {codes.index(429) + 1 if 429 in codes else '—'}")
code, j = call(host, "/api/learn/pack?id=general"); ok("тренировка получает только свои темы", code == 200 and {q["theme"] for q in j["questions"]} <= {"Страны и города", "Флаги", "Столицы"} and len(j["questions"]) > 300, len(j.get("questions", [])))
