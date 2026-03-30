import json
from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        alias = (data.get('alias') or 'Anónimo').strip()[:50]
        message = (data.get('message') or '').strip()[:1000]

        if not message:
            return

        timestamp = datetime.now(timezone.utc).isoformat()

        await self._save_message(self.room_name, alias, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'room': self.room_name,
                'alias': alias,
                'message': message,
                'timestamp': timestamp,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'room': event['room'],
                    'alias': event['alias'],
                    'message': event['message'],
                    'timestamp': event['timestamp'],
                }
            )
        )

    @sync_to_async
    def _save_message(self, room_name, alias, content):
        room, _ = Room.objects.get_or_create(name=room_name)
        Message.objects.create(room=room, alias=alias, content=content)
