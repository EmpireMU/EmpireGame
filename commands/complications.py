"""
Commands for managing complications.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.command_mixins import CharacterLookupMixin

class CmdComplication(CharacterLookupMixin, MuxCommand):
    """
    Add, remove, or list complications.
    
    Usage:
        complication/add <name>=<die size>     - Add a complication
        complication/remove <name>             - Remove a complication
        complication                           - List your complications
        complication/here                      - List all complications in the room
        complication/gmadd <character>/<name>=<die size>  - (Staff) Add complication to another character
        complication/gmrem <character>/<name>  - (Staff) Remove complication from another character
        
    Examples:
        complication/add Injured=8         - Add "Injured" as a d8 complication
        complication/remove Injured        - Remove the "Injured" complication
        complication                       - List all your complications
        complication/here                  - List all complications of characters in the room
        complication/gmadd John/Exhausted=6     - Add "Exhausted" d6 complication to John
        complication/gmrem John/Exhausted       - Remove "Exhausted" complication from John
        
    Complications are hindrances that make actions more difficult. When included
    in dice rolls:
    - Against a difficulty: Add half the die size to the difficulty
    - Without difficulty: Display "Complications are applied in GM rolls."
    
    Unlike other traits, complications don't add dice to your pool or contribute
    to the roll result - they only make things harder or provide narrative cues.
    
    The GM commands (gmadd/gmrem) require staff permissions and use the format
    character_name/complication_name.
    """
    
    key = "complication"
    aliases = ["complications"]
    locks = "cmd:all()"
    help_category = "Game"
    switch_options = ("add", "remove", "gmadd", "gmrem", "here")
    
    def func(self):
        """Handle all complication functionality based on switches."""
        # Handle GM commands first (require staff permissions)
        if "gmadd" in self.switches or "gmrem" in self.switches:
            if not self.caller.check_permstring("Builder"):
                self.caller.msg("You need staff permissions to use GM complication commands.")
                return
            
            if "gmadd" in self.switches:
                self._handle_gm_add()
            elif "gmrem" in self.switches:
                self._handle_gm_remove()
            return
        
        # Handle here command
        if "here" in self.switches:
            self._handle_here()
            return
        
        # Regular complication commands for self
        char = self.caller
        if not hasattr(char, 'complications'):
            if hasattr(char, 'char'):
                char = char.char
            else:
                self.caller.msg("You cannot use complications.")
                return
            
            
        if not self.switches:  # No switch - list complications
            complications = char.complications.all()
            if not complications:
                self.caller.msg("You have no complications.")
                return
                
            self.caller.msg("|wComplications:|n")
            for key in complications:
                complication = char.complications.get(key)
                self.caller.msg(f"  {complication.name}: d{int(complication.value)}")
                
        elif "add" in self.switches:
            if not self.args or "=" not in self.args:
                self.caller.msg("Usage: complication/add <name>=<die size>")
                return
                
            name, die_size = self.args.split("=", 1)
            name = name.strip()
            try:
                die_size = int(die_size.strip())
                if die_size not in [4, 6, 8, 10, 12]:
                    self.caller.msg("Die size must be 4, 6, 8, 10, or 12.")
                    return
            except ValueError:
                self.caller.msg("Die size must be a number (4, 6, 8, 10, or 12).")
                return
                
            # Add the complication with both value and base set
            char.complications.add(
                name.lower().replace(" ", "_"),
                value=die_size,
                base=die_size,
                name=name
            )
            
            self.caller.msg(f"Added complication '{name}' (d{die_size}).")
            self.caller.location.msg_contents(
                f"{char.name} gains a complication: {name} (d{die_size}).",
                exclude=[self.caller]
            )
            
        elif "remove" in self.switches:
            if not self.args:
                self.caller.msg("Usage: complication/remove <name>")
                return
                
            name = self.args.strip()
            key = name.lower().replace(" ", "_")
            
            # Check if complication exists
            complication = char.complications.get(key)
            if not complication:
                self.caller.msg(f"You don't have a complication named '{name}'.")
                return
                
            # Remove the complication
            char.complications.remove(key)
            
            self.caller.msg(f"Removed complication '{name}'.")
            self.caller.location.msg_contents(
                f"{char.name} recovers from their complication: {name}.",
                exclude=[self.caller]
            )

    def _handle_gm_add(self):
        """Handle GM add command with character/complication format."""
        if not self.args or "/" not in self.args or "=" not in self.args:
            self.caller.msg("Usage: complication/gmadd <character>/<name>=<die size>")
            return
        
        # Parse character/complication format
        char_comp, die_size_str = self.args.split("=", 1)
        if "/" not in char_comp:
            self.caller.msg("Usage: complication/gmadd <character>/<name>=<die size>")
            return
            
        char_name, comp_name = char_comp.split("/", 1)
        char_name = char_name.strip()
        comp_name = comp_name.strip()
        
        # Find the target character
        target_char = self.find_character(char_name)
        if not target_char:
            return
            
        # Ensure character has complications capability
        if not hasattr(target_char, 'complications'):
            if hasattr(target_char, 'char'):
                target_char = target_char.char
            else:
                self.caller.msg(f"{target_char.name} cannot use complications.")
                return
        
        if not hasattr(target_char, 'complications'):
            self.caller.msg(f"{target_char.name} cannot use complications.")
            return
        
        # Validate die size
        try:
            die_size = int(die_size_str.strip())
            if die_size not in [4, 6, 8, 10, 12]:
                self.caller.msg("Die size must be 4, 6, 8, 10, or 12.")
                return
        except ValueError:
            self.caller.msg("Die size must be a number (4, 6, 8, 10, or 12).")
            return
        
        # Add the complication
        target_char.complications.add(
            comp_name.lower().replace(" ", "_"),
            value=die_size,
            base=die_size,
            name=comp_name
        )
        
        # Notify staff member and target character
        self.caller.msg(f"Added complication '{comp_name}' (d{die_size}) to {target_char.name}.")
        target_char.msg(f"A complication '{comp_name}' (d{die_size}) has been added to your character by staff.")
        
        # Notify room if target is online and in a location
        if target_char.location:
            target_char.location.msg_contents(
                f"{target_char.name} gains a complication: {comp_name} (d{die_size}).",
                exclude=[target_char]
            )

    def _handle_gm_remove(self):
        """Handle GM remove command with character/complication format."""
        if not self.args or "/" not in self.args:
            self.caller.msg("Usage: complication/gmrem <character>/<name>")
            return
        
        # Parse character/complication format
        char_name, comp_name = self.args.split("/", 1)
        char_name = char_name.strip()
        comp_name = comp_name.strip()
        
        # Find the target character
        target_char = self.find_character(char_name)
        if not target_char:
            return
            
        # Ensure character has complications capability
        if not hasattr(target_char, 'complications'):
            if hasattr(target_char, 'char'):
                target_char = target_char.char
            else:
                self.caller.msg(f"{target_char.name} cannot use complications.")
                return
        
        if not hasattr(target_char, 'complications'):
            self.caller.msg(f"{target_char.name} cannot use complications.")
            return
        
        # Check if complication exists
        comp_key = comp_name.lower().replace(" ", "_")
        complication = target_char.complications.get(comp_key)
        if not complication:
            self.caller.msg(f"{target_char.name} doesn't have a complication named '{comp_name}'.")
            return
        
        # Remove the complication
        target_char.complications.remove(comp_key)
        
        # Notify staff member and target character
        self.caller.msg(f"Removed complication '{comp_name}' from {target_char.name}.")
        target_char.msg(f"Your complication '{comp_name}' has been removed by staff.")
        
        # Notify room if target is online and in a location
        if target_char.location:
            target_char.location.msg_contents(
                f"{target_char.name} recovers from their complication: {comp_name}.",
                exclude=[target_char]
            )

    def _handle_here(self):
        """Handle complication/here command to list all complications in the room."""
        if not self.caller.location:
            self.caller.msg("You are not in a location.")
            return
        
        # Get all characters in the room
        characters = [obj for obj in self.caller.location.contents if hasattr(obj, 'complications')]
        
        complications_found = []
        for char in characters:
            try:
                comp_keys = char.complications.all()
                if comp_keys:
                    char_complications = []
                    for key in comp_keys:
                        comp = char.complications.get(key)
                        if comp:
                            char_complications.append(f"{comp.name} (d{int(comp.value)})")
                    
                    if char_complications:
                        complications_found.append(f"|w{char.name}:|n {', '.join(char_complications)}")
            except:
                # Skip characters that don't have complications or have errors
                continue
        
        if not complications_found:
            self.caller.msg("No one in this location has any complications.")
        else:
            self.caller.msg("|wComplications in this location:|n\n" + "\n".join(complications_found))

class ComplicationCmdSet(CmdSet):
    """Command set for complication management."""
    
    def at_cmdset_creation(self):
        """Add commands to the command set."""
        self.add(CmdComplication()) 