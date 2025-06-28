"""
Resource utility functions.
"""

import re


def get_unique_resource_name(name, existing_resources, caller=None):
    """Get a unique name for a resource, appending a number if needed.
    
    Args:
        name (str): Base name for the resource
        existing_resources (dict or TraitHandler): Existing resources to check against
        caller (optional): Caller to notify about name changes
        
    Returns:
        str: A unique name for the resource
    """
    # First try to strip any existing number suffix
    base_name = re.sub(r'[_\s]+\d+$', '', name)
    
    # If it's a TraitHandler, check if the base name exists
    if hasattr(existing_resources, 'get'):
        if not existing_resources.get(base_name):
            if base_name != name and caller:
                caller.msg(f"Simplified resource name from '{name}' to '{base_name}'.")
            return base_name
            
        # Find the next available number
        counter = 1
        while existing_resources.get(f"{base_name}_{counter}"):
            counter += 1
            
        new_name = f"{base_name}_{counter}"
        if new_name != name and caller:
            caller.msg(f"Resource name '{base_name}' already exists, using '{new_name}' instead.")
            
        return new_name
    else:
        # Handle plain dictionaries (for backward compatibility)
        if base_name not in existing_resources:
            if base_name != name and caller:
                caller.msg(f"Simplified resource name from '{name}' to '{base_name}'.")
            return base_name
            
        # Find the next available number
        counter = 1
        while f"{base_name}_{counter}" in existing_resources:
            counter += 1
            
        new_name = f"{base_name}_{counter}"
        if new_name != name and caller:
            caller.msg(f"Resource name '{base_name}' already exists, using '{new_name}' instead.")
            
        return new_name


def validate_resource_owner(obj, caller=None):
    """Check if an object can own resources.
    
    Args:
        obj: The object to check
        caller (optional): Caller to notify if validation fails
        
    Returns:
        bool: True if the object can own resources, False otherwise
    """
    has_resources = (
        hasattr(obj, 'char_resources') or 
        hasattr(obj, 'org_resources')
    )
    if not has_resources and caller:
        caller.msg(f"{obj.name} cannot own resources.")
    return has_resources


def validate_die_size(die_size, caller=None):
    """Validate that a die size is valid for resources.
    
    Args:
        die_size (int): The die size to validate
        caller (optional): Caller to notify if validation fails
        
    Returns:
        bool: True if the die size is valid, False otherwise
    """
    valid_sizes = [4, 6, 8, 10, 12]
    is_valid = die_size in valid_sizes
    
    if not is_valid and caller:
        caller.msg(f"Die size must be one of: {', '.join(map(str, valid_sizes))}")
        
    return is_valid 