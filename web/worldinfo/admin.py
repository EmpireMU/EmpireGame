from django.contrib import admin
from .models import WorldInfoPage, News, MapLocation


@admin.register(WorldInfoPage)
class WorldInfoPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'subcategory', 'is_public', 'updated_at']
    list_filter = ['category', 'subcategory', 'is_public']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'content', 'emblem_image')
        }),
        ('Organization', {
            'fields': ('category', 'subcategory')
        }),
        ('Visibility', {
            'fields': ('is_public',)
        }),
    )


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'posted_date', 'is_active', 'order', 'updated_at']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'content']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'posted_date')
        }),
        ('Display', {
            'fields': ('category', 'is_active', 'order')
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

