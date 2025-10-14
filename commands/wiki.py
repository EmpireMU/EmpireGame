"""
Wiki command for accessing worldinfo pages in-game.
"""

from evennia.commands.default.muxcommand import MuxCommand
from django.conf import settings
from django.db.models import Q
import re
import html


class CmdWiki(MuxCommand):
    """
    Access the game wiki/knowledge base.
    
    Usage:
        wiki                        - Show category index
        wiki <page name>            - View a specific wiki page
        wiki/list <category>        - List pages in a category
        wiki/search <query>         - Search wiki pages
        
    The wiki contains setting information, game mechanics, house information,
    and other reference material. All content is also available on the website
    with full formatting, images, and character links.
    
    Examples:
        wiki                        - Show all categories
        wiki House Otrese           - View the House Otrese page
        wiki/list Houses            - List all pages in Houses category
        wiki/search combat          - Search for pages about combat
    """
    
    key = "wiki"
    locks = "cmd:all()"
    help_category = "General"
    
    def func(self):
        """Execute the command."""
        # Import here to avoid circular imports
        from web.worldinfo.models import WorldInfoPage
        
        # Check if user is staff
        is_staff = self.caller.check_permstring("Admin") or self.caller.check_permstring("Builder")
        
        # Get pages based on permissions
        if is_staff:
            all_pages = WorldInfoPage.objects.all()
        else:
            all_pages = WorldInfoPage.objects.filter(is_public=True)
        
        # Handle switches
        if self.switches:
            switch = self.switches[0].lower()
            
            if switch == "search":
                if not self.args or len(self.args.strip()) < 2:
                    self.msg("Usage: wiki/search <query> (minimum 2 characters)")
                    return
                
                self.search_pages(all_pages, self.args.strip())
                return
            
            elif switch == "list":
                if not self.args:
                    self.msg("Usage: wiki/list <category>")
                    return
                
                self.list_category(all_pages, self.args.strip())
                return
            
            else:
                self.msg(f"Unknown switch '{switch}'. Use /search or /list.")
                return
        
        # No arguments - show category index
        if not self.args:
            self.show_index(all_pages)
            return
        
        # Try to find and display a specific page
        self.show_page(all_pages, self.args.strip())
    
    def show_index(self, pages):
        """Show the wiki category index."""
        # Group pages by category
        categories = {}
        for page in pages:
            category = page.category or 'General'
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        if not categories:
            self.msg("No wiki pages are currently available.")
            return
        
        # Build output
        msg = "\n|w=== Wiki Categories ===|n\n"
        
        # Use the same category order as the web
        CATEGORY_ORDER = [
            'Introductory Information',
            'Setting Information',
            'Houses and Organisations',
            'Game Mechanics',
        ]
        
        # Sort categories
        sorted_categories = sorted(
            categories.keys(),
            key=lambda x: CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else 999
        )
        
        for category in sorted_categories:
            count = categories[category]
            plural = "page" if count == 1 else "pages"
            msg += f"\n  |c{category}|n - {count} {plural}"
            msg += f"\n    |xUse: |ywiki/list {category}|n"
        
        # Add search hint
        msg += "\n\n|xUse |ywiki/search <query>|x to search all pages."
        msg += "\n|xUse |ywiki <page name>|x to view a specific page.|n"
        
        # Add web link
        domain = getattr(settings, 'WEB_PROFILE_DOMAIN', 'empiremush.org')
        msg += f"\n\n|xFull wiki with images: |chttps://{domain}/worldinfo/|n"
        
        self.msg(msg)
    
    def list_category(self, pages, category):
        """List all pages in a specific category."""
        # Case-insensitive category match
        category_pages = [p for p in pages if (p.category or 'General').lower() == category.lower()]
        
        if not category_pages:
            self.msg(f"No pages found in category '{category}'.")
            self.msg("Use |ywiki|n to see available categories.")
            return
        
        # Get the actual category name (with proper capitalization)
        actual_category = category_pages[0].category or 'General'
        
        # Group by subcategory
        subcategories = {}
        for page in category_pages:
            subcat = page.subcategory or 'General'
            if subcat not in subcategories:
                subcategories[subcat] = []
            subcategories[subcat].append(page)
        
        # Build output
        msg = f"\n|w=== {actual_category} ===|n\n"
        
        for subcat in sorted(subcategories.keys()):
            if len(subcategories) > 1:  # Only show subcategory if there's more than one
                msg += f"\n|y{subcat}|n"
            
            for page in sorted(subcategories[subcat], key=lambda p: p.title):
                msg += f"\n  {page.title}"
                if not page.is_public:
                    msg += " |r[GM Only]|n"
        
        msg += f"\n\n|xUse |ywiki <page name>|x to view a page.|n"
        
        self.msg(msg)
    
    def show_page(self, pages, page_name):
        """Display a specific wiki page."""
        # Try to find the page by title or slug (case-insensitive)
        page = None
        for p in pages:
            if p.title.lower() == page_name.lower() or p.slug.lower() == page_name.lower():
                page = p
                break
        
        if not page:
            self.msg(f"Wiki page '{page_name}' not found.")
            self.msg("Use |ywiki/search <query>|n to search for pages.")
            return
        
        # Build the page display
        msg = f"\n|w{'=' * 78}|n"
        msg += f"\n|w{page.title.center(78)}|n"
        msg += f"\n|w{'=' * 78}|n"
        
        # Show category/subcategory
        if page.category:
            category_info = page.category
            if page.subcategory:
                category_info += f" > {page.subcategory}"
            msg += f"\n|x{category_info}|n\n"
        
        # Note if page has an emblem
        if page.emblem_image:
            msg += "\n|y[This page has an emblem image - view on web for full experience]|n\n"
        
        # Convert content to plain text
        content = self.convert_content(page.content)
        msg += f"\n{content}"
        
        # Add web link for full formatting
        domain = getattr(settings, 'WEB_PROFILE_DOMAIN', 'empiremush.org')
        web_url = f"https://{domain}/worldinfo/{page.slug}/"
        msg += f"\n\n|w{'=' * 78}|n"
        msg += f"\n|xView on web with full formatting: |c{web_url}|n"
        
        self.msg(msg)
    
    def search_pages(self, pages, query):
        """Search wiki pages for a query string."""
        query_lower = query.lower()
        results = []
        
        for page in pages:
            score = 0
            
            # Search title (highest priority)
            if query_lower in page.title.lower():
                score += 10
            
            # Search content
            if query_lower in page.content.lower():
                score += 5
            
            # Search category/subcategory
            if page.category and query_lower in page.category.lower():
                score += 3
            if page.subcategory and query_lower in page.subcategory.lower():
                score += 3
            
            if score > 0:
                results.append((score, page))
        
        if not results:
            self.msg(f"No results found for '{query}'.")
            return
        
        # Sort by score (highest first), then title
        results.sort(key=lambda x: (-x[0], x[1].title.lower()))
        
        # Build output
        msg = f"\n|w=== Search Results for '{query}' ===|n\n"
        msg += f"\nFound {len(results)} {'page' if len(results) == 1 else 'pages'}:\n"
        
        for score, page in results:
            msg += f"\n  |c{page.title}|n"
            if page.category:
                category_info = page.category
                if page.subcategory:
                    category_info += f" > {page.subcategory}"
                msg += f"\n    |x{category_info}|n"
            if not page.is_public:
                msg += " |r[GM Only]|n"
        
        msg += "\n\n|xUse |ywiki <page name>|x to view a page.|n"
        
        self.msg(msg)
    
    def convert_content(self, markdown_text):
        """
        Convert markdown content to plain text suitable for in-game display.
        Strips HTML, converts markdown formatting to Evennia color codes where possible.
        """
        # First, handle character links [[Character Name]]
        # Convert them to just the name with a note
        text = re.sub(r'\[\[([^\]]+)\]\]', r'|c\1|n', markdown_text)
        
        # Convert markdown headers to emphasized text
        # ### Header -> |wHeader|n
        text = re.sub(r'^#{1,6}\s+(.+)$', r'|w\1|n', text, flags=re.MULTILINE)
        
        # Convert markdown bold **text** or __text__ to |wtext|n
        text = re.sub(r'\*\*(.+?)\*\*', r'|w\1|n', text)
        text = re.sub(r'__(.+?)__', r'|w\1|n', text)
        
        # Convert markdown italic *text* or _text_ to |itext|n
        text = re.sub(r'\*(.+?)\*', r'|i\1|n', text)
        text = re.sub(r'_(.+?)_', r'|i\1|n', text)
        
        # Convert markdown links [text](url) to just text (url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1 (\2)', text)
        
        # Convert bullet points
        text = re.sub(r'^\s*[\*\-\+]\s+', r'  • ', text, flags=re.MULTILINE)
        
        # Handle numbered lists - just preserve the numbers
        text = re.sub(r'^\s*(\d+)\.\s+', r'  \1. ', text, flags=re.MULTILINE)
        
        # Remove horizontal rules
        text = re.sub(r'^[\-\*\_]{3,}$', '', text, flags=re.MULTILINE)
        
        # Unescape any HTML entities that might be in the text
        text = html.unescape(text)
        
        # Clean up multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

