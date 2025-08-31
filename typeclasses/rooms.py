"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def at_object_creation(self):
        """Called when object is first created."""
        super().at_object_creation()
        
        # Initialize ownership and key holders
        self.db.org_owners = {}  # {id: org_name}
        self.db.character_owners = {}  # {id: character_obj}
        self.db.key_holders = {}  # {id: character_obj}

    def get_display_exits(self, looker, **kwargs):
        """
        Get exits for display in room description with aliases in angle brackets.
        
        Args:
            looker: The character looking at the room
            **kwargs: Additional keyword arguments
            
        Returns:
            str: Formatted exit string showing "Exit <Alias>"
        """
        exits = [ex for ex in self.contents if ex.destination]
        if not exits:
            return ""
        
        # Cardinal directions in compass order
        cardinal_order = ['N', 'NORTH', 'NE', 'NORTHEAST', 'E', 'EAST', 'SE', 'SOUTHEAST',
                         'S', 'SOUTH', 'SW', 'SOUTHWEST', 'W', 'WEST', 'NW', 'NORTHWEST',
                         'U', 'UP', 'D', 'DOWN', 'O', 'OUT']
        
        # Separate cardinal and non-cardinal exits
        cardinal_exits = []
        other_exits = []
        
        for ex in exits:
            cardinal_found = False
            if ex.aliases.all():
                for alias in ex.aliases.all():
                    if alias.upper() in cardinal_order:
                        cardinal_exits.append((cardinal_order.index(alias.upper()), ex))
                        cardinal_found = True
                        break
            if not cardinal_found:
                other_exits.append(ex)
        
        # Sort each group
        cardinal_exits.sort()  # Sort by cardinal order
        other_exits.sort(key=lambda ex: ex.key.lower())  # Sort alphabetically
        
        # Combine back into single list
        exits = [ex for _, ex in cardinal_exits] + other_exits
            
        exit_names = []
        for ex in exits:
            # Get the exit's display name (key)
            exit_name = ex.get_display_name(looker)
            
            # Get preferred alias - prioritize location names over cardinal directions
            if ex.aliases.all():
                aliases = list(ex.aliases.all())
                
                # Cardinal directions and generic exits to deprioritize
                cardinal_directions = {
                    'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'U', 'D', 'O',
                    'NORTH', 'SOUTH', 'EAST', 'WEST', 'UP', 'DOWN', 'OUT',
                    'NORTHEAST', 'NORTHWEST', 'SOUTHEAST', 'SOUTHWEST'
                }
                
                # Separate location aliases from cardinal directions
                location_aliases = [alias for alias in aliases 
                                  if alias.upper() not in cardinal_directions]
                cardinal_aliases = [alias for alias in aliases 
                                  if alias.upper() in cardinal_directions]
                
                # Prefer shortest location alias, otherwise shortest cardinal
                if location_aliases:
                    preferred_alias = min(location_aliases, key=len).upper()
                else:
                    preferred_alias = min(cardinal_aliases, key=len).upper()
                    
                exit_display = f"{exit_name} <{preferred_alias}>"
            else:
                exit_display = exit_name
                
            exit_names.append(exit_display)
        
        return f"Exits: {', '.join(exit_names)}"

    @property
    def org_owners(self):
        """Get organization owners as {id: org_name}"""
        return self.db.org_owners or {}

    @property
    def character_owners(self):
        """Get character owners as {id: character_obj}"""
        return self.db.character_owners or {}

    @property
    def key_holders(self):
        """Get characters who have keys to this room as {id: character_obj}"""
        return self.db.key_holders or {}

    def has_access(self, character):
        """
        Check if a character has access to this room (owner or key holder)
        
        Args:
            character: The character to check
            
        Returns:
            bool: True if character has access
        """
        if character.id in self.character_owners:
            return True
            
        if character.id in self.key_holders:
            return True
            
        # Check organization ownership
        char_orgs = character.organisations if hasattr(character, 'organisations') else {}
        for org_id, org_name in self.org_owners.items():
            if org_id in char_orgs:
                return True
                
        return False

    def return_appearance(self, looker, **kwargs):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Args:
            looker (Object): Object doing the looking.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).
        """
        if not looker:
            return ""
        
        # Get the base appearance from the parent class
        appearance = super().return_appearance(looker, **kwargs)
        
        # Add places to the description
        places = self.db.places or {}
        if places:
            # Insert places section after room description but before characters/objects
            lines = appearance.split('\n')
            
            # Find where to insert places (after description, before character list)
            insert_index = len(lines)
            for i, line in enumerate(lines):
                # Look for the start of character/contents listing
                if any(keyword in line.lower() for keyword in ['exits:', 'you see:', 'contents:']):
                    insert_index = i
                    break
            
            # Build places display - just names on one line
            place_names = []
            for place_key, place_data in places.items():
                place_name = place_data.get("name", place_key)
                characters = place_data.get("characters", [])
                    
                place_display = f"|c{place_name}|n"
                if characters:
                    # Filter to only show characters the looker can see
                    visible_chars = [char for char in characters if looker.access(char, "view")]
                    if visible_chars:
                        char_names = [char.name for char in visible_chars]
                        if len(char_names) == 1:
                            place_display += f" |w({char_names[0]})|n"
                        else:
                            place_display += f" |w({', '.join(char_names)})|n"
                
                place_names.append(place_display)
            
            place_lines = [f"|wPlaces:|n {', '.join(place_names)}"]
            
            # Insert places into the appearance
            place_text = '\n'.join(place_lines)
            lines.insert(insert_index, place_text)
            lines.insert(insert_index + 1, "")  # Add blank line after places
            
            appearance = '\n'.join(lines)
        
        return appearance
