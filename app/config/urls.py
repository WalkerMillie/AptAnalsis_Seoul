"""[HAND-WRITTEN] 루트 URL conf. 컨텍스트별 web 어댑터 urls 를 마운트."""

from django.urls import include, path

from config.ui_view import index, mockups

urlpatterns = [
    path("", index, name="ui_index"),
    path("mockups/", mockups, name="ui_mockups"),
    path("mockups/<str:name>", mockups, name="ui_mockup"),
    path("api/region/", include("contexts.region.adapters.web.urls")),
    path("api/analysis/", include("contexts.analysis.adapters.web.urls")),
    path("api/market_data/", include("contexts.market_data.adapters.web.urls")),
    path("api/market_data/", include("contexts.market_data.adapters.web.query_urls")),
    # 후속: watchlist 어댑터도 여기 마운트
]
