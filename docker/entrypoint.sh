#!/usr/bin/env sh
# 컨테이너 기동 시퀀스: 스키마 마이그레이션 → (비어있으면) 백필 시딩 → 서버.
# 시딩은 idempotent(upsert)이며 DB가 비었을 때만 1회 수행 → 재기동 시 즉시 뜬다.
set -e

cd /app

echo "▶ migrate"
python manage.py migrate --noinput

# 현재 적재된 실거래 행 수 — 0이면 첫 기동으로 보고 백필.
TRADE_COUNT=$(python manage.py shell -c \
  "from contexts.market_data.adapters.db.models import TradeRecord; print(TradeRecord.objects.count())" \
  2>/dev/null | tail -n 1)
TRADE_COUNT=${TRADE_COUNT:-0}

if [ "$SEED_ON_START" = "1" ] && [ "$TRADE_COUNT" -eq 0 ]; then
  echo "▶ DB 비어있음 → 백필 시딩 (months: $SEED_MONTHS). 25개 구 × N개월, 수 분 소요…"
  # shellcheck disable=SC2086
  python backfill.py $SEED_MONTHS || echo "⚠️ 백필 일부 실패 — 서버는 계속 기동"
else
  echo "▶ 기존 실거래 ${TRADE_COUNT}건 — 시딩 건너뜀"
fi

echo "▶ runserver 0.0.0.0:8009"
exec python manage.py runserver 0.0.0.0:8009
