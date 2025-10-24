"""Template filters for scene display."""

import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


# Evennia ANSI color mappings to HTML colors
ANSI_COLORS = {
    'n': '</span>',  # normal/reset
    'r': '<span style="color: #ff0000;">',  # red
    'g': '<span style="color: #00ff00;">',  # green
    'y': '<span style="color: #ffff00;">',  # yellow
    'b': '<span style="color: #0000ff;">',  # blue
    'm': '<span style="color: #ff00ff;">',  # magenta
    'c': '<span style="color: #00ffff;">',  # cyan
    'w': '<span style="color: #ffffff;">',  # white
    'x': '<span style="color: #808080;">',  # dark gray
    'R': '<span style="color: #ff0000; font-weight: bold;">',  # bright red
    'G': '<span style="color: #00ff00; font-weight: bold;">',  # bright green
    'Y': '<span style="color: #ffff00; font-weight: bold;">',  # bright yellow
    'B': '<span style="color: #0000ff; font-weight: bold;">',  # bright blue
    'M': '<span style="color: #ff00ff; font-weight: bold;">',  # bright magenta
    'C': '<span style="color: #00ffff; font-weight: bold;">',  # bright cyan
    'W': '<span style="color: #ffffff; font-weight: bold;">',  # bright white
}


def xterm256_to_rgb(code):
    """Convert xterm-256 color code to RGB hex."""
    code = int(code)
    
    # Standard colors (0-15)
    if code < 16:
        standard = [
            '#000000', '#800000', '#008000', '#808000', '#000080', '#800080', '#008080', '#c0c0c0',
            '#808080', '#ff0000', '#00ff00', '#ffff00', '#0000ff', '#ff00ff', '#00ffff', '#ffffff'
        ]
        return standard[code]
    
    # 216 color cube (16-231)
    elif code < 232:
        code -= 16
        r = (code // 36) * 51
        g = ((code % 36) // 6) * 51
        b = (code % 6) * 51
        return f'#{r:02x}{g:02x}{b:02x}'
    
    # Grayscale (232-255)
    else:
        gray = 8 + (code - 232) * 10
        return f'#{gray:02x}{gray:02x}{gray:02x}'


@register.filter(name='ansi_to_html')
def ansi_to_html(text):
    """Convert Evennia ANSI codes (|r, |g, |n, |123, etc.) to HTML spans."""
    if not text:
        return ""
    
    # Escape HTML first
    text = escape(text)
    
    # Replace xterm-256 color codes (|000 to |555)
    def replace_xterm(match):
        code = match.group(1)
        try:
            rgb = xterm256_to_rgb(code)
            return f'<span style="color: {rgb};">'
        except (ValueError, IndexError):
            return match.group(0)  # Return original if invalid
    
    html = re.sub(r'\|(\d{3})', replace_xterm, text)
    
    # Replace single-letter ANSI codes
    def replace_ansi(match):
        code = match.group(1)
        return ANSI_COLORS.get(code, '')
    
    html = re.sub(r'\|([a-zA-Z])', replace_ansi, html)
    
    # Ensure all spans are closed
    html = f'<span style="color: #e0e0e0;">{html}</span>'
    
    return mark_safe(html)


@register.filter(name='strip_ansi')
def strip_ansi(text):
    """Strip ANSI color codes from text."""
    if not text:
        return ""
    # Remove xterm-256 codes
    text = re.sub(r'\|\d{3}', '', text)
    # Remove basic ANSI codes
    text = re.sub(r'\|[a-zA-Z]', '', text)
    return text
