"""
Organization commands for managing organisations and their members.
"""

import time

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet, create_object
from evennia.utils import evtable
from evennia.utils.search import search_object
from typeclasses.organisations import Organisation
from utils.command_mixins import CharacterLookupMixin
from utils.org_utils import (
    validate_rank, get_org, get_char,
    get_org_and_char
)


class CmdOrg(CharacterLookupMixin, MuxCommand):
    """
    Manage organisations.
    
    Usage:
        org                     - List organisations you're a member of
        org <name>              - View organisation details
        
    Examples:
        org                     - List your organisations
        org House Otrese        - View House Otrese's information
        
    Organisations represent formal groups like guilds, companies,
    or military units. Each has a hierarchy of numbered ranks (1-10).
    """
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
    
    def get_help(self, caller, cmdset):
        """
        Return help text, customized based on caller's permissions.
        
        Args:
            caller: The object requesting help
            cmdset: The cmdset this command belongs to
            
        Returns:
            str: The help text
        """
        # Get base help text from docstring
        help_text = super().get_help(caller, cmdset)
        
        # Add admin commands if caller has Admin permissions
        if caller.check_permstring("Admin"):
            help_text += """
    
    |yAdmin Commands:|n
        org/create <name>                    - Create a new organisation
        org/delete <name>                    - Delete an organisation
        org/member <org>,<char>[,<rank>]     - Add/update member
        org/remove <org>,<char>              - Remove member
        org/rankname <org>,<rank>=<name>     - Set rank name
        
    Admin Examples:
        org/create House Anadun              - Create new noble house
        org/member House Otrese,Koline,3     - Add Koline as rank 3
        org/member House Otrese,Koline,2     - Promote Koline to rank 2
        org/remove House Otrese,Koline       - Remove Koline from house
        org/rankname House Otrese,5=Knight   - Set rank 5 name to Knight
        org/delete House Otrese              - Delete the organization
            """
        
        return help_text

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
    def list_my_orgs(self):
        """List organizations the character is a member of."""
        from evennia.objects.models import ObjectDB
        
        # Get character's organisations
        orgs_dict = self.caller.organisations
        
        if not orgs_dict:
            self.msg("You are not a member of any organisations.")
            return
            
        # Build list of (org, rank) tuples
        org_list = []
        for org_id, rank in orgs_dict.items():
            org = ObjectDB.objects.filter(id=org_id).first()
            if org:
                rank_name = org.db.rank_names.get(rank, f"Rank {rank}")
                org_list.append((org.name, rank, rank_name))
                
        if not org_list:
            self.msg("You are not a member of any organisations.")
            return
            
        # Sort by organization name
        org_list.sort(key=lambda x: x[0])
        
        # Display table
        self.msg("\n|yYour Organisations:|n")
        table = evtable.EvTable(
            "|wOrganisation|n",
            "|wRank|n",
            border="table",
            width=78
        )
        
        for org_name, rank_num, rank_name in org_list:
            table.add_row(org_name, rank_name)
            
        self.msg(str(table))
        
    def func(self):
        """Execute the command."""
        if not self.args:
            # List organizations the character is a member of
            self.list_my_orgs()
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
            self.msg("Usage: org/create <n>")
            return
            
        if not self.access(self.caller, "create"):
            self.msg("You don't have permission to create organisations.")
            return
            
        # Check if an organisation with this name already exists
        if self._get_org(self.args):
            self.msg(f"An organisation with the name '{self.args}' already exists.")
            return
            
        # Create the organisation
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
            
        # Find the organisation
        org = self._get_org(self.args)
        if not org:
            return
            
        # Check if this is a confirmation for the same org
        confirming = getattr(self.caller.db, "delete_org_confirming", None)
        if isinstance(confirming, dict) and confirming.get("name") == org.name:
            # Check timeout (60 seconds)
            if time.time() - confirming.get("timestamp", 0) > 60:
                self.msg("Delete confirmation timed out. Please repeat the command to confirm.")
                self.caller.db.delete_org_confirming = {"name": org.name, "timestamp": time.time()}
                return
            # Delete the organisation
            name = org.name
            org.delete()
            self.msg(f"Deleted organisation: {name}")
            del self.caller.db.delete_org_confirming
            return

        # First time through - ask for confirmation and store target
        self.msg(f"|yWARNING: This will delete the organisation '{org.name}' and remove all member references.|n")
        self.msg("|yThis action cannot be undone. Repeat the command to confirm within 60 seconds.|n")
        self.caller.db.delete_org_confirming = {"name": org.name, "timestamp": time.time()}
        
    def manage_member(self):
        """Add or update a member's rank."""
        if not self.access(self.caller, "member"):
            self.msg("You don't have permission to manage members.")
            return
            
        # Parse arguments - format: org,char[,rank]
        parts = [p.strip() for p in self.args.split(',') if p.strip()]
        if len(parts) < 2:
            self.msg("Usage: org/member <organisation>,<character>[,<rank>]")
            return
            
        org_name = parts[0]
        char_name = parts[1]
        rank = self._validate_rank(parts[2] if len(parts) > 2 else "4", default=4)
        if rank is None:
            return
            
        # Find the organisation and character
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
            
        # Parse arguments - format: org,char
        parts = [p.strip() for p in self.args.split(',') if p.strip()]
        if len(parts) != 2:
            self.msg("Usage: org/remove <organisation>,<character>")
            return
        org_name, char_name = parts
        
        # Find the organisation and character
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
            
        # Parse arguments - format: org,rank=name
        if "," not in self.args or "=" not in self.args:
            self.msg("Usage: org/rankname <organisation>,<rank>=<name>")
            return
        
        parts = [p.strip() for p in self.args.split(",", 1)]
        if len(parts) != 2:
            self.msg("Usage: org/rankname <organisation>,<rank>=<name>")
            return
            
        org_name = parts[0]
        rank_name_part = parts[1]
        
        # Parse rank=name
        if "=" not in rank_name_part:
            self.msg("Usage: org/rankname <organisation>,<rank>=<name>")
            return
        rank_str, rank_name = [p.strip() for p in rank_name_part.split("=", 1)]
        
        rank = self._validate_rank(rank_str)
        if rank is None:
            return
            
        # Get the organisation
        org = self._get_org(org_name)
        if not org:
            return
            
        # Set the rank name
        org.db.rank_names[rank] = rank_name
        self.msg(f"Set rank {rank} name to '{rank_name}'.")
        
    def show_org_info(self):
        """Show organisation information."""
        # Find the organisation
        org = self._get_org(self.args)
        if not org:
            return
            
        # Get members
        all_members = list(org.get_members())
        
        # Filter out unfinished characters
        from typeclasses.characters import STATUS_UNFINISHED
        members = [(member, rank_num, rank_name) 
                   for member, rank_num, rank_name in all_members 
                   if getattr(member.db, 'status', None) != STATUS_UNFINISHED]
        
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
                self.msg("\nThis organisation has no resources.")
        
        # Show members
        if not members:
            self.msg("\nThis organisation has no members.")
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
