"""[HAND-WRITTEN] 개발용 가짜 소스 — 네트워크/API키 없이 샘플 데이터.

운영에선 molit_source.MolitTradesSource(API키) 등 실제 어댑터로 교체한다.
fetcher 계약: (target_date) -> list[참조객체]. (소스별 세부 인자는 합성 시 래핑)
"""

from datetime import date

from contexts.market_data.domain.trade import Trade
from contexts.market_data.domain.rate import Rate
from contexts.market_data.domain.listing_snapshot import ListingSnapshot


def make_fetchers() -> dict:
    return {
        "trades": lambda target_date: [
            Trade("11680-은마", "은마", "11680", "대치동", 84.97, 1_200_000_000, 15, date(2026, 5, 20), 1979),
            Trade("11680-은마", "은마", "11680", "대치동", 76.79, 1_050_000_000, 3, date(2026, 5, 18), 1979),
            Trade("11680-래미안대치팰리스", "래미안대치팰리스", "11680", "대치동", 94.5, 3_500_000_000, 20, date(2026, 5, 22), 2015),
        ],
        "rates": lambda target_date: [
            Rate("기준금리", 0.025, date(2026, 5, 1)),
            Rate("주담대", 0.045, date(2026, 5, 1)),
        ],
        "listings": lambda target_date: [
            ListingSnapshot("11680-은마", 7, date(2026, 6, 20)),
        ],
    }
