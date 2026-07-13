import asyncio
import json
import tempfile

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings

from chat.message_utils import create_message_payload, serialize_message
from chat.models import Message, Room, Sticker, default_nickname
from chat.forms import ProfileForm, RoomCreateForm
from tsProject.asgi import application
@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class ChatConsumerTests(TransactionTestCase):
    def test_websocket_broadcasts_and_persists_message(self):
        async def scenario():
            communicator_1 = WebsocketCommunicator(application, "/ws/chat/General/")
            communicator_2 = WebsocketCommunicator(application, "/ws/chat/General/")

            connected_1, _ = await communicator_1.connect()
            connected_2, _ = await communicator_2.connect()

            self.assertTrue(connected_1)
            self.assertTrue(connected_2)

            # Consume initial presence events.
            await communicator_1.receive_json_from()
            await communicator_1.receive_json_from()
            await communicator_2.receive_json_from()
            await communicator_2.receive_json_from()
            await communicator_1.receive_json_from()

            await communicator_1.send_json_to(
                {"alias": "Will", "message": "Hola equipo"}
            )

            response_1 = await communicator_1.receive_json_from()
            response_2 = await communicator_2.receive_json_from()

            self.assertEqual(response_1["event"], "message")
            self.assertEqual(response_1["alias"], "Will")
            self.assertEqual(response_1["message"], "Hola equipo")
            self.assertIn("timestamp", response_1)
            self.assertIn("id", response_1)
            self.assertEqual(response_1["source"], "live")

            self.assertEqual(response_2["event"], "message")
            self.assertEqual(response_2["alias"], "Will")
            self.assertEqual(response_2["message"], "Hola equipo")
            self.assertIn("timestamp", response_2)

            await communicator_1.disconnect()
            await communicator_2.disconnect()

        async_to_sync(scenario)()

        saved = Message.objects.get()
        self.assertEqual(saved.room.name, "General")
        self.assertEqual(saved.alias, "Will")
        self.assertEqual(saved.content, "Hola equipo")

    def test_empty_message_is_ignored(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, "/ws/chat/General/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Consume presence snapshot and own join event.
            await communicator.receive_json_from()
            await communicator.receive_json_from()

            await communicator.send_json_to({"alias": "Will", "message": "   "})

            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(communicator.receive_json_from(), timeout=0.2)

            await communicator.disconnect()

        async_to_sync(scenario)()

        self.assertEqual(Message.objects.count(), 0)

    def test_rate_limit_throttles_quick_messages(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, "/ws/chat/FastRoom/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Consume presence snapshot and join events.
            await communicator.receive_json_from()
            await communicator.receive_json_from()

            await communicator.send_json_to({"alias": "Will", "message": "Uno"})
            first_response = await communicator.receive_json_from()
            self.assertEqual(first_response["event"], "message")

            await communicator.send_json_to({"alias": "Will", "message": "Dos"})
            throttled_response = await communicator.receive_json_from()
            self.assertEqual(throttled_response["event"], "throttled")

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_presence_join_and_leave_events(self):
        async def scenario():
            communicator_1 = WebsocketCommunicator(
                application, "/ws/chat/Presence/?alias=Ana"
            )
            connected_1, _ = await communicator_1.connect()
            self.assertTrue(connected_1)

            snapshot_1 = await communicator_1.receive_json_from()
            self.assertEqual(snapshot_1["event"], "presence_snapshot")
            self.assertIn("Ana", snapshot_1["users"])
            await communicator_1.receive_json_from()

            communicator_2 = WebsocketCommunicator(
                application, "/ws/chat/Presence/?alias=Luis"
            )
            connected_2, _ = await communicator_2.connect()
            self.assertTrue(connected_2)

            snapshot_2 = await communicator_2.receive_json_from()
            self.assertEqual(snapshot_2["event"], "presence_snapshot")
            await communicator_2.receive_json_from()

            join_event_for_1 = await communicator_1.receive_json_from()
            self.assertEqual(join_event_for_1["event"], "user_joined")
            self.assertEqual(join_event_for_1["alias"], "Luis")

            await communicator_2.disconnect()
            leave_event_for_1 = await communicator_1.receive_json_from()
            self.assertEqual(leave_event_for_1["event"], "user_left")
            self.assertEqual(leave_event_for_1["alias"], "Luis")

            await communicator_1.disconnect()

        async_to_sync(scenario)()


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
)
class ChatApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="secret12345")
        self.client.force_login(self.user)
        self.room = Room.objects.create(name="General")
        for idx in range(35):
            Message.objects.create(
                room=self.room, alias="Bot", content=f"Mensaje {idx}"
            )

    def test_messages_endpoint_returns_paginated_history(self):
        response = self.client.get("/api/rooms/General/messages/?limit=30&offset=0")

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(len(payload["messages"]), 30)
        self.assertTrue(payload["has_more"])
        self.assertEqual(payload["messages"][0]["source"], "history")

    def test_messages_endpoint_uses_offset(self):
        response = self.client.get("/api/rooms/General/messages/?limit=10&offset=30")

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(len(payload["messages"]), 5)
        self.assertFalse(payload["has_more"])

    def test_messages_endpoint_404_for_missing_room(self):
        response = self.client.get("/api/rooms/Inexistente/messages/?limit=30&offset=0")
        self.assertEqual(response.status_code, 404)

    def test_attachment_upload_creates_message_and_returns_payload(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                gif_bytes = (
                    b"GIF89a"
                    b"\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
                    b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
                    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
                )
                uploaded_file = SimpleUploadedFile(
                    "imagen.gif",
                    gif_bytes,
                    content_type="image/gif",
                )

                response = self.client.post(
                    "/api/rooms/General/attachments/",
                    data={"message": "Mira esto", "attachment": uploaded_file},
                )

                self.assertEqual(response.status_code, 201)
                payload = json.loads(response.content)
                self.assertIn("message", payload)
                self.assertEqual(payload["message"]["message"], "Mira esto")
                self.assertTrue(payload["message"]["attachment_is_image"])
                self.assertTrue(Message.objects.filter(room=self.room).count() > 0)

    def test_stickers_endpoint_creates_and_lists_stickers(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                png_bytes = (
                    b"\x89PNG\r\n\x1a\n"
                    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                    b"\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x03\x00\x01"
                    b"+\tM\x84\x00\x00\x00\x00IEND\xaeB`\x82"
                )
                uploaded_file = SimpleUploadedFile(
                    "feliz.png",
                    png_bytes,
                    content_type="image/png",
                )

                create_response = self.client.post(
                    "/api/stickers/",
                    data={"name": "Feliz", "sticker": uploaded_file},
                )
                self.assertEqual(create_response.status_code, 201)

                list_response = self.client.get("/api/stickers/")
                self.assertEqual(list_response.status_code, 200)
                payload = json.loads(list_response.content)
                self.assertEqual(len(payload["stickers"]), 1)
                self.assertEqual(payload["stickers"][0]["name"], "Feliz")

    def test_attachment_endpoint_accepts_sticker_id(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                png_bytes = (
                    b"\x89PNG\r\n\x1a\n"
                    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                    b"\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x03\x00\x01"
                    b"+\tM\x84\x00\x00\x00\x00IEND\xaeB`\x82"
                )
                sticker = Sticker.objects.create(
                    owner=self.user,
                    name="Sticker Uno",
                    image=SimpleUploadedFile(
                        "uno.png", png_bytes, content_type="image/png"
                    ),
                )

                response = self.client.post(
                    "/api/rooms/General/attachments/",
                    data={"sticker_id": sticker.id, "message": ""},
                )

                self.assertEqual(response.status_code, 201)
                payload = json.loads(response.content)
                self.assertEqual(payload["message"]["sticker_id"], sticker.id)
                self.assertIn("sticker_url", payload["message"])

    def test_sticker_delete_endpoint_removes_owned_sticker(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                sticker = Sticker.objects.create(
                    owner=self.user,
                    name="Sticker Borrar",
                    image=SimpleUploadedFile(
                        "borrar.png",
                        b"\x89PNG\r\n\x1a\n",
                        content_type="image/png",
                    ),
                )

                response = self.client.delete(f"/api/stickers/{sticker.id}/")

                self.assertEqual(response.status_code, 200)
                self.assertFalse(Sticker.objects.filter(id=sticker.id).exists())


class ChatLogicUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="secret12345")
        self.room = Room.objects.create(name="General")

    def test_default_nickname_trims_and_limits_length(self):
        long_username = "  " + "x" * 60 + "  "
        user = User(username=long_username)

        nickname = default_nickname(user)

        self.assertEqual(len(nickname), 50)
        self.assertEqual(nickname, "x" * 50)

    def test_default_nickname_falls_back_to_usuario_when_username_is_blank(self):
        user = User(username="   ")

        self.assertEqual(default_nickname(user), "Usuario")

    def test_room_str_uses_human_readable_kind(self):
        room = Room.objects.create(name="Voz", kind="voice")

        self.assertEqual(str(room), "Voz: Voz")

    def test_room_create_form_rejects_invalid_kind(self):
        form = RoomCreateForm(data={"name": "  Sala  ", "kind": "invalid"})

        self.assertFalse(form.is_valid())
        self.assertIn("kind", form.errors)
        self.assertEqual(form.errors["kind"][0], "Tipo de canal inválido.")

    def test_profile_form_rejects_blank_nickname(self):
        form = ProfileForm(data={"nickname": "   "})

        self.assertFalse(form.is_valid())
        self.assertIn("nickname", form.errors)
        self.assertEqual(form.errors["nickname"][0], "El apodo es obligatorio.")

    def test_serialize_message_includes_attachment_and_sticker_fields(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                sticker = Sticker.objects.create(
                    owner=self.user,
                    name="Sticker Uno",
                    image=SimpleUploadedFile(
                        "sticker.png",
                        b"\x89PNG\r\n\x1a\n",
                        content_type="image/png",
                    ),
                )
                message = Message.objects.create(
                    room=self.room,
                    alias="Ana",
                    content="",
                    attachment=SimpleUploadedFile(
                        "foto.gif",
                        b"GIF89a",
                        content_type="image/gif",
                    ),
                    attachment_name="foto.gif",
                    attachment_mime="image/gif",
                    sticker=sticker,
                )

                payload = serialize_message(message, source="history")

                self.assertEqual(payload["alias"], "Ana")
                self.assertEqual(payload["source"], "history")
                self.assertEqual(payload["attachment_name"], "foto.gif")
                self.assertTrue(payload["attachment_is_image"])
                self.assertEqual(payload["sticker_id"], sticker.id)
                self.assertEqual(payload["sticker_name"], "Sticker Uno")

    def test_create_message_payload_creates_room_and_message(self):
        payload = create_message_payload(
            room_name="NuevaSala",
            alias="Luis",
            content="Hola equipo",
        )

        self.assertEqual(payload["alias"], "Luis")
        self.assertEqual(payload["message"], "Hola equipo")
        self.assertEqual(payload["source"], "live")
        self.assertTrue(Room.objects.filter(name="NuevaSala").exists())
        self.assertEqual(Message.objects.filter(room__name="NuevaSala").count(), 1)
