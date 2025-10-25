# Glossary System

An automatic glossary/tooltip system that highlights terms on worldinfo and roster pages without manual markup.

## Overview

The glossary system automatically finds and highlights the **first instance** of each configured term in your content. When users click a highlighted term, they see a popover with:
- The term name
- A short description
- An optional "Learn more" link to the full page

## Features

- **Automatic highlighting**: Just add terms to the database - no manual markup needed
- **First instance only**: Each term is highlighted only once per page (not intrusive)
- **Smart matching**: Whole-word matching, case-insensitive by default
- **Priority system**: Control which terms get matched first (useful for overlapping terms)
- **Visual indicators**: Subtle dotted underline that changes color on hover
- **Responsive popovers**: Click to show, click outside or press ESC to close
- **Works across pages**: Worldinfo pages and character roster pages

## Setup

### 1. Run the migration

```bash
python manage.py migrate worldinfo
```

### 2. Add glossary terms

Go to Django admin → Worldinfo → Glossary Terms

Or: `http://yourdomain.com/admin/worldinfo/glossaryterm/`

### 3. Create terms

For each term you want to highlight:

**Required fields:**
- **Term**: The word or phrase to highlight (e.g., "Westelth", "The Empire")
- **Short description**: Brief explanation (max 500 chars) shown in the popover

**Optional fields:**
- **Link URL**: URL to full page (e.g., `/world/westelth/` or `/characters/detail/ardent/123/`)
- **Link text**: Text for the link button (default: "Learn more")
- **Is active**: Uncheck to temporarily disable this term
- **Case sensitive**: Check if the term must match exactly (rare)
- **Priority**: Higher numbers matched first (use for overlapping terms)

## Usage Examples

### Example 1: Simple term

```
Term: Westelth
Short description: The western realm, known for its maritime culture and powerful navy.
Link URL: /world/westelth/
Link text: Learn more
Is active: ✓
Priority: 0
```

Result: The first instance of "Westelth" in any worldinfo or roster page will be highlighted. Clicking it shows the description and a "Learn more" link.

### Example 2: Character name

```
Term: Queen Aldara
Short description: The current ruler of Westelth, known for her diplomatic skill and love of the sea.
Link URL: /characters/detail/aldara/456/
Link text: View character sheet
Is active: ✓
Priority: 0
```

Result: First mention of "Queen Aldara" gets highlighted with a link to her character sheet.

### Example 3: Overlapping terms

If you have both "The Empire" and "Empire" as terms:

```
Term: The Empire
Priority: 10
---
Term: Empire
Priority: 0
```

The system will match "The Empire" first (higher priority), then "Empire" only where "The Empire" wasn't matched.

## Where It Works

The glossary system is active on:

1. **Worldinfo pages**: All content in worldinfo articles
2. **Character roster pages**: 
   - Description field
   - Background field
   - Personality field

## Technical Details

### Template Filter

The glossary uses a Django template filter: `glossary`

Applied automatically in:
- `web/worldinfo/templates/worldinfo/page.html`
- `web/roster/templates/roster/character_detail.html`

Example usage:
```django
{{ content|safe|glossary }}
```

### How It Works

1. Filter loads all active glossary terms (ordered by priority, then length)
2. For each term, finds the first match in the content using regex
3. Wraps match with: `<span class="glossary-term" data-glossary-term="..." data-glossary-desc="..." ...>term</span>`
4. JavaScript adds click handlers to show/hide popovers
5. CSS provides styling for the subtle visual indicators

### Performance

- Terms are loaded once per page render (cached by Django's ORM)
- Regex matching is efficient (pre-compiled patterns)
- Only active terms are processed
- No database queries in JavaScript (all data in HTML data attributes)

## Styling

### Visual Appearance

- **Normal state**: Subtle gray dotted underline, dark gray text
- **Hover state**: Blue dotted underline, blue text
- **Cursor**: Help cursor (question mark)

### Popover

- Clean white card with subtle shadow
- Header (term name), body (description), footer (link)
- Max width: 350px
- Smart positioning: appears below term, or above if not enough space
- Auto-adjusts to avoid going off screen edges

## Tips

### Best Practices

1. **Be selective**: Don't add every term - focus on unique world-building concepts
2. **Keep descriptions brief**: Aim for 1-2 sentences (max 500 chars)
3. **Test overlapping terms**: Use priority to handle "Empire" vs "The Empire"
4. **Use case-insensitive**: Most terms should be case-insensitive (default)
5. **Link to relevant pages**: Always provide a link URL when possible

### Common Terms to Add

- Realm/nation names (Westelth, Eastelth, etc.)
- Important organizations (The Merchant's Guild, The Council, etc.)
- Unique concepts (The Calling, The Awakening, etc.)
- Major locations (The Capital, The Citadel, etc.)
- Key historical events (The Great War, The Treaty, etc.)

### When NOT to Use

Don't add terms for:
- Very common words (unless truly unique to your world)
- Character names already linked via `[[Character Name]]` syntax
- Terms that appear hundreds of times
- Generic concepts everyone knows

## Troubleshooting

### Term not highlighting

**Check:**
1. Is "Is active" checked?
2. Does the term appear in the content?
3. Is it being matched by a higher-priority term?
4. Is it inside an HTML tag? (won't match inside existing links)

### Wrong term highlighted

**Fix:**
- Adjust priority values
- Use case-sensitive matching if needed
- Make terms more specific

### Popover not appearing

**Check:**
1. JavaScript errors in browser console
2. CSS loaded correctly
3. Data attributes present in HTML (inspect element)

### Multiple instances highlighted

**This shouldn't happen** - the filter only highlights the first instance. If you see this, there may be a template filter applied multiple times.

## Future Enhancements

Possible improvements:
- Admin action to bulk import terms from CSV
- Analytics on which terms are clicked most
- Support for multi-word variations (e.g., "Empire" and "The Empire" as aliases)
- Category/tag system for terms
- Optional glossary index page showing all terms

## Files Modified

- `web/worldinfo/models.py` - Added GlossaryTerm model
- `web/worldinfo/admin.py` - Added GlossaryTermAdmin
- `web/worldinfo/migrations/0004_glossaryterm.py` - Migration file
- `web/worldinfo/templatetags/__init__.py` - Created templatetags package
- `web/worldinfo/templatetags/glossary_filters.py` - Template filter implementation
- `web/worldinfo/templates/worldinfo/page.html` - Applied filter, added CSS/JS
- `web/roster/templates/roster/character_detail.html` - Applied filter, added CSS/JS

## Support

If you encounter issues or have questions, check:
1. This documentation
2. Django admin for term configuration
3. Browser console for JavaScript errors
4. Django logs for template/filter errors

