"""[HAND-WRITTEN] 루트 URL conf. 컨텍스트별 web 어댑터 urls 를 마운트."""

from django.urls import include, path

from config.ui_view import complex_geo, index, mockups

urlpatterns = [
    path("", index, name="ui_index"),
    # SPA 클라이언트 라우팅 — 뷰는 path로(새로고침/딥링크 시 같은 index.html 반환).
    # 상태(rc·dong·cid·m)만 쿼리스트링. 뷰가 유한 집합이라 catch-all 대신 명시(=/api·/static 무간섭).
    path("analyze", index, name="ui_analyze"),
    path("explore", index, name="ui_explore"),
    path("reco", index, name="ui_reco"),
    path("data/complex_geo", complex_geo, name="ui_complex_geo"),
    path("mockups/", mockups, name="ui_mockups"),
    path("mockups/<str:name>", mockups, name="ui_mockup"),
    path("api/region/", include("contexts.region.adapters.web.urls")),
    path("api/analysis/", include("contexts.analysis.adapters.web.urls")),
    path("api/market_data/", include("contexts.market_data.adapters.web.urls")),
    path("api/market_data/", include("contexts.market_data.adapters.web.query_urls")),
    # 후속: watchlist 어댑터도 여기 마운트
]
