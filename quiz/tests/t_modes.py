import json, urllib.request, http.cookiejar, time
B = "http://localhost:8000"
def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op
def post(op, path, body):
    return json.loads(op.open(urllib.request.Request(B + path, json.dumps(body).encode(), {"Content-Type": "application/json"})).read())
def get(op, path): return json.loads(op.open(B + path).read())
host, pa = client(), client()
r = post(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
H = lambda a, **k: post(host, "/api/host/" + a, {"room": room, "token": tok, **k})
st = lambda: get(pa, f"/api/state?room={room}&pid={pid}")
# Своя игра
H("configure", settings={"mode": "jeopardy"})
pid = post(pa, "/api/join", {"room": room, "name": "A"})["pid"]
post(pa, "/api/seen", {"room": room, "keys": ["0123abcd"]})
H("next"); H("next")
s = st(); print("si", s["phase"])
H("si_pick", theme=0, question=0); s = st(); print("si pick", s["phase"], s["si"].get("cur", {}).get("key"))
for _ in range(40):
    s = st()
    if s["phase"] in ("si_question", "si_answer"): break
    H("next"); time.sleep(0.2)
print("si q", s["phase"], s["si"]["cur"].get("key"))
# Слово на лбу
H("setup"); H("configure", settings={"mode": "heads"}); H("next"); print("heads", st()["phase"])
# 100 к 1
H("setup"); H("configure", settings={"mode": "100to1"}); H("next"); print("feud", st()["phase"])
# Викторина ещё раз (reset) — та же комната, повтор не должен падать
H("setup"); H("configure", settings={"mode": "quiz", "count": 5, "rounds": False}); H("next"); print("quiz", st()["phase"], st().get("qkey"))
H("reset"); H("next"); print("quiz again", st()["phase"])
