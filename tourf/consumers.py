"""
.. module:: consumers
   :platform: Unix
   :synopsis: Contains the consumers
.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import simplejson as json

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class TourfConsumer(AsyncJsonWebsocketConsumer):
	async def connect(self):
		self.event_id = self.scope['url_route']['kwargs']['event_id']
		self.event_group_name = 'event_%s' % self.event_id

		await self.channel_layer.group_add(
			self.event_group_name,
			self.channel_name
		)

		await self.accept()

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.event_group_name,
			self.channel_name
		)

	async def receive(self, text_data):
		text_data_json = json.loads(text_data)

		await self.send(text_data=json.dumps({
			'message': text_data_json['message'],
		}))

	async def event_update(self, event):
		await self.send_json({
			'type': 'event',
			'data': event['data'],
		})

	async def game_update(self, event):
		await self.send_json({
			'type': 'game',
			'data': event['data'],
		})

	async def robin_update(self, event):
		await self.send_json({
			'type': 'robin',
			'data': event['data'],
		})

	async def bracket_update(self, event):
		await self.send_json({
			'type': 'bracket',
			'data': event['data'],
		})

	async def stats_update(self, event):
		await self.send_json({
			'type': 'stats',
			'data': event['data'],
		})
