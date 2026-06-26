#!/usr/bin/env sh
# 컨테이너 기동 시퀀스: 스키마 마이그레이션 → (비어있으면) 백필 시딩 → 서버.
# 시딩은 idempotent(upsert)이며 DB가 비었을 때만 1회 수행 → 재기동 시 즉시 뜬다.
set -e

cd /app

# AI 코멘트(AI_PROVIDER=cli) 자격증명 셋업 — k8s Secret을 read-only로 마운트(/secrets/claude)하면
# 쓰기 가능한 HOME으로 복사한다. claude CLI가 만료 토큰을 refreshToken으로 갱신하며 파일에
# 되써야 하기 때문(read-only 마운트 직접 사용 불가). 온보딩 마커도 심어 -p 비대화 실행을 보장.
if [ -f /secrets/claude/.credentials.json ]; then
  mkdir -p "$HOME/.claude"
  cp /secrets/claude/.credentials.json "$HOME/.claude/.credentials.json"
  chmod 600 "$HOME/.claude/.credentials.json"
  [ -f "$HOME/.claude.json" ] || echo '{"hasCompletedOnboarding":true}' > "$HOME/.claude.json"
  echo "▶ claude 자격증명 셋업 완료 (AI_PROVIDER=${AI_PROVIDER:-cli})"
else
  echo "▶ /secrets/claude 없음 — AI 코멘트는 graceful-fail(나머지 기능 정상)"
fi

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
  python backfill.py trades $SEED_MONTHS || echo "⚠️ 매매 백필 일부 실패 — 계속"
  # 전세도 시딩(전월세 API 미승인 키면 FAILED로 graceful — 서버는 계속).
  # shellcheck disable=SC2086
  python backfill.py rents $SEED_MONTHS || echo "⚠️ 전세 백필 일부 실패 — 계속"
else
  echo "▶ 기존 실거래 ${TRADE_COUNT}건 — 시딩 건너뜀"
fi

echo "▶ runserver 0.0.0.0:8009"
exec python manage.py runserver 0.0.0.0:8009
