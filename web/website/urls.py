"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path, include
from django.http import HttpResponseForbidden

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

def character_creation_disabled(request):
    """Return a 403 Forbidden response for character creation/management URLs."""
    return HttpResponseForbidden("Character creation and management is only available in-game.")

# add patterns here
urlpatterns = [
    # Override Evennia's default character creation/management URLs to disable them
    path('accounts/characters/create/', character_creation_disabled, name='character-create'),
    path('accounts/characters/manage/', character_creation_disabled, name='character-manage'),
    
    # Custom app URLs
    path('characters/', include('web.roster.urls')),
    path('world/', include('web.worldinfo.urls')),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
