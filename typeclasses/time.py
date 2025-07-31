"""
Narrative Time System

This module is for a simple staff command to set the time. Time
is not set up to progress automatically.

Time can be as broad as "Spring of 632 AF" or as specific as 
"Three hours after the siege began" depending on story needs.
"""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_script


class NarrativeTime(DefaultScript):
    """
    Singleton script to track current narrative time.
    
    This handles the freeform narrative time system that advances
    only when staff explicitly changes it to match story progression.
    
    Examples of narrative time:
    - "Spring of 632 AF"
    - "Dawn on the 15th day of Harvestmoon, 632 AF"  
    - "Three hours after the siege began"
    - "The morning after the betrayal"
    """
    
    def at_script_creation(self):
        """Set up the narrative time tracker."""
        super().at_script_creation()
        
        # Current narrative time - completely freeform
        self.db.current_time = "The beginning of our tale"
        
        # Make this a persistent singleton
        self.key = "narrative_time"
        self.interval = -1
        self.persistent = True

    @property
    def current_time(self):
        """Get the current narrative time."""
        return self.db.current_time
        
    def set_time(self, new_time):
        """Set the current narrative time."""
        self.db.current_time = new_time
        
    @classmethod
    def get_instance(cls):
        """Get or create the singleton NarrativeTime instance."""
        existing = search_script("narrative_time", typeclass=cls)
        if existing:
            return existing[0]
        else:
            # Create new instance
            from evennia import create_script
            return create_script(cls, key="narrative_time") 