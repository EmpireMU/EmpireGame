"""
Character sheet commands for viewing and editing character information.
"""

from evennia import Command, CmdSet
from evennia.utils import evtable
from evennia.utils.search import search_object
from utils.command_mixins import CharacterLookupMixin

def get_trait_display(trait):
    """
    Get display information for a trait.
    
    Args:
        trait: The trait object to display
        
    Returns:
        Tuple of (display_name, die_size, description)
    """
    if not trait:
        return "", "", ""
        
    # Get the display name, falling back to key if name not set
    try:
        display_name = trait.name
    except AttributeError:
        display_name = trait.key
    
    # Get the die size from the value
    die_size = f"d{int(trait.value)}" if hasattr(trait, 'value') else ""
    
    # Get the description, falling back to empty string if not set
    # Resources don't have descriptions, so we handle that case
    try:
        description = trait.desc
    except AttributeError:
        description = ""
    
    return display_name, die_size, description

def format_trait_section(title, traits, show_desc=False):
    """
    Format a section of traits for the character sheet.
    
    Args:
        title: The section title
        traits: List of trait objects
        show_desc: Whether to show descriptions
        
    Returns:
        Formatted string for the section
    """
    if not traits:
        return ""
        
    # Create header
    section = f"|y{title}|n\n"
    
    # Create table
    # Only show description column for Resources and Signature Assets
    show_desc = show_desc and title in ["Resources", "Signature Assets"]
    
    table = evtable.EvTable(
        "|wTrait|n",
        "|wDie|n",
        "|wDescription|n" if show_desc else None,
        border="table",
        width=78
    )
    
    # Add rows
    for trait in sorted(traits, key=lambda x: str(x.key)):
        display_name, die_size, description = get_trait_display(trait)
        if show_desc:
            table.add_row(display_name, die_size, description)
        else:
            table.add_row(display_name, die_size)
    
    return section + str(table) + "\n"

def format_distinctions_short(distinctions):
    """
    Format distinctions in a compact form for the sheet header.
    
    Args:
        distinctions: List of distinction trait objects
    """
    if not distinctions:
        return ""
    
    # Create header
    section = "|yDistinctions|n\n"
    
    # Create table
    table = evtable.EvTable(border="table", width=78)
    
    # Convert trait objects to display strings
    dist_displays = [f"{get_trait_display(d)[0]} (d8)" for d in sorted(distinctions, key=lambda x: x.key)]
    table.add_row(*dist_displays)
    
    return section + str(table) + "\n"

def format_distinctions_full(distinctions):
    """
    Format distinctions with full descriptions for the sheet footer.
    
    Args:
        distinctions: List of distinction trait objects
    """
    if not distinctions:
        return ""
    
    # Create header
    section = "|yDistinction Details|n\n"
    
    # Create table
    table = evtable.EvTable(
        "|wDistinction|n",
        "|wDescription|n",
        border="table",
        width=78
    )
    
    # Add rows
    for dist in sorted(distinctions, key=lambda x: x.key):
        display_name, _, description = get_trait_display(dist)
        table.add_row(display_name, description)
    
    return section + str(table) + "\n"

def format_traits_three_columns(title, traits):
    """
    Format traits in a three-column layout without table borders.
    
    Args:
        title: The section title
        traits: List of trait objects
        
    Returns:
        Formatted string for the section with three columns
    """
    if not traits:
        return ""
    
    # Create header
    section = f"|w{title}:|n\n"
    
    # Sort traits by name
    sorted_traits = sorted(traits, key=lambda x: str(x.key))
    
    # Calculate column width (roughly 26 characters per column for 78 total width)
    col_width = 26
    
    # Group traits into rows of 3
    for i in range(0, len(sorted_traits), 3):
        row_parts = []
        for j in range(3):
            if i + j < len(sorted_traits):
                trait = sorted_traits[i + j]
                display_name, die_size, _ = get_trait_display(trait)
                trait_text = f"{display_name}: {die_size}"
                # Pad to column width
                row_parts.append(trait_text.ljust(col_width))
            else:
                # Fill empty columns
                row_parts.append("".ljust(col_width))
        
        # Join the three columns and add to section
        section += "".join(row_parts).rstrip() + "\n"
    
    return section + "\n"

class CmdSheet(CharacterLookupMixin, Command):
    """
    View a character sheet.
    
    Usage:
        sheet [character]
        
    Without arguments, shows your own character sheet.
    Staff members can view other characters' sheets by specifying their name.
    
    Sheet Sections:
    1. Basic Information
       - Character name
       - Plot Points (used for special actions)
    
    2. Distinctions (d8 or d4)
       - Character Concept: Core identity
       - Culture: Heritage and upbringing
       - Vocation: Professional role or calling
       Note: Using d4 instead of d8 earns a Plot Point
    
    3. Prime Sets (Core dice pools)
       - Attributes (d4-d12): Natural capabilities
         * Physical (Strength, Agility, etc.)
         * Mental (Intelligence, Willpower, etc.)
         * Social (Presence, Manipulation, etc.)
       - Skills (d4-d12): Trained abilities
         * Combat (Fighting, Shooting, etc.)
         * Physical (Athletics, Stealth, etc.)
         * Mental (Medicine, Science, etc.)
         * Social (Persuasion, Deception, etc.)
    
    4. Additional Sets
       - Resources: Organization-provided dice pools
       - Signature Assets: Personal items/companions
       - Powers: Supernatural or extraordinary abilities
    
    Die Size Guide:
       d4: Untrained/Weak
       d6: Average/Basic Training
       d8: Professional/Well Trained       d10: Expert/Exceptional
       d12: Master/Peak Human
    """
    
    key = "sheet"
    locks = "cmd:all();view_other:perm(Builder)"
    help_category = "Character"
    switch_options = ()

    def func(self):
        """Execute the command."""
        # Get the target character
        if not self.args:
            char = self.caller
        else:
            # Check view_other permission
            if not self.caller.locks.check_lockstring(self.caller, "view_other:perm(Builder)"):
                self.msg("You don't have permission to view other characters' sheets.")
                return
                
            # Try to find the character using the mixin's method
            char = self.find_character(self.args)
            if not char:
                return
            
            # Check if it's actually a character with trait support
            if not hasattr(char, 'character_attributes'):
                self.msg(f"{char.name} has no character sheet.")
                return
            
        # Build the character sheet
        sheet = f"\n|w{char.name}'s Character Sheet|n\n"
        
        # Add Prime Sets header
        sheet += "\n|yPrime Sets|n\n"
        
        # Add attributes section if they exist
        if hasattr(char, 'character_attributes'):
            attributes = [char.character_attributes.get(key) for key in char.character_attributes.all()]
            attributes = [trait for trait in attributes if trait]  # Filter out None values
            if attributes:
                sheet += format_traits_three_columns("Attributes", attributes)
        
        # Add skills section if they exist
        if hasattr(char, 'skills'):
            skills = [char.skills.get(key) for key in char.skills.all()]
            skills = [trait for trait in skills if trait]  # Filter out None values
            if skills:
                sheet += format_traits_three_columns("Skills", skills)
        
        # Add distinctions section if they exist
        if hasattr(char, 'distinctions'):
            sheet += "\n|wDistinctions:|n\n"
            for trait in [char.distinctions.get(key) for key in char.distinctions.all()]:
                if trait:
                    sheet += f"  {trait.name}: d{int(trait.value)}"
                    if hasattr(trait, 'desc') and trait.desc:
                        sheet += f" ({trait.desc})"
                    sheet += "\n"
        
        # Get optional handlers
        has_signature_assets = hasattr(char, 'signature_assets')
        has_resources = hasattr(char, 'char_resources')
        has_powers = hasattr(char, 'powers')
        
        # Add Additional Sets header if any optional sets exist
        if has_signature_assets or has_resources or has_powers or hasattr(char, 'temporary_assets'):
            sheet += "\n|yAdditional Sets|n\n"
            
            # Add signature assets section if they exist
            if has_signature_assets:
                sheet += "\n|wSignature Assets:|n\n"
                for trait in [char.signature_assets.get(key) for key in char.signature_assets.all()]:
                    if trait:
                        sheet += f"  {trait.name}: d{int(trait.value)}"
                        if hasattr(trait, 'desc') and trait.desc:
                            sheet += f" ({trait.desc})"
                        sheet += "\n"
            
            # Add powers section if they exist
            if has_powers:
                sheet += "\n|wPowers:|n\n"
                for trait in [char.powers.get(key) for key in char.powers.all()]:
                    if trait:
                        sheet += f"  {trait.name}: d{int(trait.value)}"
                        if hasattr(trait, 'desc') and trait.desc:
                            sheet += f" ({trait.desc})"
                        sheet += "\n"
            
            # Add temporary assets section if they exist
            if hasattr(char, 'temporary_assets'):
                temp_assets = [char.temporary_assets.get(key) for key in char.temporary_assets.all()]
                if temp_assets:
                    sheet += "\n|wTemporary Assets:|n\n"
                    for trait in temp_assets:
                        if trait:
                            sheet += f"  {trait.name}: d{int(trait.value)}\n"
            
            # Add resources section if they exist
            if has_resources:
                sheet += "\n|wResources:|n\n"
                for trait in [char.char_resources.get(key) for key in char.char_resources.all()]:
                    if trait:
                        sheet += f"  {trait.name}: d{int(trait.value)}"
                        if hasattr(trait, 'desc') and trait.desc:
                            sheet += f" ({trait.desc})"
                        sheet += "\n"
        
        # Add plot points if they exist
        if hasattr(char, 'traits'):
            plot_points = char.traits.get("plot_points")
            if plot_points:
                sheet += f"\n|wPlot Points:|n {int(plot_points.value)}\n"
        
        # Add special effects section if it exists
        if hasattr(char, 'db') and char.db.special_effects:
            sheet += f"\n|ySpecial Effects|n\n{char.db.special_effects}\n"
        
        # Send the sheet to the caller
        self.msg(sheet)


class CharSheetCmdSet(CmdSet):
    """
    Command set for viewing character sheets.
    """
    
    def at_cmdset_creation(self):
        """
        Add commands to the command set
        """
        self.add(CmdSheet()) 