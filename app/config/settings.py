"""[HAND-WRITTEN] Django 설정 (infrastructure). 도메인과 무관 — 갈아끼우는 바깥.

src/ 를 import 경로에 올려 contexts.* 를 패키지로 인식하게 한다.
DRF는 JSON 렌더러만(브라우저블 API 템플릿 의존 제거).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

# env 로더(의존성 없이) — KEY=VALUE 줄을 os.environ에 주입(setdefault=먼저 들어온 값 우선).
# 우선순위: 실제 프로세스 env > local.env(커밋 금지·비밀/로컬 오버라이드) > .env(커밋됨).
# local.env를 먼저 읽어 .env의 동일 키를 이긴다(먼저 setdefault된 값이 남으므로).
for _name in ("local.env", ".env"):
    _env_file = BASE_DIR / _name
    if not _env_file.exists():
        continue
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# prod(K8s)에선 SECRET_KEY/DEBUG를 env로 덮어쓴다. 미지정 시 기존 로컬 동작 유지.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
# CF Tunnel/Access 뒤에서만 노출 — 호스트 검증은 게이트웨이에 위임.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "contexts.market_data.adapters.db",   # 실거래 영속 어댑터(Django ORM)
    "contexts.watchlist.adapters.db",     # 관심 단지(즐겨찾기) 영속 어댑터
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# DB 선택: POSTGRES_DB가 env에 있으면 PostgreSQL, 없으면 기존 sqlite 폴백.
# 로컬은 local.env에 POSTGRES_* 를 넣어 도커 postgres(영속)에 붙는다 → 세션 간 데이터 유지.
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            # 요청 간 커넥션 재사용(매 요청 새 연결 비용 절감). 0이면 매번 새로.
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
        },
    }
else:
    # 분석 엔드포인트는 DB가 필요 없지만 Django는 기본 DB 설정을 요구한다(dev sqlite).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            # 기본은 기존과 동일(BASE_DIR/db.sqlite3). DB_PATH 환경변수로 덮어쓰면
            # 컨테이너에서 마운트 볼륨(/data 등)에 DB를 둬 재기동 간 영속 가능.
            "NAME": os.environ.get("DB_PATH") or (BASE_DIR / "db.sqlite3"),
            # 수집(쓰기)과 조회/기동(읽기)이 겹칠 때 'database is locked'로 죽지 않고 대기.
            # SQLite 동시성 한계 완화용. PostgreSQL에선 불필요.
            "OPTIONS": {"timeout": 30},
        },
    }

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
