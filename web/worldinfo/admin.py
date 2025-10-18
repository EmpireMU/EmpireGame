from django.contrib import admin
from .models import WorldInfoPage, MapLocation


@admin.register(WorldInfoPage)
class WorldInfoPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'updated_at']
    list_filter = ['category']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'content', 'emblem_image')
        }),
        ('Organization', {
            'fields': ('category',)
        }),
    )


@admin.register(MapLocation)
class MapLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'map_name', 'location_type', 'x_coord', 'y_coord', 'updated_at']
    list_filter = ['map_name', 'location_type']
    search_fields = ['name', 'description']
    list_editable = ['location_type']
    
    fieldsets = (
        ('Location Info', {
            'fields': ('map_name', 'name', 'description', 'location_type')
        }),
        ('Coordinates', {
            'fields': ('x_coord', 'y_coord')
        }),
        ('Link', {
            'fields': ('link_url',)
        }),
    )

