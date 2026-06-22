"""[HAND-WRITTEN] market_data 드릴다운 조회 라우팅 (생성된 urls.py와 별개로 마운트)."""

from django.urls import path

from contexts.market_data.adapters.web.query_views import (
    ComplexListView, ComplexScoreView, DongListView, DongSearchView,
    PriceGrowthView, PriceSeriesView, RankingView, RegionSummaryView, TradeListView,
)

urlpatterns = [
    path("dongs/", DongListView.as_view(), name="market_data_dongs"),
    path("complexes/", ComplexListView.as_view(), name="market_data_complexes"),
    path("trades/", TradeListView.as_view(), name="market_data_trades"),
    path("search_dongs/", DongSearchView.as_view(), name="market_data_search_dongs"),
    path("price_growth/", PriceGrowthView.as_view(), name="market_data_price_growth"),
    path("price_series/", PriceSeriesView.as_view(), name="market_data_price_series"),
    path("complex_scores/", ComplexScoreView.as_view(), name="market_data_complex_scores"),
    path("rankings/", RankingView.as_view(), name="market_data_rankings"),
    path("region_summary/", RegionSummaryView.as_view(), name="market_data_region_summary"),
]
