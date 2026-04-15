import asyncio
import json

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings

from chat.models import Message, Room
from tsProject.asgi import application


@override_settings(
	CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
)
class ChatConsumerTests(TransactionTestCase):
	def test_websocket_broadcasts_and_persists_message(self):
		async def scenario():
			communicator_1 = WebsocketCommunicator(application, '/ws/chat/General/')
			communicator_2 = WebsocketCommunicator(application, '/ws/chat/General/')

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

			await communicator_1.send_json_to({'alias': 'Will', 'message': 'Hola equipo'})

			response_1 = await communicator_1.receive_json_from()
			response_2 = await communicator_2.receive_json_from()

			self.assertEqual(response_1['event'], 'message')
			self.assertEqual(response_1['alias'], 'Will')
			self.assertEqual(response_1['message'], 'Hola equipo')
			self.assertIn('timestamp', response_1)
			self.assertIn('id', response_1)
			self.assertEqual(response_1['source'], 'live')

			self.assertEqual(response_2['event'], 'message')
			self.assertEqual(response_2['alias'], 'Will')
			self.assertEqual(response_2['message'], 'Hola equipo')
			self.assertIn('timestamp', response_2)

			await communicator_1.disconnect()
			await communicator_2.disconnect()

		async_to_sync(scenario)()

		saved = Message.objects.get()
		self.assertEqual(saved.room.name, 'General')
		self.assertEqual(saved.alias, 'Will')
		self.assertEqual(saved.content, 'Hola equipo')

	def test_empty_message_is_ignored(self):
		async def scenario():
			communicator = WebsocketCommunicator(application, '/ws/chat/General/')
			connected, _ = await communicator.connect()
			self.assertTrue(connected)

			# Consume presence snapshot and own join event.
			await communicator.receive_json_from()
			await communicator.receive_json_from()

			await communicator.send_json_to({'alias': 'Will', 'message': '   '})

			with self.assertRaises(asyncio.TimeoutError):
				await asyncio.wait_for(communicator.receive_json_from(), timeout=0.2)

			await communicator.disconnect()

		async_to_sync(scenario)()

		self.assertEqual(Message.objects.count(), 0)

	def test_rate_limit_throttles_quick_messages(self):
		async def scenario():
			communicator = WebsocketCommunicator(application, '/ws/chat/FastRoom/')
			connected, _ = await communicator.connect()
			self.assertTrue(connected)

			# Consume presence snapshot and join events.
			await communicator.receive_json_from()
			await communicator.receive_json_from()

			await communicator.send_json_to({'alias': 'Will', 'message': 'Uno'})
			first_response = await communicator.receive_json_from()
			self.assertEqual(first_response['event'], 'message')

			await communicator.send_json_to({'alias': 'Will', 'message': 'Dos'})
			throttled_response = await communicator.receive_json_from()
			self.assertEqual(throttled_response['event'], 'throttled')

			await communicator.disconnect()

		async_to_sync(scenario)()

	def test_presence_join_and_leave_events(self):
		async def scenario():
			communicator_1 = WebsocketCommunicator(application, '/ws/chat/Presence/?alias=Ana')
			connected_1, _ = await communicator_1.connect()
			self.assertTrue(connected_1)

			snapshot_1 = await communicator_1.receive_json_from()
			self.assertEqual(snapshot_1['event'], 'presence_snapshot')
			self.assertIn('Ana', snapshot_1['users'])
			await communicator_1.receive_json_from()

			communicator_2 = WebsocketCommunicator(application, '/ws/chat/Presence/?alias=Luis')
			connected_2, _ = await communicator_2.connect()
			self.assertTrue(connected_2)

			snapshot_2 = await communicator_2.receive_json_from()
			self.assertEqual(snapshot_2['event'], 'presence_snapshot')
			await communicator_2.receive_json_from()

			join_event_for_1 = await communicator_1.receive_json_from()
			self.assertEqual(join_event_for_1['event'], 'user_joined')
			self.assertEqual(join_event_for_1['alias'], 'Luis')

			await communicator_2.disconnect()
			leave_event_for_1 = await communicator_1.receive_json_from()
			self.assertEqual(leave_event_for_1['event'], 'user_left')
			self.assertEqual(leave_event_for_1['alias'], 'Luis')

			await communicator_1.disconnect()

		async_to_sync(scenario)()


class ChatApiTests(TestCase):
	def setUp(self):
		self.room = Room.objects.create(name='General')
		for idx in range(35):
			Message.objects.create(room=self.room, alias='Bot', content=f'Mensaje {idx}')

	def test_messages_endpoint_returns_paginated_history(self):
		response = self.client.get('/api/rooms/General/messages/?limit=30&offset=0')

		self.assertEqual(response.status_code, 200)
		payload = json.loads(response.content)
		self.assertEqual(len(payload['messages']), 30)
		self.assertTrue(payload['has_more'])
		self.assertEqual(payload['messages'][0]['source'], 'history')

	def test_messages_endpoint_uses_offset(self):
		response = self.client.get('/api/rooms/General/messages/?limit=10&offset=30')

		self.assertEqual(response.status_code, 200)
		payload = json.loads(response.content)
		self.assertEqual(len(payload['messages']), 5)
		self.assertFalse(payload['has_more'])

	def test_messages_endpoint_404_for_missing_room(self):
		response = self.client.get('/api/rooms/Inexistente/messages/?limit=30&offset=0')
		self.assertEqual(response.status_code, 404)
