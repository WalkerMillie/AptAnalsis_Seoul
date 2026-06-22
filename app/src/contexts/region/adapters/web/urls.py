"""[HAND-WRITTEN] region URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.region.adapters.web.views import DistrictListView

urlpatterns = [
    path("districts/", DistrictListView.as_view(), name="region_districts"),
]
