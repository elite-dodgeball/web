"""
.. module:: models
   :platform: Unix
   :synopsis: Contains the models
.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import math
import uuid
import datetime
from collections import defaultdict

from django.db import models

from league import models as league
from elite import serializer


class Bracket(models.Model):
	""" Bracket model

	"""
	@property
	def rounds(self):
		round_number_hash = defaultdict(list)
		games = Game.objects.filter(bracket=self).order_by('round_number', 'game_number')

		for game in games:
			round_number_hash[game.round_number].append(game)

		return [round_number_hash[round_number] for round_number in round_number_hash]

	def __str__(self):
		""" Return the bracket's title

		:returns: str

		"""
		return '%s - %s (%s)' % (self.pk, self.bracket_type, self.event_division)

	TYPE_ROBIN = 1
	TYPE_WINNER = 2
	TYPE_LOSER = 3
	TYPE_FINAL = 4

	TYPE_CHOICES = (
		(TYPE_ROBIN, 'Round-robin'),
		(TYPE_WINNER, 'Winners bracket'),
		(TYPE_LOSER, 'Losers bracket'),
		(TYPE_FINAL, 'Finals bracket'),
	)

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	bracket_type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES, default=TYPE_ROBIN)
	event_division = models.ForeignKey(league.EventDivision, on_delete=models.SET_NULL, blank=True, null=True, related_name='+')
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = (
			('bracket_type', 'event_division',),
		)


class Game(models.Model):
	""" Game model

	"""
	def __str__(self):
		""" Return the game's title

		:returns: str

		"""
		return '%s - %s - %s - %s - %s (%s) vs. %s (%s)' % (self.pk, (None if not self.bracket else self.bracket.bracket_type), self.round_number, self.game_number, (None if not self.top_team else self.top_team_id), self.top_wins, (None if not self.bottom_team else self.bottom_team_id), self.bottom_wins)

	STATE_PREP = 0
	STATE_LIVE = 1
	STATE_DONE = 2

	STATE_CHOICES = (
		(STATE_PREP, 'Prep phase'),
		(STATE_LIVE, 'Live game'),
		(STATE_DONE, 'Complete'),
	)

	# Game metas per bracket
	bracket = models.ForeignKey(Bracket, on_delete=models.CASCADE, related_name='+')
	round_number = models.PositiveSmallIntegerField(default=0)
	game_number = models.PositiveSmallIntegerField(default=0)
	state = models.PositiveSmallIntegerField(default=STATE_PREP, choices=STATE_CHOICES)

	# Team stats per game
	top_team = models.ForeignKey(league.EventDivisionTeam, on_delete=models.CASCADE, blank=True, null=True, related_name='+')
	top_wins = models.PositiveSmallIntegerField(default=0)
	bottom_team = models.ForeignKey(league.EventDivisionTeam, on_delete=models.CASCADE, blank=True, null=True, related_name='+')
	bottom_wins = models.PositiveSmallIntegerField(default=0)

	# Games lead to more games
	winner_to = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='+')
	loser_to = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='+')

	# Object metas
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	date_created = models.DateTimeField(auto_now_add=True)
	date_updated = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = (
			('bracket', 'round_number', 'game_number',),
		)


class LivePlayer(models.Model):
	""" LivePlayer model

	"""
	def __str__(self):
		""" Return the game/player combination

		:returns: str

		"""
		return '%s - %s' % (self.game_id, self.event_division_team_player_id)

	game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='+')
	event_division_team_player = models.ForeignKey(league.EventDivisionTeamPlayer, on_delete=models.CASCADE, related_name='+')
	is_playing = models.BooleanField(default=False)
	is_in = models.BooleanField(default=False)

	class Meta:
		unique_together = (
			('game', 'event_division_team_player',),
		)


def make_winners_bracket(team_list):
	""" Create a winners bracket

	:param team_list: List of EventDivisionTeam objects to create winners bracket matches with
	:type team_list: list
	:returns: list

	"""
	team_count = len(team_list)

	total_rounds = math.ceil(math.log(team_count, 2))
	team_seed_hash = {team.place: team for team in team_list}

	rounds = list()
	next_round_hash = {}

	for round_number in range(total_rounds):
		round_games = list()

		total_games = int(math.pow(2, round_number))
		total_teams = total_games * 2

		for game_number in range(total_games):
			seed_top = game_number + 1
			seed_bottom = total_teams - (seed_top - 1)

			if seed_bottom > team_count:
				continue
			elif seed_top > seed_bottom:
				break

			round_game = Game(top_team=team_seed_hash[seed_top], bottom_team=team_seed_hash[seed_bottom], round_number=round_number, game_number=game_number)

			if seed_top in next_round_hash:
				round_game.winner_to = next_round_hash[seed_top]

			round_games.append(round_game)

		next_round_hash = {}

		for round_game in round_games:
			next_round_hash[round_game.top_team.place] = round_game
			next_round_hash[round_game.bottom_team.place] = round_game

		rounds.append(round_games)

	return rounds


def make_round_robin(team_list):
	""" Create round-robin matches

	:param team_list: List of EventDivisionTeam objects to create round-robin matches with
	:type team_list: list
	:returns: list

	"""
	team_count = len(team_list)

	oddity = None

	if team_count % 2 == 0:
		team_count -= 1
		oddity = team_list.pop()

	rounds = [list() for i in range(team_count)]

	for round_number in range(team_count):
		game_number = 0
		midpoint = math.floor(team_count / 2)

		while game_number < midpoint:
			game_number += 1
			rounds[round_number].append(Game(top_team=team_list[midpoint - game_number], bottom_team=team_list[midpoint + game_number], round_number=round_number, game_number=(game_number - 1)))

		if oddity:
			rounds[round_number].append(Game(top_team=team_list[midpoint], bottom_team=oddity, round_number=round_number, game_number=game_number))

		team_list.insert(0, team_list.pop())

	return rounds


def make_managed_round_robin(team_list, court_total, referee_count):
	""" Create managed round-robin matches

	:param team_list: List of EventDivisionTeam objects to create round-robin matches with
	:type team_list: list
	:param court_total: Total number of courts to use
	:type court_total: int
	:param referee_count: Total number of referee teams
	:type referee_count: int
	:returns: list

	"""
	games = []
	rounds = []

	ref_set = set()
	play_set = set()

	bracket = make_round_robin(team_list=team_list)
	team_count = len(team_list)

	# Turn the original round-robin structure into a straight list of games

	for round_number in range(len(bracket)):
		for game_number in range(len(bracket[round_number])):
			games.append(bracket[round_number][game_number])

	# Clear all win counts

	round_play_set = set()

	while len(games) > 0:
		# Reset for each round

		refs = []
		courts = []
		reset = 0

		round_play_set.clear()
		round_number = len(rounds)

		# Add games across the courts

		while len(courts) < court_total and len(games) > 0 and reset < 2:
			for game in games:
				if len(courts) >= court_total:
					break

				if len(play_set) >= team_count:
					play_set.clear()

				if game.top_team.pk not in play_set and game.bottom_team.pk not in play_set and game.top_team.pk not in round_play_set and game.bottom_team.pk not in round_play_set:
					game.round_number = round_number
					game.game_number = len(courts)
					courts.append(game)

					play_set.add(game.top_team.pk)
					play_set.add(game.bottom_team.pk)
					round_play_set.add(game.top_team.pk)
					round_play_set.add(game.bottom_team.pk)

			if len(courts) < court_total:
				play_set.clear()
				reset += 1

		# Figure out who needs to referee

		reset = 0

		while reset < 2 and len(refs) < referee_count:
			for team in team_list:
				if len(refs) >= referee_count:
					break

				if reset == 1:
					ref_set.clear()
					team_list.reverse()

					for ref in refs:
						ref_set.add(ref.pk)

				if len(ref_set) >= team_count:
					ref_set.clear()

				if team.pk not in ref_set and team.pk not in round_play_set:
					refs.append(team)
					ref_set.add(team.pk)

			reset += 1

		# Remove games already on courts from the list

		for court in courts:
			for game_number, game in enumerate(games):
				if game.top_team.place == court.top_team.place and game.bottom_team.place == court.bottom_team.place:
					del games[game_number]
					break

		# Add courts and refs to rounds

		court_game_total = len(courts)
		rounds.append(courts + [Game(round_number=round_number, game_number=(court_game_total + ref_number), top_team=ref) for ref_number, ref in enumerate(refs)])

	return rounds


def make_losers_bracket(winners_bracket, team_list):
	""" Create a losers bracket

	:param winners_bracket: Rounds from make_winners_bracket() to work with
	:type winners_bracket: list
	:param team_list: List of Team objects to populate games with
	:type team_list: list
	:returns: list

	"""
	round_count = len(winners_bracket)
	sustain_count = round_count - 1

	rounds = [list() for round_number in range(sustain_count * 2)]
	last_seed = winners_bracket[-1][0].bottom_team.place

	is_sustain = True
	starting_seed = 2

	next_round_hash = {}
	team_seed_hash = {team.place: team for team in team_list}

	for round_number in range(sustain_count * 2):
		round_games = list()
		game_count = int(math.pow(2, math.floor(round_number / 2)))

		if not is_sustain:
			starting_seed += game_count

		is_sustain = not is_sustain

		if game_count < 2:  # Special case for the last two rounds
			if starting_seed + 1 <= last_seed:
				round_game = Game(top_team=team_seed_hash[starting_seed], bottom_team=team_seed_hash[starting_seed + 1], round_number=round_number, game_number=len(rounds[round_number]))
				rounds[round_number].append(round_game)
				round_games.append(round_game)

		elif is_sustain:  # Basic pairing in a trimming round
			for seed_number in range(starting_seed, (starting_seed + game_count)):
				seed_bottom = (game_count * 2 * 2) - (seed_number - starting_seed)
				if seed_bottom <= last_seed:
					round_game = Game(top_team=team_seed_hash[seed_number], bottom_team=team_seed_hash[seed_bottom], round_number=round_number, game_number=len(rounds[round_number]))
					rounds[round_number].append(round_game)
					round_games.append(round_game)

		else:  # Special pairing in a sustaining round
			for seed_number in range(starting_seed, starting_seed + game_count):
				seed_bottom = (starting_seed + (game_count * 2)) - (seed_number - starting_seed) - 1
				if seed_bottom <= last_seed:
					round_game = Game(top_team=team_seed_hash[seed_number], bottom_team=team_seed_hash[seed_bottom], round_number=round_number, game_number=len(rounds[round_number]))
					rounds[round_number].append(round_game)
					round_games.append(round_game)

		for round_game in round_games:  # Set the winner_to
			if round_game.top_team.place in next_round_hash:
				round_game.winner_to = next_round_hash[round_game.top_team.place]

		next_round_hash = {}

		for round_game in round_games:
			next_round_hash[round_game.top_team.place] = round_game
			next_round_hash[round_game.bottom_team.place] = round_game

	return [rounds[round_number] for round_number in range(len(rounds)) if rounds[round_number]]


def make_final_bracket(winners_bracket, losers_bracket):
	""" Create the collision between a winners_bracket and losers_bracket

	:param winners_bracket: Rounds from make_winners_bracket() to work with
	:type winners_bracket: list
	:param losers_bracket: Rounds from make_losers_bracket() to work with
	:type losers_bracket: list

	"""
	rounds = [
		[Game(top_team=winners_bracket[0][0].top_team, bottom_team=losers_bracket[0][0].top_team, round_number=0)],
		[Game(top_team=winners_bracket[0][0].top_team, bottom_team=losers_bracket[0][0].top_team, round_number=1)],
	]

	winners_bracket[0][0].winner_to = rounds[1][0]
	losers_bracket[0][0].winner_to = rounds[1][0]

	rounds[1][0].winner_to = rounds[0][0]
	rounds[1][0].loser_to = rounds[0][0]

	return rounds


def set_losers_flow(winners_bracket, losers_bracket):
	""" Set all the loser_to values in the winners_bracket

	:param winners_bracket: Rounds from make_winners_bracket() to work with
	:type winners_bracket: list
	:param losers_bracket: Rounds from make_losers_bracket() to work with
	:type losers_bracket: list

	"""
	losers_round_count = len(losers_bracket)
	losers_bracket_hash = {
		2: losers_bracket[0][0],
	}

	winners_round_count = len(winners_bracket)
	is_complete = len(winners_bracket[-1]) == math.pow(2, winners_round_count - 1)

	# Since we know the first appearance of a seed in the losers_bracket is that
	# seed dropping to the losers_bracket, we can reverse iterate through it for
	# both top_team and bottom_team

	for round_number in range(losers_round_count - 1, -1, -1):
		for round_game in losers_bracket[round_number]:
			if round_game.bottom_team.place not in losers_bracket_hash:
				losers_bracket_hash[round_game.bottom_team.place] = round_game
			if round_game.top_team.place not in losers_bracket_hash:
				losers_bracket_hash[round_game.top_team.place] = round_game

	for round_number in range(winners_round_count - 1, -1, -1):
		for round_game in winners_bracket[round_number]:
			round_game.loser_to = losers_bracket_hash.pop(round_game.bottom_team.place)


def sort_rounds(rounds, fill_type=0):
	""" Align games with their progression

	:param rounds: Rounds of Game objects to work with
	:type rounds: list
	:param fill_type: 1 = winners, 2 = losers
	:type fill_type: int
	:returns: list

	"""
	round_count = len(rounds)
	next_round_hash = {}

	if not isinstance(fill_type, int):
		fill_type = 0

	for round_number in range(round_count):
		# fill_type

		if round_number == round_count - 1 and fill_type > 0:
			game_count = 0
			feeder_limit = 2

			if fill_type == 1:
				game_count = math.pow(2, round_number)
			elif fill_type == 2:
				game_count = math.pow(2, math.floor(round_number / 2))

				if round_number % 2 > 0:
					feeder_limit = 1

			if game_count - len(rounds[round_number]) > 0:
				current_round_hash = {}

				for bround in rounds[round_number]:
					if bround['winner_to'] not in current_round_hash:
						current_round_hash[bround['winner_to']] = 0

					current_round_hash[bround['winner_to']] += 1

				for game_id, game_number in next_round_hash.items():
					if game_id not in current_round_hash:
						current_round_hash[game_id] = 0

					while current_round_hash[game_id] < feeder_limit:
						rounds[round_number].append({
							'id': '',
							'winner_to': game_id,
						})

						current_round_hash[game_id] += 1

		# sort

		rounds[round_number].sort(key=lambda game: (-next_round_hash[game['winner_to']], game['id']) if game['winner_to'] in next_round_hash else (0, ''), reverse=True)

		# replace

		if round_number == round_count - 1 and fill_type > 0:
			for game_number in range(len(rounds[round_number])):
				if rounds[round_number][game_number]['id'] == '':
					rounds[round_number][game_number] = None

		next_round_hash = {rounds[round_number][game_number]['id']: game_number for game_number in range(len(rounds[round_number])) if rounds[round_number][game_number]}

	return rounds


class TourfSerializer(serializer.Serializer):
	@staticmethod
	def dater(data, recursive=False):
		for key, value in data.items():
			if isinstance(value, datetime.datetime):
				data[key] = value.replace(tzinfo=datetime.timezone.utc).isoformat()
			elif isinstance(value, uuid.UUID):
				data[key] = str(value)
			elif recursive and isinstance(value, dict):
				data[key] = TourfSerializer.dater(value)
		return data

	@staticmethod
	def live_player(live_player):
		return {
			'event_division_team_player_id': live_player.event_division_team_player_id,
			'is_playing': live_player.is_playing,
			'is_in': live_player.is_in,
		} if live_player else None

	@staticmethod
	def event_division_team(event_division_team):
		return {
			'id': event_division_team.pk,
			'seed': event_division_team.place,
		} if event_division_team else None

	@staticmethod
	def game(game):
		return {
			'id': str(game.pk) if isinstance(game.pk, uuid.UUID) else game.pk,
			'top_team': TourfSerializer.event_division_team(game.top_team) if isinstance(game.top_team, league.EventDivisionTeam) else game.top_team,
			'top_wins': game.top_wins,
			'bottom_team': TourfSerializer.event_division_team(game.bottom_team) if isinstance(game.bottom_team, league.EventDivisionTeam) else game.bottom_team,
			'bottom_wins': game.bottom_wins,
			'winner_to': str(game.winner_to_id) if isinstance(game.winner_to, Game) else game.winner_to,
			'loser_to': str(game.loser_to_id) if isinstance(game.loser_to, Game) else game.loser_to,
			'state': game.state,
		} if game else None

	@staticmethod
	def bracket(bracket, fill_bracket=False):
		fill_type = 0

		if fill_bracket:
			if bracket.bracket_type == Bracket.TYPE_WINNER:
				fill_type = 1
			elif bracket.bracket_type == Bracket.TYPE_LOSER:
				fill_type = 2

		return {
			'id': str(bracket.pk) if isinstance(bracket.pk, uuid.UUID) else bracket.pk,
			'date_updated': bracket.date_updated.isoformat() if isinstance(bracket.date_updated, datetime.datetime) else bracket.date_updated,
			'date_created': bracket.date_created.isoformat() if isinstance(bracket.date_created, datetime.datetime) else bracket.date_created,
			'rounds': sort_rounds(rounds=[[TourfSerializer.game(game) for game in bround] for bround in bracket.rounds], fill_type=fill_type),
			'event_division_id': bracket.event_division_id,
		}
