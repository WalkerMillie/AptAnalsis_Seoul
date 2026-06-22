"""[GENERATED 골격] market_data 아웃바운드 포트 — 시그니처는 impl에서."""

from typing import Protocol

# port: fetch_molit_trades
class FetchMolitTrades(Protocol):
    # >>> impl: editable (method signatures)
    def __call__(self, *, region_code: str, deal_ym: str) -> "list[Trade]": ...
    # <<< impl

# port: fetch_ecos_rates
class FetchEcosRates(Protocol):
    # >>> impl: editable (method signatures)
    def __call__(self, *, kinds: "list[str]", as_of: str) -> "list[Rate]": ...
    # <<< impl

# port: fetch_listing_snapshot
class FetchListingSnapshot(Protocol):
    # >>> impl: editable (method signatures)
    def __call__(self, *, complex_ids: "list[str]") -> "list[ListingSnapshot]": ...
    # <<< impl

