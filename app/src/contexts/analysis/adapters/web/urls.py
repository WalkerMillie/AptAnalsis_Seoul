"""[HAND-WRITTEN] analysis URL 라우팅 (web adapter)."""

from django.urls import path

from contexts.analysis.adapters.web.views import AICommentView, AnalysisView, TransitView

urlpatterns = [
    path("evaluate/", AnalysisView.as_view(), name="analysis_evaluate"),
    path("ai_comment/", AICommentView.as_view(), name="analysis_ai_comment"),
    path("transit/", TransitView.as_view(), name="analysis_transit"),
]
