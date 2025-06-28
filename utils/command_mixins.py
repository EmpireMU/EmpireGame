"""
Base command classes with common functionality.
"""
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.command import Command
from utils.command_utils import parse_equals
from utils.trait_validation import TraitValidator

class CharacterLookupMixin(MuxCommand):
    """Mixin providing character lookup utilities for commands."""
    
    def find_character(self, char_name: str, require_traits: bool = False):
        """
        Find and validate a character.
        
        Args:
            char_name: Name of character to find
            require_traits: Whether character must support traits
            
        Returns:
            Character object or None if not found/invalid
        """
        # Use global search to find both online and offline characters
        char = self.caller.search(char_name, global_search=True)
        if not char:
            return None
            
        if require_traits and not hasattr(char, 'traits'):
            self.msg(f"{char.name} does not support traits (wrong typeclass?).")
            return None
            
        return char
    
    def parse_character_command(self, usage_msg: str):
        """
        Parse commands in format: <character> = <rest>
        
        Args:
            usage_msg: Usage message to show on error
            
        Returns:
            Tuple of (character, rest_of_args) or (None, None) on error
        """
        if not self.args or "=" not in self.args:
            self.msg(f"Usage: {usage_msg}")
            return None, None
            
        char_name, rest = parse_equals(self.args, usage_msg, self)
        if not char_name or not rest:
            return None, None
            
        char = self.find_character(char_name, require_traits=True)
        if not char:
            return None, None
            
        return char, rest

class TraitCommand(CharacterLookupMixin):
    """Base class for trait manipulation commands."""
    
    def validate_trait_args(self, rest_args: str, min_parts: int = 2):
        """
        Validate trait command arguments.
        
        Args:
            rest_args: The arguments after character name
            min_parts: Minimum number of parts required
            
        Returns:
            List of parsed parts or None on error
        """
        parts = rest_args.strip().split()
        if len(parts) < min_parts:
            return None
        return parts
    
    def get_trait_handler(self, character, category: str):
        """Get trait handler for a category with validation."""
        handler = TraitValidator.get_trait_handler(character, category)
        if not handler:
            valid_categories = ", ".join(TraitValidator.TRAIT_CATEGORIES.keys())
            self.msg(f"Invalid category. Must be one of: {valid_categories}")
            return None
        return handler
