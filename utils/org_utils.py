"""
Organisation utility functions.
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
    """Find and validate an organisation.
    
    Args:
        org_name: Name of the organisation to find
        caller: Optional caller to send error messages to
        
    Returns:
        Organisation or None: The found organisation or None if not found
    """
    if not org_name:
        return None

    search_kwargs = {
        "typeclass": Organisation,
        "global_search": True,
    }

    if caller:
        results = caller.search(org_name, quiet=True, **search_kwargs)
    else:
        results = search_object(org_name, **search_kwargs)

    if not results:
        if caller:
            caller.msg(f"No organisation named '{org_name}' found.")
        return None

    # `search` may return a single object or a list; normalise to list.
    if not isinstance(results, (list, tuple)):
        matches = [results]
    else:
        matches = list(results)

    matches = [obj for obj in matches if isinstance(obj, Organisation)]
    if not matches:
        if caller:
            caller.msg(f"No organisation named '{org_name}' found.")
        return None

    # Prefer an exact name match if more than one result.
    exact_matches = [obj for obj in matches if obj.key.lower() == org_name.lower()]
    if len(exact_matches) == 1:
        return exact_matches[0]

    if len(matches) == 1:
        return matches[0]

    if caller:
        display_names = ", ".join(
            obj.get_display_name(caller)
            if hasattr(obj, "get_display_name")
            else obj.key
            for obj in matches
        )
        caller.msg(f"Multiple organisations match '{org_name}': {display_names}.")
        caller.msg("Please be more specific.")
    return None


def get_char(char_name, caller=None, check_resources=False):
    """Find and validate a character.
    
    Args:
        char_name: Name of the character to find
        caller: Optional caller to send error messages to
        check_resources: Whether to check if character can own resources
        
    Returns:
        Character or None: The found character or None if not found
    """
    if not char_name:
        return None

    search_kwargs = {
        "typeclass": Character,
        "global_search": True,
    }

    if caller:
        results = caller.search(char_name, quiet=True, **search_kwargs)
    else:
        results = search_object(char_name, **search_kwargs)

    if not results:
        if caller:
            caller.msg(f"No character named '{char_name}' found.")
        return None

    if not isinstance(results, (list, tuple)):
        matches = [results]
    else:
        matches = list(results)

    matches = [obj for obj in matches if isinstance(obj, Character)]
    if not matches:
        if caller:
            caller.msg(f"No character named '{char_name}' found.")
        return None

    exact_matches = [obj for obj in matches if obj.key.lower() == char_name.lower()]
    if len(exact_matches) == 1:
        char = exact_matches[0]
    elif len(matches) == 1:
        char = matches[0]
    else:
        if caller:
            display_names = ", ".join(
                obj.get_display_name(caller)
                if hasattr(obj, "get_display_name")
                else obj.key
                for obj in matches
            )
            caller.msg(f"Multiple characters match '{char_name}': {display_names}.")
            caller.msg("Please be more specific.")
        return None

    if check_resources and not validate_resource_owner(char, caller):
        return None
        
    return char


def get_org_and_char(org_name, char_name, caller=None):
    """Find both an organisation and a character.
    
    Args:
        org_name: Name of the organisation to find
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


def get_character_organisation_ids(character: Character) -> set[int]:
    organisations = character.attributes.get("organisations", category="organisations") or {}
    return {int(org_id) for org_id in organisations.keys()}


def get_account_organisations(account) -> set[int]:
    org_ids: set[int] = set()
    characters = []
    # Include any stored character relations on the account
    if hasattr(account, "characters"):
        try:
            characters = list(account.characters.all())
        except Exception:  # pragma: no cover - extremely defensive
            characters = []

    # Fallback to currently puppeted characters if available
    if not characters:
        session_handler = getattr(account, "sessions", None)
        if session_handler:
            get_sessions = getattr(session_handler, "get_sessions", None)
            if callable(get_sessions):
                for session in get_sessions():
                    puppet = getattr(session, "get_puppet", None)
                    if callable(puppet):
                        puppet_obj = puppet()
                        if puppet_obj:
                            characters.append(puppet_obj)

    for character in characters:
        org_ids.update(get_character_organisation_ids(character))
    if hasattr(account, "db"):
        tracked = account.attributes.get("organisations", category="organisations") or {}
        org_ids.update(int(org_id) for org_id in tracked.keys())
    return org_ids


