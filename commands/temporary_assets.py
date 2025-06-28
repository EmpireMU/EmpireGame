"""
Commands for managing temporary assets.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.command_mixins import CharacterLookupMixin

class CmdTemporaryAsset(CharacterLookupMixin, MuxCommand):
    """
    Add, remove, or list temporary assets.
    
    Usage:
        asset/add <name>=<die size>     - Add a temporary asset
        asset/remove <name>             - Remove a temporary asset
        asset                           - List your temporary assets
        asset/gmadd <character>/<name>=<die size>  - (Staff) Add asset to another character
        asset/gmrem <character>/<name>  - (Staff) Remove asset from another character
        
    Examples:
        asset/add High Ground=8         - Add "High Ground" as a d8 asset
        asset/remove High Ground        - Remove the "High Ground" asset
        asset                           - List all your temporary assets
        asset/gmadd John/Prepared=6     - Add "Prepared" d6 asset to John
        asset/gmrem John/Prepared       - Remove "Prepared" asset from John
        
    Temporary assets are short-term advantages that can be used in rolls.
    They are marked with (T) in roll outputs to distinguish them from
    permanent assets.
    
    The GM commands (gmadd/gmrem) require staff permissions and use the format
    character_name/asset_name.
    """
    
    key = "asset"
    aliases = ["assets"]
    locks = "cmd:all()"
    help_category = "Game"
    switch_options = ("add", "remove", "gmadd", "gmrem")
    
    def func(self):
        """Handle all temporary asset functionality based on switches."""
        # Handle GM commands first (require staff permissions)
        if "gmadd" in self.switches or "gmrem" in self.switches:
            if not self.caller.check_permstring("Builder"):
                self.caller.msg("You need staff permissions to use GM asset commands.")
                return
            
            if "gmadd" in self.switches:
                self._handle_gm_add()
            elif "gmrem" in self.switches:
                self._handle_gm_remove()
            return
        
        # Regular asset commands for self
        char = self.caller
        if not hasattr(char, 'temporary_assets'):
            char = char.char
            
        if not hasattr(char, 'temporary_assets'):
            self.caller.msg("You cannot use temporary assets.")
            return
            
        if not self.switches:  # No switch - list assets
            assets = char.temporary_assets.all()
            if not assets:
                self.caller.msg("You have no temporary assets.")
                return
                
            self.caller.msg("|wTemporary Assets:|n")
            for key in assets:
                asset = char.temporary_assets.get(key)
                self.caller.msg(f"  {asset.name}: d{int(asset.value)}")
                
        elif "add" in self.switches:
            if not self.args or "=" not in self.args:
                self.caller.msg("Usage: asset/add <name>=<die size>")
                return
                
            name, die_size = self.args.split("=", 1)
            name = name.strip()
            try:
                die_size = int(die_size.strip())
                if die_size not in [4, 6, 8, 10, 12]:
                    self.caller.msg("Die size must be 4, 6, 8, 10, or 12.")
                    return
            except ValueError:
                self.caller.msg("Die size must be a number (4, 6, 8, 10, or 12).")
                return
                
            # Add the asset with both value and base set
            char.temporary_assets.add(
                name.lower().replace(" ", "_"),
                value=die_size,
                base=die_size,  # Add base value
                name=name
            )
            
            self.caller.msg(f"Added temporary asset '{name}' (d{die_size}).")
            self.caller.location.msg_contents(
                f"{char.name} creates a temporary asset: {name} (d{die_size}).",
                exclude=[self.caller]
            )
            
        elif "remove" in self.switches:
            if not self.args:
                self.caller.msg("Usage: asset/remove <name>")
                return
                
            name = self.args.strip()
            key = name.lower().replace(" ", "_")
            
            # Check if asset exists
            asset = char.temporary_assets.get(key)
            if not asset:
                self.caller.msg(f"You don't have a temporary asset named '{name}'.")
                return
                
            # Remove the asset
            char.temporary_assets.remove(key)
            
            self.caller.msg(f"Removed temporary asset '{name}'.")
            self.caller.location.msg_contents(
                f"{char.name} removes their temporary asset: {name}.",
                exclude=[self.caller]
            )

    def _handle_gm_add(self):
        """Handle GM add command with character/asset format."""
        if not self.args or "/" not in self.args or "=" not in self.args:
            self.caller.msg("Usage: asset/gmadd <character>/<name>=<die size>")
            return
        
        # Parse character/asset format
        char_asset, die_size_str = self.args.split("=", 1)
        if "/" not in char_asset:
            self.caller.msg("Usage: asset/gmadd <character>/<name>=<die size>")
            return
            
        char_name, asset_name = char_asset.split("/", 1)
        char_name = char_name.strip()
        asset_name = asset_name.strip()
        
        # Find the target character
        target_char = self.find_character(char_name)
        if not target_char:
            return
            
        # Ensure character has temporary assets capability
        if not hasattr(target_char, 'temporary_assets'):
            if hasattr(target_char, 'char'):
                target_char = target_char.char
            else:
                self.caller.msg(f"{target_char.name} cannot use temporary assets.")
                return
        
        if not hasattr(target_char, 'temporary_assets'):
            self.caller.msg(f"{target_char.name} cannot use temporary assets.")
            return
        
        # Validate die size
        try:
            die_size = int(die_size_str.strip())
            if die_size not in [4, 6, 8, 10, 12]:
                self.caller.msg("Die size must be 4, 6, 8, 10, or 12.")
                return
        except ValueError:
            self.caller.msg("Die size must be a number (4, 6, 8, 10, or 12).")
            return
        
        # Add the asset
        target_char.temporary_assets.add(
            asset_name.lower().replace(" ", "_"),
            value=die_size,
            base=die_size,
            name=asset_name
        )
        
        # Notify staff member and target character
        self.caller.msg(f"Added temporary asset '{asset_name}' (d{die_size}) to {target_char.name}.")
        target_char.msg(f"A temporary asset '{asset_name}' (d{die_size}) has been added to your character by staff.")
        
        # Notify room if target is online and in a location
        if target_char.location:
            target_char.location.msg_contents(
                f"{target_char.name} gains a temporary asset: {asset_name} (d{die_size}).",
                exclude=[target_char]
            )

    def _handle_gm_remove(self):
        """Handle GM remove command with character/asset format."""
        if not self.args or "/" not in self.args:
            self.caller.msg("Usage: asset/gmrem <character>/<name>")
            return
        
        # Parse character/asset format
        char_name, asset_name = self.args.split("/", 1)
        char_name = char_name.strip()
        asset_name = asset_name.strip()
        
        # Find the target character
        target_char = self.find_character(char_name)
        if not target_char:
            return
            
        # Ensure character has temporary assets capability
        if not hasattr(target_char, 'temporary_assets'):
            if hasattr(target_char, 'char'):
                target_char = target_char.char
            else:
                self.caller.msg(f"{target_char.name} cannot use temporary assets.")
                return
        
        if not hasattr(target_char, 'temporary_assets'):
            self.caller.msg(f"{target_char.name} cannot use temporary assets.")
            return
        
        # Check if asset exists
        asset_key = asset_name.lower().replace(" ", "_")
        asset = target_char.temporary_assets.get(asset_key)
        if not asset:
            self.caller.msg(f"{target_char.name} doesn't have a temporary asset named '{asset_name}'.")
            return
        
        # Remove the asset
        target_char.temporary_assets.remove(asset_key)
        
        # Notify staff member and target character
        self.caller.msg(f"Removed temporary asset '{asset_name}' from {target_char.name}.")
        target_char.msg(f"Your temporary asset '{asset_name}' has been removed by staff.")
        
        # Notify room if target is online and in a location
        if target_char.location:
            target_char.location.msg_contents(
                f"{target_char.name} loses their temporary asset: {asset_name}.",
                exclude=[target_char]
            )

class TemporaryAssetCmdSet(CmdSet):
    """Command set for temporary asset management."""
    
    def at_cmdset_creation(self):
        """Add commands to the command set."""
        self.add(CmdTemporaryAsset()) 