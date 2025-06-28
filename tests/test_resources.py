"""
Tests for resource system functionality.
"""

from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.organisations import CmdResource
from utils.resource_utils import get_unique_resource_name, validate_resource_owner
from utils.org_utils import get_org, get_char
from typeclasses.characters import Character
from typeclasses.organisations import Organisation
from evennia.contrib.rpg.traits import TraitHandler
from evennia import create_object

class TestResources(EvenniaTest):
    """Test cases for resource system functionality."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.cmd = CmdResource()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        
        # Set up message mocking
        self.caller = self.char1
        self.caller.msg = MagicMock()
        self.cmd.msg = self.caller.msg
        
        # Set up command attributes
        self.cmd.switches = []
        
        # Initialize trait handlers properly
        if not hasattr(self.char1, 'char_resources'):
            self.char1.char_resources = TraitHandler(self.char1, db_attribute_key="char_resources")
        
        # Create and set up an organization
        self.org = self.create_organisation()
        
        # Set up test resources
        self.setup_char_resources()
        
        # Set up permissions
        self.cmd.caller.permissions.add("Admin")
    
    def create_organisation(self):
        """Create a test organization."""
        org = create_object(Organisation, key="Test Org")
        if not hasattr(org, 'org_resources'):
            org.org_resources = TraitHandler(org, db_attribute_key="org_resources")
        
        # Add org resources
        org.org_resources.add("armory", "Armory", trait_type="static", base=8)
        org.org_resources.add("treasury", "Treasury", trait_type="static", base=6)
        
        return org
    
    def setup_char_resources(self):
        """Set up character resources."""
        # Add character resources
        self.char1.char_resources.add("gold", "Gold", trait_type="static", base=6)
        self.char1.char_resources.add("supplies", "Supplies", trait_type="static", base=4)
    
    def test_list_resources(self):
        """Test listing resources."""
        # Add test resources
        self.cmd.switches = ["char"]
        self.cmd.args = "self,armory=8"
        self.cmd.func()
        self.cmd.switches = ["char"]
        self.cmd.args = "self,treasury=6"
        self.cmd.func()
        
        # Test listing resources (no args lists caller's resources)
        self.cmd.switches = []
        self.cmd.args = ""
        self.cmd.func()
        output = str(self.cmd.msg.mock_calls[-1][1][0])  # Convert EvTable to string
        self.assertIn("armory", output)
        self.assertIn("treasury", output)
    
    def test_create_char_resource(self):
        """Test creating character resources."""
        # Test creating with valid die size
        self.cmd.switches = ["char"]
        self.cmd.args = "self,weapon=8"  # Using correct format
        self.cmd.func()
        output = str(self.cmd.msg.mock_calls[-1][1][0])
        self.assertIn("Added resource", output)
        
        # Verify resource was created
        trait = self.char1.char_resources.get("weapon")
        self.assertIsNotNone(trait)
        self.assertEqual(int(trait.base), 8)
        
        # Test creating with invalid die size
        self.cmd.switches = ["char"]
        self.cmd.args = "self,invalid=7"  # Using correct format
        self.cmd.func()
        output = str(self.cmd.msg.mock_calls[-1][1][0])
        self.assertIn("Die size must be", output)
    
    def test_create_org_resource(self):
        """Test creating organization resources."""
        # Test creating with valid die size
        self.cmd.switches = ["org"]
        self.cmd.args = "Test Org,barracks=8"  # Using correct format
        self.cmd.func()
        output = str(self.cmd.msg.mock_calls[-1][1][0])
        self.assertIn("Added resource", output)
        
        # Verify resource was created
        trait = self.org.org_resources.get("barracks")
        self.assertIsNotNone(trait)
        self.assertEqual(int(trait.base), 8)
        
        # Test creating with invalid die size
        self.cmd.switches = ["org"]
        self.cmd.args = "Test Org,invalid=7"  # Using correct format
        self.cmd.func()
        output = str(self.cmd.msg.mock_calls[-1][1][0])
        self.assertIn("Die size must be", output)
    
    def test_transfer_resource(self):
        """Test transferring resources."""
        # Create test resource
        self.cmd.switches = ["char"]
        self.cmd.args = "self,armory=8"
        self.cmd.func()
        
        # Create target character and initialize trait handler
        target = self.char2
        if not hasattr(target, 'char_resources'):
            target.char_resources = TraitHandler(target, db_attribute_key="char_resources")
        
        # Test transfer
        self.cmd.switches = ["transfer"]
        self.cmd.args = f"{self.char1.name}:armory = {target.name}"  # source:resource = target
        self.cmd.func()
        output = self.cmd.msg.mock_calls[-1][1][0]
        self.assertIn("Transferred", output)
        
        # Verify transfer
        self.assertIsNone(self.char1.char_resources.get("armory"))
        self.assertIsNotNone(target.char_resources.get("armory"))
    
    def test_delete_resource(self):
        """Test deleting resources."""
        # Create test resource
        self.cmd.switches = ["char"]
        self.cmd.args = "self,armory=8"
        self.cmd.func()
        
        # Test deletion
        self.cmd.switches = ["delete"]
        self.cmd.args = f"{self.char1.name},armory"  # owner,resource format
        self.cmd.func()
        output = self.cmd.msg.mock_calls[-1][1][0]
        self.assertIn("Deleted", output)
        
        # Verify deletion
        self.assertIsNone(self.char1.char_resources.get("armory"))
    
    def test_resource_utils(self):
        """Test resource utility functions."""
        # Test unique name generation
        name = get_unique_resource_name("gold", self.char1.char_resources)
        self.assertEqual(name, "gold_1")  # Since "gold" exists
        
        # Test unique name for new resource
        name = get_unique_resource_name("new", self.char1.char_resources)
        self.assertEqual(name, "new")  # Should use original name
        
        # Test resource owner validation
        obj = self.obj1  # Regular object without resources
        self.assertFalse(validate_resource_owner(obj))
        self.assertTrue(validate_resource_owner(self.char1))

if __name__ == '__main__':
    unittest.main() 