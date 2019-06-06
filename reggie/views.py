"""
.. module:: views
   :platform: Unix
   :synopsis: Contains the views
.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import math
import simplejson as json
from collections import defaultdict

import stripe

from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.http import Http404, JsonResponse

from django.db import transaction
from django.db.models import F

from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from league import models as league
from reggie import models as reggie


REQUIRED_CAPTAINS = 1
REQUIRED_REFEREES = 2


def _validate_registration_form(form_data):
	""" Validate registration dict

	"""
	if not isinstance(form_data, dict):
		return False

	if 'token' not in form_data or not isinstance(form_data['token'], dict) or 'id' not in form_data['token'] or not isinstance(form_data['token']['id'], str):
		return False

	try:
		int(form_data['eventId'])
	except (ValueError, KeyError, TypeError):
		return False

	try:
		int(form_data['teamId'])
	except (ValueError, KeyError, TypeError):
		return False

	if 'inviteId' in form_data and not isinstance(form_data['inviteId'], str):
		return False

	if 'divisions' not in form_data or not isinstance(form_data['divisions'], list) or len(form_data['divisions']) < 1:
		return False

	for form_division in form_data['divisions']:
		if not isinstance(form_division, dict):
			return False

		if 'divisionId' not in form_division or not isinstance(form_division['divisionId'], int):
			return False

		if 'eventDivisionId' not in form_division or not isinstance(form_division['eventDivisionId'], int):
			return False

		if 'players' not in form_division or not isinstance(form_division['players'], list) or len(form_division['players']) < 1:
			return False

		captain_count = 0
		referee_count = 0

		for form_player in form_division['players']:
			if 'isCaptain' in form_player and form_player['isCaptain']:
				captain_count += 1
			if 'isReferee' in form_player and form_player['isReferee']:
				referee_count += 1

		if captain_count != REQUIRED_CAPTAINS or referee_count != REQUIRED_REFEREES:
			return False

	return True


def _normalize_registration_form(form_data):
	""" Normalize form data

	"""
	return form_data


@csrf_exempt
def callback(request):
	""" Ingests registration data with Stripe token

	:param divisions: Divisions to register for with {divisionId, eventDivisionId, players: [{playerId, isCaptain},...]} structure
	:type divisions: list
	:param eventId: ID of the Event we're registering with
	:type eventId: int
	:param teamId: ID of the team registering
	:type teamId: int
	:param inviteId: ID of the invite we're registering against
	:type inviteId: int

	"""
	if request.method == 'POST':
		charge = None
		form_data = json.loads(request.body)

		# Validate the form data at a basic level

		if not _validate_registration_form(form_data):
			return JsonResponse({'success': False, 'message': 'Invalid form data'}, status=400)

		form_data = _normalize_registration_form(form_data)

		# Verify the event is real

		try:
			event = league.Event.objects.get(pk=form_data['eventId'])
		except league.Event.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That event does not exist: %s' % form_data['eventId']}, status=404)

		# Grab the invite

		try:
			invite = reggie.Invite.objects.select_related('team').get(pk=form_data['inviteId'])
		except reggie.Invite.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'That invite does not exist: %s' % form_data['inviteId']}, status=404)

		# Make sure the divisions are real

		related_hash = invite.related_hash(event=event, include_players=True)

		for form_division in form_data['divisions']:
			if form_division['eventDivisionId'] not in related_hash['event_division_hashes']['id']:
				return JsonResponse({'success': False, 'message': 'One or more of your divisions does not exist'}, status=400)

		# Make sure they're form_data['divisions'] matches division_invites

		missing_division_data = list()

		for form_division in form_data['divisions']:
			if form_division['divisionId'] not in related_hash['division_invite_hashes']['division_id']:
				missing_division_data.append(related_hash['event_division_hashes']['division_id'][form_division['divisionId']])

		if len(missing_division_data):
			return JsonResponse({'success': False, 'message': 'Those divisions do not match your invite', 'data': _format_event_json(event, missing_division_data)}, status=400)

		# Is this team already registered?

		division_matches = list()

		for form_division in form_data['divisions']:
			for team_datum in related_hash['event_division_hashes']['id'][form_division['eventDivisionId']]['teams']:
				if team_datum['team'].pk == invite.team_id:
					division_matches.append(related_hash['event_division_hashes']['id'][form_division['eventDivisionId']])
					break

		if len(division_matches):
			return JsonResponse({'success': False, 'message': 'That team has already registered', 'data': _format_event_json(event, division_matches)}, status=400)

		# Verify players

		player_hashes = {
			'id': dict(),
			'season_division_team_player_id': dict(),
		}

		missing_player_data = list()

		for form_division in form_data['divisions']:
			for player_datum in related_hash['season_division_team_hashes']['division_id'][form_division['divisionId']]['players']:
				player_hashes['id'][player_datum['player'].pk] = player_datum
				player_hashes['season_division_team_player_id'][player_datum['season_division_team_player'].pk] = player_datum

			for form_player in form_division['players']:
				if form_player['playerId'] not in player_hashes['id'] or form_player['seasonDivisionTeamPlayerId'] not in player_hashes['season_division_team_player_id'] or player_hashes['id'][form_player['playerId']] != player_hashes['season_division_team_player_id'][form_player['seasonDivisionTeamPlayerId']]:
					missing_player_data.append(form_player)

		if len(missing_player_data):
			return JsonResponse({'success': False, 'message': 'There are mismatched players'}, status=400)

		# Match the charge amount with the stored amount

		stripe.api_key = settings.STRIPE_API_KEY
		total_cost = float(sum(related_hash['event_division_hashes']['id'][form_division['eventDivisionId']]['event_division'].cost for form_division in form_data['divisions']))
		description = '%s Registration - %s' % (event.title, ', '.join([related_hash['event_division_hashes']['id'][form_division['eventDivisionId']]['division'].name for form_division in form_data['divisions']]))

		if total_cost > 0:
			total_cost = math.ceil(((total_cost + settings.STRIPE_SERVICE_FEE) / (1.0 - settings.STRIPE_SERVICE_PERCENT)) * 100)

			try:
				charge = stripe.Charge.create(amount=total_cost, currency='usd', source=form_data['token']['id'], capture=False, description=description)

			# Declined

			except stripe.error.CardError as e:
				err = e.json_body['error']
				return JsonResponse({'success': False, 'message': err['message'], 'type': err['type'], 'code': err['code']}, status=400)

			# Every other error

			except (stripe.error.RateLimitError, stripe.error.InvalidRequestError, stripe.error.AuthenticationError, stripe.error.APIConnectionError, stripe.error.StripeError) as e:
				return JsonResponse({'success': False, 'message': 'We\'ve hit an error in processing your payment', 'error': str(e)}, status=500)

		# Store the EventDivisionTeam and EventDivisionTeamPlayer objects

		reg_teams = []

		try:
			with transaction.atomic():
				for form_division in form_data['divisions']:
					reg_team = league.EventDivisionTeam(
						event_division=related_hash['event_division_hashes']['id'][form_division['eventDivisionId']]['event_division'],
						season_division_team=related_hash['season_division_team_hashes']['division_id'][form_division['divisionId']]['season_division_team'],
						transaction_id=charge.id if charge else None)

					# Too many queries without skip_signal

					reg_team.skip_signal = True
					reg_team.save()

					reg_teams.append(reg_team)

					league.EventDivisionTeamPlayer.objects.bulk_create([
						league.EventDivisionTeamPlayer(
							event_division_team=reg_team,
							season_division_team_player=player_hashes['season_division_team_player_id'][form_player['seasonDivisionTeamPlayerId']]['season_division_team_player'],
							is_captain=form_player['isCaptain'],
							is_referee=form_player['isReferee'])
						for form_player in form_division['players']
					])

				if charge:
					charge.capture()
		except Exception as e:
			if charge:
				stripe.Refund.create(charge=charge.id)

			return JsonResponse({'success': False, 'message': 'We couldn\'t save your registration', 'error': str(e)}, status=500)

		# Save the claimed invites

		reg_team_hash = {reg_team.event_division_id: reg_team for reg_team in reg_teams}

		event_division_ids = set()
		division_invite_ids = set()

		for division_invite in related_hash['division_invite_hashes']['id'].values():
			event_division = related_hash['event_division_hashes']['division_id'][division_invite.division_id]['event_division']

			if event_division.pk in reg_team_hash:
				event_division_ids.add(event_division.pk)
				division_invite_ids.add(division_invite.pk)

		try:
			with transaction.atomic():
				if len(division_invite_ids):
					reggie.DivisionInvite.objects.filter(pk__in=list(division_invite_ids)).update(
						is_claimed=True)

				if len(event_division_ids):
					league.EventDivision.objects.filter(pk__in=list(event_division_ids)).update(
						open_invites=F('open_invites') - 1,
						team_count=F('team_count') + 1)
		except Exception as e:
			# Really, this should also result in a 500 response, but at this point, whatever
			print('FAILED', 'Registration callback', e)

		# Send the confirmation email

		for form_division in form_data['divisions']:
			form_division['name'] = related_hash['event_division_hashes']['division_id'][form_division['divisionId']]['division'].name;

			for form_player in form_division['players']:
				form_player['name'] = player_hashes['id'][form_player['playerId']]['player'].name

		try:
			email_body = render_to_string(_make_template_path('confirmation-email.html'), {
				'event': event,
				'team': invite.team,
				'form_data': form_data,
				'total_cost': total_cost / 100,
			})
			send_mail(
				subject='Registration Confirmation - %s' % event.title,
				message=email_body,
				from_email=settings.DEFAULT_FROM_EMAIL,
				recipient_list=[invite.team.email_address],
				fail_silently=False if settings.DEBUG else True,
				html_message=email_body)
		except Exception as e:
			return JsonResponse({'success': True, 'message': 'There was a problem sending the confirmation email', 'error': str(e)})

		# We're all good!

		return JsonResponse({'success': True})

	# Catchall response for other methods

	return JsonResponse({'success': False, 'message': '%s not allowed' % request.method}, status=405)


def _format_event_json(event, division_data, invite=None, related_hash=None):
	""" Turn an event and its divisions into JSON for the Angular app

	.. todo:: Revise `is_open` calculation

	"""
	division_team_hash = dict()

	if invite and related_hash:
		player_hash = dict()

		for division_datum in division_data:
			if division_datum['division'].pk not in related_hash['season_division_team_hashes']['division_id']:
				continue

			division_team_hash[division_datum['division'].pk] = list()

			for player_datum in related_hash['season_division_team_hashes']['division_id'][division_datum['division'].pk]['players']:
				if player_datum['player'].pk not in player_hash:
					player_hash[player_datum['player'].pk] = league.LeagueSerializer.serialize(player_datum['player'])

				division_team_hash[division_datum['division'].pk].append({
					'player': player_hash[player_datum['player'].pk],
					'season_division_team_player': league.LeagueSerializer.serialize(player_datum['season_division_team_player'])
				})

	json_body = {
		'event': league.LeagueSerializer.serialize(event),
		'divisions': [{
			'event_division_id': division_datum['event_division'].pk,
			'division_id': division_datum['division'].pk,
			'name': division_datum['division'].name,
			'cost': division_datum['event_division'].cost,
			'max_teams': division_datum['event_division'].max_teams,
			'team_count': division_datum['event_division'].team_count,
			'is_open': division_datum['event_division'].is_open,
			'players': division_team_hash[division_datum['division'].pk] if division_datum['division'].pk in division_team_hash else list(),
		} for division_datum in division_data],
	}

	if isinstance(invite, reggie.Invite):
		json_body['invite'] = {
			'id': str(invite.pk),
			'team': league.LeagueSerializer.serialize(invite.team),
		}

	return json_body


def register(request, event_id, invite_id=None):
	""" Serve up the register page

	:param event_id: ID of the event to show
	:type event_id: int
	:param event_id: ID of the invite
	:type event_id: int
	:returns: render

	"""
	try:
		event = league.Event.objects.get(pk=event_id)
	except league.Event.DoesNotExist:
		raise Http404

	if not invite_id:
		return render(request, _make_template_path('register.html'), {
			'event': event,
			'empty_invite': True,
			'json': json.dumps({
				'event': league.LeagueSerializer.serialize(event),
			}, default=date_handler),
		})

	try:
		invite = reggie.Invite.objects.select_related('team').get(pk=invite_id)
	except (reggie.Invite.DoesNotExist, ValidationError):
		return render(request, _make_template_path('register.html'), {
			'event': event,
			'invalid_invite': invite_id,
			'json': json.dumps({
				'event': league.LeagueSerializer.serialize(event),
			}, default=date_handler),
		})

	related_hash = invite.related_hash(event=event, include_players=True)

	return render(request, _make_template_path('register.html'), {
		'event': event,
		'now': timezone.now(),
		'json': json.dumps(_format_event_json(
			event=event,
			division_data=list(related_hash['event_division_hashes']['id'].values()),
			invite=invite,
			related_hash=related_hash), default=date_handler),
		'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
		'STRIPE_SERVICE_FEE': settings.STRIPE_SERVICE_FEE,
		'STRIPE_SERVICE_PERCENT': settings.STRIPE_SERVICE_PERCENT,
	})


def date_handler(obj):
	if hasattr(obj, 'isoformat'):
		return obj.isoformat()
	else:
		raise TypeError('Type %s not serializable' % type(obj))


def _make_template_path(file_name):
	""" Take a file name and make it work against the template path

	:param file_name: File name to work with
	:type file_name: str
	:returns: str

	"""
	return 'reggie/%s' % file_name
