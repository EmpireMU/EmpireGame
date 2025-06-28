"""
Organization utility functions.
"""

from evennia.utils.search import search_object
from evennia.utils import evtable
from typeclasses.organisations import Organisation
from typeclasses.characters import Character
from utils.resource_utils import validate_resource_owner

# Note: For permission checks, use Evennia's built-in system:
# - caller.permissions.check() for general permission checks
# - has_perm() for specific permission checks
# - locks for more complex permission requirements

def validate_rank(rank_str, default=None, caller=None):
    """Validate rank numbers.
    
    Args:
        rank_str: The rank string to validate
        default: Default value if validation fails
        caller: Optional caller to send error messages to
        
    Returns:
        int or None: The validated rank number or None if invalid
    """
    try:
        rank = int(rank_str)
        if not 1 <= rank <= 10:
            if caller:
                caller.msg("Rank must be a number between 1 and 10.")
            return None
        return rank
    except (ValueError, TypeError):
        if default is not None:
            return default
        if caller:
            caller.msg("Rank must be a number between 1 and 10.")
        return None


def get_org(org_name, caller=None):
    """Find and validate an organization.
    
    Args:
        org_name: Name of the organization to find
        caller: Optional caller to send error messages to
        
    Returns:
        Organisation or None: The found organization or None if not found
    """
    org = caller.search(org_name, global_search=True) if caller else search_object(org_name)
    if not org:
        return None
        
    if not isinstance(org, Organisation):
        if caller:
            caller.msg(f"{org.name} is not an organization.")
        return None
        
    return org


def get_char(char_name, caller=None, check_resources=False):
    """Find and validate a character.
    
    Args:
        char_name: Name of the character to find
        caller: Optional caller to send error messages to
        check_resources: Whether to check if character can own resources
        
    Returns:
        Character or None: The found character or None if not found
    """
    char = caller.search(char_name, global_search=True) if caller else search_object(char_name)
    if not char:
        return None
        
    if check_resources and not validate_resource_owner(char, caller):
        return None
        
    return char


def get_org_and_char(org_name, char_name, caller=None):
    """Find both an organization and a character.
    
    Args:
        org_name: Name of the organization to find
        char_name: Name of the character to find
        caller: Optional caller to send error messages to
        
    Returns:
        tuple: (org, char) where either may be None if not found
    """
    org = get_org(org_name, caller)
    if not org:
        return None, None
        
    char = get_char(char_name, caller)
    if not char:
        return org, None
        
    return org, char


# Import parsing functions from centralized location
from utils.command_utils import parse_equals, parse_comma