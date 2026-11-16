import json, urllib.request, http.cookiejar, time
B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
post = lambda op, p, b: json.loads(op.open(urllib.request.Request(B + p, json.dumps(b).encode(), {"Content-Type": "application/json"})).read())
get = lambda op, p: json.loads(op.open(B + p).read())
host = client(); r = post(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
H = lambda a, **k: post(host, "/api/host/" + a, {"room": room, "token": tok, **k})
st = lambda c=None, pid="": get(c or host, f"/api/state?room={room}&pid={pid}")
ps = []
def join(n):
    c = client(); pid = post(c, "/api/join", {"room": room, "name": n})["pid"]; ps.append((c, pid))
# Викторина 6 вопросов: подстройка и финал ×2
QS = json.load(open("packs/general.json"))["questions"]
def right_idx(s):
    q = next((q for q in QS if q["q"] == s["question"] and sorted(q.get("options") or []) == sorted(s["options"])), None)
    if not q or q.get("type", "choice") != "choice": return 0
    return s["options"].index(q["options"][q["answer"]])
H("configure", settings={"mode": "quiz", "count": 10, "auto": False, "sabotage": False, "themes": ["Космос"]})
for n in ["Аня", "Борис", "Вика"]: join(n)
H("next")
for q in range(10):
    s = st(); right = None
    # верный ответ знаем у ведущего только после показа — отвечаем первым вариантом, потом смотрим очки
    sc = st(*ps[0])
    print(f"вопрос {s['index']}: уровень {s['level']}, adapt={s.get('adapt')}, final_x2={s.get('final_x2')}")
    good = right_idx(s)
    for i, (c, pid) in enumerate(ps):
        ok = q < 3 or i != 2  # Вика ошибается с 4-го вопроса, Аня и Борис — всегда верно
        if not s["options"]:
            post(c, "/api/answer", {"room": room, "pid": pid, "skip": True}); continue
        post(c, "/api/answer", {"room": room, "pid": pid, "answer": good if ok else (good + 1) % len(s["options"])})
        time.sleep(0.1)
    time.sleep(1.2)
    s = st(); print("   очки за вопрос:", [p["last"] for p in s["players"]])
    post(ps[1][0], "/api/react", {"room": room, "pid": ps[1][1], "e": "👏"})
    print("   реакции:", [r["e"] + r["name"] for r in st()["reactions"]])
    H("next")
    if st()["phase"] == "final": break
    H("next")
    if st()["phase"] not in ("question", "final"): H("next")
s = st(); print("этап", s["phase"]); print("награды:", [(a["title"], a["name"], a["detail"]) for a in s.get("awards", [])])
