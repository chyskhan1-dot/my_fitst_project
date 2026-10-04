"""Сервер квиза для компании друзей.

Ведущий открывает /host на большом экране, игроки заходят с телефонов
на главную страницу и вводят имя. Нужен только Python, без библиотек.

Запуск на компьютере:  python server.py
Онлайн (Render и т.п.): порт берётся из переменной окружения PORT.
"""

import json
import os
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).parent
STATIC = BASE / "static"
QUIZ = json.loads((BASE / "questions.json").read_text(encoding="utf-8"))
SECONDS = QUIZ.get("seconds", 20)
REVEAL_PAUSE = 1.0  # пауза перед показом ответа, когда все уже ответили

# Ключ ведущего: без него управлять игрой нельзя. Можно задать свой через HOST_KEY.
HOST_KEY = os.environ.get("HOST_KEY") or secrets.token_urlsafe(6)

lock = threading.Lock()
JOIN_URL = None  # адрес для игроков; онлайн берётся из адреса страницы


class Game:
    def __init__(self):
        self.players = {}  # id -> {"name", "score", "last_points"}
        self.reset()

    def reset(self):
        for p in self.players.values():
            p["score"] = 0
            p["last_points"] = 0
        self.phase = "lobby"  # lobby -> question -> reveal -> ... -> final
        self.index = -1
        self.started_at = 0.0
        self.answers = {}  # id -> {"choice", "time"}
        self.all_answered_at = None

    def question(self):
        return QUIZ["questions"][self.index]

    def tick(self):
        """Заканчивает вопрос, когда вышло время или ответили все."""
        if self.phase != "question":
            return
        now = time.time()
        everyone = self.players and len(self.answers) >= len(self.players)
        if everyone and self.all_answered_at is None:
            self.all_answered_at = now
        time_up = now - self.started_at >= SECONDS
        if time_up or (self.all_answered_at and now - self.all_answered_at >= REVEAL_PAUSE):
            self.finish_question()

    def finish_question(self):
        correct = self.question()["answer"]
        for pid, p in self.players.items():
            a = self.answers.get(pid)
            points = 0
            if a and a["choice"] == correct:
                # Быстрый правильный ответ даёт до 1000 очков, медленный — от 500.
                speed = max(0.0, 1 - a["time"] / SECONDS)
                points = round(500 + 500 * speed)
            p["last_points"] = points
            p["score"] += points
        self.phase = "reveal"

    def next(self):
        if self.index + 1 >= len(QUIZ["questions"]):
            self.phase = "final"
            return
        self.index += 1
        self.phase = "question"
        self.started_at = time.time()
        self.answers = {}
        self.all_answered_at = None

    def leaderboard(self):
        rows = [
            {"id": pid, "name": p["name"], "score": p["score"], "last": p["last_points"]}
            for pid, p in self.players.items()
        ]
        rows.sort(key=lambda r: -r["score"])
        return rows

    def state(self, pid=None):
        self.tick()
        s = {
            "title": QUIZ.get("title", "Квиз"),
            "phase": self.phase,
            "index": self.index,
            "total": len(QUIZ["questions"]),
            "seconds": SECONDS,
            "players": self.leaderboard(),
            "answered": len(self.answers),
            "join": JOIN_URL,
        }
        if self.phase in ("question", "reveal"):
            q = self.question()
            s["question"] = q["q"]
            s["options"] = q["options"]
            s["left"] = max(0, round(SECONDS - (time.time() - self.started_at), 1))
        if self.phase == "reveal":
            s["correct"] = self.question()["answer"]
            counts = [0] * len(self.question()["options"])
            for a in self.answers.values():
                counts[a["choice"]] += 1
            s["counts"] = counts
        if pid in self.players:
            me = self.players[pid]
            s["me"] = {
                "name": me["name"],
                "score": me["score"],
                "last": me["last_points"],
                "choice": self.answers.get(pid, {}).get("choice"),
                "place": [r["id"] for r in s["players"]].index(pid) + 1,
            }
        return s


game = Game()


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
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, name):
        body = (STATIC / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/":
            self.send_file("play.html")
        elif url.path == "/host":
            self.send_file("host.html")
        elif url.path == "/healthz":
            self.send_json({"ok": True})
        elif url.path == "/api/state":
            with lock:
                self.send_json(game.state(query.get("pid", [None])[0]))
        else:
            self.send_json({"error": "Страница не найдена"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_json()
        with lock:
            if path == "/api/join":
                name = str(data.get("name", "")).strip()[:20]
                if not name:
                    return self.send_json({"error": "Введи имя"}, 400)
                taken = {p["name"].lower() for p in game.players.values()}
                if name.lower() in taken:
                    return self.send_json({"error": "Это имя уже занято"}, 400)
                pid = secrets.token_urlsafe(8)
                game.players[pid] = {"name": name, "score": 0, "last_points": 0}
                return self.send_json({"pid": pid})

            if path == "/api/answer":
                pid, choice = data.get("pid"), data.get("choice")
                game.tick()
                ok = (
                    game.phase == "question"
                    and pid in game.players
                    and pid not in game.answers
                    and isinstance(choice, int)
                    and 0 <= choice < len(game.question()["options"])
                )
                if ok:
                    game.answers[pid] = {"choice": choice, "time": time.time() - game.started_at}
                return self.send_json({"ok": ok})

            if path.startswith("/api/host/"):
                if data.get("key") != HOST_KEY:
                    return self.send_json({"error": "Неверный ключ ведущего"}, 403)
                action = path.rsplit("/", 1)[1]
                if action == "next":
                    game.tick()
                    if game.phase == "question":
                        game.finish_question()  # ведущий может показать ответ досрочно
                    else:
                        game.next()
                elif action == "reset":
                    game.reset()
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
    if "PORT" in os.environ:
        print(f"Квиз запущен на порту {port}. Ключ ведущего: {HOST_KEY}", flush=True)
    else:
        ip = local_ip()
        JOIN_URL = f"http://{ip}:{port}"
        print("=" * 52)
        print(" Квиз запущен!")
        print(f" Экран ведущего (открой на этом компьютере):")
        print(f"   http://localhost:{port}/host?key={HOST_KEY}")
        print(f" Игрокам (телефоны в том же Wi-Fi):")
        print(f"   http://{ip}:{port}")
        print(" Остановить: Ctrl+C")
        print("=" * 52, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")


if __name__ == "__main__":
    main()
