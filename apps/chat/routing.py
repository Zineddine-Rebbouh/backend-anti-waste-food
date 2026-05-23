"""WebSocket URL routing for the chat app — hybrid support system."""

from django.urls import re_path

from .consumers import AdminConsumer, ChatConsumer

websocket_urlpatterns = [
    # User chat WebSocket
    re_path(r"ws/chat/(?P<conversation_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    # Admin pool WebSocket
    re_path(r"ws/admin/$", AdminConsumer.as_asgi()),
]
