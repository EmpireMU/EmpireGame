"""
Manager class for handling story system workflow logic.
"""

from evennia.scripts.models import ScriptDB
from evennia import create_script
from datetime import datetime
from typeclasses.story import StoryElement

class StoryManager:
    """Handles story system workflow logic."""
    
    @classmethod
    def create_plot(cls, title, description=""):
        """Create a new plot.
        
        Args:
            title (str): Plot title
            description (str, optional): Plot description
            
        Returns:
            StoryElement: The created plot
        
        Raises:
            ValueError: If title is empty
        """
        if not title.strip():
            raise ValueError("Plot title cannot be empty")
            
        plot_id = cls.get_next_plot_id()
        plot = create_script(
            "typeclasses.story.StoryElement",
            key=f"Plot-{plot_id}"
        )
        
        if not plot:
            raise RuntimeError("Failed to create plot")
            
        plot.db.story_id = plot_id
        plot.db.story_type = "plot"
        plot.db.title = title.strip()
        plot.db.description = description.strip()
        plot.db.is_active = True
        plot.db.timestamp = datetime.now()
        
        return plot
    
    @classmethod
    def create_chapter(cls, title, book_title=""):
        """Create a new chapter.
        
        Args:
            title (str): Chapter title
            book_title (str, optional): Book title
            
        Returns:
            StoryElement: The created chapter
        
        Raises:
            ValueError: If title is empty
        """
        if not title.strip():
            raise ValueError("Chapter title cannot be empty")
            
        # Get next order number before creating the chapter
        all_chapters = cls.get_all_chapters()
        next_order = len(all_chapters) + 1
        
        chapter_id = cls.get_next_chapter_id()
        chapter = create_script(
            "typeclasses.story.StoryElement",
            key=f"Chapter-{chapter_id}"
        )
        
        if not chapter:
            raise RuntimeError("Failed to create chapter")
            
        chapter.db.story_id = chapter_id
        chapter.db.story_type = "chapter"
        chapter.db.title = title.strip()
        chapter.db.book_title = book_title.strip()
        chapter.db.order = next_order
        chapter.db.is_current = False
        chapter.db.timestamp = datetime.now()
        
        return chapter
        
    @classmethod
    def create_story_update(cls, title, content, chapter_id):
        """Create a new story update.
        
        Args:
            title (str): Update title
            content (str): Update content
            chapter_id (int): Chapter ID to attach to
            
        Returns:
            StoryElement: The created story update
        
        Raises:
            ValueError: If title or content is empty
        """
        if not title.strip():
            raise ValueError("Story update title cannot be empty")
        if not content.strip():
            raise ValueError("Story update content cannot be empty")
            
        # Get next order number for this chapter before creating the update
        existing_updates = cls.get_chapter_updates(chapter_id)
        next_order = len(existing_updates) + 1
        
        update_id = cls.get_next_update_id()
        update = create_script(
            "typeclasses.story.StoryElement",
            key=f"StoryUpdate-{update_id}"
        )
        
        if not update:
            raise RuntimeError("Failed to create story update")
            
        update.db.story_id = update_id
        update.db.story_type = "update"
        update.db.title = title.strip()
        update.db.content = content.strip()
        update.db.parent_id = chapter_id
        update.db.order = next_order
        update.db.timestamp = datetime.now()
        
        return update
        
    @classmethod
    def get_next_plot_id(cls):
        """Get the next available plot ID."""
        plots = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="Plot-"
        )
        if not plots.exists():
            return 1
            
        max_id = 0
        for plot in plots:
            try:
                if hasattr(plot.db, 'story_id') and plot.db.story_id and plot.db.story_id > max_id:
                    max_id = plot.db.story_id
            except AttributeError:
                continue
                
        return max_id + 1
    
    @classmethod
    def get_next_chapter_id(cls):
        """Get the next available chapter ID."""
        chapters = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="Chapter-"
        )
        if not chapters.exists():
            return 1
            
        max_id = 0
        for chapter in chapters:
            try:
                if hasattr(chapter.db, 'story_id') and chapter.db.story_id and chapter.db.story_id > max_id:
                    max_id = chapter.db.story_id
            except AttributeError:
                continue
                
        return max_id + 1
        
    @classmethod
    def get_next_update_id(cls):
        """Get the next available story update ID."""
        updates = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="StoryUpdate-"
        )
        if not updates.exists():
            return 1
            
        max_id = 0
        for update in updates:
            try:
                if hasattr(update.db, 'story_id') and update.db.story_id and update.db.story_id > max_id:
                    max_id = update.db.story_id
            except AttributeError:
                continue
                
        return max_id + 1
        
    @classmethod
    def find_plot(cls, plot_id):
        """Find a plot by its story ID number."""
        try:
            id_num = int(str(plot_id).lstrip('#'))
            key = f"Plot-{id_num}"
            results = ScriptDB.objects.filter(
                db_typeclass_path__contains="story.StoryElement",
                db_key=key
            )
            return results[0] if results else None
        except (ValueError, IndexError):
            return None
    
    @classmethod
    def find_plot_by_name(cls, name):
        """Find a plot by its title (case-insensitive partial match)."""
        plots = cls.get_all_plots()
        name_lower = name.lower()
        
        # Try exact match first
        for plot in plots:
            if plot.db.title.lower() == name_lower:
                return plot
        
        # Try partial match
        for plot in plots:
            if name_lower in plot.db.title.lower():
                return plot
                
        return None
    
    @classmethod
    def find_chapter(cls, chapter_id):
        """Find a chapter by its story ID number."""
        try:
            id_num = int(str(chapter_id).lstrip('#'))
            key = f"Chapter-{id_num}"
            results = ScriptDB.objects.filter(
                db_typeclass_path__contains="story.StoryElement",
                db_key=key
            )
            return results[0] if results else None
        except (ValueError, IndexError):
            return None
            
    @classmethod
    def find_story_update(cls, update_id):
        """Find a story update by its story ID number."""
        try:
            id_num = int(str(update_id).lstrip('#'))
            key = f"StoryUpdate-{id_num}"
            results = ScriptDB.objects.filter(
                db_typeclass_path__contains="story.StoryElement",
                db_key=key
            )
            return results[0] if results else None
        except (ValueError, IndexError):
            return None
            
    @classmethod
    def get_current_chapter(cls):
        """Get the currently active chapter."""
        scripts = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="Chapter-"
        )
        for script in scripts:
            if hasattr(script.db, 'is_current') and script.db.is_current:
                return script
        return None
        
    @classmethod
    def get_all_chapters(cls):
        """Get all chapters, ordered by sequence."""
        scripts = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="Chapter-"
        )
        chapters = [s for s in scripts if hasattr(s.db, 'story_type') and s.db.story_type == "chapter"]
        return sorted(chapters, key=lambda x: getattr(x.db, 'order', 0))
        
    @classmethod
    def get_chapter_updates(cls, chapter_id):
        """Get all story updates for a specific chapter."""
        scripts = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="StoryUpdate-"
        )
        updates = []
        for script in scripts:
            if (hasattr(script.db, 'story_type') and script.db.story_type == "update" and
                hasattr(script.db, 'parent_id') and script.db.parent_id == chapter_id):
                updates.append(script)
        return sorted(updates, key=lambda x: getattr(x.db, 'order', 0))
        
    @classmethod
    def get_all_plots(cls):
        """Get all plots, ordered by creation."""
        scripts = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="Plot-"
        )
        plots = [s for s in scripts if hasattr(s.db, 'story_type') and s.db.story_type == "plot"]
        return sorted(plots, key=lambda x: getattr(x.db, 'story_id', 0))
    
    @classmethod
    def get_plot_updates(cls, plot_id):
        """Get all story updates for a specific plot, ordered by timestamp."""
        # Find the plot
        plot = cls.find_plot(plot_id)
        if not plot or not hasattr(plot.db, 'update_ids'):
            return []
        
        # Get the updates from the plot's list
        updates = []
        for update_id in plot.db.update_ids:
            update = cls.find_story_update(update_id)
            if update:
                updates.append(update)
        
        return sorted(updates, key=lambda x: getattr(x.db, 'timestamp', datetime.min))
    
    @classmethod
    def get_recent_updates(cls, limit=5):
        """Get the most recent story updates across all chapters."""
        scripts = ScriptDB.objects.filter(
            db_typeclass_path__contains="story.StoryElement",
            db_key__startswith="StoryUpdate-"
        )
        updates = [s for s in scripts if hasattr(s.db, 'story_type') and s.db.story_type == "update"]
        return sorted(updates, key=lambda x: getattr(x.db, 'timestamp', datetime.min), reverse=True)[:limit]
        
    @classmethod
    def set_current_chapter(cls, chapter_id):
        """Set the current chapter by clearing all current flags and setting one."""
        # Clear all current flags
        all_chapters = cls.get_all_chapters()
        for chapter in all_chapters:
            chapter.db.is_current = False
            
        # Set the target chapter as current
        target_chapter = cls.find_chapter(chapter_id)
        if target_chapter:
            target_chapter.db.is_current = True
            return target_chapter
        return None 
        
    @classmethod
    def get_current_book_title(cls):
        """Get the book title of the current chapter."""
        current_chapter = cls.get_current_chapter()
        if current_chapter:
            return current_chapter.db.book_title or "Untitled Book"
        return "Untitled Book"
        
    @classmethod
    def get_book_scoped_number(cls, global_update_id, book_title=None):
        """Get the book-scoped number for a global update ID.
        
        Args:
            global_update_id (int): Global story update ID
            book_title (str, optional): Book to check in. If None, uses current book.
            
        Returns:
            int or None: The book-scoped number (1st, 2nd, 3rd update in book) or None if not found
        """
        if book_title is None:
            book_title = cls.get_current_book_title()
            
        # Get all updates in this book, ordered by timestamp
        updates_in_book = cls.get_updates_in_book(book_title)
        
        # Find the position of our update
        for i, update in enumerate(updates_in_book):
            if update.db.story_id == global_update_id:
                return i + 1  # Convert to 1-based numbering
        
        return None
        
    @classmethod
    def find_update_by_book_scoped_number(cls, book_scoped_id, book_title=None):
        """Find a story update by its book-scoped number.
        
        Args:
            book_scoped_id (int): The book-scoped number (1st, 2nd, 3rd update in book)
            book_title (str, optional): Book to search in. If None, uses current book.
            
        Returns:
            StoryElement or None: The found update or None
        """
        if book_title is None:
            book_title = cls.get_current_book_title()
            
        # Get all updates in this book, ordered by timestamp
        updates_in_book = cls.get_updates_in_book(book_title)
        
        # Check if the requested number is valid
        if book_scoped_id < 1 or book_scoped_id > len(updates_in_book):
            return None
            
        # Return the update at that position (convert to 0-based index)
        return updates_in_book[book_scoped_id - 1]
        
    @classmethod
    def get_updates_in_book(cls, book_title):
        """Get all story updates in a specific book, ordered by timestamp.
        
        Args:
            book_title (str): The book title to filter by
            
        Returns:
            list: List of StoryElement updates in chronological order
        """
        # Get all chapters with this book title
        all_chapters = cls.get_all_chapters()
        book_chapters = [ch for ch in all_chapters if (ch.db.book_title or "Untitled Book") == book_title]
        
        # Get all updates from these chapters
        all_updates = []
        for chapter in book_chapters:
            chapter_updates = cls.get_chapter_updates(chapter.db.story_id)
            all_updates.extend(chapter_updates)
            
        # Sort by timestamp
        return sorted(all_updates, key=lambda x: getattr(x.db, 'timestamp', datetime.min))
        
    @classmethod
    def parse_story_reference(cls, args_str):
        """Parse user input that might be book-scoped or global.
        
        Supports:
        - "3" -> 3rd update in current book
        - '"Book Title" 3' -> 3rd update in specified book
        
        Args:
            args_str (str): User input string
            
        Returns:
            tuple: (update, book_title_used) or (None, None) if not found
        """
        if not args_str:
            return None, None
            
        args_str = args_str.strip()
        
        # Check if it starts with a quote (book title specified)
        if args_str.startswith('"'):
            # Find the closing quote
            quote_end = args_str.find('"', 1)
            if quote_end == -1:
                return None, None
                
            book_title = args_str[1:quote_end]
            remaining = args_str[quote_end + 1:].strip()
            
            # Parse the number
            try:
                book_scoped_id = int(remaining)
                update = cls.find_update_by_book_scoped_number(book_scoped_id, book_title)
                return update, book_title
            except ValueError:
                return None, None
        else:
            # No quotes - try book-scoped number in current book first
            try:
                book_scoped_id = int(args_str)
                current_book = cls.get_current_book_title()
                update = cls.find_update_by_book_scoped_number(book_scoped_id, current_book)
                if update:
                    return update, current_book
                else:
                    # Fallback: try as global ID
                    update = cls.find_story_update(book_scoped_id)
                    if update:
                        # Find which book this belongs to
                        chapter = cls.find_chapter(update.db.parent_id) if update.db.parent_id else None
                        if chapter:
                            fallback_book = chapter.db.book_title or "Untitled Book"
                            return update, fallback_book
                    return None, None
            except ValueError:
                return None, None
    
    @classmethod
    def delete_plot(cls, plot_id):
        """Delete a plot.
        
        Note: This does NOT delete the story updates that were in this plot.
        They remain in the system, just no longer tagged with this plot.
        
        Args:
            plot_id (int): The plot ID to delete
            
        Returns:
            tuple: (success, message, unlinked_count) where:
                - success (bool): Whether the deletion succeeded
                - message (str): Status message
                - unlinked_count (int): Number of story updates that were in this plot
        """
        # Find the plot
        plot = cls.find_plot(plot_id)
        if not plot:
            return False, f"Plot #{plot_id} not found", 0
        
        # Count how many updates were in this plot
        update_count = len(plot.db.update_ids) if hasattr(plot.db, 'update_ids') else 0
        
        # Delete the plot itself (updates remain untouched)
        plot_title = plot.db.title
        plot.delete()
        
        return True, f"Deleted plot #{plot_id}: {plot_title}", update_count
    
    @classmethod
    def add_update_to_plots(cls, update_id, plot_ids):
        """Add an update to one or more plots.
        
        Args:
            update_id (int): The update ID to add
            plot_ids (list): List of plot IDs to add the update to
            
        Returns:
            list: Successfully added plot names
        """
        added_plots = []
        for plot_id in plot_ids:
            plot = cls.find_plot(plot_id)
            if plot:
                if not hasattr(plot.db, 'update_ids'):
                    plot.db.update_ids = []
                if update_id not in plot.db.update_ids:
                    plot.db.update_ids.append(update_id)
                added_plots.append(plot.db.title)
        return added_plots
    
    @classmethod
    def remove_update_from_plots(cls, update_id, plot_ids=None):
        """Remove an update from plots.
        
        Args:
            update_id (int): The update ID to remove
            plot_ids (list, optional): Specific plot IDs to remove from. If None, removes from all plots.
            
        Returns:
            int: Number of plots the update was removed from
        """
        if plot_ids is None:
            # Remove from all plots
            all_plots = cls.get_all_plots()
            plot_ids = [p.db.story_id for p in all_plots]
        
        removed_count = 0
        for plot_id in plot_ids:
            plot = cls.find_plot(plot_id)
            if plot and hasattr(plot.db, 'update_ids') and update_id in plot.db.update_ids:
                plot.db.update_ids.remove(update_id)
                removed_count += 1
        
        return removed_count
    
    @classmethod
    def get_update_plots(cls, update_id):
        """Get all plots that contain a specific update.
        
        Args:
            update_id (int): The update ID to search for
            
        Returns:
            list: List of plot objects containing this update
        """
        all_plots = cls.get_all_plots()
        containing_plots = []
        for plot in all_plots:
            if hasattr(plot.db, 'update_ids') and update_id in plot.db.update_ids:
                containing_plots.append(plot)
        return containing_plots
    
    @classmethod
    def delete_chapter(cls, chapter_id):
        """Delete a chapter and all its story updates.
        
        Args:
            chapter_id (int): The chapter ID to delete
            
        Returns:
            tuple: (success, message, deleted_count) where:
                - success (bool): Whether the deletion succeeded
                - message (str): Status message
                - deleted_count (int): Number of story updates deleted
        """
        # Find the chapter
        chapter = cls.find_chapter(chapter_id)
        if not chapter:
            return False, f"Chapter #{chapter_id} not found", 0
        
        # Safety check: prevent deletion of current chapter
        if chapter.db.is_current:
            return False, "Cannot delete the current chapter. Set a different chapter as current first.", 0
        
        # Get and delete all story updates in this chapter
        updates = cls.get_chapter_updates(chapter_id)
        deleted_count = len(updates)
        for update in updates:
            update.delete()
        
        # Delete the chapter itself
        chapter_title = chapter.db.title
        chapter.delete()
        
        return True, f"Deleted chapter #{chapter_id}: {chapter_title}", deleted_count 