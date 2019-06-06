"""
.. module:: views
   :platform: Unix
   :synopsis: Contains the views

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import simplejson as json

from django.shortcuts import render

from client import forms
from client import models as client
from league import models as league


def index(request):
	""" Serve up the index page

	:returns: render

	"""
	posts = client.Post.objects.filter(featured=True).order_by('-date_created')[:5]
	videos = client.Video.objects.order_by('-published_at')[:4]
	division_hash, regions, season = league.get_division_region_teams()

	return render(request, 'index.html', {
		'posts': posts,
		'videos': videos,
		'regions': regions,
		'division_hash': division_hash,
		'season': season,
	})


def gallery(request, gallery_id=None):
	""" Display either all galleries or just one

	:param gallery_id: ID of the gallery to show
	:type gallery_id: int
	:returns: render

	"""
	if gallery_id:
		try:
			gallery = client.Gallery.objects.get(pk=gallery_id)
		except client.Gallery.DoesNotExist:
			raise Http404

		return render(request, 'gallery.html', {
			'gallery': gallery,
			'images': gallery.images(),
		})

	return render(request, 'galleries.html', {
		'galleries': client.Gallery.get_galleries(),
	})


def videos(request, video_id=None):
	""" Display either all videos or just one

	:param video_id: ID of the video to show
	:type video_id: int
	:returns: render

	"""
	if video_id:
		try:
			video = client.Video.objects.get(pk=video_id)
		except client.Video.DoesNotExist:
			raise Http404

		video.description = client.Video.paragraphize(video.description, False, True)

		return render(request, 'video.html', {
			'video': video,
		})

	videos = client.ClientSerializer.serialize(client.Video.get_videos())

	return render(request, 'videos.html', {
		'length': len(videos),
		'videos': json.dumps(videos),
	})


def champions(request):
	""" Show the champions page

	:returns: render

	"""
	seasons = league.Season.objects.all()[1:]
	season_hash = {season.pk: season for season in seasons}

	divisions = league.Division.objects.all()
	division_hash = {division.pk: division for division in divisions}

	season_division_teams = league.SeasonDivisionTeam.objects.filter(season__in=list(seasons))
	team_data_hash = league.SeasonDivisionTeam.get_team_data_hash(season_division_teams=season_division_teams)

	season_division_hash = dict()

	for season_division_team in season_division_teams:
		if season_division_team.season_id not in season_division_hash:
			season_division_hash[season_division_team.season_id] = {
				'season': season_hash[season_division_team.season_id],
				'division_team_hash': dict(),
			}

		if season_division_team.division_id not in season_division_hash[season_division_team.season_id]['division_team_hash']:
			season_division_hash[season_division_team.season_id]['division_team_hash'][season_division_team.division_id] = {
				'division': division_hash[season_division_team.division_id],
				'teams': list(),
			}

		season_division_hash[season_division_team.season_id]['division_team_hash'][season_division_team.division_id]['teams'].append({
			'team': team_data_hash[season_division_team.team_id]['team'],
			'season_division_team': team_data_hash[season_division_team.team_id]['season_division_team_hash'][season_division_team.division_id],
		})

	for season_id, season_datum in season_division_hash.items():
		for division_id, division_datum in season_datum['division_team_hash'].items():
			division_datum['teams'].sort(key=lambda x: x['season_division_team'].points, reverse=True)

	return render(request, 'champions.html', {
		'season_division_hash': season_division_hash,
	})


def schedule(request):
	""" Show the schedule of events

	"""
	return render(request, 'schedule.html', {
		'events': league.Event.get_upcoming(),
	})


def posts(request, post_id=None):
	""" Display news posts

	:param post_id: ID of the post to show
	:type post_id: int
	:returns: render

	"""
	if post_id:
		try:
			return render(request, 'post.html', {
				'post': client.Post.objects.get(pk=post_id),
			})
		except client.Post.DoesNotExist:
			raise Http404
	else:
		return render(request, 'posts.html', {
			'posts': client.Post.objects.order_by('-date_created')[:5],
		})


def press(request):
	""" Show the press page

	:returns: render

	"""
	return render(request, 'press.html', {
		'clips': client.Press.objects.order_by('-date_created'),
	})

def search(request):
	""" Show search results

	:returns: render

	"""
	query = request.GET.get('q', None).strip()

	if query:
		return render(request, 'search.html', {
			'query': query,
			'results': client.Search.query(query=query),
		})
	else:
		return render(request, 'search.html', {
			'query': False,
		})

def contact(request):
	""" Present and process a contact form

	:returns: render

	"""
	form = None
	saved = False

	if request.method == 'POST':
		form = forms.ContactForm(request.POST)

		if form.is_valid():
			# First save the message just in case

			con = client.Contact(
				name=form.cleaned_data['name'], email=form.cleaned_data['email'],
				subject=form.cleaned_data['subject'], body=form.cleaned_data['body'])

			con.save()
			saved = True

			# Now to actually send the contact email
			try:
				con.send_email()
			except (TypeError, ValueError):
				pass
	else:
		form = forms.ContactForm()

	return render(request, 'contact.html', {
		'form': form,
		'saved': saved,
	})


def store(request):
	""" Show the store page

	:returns: render

	"""
	return render(request, 'store.html')

def rules(request, page=None):
	""" Show the appropriate rules page

	:returns: render

	"""
	if page == 'referee':
		return render(request, 'referee.html')
	if page == 'regulations':
		return render(request, 'regulations.html')
	return render(request, 'rules.html')

def about(request, page=None):
	""" Show the proper about page

	:returns: render

	"""
	if page == 'history':
		return render(request, 'history.html')
	if page == 'leadership':
		return render(request, 'leadership.html', {
			'leaders': client.Director.objects.order_by('id'),
		})
	return render(request, 'mission.html')
