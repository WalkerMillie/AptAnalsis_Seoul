"""[GENERATED 골격] ListingSnapshot — 참조(reference) 데이터. 마스터/룩업, 거의 불변.

조회 모델/인터페이스는 impl에 정의한다(또는 결정표·어댑터로 적재).
"""

from __future__ import annotations

# >>> impl: editable — ListingSnapshot 참조 모델/조회
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ListingSnapshot:
    """매물 카운트 스냅샷(참조). 매물=분석 게이트 신호(watchlist로 이벤트 전달)."""
    complex_id: str
    count: int
    collected_at: date

    @property
    def natural_key(self) -> tuple:
        return (self.complex_id, self.collected_at)
# <<< impl
