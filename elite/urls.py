"""elite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.views import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap

from client import sitemaps as client_sitemaps
from league import sitemaps as league_sitemaps

urlpatterns = [
	path('', include('client.urls')),
	path('', include('league.urls')),
	path('', include('reggie.urls')),
    path('tourf/', include('tourf.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {
        'sitemaps': {
            'flat': client_sitemaps.FlatSitemap,
            'static': client_sitemaps.StaticSitemap,

            'post': client_sitemaps.PostSitemap,
            'video': client_sitemaps.VideoSitemap,
            'gallery': client_sitemaps.GallerySitemap,

            'team': league_sitemaps.TeamSitemap,
            'event': league_sitemaps.EventSitemap,
        },
    }, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += [
        path('media/<path:path>', static.serve, {'document_root': settings.MEDIA_ROOT}),
    ]
