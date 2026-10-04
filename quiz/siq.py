"""Чтение пакетов «Своей игры» в формате SIGame (.siq).

.siq — это zip-архив: content.xml с раундами, темами и вопросами плюс папки
Images/, Audio/, Video/ с файлами. Поддерживаются обе версии разметки:
старая (scenario/atom) и новая (params/item).
"""

import hashlib
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from urllib.parse import unquote

MAX_FILE = 15 * 1024 * 1024  # один файл внутри пакета
MAX_PACK_MEDIA = 120 * 1024 * 1024  # все файлы пакета вместе
MAX_QUESTIONS = 600

MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif",
    ".webp": "image/webp", ".bmp": "image/bmp",
    ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".mp4": "video/mp4", ".webm": "video/webm",
}
KINDS = {"image": "image", "voice": "audio", "audio": "audio", "video": "video"}
# типы особых вопросов: старые и новые названия
SPECIAL = {"cat": "cat", "bagcat": "cat", "secret": "cat", "auction": "auction", "stake": "auction",
           "sponsored": "norisk", "norisk": "norisk"}


class SiqError(ValueError):
    pass


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _children(el, name):
    return [c for c in el if _local(c.tag) == name]


def _child(el, name):
    found = _children(el, name)
    return found[0] if found else None


def parse_siq(data, store, scope):
    """Возвращает пакет «Своей игры»; файлы кладёт в store (ключ → (mime, байты))."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        xml = z.read("content.xml")
    except (zipfile.BadZipFile, KeyError):
        raise SiqError("это не пакет SIGame (.siq)")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise SiqError("файл content.xml повреждён")

    # имена файлов в архиве закодированы (%D0%...), а в вопросах — обычным текстом
    files = {}
    for name in z.namelist():
        p = PurePosixPath(name)
        if len(p.parts) == 2 and p.parts[0] in ("Images", "Audio", "Video"):
            files[unquote(p.name).lower()] = name
    used = {"bytes": 0}

    def media(ref, kind):
        name = ref.lstrip("@").strip()
        path = files.get(name.lower()) or files.get(unquote(name).lower())
        if not path:
            return None
        info = z.getinfo(path)
        mime = MIME.get(PurePosixPath(name).suffix.lower())
        if not mime or info.file_size > MAX_FILE or used["bytes"] + info.file_size > MAX_PACK_MEDIA:
            return None
        if not mime.startswith(kind if kind != "audio" else "audio"):
            return None
        body = z.read(path)
        used["bytes"] += len(body)
        key = hashlib.sha1(body).hexdigest()[:16]
        store[key] = (mime, body)
        return f"/m/{scope}/{key}"

    def content(items):
        """Список элементов вопроса → текст и медиа; marker отделяет медиа к ответу."""
        q = {"text": [], "image": None, "audio": None, "video": None}
        a = {"text": [], "image": None, "audio": None, "video": None}
        cur = q
        for kind, value, is_ref in items:
            if kind == "marker":
                cur = a
                continue
            if kind in ("text", "say", ""):
                if value and value.strip():
                    cur["text"].append(value.strip())
                continue
            k = KINDS.get(kind)
            if k and value and not cur[k]:
                cur[k] = media(value, k) if is_ref else None
        return q, a

    rounds = []
    total = 0
    for rnd in root.iter():
        if _local(rnd.tag) != "round":
            continue
        is_final = (rnd.get("type") or "").lower() == "final"
        themes = []
        themes_el = _child(rnd, "themes")
        for th in (_children(themes_el, "theme") if themes_el is not None else []):
            questions = []
            qs_el = _child(th, "questions")
            for qel in (_children(qs_el, "question") if qs_el is not None else []):
                total += 1
                if total > MAX_QUESTIONS:
                    raise SiqError(f"слишком много вопросов, максимум {MAX_QUESTIONS}")
                items, answer_items = [], []
                scen = _child(qel, "scenario")
                if scen is not None:  # старый формат
                    for atom in _children(scen, "atom"):
                        kind = (atom.get("type") or "text").lower()
                        text = atom.text or ""
                        items.append((kind, text, text.startswith("@")))
                params = _child(qel, "params")
                if params is not None:  # новый формат
                    for prm in _children(params, "param"):
                        target = answer_items if prm.get("name") == "answer" else items if prm.get("name") == "question" else None
                        if target is None:
                            continue
                        for it in _children(prm, "item"):
                            kind = (it.get("type") or "text").lower()
                            target.append((kind, it.text or "", (it.get("isRef") or "").lower() == "true"))
                qdata, adata = content(items)
                if answer_items:
                    extra, _ = content(answer_items)
                    for k in ("image", "audio", "video"):
                        adata[k] = adata[k] or extra[k]
                    adata["text"] += extra["text"]
                right = _child(qel, "right")
                answers = [(a.text or "").strip() for a in (_children(right, "answer") if right is not None else []) if (a.text or "").strip()]
                if not answers or not (qdata["text"] or qdata["image"] or qdata["audio"] or qdata["video"]):
                    continue  # пустой вопрос-заглушка
                special, cat_cost, cat_theme = "simple", None, None
                tel = _child(qel, "type")
                tname = (tel.get("name") if tel is not None else "") or ""
                tname = tname.lower()
                if tname in SPECIAL:
                    special = SPECIAL[tname]
                    for prm in _children(tel, "param"):
                        if prm.get("name") == "cost" and (prm.text or "").strip().isdigit():
                            cat_cost = int(prm.text.strip())
                        if prm.get("name") == "theme" and (prm.text or "").strip():
                            cat_theme = prm.text.strip()
                try:
                    price = int(qel.get("price") or 0)
                except ValueError:
                    price = 0
                questions.append({
                    "price": max(0, price),
                    "special": special,
                    "cat_cost": cat_cost,
                    "cat_theme": cat_theme,
                    "text": "\n".join(qdata["text"])[:600],
                    "image": qdata["image"], "audio": qdata["audio"], "video": qdata["video"],
                    "answer": answers,
                    "answer_text": answers[0][:200],
                    "answer_image": adata["image"], "answer_audio": adata["audio"],
                    "answer_note": "\n".join(adata["text"])[:300] or None,
                })
            if questions:
                themes.append({"name": (th.get("name") or "Без названия").strip()[:60], "questions": questions})
        if themes:
            rounds.append({"name": (rnd.get("name") or "Раунд").strip()[:40], "final": is_final, "themes": themes})
    if not any(not r["final"] for r in rounds):
        raise SiqError("в пакете нет обычных раундов с вопросами")
    return {"title": (root.get("name") or "Своя игра").strip()[:60], "rounds": rounds}


def answer_variants(answers):
    """«Джеймс Кук, Австралия» → полный ответ, «Джеймс Кук», «Австралия»; скобки убираем."""
    out = []
    for a in answers:
        a = a.strip().strip(".!").strip()
        plain = re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", a).strip()
        for v in (a, plain, *re.split(r"\s*(?:[,/;]|\sили\s|\s-\s)\s*", plain)):
            v = v.strip(" .\"«»")
            if v and v.lower() not in (x.lower() for x in out):
                out.append(v)
    return out
