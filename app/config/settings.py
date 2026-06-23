"""[HAND-WRITTEN] Django 설정 (infrastructure). 도메인과 무관 — 갈아끼우는 바깥.

src/ 를 import 경로에 올려 contexts.* 를 패키지로 인식하게 한다.
DRF는 JSON 렌더러만(브라우저블 API 템플릿 의존 제거).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

# .env 로더(의존성 없이) — KEY=VALUE 줄을 os.environ에 주입(기존 값 우선).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SECRET_KEY = "dev-insecure-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "contexts.market_data.adapters.db",   # 실거래 영속 어댑터(Django ORM)
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# 분석 엔드포인트는 DB가 필요 없지만 Django는 기본 DB 설정을 요구한다(dev sqlite).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # 기본은 기존과 동일(BASE_DIR/db.sqlite3). DB_PATH 환경변수로 덮어쓰면
        # 컨테이너에서 마운트 볼륨(/data 등)에 DB를 둬 재기동 간 영속 가능.
        "NAME": os.environ.get("DB_PATH") or (BASE_DIR / "db.sqlite3"),
        # 수집(쓰기)과 조회/기동(읽기)이 겹칠 때 'database is locked'로 죽지 않고 대기.
        # SQLite 동시성 한계 완화용. 운영 PostgreSQL 전환 시 불필요.
        "OPTIONS": {"timeout": 30},
    },
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
