from django.db import models


class Room(models.Model):
	name = models.CharField(max_length=100, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Message(models.Model):
	room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
	alias = models.CharField(max_length=50)
	content = models.TextField(max_length=1000)
	timestamp = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['timestamp']

	def __str__(self):
		return f'[{self.room.name}] {self.alias}: {self.content[:30]}'
