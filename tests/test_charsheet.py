"""
Tests for character sheet functionality.
"""

from unittest.mock import MagicMock, patch
from evennia.utils.test_resources import EvenniaTest
from commands.charsheet import CmdSheet, get_trait_display, format_trait_section
from utils.trait_definitions import ATTRIBUTES, SKILLS, DISTINCTIONS
from evennia.contrib.rpg.traits import TraitHandler

class TestCharSheet(EvenniaTest):
    """Test cases for character sheet functionality."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.cmd = CmdSheet()
        self.cmd.caller = self.char1
        self.cmd.obj = self.char1
        
        # Set up message mocking
        self.caller = self.char1
        self.caller.msg = MagicMock()
        self.cmd.msg = self.caller.msg
        
        # Initialize trait handlers
        if not hasattr(self.char1, 'character_attributes'):
            self.char1.character_attributes = TraitHandler(self.char1, db_attribute_key="char_attributes")
        if not hasattr(self.char1, 'skills'):
            self.char1.skills = TraitHandler(self.char1, db_attribute_key="skills")
        if not hasattr(self.char1, 'distinctions'):
            self.char1.distinctions = TraitHandler(self.char1, db_attribute_key="char_distinctions")
        if not hasattr(self.char1, 'char_resources'):
            self.char1.char_resources = TraitHandler(self.char1, db_attribute_key="char_resources")
        if not hasattr(self.char1, 'signature_assets'):
            self.char1.signature_assets = TraitHandler(self.char1, db_attribute_key="char_signature_assets")
        if not hasattr(self.char1, 'powers'):
            self.char1.powers = TraitHandler(self.char1, db_attribute_key="powers")
        
        # Add test traits
        self.char1.character_attributes.add("prowess", "Prowess", trait_type="static", base=8, desc="Physical power")
        self.char1.character_attributes.add("finesse", "Finesse", trait_type="static", base=6, desc="Agility")
        
        # Add skills
        self.char1.skills.add("fighting", "Fighting", trait_type="static", base=8, desc="Combat ability")
        self.char1.skills.add("stealth", "Stealth", trait_type="static", base=6, desc="Moving quietly")
        
        # Add distinctions
        self.char1.distinctions.add("warrior", "Warrior", trait_type="static", base=8, desc="Born fighter")
        
        # Add signature assets
        self.char1.signature_assets.add("sword", "Magic Sword", trait_type="static", base=6, desc="Ancient blade")
        
        # Add resources
        self.char1.char_resources.add("gold", "Gold", trait_type="static", base=6, desc="Wealth")

        # Add powers
        self.char1.powers.add("test_power", "Test Power", trait_type="static", base=8, desc="A test power")
    
    def test_get_trait_display(self):
        """Test trait display formatting."""
        # Test normal trait with name and description
        trait = self.char1.character_attributes.get("prowess")
        name, die, desc = get_trait_display(trait)
        self.assertEqual(name, "Prowess")
        self.assertEqual(die, "d8")
        self.assertEqual(desc, "Physical power")
        
        # Test trait without description
        trait = self.char1.skills.get("fighting")
        name, die, desc = get_trait_display(trait)
        self.assertEqual(name, "Fighting")
        self.assertEqual(die, "d8")
        self.assertEqual(desc, "Combat ability")
        
        # Test None trait
        name, die, desc = get_trait_display(None)
        self.assertEqual(name, "")
        self.assertEqual(die, "")
        self.assertEqual(desc, "")
    
    def test_format_trait_section(self):
        """Test trait section formatting."""
        # Test attributes section
        attributes = [
            self.char1.character_attributes.get("prowess"),
            self.char1.character_attributes.get("finesse")
        ]
        section = format_trait_section("Attributes", attributes)
        prowess_die = "d" + str(int(self.char1.character_attributes.get("prowess").base))
        finesse_die = "d" + str(int(self.char1.character_attributes.get("finesse").base))
        
        self.assertIn("Attributes", section)
        self.assertIn("Prowess", section)
        self.assertIn(prowess_die, section)
        self.assertIn("Finesse", section)
        self.assertIn(finesse_die, section)
        
        # Test resources section with descriptions
        resources = [self.char1.char_resources.get("gold")]
        section = format_trait_section("Resources", resources, show_desc=True)
        gold_die = "d" + str(int(self.char1.char_resources.get("gold").base))
        
        self.assertIn("Resources", section)
        self.assertIn("Gold", section)
        self.assertIn(gold_die, section)
        self.assertIn("Wealth", section)
        
        # Test empty section
        section = format_trait_section("Empty", [])
        self.assertEqual(section, "")
    
    def test_view_own_sheet(self):
        """Test viewing own character sheet."""
        # Call command with no args (view own sheet)
        self.cmd.args = ""
        self.cmd.func()
        
        # Check output contains all sections
        output = self.caller.msg.mock_calls[0][1][0]
        prowess_die = "d" + str(int(self.char1.character_attributes.get("prowess").base))
        
        self.assertIn("Character Sheet", output)
        self.assertIn("Plot Points", output)
        self.assertIn("Prime Sets", output)
        self.assertIn("Additional Sets", output)
        
        # Check specific traits
        self.assertIn("Prowess", output)
        self.assertIn(prowess_die, output)
        self.assertIn("Fighting", output)
        self.assertIn("Warrior", output)
        self.assertIn("Magic Sword", output)
        self.assertIn("Gold", output)
    
    def test_view_other_sheet(self):
        """Test viewing another character's sheet."""
        # Create another character
        other_char = self.char2
        
        # Initialize trait handlers on other character
        if not hasattr(other_char, 'character_attributes'):
            other_char.character_attributes = TraitHandler(other_char, db_attribute_key="char_attributes")
        if not hasattr(other_char, 'skills'):
            other_char.skills = TraitHandler(other_char, db_attribute_key="skills")
        if not hasattr(other_char, 'distinctions'):
            other_char.distinctions = TraitHandler(other_char, db_attribute_key="char_distinctions")
        
        # Add some test traits
        other_char.character_attributes.add("prowess", "Prowess", trait_type="static", base=6)
        other_char.skills.add("fighting", "Fighting", trait_type="static", base=6)
        
        # Try viewing without Builder permission
        self.cmd.args = other_char.name
        self.cmd.func()
        # Should show sheet since we have Builder permission
        output = str(self.caller.msg.mock_calls[0][1][0])
        self.assertIn(f"{other_char.name}'s Character Sheet", output)
    
    def test_invalid_sheet_access(self):
        """Test invalid character sheet access."""
        # Try viewing non-existent character
        self.cmd.caller.permissions.add("Admin")
        self.cmd.args = "nonexistent"
        self.cmd.func()
        self.assertIn("Could not find", self.caller.msg.mock_calls[0][1][0])
        
        # Try viewing object without traits
        obj = self.obj1
        self.cmd.args = obj.name
        self.cmd.func()
        self.assertIn("has no character sheet", self.caller.msg.mock_calls[1][1][0])

    def test_special_effects_display(self):
        """Test that special effects are displayed on character sheet when set."""
        # Set special effects
        self.char1.db.special_effects = "Has a magical aura that glows softly in darkness"
        
        # Call command with no args (view own sheet)
        self.cmd.args = ""
        self.cmd.func()
        
        # Check output contains special effects
        output = self.caller.msg.mock_calls[0][1][0]
        self.assertIn("Special Effects", output)
        self.assertIn("Has a magical aura that glows softly in darkness", output)
        
    def test_no_special_effects_display(self):
        """Test that special effects section is not shown when empty."""
        # Ensure special effects is empty
        self.char1.db.special_effects = ""
        
        # Call command with no args (view own sheet)
        self.cmd.args = ""
        self.cmd.func()
        
        # Check output does not contain special effects section
        output = self.caller.msg.mock_calls[0][1][0]
        self.assertNotIn("Special Effects", output)

if __name__ == '__main__':
    unittest.main()