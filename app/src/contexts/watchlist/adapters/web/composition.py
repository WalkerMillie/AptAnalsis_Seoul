"""[HAND-WRITTEN] watchlist 합성 루트 (web). 저장소 포트 구현을 유스케이스에 주입하는 유일한 곳."""

from contexts.watchlist.adapters.db.django_repo import DjangoWatchlistRepo
from contexts.watchlist.application import WatchlistItemService


def get_watchlist_service() -> WatchlistItemService:
    return WatchlistItemService(DjangoWatchlistRepo())
