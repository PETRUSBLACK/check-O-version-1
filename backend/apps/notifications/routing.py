from django.urls import re_path

from .consumers import UserNotifyConsumer

websocket_urlpatterns = [
    re_path(r"ws/notify/$", UserNotifyConsumer.as_asgi()),
]
