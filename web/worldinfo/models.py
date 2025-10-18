"""
Models for world information pages and map locations.
"""
from django.db import models
from evennia.utils.idmapper.models import SharedMemoryModel


class WorldInfoPage(SharedMemoryModel):
    """
    A world information page with title, content, and optional emblem.
    """
    title = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    content = models.TextField(help_text="Markdown-formatted content")
    category = models.CharField(max_length=100, blank=True, db_index=True,
                                help_text="Optional category for grouping pages")
    subcategory = models.CharField(max_length=100, blank=True, db_index=True,
                                   help_text="Optional subcategory for grouping pages")
    emblem_image = models.ImageField(
        upload_to='worldinfo/emblems/', 
        blank=True, 
        null=True,
        help_text="Optional emblem/heraldry image that appears in the upper right of the article"
    )
    is_public = models.BooleanField(default=True, db_index=True,
                                    help_text="Whether this page is visible to non-staff users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'subcategory', 'title']
        verbose_name = "World Info Page"
        verbose_name_plural = "World Info Pages"
    
    def __str__(self):
        return self.title


class News(SharedMemoryModel):
    """
    News items for the homepage.
    """
    title = models.CharField(max_length=200, db_index=True)
    content = models.TextField(help_text="News content")
    category = models.CharField(max_length=50, choices=[
        ('story', 'Story Update'),
        ('game', 'Game News'),
    ], default='game', db_index=True)
    posted_date = models.CharField(max_length=50, help_text="e.g., 'September 2025' or 'October 13, 2025'")
    is_active = models.BooleanField(default=True, db_index=True,
                                    help_text="Whether this news item is displayed")
    order = models.IntegerField(default=0, db_index=True,
                               help_text="Display order (lower numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-posted_date']
        verbose_name = "News Item"
        verbose_name_plural = "News Items"
    
    def __str__(self):
        return f"{self.title} ({self.category})"


class MapLocation(SharedMemoryModel):
    """
    A clickable location on an interactive map.
    """
    LOCATION_TYPES = [
        ('settlement', 'Settlement'),
        ('landmark', 'Landmark'),
        ('polity', 'Polity'),
        ('other', 'Other'),
    ]
    
    map_name = models.CharField(max_length=200, db_index=True,
                                help_text="Name of the map this location belongs to")
    name = models.CharField(max_length=200, db_index=True,
                           help_text="Name of the location")
    description = models.TextField(blank=True,
                                  help_text="Description shown in popup")
    location_type = models.CharField(max_length=50, choices=LOCATION_TYPES,
                                    default='other', db_index=True)
    x_coord = models.FloatField(help_text="X coordinate on the map")
    y_coord = models.FloatField(help_text="Y coordinate on the map")
    link_url = models.CharField(max_length=500, blank=True,
                               help_text="Optional URL to link to (e.g., wiki page)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['map_name', 'name']
        verbose_name = "Map Location"
        verbose_name_plural = "Map Locations"
        indexes = [
            models.Index(fields=['map_name', 'location_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.map_name})"
