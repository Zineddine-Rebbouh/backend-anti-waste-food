"""
URL configuration for the listings app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryListView, ListingViewSet

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listing")
router.register(r"categories", CategoryListView, basename="category")

urlpatterns = [
    path("", include(router.urls)),
]
