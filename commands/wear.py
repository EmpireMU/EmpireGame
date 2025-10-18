"""
Commands for wearing and removing items.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet

from utils import worn_items as worn_utils


class CmdWear(MuxCommand):
    """
    Wear an item to show it off.
    
    Usage:
        wear <item>
        
    Example:
        wear red dress
    """
    
    key = "wear"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        if not self.args:
            self.caller.msg("Wear what?")
            return
        
        char = self.caller

        # Find the item in inventory
        item = char.search(self.args, location=char)
        if not item:
            return
        
        # Clean and fetch worn items
        current_worn = worn_utils.get_worn_items(char)

        # Check if already wearing it
        if any(worn.id == item.id for worn in current_worn):
            char.msg(f"You're already wearing {item.name}.")
            return
        
        # Wear it
        worn_utils.add_worn_item(char, item)

        char.msg(f"You wear {item.name}.")

        if getattr(char, "location", None):
            char.location.msg_contents(
                f"{char.name} wears {item.name}.",
                exclude=char
            )


class CmdRemove(MuxCommand):
    """
    Remove an item you're wearing.
    
    Usage:
        remove <item>
        
    Example:
        remove red dress
    """
    
    key = "remove"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        if not self.args:
            self.caller.msg("Remove what?")
            return
        
        char = self.caller

        # Clean and fetch worn items
        current_worn = worn_utils.get_worn_items(char)

        # Check if we have any worn items
        if not current_worn:
            char.msg("You're not wearing anything special.")
            return
        
        # Find the item in worn items
        item = None
        for worn in current_worn:
            if self.args.lower() in worn.name.lower():
                item = worn
                break
        
        if not item:
            char.msg(f"You're not wearing '{self.args}'.")
            return
        
        # Remove it
        worn_utils.remove_worn_item(char, item)

        char.msg(f"You remove {item.name}.")

        if getattr(char, "location", None):
            char.location.msg_contents(
                f"{char.name} removes {item.name}.",
                exclude=char
            )


class WearCmdSet(CmdSet):
    key = "wear_commands"
    
    def at_cmdset_creation(self):
        self.add(CmdWear())
        self.add(CmdRemove())


