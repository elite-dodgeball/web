from django.urls import path, re_path
from . import views

urlpatterns = [
	path('', views.index, name='index'),

	# Dynamic pages
	re_path(r'^posts/(?P<post_id>\d+)?', views.posts, name='posts'),
	re_path(r'^episodes/(?P<video_id>\d+)?', views.videos, name='videos'),
	re_path(r'^gallery/(?P<gallery_id>\d+)?', views.gallery, name='gallery'),

	# Site pages
	path('press/', views.press, name='press'),
	path('search/', views.search, name='search'),
	path('contact/', views.contact, name='contact'),
	path('champions/', views.champions, name='champions'),
	path('schedule/', views.schedule, name='schedule'),

	# Static pages
	path('store/', views.store, name='store'),
	re_path(r'^rules/(?P<page>\w+)?', views.rules, name='rules'),
	re_path(r'^about/(?P<page>\w+)?', views.about, name='about'),
]
