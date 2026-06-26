"""[HAND-WRITTEN] 영속 모델 (Django ORM). 어댑터 — 도메인 Trade와 별개의 저장 표현.

dev=SQLite, 운영=PostgreSQL(settings.DATABASES만 교체). 도메인은 이 모듈을 모른다.
"""

from django.db import models


class TradeRecord(models.Model):
    complex_id = models.CharField(max_length=200)
    apt_name = models.CharField(max_length=200)
    region_code = models.CharField(max_length=10, db_index=True)
    legal_dong = models.CharField(max_length=100, db_index=True)
    area_m2 = models.FloatField()
    price = models.BigIntegerField()
    floor = models.IntegerField()
    contract_date = models.DateField()
    build_year = models.IntegerField(default=0)   # 건축년도(연). 0 = 정보 없음.

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["complex_id", "contract_date", "area_m2", "floor"],
                name="uq_trade_natural"),          # 자연키 — idempotent upsert
        ]
        # 전국 집계(랭킹·지도·후보)는 contract_date>=start 윈도우 스캔 + Max(anchor)에
        # 의존한다. 단독 인덱스로 풀스캔 회피(단지별 조회는 위 unique의 complex_id prefix가 커버).
        indexes = [models.Index(fields=["contract_date"], name="ix_trade_cd")]


class RentRecord(models.Model):
    """전세 실거래 영속. TradeRecord와 같은 자연키 전략(idempotent upsert)."""
    complex_id = models.CharField(max_length=200, db_index=True)
    apt_name = models.CharField(max_length=200)
    region_code = models.CharField(max_length=10, db_index=True)
    legal_dong = models.CharField(max_length=100, db_index=True)
    area_m2 = models.FloatField()
    deposit = models.BigIntegerField()    # 전세보증금(원)
    floor = models.IntegerField()
    contract_date = models.DateField()
    build_year = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["complex_id", "contract_date", "area_m2", "floor"],
                name="uq_rent_natural"),
        ]
        indexes = [models.Index(fields=["contract_date"], name="ix_rent_cd")]


class AggregateSnapshot(models.Model):
    """전국 집계 결과의 캐시 스냅샷(티커·rankings·region_summary·candidates 공용).

    payload = 라이브 함수 출력을 '그대로' 얼린 값(재구현 아님). data_version과
    logic_version이 둘 다 현재값과 일치할 때만 사용 — 데이터가 늘거나(backfill/갱신)
    계산 로직(AGG_LOGIC_VERSION)이 바뀌면 자동 무효 → 다음 요청이 1회 재계산.
    cache_key 예: "rankings|m=120|mt=10|lim=100", "ticker".
    """
    cache_key = models.CharField(max_length=120, unique=True)
    data_version = models.CharField(max_length=40)   # 마지막으로 행이 늘어난 수집 시각(ISO) 또는 "v0"
    logic_version = models.IntegerField()            # 계산 로직 버전(코드 상수). 로직 변경 시 ↑
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now=True)


class CollectionJobRecord(models.Model):
    job_type = models.CharField(max_length=40)
    target_date = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    fetched_count = models.IntegerField(default=0)
    error = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job_type", "target_date"], name="uq_job"),  # CD-INV01 보조
        ]
