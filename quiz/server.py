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
import collections
import binascii
import hashlib
import json
import mimetypes
import os
import random
import re
import unicodedata
import secrets
import socket
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from siq import SiqError, answer_variants, parse_siq

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
MAX_SIQ = 60 * 1024 * 1024  # самый большой пакет «Своей игры» (.siq)
MAX_MEDIA_TOTAL = 300 * 1024 * 1024  # сколько загруженных файлов держим в памяти на все комнаты
MAX_QUESTIONS = 200
OFFLINE_AFTER = 8  # игрок не на связи, если его телефон молчит дольше 8 секунд
AVATARS = ["🦊", "🐼", "🐯", "🦁", "🐸", "🐵", "🐧", "🦉", "🐙", "🦄", "🐲", "🐺",
           "🐻", "🐨", "🐰", "🐱", "⚽", "🏀", "🎸", "🚀", "👽", "🤖", "👑", "🔥"]
INSTRUMENTS = ("piano", "epiano", "marimba", "flute", "strings", "pluck", "synth")
NOTE_RE = re.compile(r"^(R|[A-G][#b]?[1-7])(:\d+(\.\d+)?)?$")  # нота: E4, C#5:0.5, пауза R:1
QTYPES = ("choice", "multi", "order", "text", "number")  # один ответ, несколько верных, по порядку, свой ответ, число (кто ближе)
LEVELS = ("easy", "normal", "hard")  # сложность вопроса
TYPE_TIME = {"multi": 1.5, "order": 1.5, "text": 1.25, "number": 1.25}  # на сложные типы — больше времени

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
AUDIO_TYPES = {"audio/mpeg", "audio/mp3", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/aac", "audio/webm"}

lock = threading.Lock()
DEVICE_COOKIE = "quiz_device"  # метка устройства: один игрок на один телефон
JOIN_URL = None  # адрес для игроков; онлайн берётся из адреса страницы

TEAMS = ["Красные", "Синие", "Жёлтые", "Зелёные"]
MODES = ["quiz", "jeopardy", "100to1"]
SI_DIR = BASE / "si"  # пакеты «Своей игры»: .siq из SIGame или .json
FD_DIR = BASE / "feud"  # пакеты «100 к 1»
PENALTY = 300  # сколько очков снимаем за неверный ответ


class PackError(ValueError):
    pass


TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", [
    "a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t",
    "u", "f", "h", "ts", "ch", "sh", "sch", "", "i", "", "e", "iu", "ia",
]))


def sound_key(word):
    """Упрощённое «звучание» слова латиницей: Холланд, холанд и Haaland дают почти одно и то же."""
    word = unicodedata.normalize("NFKD", word.lower())
    word = "".join(TRANSLIT.get(ch, ch) for ch in word if not unicodedata.combining(ch))
    for a, b in (("kh", "h"), ("ph", "f"), ("ck", "k"), ("q", "k"), ("x", "ks"), ("w", "v"), ("y", "i"), ("j", "i"), ("c", "k")):
        word = word.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[^a-z0-9]", "", word))  # двойные буквы → одна


def distance(a, b):
    """Сколько букв нужно поменять, вставить или удалить, чтобы из a получить b."""
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def close(a, b):
    if not a or not b:
        return False
    allowed = 0 if len(b) <= 4 else 1 if len(b) <= 7 else 2  # короткие слова — без опечаток
    return distance(a, b) <= allowed


def text_matches(given, accepted):
    """Засчитываем ответ, если он совпадает с одним из верных с точностью до опечатки,
    или если среди написанных слов есть верная фамилия (последнее слово верного ответа)."""
    words = [sound_key(w) for w in re.findall(r"[\w'-]+", given)]
    words = [w for w in words if w]
    if not words or len(words) > 3:
        return False
    whole = "".join(words)
    for variant in accepted:
        parts = [sound_key(w) for w in re.findall(r"[\w'-]+", variant)]
        parts = [w for w in parts if w]
        if not parts:
            continue
        if close(whole, "".join(parts)):
            return True
        if any(close(w, parts[-1]) for w in words):
            return True
    return False


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


def clean_melody(value, tempo):
    """Мелодия для музыкального раунда: ноты через пробел, например «E4 E4 F4 G4:2»."""
    if not value:
        return None, None
    notes = str(value).split()
    if not 1 <= len(notes) <= 300 or not all(NOTE_RE.match(n) for n in notes):
        raise PackError("мелодия записана неправильно: ноты вроде E4, C#5:0.5, пауза R")
    try:
        tempo = int(tempo or 110)
    except (TypeError, ValueError):
        tempo = 110
    return " ".join(notes), max(40, min(240, tempo))


def parse_number(value):
    """Число из ответа: 8849, «8 849», «8849,5». None — если это не число."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        n = float(value)
    else:
        try:
            n = float(re.sub(r"\s", "", str(value or "")).replace(",", "."))
        except ValueError:
            return None
    if n != n or abs(n) > 1e12:  # NaN или слишком большое
        return None
    return int(n) if n == int(n) else n


def clean_focus(value):
    """Точка, куда приближать картинку: [x, y] в процентах."""
    try:
        x, y = (max(0.0, min(100.0, float(v))) for v in value)
    except (TypeError, ValueError):
        return None
    return [round(x, 1), round(y, 1)]


def clean_seconds(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return max(5, min(120, n)) if n else None


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
            qtype = q.get("type") or "choice"
            if qtype not in QTYPES:
                raise PackError(f"неизвестный тип вопроса: {qtype}")
            text = str(q.get("q") or "").strip()
            options = [str(o).strip()[:100] for o in (q.get("options") or []) if str(o).strip()]
            answer = q.get("answer")
            if not text:
                raise PackError("нет текста вопроса")
            if qtype == "number":
                answer = parse_number(answer)
                if answer is None:
                    raise PackError("правильный ответ должен быть числом")
                options = []
            elif qtype == "text":
                variants = answer if isinstance(answer, list) else [answer]
                answer = [str(v).strip()[:60] for v in variants if str(v or "").strip()][:10]
                if not answer:
                    raise PackError("не указан правильный ответ")
                options = []
            elif not 2 <= len(options) <= 4:
                raise PackError("нужно от 2 до 4 вариантов ответа")
            elif qtype == "choice" and (not isinstance(answer, int) or not 0 <= answer < len(options)):
                raise PackError("не указан правильный ответ")
            elif qtype == "multi":
                if not isinstance(answer, list) or not answer or not all(isinstance(a, int) and 0 <= a < len(options) for a in answer):
                    raise PackError("отметь хотя бы один правильный вариант")
                answer = sorted(set(answer))
            elif qtype == "order":
                answer = list(range(len(options)))  # варианты записаны уже в правильном порядке
            questions.append({
                "type": qtype,
                "q": text[:300],
                "options": options,
                "answer": answer,
                "image": media_ref(q.get("image"), "image", store, scope),
                "audio": media_ref(q.get("audio"), "audio", store, scope),
                **dict(zip(("melody", "tempo"), clean_melody(q.get("melody"), q.get("tempo")))),
                "emoji": str(q.get("emoji") or "").strip()[:40] or None,  # картинка-ребус из эмодзи
                "theme": str(q.get("theme") or "").strip()[:40] or None,  # тема — пригодится для «Своей игры»
                "level": q.get("level") if q.get("level") in LEVELS else None,
                "unit": str(q.get("unit") or "").strip()[:12] or None,  # для чисел: «м», «км», «год»
                "seconds": clean_seconds(q.get("seconds")),  # своё время на этот вопрос
                # эффект картинки: blur — размыта и проясняется, zoom — виден кусочек (focus, в %), потом отдаляется
                "image_fx": q.get("image_fx") if q.get("image_fx") in ("blur", "zoom") else None,
                "focus": clean_focus(q.get("focus")),
                "instrument": q.get("instrument") if q.get("instrument") in INSTRUMENTS else None,
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


def clean_si_json(raw):
    """Пакет «Своей игры» в нашем формате .json (как после чтения .siq, но ссылки на файлы — как в викторине)."""
    rounds = []
    for r in raw.get("rounds", []):
        themes = []
        for t in r.get("themes", []):
            qs = []
            for q in t.get("questions", []):
                answers = q["answer"] if isinstance(q.get("answer"), list) else [q.get("answer")]
                melody, tempo = clean_melody(q.get("melody"), q.get("tempo"))
                qs.append({
                    "price": int(q.get("price", 0)), "special": q.get("special", "simple"),
                    "cat_cost": q.get("cat_cost"), "cat_theme": q.get("cat_theme"),
                    "text": str(q.get("text", "")), "image": media_ref(q.get("image"), "image", BUILTIN_MEDIA, "_"),
                    "audio": media_ref(q.get("audio"), "audio", BUILTIN_MEDIA, "_"), "video": None,
                    "melody": melody, "tempo": tempo, "instrument": q.get("instrument"),
                    "answer": [str(a) for a in answers if a], "answer_text": str(answers[0]),
                    "answer_image": None, "answer_audio": None, "answer_note": q.get("note"),
                })
            themes.append({"name": t["name"], "questions": qs})
        rounds.append({"name": r["name"], "final": bool(r.get("final")), "themes": themes})
    return {"title": raw.get("title", "Своя игра"), "rounds": rounds}


SI_PACKS = {}
for f in sorted(SI_DIR.glob("*")) if SI_DIR.exists() else []:
    try:
        if f.suffix == ".siq":
            SI_PACKS[f.stem] = parse_siq(f.read_bytes(), BUILTIN_MEDIA, "_")
        elif f.suffix == ".json":
            SI_PACKS[f.stem] = clean_si_json(json.loads(f.read_text(encoding="utf-8")))
    except (SiqError, PackError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Пакет «Своей игры» {f.name} пропущен: {e}", flush=True)


def clean_fd_pack(data):
    """Пакет «100 к 1»: вопросы и до 8 ответов с очками (самые популярные — первыми)."""
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise PackError("файл не похож на пакет «100 к 1»")
    questions = []
    for n, q in enumerate(data["questions"][:200], 1):
        text = str((q or {}).get("q") or "").strip()[:200]
        answers = []
        for a in (q or {}).get("answers") or []:
            name = str((a or {}).get("text") or "").strip()[:60]
            try:
                points = int((a or {}).get("points") or 0)
            except (TypeError, ValueError):
                points = 0
            alt = [str(x).strip()[:60] for x in (a or {}).get("alt") or [] if str(x).strip()][:8]
            if name and points > 0:
                answers.append({"text": name, "points": points, "alt": alt})
        if not text:
            raise PackError(f"вопрос {n}: нет текста")
        if not 2 <= len(answers) <= 8:
            raise PackError(f"вопрос {n}: нужно от 2 до 8 ответов с очками")
        answers.sort(key=lambda a: -a["points"])
        questions.append({"q": text, "answers": answers})
    if len(questions) < 1:
        raise PackError("в пакете нет вопросов")
    return {"title": str(data.get("title") or "100 к 1").strip()[:60], "note": str(data.get("note") or "")[:200], "questions": questions}


FD_PACKS = {}
for f in sorted(FD_DIR.glob("*.json")) if FD_DIR.exists() else []:
    try:
        FD_PACKS[f.stem] = clean_fd_pack(json.loads(f.read_text(encoding="utf-8")))
    except (PackError, json.JSONDecodeError) as e:
        print(f"Пакет «100 к 1» {f.name} пропущен: {e}", flush=True)


def pack_meta(pack):
    """Для меню: тема и сложность каждого вопроса — чтобы считать, сколько вопросов подходит."""
    return [[q.get("theme") or "", q.get("level") or ""] for q in pack["questions"]]


def si_info(pack):
    rounds = [r for r in pack["rounds"] if not r["final"]]
    count = sum(len(t["questions"]) for r in rounds for t in r["themes"])
    return {"title": pack["title"], "rounds": len(rounds), "count": count, "final": any(r["final"] for r in pack["rounds"])}


def si_match(given, answers):
    """Проверка ответа в «Своей игре»: как в викторине, плюс если ответ — заметная часть правильного."""
    variants = answer_variants(answers)
    if text_matches(given, variants):
        return True
    g = sound_key(given)
    if len(g) < 4:
        return False
    for v in variants:
        k = sound_key(v)
        if k and (g in k or k in g) and min(len(g), len(k)) / max(len(g), len(k)) >= 0.6:
            return True
    return False

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
    "count": 10,  # сколько случайных вопросов из пакета (0 — все по порядку)
    "themes": [],  # какие темы пакета играть (пусто — все)
    "level": "any",  # сложность: any, easy, normal, hard
    "si_pack": next(iter(SI_PACKS), None),  # пакет «Своей игры»
    "si_round_min": 10,  # «Своя игра»: минут на раунд (0 — без ограничения), несыгранные вопросы сгорают
    "fd_pack": next(iter(FD_PACKS), None),  # пакет «100 к 1»
}


def media_total():
    return sum(len(d) for g in rooms.values() for _, d in g.media.values())


class SiEngine:
    """«Своя игра»: табло тем и цен, кнопка «Ответить», кот в мешке, аукцион, вопрос без риска, финал.

    Этапы (game.phase): si_round → si_board → [si_cat_give | si_stake] → si_question ⇄ si_answer
    → si_reveal → si_board … → si_final_bet → si_final_q → si_final_reveal → final.
    """

    ROUND_SECONDS = 4  # заставка раунда
    BUZZ_WINDOW = 12  # сколько секунд всего ждём нажатия «Ответить» (на весь вопрос, а не на каждую попытку)
    REBUZZ_MIN = 3  # после неверного ответа остальным — остаток этого времени, но не меньше 3 с
    REVEAL_SECONDS = 6  # показ правильного ответа, потом табло

    def __init__(self, game, pack):
        self.g = game
        self.pack = pack
        self.rounds = [r for r in pack["rounds"] if not r["final"]]
        finals = [(t["name"], t["questions"][0]) for r in pack["rounds"] if r["final"] for t in r["themes"] if t["questions"]]
        self.final = random.choice(finals) if finals else None
        self.r = -1
        self.played = set()
        self.round_end = None  # когда закончится время раунда
        self.burned = 0
        self.chooser = None
        self.cur = None
        self.verdicts = []
        self.bets, self.final_answers = {}, {}

    # ---------- служебное ----------
    @property
    def answer_time(self):
        return self.g.settings["seconds"]

    def phase(self, name):
        self.g.set_phase(name)

    def players(self):
        return self.g.players

    def score(self, pid, delta):
        p = self.players().get(pid)
        if p is not None:
            p["score"] += delta
            p["last_points"] = delta

    def pick_chooser(self):
        if self.chooser not in self.players():
            online = self.g.online() or list(self.players())
            self.chooser = random.choice(online) if online else None

    def round(self):
        return self.rounds[self.r]

    def time_up(self):
        return self.round_end is not None and time.time() >= self.round_end

    def round_done(self):
        return self.time_up() or all((ti, qi) in self.played for ti, t in enumerate(self.round()["themes"]) for qi in range(len(t["questions"])))

    # ---------- ход игры ----------
    def start(self):
        for p in self.players().values():
            p.update(score=0, last_points=0)
        self.next_round()

    def next_round(self):
        if 0 <= self.r < len(self.rounds):  # сколько вопросов прошлого раунда сгорело
            self.burned = sum(len(t["questions"]) for t in self.round()["themes"]) - len(self.played)
        self.r += 1
        self.played = set()
        self.round_end = None
        if self.r < len(self.rounds):
            self.phase("si_round")
        else:
            self.start_final()

    def to_board(self):
        self.cur, self.verdicts = None, []
        minutes = self.g.settings.get("si_round_min", 0)
        if self.round_end is None and minutes:  # время раунда пошло, когда открылось табло
            self.round_end = time.time() + minutes * 60
        self.pick_chooser()
        self.phase("si_board")

    def pick(self, ti, qi):
        if self.g.phase != "si_board":
            return False
        themes = self.round()["themes"]
        if not (0 <= ti < len(themes) and 0 <= qi < len(themes[ti]["questions"])) or (ti, qi) in self.played:
            return False
        self.played.add((ti, qi))
        q = themes[ti]["questions"][qi]
        self.cur = {
            "q": q, "theme": themes[ti]["name"], "special": q["special"], "stake": q["price"],
            "answerer": None, "exclusive": False, "tried": set(), "false_start": {},
            "buzz_at": 0.0, "deadline": 0.0,
        }
        self.verdicts = []
        if q["special"] == "cat":
            self.cur["stake"] = q["cat_cost"] or q["price"]
            self.cur["theme"] = q["cat_theme"] or themes[ti]["name"]
            others = [pid for pid in self.players() if pid != self.chooser]
            if not others:  # играет один — вопрос остаётся ему
                return self.give(self.chooser, self.chooser, force=True)
            self.phase("si_cat_give")
        elif q["special"] == "auction":
            have = self.players().get(self.chooser, {}).get("score", 0)
            if have <= q["price"]:
                return self.stake(self.chooser, q["price"], force=True)
            self.phase("si_stake")
        elif q["special"] == "norisk":
            self.cur.update(answerer=self.chooser, exclusive=True, stake=q["price"] * 2)
            self.show()
        else:
            self.show()
        return True

    def give(self, pid, target, force=False):
        if not force and (self.g.phase != "si_cat_give" or pid != self.chooser or target == pid or target not in self.players()):
            return False
        self.cur.update(answerer=target, exclusive=True)
        self.show()
        return True

    def stake(self, pid, amount, force=False):
        if not force:
            if self.g.phase != "si_stake" or pid != self.chooser or not isinstance(amount, int):
                return False
            have = self.players()[pid]["score"]
            if not self.cur["q"]["price"] <= amount <= max(have, self.cur["q"]["price"]):
                return False
        self.cur.update(stake=amount, answerer=self.chooser, exclusive=True)
        self.show()
        return True

    def show(self):
        q = self.cur["q"]
        read = len(q["text"]) / 14 + (1.5 if q["image"] else 0) + (4 if q["audio"] or q.get("melody") or q["video"] else 0)
        now = time.time()
        self.cur["buzz_at"] = now + min(10, max(2, read))
        self.cur["deadline"] = self.cur["buzz_at"] + self.BUZZ_WINDOW
        self.phase("si_question")

    def open_buzz(self):
        """Ведущий: «Открыть кнопки» — не ждать конца чтения."""
        now = time.time()
        self.cur["buzz_at"] = now
        self.cur["deadline"] = now + self.BUZZ_WINDOW

    def buzz(self, pid):
        if self.g.phase != "si_question" or self.cur["exclusive"] or pid not in self.players() or pid in self.cur["tried"]:
            return "no"
        now = time.time()
        if now < self.cur["buzz_at"]:
            self.cur["false_start"][pid] = now + 1.0  # фальстарт: кнопка заблокирована на секунду
            return "early"
        if self.cur["false_start"].get(pid, 0) > now:
            return "early"
        self.cur["answerer"] = pid
        self.cur["buzz_left"] = max(0, self.cur["deadline"] - now)  # пока игрок отвечает, время на кнопку стоит
        self.cur["deadline"] = now + self.answer_time
        self.phase("si_answer")
        return "ok"

    def answer(self, pid, text):
        # в коте в мешке, аукционе и вопросе без риска отвечающий известен — можно отвечать сразу
        early = self.g.phase == "si_question" and self.cur["exclusive"]
        if (self.g.phase != "si_answer" and not early) or pid != self.cur["answerer"]:
            return False
        self.judge(pid, str(text or "").strip()[:80])
        return True

    def delta(self, ok):
        stake = self.cur["stake"]
        if self.cur["special"] == "norisk":
            return stake if ok else 0
        return stake if ok else -stake

    def judge(self, pid, text):
        ok = bool(text) and si_match(text, self.cur["q"]["answer"])
        d = self.delta(ok)
        self.score(pid, d)
        self.verdicts.append({"pid": pid, "text": text, "ok": ok, "delta": d})
        if ok:
            self.chooser = pid
            return self.phase("si_reveal")
        self.cur["tried"].add(pid)
        left = [x for x in self.g.online() if x not in self.cur["tried"]]
        if self.cur["exclusive"] or not left:
            return self.phase("si_reveal")
        now = time.time()  # остальные могут попробовать — сколько осталось от общего времени
        rest = max(self.REBUZZ_MIN, self.cur.get("buzz_left", self.BUZZ_WINDOW))
        self.cur.update(answerer=None, buzz_at=now, deadline=now + rest)
        self.phase("si_question")

    def override(self, i):
        """Ведущий исправляет проверку: засчитать или не засчитывать ответ."""
        if self.g.phase == "si_final_reveal":
            if not 0 <= i < len(self.verdicts):
                return False
            v = self.verdicts[i]
            self.score(v["pid"], -2 * v["delta"])
            v["ok"], v["delta"] = not v["ok"], -v["delta"]
            return True
        if self.g.phase != "si_reveal" or not 0 <= i < len(self.verdicts):
            return False
        v = self.verdicts[i]
        self.score(v["pid"], -v["delta"])
        v["ok"] = not v["ok"]
        v["delta"] = self.delta(v["ok"])
        self.score(v["pid"], v["delta"])
        if v["ok"]:
            self.chooser = v["pid"]
        self.g.phase_at = time.time()  # дать время посмотреть
        return True

    def after_reveal(self):
        if self.round_done():
            self.next_round()
        else:
            self.to_board()

    # ---------- финал ----------
    def eligible(self):
        return [pid for pid, p in self.players().items() if p["score"] > 0]

    def start_final(self):
        self.cur, self.verdicts = None, []
        if not self.final or not self.eligible():
            return self.g.set_phase("final")
        self.bets, self.final_answers = {}, {}
        self.phase("si_final_bet")

    def bet(self, pid, amount):
        if self.g.phase != "si_final_bet" or pid not in self.eligible() or not isinstance(amount, int):
            return False
        if not 1 <= amount <= self.players()[pid]["score"]:
            return False
        self.bets[pid] = amount
        return True

    def final_question(self):
        for pid in self.eligible():
            self.bets.setdefault(pid, 1)
        self.cur = {"deadline": time.time() + max(30, self.answer_time * 2)}
        self.phase("si_final_q")

    def final_answer(self, pid, text):
        if self.g.phase != "si_final_q" or pid not in self.bets:
            return False
        self.final_answers[pid] = str(text or "").strip()[:80]
        return True

    def final_reveal(self):
        q = self.final[1]
        self.verdicts = []
        for pid, bet in self.bets.items():
            text = self.final_answers.get(pid, "")
            ok = bool(text) and si_match(text, q["answer"])
            d = bet if ok else -bet
            self.score(pid, d)
            self.verdicts.append({"pid": pid, "text": text, "ok": ok, "delta": d, "bet": bet})
        self.phase("si_final_reveal")

    # ---------- время и ведущий ----------
    def tick(self):
        ph, now = self.g.phase, time.time()
        waited = now - self.g.phase_at
        if ph == "si_round" and waited >= self.ROUND_SECONDS:
            self.to_board()
        elif ph == "si_board" and self.time_up():
            self.next_round()  # время раунда вышло — несыгранные вопросы сгорают
        elif ph == "si_question":
            if self.cur["exclusive"] and now >= self.cur["buzz_at"]:
                self.cur["deadline"] = now + self.answer_time
                self.phase("si_answer")
            elif not self.cur["exclusive"] and now >= self.cur["deadline"]:
                self.phase("si_reveal")  # никто не ответил
        elif ph == "si_answer" and now >= self.cur["deadline"]:
            self.judge(self.cur["answerer"], "")  # время вышло
        elif ph == "si_reveal" and self.g.settings["auto"] and waited >= self.REVEAL_SECONDS:
            self.after_reveal()
        elif ph == "si_final_bet" and (waited >= 30 or all(pid in self.bets for pid in self.eligible())):
            self.final_question()
        elif ph == "si_final_q" and (now >= self.cur["deadline"] or all(pid in self.final_answers for pid in self.bets)):
            self.final_reveal()

    def host_next(self):
        ph = self.g.phase
        if ph == "si_round":
            self.to_board()
        elif ph == "si_board":
            self.next_round()  # ведущий завершает раунд досрочно
        elif ph == "si_cat_give":  # игрок не выбрал — вопрос уходит случайному сопернику
            self.give(self.chooser, random.choice([p for p in self.players() if p != self.chooser]), force=True)
        elif ph == "si_stake":
            self.stake(self.chooser, self.cur["q"]["price"], force=True)
        elif ph == "si_question":
            self.open_buzz() if not self.cur["exclusive"] else self.tick()
        elif ph == "si_answer":
            self.judge(self.cur["answerer"], "")
        elif ph == "si_reveal":
            self.after_reveal()
        elif ph == "si_final_bet":
            self.final_question()
        elif ph == "si_final_q":
            self.final_reveal()
        elif ph == "si_final_reveal":
            self.g.set_phase("final")

    # ---------- что показать ----------
    def name(self, pid):
        p = self.players().get(pid)
        return {"id": pid, "name": p["name"], "avatar": p.get("avatar")} if p else None

    def state(self, pid):
        ph, now = self.g.phase, time.time()
        s = {"round_index": self.r, "rounds_total": len(self.rounds), "chooser": self.name(self.chooser)}
        if 0 <= self.r < len(self.rounds):
            s["round_name"] = self.round()["name"]
            if self.round_end is not None:
                s["round_left"] = max(0, round(self.round_end - now))
        if ph == "si_round":
            s["burned"] = self.burned
        if ph in ("si_round", "si_board") and 0 <= self.r < len(self.rounds):
            s["board"] = [{"name": t["name"], "cells": [{"price": q["price"], "played": (ti, qi) in self.played}
                                                        for qi, q in enumerate(t["questions"])]}
                          for ti, t in enumerate(self.round()["themes"])]
        if self.cur and "q" in self.cur and ph in ("si_cat_give", "si_stake", "si_question", "si_answer", "si_reveal"):
            q, c = self.cur["q"], self.cur
            cur = {"theme": c["theme"], "price": q["price"], "stake": c["stake"], "special": c["special"],
                   "answerer": self.name(c["answerer"]), "exclusive": c["exclusive"],
                   "tried": list(c["tried"]), "max_stake": max(self.players().get(self.chooser, {}).get("score", 0), q["price"])}
            if ph in ("si_question", "si_answer", "si_reveal"):
                cur.update(text=q["text"], image=q["image"], audio=q["audio"], video=q["video"],
                           melody=q.get("melody"), tempo=q.get("tempo"), instrument=q.get("instrument"))
                cur["buzz_open"] = now >= c["buzz_at"]
                cur["buzz_in"] = max(0, round(c["buzz_at"] - now, 1))
                cur["left"] = max(0, round(c["deadline"] - now, 1))
            if ph == "si_reveal":
                cur.update(answer=q["answer_text"], answer_image=q["answer_image"], answer_audio=q["answer_audio"], note=q["answer_note"])
            s["cur"] = cur
        if ph in ("si_reveal", "si_final_reveal"):
            s["verdicts"] = [dict(v, player=self.name(v["pid"])) for v in self.verdicts]
        if ph.startswith("si_final"):
            theme, q = self.final
            f = {"theme": theme, "eligible": [self.name(x) for x in self.eligible() if ph == "si_final_bet"] or [self.name(x) for x in self.bets],
                 "bets_done": list(self.bets), "answered": list(self.final_answers)}
            if ph in ("si_final_q", "si_final_reveal"):
                f.update(text=q["text"], image=q["image"], audio=q["audio"], video=q["video"],
                         left=max(0, round(self.cur["deadline"] - now, 1)) if ph == "si_final_q" else 0)
            if ph == "si_final_reveal":
                f["answer"] = q["answer_text"]
            s["final"] = f
        if pid in self.players():
            me = {"is_chooser": pid == self.chooser}
            if self.cur and "q" in self.cur:
                me.update(is_answerer=pid == self.cur.get("answerer"), tried=pid in self.cur.get("tried", ()),
                          blocked=self.cur.get("false_start", {}).get(pid, 0) > now)
            if ph.startswith("si_final"):
                me.update(eligible=pid in self.eligible() or pid in self.bets, bet=self.bets.get(pid),
                          answered=pid in self.final_answers)
            s["me"] = me
        return s


class FeudEngine:
    """«100 к 1»: две команды угадывают самые популярные ответы.

    Этапы: fd_round → fd_play (команда отвечает по очереди, 3 промаха) → [fd_steal] → fd_reveal → …
    → fd_big_intro → fd_big_q × 5 → fd_big_result → final.
    """

    ROUNDS = [("Простая игра", 1, False), ("Двойная игра", 2, False), ("Тройная игра", 3, False), ("Игра наоборот", 1, True)]
    REVERSE_POINTS = [15, 30, 60, 120, 180, 240, 300, 360]  # в «игре наоборот» дороже редкие ответы
    ROUND_SECONDS = 4
    REVEAL_SECONDS = 7
    STRIKES = 3
    BIG_COUNT = 5
    BIG_SHARE = 0.6  # цель большой игры — 60% от суммы лучших ответов
    BIG_SECONDS = 25

    def __init__(self, game, pack):
        self.g = game
        qs = list(pack["questions"])
        random.shuffle(qs)
        rounds = min(len(self.ROUNDS), len(qs))
        self.round_qs = qs[:rounds]
        big = qs[rounds:rounds + self.BIG_COUNT]
        self.big_qs = big if len(big) >= 3 else []
        self.note = pack.get("note", "")
        self.r = -1
        self.scores = [0, 0]
        self.turn = [0, 0]
        self.cur = None
        self.big = None

    # ---------- служебное ----------
    def phase(self, name):
        self.g.set_phase(name)

    @property
    def seconds(self):
        return self.g.settings["seconds"]

    def members(self, team):
        online = set(self.g.online())
        ids = [pid for pid, p in self.g.players.items() if p.get("team") == team]
        return [pid for pid in ids if pid in online] or ids

    def next_guesser(self, team):
        m = self.members(team)
        if not m:
            return None
        pid = m[self.turn[team] % len(m)]
        self.turn[team] += 1
        return pid

    def add(self, team, points):
        self.scores[team] += points
        for p in self.g.players.values():  # у всех в команде — общий счёт команды
            if p.get("team") == team:
                p["last_points"] = points
                p["score"] = self.scores[team]

    def points(self, i):
        c = self.cur
        return self.REVERSE_POINTS[i] if c["reverse"] else c["q"]["answers"][i]["points"] * c["mult"]

    def match(self, q, text):
        for i, a in enumerate(q["answers"]):
            if text and si_match(text, [a["text"], *a["alt"]]):
                return i
        return None

    # ---------- раунды ----------
    def start(self):
        for p in self.g.players.values():
            p.update(score=0, last_points=0)
        self.next_round()

    def next_round(self):
        self.r += 1
        if self.r >= len(self.round_qs):
            return self.start_big()
        name, mult, reverse = self.ROUNDS[self.r]
        self.cur = {"q": self.round_qs[self.r], "name": name, "mult": mult, "reverse": reverse,
                    "team": self.r % 2, "opened": set(), "strikes": 0, "bank": 0,
                    "guesser": None, "deadline": 0.0, "steal": False, "winner": None, "log": []}
        self.phase("fd_round")

    def begin_play(self):
        c = self.cur
        c["guesser"] = self.next_guesser(c["team"])
        c["deadline"] = time.time() + self.seconds
        self.phase("fd_play")

    def say(self, pid, text, result):
        name = self.g.players.get(pid, {}).get("name", "—")
        self.cur["log"] = (self.cur["log"] + [{"name": name, "text": text, "result": result}])[-6:]

    def open(self, i):
        self.cur["opened"].add(i)
        self.cur["bank"] += self.points(i)

    def guess(self, pid, text):
        c, ph = self.cur, self.g.phase
        text = str(text or "").strip()[:60]
        if ph == "fd_play" and pid == c["guesser"]:
            return self.judge(pid, text)
        if ph == "fd_steal" and self.g.players.get(pid, {}).get("team") == 1 - c["team"]:
            return self.judge_steal(pid, text)
        return False

    def judge(self, pid, text):
        c = self.cur
        i = self.match(c["q"], text)
        if i is not None and i in c["opened"]:
            self.say(pid, text, "already")  # уже открыт — промахом не считаем, пусть назовёт другой
            c["deadline"] = time.time() + self.seconds
            return True
        if i is not None:
            self.open(i)
            self.say(pid, text, "right")
            if len(c["opened"]) == len(c["q"]["answers"]):
                return self.win(c["team"])
        else:
            c["strikes"] += 1
            self.say(pid, text, "wrong")
            if c["strikes"] >= self.STRIKES:
                c["steal"] = True
                c["guesser"] = None
                c["deadline"] = time.time() + self.seconds * 1.5
                self.phase("fd_steal")
                return True
        c["guesser"] = self.next_guesser(c["team"])
        c["deadline"] = time.time() + self.seconds
        return True

    def judge_steal(self, pid, text):
        c = self.cur
        i = self.match(c["q"], text)
        if i is not None and i not in c["opened"]:
            self.open(i)
            self.say(pid, text, "right")
            return self.win(1 - c["team"])
        self.say(pid, text, "wrong")
        return self.win(c["team"])

    def win(self, team):
        c = self.cur
        c["winner"] = team
        self.add(team, c["bank"])
        self.phase("fd_reveal")
        return True

    def host_open(self, i):
        """Ведущий открывает ответ вручную — если проверка не узнала правильный ответ."""
        c, ph = self.cur, self.g.phase
        if not c or not isinstance(i, int) or not 0 <= i < len(c["q"]["answers"]) or i in c["opened"]:
            return False
        if ph == "fd_play":
            self.open(i)
            if c["log"] and c["log"][-1]["result"] == "wrong":  # последний «промах» на самом деле верный
                c["log"][-1]["result"] = "right"
                c["strikes"] = max(0, c["strikes"] - 1)
            if len(c["opened"]) == len(c["q"]["answers"]):
                self.win(c["team"])
            return True
        if ph == "fd_steal":
            self.open(i)
            return self.win(1 - c["team"])
        if ph == "fd_reveal":
            # банк уже отдан победителю — дополнительный ответ тоже засчитываем ему
            c["opened"].add(i)
            self.add(c["winner"], self.points(i))
            c["bank"] += self.points(i)
            return True
        return False

    def unstrike(self):
        if self.g.phase == "fd_play" and self.cur["strikes"] > 0:
            self.cur["strikes"] -= 1
            return True
        return False

    # ---------- большая игра ----------
    def start_big(self):
        self.cur = None
        if not self.big_qs or max(self.scores) <= 0:
            return self.g.set_phase("final")
        team = 0 if self.scores[0] >= self.scores[1] else 1
        best = sum(q["answers"][0]["points"] for q in self.big_qs)
        self.big = {"team": team, "i": -1, "answers": [], "deadline": 0.0,
                    "target": max(10, round(best * self.BIG_SHARE / 10) * 10)}
        self.phase("fd_big_intro")

    def big_next(self):
        b = self.big
        b["i"] += 1
        if b["i"] >= len(self.big_qs):
            total = sum(a["points"] for a in b["answers"])
            self.add(b["team"], total)
            return self.phase("fd_big_result")
        b["deadline"] = time.time() + self.BIG_SECONDS
        self.phase("fd_big_q")

    def big_answer(self, pid, text):
        b = self.big
        if self.g.phase != "fd_big_q" or self.g.players.get(pid, {}).get("team") != b["team"]:
            return False
        q = self.big_qs[b["i"]]
        text = str(text or "").strip()[:60]
        i = self.match(q, text)
        b["answers"].append({"q": q["q"], "text": text, "points": q["answers"][i]["points"] if i is not None else 0,
                             "match": q["answers"][i]["text"] if i is not None else None, "top": q["answers"][0]["text"]})
        self.big_next()
        return True

    # ---------- время и ведущий ----------
    def tick(self):
        ph, now = self.g.phase, time.time()
        waited = now - self.g.phase_at
        if ph == "fd_round" and waited >= self.ROUND_SECONDS:
            self.begin_play()
        elif ph == "fd_play" and now >= self.cur["deadline"]:
            if self.cur["guesser"] is None:  # в команде никого — ход соперникам
                self.cur["strikes"] = self.STRIKES - 1
            self.judge(self.cur["guesser"], "")
        elif ph == "fd_steal" and now >= self.cur["deadline"]:
            self.say(None, "", "wrong")
            self.win(self.cur["team"])
        elif ph == "fd_reveal" and self.g.settings["auto"] and waited >= self.REVEAL_SECONDS:
            self.next_round()
        elif ph == "fd_big_intro" and waited >= self.ROUND_SECONDS:
            self.big_next()
        elif ph == "fd_big_q" and now >= self.big["deadline"]:
            q = self.big_qs[self.big["i"]]
            self.big["answers"].append({"q": q["q"], "text": "", "points": 0, "match": None, "top": q["answers"][0]["text"]})
            self.big_next()

    def host_next(self):
        ph = self.g.phase
        if ph == "fd_round":
            self.begin_play()
        elif ph in ("fd_play", "fd_steal", "fd_big_q"):
            if ph == "fd_play":
                self.cur["deadline"] = 0
            elif ph == "fd_steal":
                self.cur["deadline"] = 0
            else:
                self.big["deadline"] = 0
            self.tick()
        elif ph == "fd_reveal":
            self.next_round()
        elif ph == "fd_big_intro":
            self.big_next()
        elif ph == "fd_big_result":
            self.g.set_phase("final")

    # ---------- что показать ----------
    def name(self, pid):
        p = self.g.players.get(pid)
        return {"id": pid, "name": p["name"], "avatar": p.get("avatar")} if p else None

    def state(self, pid):
        ph, now = self.g.phase, time.time()
        s = {"team_scores": self.scores, "rounds_total": len(self.round_qs), "round_index": self.r,
             "has_big": bool(self.big_qs), "note": self.note}
        c = self.cur
        if c and ph in ("fd_round", "fd_play", "fd_steal", "fd_reveal"):
            show_all = ph == "fd_reveal"
            s["cur"] = {
                "name": c["name"], "mult": c["mult"], "reverse": c["reverse"], "q": c["q"]["q"],
                "slots": [{"n": i + 1, "opened": i in c["opened"],
                           **({"text": a["text"], "points": self.points(i)} if show_all or i in c["opened"] else {})}
                          for i, a in enumerate(c["q"]["answers"])],
                "strikes": c["strikes"], "bank": c["bank"], "team": c["team"], "steal": c["steal"],
                "guesser": self.name(c["guesser"]), "winner": c["winner"], "log": c["log"],
                "left": max(0, round(c["deadline"] - now, 1)) if ph in ("fd_play", "fd_steal") else None,
            }
        b = self.big
        if b and ph.startswith("fd_big"):
            s["big"] = {"team": b["team"], "i": b["i"], "count": len(self.big_qs), "target": b["target"],
                        "total": sum(a["points"] for a in b["answers"]), "answers": b["answers"],
                        "q": self.big_qs[b["i"]]["q"] if ph == "fd_big_q" else None,
                        "left": max(0, round(b["deadline"] - now, 1)) if ph == "fd_big_q" else None}
            if ph == "fd_big_result":
                s["big"]["tops"] = [{"q": q["q"], "answers": [{"text": a["text"], "points": a["points"]} for a in q["answers"][:3]]}
                                    for q in self.big_qs]
        if pid in self.g.players:
            team = self.g.players[pid].get("team")
            me = {"team": team}
            if c:
                me["is_guesser"] = ph == "fd_play" and pid == c["guesser"]
                me["can_steal"] = ph == "fd_steal" and team == 1 - c["team"]
            if b:
                me["in_big"] = team == b["team"]
            s["me"] = me
        return s


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
        self.used = {}  # пакет -> номера вопросов, которые уже были в этой комнате
        self.selected = []
        self.si = None  # «Своя игра», если выбран этот режим
        self.fd = None  # «100 к 1»
        self.fd_custom = None
        self.si_custom = None  # загруженный пакет .siq
        self.si_media = {}
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
        if isinstance(data.get("themes"), list):
            s["themes"] = [str(t)[:40] for t in data["themes"] if isinstance(t, str)][:60]
        if data.get("level") in ("any", *LEVELS):
            s["level"] = data["level"]
        if data.get("si_round_min") in (0, 5, 10, 15):
            s["si_round_min"] = data["si_round_min"]
        if data.get("count") in (0, 10, 20, 30):
            s["count"] = data["count"]
        if data.get("si_pack") in SI_PACKS or (data.get("si_pack") == "custom" and self.si_custom):
            s["si_pack"] = data["si_pack"]
        if data.get("fd_pack") in FD_PACKS or (data.get("fd_pack") == "custom" and self.fd_custom):
            s["fd_pack"] = data["fd_pack"]
        if s["mode"] == "100to1":
            s["teams"] = 2  # «100 к 1» — всегда две команды
        return s

    @property
    def fd_pack(self):
        key = self.settings.get("fd_pack")
        return self.fd_custom if key == "custom" else FD_PACKS.get(key)

    @property
    def si_pack(self):
        key = self.settings.get("si_pack")
        return self.si_custom if key == "custom" else SI_PACKS.get(key)

    def upload_siq(self, data):
        store = {}
        pack = parse_siq(data, store, self.code)
        size = sum(len(d) for _, d in store.values())
        if media_total() - sum(len(d) for _, d in self.si_media.values()) + size > MAX_MEDIA_TOTAL:
            raise SiqError("на сервере закончилось место для файлов, попробуй пакет поменьше")
        self.si_custom, self.si_media = pack, store
        self.settings["si_pack"] = "custom"
        return pack

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
        self.answers = {}  # id -> {"value", "time"}
        self.all_answered_at = None
        self.display = []  # порядок вариантов на экране (для «по порядку» — перемешан)
        self.si = None
        self.fd = None
        if phase == "lobby":
            if self.settings["mode"] == "100to1" and self.fd_pack:
                self.fd = FeudEngine(self, self.fd_pack)
            elif self.settings["mode"] == "jeopardy" and self.si_pack:
                self.si = SiEngine(self, self.si_pack)
            else:
                self.pick_questions()

    def pool(self):
        """Номера вопросов пакета, подходящих под выбранные темы и сложность."""
        allq, st = self.pack["questions"], self.settings
        themes = set(st.get("themes") or []) & {q.get("theme") for q in allq}
        level = st.get("level", "any")
        ok = [i for i, q in enumerate(allq)
              if (not themes or q.get("theme") in themes) and (level == "any" or q.get("level") == level)]
        return ok or list(range(len(allq)))  # ничего не подошло — играем весь пакет

    def pick_questions(self):
        """Выбираем вопросы на игру: случайные и по возможности те, что ещё не попадались."""
        allq = self.pack["questions"]
        pool = self.pool()
        n = self.settings["count"]
        if not n or n >= len(pool):
            self.selected = [allq[i] for i in (pool if not n else random.sample(pool, len(pool)))]
            return
        used = self.used.setdefault(self.settings["pack"], set())
        fresh = [i for i in pool if i not in used]
        if len(fresh) < n:  # вопросы закончились — начинаем круг заново
            used.difference_update(pool)
            fresh = list(pool)
        chosen = random.sample(fresh, n)
        used.update(chosen)
        self.selected = [allq[i] for i in chosen]

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
        self.used.pop("custom", None)
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
        """Время на текущий вопрос: своё у вопроса или общее, для сложных типов — больше."""
        base = self.settings["seconds"]
        if self.si or self.fd or not 0 <= self.index < len(self.selected):
            return base
        q = self.question()
        return q.get("seconds") or int(base * TYPE_TIME.get(q["type"], 1) + 0.5)

    def question(self):
        return self.selected[self.index]

    def check(self, value):
        """Проверяет ответ игрока: None — неверный формат, иначе сам ответ."""
        q = self.question()
        n = len(q["options"])
        if q["type"] == "choice":
            return value if isinstance(value, int) and 0 <= value < n else None
        if q["type"] == "multi":
            ok = isinstance(value, list) and value and all(isinstance(v, int) and 0 <= v < n for v in value)
            return sorted(set(value)) if ok else None
        if q["type"] == "order":
            return value if isinstance(value, list) and sorted(value) == list(range(n)) else None
        if q["type"] == "number":
            return parse_number(value) if isinstance(value, (int, float, str)) else None
        if not isinstance(value, str):
            return None
        return value.strip()[:60] or None

    def grade(self, value):
        """Насколько верен ответ: 1 — полностью, 0 — неверно, между ними — частично."""
        q = self.question()
        if value is None:
            return 0.0
        if q["type"] == "choice":
            return 1.0 if value == q["answer"] else 0.0
        if q["type"] == "text":
            return 1.0 if text_matches(value, q["answer"]) else 0.0
        if q["type"] == "number":
            # ближе всех — полные очки; остальным — до 70% по точности (ошибка в 50% — 35%)
            err = abs(value - q["answer"])
            if err <= self.best_err:
                return 1.0
            return round(0.7 * max(0.0, 1 - err / max(abs(q["answer"]), 1)), 3)
        if q["type"] == "multi":
            right = set(q["answer"])
            hits, misses = len(right & set(value)), len(set(value) - right)
            return max(0.0, (hits - misses) / len(right))
        order = [self.display[i] for i in value]  # что игрок поставил на каждое место
        return sum(1 for place, item in enumerate(order) if place == item) / len(order)

    def tick(self):
        """Двигает игру по времени: конец вопроса и автопереход."""
        if self.si and self.phase.startswith("si_"):
            return self.si.tick()
        if self.fd and self.phase.startswith("fd_"):
            return self.fd.tick()
        now = time.time()
        if self.phase == "question":
            online = self.online()
            everyone = online and all(pid in self.answers for pid in online)
            if everyone and self.all_answered_at is None:
                self.all_answered_at = now
            time_up = now - self.started_at >= self.seconds
            if time_up or (self.all_answered_at and now - self.all_answered_at >= REVEAL_PAUSE):
                self.finish_question()
        elif self.settings["auto"] and self.auto_left() == 0 and not self.phase.startswith(("si_", "fd_")):
            self.next()

    def auto_left(self):
        """Сколько секунд до автоперехода, или None, если его нет."""
        if not self.settings["auto"] or self.phase not in ("reveal", "leaders"):
            return None
        wait = REVEAL_SECONDS if self.phase == "reveal" else LEADERS_SECONDS
        return max(0, round(wait - (time.time() - self.phase_at), 1))

    def finish_question(self):
        rules = self.settings
        # Запоминаем места до начисления очков, чтобы показать стрелки ↑↓.
        for place, row in enumerate(self.leaderboard(), 1):
            self.players[row["id"]]["prev_place"] = place
        self.team_prev = {t["team"]: place for place, t in enumerate(self.team_board(), 1)}
        if self.question()["type"] == "number":  # ближайший ответ среди всех
            errs = [abs(a["value"] - self.question()["answer"]) for a in self.answers.values()]
            self.best_err = min(errs) if errs else 0
        for pid, p in self.players.items():
            a = self.answers.get(pid)
            frac = self.grade(a["value"]) if a else 0.0
            points = 0
            if frac > 0:
                if rules["speed"]:
                    # Быстрый правильный ответ даёт до 1000 очков, медленный — от 500.
                    points = round(500 + 500 * max(0.0, 1 - a["time"] / self.seconds))
                else:
                    points = 1000
                points = round(points * frac)  # частично верный ответ — часть очков
            if frac == 1:
                p["streak"] += 1
                if rules["streak"] and p["streak"] >= 2:
                    points += min(500, 100 * (p["streak"] - 1))  # +100 за каждый ответ серии, до +500
            else:
                p["streak"] = 0
                if a and frac == 0 and rules["penalty"]:
                    points = -min(PENALTY, p["score"])  # ниже нуля не опускаемся
            a = a or {}
            a["result"] = "right" if frac == 1 else "partial" if frac > 0 else "wrong" if a else "none"
            if pid in self.answers:
                self.answers[pid] = a
            p["last_points"] = points
            p["score"] += points
        self.set_phase("reveal")

    def next(self):
        last = self.index + 1 >= len(self.selected)
        if self.phase == "reveal" and not last and self.settings["leaders"]:
            self.set_phase("leaders")
            return
        if last and self.phase in ("reveal", "leaders"):
            self.set_phase("final")
            return
        self.index += 1
        n = len(self.question()["options"])
        self.display = list(range(n))
        if self.question()["type"] == "order":
            while n > 1 and self.display == sorted(self.display):
                random.shuffle(self.display)  # на экране варианты перемешаны
        self.set_phase("question")
        self.started_at = time.time()
        self.answers = {}
        self.all_answered_at = None

    def online(self):
        now = time.time()
        return [pid for pid, p in self.players.items() if now - p.get("seen", now) <= OFFLINE_AFTER]

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
                "avatar": p.get("avatar"),
                "online": time.time() - p.get("seen", 0) <= OFFLINE_AFTER,
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
            "total": len(self.selected) if self.phase != "setup" else len(self.pack["questions"]),
            "seconds": self.seconds,
            "settings": self.settings,
            "team_names": TEAMS,
            "avatars": AVATARS,
            "players": self.leaderboard(),
            "teams": self.team_board(),
            "answered": len(self.answers),
            "room": self.code,
            "join": JOIN_URL,
            "version": VERSION,
            "auto_left": self.auto_left(),
        }
        if self.fd:
            s["title"] = self.fd_pack["title"]
            s["fd"] = self.fd.state(pid if self.owns(pid, device) else None)
        if self.si:
            s["title"] = self.si_pack["title"]
            s["si"] = self.si.state(pid if self.owns(pid, device) else None)
        if self.phase == "setup":
            s["si_packs"] = [{"id": k, **si_info(p)} for k, p in SI_PACKS.items()]
            s["fd_packs"] = [{"id": k, "title": p["title"], "count": len(p["questions"])} for k, p in FD_PACKS.items()]
            if self.fd_custom:
                s["fd_custom"] = {"title": self.fd_custom["title"], "count": len(self.fd_custom["questions"])}
            if self.si_custom:
                s["si_custom"] = si_info(self.si_custom)
            s["packs"] = [{"id": k, "title": p["title"], "count": len(p["questions"]), "meta": pack_meta(p)} for k, p in PACKS.items()]
            if self.custom:
                s["custom"] = {"title": self.custom["title"], "count": len(self.custom["questions"]), "meta": pack_meta(self.custom)}
        if self.phase in ("question", "reveal") and not self.si and not self.fd:
            q = self.question()
            s["qtype"] = q["type"]
            s["question"] = q["q"]
            s["theme"] = q.get("theme")
            s["unit"] = q.get("unit")
            s["image_fx"] = q.get("image_fx") if q["image"] else None
            s["focus"] = q.get("focus") or [50, 50]
            s["options"] = [q["options"][i] for i in self.display]
            s["image"] = q["image"]
            s["audio"] = q["audio"]
            s["melody"] = q.get("melody")
            s["tempo"] = q.get("tempo")
            s["emoji"] = q.get("emoji")
            s["instrument"] = q.get("instrument")
            s["left"] = max(0, round(self.seconds - (time.time() - self.started_at), 1))
        if self.phase in ("reveal", "leaders") and not self.si and not self.fd:
            # для комментариев в таблице лидеров: самый быстрый верный ответ и сколько ответили верно
            right = [(a["time"], who) for who, a in self.answers.items() if a.get("result") == "right" and who in self.players]
            if right:
                t, who = min(right)
                s["fastest"] = {"name": self.players[who]["name"], "time": round(t, 1)}
            s["right_total"] = len(right)
            s["answers_total"] = len(self.answers)
        if self.phase == "reveal":
            results = [a.get("result") for a in self.answers.values()]
            s["right_count"] = results.count("right")
            s["partial_count"] = results.count("partial")
            if q["type"] in ("choice", "multi"):
                s["correct"] = q["answer"]
                counts = [0] * len(q["options"])
                for a in self.answers.values():
                    for v in a["value"] if isinstance(a["value"], list) else [a["value"]]:
                        counts[v] += 1
                s["counts"] = counts
            elif q["type"] == "order":
                s["correct_order"] = q["options"]
            elif q["type"] == "number":
                s["correct_number"] = q["answer"]
                rows = [{"name": self.players[pid]["name"], "avatar": self.players[pid].get("avatar"), "value": a["value"],
                         "diff": a["value"] - q["answer"], "best": a.get("result") == "right"}
                        for pid, a in self.answers.items() if pid in self.players]
                s["number_answers"] = sorted(rows, key=lambda r: abs(r["diff"]))
            else:
                s["correct_text"] = q["answer"][0]
                s["text_answers"] = [
                    {"name": self.players[pid]["name"], "text": a["value"], "ok": a.get("result") == "right"}
                    for pid, a in self.answers.items() if pid in self.players
                ]
        if self.owns(pid, device):
            me = self.players[pid]
            me["seen"] = time.time()
            s["me"] = {
                "name": me["name"],
                "avatar": me.get("avatar"),
                "team": me.get("team"),
                "score": me["score"],
                "last": me["last_points"],
                "prev": me["prev_place"],
                "streak": me["streak"],
                "answer": self.answers.get(pid, {}).get("value"),
                "result": self.answers.get(pid, {}).get("result"),
                "place": [r["id"] for r in s["players"]].index(pid) + 1,
            }
            if me.get("team") is not None:
                s["me"]["team_place"] = [t["team"] for t in s["teams"]].index(me["team"]) + 1
        return s


rooms = {}  # код комнаты -> Game


class Stats:
    """Статистика сайта для владельца: только счётчики, без имён. Живёт в памяти —
    обнуляется, когда сервер перезапускается (после обновления или сна на Render)."""

    def __init__(self):
        self.started = time.time()
        self.visitors = set()  # обезличенные метки устройств
        self.views = collections.Counter()  # страница -> просмотры
        self.counts = collections.Counter()  # rooms, players, answers, games:<режим>, finished:<режим>
        self.peak_players = self.peak_rooms = 0
        self.hours = collections.Counter()  # час (unix-время / 3600) -> начатых игр
        self.events = collections.deque(maxlen=80)
        self.sampled = 0.0

    def visit(self, device, page):
        self.views[page] += 1
        if device:
            self.visitors.add(hashlib.sha256(device.encode()).hexdigest()[:16])

    def event(self, text):
        self.events.appendleft((time.time(), text))
        print(f"[статистика] {text}", flush=True)  # остаётся в логах Render

    def sample(self):
        """Раз в 10 секунд считаем, сколько людей сейчас в игре, — для рекорда онлайна."""
        now = time.time()
        if now - self.sampled < 10:
            return
        self.sampled = now
        online = sum(len(g.online()) for g in rooms.values())
        active = sum(1 for g in rooms.values() if g.online())
        self.peak_players = max(self.peak_players, online)
        self.peak_rooms = max(self.peak_rooms, active)

    def report(self):
        now = time.time()
        live = [g for g in rooms.values() if now - g.touched < 120]
        return {
            "since": self.started, "now": now,
            "visitors": len(self.visitors), "views": dict(self.views), "counts": dict(self.counts),
            "peak_players": self.peak_players, "peak_rooms": self.peak_rooms,
            "online_rooms": len(live), "online_players": sum(len(g.online()) for g in live),
            "live": [{"mode": g.settings["mode"], "phase": g.phase, "players": len(g.online())} for g in live],
            "hours": {str(h * 3600): n for h, n in sorted(self.hours.items())[-48:]},
            "events": [{"t": t, "text": x} for t, x in self.events],
        }


STATS = Stats()
STATS_KEY = os.environ.get("STATS_KEY", "")  # ключ к странице /stats (на Render — в Environment)
MODE_NAMES = {"quiz": "Викторина", "jeopardy": "Своя игра", "100to1": "100 к 1"}


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
    STATS.counts["rooms"] += 1
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
        extra, device = {}, self.device()
        if set_device and not device:
            device = secrets.token_urlsafe(12)
            extra["Set-Cookie"] = f"{DEVICE_COOKIE}={device}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax"
        mime = "text/html; charset=utf-8" if name.endswith(".html") else "text/javascript; charset=utf-8"
        self.send_bytes((STATIC / name).read_bytes(), mime, extra=extra)
        return device

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
        if url.path in ("/", "/host", "/editor"):
            name = {"/": "play.html", "/host": "host.html", "/editor": "editor.html"}[url.path]
            device = self.send_file(name, set_device=True)
            with lock:
                STATS.visit(device, {"/": "Главная", "/host": "Экран ведущего", "/editor": "Редактор"}[url.path])
        elif url.path == "/stats":
            if STATS_KEY and query.get("key", [""])[0] != STATS_KEY:
                return self.send_json({"error": "Нужен ключ: /stats?key=… (STATS_KEY в настройках Render)"}, 403)
            self.send_file("stats.html")
        elif url.path == "/api/stats":
            if STATS_KEY and query.get("key", [""])[0] != STATS_KEY:
                return self.send_json({"error": "Неверный ключ"}, 403)
            with lock:
                self.send_json(STATS.report())
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
                room = rooms.get(parts[1])
                if parts[1] == "_":
                    item = BUILTIN_MEDIA.get(parts[2])
                else:
                    item = room and (room.media.get(parts[2]) or room.si_media.get(parts[2]))
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
                STATS.sample()
                self.send_json(game.state(query.get("pid", [None])[0], self.device()))
        else:
            self.send_json({"error": "Страница не найдена"}, 404)

    def upload_siq(self, url):
        query = parse_qs(url.query)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_SIQ:
            return self.send_json({"error": "Пакет больше 60 МБ — уменьши картинки или раздели на части"}, 413)
        body = self.rfile.read(length)
        with lock:
            game = rooms.get(query.get("room", [""])[0])
            if not game:
                return self.send_json({"error": "Комната не найдена"}, 404)
            if query.get("token", [""])[0] != game.host_token or self.device() != game.host_device:
                return self.send_json({"error": "Управлять игрой может только ведущий этой комнаты"}, 403)
            if game.phase != "setup":
                return self.send_json({"error": "Пакет можно сменить только в главном меню"}, 400)
            try:
                pack = game.upload_siq(body)
            except SiqError as e:
                return self.send_json({"error": f"Пакет не загружен: {e}"}, 400)
            game.settings["mode"] = "jeopardy"
            return self.send_json({"ok": True, **si_info(pack)})

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        if path == "/api/host/upload_siq":
            return self.upload_siq(url)
        data = self.read_json()
        if data is None:
            return self.send_json({"error": "Файл слишком большой: максимум 25 МБ вместе с картинками и аудио"}, 413)
        device = self.device()
        with lock:
            if not device:
                return self.send_json({"error": "Обнови страницу. Если не помогло, разреши cookies в браузере"}, 400)

            if path == "/api/my_room":
                # своя игра этого устройства: чтобы ведущий мог вернуться, а не создавать новую
                cleanup()
                game = next((g for g in rooms.values() if g.host_device == device), None)
                if not game:
                    return self.send_json({})
                return self.send_json({"room": game.code, "token": game.host_token, "phase": game.phase,
                                       "players": len(game.players), "title": game.state()["title"]})

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
                avatar = data.get("avatar") if data.get("avatar") in AVATARS else None
                same = next((pid for pid, p in game.players.items() if pid != mine and p["name"].lower() == name.lower()), None)
                if same:
                    if same in game.online():
                        return self.send_json({"error": "Это имя уже занято"}, 400)
                    # игрок с таким именем вылетел — возвращаем его вместе с очками на этот телефон
                    if mine:
                        del game.players[mine]
                    back = game.players[same]
                    back.update(device=device, seen=time.time())
                    if avatar:
                        back["avatar"] = avatar
                    return self.send_json({"pid": same, "restored": True, "score": back["score"]})
                team = data.get("team")
                if not (isinstance(team, int) and 0 <= team < game.settings["teams"]):
                    team = None
                if mine:
                    game.players[mine]["name"] = name  # с этого телефона уже играют: просто меняем имя
                    if avatar:
                        game.players[mine]["avatar"] = avatar
                    if team is not None:
                        game.players[mine]["team"] = team
                    game.balance_teams()
                    return self.send_json({"pid": mine})
                pid = secrets.token_urlsafe(8)
                game.players[pid] = {
                    "name": name, "device": device, "team": team, "avatar": avatar, "seen": time.time(),
                    "score": 0, "last_points": 0, "prev_place": 0, "streak": 0,
                }
                game.balance_teams()
                STATS.counts["players"] += 1
                return self.send_json({"pid": pid})

            if path.startswith("/api/fd/"):
                pid, fd = data.get("pid"), game.fd
                if not fd or not game.owns(pid, device):
                    return self.send_json({"ok": False})
                game.tick()
                action = path.rsplit("/", 1)[1]
                ok = fd.guess(pid, data.get("text")) if action == "guess" else fd.big_answer(pid, data.get("text")) if action == "big" else False
                STATS.counts["answers"] += bool(ok)
                game.tick()
                return self.send_json({"ok": bool(ok)})

            if path.startswith("/api/si/"):
                pid, si = data.get("pid"), game.si
                if not si or not game.owns(pid, device):
                    return self.send_json({"ok": False})
                game.tick()
                action = path.rsplit("/", 1)[1]
                if action == "pick" and pid == si.chooser:
                    ok = si.pick(data.get("theme"), data.get("question"))
                elif action == "give":
                    ok = si.give(pid, data.get("to"))
                elif action == "stake":
                    ok = si.stake(pid, data.get("amount"))
                elif action == "buzz":
                    res = si.buzz(pid)
                    return self.send_json({"ok": res == "ok", "result": res})
                elif action == "answer":
                    ok = si.answer(pid, data.get("text"))
                elif action == "bet":
                    ok = si.bet(pid, data.get("amount"))
                elif action == "final":
                    ok = si.final_answer(pid, data.get("text"))
                else:
                    ok = False
                STATS.counts["answers"] += bool(ok) and action in ("answer", "final")
                game.tick()
                return self.send_json({"ok": bool(ok)})

            if path == "/api/avatar":
                pid, avatar = data.get("pid"), data.get("avatar")
                ok = game.owns(pid, device) and avatar in AVATARS
                if ok:
                    game.players[pid]["avatar"] = avatar
                return self.send_json({"ok": ok})

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
                pid = data.get("pid")
                game.tick()
                ok = game.phase == "question" and game.owns(pid, device) and pid not in game.answers
                value = game.check(data.get("answer")) if ok else None
                ok = value is not None
                if ok:
                    STATS.counts["answers"] += 1
                    game.answers[pid] = {"value": value, "time": time.time() - game.started_at}
                    game.tick()  # если ответили все, кто на связи, — сразу засекаем паузу перед показом ответа
                return self.send_json({"ok": ok})

            if path.startswith("/api/host/"):
                if data.get("token") != game.host_token or device != game.host_device:
                    return self.send_json({"error": "Управлять игрой может только ведущий этой комнаты"}, 403)
                action = path.rsplit("/", 1)[1]
                before = game.phase
                result = self.host_action(game, action, data)
                after = game.phase
                mode = game.settings["mode"]
                if before == "lobby" and after not in ("lobby", "setup"):
                    STATS.counts["games:" + mode] += 1
                    STATS.hours[int(time.time() // 3600)] += 1
                    STATS.event(f"Началась игра: {MODE_NAMES.get(mode, mode)}, игроков: {len(game.players)}")
                if after == "final" and before != "final":
                    STATS.counts["finished:" + mode] += 1
                    STATS.event(f"Игра доиграна до конца: {MODE_NAMES.get(mode, mode)}")
                return result

        self.send_json({"error": "Страница не найдена"}, 404)

    def host_action(self, game, action, data):
        """Действие ведущего; вызывается под lock."""
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
        elif action == "upload_fd":
            if game.phase != "setup":
                return self.send_json({"error": "Пакет можно сменить только в главном меню"}, 400)
            try:
                game.fd_custom = clean_fd_pack(data.get("pack"))
            except PackError as e:
                return self.send_json({"error": f"Пакет не загружен: {e}"}, 400)
            game.settings.update(fd_pack="custom", mode="100to1")
            return self.send_json({"ok": True, "title": game.fd_custom["title"], "count": len(game.fd_custom["questions"])})
        elif action == "fd_open" and game.fd:
            game.fd.host_open(data.get("index"))
        elif action == "fd_unstrike" and game.fd:
            game.fd.unstrike()
        elif action == "next" and game.fd and game.phase == "lobby":
            game.fd.start()
        elif action == "next" and game.fd and game.phase.startswith("fd_"):
            game.tick()
            game.fd.host_next()
        elif action == "si_pick" and game.si:
            game.si.pick(data.get("theme"), data.get("question"))
        elif action == "si_override" and game.si:
            game.si.override(data.get("index"))
        elif action == "next" and game.si and game.phase == "lobby":
            game.si.start()
        elif action == "next" and game.si and game.phase.startswith("si_"):
            game.tick()
            game.si.host_next()
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
