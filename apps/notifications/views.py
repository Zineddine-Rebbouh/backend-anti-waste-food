import logging
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.pagination import CustomCursorPagination
from .models import FCMDevice, Notification, NotificationPreference
from .serializers import (
    FCMDeviceRegisterSerializer,
    FCMDeviceSerializer,
    FCMDeviceUnregisterSerializer,
    MarkReadSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from .services import NotificationService

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.GenericViewSet):
    pagination_class = CustomCursorPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user, channel="in_app"
        ).order_by("-created_at")

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        serializer = NotificationListSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        notification = self.get_object()
        if notification.recipient != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = NotificationService.mark_as_read(
            request.user, serializer.validated_data["notification_ids"]
        )
        return Response({"marked_read": count})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        count = NotificationService.mark_all_read(request.user)
        return Response({"marked_read": count})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({"unread_count": count})


class NotificationPreferenceView(RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj


class FCMDeviceRegisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FCMDeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        device, created = FCMDevice.objects.update_or_create(
            user=request.user,
            device_id=data["device_id"],
            defaults={
                "registration_id": data["registration_id"],
                "device_type": data["device_type"],
                "app_version": data.get("app_version", ""),
                "is_active": True,
            },
        )

        logger.info(
            "Registered FCM device",
            extra={
                "user_id": str(request.user.id),
                "device_id": device.device_id,
                "token_tail": device.masked_token,
                "created": created,
            },
        )
        return Response(
            FCMDeviceSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FCMDeviceUnregisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        serializer = FCMDeviceUnregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = FCMDevice.objects.filter(
            user=request.user,
            device_id=serializer.validated_data["device_id"],
        ).update(is_active=False)
        return Response({"unregistered": updated})
