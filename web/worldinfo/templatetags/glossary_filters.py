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
    replaced_terms = set()
    
    # Work with the text
    result = str(text)
    
    for term_obj in terms:
        # Get all terms (primary + aliases) for this glossary entry
        all_terms = term_obj.get_all_terms()
        
        # Try to match any of the terms
        first_match = None
        
        for search_term in all_terms:
            # Skip if we've already replaced this specific term
            search_term_lower = search_term.lower()
            if search_term_lower in replaced_terms:
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
            continue
        
        match = first_match
        matched_text = match.group(0)
        
        # Check if this match is inside an HTML tag or existing glossary span
        # Look backwards from match position to find if we're inside a tag
        start_pos = match.start()
        
        # Simple heuristic: if the last < before this position doesn't have a closing >
        # then we're inside a tag
        text_before = result[:start_pos]
        last_open_tag = text_before.rfind('<')
        last_close_tag = text_before.rfind('>')
        
        # Skip if we're inside a tag
        if last_open_tag > last_close_tag:
            continue
        
        # Check if we're inside an existing glossary span by looking for data-glossary attribute
        # Look back for opening tags
        recent_context = text_before[max(0, start_pos - 200):start_pos]
        if 'data-glossary-term' in recent_context:
            # Check if there's a closing glossary element between the last glossary trigger and here
            last_glossary_attr = recent_context.rfind('data-glossary-term')
            context_after_span = recent_context[last_glossary_attr:]
            if ('</span>' not in context_after_span) and ('</button>' not in context_after_span):
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
        
        # Mark all terms (primary + aliases) as replaced so we don't match them again
        for t in all_terms:
            replaced_terms.add(t.lower())
    
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

