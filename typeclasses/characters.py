"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.utils import lazy_property, search
from evennia.contrib.rpg.traits import TraitHandler
from .objects import ObjectParent
from utils.trait_definitions import ATTRIBUTES, SKILLS, DISTINCTIONS
from utils.resource_utils import get_unique_resource_name, validate_die_size
from utils import worn_items as worn_utils
from evennia.comms.models import Msg

# Character status constants
STATUS_UNFINISHED = "unfinished"
STATUS_AVAILABLE = "available"
STATUS_ACTIVE = "active"
STATUS_GONE = "gone"

class Character(ObjectParent, DefaultCharacter):
    """
    The Character represents a playable character in the game world.
    It implements the Empire's Cortex Prime ruleset using Evennia's trait system.
    
    Prime Sets (one die from each is used in almost every roll):
    - Distinctions (d8, can be used as d4 for plot point)
    - Attributes (d4-d12, representing innate capabilities)
    - Skills (d4-d12, representing training and expertise)
    
    Additional Sets:
    - Resources (organizational dice pools)
    - Signature Assets (remarkable items or NPC companions)
    - Temporary Assets (short-term advantages or items)
    """

    @lazy_property
    def traits(self):
        """Main trait handler for general traits like plot points."""
        return TraitHandler(self, db_attribute_key="char_traits")
        
    @lazy_property
    def distinctions(self):
        """
        Distinctions are always d8 and can be used as d4 for a plot point.
        Every character has three:
        1. Character concept (e.g. "Bold Adventurer")
        2. Culture
        3. How they are perceived by others
        """
        return TraitHandler(self, db_attribute_key="char_distinctions")
        
    @lazy_property
    def character_attributes(self):
        """
        Character attributes (d4-d12)
        """
        return TraitHandler(self, db_attribute_key="char_attributes")
        
    @lazy_property
    def skills(self):
        """
        Character skills (d4-d12)
        """
        return TraitHandler(self, db_attribute_key="skills")
        
    @lazy_property
    def signature_assets(self):
        """
        Signature assets (d4-d12)
        """
        return TraitHandler(self, db_attribute_key="char_signature_assets")

    @lazy_property
    def powers(self):
        """
        Powers (d4-d12)
        Represent supernatural or extraordinary abilities
        """
        return TraitHandler(self, db_attribute_key="powers")

    @lazy_property
    def char_resources(self):
        """
        TraitHandler that manages character resources.
        Each trait represents a die pool (d4-d12).
        """
        return TraitHandler(self, db_attribute_key="char_resources")

    @lazy_property
    def temporary_assets(self):
        """
        Temporary assets that can be added or removed at will.
        These represent short-term advantages or items.
        """
        return TraitHandler(self, db_attribute_key="char_temp_assets")

    @lazy_property
    def complications(self):
        """
        Complications that can be added or removed at will.
        These represent hindrances or problems that make actions more difficult.
        Unlike other traits, complications don't add dice to rolls but instead
        modify difficulty or provide narrative prompts.
        """
        return TraitHandler(self, db_attribute_key="char_complications")

    @property
    def organisations(self):
        """
        Get all organisations this character belongs to.
        Returns a dict of {org_id: rank_number}
        """
        return self.attributes.get('organisations', default={}, category='organisations')

    @property
    def notes(self):
        """
        Get all notes for this character.
        Returns a list of note dictionaries.
        """
        return self.db.notes or []

    @notes.setter
    def notes(self, value):
        """
        Set the notes list for this character.
        """
        self.db.notes = value

    def get_worn_items(self):
        """Return worn items as live objects, cleaning stale references."""
        return worn_items.get_worn_items(self)

    def add_worn_item(self, item):
        """Track an item as worn."""
        return worn_utils.add_worn_item(self, item)

    def remove_worn_item(self, item):
        """Stop tracking an item as worn."""
        return worn_utils.remove_worn_item(self, item)
        
    def at_object_creation(self):
        """
        Called only once when object is first created.
        Initialize all trait handlers and set up default traits.
        """
        # Call parent to set up basic character properties and permissions
        super().at_object_creation()

        # Initialize plot points
        self.traits.add("plot_points", value=1, min=0)

        # Initialize character background and personality
        self.db.background = "No background has been set."
        self.db.personality = "No personality has been set."
        self.db.notable_traits = "No notable traits have been set."
        self.db.realm = "No realm has been set."

        # Initialize character status (for roster system)
        self.db.status = STATUS_UNFINISHED

        # Initialize organization memberships
        self.attributes.add('organisations', {}, category='organisations')

        # Initialize attributes
        for trait in ATTRIBUTES:
            existing = self.character_attributes.get(trait.key)
            if existing:
                existing.base = trait.default_value
            else:
                self.character_attributes.add(
                    trait.key,
                    value=trait.default_value,
                    name=trait.name
                )
                # Ensure .base is set correctly
                self.character_attributes.get(trait.key).base = trait.default_value

        # Initialize skills
        for trait in SKILLS:
            existing = self.skills.get(trait.key)
            if existing:
                existing.base = trait.default_value
            else:
                self.skills.add(
                    trait.key,
                    value=trait.default_value,
                    name=trait.name
                )
                # Ensure .base is set correctly
                self.skills.get(trait.key).base = trait.default_value

        # Initialize distinctions
        for trait in DISTINCTIONS:
            existing = self.distinctions.get(trait.key)
            if existing:
                existing.base = trait.default_value
            else:
                self.distinctions.add(
                    trait.key,
                    value=trait.default_value,
                    desc=trait.description,
                    name=trait.name
                )
                # Ensure .base is set correctly
                self.distinctions.get(trait.key).base = trait.default_value

        # Initialize resources handler (will be initialized on first access)
        _ = self.char_resources

        # Initialize powers handler (will be initialized empty)
        _ = self.powers

        # Initialize signature assets handler (will be initialized empty)
        _ = self.signature_assets

        # Initialize temporary assets handler (will be initialized empty)
        _ = self.temporary_assets
        
        # Initialize complications handler (will be initialized empty)
        _ = self.complications

        # Initialize empty list for offline board notifications
        self.db.offline_board_notifications = []

        # Initialize home location
        self.db.home_location = None

        # Initialize special effects (staff-only text field)
        self.db.special_effects = ""
        
        # Initialize secret information (staff/owner-only text field)
        self.db.secret_information = ""
        
        # Initialize notes list
        self.db.notes = []

    def at_init(self):
        """
        Called when object is first created and after it is loaded from cache.
        Ensures trait handlers are initialized.
        """
        # Call parent to set up basic object properties
        super().at_init()
        
        # Force initialize all trait handlers without sending messages
        # Wrap in try-catch to handle potential database routing issues
        try:
            _ = self.traits
            _ = self.distinctions
            _ = self.character_attributes
            _ = self.skills
            _ = self.signature_assets
            _ = self.powers
            _ = self.char_resources
        except ValueError as e:
            if "instance is on database" in str(e):
                # Database routing issue - trait handlers will be initialized on first access instead
                # Log which character had the issue for debugging
                from evennia.utils import logger
                logger.log_err(f"Database routing issue for character {self.name} (#{self.id}): {e}")
                pass
            else:
                raise

    def return_appearance(self, looker, **kwargs):
        """
        This formats the character's appearance for display.
        Adds worn items to the description.
        """
        # Get the base appearance
        appearance = super().return_appearance(looker, **kwargs)
        
        # Add worn items if any
        worn_items = self.get_worn_items()
        if worn_items:
            worn_desc = "\n\n" + self.name + " is wearing:\n"
            for item in worn_items:
                name = item.get_display_name(looker) if hasattr(item, "get_display_name") else item.name
                worn_desc += f"  {name}|n\n"
            appearance += worn_desc
        
        return appearance
    
    def at_post_puppet(self):
        """
        Called just after puppeting has completed.
        Ensures trait handlers and command set are available.
        Shows any stored notifications.
        """
        # Call parent to handle account-character connection
        super().at_post_puppet()
        
        # Ensure trait handlers are initialized
        _ = self.traits
        _ = self.distinctions
        _ = self.character_attributes
        _ = self.skills
        _ = self.signature_assets
        _ = self.powers
        _ = self.char_resources
        
        # Check for unread mail
        unread_mail = Msg.objects.get_by_tag(category="mail").filter(db_receivers_objects=self).filter(db_tags__db_key="new")
        if unread_mail:
            self.msg("|wYou have %d unread mail message%s waiting.|n" % (unread_mail.count(), "s" if unread_mail.count() != 1 else ""))
        
        # Show any stored notifications
        notifications = self.attributes.get("_stored_notifications", [])
        if notifications:
            self.msg("\n".join(notifications))
            self.attributes.remove("_stored_notifications")

    def at_msg_receive(self, text=None, from_obj=None, **kwargs):
        """
        Called when this character receives a message.
        
        Args:
            text (str or tuple): The message text. If a tuple, it contains
                               (message, message_options)
            from_obj (Object): The sender of the message
            **kwargs: Additional keyword arguments
        """
        # Handle board messages specially
        if isinstance(text, tuple) and len(text) > 1 and isinstance(text[1], dict) and text[1].get("type") == "board_post":
            return True
            
        # Let the parent handle other messages
        return super().at_msg_receive(text, from_obj, **kwargs)


            
    def at_pre_unpuppet(self):
        """
        Called just before un-puppeting. Remove character from any places.
        """
        # Call parent first
        super().at_pre_unpuppet()
        
        # Clean up places in current location
        if self.location and hasattr(self.location, 'db') and self.location.db.places:
            self._cleanup_places(self.location)
            
    def at_pre_move(self, destination, **kwargs):
        """
        Called just before moving. Remove character from any places
        in the current location.
        
        Args:
            destination: The location we're moving to
            **kwargs: Arbitrary keyword arguments
        """
        # Call parent first
        result = super().at_pre_move(destination, **kwargs)
        
        # Clean up places in current location before leaving
        if self.location and hasattr(self.location, 'db') and self.location.db.places:
            self._cleanup_places(self.location)
            
        return result
        
    def at_object_delete(self):
        """Called just before object deletion. Remove character from any places."""
        try:
            if self.location and getattr(self.location, 'db', None) and self.location.db.places:
                self._cleanup_places(self.location)
        except Exception:
            pass  # Don't let place cleanup prevent deletion
        super().at_object_delete()
        return True
            
    def _cleanup_places(self, room):
        """
        Remove this character from any places in the given room.
        
        Args:
            room: The room to clean up places in
        """
        places = room.db.places or {}
        
        for place_key, place_data in places.items():
            characters = place_data.get("characters", [])
            if self in characters:
                characters.remove(self)
                place_data["characters"] = characters
                
                # Announce to others at the place
                place_name = place_data.get("name", place_key)
                for char in characters:
                    if hasattr(char, 'msg'):
                        char.msg(f"{self.name} leaves {place_name}.")
                        
        # Save the updated places
        room.db.places = places

    def add_resource(self, name, die_size):
        """
        Add a resource to the character.
        
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
        unique_name = get_unique_resource_name(name, self.char_resources)
            
        # Add the resource with the die size as the base value
        self.char_resources.add(
            unique_name,
            base=die_size  # Use base instead of value
        )
        return True
        
    def remove_resource(self, name):
        """
        Remove a resource from the character.
        
        Args:
            name (str): Name of the resource to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if self.char_resources.get(name):
            self.char_resources.remove(name)
            return True
        return False
        
    def transfer_resource(self, resource_name, target):
        """
        Transfer a resource to another character or organisation.
        
        Args:
            resource_name (str): Name of the resource to transfer
            target (Character or Organisation): Who to transfer to
            
        Returns:
            bool: True if transferred successfully
            
        Raises:
            ValueError: If resource not found or target is invalid
        """
        trait = self.char_resources.get(resource_name)
        if not trait:
            raise ValueError(f"Resource '{resource_name}' not found")
            
        from typeclasses.organisations import Organisation
        if not (isinstance(target, type(self)) or isinstance(target, Organisation)):
            raise ValueError("Can only transfer resources to characters or organisations")
            
        # Get the die size before removing
        die_size = trait.value
        
        # Add to target first so we can roll back if needed
        try:
            if isinstance(target, Organisation):
                target.add_org_resource(resource_name, die_size)
            else:
                target.add_resource(resource_name, die_size)
        except Exception:
            # If target addition fails, keep the resource and re-raise
            raise
        else:
            # Remove from self only once addition succeeds
            self.char_resources.remove(resource_name)
        
        return True
        
    def get_resources(self):
        """
        Get a formatted list of all resources.
        
        Returns:
            list: List of (name, die_size) tuples
        """
        resources = []
        for key in self.char_resources.all():
            trait = self.char_resources.get(key)
            resources.append((key, trait.value))
        return sorted(resources)

    @property
    def home_location(self):
        """Get character's home location."""
        return self.db.home_location

    @home_location.setter
    def home_location(self, value):
        """Set character's home location."""
        self.db.home_location = value

    def can_set_home(self, room):
        """
        Check if character can set this room as their home.
        
        Args:
            room: The room to check
            
        Returns:
            bool: True if character can set this as home
        """
        return room.has_access(self)
