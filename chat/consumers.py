import asyncio
import json
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):
    presence_lock = asyncio.Lock()
    room_presence = {}

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.alias = self._extract_alias()
        self.last_message_at = 0.0
        self.last_seen_at = time.monotonic()
        self._watchdog_task = None

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self._register_presence(self.room_name, self.alias)
        await self.send(
            text_data=json.dumps(
                {
                    'event': 'presence_snapshot',
                    'users': await self._get_presence_users(self.room_name),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'presence_event',
                'event': 'user_joined',
                'alias': self.alias,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        self._watchdog_task = asyncio.create_task(self._watch_inactivity())

    async def disconnect(self, close_code):
        if self._watchdog_task:
            self._watchdog_task.cancel()

        removed = await self._unregister_presence(self.room_name, self.alias)
        if removed:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'presence_event',
                    'event': 'user_left',
                    'alias': self.alias,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                },
            )

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        self.last_seen_at = time.monotonic()

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('event')
        if event_type == 'ping':
            await self.send(
                text_data=json.dumps(
                    {
                        'event': 'pong',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
            return

        # Rate-limit message broadcast per connection to reduce spam and CPU spikes.
        now_monotonic = time.monotonic()
        if now_monotonic - self.last_message_at < 0.5:
            await self.send(
                text_data=json.dumps(
                    {
                        'event': 'throttled',
                        'detail': 'Max 1 message every 500ms',
                    }
                )
            )
            return
        self.last_message_at = now_monotonic

        alias = (data.get('alias') or 'Anónimo').strip()[:50]
        message = (data.get('message') or '').strip()[:1000]

        if not message:
            return

        self.alias = alias

        saved = await self._save_message(self.room_name, alias, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': saved['id'],
                'alias': alias,
                'message': message,
                'timestamp': saved['timestamp'],
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'event': 'message',
                    'id': event['id'],
                    'alias': event['alias'],
                    'message': event['message'],
                    'timestamp': event['timestamp'],
                    'source': 'live',
                }
            )
        )

    async def presence_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'event': event['event'],
                    'alias': event['alias'],
                    'timestamp': event['timestamp'],
                }
            )
        )

    @sync_to_async
    def _save_message(self, room_name, alias, content):
        room, _ = Room.objects.get_or_create(name=room_name)
        msg = Message.objects.create(room=room, alias=alias, content=content)
        return {'id': msg.id, 'timestamp': msg.timestamp.isoformat()}

    def _extract_alias(self):
        raw = self.scope.get('query_string', b'').decode('utf-8', errors='ignore')
        params = parse_qs(raw)
        alias = (params.get('alias', ['Invitado'])[0] or 'Invitado').strip()[:50]
        return alias or 'Invitado'

    async def _register_presence(self, room_name, alias):
        async with self.presence_lock:
            room_map = self.room_presence.setdefault(room_name, {})
            room_map[alias] = room_map.get(alias, 0) + 1

    async def _unregister_presence(self, room_name, alias):
        async with self.presence_lock:
            room_map = self.room_presence.get(room_name, {})
            if alias not in room_map:
                return False

            room_map[alias] -= 1
            removed = False
            if room_map[alias] <= 0:
                del room_map[alias]
                removed = True

            if not room_map and room_name in self.room_presence:
                del self.room_presence[room_name]

            return removed

    async def _get_presence_users(self, room_name):
        async with self.presence_lock:
            room_map = self.room_presence.get(room_name, {})
            return sorted(room_map.keys())

    async def _watch_inactivity(self):
        try:
            while True:
                await asyncio.sleep(15)
                if time.monotonic() - self.last_seen_at > 45:
                    await self.close(code=4000)
                    return
        except asyncio.CancelledError:
            return
