"""[HAND-WRITTEN] market_data 합성 루트 (web).

포트 구현체를 유스케이스에 주입하는 유일한 곳. 도메인 직접 import 안 함.
개발 기본값 = 인메모리 스토어 + 가짜 소스. 운영은 DB 스토어 + MolitTradesSource(키)로 교체.
"""

import os

from contexts.market_data.application import CollectionJobService
from contexts.market_data.application.trade_query_service import TradeQueryService
from contexts.market_data.adapters.db.django_store import DjangoTradeStore
from contexts.market_data.adapters.fake_sources import make_fetchers
from contexts.market_data.adapters.molit_source import MolitTradesSource

# 영속 스토어(Django ORM). 수집·조회·재시작 모두 같은 DB를 본다.
# 포트(JobStore)만 맞추면 인메모리/PostgreSQL 등으로 교체 가능 — 도메인 불변.
_store = None


def _get_store() -> DjangoTradeStore:
    global _store
    if _store is None:
        _store = DjangoTradeStore()
    return _store


def _build_fetchers() -> dict:
    """MOLIT_SERVICE_KEY 있으면 실거래는 진짜 소스, 없으면 전부 fake.

    fetcher 계약은 (target_date='YYYYMM')->list. 실수집은 구별 호출이 필요하므로
    MOLIT_LAWD_CODES(쉼표구분, 기본 강남3구)의 각 구를 순회해 합친다.
    rates/listings는 별도 소스(ECOS 키 등)라 당분간 fake 유지.
    """
    fetchers = make_fetchers()
    key = os.environ.get("MOLIT_SERVICE_KEY")
    if key:
        src = MolitTradesSource(key)
        lawds = [c.strip() for c in os.environ.get(
            "MOLIT_LAWD_CODES", "11680,11650,11710").split(",") if c.strip()]

        def fetch_trades(deal_ym: str) -> list:
            out: list = []
            for code in lawds:
                out.extend(src(region_code=code, deal_ym=deal_ym))
            return out

        fetchers["trades"] = fetch_trades
    return fetchers


def get_service() -> CollectionJobService:
    return CollectionJobService(store=_get_store(), fetchers=_build_fetchers())


def get_trade_query() -> TradeQueryService:
    return TradeQueryService(_get_store())
