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
        
        # Show resources if high-ranking member or staff
        caller_rank = org.get_member_rank(self.caller)
        is_staff = self.caller.permissions.check("Admin")
        if is_staff or (caller_rank and 1 <= caller_rank <= 3):
            resources = org.get_resources()
            if resources:
                self.msg("\nResources:")
                table = evtable.EvTable(
                    "|wName|n",
                    "|wDie|n",
                    border="table"
                )
                for name, die_size in resources:
                    table.add_row(name, f"d{int(die_size)}")
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


class OrgCmdSet(CmdSet):
    """
    Command set for organisation management.
    """
    
    def at_cmdset_creation(self):
        """Add commands to the set."""
        self.add(CmdOrg())
