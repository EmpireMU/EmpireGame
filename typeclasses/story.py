"""
Story System

This module implements a hierarchical story system for tracking narrative
progression through Books, Plots, Chapters, and Story Updates.

Structure:
- Books: High-level chronological groupings
- Plots: Thematic plot threads that span chapters/books
- Chapters: Mechanical game periods (action budget units)
- Story Updates: Individual narrative posts tagged with plot

The system uses Scripts with different story_type values to represent
plots, chapters, and story updates.
"""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import search_script
from datetime import datetime

class StoryElement(DefaultScript):
    """
    A story element - either a plot, chapter, or story update.
    
    This typeclass handles plots (plot threads), chapters (mechanical 
    game periods), and story updates (narrative content).
    
    Attributes:
        story_type (str): "plot", "chapter", or "update"
        title (str): Title of the plot/chapter/update
        content (str): Content text (for updates only)
        description (str): Description (for plots only)
        update_ids (list): List of update IDs (for plots only)
        book_title (str): Book this belongs to (for chapters)
        parent_id (int): Chapter ID (for updates only)
        order (int): Order within parent/sequence
        is_current (bool): Whether this chapter is current (chapters only)
        is_active (bool): Whether this plot is active (plots only)
        timestamp (datetime): When this was created
    """
    
    def at_script_creation(self):
        """Set up the basic properties of the story element."""
        super().at_script_creation()
        
        now = datetime.now()
        
        # Core properties
        self.db.story_type = "chapter"  # "plot", "chapter", or "update"
        self.db.title = ""
        self.db.content = ""  # For updates only
        self.db.description = ""  # For plots only
        self.db.update_ids = []  # For plots - which updates they contain (list)
        
        # Hierarchy info
        self.db.book_title = ""  # For chapters - which book they belong to
        self.db.parent_id = None  # For updates - which chapter they belong to
        
        # Ordering and status
        self.db.order = 1
        self.db.is_current = False  # For chapters only
        self.db.is_active = True  # For plots only
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
    def is_plot(self):
        """Check if this is a plot."""
        return self.db.story_type == "plot"
    
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
        if self.is_plot:
            return f"Plot: {self.db.title}"
        elif self.is_chapter:
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