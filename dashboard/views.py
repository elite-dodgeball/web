"""
.. module:: views
   :platform: Unix
   :synopsis: Contains the views

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import numbers
import simplejson as json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from client import models as client
from league import models as league
from reggie import models as reggie


@login_required
def index(request):
	""" Either redirect or render dashboard

	:returns: render

	"""
	return render(request, _make_template_path('index.html'))


@csrf_exempt
def sender(request, invite_id):
	""" Send the invitation email

	:param invite_id: ID of the invite
	:type invite_id: str

	"""
	if request.method == 'POST':
		form_data = json.loads(request.body)

		try:
			invite = reggie.Invite.objects.select_related('event', 'team').get(pk=invite_id)
		except reggie.Invite.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'Invite does not exist'}, status=404)

		email_address = invite.team.email_address

		if form_data['emailAddress']:
			email_address = form_data['emailAddress']

		email_body = invite.send_email(email_address=email_address)

		return JsonResponse({'success': True, 'message': email_body})

	return JsonResponse({'success': False, 'message': '%s is not allowed' % request.method}, status=405)


@csrf_exempt
def division_invites(request, division_invite_id=None):
	""" DivisionInvite endpoints

	:param division_invite_id: ID of the division_invite
	:type division_invite_id: int

	"""
	if division_invite_id:
		try:
			division_invite = reggie.DivisionInvite.objects.get(pk=division_invite_id)
		except reggie.DivisionInvite.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That division_invite does not exist'}, status=404)

		if request.method == 'DELETE':
			try:
				division_invite.delete()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to delete division_invite', 'error': str(e)}, status=500)

		if request.method == 'GET' or request.method == 'DELETE':
			return JsonResponse({'success': True, 'data': {
				'division_invite': reggie.ReggieSerializer.serialize(division_invite),
			}})

	elif request.method == 'POST':
		form_data = json.loads(request.body)

		# Validate form_data

		errors = _validate_division_invite_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid division_invite data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_division_invite_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize division_invite data', 'error': errors}, status=400)

		# Create DivisionInvite

		division_invite = reggie.DivisionInvite(
			invite=form_data['invite'],
			division=form_data['division'],
			is_claimed=form_data['isClaimed'],
			discount=form_data['discount'])

		try:
			division_invite.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to save division_invite', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': {
			'invite': reggie.ReggieSerializer.serialize(form_data['invite']),
			'division_invite': reggie.ReggieSerializer.serialize(division_invite),
		}})

	elif request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'division_invites': reggie.ReggieSerializer.serialize(reggie.DivisionInvite.objects.all().order_by('invite')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_division_invite_form(form_data):
	""" Validate division_invite dict

	"""
	errors = list()

	if 'inviteId' in form_data:
		if not isinstance(form_data['inviteId'], str):
			errors.append('inviteId must be a str')
	elif 'teamId' in form_data and 'eventId' in form_data:
		if not isinstance(form_data['teamId'], int):
			errors.append('teamId must be an int')
		if not isinstance(form_data['eventId'], int):
			errors.append('eventId must be an int')
	else:
		errors.append('teamId and eventId are required without inviteId')

	if 'divisionId' not in form_data or not isinstance(form_data['divisionId'], int):
		errors.append('divisionId must be an int')

	if 'isClaimed' not in form_data or not isinstance(form_data['isClaimed'], bool):
		errors.append('isClaimed must be an bool')

	if 'discount' not in form_data or not isinstance(form_data['discount'], numbers.Number) or form_data['discount'] < 0:
		errors.append('discount must be a positive Number')

	return errors if len(errors) > 0 else False

def _normalize_division_invite_form(form_data):
	""" Normalize division_invite dict

	"""
	errors = list()

	if 'inviteId' in form_data:
		try:
			form_data['invite'] = reggie.Invite.objects.get(pk=form_data['inviteId'])
		except reggie.Invite.DoesNotExist:
			errors.append('Invite not found')
			form_data['invite'] = None

	if 'eventId' in form_data:
		try:
			form_data['event'] = league.Event.objects.get(pk=form_data['eventId'])
		except league.Event.DoesNotExist:
			errors.append('Event not found')
			form_data['event'] = None

	if 'teamId' in form_data:
		try:
			form_data['team'] = league.Team.objects.get(pk=form_data['teamId'])
		except league.Team.DoesNotExist:
			errors.append('Team not found')
			form_data['team'] = None

	if form_data['event'] and form_data['team']:
		form_data['invite'] = reggie.Invite.objects.filter(event=form_data['event'], team=form_data['team']).first()

		if not form_data['invite']:
			form_data['invite'] = reggie.Invite(event=form_data['event'], team=form_data['team'])

			try:
				form_data['invite'].save()
			except Exception as e:
				errors.append(str(e))

	if 'divisionId' in form_data:
		try:
			form_data['division'] = league.Division.objects.get(pk=form_data['divisionId'])
		except league.Division.DoesNotExist:
			errors.append('Division not found')
			form_data['division'] = None

	return errors if len(errors) > 0 else False


@csrf_exempt
def invites(request, invite_id=None, event_id=None):
	""" Invite endpoints

	:param invite_id: ID of the invite
	:type invite_id: str
	:param event_id: ID of the event
	:type event_id: int

	"""
	if invite_id:
		try:
			invite = reggie.Invite.objects.get(pk=invite_id)
		except reggie.Invite.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That invite does not exist'}, status=404)

		if request.method == 'GET':
			invite = reggie.ReggieSerializer.serialize(invite)
			invite['division_invites'] = reggie.ReggieSerializer.serialize(reggie.DivisionInvite.objects.filter(invite_id=invite['id']))

			return JsonResponse({'success': True, 'data': {
				'invite': invite,
			}})

	if event_id:
		invites = reggie.Invite.objects.filter(event_id=event_id)
	else:
		invites = reggie.Invite.objects.all()

	if request.method == 'GET':
		division_invites = reggie.ReggieSerializer.serialize(reggie.DivisionInvite.objects.filter(invite__in=invites).order_by('is_claimed'))

		invites = reggie.ReggieSerializer.serialize(invites.order_by('team'))
		invite_hash = {}

		for invite in invites:
			invite['division_invites'] = []
			invite_hash[invite['id']] = invite

		for division_invite in division_invites:
			invite_hash[division_invite['invite_id']]['division_invites'].append(division_invite)

		return JsonResponse({'success': True, 'data': {
			'invites': invites,
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def events(request, event_id=None):
	""" Event endpoints

	:param event_id: ID of the event
	:type event_id: int

	"""
	if event_id:
		try:
			event = league.Event.objects.get(pk=event_id)
		except league.Event.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That event does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'event': league.LeagueSerializer.serialize(event),
			}})

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'events': league.LeagueSerializer.serialize(league.Event.objects.all().order_by('-datetime')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def event_divisions(request, event_id=None, division_id=None, event_division_id=None):
	""" EventDivision endpoints

	:param event_id: ID of the event
	:type event_id: int
	:param division_id: ID of the division
	:type division_id: int
	:param event_division_id: ID of the event_division
	:type event_division_id: int

	"""
	if event_division_id or (event_id and division_id):
		if event_division_id:
			event_division = league.EventDivision.objects.filter(pk=event_division_id).first()
		else:
			event_division = league.EventDivision.objects.filter(event_id=event_id, division_id=division_id).first()

		if not event_division:
			return JsonResponse({'success': False, 'message': 'That event_division does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'event_division': league.LeagueSerializer.serialize(event_division),
			}})

	if event_id:
		event_divisions = league.EventDivision.objects.filter(event_id=event_id)
	else:
		event_divisions = league.EventDivision.objects.all()

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'event_divisions': league.LeagueSerializer.serialize(event_divisions.order_by('team_count')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def event_division_team_players(request, event_division_team_player_id=None, event_division_team_id=None, season_division_team_player_id=None):
	""" EventDivisionTeamPlayer endpoints

	:param event_division_team_player_id: ID of the event_division_team_player
	:type event_division_team_player_id: int
	:param event_division_team_id: ID of the event_division_team
	:type event_division_team_id: int
	:param season_division_team_player_id: ID of the season_division_team_player
	:type season_division_team_player_id: int

	"""
	if event_division_team_player_id or (event_division_team_id and season_division_team_player_id):
		if event_division_team_player_id:
			event_division_team_player = league.EventDivisionTeamPlayer.objects.filter(pk=event_division_team_player_id).first()
		else:
			event_division_team_player = league.EventDivisionTeamPlayer.objects.filter(event_division_team_id=event_division_team_id, season_division_team_player_id=season_division_team_player_id).first()

		if not event_division_team_player:
			return JsonResponse({'success': False, 'message': 'That event_division_team_player does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'event_division_team_player': league.LeagueSerializer.serialize(event_division_team_player),
			}})

	if event_division_team_id:
		event_division_team_players = league.EventDivisionTeamPlayer.objects.filter(event_division_team_id=event_division_team_id)
	else:
		event_division_team_players = league.EventDivisionTeamPlayer.objects.all()

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'event_division_team_players': league.LeagueSerializer.serialize(event_division_team_players.order_by('-is_captain', '-is_referee', 'event_division_team')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def event_division_teams(request, event_division_id=None, season_division_team_id=None, event_division_team_id=None):
	""" EventDivisionTeam endpoints

	:param event_division_id: ID of the event_division
	:type event_division_id: int
	:param season_division_team_id: ID of the season_division_team
	:type season_division_team_id: int
	:param event_division_team_id: ID of the event_division_team
	:type event_division_team_id: int

	"""
	if event_division_team_id or (event_division_id and season_division_team_id):
		if event_division_team_id:
			event_division_team = league.EventDivisionTeam.objects.filter(pk=event_division_team_id).first()
		else:
			event_division_team = league.EventDivisionTeam.objects.filter(event_division_id=event_division_id, season_division_team_id=season_division_team_id).first()

		if not event_division_team:
			return JsonResponse({'success': False, 'message': 'That event_division_team does not exist'}, status=404)

		if request.method == 'DELETE':
			try:
				event_division_team.delete()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to delete event_division_team', 'error': str(e)}, status=500)

		if request.method == 'GET' or request.method == 'DELETE':
			return JsonResponse({'success': True, 'data': {
				'event_division_team': league.LeagueSerializer.serialize(event_division_team),
			}})

	elif request.method == 'POST':
		form_data = json.loads(request.body)

		if event_division_id:
			form_data['eventDivisionId'] = event_division_id

		if season_division_team_id:
			form_data['seasonDivisionTeamId'] = season_division_team_id

		# Validate form_data

		errors = _validate_event_division_team_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid event_division_team data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_event_division_team_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize event_division_team data', 'error': errors}, status=400)

		# Create EventDivisionTeam

		event_division_team = league.EventDivisionTeam(
			event_division=form_data['eventDivision'],
			season_division_team=form_data['seasonDivisionTeam'],
			transaction_id=form_data['transactionId'],
			place=form_data['place'])

		# Update DivisionInvite

		try:
			division_invite = reggie.get_division_invite(event_division_team=event_division_team)
		except reggie.DivisionInvite.DoesNotExist:
			division_invite = None

		# Call atomic save

		try:
			with transaction.atomic():
				if division_invite and not division_invite.is_claimed:
					division_invite.is_claimed = True
					division_invite.save()

				event_division_team.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to create EventDivisionTeam', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': {
			'event_division_team': league.LeagueSerializer.serialize(event_division_team),
		}})

	if event_division_id:
		event_division_teams = league.EventDivisionTeam.objects.filter(event_division_id=event_division_id)
	else:
		event_division_teams = league.EventDivisionTeam.objects.all()

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'event_division_teams': league.LeagueSerializer.serialize(event_division_teams.order_by('place')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_event_division_team_form(form_data):
	""" Validate event_division_team dict

	"""
	errors = list()

	if 'eventDivisionId' not in form_data or not isinstance(form_data['eventDivisionId'], int):
		errors.append('eventDivisionId must be an int')

	if 'seasonDivisionTeamId' not in form_data or not isinstance(form_data['seasonDivisionTeamId'], int):
		errors.append('seasonDivisionTeamId must be an int')

	if 'transactionId' in form_data and not isinstance(form_data['transactionId'], str):
		errors.append('transactionId must be a str')

	if 'place' in form_data and (not isinstance(form_data['place'], int) or form_data['place'] < 1):
		errors.append('place must be a positive int')

	return errors if len(errors) > 0 else False

def _normalize_event_division_team_form(form_data):
	""" Normalize event_division_team dict

	"""
	errors = list()

	if 'eventDivisionId' in form_data:
		try:
			form_data['eventDivision'] = league.EventDivision.objects.get(pk=form_data['eventDivisionId'])
		except league.EventDivision.DoesNotExist:
			errors.append('EventDivision not found')
			form_data['eventDivision'] = None

	if 'seasonDivisionTeamId' in form_data:
		try:
			form_data['seasonDivisionTeam'] = league.SeasonDivisionTeam.objects.get(pk=form_data['seasonDivisionTeamId'])
		except league.SeasonDivisionTeam.DoesNotExist:
			errors.append('SeasonDivisionTeam not found')
			form_data['seasonDivisionTeam'] = None

	if 'transactionId' not in form_data:
		form_data['transactionId'] = None

	if 'place' not in form_data:
		form_data['place'] = None

	return errors if len(errors) > 0 else False


@csrf_exempt
def teams(request, team_id=None):
	""" Season endpoints

	:param team_id: ID of the team
	:type team_id: int

	"""
	if team_id:
		try:
			team = league.Team.objects.get(pk=team_id)
		except league.Team.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That team does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'team': league.LeagueSerializer.serialize(team),
			}})

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'teams': league.LeagueSerializer.serialize(league.Team.objects.all().order_by('-is_active', 'name')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def players(request, player_id=None):
	""" Season endpoints

	:param player_id: ID of the player
	:type player_id: int

	"""
	if player_id:
		try:
			player = league.Player.objects.get(pk=player_id)
		except league.Player.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That player does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'player': league.LeagueSerializer.serialize(player),
			}})

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'players': league.LeagueSerializer.serialize(league.Player.objects.all().order_by('-is_active', 'name')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def regions(request, region_id=None):
	""" Season endpoints

	:param region_id: ID of the region
	:type region_id: int

	"""
	if region_id:
		try:
			region = league.Region.objects.get(pk=region_id)
		except league.Region.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That region does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'region': league.LeagueSerializer.serialize(region),
			}})

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'regions': league.LeagueSerializer.serialize(league.Region.objects.all().order_by('-is_active', 'name')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def divisions(request, division_id=None, season_id=None, team_id=None):
	""" Season endpoints

	:param division_id: ID of the division
	:type division_id: int

	"""
	if division_id:
		try:
			division = league.Division.objects.get(pk=division_id)
		except league.Division.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That division does not exist'}, status=404)

		if request.method == 'GET':
			return JsonResponse({'success': True, 'data': {
				'division': league.LeagueSerializer.serialize(division),
			}})

	if request.method == 'GET':
		if season_id and team_id:
			season_division_teams = league.SeasonDivisionTeam.objects.filter(season_id=season_id, team_id=team_id)
			divisions = league.Division.objects.filter(pk__in=[season_division_team.division_id for season_division_team in season_division_teams])
		else:
			divisions = league.Division.objects.all()

		return JsonResponse({'success': True, 'data': {
			'divisions': league.LeagueSerializer.serialize(divisions.order_by('-is_active', '-is_primary', 'name')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


@csrf_exempt
def season_division_teams(request, season_division_team_id=None, season_id=None, division_id=None, team_id=None):
	""" SeasonDivisionTeam endpoints

	:param season_division_team_id: ID of the SeasonDivisionTeam
	:type season_division_team_id: int
	:param season_id: ID of the season
	:type season_id: int
	:param division_id: ID of the division
	:type division_id: int
	:param team_id: ID of the team
	:type team_id: int

	"""
	if season_division_team_id or (season_id and division_id and team_id):
		if season_division_team_id:
			season_division_team = league.SeasonDivisionTeam.objects.filter(pk=season_division_team_id).first()
		else:
			season_division_team = league.SeasonDivisionTeam.objects.filter(season_id=season_id, division_id=division_id, team_id=team_id).first()

		if not season_division_team:
			return JsonResponse({'success': False, 'message': 'That season_division_team does not exist'}, status=404)

		if request.method == 'DELETE':
			try:
				season_division_team.delete()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to delete season_division_team', 'error': str(e)}, status=500)

		if request.method == 'GET' or request.method == 'DELETE':
			return JsonResponse({'success': True, 'data': {
				'season_division_team': league.LeagueSerializer.serialize(season_division_team),
			}})

	elif request.method == 'POST':
		form_data = json.loads(request.body)

		if season_id:
			form_data['seasonId'] = season_id

		if division_id:
			form_data['divisionId'] = division_id

		if team_id:
			form_data['teamId'] = team_id

		# Validate form_data

		errors = _validate_season_division_team_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid season_division_team data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_season_division_team_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize season_division_team data', 'error': errors}, status=400)

		# Create SeasonDivisionTeam

		season_division_team = league.SeasonDivisionTeam(season=form_data['season'], division=form_data['division'], team=form_data['team'])

		try:
			season_division_team.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to save season_division_team', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': {
			'season_division_team': league.LeagueSerializer.serialize(season_division_team),
		}})

	if season_id and division_id:
		season_division_teams = league.SeasonDivisionTeam.objects.filter(season_id=season_id, division_id=division_id)
	else:
		season_division_teams = league.SeasonDivisionTeam.objects.all()

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'season_division_teams': league.LeagueSerializer.serialize(season_division_teams.order_by('-season', 'division')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_season_division_team_form(form_data):
	""" Validate season_division_team dict

	"""
	errors = list()

	if 'seasonId' not in form_data or not isinstance(form_data['seasonId'], int):
		errors.append('seasonId must be an int')

	if 'divisionId' not in form_data or not isinstance(form_data['divisionId'], int):
		errors.append('divisionId must be an int')

	if 'teamId' not in form_data or not isinstance(form_data['teamId'], int):
		errors.append('teamId must be an int')

	return errors if len(errors) > 0 else False

def _normalize_season_division_team_form(form_data):
	""" Normalize season_division_team dict

	"""
	errors = list()

	if 'seasonId' in form_data:
		try:
			form_data['season'] = league.Season.objects.get(pk=form_data['seasonId'])
		except league.Season.DoesNotExist:
			errors.append('Season not found')
			form_data['season'] = None

	if 'divisionId' in form_data:
		try:
			form_data['division'] = league.Division.objects.get(pk=form_data['divisionId'])
		except league.Division.DoesNotExist:
			errors.append('Division not found')
			form_data['division'] = None

	if 'teamId' in form_data:
		try:
			form_data['team'] = league.Team.objects.get(pk=form_data['teamId'])
		except league.Team.DoesNotExist:
			errors.append('Team not found')
			form_data['team'] = None

	return errors if len(errors) > 0 else False


@csrf_exempt
def season_division_team_players(request, season_division_team_player_id=None, season_division_team_id=None, player_id=None):
	""" SeasonDivisionTeamPlayer endpoints

	:param season_division_team_player_id: ID of the SeasonDivisionTeamPlayer
	:type season_division_team_player_id: int
	:param season_division_team_id: ID of the SeasonDivisionTeam
	:type season_division_team_id: int
	:param player_id: ID of the Player
	:type player_id: int

	"""
	if season_division_team_player_id or (season_division_team_id and player_id):
		if season_division_team_player_id:
			season_division_team_player = league.SeasonDivisionTeamPlayer.objects.filter(pk=season_division_team_player_id).first()
		else:
			season_division_team_player = league.SeasonDivisionTeamPlayer.objects.filter(season_division_team_id=season_division_team_id, player_id=player_id).first()

		if not season_division_team_player:
			return JsonResponse({'success': False, 'message': 'That season_division_team_player does not exist'}, status=404)

		if request.method == 'DELETE':
			try:
				season_division_team_player.delete()
			except Exception as e:
				return JsonResponse({'success': False, 'message': 'Failed to delete season_division_team_player', 'error': str(e)}, status=500)

		if request.method == 'GET' or request.method == 'DELETE':
			return JsonResponse({'success': True, 'data': {
				'season_division_team_player': league.LeagueSerializer.serialize(season_division_team_player),
			}})

	elif request.method == 'POST':
		form_data = json.loads(request.body)

		if player_id:
			form_data['playerId'] = player_id

		# Validate form_data

		errors = _validate_season_division_team_player_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Invalid season_division_team_player data', 'error': errors}, status=400)

		# Normalize form_data

		errors = _normalize_season_division_team_player_form(form_data)

		if errors:
			return JsonResponse({'success': False, 'message': 'Failed to normalize season_division_team_player data', 'error': errors}, status=400)

		# Create SeasonDivisionTeamPlayer

		season_division_team_player = league.SeasonDivisionTeamPlayer(player=form_data['player'], season_division_team=form_data['seasonDivisionTeam'])

		try:
			season_division_team_player.save()
		except Exception as e:
			return JsonResponse({'success': False, 'message': 'Failed to save season_division_team_player', 'error': str(e)}, status=500)

		return JsonResponse({'success': True, 'data': {
			'season_division_team_player': league.LeagueSerializer.serialize(season_division_team_player),
		}})

	if season_division_team_id:
		season_division_team_players = league.SeasonDivisionTeamPlayer.objects.filter(season_division_team_id=season_division_team_id)
	else:
		season_division_team_players = league.SeasonDivisionTeamPlayer.objects.all()

	if request.method == 'GET':
		return JsonResponse({'success': True, 'data': {
			'season_division_team_players': league.LeagueSerializer.serialize(season_division_team_players.order_by('season_division_team', 'player')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)

def _validate_season_division_team_player_form(form_data):
	""" Validate season_division_team_player dict

	"""
	errors = list()

	if 'playerId' not in form_data or not isinstance(form_data['playerId'], int):
		errors.append('playerId must be an int')

	if 'seasonDivisionTeamId' not in form_data or not isinstance(form_data['seasonDivisionTeamId'], int):
		errors.append('seasonDivisionTeamId must be an int')

	return errors if len(errors) > 0 else False

def _normalize_season_division_team_player_form(form_data):
	""" Normalize season_division_team_player dict

	"""
	errors = list()

	if 'playerId' in form_data:
		try:
			form_data['player'] = league.Player.objects.get(pk=form_data['playerId'])
		except league.Player.DoesNotExist:
			errors.append('Player not found')
			form_data['player'] = None

	if 'seasonDivisionTeamId' in form_data:
		try:
			form_data['seasonDivisionTeam'] = league.SeasonDivisionTeam.objects.get(pk=form_data['seasonDivisionTeamId'])
		except league.SeasonDivisionTeam.DoesNotExist:
			errors.append('SeasonDivisionTeam not found')
			form_data['seasonDivisionTeam'] = None

	return errors if len(errors) > 0 else False


@csrf_exempt
def seasons(request, season_id=None):
	""" Season endpoints

	:param season_id: ID of the season
	:type season_id: str

	"""
	if request.method == 'GET':
		if season_id:
			if season_id == 'current':
				season = league.Season.current_season()

				if season:
					return JsonResponse({'success': True, 'data': {'season': season}})

			return JsonResponse({'success': False, 'message': 'That season does not exist'}, status=404)

		return JsonResponse({'success': True, 'data': {
			'seasons': league.LeagueSerializer.serialize(league.Season.objects.all().order_by('-year')),
		}})

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


def _make_template_path(file_name):
	""" Take a file name and make it work against the template path

	:param file_name: File name to work with
	:type file_name: str
	:returns: str

	"""
	return 'dashboard/%s' % file_name
