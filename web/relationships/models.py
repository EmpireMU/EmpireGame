from django.db import models
from evennia.objects.models import ObjectDB


FAMILY_RELATIONSHIP_CHOICES = [
    ('parent', 'Parent'),
    ('grandparent', 'Grandparent'),
    ('great_grandparent', 'Great-Grandparent'),
    ('sibling', 'Sibling'),
    ('aunt_uncle', 'Aunt/Uncle'),
    ('niece_nephew', 'Niece/Nephew'),
    ('cousin', 'Cousin'),
    ('second_cousin', 'Second Cousin'),
    ('distant_cousin', 'Distant Cousin'),
    ('child', 'Child'),
    ('grandchild', 'Grandchild'),
    ('great_grandchild', 'Great-Grandchild'),
]

# Reciprocal relationship mapping
RECIPROCAL_RELATIONSHIPS = {
    'parent': 'child',
    'child': 'parent',
    'grandparent': 'grandchild',
    'grandchild': 'grandparent',
    'great_grandparent': 'great_grandchild',
    'great_grandchild': 'great_grandparent',
    'sibling': 'sibling',
    'aunt_uncle': 'niece_nephew',
    'niece_nephew': 'aunt_uncle',
    'cousin': 'cousin',
    'second_cousin': 'second_cousin',
    'distant_cousin': 'distant_cousin',
}


class FamilyRelationship(models.Model):
    """
    Represents a family relationship between characters.
    The character can be related to either a PC (referenced by ID) or an NPC (by name).
    """
    # The character who has this family member (always a PC)
    character_id = models.IntegerField(help_text="Evennia character object ID")
    
    # The family member (PC or NPC)
    related_character_id = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Evennia character object ID if this is a PC"
    )
    related_character_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Character name if this is an NPC"
    )
    
    # Relationship type
    relationship_type = models.CharField(
        max_length=50, 
        choices=FAMILY_RELATIONSHIP_CHOICES
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevent duplicate relationships
        unique_together = ['character_id', 'related_character_id', 'related_character_name', 'relationship_type']
        ordering = ['relationship_type', 'related_character_name']
    
    def __str__(self):
        if self.related_character_id:
            try:
                related_char = ObjectDB.objects.get(id=self.related_character_id)
                related_name = related_char.db.full_name or related_char.name
            except ObjectDB.DoesNotExist:
                related_name = f"Unknown PC (ID: {self.related_character_id})"
        else:
            related_name = f"{self.related_character_name} (NPC)"
        
        try:
            char = ObjectDB.objects.get(id=self.character_id)
            char_name = char.db.full_name or char.name
        except ObjectDB.DoesNotExist:
            char_name = f"Unknown (ID: {self.character_id})"
            
        return f"{char_name}'s {self.get_relationship_type_display()}: {related_name}"
    
    def get_related_character_display_name(self):
        """Get the display name for the related character."""
        if self.related_character_id:
            try:
                related_char = ObjectDB.objects.get(id=self.related_character_id)
                return related_char.db.full_name or related_char.name
            except ObjectDB.DoesNotExist:
                return f"Unknown PC (ID: {self.related_character_id})"
        else:
            return self.related_character_name
    
    def is_related_to_pc(self):
        """Check if this relationship is to a PC character."""
        return self.related_character_id is not None
    
    def get_related_character_object(self):
        """Get the related character object if it's a PC, otherwise None."""
        if self.related_character_id:
            try:
                return ObjectDB.objects.get(id=self.related_character_id)
            except ObjectDB.DoesNotExist:
                return None
        return None 