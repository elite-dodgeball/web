"""
.. module:: admin
   :platform: Unix
   :synopsis: ModelAdmin registration and custom round-robin page

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import simplejson as json

from django.contrib import admin
from django.conf.urls import url
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse

from client import models as client

admin.site.index_template = 'admin/index-details.html'

@admin.register(client.Press)
class PressAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
	)
	list_display = (
		'title',
		'link',
		'screen',
		'date_created',
	)

@admin.register(client.Director)
class DirectorAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'title',
		'email_address',
		'image',
		'info',
	)

@admin.register(client.Contact)
class ContactAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
	)
	list_display = (
		'name',
		'email',
		'subject',
		'body',
		'director',
		'date_created',
	)
	list_display_links = (
		'name',
		'email',
	)
	ordering = [
		'-date_created',
	]
	search_fields = [
		'name',
		'email',
	]
	list_select_related = (
		'director',
	)

@admin.register(client.Post)
class PostAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
		'date_updated',
	)
	list_display = (
		'title',
		'blurb',
		'header',
		'featured',
		'date_created',
		'date_updated',
	)
	ordering = [
		'-date_updated',
	]
	search_fields = [
		'title',
	]

@admin.register(client.Video)
class VideoAdmin(admin.ModelAdmin):
	list_display = (
		'title',
		'event',
		'youtube_id',
		'published_at',
		'thumbnail',
		'duration',
	)
	ordering = [
		'-published_at',
	]
	search_fields = [
		'title',
		'event__title',
	]
	list_select_related = (
		'event',
	)

@admin.register(client.Gallery)
class GalleryAdmin(admin.ModelAdmin):
	readonly_fields = (
		'image_count',
		'date_created',
		'date_updated',
	)
	list_display = (
		'title',
		'event',
		'image_count',
		'date_created',
		'date_updated',
	)
	ordering = [
		'-date_created',
	]
	search_fields = [
		'title',
		'event__title',
	]
	list_select_related = (
		'event',
	)

@admin.register(client.Image)
class ImageAdmin(admin.ModelAdmin):
	readonly_fields = (
		'width',
		'height',
		'date_created',
	)
	list_display = (
		'id',
		'path',
		'gallery',
		'width',
		'height',
		'date_created',
	)
	ordering = [
		'-date_created',
	]
	search_fields = [
		'gallery__title',
	]
	list_select_related = (
		'gallery',
	)

@admin.register(client.ImageTag)
class ImageTagAdmin(admin.ModelAdmin):
	list_display = (
		'image',
		'player',
	)
	search_fields = [
		'player__name',
	]
	list_select_related = (
		'image',
		'player',
	)
