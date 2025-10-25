"""
Template filters for automatic glossary term highlighting.
"""
import re
import html
import uuid
from django import template
from django.utils.safestring import mark_safe
from django.db.models.functions import Length
from ..models import GlossaryTerm

register = template.Library()


@register.filter(name='glossary')
def glossary(text):
    """
    Automatically highlight the first instance of each glossary term in the text.
    
    Usage:
        {{ content|safe|glossary }}
    
    This filter finds glossary terms in the text and wraps the first occurrence
    of each term with a special span that triggers a popover with the definition.
    """
    if not text:
        return text
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Get all active glossary terms, ordered by priority (higher first)
    terms = (
        GlossaryTerm.objects
        .filter(is_active=True)
        .annotate(term_length=Length('term'))
        .order_by('-priority', '-term_length')
    )
    
    if not terms:
        return text
    
    # Track which terms we've already replaced (one per term per document)
    replaced_term_keys = set()

    def normalize_term(term_text, is_case_sensitive):
        """Normalize term text for deduplication depending on case sensitivity."""
        return term_text if is_case_sensitive else term_text.lower()
    
    # Work with the text
    result = str(text)
    
    for term_obj in terms:
        # Get all terms (primary + aliases) for this glossary entry
        all_terms = term_obj.get_all_terms()
        
        if term_obj.term == "Sanctuary":
            logger.warning(f"DEBUG: Processing Sanctuary - all_terms: {all_terms}, case_sensitive: {term_obj.case_sensitive}, priority: {term_obj.priority}")
        
        # Try to match any of the terms
        first_match = None
        
        for search_term in all_terms:
            # Skip if we've already replaced this specific term
            term_key = (normalize_term(search_term, term_obj.case_sensitive), term_obj.case_sensitive)
            if term_key in replaced_term_keys:
                continue
            
            # Build the pattern for this term
            if term_obj.case_sensitive:
                # Case-sensitive: match exact term
                pattern = re.escape(search_term)
                flags = 0
            else:
                # Case-insensitive
                pattern = re.escape(search_term)
                flags = re.IGNORECASE
            
            # Important: Only match whole words, not parts of words
            # Use word boundaries but handle special characters
            pattern = r'\b' + pattern + r'\b'
            
            # We need to avoid matching inside HTML tags or existing glossary spans
            # Strategy: Find all matches, then check if they're inside tags
            matches = list(re.finditer(pattern, result, flags=flags))
            
            if not matches:
                continue
            
            # Check if this is the earliest match we've found
            for match in matches:
                if (
                    first_match is None
                    or match.start() < first_match.start()
                    or (
                        match.start() == first_match.start()
                        and match.end() > first_match.end()
                    )
                ):
                    first_match = match
                    break  # Only need the first match of this term
        
        # If we didn't find any matches for this glossary entry, continue
        if first_match is None:
            if term_obj.term == "Sanctuary":
                logger.warning(f"DEBUG: No match found for Sanctuary in text")
            continue
        
        match = first_match
        matched_text = match.group(0)
        
        # Check if this match is inside an HTML tag or existing glossary button
        # Look backwards from match position to find if we're inside actual tag content
        start_pos = match.start()
        text_before = result[:start_pos]
        
        # Check if we're between < and > (inside a tag definition, not content)
        # But we need to be careful: we could be inside a data attribute value
        # Strategy: find the last < and >, and check if we're truly in tag markup
        last_open_tag = text_before.rfind('<')
        last_close_tag = text_before.rfind('>')
        
        if last_open_tag > last_close_tag:
            # We might be inside a tag, but check if we're in an attribute value
            # Count quotes after the last < to see if we're inside a quoted string
            tag_content = text_before[last_open_tag:]
            # Count unescaped quotes
            quote_count = tag_content.count('"') - tag_content.count('\\"')
            # If odd number of quotes, we're inside a quoted attribute value, which is OK
            if quote_count % 2 == 0:
                # Even quotes means we're in actual tag markup, skip it
                if term_obj.term == "Sanctuary":
                    logger.warning(f"DEBUG: Sanctuary skipped - inside HTML tag markup")
                continue
            # Odd quotes means we're inside an attribute value, continue processing
        
        # Check if we're inside an existing glossary button by ensuring the last opening button tag is closed
        last_glossary_open = result.rfind('<button type="button" class="glossary-term"', 0, start_pos)
        if last_glossary_open != -1:
            # Look for a closing </button> between the opening and the current match
            button_close = result.find('</button>', last_glossary_open, start_pos)
            if button_close == -1:
                # No closing tag before this position, so we're inside the button
                if term_obj.term == "Sanctuary":
                    logger.warning(f"DEBUG: Sanctuary skipped - inside glossary button")
                continue
        
        # Build the replacement HTML
        # Escape the description for HTML
        description_escaped = html.escape(term_obj.short_description, quote=True)
        term_escaped = html.escape(term_obj.term, quote=True)
        unique_id = uuid.uuid4().hex
        trigger_id = f"glossary-trigger-{unique_id}"
        popover_id = f"glossary-popover-{unique_id}"

        data_attrs = [
            ("data-glossary-term", term_escaped),
            ("data-glossary-desc", description_escaped),
            ("data-glossary-popover-id", popover_id),
        ]
        
        if term_obj.link_url:
            link_url_escaped = html.escape(term_obj.link_url, quote=True)
            link_text_escaped = html.escape(term_obj.link_text or "Learn more", quote=True)
            data_attrs.extend([
                ("data-glossary-url", link_url_escaped),
                ("data-glossary-link-text", link_text_escaped),
            ])

        data_attr_string = " ".join(f'{name}="{value}"' for name, value in data_attrs)
        
        # Create the replacement button
        replacement = (
            f'<button type="button" class="glossary-term" id="{trigger_id}" '
            f'aria-haspopup="dialog" aria-expanded="false" aria-controls="{popover_id}" '
            f'{data_attr_string}>{matched_text}</button>'
        )
        
        # Replace only this first occurrence
        result = result[:match.start()] + replacement + result[match.end():]
        
        if term_obj.term == "Sanctuary":
            logger.warning(f"DEBUG: Sanctuary REPLACED successfully at position {match.start()}")
        
        # Mark all terms (primary + aliases) as replaced so we don't match them again
        for t in all_terms:
            # Only track the key with the actual case sensitivity of this entry
            replaced_term_keys.add((normalize_term(t, term_obj.case_sensitive), term_obj.case_sensitive))
    
    return mark_safe(result)


@register.filter(name='glossary_plaintext')
def glossary_plaintext(text):
    """
    Apply glossary highlighting to plain text (converts to HTML first).
    
    Usage:
        {{ plain_text|glossary_plaintext }}
    
    This is useful for applying glossary to text that hasn't been
    converted to HTML yet (e.g., character descriptions).
    """
    if not text:
        return text
    
    # Convert plain text to HTML (simple line breaks)
    html_text = text.replace('\n', '<br>')
    
    # Apply glossary filter
    return glossary(html_text)

