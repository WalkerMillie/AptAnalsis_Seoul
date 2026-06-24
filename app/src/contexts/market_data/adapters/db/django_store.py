"""[HAND-WRITTEN] Django ORM 기반 JobStore 구현 (영속). InMemoryJobStore의 드롭인 대체.

JobStore 포트(has_running/save/upsert/rows)를 DB로 구현 — 도메인·application 불변.
도메인 Trade ↔ TradeRecord 매핑은 여기(어댑터)서만.
"""

from __future__ import annotations

from django.db import transaction

from contexts.market_data.domain.trade import Trade
from contexts.market_data.domain.jeonse_trade import JeonseTrade
from contexts.market_data.adapters.db.models import (
    CollectionJobRecord, TradeRecord, RentRecord)


class DjangoTradeStore:
    def has_running(self, job_type: str, target_date) -> bool:
        return CollectionJobRecord.objects.filter(
            job_type=job_type, target_date=target_date, state="RUNNING").exists()

    def save(self, job) -> None:
        CollectionJobRecord.objects.update_or_create(
            job_type=job.job_type, target_date=job.target_date,
            defaults={"state": job.state.name,
                      "fetched_count": job.fetched_count,
                      "error": job.error or ""})

    def upsert(self, job_type: str, rows: list) -> int:
        if job_type == "trades":
            return self._upsert_trades(rows)
        if job_type == "rents":
            return self._upsert_rents(rows)
        return len(rows)            # rates/listings 상세 미저장(현재 드릴다운 미사용)

    def _upsert_trades(self, rows: list) -> int:
        added = 0
        # 한 작업(구·월) 전체를 단일 트랜잭션으로 묶음 — 행마다 autocommit fsync 방지(대량 백필 가속).
        # upsert 의미·created 카운트는 행별 update_or_create 그대로 보존.
        with transaction.atomic():
            for r in rows:
                _, created = TradeRecord.objects.update_or_create(
                    complex_id=r.complex_id, contract_date=r.contract_date,
                    area_m2=r.area_m2, floor=r.floor,
                    defaults={"apt_name": r.apt_name, "region_code": r.region_code,
                              "legal_dong": r.legal_dong, "price": r.price,
                              "build_year": r.build_year})
                if created:
                    added += 1
        return added                # '추가' 건수(planning §3.5). 재수집 동일행 → 0

    def _upsert_rents(self, rows: list) -> int:
        added = 0
        with transaction.atomic():
            for r in rows:
                _, created = RentRecord.objects.update_or_create(
                    complex_id=r.complex_id, contract_date=r.contract_date,
                    area_m2=r.area_m2, floor=r.floor,
                    defaults={"apt_name": r.apt_name, "region_code": r.region_code,
                              "legal_dong": r.legal_dong, "deposit": r.deposit,
                              "build_year": r.build_year})
                if created:
                    added += 1
        return added

    def rows(self, job_type: str) -> list:
        if job_type == "trades":
            return [Trade(complex_id=t.complex_id, apt_name=t.apt_name,
                          region_code=t.region_code, legal_dong=t.legal_dong,
                          area_m2=t.area_m2, price=t.price, floor=t.floor,
                          contract_date=t.contract_date, build_year=t.build_year)
                    for t in TradeRecord.objects.all()]
        if job_type == "rents":
            return [JeonseTrade(complex_id=r.complex_id, apt_name=r.apt_name,
                               region_code=r.region_code, legal_dong=r.legal_dong,
                               area_m2=r.area_m2, deposit=r.deposit, floor=r.floor,
                               contract_date=r.contract_date, build_year=r.build_year)
                    for r in RentRecord.objects.all()]
        return []
