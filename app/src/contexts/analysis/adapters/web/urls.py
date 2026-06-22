"""[HAND-WRITTEN] analysis URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.analysis.adapters.web.views import AnalysisView

urlpatterns = [
    path("evaluate/", AnalysisView.as_view(), name="analysis_evaluate"),
]
