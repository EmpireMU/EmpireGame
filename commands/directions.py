"""
Directions command for finding paths to publicly visible rooms.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.search import search_object
from evennia.objects.models import ObjectDB
from collections import deque
from evennia.utils.utils import list_to_string


class CmdDirections(MuxCommand):
    """
    Get directions to publicly accessible rooms.
    
    Usage:
        directions              - List available destinations
        directions <room>       - Get path to specific room
        directions/nearby       - Show destinations within 3 steps
        directions/list         - List all visible rooms by name
    
    This command helps you navigate to publicly accessible rooms by showing
    the shortest path of cardinal directions to reach your destination.
    
    Examples:
        directions              - Show nearby destinations
        directions tavern       - Get path to any room matching "tavern"
        directions/list         - Show all reachable room names
    """
    
    key = "directions"
    aliases = ["path", "route"]
    locks = "cmd:all()"
    help_category = "Travel"
    
    def func(self):
        """Execute the command."""
        if not self.caller.location:
            self.msg("You need to be in a room to get directions.")
            return
            
        if not self.switches:
            if not self.args:
                # Show nearby destinations (default behavior)
                self._show_nearby_destinations()
            else:
                # Get directions to specific room
                self._get_directions_to_room(self.args.strip())
        elif "nearby" in self.switches:
            self._show_nearby_destinations()
        elif "list" in self.switches:
            self._list_all_visible_rooms()
        else:
            self.msg("Unknown switch. Use: directions, directions/nearby, or directions/list")
    
    def _get_visible_rooms(self):
        """Get all rooms that are not invisible."""
        try:
            # Get all rooms
            rooms = ObjectDB.objects.filter(db_typeclass_path__contains="rooms.Room")
            visible_rooms = []
            
            for room in rooms:
                # Skip invisible rooms
                if not getattr(room, 'db_invisible', False):
                    visible_rooms.append(room)
                    
            return visible_rooms
        except Exception as e:
            # Fallback to search_object if database query fails
            all_rooms = search_object("", typeclass="typeclasses.rooms.Room")
            return [room for room in all_rooms if not room.db.invisible]
    
    def _find_path(self, start_room, target_room, max_depth=10):
        """
        Find shortest path between two rooms using BFS.
        
        Returns:
            list: List of (direction, room) tuples representing the path,
                 or None if no path found.
        """
        if start_room == target_room:
            return []
            
        visited = set()
        queue = deque([(start_room, [])])  # (current_room, path_to_reach_it)
        
        while queue:
            current_room, path = queue.popleft()
            
            if current_room in visited:
                continue
                
            visited.add(current_room)
            
            # Check if we've gone too deep
            if len(path) >= max_depth:
                continue
            
            # Get exits from current room
            exits = [ex for ex in current_room.contents if hasattr(ex, 'destination') and ex.destination]
            
            for exit_obj in exits:
                destination = exit_obj.destination
                
                # Skip if destination is invisible or we've visited it
                if destination.db.invisible or destination in visited:
                    continue
                    
                # Get the best direction name for this exit
                direction = self._get_exit_direction(exit_obj)
                new_path = path + [(direction, destination)]
                
                # Found target!
                if destination == target_room:
                    return new_path
                    
                # Add to queue for further exploration
                queue.append((destination, new_path))
        
        return None  # No path found
    
    def _get_exit_direction(self, exit_obj):
        """Get the best direction name for an exit."""
        # Prefer cardinal direction aliases
        cardinal_directions = {
            'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'U', 'D', 'O',
            'NORTH', 'SOUTH', 'EAST', 'WEST', 'UP', 'DOWN', 'OUT',
            'NORTHEAST', 'NORTHWEST', 'SOUTHEAST', 'SOUTHWEST'
        }
        
        if exit_obj.aliases.all():
            aliases = list(exit_obj.aliases.all())
            
            # First try to find a cardinal direction
            cardinal_aliases = [alias for alias in aliases 
                              if alias.upper() in cardinal_directions]
            if cardinal_aliases:
                return min(cardinal_aliases, key=len).lower()
            
            # Otherwise use shortest alias
            return min(aliases, key=len).lower()
        
        # Fall back to the exit's key
        return exit_obj.key.lower()
    
    def _show_nearby_destinations(self, max_distance=3):
        """Show destinations within max_distance steps."""
        current_room = self.caller.location
        visible_rooms = self._get_visible_rooms()
        
        # Remove current room from destinations
        destinations = [room for room in visible_rooms if room != current_room]
        
        if not destinations:
            self.msg("No publicly accessible destinations found.")
            return
        
        # Find paths to nearby rooms
        nearby_destinations = []
        
        for room in destinations:
            path = self._find_path(current_room, room, max_distance)
            if path:
                distance = len(path)
                directions = [step[0] for step in path]
                nearby_destinations.append((room, distance, directions))
        
        if not nearby_destinations:
            self.msg(f"No destinations found within {max_distance} steps.")
            return
        
        # Sort by distance, then by name
        nearby_destinations.sort(key=lambda x: (x[1], x[0].name.lower()))
        
        output_lines = ["|wNearby Destinations:|n"]
        
        current_distance = None
        for room, distance, directions in nearby_destinations:
            if distance != current_distance:
                current_distance = distance
                step_word = "step" if distance == 1 else "steps"
                output_lines.append(f"\n|c{distance} {step_word} away:|n")
            
            direction_str = " → ".join(directions)
            output_lines.append(f"  {room.name}: |y{direction_str}|n")
        
        output_lines.append(f"\nUse |wdirections <room name>|n for specific directions.")
        self.msg("\n".join(output_lines))
    
    def _get_directions_to_room(self, target_name):
        """Get directions to a specific room."""
        current_room = self.caller.location
        visible_rooms = self._get_visible_rooms()
        
        # Find rooms matching the target name
        matching_rooms = []
        target_lower = target_name.lower()
        
        for room in visible_rooms:
            if room == current_room:
                continue
                
            room_name_lower = room.name.lower()
            
            # Exact match
            if room_name_lower == target_lower:
                matching_rooms.insert(0, room)  # Put exact matches first
            # Partial match
            elif target_lower in room_name_lower:
                matching_rooms.append(room)
        
        if not matching_rooms:
            self.msg(f"No publicly accessible room found matching '{target_name}'.")
            self.msg("Use |wdirections/list|n to see all available destinations.")
            return
        
        # If multiple matches, show them
        if len(matching_rooms) > 1:
            self.msg(f"Multiple rooms match '{target_name}':")
            for i, room in enumerate(matching_rooms[:5], 1):  # Show max 5
                path = self._find_path(current_room, room)
                if path:
                    distance = len(path)
                    step_word = "step" if distance == 1 else "steps"
                    directions = " → ".join([step[0] for step in path])
                    self.msg(f"  {i}. {room.name} ({distance} {step_word}): |y{directions}|n")
                else:
                    self.msg(f"  {i}. {room.name} (no path found)")
            
            if len(matching_rooms) > 5:
                self.msg(f"  ... and {len(matching_rooms) - 5} more matches")
            return
        
        # Single match - show the path
        target_room = matching_rooms[0]
        path = self._find_path(current_room, target_room)
        
        if not path:
            self.msg(f"No path found to {target_room.name}.")
            return
        
        distance = len(path)
        step_word = "step" if distance == 1 else "steps"
        directions = [step[0] for step in path]
        
        self.msg(f"|wPath to {target_room.name}:|n {' → '.join(directions)} |c({distance} {step_word})|n")
    
    def _list_all_visible_rooms(self):
        """List all visible room names for reference."""
        visible_rooms = self._get_visible_rooms()
        current_room = self.caller.location
        
        # Remove current room and sort alphabetically
        other_rooms = [room for room in visible_rooms if room != current_room]
        other_rooms.sort(key=lambda r: r.name.lower())
        
        if not other_rooms:
            self.msg("No other publicly accessible rooms found.")
            return
        
        self.msg("|wPublicly Accessible Destinations:|n")
        
        # Group by first letter for easier reading
        current_letter = None
        for room in other_rooms:
            first_letter = room.name[0].upper()
            if first_letter != current_letter:
                current_letter = first_letter
                self.msg(f"\n|c{first_letter}:|n")
            
            self.msg(f"  {room.name}")
        
        self.msg(f"\nUse |wdirections <room name>|n to get directions to any of these locations.")
