from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class WorldInfoPage(models.Model):
    """
    A page of worldinfo.
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
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('worldinfo:page', kwargs={'slug': self.slug}) 