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
from django.contrib.auth import views as auth_views

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from .views.assets import upload_site_asset, manage_site_assets, delete_site_asset

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
    
    # Password reset URLs
    path('accounts/password/reset/', auth_views.PasswordResetView.as_view(
        template_name='website/password_reset_form.html',
        email_template_name='website/password_reset_email.html',
        success_url='/accounts/password/reset/done/'
    ), name='password_reset'),
    path('accounts/password/reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='website/password_reset_done.html'
    ), name='password_reset_done'),
    path('accounts/password/reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='website/password_reset_confirm.html',
        success_url='/accounts/password/reset/complete/'
    ), name='password_reset_confirm'),
    path('accounts/password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='website/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Admin asset management
    path('admin/upload-assets/', upload_site_asset, name='upload-assets'),
    path('admin/manage-assets/', manage_site_assets, name='manage-assets'),
    path('admin/delete-asset/', delete_site_asset, name='delete-asset'),
    
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
