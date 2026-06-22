"""[HAND-WRITTEN] region 조회 유스케이스 — 구 마스터 조회(드릴다운 1단계).

도메인 참조 데이터를 읽어 전달만 한다(판단 없음). 동·단지는 market_data 소관.
"""

from __future__ import annotations

from contexts.region.domain import region as region_ref


class RegionQueryService:
    def districts(self) -> list[dict]:
        return region_ref.districts()

    def is_valid_district(self, code: str) -> bool:
        return region_ref.is_valid_district(code)
