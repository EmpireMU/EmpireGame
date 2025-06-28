from django.urls import path
from web.roster.views import (
    roster_view, 
    character_detail_view, 
    update_character_field,
    upload_character_image,
    delete_character_image,
    set_main_character_image,
    set_secondary_character_image,
    set_tertiary_character_image
)

app_name = 'roster'

urlpatterns = [
    path('', roster_view, name='index'),
    path('detail/<str:char_name>/<int:char_id>/', character_detail_view, name='character_detail'),
    path('detail/<str:char_name>/<int:char_id>/update/', update_character_field, name='update_character_field'),
    path('detail/<str:char_name>/<int:char_id>/upload-image/', upload_character_image, name='upload_character_image'),
    path('detail/<str:char_name>/<int:char_id>/delete-image/', delete_character_image, name='delete_character_image'),
    path('detail/<str:char_name>/<int:char_id>/set-main-image/', set_main_character_image, name='set_main_character_image'),
    path('detail/<str:char_name>/<int:char_id>/set-secondary-image/', set_secondary_character_image, name='set_secondary_character_image'),
    path('detail/<str:char_name>/<int:char_id>/set-tertiary-image/', set_tertiary_character_image, name='set_tertiary_character_image'),
] 