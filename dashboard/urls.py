from django.urls import path, re_path
from . import views

app_name = 'dashboard'

urlpatterns = [
	path('', views.index, name='dashboard_index'),

	re_path(r'^api/teams/(?P<team_id>\d+)?', views.teams, name='dashboard_teams'),
	re_path(r'^api/players/(?P<player_id>\d+)?', views.players, name='dashboard_players'),
	re_path(r'^api/regions/(?P<region_id>\d+)?', views.regions, name='dashboard_regions'),

	re_path(r'^api/divisions/(?P<division_id>\d+)?', views.divisions, name='dashboard_divisions'),
	re_path(r'^api/seasons/(?P<season_id>\d+)/teams/(?P<team_id>\d+)/divisions', views.divisions, name='dashboard_divisions_fk'),

	re_path(r'^api/invites/(?P<invite_id>[0-9a-f-]+)/sender', views.sender, name='dashboard_invites'),
	re_path(r'^api/division_invites/(?P<division_invite_id>\d+)?', views.division_invites, name='dashboard_division_invites'),

	re_path(r'^api/invites/(?P<invite_id>[0-9a-f-]+)?', views.invites, name='dashboard_invites'),
	re_path(r'^api/events/(?P<event_id>\d+)/invites/(?P<invite_id>[0-9a-f-]+)?', views.invites, name='dashboard_invites_fk'),

	re_path(r'^api/event_division_team_players/(?P<event_division_team_player_id>\d+)?', views.event_division_team_players, name='dashboard_event_division_team_players'),
	re_path(r'^api/event_division_teams/(?P<event_division_team_id>\d+)/players/(?P<season_division_team_player_id>\d+)?', views.event_division_team_players, name='dashboard_event_division_team_players_fk'),

	re_path(r'^api/event_division_teams/(?P<event_division_team_id>\d+)?', views.event_division_teams, name='dashboard_event_division_teams'),
	re_path(r'^api/event_divisions/(?P<event_division_id>\d+)/season_division_teams/(?P<season_division_team_id>\d+)?', views.event_division_teams, name='dashboard_event_division_teams_fk'),

	re_path(r'^api/event_divisions/(?P<event_division_id>\d+)?', views.event_divisions, name='dashboard_event_divisions'),
	re_path(r'^api/events/(?P<event_id>\d+)/divisions/(?P<division_id>\d+)?', views.event_divisions, name='dashboard_event_divisions_fk'),

	re_path(r'^api/events/(?P<event_id>\d+)?', views.events, name='dashboard_events'),

	re_path(r'^api/season_division_team_players/(?P<season_division_team_player_id>\d+)?', views.season_division_team_players, name='dashboard_season_division_team_players'),
	re_path(r'^api/season_division_teams/(?P<season_division_team_id>\d+)/players/(?P<player_id>\d+)?', views.season_division_team_players, name='dashboard_season_division_team_players_fk'),

	re_path(r'^api/season_division_teams/(?P<season_division_team_id>\d+)?', views.season_division_teams, name='dashboard_season_division_teams'),
	re_path(r'^api/seasons/(?P<season_id>\d+)/divisions/(?P<division_id>\d+)/teams/(?P<team_id>\d+)?', views.season_division_teams, name='dashboard_season_division_teams_fk'),

	re_path(r'^api/seasons/(?P<season_id>[0-9a-f-]+)?', views.seasons, name='dashboard_seasons'),
]
