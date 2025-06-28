"""
Tests for the organization system.
"""

from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.organisations import CmdOrg, CmdResource
from typeclasses.organisations import Organisation
from evennia import create_object
from utils.org_utils import validate_rank, parse_equals, parse_comma, get_org, get_char, get_org_and_char
import unittest

class TestOrganisation(EvenniaTest):
    """Test cases for organization functionality."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Set up command
        self.cmd = CmdOrg()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        self.cmd.session = self.session
        
        # Set up message mocking
        self.caller = self.char1
        self.caller.msg = MagicMock()
        self.cmd.msg = self.caller.msg
        
        # Create a test organization
        self.org = create_object(
            typeclass=Organisation,
            key="Test House"
        )
        self.org.db.description = "A test noble house"
        self.org.db.members = {}  # Initialize empty members dict
        self.org.db.rank_names = {  # Initialize rank names
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
        
        # Initialize command properties
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.lhs = ""
        self.cmd.rhs = ""
        
        # Give admin permissions for staff-only actions
        self.caller.permissions.add("Admin")
        
        # Add helper methods to command
        self.cmd._validate_rank = lambda rank_str, default=None: validate_rank(rank_str, default, self.caller)
        self.cmd._parse_equals = lambda usage_msg: parse_equals(self.cmd.args)
        self.cmd._parse_comma = lambda text, expected_parts=2, usage_msg=None: parse_comma(text, expected_parts)
        self.cmd._get_org = lambda org_name: get_org(org_name, self.caller)
        self.cmd._get_character = lambda char_name: get_char(char_name, self.caller)
        self.cmd._get_org_and_char = lambda org_name, char_name: get_org_and_char(org_name, char_name, self.caller)
        
    def test_org_creation(self):
        """Test creating a new organization."""
        # Set up command arguments
        self.cmd.switches = ["create"]
        self.cmd.args = "New House"
        
        # Run the command
        self.cmd.func()
        
        # Verify organization was created
        orgs = Organisation.objects.filter(db_key="New House")
        self.assertTrue(len(orgs) > 0)
        
        # Get the created organization
        org = orgs[0]
        
        # Verify organization properties
        self.assertEqual(org.db.description, "No description set.")
        self.assertEqual(len(org.db.rank_names), 10)  # Should have 10 ranks
        self.assertEqual(len(org.db.members), 0)  # Should start with no members
        
    def test_member_management(self):
        """Test adding and removing members."""
        # Add member
        self.org.add_member(self.char1, rank=3)
        
        # Verify member was added
        self.assertIn(self.char1.id, self.org.db.members)
        self.assertEqual(self.org.get_member_rank(self.char1), 3)
        self.assertEqual(self.org.get_member_rank_name(self.char1), "Noble Family")
        
        # Verify character's organisations were updated
        self.assertIn(self.org.id, self.char1.organisations)
        self.assertEqual(self.char1.organisations[self.org.id], 3)
        
        # Remove member
        self.org.remove_member(self.char1)
        
        # Verify member was removed
        self.assertNotIn(self.char1.id, self.org.db.members)
        self.assertNotIn(self.org.id, self.char1.organisations)
        self.assertIsNone(self.org.get_member_rank(self.char1))
        self.assertIsNone(self.org.get_member_rank_name(self.char1))
        
    def test_rank_management(self):
        """Test managing member ranks."""
        # Add member with initial rank
        self.org.add_member(self.char1, rank=5)
        self.assertEqual(self.org.get_member_rank(self.char1), 5)
        self.assertEqual(self.char1.organisations[self.org.id], 5)
        
        # Change rank
        self.org.set_rank(self.char1, 3)
        self.assertEqual(self.org.get_member_rank(self.char1), 3)
        self.assertEqual(self.char1.organisations[self.org.id], 3)
        
        # Try invalid rank
        self.assertFalse(self.org.set_rank(self.char1, 11))
        self.assertEqual(self.org.get_member_rank(self.char1), 3)  # Should not change
        self.assertEqual(self.char1.organisations[self.org.id], 3)  # Should not change
        
        # Try setting rank of non-member
        self.assertFalse(self.org.set_rank(self.char2, 5))
        
    def test_member_listing(self):
        """Test listing members."""
        # Add two members with different ranks
        self.org.add_member(self.char1, rank=3)
        self.org.add_member(self.char2, rank=5)
        
        # Get member list
        members = self.org.get_members()
        
        # Should be sorted by rank (highest/lowest number first)
        self.assertEqual(len(members), 2)
        self.assertEqual(members[0][0], self.char1)  # Rank 3 should be first
        self.assertEqual(members[0][1], 3)
        self.assertEqual(members[1][0], self.char2)  # Rank 5 should be second
        self.assertEqual(members[1][1], 5)
        
    def test_rank_names(self):
        """Test setting and getting rank names."""
        # Test setting a rank name
        self.cmd.switches = ["rankname"]
        self.cmd.args = "Test House=5,Servant"  # Changed format to match command
        self.cmd.func()
        
        # Verify rank name was set
        self.assertEqual(self.org.db.rank_names[5], "Servant")
        
        # Test invalid rank number
        self.cmd.args = "Test House=11,Invalid"  # Rank 11 doesn't exist
        self.cmd.func()
        
        # Verify rank name wasn't set
        self.assertNotIn(11, self.org.db.rank_names)
        
    def test_permissions(self):
        """Test permission checks."""
        # Try to create an organization without permission
        with unittest.mock.patch.object(self.cmd, 'access', return_value=False):
            self.cmd.switches = ["create"]
            self.cmd.args = "New House"
            self.cmd.func()
            
            # Verify organization wasn't created
            orgs = Organisation.objects.filter(db_key="New House")
            self.assertEqual(len(orgs), 0)
            self.caller.msg.assert_called_with("You don't have permission to create organizations.")
        
        # Try to delete an organization without permission
        org = create_object(
            typeclass=Organisation,
            key="Test House"
        )
        
        with unittest.mock.patch.object(self.cmd, 'access', return_value=False):
            self.cmd.switches = ["delete"]
            self.cmd.args = "Test House"
            self.cmd.func()
            
            # Verify organization wasn't deleted
            self.assertIsNotNone(org.pk)
            self.caller.msg.assert_called_with("You don't have permission to delete organizations.")
        
        # Clean up
        org.delete()
        
    def test_viewing(self):
        """Test viewing organization information."""
        # Add a member for testing
        self.org.add_member(self.char1, 3)
        
        # View organization info
        self.cmd.switches = []
        self.cmd.args = "Test House"
        self.cmd.func()
        
        # Verify output was sent
        self.assertTrue(self.caller.msg.called)
        
    def test_deletion(self):
        """Test deleting an organization."""
        # Add a member for testing cleanup
        self.org.add_member(self.char1, 3)
        
        # Delete the organization
        self.cmd.switches = ["delete"]
        self.cmd.args = "Test House"
        self.cmd.func()
        
        # First call should ask for confirmation
        self.assertTrue(self.caller.db.delete_org_confirming)
        
        # Second call should delete
        self.cmd.func()
        
        # Verify organization was deleted
        self.assertFalse(Organisation.objects.filter(db_key="Test House").exists())


class TestResource(EvenniaTest):
    """Test cases for organization resources."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Set up command
        self.cmd = CmdResource()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        self.cmd.session = self.session
        
        # Set up message mocking
        self.caller = self.char1
        self.caller.msg = MagicMock()
        self.cmd.msg = self.caller.msg
        
        # Create a test organization
        self.org = create_object(
            typeclass=Organisation,
            key="Test House"
        )
        self.org.db.description = "A test noble house"
        self.org.db.members = {}  # Initialize empty members dict
        self.org.db.rank_names = {  # Initialize rank names
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
        
        # Initialize command properties
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.lhs = ""
        self.cmd.rhs = ""
        
        # Give admin permissions for staff-only actions
        self.caller.permissions.add("Admin")
        
        # Add helper methods to command
        self.cmd._parse_equals = lambda usage_msg: parse_equals(self.cmd.args)
        self.cmd._parse_comma = lambda text, expected_parts=2, usage_msg=None: parse_comma(text, expected_parts)
        self.cmd._get_org = lambda org_name: get_org(org_name, self.caller)
        self.cmd._get_char = lambda char_name: get_char(char_name, self.caller, check_resources=True)
        
    def test_resource_creation(self):
        """Test creating organization resources."""
        # Create a resource
        self.cmd.switches = ["org"]
        self.cmd.args = "Test House,armory=8"
        self.cmd.func()
        
        # Verify resource was created
        self.assertIsNotNone(self.org.org_resources.get("armory"))
        self.assertEqual(self.org.org_resources.get("armory").value, 8)
        
    def test_resource_transfer(self):
        """Test transferring resources."""
        # Create a resource first
        self.org.add_org_resource("gold", 6)
        
        # Transfer to a character
        self.cmd.switches = ["transfer"]
        self.cmd.args = f"Test House:gold={self.char1.name}"
        self.cmd.func()
        
        # Verify resource was transferred
        self.assertIsNone(self.org.org_resources.get("gold"))
        self.assertIsNotNone(self.char1.char_resources.get("gold"))
        
    def test_resource_deletion(self):
        """Test deleting resources."""
        # Create a resource first
        self.org.add_org_resource("armory", 8)
        
        # Delete the resource
        self.cmd.switches = ["delete"]
        self.cmd.args = "Test House,armory"
        self.cmd.func()
        
        # Verify resource was deleted
        self.assertIsNone(self.org.org_resources.get("armory"))
        
    def test_resource_permissions(self):
        """Test resource permission checks."""
        # Clear resources directly
        self.org.org_resources.clear()
        
        # Try to create a resource without permission
        with unittest.mock.patch.object(self.cmd, 'access', return_value=False):
            self.cmd.switches = ["org"]
            self.cmd.args = "Test House,new_resource=8"
            self.cmd.func()
            
            # Verify resource wasn't created
            self.assertIsNone(self.org.org_resources.get("new_resource"))
            self.caller.msg.assert_called_with("You don't have permission to create organization resources.")
        
        # Clean up
        self.org.delete()
        
    def test_resource_listing(self):
        """Test listing resources."""
        # Create some resources
        self.org.add_org_resource("armory", 8)
        self.org.add_org_resource("treasury", 6)
        
        # List resources
        self.cmd.switches = []
        self.cmd.args = ""
        self.cmd.func()
        
        # Verify output was sent
        self.assertTrue(self.caller.msg.called) 