"""
Player-created decorative items.
"""

from evennia import DefaultObject
from typeclasses.objects import ObjectParent


class PlayerItem(ObjectParent, DefaultObject):
    """A player-created decorative item."""
    
    def at_object_creation(self):
        super().at_object_creation()
        self.db.creator = None
        self.db.date_created = None
