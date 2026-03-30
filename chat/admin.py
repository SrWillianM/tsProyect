from django.contrib import admin

from .models import Message, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ('name', 'created_at')
	search_fields = ('name',)
	ordering = ('name',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ('room', 'alias', 'short_content', 'timestamp')
	search_fields = ('alias', 'content', 'room__name')
	list_filter = ('room', 'timestamp')
	ordering = ('-timestamp',)

	@staticmethod
	def short_content(obj):
		return obj.content[:60]
