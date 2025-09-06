"""
Message coloring utilities for roleplay commands.

Provides functions to colorize speech and specific words in messages
based on player preferences.
"""

import re


def colorize_speech(message, speech_color="|y"):
    """
    Colourise quoted speech in a message.
    
    Args:
        message (str): The message to process
        speech_color (str): The colour code to apply to speech
        
    Returns:
        str: Message with coloured speech
    """
    # Pattern to match quoted speech (both " and ' quotes)
    # This matches quotes and everything between them
    speech_pattern = r'(["\'])([^"\']*?)\1'
    
    def replace_speech(match):
        quote_char = match.group(1)
        speech_content = match.group(2)
        return f"{speech_color}{quote_char}{speech_content}{quote_char}|n"
    
    return re.sub(speech_pattern, replace_speech, message)


def colorize_words(message, word_colors):
    """
    Colourise specific words in a message.
    
    Args:
        message (str): The message to process
        word_colors (dict): Dictionary of word -> color mappings
        
    Returns:
        str: Message with coloured words
    """
    if not word_colors:
        return message
        
    # Apply word coloring (case-insensitive)
    for word, color in word_colors.items():
        # Use word boundary regex to match whole words only
        pattern = r'\b' + re.escape(word) + r'\b'
        replacement = f"{color}\\g<0>|n"
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    
    return message


def apply_character_coloring(message, character):
    """
    Apply a character's color preferences to a message.
    
    Args:
        message (str): The message to process
        character: The character object with color preferences
        
    Returns:
        str: Message with character's color preferences applied
    """
    # Get character's speech colour preference (default to |y)
    speech_color = character.db.emit_speech_color or "|y"
    
    # Get character's word colour preferences
    word_colors = character.db.emit_word_colors or {}
    
    # Apply word colouring first, then speech colouring
    colored_message = colorize_words(message, word_colors)
    colored_message = colorize_speech(colored_message, speech_color)
    
    return colored_message


def apply_name_coloring(name, character):
    """
    Apply a character's word color preferences to a sender name in emit attribution.
    
    This is used for coloring names that appear at the start of poses or in 
    parentheses for emits (e.g., "Ada sits down" or "(Ada) message").
    
    Args:
        name (str): The sender name to process
        character: The character object with color preferences
        
    Returns:
        str: Sender name with character's word color preferences applied
    """
    # Get character's word colour preferences
    word_colors = character.db.emit_word_colors or {}
    
    # Apply word colouring to the name
    return colorize_words(name, word_colors)
