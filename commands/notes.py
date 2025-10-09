"""
Commands for managing character notes.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from evennia.utils import evtable
from utils.command_mixins import CharacterLookupMixin
from datetime import datetime


class CmdNote(CharacterLookupMixin, MuxCommand):
    """
    Manage character notes - OOC and IC journals, staff notes, etc.
    
    Usage:
        note                           - List all your notes
        note/ooc title=content         - Add an OOC note
        note/ic title=content          - Add an IC note
        note/edit id=content           - Edit a note's content
        note/delete id                 - Delete a note
        note/show id                   - Show detailed view of a note
        note/tag id=tag1,tag2          - Add/update tags for a note
        note/public id                 - Toggle public visibility (IC only)
        note/search text               - Search note content
        note/filter tag                - Filter by tag
        note/category ooc or ic        - Show notes of specific category
        
    Public notes:
        note/view character                     - List character's public IC notes
        note/view character id                  - Read specific public IC note
        
    Examples:
        note/ooc Planning=Remember to follow up on the tavern mystery
        note/ic Journal=Met a mysterious stranger at the crossroads today
        note/tag 1=planning,session-3
        note/public 2                             - Make IC note #2 public
        note/search stranger                      - Find notes mentioning "stranger"
        note/filter journal                       - Show notes tagged "journal"
        note/view John                            - List John's public IC notes
        note/view John 2                          - Read John's public note #2
        
    Notes:
    - OOC notes are always private to you and GM
    - IC notes are private by default, but can be made public
    - Public IC notes are visible to other players when they examine you
    - Note IDs are unique per character
    - Tags are comma-separated and help organize notes
    """
    
    key = "note"
    aliases = ["notes"]
    locks = "cmd:all()"
    help_category = "Character"
    switch_options = ("ooc", "ic", "edit", "delete", "show", "tag", "public", 
                     "search", "filter", "category", "view", "gm", "gmshow", 
                     "gmic", "gmooc", "gmedit", "gmdelete")
    
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
        
        # Add GM commands if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yGM Commands:|n
        note/gm character                       - List character's notes
        note/gmshow character id                - Show specific note details
        note/gmedit character id=content        - Edit any note
        note/gmdelete character id              - Delete any note
        note/gmooc character title=content      - Add OOC GM note
        note/gmic character title=content       - Add IC GM note
        
    GM Examples:
        note/gmooc John Background=Noble family connections
        note/gm Alice                           - List all of Alice's notes
        note/gmshow Alice 3                     - Show Alice's note #3
        note/gmedit Bob 5=Updated content       - Edit Bob's note #5
            """
        
        return help_text
    
    def func(self):
        """Handle all note functionality based on switches."""
        
        # Handle GM commands first (require GM permissions)
        if any(switch in self.switches for switch in ["gm", "gmshow", "gmic", "gmooc", "gmedit", "gmdelete"]):
            if not self.caller.check_permstring("Builder"):
                self.caller.msg("You need GM permissions to use GM note commands.")
                return
            
            if "gm" in self.switches:
                self._handle_gm_list()
            elif "gmshow" in self.switches:
                self._handle_gm_show()
            elif "gmic" in self.switches:
                self._handle_gm_add_ic()
            elif "gmooc" in self.switches:
                self._handle_gm_add_ooc()
            elif "gmedit" in self.switches:
                self._handle_gm_edit()
            elif "gmdelete" in self.switches:
                self._handle_gm_delete()
            return
        
        # Handle viewing other characters' public notes
        if "view" in self.switches:
            self._handle_view_public_notes()
            return
        
        # Regular commands for self
        char = self.caller
        if not hasattr(char, 'notes'):
            char = char.char
            
        if not hasattr(char, 'notes'):
            self.caller.msg("You cannot use notes.")
            return
        
        # Route to appropriate handler
        if "ooc" in self.switches:
            self._handle_add_note(char, "ooc")
        elif "ic" in self.switches:
            self._handle_add_note(char, "ic")
        elif "edit" in self.switches:
            self._handle_edit_note(char)
        elif "delete" in self.switches:
            self._handle_delete_note(char)
        elif "show" in self.switches:
            self._handle_show_note(char)
        elif "tag" in self.switches:
            self._handle_tag_note(char)
        elif "public" in self.switches:
            self._handle_public_toggle(char)
        elif "search" in self.switches:
            self._handle_search_notes(char)
        elif "filter" in self.switches:
            self._handle_filter_notes(char)
        elif "category" in self.switches:
            self._handle_category_notes(char)
        else:
            # No switch - list all notes
            self._handle_list_notes(char)
    
    def _get_next_note_id(self, char):
        """Get the next available note ID for a character."""
        notes = char.notes
        if not notes:
            return 1
        return max(note["id"] for note in notes) + 1
    
    def _get_note_by_id(self, char, note_id):
        """Get a note by its ID."""
        try:
            note_id = int(note_id)
        except ValueError:
            return None
        
        for note in char.notes:
            if note["id"] == note_id:
                return note
        return None
    
    def _handle_add_note(self, char, category):
        """Handle adding a new note."""
        if not self.args or "=" not in self.args:
            self.caller.msg(f"Usage: note/{category} title=content")
            return
        
        title, content = self.args.split("=", 1)
        title = title.strip()
        content = content.strip()
        
        if not title or not content:
            self.caller.msg("Both title and content are required.")
            return
        
        # Create the note
        note = {
            "id": self._get_next_note_id(char),
            "title": title,
            "content": content,
            "category": category,
            "public": False,
            "tags": [],
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add to character's notes
        notes = char.notes[:]  # Make a copy
        notes.append(note)
        char.notes = notes
        
        category_name = "out-of-character" if category == "ooc" else "in-character"
        self.caller.msg(f"Added {category_name} note #{note['id']}: '{title}'")
    
    def _handle_edit_note(self, char):
        """Handle editing an existing note."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: note/edit id=new_content")
            return
        
        note_id, new_content = self.args.split("=", 1)
        note_id = note_id.strip()
        new_content = new_content.strip()
        
        if not new_content:
            self.caller.msg("New content cannot be empty.")
            return
        
        note = self._get_note_by_id(char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found.")
            return
        
        # Check if GM note and caller isn't GM
        if note.get("author") and not self.caller.check_permstring("Builder"):
            self.caller.msg("You cannot edit GM notes.")
            return
        
        # Update the note
        notes = char.notes[:]
        for i, n in enumerate(notes):
            if n["id"] == note["id"]:
                notes[i]["content"] = new_content
                notes[i]["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        char.notes = notes
        self.caller.msg(f"Updated note #{note['id']}: '{note['title']}'")
    
    def _handle_delete_note(self, char):
        """Handle deleting a note."""
        if not self.args:
            self.caller.msg("Usage: note/delete id")
            return
        
        note_id = self.args.strip()
        note = self._get_note_by_id(char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found.")
            return
        
        # Check if GM note and caller isn't GM
        if note.get("author") and not self.caller.check_permstring("Builder"):
            self.caller.msg("You cannot delete GM notes.")
            return
        
        # Remove the note
        notes = char.notes[:]
        notes = [n for n in notes if n["id"] != note["id"]]
        char.notes = notes
        
        self.caller.msg(f"Deleted note #{note['id']}: '{note['title']}'")
    
    def _handle_show_note(self, char):
        """Handle showing a detailed view of a note."""
        if not self.args:
            self.caller.msg("Usage: note/show id")
            return
        
        note_id = self.args.strip()
        note = self._get_note_by_id(char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found.")
            return
        
        # Format note details
        category_name = "Out-of-Character" if note["category"] == "ooc" else "In-Character"
        visibility = "Public" if note.get("public", False) else "Private"
        
        output = f"|w=== Note #{note['id']}: {note['title']} ===|n\n"
        output += f"|wCategory:|n {category_name}\n"
        if note["category"] == "ic":
            output += f"|wVisibility:|n {visibility}\n"
        output += f"|wCreated:|n {note['created']}\n"
        output += f"|wModified:|n {note['modified']}\n"
        
        if note.get("author"):
            output += f"|wAdded by:|n {note['author']}\n"
        
        if note.get("tags"):
            output += f"|wTags:|n {', '.join(note['tags'])}\n"
        
        output += f"|wContent:|n\n{note['content']}\n"
        
        self.caller.msg(output)
    
    def _handle_tag_note(self, char):
        """Handle adding/updating tags for a note."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: note/tag id=tag1,tag2,...")
            return
        
        note_id, tags_str = self.args.split("=", 1)
        note_id = note_id.strip()
        tags_str = tags_str.strip()
        
        note = self._get_note_by_id(char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found.")
            return
        
        # Parse tags
        tags = [tag.strip().lower() for tag in tags_str.split(",") if tag.strip()]
        
        # Update the note
        notes = char.notes[:]
        for i, n in enumerate(notes):
            if n["id"] == note["id"]:
                notes[i]["tags"] = tags
                notes[i]["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        char.notes = notes
        
        if tags:
            self.caller.msg(f"Updated tags for note #{note['id']}: {', '.join(tags)}")
        else:
            self.caller.msg(f"Cleared tags for note #{note['id']}")
    
    def _handle_public_toggle(self, char):
        """Handle toggling public visibility for IC notes."""
        if not self.args:
            self.caller.msg("Usage: note/public id")
            return
        
        note_id = self.args.strip()
        note = self._get_note_by_id(char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found.")
            return
        
        if note["category"] != "ic":
            self.caller.msg("Only in-character notes can be made public.")
            return
        
        # Toggle public status
        notes = char.notes[:]
        for i, n in enumerate(notes):
            if n["id"] == note["id"]:
                notes[i]["public"] = not notes[i].get("public", False)
                notes[i]["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        char.notes = notes
        
        status = "public" if note.get("public", False) else "private"
        new_status = "private" if note.get("public", False) else "public"
        self.caller.msg(f"Note #{note['id']} is now {new_status} (was {status})")
    
    def _handle_search_notes(self, char):
        """Handle searching notes by content."""
        if not self.args:
            self.caller.msg("Usage: note/search text")
            return
        
        search_text = self.args.strip().lower()
        matching_notes = []
        
        for note in char.notes:
            if (search_text in note["title"].lower() or 
                search_text in note["content"].lower()):
                matching_notes.append(note)
        
        if not matching_notes:
            self.caller.msg(f"No notes found matching '{search_text}'.")
            return
        
        self._display_notes_list(matching_notes, f"Notes matching '{search_text}':")
    
    def _handle_filter_notes(self, char):
        """Handle filtering notes by tag."""
        if not self.args:
            self.caller.msg("Usage: note/filter tag")
            return
        
        filter_tag = self.args.strip().lower()
        matching_notes = []
        
        for note in char.notes:
            if filter_tag in note.get("tags", []):
                matching_notes.append(note)
        
        if not matching_notes:
            self.caller.msg(f"No notes found with tag '{filter_tag}'.")
            return
        
        self._display_notes_list(matching_notes, f"Notes tagged '{filter_tag}':")
    
    def _handle_category_notes(self, char):
        """Handle showing notes of a specific category."""
        if not self.args:
            self.caller.msg("Usage: note/category ooc or ic")
            return
        
        category = self.args.strip().lower()
        if category not in ["ooc", "ic"]:
            self.caller.msg("Category must be 'ooc' or 'ic'.")
            return
        
        matching_notes = [note for note in char.notes if note["category"] == category]
        
        if not matching_notes:
            category_name = "out-of-character" if category == "ooc" else "in-character"
            self.caller.msg(f"No {category_name} notes found.")
            return
        
        category_name = "Out-of-Character" if category == "ooc" else "In-Character"
        self._display_notes_list(matching_notes, f"{category_name} Notes:")
    
    def _handle_list_notes(self, char):
        """Handle listing all notes."""
        notes = char.notes
        if not notes:
            self.caller.msg("You have no notes.")
            return
        
        self._display_notes_list(notes, "Your Notes:")
    
    def _display_notes_list(self, notes, title):
        """Display a formatted list of notes."""
        # Sort notes by ID
        sorted_notes = sorted(notes, key=lambda x: x["id"])
        
        table = evtable.EvTable(
            "|wID|n", "|wTitle|n", "|wCategory|n", "|wTags|n", "|wVisibility|n",
            border="table", width=78
        )
        
        for note in sorted_notes:
            category = "OOC" if note["category"] == "ooc" else "IC"
            tags = ", ".join(note.get("tags", []))[:20]  # Limit tag display
            if len(note.get("tags", [])) > 0 and len(", ".join(note.get("tags", []))) > 20:
                tags += "..."
            
            if note["category"] == "ic":
                visibility = "Public" if note.get("public", False) else "Private"
            else:
                visibility = "Private"
            
            # Show GM author if present
            note_title = note["title"]
            if note.get("author"):
                note_title += f" |y[{note['author']}]|n"
            
            table.add_row(
                str(note["id"]),
                note_title[:30],  # Limit title display
                category,
                tags,
                visibility
            )
        
        self.caller.msg(f"|w{title}|n\n{table}")
    
    def _handle_view_public_notes(self):
        """Handle viewing another character's public IC notes."""
        if not self.args:
            self.caller.msg("Usage: note/view character [id]")
            return
        
        args = self.args.strip().split()
        char_name = args[0]
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        # Get only public IC notes
        public_notes = [note for note in target_char.notes 
                       if note["category"] == "ic" and note.get("public", False)]
        
        if not public_notes:
            self.caller.msg(f"{target_char.name} has no public notes.")
            return
        
        # If no note ID specified, list all public notes
        if len(args) == 1:
            self._display_notes_list(public_notes, f"{target_char.name}'s Public Notes:")
            return
        
        # If note ID specified, show that specific public note
        try:
            note_id = int(args[1])
        except ValueError:
            self.caller.msg("Note ID must be a number.")
            return
        
        # Find the specific note and verify it's public
        target_note = None
        for note in public_notes:
            if note["id"] == note_id:
                target_note = note
                break
        
        if not target_note:
            self.caller.msg(f"Public note #{note_id} not found for {target_char.name}.")
            return
        
        # Show the note content (similar to regular show but for public notes)
        output = f"|w=== {target_char.name}'s Note #{target_note['id']}: {target_note['title']} ===|n\n"
        output += f"|wCategory:|n In-Character (Public)\n"
        output += f"|wCreated:|n {target_note['created']}\n"
        output += f"|wModified:|n {target_note['modified']}\n"
        
        if target_note.get("author"):
            output += f"|wAdded by:|n {target_note['author']}\n"
        
        if target_note.get("tags"):
            output += f"|wTags:|n {', '.join(target_note['tags'])}\n"
        
        output += f"|wContent:|n\n{target_note['content']}\n"
        
        self.caller.msg(output)
    
    def _handle_gm_list(self):
        """Handle GM listing notes."""
        if not self.args:
            self.caller.msg("Usage: note/gm character")
            return
        
        char_name = self.args.strip()
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        notes = target_char.notes
        if not notes:
            self.caller.msg(f"{target_char.name} has no notes.")
            return
        
        self._display_notes_list(notes, f"{target_char.name}'s Notes:")
    
    def _handle_gm_show(self):
        """Handle GM showing specific note details."""
        if not self.args or len(self.args.strip().split()) < 2:
            self.caller.msg("Usage: note/gmshow character id")
            return
        
        args = self.args.strip().split()
        char_name = args[0]
        note_id = args[1]
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        note = self._get_note_by_id(target_char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found for {target_char.name}.")
            return
        
        # Format note details (same as regular show but with character name)
        category_name = "Out-of-Character" if note["category"] == "ooc" else "In-Character"
        visibility = "Public" if note.get("public", False) else "Private"
        
        output = f"|w=== {target_char.name}'s Note #{note['id']}: {note['title']} ===|n\n"
        output += f"|wCategory:|n {category_name}\n"
        if note["category"] == "ic":
            output += f"|wVisibility:|n {visibility}\n"
        output += f"|wCreated:|n {note['created']}\n"
        output += f"|wModified:|n {note['modified']}\n"
        
        if note.get("author"):
            output += f"|wAdded by:|n {note['author']}\n"
        
        if note.get("tags"):
            output += f"|wTags:|n {', '.join(note['tags'])}\n"
        
        output += f"|wContent:|n\n{note['content']}\n"
        
        self.caller.msg(output)
    
    def _handle_gm_edit(self):
        """Handle GM editing any note."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: note/gmedit character id=new_content")
            return
        
        char_part, new_content = self.args.split("=", 1)
        args = char_part.strip().split()
        
        if len(args) < 2:
            self.caller.msg("Usage: note/gmedit character id=new_content")
            return
        
        char_name = args[0]
        note_id = args[1]
        new_content = new_content.strip()
        
        if not new_content:
            self.caller.msg("New content cannot be empty.")
            return
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        note = self._get_note_by_id(target_char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found for {target_char.name}.")
            return
        
        # Update the note
        notes = target_char.notes[:]
        for i, n in enumerate(notes):
            if n["id"] == note["id"]:
                notes[i]["content"] = new_content
                notes[i]["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        target_char.notes = notes
        self.caller.msg(f"Updated {target_char.name}'s note #{note['id']}: '{note['title']}'")
    
    def _handle_gm_delete(self):
        """Handle GM deleting any note."""
        if not self.args or len(self.args.strip().split()) < 2:
            self.caller.msg("Usage: note/gmdelete character id")
            return
        
        args = self.args.strip().split()
        char_name = args[0]
        note_id = args[1]
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        note = self._get_note_by_id(target_char, note_id)
        if not note:
            self.caller.msg(f"Note #{note_id} not found for {target_char.name}.")
            return
        
        # Remove the note
        notes = target_char.notes[:]
        notes = [n for n in notes if n["id"] != note["id"]]
        target_char.notes = notes
        
        self.caller.msg(f"Deleted {target_char.name}'s note #{note['id']}: '{note['title']}'")
    
    def _handle_gm_add_ooc(self):
        """Handle GM adding an OOC note to another character."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: note/gmooc character title=content")
            return
        
        args_part, content = self.args.split("=", 1)
        args = args_part.strip().split()
        
        if len(args) < 2:
            self.caller.msg("Usage: note/gmooc character title=content")
            return
        
        char_name = args[0]
        title = " ".join(args[1:])
        content = content.strip()
        
        if not title or not content:
            self.caller.msg("Both title and content are required.")
            return
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        # Create the note with GM author
        note = {
            "id": self._get_next_note_id(target_char),
            "title": title,
            "content": content,
            "category": "ooc",
            "public": False,
            "tags": [],
            "author": self.caller.name,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add to character's notes
        notes = target_char.notes[:]
        notes.append(note)
        target_char.notes = notes
        
        self.caller.msg(f"Added out-of-character note #{note['id']} to {target_char.name}: '{title}'")
        
        # Notify the target character if they're online
        if target_char.sessions.all():
            target_char.msg(f"An out-of-character note has been added to your character by GM.")
    
    def _handle_gm_add_ic(self):
        """Handle GM adding an IC note to another character."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: note/gmic character title=content")
            return
        
        args_part, content = self.args.split("=", 1)
        args = args_part.strip().split()
        
        if len(args) < 2:
            self.caller.msg("Usage: note/gmic character title=content")
            return
        
        char_name = args[0]
        title = " ".join(args[1:])
        content = content.strip()
        
        if not title or not content:
            self.caller.msg("Both title and content are required.")
            return
        
        target_char = self.find_character(char_name)
        if not target_char:
            return
        
        # Create the note with GM author
        note = {
            "id": self._get_next_note_id(target_char),
            "title": title,
            "content": content,
            "category": "ic",
            "public": False,
            "tags": [],
            "author": self.caller.name,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add to character's notes
        notes = target_char.notes[:]
        notes.append(note)
        target_char.notes = notes
        
        self.caller.msg(f"Added in-character note #{note['id']} to {target_char.name}: '{title}'")
        
        # Notify the target character if they're online
        if target_char.sessions.all():
            target_char.msg(f"An in-character note has been added to your character by GM.")
    
class NotesCmdSet(CmdSet):
    """Command set for note management."""
    
    def at_cmdset_creation(self):
        self.add(CmdNote()) 