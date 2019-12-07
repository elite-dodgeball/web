from django.urls import path, re_path
from . import views

app_name = 'tourf'

urlpatterns = [
	path('', views.index, name='tourf_index'),
	path('live/<int:event_id>/', views.live, name='live'),
	re_path(r'^events/(?P<event_id>\d+)/stats', views.stats, name='tourf_stats'),
	re_path(r'^events/(?P<event_id>\d+)?', views.events, name='tourf_events'),
	re_path(r'^divisions/(?P<division_id>\d+)?', views.divisions, name='tourf_divisions'),
	re_path(r'^brackets/(?P<bracket_id>[0-9a-f-]+)?', views.brackets, name='tourf_brackets'),
	re_path(r'^robins/(?P<bracket_id>[0-9a-f-]+)?', views.robins, name='tourf_robins'),
	re_path(r'^games/(?P<game_id>[0-9a-f-]+)?', views.games, name='tourf_games'),
	re_path(r'^teams/(?P<team_id>\d+)?', views.teams, name='tourf_teams'),
	re_path(r'^players/(?P<player_id>\d+)?', views.players, name='tourf_players'),
]
