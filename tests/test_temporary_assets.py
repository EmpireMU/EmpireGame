"""
Tests for temporary assets management commands.
"""

from evennia.utils.test_resources import EvenniaTest
from commands.temporary_assets import CmdTemporaryAsset
from typeclasses.characters import Character


class TestTemporaryAssets(EvenniaTest):
    """Test temporary asset commands."""
    
    def setUp(self):
        super().setUp()
        # Create test characters
        self.char1 = Character.create("TestChar1", char_typeclass=Character)
        self.char2 = Character.create("TestChar2", char_typeclass=Character)
        self.staff_char = Character.create("StaffChar", char_typeclass=Character)
        
        # Give staff permissions to staff_char
        self.staff_char.permissions.add("Builder")
        
        # Create the command
        self.cmd = CmdTemporaryAsset()
    
    def test_regular_asset_commands(self):
        """Test regular asset add/remove commands."""
        # Test adding asset
        self.cmd.caller = self.char1
        self.cmd.args = "High Ground=8"
        self.cmd.switches = ["add"]
        self.cmd.func()
        
        # Check asset was added
        asset = self.char1.temporary_assets.get("high_ground")
        self.assertIsNotNone(asset)
        self.assertEqual(asset.value, 8)
        
        # Test listing assets
        self.cmd.switches = []
        self.cmd.args = ""
        self.cmd.func()
        
        # Test removing asset
        self.cmd.switches = ["remove"]
        self.cmd.args = "High Ground"
        self.cmd.func()
        
        # Check asset was removed
        asset = self.char1.temporary_assets.get("high_ground")
        self.assertIsNone(asset)
    
    def test_gm_add_command(self):
        """Test GM add command with character/asset format."""
        # Test with staff permissions
        self.cmd.caller = self.staff_char
        self.cmd.args = "TestChar1/Prepared=6"
        self.cmd.switches = ["gmadd"]
        self.cmd.func()
        
        # Check asset was added to target character
        asset = self.char1.temporary_assets.get("prepared")
        self.assertIsNotNone(asset)
        self.assertEqual(asset.value, 6)
        self.assertEqual(asset.name, "Prepared")
    
    def test_gm_remove_command(self):
        """Test GM remove command with character/asset format."""
        # First add an asset to remove
        self.char1.temporary_assets.add("test_asset", value=8, base=8, name="Test Asset")
        
        # Test with staff permissions
        self.cmd.caller = self.staff_char
        self.cmd.args = "TestChar1/Test Asset"
        self.cmd.switches = ["gmrem"]
        self.cmd.func()
        
        # Check asset was removed
        asset = self.char1.temporary_assets.get("test_asset")
        self.assertIsNone(asset)
    
    def test_gm_commands_without_permissions(self):
        """Test that GM commands fail without staff permissions."""
        # Test gmadd without permissions
        self.cmd.caller = self.char1  # Non-staff character
        self.cmd.args = "TestChar2/Something=6"
        self.cmd.switches = ["gmadd"]
        self.cmd.func()
        
        # Check asset was not added
        asset = self.char2.temporary_assets.get("something")
        self.assertIsNone(asset)
        
        # Test gmrem without permissions
        self.char2.temporary_assets.add("test", value=6, base=6, name="Test")
        self.cmd.args = "TestChar2/Test"
        self.cmd.switches = ["gmrem"]
        self.cmd.func()
        
        # Check asset was not removed
        asset = self.char2.temporary_assets.get("test")
        self.assertIsNotNone(asset)
    
    def test_gm_commands_invalid_format(self):
        """Test GM commands with invalid format."""
        self.cmd.caller = self.staff_char
        
        # Test gmadd without character/asset format
        self.cmd.args = "BadFormat=6"
        self.cmd.switches = ["gmadd"]
        self.cmd.func()
        
        # Test gmadd without die size
        self.cmd.args = "TestChar1/Asset"
        self.cmd.switches = ["gmadd"]
        self.cmd.func()
        
        # Test gmrem without character/asset format
        self.cmd.args = "BadFormat"
        self.cmd.switches = ["gmrem"]
        self.cmd.func()
    
    def test_gm_commands_nonexistent_character(self):
        """Test GM commands with non-existent character."""
        self.cmd.caller = self.staff_char
        
        # Test with non-existent character
        self.cmd.args = "NonExistentChar/Asset=6"
        self.cmd.switches = ["gmadd"]
        self.cmd.func()
    
    def test_gm_remove_nonexistent_asset(self):
        """Test GM remove with non-existent asset."""
        self.cmd.caller = self.staff_char
        self.cmd.args = "TestChar1/NonExistentAsset"
        self.cmd.switches = ["gmrem"]
        self.cmd.func() 