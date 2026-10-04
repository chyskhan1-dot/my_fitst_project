"""Сервер квиза для компании друзей.

На главной странице любой может нажать «Я ведущий» — сервер создаст комнату
с кодом из 4 цифр. Игроки нажимают «Я игрок», вводят код и имя.
Комнат может быть сколько угодно, игры в них идут независимо.
Нужен только Python, без библиотек.

Вопросы хранятся пакетами в папке packs/ (по файлу .json на пакет).
Картинки и аудио можно положить в media/ или вшить прямо в пакет.

Запуск на компьютере:  python server.py
Онлайн (Render и т.п.): порт берётся из переменной окружения PORT.
"""

import base64
import binascii
import hashlib
import json
import mimetypes
import os
import secrets
import socket
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BASE = Path(__file__).parent
STATIC = BASE / "static"
PACKS_DIR = BASE / "packs"
MEDIA_DIR = BASE / "media"
# Версия сайта: меняется при каждом обновлении файлов. Открытые страницы
# сравнивают её со своей и перезагружаются, если сервер обновился.
VERSION = hashlib.md5(
    b"".join(f.read_bytes() for f in [Path(__file__), *sorted(STATIC.iterdir())])
).hexdigest()[:8]

REVEAL_PAUSE = 0.8  # пауза перед показом ответа, когда все уже ответили
REVEAL_SECONDS = 4  # автопереход: сколько показываем правильный ответ
LEADERS_SECONDS = 5  # автопереход: сколько показываем таблицу лидеров
ROOM_IDLE = 3 * 60 * 60  # комната без активности удаляется через 3 часа
MAX_ROOMS = 500
MAX_BODY = 25 * 1024 * 1024  # самый большой запрос (пакет с картинками и аудио)
MAX_MEDIA_TOTAL = 300 * 1024 * 1024  # сколько загруженных файлов держим в памяти на все комнаты
MAX_QUESTIONS = 200

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/aac", "audio/webm"}

lock = threading.Lock()
DEVICE_COOKIE = "quiz_device"  # метка устройства: один игрок на один телефон
JOIN_URL = None  # адрес для игроков; онлайн берётся из адреса страницы

TEAMS = ["Красные", "Синие", "Жёлтые", "Зелёные"]
MODES = ["quiz"]  # «Своя игра» и «100 к 1» пока в разработке
PENALTY = 300  # сколько очков снимаем за неверный ответ


class PackError(ValueError):
    pass


def media_ref(value, kind, store, scope):
    """Превращает ссылку на картинку или аудио из пакета в адрес, который поймёт браузер.

    Можно: ссылку из интернета (https://...), файл из папки media/ (media/cat.jpg)
    или сам файл, вшитый в пакет (data:image/jpeg;base64,...).
    """
    if not value:
        return None
    if not isinstance(value, str):
        raise PackError("ссылка на файл должна быть текстом")
    value = value.strip()
    if value.startswith(("https://", "http://")):
        if len(value) > 2000:
            raise PackError("слишком длинная ссылка")
        return value
    if value.startswith("data:"):
        if store is None:
            raise PackError("вшитые файлы здесь не поддерживаются")
        head, _, body = value.partition(",")
        mime = head[5:].split(";")[0].lower()
        allowed = IMAGE_TYPES if kind == "image" else AUDIO_TYPES
        if mime not in allowed or ";base64" not in head:
            raise PackError(f"неподдерживаемый формат файла: {mime or 'неизвестно'}")
        try:
            data = base64.b64decode(body, validate=True)
        except (binascii.Error, ValueError):
            raise PackError("файл повреждён")
        key = hashlib.sha1(data).hexdigest()[:16]
        store[key] = (mime, data)
        return f"/m/{scope}/{key}"
    path = value.removeprefix("/").removeprefix("media/")
    if (MEDIA_DIR / path).resolve().is_relative_to(MEDIA_DIR.resolve()) and (MEDIA_DIR / path).is_file():
        return "/media/" + path
    raise PackError(f"файл не найден: {value}")


def clean_pack(data, store=None, scope="_"):
    """Проверяет пакет вопросов и приводит его к единому виду."""
    if not isinstance(data, dict):
        raise PackError("файл не похож на пакет вопросов")
    title = str(data.get("title") or "Без названия").strip()[:60]
    raw = data.get("questions")
    if not isinstance(raw, list) or not raw:
        raise PackError("в пакете нет вопросов")
    if len(raw) > MAX_QUESTIONS:
        raise PackError(f"слишком много вопросов, максимум {MAX_QUESTIONS}")
    questions = []
    for n, q in enumerate(raw, 1):
        try:
            if not isinstance(q, dict):
                raise PackError("неверный формат")
            text = str(q.get("q") or "").strip()
            options = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
            answer = q.get("answer")
            if not text:
                raise PackError("нет текста вопроса")
            if not 2 <= len(options) <= 4:
                raise PackError("нужно от 2 до 4 вариантов ответа")
            if not isinstance(answer, int) or not 0 <= answer < len(options):
                raise PackError("не указан правильный ответ")
            questions.append({
                "q": text[:300],
                "options": [o[:100] for o in options],
                "answer": answer,
                "image": media_ref(q.get("image"), "image", store, scope),
                "audio": media_ref(q.get("audio"), "audio", store, scope),
            })
        except PackError as e:
            raise PackError(f"вопрос {n}: {e}")
    return {"title": title, "questions": questions}


BUILTIN_MEDIA = {}  # файлы, вшитые во встроенные пакеты
PACKS = {}  # id пакета -> пакет
PACK_FILES = {}  # id пакета -> исходный файл (для редактора)
for f in sorted(PACKS_DIR.glob("*.json")):
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
        PACKS[f.stem] = clean_pack(raw, BUILTIN_MEDIA, "_")
        PACK_FILES[f.stem] = f
    except (json.JSONDecodeError, PackError) as e:
        print(f"Пакет {f.name} пропущен: {e}", flush=True)
DEFAULT_PACK = "general" if "general" in PACKS else next(iter(PACKS), None)

DEFAULTS = {
    "mode": "quiz",
    "pack": DEFAULT_PACK,
    "penalty": False,  # штраф за неверный ответ
    "teams": 0,  # 0 — каждый сам за себя, иначе число команд (2–4)
    "speed": True,  # бонус за скорость ответа
    "streak": False,  # бонус за серию правильных ответов
    "leaders": True,  # таблица лидеров после каждого вопроса
    "auto": True,  # дальше без нажатий: ответ → лидеры → следующий вопрос
    "seconds": 20,
}


def media_total():
    return sum(len(d) for g in rooms.values() for _, d in g.media.values())


class Game:
    def __init__(self, code, host_device):
        self.code = code
        self.host_device = host_device  # управлять игрой может только устройство, создавшее комнату
        self.host_token = secrets.token_urlsafe(16)
        self.touched = time.time()
        # id -> {"name", "device", "team", "score", "last_points", "prev_place", "streak"}
        self.players = {}
        self.settings = dict(DEFAULTS)
        self.custom = None  # свой пакет, загруженный ведущим
        self.media = {}  # файлы из своего пакета
        self.reset()

    def clean_settings(self, data):
        """Берём из присланных настроек только то, что знаем, и проверяем значения."""
        s = dict(DEFAULTS)
        for key, default in DEFAULTS.items():
            if isinstance(default, bool):
                s[key] = bool(data.get(key, default))
        if data.get("mode") in MODES:
            s["mode"] = data["mode"]
        if data.get("pack") in PACKS or (data.get("pack") == "custom" and self.custom):
            s["pack"] = data["pack"]
        if data.get("teams") in (0, 2, 3, 4):
            s["teams"] = data["teams"]
        if data.get("seconds") in (10, 20, 30):
            s["seconds"] = data["seconds"]
        return s

    @property
    def pack(self):
        return self.custom if self.settings["pack"] == "custom" else PACKS[self.settings["pack"]]

    def reset(self, phase="setup"):
        for p in self.players.values():
            p.update(score=0, last_points=0, prev_place=0, streak=0)
        self.team_prev = {}
        self.phase = phase  # setup -> lobby -> question -> reveal -> leaders -> ... -> final
        self.phase_at = time.time()
        self.index = -1
        self.started_at = 0.0
        self.answers = {}  # id -> {"choice", "time"}
        self.all_answered_at = None

    def set_phase(self, phase):
        self.phase = phase
        self.phase_at = time.time()

    def configure(self, data):
        self.settings = self.clean_settings(data)
        self.reset("lobby")
        self.balance_teams()

    def upload(self, data):
        store = {}
        pack = clean_pack(data, store, self.code)
        size = sum(len(d) for _, d in store.values())
        if media_total() - sum(len(d) for _, d in self.media.values()) + size > MAX_MEDIA_TOTAL:
            raise PackError("на сервере закончилось место для файлов, попробуй пакет поменьше")
        self.custom, self.media = pack, store
        self.settings["pack"] = "custom"
        return pack

    def balance_teams(self):
        """Раздаём команды тем, у кого её нет: в самую маленькую."""
        n = self.settings["teams"]
        for p in self.players.values():
            if not n:
                p["team"] = None
            elif p.get("team") is None or p["team"] >= n:
                p["team"] = None
                sizes = [sum(1 for x in self.players.values() if x.get("team") == t) for t in range(n)]
                p["team"] = sizes.index(min(sizes))

    @property
    def seconds(self):
        return self.settings["seconds"]

    def question(self):
        return self.pack["questions"][self.index]

    def tick(self):
        """Двигает игру по времени: конец вопроса и автопереход."""
        now = time.time()
        if self.phase == "question":
            everyone = self.players and len(self.answers) >= len(self.players)
            if everyone and self.all_answered_at is None:
                self.all_answered_at = now
            time_up = now - self.started_at >= self.seconds
            if time_up or (self.all_answered_at and now - self.all_answered_at >= REVEAL_PAUSE):
                self.finish_question()
        elif self.settings["auto"] and self.auto_left() == 0:
            self.next()

    def auto_left(self):
        """Сколько секунд до автоперехода, или None, если его нет."""
        if not self.settings["auto"] or self.phase not in ("reveal", "leaders"):
            return None
        wait = REVEAL_SECONDS if self.phase == "reveal" else LEADERS_SECONDS
        return max(0, round(wait - (time.time() - self.phase_at), 1))

    def finish_question(self):
        rules = self.settings
        correct = self.question()["answer"]
        # Запоминаем места до начисления очков, чтобы показать стрелки ↑↓.
        for place, row in enumerate(self.leaderboard(), 1):
            self.players[row["id"]]["prev_place"] = place
        self.team_prev = {t["team"]: place for place, t in enumerate(self.team_board(), 1)}
        for pid, p in self.players.items():
            a = self.answers.get(pid)
            points = 0
            if a and a["choice"] == correct:
                if rules["speed"]:
                    # Быстрый правильный ответ даёт до 1000 очков, медленный — от 500.
                    points = round(500 + 500 * max(0.0, 1 - a["time"] / self.seconds))
                else:
                    points = 1000
                p["streak"] += 1
                if rules["streak"] and p["streak"] >= 2:
                    points += min(500, 100 * (p["streak"] - 1))  # +100 за каждый ответ серии, до +500
            else:
                p["streak"] = 0
                if a and rules["penalty"]:
                    points = -min(PENALTY, p["score"])  # ниже нуля не опускаемся
            p["last_points"] = points
            p["score"] += points
        self.set_phase("reveal")

    def next(self):
        last = self.index + 1 >= len(self.pack["questions"])
        if self.phase == "reveal" and not last and self.settings["leaders"]:
            self.set_phase("leaders")
            return
        if last and self.phase in ("reveal", "leaders"):
            self.set_phase("final")
            return
        self.index += 1
        self.set_phase("question")
        self.started_at = time.time()
        self.answers = {}
        self.all_answered_at = None

    def leaderboard(self):
        rows = [
            {
                "id": pid,
                "name": p["name"],
                "team": p.get("team"),
                "score": p["score"],
                "last": p["last_points"],
                "prev": p["prev_place"],
                "streak": p["streak"],
            }
            for pid, p in self.players.items()
        ]
        rows.sort(key=lambda r: (-r["score"], r["name"].lower()))
        return rows

    def team_board(self):
        """Счёт команды — среднее по игрокам, чтобы большая команда не выигрывала числом."""
        rows = []
        for t in range(self.settings["teams"]):
            members = [p for p in self.players.values() if p.get("team") == t]
            n = max(1, len(members))
            rows.append({
                "team": t,
                "name": TEAMS[t],
                "size": len(members),
                "score": round(sum(p["score"] for p in members) / n),
                "last": round(sum(p["last_points"] for p in members) / n),
                "prev": self.team_prev.get(t, 0),
            })
        rows.sort(key=lambda r: (-r["score"], r["team"]))
        return rows

    def player_of(self, device):
        """Игрок, который уже зашёл с этого устройства."""
        for pid, p in self.players.items():
            if device and p["device"] == device:
                return pid
        return None

    def owns(self, pid, device):
        return pid in self.players and device and self.players[pid]["device"] == device

    def state(self, pid=None, device=None):
        self.tick()
        s = {
            "title": self.pack["title"] if self.phase != "setup" else "Квиз",
            "phase": self.phase,
            "index": self.index,
            "total": len(self.pack["questions"]),
            "seconds": self.seconds,
            "settings": self.settings,
            "team_names": TEAMS,
            "players": self.leaderboard(),
            "teams": self.team_board(),
            "answered": len(self.answers),
            "room": self.code,
            "join": JOIN_URL,
            "version": VERSION,
            "auto_left": self.auto_left(),
        }
        if self.phase == "setup":
            s["packs"] = [{"id": k, "title": p["title"], "count": len(p["questions"])} for k, p in PACKS.items()]
            if self.custom:
                s["custom"] = {"title": self.custom["title"], "count": len(self.custom["questions"])}
        if self.phase in ("question", "reveal"):
            q = self.question()
            s["question"] = q["q"]
            s["options"] = q["options"]
            s["image"] = q["image"]
            s["audio"] = q["audio"]
            s["left"] = max(0, round(self.seconds - (time.time() - self.started_at), 1))
        if self.phase == "reveal":
            s["correct"] = q["answer"]
            counts = [0] * len(q["options"])
            for a in self.answers.values():
                counts[a["choice"]] += 1
            s["counts"] = counts
        if self.owns(pid, device):
            me = self.players[pid]
            s["me"] = {
                "name": me["name"],
                "team": me.get("team"),
                "score": me["score"],
                "last": me["last_points"],
                "prev": me["prev_place"],
                "streak": me["streak"],
                "choice": self.answers.get(pid, {}).get("choice"),
                "place": [r["id"] for r in s["players"]].index(pid) + 1,
            }
            if me.get("team") is not None:
                s["me"]["team_place"] = [t["team"] for t in s["teams"]].index(me["team"]) + 1
        return s


rooms = {}  # код комнаты -> Game


def cleanup():
    now = time.time()
    for code in [c for c, g in rooms.items() if now - g.touched > ROOM_IDLE]:
        del rooms[code]


def create_room(device):
    cleanup()
    # у одного устройства одна комната: старую закрываем
    for code in [c for c, g in rooms.items() if g.host_device == device]:
        del rooms[code]
    if len(rooms) >= MAX_ROOMS:
        return None
    code = f"{secrets.randbelow(9000) + 1000}"
    while code in rooms:
        code = f"{secrets.randbelow(9000) + 1000}"
    rooms[code] = Game(code, device)
    return rooms[code]


def local_ip():
    """IP компьютера в домашней сети — по нему подключаются телефоны."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # не засоряем консоль запросами каждые полсекунды

    def send_json(self, data, code=200):
        self.send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", code, "no-store")

    def send_bytes(self, body, mime, code=200, cache="no-cache", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def device(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie[DEVICE_COOKIE].value if DEVICE_COOKIE in cookie else None

    def send_file(self, name, set_device=False):
        extra = {}
        if set_device and not self.device():
            extra["Set-Cookie"] = f"{DEVICE_COOKIE}={secrets.token_urlsafe(12)}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax"
        mime = "text/html; charset=utf-8" if name.endswith(".html") else "text/javascript; charset=utf-8"
        self.send_bytes((STATIC / name).read_bytes(), mime, extra=extra)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return None
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        parts = url.path.strip("/").split("/")
        if url.path == "/":
            self.send_file("play.html", set_device=True)
        elif url.path == "/host":
            self.send_file("host.html", set_device=True)
        elif url.path == "/editor":
            self.send_file("editor.html", set_device=True)
        elif parts[0] == "static" and len(parts) == 2 and parts[1].endswith(".js") and (STATIC / parts[1]).is_file():
            self.send_file(parts[1])
        elif url.path == "/healthz":
            self.send_json({"ok": True})
        elif parts[0] == "media" and len(parts) > 1:
            path = (MEDIA_DIR / unquote("/".join(parts[1:]))).resolve()
            if not path.is_relative_to(MEDIA_DIR.resolve()) or not path.is_file():
                return self.send_json({"error": "Файл не найден"}, 404)
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_bytes(path.read_bytes(), mime, cache="public, max-age=86400")
        elif parts[0] == "m" and len(parts) == 3:
            with lock:
                store = BUILTIN_MEDIA if parts[1] == "_" else getattr(rooms.get(parts[1]), "media", {})
                item = store.get(parts[2])
            if not item:
                return self.send_json({"error": "Файл не найден"}, 404)
            self.send_bytes(item[1], item[0], cache="public, max-age=86400")
        elif url.path == "/api/packs":
            self.send_json([{"id": k, "title": p["title"], "count": len(p["questions"])} for k, p in PACKS.items()])
        elif parts[:2] == ["api", "packs"] and len(parts) == 3 and parts[2] in PACK_FILES:
            self.send_bytes(PACK_FILES[parts[2]].read_bytes(), "application/json; charset=utf-8")
        elif url.path == "/api/state":
            with lock:
                game = rooms.get(query.get("room", [""])[0])
                if not game:
                    return self.send_json({"error": "Комната не найдена", "phase": "gone"}, 404)
                game.touched = time.time()
                self.send_json(game.state(query.get("pid", [None])[0], self.device()))
        else:
            self.send_json({"error": "Страница не найдена"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_json()
        if data is None:
            return self.send_json({"error": "Файл слишком большой: максимум 25 МБ вместе с картинками и аудио"}, 413)
        device = self.device()
        with lock:
            if not device:
                return self.send_json({"error": "Обнови страницу. Если не помогло, разреши cookies в браузере"}, 400)

            if path == "/api/rooms":
                game = create_room(device)
                if not game:
                    return self.send_json({"error": "Сервер переполнен, попробуй позже"}, 503)
                return self.send_json({"room": game.code, "token": game.host_token})

            game = rooms.get(str(data.get("room", "")))
            if not game:
                return self.send_json({"error": "Комнаты с таким кодом нет. Проверь код у ведущего"}, 404)
            game.touched = time.time()

            if path == "/api/join":
                mine = game.player_of(device)
                if mine and game.phase not in ("setup", "lobby"):
                    return self.send_json({"pid": mine})  # вернули своего игрока, новый не создаём
                name = str(data.get("name", "")).strip()[:20]
                if not name:
                    return self.send_json({"error": "Введи имя"}, 400)
                taken = {p["name"].lower() for pid, p in game.players.items() if pid != mine}
                if name.lower() in taken:
                    return self.send_json({"error": "Это имя уже занято"}, 400)
                team = data.get("team")
                if not (isinstance(team, int) and 0 <= team < game.settings["teams"]):
                    team = None
                if mine:
                    game.players[mine]["name"] = name  # с этого телефона уже играют: просто меняем имя
                    if team is not None:
                        game.players[mine]["team"] = team
                    game.balance_teams()
                    return self.send_json({"pid": mine})
                pid = secrets.token_urlsafe(8)
                game.players[pid] = {
                    "name": name, "device": device, "team": team,
                    "score": 0, "last_points": 0, "prev_place": 0, "streak": 0,
                }
                game.balance_teams()
                return self.send_json({"pid": pid})

            if path == "/api/team":
                pid, team = data.get("pid"), data.get("team")
                ok = (
                    game.phase == "lobby"
                    and game.owns(pid, device)
                    and isinstance(team, int)
                    and 0 <= team < game.settings["teams"]
                )
                if ok:
                    game.players[pid]["team"] = team
                return self.send_json({"ok": ok})

            if path == "/api/answer":
                pid, choice = data.get("pid"), data.get("choice")
                game.tick()
                ok = (
                    game.phase == "question"
                    and game.owns(pid, device)
                    and pid not in game.answers
                    and isinstance(choice, int)
                    and 0 <= choice < len(game.question()["options"])
                )
                if ok:
                    game.answers[pid] = {"choice": choice, "time": time.time() - game.started_at}
                return self.send_json({"ok": ok})

            if path.startswith("/api/host/"):
                if data.get("token") != game.host_token or device != game.host_device:
                    return self.send_json({"error": "Управлять игрой может только ведущий этой комнаты"}, 403)
                action = path.rsplit("/", 1)[1]
                if action == "upload":
                    if game.phase != "setup":
                        return self.send_json({"error": "Пакет можно сменить только в главном меню"}, 400)
                    try:
                        pack = game.upload(data.get("pack"))
                    except PackError as e:
                        return self.send_json({"error": f"Пакет не загружен: {e}"}, 400)
                    return self.send_json({"ok": True, "title": pack["title"], "count": len(pack["questions"])})
                if action == "configure":
                    game.configure(data.get("settings") or {})
                elif action == "setup":
                    game.reset("setup")  # назад в меню, игроки остаются
                elif action == "next":
                    if game.phase in ("setup", "final"):
                        return self.send_json({"error": "Сначала создай игру"}, 400)
                    game.tick()
                    if game.phase == "question":
                        game.finish_question()  # ведущий может показать ответ досрочно
                    else:
                        game.next()
                elif action == "reset":
                    game.reset("lobby")  # та же игра с теми же правилами ещё раз
                elif action == "kick":
                    game.players.pop(data.get("pid"), None)
                elif action != "check":
                    return self.send_json({"error": "Неизвестное действие"}, 400)
                return self.send_json({"ok": True})

        self.send_json({"error": "Страница не найдена"}, 404)


def main():
    global JOIN_URL
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Пакетов вопросов: {len(PACKS)} ({', '.join(PACKS)})", flush=True)
    if "PORT" in os.environ:
        print(f"Квиз запущен на порту {port}", flush=True)
    else:
        ip = local_ip()
        JOIN_URL = f"http://{ip}:{port}"
        print("=" * 52)
        print(" Квиз запущен!")
        print(" Открой на этом компьютере и нажми «Я ведущий»:")
        print(f"   http://localhost:{port}")
        print(" Игроки (телефоны в том же Wi-Fi) открывают:")
        print(f"   http://{ip}:{port}")
        print(" Редактор вопросов:")
        print(f"   http://localhost:{port}/editor")
        print(" Остановить: Ctrl+C")
        print("=" * 52, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")


if __name__ == "__main__":
    main()
