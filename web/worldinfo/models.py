from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class WorldInfoPage(models.Model):
    """
    A world information page with title, content, and optional emblem.
    """
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField(help_text="Use Markdown formatting. Use [[Character Name]] to link to characters.")
    category = models.CharField(max_length=50, blank=True, help_text="e.g., Factions, History, Locations, NPCs")
    subcategory = models.CharField(max_length=50, blank=True, help_text="e.g., Realm of Dyria, Imperial Territories")
    is_public = models.BooleanField(default=True, help_text="Uncheck to make this page GM-only")
    emblem_image = models.ImageField(
        upload_to='worldinfo/emblems/', 
        blank=True, 
        null=True,
        help_text="Optional emblem/heraldry image that appears in the upper right of the article"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'subcategory', 'title']
        verbose_name = "World Info Page"
        verbose_name_plural = "World Info Pages"
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('worldinfo:page', kwargs={'slug': self.slug})


class News(models.Model):
    """
    A news/announcement item for the homepage.
    Can be either Story Updates or Game News.
    """
    CATEGORY_CHOICES = [
        ('story', 'Story Update'),
        ('game', 'Game News'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Main content of the news item. HTML is allowed.")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='game')
    posted_date = models.CharField(max_length=50, help_text="e.g., 'September 2025' or 'October 13, 2025'")
    is_active = models.BooleanField(default=True, help_text="Only active news items are shown on the homepage")
    order = models.IntegerField(default=0, help_text="Lower numbers appear first within each category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'order', '-created_at']
        verbose_name_plural = "News"
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"


class MapLocation(models.Model):
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


class GlossaryTerm(models.Model):
    """
    A glossary term that can be automatically highlighted in worldinfo and roster pages.
    """
    term = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        help_text="The term to highlight (e.g., 'Westelth', 'The Empire')"
    )
    short_description = models.TextField(
        max_length=500,
        help_text="Brief description shown in the popover (max 500 characters)"
    )
    link_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional URL to full page (e.g., /world/westelth/ or /wiki/empire/)"
    )
    link_text = models.CharField(
        max_length=100,
        blank=True,
        default="Learn more",
        help_text="Text for the 'Learn more' link (default: 'Learn more')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to temporarily disable highlighting for this term"
    )
    case_sensitive = models.BooleanField(
        default=False,
        help_text="Check if the term should be matched case-sensitively"
    )
    priority = models.IntegerField(
        default=0,
        help_text="Higher priority terms are matched first (useful for overlapping terms)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'term']
        verbose_name = "Glossary Term"
        verbose_name_plural = "Glossary Terms"
    
    def __str__(self):
        return self.term