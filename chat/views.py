from django.shortcuts import render

from .models import Room


def index(request):
	rooms = Room.objects.all()
	return render(request, 'chat/index.html', {'rooms': rooms})


def room(request, room_name):
	rooms = Room.objects.all()
	return render(
		request,
		'chat/room.html',
		{
			'room_name': room_name,
			'rooms': rooms,
		},
	)
