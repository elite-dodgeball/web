"""
.. module:: models
   :platform: Unix
   :synopsis: Contains the models for the Elite site

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import uuid

from django.conf import settings
from django.db import models
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string

from elite import serializer
from league import models as league


class Invite(models.Model):
	""" Invite model

	"""
	def send_email(self, email_address=None):
		""" Send the invitation email

		:param email_address: Email address to send to
		:type email_address: str

		"""
		if not isinstance(email_address, str):
			email_address = self.team.email_address

		division_invites = DivisionInvite.objects.select_related('division').filter(invite=self)

		event_divisions = league.EventDivision.objects.filter(
			event=self.event,
			division__in=[division_invite.division for division_invite in division_invites])

		event_division_hash = {event_division.division_id: event_division for event_division in event_divisions}

		if not division_invites:
			return JsonResponse({'success': False, 'message': 'There are no DivisionInvite objects associated with that Invite'}, status=404)

		for division_invite in division_invites:
			division_invite.event_division = event_division_hash[division_invite.division_id]

			if division_invite.discount > 0:
				division_invite.event_division.discount_cost = max(division_invite.event_division.cost - division_invite.discount, 0)

		email_body = render_to_string('reggie/invitation-email.html', {
			'invite': self,
			'division_invites': division_invites,
		})

		send_mail(
			subject='Elite Dodgeball Invitation - %s' % self.event.title,
			message=email_body,
			from_email=settings.DEFAULT_FROM_EMAIL,
			recipient_list=[email_address],
			fail_silently=False if settings.DEBUG else True,
			html_message=email_body)

		return email_body

	def related_hash(self, event=None, include_players=False):
		""" Get all the related data for the invite

		:param event: Save a query if you already have the event
		:type event: league.Event
		:returns: dict

		"""
		if not event:
			event = self.event

		event_division_hash = event.event_division_hash()

		# Get the DivisionInvite objects

		division_invite_hashes = {
			'id': dict(),
			'division_id': dict(),
		}

		division_invites = DivisionInvite.objects.filter(invite=self)

		for division_invite in division_invites:
			division_invite_hashes['id'][division_invite.pk] = division_invite
			division_invite_hashes['division_id'][division_invite.division_id] = division_invite

		# Get the league.EventDivision objects

		event_division_hashes = {
			'id': dict(),
			'division_id': dict(),
		}

		for event_division_id, division_datum in event_division_hash.items():
			event_division_hashes['id'][division_datum['event_division'].pk] = division_datum
			event_division_hashes['division_id'][division_datum['event_division'].division_id] = division_datum

			if division_datum['division'].pk in division_invite_hashes['division_id']:
				division_datum['event_division'].cost = max(
					division_datum['event_division'].cost - division_invite_hashes['division_id'][division_datum['division'].pk].discount,
					0)
				division_datum['event_division'].max_teams = None

			division_datum['event_division'].is_open = not isinstance(division_datum['event_division'].max_teams, int) or division_datum['event_division'].team_count + division_datum['event_division'].open_invites < division_datum['event_division'].max_teams

			for team_datum in division_datum['teams']:
				if team_datum['team'].pk == self.team_id:
					division_datum['event_division'].is_open = False
					break

		# Get the league.SeasonDivisionTeam objects

		season_division_team_hashes = {
			'id': dict(),
			'division_id': dict(),
		}

		season_division_teams = league.SeasonDivisionTeam.objects.filter(
			team__exact=self.team_id,
			season__exact=event.season_id,
			division__in=list(event_division_hashes['division_id'].keys()))

		for season_division_team in season_division_teams:
			team_datum = {
				'season_division_team': season_division_team,
				'players': list(),
			}
			season_division_team_hashes['id'][season_division_team.pk] = team_datum
			season_division_team_hashes['division_id'][season_division_team.division_id] = team_datum

		# Get the league.Player and league.SeasonDivisionTeamPlayer objects

		if include_players:
			season_division_team_players = league.SeasonDivisionTeamPlayer.objects.filter(season_division_team__in=list(season_division_team_hashes['id'].keys()))
			players = league.Player.objects.filter(pk__in=list({season_division_team_player.player_id for season_division_team_player in season_division_team_players}))

			player_hash = {player.pk: player for player in players}

			for season_division_team_player in season_division_team_players:
				season_division_team_hashes['id'][season_division_team_player.season_division_team_id]['players'].append({
					'player': player_hash[season_division_team_player.player_id],
					'season_division_team_player': season_division_team_player,
				})

		return {
			'event': event,
			'event_division_hashes': event_division_hashes,
			'division_invite_hashes': division_invite_hashes,
			'season_division_team_hashes': season_division_team_hashes,
		}

	def __str__(self):
		""" Return the invite's title

		:returns: str

		"""
		return '%s - %s' % (self.event, self.team)

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	event = models.ForeignKey(league.Event, on_delete=models.CASCADE)
	team = models.ForeignKey(league.Team, on_delete=models.CASCADE)
	date_created = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (
			('event', 'team',),
		)


class DivisionInvite(models.Model):
	""" Model tying Division to an Invite

	"""
	def __str__(self):
		""" Return the division invite's division

		:returns: str

		"""
		return '%s - %s (%s)' % (self.division, self.invite.team, 'claimed' if self.is_claimed else 'open')

	invite = models.ForeignKey(Invite, on_delete=models.CASCADE)
	division = models.ForeignKey(league.Division, on_delete=models.CASCADE)
	is_claimed = models.BooleanField(default=False)
	discount = models.DecimalField(default=0, max_digits=5, decimal_places=2)

	class Meta:
		unique_together = (
			('invite', 'division',),
		)


@receiver(models.signals.post_save, sender=DivisionInvite)
def add_open_invites_count(**kwargs):
	""" Increase the EventDivision's number of open_invites count if being created

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	if kwargs.get('created'):
		division_invite = kwargs.get('instance')

		if not hasattr(division_invite, 'skip_signal') or not division_invite.skip_signal:
			event_division = league.EventDivision.objects.filter(
				division__exact=division_invite.division_id,
				event__exact=division_invite.invite.event_id)

			event_division.update(open_invites=models.F('open_invites') + 1)

@receiver(models.signals.post_delete, sender=DivisionInvite)
def sub_open_invites_count(**kwargs):
	""" Decrease the EventDivision's number of open_invites count

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	division_invite = kwargs.get('instance')

	# TODO: Throws an error when you delete league.EventDivisionTeam first
	if not division_invite.is_claimed:
		event_division = league.EventDivision.objects.filter(
			division__exact=division_invite.division_id,
			event__exact=division_invite.invite.event_id).first()

		if event_division and event_division.open_invites > 0:
			event_division.open_invites = models.F('open_invites') - 1
			event_division.save()


@receiver(models.signals.post_save, sender=league.EventDivisionTeam)
def add_registered_count(**kwargs):
	""" Increase the EventDivision's number of registered teams count if being created

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	if kwargs.get('created'):
		event_division_team = kwargs.get('instance')

		if not hasattr(event_division_team, 'skip_signal') or not event_division_team.skip_signal:
			event_division = league.EventDivision.objects.get(pk=event_division_team.event_division_id)
			event_division.team_count = models.F('team_count') + 1

			try:
				division_invite = get_division_invite(event_division_team)
			except DivisionInvite.DoesNotExist:
				division_invite = None

			if division_invite and division_invite.is_claimed and event_division.open_invites > 0:
				event_division.open_invites = models.F('open_invites') - 1

			event_division.save()

@receiver(models.signals.post_delete, sender=league.EventDivisionTeam)
def sub_registered_count(**kwargs):
	""" Decrease the EventDivision's number of registered teams count

	:param kwargs: Keyword arguments provided by the signal
	:type kwargs: kwargs

	"""
	event_division_team = kwargs.get('instance')

	event_division = league.EventDivision.objects.get(pk=event_division_team.event_division_id)

	if event_division.team_count > 0:
		event_division.team_count = models.F('team_count') - 1

	try:
		division_invite = get_division_invite(event_division_team)
	except DivisionInvite.DoesNotExist:
		division_invite = None

	if division_invite and division_invite.is_claimed:
		event_division.open_invites = models.F('open_invites') + 1

		division_invite.is_claimed = False
		division_invite.save()

	event_division.save()


class ReggieSerializer(serializer.Serializer):
	@staticmethod
	def invite(invite):
		return {
			'id': str(invite.pk) if isinstance(invite.pk, uuid.UUID) else invite.pk,
			'event_id': invite.event_id,
			'team_id': invite.team_id,
			'date_created': invite.date_created,
		} if invite else None

	@staticmethod
	def division_invite(division_invite):
		return {
			'id': division_invite.pk,
			'invite_id': str(division_invite.invite_id) if isinstance(division_invite.invite_id, uuid.UUID) else division_invite.invite_id,
			'division_id': division_invite.division_id,
			'is_claimed': division_invite.is_claimed,
			'discount': float(division_invite.discount),
		} if division_invite else None


def get_division_invite(event_division_team):
	""" Get a matching DivisionInvite

	:param event_division_team: The EventDivisionTeam to match against
	:type event_division_team: EventDivisionTeam
	:returns: DivisionInvite

	"""
	return DivisionInvite.objects.get(
		division=event_division_team.event_division.division_id,
		invite__event__exact=event_division_team.event_division.event_id,
		invite__team__exact=event_division_team.season_division_team.team_id)
