from django.contrib import admin

from .models import Message, Profile, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "created_at", "created_by")
    search_fields = ("name",)
    list_filter = ("kind", "created_at")
    ordering = ("kind", "name")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("nickname", "user", "updated_at")
    search_fields = ("nickname", "user__username")
    ordering = ("nickname",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("room", "alias", "short_content", "timestamp")
    search_fields = ("alias", "content", "room__name")
    list_filter = ("room", "timestamp")
    ordering = ("-timestamp",)

    @staticmethod
    def short_content(obj):
        return obj.content[:60]
