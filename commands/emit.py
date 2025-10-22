"""
Emit command

The emit command allows players to send messages to everyone in their
current room.
"""

from evennia.commands.default.muxcommand import MuxCommand
from utils.message_coloring import apply_character_coloring, apply_name_coloring


class CmdEmit(MuxCommand):
    """
    Send a message to everyone in your current room.
    
    Usage:
        emit <message>                      - No name
        pose <message>                      - Your name at start
        emit/shownames - Toggle seeing sender names on emits
        emit/speechcolour <colour> - Set speech colour in emits
        emit/colourword <word>=<colour> - Set colour for specific words

    Examples:

        emit/shownames
        emit/speechcolour ||y
        emit/speechcolour ||344
        emit/speechcolour ||r
        emit/colourword drum=||344
        emit/colourword magic=||b
        
    Use 'emit/shownames' to toggle whether you see the name of who 
    sent an emit. When enabled, emits will show as "(Name) message".
    
    Use 'emit/speechcolour <colour>' to set the colour for quoted speech
    in emits. Supports ANSI colours (||r, ||g, ||b, ||y, etc.) and xterm 
    colours (||001 to ||255). Default is ||y (yellow).
    
    Use 'emit/colourword <word>=<colour>' to set custom colours for 
    specific words in emits. For example, 'emit/colourword drum=||344'
    will highlight all instances of 'drum' in colour 344.
    """
    
    key = "emit"
    aliases = ["pose", ";", ":"]
    locks = "cmd:all()"
    help_category = "Social"
    
    def func(self):
        """Execute the emit command."""
        # Handle the shownames switch
        if "shownames" in self.switches:
            current_setting = self.caller.db.show_emit_names
            new_setting = not current_setting
            self.caller.db.show_emit_names = new_setting
            
            if new_setting:
                self.msg("You will now see sender names on emits: (Name) message")
            else:
                self.msg("You will no longer see sender names on emits.")
            return
            
        # Handle the speechcolour switch
        if "speechcolour" in self.switches:
            if not self.args:
                current_color = self.caller.db.emit_speech_color or "|y"
                self.msg(f"Current speech colour: {current_color}Hello|n")
                self.msg("Usage: emit/speechcolour <colour> (e.g., |y, |r, |344)")
                return
                
            color = self.args.strip()
            
            # Validate colour format (basic validation)
            if not color.startswith('|'):
                self.msg("Colour must start with | (e.g., |y, |r, |344)")
                return
                
            # Store the colour setting
            self.caller.db.emit_speech_color = color
            # Escape the color code in the confirmation message so it displays as text
            escaped_color = color.replace("|", "||")
            self.msg(f"Speech colour set to: {color}\"Sample speech\"|n = {escaped_color}")
            return
            
        # Handle the colourword switch
        if "colourword" in self.switches:
            if not self.args or "=" not in self.args:
                # Show current word colours
                word_colors = self.caller.db.emit_word_colors or {}
                if word_colors:
                    self.msg("Current word colours:")
                    for word, color in word_colors.items():
                        escaped_color = color.replace("|", "||")
                        self.msg(f"  {color}{word}|n = {escaped_color}")
                else:
                    self.msg("No word colours set.")
                self.msg("Usage: emit/colourword <word>=<colour> (e.g., emit/colourword drum=|344)")
                self.msg("To remove: emit/colourword <word>= (empty colour)")
                return
                
            word, color = self.args.split("=", 1)
            word = word.strip().lower()  # Store words in lowercase for case-insensitive matching
            color = color.strip()
            
            # Initialize word colors dict if it doesn't exist
            if not self.caller.db.emit_word_colors:
                self.caller.db.emit_word_colors = {}
            
            # Check if removing a color (empty value)
            if not color:
                if word in self.caller.db.emit_word_colors:
                    del self.caller.db.emit_word_colors[word]
                    self.msg(f"Word colour removed for: {word}")
                else:
                    self.msg(f"No colour was set for: {word}")
                return
            
            # Validate colour format
            if not color.startswith('|'):
                self.msg("Colour must start with | (e.g., |y, |r, |344)")
                return
                
            # Store the word colour setting
            self.caller.db.emit_word_colors[word] = color
            # Escape the color code in the confirmation message so it displays as text
            escaped_color = color.replace("|", "||")
            self.msg(f"Word colour set: {color}{word}|n = {escaped_color}")
            return
        
        if not self.args:
            self.msg("Usage: emit <message>, emit/shownames, emit/speechcolour <colour>, or emit/colourword <word>=<colour>")
            return
            
        if not self.caller.location:
            self.msg("You must be in a room to use emit.")
            return
            
        message = self.args.strip()
        location = self.caller.location
        
        # Check if user typed 'pose' or ':' vs 'emit' or ';' to determine message format
        is_pose = self.cmdstring.lower() in ["pose", ":"]
        
        # Send personalized messages to each receiver with their color preferences
        # We need to manually iterate since each person sees different colors
        for obj in self.caller.location.contents:
            # Only send to characters with active sessions (online players)
            if hasattr(obj, 'sessions') and obj.sessions.all():
                # Apply this receiver's color preferences to the message
                colored_message = apply_character_coloring(message, obj)
                colored_sender_name = apply_name_coloring(self.caller.name, obj)
                
                if is_pose:
                    # Pose: always show sender name at the start
                    final_message = f"{colored_sender_name} {colored_message}"
                else:
                    # Emit: check if this receiver wants to see emit names
                    show_names = obj.db.show_emit_names
                    if show_names:
                        # Show with sender name in parentheses
                        final_message = f"({colored_sender_name}) {colored_message}"
                    else:
                        # Show without sender name (traditional emit)
                        final_message = colored_message
                
                obj.msg(final_message)