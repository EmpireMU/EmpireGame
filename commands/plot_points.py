"""
Commands for managing Cortex Prime plot points.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.command_mixins import CharacterLookupMixin

class CmdPlotPoints(CharacterLookupMixin, MuxCommand):
    """
    Check and manage plot points.
    
    Usage:
        pp [character]              - Check plot points
        pp/give <character>         - Give a plot point to someone (staff only)
        pp/spend [reason]           - Spend a plot point, optionally noting what for
        pp/set <character>=<amount> - Set someone's plot points (staff only)
        pp/room <amount>            - Set plot points for everyone in room (staff only)
        
    Examples:
        pp                  - Check your plot points
        pp Bob             - Check Bob's plot points (staff only)
        pp/give Bob        - Give Bob a plot point
        pp/spend           - Spend a plot point
        pp/spend for extra die - Spend a plot point, noting what it's for
        pp/set Bob=3       - Set Bob's plot points to 3
        pp/room 2          - Set everyone's plot points to 2
    """
    
    key = "pp"
    aliases = ["plotpoints"]
    locks = "cmd:all();give:perm(Builder);set:perm(Builder);room:perm(Builder);view_other:perm(Builder)"
    help_category = "Game"
    switch_options = ("give", "spend", "set", "room")
    
    def func(self):
        """Handle all plot point functionality based on switches."""
        if not self.switches:  # No switch - check points
            self._check_points()
        elif "give" in self.switches:
            if not self.access(self.caller, "give"):
                self.caller.msg("You don't have permission to give plot points.")
                return
            self._give_points()
        elif "spend" in self.switches:
            self._spend_points()
        elif "set" in self.switches:
            if not self.access(self.caller, "set"):
                self.caller.msg("You don't have permission to set plot points.")
                return
            self._set_points()
        elif "room" in self.switches:
            if not self.access(self.caller, "room"):
                self.caller.msg("You don't have permission to set room plot points.")
                return
            self._set_room_points()
            
    def _check_points(self):
        """Check plot points for self or another character."""
        if not self.args:
            # Check own plot points
            char = self.caller
            if not hasattr(char, 'traits'):
                char = char.char
        else:
            # Staff checking other character
            if not self.access(self.caller, "view_other"):
                self.caller.msg("You can only check your own plot points.")
                return
            char = self.find_character(self.args)
            if not char:
                return
                
        if not hasattr(char, 'traits'):
            self.caller.msg(f"{char.name} does not have any plot points.")
            return
            
        try:
            pp_trait = char.traits.get("plot_points")
            if not pp_trait:
                self.caller.msg(f"{char.name} does not have any plot points.")
                return
                
            current = int(float(pp_trait.value))
            self.caller.msg(f"{char.name} has {current} plot point{'s' if current != 1 else ''}.")
            
        except Exception as e:
            self.caller.msg(f"Error checking plot points: {e}")
            
    def _give_points(self):
        """Give a plot point to someone."""
        if not self.args:
            self.caller.msg("Usage: pp/give <character>")
            return
            
        char = self.find_character(self.args.strip())
        if not char:
            return
            
        if not hasattr(char, 'traits'):
            self.caller.msg(f"{char.name} does not have trait support.")
            return
            
        try:
            pp_trait = char.traits.get("plot_points")
            if not pp_trait:
                self.caller.msg(f"{char.name} does not have a plot points trait.")
                return
                
            current = int(float(pp_trait.value))
            
            # Remove and re-add with new value
            char.traits.remove("plot_points")
            char.traits.add("plot_points", value=current + 1, base=current + 1, min=0)
            
            self.caller.msg(f"You give a plot point to {char.name}.")
            char.msg(f"{self.caller.name} gives you a plot point.")
            
        except Exception as e:
            self.caller.msg(f"Error giving plot point: {e}")
            
    def _spend_points(self):
        """Spend a plot point."""
        char = self.caller
        if not hasattr(char, 'traits'):
            char = char.char
            
        if not hasattr(char, 'traits'):
            self.caller.msg("You don't have any plot points to spend.")
            return
            
        try:
            pp_trait = char.traits.get("plot_points")
            if not pp_trait:
                self.caller.msg("You don't have any plot points to spend.")
                return
                
            current = int(float(pp_trait.value))
            if current < 1:
                self.caller.msg("You don't have any plot points to spend.")
                return
                
            # Remove and re-add with new value
            char.traits.remove("plot_points")
            char.traits.add("plot_points", value=current - 1, base=current - 1, min=0)
            
            reason = f" {self.args}" if self.args.strip() else ""
            self.caller.msg(f"You spend a plot point{reason}. ({current-1} remaining)")
            self.caller.location.msg_contents(
                f"{char.name} spends a plot point{reason}.",
                exclude=[self.caller]
            )
            
        except Exception as e:
            self.caller.msg(f"Error spending plot point: {e}")
            
    def _set_points(self):
        """Set a character's plot points to a specific value."""
        if not self.args or not self.rhs:
            self.caller.msg("Usage: pp/set <character>=<amount>")
            return
            
        char = self.find_character(self.lhs)
        if not char:
            return
            
        try:
            amount = int(self.rhs)
            if amount < 0:
                self.caller.msg("Plot points cannot be negative.")
                return
        except ValueError:
            self.caller.msg("Plot point amount must be a number.")
            return
            
        if not hasattr(char, 'traits'):
            self.caller.msg(f"{char.name} does not have trait support.")
            return
            
        try:
            pp_trait = char.traits.get("plot_points")
            if not pp_trait:
                self.caller.msg(f"{char.name} does not have a plot points trait.")
                return
                
            # Remove and re-add with new value
            char.traits.remove("plot_points")
            char.traits.add("plot_points", value=amount, base=amount, min=0)
            
            self.caller.msg(f"Set {char.name}'s plot points to {amount}.")
            if char != self.caller:
                char.msg(f"{self.caller.name} sets your plot points to {amount}.")
            
        except Exception as e:
            self.caller.msg(f"Error setting plot points: {e}")
            
    def _set_room_points(self):
        """Set plot points for all characters in the room."""
        if not self.args:
            self.caller.msg("Usage: pp/room <amount>")
            return
            
        try:
            amount = int(self.args.strip())
            if amount < 0:
                self.caller.msg("Plot points cannot be negative.")
                return
        except ValueError:
            self.caller.msg("Amount must be a number.")
            return
            
        chars = [obj for obj in self.caller.location.contents if hasattr(obj, 'traits')]
        success_count = 0
        
        for char in chars:
            try:
                if not hasattr(char, 'traits'):
                    continue
                    
                pp_trait = char.traits.get("plot_points")
                if not pp_trait:
                    continue
                    
                char.traits.add("plot_points", value=amount)
                success_count += 1
                
                if char != self.caller:
                    char.msg(f"{self.caller.name} sets your plot points to {amount}.")
                
            except Exception as e:
                self.caller.msg(f"Error setting plot points for {char.name}: {e}")
                
        self.caller.msg(f"Set plot points to {amount} for {success_count} character{'s' if success_count != 1 else ''}.")

class PlotPointCmdSet(CmdSet):
    """Command set for plot point management."""
    
    def at_cmdset_creation(self):
        """Add commands to the command set."""
        self.add(CmdPlotPoints()) 