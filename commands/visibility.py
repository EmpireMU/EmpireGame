"""
Simple visibility commands for the where command.
"""

from evennia.commands.default.muxcommand import MuxCommand


class CmdInvisible(MuxCommand):
    """
    Make yourself invisible in the where command.
    
    Usage:
        invisible
    """
    
    key = "invisible"
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        self.caller.db.invisible = True
        self.msg("You are now invisible in the 'where' command.")


class CmdVisible(MuxCommand):
    """
    Make yourself visible in the where command.
    
    Usage:
        visible
    """
    
    key = "visible"
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        self.caller.db.invisible = False
        self.msg("You are now visible in the 'where' command.") 