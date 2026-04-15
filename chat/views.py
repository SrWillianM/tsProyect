import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Room


def index(request):
	rooms = Room.objects.only('id', 'name').all()
	return render(request, 'chat/index.html', {'rooms': rooms})


def room(request, room_name):
	rooms = Room.objects.only('id', 'name').all()
	return render(
		request,
		'chat/room.html',
		{
			'room_name': room_name,
			'rooms': rooms,
		},
	)


def _parse_pagination(query_dict):
	try:
		limit = int(query_dict.get('limit', 30))
		offset = int(query_dict.get('offset', 0))
	except (TypeError, ValueError):
		return None, None

	# Hard limit to avoid excessive memory/CPU usage per request.
	limit = max(1, min(limit, 100))
	offset = max(0, offset)
	return limit, offset


@require_http_methods(['GET', 'POST'])
def api_rooms(request):
	if request.method == 'GET':
		rooms = list(
			Room.objects.only('id', 'name', 'created_at').values('id', 'name', 'created_at')
		)
		return JsonResponse({'rooms': rooms})

	if not request.user.is_authenticated:
		return JsonResponse({'error': 'Authentication required'}, status=401)

	try:
		payload = json.loads(request.body or '{}')
	except json.JSONDecodeError:
		return JsonResponse({'error': 'Invalid JSON body'}, status=400)

	name = (payload.get('name') or '').strip()[:100]
	if not name:
		return JsonResponse({'error': 'Room name is required'}, status=400)

	room, created = Room.objects.get_or_create(name=name, defaults={'created_by': request.user})
	if not created and room.created_by_id is None:
		room.created_by = request.user
		room.save(update_fields=['created_by'])

	return JsonResponse(
		{
			'room': {
				'id': room.id,
				'name': room.name,
				'created_at': room.created_at,
				'created_by_id': room.created_by_id,
			},
			'created': created,
		}
	)


@require_http_methods(['GET', 'DELETE'])
def api_room_detail(request, room_id):
	room = get_object_or_404(Room.objects.only('id', 'name', 'created_at', 'created_by'), pk=room_id)

	if request.method == 'GET':
		return JsonResponse(
			{
				'room': {
					'id': room.id,
					'name': room.name,
					'created_at': room.created_at,
					'created_by_id': room.created_by_id,
				}
			}
		)

	if not request.user.is_authenticated:
		return JsonResponse({'error': 'Authentication required'}, status=401)

	if not (request.user.is_superuser or room.created_by_id == request.user.id):
		return JsonResponse({'error': 'Only room owner can delete this room'}, status=403)

	room.delete()
	return JsonResponse({'deleted': True})


@require_http_methods(['GET'])
def api_room_messages(request, room_name):
	limit, offset = _parse_pagination(request.GET)
	if limit is None:
		return JsonResponse({'error': 'Invalid limit/offset'}, status=400)

	queryset = (
		Room.objects.filter(name=room_name)
		.only('id')
		.first()
	)
	if queryset is None:
		return JsonResponse({'error': 'Room not found'}, status=404)

	rows = list(
		queryset.messages.select_related('room')
		.only('id', 'alias', 'content', 'timestamp', 'room__name')
		.order_by('-timestamp')[offset : offset + limit + 1]
	)

	has_more = len(rows) > limit
	rows = rows[:limit]
	rows.reverse()

	messages = [
		{
			'id': msg.id,
			'alias': msg.alias,
			'message': msg.content,
			'timestamp': msg.timestamp.isoformat(),
			'source': 'history',
		}
		for msg in rows
	]

	return JsonResponse(
		{
			'room': room_name,
			'limit': limit,
			'offset': offset,
			'has_more': has_more,
			'messages': messages,
		}
	)
