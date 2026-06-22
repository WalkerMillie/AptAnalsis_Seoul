"""[GENERATED 골격] Trade — 참조(reference) 데이터. 마스터/룩업, 거의 불변.

조회 모델/인터페이스는 impl에 정의한다(또는 결정표·어댑터로 적재).
"""

from __future__ import annotations

# >>> impl: editable — Trade 참조 모델/조회
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Trade:
    """국토부 실거래가 한 건(참조 데이터). 자연키로 idempotent upsert.

    region_code(구)·legal_dong(동)은 구→동→단지 드릴다운의 파생 근거다.
    """
    complex_id: str       # 지역코드-아파트 (단지 식별)
    apt_name: str         # 아파트명(표시용)
    region_code: str      # LAWD 5자리 (구)
    legal_dong: str       # 법정동(동)
    area_m2: float
    price: int            # 거래금액(원)
    floor: int
    contract_date: date
    build_year: int = 0   # 건축년도(연). 0 = 정보 없음. 용적률·건폐율은 실거래 API에 없음.

    @property
    def natural_key(self) -> tuple:
        return (self.complex_id, self.contract_date, self.area_m2, self.floor)
# <<< impl
