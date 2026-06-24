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
