"""
.. module:: sitemaps
   :platform: Unix
   :synopsis: Contains the sitemaps

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from league import models as league

class TeamSitemap(Sitemap):
	changefreq = 'weekly'
	priority = 0.7

	def items(self):
		return list(league.Team.objects.filter(is_active=True)) + [None]

	def lastmod(self, item):
		return None

	def location(self, item):
		return reverse('teams', args=[item.pk]) if item else reverse('teams')

class EventSitemap(Sitemap):
	changefreq = 'daily'
	priority = 1.0

	def items(self):
		return list(league.Event.objects.all()) + [None]

	def lastmod(self, item):
		return item.date_updated if item else None

	def location(self, item):
		return reverse('events', args=[item.pk]) if item else reverse('events')
