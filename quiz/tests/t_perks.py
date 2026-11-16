import json, urllib.request, http.cookiejar, time
B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
post = lambda op, p, b: json.loads(op.open(urllib.request.Request(B + p, json.dumps(b).encode(), {"Content-Type": "application/json"})).read())
get = lambda op, p: json.loads(op.open(B + p).read())
host = client(); r = post(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
H = lambda a, **k: post(host, "/api/host/" + a, {"room": room, "token": tok, **k})
H("configure", settings={"mode": "king", "doubles": True, "auto": False})
ps = []
for n in range(3):
    c = client(); pid = post(c, "/api/join", {"room": room, "name": f"P{n}"})["pid"]; ps.append((c, pid))
st = lambda c=None, pid="": get(c or host, f"/api/state?room={room}&pid={pid}")
H("next"); H("next"); H("next")  # голосование → колесо → перки
s = st(); print("этап", s["phase"], "ждём", s["perks"]["waiting"], "left", s["perks"]["left"])
c0, p0 = ps[0]
me = st(c0, p0)["me"]; print("P0 can_bet", me["can_bet"], "perks_turn", me["perks_turn"])
print("×2", post(c0, "/api/double", {"room": room, "pid": p0, "on": True}))
s = st(); print("ждём", s["perks"]["waiting"], "×2:", s["perks"]["doubled"])
for c, pid in ps[1:]: post(c, "/api/perks_ready", {"room": room, "pid": pid})
s = st(); print("этап после «Готово» всех", s["phase"], "index", s["index"])
for i in range(3):
    s0 = st(c0, p0); print("вопрос", s0["index"], s0["phase"], "P0 doubled", s0["me"]["doubled"])
    H("next"); H("next")  # показать ответ → таблица
    if i < 2: H("next")
print("после раунда:", st()["phase"])
H("next"); s = st(); print("новый раунд:", s["phase"])
print("P0 doubles left", st(c0, p0)["me"]["doubles"], "bet", st(c0, p0)["me"]["doubled"])
