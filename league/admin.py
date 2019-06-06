"""
.. module:: admin
   :platform: Unix
   :synopsis: ModelAdmin registration and custom round-robin page

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import simplejson as json

from django.urls import path
from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from league import models as league

@admin.register(league.Season)
class SeasonAdmin(admin.ModelAdmin):
	list_display = (
		'year',
	)
	ordering = [
		'-year',
	]

@admin.register(league.Region)
class RegionAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'is_active',
	)
	ordering = [
		'-is_active',
		'name',
	]

@admin.register(league.Division)
class DivisionAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'is_active',
		'is_primary',
	)
	ordering = [
		'-is_active',
		'-is_primary',
		'name',
	]

@admin.register(league.Team)
class TeamAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'region',
		'email_address',
		'location',
		'website',
		'twitter',
		'instagram',
		'youtube',
		'facebook',
		'logo',
		'cover',
		'is_active',
	)
	search_fields = [
		'name',
	]
	ordering = [
		'region__name',
		'name',
	]
	list_select_related = (
		'region',
	)

@admin.register(league.Player)
class PlayerAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'number',
		'email_address',
		'headshot',
		'usad_id',
		'can_referee',
		'is_active',
	)
	search_fields = [
		'name',
		'usad_id',
	]
	ordering = [
		'name',
	]

@admin.register(league.SeasonDivisionTeam)
class SeasonDivisionTeamAdmin(admin.ModelAdmin):
	list_display = (
		'team',
		'division',
		'season',
		'wins',
		'losses',
		'points',
	)
	search_fields = [
		'team__name',
		'division__name',
		'season__year',
	]
	ordering = [
		'-season__year',
		'division__name',
		'team__name',
	]
	list_select_related = (
		'season',
		'division',
		'team',
	)

@admin.register(league.SeasonDivisionTeamPlayer)
class SeasonDivisionTeamPlayerAdmin(admin.ModelAdmin):
	list_display = (
		'player',
		'team',
		'division',
		'season',
	)
	search_fields = [
		'player__name',
		'season_division_team__team__name',
		'season_division_team__division__name',
		'season_division_team__season__year',
	]
	ordering = [
		'-season_division_team__season__year',
		'season_division_team__division__name',
		'season_division_team__team__name',
		'player__name',
	]
	list_select_related = (
		'player',
		'season_division_team',
	)

	def season(self, obj):
		return obj.season_division_team.season

	def division(self, obj):
		return obj.season_division_team.division

	def team(self, obj):
		return obj.season_division_team.team

@admin.register(league.Event)
class EventAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
		'date_updated',
	)
	list_display = (
		'title',
		'datetime',
		'season',
		'location',
		'registration_open',
		'registration_close',
		'header',
		'calendar_background',
		'date_created',
		'date_updated',
	)
	search_fields = [
		'title',
	]
	ordering = [
		'-datetime',
	]

	def get_urls(self):
		return [
			path('<int:event_id>/manage/', self.manage, name='league_event_manage'),
			path('<int:event_id>/registered/', self.registered, name='league_event_registered'),
		] + super(EventAdmin, self).get_urls()

	def manage(self, request, event_id):
		if not request.user.is_authenticated:
			return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))

		return TemplateResponse(request, 'admin/manage.html', {
			'event': get_object_or_404(league.Event, pk=event_id),
		})

	@csrf_exempt
	def registered(self, request, event_id):
		try:
			event = league.Event.objects.get(pk=event_id)
		except league.Event.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'Event does not exist'}, status=404)

		return JsonResponse({'success': True, 'data': league.LeagueSerializer.serialize(event.event_division_hash(include_players=True))})

@admin.register(league.EventDivision)
class EventDivisionAdmin(admin.ModelAdmin):
	list_display = (
		'division',
		'event',
		'cost',
		'max_teams',
		'team_count',
		'open_invites',
	)
	search_fields = [
		'division__name',
		'event__title',
	]
	ordering = [
		'-event__datetime',
		'event__title',
		'division__name',
	]
	list_select_related = (
		'event',
		'division',
	)

@admin.register(league.EventDivisionTeam)
class EventDivisionTeamAdmin(admin.ModelAdmin):
	readonly_fields = (
		'transaction_id',
	)
	list_display = (
		'team',
		'division',
		'event',
		'place',
		'transaction_id',
	)
	ordering = [
		'-season_division_team__season__year',
		'event_division__division__name',
		'season_division_team__team__name',
	]
	search_fields = [
		'season_division_team__team__name',
		'event_division__division__name',
		'season_division_team__season__year',
	]
	list_select_related = (
		'event_division',
		'season_division_team',
	)

	def team(self, obj):
		return obj.season_division_team.team.name

	def division(self, obj):
		return obj.event_division.division.name

	def event(self, obj):
		return obj.event_division.event.title

@admin.register(league.EventDivisionTeamPlayer)
class EventDivisionTeamPlayerAdmin(admin.ModelAdmin):
	list_display = (
		'player',
		'team',
		'division',
		'event',
		'is_captain',
		'is_referee',
	)
	ordering = [
		'-event_division_team',
		'-is_captain',
		'-is_referee',
	]
	search_fields = [
		'player',
		'team',
		'division',
		'event',
	]
	list_select_related = (
		'event_division_team',
		'season_division_team_player',
	)

	def player(self, obj):
		return obj.season_division_team_player.player.name

	def team(self, obj):
		return obj.season_division_team_player.season_division_team.team.name

	def division(self, obj):
		return obj.event_division_team.event_division.division.name

	def event(self, obj):
		return obj.event_division_team.event_division.event.title
