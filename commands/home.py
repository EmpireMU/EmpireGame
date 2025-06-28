"""
Home-related commands.
"""
from evennia.commands.default.muxcommand import MuxCommand
from utils.command_mixins import CharacterLookupMixin


class CmdHome(CharacterLookupMixin, MuxCommand):
    """
    Set your home location or teleport to it.
    
    Usage:
        home        - Teleport to your home location
        home/here   - Set your current location as home
        home/clear  - Clear your home location
    """
    
    key = "home"
    locks = "cmd:all()"
    help_category = "Travel"
    
    def func(self):
        """Execute command."""
        if not self.switches:
            # Teleport to home
            if not self.caller.home_location:
                self.msg("You haven't set a home location yet.")
                return
                
            if not self.caller.home_location.access(self.caller, "view"):
                self.msg("Your home location no longer exists.")
                self.caller.home_location = None
                return
                
            # Move to home location with proper messaging
            source_location = self.caller.location
            if source_location:
                source_location.msg_contents(f"{self.caller.name} returns home.", exclude=[self.caller])
                
            if self.caller.move_to(self.caller.home_location):
                self.caller.msg(f"You return to your home in {self.caller.home_location.name}.")
                self.caller.home_location.msg_contents(
                    f"{self.caller.name} arrives home.",
                    exclude=[self.caller]
                )
            else:
                self.caller.msg("Something prevented you from returning home.")
            return
            
        switch = self.switches[0]
        
        if switch == "here":
            # Set current location as home
            room = self.caller.location
            if not room:
                self.msg("You can't set this as your home.")
                return
                
            if not self.caller.can_set_home(room):
                self.msg("You must own or have a key to this room to set it as your home.")
                return
                
            old_home = self.caller.home_location
            self.caller.home_location = room
            self.msg(f"You set {room.name} as your home.")
            if old_home:
                self.msg(f"(Previously: {old_home.name})")
                
        elif switch == "clear":
            # Clear home location
            if not self.caller.home_location:
                self.msg("You haven't set a home location.")
                return
                
            old_home = self.caller.home_location
            self.caller.home_location = None
            self.msg(f"Cleared your home location. (Previously: {old_home.name})")
            
        else:
            self.msg("Usage: home, home/here, or home/clear") 