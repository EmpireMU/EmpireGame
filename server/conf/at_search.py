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

from evennia.utils import logger


def _find_character_in_context(caller, name_prefix):
    """Find a character in caller's vicinity whose name starts with prefix."""
    name_prefix = name_prefix.lower()
    candidates = []

    def consider(obj):
        if obj and obj.is_typeclass("typeclasses.characters.Character", exact=False):
            if obj.key.lower().startswith(name_prefix):
                candidates.append(obj)

    consider(caller if hasattr(caller, "is_typeclass") else None)

    location = getattr(caller, "location", None)
    if location:
        for obj in location.contents:
            consider(obj)

    return candidates


def _find_worn_items(owner, item_prefix):
    """Return worn items on owner matching the given prefix."""
    item_prefix = item_prefix.lower()
    items = []

    worn_items = []
    if hasattr(owner, "get_worn_items"):
        worn_items = owner.get_worn_items() or []
    else:
        worn_items = owner.db.worn_items or []

    for item in worn_items:
        if not item:
            continue
        if item.key.lower().startswith(item_prefix):
            items.append(item)
            continue
        for alias in item.aliases.all():
            if alias.lower().startswith(item_prefix):
                items.append(item)
                break

    return items


def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """
    This is a generic hook for handling all processing of a search
    result, including error reporting.

    args:
        matches (list): This is a list of 0, 1 or more typeclass instances,
            the matched result of the search. If 0, a nomatch error should
            be echoed, and if >1, multimatch errors should be given. Only
            if a single match should the result pass through.
        caller (Object): The object performing the search and/or which should
            receive error messages.
        query (str, optional): The search query used to produce `matches`.
        quiet (bool, optional): If `True`, no messages will be echoed to caller
            on errors.

    Kwargs:
        nofound_string (str): Replacement string to echo on a notfound error.
        multimatch_string (str): Replacement string to echo on a multimatch error.

    Returns:
        processed_result (Object or None): This is always a single result
            or `None`. If `None`, any error reporting/handling should
            already have happened.

    """
    if matches:
        if len(matches) == 1:
            return matches[0]

        # Prefer characters over other objects when there is a single
        # character among the matches.
        char_matches = [obj for obj in matches if obj.is_typeclass("typeclasses.characters.Character", exact=False)]
        if len(char_matches) == 1:
            return char_matches[0]

        if not quiet:
            entries = []
            for index, match in enumerate(matches, start=1):
                display = match.get_display_name(caller) if hasattr(match, "get_display_name") else match.key
                entries.append(f"  {index}. {display}")

            multimatch_msg = kwargs.get("multimatch_string")
            if not multimatch_msg:
                multimatch_msg = (
                    f"Multiple matches for '{{query}}':\n{{entries}}\n"
                    "Use '{query}-{number}' (for example '{query}-1') to select a specific one."
                )

            caller.msg(multimatch_msg.format(query=query, entries="\n".join(entries)))
        return None

    # If no matches, try possessive/worn item lookup (e.g. "Ada's red dress")
    if query:
        owner_query = None
        item_query = None

        if "'s" in query:
            owner_query, item_query = query.split("'s", 1)
        elif " " in query:
            owner_query, item_query = query.split(" ", 1)

        if owner_query and item_query:
            owner_query = owner_query.strip()
            item_query = item_query.strip()

            if owner_query and item_query:
                owners = _find_character_in_context(caller, owner_query)
                if len(owners) == 1:
                    owner = owners[0]
                    worn_matches = _find_worn_items(owner, item_query)
                    if len(worn_matches) == 1:
                        return worn_matches[0]
                    elif len(worn_matches) > 1 and not quiet:
                        entries = []
                        for index, match in enumerate(worn_matches, start=1):
                            display = match.get_display_name(caller) if hasattr(match, "get_display_name") else match.key
                            entries.append(f"  {index}. {display}")
                        caller.msg(
                            "Multiple worn items match '{item}' on {owner}:\n{entries}".format(
                                item=item_query,
                                owner=owner.get_display_name(caller) if hasattr(owner, "get_display_name") else owner.key,
                                entries="\n".join(entries)
                            )
                        )
                        return None

    # No matches were found.
    if not quiet:
        nofound_string = kwargs.get("nofound_string") or "Could not find '{query}'."
        caller.msg(nofound_string.format(query=query))
    return None


def at_multimatch_input(caller, raw_string, matches, **kwargs):
    """
    This processes the input leading up to a new search when the
    previous search result produced multiple matches.  By default it
    expects the user to append a number at the end of the input, to
    identify which of the matches they want.  You can customize this
    to this to produce more advanced parsing/syntax.

    The arguments are the same as for `at_search_result`.

    Returns:
        str: A string that should be used for a new search. If None,
            the search should be redone with the original input.

    """
    if matches and raw_string:
        index = raw_string.split()[-1]
        if index.isdigit():
            index = int(index) - 1
            if 0 <= index < len(matches):
                return matches[index]
    return raw_string

