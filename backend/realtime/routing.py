from django.urls import re_path
from realtime.consumers import UserNotifyConsumer

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", UserNotifyConsumer.as_asgi()),
]
