import json, urllib.request, http.cookiejar, hashlib, sys, time
sys.path.insert(0, '.')
B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
def post(op, path, body):
    r = op.open(urllib.request.Request(B + path, json.dumps(body).encode(), {"Content-Type": "application/json"})); return json.loads(r.read())
def get(op, path): return json.loads(op.open(B + path).read())
import server; qk = lambda q: server.qkey(q["q"], q["image"])
gen = server.PACKS["general"]["questions"]
host, pa, pb = client(), client(), client()
r = post(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
# 1) Викторина: тема с 39 вопросами («Убери лишнее»), 10 вопросов; игрок A видел все, кроме 12
th = "Убери лишнее"
pool = [q for q in gen if q.get("theme") == th and q.get("level") in ("normal", "hard")]
fresh = {qk(q) for q in pool[:12]}
post(host, "/api/host/configure", {"room": room, "token": tok, "settings": {"mode": "quiz", "count": 10, "themes": [th], "rounds": False, "auto": False}})
post(pa, "/api/join", {"room": room, "name": "A"}); post(pb, "/api/join", {"room": room, "name": "B"})
print("seen", post(pa, "/api/seen", {"room": room, "keys": [qk(q) for q in pool[12:]] + ["bad", 5]}), len(pool))
post(host, "/api/host/next", {"room": room, "token": tok})
keys = set()
for i in range(10):
    s = get(host, f"/api/state?room={room}")
    assert s["phase"] == "question", s["phase"]
    keys.add(s["qkey"])
    while s["phase"] in ("question", "reveal", "leaders") and (s["phase"] != "question" or s["qkey"] in keys):
        post(host, "/api/host/next", {"room": room, "token": tok}); s = get(host, f"/api/state?room={room}")
print("quiz: all fresh", keys <= fresh, len(keys))
# 2) Царь горы: раунд по теме, только тема th
post(host, "/api/host/setup", {"room": room, "token": tok})
post(host, "/api/host/configure", {"room": room, "token": tok, "settings": {"mode": "king", "themes": [th], "auto": False}})
post(host, "/api/host/next", {"room": room, "token": tok})  # голосование
post(host, "/api/host/next", {"room": room, "token": tok})  # колесо
post(host, "/api/host/next", {"room": room, "token": tok})  # вопрос
s = get(host, f"/api/state?room={room}"); print("king", s["phase"], s["qkey"] in fresh)
# 3) Своя игра: ключи у текущего вопроса
post(host, "/api/host/setup", {"room": room, "token": tok})
post(host, "/api/host/configure", {"room": room, "token": tok, "settings": {"mode": "jeopardy"}})
post(host, "/api/host/next", {"room": room, "token": tok})
s = get(host, f"/api/state?room={room}"); print("si", s["phase"], len(s["si"].get("board") or []))
