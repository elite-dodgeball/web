"""
.. module:: models
   :platform: Unix
   :synopsis: Contains the models for the Elite site

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import re
import uuid
import datetime

from django.db import models
from django.utils import timezone
from django.db.models.query import QuerySet
from django.contrib.postgres.search import SearchVector

from elite import serializer


class Season(models.Model):
	""" Season model

	"""
	@staticmethod
	def current_season():
		""" Get the current season

		:returns: Season

		"""
		return Season.objects.all().order_by('-year').first()

	def __str__(self):
		""" Return the season's year

		:returns: int

		"""
		return str(self.year)

	year = models.PositiveSmallIntegerField(default=datetime.datetime.now().year, unique=True)


class Region(models.Model):
	""" Region model

	"""
	def __str__(self):
		""" Return the region's name

		:returns: str

		"""
		return self.name

	name = models.CharField(max_length=255)
	is_active = models.BooleanField(default=False)


class Division(models.Model):
	""" Division model

	"""
	def __str__(self):
		""" Return the division's name

		:returns: str

		"""
		return self.name

	name = models.CharField(max_length=255)
	is_active = models.BooleanField(default=False)
	is_primary = models.BooleanField(default=False)


class Team(models.Model):
	""" Team model

	"""
	def players(self):
		""" Get all the players for all the divisions

		:returns: dict

		"""
		season = Season.current_season()

		season_division_teams = SeasonDivisionTeam.objects.filter(season=season, team=self)
		season_division_team_hash = {season_division_team.pk: season_division_team for season_division_team in season_division_teams}

		season_division_team_players = SeasonDivisionTeamPlayer.objects.filter(season_division_team__in=season_division_teams)

		players = Player.objects.filter(id__in=[season_division_team_player.player_id for season_division_team_player in season_division_team_players])
		player_hash = {player.pk: player for player in players}

		divisions = Division.objects.filter(id__in=[season_division_team.division_id for season_division_team in season_division_teams])
		division_hash = {division.pk: division for division in divisions}

		division_team_hash = dict()

		for season_division_team_player in season_division_team_players:
			division_id = season_division_team_hash[season_division_team_player.season_division_team_id].division_id

			if division_id not in division_team_hash:
				division_team_hash[division_id] = {
					'division': division_hash[division_id],
					'players': list(),
				}

			division_team_hash[division_id]['players'].append(player_hash[season_division_team_player.player_id])

		return division_team_hash

	def social(self):
		""" Build a hash of social user handles

		:returns: dict

		"""
		social = {}

		if self.twitter:
			social['twitter'] = Team.get_username('twitter.com', self.twitter)
		if self.instagram:
			social['instagram'] = Team.get_username('instagram.com', self.instagram)
		if self.youtube:
			social['youtube'] = Team.get_username('youtube.com/user', self.youtube)
		if self.facebook:
			social['facebook'] = Team.get_username('facebook.com', self.facebook)

		return social

	@staticmethod
	def get_username(base, url):
		""" Get the handle from a social media link

		:param base: Base string to search against in the regex
		:type base: str
		:param url: Full URL to extract from
		:type url: str
		:returns: str

		"""
		if not isinstance(base, str):
			raise TypeError('Base must be a string')
		if not isinstance(url, str):
			raise TypeError('URL must be a string')

		try:
			ret = re.search(r'%s\/([^/\s?]+)[/\s?]?' % re.escape(base), url).group(1)
			return '@%s' % ret if base == 'twitter.com' else ret
		except AttributeError:
			return url

	def logo_path(self, filename):
		""" Return the logo's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'teams/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def cover_path(self, filename):
		""" Return the cover's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'teams/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the team's name

		:returns: str

		"""
		return self.name

	name = models.CharField(max_length=255, db_index=True)
	logo = models.ImageField(upload_to=logo_path)
	cover = models.ImageField(upload_to=cover_path)
	location = models.CharField(max_length=255)
	information = models.TextField()
	email_address = models.EmailField()
	website = models.URLField(blank=True)
	twitter = models.URLField(blank=True)
	instagram = models.URLField(blank=True)
	youtube = models.URLField(blank=True)
	facebook = models.URLField(blank=True)
	region = models.ForeignKey(Region, on_delete=models.PROTECT)
	is_active = models.BooleanField(default=False)


class Player(models.Model):
	""" Player model

	"""
	def headshot_path(self, filename):
		""" Return the headshot's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'players/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the player's name

		:returns: str

		"""
		return '%s (#%s)' % (self.name, self.number)

	name = models.CharField(max_length=255)
	email_address = models.EmailField()
	headshot = models.ImageField(upload_to=headshot_path)
	number = models.CharField(max_length=255)
	bio = models.TextField(blank=True)
	usad_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
	can_referee = models.BooleanField(default=False)
	is_active = models.BooleanField(default=False)


class SeasonDivisionTeam(models.Model):
	""" SeasonDivisionTeam model

	"""
	@staticmethod
	def get_team_data_hash(season_division_team_ids=None, season_division_teams=None):
		""" Match up Team and SeasonDivisionTeam data in a Team-based hash

		:param season_division_team_ids: SeasonDivisionTeam IDs to get
		:type season_division_team_ids: list
		:param season_division_teams: SeasonDivisionTeam objects to work with
		:type season_division_teams: list
		:returns: dict

		"""
		if season_division_team_ids and not isinstance(season_division_team_ids, (list, tuple)):
			raise TypeError('season_division_team_ids must be a list or tuple: %s' % type(season_division_team_ids))

		if season_division_teams and not isinstance(season_division_teams, (list, tuple, QuerySet)):
			raise TypeError('season_division_teams must be a list or tuple or QuerySet: %s' % type(season_division_teams))

		if season_division_team_ids:
			season_division_teams = SeasonDivisionTeam.objects.filter(id__in=season_division_team_ids)

		team_data_hash = dict()
		team_ids = set()

		for season_division_team in season_division_teams:
			if season_division_team.team_id not in team_ids:
				team_data_hash[season_division_team.team_id] = {
					'season_division_team_hash': dict(),
				}
				team_ids.add(season_division_team.team_id)

			team_data_hash[season_division_team.team_id]['season_division_team_hash'][season_division_team.division_id] = season_division_team

		teams = Team.objects.filter(id__in=list(team_ids))

		for team in teams:
			team_data_hash[team.pk]['team'] = team

		return team_data_hash

	def __str__(self):
		""" Return the team's name

		:returns: str

		"""
		return '%s (%s - %s) %s %s' % (self.team, self.wins, self.losses, self.division, self.season)

	season = models.ForeignKey(Season, on_delete=models.PROTECT)
	division = models.ForeignKey(Division, on_delete=models.PROTECT)
	team = models.ForeignKey(Team, on_delete=models.PROTECT)
	wins = models.PositiveSmallIntegerField(default=0)
	losses = models.PositiveSmallIntegerField(default=0)
	points = models.PositiveSmallIntegerField(db_index=True, default=0)

	class Meta:
		unique_together = (
			('season', 'division', 'team',),
		)


class SeasonDivisionTeamPlayer(models.Model):
	""" SeasonDivisionTeamPlayer model

	"""
	def __str__(self):
		""" Return the player's name

		:returns: str

		"""
		return '%s - %s %s %s' % (
			self.player,
			self.season_division_team.team,
			self.season_division_team.division,
			self.season_division_team.season)

	player = models.ForeignKey(Player, on_delete=models.PROTECT)
	season_division_team = models.ForeignKey(SeasonDivisionTeam, on_delete=models.PROTECT)

	class Meta:
		unique_together = (
			('player', 'season_division_team',),
		)


class Event(models.Model):
	""" Event model

	"""
	STATE_PREP = 0
	STATE_LIVE = 1
	STATE_DONE = 2
	STATE_CHOICES = (
		(STATE_PREP, 'Prep phase'),
		(STATE_LIVE, 'Live event'),
		(STATE_DONE, 'Complete'),
	)

	@staticmethod
	def search(query):
		""" Search events

		:param query: Query to search for
		:type query: str
		:returns: list

		"""
		try:
			return list(Event.objects.annotate(
				search=SearchVector('title') + SearchVector('description'),
			).filter(search=query).order_by('datetime'))
		except Event.DoesNotExist:
			return []

	@staticmethod
	def get_upcoming(date=None):
		""" Get upcoming events past a certain date

		:param date: Date to seek past
		:type date: datetime
		:returns: list

		"""
		if not isinstance(date, datetime.datetime):
			date = timezone.now()
		return Event.objects.filter(datetime__gte=date).order_by('datetime')

	def event_division_hash(self, include_players=False):
		""" Get a hash of divisions

		:returns: dict

		"""
		divisions = Division.objects.all()
		division_hash = {division.pk: division for division in divisions}

		event_divisions = EventDivision.objects.filter(event__exact=self.pk).order_by('division_id')
		event_division_hash = {
			event_division.pk: {
				'division': division_hash[event_division.division_id],
				'event_division': event_division,
				'teams': list(),
			} for event_division in event_divisions
		}

		player_data_hash = {
			'id': dict(),
			'season_division_team_id': dict(),
		}

		if include_players:
			event_division_team_players = EventDivisionTeamPlayer.objects.select_related('season_division_team_player').filter(
				event_division_team__event_division__in=[event_division.pk for event_division in event_divisions])

			player_ids = set()

			for event_division_team_player in event_division_team_players:
				player_datum = {
					'event_division_team_player': event_division_team_player,
					'season_division_team_player': event_division_team_player.season_division_team_player,
				}

				if event_division_team_player.season_division_team_player.season_division_team_id not in player_data_hash['season_division_team_id']:
					player_data_hash['season_division_team_id'][event_division_team_player.season_division_team_player.season_division_team_id] = list()

				player_data_hash['season_division_team_id'][event_division_team_player.season_division_team_player.season_division_team_id].append(player_datum)
				player_data_hash['id'][event_division_team_player.season_division_team_player.player_id] = player_datum

				player_ids.add(event_division_team_player.season_division_team_player.player_id)

			players = Player.objects.filter(pk__in=list(player_ids))

			for player in players:
				player_data_hash['id'][player.pk]['player'] = player

		event_division_teams = EventDivisionTeam.objects.filter(event_division__in=event_divisions)

		if len(event_division_teams):
			season_division_team_ids = set()
			season_division_team_hash = dict()

			for event_division_team in event_division_teams:
				if event_division_team.season_division_team_id not in season_division_team_ids:
					season_division_team_ids.add(event_division_team.season_division_team_id)
					season_division_team_hash[event_division_team.season_division_team_id] = event_division_team

			team_data_hash = SeasonDivisionTeam.get_team_data_hash(season_division_team_ids=list(season_division_team_ids))

			for team_id, team_datum in team_data_hash.items():
				for division_id, season_division_team in team_datum['season_division_team_hash'].items():
					event_division_id = season_division_team_hash[season_division_team.pk].event_division_id
					event_division_hash[event_division_id]['teams'].append({
						'team': team_datum['team'],
						'event_division_team': season_division_team_hash[season_division_team.pk],
						'season_division_team': season_division_team,
						'players': player_data_hash['season_division_team_id'][season_division_team.pk] if season_division_team.pk in player_data_hash['season_division_team_id'] else list(),
					})

		return event_division_hash

	def header_path(self, filename):
		""" Return the header's upload path

		:param filename: Filename uploaded with
		:type filename: str
		:returns: str

		"""
		return 'events/%s.%s' % (uuid.uuid1(), get_extension(filename))

	def __str__(self):
		""" Return the event's title

		:returns: str

		"""
		return self.title

	title = models.CharField(max_length=255, db_index=True)
	header = models.ImageField(upload_to=header_path)
	datetime = models.DateTimeField(db_index=True)
	location = models.CharField(max_length=255)
	description = models.TextField()
	season = models.ForeignKey(Season, on_delete=models.PROTECT)
	registration_open = models.DateTimeField(default=timezone.now)
	registration_close = models.DateTimeField(default=timezone.now)
	calendar_background = models.CharField(max_length=7) # ColorField()
	stream_link = models.URLField(blank=True, null=True)
	state = models.PositiveSmallIntegerField(default=STATE_PREP, choices=STATE_CHOICES, db_index=True)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)


class EventDivision(models.Model):
	""" EventDivision model

	"""
	TYPE_SINGLE_ELIMINATION = 0
	TYPE_DOUBLE_ELIMINATION = 1
	TYPE_CHOICES = (
		(TYPE_SINGLE_ELIMINATION, 'Single-elimination'),
		(TYPE_DOUBLE_ELIMINATION, 'Double-elimination'),
	)

	def __str__(self):
		""" Return the division's name

		:returns: str

		"""
		return '%s (%s)' % (self.division, self.event)

	event = models.ForeignKey(Event, on_delete=models.PROTECT)
	division = models.ForeignKey(Division, on_delete=models.PROTECT)
	cost = models.DecimalField(default=0, max_digits=5, decimal_places=2)
	max_teams = models.PositiveSmallIntegerField(default=0, blank=True, null=True)
	team_count = models.PositiveSmallIntegerField(default=0)
	open_invites = models.PositiveSmallIntegerField(default=0)
	tournament_type = models.PositiveSmallIntegerField(default=TYPE_SINGLE_ELIMINATION, choices=TYPE_CHOICES)

	class Meta:
		unique_together = (
			('event', 'division',),
		)


class EventDivisionTeam(models.Model):
	""" EventDivisionTeam model

	"""
	@property
	def suffix(self):
		""" Build the suffix for the place

		:returns: str

		"""
		suffix = ''
		place = str(self.place)
		end = place[-1]

		if len(place) > 1 and place[-2] == '1':
			suffix = 'th'
		elif end == '1':
			suffix = 'st'
		elif end == '2':
			suffix = 'nd'
		elif end == '3':
			suffix = 'rd'
		else:
			suffix = 'th'

		return suffix

	def __str__(self):
		""" Return the team's name

		:returns: str

		"""
		return '%s (%s)' % (self.season_division_team.team, self.event_division)

	event_division = models.ForeignKey(EventDivision, on_delete=models.PROTECT)
	season_division_team = models.ForeignKey(SeasonDivisionTeam, on_delete=models.PROTECT)
	transaction_id = models.CharField(max_length=255, blank=True, null=True)
	place = models.PositiveSmallIntegerField(blank=True, null=True)
	is_checked_in = models.BooleanField(default=False)

	class Meta:
		unique_together = (
			('event_division', 'season_division_team',),
		)


class EventDivisionTeamPlayer(models.Model):
	""" EventDivisionTeamPlayer model

	"""
	def __str__(self):
		""" Return the player's name

		:returns: str

		"""
		return '%s (%s)' % (self.season_division_team_player.player.name, self.event_division_team)

	event_division_team = models.ForeignKey(EventDivisionTeam, on_delete=models.PROTECT)
	season_division_team_player = models.ForeignKey(SeasonDivisionTeamPlayer, on_delete=models.PROTECT)
	is_captain = models.BooleanField(default=False)
	is_referee = models.BooleanField(default=False)
	is_checked_in = models.BooleanField(default=False)

	class Meta:
		unique_together = (
			('event_division_team', 'season_division_team_player',),
		)


def get_division_region_teams():
	regions = Region.objects.filter(is_active=True)
	region_hash = {region.pk: region for region in regions}

	divisions = Division.objects.filter(is_active=True, is_primary=True)
	division_hash = {
		division.pk: {
			'division': division,
			'region_team_hash': dict(),
		} for division in divisions
	}

	season = Season.current_season()
	season_division_teams = SeasonDivisionTeam.objects.filter(season=season, division__in=divisions)

	team_data_hash = SeasonDivisionTeam.get_team_data_hash(season_division_teams=season_division_teams)

	for season_division_team in season_division_teams:
		region_id = team_data_hash[season_division_team.team_id]['team'].region_id
		region_team_hash = division_hash[season_division_team.division_id]['region_team_hash']

		if region_id not in region_team_hash:
			region_team_hash[region_id] = {
				'region': region_hash[region_id],
				'team_data': list(),
			}

		region_team_hash[region_id]['team_data'].append({
			'team': team_data_hash[season_division_team.team_id]['team'],
			'season_division_team': team_data_hash[season_division_team.team_id]['season_division_team_hash'][season_division_team.division_id],
		})

	return division_hash, regions, season


class LeagueSerializer(serializer.Serializer):
	@staticmethod
	def season(season):
		return {
			'id': season.pk,
			'year': season.year,
		} if season else None

	@staticmethod
	def region(region):
		return {
			'id': region.pk,
			'name': region.name,
			'is_active': region.is_active,
		} if region else None

	@staticmethod
	def division(division):
		return {
			'id': division.pk,
			'name': division.name,
			'is_active': division.is_active,
			'is_primary': division.is_primary,
		} if division else None

	@staticmethod
	def event(event):
		return {
			'id': event.pk,
			'title': event.title,
			'header': event.header.url,
			'datetime': event.datetime,
			'location': event.location,
			'description': event.description,
			'season': event.season_id,
			'registration_open': event.registration_open,
			'registration_close': event.registration_close,
			'calendar_background': event.calendar_background,
			'stream_link': event.stream_link,
			'state': event.state,
			'date_created': event.date_created,
			'date_updated': event.date_updated,
		} if event else None

	@staticmethod
	def event_division(event_division):
		return {
			'id': event_division.pk,
			'event_id': event_division.event_id,
			'division_id': event_division.division_id,
			'cost': event_division.cost,
			'max_teams': event_division.max_teams,
			'team_count': event_division.team_count,
			'open_invites': event_division.open_invites,
			'tournament_type': event_division.tournament_type,
		} if event_division else None

	@staticmethod
	def event_division_team(event_division_team):
		return {
			'id': event_division_team.pk,
			'event_division_id': event_division_team.event_division_id,
			'season_division_team_id': event_division_team.season_division_team_id,
			'place': event_division_team.place,
			'suffix': event_division_team.suffix,
			'is_checked_in': event_division_team.is_checked_in,
		} if event_division_team else None

	@staticmethod
	def event_division_team_player(event_division_team_player):
		return {
			'id': event_division_team_player.pk,
			'event_division_team_id': event_division_team_player.event_division_team_id,
			'season_division_team_player_id': event_division_team_player.season_division_team_player_id,
			'is_captain': event_division_team_player.is_captain,
			'is_referee': event_division_team_player.is_referee,
			'is_checked_in': event_division_team_player.is_checked_in,
		} if event_division_team_player else None

	@staticmethod
	def team(team):
		return {
			'id': team.pk,
			'name': team.name,
			'logo': team.logo.url,
			'cover': team.cover.url,
			'location': team.location,
			'information': team.information,
			'email_address': team.email_address,
			'website': team.website,
			'twitter': team.twitter,
			'instagram': team.instagram,
			'youtube': team.youtube,
			'facebook': team.facebook,
			'region_id': team.region_id,
			'is_active': team.is_active,
		} if team else None

	@staticmethod
	def player(player):
		return {
			'id': player.pk,
			'name': player.name,
			'email_address': player.email_address,
			'headshot': player.headshot.url,
			'number': player.number,
			'bio': player.bio,
			'usad_id': player.usad_id,
			'can_referee': player.can_referee,
			'is_active': player.is_active,
		} if player else None

	@staticmethod
	def season_division_team(season_division_team):
		return {
			'id': season_division_team.pk,
			'season_id': season_division_team.season_id,
			'division_id': season_division_team.division_id,
			'team_id': season_division_team.team_id,
			'wins': season_division_team.wins,
			'losses': season_division_team.losses,
			'points': season_division_team.points,
		} if season_division_team else None

	@staticmethod
	def season_division_team_player(season_division_team_player):
		return {
			'id': season_division_team_player.pk,
			'player_id': season_division_team_player.player_id,
			'season_division_team_id': season_division_team_player.season_division_team_id,
		} if season_division_team_player else None


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
