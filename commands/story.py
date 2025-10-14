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
        story <id>                      - Read story update from current book
        story "<book>" <id>             - Read story update from specific book
        story/read <id>                 - Read story update from current book
        story/read "<book>" <id>        - Read story update from specific book
        story/plots                     - List all plots
        story/plot <name>               - View updates in a plot
        story/plot "<name>" <id>        - Read specific update in plot
        
    Examples:
        story                           - View the full story timeline
        story 3                         - Read 3rd update in current book
        story "A New Book" 1            - Read 1st update in "A New Book"
        story/plots                     - List all plot threads
        story/plot "Rin"                - View all Rin plot updates
        story/plot "Rin" 3              - Read 3rd update in Rin plot
        
    Story updates use book-scoped numbering for user convenience. Each book
    has its own sequence (1, 2, 3...) while maintaining global IDs internally.
    """
    
    key = "story"
    locks = "cmd:all();create:perm(Builder);edit:perm(Builder);delete:perm(Builder);list:perm(Builder);read:all();plots:all();plot:all();tag:perm(Builder)"
    help_category = "General"
    switch_options = ("create", "edit", "delete", "list", "read", "plots", "plot", "tag")
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add staff commands if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yBuilder Commands:|n
        story/create <title>=<content>         - Create new story update
        story/edit <id>=<content>              - Edit story update
        story/edit "<book>" <id>=<content>     - Edit update from specific book
        story/delete <id>                      - Delete story update
        story/delete "<book>" <id>             - Delete update from specific book
        story/list                             - Show all story updates
        
    Builder Examples:
        story/create Tensions Rise=The Duke's mysterious visitors continue...
        story/edit 5=The Duke's mysterious visitors arrived under cover...
        story/edit "A New Book" 1=New content for first update...
        story/delete 5                         - Delete update #5
        story/list                             - List all updates
            """
        
        return help_text
    
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
            elif switch == "plots":
                self._list_plots()
            elif switch == "plot":
                self._view_plot()
            elif switch == "tag":
                if not self.access(self.caller, "tag"):
                    self.msg("You don't have permission to tag story updates.")
                    return
                self._tag_update()
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
        
        # Group chapters by book
        from collections import OrderedDict
        
        # Create hierarchical structure: book -> chapters
        book_structure = OrderedDict()
        
        for chapter in all_chapters:
            book = chapter.db.book_title or "Untitled Book"
            
            if book not in book_structure:
                book_structure[book] = []
            
            book_structure[book].append(chapter)
        
        # Get all plots for reference
        all_plots = StoryManager.get_all_plots()
        plot_map = {s.db.story_id: s.db.title for s in all_plots}
        
        # Display hierarchically
        for book_title, chapters in book_structure.items():
            lines.append(f"|yBook: {book_title}|n")
            
            for chapter in chapters:
                current_marker = " |g[CURRENT]|n" if chapter.db.is_current else ""
                lines.append(f"  |wChapter {chapter.db.story_id}: {chapter.db.title}{current_marker}|n")
                
                # Show updates for this chapter with plot tags
                updates = StoryManager.get_chapter_updates(chapter.db.story_id)
                if updates:
                    for update in updates[:10]:  # Show first 10
                        book_scoped = StoryManager.get_book_scoped_number(update.db.story_id, book_title)
                        
                        # Get plot tags for this update
                        update_plots = StoryManager.get_update_plots(update.db.story_id)
                        plot_tags = [p.db.title for p in update_plots]
                        
                        # Format plot tags
                        if plot_tags:
                            tag_str = " | ".join(plot_tags)
                            lines.append(f"    [{tag_str}] |c{update.db.title} ({book_scoped})|n")
                        else:
                            lines.append(f"    [Uncategorized] |c{update.db.title} ({book_scoped})|n")
                    
                    if len(updates) > 10:
                        lines.append(f"    |w... and {len(updates) - 10} more updates ...|n")
                else:
                    lines.append("    |w(No story updates yet)|n")
            
            lines.append("")  # Space between books
        
        # Summary
        total_updates = len(StoryManager.get_recent_updates(limit=999))
        current_pos = f"Chapter {current_chapter.db.story_id}" if current_chapter else "No current chapter"
        lines.append(f"|wSummary:|n {len(all_chapters)} chapters, {total_updates} story updates")
        lines.append(f"Currently at: |y{current_pos}|n")
        lines.append(f"Plots: {len(all_plots)} (use |wstory/plots|n to view)")
        
        self.msg("\n".join(lines))
    
    def _create_update(self):
        """Create a new story update."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: story/create <title>=<content>")
            self.msg("After creation, you'll be prompted to tag plots.")
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
            
        # Create the update (without plots for now)
        try:
            update = StoryManager.create_story_update(title, content, current_chapter.db.story_id)
            self.msg(f"Created story update #{update.db.story_id}: |c{title}|n")
            
            # Show available plots and prompt
            all_plots = StoryManager.get_all_plots()
            if all_plots:
                self.msg("\n|wAvailable plots:|n")
                for plot in all_plots:
                    self.msg(f"  {plot.db.story_id}. {plot.db.title}")
                self.msg(f"\nTo tag plots, use: |wstory/tag {update.db.story_id} <plot_ids>|n")
                self.msg(f"Example: |wstory/tag {update.db.story_id} 1,3|n (tags plots 1 and 3)")
            else:
                self.msg("\n|yNo plots exist yet.|n Use |wplot/create|n to create plot threads.")
            
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
            self.msg("Usage: story/edit <id>=<new content> OR story/edit \"<book>\" <id>=<new content>")
            return
            
        id_part, content = self.args.split("=", 1)
        content = content.strip()
        
        if not content:
            self.msg("Content cannot be empty.")
            return
        
        # Parse the ID part - might be just "3" or '"Book Title" 3'
        update, book_title = StoryManager.parse_story_reference(id_part.strip())
        
        if not update:
            self.msg(f"Story update not found. Use: story/edit <id>=<content> OR story/edit \"<book>\" <id>=<content>")
            return
            
        # Update content only, keep existing title
        update.db.content = content
        
        # Get book-scoped number for display
        book_scoped_num = StoryManager.get_book_scoped_number(update.db.story_id, book_title)
        
        if book_scoped_num and book_title and book_title != "Untitled Book":
            self.msg(f"Updated story update #{book_scoped_num} in '{book_title}': |c{update.db.title}|n")
        else:
            self.msg(f"Updated story update #{update.db.story_id}: |c{update.db.title}|n")
    
    def _delete_update(self):
        """Delete a story update."""
        if not self.args:
            self.msg("Usage: story/delete <id> OR story/delete \"<book>\" <id>")
            return
            
        # Parse the reference - might be just "3" or '"Book Title" 3'
        update, book_title = StoryManager.parse_story_reference(self.args.strip())
        
        if not update:
            self.msg(f"Story update not found. Use: story/delete <id> OR story/delete \"<book>\" <id>")
            return
            
        title = update.db.title
        global_id = update.db.story_id
        book_scoped_num = StoryManager.get_book_scoped_number(global_id, book_title)
        
        update.delete()
        
        if book_scoped_num and book_title and book_title != "Untitled Book":
            self.msg(f"Deleted story update #{book_scoped_num} from '{book_title}': |r{title}|n")
        else:
            self.msg(f"Deleted story update #{global_id}: |r{title}|n")
    
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
    
    def _tag_update(self):
        """Tag a story update with plot(s)."""
        if not self.args:
            self.msg("Usage: story/tag <update_id> <plot_ids>")
            self.msg("Example: story/tag 5 1,3  (tags update #5 with plots 1 and 3)")
            return
        
        parts = self.args.split(None, 1)
        if len(parts) < 2:
            self.msg("Usage: story/tag <update_id> <plot_ids>")
            return
        
        # Parse update ID
        try:
            update_id = int(parts[0])
        except ValueError:
            self.msg("Update ID must be a number.")
            return
        
        # Find the update
        update = StoryManager.find_story_update(update_id)
        if not update:
            self.msg(f"Story update #{update_id} not found.")
            return
        
        # Parse plot IDs (comma-separated)
        plot_ids_input = parts[1].strip()
        
        # Handle "none" to clear plots
        if plot_ids_input.lower() == "none":
            # Remove from all plots
            removed = StoryManager.remove_update_from_plots(update_id)
            self.msg(f"Removed update #{update_id} from {removed} plot(s): |c{update.db.title}|n")
            return
        
        # Parse plot IDs
        plot_ids = []
        for pid_str in plot_ids_input.split(','):
            try:
                pid = int(pid_str.strip())
                # Verify plot exists
                plot = StoryManager.find_plot(pid)
                if plot:
                    plot_ids.append(pid)
                else:
                    self.msg(f"|yWarning:|n Plot #{pid} not found, skipping.")
            except ValueError:
                self.msg(f"|yWarning:|n Invalid plot ID '{pid_str}', skipping.")
        
        if not plot_ids:
            self.msg("No valid plot IDs provided.")
            return
        
        # First, remove from all plots
        StoryManager.remove_update_from_plots(update_id)
        
        # Then add to specified plots
        added_plot_names = StoryManager.add_update_to_plots(update_id, plot_ids)
        
        if added_plot_names:
            tag_str = ", ".join(added_plot_names)
            self.msg(f"Tagged update #{update_id} with: |c{tag_str}|n")
        else:
            self.msg(f"No plots were updated.")
    
    def _list_plots(self):
        """List all plots and their info."""
        all_plots = StoryManager.get_all_plots()
        
        if not all_plots:
            self.msg("No plots have been created yet.")
            return
        
        lines = ["|wActive Plot Threads|n", ""]
        
        for plot in all_plots:
            # Get update count for this plot
            updates = StoryManager.get_plot_updates(plot.db.story_id)
            
            # Get chapter span
            if updates:
                chapters = set()
                for update in updates:
                    if update.db.parent_id:
                        chapters.add(update.db.parent_id)
                
                if chapters:
                    min_chapter = min(chapters)
                    max_chapter = max(chapters)
                    if min_chapter == max_chapter:
                        span_text = f"Chapter {min_chapter}"
                    else:
                        span_text = f"Chapters {min_chapter}-{max_chapter}"
                    
                    latest_update = updates[-1]
                    latest_chapter = StoryManager.find_chapter(latest_update.db.parent_id) if latest_update.db.parent_id else None
                    latest_chapter_num = latest_chapter.db.story_id if latest_chapter else "?"
                    
                    lines.append(f"|c{plot.db.title}|n ({len(updates)} updates)")
                    lines.append(f"  Spans: {span_text}")
                    lines.append(f"  Latest: \"{latest_update.db.title}\" (Chapter {latest_chapter_num})")
                    if plot.db.description:
                        lines.append(f"  |w{plot.db.description}|n")
                    lines.append("")
                else:
                    lines.append(f"|c{plot.db.title}|n ({len(updates)} updates)")
                    lines.append(f"  |w(No chapter data)|n")
                    if plot.db.description:
                        lines.append(f"  |w{plot.db.description}|n")
                    lines.append("")
            else:
                lines.append(f"|c{plot.db.title}|n (0 updates)")
                if plot.db.description:
                    lines.append(f"  |w{plot.db.description}|n")
                lines.append("")
        
        lines.append(f"Type |wstory/plot \"<name>\"|n to view updates in a specific plot.")
        
        self.msg("\n".join(lines))
    
    def _view_plot(self):
        """View all updates in a specific plot thread."""
        if not self.args:
            self.msg("Usage: story/plot <name> OR story/plot \"<name>\" <id>")
            return
        
        args = self.args.strip()
        
        # Check if there's a number at the end (reading specific update)
        parts = args.rsplit(None, 1)
        read_index = None
        plot_name = args
        
        if len(parts) == 2:
            try:
                read_index = int(parts[1])
                plot_name = parts[0]
            except ValueError:
                pass
        
        # Remove quotes if present
        if plot_name.startswith('"') and plot_name.endswith('"'):
            plot_name = plot_name[1:-1]
        
        # Find the plot
        plot = StoryManager.find_plot_by_name(plot_name)
        if not plot:
            self.msg(f"Plot '{plot_name}' not found. Use |wstory/plots|n to see available plots.")
            return
        
        # Get all updates in this plot
        updates = StoryManager.get_plot_updates(plot.db.story_id)
        
        if not updates:
            self.msg(f"|wPlot: {plot.db.title}|n\n\nNo updates in this plot yet.")
            return
        
        # If reading a specific update
        if read_index is not None:
            if read_index < 1 or read_index > len(updates):
                self.msg(f"Update #{read_index} not found in '{plot.db.title}'. This plot has {len(updates)} updates.")
                return
            
            update = updates[read_index - 1]
            chapter = StoryManager.find_chapter(update.db.parent_id) if update.db.parent_id else None
            
            lines = [f"|wPlot: {plot.db.title}|n"]
            if chapter:
                book = chapter.db.book_title or "Untitled Book"
                lines.append(f"|wBook: {book}|n")
                lines.append(f"|wChapter {chapter.db.story_id}: {chapter.db.title}|n")
            lines.append(f"|wUpdate #{read_index} of {len(updates)}: {update.db.title}|n")
            lines.append(f"|wDate:|n {update.db.timestamp.strftime('%Y-%m-%d %H:%M')}")
            lines.append("")
            lines.append(update.db.content)
            
            self.msg("\n".join(lines))
            return
        
        # Otherwise, list all updates in the plot
        lines = [f"|wPlot: {plot.db.title}|n"]
        if plot.db.description:
            lines.append(f"{plot.db.description}")
        lines.append("")
        
        # Group by chapter
        from collections import OrderedDict
        updates_by_chapter = OrderedDict()
        
        for update in updates:
            chapter_id = update.db.parent_id
            if chapter_id not in updates_by_chapter:
                updates_by_chapter[chapter_id] = []
            updates_by_chapter[chapter_id].append(update)
        
        update_index = 1
        for chapter_id, chapter_updates in updates_by_chapter.items():
            chapter = StoryManager.find_chapter(chapter_id) if chapter_id else None
            if chapter:
                lines.append(f"|yChapter {chapter.db.story_id}: {chapter.db.title}|n")
            else:
                lines.append(f"|y(No Chapter)|n")
            
            for update in chapter_updates:
                lines.append(f"  {update_index}. |c{update.db.title}|n")
                update_index += 1
            
            lines.append("")
        
        lines.append(f"Type |wstory/plot \"{plot.db.title}\" <number>|n to read a specific update.")
        
        self.msg("\n".join(lines))


class CmdChapter(MuxCommand):
    """
    Manage story chapters and view chapter information.
    
    Usage:
        chapter                           - Show current chapter info
        chapter <id>                      - Show specific chapter info
        
    Examples:
        chapter                           - View current chapter
        chapter 2                         - View chapter #2
        
    Chapters represent mechanical game periods (action budget units). Books 
    are organizational labels for grouping chapters chronologically.
    """
    
    key = "chapter"
    locks = "cmd:all();create:perm(Builder);setcurrent:perm(Builder);edit:perm(Builder);book:perm(Builder);time:perm(Builder);delete:perm(Builder);list:perm(Builder);debug:perm(Builder)"
    help_category = "General"
    switch_options = ("create", "setcurrent", "edit", "book", "time", "delete", "list", "debug")
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add staff commands if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yBuilder Commands:|n
        chapter/create <title>            - Create new chapter
        chapter/setcurrent <id>           - Set current chapter
        chapter/edit <id> <title>         - Edit chapter title
        chapter/book <id> <book_title>    - Set chapter's book
        chapter/time <id> <time_desc>     - Set chapter's time
        chapter/delete <id>               - Delete chapter
        chapter/list                      - List all chapters
        chapter/debug                     - Show chapter debug info
        
    Builder Examples:
        chapter/create Prologue
        chapter/setcurrent 3                      - Set chapter 3 as current
        chapter/edit 3 Chapter 1: The Gathering Storm
        chapter/book 3 The Imperial Crisis        - Set book title
        chapter/time 3 Three days after siege     - Set time description
        chapter/list                              - List all chapters
            """
        
        return help_text
    
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
            
        table = evtable.EvTable("ID", "Title", "Book", "Time", "Current", border="cells")
        
        for chapter in all_chapters:
            current_marker = "|gYes|n" if chapter.db.is_current else "No"
            book = chapter.db.book_title or "-"
            chapter_time = getattr(chapter.db, 'chapter_time', '') or "-"
            
            table.add_row(chapter.db.story_id, chapter.db.title, book, chapter_time, current_marker)
            
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


class CmdPlot(MuxCommand):
    """
    Manage plot threads for organizing story updates.
    
    Usage:
        plot                              - List all plots
        plot <id>                         - View specific plot info
        
    Plots are thematic story threads that span across chapters and books.
    Story updates can be tagged with a plot to organize concurrent storylines.
    """
    
    key = "plot"
    locks = "cmd:all();create:perm(Builder);edit:perm(Builder);delete:perm(Builder);activate:perm(Builder);deactivate:perm(Builder)"
    help_category = "General"
    switch_options = ("create", "edit", "delete", "activate", "deactivate")
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add staff commands if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yBuilder Commands:|n
        plot/create <title>=<description>    - Create new plot thread
        plot/edit <id>=<new description>     - Edit plot description
        plot/delete <id>                     - Delete plot thread
        plot/activate <id>                   - Mark plot as active
        plot/deactivate <id>                 - Mark plot as inactive
        
    Builder Examples:
        plot/create Rin's Journey=Following Rin's adventures in the city
        plot/edit 1=Updated description of Rin's story arc
        plot/delete 3                        - Remove unused plot
        plot/activate 1                      - Mark plot as active
            """
        
        return help_text
    
    def func(self):
        """Execute the command."""
        if self.switches:
            switch = self.switches[0]
            
            if switch == "create":
                if not self.access(self.caller, "create"):
                    self.msg("You don't have permission to create plots.")
                    return
                self._create_plot()
            elif switch == "edit":
                if not self.access(self.caller, "edit"):
                    self.msg("You don't have permission to edit plots.")
                    return
                self._edit_plot()
            elif switch == "delete":
                if not self.access(self.caller, "delete"):
                    self.msg("You don't have permission to delete plots.")
                    return
                self._delete_plot()
            elif switch == "activate":
                if not self.access(self.caller, "activate"):
                    self.msg("You don't have permission to activate plots.")
                    return
                self._activate_plot()
            elif switch == "deactivate":
                if not self.access(self.caller, "deactivate"):
                    self.msg("You don't have permission to deactivate plots.")
                    return
                self._deactivate_plot()
            else:
                self.msg(f"Unknown switch: {switch}")
        else:
            # Default: list all plots or show specific plot
            if self.args:
                self._show_plot()
            else:
                self._list_plots()
    
    def _list_plots(self):
        """List all plots."""
        all_plots = StoryManager.get_all_plots()
        
        if not all_plots:
            self.msg("No plots have been created yet.")
            return
        
        lines = ["|wPlot Threads|n", ""]
        
        for plot in all_plots:
            active_marker = "|g[ACTIVE]|n" if plot.db.is_active else "|x[INACTIVE]|n"
            updates = StoryManager.get_plot_updates(plot.db.story_id)
            lines.append(f"|cPlot {plot.db.story_id}: {plot.db.title}|n {active_marker}")
            lines.append(f"  Updates: {len(updates)}")
            if plot.db.description:
                lines.append(f"  {plot.db.description}")
            lines.append("")
        
        self.msg("\n".join(lines))
    
    def _show_plot(self):
        """Show specific plot information."""
        if not self.args:
            self.msg("Usage: plot <id>")
            return
        
        try:
            plot_id = int(self.args.strip())
        except ValueError:
            self.msg("Plot ID must be a number.")
            return
        
        # Find the plot
        plot = StoryManager.find_plot(plot_id)
        if not plot:
            self.msg(f"Plot #{plot_id} not found.")
            return
        
        lines = [f"|wPlot {plot.db.story_id}: {plot.db.title}|n"]
        lines.append(f"Status: {'|gActive|n' if plot.db.is_active else '|xInactive|n'}")
        
        if plot.db.description:
            lines.append(f"\n{plot.db.description}")
        
        lines.append("")
        
        # Show updates in this plot
        updates = StoryManager.get_plot_updates(plot.db.story_id)
        if updates:
            lines.append(f"|wStory Updates ({len(updates)}):|n")
            for i, update in enumerate(updates[:10], 1):
                chapter = StoryManager.find_chapter(update.db.parent_id) if update.db.parent_id else None
                chapter_text = f"(Chapter {chapter.db.story_id})" if chapter else ""
                timestamp = update.db.timestamp.strftime("%Y-%m-%d")
                lines.append(f"  {i}. |c{update.db.title}|n {chapter_text} ({timestamp})")
            
            if len(updates) > 10:
                lines.append(f"  ... and {len(updates) - 10} more")
        else:
            lines.append("No story updates in this plot yet.")
        
        self.msg("\n".join(lines))
    
    def _create_plot(self):
        """Create a new plot."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: plot/create <title>=<description>")
            return
        
        title, description = self.args.split("=", 1)
        title = title.strip()
        description = description.strip()
        
        if not title:
            self.msg("Title cannot be empty.")
            return
        
        # Create the plot
        try:
            plot = StoryManager.create_plot(title, description)
            self.msg(f"Created plot #{plot.db.story_id}: |c{title}|n")
            
        except Exception as e:
            self.msg(f"Error creating plot: {e}")
    
    def _edit_plot(self):
        """Edit a plot's description."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: plot/edit <id>=<new description>")
            return
        
        id_part, description = self.args.split("=", 1)
        description = description.strip()
        
        try:
            plot_id = int(id_part.strip())
        except ValueError:
            self.msg("Plot ID must be a number.")
            return
        
        # Find the plot
        plot = StoryManager.find_plot(plot_id)
        if not plot:
            self.msg(f"Plot #{plot_id} not found.")
            return
        
        plot.db.description = description
        self.msg(f"Updated plot #{plot_id}: |c{plot.db.title}|n")
    
    def _delete_plot(self):
        """Delete a plot."""
        if not self.args:
            self.msg("Usage: plot/delete <id>")
            return
        
        try:
            plot_id = int(self.args.strip())
        except ValueError:
            self.msg("Plot ID must be a number.")
            return
        
        # Use StoryManager to delete the plot
        success, message, unlinked_count = StoryManager.delete_plot(plot_id)
        
        if success:
            self.msg(f"|gSuccess:|n {message}")
            if unlinked_count > 0:
                self.msg(f"|yNote:|n This unlinked {unlinked_count} story updates from this plot.")
        else:
            self.msg(f"|rError:|n {message}")
    
    def _activate_plot(self):
        """Mark a plot as active."""
        if not self.args:
            self.msg("Usage: plot/activate <id>")
            return
        
        try:
            plot_id = int(self.args.strip())
        except ValueError:
            self.msg("Plot ID must be a number.")
            return
        
        # Find the plot
        plot = StoryManager.find_plot(plot_id)
        if not plot:
            self.msg(f"Plot #{plot_id} not found.")
            return
        
        plot.db.is_active = True
        self.msg(f"Marked plot #{plot_id} as |gactive|n: |c{plot.db.title}|n")
    
    def _deactivate_plot(self):
        """Mark a plot as inactive."""
        if not self.args:
            self.msg("Usage: plot/deactivate <id>")
            return
        
        try:
            plot_id = int(self.args.strip())
        except ValueError:
            self.msg("Plot ID must be a number.")
            return
        
        # Find the plot
        plot = StoryManager.find_plot(plot_id)
        if not plot:
            self.msg(f"Plot #{plot_id} not found.")
            return
        
        plot.db.is_active = False
        self.msg(f"Marked plot #{plot_id} as |xinactive|n: |c{plot.db.title}|n") 