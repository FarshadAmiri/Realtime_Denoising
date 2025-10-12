from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
    re_path(r'ws/stream/(?P<username>\w+)/$', consumers.StreamConsumer.as_asgi()),
]
