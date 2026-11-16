import json, urllib.request, http.cookiejar, time
B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
post = lambda op, p, b: json.loads(op.open(urllib.request.Request(B + p, json.dumps(b).encode(), {"Content-Type": "application/json"})).read())
get = lambda op, p: json.loads(op.open(B + p).read())
host = client(); r = post(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
H = lambda a, **k: post(host, "/api/host/" + a, {"room": room, "token": tok, **k})
pack = {"title": "T", "questions": [{"q": f"Вопрос {i}?", "options": ["А", "Б", "В", "Г"], "answer": 0} for i in range(3)]}
H("upload", pack=pack)
H("configure", settings={"mode": "quiz", "pack": "custom", "count": 0, "auto": False, "sabotage": False})
ps = []
for n in range(7):
    c = client(); pid = post(c, "/api/join", {"room": room, "name": f"P{n}"})["pid"]; ps.append((c, pid))
st = lambda: get(host, f"/api/state?room={room}")
H("next")
s = st(); print("phase", s["phase"])
# P0..P5 отвечают верно по очереди, P6 — неверно
for n, (c, pid) in enumerate(ps):
    disp = s["options"]; right = disp.index("А"); wrong = disp.index("Б")
    print(post(c, "/api/answer", {"room": room, "pid": pid, "answer": right if n < 6 else wrong})["ok"], end=" ")
    time.sleep(0.15)
time.sleep(1.2)
s = st(); print("\nphase", s["phase"])
pts = {p["name"]: p["score"] for p in s["players"]}
print("очки:", [pts[f"P{n}"] for n in range(7)], "ожидаем [5, 4, 3, 2, 1, 1, 0]")
print("rope_top", s.get("rope_top"))
# устаревшее «Дальше»: сейчас reveal; жмём next с from=leaders — ничего не должно случиться
print(H("next", **{"from": "leaders", "index": s["index"]}), st()["phase"], "→ должно остаться reveal")
print(H("next", **{"from": "reveal", "index": s["index"]})["ok"], st()["phase"], "→ leaders")
H("next", **{"from": "leaders", "index": s["index"]}); s2 = st(); print("phase", s2["phase"], "index", s2["index"])
# второе нажатие «Следующий вопрос» с того же экрана (двойное касание) — вопрос не должен закончиться
print(H("next", **{"from": "leaders", "index": s["index"]}), st()["phase"], "→ должно остаться question")
# король горы: цель
H("setup"); H("configure", settings={"mode": "king"}); print("king race", st()["settings"]["race"])
