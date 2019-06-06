"""
.. module:: admin
   :platform: Unix
   :synopsis: ModelAdmin registration

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.contrib import admin

from tourf import models as tourf

@admin.register(tourf.Bracket)
class BracketAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
		'date_updated',
	)
	list_display = (
		'id',
		'bracket_type',
		'division',
		'event',
	)
	ordering = [
		'-event_division__event__datetime',
		'event_division__event__title',
		'event_division__division__name',
	]
	search_fields = [
		'event_division__division__name',
		'event_division__event__title',
	]
	list_select_related = (
		'event_division__division',
		'event_division__event',
	)

	def division(self, obj):
		return obj.event_division.division.name

	def event(self, obj):
		return obj.event_division.event.title

@admin.register(tourf.Game)
class GameAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
		'date_updated',
	)
	list_display = (
		'id',
		'bracket',
		'round_number',
		'game_number',
		'top_team',
		'top_wins',
		'bottom_team',
		'bottom_wins',
	)
	ordering = [
		'bracket',
		'round_number',
		'game_number',
	]
	search_fields = [
		'bracket__event_division__division__name',
		'bracket__event_division__event__title',
	]
	list_select_related = (
		'bracket',
		'top_team',
		'bottom_team',
	)

@admin.register(tourf.LivePlayer)
class LivePlayerAdmin(admin.ModelAdmin):
	list_display = (
		'game',
		'event_division_team_player',
		'is_playing',
		'is_in',
	)
	ordering = [
		'game',
		'event_division_team_player__event_division_team',
		'-is_playing',
		'-is_in',
	]
	list_select_related = (
		'game',
		'event_division_team_player',
	)
