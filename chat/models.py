from django.conf import settings
from django.db import models


class ChannelKind(models.TextChoices):
    CHAT = "chat", "Chat"
    VOICE = "voice", "Voz"


class Room(models.Model):
    kind = models.CharField(
        max_length=10, choices=ChannelKind.choices, default=ChannelKind.CHAT
    )
    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.name}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    nickname = models.CharField(max_length=50)
    avatar = models.FileField(upload_to="profiles/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nickname


def default_nickname(user):
    base_name = (user.get_username() or "Usuario").strip()
    return base_name[:50] or "Usuario"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    alias = models.CharField(max_length=50)
    content = models.TextField(max_length=1000, blank=True, default="")
    attachment = models.FileField(upload_to="chat_attachments/", blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    attachment_mime = models.CharField(max_length=100, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["room", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        preview = (
            self.content[:30]
            if self.content
            else self.attachment_name or "archivo"
        )
        return f"[{self.room.name}] {self.alias}: {preview}"
