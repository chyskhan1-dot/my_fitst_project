#!/bin/bash
# Все проверки разом. Запуск из папки quiz:  bash tests/run_all.sh
# Сам поднимает сервер на порту 8000, в конце останавливает. Скриншоты — во временную папку (путь печатается).
# «✗», непустые «errors [...]», «СБОИ: N» (N > 0) или «ошибок сервера: N» (N > 0) — что-то сломалось.
cd "$(dirname "$0")/.." || exit 1
OUT=$(mktemp -d); echo "скриншоты и лог: $OUT"
pkill -f "[s]erver\.py"; sleep 0.5
python3 server.py > "$OUT/server.log" 2>&1 &
sleep 2
for t in tests/t_*.py; do echo "== $t"; PYTHONPATH=. timeout 300 python3 "$t" 2>&1 | tail -16; done
for b in tests/b_*.js; do
  case "$b" in
    *b_monkey.js) for m in king quiz jeopardy heads; do echo "== $b $m"; timeout 280 node "$b" "$OUT" $m 60 2>&1 | grep -E 'этапы|errors|не влезло'; done ;;
    *) echo "== $b"; timeout 280 node "$b" "$OUT" 2>&1 | grep -v 'ответ /api' | tail -3 ;;
  esac
done
echo "ошибок сервера: $(grep -c Traceback "$OUT/server.log")"
pkill -f "[s]erver\.py"
