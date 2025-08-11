"""
Commands for the story system.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import create_script
from evennia.utils import evtable
from typeclasses.story import StoryElement
from typeclasses.time import NarrativeTime
from utils.story_manager import StoryManager
from datetime import datetime


class CmdStory(MuxCommand):
    """
    Manage story updates and view story timeline.
    
    Usage:
        story                           - Show story timeline
        story <id>                      - Read story update (book-scoped number)
        story "<book>" <id>             - Read story update from specific book
        story/read <id>                 - Read story update (book-scoped number)
        story/read "<book>" <id>        - Read story update from specific book
        story/create <title>=<content> - Create new story update (staff only)
        story/edit <id> <title>=<content> - Edit story update (staff only)
        story/delete <id>               - Delete story update (staff only)
        story/list                      - Show all story updates (staff only)
        
    Examples:
        story
        story 3                         (3rd update in current book)
        story "A New Book" 1            (1st update in "A New Book")
        story/read 3
        story/create Tensions Rise=The Duke's mysterious visitors continue to arrive...
        story/edit 5 Tensions Rise=The Duke's mysterious visitors arrived under cover of darkness...
        story/delete 5
        
    Story updates use book-scoped numbering for user convenience. Each book
    has its own sequence (1, 2, 3...) while maintaining global IDs internally.
    """
    
    key = "story"
    locks = "cmd:all();create:perm(Builder);edit:perm(Builder);delete:perm(Builder);list:perm(Builder);read:all()"
    help_category = "General"
    switch_options = ("create", "edit", "delete", "list", "read")
    
    def func(self):
        """Execute the command."""
        if self.switches:
            switch = self.switches[0]
            
            if switch == "create":
                if not self.access(self.caller, "create"):
                    self.msg("You don't have permission to create story updates.")
                    return
                self._create_update()
            elif switch == "edit":
                if not self.access(self.caller, "edit"):
                    self.msg("You don't have permission to edit story updates.")
                    return
                self._edit_update()
            elif switch == "delete":
                if not self.access(self.caller, "delete"):
                    self.msg("You don't have permission to delete story updates.")
                    return
                self._delete_update()
            elif switch == "list":
                if not self.access(self.caller, "list"):
                    self.msg("You don't have permission to list all story updates.")
                    return
                self._list_all_updates()
            elif switch == "read":
                self._read_update()
            else:
                self.msg(f"Unknown switch: {switch}")
        else:
            # If there are arguments, treat it as a read command
            if self.args.strip():
                self._read_update()
            else:
                # Default: show story timeline
                self._show_recent_updates()
    
    def _show_recent_updates(self):
        """Show overall story timeline and progression."""
        # Get all chapters
        all_chapters = StoryManager.get_all_chapters()
        current_chapter = StoryManager.get_current_chapter()
        
        if not all_chapters:
            self.msg("No story chapters have been created yet.")
            return
            
        lines = ["|wStory Timeline - The Story So Far|n"]
        
        # Show current time
        time_tracker = NarrativeTime.get_instance()
        lines.append(f"Current Time: |g{time_tracker.current_time}|n")
        lines.append("")
        
        # Group chapters by book and volume
        from collections import defaultdict, OrderedDict
        
        # Create hierarchical structure: book -> volume -> chapters
        book_structure = OrderedDict()
        
        for chapter in all_chapters:
            book = chapter.db.book_title or "Untitled Book"
            volume = chapter.db.volume_title or "Untitled Volume"
            
            if book not in book_structure:
                book_structure[book] = OrderedDict()
            if volume not in book_structure[book]:
                book_structure[book][volume] = []
            
            book_structure[book][volume].append(chapter)
        
        # Display hierarchically
        for book_title, volumes in book_structure.items():
            lines.append(f"|yBook: {book_title}|n")
            
            for volume_title, chapters in volumes.items():
                lines.append(f"  |cVolume: {volume_title}|n")
                
                for chapter in chapters:
                    lines.append(f"    |wChapter {chapter.db.story_id}: {chapter.db.title}|n")
                    
                    # Show key updates for this chapter
                    updates = StoryManager.get_chapter_updates(chapter.db.story_id)
                    if updates:
                        # Show first and last update if multiple, or just the updates if few
                        if len(updates) <= 3:
                            for update in updates:
                                book_scoped = StoryManager.get_book_scoped_number(update.db.story_id, book_title)
                                lines.append(f"      - |c{update.db.title} ({book_scoped})|n")
                        else:
                            # Show first, middle indicator, and last
                            first_scoped = StoryManager.get_book_scoped_number(updates[0].db.story_id, book_title)
                            last_scoped = StoryManager.get_book_scoped_number(updates[-1].db.story_id, book_title)
                            lines.append(f"      - |c{updates[0].db.title} ({first_scoped})|n")
                            lines.append(f"      - |w... {len(updates)-2} more updates ...|n")
                            lines.append(f"      - |c{updates[-1].db.title} ({last_scoped})|n")
                    else:
                        lines.append("      |w(No story updates yet)|n")
                
                lines.append("")  # Space between volumes
            
            lines.append("")  # Space between books
        
        # Summary
        total_updates = len(StoryManager.get_recent_updates(limit=999))
        current_pos = f"Chapter {current_chapter.db.story_id}" if current_chapter else "No current chapter"
        lines.append(f"|wSummary:|n {len(all_chapters)} chapters, {total_updates} story updates")
        lines.append(f"Currently at: |y{current_pos}|n")
        
        self.msg("\n".join(lines))
    
    def _create_update(self):
        """Create a new story update."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: story/create <title>=<content>")
            return
            
        title, content = self.args.split("=", 1)
        title = title.strip()
        content = content.strip()
        
        if not title:
            self.msg("Title cannot be empty.")
            return
        if not content:
            self.msg("Content cannot be empty.")
            return
            
        # Get current chapter
        current_chapter = StoryManager.get_current_chapter()
        if not current_chapter:
            self.msg("No current chapter set. Use chapter/create to create one first.")
            return
            
        # Create the update
        try:
            update = StoryManager.create_story_update(title, content, current_chapter.db.story_id)
            self.msg(f"Created story update #{update.db.story_id}: |c{title}|n")
            
        except Exception as e:
            self.msg(f"Error creating story update: {e}")
            return
        
        # Announce to all online players
        from evennia.server.sessionhandler import SESSIONS
        
        # Get book-scoped number for the notification
        current_book = StoryManager.get_current_book_title()
        book_scoped_num = StoryManager.get_book_scoped_number(update.db.story_id, current_book)
        
        if book_scoped_num:
            if current_book and current_book != "Untitled Book":
                message = f"|wStory Update #{book_scoped_num}:|n {title} |w({current_book})|n"
            else:
                message = f"|wStory Update #{book_scoped_num}:|n {title}"
        else:
            message = f"|wStory Update:|n {title}"
            
        # Send to online players immediately, store for offline players
        from evennia.accounts.models import AccountDB
        
        # Get list of online accounts and send immediate notifications
        online_accounts = set()
        for session in SESSIONS.get_sessions():
            if session.logged_in and session.get_puppet():
                session.msg(message)  # Immediate display, no storage
                online_accounts.add(session.account)
        
        # Store notification for offline players only
        for account in AccountDB.objects.all():
            if account not in online_accounts:
                notifications = account.db.offline_story_notifications or []
                notifications.append(message)
                account.db.offline_story_notifications = notifications
    
    def _edit_update(self):
        """Edit an existing story update."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: story/edit <id> <title>=<content>")
            return
            
        id_and_title, content = self.args.split("=", 1)
        content = content.strip()
        
        parts = id_and_title.strip().split(" ", 1)
        if len(parts) < 2:
            self.msg("Usage: story/edit <id> <title>=<content>")
            return
            
        try:
            update_id = int(parts[0])
        except ValueError:
            self.msg("Update ID must be a number.")
            return
            
        title = parts[1].strip()
        
        if not title:
            self.msg("Title cannot be empty.")
            return
        if not content:
            self.msg("Content cannot be empty.")
            return
            
        # Find the update
        update = StoryManager.find_story_update(update_id)
        if not update:
            self.msg(f"Story update #{update_id} not found.")
            return
            
        # Update it
        old_title = update.db.title
        update.db.title = title
        update.db.content = content
        
        self.msg(f"Updated story update #{update_id}: |y{old_title}|n -> |c{title}|n")
    
    def _delete_update(self):
        """Delete a story update."""
        if not self.args:
            self.msg("Usage: story/delete <id>")
            return
            
        try:
            update_id = int(self.args.strip())
        except ValueError:
            self.msg("Update ID must be a number.")
            return
            
        # Find the update
        update = StoryManager.find_story_update(update_id)
        if not update:
            self.msg(f"Story update #{update_id} not found.")
            return
            
        title = update.db.title
        update.delete()
        
        self.msg(f"Deleted story update #{update_id}: |r{title}|n")
    
    def _list_all_updates(self):
        """List all story updates for staff."""
        all_updates = StoryManager.get_recent_updates(limit=20)
        
        if not all_updates:
            self.msg("No story updates found.")
            return
            
        table = evtable.EvTable("ID", "Title", "Chapter", "Date", border="cells")
        
        for update in all_updates:
            # Find which chapter this belongs to
            chapter = StoryManager.find_chapter(update.db.parent_id) if update.db.parent_id else None
            chapter_name = f"Chapter {chapter.db.story_id}" if chapter else "Unknown"
            date_str = update.db.timestamp.strftime("%m/%d")
            
            table.add_row(update.db.story_id, update.db.title, chapter_name, date_str)
            
        self.msg(table)
    
    def _read_update(self):
        """Read a specific story update in full."""
        if not self.args:
            self.msg("Usage: story/read <id> OR story/read \"<book>\" <id>")
            return
            
        # Use the new parsing helper
        update, book_title = StoryManager.parse_story_reference(self.args)
        
        if not update:
            self.msg(f"Story update not found. Use: story/read <id> OR story/read \"<book>\" <id>")
            return
            
        # Find which chapter this belongs to
        chapter = StoryManager.find_chapter(update.db.parent_id) if update.db.parent_id else None
        
        # Get book-scoped number for display
        book_scoped_num = StoryManager.get_book_scoped_number(update.db.story_id, book_title)
        
        lines = []
        if book_title and book_title != "Untitled Book":
            lines.append(f"|wBook: {book_title}|n")
        if chapter:
            lines.append(f"|wChapter {chapter.db.story_id}: {chapter.db.title}|n")
        
        # Show both book-scoped and global numbers
        if book_scoped_num:
            lines.append(f"|wStory Update #{book_scoped_num} (Global #{update.db.story_id}): {update.db.title}|n")
        else:
            lines.append(f"|wStory Update #{update.db.story_id}: {update.db.title}|n")
            
        lines.append(f"|wDate:|n {update.db.timestamp.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append(update.db.content)
        
        self.msg("\n".join(lines))


class CmdChapter(MuxCommand):
    """
    Manage story chapters and view chapter information.
    
    Usage:
        chapter                           - Show current chapter info
        chapter <id>                      - Show specific chapter info
        chapter/create <title>            - Create new chapter (staff only)
        chapter/setcurrent <id>           - Set current chapter (staff only)
        chapter/edit <id> <title>         - Edit chapter title (staff only)
        chapter/book <id> <book_title>    - Set chapter's book (staff only)
        chapter/volume <id> <volume_title> - Set chapter's volume (staff only)
        chapter/time <id> <time_desc>     - Set chapter's time (staff only)
        chapter/list                      - List all chapters (staff only)
        
    Examples:
        chapter
        chapter 2
        chapter/create Chapter 1: Gathering Storm - Spring 632 AF
        chapter/setcurrent 3
        chapter/edit 3 Chapter 1: The Gathering Storm - Spring 632 AF
        chapter/book 3 The Imperial Crisis
        chapter/volume 3 Volume I: Seeds of Rebellion
        chapter/time 3 Three days after the siege began
        
    Chapters represent major story divisions. Books and volumes are 
    organisational labels for grouping chapters in the larger narrative.
    """
    
    key = "chapter"
    locks = "cmd:all();create:perm(Builder);setcurrent:perm(Builder);edit:perm(Builder);book:perm(Builder);volume:perm(Builder);time:perm(Builder);delete:perm(Builder);list:perm(Builder);debug:perm(Builder)"
    help_category = "General"
    switch_options = ("create", "setcurrent", "edit", "book", "volume", "time", "delete", "list", "debug")
    
    def func(self):
        """Execute the command."""
        if self.switches:
            switch = self.switches[0]
            
            if switch == "create":
                if not self.access(self.caller, "create"):
                    self.msg("You don't have permission to create chapters.")
                    return
                self._create_chapter()
            elif switch == "setcurrent":
                if not self.access(self.caller, "setcurrent"):
                    self.msg("You don't have permission to set current chapter.")
                    return
                self._set_current()
            elif switch == "edit":
                if not self.access(self.caller, "edit"):
                    self.msg("You don't have permission to edit chapters.")
                    return
                self._edit_chapter()
            elif switch == "book":
                if not self.access(self.caller, "book"):
                    self.msg("You don't have permission to set chapter books.")
                    return
                self._set_book()
            elif switch == "volume":
                if not self.access(self.caller, "volume"):
                    self.msg("You don't have permission to set chapter volumes.")
                    return
                self._set_volume()
            elif switch == "time":
                if not self.access(self.caller, "time"):
                    self.msg("You don't have permission to set chapter times.")
                    return
                self._set_chapter_time()
            elif switch == "delete":
                if not self.access(self.caller, "delete"):
                    self.msg("You don't have permission to delete chapters.")
                    return
                self._delete_chapter()
            elif switch == "list":
                if not self.access(self.caller, "list"):
                    self.msg("You don't have permission to list all chapters.")
                    return
                self._list_chapters()
            elif switch == "debug":
                self._debug_search()
            else:
                self.msg(f"Unknown switch: {switch}")
        else:
            # Default: show current chapter or specific chapter if ID provided
            if self.args:
                self._show_specific_chapter()
            else:
                self._show_current_chapter()
    
    def _show_current_chapter(self):
        """Show current chapter information."""
        current_chapter = StoryManager.get_current_chapter()
        if not current_chapter:
            self.msg("No current chapter set.")
            return
            
        lines = ["|wCurrent Chapter|n"]
        
        # Show hierarchy
        if current_chapter.db.book_title:
            lines.append(f"Book: |c{current_chapter.db.book_title}|n")
        if current_chapter.db.volume_title:
            lines.append(f"Volume: |c{current_chapter.db.volume_title}|n")
        lines.append(f"Chapter {current_chapter.db.story_id}: |y{current_chapter.db.title}|n")
        
        # Show time - chapter-specific if set, otherwise global narrative time
        if hasattr(current_chapter.db, 'chapter_time') and current_chapter.db.chapter_time:
            lines.append(f"Chapter Time: |g{current_chapter.db.chapter_time}|n")
        else:
            time_tracker = NarrativeTime.get_instance()
            lines.append(f"Global Time: |g{time_tracker.current_time}|n")
        lines.append("")
        
        # Show all story updates in this chapter
        updates = StoryManager.get_chapter_updates(current_chapter.db.story_id)
        if updates:
            lines.append(f"|wStory Updates ({len(updates)}):|n")
            for update in updates:
                timestamp = update.db.timestamp.strftime("%Y-%m-%d")
                lines.append(f"  {update.db.story_id}. |c{update.db.title}|n ({timestamp})")
                # Show preview of content
                content_preview = update.db.content.split('\n')[0][:70]
                if len(update.db.content) > 70:
                    content_preview += "..."
                lines.append(f"    {content_preview}")
                lines.append("")  # Blank line between updates
        else:
            lines.append("No story updates in this chapter yet.")
            
        self.msg("\n".join(lines))
    
    def _show_specific_chapter(self):
        """Show specific chapter information."""
        if not self.args:
            self.msg("Usage: chapter <id>")
            return
            
        try:
            chapter_id = int(self.args.strip())
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        # Find the chapter
        chapter = StoryManager.find_chapter(chapter_id)
        if not chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
            
        lines = [f"|wChapter {chapter.db.story_id}|n"]
        
        # Show hierarchy
        if chapter.db.book_title:
            lines.append(f"Book: |c{chapter.db.book_title}|n")
        if chapter.db.volume_title:
            lines.append(f"Volume: |c{chapter.db.volume_title}|n")
        lines.append(f"Title: |y{chapter.db.title}|n")
        
        # Show if this is current
        if chapter.db.is_current:
            lines.append("|g[CURRENT CHAPTER]|n")
            
        # Show time - chapter-specific if set, otherwise global for current chapter
        if hasattr(chapter.db, 'chapter_time') and chapter.db.chapter_time:
            lines.append(f"Chapter Time: |g{chapter.db.chapter_time}|n")
        elif chapter.db.is_current:
            time_tracker = NarrativeTime.get_instance()
            lines.append(f"Global Time: |g{time_tracker.current_time}|n")
        
        lines.append("")
        
        # Show all story updates in this chapter
        updates = StoryManager.get_chapter_updates(chapter.db.story_id)
        if updates:
            lines.append(f"|wStory Updates ({len(updates)}):|n")
            for update in updates:
                timestamp = update.db.timestamp.strftime("%Y-%m-%d")
                lines.append(f"  {update.db.story_id}. |c{update.db.title}|n ({timestamp})")
                # Show preview of content
                content_preview = update.db.content.split('\n')[0][:70]
                if len(update.db.content) > 70:
                    content_preview += "..."
                lines.append(f"    {content_preview}")
                lines.append("")  # Blank line between updates
        else:
            lines.append("No story updates in this chapter yet.")
            
        self.msg("\n".join(lines))
    
    def _create_chapter(self):
        """Create a new chapter."""
        if not self.args:
            self.msg("Usage: chapter/create <title>")
            return
            
        title = self.args.strip()
        if not title:
            self.msg("Title cannot be empty.")
            return
            
        # Create the chapter
        try:
            chapter = StoryManager.create_chapter(title)
            self.msg(f"Created chapter #{chapter.db.story_id}: |c{title}|n")
            self.msg("Use chapter/setcurrent to make this the active chapter.")
            
        except Exception as e:
            self.msg(f"Error creating chapter: {e}")
    
    def _set_current(self):
        """Set the current chapter."""
        if not self.args:
            self.msg("Usage: chapter/setcurrent <id>")
            return
            
        try:
            chapter_id = int(self.args.strip())
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        # Set current chapter using manager
        target_chapter = StoryManager.set_current_chapter(chapter_id)
        if not target_chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
        
        self.msg(f"Set current chapter to #{target_chapter.db.story_id}: |c{target_chapter.db.title}|n")
    
    def _edit_chapter(self):
        """Edit a chapter title."""
        if not self.args:
            self.msg("Usage: chapter/edit <id> <title>")
            return
            
        parts = self.args.split(" ", 1)
        if len(parts) < 2:
            self.msg("Usage: chapter/edit <id> <title>")
            return
            
        try:
            chapter_id = int(parts[0])
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        new_title = parts[1].strip()
        if not new_title:
            self.msg("Title cannot be empty.")
            return
            
        # Find the chapter
        target_chapter = StoryManager.find_chapter(chapter_id)
        if not target_chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
            
        old_title = target_chapter.db.title
        target_chapter.db.title = new_title
        
        self.msg(f"Updated chapter #{chapter_id}: |y{old_title}|n -> |c{new_title}|n")
    
    def _set_book(self):
        """Set a chapter's book."""
        if not self.args:
            self.msg("Usage: chapter/book <id> <book_title>")
            return
            
        parts = self.args.split(" ", 1)
        if len(parts) < 2:
            self.msg("Usage: chapter/book <id> <book_title>")
            return
            
        try:
            chapter_id = int(parts[0])
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        book_title = parts[1].strip()
        
        # Find the chapter
        target_chapter = StoryManager.find_chapter(chapter_id)
        if not target_chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
            
        target_chapter.db.book_title = book_title
        self.msg(f"Set chapter #{chapter_id} book to: |c{book_title}|n")
    
    def _set_volume(self):
        """Set a chapter's volume."""
        if not self.args:
            self.msg("Usage: chapter/volume <id> <volume_title>")
            return
            
        parts = self.args.split(" ", 1)
        if len(parts) < 2:
            self.msg("Usage: chapter/volume <id> <volume_title>")
            return
            
        try:
            chapter_id = int(parts[0])
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        volume_title = parts[1].strip()
        
        # Find the chapter
        target_chapter = StoryManager.find_chapter(chapter_id)
        if not target_chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
            
        target_chapter.db.volume_title = volume_title
        self.msg(f"Set chapter #{chapter_id} volume to: |c{volume_title}|n")
    
    def _set_chapter_time(self):
        """Set a chapter's time description."""
        if not self.args:
            self.msg("Usage: chapter/time <id> <time_description>")
            return
            
        parts = self.args.split(" ", 1)
        if len(parts) < 2:
            self.msg("Usage: chapter/time <id> <time_description>")
            return
            
        try:
            chapter_id = int(parts[0])
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        time_desc = parts[1].strip()
        
        # Find the chapter
        target_chapter = StoryManager.find_chapter(chapter_id)
        if not target_chapter:
            self.msg(f"Chapter #{chapter_id} not found.")
            return
            
        target_chapter.db.chapter_time = time_desc
        self.msg(f"Set chapter #{chapter_id} time to: |c{time_desc}|n")
    
    def _delete_chapter(self):
        """Delete a chapter and all its story updates."""
        if not self.args:
            self.msg("Usage: chapter/delete <id>")
            return
            
        try:
            chapter_id = int(self.args.strip())
        except ValueError:
            self.msg("Chapter ID must be a number.")
            return
            
        # Use StoryManager to delete the chapter
        success, message, deleted_count = StoryManager.delete_chapter(chapter_id)
        
        if success:
            self.msg(f"|gSuccess:|n {message}")
            if deleted_count > 0:
                self.msg(f"|yNote:|n This also deleted {deleted_count} story updates that were in this chapter.")
        else:
            self.msg(f"|rError:|n {message}")
    
    def _list_chapters(self):
        """List all chapters for staff."""
        all_chapters = StoryManager.get_all_chapters()
        
        if not all_chapters:
            self.msg("No chapters found.")
            return
            
        table = evtable.EvTable("ID", "Title", "Book", "Volume", "Current", border="cells")
        
        table = evtable.EvTable("ID", "Title", "Book", "Volume", "Time", "Current", border="cells")
        
        for chapter in all_chapters:
            current_marker = "|gYes|n" if chapter.db.is_current else "No"
            book = chapter.db.book_title or "-"
            volume = chapter.db.volume_title or "-"
            chapter_time = getattr(chapter.db, 'chapter_time', '') or "-"
            
            table.add_row(chapter.db.story_id, chapter.db.title, book, volume, chapter_time, current_marker)
            
        self.msg(table) 

    def _debug_search(self):
        """Debug story system status."""
        self.msg("Story System Status:")
        
        # Show chapters
        all_chapters = StoryManager.get_all_chapters()
        self.msg(f"Chapters: {len(all_chapters)}")
        for chapter in all_chapters:
            current = " [CURRENT]" if chapter.db.is_current else ""
            self.msg(f"  Chapter {chapter.db.story_id}: {chapter.db.title}{current}")
        
        # Show recent updates
        all_updates = StoryManager.get_recent_updates(limit=10)
        self.msg(f"Recent Updates: {len(all_updates)}")
        for update in all_updates[:5]:
            chapter = StoryManager.find_chapter(update.db.parent_id) if update.db.parent_id else None
            chapter_name = f"Chapter {chapter.db.story_id}" if chapter else "No Chapter"
            self.msg(f"  Update {update.db.story_id}: {update.db.title} ({chapter_name})")
        
        # Show current time
        time_tracker = NarrativeTime.get_instance()
        self.msg(f"Current Time: {time_tracker.current_time}")
        
        self.msg("Debug complete.") 