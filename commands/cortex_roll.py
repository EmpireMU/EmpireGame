"""
Commands for Cortex Prime dice rolling.
"""

from evennia.commands.default.muxcommand import MuxCommand
from evennia import CmdSet
from utils.cortex import (
    DIFFICULTIES,
    DIE_SIZES,
    TraitDie,
    get_trait_die,
    validate_dice_pool,
    roll_die,
    process_results,
    get_success_level
)
from utils import scene_logger
from web.scenes.models import SceneEntry
from collections import defaultdict

# Constants for validation
MAX_DICE_POOL = 10  # Maximum number of dice that can be rolled at once

def format_colored_roll(value, die, trait_info, extra_value=None):
    """
    Format a single die roll with color.
    
    Args:
        value: The value rolled on the main die
        die: The die size
        trait_info: The TraitDie object with trait information
        extra_value: If not None, this is the value of the extra die from doubling
    """
    if trait_info.key:  # Changed from trait_name to key to match TraitDie NamedTuple
        # Display name mapping
        display_names = {
            'distinctions': 'Distinction',
            'character_attributes': 'Attribute',
            'skills': 'Skill',
            'char_resources': 'Resource',
            'signature_assets': 'Signature Asset',
            'temporary_assets': 'Temporary Asset'
        }
        category_name = display_names.get(trait_info.category, trait_info.category.title().replace('_', ' ').rstrip('s')) if trait_info.category else "Raw"
        
        # Build modifier suffix
        modifiers = []
        if trait_info.step_mod == 'U':
            modifiers.append("|g(U)|n")
        elif trait_info.step_mod == 'D':
            modifiers.append("|r(D)|n")
        mod_suffix = "".join(modifiers)
        
        # Get the trait object to check for name
        trait = None
        if trait_info.category == 'distinctions':
            trait = trait_info.caller.distinctions.get(trait_info.key)
        elif trait_info.category == 'character_attributes':
            trait = trait_info.caller.character_attributes.get(trait_info.key)
        elif trait_info.category == 'skills':
            trait = trait_info.caller.skills.get(trait_info.key)
        elif trait_info.category == 'char_resources':
            trait = trait_info.caller.char_resources.get(trait_info.key)
        elif trait_info.category == 'signature_assets':
            trait = trait_info.caller.signature_assets.get(trait_info.key)
            
        # Use trait name if available, otherwise use key, and properly capitalize
        display_name = trait.name if trait and hasattr(trait, 'name') else trait_info.key
        display_name = display_name.title() if display_name else ""
        
        # If we have an extra die from doubling, include both values
        if extra_value is not None:
            return f"|c{value}, {extra_value}|n({display_name}: d{die}{mod_suffix} |c(Doubled)|n)"
        return f"|c{value}|n({display_name}: d{die}{mod_suffix})"
    return f"|c{value}|n(d{die})"

class CmdCortexRoll(MuxCommand):
    """
    Roll dice using the Cortex Prime system.
    
    Usage:
        roll <trait1> [<trait2>...] [vs <difficulty>]
        roll/keepextra <trait1> [<trait2>...] [vs <difficulty>]
        roll/reroll <trait1> [<trait2>...] [d6/d8/etc]
        
    For multi-word traits, either:
    - Use quotes: roll "High Ground" prowess fighting
    - Use underscores: roll high_ground prowess fighting
        
    Examples:
        roll strength fighting - Roll Strength + Fighting dice
        roll strength d8 - Roll Strength + a d8
        roll strength(U) fighting - Roll Strength stepped up + Fighting
        roll strength fighting(D) - Roll Strength + Fighting stepped down
        roll "High Ground" fighting vs hard - Roll High Ground + Fighting vs hard difficulty
        roll "High Ground"(d) fighting - Roll High Ground stepped down + Fighting
        roll high_ground fighting vs hard - Same as above using underscore
        roll/keepextra prowess fighting warrior - Keep 3rd highest die in total
        roll/reroll prowess d6 - Reroll prowess die and raw d6 from last roll
        
    Dice Mechanics:
    - Each trait adds its die to the pool (e.g., d6, d8, d10, d12)
    - Roll all dice and sum the two highest
    - If rolling against difficulty, must beat the target number
    - Distinctions can be used as d8 (default) or stepped down to d4 using (D)
    - Plot points can be spent to:
      * Step up or down a die by adding (U) or (D) after the trait name
      * Keep an additional die in the total
    
    Special Rules:
    - Rolling 1 on any die is a "hitch" (minor complication)
    - Matching dice can be used for special effects
    - Effect die (highest unused die) determines impact
    - Difficulty numbers:
      * 3 - very easy
      * 7 - easy
      * 11 - challenging
      * 15 - hard
      * 19 - very hard
    """
    
    key = "roll"
    locks = "cmd:all()"  # Everyone can use this command
    help_category = "Game"
    switch_options = ("reroll", "keepextra")
    
    def at_pre_cmd(self):
        """
        Called before command validation and parsing.
        Can be used to do setup or prevent command execution.
        
        Returns:
            True if command should be prevented, None to allow execution
        """
        # For now just check if character can roll dice (not incapacitated etc)
        # Add your character state validation here if needed
        return None
        
    def parse(self):
        """Parse the dice input and difficulty."""
        # Call parent parse first to initialize switches, args, etc.
        super().parse()
            
        # For rerolls, skip normal parsing - we'll use cached roll data
        if "reroll" in self.switches:
            self.dice = None
            self.trait_info = None
            return
        if not self.args:
            self.msg("What dice do you want to roll?")
            self.dice = None
            return
            
        # Split and clean args, handling quoted strings and underscores
        args = []
        current_arg = []
        in_quotes = False
        
        # First pass: handle quoted strings
        for word in self.args.split():
            if in_quotes:
                # Check if this word contains a closing quote
                if '"' in word:
                    quote_idx = word.index('"')
                    # Add everything before the quote to current_arg
                    current_arg.append(word[:quote_idx])
                    # Join the quoted parts
                    quoted_text = ' '.join(current_arg)
                    # Get any modifier after the quote (e.g., (d) or (U))
                    modifier = word[quote_idx + 1:]
                    # Combine quoted text with modifier
                    args.append(quoted_text + modifier if modifier else quoted_text)
                    current_arg = []
                    in_quotes = False
                else:
                    current_arg.append(word)
                continue

            if word.startswith('"'):
                # Check if the quote closes in the same word
                if '"' in word[1:]:
                    quote_idx = word.index('"', 1)
                    quoted_text = word[1:quote_idx]
                    modifier = word[quote_idx + 1:]
                    args.append(quoted_text + modifier if modifier else quoted_text)
                else:
                    in_quotes = True
                    current_arg.append(word[1:])
                continue

            # Handle underscores by replacing them with spaces
            if '_' in word:
                args.append(word.replace('_', ' '))
            else:
                args.append(word)
                
        if current_arg:  # Handle any remaining words
            args.append(' '.join(current_arg))
            
        # Clean up args
        args = [arg.strip().lower() for arg in args if arg.strip()]
        
        if not args:
            self.msg("What dice do you want to roll?")
            self.dice = None
            return
            
        # Check for difficulty
        self.difficulty = None
        try:
            # Find the "vs" marker
            vs_index = -1
            for i, arg in enumerate(args):
                if arg == "vs":
                    vs_index = i
                    break
                    
            if vs_index >= 0:
                # Get everything after "vs" as the difficulty
                if vs_index + 1 >= len(args):
                    self.msg("Missing difficulty value after 'vs'.")
                    self.dice = None
                    return
                    
                # Join all remaining words as they might be part of difficulty name
                diff_val = " ".join(args[vs_index + 1:]).lower()
                args = args[:vs_index]  # Remove difficulty from args
                
                # Try to parse as number first
                try:
                    self.difficulty = int(diff_val)
                except ValueError:
                    # Try to match named difficulty exactly first
                    exact_match = None
                    partial_matches = []
                    
                    # First check for exact matches
                    for name, value in DIFFICULTIES.items():
                        if diff_val == name.lower():
                            exact_match = value
                            break
                    
                    if exact_match is not None:
                        self.difficulty = exact_match
                    else:
                        # Special handling for "very" prefix
                        if diff_val == "very":
                            self.msg("Please specify 'very easy' or 'very hard'.")
                            self.dice = None
                            return
                            
                        # Check for partial matches
                        for name, value in DIFFICULTIES.items():
                            name_lower = name.lower()
                            if diff_val in name_lower:
                                # Only add to partial matches if it's not just the "very" prefix
                                if not (diff_val == "very" and name_lower.startswith("very")):
                                    partial_matches.append(name)
                        
                        if len(partial_matches) == 1:
                            self.difficulty = DIFFICULTIES[partial_matches[0]]
                        elif len(partial_matches) > 1:
                            self.msg(f"Ambiguous difficulty '{diff_val}'. Matches: {', '.join(partial_matches)}")
                            self.dice = None
                            return
                        else:
                            self.msg(f"Unknown difficulty '{diff_val}'. Valid difficulties are: {', '.join(DIFFICULTIES.keys())}")
                            self.dice = None
                            return
        except ValueError:
            # No "vs" found, that's fine
            pass
        
        # Validate dice pool size
        if not args:
            self.msg("You must specify at least one die to roll.")
            self.dice = None
            return
            
        if len(args) > MAX_DICE_POOL:
            self.msg(f"You cannot roll more than {MAX_DICE_POOL} dice at once.")
            self.dice = None
            return
        
        # Check for complications first and handle them
        complications_found = []
        filtered_args = []
        
        for arg in args:
            # Check if this argument is a complication
            if hasattr(self.caller, 'complications'):
                trait_key = arg.lower().replace(' ', '_')
                complication = self.caller.complications.get(trait_key)
                if complication:
                    complications_found.append(complication)
                    continue  # Don't add to filtered_args
            
            # Not a complication, add to filtered args for normal processing
            filtered_args.append(arg)
        
        # Handle complications
        if complications_found:
            if self.difficulty is not None:
                # Add half the complication die size to difficulty
                for comp in complications_found:
                    self.difficulty += int(comp.value) // 2
            else:
                # No difficulty, show message and set empty dice
                self.dice = None
                self.trait_info = []
                self.msg("Complications are applied in GM rolls or versus set difficulties; please remove the complication from your roll or set a difficulty.")
                return
        
        # Process remaining dice/traits
        dice_pool = []
        
        for arg in filtered_args:
            # Validate argument
            if not arg:  # Skip empty arguments
                continue
                
            # Check if it's a raw die (must match pattern 'd' followed by a valid die size)
            # or just a valid die size number
            if arg.startswith('d') or arg in DIE_SIZES:
                # Get the die size, either after 'd' or the full arg
                die = arg[1:] if arg.startswith('d') else arg
                
                # Check for step modifiers on raw dice
                if '(' in arg:
                    self.msg("Raw dice (like 'd8' or '8') cannot be stepped up or down. Only traits can be modified.")
                    self.dice = None
                    return
                
                if die in DIE_SIZES:
                    dice_pool.append(TraitDie(die, None, None, None, self.caller))
                else:
                    self.msg(f"Invalid die size: {arg}")
                    self.dice = None
                    return
            else:
                # Check for invalid characters in trait names (allowing parentheses for modifiers)
                base_name = arg.split('(')[0] if '(' in arg else arg
                if not base_name.replace(' ', '').isalnum():
                    self.msg(f"Invalid character in trait name: {base_name}")
                    self.dice = None
                    return
                    
                # Try to find trait
                trait_info = get_trait_die(self.caller, arg)
                if trait_info:
                    die_size, category, step_mod, doubled = trait_info
                    # Add the main trait die
                    base_arg = arg.split('(')[0].strip()
                    trait_die = TraitDie(die_size, category, base_arg, step_mod, self.caller)
                    dice_pool.append(trait_die)
                    # If doubled, add an extra die of the same size (without trait info)
                    if doubled:
                        dice_pool.append(TraitDie(die_size, None, None, None, self.caller))
                else:
                    self.msg(f"Unknown trait '{arg}'. Use 'help roll' to see available traits and modifiers.")
                    self.dice = None
                    return
        
        # Validate the dice pool
        error = validate_dice_pool(dice_pool)
        if error:
            self.msg(error)
            self.dice = None
            return
        
        # Store dice and trait information
        self.dice = [die.size for die in dice_pool]
        self.trait_info = dice_pool

    def func(self):
        """Execute the dice roll."""
        # Handle reroll switch
        if "reroll" in self.switches:
            self._handle_reroll()
            return
            
        # Handle regular roll or keepextra
        if not self.dice:
            return
            
        keep_extra = "keepextra" in self.switches
            
        try:
            # Roll all dice and track results with their indices.
            rolls = [(roll_die(int(die)), int(die), i) for i, die in enumerate(self.dice)]
            
            # Store last roll for potential reroll
            self._store_last_roll(rolls)
            
            # Check for botch (all 1s)
            all_values = [value for value, _, _ in rolls]
            if all(value == 1 for value in all_values):
                result_msg = f"|r{self.caller.key} BOTCHES! All dice came up 1s!|n\n"
                
                # Format rolls for botch message
                formatted_rolls = []
                i = 0
                while i < len(rolls):
                    trait_info = self.trait_info[rolls[i][2]]
                    if i + 1 < len(rolls) and trait_info.key and not self.trait_info[rolls[i+1][2]].key:
                        # This is a doubled trait
                        formatted_rolls.append(format_colored_roll(rolls[i][0], rolls[i][1], trait_info, rolls[i+1][0]))
                        i += 2
                    else:
                        formatted_rolls.append(format_colored_roll(rolls[i][0], rolls[i][1], trait_info))
                        i += 1
                        
                result_msg += f"Rolled: {', '.join(formatted_rolls)}"
                self.caller.location.msg_contents(result_msg)
                return
            
            # Process results
            # Convert rolls to the format process_results expects (value, die_size).
            process_rolls = [(value, die) for value, die, _ in rolls]
            total, effect_die, hitches, extra_die_value = process_results(process_rolls, keep_extra=keep_extra)
            
            # Format individual roll results with trait names
            roll_results = []
            i = 0
            while i < len(rolls):
                trait_info = self.trait_info[rolls[i][2]]
                if i + 1 < len(rolls) and trait_info.key and not self.trait_info[rolls[i+1][2]].key:
                    # This is a doubled trait
                    roll_results.append(format_colored_roll(rolls[i][0], rolls[i][1], trait_info, rolls[i+1][0]))
                    i += 2
                else:
                    roll_results.append(format_colored_roll(rolls[i][0], rolls[i][1], trait_info))
                    i += 1            # Build output message
            result_msg = f"{self.caller.key} rolls: {', '.join(roll_results)}\n"
            
            # Build total line with difficulty and success result if applicable
            non_hitch_count = len([r for r in rolls if r[0] != 1])
            effect_die_text = f"d{effect_die}"
            if effect_die == 4 and non_hitch_count < 3:
                effect_die_text += " |y(defaulted to d4)|n"
            
            # Build total text with keepextra indicator
            if keep_extra and extra_die_value is not None:
                total_text = f"|w{total}|n |c(keeping extra die: +{extra_die_value})|n"
            else:
                total_text = f"|w{total}|n"
            
            if self.difficulty is not None:
                success, heroic = get_success_level(total, self.difficulty)
                if success:
                    if heroic:
                        success_text = f"|g{self.caller.key} achieves a HEROIC SUCCESS!|n"
                    else:
                        success_text = "|gSuccess|n"
                else:
                    success_text = "|yFailure|n"
                result_msg += f"Total: {total_text} (vs {self.difficulty}) - {success_text} | Effect Die: |w{effect_die_text}|n"
            else:
                result_msg += f"Total: {total_text} | Effect Die: |w{effect_die_text}|n"
            
            # Track traits used from each category for GM notification
            category_count = defaultdict(int)
            category_names = defaultdict(list)
            for trait in self.trait_info:
                if trait.category and trait.key:  # Skip raw dice and doubled dice (which have no category/key)
                    category_count[trait.category] += 1
                    category_names[trait.category].append(trait.key)
            
            # Send private notifications about multiple traits from same category
            for category, count in category_count.items():
                if count > 1:
                    notice = f"|yNote: Using multiple {category} traits ({', '.join(category_names[category])})|n"
                    # Send to the player
                    self.caller.msg(notice)
                    # Send to GMs in the room
                    for obj in self.caller.location.contents:
                        if obj.check_permstring("Builder") and obj != self.caller:
                            obj.msg(f"|y{self.caller.name} is using multiple {category} traits ({', '.join(category_names[category])})|n")
            
            if hitches:
                hitch_text = ", ".join(f"d{int(h)}" for h in hitches)
                result_msg += f"\n|yHitches: {len(hitches)} (rolled 1 on: {hitch_text})|n"
            
            # Send result to room
            self.caller.location.msg_contents(result_msg)

            # Log the roll to the active scene, if any
            scene_ctx = scene_logger.get_room_scene(self.caller.location)
            if scene_ctx:
                scene_logger.record_entry(
                    scene_ctx.scene,
                    SceneEntry.EntryType.ROLL,
                    text=result_msg,
                    actor=self.caller,
                    text_plain=scene_logger.strip_ansi(result_msg),
                )

        except Exception as e:
            self.msg(f"Error during dice roll: {e}")
            return
    
    def _store_last_roll(self, rolls):
        """Store the last roll for potential reroll."""
        char = self.caller
        if not hasattr(char, 'traits'):
            char = char.char
        if not hasattr(char, 'ndb'):
            return
            
        # Store roll data: (value, die_size, index, trait_info)
        char.ndb.last_roll = {
            'rolls': rolls,  # List of (value, die_size, index) tuples
            'trait_info': self.trait_info,  # List of TraitDie objects
            'difficulty': self.difficulty
        }
    
    def _handle_reroll(self):
        """Handle rerolling specific dice from the last roll."""
        char = self.caller
        if not hasattr(char, 'traits'):
            char = char.char
            
        # Check if there's a last roll to reroll
        if not hasattr(char, 'ndb') or not char.ndb.last_roll:
            self.msg("You haven't made a roll yet to reroll.")
            return
            
        last_roll_data = char.ndb.last_roll
        rolls = last_roll_data['rolls']
        trait_info = last_roll_data['trait_info']
        # Ensure trait info is available for any subsequent rerolls
        self.trait_info = trait_info
        self.difficulty = last_roll_data['difficulty']
        
        if not self.args:
            self.msg("Specify which dice to reroll (e.g., roll/reroll prowess d6)")
            return
            
        # Parse which dice to reroll
        args = []
        current_arg = []
        in_quotes = False
        
        # First pass: handle quoted strings
        for word in self.args.split():
            if in_quotes:
                # Check if this word contains a closing quote
                if '"' in word:
                    quote_idx = word.index('"')
                    # Add everything before the quote to current_arg
                    current_arg.append(word[:quote_idx])
                    # Join the quoted parts
                    quoted_text = ' '.join(current_arg)
                    # Get any modifier after the quote (e.g., (d) or (U))
                    modifier = word[quote_idx + 1:]
                    # Combine quoted text with modifier
                    args.append(quoted_text + modifier if modifier else quoted_text)
                    current_arg = []
                    in_quotes = False
                else:
                    current_arg.append(word)
                continue

            if word.startswith('"'):
                # Check if the quote closes in the same word
                if '"' in word[1:]:
                    quote_idx = word.index('"', 1)
                    quoted_text = word[1:quote_idx]
                    modifier = word[quote_idx + 1:]
                    args.append(quoted_text + modifier if modifier else quoted_text)
                else:
                    in_quotes = True
                    current_arg.append(word[1:])
                continue

            # Handle underscores by replacing them with spaces
            if '_' in word:
                args.append(word.replace('_', ' '))
            else:
                args.append(word)
                
        if current_arg:  # Handle any remaining words
            args.append(' '.join(current_arg))
            
        # Clean up args
        args = [arg.strip().lower() for arg in args if arg.strip()]
        
        # Track which dice to reroll by index
        indices_to_reroll = []
        
        for arg in args:
            # Check if it's a raw die (d6, d8, etc. or just 6, 8, etc.)
            if arg.startswith('d'):
                die_size = arg[1:]
            elif arg in DIE_SIZES:
                die_size = arg
            else:
                die_size = None
                
            if die_size:
                # Find all raw dice of this size
                for i, (value, die, idx) in enumerate(rolls):
                    if str(die) == die_size and not trait_info[idx].key:
                        indices_to_reroll.append(i)
            else:
                # It's a trait name - find matching traits
                # Handle the trait being doubled - reroll both dice
                trait_key = arg.replace(' ', '_')
                for i, (value, die, idx) in enumerate(rolls):
                    trait = trait_info[idx]
                    if trait.key and trait.key.lower() == trait_key:
                        indices_to_reroll.append(i)
                        # Check if next die is the doubled version
                        if i + 1 < len(rolls):
                            next_trait = trait_info[rolls[i+1][2]]
                            if not next_trait.key and rolls[i+1][1] == die:
                                indices_to_reroll.append(i+1)
        
        if not indices_to_reroll:
            self.msg("No matching dice found to reroll. Check your dice names.")
            return
            
        # Remove duplicates and sort
        indices_to_reroll = sorted(set(indices_to_reroll))
        
        # Reroll the specified dice
        new_rolls = []
        for i, (value, die, idx) in enumerate(rolls):
            if i in indices_to_reroll:
                new_value = roll_die(int(die))
                new_rolls.append((new_value, die, idx))
            else:
                new_rolls.append((value, die, idx))
        
        # Store the new roll
        self.trait_info = trait_info
        self._store_last_roll(new_rolls)
        
        # Check for botch
        all_values = [value for value, _, _ in new_rolls]
        if all(value == 1 for value in all_values):
            result_msg = f"|r{self.caller.key} BOTCHES! All dice came up 1s!|n\n"
            
            # Format rolls for botch message
            formatted_rolls = []
            i = 0
            while i < len(new_rolls):
                t_info = trait_info[new_rolls[i][2]]
                if i + 1 < len(new_rolls) and t_info.key and not trait_info[new_rolls[i+1][2]].key:
                    # This is a doubled trait
                    formatted_rolls.append(format_colored_roll(new_rolls[i][0], new_rolls[i][1], t_info, new_rolls[i+1][0]))
                    i += 2
                else:
                    formatted_rolls.append(format_colored_roll(new_rolls[i][0], new_rolls[i][1], t_info))
                    i += 1
                    
            result_msg += f"Rolled: {', '.join(formatted_rolls)}"
            self.caller.location.msg_contents(result_msg)
            return
        
        # Process results
        process_rolls = [(value, die) for value, die, _ in new_rolls]
        total, effect_die, hitches, extra_die_value = process_results(process_rolls, keep_extra=False)
        
        # Format individual roll results with trait names, marking rerolled dice
        roll_results = []
        i = 0
        while i < len(new_rolls):
            t_info = trait_info[new_rolls[i][2]]
            rerolled_marker = " |y(rerolled)|n" if i in indices_to_reroll else ""
            if i + 1 < len(new_rolls) and t_info.key and not trait_info[new_rolls[i+1][2]].key:
                # This is a doubled trait
                extra_rerolled = " |y(rerolled)|n" if (i+1) in indices_to_reroll else ""
                base_text = format_colored_roll(new_rolls[i][0], new_rolls[i][1], t_info, new_rolls[i+1][0])
                roll_results.append(base_text + rerolled_marker + extra_rerolled)
                i += 2
            else:
                roll_results.append(format_colored_roll(new_rolls[i][0], new_rolls[i][1], t_info) + rerolled_marker)
                i += 1
                
        result_msg = f"{self.caller.key} rerolls: {', '.join(roll_results)}\n"
        
        # Build total line
        non_hitch_count = len([r for r in new_rolls if r[0] != 1])
        effect_die_text = f"d{effect_die}"
        if effect_die == 4 and non_hitch_count < 3:
            effect_die_text += " |y(defaulted to d4)|n"
        
        if self.difficulty is not None:
            success, heroic = get_success_level(total, self.difficulty)
            if success:
                if heroic:
                    success_text = f"|g{self.caller.key} achieves a HEROIC SUCCESS!|n"
                else:
                    success_text = "|gSuccess|n"
            else:
                success_text = "|yFailure|n"
            result_msg += f"Total: |w{total}|n (vs {self.difficulty}) - {success_text} | Effect Die: |w{effect_die_text}|n"
        else:
            result_msg += f"Total: |w{total}|n | Effect Die: |w{effect_die_text}|n"
        
        if hitches:
            hitch_text = ", ".join(f"d{int(h)}" for h in hitches)
            result_msg += f"\n|yHitches: {len(hitches)} (rolled 1 on: {hitch_text})|n"
        
        # Send result to room
        self.caller.location.msg_contents(result_msg)
            
    def at_post_cmd(self):
        """
        Called after command execution, even if it failed.
        Can be used for cleanup or to trigger other actions.
        """
        # For now just cleanup any temporary attributes if needed
        pass

    def get_trait_dice(self, trait_info):
        """Get the dice for a trait."""
        if trait_info.category == 'character_attributes':
            trait = trait_info.caller.character_attributes.get(trait_info.key)
        elif trait_info.category == 'skills':
            trait = trait_info.caller.skills.get(trait_info.key)
        elif trait_info.category == 'signature_assets':
            trait = trait_info.caller.signature_assets.get(trait_info.key)
        elif trait_info.category == 'char_resources':
            trait = trait_info.caller.char_resources.get(trait_info.key)
        else:
            return None
            
        if not trait:
            return None
            
        return [trait.base]


class CortexCmdSet(CmdSet):
    """
    Command set for Cortex Prime dice rolling.
    """
    key = "cortex"
    
    def at_cmdset_creation(self):
        """Add commands to the command set."""
        self.add(CmdCortexRoll())