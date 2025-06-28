"""
Administrative commands for managing character sheets.
These commands are for staff use only and should not be used in normal gameplay.
"""
from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.character_setup import initialize_traits
from utils.command_mixins import CharacterLookupMixin

class CmdInitTraits(CharacterLookupMixin, MuxCommand):
    """
    Initialize missing traits on a character.
    
    Usage:
        inittraits <character>  - Initialize one character
        inittraits/all         - Initialize all characters
        
    Examples:
        inittraits Bob     - Initialize Bob's traits
        inittraits/all     - Initialize all characters' traits
        
    Default Trait Setup:
    1. Plot Points
       - Starts at 1
       - Used for special actions and dice manipulation
    
    2. Attributes (all start at d6)
       - Prowess: Strength, endurance and ability to fight
       - Finesse: Dexterity and agility
       - Leadership: Capacity as a leader
       - Social: Charisma and social navigation
       - Acuity: Perception and information processing
       - Erudition: Learning and recall ability
    
    3. Skills (all start at d4)
       - Administration: Organizing affairs of large groups
       - Arcana: Knowledge of magic
       - Athletics: General physical feats
       - Dexterity: Precision physical feats
       - Diplomacy: Protocol and high politics
       - Direction: Leading in non-combat
       - Exploration: Wilderness and ruins
       - Fighting: Melee combat
       - Influence: Personal persuasion
       - Learning: Education and research
       - Making: Crafting and building
       - Medicine: Healing and medical knowledge
       - Perception: Awareness and searching
       - Performance: Entertainment arts
       - Presentation: Style and bearing
       - Rhetoric: Public speaking
       - Seafaring: Sailing and navigation
       - Shooting: Ranged combat
       - Warfare: Military leadership and strategy
    
    4. Distinction Slots (all d8)
       - Character Concept: Core character concept
       - Culture: Character's cultural origin
       - Vocation: Professional role or calling
    
    Important Notes:
    - This command ONLY adds missing traits with default values
    - Existing traits are NOT modified
    - Custom traits and values are preserved
    - To reset all traits to defaults, use 'wipetraits' instead
    
    Troubleshooting:
    - If traits appear missing, check character typeclass
    - If values seem wrong, verify trait handlers are initialized
    - For complete reset, use 'wipetraits'
    - Contact admin if persistent initialization issues occur
    
    Only administrators can use this command.
    """
    
    key = "inittraits"
    locks = "cmd:perm(Admin)"  # Admin and above can use this
    help_category = "Building"
    switch_options = ("all",)
    
    def func(self):
        """Handle trait initialization."""
        if "all" in self.switches:
            # Initialize all characters
            from evennia.objects.models import ObjectDB
            from typeclasses.characters import Character
            chars = ObjectDB.objects.filter(db_typeclass_path__contains="characters.Character")
            count = 0
            for char in chars:
                if hasattr(char, 'traits'):  # Verify it's actually a character
                    success, msg = initialize_traits(char)
                    if success:
                        count += 1
                        self.caller.msg(f"{char.name}: {msg}")
            self.caller.msg(f"\nInitialized traits for {count} character{'s' if count != 1 else ''}.")
            return
              # Initialize specific character
        if not self.args:
            self.caller.msg("Usage: inittraits <character> or inittraits/all")
            return
            
        char = self.find_character(self.args)
        if not char:
            return
            
        if not hasattr(char, 'traits'):
            self.caller.msg(f"{char.name} does not support traits (wrong typeclass?).")
            return
            
        # Check if this is a confirmation
        confirming = self.caller.db.init_traits_confirming
        
        if confirming:
            success, msg = initialize_traits(char)
            self.caller.msg(msg)
            del self.caller.db.init_traits_confirming
            return
            
        # First time through - ask for confirmation
        self.caller.msg(f"|yWARNING: This will initialize traits for {char.name}.|n")
        self.caller.msg("|yThis may affect existing traits. Type 'inittraits' again to confirm.|n")
        self.caller.db.init_traits_confirming = True
        return  # Add this to prevent the command from continuing

class CmdWipeTraits(CharacterLookupMixin, MuxCommand):
    """
    Wipe and reinitialize a character's traits.
    
    Usage:
        wipetraits <character>
        wipetraits/all
        
    Examples:
        wipetraits Bob     - Wipe and reinitialize Bob's traits
        wipetraits/all     - Wipe and reinitialize all characters' traits
        
    This will:
    1. Remove all existing traits
    2. Reinitialize with default traits:
       - Plot Points (starts at 1)
       - Attributes (all start at d6)
       - Skills (all start at d4)
       - Distinction slots (all d8)
    
    Only administrators can use this command.
    """
    
    key = "wipetraits"
    locks = "cmd:perm(Admin)"  # Admin and above can use this
    help_category = "Building"
    switch_options = ("all",)  # Define valid switches
    
    def func(self):
        """Handle trait wiping and reinitialization."""
        if "all" in self.switches:
            # Wipe all characters
            from evennia.objects.models import ObjectDB
            from typeclasses.characters import Character
            chars = ObjectDB.objects.filter(db_typeclass_path__contains="characters.Character")
            count = 0
            for char in chars:
                if hasattr(char, 'traits'):  # Verify it's actually a character
                    success, msg = self._wipe_and_init(char)
                    if success:
                        count += 1
                        self.caller.msg(f"{char.name}: {msg}")
            self.caller.msg(f"\nWiped and reinitialized traits for {count} character{'s' if count != 1 else ''}.")
            return
              # Wipe specific character
        if not self.args:
            self.caller.msg("Usage: wipetraits <character> or wipetraits/all")
            return
            
        char = self.find_character(self.args)
        if not char:
            return
            
        if not hasattr(char, 'traits'):
            self.caller.msg(f"{char.name} does not support traits (wrong typeclass?).")
            return
            
        success, msg = self._wipe_and_init(char)
        self.caller.msg(msg)
        
    def _wipe_and_init(self, char):
        """Helper method to wipe and reinitialize traits for a character."""
        try:
            # Ensure trait handlers are initialized
            _ = char.traits
            _ = char.distinctions
            _ = char.character_attributes
            _ = char.skills
            _ = char.signature_assets
            _ = char.powers
            
            # Wipe all traits
            for handler_name in ['traits', 'distinctions', 'character_attributes', 'skills', 'signature_assets', 'powers']:
                handler = getattr(char, handler_name, None)
                if handler:
                    # Get all trait keys and remove them
                    for key in handler.all():
                        handler.remove(key)
            
            # Force reinitialize traits
            success, msg = initialize_traits(char, force=True)
            if success:
                return True, "Traits wiped and reinitialized"
            return False, msg
            
        except Exception as e:
            return False, f"Error: {e}"

class CharSheetAdminCmdSet(CmdSet):
    """
    Command set for administrative character sheet management.
    """
    
    def at_cmdset_creation(self):
        """
        Add commands to the command set
        """
        self.add(CmdInitTraits())
        self.add(CmdWipeTraits()) 