"""
.. module:: routing
   :platform: Unix
   :synopsis: Contains the routing
.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.conf.urls import url

from tourf import consumers

websocket_urlpatterns = [
	url(r'^ws/tourf/(?P<event_id>[^/]+)/$', consumers.TourfConsumer),
]
