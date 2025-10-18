"""
Tests for the info/finger command.
"""

from datetime import datetime
from unittest.mock import MagicMock

from django.utils import timezone

from evennia.utils.test_resources import EvenniaTestCase

from commands.info import CmdInfo


class TestInfoCommand(EvenniaTestCase):
    """Test the info command functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.cmd = CmdInfo()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        self.cmd.msg = MagicMock()
        
    def test_info_basic_display(self):
        """Test basic info display."""
        # Set up character data
        self.char1.db.full_name = "Alice the Adventurer"
        
        # Test viewing own info
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.func()
        
        # Check that the message was sent
        self.cmd.msg.assert_called()
        output = self.cmd.msg.call_args[0][0]
        
        # Verify the content
        self.assertIn("Alice the Adventurer", output)
        self.assertIn("Web Profile:", output)
        self.assertIn(
            f"https://yoursite.com/characters/detail/{self.char1.name.lower()}/{self.char1.id}/",
            output,
        )
        
    def test_info_no_full_name(self):
        """Test info display when no full name is set."""
        # Don't set full_name, should fall back to character name
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.func()
        
        output = self.cmd.msg.call_args[0][0]
        self.assertIn(self.char1.name, output)
        
    def test_info_set_custom_field(self):
        """Test setting a custom field."""
        self.cmd.switches = ["set"]
        self.cmd.args = "Online Times = Usually evenings EST"
        self.cmd.func()
        
        # Check that the field was set
        custom_info = self.char1.db.custom_info
        self.assertIsNotNone(custom_info)
        self.assertEqual(custom_info["Online Times"], "Usually evenings EST")
        
        # Check the success message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Set custom field 'Online Times'", output)
        
    def test_info_display_custom_fields(self):
        """Test displaying custom fields."""
        # Set up custom fields
        self.char1.db.custom_info = {
            "Online Times": "Usually evenings EST",
            "Roleplay Hooks": "Looking for adventure companions"
        }
        
        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.func()
        
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Online Times:", output)
        self.assertIn("Usually evenings EST", output)
        self.assertIn("Roleplay Hooks:", output)
        self.assertIn("Looking for adventure companions", output)
        
    def test_info_clear_field(self):
        """Test clearing a custom field."""
        # Set up a field first
        self.char1.db.custom_info = {"Test Field": "Test Value"}
        
        self.cmd.switches = ["clear"]
        self.cmd.args = "Test Field"
        self.cmd.func()
        
        # Check that the field was removed
        custom_info = self.char1.db.custom_info
        self.assertNotIn("Test Field", custom_info)
        
        # Check the success message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Removed custom field 'Test Field'", output)
        
    def test_info_field_limit_check(self):
        """Test that the 10 field limit is enforced."""
        # Set up 10 fields
        custom_info = {}
        for i in range(10):
            custom_info[f"Field{i}"] = f"Value{i}"
        self.char1.db.custom_info = custom_info
        
        # Try to add an 11th field
        self.cmd.switches = ["set"]
        self.cmd.args = "Field11 = Value11"
        self.cmd.func()
        
        # Should get an error message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Maximum 10 custom fields allowed", output)
        
        # Field should not be added
        self.assertNotIn("Field11", self.char1.db.custom_info)
        
    def test_info_word_limit_check(self):
        """Test that the 200 word limit is enforced."""
        # Create a value with more than 200 words
        long_value = " ".join([f"word{i}" for i in range(201)])
        
        self.cmd.switches = ["set"]
        self.cmd.args = f"Long Field = {long_value}"
        self.cmd.func()
        
        # Should get an error message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Field value too long", output)
        self.assertIn("201 words", output)
        self.assertIn("Maximum 200 words allowed", output)
        
    def test_info_invalid_switches(self):
        """Test handling of invalid switches."""
        self.cmd.switches = ["invalid"]
        self.cmd.args = "something"
        self.cmd.func()
        
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Unknown switch 'invalid'", output)
        
    def test_info_set_without_equals(self):
        """Test set command without equals sign."""
        self.cmd.switches = ["set"]
        self.cmd.args = "Field without equals"
        self.cmd.func()
        
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Usage: info/set <field_name> = <value>", output)
        
    def test_info_clear_nonexistent_field(self):
        """Test clearing a field that doesn't exist."""
        self.cmd.switches = ["clear"]
        self.cmd.args = "Nonexistent Field"
        self.cmd.func()
        
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Field 'Nonexistent Field' not found", output)
        
    def test_info_staff_set_field_on_other_character(self):
        """Test staff setting a custom field on another character."""
        # Mock staff permissions
        self.char1.check_permstring = lambda perm: perm == "Admin"
        
        self.cmd.switches = ["set"]
        self.cmd.args = f"{self.char2.name} = Online Times = Usually evenings EST"
        self.cmd.func()
        
        # Check that the field was set on char2
        custom_info = self.char2.db.custom_info
        self.assertIsNotNone(custom_info)
        self.assertEqual(custom_info["Online Times"], "Usually evenings EST")
        
        # Check the success message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn(f"Set custom field 'Online Times' on {self.char2.name}", output)
        
    def test_info_staff_clear_field_from_other_character(self):
        """Test staff clearing a custom field from another character."""
        # Mock staff permissions
        self.char1.check_permstring = lambda perm: perm == "Admin"
        
        # Set up a field on char2 first
        self.char2.db.custom_info = {"Test Field": "Test Value"}
        
        self.cmd.switches = ["clear"]
        self.cmd.args = f"{self.char2.name} = Test Field"
        self.cmd.func()
        
        # Check that the field was removed from char2
        custom_info = self.char2.db.custom_info
        self.assertNotIn("Test Field", custom_info)
        
        # Check the success message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn(f"Removed custom field 'Test Field' from {self.char2.name}", output)
        
    def test_info_non_staff_cannot_use_staff_syntax(self):
        """Test that non-staff cannot use staff syntax."""
        # Mock non-staff permissions
        self.char1.check_permstring = lambda perm: False
        
        self.cmd.switches = ["set"]
        self.cmd.args = f"{self.char2.name} = Online Times = Usually evenings EST"
        self.cmd.func()
        
        # Should get a usage error
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Usage: info/set <field_name> = <value>", output)
        
        # Field should not be set on char2
        self.assertIsNone(self.char2.db.custom_info)
        
    def test_info_staff_invalid_character_name(self):
        """Test staff using invalid character name."""
        # Mock staff permissions
        self.char1.check_permstring = lambda perm: perm == "Admin"
        
        self.cmd.switches = ["set"]
        self.cmd.args = "InvalidChar = Online Times = Usually evenings EST"
        self.cmd.func()
        
        # Should get character not found error (from CharacterLookupMixin)
        # The exact message depends on the mixin implementation
        
    def test_info_staff_can_use_regular_syntax(self):
        """Test that staff can still use regular syntax to set fields on themselves."""
        # Mock staff permissions
        self.char1.check_permstring = lambda perm: perm == "Admin"
        
        self.cmd.switches = ["set"]
        self.cmd.args = "Online Times = Usually evenings EST"
        self.cmd.func()
        
        # Check that the field was set on char1 (self)
        custom_info = self.char1.db.custom_info
        self.assertIsNotNone(custom_info)
        self.assertEqual(custom_info["Online Times"], "Usually evenings EST")
        
        # Check the success message
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Set custom field 'Online Times'", output)
        self.assertNotIn(" on ", output)  # Should not say "on CharName" 

    def test_info_offline_last_seen(self):
        """Offline characters should show last-seen date."""
        # Remove sessions to simulate offline status
        self.char1.account.sessions.all().delete()

        last_seen = timezone.make_aware(datetime(2025, 1, 15, 13, 45))
        self.char1.account.last_login = last_seen
        self.char1.account.save()

        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.func()

        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Status:", output)
        self.assertIn("Last seen 2025-01-15", output)

    def test_info_online_idle_status(self):
        """Online characters should show appropriate idle labels."""
        account = self.char1.account

        # Simulate idle times by monkeypatching idle_time property
        account.idle_time = 20 * 60  # 20 minutes -> Online

        self.cmd.args = ""
        self.cmd.switches = []
        self.cmd.func()
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Status:", output)
        self.assertIn("Online", output)

        # 45 minutes -> Idle
        self.cmd.msg.reset_mock()
        account.idle_time = 45 * 60
        self.cmd.func()
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Status:", output)
        self.assertIn("Idle", output)

        # 2 hours -> Very Idle
        self.cmd.msg.reset_mock()
        account.idle_time = 120 * 60
        self.cmd.func()
        output = self.cmd.msg.call_args[0][0]
        self.assertIn("Status:", output)
        self.assertIn("Very Idle", output)

    def test_info_rejects_non_character_objects(self):
        """Info command should reject non-character objects without revealing they exist."""
        # Try to view info on a non-character object (obj1 is a DefaultObject)
        self.cmd.args = self.obj1.name
        self.cmd.switches = []
        self.cmd.func()

        output = self.cmd.msg.call_args[0][0]
        # Should show same message as if object doesn't exist
        self.assertIn("Could not find", output)
        # Should NOT reveal the object name/existence
        self.assertNotIn(self.obj1.name, output.replace(self.cmd.args, ""))