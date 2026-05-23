"""
URL patterns for core health checks and geographic utility endpoints.
"""

from django.urls import path

from . import views
from .utils_views import WilayaFromCoordsView, WilayaListView

urlpatterns = [
    # ── Health checks ────────────────────────────────────────────────────────
    path("", views.health_check, name="health-check"),
    path("liveness/", views.liveness_check, name="liveness-check"),
    path("readiness/", views.readiness_check, name="readiness-check"),
    # ── Geographic utilities ──────────────────────────────────────────────────
    path("utils/wilaya-from-coords/", WilayaFromCoordsView.as_view(), name="wilaya-from-coords"),
    path("utils/wilayas/", WilayaListView.as_view(), name="wilaya-list"),
]
