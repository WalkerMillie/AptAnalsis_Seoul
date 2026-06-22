"""[GENERATED 골격] Rate — 참조(reference) 데이터. 마스터/룩업, 거의 불변.

조회 모델/인터페이스는 impl에 정의한다(또는 결정표·어댑터로 적재).
"""

from __future__ import annotations

# >>> impl: editable — Rate 참조 모델/조회
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Rate:
    """ECOS 금리 한 건(참조). (종류, 기준일) 유니크."""
    kind: str             # 기준금리 / 주담대 / 국고채 ...
    value: float          # 소수(0.035 == 3.5%)
    as_of: date

    @property
    def natural_key(self) -> tuple:
        return (self.kind, self.as_of)
# <<< impl
