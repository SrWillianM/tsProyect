import asyncio

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from chat.models import Message
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

			await communicator_1.send_json_to({'alias': 'Will', 'message': 'Hola equipo'})

			response_1 = await communicator_1.receive_json_from()
			response_2 = await communicator_2.receive_json_from()

			self.assertEqual(response_1['room'], 'General')
			self.assertEqual(response_1['alias'], 'Will')
			self.assertEqual(response_1['message'], 'Hola equipo')
			self.assertIn('timestamp', response_1)

			self.assertEqual(response_2['room'], 'General')
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

			await communicator.send_json_to({'alias': 'Will', 'message': '   '})

			with self.assertRaises(asyncio.TimeoutError):
				await asyncio.wait_for(communicator.receive_json_from(), timeout=0.2)

			await communicator.disconnect()

		async_to_sync(scenario)()

		self.assertEqual(Message.objects.count(), 0)
