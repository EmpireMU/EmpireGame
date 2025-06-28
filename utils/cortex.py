"""
Cortex Prime game system utilities.
"""

from typing import List, Tuple, Optional, Dict, NamedTuple, Any
from collections import defaultdict
from random import randint

# Define difficulty ratings as constants
DIFFICULTIES = {
    "very easy": 3,
    "easy": 7,
    "challenging": 11,
    "hard": 15,
    "very hard": 19
}

# Define die size progression
DIE_SIZES = ['4', '6', '8', '10', '12']

def step_die(die_size: str, steps: int) -> str:
    """
    Step a die up or down by the specified number of steps.
    
    Args:
        die_size: The current die size (e.g., "8" for d8)
        steps: Number of steps (positive for up, negative for down)
        
    Returns:
        New die size after stepping
    """
    try:
        current_index = DIE_SIZES.index(die_size)
        new_index = max(0, min(len(DIE_SIZES) - 1, current_index + steps))
        return DIE_SIZES[new_index]
    except ValueError:
        return die_size  # Return original if invalid

class TraitDie(NamedTuple):
    """Represents a die in the pool with its trait information."""
    size: str  # The die size (e.g., "8" for d8)
    category: Optional[str]  # The trait category (e.g., "attributes")
    key: Optional[str]  # The trait key (e.g., "prowess")
    step_mod: Optional[str]  # Step modifier (U for up, D for down, None for no mod)
    caller: Optional[Any] = None  # Reference to the character object

def get_trait_die(character, trait_spec: str) -> Optional[Tuple[str, str, str, bool]]:
    """
    Get the die size and category for a trait specification.
    Handles step up/down modifiers in the form trait_key(U) or trait_key(D),
    and doubling in the form trait_key(double).
    
    Args:
        character: The character object to check traits on
        trait_spec: The trait specification (e.g., "prowess" or "prowess(U)" or "prowess(double)")
        
    Returns:
        Tuple of (die_size, category_name, step_mod, doubled) or None if not found
        doubled indicates if an extra die of the same size should be added
    """
    if not hasattr(character, 'character_attributes'):
        return None
        
    # Parse trait specification for modifiers
    trait_key = trait_spec
    step_mod = None
    doubled = False
    if '(' in trait_spec and ')' in trait_spec:
        trait_key, mod = trait_spec.split('(', 1)
        mod = mod.rstrip(')').upper()  # Convert to uppercase for comparison
        if mod in ('U', 'D'):
            step_mod = mod
        elif mod.lower() == 'double':
            doubled = True
        trait_key = trait_key.strip()
    
    # Try each trait category in order
    categories = [
        ('character_attributes', character.character_attributes),
        ('skills', character.skills),
        ('distinctions', character.distinctions),
        ('char_resources', character.char_resources),
        ('signature_assets', character.signature_assets),
        ('powers', character.powers),
        ('temporary_assets', character.temporary_assets)
    ]
    
    # Convert spaces to underscores for key lookup
    trait_key = trait_key.lower().replace(' ', '_')
    
    for category_name, handler in categories:
        # For distinctions, check both key and name
        if category_name == 'distinctions':
            # First try by key
            trait = handler.get(trait_key)
            if not trait:
                # If not found by key, try to find by name
                for key in handler.all():
                    trait = handler.get(key)
                    if hasattr(trait, 'name') and trait.name.lower() == trait_key.replace('_', ' '):
                        trait_key = key  # Use the actual key for the trait
                        break
                else:
                    trait = None
        else:
            # For other categories, try case-insensitive key lookup
            trait = None
            for key in handler.all():
                if key.lower() == trait_key:
                    trait = handler.get(key)
                    trait_key = key  # Use the actual key for the trait
                    break
            
        if trait:
            # For distinctions, always use d8 unless stepped down
            if category_name == 'distinctions':
                die_size = '8'
            else:
                die_size = str(trait.base)
                
            # Apply step modification if present
            if step_mod:
                die_size = step_die(die_size, 1 if step_mod == 'U' else -1)
            return die_size, category_name, step_mod, doubled
            
    return None

def validate_dice_pool(dice: List[TraitDie]) -> Optional[str]:
    """
    Validate the dice pool according to Cortex Prime rules.
    
    Args:
        dice: List of TraitDie objects representing the dice pool
        
    Returns:
        Error message if invalid, None if valid
        
    Rules:
    - When using any traits (including Resources/Assets), all three Prime sets are required:
      * One Attribute
      * One Skill
      * One Distinction
    - Raw dice can be rolled individually
    """
    # Track which prime trait sets are used
    has_attribute = False
    has_skill = False
    has_distinction = False
    requires_prime_sets = False  # True if prime sets are required
    
    for die in dice:
        if die.category:  # It's a trait, not a raw die
            if die.category == 'character_attributes':
                has_attribute = True
                requires_prime_sets = True
            elif die.category == 'skills':
                has_skill = True
                requires_prime_sets = True
            elif die.category == 'distinctions':
                has_distinction = True
                requires_prime_sets = True
            elif die.category in ('signature_assets', 'char_resources'):
                requires_prime_sets = True  # Signature Assets and Resources require prime sets
    
    # If prime sets are required (due to any trait use), check all three are present
    if requires_prime_sets:
        missing_sets = []
        if not has_attribute:
            missing_sets.append("Attribute")
        if not has_skill:
            missing_sets.append("Skill")
        if not has_distinction:
            missing_sets.append("Distinction")
            
        if missing_sets:
            if len(missing_sets) == 1:
                return f"When using traits, you must include a {missing_sets[0]}."
            else:
                missing = ", ".join(missing_sets[:-1]) + f" and {missing_sets[-1]}"
                return f"When using traits, you must include an {missing}."
        
    return None

def roll_die(sides: int) -> int:
    """Roll a single die."""
    return randint(1, int(sides))

def process_results(results, hitches=False):
    """
    Process dice roll results.
    
    Args:
        results: List of (value, die_size) tuples
        hitches: Whether to count 1s as hitches (parameter kept for compatibility)
        
    Returns:
        Tuple of (total, effect_die, hitch_dice_sizes)
        - total: Sum of the two highest non-hitch dice
        - effect_die: The largest die size not used in the final result calculation, or 4 if no unused dice
        - hitch_dice_sizes: List of die sizes that rolled 1s
    """
    if not results:
        return 0, 0, []
        
    # Sort results by value, highest first
    sorted_results = sorted(results, key=lambda x: x[0], reverse=True)
    
    # Find hitches (dice that rolled 1) and collect their die sizes
    hitch_dice_sizes = [die_size for value, die_size in results if value == 1]
    
    # Filter out hitches from total calculation
    non_hitch_results = [result for result in sorted_results if result[0] != 1]
    
    # Calculate total from two highest non-hitch dice
    if len(non_hitch_results) >= 2:
        total = non_hitch_results[0][0] + non_hitch_results[1][0]
        # Get the die sizes used for the final result (two highest non-hitch)
        used_dice = non_hitch_results[:2]
        used_die_sizes = [die_size for value, die_size in used_dice]
        
        # Find unused dice (excluding hitches)
        unused_dice = non_hitch_results[2:]  # All non-hitch dice after the first two
        
        if unused_dice:
            # Effect die is the largest die size among unused dice
            unused_die_sizes = [die_size for value, die_size in unused_dice]
            effect_die = max(unused_die_sizes)
        else:
            # No unused dice, effect die defaults to 4
            effect_die = 4
    elif len(non_hitch_results) == 1:
        total = non_hitch_results[0][0]
        # Only one non-hitch die, effect die defaults to 4
        effect_die = 4
    else:
        # All dice are hitches - total is 0, effect die defaults to 4
        total = 0
        effect_die = 4
    
    return total, effect_die, hitch_dice_sizes

def get_success_level(total: int, difficulty: Optional[int]) -> Tuple[bool, bool]:
    """
    Determine success and if it's heroic.
    
    Args:
        total: The total of the two highest dice
        difficulty: The target difficulty number or None
        
    Returns:
        Tuple of (success, heroic) where:
        - success is True if total >= difficulty
        - heroic is True if total >= difficulty + 5 AND difficulty >= 11 (challenging)
        
    Example: Against difficulty 11 (challenging)
    - 10 or less = Failure
    - 11-15 = Success
    - 16+ = Heroic Success
    
    Example: Against difficulty 7 (easy)
    - 6 or less = Failure
    - 7+ = Success (no heroic possible)
    """
    if difficulty is None:
        return True, False
        
    success = total >= difficulty
    # Only allow heroic successes on challenging (11) or higher difficulties
    heroic = total >= (difficulty + 5) and difficulty >= 11
    return success, heroic

def format_roll_result(value: int, die: str, trait: TraitDie) -> str:
    """
    Format a single die roll result with trait information.
    
    Args:
        value: The number rolled
        die: The die size
        trait: The TraitDie object with trait information
        
    Returns:
        Formatted string like "7(d8)" or "7(d8 Attribute: prowess)"
    """
    if trait.category:
        category_name = trait.category.title().rstrip('s')  # Remove trailing 's' and capitalize
        return f"{value}(d{die} {category_name}: {trait.key})"
    return f"{value}(d{die})"

def get_all_traits(character):
    """Get all traits for a character."""
    return [
        ('character_attributes', character.character_attributes),
        ('skills', character.skills),
        ('distinctions', character.distinctions),
        ('signature_assets', character.signature_assets),
        ('powers', character.powers),
        ('char_resources', character.char_resources)
    ] 