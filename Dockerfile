# 서울 아파트 분석 — 앱 이미지.
# 무거운 의존성(node/claude CLI/pip)은 베이스(seoul-apt-base)에 고정돼 있어,
# 코드만 바뀌면 이 파일은 COPY app/ 레이어만 다시 탄다(수 초). 베이스 빌드는 scripts/build.sh.
ARG BASE_IMAGE=localhost:30500/seoul-apt-base:v1
FROM ${BASE_IMAGE}

# 런타임 동작용 env(앱 고유, 변경 잦지 않음).
#   DB는 마운트 볼륨에 둬 재기동 간 영속(시딩 1회면 끝).
#   첫 기동 시 비어있으면 백필. 24개월(2024-06~2026-05) — 12개월+ 있어야 신뢰도 게이트가
#   서고 [최근6 vs 직전6] 가속 신호가 성립(실측 검증).
ENV DB_PATH=/data/db.sqlite3 \
    SEED_ON_START=1 \
    SEED_MONTHS="202406 202407 202408 202409 202410 202411 202412 202501 202502 202503 202504 202505 202506 202507 202508 202509 202510 202511 202512 202601 202602 202603 202604 202605"

WORKDIR /app

# 앱 소스(.env 포함 — 무료 공공 MOLIT 키).
COPY app/ /app/

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /data

EXPOSE 8009
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
