"""
Staff commands for editing character sheets.
"""
from evennia.commands.command import Command
from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet, create_object
from evennia.utils import dbserialize
from evennia.utils import evtable
from evennia.utils.search import search_object
from utils.command_mixins import CharacterLookupMixin, TraitCommand

UNDELETABLE_TRAITS = ["attributes", "skills"]

class CmdSetTrait(CharacterLookupMixin, MuxCommand):
    """
    Set a trait on a character sheet.

    Usage:
      settrait <character> = <category> "<trait name>" d<size> [description]

    Categories:
      attributes   - Core attributes (d4-d12, default d6)
        Represent innate capabilities. No custom descriptions allowed.
      skills       - Skills (d4-d12, default d4)
        Represent learned abilities. No custom descriptions allowed.
      signature_assets - Signature assets (d4-d12)
        Represent important items or companions. Custom descriptions allowed.
      powers      - Powers (d4-d12)
        Represent supernatural abilities. Custom descriptions allowed.

    Die Sizes:
      d4  - Untrained/Weak
      d6  - Average/Basic Training
      d8  - Professional/Well Trained
      d10 - Expert/Exceptional
      d12 - Master/Peak Human

    Examples:
      settrait Tom = attributes strength d8
        Sets Tom's Strength attribute to d8
      settrait Tom = skills fighting d6
        Sets Tom's Fighting skill to d6
      settrait Tom = signature_assets "Magic Sword" d8 "Family heirloom blade"
        Creates a d8 Signature Asset with description
      settrait Tom = powers "Divine Blessing" d10 "Blessed by the gods"
        Creates a d10 Power with description

    Notes:
    - Setting a trait that already exists will overwrite it
    - Descriptions not allowed for attributes and skills (standardized traits)
    - For signature_assets and powers, enclose multi-word names in quotes
    """
    key = "settrait"
    help_category = "Character"
    locks = "cmd:perm(Admin)"

    def func(self):
        """Execute the command."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: settrait <character> = <category> \"<trait name>\" d<size> [description]")
            return

        # Split into character and trait parts
        char_name, trait_part = [part.strip() for part in self.args.split("=", 1)]
        
        # Find the character using inherited method
        char = self.find_character(char_name)
        if not char:
            return

        # Parse trait information - handle quoted trait names
        import shlex
        try:
            parts = shlex.split(trait_part)
        except ValueError as e:
            self.msg("Error parsing command. Make sure to close all quotes.")
            return

        if len(parts) < 3:
            self.msg("Usage: settrait <character> = <category> \"<trait name>\" d<size> [description]")
            return

        category = parts[0].lower()
        if category not in ['attributes', 'skills', 'signature_assets', 'powers']:
            self.msg("Invalid category. Must be one of: attributes, skills, signature_assets, powers")
            return

        name = parts[1]
        die_size = parts[2]
        description = " ".join(parts[3:]) if len(parts) > 3 else ""

        # Check if description provided for attributes/skills (not allowed)
        if category in ['attributes', 'skills'] and description:
            self.msg(f"Descriptions are not allowed for {category}. These are standardized traits.")
            return

        # Validate die size
        if not die_size.startswith('d') or not die_size[1:].isdigit():
            self.msg("Die size must be in the format dN where N is a number (e.g., d4, d6, d8, d10, d12)")
            return

        die_size = int(die_size[1:])
        if die_size not in [4, 6, 8, 10, 12]:
            self.msg("Die size must be one of: d4, d6, d8, d10, d12")
            return

        # Convert spaces to underscores for the key
        key = name.lower().replace(' ', '_')

        # Set the trait (only add description for signature_assets and powers)
        if category == 'attributes':
            char.character_attributes.add(key, name, trait_type="static", base=die_size)
        elif category == 'skills':
            char.skills.add(key, name, trait_type="static", base=die_size)
        elif category == 'signature_assets':
            char.signature_assets.add(key, name, trait_type="static", base=die_size, desc=description)
        elif category == 'powers':
            char.powers.add(key, name, trait_type="static", base=die_size, desc=description)

        self.msg(f"Set {name} to d{die_size} for {char.name}")

class CmdDeleteTrait(CharacterLookupMixin, MuxCommand):
    """Delete a trait from a character.
    
    Usage:
        deletetrait <character> = <category> "<trait name>"
        
    Categories:
        attributes - Core attributes
        skills - Learned abilities
        signature_assets - Important items/companions
        powers - Supernatural or extraordinary abilities
        
    Examples:
        deletetrait Bob = attributes strength
        deletetrait Jane = skills fighting
        deletetrait Tom = signature_assets "Magic Sword"
        deletetrait Jane = powers "Divine Blessing"
        
    Notes:
    - For signature_assets and powers, enclose multi-word names in quotes
    """
    key = "deletetrait"
    locks = "cmd:perm(Admin)"
    help_category = "Character"

    def func(self):
        """Execute the command."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: deletetrait <character> = <category> \"<trait name>\"")
            return

        char_name, rest = [part.strip() for part in self.args.split("=", 1)]
        
        # Find the character using inherited method
        char = self.find_character(char_name)
        if not char:
            return

        # Parse category and trait name - handle quoted trait names
        import shlex
        try:
            parts = shlex.split(rest)
        except ValueError as e:
            self.msg("Error parsing command. Make sure to close all quotes.")
            return
            
        if len(parts) < 2:
            self.msg("You must specify both a category and a trait name.")
            return
            
        category = parts[0].lower()
        trait_name = parts[1].lower().replace(' ', '_')  # Convert spaces to underscores for lookup
          
        # Get the appropriate trait handler
        if category == 'attributes':
            handler = char.character_attributes
        elif category == 'skills':
            handler = char.skills
        elif category == 'signature_assets':
            handler = char.signature_assets
        elif category == 'powers':
            handler = char.powers
        else:
            self.msg("Invalid category. Must be one of: attributes, skills, signature_assets, powers")
            return

        # Check if trait exists
        trait = handler.get(trait_name)
        if not trait:
            self.msg(f"Trait '{parts[1]}' not found in category '{category}'.")
            return

        # Check if trait can be deleted
        if category in UNDELETABLE_TRAITS:
            self.msg(f"Cannot delete traits from the {category} category.")
            return

        # Delete the trait
        handler.remove(trait_name)
        self.msg(f"Deleted trait '{parts[1]}' from {char.name}'s {category}.")

class CmdSetDistinction(CharacterLookupMixin, MuxCommand):
    """
    Set a distinction on a character.
    
    Usage:
        setdist <character> = <slot> : <n> : <description>
        
          Notes:
    - All distinctions are d8 (can be used as d4 to gain a plot point)
    """
    
    key = "setdist"
    locks = "cmd:perm(Builder)"  # Builders and above can use this
    help_category = "Building"
    
    def func(self):
        """Handle setting the distinction."""
        if not self.args or ":" not in self.args or "=" not in self.args:
            self.msg("Usage: setdist <character> = <slot> : <n> : <description>")
            return
            
        char_name, rest = self.args.split("=", 1)
        char_name = char_name.strip()
        
        try:
            slot, name, desc = [part.strip() for part in rest.split(":", 2)]
        except ValueError:
            self.msg("Usage: setdist <character> = <slot> : <n> : <description>")
            return
            
        # Find the character using inherited method
        char = self.find_character(char_name)
        if not char:
            return
            
        # Verify character has distinctions
        if not hasattr(char, 'distinctions'):
            self.msg(f"{char.name} does not have distinctions.")
            return
            
        # Validate slot
        valid_slots = ["concept", "culture", "vocation"]
        if slot not in valid_slots:
            self.msg(f"Invalid slot. Must be one of: {', '.join(valid_slots)}")
            return
            
        # Set the distinction (all distinctions are d8)
        char.distinctions.add(slot, name, trait_type="static", base=8, desc=desc)
        self.msg(f"Set {char.name}'s {slot} distinction to '{name}' (d8)")

class CmdBiography(CharacterLookupMixin, MuxCommand):
    """
    View or edit a character's biography information.
    
    Usage:
        biography [<character>]                    - View full biography
        biography/description <char> = <text>      - Set description
        biography/background <char> = <text>       - Set background
        biography/personality <char> = <text>      - Set personality
        biography/age <char> = <age>              - Set age
        biography/birthday <char> = <date>        - Set birthday
        biography/gender <char> = <gender>        - Set gender
        biography/name <char> = <full name>       - Set full name
        biography/notable <char> = <text>         - Set notable traits
        biography/realm <char> = <realm>          - Set realm
        biography/secret <char> = <text>          - Set secret information
        
    Examples:
        biography                    - View your own biography
        biography Ada               - View Ada's biography
        biography/description Ada = A tall woman with piercing blue eyes...
        biography/background Ada = Born in the mountains...
        biography/personality Ada = Friendly and outgoing...
        biography/age Ada = 30
        biography/birthday Ada = December 25th
        biography/gender Ada = Female
        biography/name Ada = Ada the Adventurer
        biography/notable Ada = The best explorer ever.
        biography/realm Ada = Imperial Territories
        biography/secret Ada = Has trust issues due to past betrayal
        
            Shows:
        - Description (set with 'desc' command or biography/description)
        - Age (set with biography/age)
        - Birthday (set with biography/birthday)
        - Gender (set with biography/gender)
        - Realm (set with biography/realm)
        - Background (set with biography/background)
        - Personality (set with biography/personality)
        - Distinctions (set with 'setdist' command):
          * Character Concept
          * Culture
          * Vocation
        - Notable Traits (set with biography/notable)
        - Secret Information (set with biography/secret) - visible only to character owner and staff
        
    Note: When editing description, background, personality, notable traits,
    or special effects, the old value will be displayed before making changes.
    """
    
    key = "biography"
    locks = "cmd:all();edit:perm(Builder)"  # Everyone can view, builders can edit
    help_category = "Character"
    
    def func(self):
        """Execute the command."""
        # Handle switches
        if self.switches:
            if not self.access(self.caller, "edit"):
                self.msg("You don't have permission to edit biographies.")
                return
                
            if not self.args or "=" not in self.args:
                self.msg(f"Usage: biography/{self.switches[0]} <character> = <value>")
                return
                
            try:
                switch = self.switches[0].lower()
                char_name, value = self.args.split("=", 1)
                char = self.find_character(char_name.strip())
                if not char:
                    return
                    
                value = value.strip()
                
                # Map switches to attributes
                switch_map = {
                    "background": "background",
                    "personality": "personality",
                    "age": "age",
                    "birthday": "birthday",
                    "gender": "gender",
                    "name": "full_name",
                    "notable": "notable_traits",
                    "realm": "realm",
                    "description": "desc",  # Special case for description
                    "secret": "secret_information"
                }
                
                if switch not in switch_map:
                    self.msg(f"Invalid switch. Use one of: {', '.join(switch_map.keys())}")
                    return
                
                # Get the old value before changing it
                if switch == "description":
                    # For description, use the character's desc attribute
                    old_value = getattr(char.db, "desc", "")
                    if not old_value:
                        old_value = "(not set)"
                else:
                    # For other attributes, check the db attributes
                    old_value = getattr(char.db, switch_map[switch], "")
                    if not old_value:
                        old_value = "(not set)"
                
                # Show old value to the user making the change
                if old_value != "(not set)":
                    self.msg(f"|w{char.name}'s old {switch}:|n\n{old_value}")
                    self.msg("|w" + "="*50 + "|n")
                else:
                    self.msg(f"|w{char.name}'s {switch} was not previously set.|n")
                
                # Update the appropriate attribute
                if switch == "description":
                    # For description, set the desc attribute directly
                    char.db.desc = value
                else:
                    setattr(char.db, switch_map[switch], value)
                
                self.msg(f"Updated {char.name}'s {switch}.")
                char.msg(f"{self.caller.name} updated your {switch}.")
                
            except Exception as e:
                self.msg(f"Error updating {switch}: {e}")
            return
            
        # If no switches, show biography
        if not self.args:
            self.show_biography(self.caller)
            return
            
        # View command
        char = self.find_character(self.args)
        if not char:
            return
        self.show_biography(char)
            
    def show_biography(self, char):
        """Show a character's biography."""
        # Get the character's description using Evennia's built-in method
        desc = char.get_display_desc(self.caller)
        
        # Build the biography message
        msg = f"\n|w{char.name}'s Biography|n"
        
        # Add full name if it exists
        if char.db.full_name:
            msg += f"\n|wFull Name:|n {char.db.full_name}"
        
        # Add character concept first if it exists
        if hasattr(char, 'distinctions'):
            concept = char.distinctions.get("concept")
            if concept:
                msg += f"\n|wConcept:|n {concept.name}"
            else:
                msg += "\n|wConcept:|n Not set"
        
        # Add demographic information on one line
        msg += "\n"
        demographics = []
        if char.db.gender:
            demographics.append(f"|wGender:|n {char.db.gender}")
        if char.db.age:
            demographics.append(f"|wAge:|n {char.db.age}")
        if char.db.birthday:
            demographics.append(f"|wBirthday:|n {char.db.birthday}")
        if char.db.realm:
            demographics.append(f"|wRealm:|n {char.db.realm}")
        msg += " | ".join(demographics) if demographics else "|wNo demographics set|n"
        
        # Add culture and vocation on one line if they exist
        if hasattr(char, 'distinctions'):
            culture = char.distinctions.get("culture")
            vocation = char.distinctions.get("vocation")
            culture_text = f"|wCulture:|n {culture.name}" if culture else "|wCulture:|n Not set"
            vocation_text = f"|wVocation:|n {vocation.name}" if vocation else "|wVocation:|n Not set"
            msg += f"\n{culture_text} | {vocation_text}"
        
        # Add main character information
        msg += f"\n\n|wDescription:|n\n{desc}"
        msg += f"\n\n|wBackground:|n\n{char.db.background}"
        msg += f"\n\n|wPersonality:|n\n{char.db.personality}"
        
        # Add organization memberships
        orgs = char.organisations
        if orgs:
            msg += "\n\n|wOrganizations:|n"
            table = evtable.EvTable(
                "|wOrganization|n",
                "|wRank|n",
                border="table",
                width=78
            )
            
            # Add each organization and rank
            for org_id, rank in orgs.items():
                # Search for organization using its ID
                orgs_found = search_object(f"#{org_id}")
                if orgs_found:
                    org = orgs_found[0]
                    rank_name = org.get_member_rank_name(char)
                    table.add_row(org.name, rank_name)
            
            msg += f"\n{str(table)}"
        
        # Add notable traits if they exist
        if char.db.notable_traits:
            msg += f"\n\n|wNotable Traits:|n\n{char.db.notable_traits}"
        
        # Add secret information if viewer has permission (character owner or staff)
        can_see_secret = (self.caller == char or 
                         self.caller.locks.check_lockstring(self.caller, "edit:perm(Builder)"))
        if can_see_secret and char.db.secret_information:
            msg += f"\n\n|wSecret Information:|n\n{char.db.secret_information}"
        
        self.msg(msg)

class CmdSetSpecialEffects(CharacterLookupMixin, MuxCommand):
    """
    Set special effects for a character.
    
    Usage:
        setsfx <character> = <special effects text>
        setsfx <character> =    (clears special effects)
        
    Sets the special effects text for a character. This is a pure text
    field with no dice associated. Only staff can use this command.
    
    Examples:
        setsfx Alice = Has a magical aura that glows softly in darkness
        setsfx Bob = Leaves frost footprints when walking
        setsfx Charlie =    (clears Alice's special effects)
        
    The special effects will appear at the bottom of the character sheet
    and in the web view.
    """
    
    key = "setsfx"
    aliases = ["specialeffects"]
    locks = "cmd:perm(Builder)"
    help_category = "Character"
    
    def func(self):
        """Execute the command."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: setsfx <character> = <special effects text>")
            return
            
        # Split into character and effects parts
        char_name, effects_text = [part.strip() for part in self.args.split("=", 1)]
        
        # Find the character using inherited method
        char = self.find_character(char_name)
        if not char:
            return
            
        # Get the old value before changing it
        old_value = getattr(char.db, "special_effects", "")
        if not old_value:
            old_value = "(not set)"
        
        # Show old value to the user making the change
        if old_value != "(not set)":
            self.msg(f"|w{char.name}'s old special effects:|n\n{old_value}")
            self.msg("|w" + "="*50 + "|n")
        else:
            self.msg(f"|w{char.name}'s special effects were not previously set.|n")
            
        # Set the special effects (empty string if no text provided)
        char.db.special_effects = effects_text
        
        if effects_text:
            self.msg(f"Set special effects for {char.name}:\n{effects_text}")
            # Notify the character if they're online
            if char.has_account:
                char.msg(f"{self.caller.name} set your special effects: {effects_text}")
        else:
            self.msg(f"Cleared special effects for {char.name}.")
            # Notify the character if they're online
            if char.has_account:
                char.msg(f"{self.caller.name} cleared your special effects.")

class CharSheetEditorCmdSet(CmdSet):
    """
    Command set for editing character sheets.
    """
    
    def at_cmdset_creation(self):
        """
        Add commands to the command set
        """
        self.add(CmdSetTrait())
        self.add(CmdDeleteTrait())
        self.add(CmdSetDistinction())
        self.add(CmdBiography())
        self.add(CmdSetSpecialEffects())