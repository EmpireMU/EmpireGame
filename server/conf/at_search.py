"""
Search and multimatch handling

This module allows for overloading two functions used by Evennia's
search functionality:

    at_search_result:
        This is called whenever a result is returned from an object
        search (a common operation in commands).  It should (together
        with at_multimatch_input below) define some way to present and
        differentiate between multiple matches (by default these are
        presented as 1-ball, 2-ball etc)
    at_multimatch_input:
        This is called with a search term and should be able to
        identify if the user wants to separate a multimatch-result
        (such as that from a previous search). By default, this
        function understands input on the form 1-ball, 2-ball etc as
        indicating that the 1st or 2nd match for "ball" should be
        used.

This module is not called by default, to use it, add the following
line to your settings file:

    SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"

"""


def fuzzy_match(obj, search_words):
    """
    Check if an object matches a multi-keyword search.
    
    Allows searches like "ad upe cha" to match "Ada's super duper awesome chair"
    by checking if each search word is a prefix of words in the name, in order.
    
    Args:
        obj: The object to check
        search_words (list): List of search word prefixes
        
    Returns:
        bool: True if the object matches
    """
    # Check the object's key (name)
    name_words = obj.key.lower().split()
    search_idx = 0
    for name_word in name_words:
        if search_idx < len(search_words) and name_word.startswith(search_words[search_idx]):
            search_idx += 1
    
    if search_idx == len(search_words):
        return True
    
    # Also check aliases
    for alias in obj.aliases.all():
        alias_words = alias.lower().split()
        search_idx = 0
        for alias_word in alias_words:
            if search_idx < len(search_words) and alias_word.startswith(search_words[search_idx]):
                search_idx += 1
        
        if search_idx == len(search_words):
            return True
    
    return False


def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """
    This is a generic hook for handling all processing of a search
    result, including error reporting.

    Custom implementation: Adds multi-keyword fuzzy matching as a fallback
    when the default search returns no results.

    Args:
        matches (list): This is a list of 0, 1 or more typeclass instances,
            the matched result of the search. If 0, a nomatch error should
            be echoed, and if >1, multimatch errors should be given. Only
            if a single match should the result pass through.
        caller (Object): The object performing the search and/or which should
        receive error messages.
    query (str, optional): The search query used to produce `matches`.
        quiet (bool, optional): If `True`, no messages will be echoed to caller
            on errors.

    Keyword Args:
        nofound_string (str): Replacement string to echo on a notfound error.
        multimatch_string (str): Replacement string to echo on a multimatch error.

    Returns:
        processed_result (Object or None): This is always a single result
            or `None`. If `None`, any error reporting/handling should
            already have happened.

    """
    # If we got matches, use default behavior
    if matches:
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            if not quiet:
                caller.msg(f"Multiple matches for '{query}': {', '.join([m.get_display_name(caller) for m in matches])}")
            return None
    
    # No matches - try fuzzy matching if it's a multi-word search
    if query and ' ' in query:
        search_words = query.lower().split()
        fuzzy_matches = []
        
        # Search in location
        if hasattr(caller, 'location') and caller.location:
            for obj in caller.location.contents:
                if obj != caller and fuzzy_match(obj, search_words):
                    fuzzy_matches.append(obj)
        
        # Search in inventory
        if hasattr(caller, 'contents'):
            for obj in caller.contents:
                if fuzzy_match(obj, search_words):
                    fuzzy_matches.append(obj)
        
        # If we found fuzzy matches, handle them
        if fuzzy_matches:
            if len(fuzzy_matches) == 1:
                return fuzzy_matches[0]
            elif len(fuzzy_matches) > 1:
                if not quiet:
                    caller.msg(f"Multiple matches for '{query}': {', '.join([m.get_display_name(caller) for m in fuzzy_matches])}")
                return None
    
    # No matches at all
    if not quiet:
        nofound_string = kwargs.get('nofound_string')
        if nofound_string:
            caller.msg(nofound_string)
        else:
            caller.msg(f"Could not find '{query}'.")
    
    return None
