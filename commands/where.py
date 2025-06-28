"""
Commands for listing character locations.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.utils import list_to_string
from evennia.objects.models import ObjectDB


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
            # Get all puppeted characters in the room
            online_chars = [obj for obj in room.contents 
                          if hasattr(obj, 'sessions') and obj.sessions.count()]
            
            # If room has online characters, add it to output
            if online_chars:
                found_occupied = True
                char_names = list_to_string([char.name for char in online_chars])
                output_lines.append(f"|w{room.name}|n: {char_names}")
        
        if not found_occupied:
            self.msg("No rooms currently have online characters.")
            return
            
        # Join all lines with newlines and send
        self.msg("\n".join(output_lines)) 