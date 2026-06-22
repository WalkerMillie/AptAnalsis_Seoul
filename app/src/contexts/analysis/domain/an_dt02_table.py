"""[GENERATED] an_dt02 결정표 — flag 정확매칭 룩업 + 버저닝. 순수 도메인.

행=decision_tables/an_dt02.csv, 읽기=adapters/an_dt02_loader.  req: AN-DT02
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from contexts.analysis.domain.exceptions import NoMatchingRow


@dataclass(frozen=True)
class AnDt02Rule:
    version: str
    effective_date: date
    complex_id: str
    ltz_applies: str


class AnDt02Table:
    def __init__(self, rules: list[AnDt02Rule]):
        self.rules = list(rules)
    def active_version_as_of(self, as_of: date) -> str:
        eligible = {r.effective_date for r in self.rules if r.effective_date <= as_of}
        if not eligible:
            raise NoMatchingRow(f"{as_of} 시점에 유효한 버전 없음")
        latest = max(eligible)
        return next(r.version for r in self.rules if r.effective_date == latest)
    def lookup(self, complex_id: str, as_of: date) -> str:
        key = (complex_id,)
        version = self.active_version_as_of(as_of)
        for r in self.rules:
            if r.version != version:
                continue
            if (r.complex_id,) == key:
                return r.ltz_applies
        raise NoMatchingRow(str(key) + " 조합에 맞는 행 없음")
