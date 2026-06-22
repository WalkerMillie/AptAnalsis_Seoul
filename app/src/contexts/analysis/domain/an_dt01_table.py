"""[GENERATED] an_dt01 결정표 — range 룩업 + effective_date 버저닝 + 완전성 검사. 순수 도메인.

정책을 도메인 코어에 박는다. 행(데이터)=decision_tables/an_dt01.csv, 읽기=adapters/an_dt01_loader.
스펙에서 결정론 생성 — 직접 수정 금지(정책을 바꾸려면 스펙/CSV를 고친다).  req: AN-DT01
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from contexts.analysis.domain.exceptions import IncompleteDecisionTable, NoMatchingRow


@dataclass(frozen=True)
class AnDt01Rule:
    version: str
    effective_date: date
    purchase_price_min: float
    purchase_price_max: float | None   # None = 무한대(∞)
    max_loan_amount: str

    def contains(self, purchase_price: float) -> bool:
        if purchase_price < self.purchase_price_min:
            return False
        return self.purchase_price_max is None or purchase_price < self.purchase_price_max


class AnDt01Table:
    def __init__(self, rules: list[AnDt01Rule]):
        self.rules = list(rules)
    def active_version_as_of(self, as_of: date) -> str:
        eligible = {r.effective_date for r in self.rules if r.effective_date <= as_of}
        if not eligible:
            raise NoMatchingRow(f"{as_of} 시점에 유효한 버전 없음")
        latest = max(eligible)
        return next(r.version for r in self.rules if r.effective_date == latest)

    def _grouped(self) -> dict:
        groups: dict = {}
        for r in self.rules:
            groups.setdefault(r.version, []).append(r)
        return {v: sorted(rs, key=lambda r: r.purchase_price_min) for v, rs in groups.items()}

    def lookup(self, purchase_price: float, as_of: date) -> str:
        for r in self._grouped()[self.active_version_as_of(as_of)]:
            if r.contains(purchase_price):
                return r.max_loan_amount
        raise NoMatchingRow(str(purchase_price) + " 값이 어느 구간에도 안 걸림")
    def check_completeness(self) -> list[str]:
        """버전별로 [0, ∞)를 빈틈/겹침 없이 타일링하는지 (§9-④)."""
        problems: list[str] = []
        for version, rows in sorted(self._grouped().items()):
            if not rows:
                continue
            if rows[0].purchase_price_min != 0:
                problems.append(f"[{version}] 0부터 시작 안 함 (시작={rows[0].purchase_price_min})")
            for prev, cur in zip(rows, rows[1:]):
                if prev.purchase_price_max is None:
                    problems.append(f"[{version}] ∞ 구간 뒤에 또 구간 존재")
                elif cur.purchase_price_min > prev.purchase_price_max:
                    problems.append(f"[{version}] 공백: {prev.purchase_price_max}~{cur.purchase_price_min}")
                elif cur.purchase_price_min < prev.purchase_price_max:
                    problems.append(f"[{version}] 겹침: {cur.purchase_price_min} < {prev.purchase_price_max}")
            if rows[-1].purchase_price_max is not None:
                problems.append(f"[{version}] 마지막 구간이 ∞로 안 열림 (max={rows[-1].purchase_price_max})")
        return problems

    def assert_complete(self) -> None:
        problems = self.check_completeness()
        if problems:
            raise IncompleteDecisionTable(problems)
