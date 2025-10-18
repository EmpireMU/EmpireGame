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

    # No matches were found.
    if not quiet:
        nofound_string = kwargs.get("nofound_string", "Could not find '{query}'.")
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

