"""
.. module:: views
   :platform: Unix
   :synopsis: Contains the views

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import simplejson as json

from django.http import Http404
from django.utils import timezone
from django.shortcuts import render

from client import models as client
from league import models as league


def events(request, event_id=None):
	""" Display either all events or just one

	:param event_id: ID of the event to show
	:type event_id: int
	:returns: render

	"""
	if event_id:
		try:
			event = league.Event.objects.get(pk=event_id)
		except models.Event.DoesNotExist:
			raise Http404

		return render(request, 'event.html', {
			'event': event,
			'states': league.Event,
			'passed': event.datetime < timezone.now(),
			'videos': json.dumps(client.ClientSerializer.serialize(client.Video.get_videos(event_id=event_id))),
			'galleries': client.Gallery.get_galleries(event_id=event_id),
			'event_division_hash': event.event_division_hash(),
		})

	now = timezone.now()
	events = league.Event.objects.all().order_by('-datetime')

	ret = {
		'passed': list(),
		'upcoming': list(),
	}

	for event in events:
		if event.datetime < now:
			ret['passed'].append(event)
		else:
			ret['upcoming'].append(event)

	ret['upcoming'].reverse()

	return render(request, 'events.html', ret)


def teams(request, team_id=None):
	""" Display either teams by region or an individual team

	:param team_id: ID of the team to show
	:type team_id: int
	:returns: render

	"""
	if team_id:
		try:
			team = league.Team.objects.get(pk=team_id)
		except league.Team.DoesNotExist:
			raise Http404

		return render(request, 'team.html', {
			'team': team,
			'players': team.players(),
			'social': team.social(),
		})

	division_hash, regions, season = league.get_division_region_teams()

	return render(request, 'teams.html', {
		'regions': regions,
		'division_hash': division_hash,
		'season': season,
	})
