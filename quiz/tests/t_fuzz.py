# Случайные действия по API во всех режимах: выгоняем игроков, шлём мусор, выходим в меню посреди игры.
# Потом ищем ошибки сервера (обрыв ответа = исключение в обработчике).
import json, random, sys, urllib.request, urllib.error, http.cookiejar
B = "http://localhost:8000"
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
fails = []

def client():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.open(B + "/").read(); return op

def call(op, path, body=None, tag=""):
    try:
        if body is None:
            return json.loads(op.open(B + path, timeout=5).read())
        return json.loads(op.open(urllib.request.Request(B + path, json.dumps(body).encode()), timeout=5).read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except Exception: fails.append((tag, path, "HTTP %s" % e.code)); return {}
    except Exception as e:
        fails.append((tag, path, json.dumps(body, ensure_ascii=False)[:200] if body else "", repr(e)[:80])); return {}

JUNK = [None, "", "x", -1, 99, 3.5, [], [0], [0, 1, 2, 3], [3, 2, 1, 0], {"a": 1}, [50, 50], [999, 999], "Москва", "12", True, [[1]], "9" * 400]

def play(mode, steps, extra=None):
    host = client(); r = call(host, "/api/rooms", {}); room, tok = r["room"], r["token"]
    H = lambda a, **kw: call(host, "/api/host/" + a, {"room": room, "token": tok, **kw}, mode)
    H("configure", settings={"mode": mode, "auto": random.random() < .5, "seconds": 5, **(extra or {})})
    ps = []
    def join(name):
        c = client(); j = call(c, "/api/join", {"room": room, "name": name, "avatar": "🦊"}, mode)
        if j.get("pid"): ps.append([c, j["pid"], name])
    for n in ["Аня", "Борис", "Вика", "Гена"]: join(n)
    H("next")
    phases = set()
    for i in range(steps):
        s = call(host, f"/api/state?room={room}", tag=mode)
        ph = s.get("phase"); phases.add(ph)
        if not ph: break
        for c, pid, name in list(ps):
            st = call(c, f"/api/state?room={room}&pid={pid}", tag=mode + ":" + str(ph))
            a = random.random()
            P = lambda path, **kw: call(c, path, {"room": room, "pid": pid, **kw}, mode + ":" + str(ph))
            if ph == "question":
                if a < .6: P("/api/answer", answer=random.choice(JUNK + [0, 1, 2, 3, [0, 1], [1, 0, 2, 3], "42", [55.7, 37.6]]))
                elif a < .7: P("/api/answer", skip=True)
            elif ph == "topic_vote" and s.get("topic"): P("/api/vote", theme=random.choice(s["topic"]["options"] + JUNK[:4]))
            elif ph == "perks":
                if a < .4: P("/api/double", on=random.choice([True, False, None]))
                elif a < .7: P("/api/trick", to=random.choice([p[1] for p in ps] + [None, "zzz"]))
                else: P("/api/perks_ready")
            elif ph in ("reveal", "leaders"):
                if a < .3: P("/api/double", on=True)
                elif a < .5: P("/api/trick", to=random.choice([p[1] for p in ps] + [None]))
                elif a < .7: P("/api/react", e=random.choice(["👏", "x", None]))
            elif str(ph).startswith("si_"):
                act = random.choice(["pick", "give", "stake", "buzz", "answer", "bet", "final"])
                P("/api/si/" + act, theme=random.choice([0, 1, 5, -1, "x", None]), question=random.choice([0, 1, 4, 9, None]),
                  to=random.choice([p[1] for p in ps] + [None]), amount=random.choice([100, 0, -5, 99999, "x", None]), text=random.choice(["Москва", "", None, 5, "x" * 300]))
            elif str(ph).startswith("hd_"):
                act = random.choice(["start", "mark", "claim", "fix"])
                P("/api/hd/" + act, ok=random.choice([True, False, None]), n=random.choice([0, 1, 2, 3, None, "x"]), index=random.choice([0, 1, 9, -1, None]))
            elif str(ph).startswith("fd_"):
                P("/api/fd/" + random.choice(["guess", "big"]), text=random.choice(["деньги", "", None, 7, "x" * 300]))
        b = random.random()
        if b < .35: H("next")
        elif b < .40 and ps:
            v = random.choice(ps); H("kick", pid=v[1]); ps.remove(v)
        elif b < .44: join("Новый%d" % i)
        elif b < .47: H("pause", on=random.choice([True, False]))
        elif b < .49: H("si_pick", theme=random.choice([0, 1, 7, None]), question=random.choice([0, 3, 8, None])); H("si_override", index=random.choice([0, 1, None, "x"]))
        elif b < .51: H("hd_fix", index=random.choice([0, 5])); H("fd_open", index=random.choice([0, 1, 9, None])); H("fd_unstrike")
        elif b < .52: H("pause", on=False); H("setup"); H("configure", settings={"mode": mode, **(extra or {})}); H("next")
        elif b < .53: H("pause", on=False); H("reset"); H("next")
        if ph == "final" and random.random() < .5: H("reset"); H("next")
        import time; time.sleep(0.03)
    return phases

for mode, extra in [("king", None), ("quiz", {"count": 6, "rounds": False}), ("quiz", {"count": 6, "teams": 2, "rounds": True}), ("jeopardy", None), ("heads", None), ("heads", {"hd_teams": 0}), ("100to1", None)]:
    ph = play(mode, 140, extra)
    print(mode, extra or "", "этапы:", " ".join(sorted(str(p) for p in ph)))
print("СБОИ:", len(fails))
for f in fails[:25]: print("  ", f)
