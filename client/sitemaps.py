"""
.. module:: sitemaps
   :platform: Unix
   :synopsis: Contains the sitemaps

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from client import models as client

class FlatSitemap(Sitemap):
	changefreq = 'monthly'
	priority = 0.4

	def items(self):
		return ['press', 'contact', 'champions', 'schedule']

	def lastmod(self, item):
		return None

	def location(self, item):
		return reverse(item)

class StaticSitemap(Sitemap):
	changefreq = 'monthly'
	priority = 0.3

	def items(self):
		return ['rules', 'rules.referee', 'rules.regulations', 'about', 'about.history', 'about.leadership']

	def lastmod(self, item):
		return None

	def location(self, item):
		item = item.split('.')
		return reverse(item[0], args=[item[1]]) if len(item) > 1 else reverse(item[0])

class PostSitemap(Sitemap):
	changefreq = 'daily'
	priority = 0.7

	def items(self):
		return list(client.Post.objects.all()) + [None]

	def lastmod(self, item):
		return item.date_updated if item else None

	def location(self, item):
		return reverse('posts', args=[item.pk]) if item else reverse('posts')

class VideoSitemap(Sitemap):
	changefreq = 'daily'
	priority = 0.6

	def items(self):
		return list(client.Video.objects.all()) + [None]

	def lastmod(self, item):
		return item.published_at if item else None

	def location(self, item):
		return reverse('videos', args=[item.pk]) if item else reverse('videos')

class GallerySitemap(Sitemap):
	changefreq = 'weekly'
	priority = 0.5

	def items(self):
		return list(client.Gallery.objects.all()) + [None]

	def lastmod(self, item):
		return item.date_updated if item else None

	def location(self, item):
		return reverse('gallery', args=[item.pk]) if item else reverse('gallery')
