from django.contrib import admin
from .models import FamilyRelationship


@admin.register(FamilyRelationship)
class FamilyRelationshipAdmin(admin.ModelAdmin):
    list_display = ['character_id', 'get_character_name', 'relationship_type', 'get_related_character_display_name', 'created_at']
    list_filter = ['relationship_type', 'created_at']
    search_fields = ['character_id', 'related_character_name']
    ordering = ['character_id', 'relationship_type']
    
    def get_character_name(self, obj):
        try:
            from evennia.objects.models import ObjectDB
            char = ObjectDB.objects.get(id=obj.character_id)
            return char.db.full_name or char.name
        except ObjectDB.DoesNotExist:
            return f"Unknown (ID: {obj.character_id})"
    get_character_name.short_description = 'Character'
    
    def get_related_character_display_name(self, obj):
        return obj.get_related_character_display_name()
    get_related_character_display_name.short_description = 'Related To' 