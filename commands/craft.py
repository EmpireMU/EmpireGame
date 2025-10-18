"""
Simple player item creation command.
"""

from datetime import datetime

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet, create_object

from typeclasses.player_items import PlayerItem
from utils import worn_items as worn_utils


DAILY_ITEM_LIMIT = 5


class CmdCraft(MuxCommand):
    """
    Create a decorative item.
    
    Usage:
        craft <name>=<description>
        craft/destroy <item>
        
    Examples:
        craft wooden chair=A sturdy oak chair
        craft/destroy chair
        
    You can create up to 5 items per day.
    """
    
    key = "craft"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        char = self.caller
        
        # Destroy an item
        if "destroy" in self.switches:
            if not self.args:
                char.msg("Usage: craft/destroy <item>")
                return
                
            item = char.search(self.args)
            if not item:
                return
                
            if not item.db.creator == char:
                char.msg("You can only destroy items you created.")
                return
                
            # Ensure the item is no longer tracked as worn
            worn_utils.remove_worn_item(char, item)

            item.delete()
            char.msg(f"You destroy {item.name}.")
            return
        
        # Create an item
        if not self.rhs:
            char.msg("Usage: craft <name>=<description>")
            return
        
        # Check daily limit using a simple counter on the character
        today = datetime.now().date()
        last_craft_date = char.db.last_craft_date
        craft_count = char.db.craft_count_today or 0
        
        # Reset counter if it's a new day
        if not last_craft_date or last_craft_date < today:
            craft_count = 0
        
        if craft_count >= DAILY_ITEM_LIMIT:
            char.msg(f"You've reached your daily limit of {DAILY_ITEM_LIMIT} items. Try again tomorrow.")
            return
        
        # Create the item
        item = create_object(
            PlayerItem,
            key=self.lhs.strip(),
            location=char.location
        )
        item.db.desc = self.rhs.strip()
        item.db.creator = char
        item.db.date_created = datetime.now()
        
        # Update character's craft counter
        char.db.craft_count_today = craft_count + 1
        char.db.last_craft_date = today
        
        char.msg(f"You craft {item.name}.")


class CraftCmdSet(CmdSet):
    key = "craft_commands"
    
    def at_cmdset_creation(self):
        self.add(CmdCraft())
