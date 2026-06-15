from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    FCMDeviceRegisterView,
    FCMDeviceUnregisterView,
    NotificationPreferenceView,
    NotificationViewSet,
)

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
    path("notifications/preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("devices/register/", FCMDeviceRegisterView.as_view(), name="device-register"),
    path("devices/unregister/", FCMDeviceUnregisterView.as_view(), name="device-unregister"),
]
