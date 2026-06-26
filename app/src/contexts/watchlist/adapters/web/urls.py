"""[HAND-WRITTEN] watchlist URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.watchlist.adapters.web.views import WatchlistItemsView

urlpatterns = [
    path("items/", WatchlistItemsView.as_view(), name="watchlist_items"),
]
