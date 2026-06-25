"""[HAND-WRITTEN] 인메모리 JobStore 어댑터 — 개발/테스트용.

운영에선 같은 인터페이스(ports.job_store.JobStore)의 DB 어댑터로 교체(도메인 불변).
upsert는 자연키 기준 idempotent: 같은 행 재수집은 0건으로 집계.
"""

from __future__ import annotations

from collections import Counter
from datetime import date


class InMemoryJobStore:
    def __init__(self) -> None:
        self._running: set = set()
        self._rows: dict = {}      # job_type -> {natural_key: row}

    def has_running(self, job_type: str, target_date) -> bool:
        return (job_type, target_date) in self._running

    def save(self, job) -> None:
        key = (job.job_type, job.target_date)
        if job.state.name == "RUNNING":
            self._running.add(key)       # 점유
        else:
            self._running.discard(key)   # DONE/FAILED → 해제

    def upsert(self, job_type: str, rows: list) -> int:
        bucket = self._rows.setdefault(job_type, {})
        changed = 0
        for r in rows:
            k = r.natural_key
            if bucket.get(k) != r:       # 신규 또는 값 변경만 카운트(idempotent)
                bucket[k] = r
                changed += 1
        return changed

    def rows(self, job_type: str) -> list:
        return list(self._rows.get(job_type, {}).values())

    # ── 조회 포트(푸시다운) ── DjangoTradeStore와 동일 시그니처·반환형태.
    # 인메모리는 이미 작은 데이터라 Python 필터로 충분(테스트/개발용).
    def _trades(self) -> list:
        return list(self._rows.get("trades", {}).values())

    def _rents(self) -> list:
        return list(self._rows.get("rents", {}).values())

    def anchor_month(self) -> date | None:
        return max((t.contract_date for t in self._trades()), default=None)

    def trades_by_complex(self, complex_id: str) -> list:
        return [t for t in self._trades() if t.complex_id == complex_id]

    def rents_by_complex(self, complex_id: str) -> list:
        return [r for r in self._rents() if r.complex_id == complex_id]

    def trades_by_region_dong(self, region_code: str, dong: str) -> list:
        return [t for t in self._trades()
                if t.region_code == region_code and t.legal_dong == dong]

    def dongs_by_region(self, region_code: str) -> list[str]:
        return sorted({t.legal_dong for t in self._trades()
                       if t.region_code == region_code})

    def complex_counts(self, region_code: str, dong: str) -> list[tuple]:
        c = Counter((t.complex_id, t.apt_name) for t in self._trades()
                    if t.region_code == region_code and t.legal_dong == dong)
        return [(cid, name, n) for (cid, name), n in c.most_common()]

    def search_dongs_counts(self, q: str, limit: int) -> list[tuple]:
        c = Counter((t.region_code, t.legal_dong) for t in self._trades()
                    if q in t.legal_dong)
        return c.most_common(limit)

    def trades_window(self, start: date) -> list[tuple]:
        return [(t.complex_id, t.region_code, t.legal_dong, t.apt_name,
                 t.build_year, t.area_m2, t.price, t.contract_date)
                for t in self._trades()
                if t.area_m2 > 0 and t.contract_date >= start]

    def rents_window(self, start: date) -> list[tuple]:
        return [(r.complex_id, r.area_m2, r.deposit)
                for r in self._rents()
                if r.area_m2 > 0 and r.contract_date >= start]
