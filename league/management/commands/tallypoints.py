"""
.. module:: Pointer
   :platform: Unix
   :synopsis: Update points for teams

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from league import models as league
from tourf import models as tourf


class Pointer(object):
	max_points = 10

	def __init__(self):
		self.season_division_team_hash = {}
		season_division_teams = league.SeasonDivisionTeam.objects.all()

		for season_division_team in season_division_teams:
			season_division_team.wins = 0
			season_division_team.losses = 0
			season_division_team.points = 0
			self.season_division_team_hash[season_division_team.pk] = season_division_team

	def update(self, seasons):
		""" Kick off the update process

		:param seasons: Seasons to process
		:type seasons: list

		"""
		season_hash = {}

		for season in seasons:
			season_hash[season.pk] = season
			self.traverse_season(season=season)

		try:
			with transaction.atomic():
				for season_division_team_id, season_division_team in self.season_division_team_hash.items():
					if season_division_team.season_id in season_hash:
						season_division_team.save()
		except Exception as e:
			raise CommandError(str(e))

	def traverse_season(self, season):
		""" Crawl the division results of a Season

		:param season: Season to traverse
		:type season: league.Season

		"""
		event_divisions = league.EventDivision.objects.select_related('event').filter(event__season=season, event__state=league.Event.STATE_DONE)

		for event_division in event_divisions:
			event_division_team_hash = self.count_points(event_division=event_division)
			self.count_record(event_division=event_division, event_division_team_hash=event_division_team_hash)

	def count_points(self, event_division):
		""" Add points to relevant SeasonDivisionTeam based on EventDivision results

		:param event_division: EventDivision to count
		:type event_division: league.EventDivision
		:returns: dict

		"""
		event_division_team_hash = {}
		event_division_teams = league.EventDivisionTeam.objects.filter(event_division=event_division)

		for event_division_team in event_division_teams:
			if isinstance(event_division_team.place, int) and event_division_team.place <= self.max_points:
				self.season_division_team_hash[event_division_team.season_division_team_id].points += self.max_points - (event_division_team.place - 1)

			event_division_team_hash[event_division_team.pk] = event_division_team

		return event_division_team_hash

	def count_record(self, event_division, event_division_team_hash=None):
		""" Total wins and losses for relevant SeasonDivisionTeam based on EventDivision results

		:param event_division: EventDivision to count
		:type event_division: league.EventDivision
		:param event_division_team_hash: Hash of EventDivisionTeam objects for avoiding another database call
		:type event_division_team_hash: dict

		"""
		if not event_division_team_hash:
			event_division_teams = league.EventDivisionTeam.objects.filter(event_division=event_division)
			event_division_team_hash = {event_division_team.pk: event_division_team for event_division_team in event_division_teams}

		games = tourf.Game.objects.select_related('bracket').filter(
			bracket__event_division=event_division,
			bracket__bracket_type__in=[tourf.Bracket.TYPE_WINNER, tourf.Bracket.TYPE_LOSER, tourf.Bracket.TYPE_FINAL])

		for game in games:
			if game.top_wins > game.bottom_wins:
				self.season_division_team_hash[event_division_team_hash[game.top_team_id].season_division_team_id].wins += 1
				self.season_division_team_hash[event_division_team_hash[game.bottom_team_id].season_division_team_id].losses += 1
			elif game.bottom_wins > game.top_wins:
				self.season_division_team_hash[event_division_team_hash[game.top_team_id].season_division_team_id].losses += 1
				self.season_division_team_hash[event_division_team_hash[game.bottom_team_id].season_division_team_id].wins += 1


class Command(BaseCommand):
	help = 'Update points for teams based on event placement'

	def add_arguments(self, parser):
		parser.add_argument('season', nargs='*', type=int)

	def handle(self, *args, **options):
		seasons = league.Season.objects.filter(year__in=list(options['season']))

		if len(seasons) < 1:
			seasons = league.Season.objects.all()

		PTR = Pointer()
		PTR.update(seasons=seasons)

		self.stdout.write(self.style.SUCCESS('Successfully updated points'))
