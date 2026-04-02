"""
Health check URL patterns for SaveFood DZ.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.health_check, name="health-check"),
    path("liveness/", views.liveness_check, name="liveness-check"),
    path("readiness/", views.readiness_check, name="readiness-check"),
]
