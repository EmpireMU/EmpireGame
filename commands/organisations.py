"""
Organization commands for managing organisations and their members.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet, create_object
from evennia.utils import evtable
from evennia.utils.search import search_object
from typeclasses.organisations import Organisation
from utils.command_mixins import CharacterLookupMixin
from utils.org_utils import (
    validate_rank, get_org, get_char,
    get_org_and_char, parse_equals, parse_comma
)


class CmdOrg(CharacterLookupMixin, MuxCommand):
    """
    Manage organisations.
    
    Usage:
        org                     - List organisations you're a member of
        org <name>             - View organisation details
        org/create <name>      - Create a new organisation (Admin)
        org/delete <name>      - Delete an organisation (Admin)
        org/member <org>,<char>[,<rank>] - Add/update member (Admin)
        org/remove <org>,<char> - Remove member (Admin)
        org/rankname <org>,<rank>=<name> - Set rank name (Admin)
        
    Examples:
        org House Otrese                   - View House Otrese's info
        org/create House Anadun            - Create new noble house
        org/member House Otrese = Koline,3 - Add Koline as Senior Member
        org/member House Otrese = Koline,2 - Promote Koline to Deputy
        org/remove House Otrese = Koline   - Remove Koline from house
        org/rankname House Otrese = 5,Knight - Set rank 5 name to Knight
        org/delete House Otrese            - Delete the organization
        
    Organisations represent formal groups like guilds, companies,
    or military units. Each has a hierarchy of numbered ranks (1-10).    """
    key = "org"
    locks = (
        "cmd:all();"           # Base command available to all
        "create:perm(Admin);"  # Creating orgs requires Admin
        "delete:perm(Admin);"  # Deleting orgs requires Admin
        "member:perm(Admin);"  # Managing members requires Admin
        "remove:perm(Admin);"  # Removing members requires Admin
        "rankname:perm(Admin)" # Setting rank names requires Admin
    )
    help_category = "Organizations"
    switch_options = ("create", "member", "remove", "rankname", "delete")

    def _check_admin(self, operation):
        """Helper method to check for Admin permission."""
        if not self.caller.permissions.check("Admin"):
            self.msg(f"You don't have permission to {operation} organisations.")
            return False
        return True

    def _get_org(self, org_name):
        """Helper method to find and validate an organisation."""
        return get_org(org_name, self.caller)
        
    def _get_character(self, char_name):
        """Helper method to find a character."""
        return get_char(char_name, self.caller)
        
    def _get_org_and_char(self, org_name, char_name):
        """Helper method to find both an organisation and a character."""
        return get_org_and_char(org_name, char_name, self.caller)
        
    def _parse_equals(self, usage_msg):
        """Helper method to parse = separated arguments."""
        parts = parse_equals(self.args)
        if not parts:
            self.msg(f"Usage: {usage_msg}")
            return None
        return parts
        
    def _parse_comma(self, text, expected_parts=2, usage_msg=None):
        """Helper method to parse comma-separated arguments."""
        return parse_comma(text, expected_parts, usage_msg, self.caller)
        
    def _validate_rank(self, rank_str, default=None):
        """Helper method to validate rank numbers."""
        return validate_rank(rank_str, default, self.caller)
        
    # Member management helpers
    def _is_member(self, org, char):
        """Helper method to check if a character is a member of an organization."""
        return org.get_member_rank(char) is not None
        
    def _update_member_rank(self, org, char, rank):
        """Helper method to update a member's rank."""
        if org.set_rank(char, rank):
            self.msg(f"Changed {char.name}'s rank to '{org.get_member_rank_name(char)}'.")
            return True
        self.msg(f"Failed to set rank. Make sure the rank (1-10) is valid.")
        return False
        
    def _add_new_member(self, org, char, rank):
        """Helper method to add a new member to an organization."""
        if org.add_member(char, rank):
            self.msg(f"Added {char.name} to '{org.name}' as '{org.get_member_rank_name(char)}'.")
            return True
        self.msg(f"Failed to add member. Make sure the rank (1-10) is valid.")
        return False
        
    # Main command methods
    def func(self):
        """Execute the command."""
        if not self.args:
            self.msg("Usage: org <organization>")
            return
            
        # Handle switches
        if self.switches:
            if self.switches[0] == "create":
                self.create_org()
            elif self.switches[0] == "member":
                self.manage_member()
            elif self.switches[0] == "remove":
                self.remove_member()
            elif self.switches[0] == "rankname":
                self.set_rank_name()
            elif self.switches[0] == "delete":
                self.delete_org()
            return
            
        # Default: show organization info
        self.show_org_info()
        
    def at_post_cmd(self):
        """Clean up any temporary attributes."""
        # Only clean up if the command wasn't successful
        if hasattr(self.caller, 'db') and hasattr(self.caller.db, 'delete_org_confirming'):
            if not self.caller.db.delete_org_confirming:
                del self.caller.db.delete_org_confirming
        
    def create_org(self):
        """Create a new organisation."""
        if not self.args:
            self.msg("Usage: org/create <name>")
            return
            
        if not self.access(self.caller, "create"):
            self.msg("You don't have permission to create organisations.")
            return
            
        # Create the organization
        try:
            org = create_object(
                typeclass=Organisation,
                key=self.args
            )
            if org:
                self.msg(f"Created organisation: {org.name}")
            else:
                self.msg("Failed to create organisation.")
        except Exception as e:
            self.msg(f"Error creating organisation: {e}")
            
    def delete_org(self):
        """Delete an organisation."""
        if not self.access(self.caller, "delete"):
            self.msg("You don't have permission to delete organisations.")
            return
            
        # Find the organization
        org = self._get_org(self.args)
        if not org:
            return
            
        # Check if this is a confirmation
        confirming = self.caller.db.delete_org_confirming
        if confirming:
            # Delete the organization
            name = org.name
            org.delete()
            self.msg(f"Deleted organisation: {name}")
            del self.caller.db.delete_org_confirming
            return
        # First time through - ask for confirmation
        self.msg(f"|yWARNING: This will delete the organisation '{org.name}' and remove all member references.|n")
        self.msg("|yThis action cannot be undone. Type 'org/delete' again to confirm.|n")
        self.caller.db.delete_org_confirming = True
        
    def manage_member(self):
        """Add or update a member's rank."""
        if not self.access(self.caller, "member"):
            self.msg("You don't have permission to manage members.")
            return
            
        # Parse arguments
        parts = self._parse_equals("org/member <organisation>,<character>,<rank>")
        if not parts:
            return
        org_name, rest = parts
        
        # Parse character and optional rank - split on comma with more robust handling
        parts = [p.strip() for p in rest.split(',')]
        if not parts:
            self.msg("Unable to parse character name and rank.")
            return
            
        char_name = parts[0]
        rank = self._validate_rank(parts[1] if len(parts) > 1 else "4", default=4)
        if rank is None:
            return
            
        # Find the organization and character
        org, char = self._get_org_and_char(org_name, char_name)
        if not org or not char:
            return
            
        # Check if already a member
        if self._is_member(org, char):
            self._update_member_rank(org, char, rank)
        else:
            self._add_new_member(org, char, rank)
            
    def remove_member(self):
        """Remove a member from an organisation."""
        if not self.access(self.caller, "remove"):
            self.msg("You don't have permission to remove members.")
            return
            
        # Parse arguments
        parts = self._parse_equals("org/remove <organisation>,<character>")
        if not parts:
            return
        org_name, char_name = parts
        
        # Find the organization and character
        org, char = self._get_org_and_char(org_name, char_name)
        if not org or not char:
            return
            
        # Check if member
        if not self._is_member(org, char):
            self.msg(f"{char.name} is not a member of '{org.name}'.")
            return
            
        # Remove member
        if org.remove_member(char):
            self.msg(f"Removed {char.name} from '{org.name}'.")
        else:
            self.msg("Failed to remove member. This should not happen - please report this error.")
            
    def set_rank_name(self):
        """Set the name for a rank."""
        if not self.access(self.caller, "rankname"):
            self.msg("You don't have permission to set rank names.")
            return
            
        # Parse arguments
        parts = self._parse_equals("org/rankname <organisation>,<rank>=<name>")
        if not parts:
            return
        org_name, rest = parts
        
        # Parse rank and name
        rank_parts = self._parse_comma(rest, 2, "org/rankname <organisation>,<rank>=<name>")
        if not rank_parts:
            return
            
        rank = self._validate_rank(rank_parts[0])
        if rank is None:
            return
            
        # Get the organisation
        org = self._get_org(org_name)
        if not org:
            return
            
        # Set the rank name
        org.db.rank_names[rank] = rank_parts[1]
        self.msg(f"Set rank {rank} name to '{rank_parts[1]}'.")
        
    def show_org_info(self):
        """Show organisation information."""
        # Find the organisation
        org = self._get_org(self.args)
        if not org:
            return
            
        # Get members
        members = list(org.get_members())
        
        # Show basic info
        self.msg(f"\n|y{org.name}|n")
        self.msg(f"Description: {org.db.description}")
        
        # Show resources if high-ranking member
        caller_rank = org.get_member_rank(self.caller)
        if caller_rank and 1 <= caller_rank <= 3:
            resources = org.get_resources()
            if resources:
                self.msg("\nResources:")
                table = evtable.EvTable(
                    "|wName|n",
                    "|wDie|n",
                    border="table"
                )
                for name, die_size in resources:
                    table.add_row(name, f"d{die_size}")
                self.msg(str(table))
            else:
                self.msg("\nThis organization has no resources.")
        
        # Show members
        if not members:
            self.msg("\nThis organization has no members.")
            return
            
        # Create member table
        self.msg(f"\nMembers ({len(members)}):")
        table = evtable.EvTable(
            "|wName|n",
            "|wRank|n",
            border="table",
            width=78
        )
        
        # Add members
        for member, rank_num, rank_name in members:
            table.add_row(member.name, rank_name)
            
        self.msg(str(table))


class CmdResource(CharacterLookupMixin, MuxCommand):
    """
    Manage organisation resources.
    
    Usage:
        resource                    - List all resources you can access
        resource/org <org>,<name>=<value>  - Create org resource (Admin)
        resource/char <char>,<name>=<value> - Create character resource (Admin)
        resource/transfer <from>,<to>,<name> - Transfer resource (Admin)
        resource/delete <owner>,<name>     - Delete a resource (Admin)
        
    Examples:
        resource/org "Knights Custodian",Wealth=8    # Creates a d8 Wealth resource
        resource/char Bob,Wealth=6                   # Creates a d6 Wealth resource
        resource/transfer "Knights Custodian",Bob,Wealth=10  # Transfers a d10 Wealth resource
        resource/delete "Knights Custodian",Sanctuary Chapter
        
    Valid die sizes: 4, 6, 8, 10, 12
    
    Resources represent assets that can be owned by organisations
    or characters and transferred between them.    """
    
    key = "resource"
    aliases = ["res"]
    locks = (
        "cmd:all();"             # Base command available to all
        "org:perm(Admin);"       # Creating org resources requires Admin
        "char:perm(Admin);"      # Creating char resources requires Admin
        "transfer:perm(Admin);"  # Transferring resources requires Admin
        "delete:perm(Admin)"     # Deleting resources requires Admin
    )
    help_category = "Resources"
    
    def _get_org(self, org_name):
        """Helper method to find and validate an organisation."""
        return get_org(org_name, self.caller)
        
    def _get_char(self, char_name):
        """Helper method to find and validate a character."""
        return self.find_character(char_name)
        
    def func(self):
        """Handle resource management."""
        if not self.args and not self.switches:
            # List all owned resources
            self.list_resources()
            return
            
        if not self.switches:
            # View specific resource
            self.view_resource()
            return
            
        # Handle switches
        switch = self.switches[0]
        
        if switch == "org":
            if not self.access(self.caller, "org"):
                self.msg("You don't have permission to create organisation resources.")
                return
            self.create_org_resource()
        elif switch == "char":
            if not self.access(self.caller, "char"):
                self.msg("You don't have permission to create character resources.")
                return
            self.create_char_resource()
        elif switch == "transfer":
            if not self.access(self.caller, "transfer"):
                self.msg("You don't have permission to transfer resources.")
                return
            self.transfer_resource()
        elif switch == "delete":
            if not self.access(self.caller, "delete"):
                self.msg("You don't have permission to delete resources.")
                return
            self.delete_resource()
        else:
            self.msg(f"Unknown switch: {switch}")
            
    def list_resources(self):
        """List all resources owned by the caller."""
        owner = self.caller
        if hasattr(self.caller, 'char'):
            owner = self.caller.char
            
        # Get resources from trait handler
        resources = None
        if hasattr(owner, 'char_resources') and owner.char_resources:
            resources = owner.char_resources
        elif hasattr(owner, 'org_resources') and owner.org_resources:
            resources = owner.org_resources
            
        if not resources:
            self.msg("You don't own any resources.")
            return
            
        # Create table
        from evennia.utils.evtable import EvTable
        table = EvTable(
            "|wName|n",
            "|wDie|n",
            border="header"
        )
        
        # Add each resource to the table
        for name in resources.all():
            trait = resources.get(name)
            table.add_row(name, f"d{trait.value}")
            
        self.msg(table)
        
    def view_resource(self):
        """View details of a specific resource."""
        if not self.args:
            self.msg("Usage: resource <n>")
            return
            
        owner = self.caller
        if hasattr(self.caller, 'char'):
            owner = self.caller.char
            
        # Get resources from trait handler
        resources = None
        if hasattr(owner, 'char_resources') and owner.char_resources:
            resources = owner.char_resources
        elif hasattr(owner, 'org_resources') and owner.org_resources:
            resources = owner.org_resources
            
        if not resources:
            self.msg("You don't own any resources.")
            return
            
        name = self.args.strip()
        trait = resources.get(name)
        if not trait:
            self.msg(f"No resource found named '{name}'.")
            return
            
        # Create table
        from evennia.utils.evtable import EvTable
        table = EvTable(
            "|wName|n",
            "|wDie|n",
            border="header"
        )
        table.add_row(name, f"d{trait.value}")
        
        self.msg(table)
        
    def create_org_resource(self):
        """Create a resource for an organization."""
        if not self.args:
            self.msg("Usage: resource/org <org>,<name>=<value>")
            return
            
        if not self.access(self.caller, "org"):
            self.msg("You don't have permission to create organisation resources.")
            return
            
        org_name, rest = self.args.split(",", 1)
        name, value = [part.strip() for part in rest.split("=", 1)]
        
        # Get organization
        org = self._get_org(org_name)
        if not org:
            return
            
        # Parse value
        try:
            value = int(value.strip())
            if value not in [4, 6, 8, 10, 12]:
                self.msg("Die size must be one of: 4, 6, 8, 10, 12")
                return
        except ValueError:
            self.msg("You must provide a valid die size.")
            return
            
        # Add resource to organization
        try:
            if not hasattr(org, 'org_resources'):
                self.msg("That organisation cannot have resources.")
                return
                
            org.add_org_resource(name, value)
            self.msg(f"Added resource '{name}' (d{value}) to {org.name}.")
        except ValueError as e:
            self.msg(str(e))
            
    def create_char_resource(self):
        """Create a resource for a character."""
        if not self.args:
            self.msg("Usage: resource/char <char>,<name>=<value>")
            return
            
        char_name, rest = self.args.split(",", 1)
        name, value = [part.strip() for part in rest.split("=", 1)]
        
        # Get character
        char = self._get_char(char_name)
        if not char:
            return
            
        # Parse value
        try:
            value = int(value.strip())
            if value not in [4, 6, 8, 10, 12]:
                self.msg("Die size must be one of: 4, 6, 8, 10, 12")
                return
        except ValueError:
            self.msg("You must provide a valid die size.")
            return
            
        # Add resource to character
        try:
            if not hasattr(char, 'char_resources'):
                self.msg("That character cannot have resources.")
                return
                
            char.add_resource(name, value)
            self.msg(f"Added resource '{name}' (d{value}) to {char.name}.")
        except ValueError as e:
            self.msg(str(e))
            
    def transfer_resource(self):
        """Transfer a resource to another character or organisation."""
        if not self.args or "=" not in self.args:
            self.msg("Usage: resource/transfer <source>:<resource> = <target>")
            return
            
        source_and_name, target = [part.strip() for part in self.args.split("=", 1)]
        
        # Parse source and resource name
        if ":" not in source_and_name:
            self.msg("You must specify the source and resource name in the format: source:resource")
            return
            
        source_name, name = [part.strip().strip('"') for part in source_and_name.split(":", 1)]
        target = target.strip().strip('"')  # Also strip quotes from target
        
        # Find source and target
        from evennia.utils.search import search_object
        from typeclasses.organisations import Organisation
        from typeclasses.characters import Character
        
        # Try to find source
        source_matches = search_object(source_name)
        if not source_matches:
            self.msg(f"Source '{source_name}' not found.")
            return
        source = source_matches[0]
        
        # Verify source type and resource capability
        if not (isinstance(source, (Character, Organisation)) and 
                (hasattr(source, 'char_resources') or hasattr(source, 'org_resources'))):
            self.msg(f"{source.name} cannot have resources.")
            return
            
        # Try to find target
        target_matches = search_object(target)
        if not target_matches:
            self.msg(f"Target '{target}' not found.")
            return
        target = target_matches[0]
        
        # Verify target type and resource capability
        if not (isinstance(target, (Character, Organisation)) and 
                (hasattr(target, 'char_resources') or hasattr(target, 'org_resources'))):
            self.msg(f"{target.name} cannot have resources.")
            return
            
        # Check transfer permissions
        if not self.caller.permissions.check("Admin"):
            # Check if resource is transferable
            if "Wealth" not in name and "Political Capital" not in name:
                self.msg("Only Wealth and Political Capital resources can be transferred.")
                return
                
            # If source is an organization, check rank permissions
            if isinstance(source, Organisation):
                caller_rank = source.get_member_rank(self.caller)
                if caller_rank not in [1, 2]:
                    self.msg("Only members of rank 1 or 2 can transfer resources from an organization.")
                    return
            
            # If target is a character and source is a character, check if it's the caller
            if isinstance(source, Character) and isinstance(target, Character):
                if source != self.caller:
                    self.msg("You can only transfer your own resources.")
                    return
        
        try:
            # Get the resource from the appropriate handler
            if hasattr(source, 'char_resources'):
                trait = source.char_resources.get(name)
                if not trait:
                    self.msg(f"Resource '{name}' not found on {source.name}.")
                    return
                die_size = trait.value
                source.char_resources.remove(name)
            else:  # Organization
                trait = source.org_resources.get(name)
                if not trait:
                    self.msg(f"Resource '{name}' not found on {source.name}.")
                    return
                die_size = trait.value
                source.org_resources.remove(name)
            
            # Add to target using appropriate method
            if hasattr(target, 'char_resources'):
                target.add_resource(name, die_size)
            else:  # Organization
                target.add_org_resource(name, die_size)
                
            self.msg(f"Transferred {name} from {source.name} to {target.name}.")
        except ValueError as e:
            self.msg(str(e))
            
    def delete_resource(self):
        """Delete a resource from any character or organisation."""
        if not self.args or "," not in self.args:
            self.msg("Usage: resource/delete <owner>,<name>")
            return
            
        owner_name, name = [part.strip() for part in self.args.split(",", 1)]
        
        # Find the owner
        from evennia.utils.search import search_object
        from typeclasses.organisations import Organisation
        from typeclasses.characters import Character
        
        owner_matches = search_object(owner_name)
        if not owner_matches:
            self.msg(f"Owner '{owner_name}' not found.")
            return
        owner = owner_matches[0]
        
        # Verify owner type and resource capability
        if not (isinstance(owner, (Character, Organisation)) and 
                (hasattr(owner, 'char_resources') or hasattr(owner, 'org_resources'))):
            self.msg(f"{owner.name} cannot have resources.")
            return
            
        # Get resources from trait handler
        resources = None
        if hasattr(owner, 'char_resources') and owner.char_resources:
            resources = owner.char_resources
        elif hasattr(owner, 'org_resources') and owner.org_resources:
            resources = owner.org_resources
            
        if not resources:
            self.msg(f"{owner.name} doesn't own any resources.")
            return
            
        # Delete the resource
        if resources.get(name):
            resources.remove(name)
            self.msg(f"Deleted resource '{name}' from {owner.name}.")
        else:
            self.msg(f"No resource found named '{name}' on {owner.name}.")


class OrgCmdSet(CmdSet):
    """
    Command set for organisation management.
    """
    
    def at_cmdset_creation(self):
        """Add commands to the set."""
        self.add(CmdOrg())
        self.add(CmdResource())  # Add resource management commands