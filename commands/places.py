"""
Place system for rooms.

This module implements a place system that allows characters to create
sub-locations within rooms and interact with others at those places.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.command_mixins import CharacterLookupMixin
from utils.message_coloring import apply_character_coloring, apply_name_coloring


class CmdPlace(MuxCommand):
    """
    Manage places within a room.
    
    Usage:
        place                           - List places in current room
        place/create <name>             - Create a new place
        place/create <name> = <desc>    - Create a place with description
        place/delete <name>             - Delete a place you created
        place/desc <name> = <desc>      - Set place description
        place/look <name>               - Look at a specific place
        
    Examples:
        place                           - Show all places here
        place/create bar                - Create "bar" place
        place/create corner table = A small wooden table in a quiet corner
        place/delete bar                - Delete your place
        place/desc bar = A polished oak bar with brass fittings
        place/look bar                  - Look at the bar
        
    Places allow characters to join sub-locations within a room and
    communicate privately with others at the same place using 'pemit'.
    """
    
    key = "place"
    locks = "cmd:all()"
    help_category = "Building"
    
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
        
        # Add staff information if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yStaff Note:|n
        Staff can delete any place in the room, not just their own creations.
            """
        
        return help_text
    
    def func(self):
        """Execute the command."""
        if not self.caller.location:
            self.msg("You must be in a room to manage places.")
            return
            
        room = self.caller.location
        
        if not self.switches:
            self._list_places(room)
        elif "create" in self.switches:
            self._create_place(room)
        elif "delete" in self.switches:
            self._delete_place(room)
        elif "desc" in self.switches:
            self._set_description(room)
        elif "look" in self.switches:
            self._look_at_place(room)
        else:
            self.msg("Invalid switch. See 'help place' for usage.")
            
    def _list_places(self, room):
        """List all places in the room."""
        places = room.db.places or {}
        
        if not places:
            self.msg("There are no places in this room.")
            return
            
        lines = ["|wPlaces in this room:|n"]
        for place_key, place_data in places.items():
            name = place_data.get("name", place_key)
            desc = place_data.get("desc", "")
            characters = place_data.get("characters", [])
            char_count = len(characters)
            
            line = f"  |c{name}|n"
            if desc:
                line += f" - {desc}"
            if char_count > 0:
                line += f" |w({char_count} {'person' if char_count == 1 else 'people'})|n"
            lines.append(line)
            
        self.msg("\n".join(lines))
        
    def _create_place(self, room):
        """Create a new place."""
        if not self.args:
            self.msg("Usage: place/create <name> [= description]")
            return
            
        # Parse name and optional description
        if "=" in self.args:
            name, desc = [part.strip() for part in self.args.split("=", 1)]
        else:
            name = self.args.strip()
            desc = ""
            
        if not name:
            self.msg("Place name cannot be empty.")
            return
            
        # Initialize places dict if it doesn't exist
        if not room.db.places:
            room.db.places = {}
            
        places = room.db.places
        place_key = name.lower()  # Store key in lowercase for case-insensitive matching
        
        # Check if place already exists
        if place_key in places:
            self.msg(f"A place named '{name}' already exists here.")
            return
            

            
        # Create the place
        place_data = {
            "name": name,  # Preserve original case for display
            "desc": desc,
            "characters": [],
            "creator": self.caller.id
        }
        
        places[place_key] = place_data
        room.db.places = places
        
        self.msg(f"Created place '{name}'.")
        if desc:
            self.msg(f"Description: {desc}")
            
        # Announce to room
        room.msg_contents(
            f"{self.caller.name} creates a new place: {name}.",
            exclude=[self.caller]
        )
        
    def _delete_place(self, room):
        """Delete a place."""
        if not self.args:
            self.msg("Usage: place/delete <name>")
            return
            
        places = room.db.places or {}
        place_key = self.args.strip().lower()
        
        if place_key not in places:
            self.msg(f"No place named '{self.args.strip()}' found.")
            return
            
        place_data = places[place_key]
        place_name = place_data.get("name", self.args.strip())
        
        # Check permissions (creator or staff)
        if (place_data.get("creator") != self.caller.id and 
            not self.caller.check_permstring("Builder")):
            self.msg("You can only delete places you created.")
            return
            
        # Remove characters from the place
        characters = place_data.get("characters", [])
        for char in characters[:]:  # Copy list to avoid modification during iteration
            if char in characters:
                characters.remove(char)
                if hasattr(char, 'msg'):
                    char.msg(f"The place '{place_name}' has been deleted. You are no longer at any place.")
                    
        # Delete the place
        del places[place_key]
        room.db.places = places
        
        self.msg(f"Deleted place '{place_name}'.")
        room.msg_contents(
            f"{self.caller.name} removes the place: {place_name}.",
            exclude=[self.caller]
        )
        
    def _set_description(self, room):
        """Set the description of a place."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: place/desc <name> = <description>")
            return
            
        name, desc = [part.strip() for part in self.args.split("=", 1)]
        places = room.db.places or {}
        place_key = name.lower()
        
        if place_key not in places:
            self.msg(f"No place named '{name}' found.")
            return
            
        place_data = places[place_key]
        
        # Check permissions (creator or staff)
        if (place_data.get("creator") != self.caller.id and 
            not self.caller.check_permstring("Builder")):
            self.msg("You can only modify places you created.")
            return
            
        # Update description
        place_data["desc"] = desc
        room.db.places = places
        
        place_name = place_data.get("name", name)
        self.msg(f"Set description for '{place_name}': {desc}")
        
    def _look_at_place(self, room):
        """Look at a specific place."""
        if not self.args:
            self.msg("Usage: place/look <name>")
            return
            
        places = room.db.places or {}
        place_key = self.args.strip().lower()
        
        if place_key not in places:
            self.msg(f"No place named '{self.args.strip()}' found.")
            return
            
        place_data = places[place_key]
        place_name = place_data.get("name", self.args.strip())
        desc = place_data.get("desc", "You see nothing special about this place.")
        characters = place_data.get("characters", [])
        
        output = [f"|w{place_name}|n"]
        output.append(desc)
        
        if characters:
            char_names = [char.name for char in characters if hasattr(char, 'name')]
            if char_names:
                if len(char_names) == 1:
                    output.append(f"|w{char_names[0]}|n is here.")
                else:
                    output.append(f"|w{', '.join(char_names[:-1])} and {char_names[-1]}|n are here.")
        else:
            output.append("No one is currently at this place.")
            
        self.msg("\n".join(output))


class CmdJoin(MuxCommand):
    """
    Join a place within a room.
    
    Usage:
        join <place>
        
    Examples:
        join bar            - Join the bar
        join corner table   - Join the corner table
        
    Once you join a place, you can use 'pemit' to communicate
    with others at the same place.
    """
    
    key = "join"
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        """Execute the command."""
        if not self.args:
            self.msg("Usage: join <place>")
            return
            
        if not self.caller.location:
            self.msg("You must be in a room to join a place.")
            return
            
        room = self.caller.location
        places = room.db.places or {}
        place_name = self.args.strip()
        place_key = place_name.lower()
        
        if place_key not in places:
            self.msg(f"No place named '{place_name}' found. Use 'place' to see available places.")
            return
            
        # Remove character from any current place first
        old_place_name = self._leave_current_place(room)
        
        # Refresh places data after potential removal
        places = room.db.places or {}
        place_data = places[place_key]
        characters = place_data.get("characters", [])
        display_name = place_data.get("name", place_name)
        
        # Add character to the new place
        if self.caller not in characters:
            characters.append(self.caller)
            place_data["characters"] = characters
            room.db.places = places
            
        if old_place_name:
            self.msg(f"You leave {old_place_name} and join {display_name}.")
        else:
            self.msg(f"You join {display_name}.")
        
        # Announce to others at the place
        for char in characters:
            if char != self.caller and hasattr(char, 'msg'):
                char.msg(f"{self.caller.name} joins you at {display_name}.")
                
        # Announce to room (excluding those at the place)
        room_chars = [obj for obj in room.contents if hasattr(obj, 'sessions') and obj.sessions.count()]
        for char in room_chars:
            if char not in characters and char != self.caller:
                char.msg(f"{self.caller.name} joins {display_name}.")
                
    def _leave_current_place(self, room):
        """Remove character from their current place, if any. Returns name of place left."""
        places = room.db.places or {}
        
        for place_key, place_data in places.items():
            characters = place_data.get("characters", [])
            if self.caller in characters:
                characters.remove(self.caller)
                place_data["characters"] = characters
                room.db.places = places
                
                # Announce to others still at the old place
                old_place_name = place_data.get("name", place_key)
                for char in characters:
                    if hasattr(char, 'msg'):
                        char.msg(f"{self.caller.name} leaves {old_place_name}.")
                
                return old_place_name
        return None


class CmdLeave(MuxCommand):
    """
    Leave your current place.
    
    Usage:
        leave
        
    Leaves your current place and returns you to the general room area.
    """
    
    key = "leave"
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        """Execute the command."""
        if not self.caller.location:
            self.msg("You are not in a room.")
            return
            
        room = self.caller.location
        places = room.db.places or {}
        
        # Find which place the character is in
        current_place = None
        for place_key, place_data in places.items():
            characters = place_data.get("characters", [])
            if self.caller in characters:
                current_place = place_data
                current_place_key = place_key
                break
                
        if not current_place:
            self.msg("You are not currently at any place.")
            return
            
        # Remove character from place
        characters = current_place.get("characters", [])
        if self.caller in characters:
            characters.remove(self.caller)
            current_place["characters"] = characters
            room.db.places = places
            
        place_name = current_place.get("name", current_place_key)
        self.msg(f"You leave {place_name}.")
        
        # Announce to others at the place
        for char in characters:
            if hasattr(char, 'msg'):
                char.msg(f"{self.caller.name} leaves {place_name}.")
                
        # Announce to room (excluding those still at the place)
        room_chars = [obj for obj in room.contents if hasattr(obj, 'sessions') and obj.sessions.count()]
        for char in room_chars:
            if char not in characters and char != self.caller:
                char.msg(f"{self.caller.name} leaves {place_name}.")


class CmdPemit(MuxCommand):
    """
    Emit a message to everyone at your current place.
    
    Usage:
        pemit <message>        - Environmental message to place
        ppose <message>        - Action with your name at start
        
    Examples:
        pemit orders a drink                          -> [Place] orders a drink (or [Place] (Ada) orders a drink if shownames on)
        ppose sits down and sighs.                    -> [Place] Ada sits down and sighs.
        
    Sends a message only to other characters at your current place.
    If you're not at a place, this command won't work.
    """
    
    key = "pemit"
    aliases = ["ppose"]
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        """Execute the command."""
        if not self.args:
            self.msg("Usage: pemit <message> or ppose <message>")
            return
            
        if not self.caller.location:
            self.msg("You must be in a room to use pemit.")
            return
            
        room = self.caller.location
        places = room.db.places or {}
        
        # Find which place the character is in
        current_place = None
        current_place_name = None
        for place_key, place_data in places.items():
            characters = place_data.get("characters", [])
            if self.caller in characters:
                current_place = place_data
                current_place_name = place_data.get("name", place_key)
                break
                
        if not current_place:
            self.msg("You must be at a place to use pemit. Use 'join <place>' first.")
            return
            
        characters = current_place.get("characters", [])
        if len(characters) <= 1:
            self.msg(f"You are alone at {current_place_name}.")
            return
            
        message = self.args.strip()
        
        # Check if user typed 'ppose' vs 'pemit' to determine message format
        is_ppose = self.cmdstring.lower() == "ppose"
        
        # Send personalized messages to each character at the place
        for character in characters:
            if hasattr(character, 'sessions') and character.sessions.all():
                # Apply character's color preferences to the message
                colored_message = apply_character_coloring(message, character)
                
                # Apply character's color preferences to the sender name
                colored_sender_name = apply_name_coloring(self.caller.name, character)
                
                if is_ppose:
                    # Ppose: always show sender name at start of message
                    place_message = f"|w[{current_place_name}]|n {colored_sender_name} {colored_message}"
                else:
                    # Pemit: check if this character wants to see emit names
                    show_names = character.db.show_emit_names
                    if show_names:
                        # Show with sender name in parentheses
                        place_message = f"|w[{current_place_name}]|n ({colored_sender_name}) {colored_message}"
                    else:
                        # Show without sender name (respects emit/shownames setting)
                        place_message = f"|w[{current_place_name}]|n {colored_message}"
                
                character.msg(place_message)





class PlaceCmdSet(CmdSet):
    """Command set for place management."""
    
    def at_cmdset_creation(self):
        """Add commands to the command set."""
        self.add(CmdPlace())
        self.add(CmdJoin())
        self.add(CmdLeave())
        self.add(CmdPemit()) 