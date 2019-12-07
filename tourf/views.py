"""
.. module:: views
   :platform: Unix
   :synopsis: Contains the views
.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import uuid
import simplejson as json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt

from asgiref.sync import async_to_sync
import channels.layers

from league import models as league
from tourf import models as tourf


@csrf_exempt
def index(request):
	team_list = [league.EventDivisionTeam(place=(team_number + 1)) for team_number in range(9)]

	winners_bracket = tourf.make_winners_bracket(team_list=team_list)
	losers_bracket = tourf.make_losers_bracket(winners_bracket=winners_bracket, team_list=team_list)
	final_bracket = tourf.make_final_bracket(winners_bracket=winners_bracket, losers_bracket=losers_bracket)

	tourf.set_losers_flow(winners_bracket=winners_bracket, losers_bracket=losers_bracket)

	return JsonResponse({
		'success': True,
		'winners': tourf.sort_rounds(rounds=tourf.TourfSerializer.serialize(winners_bracket), fill_type=1 if request.GET.get('fillBracket') == 'true' else 0),
		'losers': tourf.sort_rounds(rounds=tourf.TourfSerializer.serialize(losers_bracket), fill_type=2 if request.GET.get('fillBracket') == 'true' else 0),
		'final': tourf.TourfSerializer.serialize(final_bracket),
		'robin': tourf.TourfSerializer.serialize(tourf.make_round_robin(team_list=team_list)),
		'managed': tourf.TourfSerializer.serialize(tourf.make_managed_round_robin(team_list=team_list, court_total=3, referee_count=2)),
	})


def live(request, event_id):
	""" Plain view for live events

	:param event_id: ID of the game
	:type event_id: int

	"""
	return TemplateResponse(request, _make_template_path('live.html'), {
		'event': get_object_or_404(league.Event, pk=event_id),
	})


@csrf_exempt
def stats(request, event_id):
	""" Get live stats for an event

	:param event_id: ID of the event
	:type event_id: int

	"""
	try:
		event = league.Event.objects.get(pk=event_id)
	except league.Event.DoesNotExist:
		return JsonResponse({'success': False, 'message': 'That event does not exist'}, status=404)

	live_players = None

	if request.method == 'DELETE':
		live_players = tourf.LivePlayer.objects.filter(game__bracket__event_division__event=event)

		try:
			live_players.delete()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to delete live_players', 'error': str(e)}, status=500)

		live_players = []
	elif request.method == 'PUT':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_stats_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid stats data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_stats_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize stats data', 'error': errors}, status=400)

		# Remove existing live_players

		live_players = tourf.LivePlayer.objects.filter(game__bracket__event_division__event=event)

		try:
			live_players.delete()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to delete live_players', 'error': str(e)}, status=500)

		# Create new live_players

		live_players = []

		for event_division_team_player in form_data['players']:
			live_players.append(tourf.LivePlayer(game=form_data['game'], event_division_team_player=event_division_team_player, is_playing=event_division_team_player.is_playing, is_in=event_division_team_player.is_in))

		try:
			tourf.LivePlayer.objects.bulk_create(live_players)
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create LivePlayer objects', 'error': str(e)}, status=500)

	# Build json_data

	json_data = {
		'bracket_types': tourf.Bracket.TYPE_CHOICES,
	}

	if not live_players:
		live_players = tourf.LivePlayer.objects.select_related('game', 'game__bracket', 'event_division_team_player').filter(game__bracket__event_division__event=event).order_by('-is_playing', '-is_in')

	for live_player in live_players:
		if 'game' not in json_data:
			json_data['game'] = {
				'id': str(live_player.game.pk) if isinstance(live_player.game.pk, uuid.UUID) else live_player.game.pk,
				'bracket_type': live_player.game.bracket.bracket_type,
				'round_number': live_player.game.round_number,
				'game_number': live_player.game.game_number,
			}

			json_data['top_team'] = {
				'id': live_player.game.top_team_id,
				'wins': live_player.game.top_wins,
				'players': [],
			}

			json_data['bottom_team'] = {
				'id': live_player.game.bottom_team_id,
				'wins': live_player.game.bottom_wins,
				'players': [],
			}

		if live_player.event_division_team_player.event_division_team_id == json_data['top_team']['id']:
			json_data['top_team']['players'].append(tourf.TourfSerializer.serialize(live_player))
		elif live_player.event_division_team_player.event_division_team_id == json_data['bottom_team']['id']:
			json_data['bottom_team']['players'].append(tourf.TourfSerializer.serialize(live_player))

	# Send a channel_layer update

	if request.method == 'PUT' or request.method == 'DELETE':
		async_to_sync(channels.layers.get_channel_layer().group_send)('event_%s' % event.pk, {
			'type': 'stats.update',
			'data': json_data,
		})

	return JsonResponse({'success': True, 'data': json_data})

def _validate_stats_form(form_data):
	""" Validate stats list

	"""
	errors = []

	if 'game' not in form_data or not isinstance(form_data['game'], dict):
		errors.append('game must be a dict')
	elif 'id' not in form_data['game'] or not isinstance(form_data['game']['id'], str):
		errors.append('game id must be a str')

	if not isinstance(form_data['players'], list):
		errors.append('Payload must be a list')
	else:
		for player_index, live_player in enumerate(form_data['players']):
			if not isinstance(live_player, dict):
				errors.append('%s is not a dict' % player_index)
			elif 'eventDivisionTeamPlayerId' not in live_player or not isinstance(live_player['eventDivisionTeamPlayerId'], int):
				errors.append('%s must have eventDivisionTeamPlayerId' % player_index)
			elif 'isPlaying' not in live_player or not isinstance(live_player['isPlaying'], bool):
				errors.append('%s must have bool isPlaying' % player_index)
			elif 'isIn' not in live_player or not isinstance(live_player['isIn'], bool):
				errors.append('%s must have bool isIn' % player_index)

	return errors if len(errors) > 0 else False

def _normalize_stats_form(form_data):
	""" Normalize stats list

	"""
	errors = list()

	try:
		form_data['game'] = tourf.Game.objects.select_related('bracket').get(pk=form_data['game']['id'])
	except league.Game.DoesNotExist:
		errors.append('game does not exist')

	live_players = league.EventDivisionTeamPlayer.objects.filter(pk__in=[live_player['eventDivisionTeamPlayerId'] for live_player in form_data['players']])
	live_player_hash = {live_player.pk: live_player for live_player in live_players}

	if len(live_players) != len(form_data['players']):
		errors.append('Missing eventDivisionTeamPlayerId')
	else:
		for player_index, live_player in enumerate(form_data['players']):
			form_data['players'][player_index] = live_player_hash[live_player['eventDivisionTeamPlayerId']]
			form_data['players'][player_index].is_playing = live_player['isPlaying']
			form_data['players'][player_index].is_in = live_player['isIn']

	return errors if len(errors) > 0 else False


@csrf_exempt
def events(request, event_id=None):
	""" Event endpoints

	:param event_id: ID of the event
	:type event_id: int

	"""
	if not event_id:
		return JsonResponse({'success': False, 'message': 'event_id is required'}, status=400)

	try:
		event = league.Event.objects.get(pk=event_id)
	except league.Event.DoesNotExist:
		return JsonResponse({'success': False, 'message': 'That event does not exist'}, status=404)

	if request.method == 'PATCH':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_event_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid event data', 'error': errors}, status=400)

		# Update Event object

		if 'state' in form_data:
			event.state = form_data['state']

		if 'streamLink' in form_data:
			event.stream_link = form_data['streamLink']

		try:
			event.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to update Event object', 'error': str(e)}, status=500)

		# Send a channel_layer update

		channel_layer = channels.layers.get_channel_layer()

		async_to_sync(channel_layer.group_send)('event_%s' % event_id, {
			'type': 'event.update',
			'data': tourf.TourfSerializer.dater(league.LeagueSerializer.serialize(event)),
		})

	if request.method == 'GET' or request.method == 'PATCH':
		event_division_hash = event.event_division_hash(include_players=(request.method == 'GET' and request.GET.get('includePlayers') == 'true'))

		json_data = {
			'event': league.LeagueSerializer.serialize(event),
			'event_division_hash': league.LeagueSerializer.serialize(event_division_hash),
			'event_states': league.Event.STATE_CHOICES,
			'game_states': tourf.Game.STATE_CHOICES,
			'tournament_types': league.EventDivision.TYPE_CHOICES,
		}

		fill_bracket = request.GET.get('fillBracket') == 'true'

		# Stuff the Bracket objects into the Division objects

		event_division_ids = list(event_division_hash.keys())

		bracket_hash = dict()
		brackets = tourf.Bracket.objects.filter(event_division__in=event_division_ids)

		for bracket in brackets:
			if bracket.event_division_id not in bracket_hash:
				bracket_hash[bracket.event_division_id] = dict()

			if bracket.bracket_type == tourf.Bracket.TYPE_WINNER:
				bracket_hash[bracket.event_division_id]['winners_bracket'] = tourf.TourfSerializer.bracket(bracket=bracket, fill_bracket=fill_bracket)
			elif bracket.bracket_type == tourf.Bracket.TYPE_LOSER:
				bracket_hash[bracket.event_division_id]['losers_bracket'] = tourf.TourfSerializer.bracket(bracket=bracket, fill_bracket=fill_bracket)
			elif bracket.bracket_type == tourf.Bracket.TYPE_FINAL:
				bracket_hash[bracket.event_division_id]['finals_bracket'] = tourf.TourfSerializer.serialize(bracket)
			elif bracket.bracket_type == tourf.Bracket.TYPE_ROBIN:
				bracket_hash[bracket.event_division_id]['round_robin'] = tourf.TourfSerializer.serialize(bracket)

		for event_division_id in event_division_ids:
			if event_division_id in bracket_hash:
				json_data['event_division_hash'][event_division_id]['bracket'] = bracket_hash[event_division_id]
			else:
				json_data['event_division_hash'][event_division_id]['bracket'] = dict()

		return JsonResponse({'success': True, 'data': json_data})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_event_form(form_data):
	""" Validate event dict

	"""
	errors = []

	if 'state' in form_data:
		if form_data['state'] != league.Event.STATE_PREP and form_data['state'] != league.Event.STATE_LIVE and form_data['state'] != league.Event.STATE_DONE:
			errors.append('state must be STATE_PREP, STATE_LIVE, or STATE_DONE')

	if 'streamLink' in form_data and form_data['streamLink'] != None and not isinstance(form_data['streamLink'], str):
		errors.append('streamLink must be a string')

	return errors if len(errors) > 0 else False


@csrf_exempt
def divisions(request, division_id=None):
	""" Event endpoints

	:param division_id: ID of the division
	:type division_id: int

	"""
	if not division_id:
		return JsonResponse({'success': False, 'message': 'division_id is required'}, status=400)

	try:
		event_division = league.EventDivision.objects.get(pk=division_id)
	except league.EventDivision.DoesNotExist:
		return JsonResponse({'success': False, 'message': 'That division does not exist'}, status=404)

	if request.method == 'PATCH':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_division_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid division data', 'error': errors}, status=400)

		# Update EventDivision object

		if 'tournamentType' in form_data:
			event_division.tournament_type = form_data['tournamentType']

		try:
			event_division.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to update EventDivision object', 'error': str(e)}, status=500)

	if request.method == 'GET' or request.method == 'PATCH':
		json_data = {
			'event_division': league.LeagueSerializer.serialize(event_division),
			'tournament_types': league.EventDivision.TYPE_CHOICES,
		}

		return JsonResponse({'success': True, 'data': json_data})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_division_form(form_data):
	""" Validate division dict

	"""
	errors = []

	if 'tournamentType' in form_data:
		if form_data['tournamentType'] != league.EventDivision.TYPE_SINGLE_ELIMINATION and form_data['tournamentType'] != league.EventDivision.TYPE_DOUBLE_ELIMINATION:
			errors.append('state must be TYPE_SINGLE_ELIMINATION or TYPE_DOUBLE_ELIMINATION')

	return errors if len(errors) > 0 else False


@csrf_exempt
def games(request, game_id=None):
	""" Game endpoints

	:param game_id: ID of the game
	:type game_id: str

	"""
	if game_id:
		try:
			game = tourf.Game.objects.select_related('top_team', 'bottom_team', 'bracket').get(pk=game_id)
		except tourf.Game.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That game does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(game)})
		elif request.method == 'PUT':
			if not request.user.is_authenticated:
				return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

			form_data = json.loads(request.body)

			# Validate form_data

			errors = _validate_game_form(form_data)

			if errors:
				return JsonResponse({'success': False, 'message': 'Invalid game data', 'error': errors}, status=400)

			# Normalize form_data

			errors = _normalize_game_form(form_data, game)

			if errors:
				return JsonResponse({'success': False, 'message': 'Failed to normalize game data', 'error': errors}, status=400)

			# Update Game object

			game.state = form_data['state']
			game.top_wins = form_data['topWins']
			game.top_team = form_data['topTeam']
			game.bottom_wins = form_data['bottomWins']
			game.bottom_team = form_data['bottomTeam']

			try:
				game.save()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to update Game object', 'error': str(e)}, status=500)

			channel_layer = channels.layers.get_channel_layer()

			# Propagate game.winner_to and game.loser_to

			if game.state == tourf.Game.STATE_DONE and game.bracket.bracket_type != tourf.Bracket.TYPE_ROBIN:
				updated_games, updated_teams = _propagate_results(game)

				try:
					with transaction.atomic():
						for updated_game in updated_games:
							updated_game.save()
						for updated_team in updated_teams:
							updated_team.save()
				except Exception as e:
					return JsonResponse({'success': False, 'message': 'Failed to propagate Game object', 'error': str(e)}, status=500)

				json_data = {
					'games': tourf.TourfSerializer.serialize(updated_games),
					'teams': league.LeagueSerializer.serialize(updated_teams),
				}

				async_to_sync(channel_layer.group_send)('event_%s' % game.bracket.event_division.event_id, {
					'type': 'game.update',
					'data': json_data,
				})

				return JsonResponse({'success': True, 'data': json_data})

			json_data = {
				'games': [tourf.TourfSerializer.serialize(game)],
				'teams': list(),
			}

			async_to_sync(channel_layer.group_send)('event_%s' % game.bracket.event_division.event_id, {
				'type': 'game.update',
				'data': json_data,
			})

			return JsonResponse({'success': True, 'data': json_data})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _propagate_results(game):
	""" Propagate the entire lineage of a game

	:param game: Game to start with
	:type game: tourf.Game
	:returns: tourf.Game

	"""
	updated_game_hash = dict()

	games = tourf.Game.objects.select_related('top_team', 'bottom_team').filter(bracket__event_division__exact=game.bracket.event_division_id)
	game_hash = {game.pk: game for game in games}

	# Determine winner_team and loser_team

	original_game = game_hash[game.pk]

	winner_team = original_game.top_team
	loser_team = original_game.bottom_team

	if original_game.top_wins < original_game.bottom_wins:
		winner_team = original_game.bottom_team
		loser_team = original_game.top_team

	# Propagate loser_to

	current_game = game_hash[game.pk]

	if current_game.loser_to:
		next_game = game_hash[current_game.loser_to_id]
		loser_to_games = list()

		while next_game:
			if next_game.state != tourf.Game.STATE_PREP:
				break

			if next_game.top_team.place == original_game.bottom_team.place:
				loser_to_games.append(next_game)
				current_game = next_game
				next_game = game_hash[next_game.winner_to_id] if next_game.winner_to_id in game_hash else None
			elif next_game.bottom_team.place == original_game.bottom_team.place:
				loser_to_games.append(next_game)
				current_game = next_game
				next_game = game_hash[next_game.loser_to_id] if next_game.loser_to_id in game_hash else None
			else:
				current_game = next_game
				next_game = None

		for loser_to_game in loser_to_games:
			if loser_to_game.top_team.place == original_game.bottom_team.place:
				loser_to_game.top_team = loser_team
				updated_game_hash[loser_to_game.pk] = loser_to_game
			elif loser_to_game.bottom_team.place == original_game.bottom_team.place:
				loser_to_game.bottom_team = loser_team
				updated_game_hash[loser_to_game.pk] = loser_to_game

	# Propagate winner_to

	current_game = game_hash[game.pk]

	if current_game.winner_to:
		next_game = game_hash[current_game.winner_to_id]
		winner_to_games = list()

		while next_game:
			if next_game.state != tourf.Game.STATE_PREP:
				break

			if next_game.top_team.place == original_game.top_team.place:
				winner_to_games.append(next_game)
				current_game = next_game
				next_game = game_hash[next_game.winner_to_id] if next_game.winner_to_id in game_hash else None
			elif next_game.bottom_team.place == original_game.top_team.place:
				winner_to_games.append(next_game)
				current_game = next_game
				next_game = game_hash[next_game.loser_to_id] if next_game.loser_to_id in game_hash else None
			else:
				current_game = next_game
				next_game = None

		for winner_to_game in winner_to_games:
			if winner_to_game.top_team.place == original_game.top_team.place:
				winner_to_game.top_team = winner_team
				updated_game_hash[winner_to_game.pk] = winner_to_game
			elif winner_to_game.bottom_team.place == original_game.top_team.place:
				winner_to_game.bottom_team = winner_team
				updated_game_hash[winner_to_game.pk] = winner_to_game

	# Update team place

	winner_place = min(original_game.top_team.place, original_game.bottom_team.place)
	loser_place = max(original_game.top_team.place, original_game.bottom_team.place)

	winner_team.place = winner_place
	loser_team.place = loser_place

	return list(updated_game_hash.values()), [winner_team, loser_team]

def _validate_game_form(form_data):
	""" Validate game dict

	"""
	errors = list()

	if 'state' in form_data:
		if form_data['state'] != tourf.Game.STATE_PREP and form_data['state'] != tourf.Game.STATE_LIVE and form_data['state'] != tourf.Game.STATE_DONE:
			errors.append('state must be STATE_PREP, STATE_LIVE, or STATE_DONE')

	if 'topWins' in form_data and (not isinstance(form_data['topWins'], int) or form_data['topWins'] < 0):
		errors.append('topWins must be a positive integer')

	if 'bottomWins' in form_data and (not isinstance(form_data['bottomWins'], int) or form_data['bottomWins'] < 0):
		errors.append('bottomWins must be a positive integer')

	if 'topTeamId' in form_data and not isinstance(form_data['topTeamId'], int):
		errors.append('topTeamId must be a string')

	if 'bottomTeamId' in form_data and not isinstance(form_data['bottomTeamId'], int):
		errors.append('bottomTeamId must be a string')

	if 'topTeam' in form_data:
		if isinstance(form_data['topTeam'], dict):
			if 'eventDivisionTeamId' not in form_data['topTeam']:
				errors.append('eventDivisionTeamId is missing from topTeam')
		elif form_data['topTeam'] is not None:
			errors.append('topTeam must be an object or null')

	if 'bottomTeam' in form_data:
		if isinstance(form_data['bottomTeam'], dict):
			if 'eventDivisionTeamId' not in form_data['bottomTeam']:
				errors.append('eventDivisionTeamId is missing from bottomTeam')
		elif form_data['bottomTeam'] is not None:
			errors.append('bottomTeam must be an object or null')

	return errors if len(errors) > 0 else False

def _normalize_game_form(form_data, game=None):
	""" Normalize game dict

	"""
	errors = list()

	if 'state' not in form_data:
		form_data['state'] = tourf.Game.STATE_PREP

	if 'topTeam' in form_data:
		if isinstance(form_data['topTeam'], dict):
			form_data['topTeamId'] = form_data['topTeam']['eventDivisionTeamId']
	else:
		form_data['topTeam'] = None

	if 'bottomTeam' in form_data:
		if isinstance(form_data['bottomTeam'], dict):
			form_data['bottomTeamId'] = form_data['bottomTeam']['eventDivisionTeamId']
	else:
		form_data['bottomTeam'] = None

	if 'topTeamId' in form_data:
		if game:
			if game.top_team_id == form_data['topTeamId']:
				form_data['topTeam'] = game.top_team
			else:
				errors.append('topTeamId does not match game.top_team')
		else:
			try:
				form_data['topTeam'] = league.EventDivisionTeam.objects.get(pk=form_data['topTeamId'])
			except league.EventDivisionTeam.DoesNotExist:
				errors.append('topTeamId could not be found')

	if 'bottomTeamId' in form_data:
		if game:
			if game.bottom_team_id == form_data['bottomTeamId']:
				form_data['bottomTeam'] = game.bottom_team
			else:
				errors.append('bottomTeamId does not match game.bottom_team')
		else:
			try:
				form_data['bottomTeam'] = league.EventDivisionTeam.objects.get(pk=form_data['bottomTeamId'])
			except league.EventDivisionTeam.DoesNotExist:
				errors.append('bottomTeamId could not be found')

	return errors if len(errors) > 0 else False


@csrf_exempt
def teams(request, team_id=None):
	""" EventDivisionTeam endpoints

	:param team_id: ID of the team
	:type team_id: int

	"""
	if team_id:
		try:
			team = league.EventDivisionTeam.objects.get(pk=team_id)
		except league.EventDivisionTeam.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That team does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(team)})
		elif request.method == 'PATCH':
			if not request.user.is_authenticated:
				return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

			form_data = json.loads(request.body)

			# Validate form_data

			errors = _validate_team_form(form_data)

			if errors:
				return JsonResponse({'success': False, 'message': 'Invalid team data', 'error': errors}, status=400)

			# Update EventDivisionTeam object

			if 'seed' in form_data:
				team.place = form_data['seed']

			if 'isCheckedIn' in form_data:
				team.is_checked_in = form_data['isCheckedIn']

			try:
				team.save()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to update team object', 'error': str(e)}, status=500)

			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(team), 'error': errors})
	elif request.method == 'PATCH':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_team_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid team data', 'error': errors}, status=400)

		# Update the EventDivisionTeam objects

		event_division_team_ids = list()
		event_division_team_hash = dict()

		for form_team in form_data['teams']:
			event_division_team_ids.append(form_team['eventDivisionTeamId'])
			event_division_team_hash[form_team['eventDivisionTeamId']] = form_team

		event_division_teams = list(league.EventDivisionTeam.objects.filter(pk__in=event_division_team_ids))

		try:
			with transaction.atomic():
				for event_division_team in event_division_teams:
					if 'seed' in event_division_team_hash[event_division_team.pk]:
						event_division_team.place = event_division_team_hash[event_division_team.pk]['seed']

					if 'isCheckedIn' in event_division_team_hash[event_division_team.pk]:
						event_division_team.is_checked_in = event_division_team_hash[event_division_team.pk]['isCheckedIn']

					event_division_team.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to update EventDivisionTeam objects', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(event_division_teams), 'error': errors})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_team_form(form_data):
	""" Validate team dict

	"""
	errors = list()

	if 'teams' in form_data:
		if isinstance(form_data['teams'], list):
			for form_team in form_data['teams']:
				team_errors = _validate_team_form(form_team)

				if team_errors:
					errors += team_errors
		else:
			errors.append('teams must be an array')

	if 'eventDivisionTeamId' in form_data and not isinstance(form_data['eventDivisionTeamId'], int):
		errors.append('eventDivisionTeamId must be a positive integer')

	if 'seed' in form_data and (not isinstance(form_data['seed'], int) or form_data['seed'] < 0):
		errors.append('seed must be a positive integer')

	if 'isCheckedIn' in form_data and not isinstance(form_data['isCheckedIn'], bool):
		errors.append('isCheckedIn must be a bool')

	return errors if len(errors) > 0 else False


@csrf_exempt
def players(request, player_id=None):
	""" EventDivisionTeamPlayer endpoints

	:param player_id: ID of the player
	:type player_id: int

	"""
	if player_id:
		try:
			player = league.EventDivisionTeamPlayer.objects.get(pk=player_id)
		except league.EventDivisionTeamPlayer.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That player does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(player)})
		elif request.method == 'PATCH':
			if not request.user.is_authenticated:
				return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

			form_data = json.loads(request.body)

			# Validate form_data

			errors = _validate_player_form(form_data)

			if errors:
				return JsonResponse({'success': False, 'message': 'Invalid player data', 'error': errors}, status=400)

			# Update EventDivisionTeamPlayer object

			if 'isCheckedIn' in form_data:
				player.is_checked_in = form_data['isCheckedIn']

			try:
				player.save()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to update player object', 'error': str(e)}, status=500)

			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(player), 'error': errors})
	elif request.method == 'PATCH':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_player_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid player data', 'error': errors}, status=400)

		# Update the EventDivisionTeamPlayer objects

		event_division_team_player_ids = list()
		event_division_team_player_hash = dict()

		for form_player in form_data['players']:
			event_division_team_player_ids.append(form_player['eventDivisionTeamPlayerId'])
			event_division_team_player_hash[form_player['eventDivisionTeamPlayerId']] = form_player

		event_division_team_players = list(league.EventDivisionTeamPlayer.objects.filter(pk__in=event_division_team_player_ids))

		try:
			with transaction.atomic():
				for event_division_team_player in event_division_team_players:
					if 'isCheckedIn' in event_division_team_player_hash[event_division_team_player.pk]:
						event_division_team_player.is_checked_in = event_division_team_player_hash[event_division_team_player.pk]['isCheckedIn']

					event_division_team_player.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to update EventDivisionTeamPlayer objects', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': tourf.TourfSerializer.serialize(event_division_team_players), 'error': errors})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_player_form(form_data):
	""" Validate player dict

	"""
	errors = list()

	if 'players' in form_data:
		if isinstance(form_data['players'], list):
			for form_player in form_data['players']:
				player_errors = _validate_player_form(form_player)

				if player_errors:
					errors += player_errors
		else:
			errors.append('players must be an array')

	if 'eventDivisionTeamPlayerId' in form_data and not isinstance(form_data['eventDivisionTeamPlayerId'], int):
		errors.append('eventDivisionTeamPlayerId must be a positive integer')

	if 'isCheckedIn' in form_data and not isinstance(form_data['isCheckedIn'], bool):
		errors.append('isCheckedIn must be a bool')

	return errors if len(errors) > 0 else False


@csrf_exempt
def robins(request, bracket_id=None):
	""" Round-robin endpoints

	:param bracket_id: ID of the bracket
	:type bracket_id: str

	"""
	if not request.user.is_authenticated:
		return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

	if request.method == 'POST':
		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_bracket_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid bracket data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_bracket_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize bracket data', 'error': errors}, status=400)

		# Remove existing Bracket

		try:
			round_robin = tourf.Bracket.objects.get(
				bracket_type=tourf.Bracket.TYPE_ROBIN,
				event_division=form_data['event_division'])
		except tourf.Bracket.DoesNotExist:
			round_robin = None

		if round_robin:
			try:
				round_robin.delete()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to delete existing round_robin', 'error': errors}, status=500)

		# Build Team objects

		data = {
			'teams': list(),
		}

		season_division_teams = league.SeasonDivisionTeam.objects.select_related('team').filter(
			pk__in=[event_division_team.season_division_team_id for event_division_team in form_data['event_division_teams']])

		season_division_team_hash = {
			season_division_team.pk: {
				'team': league.LeagueSerializer.serialize(season_division_team.team),
				'season_division_team': league.LeagueSerializer.serialize(season_division_team),
			} for season_division_team in season_division_teams
		}

		for event_division_team in form_data['event_division_teams']:
			team_datum = season_division_team_hash[event_division_team.season_division_team_id]
			team_datum['event_division_team'] = league.LeagueSerializer.serialize(event_division_team)
			data['teams'].append(team_datum)

		# Create the Bracket

		round_robin = tourf.Bracket(bracket_type=tourf.Bracket.TYPE_ROBIN, event_division=form_data['event_division'])

		try:
			round_robin.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create round_robin', 'error': str(e)}, status=500)

		data['round_robin'] = {
			'id': round_robin.pk,
			'date_updated': round_robin.date_updated,
			'date_created': round_robin.date_created,
			'event_division_id': round_robin.event_division_id,
		}

		# Flat round-robin is straightforward

		if 'courtTotal' not in form_data or 'refereeCount' not in form_data or 'poolNumber' not in form_data:
			data['round_robin']['rounds'] = tourf.make_round_robin(team_list=form_data['event_division_teams'])
		else:
			data['round_robin']['rounds'] = tourf.make_managed_round_robin(team_list=form_data['event_division_teams'], court_total=form_data['courtTotal'], referee_count=form_data['refereeCount'], pool_number=form_data['poolNumber'])

		# Save the Game objects

		try:
			tourf.Game.objects.bulk_create(_extract_games(data['round_robin']['rounds'], round_robin))
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create Game objects', 'error': str(e)}, status=500)

		# Prepare for payload

		data['round_robin']['rounds'] = tourf.TourfSerializer.serialize(data['round_robin']['rounds'])

		# Send a channel_layer update

		channel_layer = channels.layers.get_channel_layer()

		async_to_sync(channel_layer.group_send)('event_%s' % round_robin.event_division.event_id, {
			'type': 'robin.update',
			'data': tourf.TourfSerializer.dater(data['round_robin']),
		})

		return JsonResponse({
			'success': True,
			'data': data,
		})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def brackets(request, bracket_id=None):
	""" Bracket endpoints

	:param bracket_id: ID of the bracket
	:type bracket_id: int

	"""
	if bracket_id:
		try:
			bracket = tourf.Bracket.objects.get(pk=bracket_id)
		except tourf.Bracket.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That bracket does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': tourf.TourfSerializer.bracket(bracket=bracket, fill_bracket=request.GET.get('fillBracket') == 'true')})
	elif request.method == 'POST':
		if not request.user.is_authenticated:
			return JsonResponse({'success': False, 'message': 'Not authorized for %s' % request.method}, status=401)

		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_bracket_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid bracket data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_bracket_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize bracket data', 'error': errors}, status=400)

		# Remove existing brackets

		brackets = tourf.Bracket.objects.filter(
				bracket_type__in=[tourf.Bracket.TYPE_WINNER, tourf.Bracket.TYPE_LOSER, tourf.Bracket.TYPE_FINAL],
				event_division=form_data['event_division'])

		try:
			brackets.delete()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to delete brackets', 'error': str(e)}, status=500)

		# Create brackets

		winners_bracket = tourf.Bracket(bracket_type=tourf.Bracket.TYPE_WINNER, event_division=form_data['event_division'])

		try:
			winners_bracket.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create winners_bracket', 'error': str(e)}, status=500)

		data = {
			'winners_bracket': {
				'id': winners_bracket.pk,
				'date_updated': winners_bracket.date_updated,
				'date_created': winners_bracket.date_created,
				'rounds': tourf.make_winners_bracket(team_list=form_data['event_division_teams']),
				'event_division_id': winners_bracket.event_division_id,
			},
		}

		games = _extract_games(data['winners_bracket']['rounds'], winners_bracket)

		if form_data['isDoubleElimination']:
			losers_bracket = tourf.Bracket(bracket_type=tourf.Bracket.TYPE_LOSER, event_division=form_data['event_division'])

			try:
				losers_bracket.save()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to create losers_bracket', 'error': str(e)}, status=500)

			data['losers_bracket'] = {
				'id': losers_bracket.pk,
				'date_updated': losers_bracket.date_updated,
				'date_created': losers_bracket.date_created,
				'rounds': tourf.make_losers_bracket(winners_bracket=data['winners_bracket']['rounds'], team_list=form_data['event_division_teams']),
				'event_division_id': losers_bracket.event_division_id,
			}

			finals_bracket = tourf.Bracket(bracket_type=tourf.Bracket.TYPE_FINAL, event_division=form_data['event_division'])

			try:
				finals_bracket.save()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to create finals_bracket', 'error': str(e)}, status=500)

			data['finals_bracket'] = {
				'id': finals_bracket.pk,
				'date_updated': finals_bracket.date_updated,
				'date_created': finals_bracket.date_created,
				'rounds': tourf.make_final_bracket(winners_bracket=data['winners_bracket']['rounds'], losers_bracket=data['losers_bracket']['rounds']),
				'event_division_id': finals_bracket.event_division_id,
			}

			games = games + _extract_games(data['losers_bracket']['rounds'], losers_bracket) + _extract_games(data['finals_bracket']['rounds'], finals_bracket)
			tourf.set_losers_flow(winners_bracket=data['winners_bracket']['rounds'], losers_bracket=data['losers_bracket']['rounds'])

		# Save all the Game objects

		try:
			with transaction.atomic():
				for game in reversed(games):
					game.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create Game objects', 'error': str(e)}, status=500)

		# Prepare for payload

		fill_bracket = request.GET.get('fillBracket') == 'true'

		data['winners_bracket']['rounds'] = tourf.sort_rounds(rounds=tourf.TourfSerializer.serialize(data['winners_bracket']['rounds']), fill_type=1 if fill_bracket else 0)

		if form_data['isDoubleElimination']:
			data['losers_bracket']['rounds'] = tourf.sort_rounds(rounds=tourf.TourfSerializer.serialize(data['losers_bracket']['rounds']), fill_type=2 if fill_bracket else 0)
			data['finals_bracket']['rounds'] = tourf.TourfSerializer.serialize(data['finals_bracket']['rounds'])

		# Send a channel_layer update

		channel_layer = channels.layers.get_channel_layer()

		async_to_sync(channel_layer.group_send)('event_%s' % winners_bracket.event_division.event_id, {
			'type': 'bracket.update',
			'data': tourf.TourfSerializer.dater(data, recursive=True),
		})

		return JsonResponse({
			'success': True,
			'data': data,
		})
	elif request.method == 'GET':
		fill_bracket = request.GET.get('fillBracket') == 'true'

		return JsonResponse({
			'success': True,
			'data': [tourf.TourfSerializer.bracket(bracket=bracket, fill_bracket=fill_bracket) for bracket in tourf.Bracket.objects.order_by('-date_created')],
		})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _extract_games(rounds, bracket=None):
	""" Extract games from a list of rounds

	"""
	games = list()

	if not isinstance(bracket, tourf.Bracket):
		bracket = None

	for bround in reversed(rounds):
		for game in bround:
			game.bracket = bracket
			games.append(game)

	return games

def _validate_bracket_form(form_data):
	""" Validate bracket dict

	"""
	errors = list()

	if 'teams' in form_data:
		if not isinstance(form_data['teams'], list):
			errors.append('teams should be an array')
		else:
			for team_index, team in enumerate(form_data['teams']):
				if 'eventDivisionTeamId' not in team or team['eventDivisionTeamId'] and not isinstance(team['eventDivisionTeamId'], int):
					errors.append('teams[%s].eventDivisionTeamId should be a positive integer' % team_index)
				if 'seed' not in team or not isinstance(team['seed'], int) or team['seed'] < 1:
					errors.append('teams[%s].seed should be a positive integer' % team_index)

	if 'courtTotal' in form_data and (not isinstance(form_data['courtTotal'], int) or form_data['courtTotal'] < 1):
		errors.append('courtTotal should be a positive integer')

	if 'refereeCount' in form_data and (not isinstance(form_data['refereeCount'], int) or form_data['refereeCount'] < 1):
		errors.append('refereeCount should be a positive integer')

	if 'poolNumber' in form_data and (not isinstance(form_data['poolNumber'], int) or form_data['poolNumber'] < 1):
		errors.append('poolNumber should be a positive integer')

	return errors if len(errors) > 0 else False

def _normalize_bracket_form(form_data):
	""" Normalize bracket dict

	"""
	errors = list()

	if 'eventDivisionId' in form_data:
		try:
			form_data['event_division'] = league.EventDivision.objects.get(pk=form_data['eventDivisionId'])
		except league.EventDivision.DoesNotExist:
			errors.append('Division not found')
			form_data['event_division'] = None

	if 'teams' in form_data and isinstance(form_data['teams'], list):
		team_ids = list()
		team_id_place_hash = dict()

		for team in form_data['teams']:
			if 'eventDivisionTeamId' in team and isinstance(team['eventDivisionTeamId'], int):
				team_ids.append(team['eventDivisionTeamId'])
				team_id_place_hash[team['eventDivisionTeamId']] = team['seed']

		found_teams = list(league.EventDivisionTeam.objects.filter(pk__in=team_ids))

		try:
			with transaction.atomic():
				for found_team in found_teams:
					found_team.place = team_id_place_hash[found_team.pk]
					found_team.save()
		except Exception as e:
			errors.append('Failed to update EventDivisionTeam object: %s' % str(e))

		if len(found_teams) != len(team_ids):
			errors.append('Missing team_ids')

		form_data['event_division_teams'] = found_teams

	if 'isDoubleElimination' in form_data:
		if isinstance(form_data['isDoubleElimination'], str):
			form_data['isDoubleElimination'] = form_data['isDoubleElimination'].strip().lower() == 'true'
		else:
			form_data['isDoubleElimination'] = bool(form_data['isDoubleElimination'])

	return errors if len(errors) > 0 else False


def _make_template_path(file_name):
	""" Take a file name and make it work against the template path

	:param file_name: File name to work with
	:type file_name: str
	:returns: str

	"""
	return 'tourf/%s' % file_name
