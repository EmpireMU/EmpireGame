"""
Commands for listing character locations and online players.
"""

from evennia import SESSION_HANDLER
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.utils import list_to_string
from evennia.objects.models import ObjectDB


class CmdWho(MuxCommand):
    """
    List who is currently online.
    
    Usage:
        who
        
    Shows who is currently connected. Displays character full names.
    """
    
    key = "who"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the command."""
        # Get all connected sessions
        sessions = SESSION_HANDLER.get_sessions()
        
        if not sessions:
            self.msg("No one is currently online.")
            return
        
        # Get all connected characters
        characters = []
        for session in sessions:
            puppet = session.get_puppet()
            if puppet and puppet.pk:
                # Skip invisible characters unless caller is staff
                if puppet.db.invisible and not self.caller.check_permstring("Admin"):
                    continue
                characters.append(puppet)
        
        if not characters:
            self.msg("No one is currently online.")
            return
        
        # Sort characters by full name or name
        characters.sort(key=lambda x: (x.db.full_name or x.name).lower())
        
        # Build the output
        output = ["|wPlayers:|n"]
        for char in characters:
            # Use full name if available, otherwise use regular name
            display_name = char.db.full_name or char.name
            
            # Check if AFK
            is_afk = char.db.afk or False
            afk_message = char.db.afk_message or None
            
            # Build the display with AFK status and optional message
            if is_afk and afk_message:
                display_name = f"{display_name} |y(AFK: {afk_message})|n"
            elif is_afk:
                display_name = f"{display_name} |y(AFK)|n"
            
            # Get idle time
            account = getattr(char, "account", None) or char.db.account
            if account:
                idle_seconds = account.idle_time
                if idle_seconds and idle_seconds >= 60:
                    idle_minutes = int(idle_seconds / 60)
                    output.append(f"  {display_name} ({idle_minutes}m idle)")
                else:
                    output.append(f"  {display_name}")
            else:
                output.append(f"  {display_name}")
        
        # Add count
        count = len(characters)
        output.append(f"\n{count} player{'s' if count != 1 else ''} online.")
        
        self.msg("\n".join(output))


class CmdWhere(MuxCommand):
    """
    List all rooms that currently have online characters in them.
    
    Usage:
        where
        
    Shows a list of all rooms that have online characters in them,
    along with the names of those characters.
    """
    
    key = "where"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the command."""
        # Get all rooms using direct database query
        rooms = ObjectDB.objects.filter(db_typeclass_path__contains="rooms.Room")
        if not rooms:
            self.msg("No rooms found.")
            return
            
        # Track if we found any rooms with online characters
        found_occupied = False
        output_lines = []
        
        # Check each room
        for room in rooms:
            # Skip invisible rooms
            if room.db.invisible:
                continue
                
            # Get all puppeted characters in the room
            online_chars = [obj for obj in room.contents 
                          if hasattr(obj, 'sessions') and obj.sessions.count()]
            
            # Filter out invisible characters
            visible_chars = [char for char in online_chars if not char.db.invisible]
            
            # If room has visible online characters, add it to output
            if visible_chars:
                found_occupied = True
                # Build character names with AFK indicators
                char_names_with_afk = []
                for char in visible_chars:
                    char_name = char.name
                    if char.db.afk:
                        char_name = f"{char_name} |y(AFK)|n"
                    char_names_with_afk.append(char_name)
                char_names = list_to_string(char_names_with_afk)
                output_lines.append(f"|w{room.name}|n: {char_names}")
        
        if not found_occupied:
            self.msg("No rooms currently have online characters.")
            return
            
        # Join all lines with newlines and send
        self.msg("\n".join(output_lines)) 