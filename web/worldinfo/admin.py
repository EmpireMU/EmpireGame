from django.contrib import admin
from .models import WorldInfoPage, News, MapLocation, GlossaryTerm


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


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ['term', 'alias_count', 'is_active', 'case_sensitive', 'priority', 'has_link', 'updated_at']
    list_filter = ['is_active', 'case_sensitive']
    search_fields = ['term', 'aliases', 'short_description']
    list_editable = ['is_active', 'priority']
    
    fieldsets = (
        ('Term', {
            'fields': ('term', 'aliases', 'short_description'),
            'description': 'Enter alternative terms (aliases) one per line. For example, if the term is "Greytide", you could add "Greytides" as an alias.'
        }),
        ('Link', {
            'fields': ('link_url', 'link_text'),
            'description': 'Optional link to a full page for this term'
        }),
        ('Settings', {
            'fields': ('is_active', 'case_sensitive', 'priority'),
            'description': 'Priority: higher numbers are matched first (useful for overlapping terms like "Empire" vs "The Empire")'
        }),
    )
    
    def has_link(self, obj):
        return bool(obj.link_url)
    has_link.boolean = True
    has_link.short_description = 'Has Link'
    
    def alias_count(self, obj):
        """Show how many aliases this term has."""
        if not obj.aliases:
            return 0
        return len([a for a in obj.aliases.split('\n') if a.strip()])
    alias_count.short_description = 'Aliases'

