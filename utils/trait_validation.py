"""
Centralized trait validation and manipulation utilities.
"""
from typing import Optional, Tuple, Dict, Any, Union
from .trait_definitions import TraitDefinition

class TraitValidator:
    """Centralized trait validation and helper methods."""
    
    VALID_DIE_SIZES = {'4', '6', '8', '10', '12'}
    
    TRAIT_CATEGORIES = {
        'attributes': 'character_attributes',
        'skills': 'skills', 
        'signature_assets': 'signature_assets',
        'distinctions': 'distinctions',
        'resources': 'char_resources',
        'powers': 'powers'
    }
    
    @classmethod
    def validate_die_size(cls, die_size: Union[str, int]) -> bool:
        """Validate that a die size is valid."""
        return str(die_size) in cls.VALID_DIE_SIZES
    
    @classmethod
    def validate_trait_category(cls, category: str) -> bool:
        """Validate that a trait category is valid."""
        return category.lower() in cls.TRAIT_CATEGORIES
    
    @classmethod
    def get_trait_handler(cls, character: Any, category: str) -> Optional[Any]:
        """Get the appropriate trait handler for a category."""
        category = category.lower()
        if category not in cls.TRAIT_CATEGORIES:
            return None
        
        handler_name = cls.TRAIT_CATEGORIES[category]
        return getattr(character, handler_name, None)
    
    @classmethod
    def parse_trait_command(cls, args: str) -> Optional[Tuple[str, str, str, str]]:
        """
        Parse trait command arguments in format: <character> = <category> <name> <die> [description]
        
        Returns:
            Tuple of (character_name, category, trait_name, die_size, description) or None
        """
        if not args or "=" not in args:
            return None
            
        char_name, rest = [part.strip() for part in args.split("=", 1)]
        parts = rest.strip().split()
        
        if len(parts) < 3:
            return None
            
        category = parts[0].lower()
        trait_name = parts[1].lower()
        die_size = parts[2]
        description = " ".join(parts[3:]) if len(parts) > 3 else ""
        
        # Validate die size format
        if not die_size.startswith('d') or not die_size[1:].isdigit():
            return None
            
        die_value = die_size[1:]
        if not cls.validate_die_size(die_value):
            return None
            
        if not cls.validate_trait_category(category):
            return None
            
        return char_name, category, trait_name, die_value, description
    
    @classmethod
    def get_trait_display_info(cls, trait: Any) -> Tuple[str, str, str]:
        """Get standardized display information for a trait."""
        if not trait:
            return "", "", ""
            
        # Get name (prefer trait.name, fallback to trait.key)
        name = getattr(trait, 'name', '') or getattr(trait, 'key', '')
        
        # Get die size
        die_value = getattr(trait, 'base', None) or getattr(trait, 'value', 0)
        die_size = f"d{int(die_value)}" if die_value else ""
        
        # Get description
        description = getattr(trait, 'desc', '') or ""
        
        return name, die_size, description
