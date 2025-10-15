"""
Commands for wearing and removing items.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet


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
        worn_items = char.get_worn_items() if hasattr(char, "get_worn_items") else list(char.db.worn_items or [])

        def _item_id(obj):
            return getattr(obj, "id", getattr(obj, "pk", obj))

        # Check if already wearing it
        if any(_item_id(worn_item) == item.id for worn_item in worn_items):
            char.msg(f"You're already wearing {item.name}.")
            return
        
        # Wear it
        if hasattr(char, "add_worn_item"):
            char.add_worn_item(item)
        else:
            updated = list(worn_items)
            updated.append(item.id)
            char.db.worn_items = updated

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
    
    def func(self):
        if not self.args:
            self.caller.msg("Remove what?")
            return
        
        char = self.caller

        # Clean and fetch worn items
        worn_items = char.get_worn_items() if hasattr(char, "get_worn_items") else list(char.db.worn_items or [])

        def _item_id(obj):
            return getattr(obj, "id", getattr(obj, "pk", obj))

        # Check if we have any worn items
        if not worn_items:
            char.msg("You're not wearing anything special.")
            return
        
        # Find the item in worn items
        item = None
        for worn in worn_items:
            if self.args.lower() in worn.name.lower():
                item = worn
                break
        
        if not item:
            char.msg(f"You're not wearing '{self.args}'.")
            return
        
        # Remove it
        if hasattr(char, "remove_worn_item"):
            char.remove_worn_item(item)
        else:
            updated = [w for w in worn_items if _item_id(w) != item.id]
            char.db.worn_items = updated

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


