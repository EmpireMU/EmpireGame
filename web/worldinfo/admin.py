from django.contrib import admin
from .models import WorldInfoPage, News


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

