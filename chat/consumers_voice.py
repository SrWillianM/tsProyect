"""
VoiceSignalingConsumer - Maneja la señalización WebRTC para chat de voz

Este consumidor:
- Gestiona la presencia de usuarios en voz por sala (usando Redis)
- Recibe y reenvía señales SDP (offer/answer)
- Recibe y reenvía candidatos ICE
- Notifica cuando un usuario entra/sale del chat de voz
"""

import asyncio
import json
from datetime import datetime, timezone

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import redis

from .models import ChannelKind, Profile, Room


class VoiceSignalingConsumer(AsyncWebsocketConsumer):
    """
    Consumidor WebSocket para señalización de voz (WebRTC)

    Maneja:
    - join: Usuario se une al chat de voz de una sala
    - leave: Usuario sale del chat de voz
    - signal: Intercambio de señales WebRTC (offer/answer/ice-candidate)
    - mute_status: Notificación de mute/unmute
    """

    # Conexión a Redis para presencia centralizada
    _redis = None

    @classmethod
    def get_redis(cls):
        """Obtener conexión Redis (singleton)"""
        if cls._redis is None:
            cls._redis = redis.Redis(
                host="localhost", port=6379, db=1, decode_responses=True
            )
        return cls._redis

    def _get_presence_key(self, room_name):
        return f"voice_presence:{room_name}"

    async def connect(self):
        # Extraer parámetros de la URL
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        if not await self._is_voice_room(self.room_name):
            await self.close()
            return
        self.room_group_name = f"voice_{self.room_name}"
        self.alias = await self._resolve_alias()
        self.is_voice = self.scope["query_string"].decode().find("voice=true") >= 0

        if not self.is_voice:
            # No es una conexión de voz, rechazar
            await self.close()
            return

        # Unirse al grupo de la sala
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Registrar en presencia de voz
        await self._register_voice_user(self.room_name, self.alias)

        # Enviar lista actual de usuarios en voz
        await self.send_voice_users()

        # Notificar a otros usuarios
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "voice_user_joined",
                "alias": self.alias,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"[VoiceSignaling] {self.alias} se unió a voz en sala {self.room_name}")

    async def disconnect(self, close_code):
        # Salir del grupo
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Desregistrar de presencia de voz
        await self._unregister_voice_user(self.room_name, self.alias)

        # Notificar a otros usuarios
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "voice_user_left",
                "alias": self.alias,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"[VoiceSignaling] {self.alias} salió de voz en sala {self.room_name}")

    async def receive(self, text_data):
        """Manejar mensajes recibidos del cliente"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get("event")

        if event_type == "voice_signal":
            await self._handle_voice_signal(data)
        elif event_type == "mute_status":
            await self._handle_mute_status(data)

    async def _handle_voice_signal(self, data):
        """Reenviar señal WebRTC al destinatario"""
        signal_type = data.get("type")
        target_alias = data.get("to")

        # Reenviar la señal al grupo (todos la reciben, pero solo el destinatario la procesa)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_signal",
                "from": self.alias,
                "to": target_alias,
                "signal_type": signal_type,
                "signal": data.get("signal"),
            },
        )

    async def _handle_mute_status(self, data):
        """Actualizar estado de mute del usuario"""
        muted = data.get("muted", False)
        await self._update_voice_user_muted(self.room_name, self.alias, muted)

    # Handlers para mensajes del grupo (enviados por otros usuarios)

    async def voice_user_joined(self, event):
        """Notificar que un usuario se unió a voz"""
        if event["alias"] != self.alias:
            await self.send(
                text_data=json.dumps(
                    {
                        "event": "user_joined_voice",
                        "from": event["alias"],
                        "timestamp": event["timestamp"],
                    }
                )
            )

    async def voice_user_left(self, event):
        """Notificar que un usuario salió de voz"""
        if event["alias"] != self.alias:
            await self.send(
                text_data=json.dumps(
                    {
                        "event": "user_left_voice",
                        "from": event["alias"],
                        "timestamp": event["timestamp"],
                    }
                )
            )

    async def webrtc_signal(self, event):
        """Reenviar señal WebRTC al cliente"""
        # Solo enviar si el mensaje es para este usuario
        if event.get("to") == self.alias or event.get("to") is None:
            await self.send(
                text_data=json.dumps(
                    {
                        "event": "signal",
                        "type": event.get("signal_type"),
                        "from": event.get("from"),
                        "signal": event.get("signal"),
                    }
                )
            )

    # Métodos de presencia (usando Redis)

    async def _register_voice_user(self, room_name, alias):
        """Registrar usuario en presencia de voz (Redis)"""
        r = self.get_redis()
        key = self._get_presence_key(room_name)
        user_data = json.dumps(
            {
                "connected": True,
                "muted": True,  # Por defecto muteado hasta que active el micrófono
            }
        )
        r.hset(key, alias, user_data)
        print(
            f"[VoiceSignaling] Usuario {alias} registrado en presencia de sala {room_name}"
        )

    async def _unregister_voice_user(self, room_name, alias):
        """Desregistrar usuario de presencia de voz (Redis)"""
        r = self.get_redis()
        key = self._get_presence_key(room_name)
        r.hdel(key, alias)
        print(
            f"[VoiceSignaling] Usuario {alias} desregistrado de presencia de sala {room_name}"
        )

    async def _update_voice_user_muted(self, room_name, alias, muted):
        """Actualizar estado de mute (Redis)"""
        r = self.get_redis()
        key = self._get_presence_key(room_name)
        user_data = r.hget(key, alias)
        if user_data:
            data = json.loads(user_data)
            data["muted"] = muted
            r.hset(key, alias, json.dumps(data))

    async def send_voice_users(self):
        """Enviar lista de usuarios en voz al cliente que se conecta"""
        r = self.get_redis()
        key = self._get_presence_key(self.room_name)

        users = []
        all_users = r.hgetall(key)
        for alias, user_data in all_users.items():
            data = json.loads(user_data)
            users.append({"alias": alias, "muted": data.get("muted", False)})

        print(f"[VoiceSignaling] Enviando lista de usuarios en voz: {users}")
        await self.send(
            text_data=json.dumps(
                {
                    "event": "voice_users",
                    "users": users,
                }
            )
        )

    async def _resolve_alias(self):
        user = self.scope.get("user")
        if user and user.is_authenticated:
            nickname = await self._get_profile_nickname(user.id)
            return nickname or user.get_username() or "Anonymous"

        return self._get_query_param("alias", "Anonymous")

    @database_sync_to_async
    def _is_voice_room(self, room_name):
        return Room.objects.filter(name=room_name, kind=ChannelKind.VOICE).exists()

    @database_sync_to_async
    def _get_profile_nickname(self, user_id):
        return (
            Profile.objects.filter(user_id=user_id)
            .values_list("nickname", flat=True)
            .first()
        )

    def _get_query_param(self, key, default=None):
        """Extraer parámetro de query string"""
        query_string = self.scope.get("query_string", b"").decode()
        params = dict(
            param.split("=") for param in query_string.split("&") if "=" in param
        )
        return params.get(key, default)
