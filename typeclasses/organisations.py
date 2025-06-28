"""
Organisations

Organisations represent groups like noble houses, guilds, or factions.
They can have members with different ranks and provide resources to their members.
"""

from evennia.objects.objects import DefaultObject
from evennia.utils import lazy_property
from evennia.utils.search import search_object
from .objects import ObjectParent
from evennia.contrib.rpg.traits import TraitHandler
from utils.resource_utils import get_unique_resource_name, validate_die_size
from evennia.objects.models import ObjectDB


class Organisation(ObjectParent, DefaultObject):
    """
    An organisation that characters can join.
    Organisations can have different ranks and provide resources to members.
    Organisations are abstract concepts and do not have a physical location.
    """
    
    MAX_RANKS = 10
    
    @lazy_property
    def org_resources(self):
        """TraitHandler that manages organisation resources."""
        return TraitHandler(self, db_attribute_key="org_resources")
        
    def at_object_creation(self):
        """Called when object is first created."""
        super().at_object_creation()
        
        # Set default locks
        self.locks.add(
            "examine:all();"  # Anyone can examine organizations
            "edit:perm(Admin);"  # Only Admin can edit org settings
            "members:perm(Admin)"  # Only Admin can manage members
        )
        
        # Initialize description
        self.db.description = "No description set."
        
        # Initialize rank names (1-10)
        self.db.rank_names = {
            1: "Head of House",      
            2: "Minister",        
            3: "Noble Family",       
            4: "Senior Servant",        
            5: "Servant",         
            6: "Junior Servant",        
            7: "Affiliate",   
            8: "Extended Family",      
            9: "",       
            10: ""     
        }
        
        # Initialize members dict {character_id: rank_number}
        self.db.members = {}
        
        # Initialize resources handler
        _ = self.org_resources
        
    def at_post_move(self, source_location, **kwargs):
        """Override to prevent movement."""
        return False
        
    def move_to(self, destination, **kwargs):
        """Override to prevent movement."""
        return False
        
    @property
    def location(self):
        """Override to always return None."""
        return None
        
    @location.setter
    def location(self, value):
        """Override to prevent setting location."""
        pass
        
    @property
    def home(self):
        """Override to always return None."""
        return None
        
    @home.setter
    def home(self, value):
        """Override to prevent setting home."""
        pass
        
    def add_org_resource(self, name, die_size):
        """Add a resource to the organisation.
        
        Args:
            name (str): Name of the resource
            die_size (int): Size of the die (4, 6, 8, 10, or 12)
            
        Returns:
            bool: True if added successfully
            
        Raises:
            ValueError: If die size is invalid
        """
        if not validate_die_size(die_size):
            raise ValueError(f"Invalid die size: {die_size}")
            
        # Get a unique name for the resource
        unique_name = get_unique_resource_name(name, self.org_resources)
            
        # Add the resource with the die size as the base value
        self.org_resources.add(
            unique_name,
            base=die_size  # Use base instead of value
        )
        return True
        
    def remove_org_resource(self, name):
        """Remove a resource from the organisation.
        
        Args:
            name (str): Name of the resource to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if self.org_resources.get(name):
            self.org_resources.remove(name)
            return True
        return False
        
    def transfer_resource(self, resource_name, target):
        """Transfer a resource to another organisation or character.
        
        Args:
            resource_name (str): Name of the resource to transfer
            target (Character or Organisation): Who to transfer to
            
        Returns:
            bool: True if transferred successfully
            
        Raises:
            ValueError: If resource not found or target is invalid
        """
        trait = self.org_resources.get(resource_name)
        if not trait:
            raise ValueError(f"Resource '{resource_name}' not found")
            
        from typeclasses.characters import Character
        if not (isinstance(target, type(self)) or isinstance(target, Character)):
            raise ValueError("Can only transfer resources to organisations or characters")
            
        # Get the die size before removing
        die_size = trait.value
        
        # Remove from self
        self.org_resources.remove(resource_name)
        
        # Add to target
        if isinstance(target, Character):
            target.add_resource(resource_name, die_size)
        else:
            target.add_org_resource(resource_name, die_size)
            
        return True
        
    def get_resources(self):
        """Get a formatted list of all resources.
        
        Returns:
            list: List of (name, die_size) tuples
        """
        resources = []
        for key in self.org_resources.all():
            trait = self.org_resources.get(key)
            resources.append((key, trait.value))
        return sorted(resources)
        
    def add_member(self, character, rank=4):
        """Add a character as a member.
        
        Args:
            character: The character to add
            rank (int): Their rank number (1-10)
            
        Returns:
            bool: True if added successfully
        """
        if not 1 <= rank <= 10:
            return False
            
        self.db.members[character.id] = rank
        # Update character's organisations attribute
        orgs = character.organisations
        orgs[self.id] = rank  # Store using org ID for consistency
        character.attributes.add('organisations', orgs, category='organisations')
        return True
        
    def remove_member(self, character):
        """Remove a character from membership.
        
        Args:
            character: The character to remove
            
        Returns:
            bool: True if removed successfully
        """
        if character.id in self.db.members:
            del self.db.members[character.id]
            # Update character's organisations attribute
            orgs = character.organisations
            if self.id in orgs:  # Check org ID for consistency
                del orgs[self.id]
                character.attributes.add('organisations', orgs, category='organisations')
            return True
        return False
        
    def set_rank(self, character, rank):
        """Set a member's rank.
        
        Args:
            character: The character to update
            rank (int): Their new rank (1-10)
            
        Returns:
            bool: True if set successfully
        """
        if character.id not in self.db.members:
            return False
            
        if not 1 <= rank <= 10:
            return False
            
        self.db.members[character.id] = rank
        # Update character's organisations attribute
        orgs = character.organisations
        orgs[self.id] = rank  # Store using org ID for consistency
        character.attributes.add('organisations', orgs, category='organisations')
        return True
        
    def get_member_rank(self, character):
        """Get a member's rank number.
        
        Args:
            character: The character to check
            
        Returns:
            int or None: Their rank number, or None if not a member
        """
        return self.db.members.get(character.id)
        
    def get_member_rank_name(self, character):
        """Get a member's rank name.
        
        Args:
            character: The character to check
            
        Returns:
            str or None: Their rank name, or None if not a member
        """
        rank = self.get_member_rank(character)
        if rank is None:
            return None
        return self.db.rank_names.get(rank, f"Rank {rank}")
        
    def set_rank_name(self, rank, name):
        """Set the name for a rank number.
        
        Args:
            rank (int): The rank number (1-10)
            name (str): The name for this rank
            
        Returns:
            bool: True if set successfully
        """
        if not 1 <= rank <= 10:
            return False
            
        self.db.rank_names[rank] = name
        return True
        
    def get_members(self):
        """Get all members and their ranks.
        
        Returns:
            list: List of (character, rank_number, rank_name) tuples,
                  sorted by rank (highest first) then name
        """
        members = []
        for char_id, rank in self.db.members.items():
            char = ObjectDB.objects.get(id=char_id)
            rank_name = self.db.rank_names.get(rank, f"Rank {rank}")
            members.append((char, rank, rank_name))
            
        return sorted(
            members,
            key=lambda x: (-x[1], x[0].key)  # Sort by rank (desc) then name
        )
        
    def delete(self):
        """
        Delete the organisation and clean up all references.
        """
        # Remove all members
        for char_id in list(self.db.members.keys()):
            char = ObjectDB.objects.get(id=char_id)
            self.remove_member(char)
        
        # Delete the organisation
        super().delete() 