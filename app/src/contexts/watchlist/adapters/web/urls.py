"""[GENERATED 골격] watchlist URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.watchlist.adapters.web.views import (
    WatchlistItemView,
)

urlpatterns = [
    # >>> impl: editable (경로 ↔ 뷰 매핑)
    path("watchlist_item/", WatchlistItemView.as_view(), name="watchlist_item"),
    # <<< impl
]
