"""
Family relationship commands for viewing character family trees.
"""

from evennia.commands.command import Command
from evennia.utils import search
from evennia.objects.models import ObjectDB


class CmdFamily(Command):
    """
    View family relationships for a character.
    
    Usage:
        family [character name]
        
    Shows the family relationships for yourself or the specified character.
    Family information includes parents, siblings, children, and extended family.
    
    Examples:
        family               - Show your own family
        family Alice         - Show Alice's family relationships
    """
    
    key = "family"
    aliases = ["relatives", "kin"]
    help_category = "Information"
    
    def func(self):
        """Execute the family command."""
        
        # Determine target character
        if self.args.strip():
            # Look for specified character
            target_name = self.args.strip()
            target = search.object_search(target_name, typeclass="typeclasses.characters.Character")
            if not target:
                self.caller.msg(f"No character found with the name '{target_name}'.")
                return
            if len(target) > 1:
                self.caller.msg(f"Multiple characters found with that name: {', '.join([char.name for char in target])}")
                return
            target = target[0]
        else:
            # Use caller's character
            target = self.caller
            
        # Import here to avoid circular imports
        try:
            from web.relationships.views import get_character_family
        except ImportError:
            self.caller.msg("Family relationships system is not available.")
            return
            
        # Get family relationships
        family_relationships = get_character_family(target.id)
        
        if not family_relationships:
            if target == self.caller:
                self.caller.msg("You have no recorded family relationships.")
            else:
                self.caller.msg(f"{target.name} has no recorded family relationships.")
            return
        
        # Build the family display
        target_name = target.db.full_name or target.name
        lines = [f"|w{target_name}'s Family:|n", ""]
        
        # Define the order we want to display relationships
        relationship_order = [
            'Parent', 'Grandparent', 'Great-Grandparent',
            'Sibling', 'Aunt/Uncle', 'Cousin', 'Second Cousin', 'Distant Cousin',
            'Child', 'Grandchild', 'Great-Grandchild', 'Niece/Nephew'
        ]
        
        # Display relationships in order
        for relationship_type in relationship_order:
            if relationship_type in family_relationships:
                members = family_relationships[relationship_type]
                
                # Format the relationship type for display
                if len(members) == 1:
                    header = relationship_type
                else:
                    # Pluralize
                    if relationship_type.endswith('child'):
                        header = relationship_type.replace('child', 'children')
                    elif relationship_type == 'Sibling':
                        header = 'Siblings'
                    elif relationship_type == 'Aunt/Uncle':
                        header = 'Aunts/Uncles'
                    elif relationship_type.endswith('Cousin'):
                        header = relationship_type + 's'
                    elif relationship_type == 'Niece/Nephew':
                        header = 'Nieces/Nephews'
                    else:
                        header = relationship_type + 's'
                
                lines.append(f"|c{header}:|n")
                
                for member in members:
                    name = member['name']
                    if member['is_pc']:
                        # PC - make it stand out
                        lines.append(f"  {name}")
                    else:
                        # NPC - mark as such
                        lines.append(f"  {name} |K(NPC)|n")
                
                lines.append("")  # Empty line between relationship types
        
        # Remove the last empty line
        if lines and lines[-1] == "":
            lines.pop()
            
        self.caller.msg("\n".join(lines)) 