from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='chat-index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('channels/create/', views.create_room, name='create-room'),
    path('room/<str:room_name>/', views.room, name='chat-room'),
    path('api/rooms/', views.api_rooms, name='api-rooms'),
    path('api/rooms/<int:room_id>/', views.api_room_detail, name='api-room-detail'),
    path(
        'api/rooms/<str:room_name>/messages/',
        views.api_room_messages,
        name='api-room-messages',
    ),
    path(
        'api/rooms/<str:room_name>/attachments/',
        views.api_room_attachment,
        name='api-room-attachment',
    ),
    path('api/stickers/', views.api_stickers, name='api-stickers'),
    path(
        'api/stickers/<int:sticker_id>/',
        views.api_sticker_detail,
        name='api-sticker-detail',
    ),
]
