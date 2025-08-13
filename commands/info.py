"""
Info/Finger command for displaying character information.
"""

from evennia import Command
from evennia.utils.search import search_object
from utils.command_mixins import CharacterLookupMixin
from django.conf import settings


class CmdInfo(CharacterLookupMixin, Command):
    """
    Display character information.
    
    Usage:
        info [character]                        - View character info
        info/set <field_name> = <value>         - Set a custom field on yourself
        info/clear <field_name>                 - Remove a custom field from yourself
        
    Staff Usage:
        info/set <character> = <field_name> = <value>  - Set field on another character
        info/clear <character> = <field_name>          - Remove field from another character
        
    This command shows a character's basic information including their full name,
    web profile link, and any custom fields they've set up. Custom fields can be
    used for things like "Online Times", "Roleplay Hooks", etc.
    
    Custom field limits:
    - Maximum 10 custom fields per character
    - Maximum 200 words per field
    
    Examples:
        info                                - View your own info
        info Alice                          - View Alice's info
        info/set Online Times = Usually evenings EST, weekends
        info/set Roleplay Hooks = Looking for adventure companions
        info/clear Online Times             - Remove the Online Times field
        
    Staff Examples:
        info/set Alice = Online Times = Usually evenings EST
        info/clear Alice = Online Times     - Remove Alice's Online Times field
    """
    
    key = "info"
    aliases = ["finger"]
    locks = "cmd:all()"
    help_category = "Character"
    
    def func(self):
        """Execute the command."""
        # Handle switches for setting/clearing custom fields
        if self.switches:
            switch = self.switches[0].lower()
            
            if switch == "set":
                if not self.args or "=" not in self.args:
                    if self.caller.check_permstring("Admin"):
                        self.msg("Usage: info/set <field_name> = <value> OR info/set <character> = <field_name> = <value>")
                    else:
                        self.msg("Usage: info/set <field_name> = <value>")
                    return
                    
                try:
                    # Check if this is staff syntax (character = field = value)
                    is_staff = self.caller.check_permstring("Admin")
                    parts = self.args.split("=")
                    
                    if is_staff and len(parts) == 3:
                        # Staff syntax: character = field_name = value
                        char_name, field_name, value = [part.strip() for part in parts]
                        target_char = self.find_character(char_name)
                        if not target_char:
                            return
                    elif len(parts) == 2:
                        # Regular syntax: field_name = value
                        field_name, value = [part.strip() for part in parts]
                        target_char = self.caller
                    else:
                        if is_staff:
                            self.msg("Usage: info/set <field_name> = <value> OR info/set <character> = <field_name> = <value>")
                        else:
                            self.msg("Usage: info/set <field_name> = <value>")
                        return
                    
                    if not field_name:
                        self.msg("Field name cannot be empty.")
                        return
                        
                    if not value:
                        self.msg("Field value cannot be empty. Use 'info/clear' to remove a field.")
                        return
                    
                    # Check word count (split on whitespace)
                    word_count = len(value.split())
                    if word_count > 200:
                        self.msg(f"Field value too long ({word_count} words). Maximum 200 words allowed.")
                        return
                    
                    # Get or create custom info dict
                    custom_info = target_char.db.custom_info or {}
                    
                    # Check field count limit
                    if field_name not in custom_info and len(custom_info) >= 10:
                        self.msg(f"Maximum 10 custom fields allowed on {target_char.name}. Remove a field first with 'info/clear'.")
                        return
                    
                    # Set the field
                    custom_info[field_name] = value
                    target_char.db.custom_info = custom_info
                    
                    if target_char == self.caller:
                        self.msg(f"Set custom field '{field_name}'.")
                    else:
                        self.msg(f"Set custom field '{field_name}' on {target_char.name}.")
                        target_char.msg(f"{self.caller.name} set your custom field '{field_name}'.")
                    
                except Exception as e:
                    self.msg(f"Error setting field: {e}")
                return
                
            elif switch == "clear":
                if not self.args:
                    if self.caller.check_permstring("Admin"):
                        self.msg("Usage: info/clear <field_name> OR info/clear <character> = <field_name>")
                    else:
                        self.msg("Usage: info/clear <field_name>")
                    return
                    
                # Check if this is staff syntax (character = field_name)
                is_staff = self.caller.check_permstring("Admin")
                
                if is_staff and "=" in self.args:
                    # Staff syntax: character = field_name
                    try:
                        char_name, field_name = self.args.split("=", 1)
                        char_name = char_name.strip()
                        field_name = field_name.strip()
                        target_char = self.find_character(char_name)
                        if not target_char:
                            return
                    except ValueError:
                        self.msg("Usage: info/clear <character> = <field_name>")
                        return
                else:
                    # Regular syntax: field_name
                    field_name = self.args.strip()
                    target_char = self.caller
                
                custom_info = target_char.db.custom_info or {}
                
                if field_name not in custom_info:
                    if target_char == self.caller:
                        self.msg(f"Field '{field_name}' not found.")
                    else:
                        self.msg(f"Field '{field_name}' not found on {target_char.name}.")
                    return
                
                del custom_info[field_name]
                target_char.db.custom_info = custom_info
                
                if target_char == self.caller:
                    self.msg(f"Removed custom field '{field_name}'.")
                else:
                    self.msg(f"Removed custom field '{field_name}' from {target_char.name}.")
                    target_char.msg(f"{self.caller.name} removed your custom field '{field_name}'.")
                return
                
            else:
                self.msg(f"Unknown switch '{switch}'. Use 'set' or 'clear'.")
                return
        
        # Show info (no switches)
        if not self.args:
            # Show own info
            self.show_info(self.caller)
            return
            
        # Show someone else's info
        char = self.find_character(self.args)
        if not char:
            return
        self.show_info(char)
    
    def show_info(self, char):
        """Display a character's info."""
        # Get character's display name
        display_name = char.db.full_name or char.name
        
        # Build web profile URL
        # Get the site domain from settings, defaulting to empiremush.org
        domain = getattr(settings, 'WEB_PROFILE_DOMAIN', 'empiremush.org')
        # Format: https://empiremush.org/characters/detail/CharName/123/
        web_url = f"https://{domain}/characters/detail/{char.name.lower()}/{char.id}/"
        
        # Start building the message
        msg = f"\n|w{char.name}'s Character Information|n"
        msg += f"\n|wCharacter Name:|n {display_name}"
        msg += f"\n|wWeb Profile:|n {web_url}"
        
        # Add custom fields if any exist
        custom_info = char.db.custom_info or {}
        if custom_info:
            msg += "\n"
            for field_name, field_value in sorted(custom_info.items()):
                msg += f"\n|w{field_name}:|n {field_value}"
        else:
            if char == self.caller:
                msg += "\n\n|yNo custom fields set. Use 'info/set <field> = <value>' to add some!|n"
        
        self.msg(msg) 