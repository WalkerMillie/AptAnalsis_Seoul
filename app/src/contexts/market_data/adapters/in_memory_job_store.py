"""[HAND-WRITTEN] 인메모리 JobStore 어댑터 — 개발/테스트용.

운영에선 같은 인터페이스(ports.job_store.JobStore)의 DB 어댑터로 교체(도메인 불변).
upsert는 자연키 기준 idempotent: 같은 행 재수집은 0건으로 집계.
"""

from __future__ import annotations


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
