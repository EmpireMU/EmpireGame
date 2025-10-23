"""
AFK (Away From Keyboard) command for toggling away status.
"""

from evennia.commands.default.muxcommand import MuxCommand


class CmdAFK(MuxCommand):
    """
    Toggle your AFK (Away From Keyboard) status.
    
    Usage:
        afk [<message>]
        
    This command toggles your AFK status. When AFK, other players will see
    an indicator next to your name in various commands (who, where, room lists).
    
    You can optionally provide a message that will be shown in the 'who' and
    'info' commands, such as "Back in 30 minutes".
    
    When someone pages you while AFK, they will be notified that you are away.
    
    Examples:
        afk                          - Toggle AFK on/off
        afk Back in 30 minutes       - Set AFK with a message
        afk                          - Toggle off (message is cleared)
    """
    
    key = "afk"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the command."""
        caller = self.caller
        
        # Check current AFK status
        is_afk = caller.db.afk or False
        
        if is_afk:
            # Turning AFK off
            caller.db.afk = False
            caller.db.afk_message = None
            caller.msg("|yYou are no longer AFK.|n")
        else:
            # Turning AFK on
            caller.db.afk = True
            
            # Store the optional message
            if self.args:
                afk_message = self.args.strip()
                caller.db.afk_message = afk_message
                caller.msg(f"|yYou are now AFK: {afk_message}|n")
            else:
                caller.db.afk_message = None
                caller.msg("|yYou are now AFK.|n")

