from django.urls import re_path
from . import views

urlpatterns = [
	re_path(r'^teams/(?P<team_id>\d+)?', views.teams, name='teams'),
	re_path(r'^events/(?P<event_id>\d+)?', views.events, name='events'),
]
