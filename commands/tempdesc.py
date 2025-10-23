"""
Temporary description command.

Allows players to set a temporary description that appears after their main
description, separated by a blank line.
"""

from evennia.commands.default.muxcommand import MuxCommand


class CmdTempDesc(MuxCommand):
    """
    Set a temporary description for your character.
    
    Usage:
        tempdesc <description>
        tempdesc/clear
        tempdesc
    
    This sets a temporary description that will appear after your main
    description when someone looks at you. The temporary description is
    separated from your main description by a blank line.
    
    Examples:
        tempdesc She has a fresh bandage wrapped around her left arm.
        tempdesc/clear  - Removes the temporary description
        tempdesc        - Views your current temporary description
    """
    
    key = "tempdesc"
    aliases = ["tdesc"]
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the command."""
        caller = self.caller
        
        # Check if we have /clear switch
        if "clear" in self.switches:
            if caller.db.tempdesc:
                caller.db.tempdesc = ""
                caller.msg("Temporary description cleared.")
            else:
                caller.msg("You don't have a temporary description set.")
            return
        
        # If no arguments, show current temporary description
        if not self.args:
            tempdesc = caller.db.tempdesc
            if tempdesc:
                caller.msg(f"Your current temporary description:\n{tempdesc}")
            else:
                caller.msg("You don't have a temporary description set.")
            return
        
        # Set the temporary description
        tempdesc = self.args.strip()
        caller.db.tempdesc = tempdesc
        caller.msg(f"Temporary description set to:\n{tempdesc}")

