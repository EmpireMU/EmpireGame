from django.urls import path
from . import views

app_name = 'worldinfo'

urlpatterns = [
    path('', views.worldinfo_index, name='index'),
    path('search/', views.worldinfo_search_view, name='search'),
    path('create/', views.create_page, name='create'),
    path('<slug:slug>/', views.worldinfo_page, name='page'),
    path('<slug:slug>/edit/', views.edit_page, name='edit'),
    path('<slug:slug>/delete/', views.delete_page, name='delete'),
] 