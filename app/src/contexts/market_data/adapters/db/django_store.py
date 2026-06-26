"""[HAND-WRITTEN] Django ORM 기반 JobStore 구현 (영속). InMemoryJobStore의 드롭인 대체.

JobStore 포트(has_running/save/upsert/rows)를 DB로 구현 — 도메인·application 불변.
도메인 Trade ↔ TradeRecord 매핑은 여기(어댑터)서만.
"""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Count, Max

from contexts.market_data.domain.trade import Trade
from contexts.market_data.domain.jeonse_trade import JeonseTrade
from contexts.market_data.adapters.db.models import (
    CollectionJobRecord, TradeRecord, RentRecord, AggregateSnapshot)


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

    # ── 조회 포트(푸시다운) ──────────────────────────────────────────
    # rows()는 전 테이블을 도메인 객체로 materialize한다(O(N), 백필 10년치엔 치명적).
    # 아래 메서드는 필터/집계를 DB(SQL)로 내려 필요한 만큼만 가져온다. InMemoryJobStore가
    # 동일 시그니처·반환형태를 Python으로 구현 — 도메인/application은 어느 스토어든 불변.

    def anchor_month(self) -> date | None:
        """전체 매매 실거래의 최신 계약일(공통 anchor 산정용). 인덱스로 즉답."""
        return TradeRecord.objects.aggregate(m=Max("contract_date"))["m"]

    def trades_by_complex(self, complex_id: str) -> list[Trade]:
        """한 단지의 매매 실거래 전체(complex_id 인덱스 prefix로 좁힘)."""
        return [Trade(complex_id=t.complex_id, apt_name=t.apt_name,
                      region_code=t.region_code, legal_dong=t.legal_dong,
                      area_m2=t.area_m2, price=t.price, floor=t.floor,
                      contract_date=t.contract_date, build_year=t.build_year)
                for t in TradeRecord.objects.filter(complex_id=complex_id)]

    def rents_by_complex(self, complex_id: str) -> list[JeonseTrade]:
        """한 단지의 전세 실거래 전체."""
        return [JeonseTrade(complex_id=r.complex_id, apt_name=r.apt_name,
                            region_code=r.region_code, legal_dong=r.legal_dong,
                            area_m2=r.area_m2, deposit=r.deposit, floor=r.floor,
                            contract_date=r.contract_date, build_year=r.build_year)
                for r in RentRecord.objects.filter(complex_id=complex_id)]

    def trades_by_region_dong(self, region_code: str, dong: str) -> list[Trade]:
        """구+동의 매매 실거래 전체(region_code·legal_dong 인덱스로 좁힘)."""
        return [Trade(complex_id=t.complex_id, apt_name=t.apt_name,
                      region_code=t.region_code, legal_dong=t.legal_dong,
                      area_m2=t.area_m2, price=t.price, floor=t.floor,
                      contract_date=t.contract_date, build_year=t.build_year)
                for t in TradeRecord.objects.filter(
                    region_code=region_code, legal_dong=dong)]

    def dongs_by_region(self, region_code: str) -> list[str]:
        """구에서 거래가 있는 법정동(distinct, 오름차순)."""
        return sorted(TradeRecord.objects.filter(region_code=region_code)
                      .values_list("legal_dong", flat=True).distinct())

    def complex_counts(self, region_code: str, dong: str) -> list[tuple]:
        """구+동 단지별 (complex_id, apt_name, 거래수) — 거래빈도 내림차순."""
        qs = (TradeRecord.objects.filter(region_code=region_code, legal_dong=dong)
              .values("complex_id", "apt_name").annotate(n=Count("id")).order_by("-n"))
        return [(r["complex_id"], r["apt_name"], r["n"]) for r in qs]

    def search_dongs_counts(self, q: str, limit: int) -> list[tuple]:
        """동 이름 부분일치 (region_code, dong)별 거래수 — 빈도 내림차순. ((rc,dong), n)."""
        qs = (TradeRecord.objects.filter(legal_dong__contains=q)
              .values("region_code", "legal_dong").annotate(n=Count("id"))
              .order_by("-n")[:limit])
        return [((r["region_code"], r["legal_dong"]), r["n"]) for r in qs]

    def trades_window(self, start: date) -> list[tuple]:
        """start(포함) 이후 매매 실거래(area>0)를 경량 튜플로 — 전국 집계용.
        튜플: (complex_id, region_code, legal_dong, apt_name, build_year, area_m2, price, contract_date).
        """
        return list(TradeRecord.objects
                    .filter(area_m2__gt=0, contract_date__gte=start)
                    .values_list("complex_id", "region_code", "legal_dong",
                                 "apt_name", "build_year", "area_m2",
                                 "price", "contract_date"))

    def rents_window(self, start: date) -> list[tuple]:
        """start(포함) 이후 전세 실거래(area>0). 튜플: (complex_id, area_m2, deposit)."""
        return list(RentRecord.objects
                    .filter(area_m2__gt=0, contract_date__gte=start)
                    .values_list("complex_id", "area_m2", "deposit"))

    def data_version(self) -> str:
        """데이터가 마지막으로 '실제로 늘어난' 수집 시각(ISO). 없으면 "v0".

        싼 probe(수집작업 메타는 행 수십 개) — 매 요청 COUNT(수십만행) 없이 ~1ms에
        '데이터 바뀌었나'를 판정. fetched_count>0 만 봐서 빈 갱신은 버전 안 올림."""
        v = (CollectionJobRecord.objects.filter(fetched_count__gt=0)
             .aggregate(v=Max("updated_at"))["v"])
        return v.isoformat() if v else "v0"

    def agg_snapshot(self, cache_key: str) -> dict | None:
        """캐시키 스냅샷 — {data_version, logic_version, payload} 또는 None."""
        row = AggregateSnapshot.objects.filter(cache_key=cache_key).first()
        if row is None:
            return None
        return {"data_version": row.data_version,
                "logic_version": row.logic_version, "payload": row.payload}

    def save_agg_snapshot(self, cache_key: str, data_version: str,
                          logic_version: int, payload) -> None:
        """캐시키 스냅샷 저장/갱신(키 unique → 1키 1행, 재계산 시 덮어씀)."""
        AggregateSnapshot.objects.update_or_create(
            cache_key=cache_key,
            defaults={"data_version": data_version,
                      "logic_version": logic_version, "payload": payload})
