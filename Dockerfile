# 서울 아파트 분석 플랫폼 — 로컬 실행 이미지.
# Django + DRF는 순수 파이썬 휠이라 빌드 도구 불필요(slim으로 충분).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    # DB는 마운트 볼륨에 둬 재기동 간 영속(시딩 1회면 끝).
    DB_PATH=/data/db.sqlite3 \
    # 첫 기동 시 비어있으면 백필. 24개월(2024-06~2026-05) — 12개월+ 있어야
    # 신뢰도 게이트가 제대로 서고 [최근6 vs 직전6] 가속 신호가 성립(실측 검증).
    SEED_ON_START=1 \
    SEED_MONTHS="202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 202504 202505 202506 202507 202508 202509 202510 202511 202512 202601 202602 202603 202604 202605"

WORKDIR /app

# slim 이미지엔 CA 번들이 없어 MOLIT(https) TLS 검증이 실패한다 → ca-certificates 설치.
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 의존성 레이어 캐시: requirements 먼저 설치.
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 앱 소스(.env 포함 — 무료 공공 MOLIT 키).
COPY app/ /app/

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /data

EXPOSE 8009
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
