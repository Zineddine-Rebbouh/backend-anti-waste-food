"""
URL configuration for the listings app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminListingListView, CategoryListView, ListingViewSet, ListingFeedView

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listing")
router.register(r"categories", CategoryListView, basename="category")

urlpatterns = [
    path("listings/feed/", ListingFeedView.as_view(), name="listing-feed"),
    path("", include(router.urls)),
    path("admin/listings/", AdminListingListView.as_view(), name="admin-listing-list"),
]
