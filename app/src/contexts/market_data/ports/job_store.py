"""[HAND-WRITTEN] market_data 아웃바운드 포트 — 잡 스토어/저장소.

CD-INV01(동일 (job_type, target_date) RUNNING 최대 1개)을 강제하는 책임은
영속화 계층(이 스토어)에 있다 — 애그리거트 한 개로는 동시성을 막지 못한다.
운영에선 PostgreSQL 어댑터가, 개발/테스트에선 InMemoryJobStore가 구현한다.
"""

from typing import Protocol


class JobStore(Protocol):
    def has_running(self, job_type: str, target_date) -> bool: ...
    def save(self, job) -> None: ...
    def upsert(self, job_type: str, rows: list) -> int: ...
