"""
Resource commands for managing character and organisation resources.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.command_mixins import CharacterLookupMixin
from utils.org_utils import get_org
from utils.resource_utils import (
    get_resource_disbursements,
    set_resource_disbursement,
    increment_resource_disbursement,
    clear_resource_disbursements,
)


class CmdResource(CharacterLookupMixin, MuxCommand):
    """
    Manage organisation resources.
    
    Usage:
        resource                                      - List all resources you can access
        resource/transfer <from>,<to>,<name>[=<size>] - Transfer Wealth or Political Capital
        
    Resources represent assets that can be owned by organisations or characters
    and transferred between them. These resources are shown on your character 
    sheet and can be used in dice rolls.
    
    Transfer Restrictions:
    - You can only transfer Wealth and Political Capital resources
    - To transfer from an org, you must be rank 1 or 2 in that organization
    - To transfer from a character, it must be your own character
    
    Examples:
        resource                                      - List your resources
        resource/transfer Self,Bob,Wealth=8           - Transfer d8 Wealth to Bob
        resource/transfer "House Otrese",Alice,Political Capital=6
    
    Valid die sizes: 4, 6, 8, 10, 12
    """
    
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
        resource/org <org>,<name>=<value>              - Create org resource
        resource/char <char>,<name>=<value>            - Create character resource
        resource/transfer <from>,<to>,<name>[=<size>]  - Transfer ANY resource (no restrictions)
        resource/delete <owner>,<name>                 - Delete a resource
        resource/due <target>                          - View recurring disbursements
        resource/due <target>,<name>=<count>/<die>     - Set recurring amount (e.g. Wealth=3/6)
        resource/due/add <target>,<name>=<count>/<die> - Adjust recurring amount
        resource/due/clear <target>[,<name>=<die>]     - Remove recurring configuration
        resource/disburse [<target1>,<target2>,...]    - Apply all recurring disbursements
        
    Admin Examples:
        resource/org "Knights Custodian",Wealth=8      - Create d8 org resource
        resource/char Bob,Wealth=6                     - Create d6 char resource
        resource/transfer "Knights Custodian",Bob,Sanctuary=10  - Transfer ANY resource
        resource/delete "Knights Custodian",Sanctuary  - Delete a resource
        
    Note: Admins can transfer any resource type, not just Wealth and Political Capital.
            """
        
        return help_text
    
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
        elif switch == "due":
            if not self.caller.permissions.check("Admin"):
                self.msg("Only staff can manage resource disbursements.")
                return
            self.manage_due()
        elif switch == "disburse":
            if not self.caller.permissions.check("Admin"):
                self.msg("Only staff can run bulk disbursements.")
                return
            self.disburse_resources()
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
            table.add_row(name, f"d{int(trait.base)}")
            
        self.msg(table)
        
    def view_resource(self):
        """View details of a specific resource."""
        if not self.args:
            self.msg("Usage: resource <name>")
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
        # Case-insensitive search for the resource
        trait = None
        actual_name = None
        for key in resources.all():
            if key.lower() == name.lower():
                trait = resources.get(key)
                actual_name = key
                break
                
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
        table.add_row(actual_name, f"d{int(trait.base)}")
        
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
        if not self.args:
            self.msg("Usage: resource/transfer <source>,<target>,<resource_name>[=<die_size>]")
            return
            
        # Parse comma-separated arguments
        parts = [part.strip().strip('"') for part in self.args.split(",")]
        if len(parts) < 3:
            self.msg("Usage: resource/transfer <source>,<target>,<resource_name>[=<die_size>]")
            return
            
        source_name = parts[0]
        target_name = parts[1]
        resource_spec = parts[2]
        
        # Parse resource name and optional die size
        if "=" in resource_spec:
            resource_name, die_size_str = [part.strip() for part in resource_spec.split("=", 1)]
            try:
                specified_die_size = int(die_size_str)
                if specified_die_size not in [4, 6, 8, 10, 12]:
                    self.msg("Die size must be one of: 4, 6, 8, 10, 12")
                    return
            except ValueError:
                self.msg("Invalid die size specified")
                return
        else:
            resource_name = resource_spec
            specified_die_size = None
        
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
        target_matches = search_object(target_name)
        if not target_matches:
            self.msg(f"Target '{target_name}' not found.")
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
            if "Wealth" not in resource_name and "Political Capital" not in resource_name:
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
            # Get the appropriate resource handler
            if hasattr(source, 'char_resources'):
                resources = source.char_resources
            else:  # Organization
                resources = source.org_resources
                
            # Find the resource, optionally matching die size
            trait_to_transfer = None
            trait_key_to_remove = None
            
            if specified_die_size:
                # Look for a resource with the exact name and die size (case-insensitive)
                for key in resources.all():
                    trait = resources.get(key)
                    if key.lower().startswith(resource_name.lower()) and trait.base == specified_die_size:
                        trait_to_transfer = trait
                        trait_key_to_remove = key
                        break
                        
                if not trait_to_transfer:
                    self.msg(f"Resource '{resource_name}' with die size d{specified_die_size} not found on {source.name}.")
                    return
            else:
                # Look for any resource with the given name (case-insensitive)
                trait_to_transfer = None
                trait_key_to_remove = None
                
                # First try exact match (case-insensitive)
                for key in resources.all():
                    if key.lower() == resource_name.lower():
                        trait_to_transfer = resources.get(key)
                        trait_key_to_remove = key
                        break
                
                # If no exact match, try prefix match (for numbered variants)
                if not trait_to_transfer:
                    for key in resources.all():
                        if key.lower().startswith(resource_name.lower()):
                            trait_to_transfer = resources.get(key)
                            trait_key_to_remove = key
                            break
                            
                if not trait_to_transfer:
                    self.msg(f"Resource '{resource_name}' not found on {source.name}.")
                    return
            
            # Get the die size and remove from source
            die_size = trait_to_transfer.base
            resources.remove(trait_key_to_remove)
            
            # Add to target using appropriate method
            if hasattr(target, 'char_resources'):
                target.add_resource(resource_name, die_size)
            else:  # Organization
                target.add_org_resource(resource_name, die_size)
                
            self.msg(f"Transferred {resource_name} (d{int(die_size)}) from {source.name} to {target.name}.")
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
            
        # Delete the resource (case-insensitive search)
        resource_to_delete = None
        for key in resources.all():
            if key.lower() == name.lower():
                resource_to_delete = key
                break
                
        if resource_to_delete:
            resources.remove(resource_to_delete)
            self.msg(f"Deleted resource '{resource_to_delete}' from {owner.name}.")
        else:
            self.msg(f"No resource found named '{name}' on {owner.name}.")

    # ------------------------------------------------------------------
    # Resource disbursement management
    # ------------------------------------------------------------------

    def _parse_due_args(self):
        """Parse arguments for due management commands."""
        if not self.args:
            self.msg(
                "Usage: resource/due <target>[,<name>=<count>/<die>]"
                " or switches like /due/add,/due/clear"
            )
            return None, None, None
        segments = [segment.strip() for segment in self.args.split(",", 1)]
        target_spec = segments[0]
        spec = segments[1] if len(segments) > 1 else None
        return target_spec, spec, self.switches[1:] if len(self.switches) > 1 else []

    def _find_due_target(self, target_spec):
        from evennia.utils.search import search_object
        from typeclasses.organisations import Organisation
        from typeclasses.characters import Character

        matches = search_object(target_spec)
        if not matches:
            self.msg(f"Target '{target_spec}' not found.")
            return None
        target = matches[0]
        if not isinstance(target, (Character, Organisation)):
            self.msg(f"{target.name} cannot receive resource disbursements.")
            return None
        return target

    def manage_due(self):
        """View or update queued resource disbursements for a target."""
        target_spec, spec, sub_switches = self._parse_due_args()
        if not target_spec:
            return

        target = self._find_due_target(target_spec)
        if not target:
            return

        # Handle clearing all without a resource spec
        if not spec and sub_switches and sub_switches[0] == "clear":
            clear_resource_disbursements(target)
            self.msg(f"Cleared all recurring disbursements for {target.name}.")
            return

        if not spec:
            self._show_due(target)
            return

        parts = spec.split("/")
        if len(parts) not in (1, 2):
            self.msg("Specify <name>=<count>/<die> (e.g. Wealth=3/6 for 3x d6 Wealth).")
            return

        name_count = parts[0].strip()
        die_size = None
        if len(parts) == 2:
            try:
                die_size = int(parts[1])
                if die_size not in [4, 6, 8, 10, 12]:
                    self.msg("Die size must be one of: 4, 6, 8, 10, 12")
                    return
            except ValueError:
                self.msg("Die size must be a number.")
                return

        if "=" not in name_count:
            self.msg("Specify resource name and count as <name>=<count>/<die>.")
            return
        name_part, count_part = [p.strip() for p in name_count.split("=", 1)]
        try:
            count = int(count_part)
        except ValueError:
            self.msg("Count must be a number.")
            return
        
        # If no die size in second part, we need both name and die from first part
        if die_size is None:
            self.msg("Specify die size after count: <name>=<count>/<die>")
            return

        if not sub_switches:
            entry = set_resource_disbursement(target, name_part, die_size, count)
            if entry:
                self.msg(
                    f"Set due {entry['name']} d{entry['die_size']} for {target.name} to {entry['count']} (will receive {entry['count']}x d{entry['die_size']})."
                )
            else:
                self.msg(f"Removed due {name_part} d{die_size} for {target.name}.")
            return

        sub = sub_switches[0]
        if sub == "add":
            entry = increment_resource_disbursement(target, name_part, die_size, count)
            if entry:
                self.msg(
                    f"Adjusted due {entry['name']} d{entry['die_size']} for {target.name} to {entry['count']} (will receive {entry['count']}x d{entry['die_size']})."
                )
            else:
                self.msg(f"Cleared due {name_part} d{die_size} for {target.name}.")
        elif sub == "clear":
            set_resource_disbursement(target, name_part, die_size, 0)
            self.msg(f"Cleared due {name_part} d{die_size} for {target.name}.")
        else:
            self.msg(f"Unknown resource/due sub-switch '{sub}'.")

    def _show_due(self, target):
        from evennia.utils.evtable import EvTable

        disbursements = get_resource_disbursements(target)
        if not disbursements:
            self.msg(f"{target.name} has no recurring resource disbursements configured.")
            return

        table = EvTable("|wName|n", "|wDie|n", "|wCount|n", border="header")
        for entry in disbursements.values():
            table.add_row(entry["name"], f"d{entry['die_size']}", entry["count"])
        self.msg(f"Recurring disbursements for {target.name}:")
        self.msg(table)

    def disburse_resources(self):
        """Apply recurring resource disbursements for listed targets or all configured."""
        targets = []
        if self.args:
            specs = [part.strip() for part in self.args.split(",") if part.strip()]
            for spec in specs:
                target = self._find_due_target(spec)
                if target:
                    targets.append(target)
        else:
            from evennia.objects.models import ObjectDB

            seen = set()
            for obj in ObjectDB.objects.filter(
                db_attributes__db_key="resource_disbursements",
                db_attributes__db_category="resources",
            ).distinct():
                target = obj.typeclass or obj
                key = getattr(target, "id", id(target))
                if key in seen:
                    continue
                seen.add(key)
                targets.append(target)

        if not targets:
            self.msg("No targets found with recurring disbursements configured.")
            return

        total_allocated = 0
        messages = []
        for raw_target in targets:
            target = raw_target
            if hasattr(raw_target, "typeclass") and raw_target.typeclass:
                target = raw_target.typeclass
            if not target:
                continue

            disbursements = get_resource_disbursements(target)
            if not disbursements:
                continue
            applied = []
            for entry in disbursements.values():
                count = entry.get("count", 0)
                if count <= 0:
                    continue
                name = entry["name"]
                die_size = entry["die_size"]
                for _ in range(count):
                    try:
                        if hasattr(target, "add_resource"):
                            target.add_resource(name, die_size)
                        elif hasattr(target, "add_org_resource"):
                            target.add_org_resource(name, die_size)
                        else:
                            self.msg(f"{target.name} cannot receive resources; skipping.")
                            break
                    except ValueError as err:
                        self.msg(
                            f"Failed to add {name} d{die_size} to {target.name}: {err}"
                        )
                        break
                    else:
                        total_allocated += 1
                        applied.append((name, die_size))
            if applied:
                messages.append(
                    f"{target.name}: added {len(applied)} resources ("
                    + ", ".join(f"{n} d{d}" for n, d in applied)
                    + ")"
                )

        if not messages:
            self.msg("No disbursements were applied.")
            return

        self.msg("Processed resource disbursements:\n" + "\n".join(messages))
        self.msg(f"Total resources allocated: {total_allocated}")


class ResourceCmdSet(CmdSet):
    """
    Command set for resource management.
    """
    
    def at_cmdset_creation(self):
        """Add commands to the set."""
        self.add(CmdResource()) 