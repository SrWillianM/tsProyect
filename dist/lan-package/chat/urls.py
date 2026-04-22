from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='chat-index'),
    path('room/<str:room_name>/', views.room, name='chat-room'),
    path('api/rooms/', views.api_rooms, name='api-rooms'),
    path('api/rooms/<int:room_id>/', views.api_room_detail, name='api-room-detail'),
    path('api/rooms/<str:room_name>/messages/', views.api_room_messages, name='api-room-messages'),
]
