"""
.. module:: models
   :platform: Unix
   :synopsis: Contains the models for the Elite site

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import re
import html
import uuid
import datetime

from django.db import models
from django.conf import settings
from django.core import validators
from django.dispatch import receiver
from django.core.mail import send_mail
from django.db.models.query import QuerySet
from django.contrib.postgres.search import SearchVector

from ckeditor.fields import RichTextField

from league import models as league
from elite import serializer


class Press(models.Model):
	""" Press model

	"""
	def screen_path(self, filename):
		""" Return the screen's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'press/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the post's title

		:returns: str

		"""
		return self.title

	title = models.CharField(max_length=255)
	link = models.URLField()
	screen = models.ImageField(upload_to=screen_path)
	date_created = models.DateTimeField(auto_now_add=True, db_index=True)


class Director(models.Model):
	""" Director model

	"""
	def image_path(self, filename):
		""" Return the image's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'directors/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the post's title

		:returns: str

		"""
		return '%s - %s' % (self.name, self.title)

	name = models.CharField(max_length=255)
	title = models.CharField(max_length=255)
	email_address = models.EmailField()
	image = models.ImageField(upload_to=image_path)
	info = models.TextField()


class Contact(models.Model):
	""" Contact model

	"""
	def send_email(self, to_addr=None):
		""" Send the contact information to an email address

		:param to_addr: The email address to send to
		:type to_addr: str
		:returns: int

		"""
		if to_addr:
			if not isinstance(to_addr, str):
				raise TypeError('to_addr must be a string')

			try:
				validators.validate_email(to_addr)
			except:
				raise ValueError('to_addr must be a valid email address')
		else:
			to_addr = settings.DEFAULT_FROM_EMAIL

		fdate = self.date_created.strftime('%B %d, %Y at %I:%M:%S %p')

		return send_mail(
			subject='Elite Dodgeball Contact Form - %s' % self.subject,
			message='%s\r\n\r\n%s (%s) said:\r\n\r\n%s' % (
				fdate, self.name, self.email, self.body),
			from_email='%s <%s>' % (self.name, self.email),
			recipient_list=[to_addr],
			fail_silently=False if settings.DEBUG else True,
			html_message='%s<br /><br />%s (<a href="mailto:%s?%s">%s</a>) said:<br /><br />%s' % (
				fdate, self.name, self.email, parse.urlencode(query={
					'subject': 'RE: Elite Dodgeball Contact Form - %s' % self.subject
				}), self.email, html.escape(s=self.body).replace('\n', '<br />')))

	def __str__(self):
		""" Return the contact missive's string representation

		:returns: str

		"""
		return '%s - %s (%s)' % (self.name, self.subject, self.date_created)

	name = models.CharField(max_length=255)
	email = models.EmailField()
	director = models.ForeignKey(Director, on_delete=models.SET_NULL, blank=True, null=True)
	subject = models.CharField(max_length=255)
	body = models.TextField()
	date_created = models.DateTimeField(auto_now_add=True, db_index=True)


class Post(models.Model):
	""" Post model

	"""
	@staticmethod
	def search(query):
		""" Search posts

		:param query: Query to search for
		:type query: str
		:returns: list

		"""
		try:
			return list(Post.objects.annotate(
				search=SearchVector('title') + SearchVector('body') + SearchVector('blurb'),
			).filter(search=query).order_by('date_created'))
		except Post.DoesNotExist:
			return []

	def header_path(self, filename):
		""" Return the header's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'posts/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the post's title

		:returns: str

		"""
		return self.title

	title = models.CharField(max_length=255, db_index=True)
	body = RichTextField()
	blurb = models.CharField(max_length=255)
	header = models.ImageField(upload_to=header_path)
	featured = models.BooleanField(db_index=True, default=False)
	date_created = models.DateTimeField(auto_now_add=True, db_index=True)
	date_updated = models.DateTimeField(auto_now=True)


class Video(models.Model):
	""" YouTube video model

	"""
	@staticmethod
	def search(query):
		""" Search videos

		:param query: Query to search for
		:type query: str
		:returns: list

		"""
		try:
			return list(Video.objects.annotate(
				search=SearchVector('title') + SearchVector('description') + SearchVector('event__title'),
			).filter(search=query).order_by('published_at'))
		except Video.DoesNotExist:
			return []

	@staticmethod
	def paragraphize(string, wrap=True, blank=False):
		""" Turn a string into HTML-formatted paragraphs

		:param string: The string to break up
		:type string: str
		:param wrap: Wrap the lines in paragraph tags
		:type wrap: bool
		:param blank: Force blank lines into paragraphs
		:type blank: bool
		:returns: list

		"""
		if not isinstance(string, str):
			raise TypeError('String to paragraphize must be a string')

		ret = []
		lines = string.split('\n')

		for line in lines:
			line = line.strip()

			if blank or line:
				if wrap:
					ret.append('<p>%s</p>' % line)
				else:
					ret.append(line)
		return ret

	@staticmethod
	def get_videos(event_id=None, page=None, per_page=10):
		""" Get all the videos, perhaps for a particular event

		:param event_id: ID of the event to get for
		:type event_id: int
		:param page: Page to start at for retrieval (None for all)
		:type page: int
		:param per_page: How many per page for calculations
		:type per_page: int
		:returns: list

		"""
		if page is not None:
			try:
				page = int(page) - 1
				per_page = int(per_page)
			except ValueError:
				raise TypeError('page and per_page parameters must be integers')

			if page < 0 or per_page < 1:
				raise ValueError('page and per_page must be at least 1')

		ret = []
		vids = []

		if event_id:
			vids = Video.objects.filter(event_id__exact=event_id).order_by('-published_at')
		else:
			vids = Video.objects.order_by('-published_at')

		if page is not None:
			offset = page * per_page
			vids = vids[offset : offset+per_page]

		for vid in vids:
			vid.description = Video.paragraphize(vid.description, False, True)
			ret.append(vid)

		return ret

	def __str__(self):
		""" Return the video's title

		:returns: str

		"""
		return self.title

	title = models.CharField(max_length=255, db_index=True)
	event = models.ForeignKey(league.Event, on_delete=models.SET_NULL, blank=True, null=True)
	youtube_id = models.CharField(max_length=255, unique=True)
	description = models.TextField()
	published_at = models.DateTimeField(db_index=True)
	thumbnail = models.URLField()
	duration = models.CharField(max_length=255)


class Gallery(models.Model):
	""" Gallery model

	"""
	def images(self):
		""" Get all of the images

		:returns: QuerySet

		"""
		return Image.objects.filter(gallery=self).order_by('date_created')

	@staticmethod
	def get_galleries(event_id=None):
		""" Get all of the galleries

		:param event_id: ID of the event to get galleries for
		:type event_id: int
		:returns: list

		"""
		ret = []
		galleries = []

		if event_id:
			galleries = Gallery.objects.filter(event__exact=event_id).order_by('date_created')
		else:
			galleries = Gallery.objects.order_by('-date_created')

		for gallery in galleries:
			ret.append({
				'gallery': gallery,
				'cover': Image.objects.filter(gallery__exact=gallery.pk).first(),
			})

		return ret

	def __str__(self):
		""" Return the gallery's title

		:returns: str

		"""
		return self.title

	title = models.CharField(max_length=255, db_index=True)
	event = models.ForeignKey(league.Event, on_delete=models.SET_NULL, blank=True, null=True)
	image_count = models.PositiveSmallIntegerField(default=0)
	date_created = models.DateTimeField(auto_now_add=True, db_index=True)
	date_updated = models.DateTimeField(auto_now=True, db_index=True)


class Image(models.Model):
	""" Image model

	"""
	def save(self, *args, **kwargs):
		""" Override the save method

		"""
		from PIL import Image as PIL_Image

		image_path = '%s/%s' % (settings.MEDIA_ROOT, self.path)
		img = PIL_Image.open(image_path)

		self.width = img.size[0]
		self.height = img.size[1]

		super().save(*args, **kwargs)

		for thumb_name, thumb_size in THUMBNAIL_SIZES.items():
			if self.width <= thumb_size[0] and self.height <= thumb_size[1]:
				thumb_image = img.copy()
			else:
				min_side = min(self.width, self.height)

				resize_x_start = (self.width - min_side) / 2
				resize_x_end = resize_x_start + min_side

				resize_y_start = (self.height - min_side) / 2
				resize_y_end = resize_y_start + min_side

				thumb_image = img.resize(thumb_size, resample=PIL_Image.HAMMING, box=(
					max(resize_x_start - (resize_x_start % 1), 0),
					max(resize_y_start - (resize_y_start % 1), 0),
					min(resize_x_end - (resize_x_end % 1), self.width),
					min(resize_y_end - (resize_y_end % 1), self.height),
				))

			thumb_image.save('%s.%s' % (image_path, thumb_name), 'JPEG', quality=90)

			thumb_image.close()

		img.close()

	def delete(self, *args, **kwargs):
		""" Override the delete method

		"""
		import os

		super().delete(*args, **kwargs)

		for thumb_name in THUMBNAIL_SIZES.keys():
			image_path = '%s/%s.%s' % (settings.MEDIA_ROOT, self.path, thumb_name)

			if os.path.isfile(image_path):
				os.remove(image_path)

		os.remove('%s/%s' % (settings.MEDIA_ROOT, self.path))

	def image_path(self, filename):
		""" Return the image's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'gallery/%s/%s.%s' % (
			str(self.gallery.pk), uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the image's path

		:returns: str

		"""
		return '%s - %s' % (self.gallery, self.pk)

	path = models.ImageField(height_field='height', width_field='width', upload_to=image_path)
	width = models.PositiveSmallIntegerField()
	height = models.PositiveSmallIntegerField()
	gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE)
	date_created = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		unique_together = (
			('path', 'gallery',),
		)


class ImageTag(models.Model):
	""" Image tag model

	"""
	def __str__(self):
		""" Return the tag's compound IDs

		:returns: str

		"""
		return '%s - %s' % (self.image, self.player)

	image = models.ForeignKey(Image, on_delete=models.CASCADE)
	player = models.ForeignKey(league.Player, on_delete=models.CASCADE)

	class Meta:
		unique_together = (
			('image', 'player',),
		)

@receiver(models.signals.post_save, sender=Image)
def add_gallery_count(**kwargs):
	""" Increase the gallery's number of images count if being created

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	if kwargs.get('created'):
		gallery = Gallery.objects.get(pk=kwargs.get('instance').gallery.pk)
		gallery.image_count = models.F('image_count') + 1
		gallery.save()

@receiver(models.signals.post_delete, sender=Image)
def sub_gallery_count(**kwargs):
	""" Decrease the gallery's number of images count

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	gallery = Gallery.objects.get(pk=kwargs.get('instance').gallery.pk)
	gallery.image_count = models.F('image_count') - 1
	gallery.save()

def get_extension(filename):
	""" Return the extension to a file

	:param filename: Filename to get the extension from
	:type filename: str
	:returns: str

	"""
	if not isinstance(filename, str):
		raise TypeError('Filename must be a string: %s' % type(filename))
	try:
		return re.search(r'\.([a-zA-Z]+)$', filename).group(0)[1:].lower()
	except Exception as err:
		raise ValueError('Could not find an extension in the filename: %s' % err)


class ClientSerializer(serializer.Serializer):
	@staticmethod
	def video(video):
		return {
			'id': video.pk,
			'title': video.title,
			'youtube_id': video.youtube_id,
			'duration': video.duration,
			'description': video.description,
			'thumbnail': video.thumbnail,
		} if video else None


class Search(object):
	""" Gather up search results

	"""
	def __init__(self):
		pass

	@staticmethod
	def _make_things(current, data):
		""" Take a list of objects and turn it into a list of sortable dicts

		:param current: Current list of things
		:type current: dict
		:param data: List of objects
		:type data: list
		:returns: list

		"""
		if not isinstance(current, dict):
			raise TypeError('Current must be a dict')
		if not isinstance(data, (list, tuple)):
			raise TypeError('Data must be a list or tuple')

		for datum in data:
			try:
				obj = datum[-1:][0]
			except IndexError:
				continue

			toj = type(obj)

			if toj in current:
				continue

			datum.pop()

			if hasattr(obj, 'registration_open'):
				current[toj] = {'date': obj.datetime, 'object': obj, 'type': 'event'}
			elif hasattr(obj, 'blurb'):
				current[toj] = {'date': obj.date_created, 'object': obj, 'type': 'post'}
			elif hasattr(obj, 'youtube_id'):
				current[toj] = {'date': obj.published_at, 'object': obj, 'type': 'video'}

		return current

	@staticmethod
	def query(query):
		""" Run a search query

		:param query: Query search string
		:type query: str

		"""
		if not isinstance(query, str):
			query = str(query)

		posts = Post.search(query)
		events = league.Event.search(query)
		videos = Video.search(query)

		things = Search._make_things({}, [posts, events, videos])
		results = []

		while things:
			recent = things[max(things, key=lambda key: things[key]['date'])]
			results.append(recent)
			del things[type(recent['object'])]
			things = Search._make_things(things, [posts, events, videos])

		return results


THUMBNAIL_SIZES = {
	'medium': (306, 306),
	'small': (176, 176),
}
