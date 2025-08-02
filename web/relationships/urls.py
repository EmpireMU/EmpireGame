from django.urls import path
from . import views

app_name = 'relationships'

urlpatterns = [
    path('', views.relationship_list, name='list'),
    path('add/', views.add_relationship, name='add'),
    path('delete/<int:relationship_id>/', views.delete_relationship, name='delete'),
    path('search-characters/', views.character_search, name='character_search'),
    path('get-character-name/', views.get_character_name, name='get_character_name'),
] 