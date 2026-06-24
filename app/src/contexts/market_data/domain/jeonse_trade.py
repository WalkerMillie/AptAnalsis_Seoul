"""[HAND-WRITTEN] JeonseTrade — 전세 실거래 한 건(참조 데이터). Trade와 같은 패턴.

전세만 다룬다(월세=0). 매매 Trade와 같은 complex_id 규칙(sgg-aptNm)이라 단지×평형으로
조인해 전세가율을 낸다. 도메인은 순수 — I/O·프레임워크 의존 없음(AGENTS.md 규칙2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class JeonseTrade:
    """전세 실거래 한 건. 자연키로 idempotent upsert(매매 Trade와 동일 전략)."""
    complex_id: str       # 지역코드-아파트 (매매 Trade와 동일 규칙 → 조인 가능)
    apt_name: str
    region_code: str      # LAWD 5자리(구)
    legal_dong: str       # 법정동(동)
    area_m2: float
    deposit: int          # 전세보증금(원)
    floor: int
    contract_date: date
    build_year: int = 0

    @property
    def natural_key(self) -> tuple:
        return (self.complex_id, self.contract_date, self.area_m2, self.floor)
