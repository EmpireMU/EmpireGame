"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path, include
from django.http import HttpResponseForbidden
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import TemplateView

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from .views import upload_site_asset

def character_creation_disabled(request):
    """Return a 403 Forbidden response for character creation/management URLs."""
    return HttpResponseForbidden("Character creation and management is only available in-game.")

def custom_logout(request):
    """Custom logout view that accepts both GET and POST requests."""
    logout(request)
    return redirect('/')

# add patterns here
urlpatterns = [
    # Override Evennia's default character creation/management URLs to disable them
    path('accounts/characters/create/', character_creation_disabled, name='character-create'),
    path('accounts/characters/manage/', character_creation_disabled, name='character-manage'),
    
    # Custom logout that accepts GET requests
    path('auth/logout/', custom_logout, name='logout'),
    
    # Admin asset upload
    path('admin/upload-assets/', upload_site_asset, name='upload-assets'),
    
    # Custom app URLs
    path('characters/', include('web.roster.urls')),
    path('world/', include('web.worldinfo.urls')),
    path('family/', include('web.relationships.urls')),
    
    # SEO files
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('sitemap.xml', TemplateView.as_view(template_name='sitemap.xml', content_type='application/xml')),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
