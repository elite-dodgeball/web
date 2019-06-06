"""
.. module:: pullvideos
   :platform: Unix
   :synopsis: Gather video feed for a YouTube channel

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import re
import requests
import simplejson
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import dateparse

from client.models import Video


class YouTube(object):
	""" Gather video feed for a YouTube channel

	"""

	API_KEY = 'AIzaSyAwYBh_fCHOmuPw7k58SzTxOC82_56OPno'
	CHANNEL_ID = 'UCbockZ0USLRDDBmMq33kF3Q'
	API_VERSION = 'v3'
	SERVICE_NAME = 'youtube'
	SEARCH_BASE = 'https://www.googleapis.com/youtube/v3/search?part=id,snippet&key=%s&channelId=%s&maxResults=50&order=date&type=video'
	VIDEO_BASE = 'https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&key=%s&id=%s'

	def __init__(self):
		self.next_page = None

	def get_videos(self):
		while self.next_page is not False:
			items = self.get_page(self.next_page)
			for item in items:
				video = Video(
					youtube_id=item['id'],
					title=item['snippet']['title'],
					description=item['snippet']['description'],
					published_at=dateparse.parse_datetime(item['snippet']['publishedAt']),
					thumbnail=YouTube.get_thumbnail(item['snippet']['thumbnails']),
					duration=YouTube.extract_duration(item['contentDetails']['duration']))
				video.save()

	def get_page(self, page_token=None):
		if not isinstance(page_token, str) and page_token is not None:
			raise CommandError('pageToken value must be a string')

		url = self.SEARCH_BASE % (self.API_KEY, self.CHANNEL_ID)
		if page_token:
			url = '%s&pageToken=%s' % (url, page_token)

		req = requests.get(url)
		if req.status_code != 200:
			req.raise_for_status()

		data = simplejson.loads(req.text)
		self.next_page = data['nextPageToken'] if 'nextPageToken' in data else False

		ids = []
		for item in data['items']:
			ids.append(item['id']['videoId'])

		return self.get_batch(self.filter_batch(ids))

	def get_batch(self, batch):
		""" Get a bunch of ID'd videos and return them

		:param batch: List of IDs
		:type batch: list
		:returns: list

		"""
		if type(batch) is not list:
			raise CommandError('Batch must be a list of IDs')

		req = requests.get(self.VIDEO_BASE % (self.API_KEY, ','.join(batch)))
		if req.status_code != 200:
			req.raise_for_status()

		data = simplejson.loads(req.text)
		return data['items']

	@staticmethod
	def filter_batch(batch):
		""" Filter a batch of IDs of in and not in database

		:param batch: List of YouTube video IDs
		:type batch: list
		:returns: list

		"""
		if type(batch) is not list:
			raise CommandError('Batch must be a list of YouTube IDs')

		indb = []
		videos = Video.objects.filter(youtube_id__in=batch)
		for video in videos:
			indb.append(video.youtube_id)

		return list(set(batch) - set(indb))

	@staticmethod
	def in_database(yid):
		""" Check if a video is in the database

		:param yid: YouTube ID of the video
		:type yid: str
		:returns: bool

		"""
		try:
			Video.objects.get(pk=yid)
			return True
		except Video.DoesNotExist:
			return False

	@staticmethod
	def to_datetime(value):
		""" Turn a string into a datetime

		:param value: String to convert
		:type value: str
		:returns: datetime

		"""
		return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")

	@staticmethod
	def get_thumbnail(thumbs):
		""" Find the highest resolution thumbnail available

		:param thumbs: List of thumbnails from the YouTube API
		:type thumbs: list
		:returns: str

		"""
		if 'maxres' in thumbs:
			return thumbs['maxres']['url']
		if 'standard' in thumbs:
			return thumbs['standard']['url']
		if 'high' in thumbs:
			return thumbs['high']['url']
		if 'medium' in thumbs:
			return thumbs['medium']['url']
		if 'default' in thumbs:
			return thumbs['default']['url']
		raise CommandError('No thumbnails available')

	@staticmethod
	def extract_duration(value):
		""" Turn a YouTube API duration string into a more usable thing

		:param value: String to sift through
		:type value: str
		:returns: str

		"""
		if not isinstance(value, str):
			raise CommandError('Value must be a string')

		ret = '%s%s%s'
		hour = re.search(r'(\d+)H', value)
		minute = re.search(r'(\d+)M', value)
		second = re.search(r'(\d+)S', value)

		if hour and minute:
			minute = '%s:' % minute.group(1).zfill(2)
		elif minute:
			minute = '%s:' % minute.group(1)
		else:
			minute = '0:'

		hour = '%s:' % hour.group(1) if hour else ''
		second = second.group(1).zfill(2) if second else '00'

		return ret % (hour, minute, second)


class Command(BaseCommand):
	help = 'Gather video feed for the YouTube channel'

	def handle(self, *args, **options):
		YTV = YouTube()
		YTV.get_videos()

		self.stdout.write(self.style.SUCCESS('Successfully pulled YouTube videos'))
