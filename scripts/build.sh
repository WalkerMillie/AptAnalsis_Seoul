#!/usr/bin/env bash
# 서울 아파트 분석 — 이미지 빌드/푸시.
#
# 두 단계로 나뉜다:
#   1) 베이스(seoul-apt-base) — node22 + claude CLI + pip 의존성. 무겁다(~1분+).
#   2) 앱(seoul-apt)          — FROM 베이스 + 앱 코드. 코드만 바뀌면 수 초.
#
# requirements.txt 가 바뀌지 않는 한 베이스는 건드리지 않는다(자동 판단).
# requirements.txt 가 바뀌었거나 베이스가 레지스트리에 없으면 베이스를 먼저 재빌드한다.
#
# 사용법:
#   ./scripts/build.sh v2            # 앱만 빌드·푸시(베이스 재사용). 태그 v2
#   ./scripts/build.sh v2 --base     # 베이스도 강제 재빌드(requirements 손댔을 때)
#
# 환경변수: REGISTRY(기본 localhost:30500), BASE_TAG(기본 v1)
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:30500}"
BASE_TAG="${BASE_TAG:-v1}"
BASE_IMAGE="$REGISTRY/seoul-apt-base:$BASE_TAG"
APP_TAG="${1:-latest}"
APP_IMAGE="$REGISTRY/seoul-apt:$APP_TAG"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

force_base=0
[[ "${2:-}" == "--base" ]] && force_base=1

# 베이스가 레지스트리에 없으면 강제 빌드(처음 셋업/캐시 소실 대비).
if ! curl -fsS "http://$REGISTRY/v2/seoul-apt-base/tags/list" 2>/dev/null | grep -q "\"$BASE_TAG\""; then
  echo "▶ 베이스($BASE_IMAGE) 레지스트리에 없음 → 베이스 빌드 강제"
  force_base=1
fi

if [[ $force_base -eq 1 ]]; then
  echo "▶ 베이스 빌드: $BASE_IMAGE (node22 + claude CLI + pip)"
  docker build -f Dockerfile.base -t "$BASE_IMAGE" .
  docker push "$BASE_IMAGE"
else
  echo "▶ 베이스 재사용: $BASE_IMAGE (requirements 변경 없음 — --base 로 강제 가능)"
fi

echo "▶ 앱 빌드: $APP_IMAGE (FROM $BASE_IMAGE)"
docker build --build-arg BASE_IMAGE="$BASE_IMAGE" -t "$APP_IMAGE" .
docker push "$APP_IMAGE"

echo "✅ 완료: $APP_IMAGE"
echo "   다음: k8s-manifests/apps/seoul-apt/app.yaml 의 image 태그를 '$APP_TAG' 로 바꿔 커밋 → ArgoCD 자동 배포"
