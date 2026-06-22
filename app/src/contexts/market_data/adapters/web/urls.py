"""[GENERATED 골격] market_data URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.market_data.adapters.web.views import (
    CollectionJobView,
)

urlpatterns = [
    # >>> impl: editable (경로 ↔ 뷰 매핑)
    path("collection_job/", CollectionJobView.as_view(), name="collection_job"),
    # <<< impl
]
