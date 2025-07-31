"""
Story System

This module implements a hierarchical story system for tracking narrative
progression through Books, Volumes, Chapters, and Story Updates.

The system uses a single Script typeclass with different story_type values
to represent chapters and story updates. Books and volumes are stored as
text labels on chapters rather than separate entities.
"""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_script
from datetime import datetime

class StoryElement(DefaultScript):
    """
    A story element - either a chapter or story update.
    
    This typeclass handles both chapters (major story divisions) and 
    story updates (frequent narrative content within chapters).
    
    Attributes:
        story_type (str): "chapter" or "update"
        title (str): Title of the chapter/update
        content (str): Content text (for updates only)
        book_title (str): Book this belongs to (for chapters)
        volume_title (str): Volume this belongs to (for chapters) 
        parent_id (int): Chapter ID (for updates only)
        order (int): Order within parent/sequence
        is_current (bool): Whether this chapter is current (chapters only)
        timestamp (datetime): When this was created
    """
    
    def at_script_creation(self):
        """Set up the basic properties of the story element."""
        super().at_script_creation()
        
        now = datetime.now()
        
        # Core properties
        self.db.story_type = "chapter"  # "chapter" or "update"
        self.db.title = ""
        self.db.content = ""  # For updates only
        
        # Hierarchy info
        self.db.book_title = ""  # For chapters - which book they belong to
        self.db.volume_title = ""  # For chapters - which volume they belong to  
        self.db.parent_id = None  # For updates - which chapter they belong to
        
        # Ordering and status
        self.db.order = 1
        self.db.is_current = False  # For chapters only
        self.db.timestamp = now
        
        # Make sure this script persists and doesn't repeat
        self.interval = -1
        self.persistent = True

    @property
    def story_type(self):
        """Get the story type."""
        return self.db.story_type
        
    @property 
    def title(self):
        """Get the title."""
        return self.db.title
        
    @property
    def is_chapter(self):
        """Check if this is a chapter."""
        return self.db.story_type == "chapter"
        
    @property
    def is_update(self):
        """Check if this is a story update."""
        return self.db.story_type == "update"

    def get_display_name(self, looker=None, **kwargs):
        """
        Returns the display name - used in listings.
        """
        if self.is_chapter:
            return f"Chapter #{self.id}: {self.db.title}"
        else:
            return f"Update #{self.id}: {self.db.title}"
    
    @classmethod
    def get_current_chapter(cls):
        """Get the currently active chapter."""
        scripts = search_script("", typeclass="typeclasses.story.StoryElement")
        current = [s for s in scripts if s.db.story_type == "chapter" and s.db.is_current]
        return current[0] if current else None
        
    @classmethod
    def get_all_chapters(cls):
        """Get all chapters, ordered by sequence."""
        scripts = search_script("", typeclass="typeclasses.story.StoryElement")
        chapters = [s for s in scripts if s.db.story_type == "chapter"]
        return sorted(chapters, key=lambda x: x.db.order)
        
    @classmethod
    def get_chapter_updates(cls, chapter_id):
        """Get all story updates for a specific chapter."""
        scripts = search_script("", typeclass="typeclasses.story.StoryElement")
        updates = [s for s in scripts if s.db.story_type == "update" and s.db.parent_id == chapter_id]
        return sorted(updates, key=lambda x: x.db.order)
        
    @classmethod
    def get_recent_updates(cls, limit=5):
        """Get the most recent story updates across all chapters."""
        scripts = search_script("", typeclass="typeclasses.story.StoryElement")
        updates = [s for s in scripts if s.db.story_type == "update"]
        return sorted(updates, key=lambda x: x.db.timestamp, reverse=True)[:limit] 