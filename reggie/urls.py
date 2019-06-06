from django.urls import path, re_path
from . import views

app_name = 'reggie'

urlpatterns = [
	re_path(r'^register/(?P<event_id>\d+)/(?P<invite_id>[^\/]+)?', views.register, name='register'),
	path('register/callback/', views.callback, name='callback'),
]
