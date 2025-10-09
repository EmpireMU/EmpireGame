"""
Commands for the narrative time system.
"""

from evennia.commands.default.muxcommand import MuxCommand
from typeclasses.time import NarrativeTime


class CmdTime(MuxCommand):
    """
    View the current time.
    
    Usage:
        time                - View current time
        
    Time advances at the speed of story.
    
    Example:
        time                - View current time
    """
    
    key = "time"
    locks = "cmd:all();set:perm(Builder)"
    help_category = "General"
    switch_options = ("set",)
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add staff commands if caller has Builder permissions
        if caller.check_permstring("Builder"):
            help_text += """
    
    |yBuilder Commands:|n
        time/set <time>     - Set narrative time
        
    Builder Examples:
        time/set Spring of 632 AF                        - Set simple time
        time/set Dawn on the 15th day of Harvestmoon     - Set detailed time
        time/set Three hours after the siege began       - Set relative time
        time/set The morning after the betrayal          - Set narrative time
        
    Note: Narrative time is freeform text and can be any description that
    fits the story progression.
            """
        
        return help_text
    
    def func(self):
        """Execute the command."""
        if self.switches:
            if "set" in self.switches:
                # Staff command to set time
                if not self.access(self.caller, "set"):
                    self.msg("You don't have permission to set the narrative time.")
                    return
                    
                if not self.args:
                    self.msg("Usage: time/set <narrative time>")
                    return
                    
                self._set_time()
            else:
                self.msg(f"Unknown switch: {self.switches[0]}")
        else:
            # Default: show current time
            self._show_time()
    
    def _show_time(self):
        """Show the current narrative time."""
        time_tracker = NarrativeTime.get_instance()
        current_time = time_tracker.current_time
        self.msg(f"It is |c{current_time}|n.")
    
    def _set_time(self):
        """Set the narrative time (staff only)."""
        new_time = self.args.strip()
        
        if not new_time:
            self.msg("Time cannot be empty.")
            return
            
        time_tracker = NarrativeTime.get_instance()
        old_time = time_tracker.current_time
        time_tracker.set_time(new_time)
        
        self.msg(f"Narrative time changed from '|y{old_time}|n' to '|c{new_time}|n'.")
        
        # Announce to all online players
        from evennia.server.sessionhandler import SESSIONS
        message = f"|wTime Update:|n It is now |c{new_time}|n."
        for session in SESSIONS.get_sessions():
            if session.logged_in and session.get_puppet():
                session.msg(message) 