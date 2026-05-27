from django.urls import re_path

from .consumers import ChatConsumer
from .consumers_voice import VoiceSignalingConsumer

websocket_urlpatterns = [
    re_path(r'^ws/chat/(?P<room_name>[^/]+)/$', ChatConsumer.as_asgi()),
    re_path(r'^ws/voice/(?P<room_name>[^/]+)/$', VoiceSignalingConsumer.as_asgi()),
]
