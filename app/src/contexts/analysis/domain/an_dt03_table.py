"""[GENERATED] an_dt03 결정표 — flag 정확매칭 룩업 + 버저닝. 순수 도메인.

행=decision_tables/an_dt03.csv, 읽기=adapters/an_dt03_loader.  req: AN-DT03
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from contexts.analysis.domain.exceptions import NoMatchingRow


@dataclass(frozen=True)
class AnDt03Rule:
    version: str
    effective_date: date
    holding_years: str
    residency_years: str
    house_count: str
    capital_gains_tax_exempt: str


class AnDt03Table:
    def __init__(self, rules: list[AnDt03Rule]):
        self.rules = list(rules)
    def active_version_as_of(self, as_of: date) -> str:
        eligible = {r.effective_date for r in self.rules if r.effective_date <= as_of}
        if not eligible:
            raise NoMatchingRow(f"{as_of} 시점에 유효한 버전 없음")
        latest = max(eligible)
        return next(r.version for r in self.rules if r.effective_date == latest)
    def lookup(self, holding_years: str, residency_years: str, house_count: str, as_of: date) -> str:
        key = (holding_years, residency_years, house_count)
        version = self.active_version_as_of(as_of)
        for r in self.rules:
            if r.version != version:
                continue
            if (r.holding_years, r.residency_years, r.house_count) == key:
                return r.capital_gains_tax_exempt
        raise NoMatchingRow(str(key) + " 조합에 맞는 행 없음")
