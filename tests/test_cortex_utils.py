"""
Tests for Cortex Prime game system utilities.
"""

from evennia.utils.test_resources import EvenniaTest
from utils.cortex import (
    DIFFICULTIES,
    DIE_SIZES,
    TraitDie,
    step_die,
    roll_die,
    process_results,
    get_success_level,
    validate_dice_pool
)

class TestCortexUtils(EvenniaTest):
    """Test cases for Cortex utility functions."""
    
    def test_step_die(self):
        """Test stepping dice up and down."""
        # Test stepping up
        self.assertEqual(step_die("4", 1), "6")
        self.assertEqual(step_die("6", 1), "8")
        self.assertEqual(step_die("8", 1), "10")
        self.assertEqual(step_die("10", 1), "12")
        self.assertEqual(step_die("12", 1), "12")  # Can't step up past d12
        
        # Test stepping down
        self.assertEqual(step_die("12", -1), "10")
        self.assertEqual(step_die("10", -1), "8")
        self.assertEqual(step_die("8", -1), "6")
        self.assertEqual(step_die("6", -1), "4")
        self.assertEqual(step_die("4", -1), "4")  # Can't step down past d4
        
        # Test multiple steps
        self.assertEqual(step_die("4", 2), "8")
        self.assertEqual(step_die("12", -2), "8")
         # Test invalid die sizes
        self.assertEqual(step_die("5", 1), "5")  # Invalid die returns unchanged
        self.assertEqual(step_die("", 1), "")  # Empty string returns unchanged
    
    def test_roll_die(self):
        """Test die rolling."""
        # Test range for each die size
        for sides in [4, 6, 8, 10, 12]:
            # Roll multiple times to ensure we get valid results
            for _ in range(100):
                result = roll_die(sides)
                self.assertGreaterEqual(result, 1)
                self.assertLessEqual(result, sides)
                
    def test_process_results(self):
        """Test processing of dice roll results."""
        # Test normal roll: 6 on d8, 4 on d6, 8 on d10
        # Sorted by value: 8(d10), 6(d8), 4(d6)
        # Total: 8 + 6 = 14, Effect die: largest unused die size = d6 = 6
        rolls = [(6, 8), (4, 6), (8, 10)]  # (rolled_value, die_size)
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 14)  # Two highest dice: 8 + 6
        self.assertEqual(effect_die, 6)  # Largest unused die size (d6)
        self.assertEqual(len(hitches), 0)  # No 1s rolled
        
        # Test roll with hitches
        rolls = [(1, 8), (1, 6), (8, 10)]  # (rolled_value, die_size)
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 8)  # Only one non-hitch die
        self.assertEqual(effect_die, 4)  # Defaults to 4 when no third die available
        self.assertEqual(len(hitches), 2)  # Two 1s rolled
        self.assertEqual(hitches, [8, 6])  # Die sizes that rolled 1s
        
        # Test with multiple dice of same size unused
        # Rolls: 5 on d8, 3 on d6, 9 on d10, 2 on d8
        # Sorted by value: 9(d10), 5(d8), 3(d6), 2(d8)
        # Total: 9 + 5 = 14, Effect die: largest unused die size = max(d6, d8) = d8 = 8
        rolls = [(5, 8), (3, 6), (9, 10), (2, 8)]
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 14)  # 9 + 5
        self.assertEqual(effect_die, 8)  # Largest unused die size (d8)
        self.assertEqual(len(hitches), 0)
        
        # Test edge case: only two dice
        rolls = [(6, 8), (4, 6)]
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 10)  # 6 + 4
        self.assertEqual(effect_die, 4)  # Defaults to 4 when no unused dice
        self.assertEqual(len(hitches), 0)
        # Sorted by value: 9(d10), 5(d8), 3(d6), 2(d8)
        # Total: 9 + 5 = 14, Effect die: largest unused die size = max(d6, d8) = d8 = 8
        rolls = [(5, 8), (3, 6), (9, 10), (2, 8)]
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 14)  # 9 + 5
        self.assertEqual(effect_die, 8)  # Largest unused die size (d8)
        self.assertEqual(len(hitches), 0)
        
        # Test edge case: only two dice
        rolls = [(6, 8), (4, 6)]
        total, effect_die, hitches = process_results(rolls)
        self.assertEqual(total, 10)  # 6 + 4
        self.assertEqual(effect_die, 4)  # Defaults to 4 when no unused dice
        self.assertEqual(len(hitches), 0)
    
    def test_get_success_level(self):
        """Test success level determination."""
        # Test basic success/failure
        self.assertEqual(get_success_level(10, 11), (False, False))  # Failure
        self.assertEqual(get_success_level(11, 11), (True, False))   # Success
        self.assertEqual(get_success_level(16, 11), (True, True))    # Heroic
        
        # Test heroic success requirements
        self.assertEqual(get_success_level(12, 7), (True, False))    # Success but not heroic (diff too low)
        self.assertEqual(get_success_level(20, 15), (True, True))    # Heroic on hard difficulty
        
        # Test edge cases
        self.assertEqual(get_success_level(0, 1), (False, False))    # Zero total
        self.assertEqual(get_success_level(100, 11), (True, True))   # Very high roll        self.assertEqual(get_success_level(10, None), (True, False)) # No difficulty
    
    def test_validate_dice_pool(self):
        """Test dice pool validation."""
        # Create some test dice
        attribute = TraitDie("8", "character_attributes", "strength", None)
        skill = TraitDie("6", "skills", "fighting", None)
        distinction = TraitDie("8", "distinctions", "warrior", None)
        asset = TraitDie("6", "signature_assets", "sword", None)
        raw_die = TraitDie("8", None, None, None)
        
        # Test valid pools
        self.assertIsNone(validate_dice_pool([raw_die]))  # Single raw die is valid
        self.assertIsNone(validate_dice_pool([raw_die, raw_die]))  # Multiple raw dice are valid
        self.assertIsNone(validate_dice_pool([attribute, skill, distinction]))  # Complete prime set        self.assertIsNone(validate_dice_pool([attribute, skill, distinction, asset]))  # Prime set with asset
        
        # Test invalid pools
        self.assertIsNotNone(validate_dice_pool([attribute]))  # Missing skill and distinction
        self.assertIsNotNone(validate_dice_pool([attribute, skill]))  # Missing distinction
        self.assertIsNotNone(validate_dice_pool([asset]))  # Asset without prime set
        self.assertIsNotNone(validate_dice_pool([attribute, distinction, asset]))  # Missing skill